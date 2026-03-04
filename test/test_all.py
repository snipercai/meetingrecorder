# -*- coding: utf-8 -*-
"""
会议转写系统测试脚本
支持独立测试每个模块，也支持运行端到端冒烟测试
每次运行测试会生成Markdown格式的日志报告文件

使用方法:
    python test/test_all.py                    # 运行所有测试
    python test/test_all.py --module config    # 只测试config模块
    python test/test_all.py --module logger    # 只测试logger模块
    python test/test_all.py --module audio     # 只测试audio_capture模块
    python test/test_all.py --module asr       # 只测试asr_engine模块
    python test/test_all.py --module summarizer # 只测试summarizer模块
    python test/test_all.py --module file      # 只测试file_manager模块
    python test/test_all.py --module web       # 只测试web_server模块
    python test/test_all.py --smoke            # 运行端到端冒烟测试
    python test/test_all.py --list             # 列出所有可用测试
"""

import argparse
import asyncio
import importlib
import io
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_DIR = Path(__file__).parent

COLORS = {
    "reset": "\033[0m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
}

ANSI_ESCAPE = "\033"


def strip_ansi(text: str) -> str:
    """移除ANSI颜色代码"""
    import re
    ansi_pattern = re.compile(r'\033\[[0-9;]*m')
    return ansi_pattern.sub('', text)


