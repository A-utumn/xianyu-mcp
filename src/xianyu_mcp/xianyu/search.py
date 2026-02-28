"""
搜索模块

实现闲鱼商品搜索、筛选、竞品监控等功能
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlencode
from loguru import logger

from .browser import XianyuBrowser


@dataclass
class XianyuItem:
    """商品数据结构"""
    id: str = ""
    title: str = ""
    price: float = 0.0
    original_price: float = 0.0
    image_url: str = ""
    seller_name: str = ""
    seller_id: str = ""
    location: str = ""
    sales_count: int = 0
    want_count: int = 0  # 想要人数
    url: str = ""
    xsec_token: str = ""  # 用于获取详情
    description: str = ""
    condition: str = ""  # 新旧程度
    category: str = ""
    publish_time: Optional[datetime] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "location": self.location,
            "seller_name": self.seller_name,
            "url": self.url,
            "image_url": self.image_url,
            "want_count": self.want_count,
        }


class XianyuSearch:
    """闲鱼搜索类"""
    
    def __init__(self, browser: XianyuBrowser):
        """
        初始化搜索模块
        
        Args:
            browser: 浏览器实例
        """
        self.browser = browser
        logger.info("搜索模块已初始化")
    
    async def search(
        self,
        keyword: str,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        location: Optional[str] = None,
        sort_by: str = "default",
        limit: int = 20,
        retry_count: int = 3,
        filter_keywords: Optional[List[str]] = None,
        exact_match: bool = False
    ) -> List[XianyuItem]:
        """
        搜索商品（增强版 - 带关键词过滤和精确匹配）
        
        Args:
            keyword: 搜索关键词
            price_min: 最低价格
            price_max: 最高价格
            location: 地区筛选
            sort_by: 排序方式 (default, price_asc, price_desc, sales)
            limit: 返回数量限制
            retry_count: 失败重试次数
            filter_keywords: 过滤关键词（标题必须包含这些词）
            exact_match: 是否精确匹配关键词
            
        Returns:
            商品列表
        """
        logger.info(f"开始搜索：{keyword}, 限制：{limit}条")
        
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")
        
        # 参数验证
        if not keyword or len(keyword) > 50:
            logger.error("关键词长度必须在 1-50 个字符之间")
            return []
        
        # 重试机制
        for attempt in range(retry_count):
            try:
                logger.debug(f"搜索尝试 {attempt + 1}/{retry_count}")
                
                # 构建搜索 URL
                base_url = "https://www.goofish.com/search"
                query_params: Dict[str, Any] = {"q": keyword}
                
                # 添加价格筛选
                if price_min is not None and price_max is not None:
                    query_params["price"] = f"{price_min}-{price_max}"
                elif price_min is not None:
                    query_params["price"] = f"{price_min}-"
                elif price_max is not None:
                    query_params["price"] = f"-{price_max}"
                
                # 添加地区筛选
                if location:
                    query_params["location"] = location
                
                # 添加排序
                sort_map = {
                    "default": None,
                    "price_asc": "priceAsc",
                    "price_desc": "priceDesc",
                    "sales": "sales",
                }
                sort_value = sort_map.get(sort_by)
                if sort_value:
                    query_params["sort"] = sort_value
                
                # 打开搜索页面
                search_url = f"{base_url}?{urlencode(query_params)}"
                logger.info(f"搜索 URL: {search_url}")
                
                # 访问页面（带重试）
                try:
                    await self.browser.page.goto(search_url, wait_until="networkidle", timeout=30000)
                except Exception as nav_error:
                    logger.warning(f"导航失败：{nav_error}，尝试等待页面加载")
                    await self.browser.page.wait_for_timeout(5000)
                
                # 等待内容加载（更长时间）
                await self.browser.page.wait_for_timeout(5000 + (attempt * 2000))
                
                # 尝试等待搜索结果出现
                try:
                    await self.browser.page.wait_for_selector(
                        ".feeds-list-container--UkIMBPNk a[href*='/item?id='], [class*='feeds-list-container'] a[href*='/item?id='], a[href*='/item?id=']",
                        timeout=10000
                    )
                    logger.debug("搜索结果已加载")
                except:
                    logger.warning("等待搜索结果超时，继续解析")
                
                # 检查是否有搜索结果
                has_results = await self._check_has_results()
                if not has_results:
                    logger.warning(f"未找到搜索结果，尝试重试 {attempt + 1}/{retry_count}")
                    if attempt < retry_count - 1:
                        await self.browser.page.reload(wait_until="networkidle")
                        await self.browser.page.wait_for_timeout(3000)
                        continue
                
                # 解析搜索结果
                items = await self._parse_search_results(limit)
                
                if len(items) == 0 and attempt < retry_count - 1:
                    logger.warning(f"解析结果为空，尝试重试 {attempt + 1}/{retry_count}")
                    continue
                
                # 关键词过滤（提高准确性）
                if filter_keywords or exact_match:
                    filtered_items = self._filter_items(items, keyword, filter_keywords, exact_match)
                    logger.info(f"过滤后剩余 {len(filtered_items)} 个商品")
                    items = filtered_items
                
                logger.info(f"搜索完成，找到 {len(items)} 个商品")
                return items
                
            except Exception as e:
                logger.error(f"搜索失败 (尝试 {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    wait_time = (attempt + 1) * 2000
                    logger.info(f"等待 {wait_time}ms 后重试...")
                    await self.browser.page.wait_for_timeout(wait_time)
                else:
                    import traceback
                    traceback.print_exc()
                    return []
        
        return []
    
    def _filter_items(
        self,
        items: List[XianyuItem],
        keyword: str,
        filter_keywords: Optional[List[str]] = None,
        exact_match: bool = False
    ) -> List[XianyuItem]:
        """
        过滤商品（提高搜索准确性）
        
        Args:
            items: 商品列表
            keyword: 主关键词
            filter_keywords: 过滤关键词列表
            exact_match: 是否精确匹配
            
        Returns:
            过滤后的商品列表
        """
        filtered = []
        
        # 中文不需要转小写，直接使用原关键词
        # 但为了兼容性，同时准备小写版本（用于英文）
        keyword_check = keyword.lower()
        filter_keywords_check = [kw.lower() for kw in filter_keywords] if filter_keywords else []
        
        for item in items:
            if not item.title:
                continue
            
            # 标题也准备两个版本
            title_check = item.title.lower()
            title_original = item.title
            
            # 精确匹配模式
            if exact_match:
                # 检查原始标题或小写标题是否包含关键词
                if keyword in title_original or keyword_check in title_check:
                    filtered.append(item)
                continue
            
            # 过滤关键词模式
            if filter_keywords:
                # 标题必须包含至少一个过滤关键词（更宽松）
                match = False
                for kw in filter_keywords:
                    if kw in title_original or kw.lower() in title_check:
                        match = True
                        break
                if match:
                    filtered.append(item)
                continue
            
            # 默认模式：包含主关键词即可
            if keyword in title_original or keyword_check in title_check:
                filtered.append(item)
        
        return filtered
    
    async def _check_has_results(self) -> bool:
        """
        检查是否有搜索结果
        
        Returns:
            bool: 是否有结果
        """
        try:
            # 检查是否有商品列表
            result_selector = (
                ".feeds-list-container--UkIMBPNk a[href*='/item?id='], "
                "[class*='feeds-list-container'] a[href*='/item?id='], "
                "a[href*='/item?id=']"
            )
            await self.browser.page.wait_for_selector(result_selector, timeout=5000)
            return True
        except:
            # 检查是否有"未找到相关商品"提示
            no_result = await self.browser.page.query_selector(".no-result, .empty-state")
            if no_result:
                logger.info("未找到相关商品")
                return False
            return True
    
    async def _parse_search_results(self, limit: int = 20) -> List[XianyuItem]:
        """
        解析搜索结果（增强版 - 确保选择搜索结果而非推荐）
        
        Args:
            limit: 最大返回数量
            
        Returns:
            商品列表
        """
        items = []
        
        try:
            # 优先锁定真实商品流容器，避免抓到搜索建议和 SEO 隐藏链接
            container_selectors = [
                ".feeds-list-container--UkIMBPNk",
                "[class*='feeds-list-container']",
                "[class*='search-result']",
                "[class*='search-list']",
                "[class*='goods-list']",
                "[class*='item-list']",
            ]
            
            container = None
            for selector in container_selectors:
                try:
                    container = await self.browser.page.query_selector(selector)
                    if container:
                        logger.debug(f"找到搜索容器：{selector}")
                        break
                except:
                    continue
            
            # 多种选择器尝试（在容器内查找）
            selectors = [
                "a[href*='/item?id=']",
                "a[class*='feeds-item-wrap']",
                "[class*='feeds-item-wrap']",
                "[class*='card-container']",
                "[class*='goods-item']",
                "[class*='item-card']",
            ]
            
            cards = []
            for selector in selectors:
                try:
                    if container:
                        cards = await container.query_selector_all(selector)
                    else:
                        cards = await self.browser.page.query_selector_all(selector)
                    
                    if cards:
                        logger.debug(f"使用选择器 '{selector}' 找到 {len(cards)} 个商品")
                        break
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 失败：{str(e)[:50]}")
                    continue
            
            # 如果还是没有找到，再做一次全页兜底，但仍然只接受商品详情链接
            if not cards:
                cards = await self.browser.page.query_selector_all(
                    "a[href*='/item?id='], a[href*='/detail/'], a[href*='/goods/']"
                )
                if cards:
                    logger.debug(f"使用备用方案（商品链接）找到 {len(cards)} 个商品")
            
            logger.debug(f"总共找到 {len(cards)} 个商品卡片")
            
            for i, card in enumerate(cards[:limit]):
                try:
                    is_visible = await card.is_visible()
                    if not is_visible:
                        continue
                    
                    item = await self._parse_single_item(card)
                    if item and item.title:
                        items.append(item)
                        logger.debug(f"解析商品 {i+1}: {item.title[:30]}...")
                except Exception as e:
                    logger.debug(f"解析商品失败：{e}")
                    continue
            
        except Exception as e:
            logger.error(f"解析搜索结果失败：{e}")
        
        return items
    
    async def _parse_single_item(self, card) -> Optional[XianyuItem]:
        """
        解析单个商品卡片（增强版 - 支持多种选择器 + 详细数据提取）
        
        Args:
            card: 商品卡片元素
            
        Returns:
            商品对象
        """
        try:
            item = XianyuItem()
            
            # ========== 1. 提取标题 ==========
            # 尝试多种选择器
            title_selectors = [
                "[class*='main-title']",
                "[class*='row1-wrap-title']",
                "[class*='title']",
                "[class*='name']",
                "h3",
                "h4",
                "div[class*='card'] div:first-child",
            ]
            
            for selector in title_selectors:
                title_el = await card.query_selector(selector)
                if title_el:
                    item.title = (await title_el.inner_text()).strip()[:100]
                    break
            
            if not item.title:
                title_attr = await card.get_attribute("title")
                if title_attr:
                    item.title = title_attr.strip()[:100]
            
            # 备用方案：获取整个卡片的文本（排除价格和按钮）
            if not item.title or len(item.title) < 2:
                all_text = await card.inner_text()
                lines = all_text.split('\n')
                if lines:
                    item.title = lines[0].strip()[:100]
            
            # 如果标题为空，跳过
            if not item.title or len(item.title) < 2:
                return None
            
            # ========== 2. 提取价格 ==========
            price_selectors = [
                "[class*='price-wrap']",
                "[class*='price']",
                "span[class*='money']",
                "[class*='money']",
                "div[class*='price']",
            ]
            
            for selector in price_selectors:
                price_el = await card.query_selector(selector)
                if price_el:
                    price_text = await price_el.inner_text()
                    import re
                    # 匹配价格（支持￥、¥、元等符号）
                    price_match = re.search(r'[￥¥]?([\d.]+)', price_text)
                    if price_match:
                        try:
                            item.price = float(price_match.group(1))
                            break
                        except:
                            pass
            
            # ========== 3. 提取图片 ==========
            img_el = await card.query_selector("img")
            if img_el:
                # 尝试获取高分辨率图片
                for attr in ['src', 'data-src', 'original-src']:
                    img_url = await img_el.get_attribute(attr)
                    if img_url and img_url.startswith('http'):
                        item.image_url = img_url
                        break
            
            # ========== 4. 提取卖家信息 ==========
            seller_selectors = [
                "[class*='seller']",
                "[class*='user']",
                "[class*='nick']",
                "div[class*='user-info']",
            ]
            
            for selector in seller_selectors:
                seller_el = await card.query_selector(selector)
                if seller_el:
                    item.seller_name = (await seller_el.inner_text()).strip()[:50]
                    break
            
            # ========== 5. 提取地区 ==========
            location_selectors = [
                "[class*='seller-text']",
                "[class*='location']",
                "[class*='area']",
                "[class*='city']",
                "div[class*='region']",
            ]
            
            for selector in location_selectors:
                location_el = await card.query_selector(selector)
                if location_el:
                    item.location = (await location_el.inner_text()).strip()[:50]
                    break
            
            # ========== 6. 提取想要人数 ==========
            want_selectors = [
                "[class*='price-desc']",
                "[class*='want']",
                "[class*='like']",
                "[class*='collect']",
                "span[class*='count']",
            ]
            
            for selector in want_selectors:
                want_el = await card.query_selector(selector)
                if want_el:
                    want_text = await want_el.inner_text()
                    import re
                    want_match = re.search(r'([\d.]+)', want_text)
                    if want_match:
                        try:
                            want_num = float(want_match.group(1))
                            # 处理"万"单位
                            if '万' in want_text:
                                want_num *= 10000
                            item.want_count = int(want_num)
                            break
                        except:
                            pass
            
            # ========== 7. 提取商品链接和 ID ==========
            link_el = card
            tag_name = await card.evaluate("el => el.tagName")
            if tag_name != "A":
                link_el = await card.query_selector("a[href]")
            if link_el:
                href = await link_el.get_attribute("href") or ""
                
                # 检查是否是商品链接
                if any(pattern in href for pattern in ['/detail/', '/item?id=', '/goods/']):
                    item.url = href
                    
                    # 提取商品 ID
                    import re
                    # 尝试多种 ID 提取模式
                    id_patterns = [
                        r'/detail/(\w+)',
                        r'[?&]id=(\w+)',
                        r'/goods/(\w+)',
                        r'id=(\w+)',
                    ]
                    
                    for pattern in id_patterns:
                        match = re.search(pattern, href)
                        if match:
                            item.id = match.group(1)
                            break
                    
                    # 提取 xsec_token
                    token_match = re.search(r'xsec_token=([^&]+)', href)
                    if token_match:
                        item.xsec_token = token_match.group(1)
            
            # ========== 8. 提取其他信息 ==========
            # 提取分类
            category_el = await card.query_selector("[class*='category'], [class*='tag']")
            if category_el:
                item.category = (await category_el.inner_text()).strip()[:50]
            
            # 提取描述/副标题
            desc_el = await card.query_selector("[class*='desc'], [class*='subtitle']")
            if desc_el:
                item.description = (await desc_el.inner_text()).strip()[:200]
            
            # 提取新旧程度
            condition_el = await card.query_selector("[class*='condition'], [class*='new']")
            if condition_el:
                item.condition = (await condition_el.inner_text()).strip()[:20]
            
            return item
            
        except Exception as e:
            logger.debug(f"解析单个商品失败：{e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_competitor_prices(self, item_ids: List[str]) -> Dict[str, Dict]:
        """
        获取竞品价格
        
        Args:
            item_ids: 商品 ID 列表
            
        Returns:
            价格信息字典
        """
        logger.info(f"获取竞品价格：{len(item_ids)}个商品")
        
        result = {}
        for item_id in item_ids:
            try:
                # TODO: 实现获取商品详情和价格
                result[item_id] = {
                    "price": 0,
                    "status": "available",
                }
            except Exception as e:
                logger.error(f"获取竞品价格失败 {item_id}: {e}")
                result[item_id] = {
                    "error": str(e),
                }
        
        return result
    
    async def get_hot_items(self, category: str = "", limit: int = 20) -> List[XianyuItem]:
        """
        获取热门商品
        
        Args:
            category: 分类
            limit: 数量限制
            
        Returns:
            热门商品列表
        """
        logger.info(f"获取热门商品，分类：{category or '全部'}")
        
        # 打开闲鱼首页获取推荐
        await self.browser.goto_xianyu()
        await self.browser.page.wait_for_timeout(3000)
        
        # TODO: 解析首页推荐商品
        return []
