# -*- coding: utf-8 -*-
"""
会议转写系统主入口模块
协调音频采集、ASR识别、LLM总结、文件管理和Web服务等模块
"""

import argparse
import asyncio
import signal
import sys
from typing import Optional

from config import (
    AudioConfig,
    ASRConfig,
    LLMConfig,
    WebConfig,
    SummaryConfig,
    OUTPUT_DIR,
    validate_config
)
from logger import get_logger, set_log_level, LoggerManager
from audio_capture import AudioCapture, AudioCaptureError
from asr_engine import ASREngine, ASRError
from summarizer import Summarizer
from file_manager import FileManager
from web_server import WebServer

logger = get_logger(__name__)


class MeetingRecorder:
    """
    会议转写系统主类
    负责协调各模块之间的数据流转和生命周期管理
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        device: str = None,
        interval: int = None,
        log_level: str = None,
        llm_api_url: str = None,
        llm_api_key: str = None,
        llm_api_model: str = None
    ):
        """
        初始化会议转写系统

        Args:
            host: Web服务主机地址
            port: Web服务端口
            device: 模型设备（cuda/cpu）
            interval: 总结间隔（秒）
            log_level: 日志级别
            llm_api_url: LLM API地址
            llm_api_key: LLM API密钥
            llm_api_model: LLM API模型名称
        """
        self.host = host or WebConfig.HOST
        self.port = port or WebConfig.PORT
        self.device = device or ASRConfig.DEVICE
        self.interval = interval or SummaryConfig.INTERVAL
        self.log_level = log_level or "INFO"
        self.llm_api_url = llm_api_url
        self.llm_api_key = llm_api_key
        self.llm_api_model = llm_api_model

        self._is_running = False
        self._shutdown_event = asyncio.Event()

        self.audio_capture: Optional[AudioCapture] = None
        self.asr_engine: Optional[ASREngine] = None
        self.summarizer: Optional[Summarizer] = None
        self.file_manager: Optional[FileManager] = None
        self.web_server: Optional[WebServer] = None

        self._transcription_buffer: list = []
        self._audio_buffer: list = []
        self._last_transcription: str = ""

        logger.info("MeetingRecorder 实例创建")

    def _setup_logging(self):
        """配置日志系统"""
        try:
            LoggerManager()
            set_log_level(self.log_level)
            logger.info(f"日志级别设置为: {self.log_level}")
        except Exception as e:
            print(f"日志系统初始化失败: {e}", file=sys.stderr)

    def _initialize_modules(self) -> bool:
        """
        初始化所有模块

        Returns:
            bool: 初始化成功返回True，失败返回False
        """
        try:
            logger.info("=" * 50)
            logger.info("开始初始化各模块...")
            logger.info("=" * 50)

            logger.info("[1/5] 初始化文件管理器...")
            self.file_manager = FileManager(output_dir=str(OUTPUT_DIR))
            self.file_manager.create_meeting_file()
            logger.info("文件管理器初始化完成")

            logger.info("[2/5] 初始化Web服务器...")
            self.web_server = WebServer(host=self.host, port=self.port)
            logger.info("Web服务器初始化完成")

            logger.info("[3/5] 初始化音频采集模块...")
            self.audio_capture = AudioCapture(
                sample_rate=AudioConfig.SAMPLE_RATE,
                channels=AudioConfig.CHANNELS,
                chunk_size=AudioConfig.CHUNK_SIZE
            )
            self.audio_capture.initialize()
            logger.info("音频采集模块初始化完成")

            logger.info("[4/5] 初始化ASR引擎...")
            self.asr_engine = ASREngine(device=self.device)
            self.asr_engine.load_model()
            logger.info("ASR引擎初始化完成")

            logger.info("[5/5] 初始化LLM总结器...")
            self.summarizer = Summarizer(
                api_base_url=self.llm_api_url,
                api_key=self.llm_api_key,
                api_model=self.llm_api_model
            )
            if not self.summarizer.load_model():
                raise RuntimeError("LLM API客户端初始化失败")
            logger.info("LLM总结器初始化完成，模式: api")

            logger.info("=" * 50)
            logger.info("所有模块初始化完成")
            logger.info("=" * 50)

            return True

        except AudioCaptureError as e:
            logger.error(f"音频采集模块初始化失败: {e}")
            return False
        except ASRError as e:
            logger.error(f"ASR引擎初始化失败: {e}")
            return False
        except Exception as e:
            logger.error(f"模块初始化失败: {e}")
            return False

    async def _process_audio_data(self, audio_data):
        """
        处理音频数据回调

        Args:
            audio_data: 音频数据（numpy数组）
        """
        try:
            self._audio_buffer.append(audio_data)

            buffer_duration = len(self._audio_buffer) * AudioConfig.CHUNK_SIZE / AudioConfig.SAMPLE_RATE

            if buffer_duration >= 3.0:
                await self._process_audio_buffer()

        except Exception as e:
            logger.error(f"音频数据处理错误: {e}")

    async def _process_audio_buffer(self):
        """处理累积的音频缓冲区"""
        if not self._audio_buffer:
            return

        try:
            import numpy as np
            import io
            import soundfile as sf

            combined_audio = np.concatenate(self._audio_buffer)
            self._audio_buffer.clear()

            audio_bytes = io.BytesIO()
            sf.write(audio_bytes, combined_audio, AudioConfig.SAMPLE_RATE, format='WAV')
            audio_bytes.seek(0)
            audio_data = audio_bytes.read()

            logger.debug(f"处理音频缓冲区，大小: {len(audio_data)} 字节")

            transcription = await asyncio.get_event_loop().run_in_executor(
                None,
                self.asr_engine.transcribe,
                audio_data
            )

            if transcription and transcription.strip():
                await self._handle_transcription(transcription.strip())

        except Exception as e:
            logger.error(f"音频缓冲区处理失败: {e}")

    async def _handle_transcription(self, text: str):
        """
        处理转写文字

        Args:
            text: 转写文字
        """
        try:
            logger.info(f"转写结果: {text}")

            self._transcription_buffer.append(text)
            self._last_transcription = text

            if self.file_manager:
                self.file_manager.append_transcription(text)

            if self.web_server:
                await self.web_server.broadcast_transcription(text)

        except Exception as e:
            logger.error(f"处理转写文字失败: {e}")

    def _get_current_text(self) -> str:
        """
        获取当前累积的转写文本

        Returns:
            str: 累积的转写文本
        """
        return "\n".join(self._transcription_buffer)

    def _on_summary_complete(self, summary: str):
        """
        总结完成回调

        Args:
            summary: 生成的总结内容
        """
        try:
            logger.info(f"会议总结生成完成: {summary[:100]}...")

            if self.file_manager:
                self.file_manager.update_summary(summary)

            asyncio.create_task(self._broadcast_summary_async(summary))

        except Exception as e:
            logger.error(f"处理总结失败: {e}")

    async def _broadcast_summary_async(self, summary: str):
        """
        异步广播总结

        Args:
            summary: 总结内容
        """
        try:
            if self.web_server:
                await self.web_server.broadcast_summary(summary)
        except Exception as e:
            logger.error(f"广播总结失败: {e}")

    async def _run_audio_capture(self):
        """运行音频采集任务"""
        try:
            logger.info("启动音频采集任务...")

            loop = asyncio.get_event_loop()

            def audio_callback(audio_data):
                asyncio.run_coroutine_threadsafe(
                    self._process_audio_data(audio_data),
                    loop
                )

            await loop.run_in_executor(
                None,
                self.audio_capture.start_capture,
                audio_callback
            )

            while self._is_running and not self._shutdown_event.is_set():
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"音频采集任务异常: {e}")
            self._shutdown_event.set()

    async def start(self) -> bool:
        """
        启动会议转写系统

        Returns:
            bool: 启动成功返回True，失败返回False
        """
        try:
            logger.info("=" * 60)
            logger.info("会议转写系统启动中...")
            logger.info("=" * 60)

            self._setup_logging()

            try:
                validate_config()
                logger.info("配置验证通过")
            except ValueError as e:
                logger.error(f"配置验证失败: {e}")
                return False

            if not self._initialize_modules():
                logger.error("模块初始化失败，无法启动系统")
                return False

            logger.info("启动Web服务器...")
            await self.web_server.start()
            logger.info(f"Web服务地址: http://{self.host}:{self.port}")

            self._is_running = True
            self._shutdown_event.clear()

            logger.info("启动定时总结任务...")
            self.summarizer.start_periodic_summary(
                text_provider=self._get_current_text,
                callback=self._on_summary_complete,
                interval=self.interval
            )

            logger.info("=" * 60)
            logger.info("会议转写系统已启动")
            logger.info(f"Web界面: http://{self.host}:{self.port}")
            logger.info(f"总结间隔: {self.interval} 秒")
            logger.info("按 Ctrl+C 停止系统")
            logger.info("=" * 60)

            await self._run_audio_capture()

            return True

        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            return False

    async def stop(self):
        """停止会议转写系统"""
        if not self._is_running:
            return

        logger.info("=" * 60)
        logger.info("正在停止会议转写系统...")
        logger.info("=" * 60)

        self._is_running = False
        self._shutdown_event.set()

        try:
            logger.info("[1/5] 停止定时总结任务...")
            if self.summarizer:
                self.summarizer.stop_periodic_summary()
        except Exception as e:
            logger.error(f"停止定时总结任务失败: {e}")

        try:
            logger.info("[2/5] 停止音频采集...")
            if self.audio_capture:
                self.audio_capture.stop_capture()
        except Exception as e:
            logger.error(f"停止音频采集失败: {e}")

        try:
            logger.info("[3/5] 停止Web服务器...")
            if self.web_server:
                await self.web_server.stop()
        except Exception as e:
            logger.error(f"停止Web服务器失败: {e}")

        try:
            logger.info("[4/5] 释放ASR引擎资源...")
            if self.asr_engine:
                self.asr_engine.release()
        except Exception as e:
            logger.error(f"释放ASR引擎资源失败: {e}")

        try:
            logger.info("[5/5] 释放LLM总结器资源...")
            if self.summarizer:
                self.summarizer.release()
        except Exception as e:
            logger.error(f"释放LLM总结器资源失败: {e}")

        try:
            logger.info("释放音频采集资源...")
            if self.audio_capture:
                self.audio_capture.cleanup()
        except Exception as e:
            logger.error(f"释放音频采集资源失败: {e}")

        logger.info("=" * 60)
        logger.info("会议转写系统已停止")
        logger.info("=" * 60)

    async def run(self):
        """运行会议转写系统主循环"""
        try:
            success = await self.start()
            if not success:
                return

            while self._is_running and not self._shutdown_event.is_set():
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("主任务被取消")
        except Exception as e:
            logger.error(f"系统运行异常: {e}")
        finally:
            await self.stop()


def parse_arguments():
    """
    解析命令行参数

    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="会议转写系统 - 实时语音识别与智能总结",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                           # 使用默认配置启动
  python main.py --port 9000              # 指定端口
  python main.py --device cpu             # 使用CPU模式
  python main.py --interval 120           # 每2分钟总结一次
  python main.py --log-level DEBUG        # 开启调试日志
  python main.py --llm-api-model gpt-4    # 指定API模型

