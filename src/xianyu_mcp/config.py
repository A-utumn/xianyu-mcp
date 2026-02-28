"""
配置管理模块
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """闲鱼 MCP 配置"""
    
    # 项目配置
    project_name: str = "xianyu-mcp"
    version: str = "0.1.0"
    
    # 浏览器配置
    headless: bool = False  # 是否无头模式
    browser_path: Optional[str] = None  # 浏览器路径
    viewport_width: int = 1920
    viewport_height: int = 1080
    
    # Cookie 配置
    cookie_file: Path = Path("./cookies/default.json")
    user_data_dir: Path = Path("./user_data")
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[Path] = Path("./logs/xianyu.log")
    
    # 超时配置
    timeout: int = 30  # 操作超时时间（秒）
    page_load_timeout: int = 60
    
    # 频率控制（秒）
    search_interval: float = 3.0
    publish_interval: float = 30.0
    message_interval: float = 5.0
    
    # 闲鱼配置
    xianyu_url: str = "https://2.taobao.com/"
    xianyu_mobile_url: str = "https://m.goofish.com/"
    
    class Config:
        env_prefix = "XIANIU_"
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
