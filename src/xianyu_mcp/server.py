"""
闲鱼 MCP 服务器入口

使用方法:
    python src/xianyu_mcp/server.py
"""

import asyncio
from mcp.server.fastmcp import FastMCP

from .config import settings
from .utils.logger import setup_logger

# 初始化日志
logger = setup_logger()

# 创建 MCP 服务器
mcp = FastMCP(
    "xianyu",
    instructions="闲鱼自动化 MCP 服务器 - 提供商品搜索、发布、消息、数据分析等功能"
)


@mcp.tool()
async def hello(name: str) -> str:
    """测试工具 - 验证 MCP 服务器是否正常运行"""
    logger.info(f"收到测试请求：{name}")
    return f"Hello, {name}! 闲鱼 MCP 服务器已启动！"


@mcp.tool()
async def check_server_status() -> dict:
    """检查服务器状态"""
    return {
        "status": "running",
        "version": "0.1.0",
        "headless": settings.headless,
        "cookie_file": str(settings.cookie_file),
    }


def main():
    """主函数"""
    logger.info("启动闲鱼 MCP 服务器...")
    mcp.run()


if __name__ == "__main__":
    main()
