"""
ASR引擎模块
基于Qwen3-ASR-0.6B模型实现语音识别功能
支持从ModelScope或HuggingFace加载模型
"""

import logging
from typing import Callable, Optional, Union, Generator
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)


class ASRError(Exception):
    """ASR引擎异常基类"""
    pass


class ModelLoadError(ASRError):
    """模型加载失败异常"""
    pass


class DeviceNotAvailableError(ASRError):
    """设备不可用异常"""
    pass


class InferenceError(ASRError):
    """推理错误异常"""
    pass


class ASREngine:
    """
    ASR引擎类
    封装Qwen3-ASR-0.6B模型的加载和推理功能
    """

    # 默认模型名称
    DEFAULT_MODEL_NAME = "Qwen/Qwen3-ASR-0.6B"

    def __init__(self, model_path: Optional[str] = None, device: str = "cuda"):
        """
        初始化ASR引擎

        Args:
            model_path: 本地模型路径，如果为None则使用默认模型名称
            device: 推理设备，支持"cuda"或"cpu"
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        self._is_loaded = False

        logger.info(f"初始化ASR引擎，设备: {device}，模型路径: {model_path or '自动下载'}")

    def _check_device_availability(self) -> str:
        """
        检查设备可用性

        Returns:
            实际可用的设备名称

        Raises:
            DeviceNotAvailableError: 当请求的设备不可用时
        """
        import torch
        
        if self.device == "auto":
            if torch.cuda.is_available():
                logger.info(f"CUDA可用，设备数量: {torch.cuda.device_count()}，自动选择CUDA模式")
                return "cuda"
            else:
                logger.info("CUDA不可用，自动选择CPU模式")
                return "cpu"
        elif self.device == "cuda":
            if not torch.cuda.is_available():
                logger.warning("CUDA不可用，将回退到CPU模式")
                return "cpu"
            logger.info(f"CUDA可用，设备数量: {torch.cuda.device_count()}")
            return "cuda"
        elif self.device == "cpu":
            logger.info("使用CPU模式")
            return "cpu"
        else:
            logger.error(f"不支持的设备类型: {self.device}")
            raise DeviceNotAvailableError(f"不支持的设备类型: {self.device}")

    def load_model(self) -> None:
        """
        加载Qwen3-ASR-0.6B模型

        Raises:
            ModelLoadError: 模型加载失败时抛出
            DeviceNotAvailableError: 设备不可用时抛出
        """
        if self._is_loaded:
            logger.info("模型已加载，跳过重复加载")
            return

        try:
            import torch
            from qwen_asr import Qwen3ASRModel

            # 检查设备可用性
            actual_device = self._check_device_availability()

            # 确定模型路径或名称
            model_identifier = self.model_path or self.DEFAULT_MODEL_NAME
            logger.info(f"开始加载模型: {model_identifier}")

            # 设置数据类型
            dtype = torch.bfloat16 if actual_device == "cuda" else torch.float32

            # 加载模型
            logger.debug("加载模型...")
            self.model = Qwen3ASRModel.from_pretrained(
                model_identifier,
                dtype=dtype,
                device_map=actual_device if actual_device == "cuda" else "cpu",
                max_inference_batch_size=1,
            )
            logger.debug("模型加载完成")

            self._is_loaded = True
            logger.info(f"模型加载成功，设备: {actual_device}")

        except ImportError as e:
            error_msg = f"qwen-asr库未安装，请运行: pip install qwen-asr. 错误: {e}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from e

        except torch.cuda.OutOfMemoryError as e:
            error_msg = f"CUDA内存不足: {str(e)}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from e

        except OSError as e:
            error_msg = f"模型文件不存在或无法访问: {str(e)}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from e

        except Exception as e:
            error_msg = f"模型加载失败: {str(e)}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from e

    def _ensure_model_loaded(self) -> None:
        """
        确保模型已加载

        Raises:
            ModelLoadError: 模型未加载时抛出
        """
        if not self._is_loaded or self.model is None:
            error_msg = "模型未加载，请先调用load_model()"
            logger.error(error_msg)
            raise ModelLoadError(error_msg)

    def transcribe(self, audio_data: Union[str, Path, bytes]) -> str:
        """
        对音频数据进行识别

        Args:
            audio_data: 音频数据，支持以下格式：
                - str/Path: 音频文件路径
                - bytes: 音频字节数据

        Returns:
            识别出的文字结果

        Raises:
            InferenceError: 推理失败时抛出
            ModelLoadError: 模型未加载时抛出
        """
        self._ensure_model_loaded()

        try:
            import torch
            
            logger.debug(f"开始音频识别，输入类型: {type(audio_data).__name__}")

            # 处理不同类型的输入
            if isinstance(audio_data, (str, Path)):
                # 文件路径输入
                audio_path = str(audio_data)
                logger.debug(f"从文件加载音频: {audio_path}")
                
                # 使用模型进行识别
                result = self.model.transcribe(audio_path)
            elif isinstance(audio_data, bytes):
                # 字节数据输入 - 需要先保存为临时文件
                logger.debug("处理音频字节数据")
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(audio_data)
                    tmp_path = tmp_file.name
                
                try:
                    result = self.model.transcribe(tmp_path)
                finally:
                    os.unlink(tmp_path)
            else:
                raise InferenceError(f"不支持的音频数据类型: {type(audio_data)}")

            # 处理返回结果 - qwen-asr返回List[ASRTranscription]
            # ASRTranscription对象有text属性包含识别文本
            if isinstance(result, list) and len(result) > 0:
                # 取第一个ASRTranscription对象的text属性
                first_result = result[0]
                if hasattr(first_result, 'text'):
                    result_text = first_result.text
                else:
                    result_text = str(first_result)
            elif hasattr(result, 'text'):
                # 单个ASRTranscription对象
                result_text = result.text
            elif isinstance(result, str):
                result_text = result
            else:
                # 尝试转换为字符串
                result_text = str(result) if result else ""

            # 确保结果是字符串
            if not isinstance(result_text, str):
                result_text = ""

            logger.info(f"识别完成，结果长度: {len(result_text)} 字符")
            return result_text

        except torch.cuda.OutOfMemoryError as e:
            error_msg = f"推理时CUDA内存不足: {str(e)}"
            logger.error(error_msg)
            raise InferenceError(error_msg) from e

        except Exception as e:
            error_msg = f"音频识别失败: {str(e)}"
            logger.error(error_msg)
            raise InferenceError(error_msg) from e

    def transcribe_stream(
        self,
        audio_stream: Generator[bytes, None, None],
        callback: Callable[[str, bool], None]
    ) -> None:
        """
        实时流式识别

        Args:
            audio_stream: 音频数据流生成器，每次产生一块音频数据
            callback: 回调函数，接收两个参数：
                - text: 识别出的文字
                - is_final: 是否为最终结果

        Raises:
            InferenceError: 推理失败时抛出
            ModelLoadError: 模型未加载时抛出
        """
        self._ensure_model_loaded()

        logger.info("开始流式识别")

        try:
            # 累积音频缓冲区
            audio_buffer = []
            chunk_count = 0

            for chunk in audio_stream:
                chunk_count += 1
                audio_buffer.append(chunk)
                logger.debug(f"接收到音频块 {chunk_count}，大小: {len(chunk)} 字节")

                # 合并音频数据进行识别
                combined_audio = b"".join(audio_buffer)

                try:
                    # 对累积的音频进行识别
                    result = self.transcribe(combined_audio)

                    # 通过回调返回中间结果
                    if result:
                        callback(result, is_final=False)

                except InferenceError as e:
                    logger.warning(f"中间结果识别失败: {str(e)}")
                    continue

            # 处理最终结果
            if audio_buffer:
                combined_audio = b"".join(audio_buffer)
                final_result = self.transcribe(combined_audio)
                callback(final_result, is_final=True)
                logger.info(f"流式识别完成，最终结果长度: {len(final_result)} 字符")

        except Exception as e:
            error_msg = f"流式识别失败: {str(e)}"
            logger.error(error_msg)
            raise InferenceError(error_msg) from e

    def release(self) -> None:
        """
        释放模型资源
        """
        if self.model is not None:
            logger.info("释放模型资源")

            # 删除模型引用
            del self.model
            self.model = None
            self._is_loaded = False

            # 清理CUDA缓存
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.debug("CUDA缓存已清理")
            except ImportError:
                pass

            logger.info("模型资源已释放")

    @property
    def is_loaded(self) -> bool:
        """
        检查模型是否已加载

        Returns:
            模型是否已加载
        """
        return self._is_loaded

    def __enter__(self):
        """
        上下文管理器入口
        """
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.release()
        return False

    def __del__(self):
        """
        析构函数，确保资源释放
        """
        if self._is_loaded:
            self.release()
