"""
闲鱼 MCP 测试套件

包含所有模块的单元测试和集成测试
"""

import asyncio
import time
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

from typing import List, Dict, Any
from loguru import logger
from datetime import datetime


class TestResult:
    """测试结果"""
    
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0.0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name} ({self.duration*1000:.1f}ms) - {self.message}"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "duration_ms": f"{self.duration*1000:.1f}",
            "timestamp": self.timestamp.isoformat(),
        }


class TestSuite:
    """测试套件"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
    
    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)
        status = "[OK]" if result.passed else "[FAIL]"
        logger.info(f"{status} {result.name}: {result.message}")
    
    def get_summary(self) -> dict:
        """获取测试摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        total_duration = sum(r.duration for r in self.results)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{success_rate:.1f}%",
            "total_duration_ms": f"{total_duration*1000:.1f}",
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
    
    def print_report(self):
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        
        for result in self.results:
            print(result)
        
        print()
        print("-" * 60)
        summary = self.get_summary()
        print(f"总计：{summary['total']} 个测试")
        print(f"通过：{summary['passed']} 个 [OK]")
        print(f"失败：{summary['failed']} 个 [FAIL]")
        print(f"成功率：{summary['success_rate']}")
        print(f"总耗时：{summary['total_duration_ms']}ms")
        print("=" * 60)


# ============== 测试用例 ==============

async def test_browser_launch(suite: TestSuite):
    """测试浏览器启动"""
    test_name = "浏览器启动"
    start = time.time()
    
    try:
        from xianyu_mcp.xianyu.browser import XianyuBrowser
        
        browser = XianyuBrowser(headless=True)
        await browser.launch()
        
        # 检查浏览器是否正常
        assert browser.page is not None, "页面未初始化"
        assert browser.browser is not None, "浏览器未启动"
        
        await browser.close()
        
        duration = time.time() - start
        suite.add_result(TestResult(test_name, True, "浏览器启动正常", duration))
        
    except Exception as e:
        duration = time.time() - start
        suite.add_result(TestResult(test_name, False, str(e), duration))


async def test_login_status(suite: TestSuite):
    """测试登录状态"""
    test_name = "登录状态检查"
    start = time.time()
    
    try:
        from xianyu_mcp.xianyu.browser import XianyuBrowser
        from xianyu_mcp.xianyu.login import XianyuLogin
        
        browser = XianyuBrowser(headless=True)
        await browser.launch()
        
        login = XianyuLogin(browser)
        
        # 加载 Cookie
        cookie_loaded = await login.load_cookies()
        
        if not cookie_loaded:
            await browser.close()
            duration = time.time() - start
            suite.add_result(TestResult(test_name, False, "Cookie 文件不存在", duration))
            return
        
        # 检查登录状态
        await browser.goto_xianyu()
        is_logged_in = await login.check_login_status()
        
        await browser.close()
        
        duration = time.time() - start
        
        if is_logged_in:
            suite.add_result(TestResult(test_name, True, "登录状态正常", duration))
        else:
            suite.add_result(TestResult(test_name, False, "Cookie 已失效", duration))
        
    except Exception as e:
        duration = time.time() - start
        suite.add_result(TestResult(test_name, False, str(e), duration))


async def test_search_items(suite: TestSuite):
    """测试商品搜索"""
    test_name = "商品搜索"
    start = time.time()
    
    try:
        from xianyu_mcp.xianyu.browser import XianyuBrowser
        from xianyu_mcp.xianyu.search import XianyuSearch
        
        browser = XianyuBrowser(headless=True)
        await browser.launch()
        
        search = XianyuSearch(browser)
        
        # 测试搜索
        items = await search.search(
            keyword="手机",
            limit=5
        )
        
        await browser.close()
        
        duration = time.time() - start
        
        if len(items) > 0:
            suite.add_result(TestResult(
                test_name, 
                True, 
                f"搜索到 {len(items)} 个商品", 
                duration
            ))
        else:
            suite.add_result(TestResult(
                test_name, 
                False, 
                "未搜索到商品", 
                duration
            ))
        
    except Exception as e:
        duration = time.time() - start
        suite.add_result(TestResult(test_name, False, str(e), duration))


async def test_message_reply(suite: TestSuite):
    """测试消息回复"""
    test_name = "消息回复生成"
    start = time.time()
    
    try:
        from xianyu_mcp.xianyu.message import XianyuMessage
        
        # 创建消息处理器（不需要浏览器）
        from xianyu_mcp.xianyu.browser import XianyuBrowser
        browser = XianyuBrowser(headless=True)
        await browser.launch()
        
        message_handler = XianyuMessage(browser)
        
        # 测试各种回复场景
        test_cases = [
            ("在吗？", "greeting"),
            ("这个多少钱？", "price"),
            ("包邮吗？", "shipping"),
            ("可以刀吗？", "bargain"),
            ("在哪里？", "location"),
        ]
        
        all_passed = True
        for message, expected_type in test_cases:
            reply = message_handler.generate_reply(message)
            if not reply or len(reply) == 0:
                all_passed = False
                break
        
        await browser.close()
        
        duration = time.time() - start
        
        if all_passed:
            suite.add_result(TestResult(
                test_name, 
                True, 
                f"成功生成 {len(test_cases)} 种回复", 
                duration
            ))
        else:
            suite.add_result(TestResult(
                test_name, 
                False, 
                "部分回复生成失败", 
                duration
            ))
        
    except Exception as e:
        duration = time.time() - start
        suite.add_result(TestResult(test_name, False, str(e), duration))


