"""
简化测试脚本 - 测试核心功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def main():
    print("=" * 60)
    print("闲鱼 MCP 核心功能测试")
    print("=" * 60)
    print()
    
    # 测试 1：导入模块
    print("[测试] 导入模块...")
    try:
        import xianyu_mcp
        from xianyu_mcp.xianyu.browser import XianyuBrowser
        from xianyu_mcp.xianyu.login import XianyuLogin
        from xianyu_mcp.xianyu.search import XianyuSearch
        from xianyu_mcp.xianyu.publish import XianyuPublish, PublishParams
        from xianyu_mcp.xianyu.message import XianyuMessage
        from xianyu_mcp.xianyu.analytics import XianyuAnalytics, ItemStats
        from xianyu_mcp.utils.monitor import PerformanceMonitor
        print("[OK] 所有模块导入成功")
    except Exception as e:
        print(f"[FAIL] 模块导入失败：{e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # 测试 2：性能监控
    print("[测试] 性能监控...")
    try:
        monitor = PerformanceMonitor()
        monitor.record_call("test", 0.1, True)
        metrics = monitor.get_metrics("test")
        assert metrics["total_calls"] == 1
        print(f"[OK] 性能监控正常 - {metrics['total_calls']} 次调用")
    except Exception as e:
        print(f"[FAIL] 性能监控失败：{e}")
    
    print()
    
    # 测试 3：数据统计
    print("[测试] 数据统计...")
    try:
        stats = ItemStats(
            item_id="test_123",
            title="测试商品",
            price=100.0,
            view_count=1000,
            want_count=50,
            chat_count=10,
            order_count=5
        )
        stats.calculate_rates()
        data = stats.to_dict()
        print(f"[OK] 数据统计正常 - 转化率 {stats.view_to_want_rate:.1f}%")
    except Exception as e:
        print(f"[FAIL] 数据统计失败：{e}")
    
    print()
    
    # 测试 4：参数验证
    print("[测试] 发布参数验证...")
    try:
        temp_image = Path(__file__).parent / "quick_test_image.jpg"
        temp_image.write_bytes(b"test")

        params = PublishParams(
            title="测试商品标题",
            description="这是一个测试商品的详细描述，至少 20 个字",
            price=100.0,
            images=[str(temp_image)],
            location="上海",
            condition="全新"
        )
        is_valid, message = params.validate()
        if is_valid:
            print(f"[OK] 参数验证通过")
        else:
            print(f"[FAIL] 参数验证失败：{message}")
        temp_image.unlink(missing_ok=True)
    except Exception as e:
        print(f"[FAIL] 参数验证失败：{e}")
    
    print()
    
    # 测试 5：智能回复
    print("[测试] 智能回复生成...")
    try:
        from xianyu_mcp.xianyu.message import XianyuMessage
        from xianyu_mcp.xianyu.browser import XianyuBrowser
        
        browser = XianyuBrowser(headless=True)
        await browser.launch()
        
        message_handler = XianyuMessage(browser)
        
        test_messages = [
            "在吗？",
            "这个多少钱？",
            "包邮吗？",
            "可以刀吗？",
        ]
        
        for msg in test_messages:
            reply = message_handler.generate_reply(msg)
            print(f"  问：{msg} -> 答：{reply[:30]}...")
        
        await browser.close()
        print(f"[OK] 智能回复正常 - 测试 {len(test_messages)} 条消息")
    except Exception as e:
        print(f"[FAIL] 智能回复失败：{e}")
    
    print()
    
    # 测试 6：消息数据结构
    print("[测试] 消息数据结构...")
    try:
        from xianyu_mcp.xianyu.message import Message, Conversation

        msg = Message(
            id="msg_1",
            conversation_id="conv_1",
            content="测试",
            source="dom",
            item_id="item_1",
            item_title="测试商品"
        )
        conv = Conversation(
            id="conv_1",
            user_name="测试会话",
            can_send=True,
            source="api",
            has_context=True
        )

        msg_data = msg.to_dict()
        conv_data = conv.to_dict()
        assert msg_data["source"] == "dom"
        assert conv_data["source"] == "api"
        assert conv_data["has_context"] is True
        print("[OK] 消息数据结构正常")
    except Exception as e:
        print(f"[FAIL] 消息数据结构失败：{e}")

    print()

    # 测试 7：登录状态
    print("[测试] 登录状态检查...")
    try:
        from xianyu_mcp.xianyu.login import XianyuLogin
        from xianyu_mcp.xianyu.browser import XianyuBrowser
        
        browser = XianyuBrowser(headless=True)
        await browser.launch()
        
        login = XianyuLogin(browser)
        cookie_loaded = await login.load_cookies()
        
        if cookie_loaded:
            await browser.goto_xianyu()
            is_logged_in = await login.check_login_status()
            
            if is_logged_in:
                print(f"[OK] 登录状态正常")
            else:
                print(f"[WARN] Cookie 可能已失效")
        else:
            print(f"[WARN] Cookie 文件不存在")
        
        await browser.close()
    except Exception as e:
        print(f"[FAIL] 登录状态检查失败：{e}")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
