"""
闲鱼登录脚本

使用方法:
    python scripts/login.py
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
    print("闲鱼 MCP - 扫码登录")
    print("=" * 60)
    print()
    
    # 创建浏览器实例
    browser = XianyuBrowser(headless=False)  # 使用有头模式，方便扫码
    
    try:
        # 启动浏览器
        await browser.launch()
        
        # 创建登录管理
        login = XianyuLogin(browser)
        
        # 执行扫码登录
        success = await login.login_with_qrcode(timeout=120)
        
        if success:
            print()
            print("=" * 60)
            print("✅ 登录成功！")
            print("=" * 60)
            print()
            print("Cookie 已保存到：cookies/default.json")
            print()
            print("下一步:")
            print("1. 运行 python scripts/check_status.py 检查登录状态")
            print("2. 运行 python src/xianyu_mcp/server.py 启动 MCP 服务器")
        else:
            print()
            print("=" * 60)
            print("❌ 登录失败")
            print("=" * 60)
            print()
            print("请检查:")
            print("1. 网络是否正常")
            print("2. 是否在规定时间内完成扫码")
            print("3. 闲鱼账号是否正常")
        
    except KeyboardInterrupt:
        print("\n\n用户中断登录")
    except Exception as e:
        logger.error(f"登录过程出错：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭浏览器
        await browser.close()
        print("浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
