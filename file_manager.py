"""
文件管理器模块
用于管理会议记录文件的创建、写入等操作
"""

import os
import logging
from datetime import datetime
from typing import Optional

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 设置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)

# 添加处理器到logger
if not logger.handlers:
    logger.addHandler(console_handler)


class FileManager:
    """会议文件管理器类"""

    def __init__(self, output_dir: str = "output"):
        """
        初始化文件管理器

        Args:
            output_dir: 输出目录路径，默认为 "output"
        """
        self.output_dir = output_dir
        self.current_file_path: Optional[str] = None
        self.meeting_start_time: Optional[str] = None
        self._ensure_output_directory()
        logger.info(f"文件管理器初始化完成，输出目录: {output_dir}")

    def _ensure_output_directory(self) -> None:
        """
        确保输出目录存在，不存在则自动创建
        """
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logger.info(f"创建输出目录: {self.output_dir}")
            else:
                logger.debug(f"输出目录已存在: {self.output_dir}")
        except OSError as e:
            logger.error(f"创建输出目录失败: {e}")
            raise

    def create_meeting_file(self) -> str:
        """
        创建新的会议Markdown文件

        Returns:
            创建的文件路径

        Raises:
            IOError: 文件创建失败时抛出
        """
        try:
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{timestamp}.md"
            self.current_file_path = os.path.join(self.output_dir, filename)
            self.meeting_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 写入文件头部信息
            header = f"""# 会议记录

**会议开始时间**: {self.meeting_start_time}

---

*等待生成会议总结...*

"""

            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(header)

            logger.info(f"创建会议文件成功: {self.current_file_path}")
            return self.current_file_path

        except IOError as e:
            logger.error(f"创建会议文件失败: {e}")
            raise IOError(f"创建会议文件失败: {e}")

    def update_summary(self, summary: str) -> None:
        """
        更新会议总结到文件（替换原有内容）

        Args:
            summary: 最新的会议总结

        Raises:
            IOError: 写入失败时抛出
            ValueError: 没有当前文件时抛出
        """
        if not self.current_file_path:
            logger.error("没有当前会议文件，请先调用 create_meeting_file()")
            raise ValueError("没有当前会议文件，请先调用 create_meeting_file()")

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 重写整个文件，只保留最新的总结
            content = f"""# 会议记录

**会议开始时间**: {self.meeting_start_time}

---

## 会议总结

**最后更新**: {timestamp}

{summary}

"""

            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"更新会议总结成功")

        except IOError as e:
            logger.error(f"更新会议总结失败: {e}")
            raise IOError(f"更新会议总结失败: {e}")

    def append_transcription(self, text: str) -> None:
        """
        追加转写文字到文件（可选，用于调试）

        Args:
            text: 要追加的转写文字

        Raises:
            IOError: 写入失败时抛出
            ValueError: 没有当前文件时抛出
        """
        # 转写文字不再写入文件，只在内存中累积用于总结
        logger.debug(f"转写文字已记录: {text[:50]}...")

    def get_current_file_path(self) -> Optional[str]:
        """
        获取当前会议文件路径

        Returns:
            当前会议文件的完整路径，如果没有则返回 None
        """
        return self.current_file_path


if __name__ == "__main__":
    # 测试代码
    fm = FileManager()
    file_path = fm.create_meeting_file()
    print(f"创建文件: {file_path}")

    fm.update_summary("第一次总结：本次会议讨论了项目进度。")
    print(f"第一次总结已写入")

    fm.update_summary("第二次总结：本次会议讨论了项目进度和下一步计划，决定下周完成原型开发。")
    print(f"第二次总结已写入（替换第一次）")

    print(f"文件内容已写入: {fm.get_current_file_path()}")