环境变量:
  LLM_API_BASE_URL  LLM API地址
  LLM_API_KEY       LLM API密钥
  LLM_API_MODEL     LLM API模型名称
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default=WebConfig.HOST,
        help=f"Web服务主机地址 (默认: {WebConfig.HOST})"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=WebConfig.PORT,
        help=f"Web服务端口 (默认: {WebConfig.PORT})"
    )

    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu", "auto"],
        default=ASRConfig.DEVICE,
        help=f"模型设备 (默认: {ASRConfig.DEVICE})"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=SummaryConfig.INTERVAL,
        help=f"总结间隔秒数 (默认: {SummaryConfig.INTERVAL})"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )



    parser.add_argument(
        "--llm-api-url",
        type=str,
        default=None,
        help=f"LLM API地址 (默认: {LLMConfig.API_BASE_URL})"
    )

    parser.add_argument(
        "--llm-api-key",
        type=str,
        default=None,
        help="LLM API密钥 (也可通过LLM_API_KEY环境变量设置)"
    )

    parser.add_argument(
        "--llm-api-model",
        type=str,
        default=None,
        help=f"LLM API模型名称 (默认: {LLMConfig.API_MODEL})"
    )

    return parser.parse_args()


async def main():
    """主函数入口"""
    args = parse_arguments()

    recorder = MeetingRecorder(
        host=args.host,
        port=args.port,
        device=args.device,
        interval=args.interval,
        log_level=args.log_level,
        llm_api_url=args.llm_api_url,
        llm_api_key=args.llm_api_key,
        llm_api_model=args.llm_api_model
    )

    loop = asyncio.get_event_loop()

    def signal_handler():
        """信号处理函数"""
        logger.info("收到中断信号，正在关闭系统...")
        recorder._shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: signal_handler())

    try:
        await recorder.run()
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        sys.exit(1)
    finally:
        await recorder.stop()


if __name__ == "__main__":
    asyncio.run(main())
