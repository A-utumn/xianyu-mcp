"""
闲鱼 MCP 服务器入口

使用方法:
    python src/xianyu_mcp/server.py
"""

import asyncio
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xianyu_mcp.config import settings
from xianyu_mcp.utils.logger import setup_logger

# 初始化日志
logger = setup_logger()

# 创建 MCP 服务器
mcp = FastMCP(
    "xianyu",
    instructions="闲鱼自动化 MCP 服务器 - 提供商品搜索、发布、消息、数据分析等功能"
)


# ============== 基础工具 ==============

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
        "version": "0.2.0",
        "modules": ["search", "publish", "message"],
        "headless": settings.headless,
        "cookie_file": str(settings.cookie_file),
    }


# ============== 搜索工具 ==============

@mcp.tool()
async def search_items(
    keyword: str,
    price_min: float = None,
    price_max: float = None,
    location: str = None,
    sort_by: str = "default",
    limit: int = 20
) -> list:
    """
    搜索闲鱼商品（带错误恢复）
    
    Args:
        keyword: 搜索关键词
        price_min: 最低价格
        price_max: 最高价格
        location: 地区筛选
        sort_by: 排序方式 (default, price_asc, price_desc, sales)
        limit: 返回数量限制
        
    Returns:
        商品列表
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.search import XianyuSearch
    
    logger.info(f"搜索商品：{keyword}")
    
    browser = None
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            browser = XianyuBrowser(headless=True)
            await browser.launch()
            
            search = XianyuSearch(browser)
            items = await search.search(
                keyword=keyword,
                price_min=price_min,
                price_max=price_max,
                location=location,
                sort_by=sort_by,
                limit=limit,
                retry_count=1  # 模块内部不重试，由服务器控制
            )
            
            await browser.close()
            browser = None
            
            logger.info(f"搜索成功，找到 {len(items)} 个商品")
            return [item.to_dict() for item in items]
            
        except Exception as e:
            logger.error(f"搜索失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if browser:
                try:
                    await browser.close()
                except:
                    pass
                browser = None
            
            if attempt < max_retries - 1:
                logger.info("等待 3 秒后重试...")
                import asyncio
                await asyncio.sleep(3)
            else:
                logger.error("搜索失败，已达最大重试次数")
                return []
    
    return []


# ============== 发布工具 ==============

@mcp.tool()
async def publish_item(
    title: str,
    description: str,
    price: float,
    images: list,
    category: str = "",
    location: str = "",
    condition: str = "全新",
    delivery: str = "包邮",
    dry_run: bool = False,
) -> dict:
    """
    发布闲鱼商品
    
    Args:
        title: 标题（最多 20 字）
        description: 描述（最多 1000 字）
        price: 价格
        images: 图片路径列表
        category: 分类
        location: 地区
        condition: 新旧程度
        delivery: 配送方式
        dry_run: 是否仅预检查表单，不真正提交发布
        
    Returns:
        发布结果 {"success": bool, "item_id": str, "message": str}
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.publish import XianyuPublish, PublishParams
    
    logger.info(f"发布商品：{title}")
    
    # 验证参数
    if not title or len(title) > 20:
        return {"success": False, "message": "标题最多 20 个字"}
    
    if not description or len(description) > 1000:
        return {"success": False, "message": "描述最多 1000 字"}
    
    if price <= 0:
        return {"success": False, "message": "价格必须大于 0"}
    
    if not images or len(images) == 0:
        return {"success": False, "message": "至少需要 1 张图片"}
    
    browser = XianyuBrowser(headless=False)
    try:
        await browser.launch()
        publish = XianyuPublish(browser)
        
        params = PublishParams(
            title=title,
            description=description,
            price=price,
            images=images,
            category=category,
            location=location,
            condition=condition,
            delivery=delivery
        )

        if dry_run:
            result = await publish.precheck_publish(params)
            await browser.close()
            return result

        success, result = await publish.publish(params)
        await browser.close()
        
        if success:
            return {"success": True, "item_id": result, "message": "发布成功"}
        else:
            return {"success": False, "message": result}
        
    except Exception as e:
        logger.error(f"发布失败：{e}")
        return {"success": False, "message": str(e)}


# ============== 消息工具 ==============

