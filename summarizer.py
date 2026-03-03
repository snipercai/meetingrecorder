"""
会议总结模块
支持本地LLM模型和OpenAI兼容HTTP API两种模式对会议转写内容进行定时总结
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Callable, Optional

import aiohttp

from logger import get_logger
from config import LLMConfig

logger = get_logger(__name__)


class Summarizer:
    """
    会议总结器类
    支持本地模型和OpenAI兼容HTTP API两种模式对会议转写内容进行增量总结
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cuda",
        mode: Optional[str] = None,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_model: Optional[str] = None
    ):
        """
        初始化LLM总结器

        Args:
            model_path: 本地模型路径，如果为None则使用配置中的默认模型
            device: 运行设备，可选"cuda"或"cpu"（仅本地模式有效）
            mode: 运行模式，"local"使用本地模型，"api"使用HTTP API
            api_base_url: API基础URL（仅API模式有效）
            api_key: API密钥（仅API模式有效）
            api_model: API模型名称（仅API模式有效）
        """
        self.mode = mode or LLMConfig.MODE
        self.model_path = model_path or LLMConfig.MODEL_PATH
        self.device = device

        self.api_base_url = (api_base_url or LLMConfig.API_BASE_URL).rstrip("/")
        self.api_key = api_key or LLMConfig.API_KEY
        self.api_model = api_model or LLMConfig.API_MODEL

        self.model = None
        self.tokenizer = None
        self._is_loaded = False
        self._periodic_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        logger.info(f"初始化Summarizer，模式: {self.mode}")
        if self.mode == "api":
            logger.info(f"API地址: {self.api_base_url}，模型: {self.api_model}")
        else:
            logger.info(f"设备: {device}，模型路径: {self.model_path}")

    def load_model(self) -> bool:
        """
        加载模型或验证API配置

        Returns:
            bool: 加载成功返回True，失败返回False
        """
        if self.mode == "api":
            return self._validate_api_config()
        else:
            return self._load_local_model()

    def _validate_api_config(self) -> bool:
        """
        验证API配置是否有效

        Returns:
            bool: 配置有效返回True，失败返回False
        """
        try:
            logger.info("验证API配置...")

            if not self.api_key:
                logger.error("API密钥未配置，请设置LLM_API_KEY环境变量或在配置中指定")
                return False

            if not self.api_base_url:
                logger.error("API地址未配置，请设置LLM_API_BASE_URL环境变量或在配置中指定")
                return False

            if not self.api_model:
                logger.error("API模型名称未配置，请设置LLM_API_MODEL环境变量或在配置中指定")
                return False

            self._is_loaded = True
            logger.info(f"API配置验证成功，地址: {self.api_base_url}，模型: {self.api_model}")
            return True

        except Exception as e:
            logger.error(f"API配置验证失败: {e}")
            return False

    def _load_local_model(self) -> bool:
        """
        加载本地LLM模型

        Returns:
            bool: 加载成功返回True，失败返回False
        """
        try:
            logger.info(f"开始加载本地LLM模型: {self.model_path}")

            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )

            if self.device == "cpu":
                self.model = self.model.to(self.device)

            self.model.eval()
            self._is_loaded = True

            logger.info("本地LLM模型加载成功")
            return True

        except FileNotFoundError as e:
            logger.error(f"模型文件不存在: {e}")
            return False
        except ImportError as e:
            logger.error(f"依赖库未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False

    def _build_messages(self, text: str, previous_summary: Optional[str] = None) -> list:
        """
        构建消息列表

        Args:
            text: 当前需要总结的文本
            previous_summary: 之前的历史总结

        Returns:
            list: 消息列表
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if previous_summary:
            user_content = f"""你是一个专业的会议记录助手。请随着会议推进，持续滚动生成一份“到当前时刻为止”的完整会议总结。

当前时间: {current_time}

【历史总结】
{previous_summary}

【新的会议内容】
{text}

请生成更新的会议总结，要求：
1. 整合历史总结和新内容
2. 提取会议主要内容
3. 保持结构清晰，使用Markdown格式
4. 标注重要时间节点
5. 如果有待办事项和工作要求，请明确列出
6. 不要添加任何额外说明，只输出总结本身, 将句子理顺，不要包含任何解释或说明。

【会议总结】"""
        else:
            user_content = f"""你是一个专业的会议记录助手。请随着会议推进，持续滚动生成一份“到当前时刻为止”的完整会议总结。

当前时间: {current_time}

【会议内容】
{text}

请生成会议总结，要求：
1. 提取会议主要内容
2. 保持结构清晰，使用Markdown格式
3. 标注重要时间节点
4. 如果有待办事项和工作要求，请明确列出
5. 不要添加任何额外说明，只输出总结本身, 将句子理顺，不要包含任何解释或说明。

【会议总结】"""

        return [
            {"role": "system", "content": "你是一个专业的会议记录助手，擅长总结会议内容并提取关键信息。"},
            {"role": "user", "content": user_content}
        ]

    def _summarize_with_api(self, text: str, previous_summary: Optional[str] = None) -> Optional[str]:
        """
        使用HTTP API生成会议总结

        Args:
            text: 需要总结的文本
            previous_summary: 之前的历史总结

        Returns:
            Optional[str]: 生成的总结内容，失败返回None
        """
        try:
            messages = self._build_messages(text, previous_summary)

            # 直接使用api_base_url作为完整URL（配置中已包含完整路径）
            url = self.api_base_url

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.api_model,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": LLMConfig.TEMPERATURE,
                "top_p": LLMConfig.TOP_P
            }

            logger.debug(f"发送API请求到: {url}")

            import requests

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                logger.error(f"API请求失败，状态码: {response.status_code}，响应: {response.text}")
                return None

            result = response.json()

            if "choices" not in result or len(result["choices"]) == 0:
                logger.error(f"API响应格式异常: {result}")
                return None

            content = result["choices"][0].get("message", {}).get("content")
            return content.strip() if content else None

        except requests.exceptions.Timeout:
            logger.error("API请求超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求异常: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"API响应JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return None

    def _summarize_with_local(self, text: str, previous_summary: Optional[str] = None) -> Optional[str]:
        """
        使用本地模型生成会议总结

        Args:
            text: 需要总结的文本
            previous_summary: 之前的历史总结

        Returns:
            Optional[str]: 生成的总结内容，失败返回None
        """
        try:
            import torch

            messages = self._build_messages(text, previous_summary)

            text_input = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            inputs = self.tokenizer(
                text_input,
                return_tensors="pt",
                padding=True
            )
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    do_sample=True,
                    temperature=LLMConfig.TEMPERATURE,
                    top_p=LLMConfig.TOP_P,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
            summary = self.tokenizer.decode(
                generated_ids,
                skip_special_tokens=True
            )

            return summary.strip()

        except Exception as e:
            logger.error(f"本地模型推理失败: {e}")
            return None

    def summarize(self, text: str, previous_summary: Optional[str] = None) -> Optional[str]:
        """
        生成会议总结

        Args:
            text: 需要总结的文本
            previous_summary: 之前的历史总结，用于增量总结

        Returns:
            Optional[str]: 生成的总结内容，失败返回None
        """
        if not self._is_loaded:
            logger.warning("模型/客户端未加载，无法生成总结")
            return None

        if not text or not text.strip():
            logger.debug("输入文本为空，跳过总结")
            return previous_summary

        try:
            logger.info("开始生成会议总结...")
            start_time = time.time()

            if self.mode == "api":
                summary = self._summarize_with_api(text, previous_summary)
            else:
                summary = self._summarize_with_local(text, previous_summary)

            elapsed_time = time.time() - start_time
            if summary:
                logger.info(f"会议总结生成完成，耗时: {elapsed_time:.2f}秒")
            else:
                logger.warning(f"会议总结生成失败，耗时: {elapsed_time:.2f}秒")

            return summary

        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return None

    async def _periodic_summary_loop(
        self,
        text_provider: Callable[[], str],
        callback: Callable[[str], None],
        interval: int
    ):
        """
        定时总结循环

        Args:
            text_provider: 获取当前文本的回调函数
            callback: 总结完成后的回调函数
            interval: 总结间隔（秒）
        """
        logger.info(f"启动定时总结任务，间隔: {interval}秒")

        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(interval)

                if self._stop_event.is_set():
                    break

                current_text = text_provider()

                if current_text and current_text.strip():
                    logger.debug("定时总结触发，开始生成总结...")

                    summary = self.summarize(current_text)

                    if summary:
                        callback(summary)
                    else:
                        logger.warning("总结生成失败，将在下次重试")
                else:
                    logger.debug("当前无文本内容，跳过本次总结")

            except asyncio.CancelledError:
                logger.info("定时总结任务被取消")
                break
            except Exception as e:
                logger.error(f"定时总结任务出错: {e}，继续运行")

        logger.info("定时总结任务已停止")

    def start_periodic_summary(
        self,
        text_provider: Callable[[], str],
        callback: Callable[[str], None],
        interval: int = 60
    ) -> bool:
        """
        启动定时总结任务

        Args:
            text_provider: 获取当前文本的回调函数
            callback: 总结完成后的回调函数
            interval: 总结间隔（秒），默认60秒

        Returns:
            bool: 启动成功返回True，失败返回False
        """
        if self._periodic_task is not None and not self._periodic_task.done():
            logger.warning("定时总结任务已在运行中")
            return False

        if not self._is_loaded:
            logger.error("模型/客户端未加载，无法启动定时总结任务")
            return False

        self._stop_event.clear()

        self._periodic_task = asyncio.create_task(
            self._periodic_summary_loop(text_provider, callback, interval)
        )

        logger.info(f"定时总结任务已启动，间隔: {interval}秒")
        return True

    def stop_periodic_summary(self):
        """
        停止定时总结任务
        """
        if self._periodic_task is None or self._periodic_task.done():
            logger.debug("定时总结任务未在运行")
            return

        logger.info("正在停止定时总结任务...")
        self._stop_event.set()

        try:
            self._periodic_task.cancel()
        except Exception as e:
            logger.warning(f"取消定时任务时出错: {e}")

        self._periodic_task = None
        logger.info("定时总结任务已停止")

    def release(self):
        """
        释放资源
        """
        logger.info("正在释放Summarizer资源...")

        self.stop_periodic_summary()

        if self.mode == "local":
            if self.model is not None:
                del self.model
                self.model = None

            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None

            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

        self._is_loaded = False
        logger.info("Summarizer资源已释放")

    def is_loaded(self) -> bool:
        """
        检查模型/客户端是否已加载

        Returns:
            bool: 已加载返回True
        """
        return self._is_loaded

    def is_running(self) -> bool:
        """
        检查定时任务是否在运行

        Returns:
            bool: 正在运行返回True
        """
        return self._periodic_task is not None and not self._periodic_task.done()