class TestReport:
    """测试报告生成器"""

    def __init__(self):
        self.start_time: datetime = None
        self.end_time: datetime = None
        self.test_type: str = ""
        self.results: Dict[str, Tuple[bool, str, float]] = {}
        self.logs: List[str] = []
        self._capture_buffer: io.StringIO = None
        self._original_stdout = None

    def start(self, test_type: str):
        """开始测试记录"""
        self.start_time = datetime.now()
        self.test_type = test_type
        self.results = {}
        self.logs = []
        self._start_capture()

    def _start_capture(self):
        """开始捕获输出"""
        self._capture_buffer = io.StringIO()
        self._original_stdout = sys.stdout

        class TeeOutput:
            def __init__(self, original, buffer):
                self.original = original
                self.buffer = buffer

            def write(self, text):
                self.original.write(text)
                self.buffer.write(text)
                return len(text)

            def flush(self):
                self.original.flush()
                self.buffer.flush()

        sys.stdout = TeeOutput(self._original_stdout, self._capture_buffer)

    def _stop_capture(self):
        """停止捕获输出"""
        if self._original_stdout:
            sys.stdout = self._original_stdout
        if self._capture_buffer:
            self.logs.append(self._capture_buffer.getvalue())
            self._capture_buffer = None

    def add_result(self, name: str, passed: bool, message: str, elapsed: float):
        """添加测试结果"""
        self.results[name] = (passed, message, elapsed)

    def end(self):
        """结束测试记录"""
        self._stop_capture()
        self.end_time = datetime.now()

    def generate_markdown(self) -> str:
        """生成Markdown格式报告"""
        lines = []

        lines.append("# 会议转写系统测试报告")
        lines.append("")

        lines.append("## 测试概览")
        lines.append("")
        lines.append(f"- **测试类型**: {self.test_type}")
        lines.append(f"- **开始时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **结束时间**: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        elapsed = (self.end_time - self.start_time).total_seconds()
        lines.append(f"- **总耗时**: {elapsed:.2f} 秒")
        lines.append("")

        passed = sum(1 for r in self.results.values() if r[0])
        total = len(self.results)
        status_emoji = "✅" if passed == total else "⚠️"
        lines.append("## 测试结果摘要")
        lines.append("")
        lines.append(f"| 状态 | 模块 | 结果 | 耗时 |")
        lines.append(f"|:----:|:-----|:-----|:----:|")

        for name, (result, message, elapsed_time) in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            lines.append(f"| {status} | {name} | {message} | {elapsed_time:.2f}s |")

        lines.append("")
        lines.append(f"**总计**: {passed}/{total} 测试通过 {status_emoji}")
        lines.append("")

        lines.append("## 详细日志")
        lines.append("")
        lines.append("```")
        for log in self.logs:
            clean_log = strip_ansi(log)
            lines.append(clean_log)
        lines.append("```")
        lines.append("")

        lines.append("---")
        lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def save_report(self) -> str:
        """保存报告到文件"""
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        test_type_safe = self.test_type.replace(" ", "_").replace("/", "_")
        filename = f"test_report_{test_type_safe}_{timestamp}.md"
        report_path = TEST_DIR / filename

        markdown_content = self.generate_markdown()

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return str(report_path)


def print_color(text: str, color: str = "reset"):
    """打印彩色文本"""
    print(f"{COLORS.get(color, '')}{text}{COLORS['reset']}")


def print_header(title: str):
    """打印标题头"""
    width = 60
    print()
    print_color("=" * width, "cyan")
    print_color(f"  {title}", "cyan")
    print_color("=" * width, "cyan")
    print()


def print_result(passed: bool, message: str = ""):
    """打印测试结果"""
    status = f"[{'PASS' if passed else 'FAIL'}]"
    color = "green" if passed else "red"
    print_color(f"  {status} {message}", color)


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.results: Dict[str, Tuple[bool, str]] = {}
        self.report: TestReport = None
        self.test_modules: Dict[str, Callable] = {
            "config": self.test_config,
            "logger": self.test_logger,
            "audio": self.test_audio_capture,
            "asr": self.test_asr_engine,
            "summarizer": self.test_summarizer,
            "file": self.test_file_manager,
            "web": self.test_web_server,
        }

    def run_test(self, test_name: str, test_func: Callable, mode: str = "online") -> Tuple[bool, str]:
        """运行单个测试"""
        print_color(f"\n>>> 运行测试: {test_name} (模式: {mode})" , "yellow")
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(test_func):
                result, message = asyncio.run(test_func(mode))
            else:
                result, message = test_func(mode)
            elapsed = time.time() - start_time
            print_result(result, f"{message} (耗时: {elapsed:.2f}秒)")

            if self.report:
                self.report.add_result(test_name, result, message, elapsed)

            return result, message
        except Exception as e:
            elapsed = time.time() - start_time
            print_result(False, f"测试异常: {str(e)} (耗时: {elapsed:.2f}秒)")

            if self.report:
                self.report.add_result(test_name, False, str(e), elapsed)

            return False, str(e)

    def test_config(self, mode: str = "online") -> Tuple[bool, str]:
        """测试配置模块"""
        print_header("测试配置模块 (config.py)")

        try:
            from config import (
                ASRConfig,
                LLMConfig,
                AudioConfig,
                WebConfig,
                SummaryConfig,
                LogConfig,
                OUTPUT_DIR,
                validate_config,
                get_config,
            )

            all_passed = True
            messages = []

            print("1. 测试配置类加载...")
            try:
                assert hasattr(ASRConfig, "MODEL_PATH"), "ASRConfig缺少MODEL_PATH"
                assert hasattr(LLMConfig, "API_BASE_URL"), "LLMConfig缺少API_BASE_URL"
                assert hasattr(LLMConfig, "API_KEY"), "LLMConfig缺少API_KEY"
                assert hasattr(LLMConfig, "API_MODEL"), "LLMConfig缺少API_MODEL"
                assert hasattr(AudioConfig, "SAMPLE_RATE"), "AudioConfig缺少SAMPLE_RATE"
                assert hasattr(WebConfig, "PORT"), "WebConfig缺少PORT"
                assert hasattr(SummaryConfig, "INTERVAL"), "SummaryConfig缺少INTERVAL"
                assert hasattr(LogConfig, "LEVEL"), "LogConfig缺少LEVEL"
                print_result(True, "配置类加载成功")
            except AssertionError as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("2. 测试配置值有效性...")
            try:
                assert AudioConfig.SAMPLE_RATE > 0, "采样率必须大于0"
                assert AudioConfig.CHANNELS in [1, 2], "通道数必须为1或2"
                assert 0 <= WebConfig.PORT <= 65535, "端口号必须在有效范围内"
                assert SummaryConfig.INTERVAL > 0, "总结间隔必须大于0"
                print_result(True, "配置值验证通过")
            except AssertionError as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("3. 测试输出目录创建...")
            try:
                assert OUTPUT_DIR.exists(), "输出目录不存在"
                print_result(True, f"输出目录: {OUTPUT_DIR}")
            except AssertionError as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("4. 测试get_config函数...")
            try:
                config = get_config()
                assert "asr" in config, "配置字典缺少asr键"
                assert "llm" in config, "配置字典缺少llm键"
                assert "audio" in config, "配置字典缺少audio键"
                print_result(True, "get_config函数正常")
            except AssertionError as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("5. 测试validate_config函数...")
            try:
                validate_config()
                print_result(True, "配置验证通过")
            except ValueError as e:
                print_result(False, f"配置验证失败: {e}")
                messages.append(f"配置验证失败: {e}")
                all_passed = False

            message = "配置模块测试完成" if all_passed else "; ".join(messages)
            return all_passed, message

        except ImportError as e:
            print_result(False, f"导入配置模块失败: {e}")
            return False, f"导入失败: {e}"

    def test_logger(self, mode: str = "online") -> Tuple[bool, str]:
        """测试日志模块"""
        print_header("测试日志模块 (logger.py)")

        try:
            from logger import get_logger, set_log_level, LoggerManager

            all_passed = True
            messages = []

            print("1. 测试LoggerManager单例模式...")
            try:
                manager1 = LoggerManager()
                manager2 = LoggerManager()
                assert manager1 is manager2, "LoggerManager单例模式失败"
                print_result(True, "LoggerManager单例模式正常")
            except AssertionError as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("2. 测试get_logger函数...")
            try:
                logger = get_logger("test_module")
                assert logger is not None, "获取logger失败"
                print_result(True, "get_logger函数正常")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("3. 测试日志级别设置...")
            try:
                set_log_level("DEBUG")
                set_log_level("INFO")
                print_result(True, "日志级别设置正常")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("4. 测试日志输出...")
            try:
                logger = get_logger("test_output")
                logger.debug("这是一条DEBUG测试消息")
                logger.info("这是一条INFO测试消息")
                logger.warning("这是一条WARNING测试消息")
                logger.error("这是一条ERROR测试消息")
                print_result(True, "日志输出正常")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            message = "日志模块测试完成" if all_passed else "; ".join(messages)
            return all_passed, message

        except ImportError as e:
            print_result(False, f"导入日志模块失败: {e}")
            return False, f"导入失败: {e}"

    def test_audio_capture(self, mode: str = "online") -> Tuple[bool, str]:
        """测试音频采集模块"""
        print_header("测试音频采集模块 (audio_capture.py)")

        try:
            from audio_capture import (
                AudioCapture,
                AudioCaptureError,
                MicrophoneNotAvailableError,
                AudioStreamError,
            )

            all_passed = True
            messages = []

            print("1. 测试AudioCapture类实例化...")
            try:
                capture = AudioCapture(
                    sample_rate=16000,
                    channels=1,
                    chunk_size=1024
                )
                assert capture.sample_rate == 16000, "采样率设置错误"
                assert capture.channels == 1, "通道数设置错误"
                assert capture.chunk_size == 1024, "块大小设置错误"
                print_result(True, "AudioCapture实例化成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))
                return all_passed, "; ".join(messages)

            print("2. 测试麦克风设备初始化...")
            try:
                capture.initialize()
                print_result(True, "麦克风设备初始化成功")
            except MicrophoneNotAvailableError as e:
                print_result(False, f"麦克风不可用: {e}")
                messages.append(f"麦克风不可用: {e}")
                all_passed = False
            except AudioStreamError as e:
                print_result(False, f"音频流错误: {e}")
                messages.append(f"音频流错误: {e}")
                all_passed = False
            except Exception as e:
                print_result(False, f"初始化异常: {e}")
                messages.append(f"初始化异常: {e}")
                all_passed = False

            print("3. 测试is_capturing属性...")
            try:
                assert capture.is_capturing == False, "初始状态应为非采集状态"
                print_result(True, "is_capturing属性正常")
            except AssertionError as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("4. 测试资源清理...")
            try:
                capture.cleanup()
                print_result(True, "资源清理成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("5. 测试上下文管理器...")
            try:
                with AudioCapture() as cap:
                    assert cap._pyaudio is not None, "上下文管理器初始化失败"
                print_result(True, "上下文管理器正常")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            message = "音频采集模块测试完成" if all_passed else "; ".join(messages)
            return all_passed, message

        except ImportError as e:
            print_result(False, f"导入音频采集模块失败: {e}")
            return False, f"导入失败: {e}"

    def test_asr_engine(self, mode: str = "online") -> Tuple[bool, str]:
        """测试ASR引擎模块"""
        print_header("测试ASR引擎模块 (asr_engine.py)")

        try:
            from asr_engine import (
                ASREngine,
                ASRError,
                ModelLoadError,
                DeviceNotAvailableError,
                InferenceError,
            )

            all_passed = True
            messages = []

            print("1. 测试ASREngine类实例化...")
            try:
                # 根据mode参数设置offline标志
                offline = (mode == "offline")
                engine = ASREngine(device="cpu", offline=offline)
                assert engine.device == "cpu", "设备设置错误"
                assert engine.offline == offline, "离线模式设置错误"
                assert engine.model is None, "初始状态模型应为None"
                assert not engine.is_loaded, "初始状态is_loaded应为False"
                print_result(True, "ASREngine实例化成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))
                return all_passed, "; ".join(messages)

            print("2. 测试模型加载（这可能需要几分钟）...")
            try:
                engine.load_model()
                assert engine.is_loaded, "模型加载后is_loaded应为True"
                assert engine.model is not None, "模型加载后model不应为None"
                print_result(True, f"{mode}模式模型加载成功")
            except ModelLoadError as e:
                print_result(False, f"模型加载失败: {e}")
                messages.append(f"模型加载失败: {e}")
                all_passed = False
                return all_passed, "; ".join(messages)
            except Exception as e:
                print_result(False, f"模型加载异常: {e}")
                messages.append(f"模型加载异常: {e}")
                all_passed = False
                return all_passed, "; ".join(messages)

            print("3. 测试模型资源释放...")
            try:
                engine.release()
                assert not engine.is_loaded, "释放后is_loaded应为False"
                assert engine.model is None, "释放后model应为None"
                print_result(True, "模型资源释放成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            message = "ASR引擎模块测试完成" if all_passed else "; ".join(messages)
            return all_passed, message

        except ImportError as e:
            print_result(False, f"导入ASR引擎模块失败: {e}")
            return False, f"导入失败: {e}"

    def test_summarizer(self, mode: str = "online") -> Tuple[bool, str]:
        """测试总结模块"""
        print_header("测试总结模块 (summarizer.py)")

        try:
            from summarizer import Summarizer
            from config import LLMConfig

            all_passed = True
            messages = []

            print("1. 测试Summarizer类实例化...")
            try:
                summarizer = Summarizer()
                print_result(True, "Summarizer实例化成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))
                return all_passed, "; ".join(messages)

            print("2. 测试API配置验证...")
            try:
                if summarizer.load_model():
                    print_result(True, "API配置验证通过")
                else:
                    print_result(False, "API配置验证失败，请检查.env文件中的LLM配置")
                    messages.append("API配置验证失败")
                    all_passed = False
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("3. 测试消息构建...")
            try:
                messages_list = summarizer._build_messages("测试文本")
                assert len(messages_list) == 2, "消息列表长度错误"
                assert messages_list[0]["role"] == "system", "第一条消息角色错误"
                assert messages_list[1]["role"] == "user", "第二条消息角色错误"
                print_result(True, "消息构建正常")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("4. 测试总结功能（需要有效API配置）...")
            try:
                if summarizer.is_loaded():
                    summary = summarizer.summarize("这是一段测试文本，用于验证总结功能是否正常工作。")
                    if summary:
                        print_result(True, f"总结功能正常，结果长度: {len(summary)}字符")
                    else:
                        print_result(False, "总结返回空结果")
                        messages.append("总结返回空结果")
                        all_passed = False
                else:
                    print_result(True, "跳过总结功能测试（模型未加载）")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("5. 测试资源释放...")
            try:
                summarizer.release()
                assert not summarizer.is_loaded(), "释放后is_loaded应为False"
                print_result(True, "资源释放成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            message = "总结模块测试完成" if all_passed else "; ".join(messages)
            return all_passed, message

        except ImportError as e:
            print_result(False, f"导入总结模块失败: {e}")
            return False, f"导入失败: {e}"

    def test_file_manager(self, mode: str = "online") -> Tuple[bool, str]:
        """测试文件管理模块"""
        print_header("测试文件管理模块 (file_manager.py)")

        try:
            from file_manager import FileManager

            all_passed = True
            messages = []
            test_file_path = None

            print("1. 测试FileManager类实例化...")
            try:
                fm = FileManager(output_dir="test_output")
                assert fm.output_dir == "test_output", "输出目录设置错误"
                print_result(True, "FileManager实例化成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))
                return all_passed, "; ".join(messages)

            print("2. 测试输出目录创建...")
            try:
                assert os.path.exists("test_output"), "输出目录未创建"
                print_result(True, "输出目录创建成功")
            except AssertionError as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("3. 测试会议文件创建...")
            try:
                test_file_path = fm.create_meeting_file()
                assert os.path.exists(test_file_path), "会议文件未创建"
                assert fm.current_file_path == test_file_path, "当前文件路径设置错误"
                print_result(True, f"会议文件创建成功: {test_file_path}")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("4. 测试总结更新...")
            try:
                test_summary = "# 测试总结\n\n这是一段测试总结内容。"
                fm.update_summary(test_summary)
                with open(test_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                assert test_summary in content, "总结内容未写入文件"
                print_result(True, "总结更新成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("5. 测试获取当前文件路径...")
            try:
                current_path = fm.get_current_file_path()
                assert current_path == test_file_path, "获取当前文件路径错误"
                print_result(True, f"当前文件路径: {current_path}")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("6. 清理测试文件...")
            try:
                import shutil
                if os.path.exists("test_output"):
                    shutil.rmtree("test_output")
                print_result(True, "测试文件清理完成")
            except Exception as e:
                print_result(False, str(e))

            message = "文件管理模块测试完成" if all_passed else "; ".join(messages)
            return all_passed, message

        except ImportError as e:
            print_result(False, f"导入文件管理模块失败: {e}")
            return False, f"导入失败: {e}"

    async def test_web_server(self, mode: str = "online") -> Tuple[bool, str]:
        """测试Web服务器模块"""
        print_header("测试Web服务器模块 (web_server.py)")

        try:
            from web_server import WebServer

            all_passed = True
            messages = []

            print("1. 测试WebServer类实例化...")
            try:
                server = WebServer(host="127.0.0.1", port=18080)
                assert server.host == "127.0.0.1", "主机设置错误"
                assert server.port == 18080, "端口设置错误"
                assert server.app is not None, "aiohttp应用未创建"
                print_result(True, "WebServer实例化成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))
                return all_passed, "; ".join(messages)

            print("2. 测试服务器启动...")
            try:
                await server.start()
                print_result(True, f"服务器启动成功: http://{server.host}:{server.port}")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))
                return all_passed, "; ".join(messages)

            print("3. 测试WebSocket客户端集合...")
            try:
                assert isinstance(server.websocket_clients, set), "WebSocket客户端集合类型错误"
                print_result(True, "WebSocket客户端集合正常")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("4. 测试广播功能...")
            try:
                await server.broadcast_transcription("测试转写文字")
                await server.broadcast_summary("测试总结内容")
                print_result(True, "广播功能正常")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            print("5. 测试服务器停止...")
            try:
                await server.stop()
                print_result(True, "服务器停止成功")
            except Exception as e:
                print_result(False, str(e))
                all_passed = False
                messages.append(str(e))

            message = "Web服务器模块测试完成" if all_passed else "; ".join(messages)
            return all_passed, message

        except ImportError as e:
            print_result(False, f"导入Web服务器模块失败: {e}")
            return False, f"导入失败: {e}"

    def run_smoke_test(self, mode: str = "online") -> Tuple[bool, str]:
        """运行端到端冒烟测试"""
        print_header("端到端冒烟测试")

        all_passed = True
        messages = []

        print_color(f"冒烟测试将验证系统各模块能否正常协同工作（模式: {mode}", "yellow")
        print_color("注意：此测试需要完整的运行环境（ASR模型、LLM API等）", "yellow")

        print("\n1. 测试配置加载...")
        try:
            from config import validate_config, OUTPUT_DIR
            validate_config()
            print_result(True, "配置加载成功")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))
            return all_passed, "; ".join(messages)

        print("\n2. 测试日志系统...")
        try:
            from logger import get_logger
            logger = get_logger("smoke_test")
            logger.info("冒烟测试日志")
            print_result(True, "日志系统正常")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))

        print("\n3. 测试文件管理器...")
        try:
            from file_manager import FileManager
            fm = FileManager(output_dir=str(OUTPUT_DIR))
            file_path = fm.create_meeting_file()
            fm.update_summary("冒烟测试总结")
            print_result(True, f"文件管理器正常: {file_path}")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))

        print("\n4. 测试音频采集初始化...")
        try:
            from audio_capture import AudioCapture
            capture = AudioCapture()
            capture.initialize()
            capture.cleanup()
            print_result(True, "音频采集初始化成功")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))

        print("\n5. 测试ASR引擎初始化...")
        try:
            from asr_engine import ASREngine
            # 根据mode参数设置offline标志
            offline = (mode == "offline")
            engine = ASREngine(device="cpu", offline=offline)
            engine.load_model()
            engine.release()
            print_result(True, f"ASR引擎初始化成功（{mode}模式）")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))

        print("\n6. 测试LLM总结器初始化...")
        try:
            from summarizer import Summarizer
            summarizer = Summarizer()
            if summarizer.load_model():
                print_result(True, "LLM总结器初始化成功")
                summarizer.release()
            else:
                print_result(False, "LLM总结器初始化失败")
                all_passed = False
                messages.append("LLM总结器初始化失败")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))

        print("\n7. 测试Web服务器...")
        try:
            async def test_web():
                from web_server import WebServer
                server = WebServer(port=18081)
                await server.start()
                await server.stop()
                return True

            asyncio.run(test_web())
            print_result(True, "Web服务器正常")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))

        print("\n8. 测试主程序入口导入...")
        try:
            from main import MeetingRecorder, parse_arguments
            print_result(True, "主程序入口导入成功")
        except Exception as e:
            print_result(False, str(e))
            all_passed = False
            messages.append(str(e))

        message = "冒烟测试完成" if all_passed else "; ".join(messages)
        return all_passed, message

    def run_all_tests(self, mode: str = "online") -> Dict[str, Tuple[bool, str]]:
        """运行所有模块测试"""
        print_header("运行所有模块测试")

        results = {}
        for name, test_func in self.test_modules.items():
            results[name] = self.run_test(name, test_func, mode)

        return results

    def list_tests(self):
        """列出所有可用测试"""
        print_header("可用测试列表")
        print("模块测试:")
        for name in self.test_modules.keys():
            print_color(f"  - {name}", "blue")
        print("\n其他测试:")
        print_color("  - smoke (端到端冒烟测试)", "blue")
        print("\n使用方法:")
        print("  python test/test_all.py --module <模块名>  # 运行指定模块测试")
        print("  python test/test_all.py --smoke           # 运行冒烟测试")
        print("  python test/test_all.py                   # 运行所有测试")


