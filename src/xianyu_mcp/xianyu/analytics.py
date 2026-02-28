"""
数据分析模块

实现闲鱼商品数据、销售统计、流量分析等功能
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import re
from loguru import logger

from .browser import XianyuBrowser


@dataclass
class ItemStats:
    """商品统计数据"""
    item_id: str = ""
    title: str = ""
    price: float = 0.0
    
    # 互动数据
    view_count: int = 0  # 浏览数
    want_count: int = 0  # 想要人数
    like_count: int = 0  # 点赞数
    collect_count: int = 0  # 收藏数
    comment_count: int = 0  # 评论数
    
    # 转化数据
    chat_count: int = 0  # 咨询人数
    order_count: int = 0  # 成交数
    
    # 时间数据
    publish_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    
    # 转化率
    view_to_want_rate: float = 0.0  # 浏览到想要转化率
    view_to_chat_rate: float = 0.0  # 浏览到咨询转化率
    chat_to_order_rate: float = 0.0  # 咨询到成交转化率
    
    def calculate_rates(self):
        """计算转化率"""
        if self.view_count > 0:
            self.view_to_want_rate = self.want_count / self.view_count * 100
            self.view_to_chat_rate = self.chat_count / self.view_count * 100
        
        if self.chat_count > 0:
            self.chat_to_order_rate = self.order_count / self.chat_count * 100
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "item_id": self.item_id,
            "title": self.title,
            "price": self.price,
            "view_count": self.view_count,
            "want_count": self.want_count,
            "like_count": self.like_count,
            "collect_count": self.collect_count,
            "comment_count": self.comment_count,
            "chat_count": self.chat_count,
            "order_count": self.order_count,
            "view_to_want_rate": f"{self.view_to_want_rate:.1f}%",
            "view_to_chat_rate": f"{self.view_to_chat_rate:.1f}%",
            "chat_to_order_rate": f"{self.chat_to_order_rate:.1f}%",
        }


@dataclass
class SalesStats:
    """销售统计数据"""
    # 时间范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # 销售数据
    total_sales: float = 0.0  # 总销售额
    total_orders: int = 0  # 总订单数
    total_items: int = 0  # 总商品数
    
    # 日均数据
    daily_sales: float = 0.0  # 日均销售额
    daily_orders: float = 0.0  # 日均订单数
    
    # 转化数据
    total_views: int = 0  # 总浏览数
    total_wants: int = 0  # 总想要数
    view_to_order_rate: float = 0.0  # 浏览到订单转化率
    
    # 商品排行
    top_items: List[Dict] = field(default_factory=list)
    
    # 趋势数据
    sales_trend: List[Dict] = field(default_factory=list)  # 销售趋势
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "period": {
                "start": self.start_date.isoformat() if self.start_date else None,
                "end": self.end_date.isoformat() if self.end_date else None,
                "days": (self.end_date - self.start_date).days if self.start_date and self.end_date else 0,
            },
            "sales": {
                "total": f"¥{self.total_sales:.2f}",
                "daily": f"¥{self.daily_sales:.2f}",
            },
            "orders": {
                "total": self.total_orders,
                "daily": f"{self.daily_orders:.1f}",
            },
            "conversion": {
                "view_to_order": f"{self.view_to_order_rate:.2f}%",
            },
            "top_items": self.top_items[:5],  # 前 5 名
        }


@dataclass
class TrafficStats:
    """流量统计数据"""
    # 总体流量
    total_views: int = 0  # 总浏览数
    total_visitors: int = 0  # 总访客数
    avg_views_per_day: float = 0.0  # 日均浏览数
    
    # 流量来源
    traffic_sources: Dict[str, int] = field(default_factory=dict)
    # 示例：{"search": 500, "recommend": 300, "direct": 200}
    
    # 时间段分布
    hourly_distribution: Dict[int, int] = field(default_factory=dict)
    # 示例：{9: 50, 10: 80, 11: 100, ...}
    
    # 用户画像
    user_demographics: Dict[str, Any] = field(default_factory=dict)
    # 示例：{"age_groups": {"18-24": 30, "25-34": 50}, "genders": {"male": 60, "female": 40}}
    
    # 热门关键词
    hot_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "overview": {
                "total_views": self.total_views,
                "total_visitors": self.total_visitors,
                "avg_views_per_day": f"{self.avg_views_per_day:.1f}",
            },
            "sources": self.traffic_sources,
            "hourly_distribution": self.hourly_distribution,
            "hot_keywords": self.hot_keywords[:10],
        }


class XianyuAnalytics:
    """闲鱼数据分析类"""
    
    def __init__(self, browser: XianyuBrowser):
        """
        初始化数据分析模块
        
        Args:
            browser: 浏览器实例
        """
        self.browser = browser
        logger.info("数据分析模块已初始化")
    
    async def get_item_stats(self, item_id: str) -> Optional[ItemStats]:
        """
        获取商品统计数据
        
        Args:
            item_id: 商品 ID
            
        Returns:
            商品统计数据
        """
        logger.info(f"获取商品 {item_id} 的统计数据")
        
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")
        
        try:
            # 打开商品详情页
            item_url = f"https://www.goofish.com/item?id={item_id}"
            await self.browser.page.goto(item_url, wait_until="networkidle", timeout=30000)
            await self.browser.page.wait_for_timeout(3000)
            
            # 解析统计数据
            stats = await self._parse_item_stats(item_id)
            
            if stats:
                stats.calculate_rates()
                logger.info(f"商品统计：浏览 {stats.view_count}, 想要 {stats.want_count}, 成交 {stats.order_count}")
            
            return stats
            
        except Exception as e:
            logger.error(f"获取商品统计失败：{e}")
            return None
    
    async def _parse_item_stats(self, item_id: str) -> Optional[ItemStats]:
        """解析商品统计数据"""
        try:
            stats = ItemStats(item_id=item_id)
            
            if not self.browser.page:
                return None
            
            detail_text = await self._get_item_detail_text()

            # 提取价格
            price_text = await self._first_visible_text(
                [
                    "[class*='price--'][class*='windows--']",
                    "[class*='price--']",
                    "[class*='price-wrap']",
                ]
            )
            stats.price = self._parse_price(price_text or detail_text)

            # 提取想要数、浏览数
            stats.want_count = self._extract_metric(detail_text, [r"(\d+(?:\.\d+)?)\s*人想要"])
            stats.view_count = self._extract_metric(detail_text, [r"(\d+(?:\.\d+)?)\s*浏览"])

            # 标题优先从详情文本窗口中取，避免误抓推荐区
            stats.title = self._extract_title(detail_text)

            # 收藏/评论当前详情页没有稳定显式入口，先保守留空
            stats.collect_count = self._extract_metric(
                detail_text,
                [r"(\d+(?:\.\d+)?)\s*收藏", r"收藏\s*(\d+(?:\.\d+)?)"],
            )
            stats.comment_count = self._extract_metric(
                detail_text,
                [r"(\d+(?:\.\d+)?)\s*评论", r"评论\s*(\d+(?:\.\d+)?)"],
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"解析商品统计失败：{e}")
            return None
    
    def _parse_number(self, text: str) -> int:
        """解析数字（支持万、亿单位）"""
        text = text.strip()
        
        # 提取数字
        match = re.search(r'([\d.]+)', text)
        if not match:
            return 0
        
        num = float(match.group(1))
        
        # 处理单位
        if '万' in text:
            num *= 10000
        elif '亿' in text:
            num *= 100000000
        
        return int(num)

    async def _first_visible_text(self, selectors: List[str]) -> str:
        """从多个选择器中提取第一个可见元素文本。"""
        if not self.browser.page:
            return ""

        for selector in selectors:
            locator = self.browser.page.locator(selector)
            count = await locator.count()
            for index in range(count):
                item = locator.nth(index)
                try:
                    if not await item.is_visible():
                        continue
                    text = (await item.inner_text()).strip()
                    if text:
                        return text
                except Exception:
                    continue

        return ""

    async def _get_item_detail_text(self) -> str:
        """获取商品详情主区域文本，尽量排除推荐区。"""
        if not self.browser.page:
            return ""

        body_text = await self.browser.page.evaluate(
            "() => document.body && document.body.innerText ? document.body.innerText : ''"
        )
        if not body_text:
            return ""

        for marker in ["为你推荐", "发闲置", "消息\n商品码"]:
            if marker in body_text:
                body_text = body_text.split(marker, 1)[0]
                break

        return body_text.strip()

    def _parse_price(self, text: str) -> float:
        """解析价格文本。"""
        if not text:
            return 0.0

        match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
        if not match:
            return 0.0

        try:
            return float(match.group(1))
        except ValueError:
            return 0.0

    def _extract_metric(self, text: str, patterns: List[str]) -> int:
        """从文本窗口中按正则提取单个指标。"""
        if not text:
            return 0

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._parse_number(match.group(0))

        return 0

    def _extract_title(self, detail_text: str) -> str:
        """从详情文本窗口提取商品标题。"""
        if not detail_text:
            return ""

        lines = [line.strip() for line in detail_text.splitlines() if line.strip()]
        if not lines:
            return ""

        metadata_prefixes = [
            "搜索",
            "网页版发闲置功能又升级啦",
            "闲鱼号",
            "担保交易",
            "举报",
            "下架",
            "删除",
            "卖出",
            "来闲鱼",
        ]

        for index, line in enumerate(lines):
            if "浏览" not in line:
                continue

            for candidate in lines[index + 1:index + 6]:
                if candidate == "¥":
                    continue
                if any(prefix in candidate for prefix in metadata_prefixes):
                    continue
                if re.search(r"\d+\s*人想要", candidate):
                    continue
                if re.fullmatch(r"[\d.]+", candidate):
                    continue
                return candidate

        # 回退：选择第一条看起来像商品标题的长文本
        for line in lines:
            if any(prefix in line for prefix in metadata_prefixes):
                continue
            if re.search(r"\d+\s*(人想要|浏览)", line):
                continue
            if re.fullmatch(r"[\d.]+", line):
                continue
            if len(line) >= 4:
                return line

        return ""
    
    async def get_sales_stats(
        self,
        days: int = 7,
        item_ids: List[str] = None
    ) -> SalesStats:
        """
        获取销售统计
        
        Args:
            days: 统计天数
            item_ids: 商品 ID 列表（可选）
            
        Returns:
            销售统计数据
        """
        logger.info(f"获取最近 {days} 天的销售统计")
        
        stats = SalesStats()
        stats.end_date = datetime.now()
        stats.start_date = stats.end_date - timedelta(days=days)
        
        try:
            # 打开卖家中心
            seller_url = "https://www.goofish.com/seller center"
            await self.browser.page.goto(seller_url, wait_until="networkidle", timeout=30000)
            await self.browser.page.wait_for_timeout(3000)
            
            # 解析销售数据
            # TODO: 实现具体的解析逻辑
            stats.total_sales = 0.0
            stats.total_orders = 0
            stats.total_items = len(item_ids) if item_ids else 0
            
            # 计算日均数据
            if days > 0:
                stats.daily_sales = stats.total_sales / days
                stats.daily_orders = stats.total_orders / days
            
            logger.info(f"销售统计：总额 ¥{stats.total_sales:.2f}, 订单 {stats.total_orders}")
            
        except Exception as e:
            logger.error(f"获取销售统计失败：{e}")
        
        return stats
    
    async def get_traffic_stats(self, days: int = 7) -> TrafficStats:
        """
        获取流量统计
        
        Args:
            days: 统计天数
            
        Returns:
            流量统计数据
        """
        logger.info(f"获取最近 {days} 天的流量统计")
        
        stats = TrafficStats()
        
        try:
            # 打开流量分析页面
            traffic_url = "https://www.goofish.com/traffic"
            await self.browser.page.goto(traffic_url, wait_until="networkidle", timeout=30000)
            await self.browser.page.wait_for_timeout(3000)
            
            # 解析流量数据
            # TODO: 实现具体的解析逻辑
            stats.total_views = 0
            stats.total_visitors = 0
            stats.avg_views_per_day = stats.total_views / days if days > 0 else 0
            
            # 流量来源（示例数据）
            stats.traffic_sources = {
                "search": 0,      # 搜索
                "recommend": 0,   # 推荐
                "direct": 0,      # 直接访问
                "other": 0,       # 其他
            }
            
            # 时段分布（示例数据）
            stats.hourly_distribution = {hour: 0 for hour in range(24)}
            
            logger.info(f"流量统计：总浏览 {stats.total_views}, 访客 {stats.total_visitors}")
            
        except Exception as e:
            logger.error(f"获取流量统计失败：{e}")
        
        return stats
    
    async def get_top_items(self, limit: int = 10, sort_by: str = "sales") -> List[ItemStats]:
        """
        获取热门商品排行
        
        Args:
            limit: 返回数量
            sort_by: 排序方式 (sales, views, wants)
            
        Returns:
            商品列表
        """
        logger.info(f"获取热门商品排行 (sort_by={sort_by}, limit={limit})")
        
        top_items = []
        
        try:
            # TODO: 实现获取商品列表并排序
            # 这里返回示例数据
            for i in range(limit):
                item = ItemStats(
                    item_id=f"item_{i}",
                    title=f"热门商品 {i+1}",
                    price=100.0 * (i + 1),
                    view_count=1000 * (limit - i),
                    want_count=100 * (limit - i),
                    order_count=10 * (limit - i),
                )
                item.calculate_rates()
                top_items.append(item)
            
            logger.info(f"找到 {len(top_items)} 个热门商品")
            
        except Exception as e:
            logger.error(f"获取热门商品失败：{e}")
        
        return top_items
    
    async def analyze_competitors(self, item_ids: List[str]) -> Dict[str, Any]:
        """
        竞品分析
        
        Args:
            item_ids: 竞品 ID 列表
            
        Returns:
            分析结果
        """
        logger.info(f"分析 {len(item_ids)} 个竞品")
        
        result = {
            "total_items": len(item_ids),
            "avg_price": 0.0,
            "price_range": {"min": 0, "max": 0},
            "avg_views": 0,
            "avg_wants": 0,
            "items": [],
        }
        
        try:
            prices = []
            views = []
            wants = []
            
            for item_id in item_ids:
                stats = await self.get_item_stats(item_id)
                if stats:
                    prices.append(stats.price)
                    views.append(stats.view_count)
                    wants.append(stats.want_count)
                    result["items"].append(stats.to_dict())
            
            if prices:
                result["avg_price"] = sum(prices) / len(prices)
                result["price_range"] = {"min": min(prices), "max": max(prices)}
            
            if views:
                result["avg_views"] = sum(views) / len(views)
            
            if wants:
                result["avg_wants"] = sum(wants) / len(wants)
            
            logger.info(f"竞品分析完成：平均价格 ¥{result['avg_price']:.2f}")
            
        except Exception as e:
            logger.error(f"竞品分析失败：{e}")
        
        return result
    
    async def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """
        生成综合分析报告
        
        Args:
            days: 统计天数
            
        Returns:
            报告数据
        """
        logger.info(f"生成最近 {days} 天的综合分析报告")
        
        report = {
            "period": {
                "days": days,
                "start": (datetime.now() - timedelta(days=days)).isoformat(),
                "end": datetime.now().isoformat(),
            },
            "sales": None,
            "traffic": None,
            "top_items": None,
            "summary": "",
        }
        
        try:
            # 获取销售统计
            sales_stats = await self.get_sales_stats(days=days)
            report["sales"] = sales_stats.to_dict()
            
            # 获取流量统计
            traffic_stats = await self.get_traffic_stats(days=days)
            report["traffic"] = traffic_stats.to_dict()
            
            # 获取热门商品
            top_items = await self.get_top_items(limit=10)
            report["top_items"] = [item.to_dict() for item in top_items]
            
            # 生成总结
            report["summary"] = self._generate_summary(sales_stats, traffic_stats, top_items)
            
            logger.info("综合分析报告生成完成")
            
        except Exception as e:
            logger.error(f"生成报告失败：{e}")
        
        return report
    
    def _generate_summary(
        self,
        sales: SalesStats,
        traffic: TrafficStats,
        top_items: List[ItemStats]
    ) -> str:
        """生成报告总结"""
        summary_parts = []
        
        # 销售总结
        if sales.total_sales > 0:
            summary_parts.append(f"总销售额 ¥{sales.total_sales:.2f}")
            summary_parts.append(f"订单 {sales.total_orders} 个")
        
        # 流量总结
        if traffic.total_views > 0:
            summary_parts.append(f"总浏览 {traffic.total_views} 次")
            summary_parts.append(f"访客 {traffic.total_visitors} 人")
        
        # 商品总结
        if top_items:
            best_item = top_items[0]
            summary_parts.append(f"最畅销商品：{best_item.title}")
        
        return "，".join(summary_parts) if summary_parts else "暂无数据"