@mcp.tool()
async def get_conversations(
    limit: int = 20,
    sendable_only: bool = False,
    context_only: bool = False,
) -> dict:
    """
    获取会话列表

    Args:
        limit: 数量限制
        sendable_only: 是否仅返回可发送会话
        context_only: 是否仅返回已有商品上下文的会话

    Returns:
        会话列表和状态
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.message import XianyuMessage

    logger.info(
        f"获取会话列表，限制：{limit}，仅可发送：{sendable_only}，仅上下文完整：{context_only}"
    )

    browser = XianyuBrowser(headless=False)
    try:
        await browser.launch()
        message = XianyuMessage(browser)
        conversations = await message.get_conversations(limit=limit)
        total_before_filter = len(conversations)

        if sendable_only:
            conversations = [item for item in conversations if item.can_send]

        if context_only:
            conversations = [item for item in conversations if item.has_context]

        conversations = conversations[:limit]
        block_reason = message.get_last_block_reason()
        await browser.close()

        response_message = block_reason or "获取成功"
        if (
            not block_reason
            and context_only
            and total_before_filter > 0
            and not conversations
        ):
            response_message = "当前会话尚未建立商品上下文；请先读取或打开目标会话后再使用 context_only 过滤"

        return {
            "success": not bool(block_reason) or bool(conversations),
            "requires_manual_verification": bool(block_reason) and not bool(conversations),
            "message": response_message,
            "total_before_filter": total_before_filter,
            "applied_filters": {
                "sendable_only": sendable_only,
                "context_only": context_only,
            },
            "items": [item.to_dict() for item in conversations],
        }

    except Exception as e:
        logger.error(f"获取会话列表失败：{e}")
        return {
            "success": False,
            "requires_manual_verification": False,
            "message": str(e),
            "total_before_filter": 0,
            "applied_filters": {
                "sendable_only": sendable_only,
                "context_only": context_only,
            },
            "items": [],
        }


@mcp.tool()
async def get_unread_messages() -> dict:
    """
    获取未读消息数
    
    Returns:
        未读消息状态
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.message import XianyuMessage
    
    logger.info("获取未读消息数")
    
    browser = XianyuBrowser(headless=False)
    try:
        await browser.launch()
        message = XianyuMessage(browser)
        count = await message.get_unread_count()
        block_reason = message.get_last_block_reason()
        await browser.close()
        
        return {
            "success": not bool(block_reason),
            "count": count,
            "requires_manual_verification": bool(block_reason),
            "message": block_reason or "获取成功",
        }
        
    except Exception as e:
        logger.error(f"获取未读数失败：{e}")
        return {
            "success": False,
            "count": 0,
            "requires_manual_verification": False,
            "message": str(e),
        }


@mcp.tool()
async def get_sendable_conversations(limit: int = 10, warm_context: bool = False) -> dict:
    """
    获取可发送会话列表

    Args:
        limit: 返回数量限制
        warm_context: 是否尝试预热前几个会话的商品上下文

    Returns:
        可发送会话列表和状态
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.message import XianyuMessage

    logger.info(f"获取可发送会话，限制：{limit}，预热上下文：{warm_context}")

    browser = XianyuBrowser(headless=False)
    try:
        await browser.launch()
        message = XianyuMessage(browser)

        fetch_limit = max(limit * 3, limit)
        conversations = await message.get_conversations(limit=fetch_limit)
        sendable_conversations = [item for item in conversations if item.can_send][:limit]

        warmed = 0
        if warm_context:
            for conversation in sendable_conversations:
                if conversation.has_context:
                    continue
                context = await message.warm_conversation_context(conversation.id)
                if context:
                    warmed += 1

            # 重新获取并过滤，带上预热后的上下文信息和排序
            refreshed = await message.get_conversations(limit=fetch_limit)
            refreshed_map = {item.id: item for item in refreshed}
            sendable_conversations = [
                refreshed_map.get(item.id, item)
                for item in sendable_conversations
                if (refreshed_map.get(item.id, item)).can_send
            ][:limit]

        block_reason = message.get_last_block_reason()
        await browser.close()

        response_message = block_reason or "获取成功"
        if warm_context and not block_reason and warmed == 0:
            response_message = "获取成功；本次没有新增可预热的商品上下文"

        return {
            "success": not bool(block_reason) or bool(sendable_conversations),
            "requires_manual_verification": bool(block_reason) and not bool(sendable_conversations),
            "message": response_message,
            "warmed_context_count": warmed,
            "items": [item.to_dict() for item in sendable_conversations],
        }

    except Exception as e:
        logger.error(f"获取可发送会话失败：{e}")
        return {
            "success": False,
            "requires_manual_verification": False,
            "message": str(e),
            "warmed_context_count": 0,
            "items": [],
        }


@mcp.tool()
async def get_messages(conversation_id: str, limit: int = 50) -> dict:
    """
    获取指定会话的消息列表

    Args:
        conversation_id: 会话 ID
        limit: 消息数量限制

    Returns:
        消息列表和状态
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.message import XianyuMessage

    logger.info(f"获取会话 {conversation_id} 的消息，限制：{limit}")

    browser = XianyuBrowser(headless=False)
    try:
        await browser.launch()
        message = XianyuMessage(browser)
        items = await message.get_messages(conversation_id=conversation_id, limit=limit)
        block_reason = message.get_last_block_reason()
        await browser.close()

        sources = {item.source for item in items if getattr(item, "source", "")}
        source = "mixed" if len(sources) > 1 else (next(iter(sources)) if sources else "unknown")

        return {
            "success": not bool(block_reason) or bool(items),
            "requires_manual_verification": bool(block_reason) and not bool(items),
            "message": block_reason or "获取成功",
            "source": source,
            "items": [item.to_dict() for item in items],
        }

    except Exception as e:
        logger.error(f"获取会话消息失败：{e}")
        return {
            "success": False,
            "requires_manual_verification": False,
            "message": str(e),
            "source": "unknown",
            "items": [],
        }


