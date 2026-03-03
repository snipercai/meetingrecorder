"""
音频采集模块
用于从麦克风采集音频数据
"""

import logging
from typing import Callable, Optional

import numpy as np
import pyaudio

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(console_handler)


class AudioCaptureError(Exception):
    """音频采集相关异常基类"""
    pass


class MicrophoneNotAvailableError(AudioCaptureError):
    """麦克风设备不可用异常"""
    pass


class AudioStreamError(AudioCaptureError):
    """音频流初始化或操作异常"""
    pass


class AudioCapture:
    """音频采集类，用于从麦克风采集音频数据"""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024
    ):
        """
        初始化音频参数

        Args:
            sample_rate: 采样率，默认16000Hz
            channels: 声道数，默认1（单声道）
            chunk_size: 每次读取的音频帧数，默认1024
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size

        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._is_capturing: bool = False
        self._callback: Optional[Callable[[np.ndarray], None]] = None

        logger.info(
            f"AudioCapture 实例创建 - 采样率: {sample_rate}Hz, "
            f"声道数: {channels}, 帧大小: {chunk_size}"
        )

    @property
    def is_capturing(self) -> bool:
        """
        返回是否正在采集

        Returns:
            bool: 是否正在采集音频
        """
        return self._is_capturing

    def initialize(self) -> None:
        """
        初始化麦克风设备

        Raises:
            MicrophoneNotAvailableError: 麦克风设备不可用
            AudioStreamError: PyAudio初始化失败
        """
        try:
            logger.info("正在初始化麦克风设备...")
            self._pyaudio = pyaudio.PyAudio()
            logger.debug(f"PyAudio 初始化成功，检测到 {self._pyaudio.get_device_count()} 个音频设备")

            default_input = self._pyaudio.get_default_input_device_info()
            logger.info(
                f"默认输入设备: {default_input['name']} "
                f"(采样率: {default_input['defaultSampleRate']}Hz)"
            )

            input_devices = []
            for i in range(self._pyaudio.get_device_count()):
                device_info = self._pyaudio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(device_info['name'])

            if not input_devices:
                raise MicrophoneNotAvailableError("未检测到可用的麦克风设备")

            logger.info(f"可用输入设备: {input_devices}")
            logger.info("麦克风设备初始化完成")

        except OSError as e:
            error_msg = f"PyAudio 初始化失败: {e}"
            logger.error(error_msg)
            raise AudioStreamError(error_msg) from e
        except Exception as e:
            error_msg = f"麦克风设备初始化异常: {e}"
            logger.error(error_msg)
            raise MicrophoneNotAvailableError(error_msg) from e

    def _audio_callback(
        self,
        in_data: bytes,
        frame_count: int,
        time_info: dict,
        status: int
    ) -> tuple:
        """
        音频流回调函数

        Args:
            in_data: 音频数据字节
            frame_count: 帧数
            time_info: 时间信息
            status: 状态标志

        Returns:
            tuple: (None, pyaudio.paContinue)
        """
        try:
            audio_data = np.frombuffer(in_data, dtype=np.int16)

            if self._callback is not None:
                self._callback(audio_data)

        except Exception as e:
            logger.error(f"音频数据处理错误: {e}")

        return (None, pyaudio.paContinue)

    def start_capture(self, callback: Callable[[np.ndarray], None]) -> None:
        """
        开始采集音频流

        Args:
            callback: 回调函数，接收numpy数组格式的音频数据

        Raises:
            AudioStreamError: 音频流初始化失败
            RuntimeError: 未初始化设备或已在采集中
        """
        if self._pyaudio is None:
            error_msg = "未初始化麦克风设备，请先调用 initialize()"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        if self._is_capturing:
            logger.warning("音频采集已在进行中")
            return

        try:
            logger.info("正在启动音频采集...")
            self._callback = callback

            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )

            self._stream.start_stream()
            self._is_capturing = True

            logger.info(
                f"音频采集已启动 - 格式: 16位PCM, "
                f"采样率: {self.sample_rate}Hz, "
                f"声道: {self.channels}"
            )

        except OSError as e:
            error_msg = f"音频流初始化失败: {e}"
            logger.error(error_msg)
            self._cleanup_stream()
            raise AudioStreamError(error_msg) from e
        except Exception as e:
            error_msg = f"启动音频采集异常: {e}"
            logger.error(error_msg)
            self._cleanup_stream()
            raise AudioStreamError(error_msg) from e

    def stop_capture(self) -> None:
        """
        停止采集并释放资源
        """
        logger.info("正在停止音频采集...")
        self._is_capturing = False
        self._callback = None
        self._cleanup_stream()
        logger.info("音频采集已停止")

    def _cleanup_stream(self) -> None:
        """
        清理音频流资源
        """
        if self._stream is not None:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
                logger.debug("音频流已关闭")
            except Exception as e:
                logger.warning(f"关闭音频流时出错: {e}")
            finally:
                self._stream = None

    def cleanup(self) -> None:
        """
        释放所有资源
        """
        self.stop_capture()

        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
                logger.debug("PyAudio 已终止")
            except Exception as e:
                logger.warning(f"终止 PyAudio 时出错: {e}")
            finally:
                self._pyaudio = None

        logger.info("AudioCapture 资源已释放")

    def __enter__(self) -> "AudioCapture":
        """上下文管理器入口"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.cleanup()
