# -*- coding: utf-8 -*-
"""
配置文件模块
包含ASR模型、LLM模型、音频参数、Web服务等配置
"""

import os
from pathlib import Path

# 尝试加载.env文件
if os.path.exists('.env'):
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                os.environ.setdefault(key, value)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()

# 输出目录配置
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ASRConfig:
    """ASR（自动语音识别）模型配置"""
    
    # 模型路径（可以是Hugging Face模型ID或本地路径）
    MODEL_PATH = os.environ.get("ASR_MODEL_PATH", "Qwen/Qwen3-ASR-0.6B")
    
    # 设备设置（auto/cpu/cuda）
    DEVICE = os.environ.get("ASR_DEVICE", "auto")
    
    # 语言设置（中文）
    LANGUAGE = "zh"
    
    # 采样率
    SAMPLE_RATE = 16000


class LLMConfig:
    """LLM（大语言模型）配置"""
    
    # OpenAI兼容API配置
    API_BASE_URL = os.environ.get("LLM_API_BASE_URL", "")
    API_KEY = os.environ.get("LLM_API_KEY", "")
    API_MODEL = os.environ.get("LLM_API_MODEL", "")
    
    # 最大生成长度
    MAX_LENGTH = 2048
    
    # 温度参数
    TEMPERATURE = 0.7
    
    # Top-p采样参数
    TOP_P = 0.9


class AudioConfig:
    """音频参数配置"""
    
    # 采样率（Hz）
    SAMPLE_RATE = 16000
    
    # 通道数（1=单声道，2=立体声）
    CHANNELS = 1
    
    # 块大小（每次读取的采样点数）
    CHUNK_SIZE = 1024
    
    # 音频格式
    FORMAT = "int16"


class WebConfig:
    """Web服务配置"""
    
    # 服务主机
    HOST = os.environ.get("WEB_HOST", "0.0.0.0")
    
    # 服务端口
    PORT = int(os.environ.get("WEB_PORT", "8080"))
    
    # WebSocket路径
    WS_PATH = "/ws"
    
    # 静态文件目录
    STATIC_DIR = PROJECT_ROOT / "static"


class SummaryConfig:
    """总结配置"""
    
    # 总结间隔（秒）
    INTERVAL = int(os.environ.get("SUMMARY_INTERVAL", "60"))
    
    # 最小总结长度（字符数）
    MIN_LENGTH = 50


class LogConfig:
    """日志配置"""
    
    # 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    LEVEL = "INFO"
    
    # 日志文件路径
    LOG_FILE = PROJECT_ROOT / "logs" / "meeting_recorder.log"
    
    # 日志文件最大大小（字节）
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # 日志文件备份数量
    BACKUP_COUNT = 5
    
    # 日志格式
    FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    
    # 日期格式
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_config():
    """
    获取配置字典
    
    Returns:
        dict: 包含所有配置的字典
    """
    return {
        "asr": ASRConfig(),
        "llm": LLMConfig(),
        "audio": AudioConfig(),
        "web": WebConfig(),
        "summary": SummaryConfig(),
        "log": LogConfig(),
        "output_dir": OUTPUT_DIR
    }


def validate_config():
    """
    验证配置是否有效
    
    Raises:
        ValueError: 配置无效时抛出异常
    """
    try:
        # 验证音频参数
        if AudioConfig.SAMPLE_RATE <= 0:
            raise ValueError(f"采样率必须大于0，当前值: {AudioConfig.SAMPLE_RATE}")
        
        if AudioConfig.CHANNELS not in [1, 2]:
            raise ValueError(f"通道数必须为1或2，当前值: {AudioConfig.CHANNELS}")
        
        if AudioConfig.CHUNK_SIZE <= 0:
            raise ValueError(f"块大小必须大于0，当前值: {AudioConfig.CHUNK_SIZE}")
        
        # 验证Web服务配置
        if not (0 <= WebConfig.PORT <= 65535):
            raise ValueError(f"端口号必须在0-65535范围内，当前值: {WebConfig.PORT}")
        
        # 验证总结配置
        if SummaryConfig.INTERVAL <= 0:
            raise ValueError(f"总结间隔必须大于0，当前值: {SummaryConfig.INTERVAL}")
        
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if LogConfig.LEVEL.upper() not in valid_levels:
            raise ValueError(f"日志级别无效，当前值: {LogConfig.LEVEL}，有效值: {valid_levels}")
        
        # 验证LLM API配置
        if not LLMConfig.API_BASE_URL:
            raise ValueError("LLM API地址未配置，请在.env文件中设置LLM_API_BASE_URL")
        if not LLMConfig.API_KEY:
            raise ValueError("LLM API密钥未配置，请在.env文件中设置LLM_API_KEY")
        if not LLMConfig.API_MODEL:
            raise ValueError("LLM API模型未配置，请在.env文件中设置LLM_API_MODEL")
        
        return True
        
    except Exception as e:
        raise ValueError(f"配置验证失败: {str(e)}")


if __name__ == "__main__":
    # 测试配置
    try:
        validate_config()
        print("配置验证通过")
        print(f"输出目录: {OUTPUT_DIR}")
        print(f"音频采样率: {AudioConfig.SAMPLE_RATE} Hz")
        print(f"Web服务地址: {WebConfig.HOST}:{WebConfig.PORT}")
        print(f"总结间隔: {SummaryConfig.INTERVAL} 秒")
        print(f"LLM API地址: {LLMConfig.API_BASE_URL}")
        print(f"LLM API模型: {LLMConfig.API_MODEL}")
    except ValueError as e:
        print(f"配置错误: {e}")