@mcp.tool()
async def send_message(user_id: str, content: str) -> dict:
    """
    发送消息
    
    Args:
        user_id: 用户 ID
        content: 消息内容
        
    Returns:
        发送结果
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.message import XianyuMessage
    
    logger.info(f"发送消息给 {user_id}")
    
    browser = XianyuBrowser(headless=False)
    try:
        await browser.launch()
        message = XianyuMessage(browser)
        success, result = await message.send_reply(user_id=user_id, content=content)
        block_reason = message.get_last_block_reason()
        await browser.close()
        
        return {
            "success": success,
            "requires_manual_verification": bool(block_reason),
            "message": result
        }
        
    except Exception as e:
        logger.error(f"发送消息失败：{e}")
        return {
            "success": False,
            "requires_manual_verification": False,
            "message": str(e)
        }


# ============== 数据分析工具 ==============

@mcp.tool()
async def get_item_analytics(item_id: str) -> dict:
    """
    获取商品统计数据
    
    Args:
        item_id: 商品 ID
        
    Returns:
        商品统计数据
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.analytics import XianyuAnalytics
    
    logger.info(f"获取商品 {item_id} 的统计数据")
    
    browser = XianyuBrowser(headless=True)
    try:
        await browser.launch()
        analytics = XianyuAnalytics(browser)
        stats = await analytics.get_item_stats(item_id=item_id)
        await browser.close()
        
        if stats:
            return stats.to_dict()
        return {"error": "获取失败"}
        
    except Exception as e:
        logger.error(f"获取商品统计失败：{e}")
        return {"error": str(e)}


@mcp.tool()
async def get_sales_analytics(days: int = 7) -> dict:
    """
    获取销售统计
    
    Args:
        days: 统计天数
        
    Returns:
        销售统计数据
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.analytics import XianyuAnalytics
    
    logger.info(f"获取最近 {days} 天的销售统计")
    
    browser = XianyuBrowser(headless=True)
    try:
        await browser.launch()
        analytics = XianyuAnalytics(browser)
        stats = await analytics.get_sales_stats(days=days)
        await browser.close()
        
        return stats.to_dict()
        
    except Exception as e:
        logger.error(f"获取销售统计失败：{e}")
        return {"error": str(e)}


@mcp.tool()
async def get_traffic_analytics(days: int = 7) -> dict:
    """
    获取流量统计
    
    Args:
        days: 统计天数
        
    Returns:
        流量统计数据
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.analytics import XianyuAnalytics
    
    logger.info(f"获取最近 {days} 天的流量统计")
    
    browser = XianyuBrowser(headless=True)
    try:
        await browser.launch()
        analytics = XianyuAnalytics(browser)
        stats = await analytics.get_traffic_stats(days=days)
        await browser.close()
        
        return stats.to_dict()
        
    except Exception as e:
        logger.error(f"获取流量统计失败：{e}")
        return {"error": str(e)}


