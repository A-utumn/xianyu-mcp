"""
日志配置模块
"""

from loguru import logger
import sys
from pathlib import Path

from ..config import settings


def setup_logger() -> logger:
    """
    配置日志
    
    Returns:
        logger: 配置好的 logger 实例
    """
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # 添加文件输出（如果配置了日志文件）
    if settings.log_file:
        log_dir = settings.log_file.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            settings.log_file,
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )
        logger.info(f"日志文件：{settings.log_file}")
    
    return logger
