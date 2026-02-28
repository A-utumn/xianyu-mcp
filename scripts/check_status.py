"""
检查登录状态脚本

使用方法:
    python scripts/check_status.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xianyu_mcp.xianyu.browser import XianyuBrowser
from xianyu_mcp.xianyu.login import XianyuLogin
from loguru import logger


async def main():
    """主函数"""
    print("=" * 60)
    print("闲鱼 MCP - 检查登录状态")
    print("=" * 60)
    print()
    
    # 创建浏览器实例（使用无头模式）
    browser = XianyuBrowser(headless=True)
    
    try:
        # 启动浏览器
        await browser.launch()
        
        # 创建登录管理
        login = XianyuLogin(browser)
        
        # 尝试加载 Cookie
        print("正在加载 Cookie...")
        cookie_loaded = await login.load_cookies()
        
        if not cookie_loaded:
            print("❌ Cookie 文件不存在")
            print()
            print("请先运行登录脚本:")
            print("  python scripts/login.py")
            return
        
        # 打开闲鱼
        print("正在打开闲鱼...")
        await browser.goto_xianyu()
        
        # 检查登录状态
        print("正在检查登录状态...")
        await asyncio.sleep(3)  # 等待页面加载
        
        is_logged_in = await login.check_login_status()
        
        print()
        print("=" * 60)
        if is_logged_in:
            print("✅ 登录状态正常！")
            print("=" * 60)
            print()
            print("可以开始使用 MCP 服务器:")
            print("  python src/xianyu_mcp/server.py")
        else:
            print("❌ Cookie 已失效")
            print("=" * 60)
            print()
            print("请重新登录:")
            print("  python scripts/login.py")
        
    except Exception as e:
        logger.error(f"检查失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭浏览器
        await browser.close()
        print("\n浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