@mcp.tool()
async def get_top_items(limit: int = 10, sort_by: str = "sales") -> list:
    """
    获取热门商品排行
    
    Args:
        limit: 返回数量
        sort_by: 排序方式 (sales, views, wants)
        
    Returns:
        商品列表
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.analytics import XianyuAnalytics
    
    logger.info(f"获取热门商品排行")
    
    browser = XianyuBrowser(headless=True)
    try:
        await browser.launch()
        analytics = XianyuAnalytics(browser)
        items = await analytics.get_top_items(limit=limit, sort_by=sort_by)
        await browser.close()
        
        return [item.to_dict() for item in items]
        
    except Exception as e:
        logger.error(f"获取热门商品失败：{e}")
        return []


@mcp.tool()
async def analyze_competitors(item_ids: list) -> dict:
    """
    分析竞品商品

    Args:
        item_ids: 竞品商品 ID 列表

    Returns:
        竞品分析结果
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.analytics import XianyuAnalytics

    logger.info(f"分析竞品：{item_ids}")

    if not item_ids:
        return {
            "total_items": 0,
            "analyzed_items": 0,
            "avg_price": 0.0,
            "price_range": {"min": 0, "max": 0},
            "avg_views": 0,
            "avg_wants": 0,
            "items": [],
            "message": "请至少提供一个商品 ID",
        }

    browser = XianyuBrowser(headless=True)
    try:
        await browser.launch()
        analytics = XianyuAnalytics(browser)
        result = await analytics.analyze_competitors(item_ids=item_ids)
        await browser.close()

        result["analyzed_items"] = len(result.get("items", []))
        result["message"] = "分析完成" if result["analyzed_items"] else "未获取到有效竞品数据"
        return result

    except Exception as e:
        logger.error(f"竞品分析失败：{e}")
        return {
            "total_items": len(item_ids),
            "analyzed_items": 0,
            "avg_price": 0.0,
            "price_range": {"min": 0, "max": 0},
            "avg_views": 0,
            "avg_wants": 0,
            "items": [],
            "message": str(e),
        }


@mcp.tool()
async def generate_report(days: int = 7) -> dict:
    """
    生成综合分析报告
    
    Args:
        days: 统计天数
        
    Returns:
        报告数据
    """
    from xianyu_mcp.xianyu.browser import XianyuBrowser
    from xianyu_mcp.xianyu.analytics import XianyuAnalytics
    
    logger.info(f"生成最近 {days} 天的综合分析报告")
    
    browser = XianyuBrowser(headless=True)
    try:
        await browser.launch()
        analytics = XianyuAnalytics(browser)
        report = await analytics.generate_report(days=days)
        await browser.close()
        
        return report
        
    except Exception as e:
        logger.error(f"生成报告失败：{e}")
        return {"error": str(e)}


# ============== 主函数 ==============

async def main_async():
    """异步主函数"""
    logger.info("启动闲鱼 MCP 服务器 v0.3.0...")
    logger.info("服务器名称：xianyu")
    logger.info("可用工具:")
    logger.info("  基础工具:")
    logger.info("    - hello: 测试连接")
    logger.info("    - check_server_status: 检查服务器状态")
    logger.info("  搜索工具:")
    logger.info("    - search_items: 搜索商品")
    logger.info("  发布工具:")
    logger.info("    - publish_item: 发布商品")
    logger.info("  消息工具:")
    logger.info("    - get_conversations: 获取会话列表")
    logger.info("    - get_sendable_conversations: 获取可发送会话")
    logger.info("    - get_unread_messages: 获取未读消息")
    logger.info("    - get_messages: 获取会话消息")
    logger.info("    - send_message: 发送消息")
    logger.info("  数据分析工具:")
    logger.info("    - get_item_analytics: 商品统计")
    logger.info("    - get_sales_analytics: 销售统计")
    logger.info("    - get_traffic_analytics: 流量统计")
    logger.info("    - get_top_items: 热门排行")
    logger.info("    - analyze_competitors: 竞品分析")
    logger.info("    - generate_report: 综合报告")
    logger.info("=" * 60)
    logger.info("MCP 服务器已启动，等待连接...")
    logger.info("按 Ctrl+C 停止服务器")
    logger.info("=" * 60)
    
    # 保持服务器运行
    import signal
    
    stop_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        logger.info("收到停止信号，正在关闭...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 等待停止信号
    await stop_event.wait()
    logger.info("服务器已停止")


def main():
    """主函数"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
