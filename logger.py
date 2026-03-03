# -*- coding: utf-8 -*-
"""
日志模块
提供统一的日志记录功能，支持控制台和文件输出
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import LogConfig, PROJECT_ROOT


class LoggerManager:
    """日志管理器"""
    
    _instance: Optional['LoggerManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志管理器"""
        if self._initialized:
            return
        
        self._initialized = True
        self._loggers = {}
        self._root_logger = None
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """设置根日志记录器"""
        try:
            # 创建根日志记录器
            self._root_logger = logging.getLogger()
            self._root_logger.setLevel(self._get_log_level(LogConfig.LEVEL))
            
            # 清除现有处理器
            self._root_logger.handlers.clear()
            
            # 创建格式化器
            formatter = logging.Formatter(
                fmt=LogConfig.FORMAT,
                datefmt=LogConfig.DATE_FORMAT
            )
            
            # 添加控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._get_log_level(LogConfig.LEVEL))
            console_handler.setFormatter(formatter)
            self._root_logger.addHandler(console_handler)
            
            # 添加文件处理器
            self._add_file_handler(formatter)
            
        except Exception as e:
            print(f"初始化日志系统失败: {str(e)}", file=sys.stderr)
            raise
    
    def _add_file_handler(self, formatter: logging.Formatter):
        """
        添加文件处理器
        
        Args:
            formatter: 日志格式化器
        """
        try:
            # 确保日志目录存在
            log_dir = Path(LogConfig.LOG_FILE).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建轮转文件处理器
            file_handler = RotatingFileHandler(
                filename=str(LogConfig.LOG_FILE),
                maxBytes=LogConfig.MAX_FILE_SIZE,
                backupCount=LogConfig.BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(self._get_log_level(LogConfig.LEVEL))
            file_handler.setFormatter(formatter)
            self._root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"创建日志文件处理器失败: {str(e)}", file=sys.stderr)
    
    @staticmethod
    def _get_log_level(level_str: str) -> int:
        """
        将日志级别字符串转换为日志级别常量
        
        Args:
            level_str: 日志级别字符串（DEBUG/INFO/WARNING/ERROR/CRITICAL）
            
        Returns:
            int: 日志级别常量
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_str.upper(), logging.INFO)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            logging.Logger: 日志记录器实例
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]
    
    def set_level(self, level: str):
        """
        设置日志级别
        
        Args:
            level: 日志级别字符串（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        """
        try:
            log_level = self._get_log_level(level)
            self._root_logger.setLevel(log_level)
            
            # 更新所有处理器的级别
            for handler in self._root_logger.handlers:
                handler.setLevel(log_level)
            
            print(f"日志级别已设置为: {level.upper()}")
            
        except Exception as e:
            print(f"设置日志级别失败: {str(e)}", file=sys.stderr)


def get_logger(name: str = __name__) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称，默认为调用模块名
        
    Returns:
        logging.Logger: 日志记录器实例
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条日志消息")
    """
    try:
        manager = LoggerManager()
        return manager.get_logger(name)
    except Exception as e:
        print(f"获取日志记录器失败: {str(e)}", file=sys.stderr)
        # 返回默认日志记录器
        return logging.getLogger(name)


def set_log_level(level: str):
    """
    设置日志级别
    
    Args:
        level: 日志级别字符串（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        
    Example:
        >>> set_log_level("DEBUG")
    """
    try:
        manager = LoggerManager()
        manager.set_level(level)
    except Exception as e:
        print(f"设置日志级别失败: {str(e)}", file=sys.stderr)


if __name__ == "__main__":
    # 测试日志功能
    logger = get_logger(__name__)
    
    logger.debug("这是一条DEBUG消息")
    logger.info("这是一条INFO消息")
    logger.warning("这是一条WARNING消息")
    logger.error("这是一条ERROR消息")
    logger.critical("这是一条CRITICAL消息")
    
    print("\n测试修改日志级别为DEBUG:")
    set_log_level("DEBUG")
    logger.debug("修改级别后的DEBUG消息")