async def test_analytics_item(suite: TestSuite):
    """测试商品统计"""
    test_name = "商品统计分析"
    start = time.time()
    
    try:
        from xianyu_mcp.xianyu.analytics import ItemStats
        
        # 创建测试数据
        stats = ItemStats(
            item_id="test_123",
            title="测试商品",
            price=100.0,
            view_count=1000,
            want_count=50,
            chat_count=10,
            order_count=5
        )
        
        # 计算转化率
        stats.calculate_rates()
        
        # 验证转化率计算
        assert stats.view_to_want_rate > 0, "转化率计算失败"
        assert stats.view_to_chat_rate > 0, "咨询转化率计算失败"
        
        # 验证数据导出
        data = stats.to_dict()
        assert "view_count" in data, "数据导出失败"
        
        duration = time.time() - start
        suite.add_result(TestResult(
            test_name, 
            True, 
            f"转化率：{stats.view_to_want_rate:.1f}%", 
            duration
        ))
        
    except Exception as e:
        duration = time.time() - start
        suite.add_result(TestResult(test_name, False, str(e), duration))


async def test_performance_monitor(suite: TestSuite):
    """测试性能监控"""
    test_name = "性能监控"
    start = time.time()
    
    try:
        from xianyu_mcp.utils.monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # 记录几次调用
        monitor.record_call("test_func", 0.1, True)
        monitor.record_call("test_func", 0.15, True)
        monitor.record_call("test_func", 0.2, False, "Error message")
        
        # 获取指标
        metrics = monitor.get_metrics("test_func")
        
        assert metrics["total_calls"] == 3, "调用次数统计错误"
        assert metrics["successful_calls"] == 2, "成功次数统计错误"
        assert metrics["failed_calls"] == 1, "失败次数统计错误"
        
        duration = time.time() - start
        suite.add_result(TestResult(
            test_name, 
            True, 
            f"监控 {metrics['total_calls']} 次调用", 
            duration
        ))
        
    except Exception as e:
        duration = time.time() - start
        suite.add_result(TestResult(test_name, False, str(e), duration))


async def test_publish_validation(suite: TestSuite):
    """测试发布参数验证"""
    test_name = "发布参数验证"
    start = time.time()
    
    try:
        from xianyu_mcp.xianyu.publish import PublishParams
        
        # 测试有效参数
        temp_image = Path(__file__).parent / "test_all_image.jpg"
        temp_image.write_bytes(b"test")

        valid_params = PublishParams(
            title="测试商品标题",
            description="这是一个测试商品的详细描述，至少 20 个字",
            price=100.0,
            images=[str(temp_image)],
            location="上海",
            condition="全新"
        )
        
        is_valid, message = valid_params.validate()
        
        duration = time.time() - start
        
        if is_valid:
            suite.add_result(TestResult(
                test_name, 
                True, 
                "参数验证通过", 
                duration
            ))
        else:
            suite.add_result(TestResult(
                test_name, 
                False, 
                f"参数验证失败：{message}", 
                duration
            ))
        temp_image.unlink(missing_ok=True)
        
    except Exception as e:
        duration = time.time() - start
        suite.add_result(TestResult(test_name, False, str(e), duration))


# ============== 测试运行器 ==============

async def run_all_tests():
    """运行所有测试"""
    suite = TestSuite()
    suite.start_time = datetime.now()
    
    logger.info("开始运行测试套件...")
    print("\n" + "=" * 60)
    print("闲鱼 MCP 测试套件")
    print("=" * 60)
    
    # 运行所有测试
    tests = [
        test_browser_launch,
        test_login_status,
        test_search_items,
        test_message_reply,
        test_analytics_item,
        test_performance_monitor,
        test_publish_validation,
    ]
    
    for test in tests:
        try:
            await test(suite)
        except Exception as e:
            logger.error(f"测试执行失败：{e}")
    
    suite.end_time = datetime.now()
    
    # 打印报告
    suite.print_report()
    
    # 保存报告
    report_path = Path(__file__).parent.parent / "test_report.json"
    import json
    
    report_data = {
        "summary": suite.get_summary(),
        "results": [r.to_dict() for r in suite.results],
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"测试报告已保存到：{report_path}")
    
    return suite.get_summary()


if __name__ == "__main__":
    # 设置日志
    from loguru import logger
    logger.add("test.log", rotation="10 MB")
    
    # 运行测试
    asyncio.run(run_all_tests())