def print_summary(results: Dict[str, Tuple[bool, str]]):
    """打印测试结果摘要"""
    print_header("测试结果摘要")

    passed = sum(1 for r in results.values() if r[0])
    total = len(results)

    for name, (result, message) in results.items():
        status = "PASS" if result else "FAIL"
        color = "green" if result else "red"
        print_color(f"  [{status}] {name}: {message}", color)

    print()
    print_color(f"总计: {passed}/{total} 测试通过", "green" if passed == total else "yellow")

    if passed == total:
        print_color("\n所有测试通过！", "green")
    else:
        print_color(f"\n{total - passed} 个测试失败，请检查上述错误信息", "red")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="会议转写系统测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test/test_all.py                    # 运行所有测试
  python test/test_all.py --module config    # 只测试config模块
  python test/test_all.py --module logger    # 只测试logger模块
  python test/test_all.py --module audio     # 只测试audio_capture模块
  python test/test_all.py --module asr       # 只测试asr_engine模块
  python test/test_all.py --module summarizer # 只测试summarizer模块
  python test/test_all.py --module file      # 只测试file_manager模块
  python test/test_all.py --module web       # 只测试web_server模块
  python test/test_all.py --smoke            # 运行端到端冒烟测试
  python test/test_all.py --list             # 列出所有可用测试
        """
    )

    parser.add_argument(
        "--module",
        type=str,
        choices=["config", "logger", "audio", "asr", "summarizer", "file", "web"],
        help="指定要测试的模块"
    )

    parser.add_argument(
        "--smoke",
        action="store_true",
        help="运行端到端冒烟测试"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用测试"
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="不生成测试报告文件"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["online", "offline"],
        default="online",
        help="指定测试模式（online/offline）"
    )

    args = parser.parse_args()

    runner = TestRunner()

    if args.list:
        runner.list_tests()
        return

    if not args.no_report:
        runner.report = TestReport()

    if args.smoke:
        if runner.report:
            runner.report.start(f"smoke_test_{args.mode}")
        result, message = runner.run_smoke_test(args.mode)
        print_summary({"smoke": (result, message)})
        if runner.report:
            runner.report.end()
            report_path = runner.report.save_report()
            print_color(f"\n测试报告已保存: {report_path}", "green")
        return

    if args.module:
        if runner.report:
            runner.report.start(f"module_{args.module}_{args.mode}")
        result, message = runner.run_test(args.module, runner.test_modules[args.module], args.mode)
        print_summary({args.module: (result, message)})
        if runner.report:
            runner.report.end()
            report_path = runner.report.save_report()
            print_color(f"\n测试报告已保存: {report_path}", "green")
        return

    if runner.report:
        runner.report.start(f"all_modules_{args.mode}")
    results = runner.run_all_tests(args.mode)
    print_summary(results)
    if runner.report:
        runner.report.end()
        report_path = runner.report.save_report()
        print_color(f"\n测试报告已保存: {report_path}", "green")


if __name__ == "__main__":
    main()
