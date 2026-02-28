"""
发布模块

实现闲鱼商品发布、编辑、下架等功能
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from loguru import logger

from .browser import XianyuBrowser


@dataclass
class PublishParams:
    """发布商品参数"""
    title: str  # 标题（最多 20 字）
    description: str  # 描述（最多 1000 字）
    price: float  # 价格
    images: List[str] = field(default_factory=list)  # 图片路径列表
    category: str = ""  # 分类
    location: str = ""  # 地区
    condition: str = "全新"  # 新旧程度
    delivery: str = "包邮"  # 配送方式
    is_original: bool = False  # 是否原创
    tags: List[str] = field(default_factory=list)  # 标签
    
    def validate(self) -> tuple[bool, str]:
        """
        验证参数
        
        Returns:
            (是否有效，错误信息)
        """
        # 标题验证
        if not self.title:
            return False, "标题不能为空"
        if len(self.title) > 20:
            return False, "标题最多 20 个字"
        if len(self.title) < 5:
            return False, "标题至少 5 个字"
        
        # 描述验证
        if not self.description:
            return False, "描述不能为空"
        if len(self.description) > 1000:
            return False, "描述最多 1000 字"
        if len(self.description) < 20:
            return False, "描述至少 20 个字"
        
        # 价格验证
        if self.price <= 0:
            return False, "价格必须大于 0"
        if self.price > 1000000:
            return False, "价格过高"
        
        # 图片验证
        if not self.images or len(self.images) == 0:
            return False, "至少需要 1 张图片"
        if len(self.images) > 9:
            return False, "最多 9 张图片"
        
        # 检查图片文件是否存在
        for img_path in self.images:
            img_file = Path(img_path)
            if not img_file.exists():
                return False, f"图片文件不存在：{img_path}"
            if not img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                return False, f"不支持的图片格式：{img_path}"
        
        # 违禁词检查
        banned_words = ["微信", "QQ", "电话", "转账", "定金", "订金"]
        for word in banned_words:
            if word in self.title or word in self.description:
                return False, f"标题或描述包含违禁词：{word}"
        
        return True, ""
    
    def optimize_title(self) -> str:
        """
        优化标题（添加 emoji 和热门标签）
        
        Returns:
            优化后的标题
        """
        # 如果标题已经很好，直接返回
        if len(self.title) >= 15:
            return self.title
        
        # 添加 emoji
        emojis = ["🔥", "✨", "💯", "🎉", "⭐"]
        import random
        emoji = random.choice(emojis)
        
        # 添加热门标签
        tags = ["包邮", "全新", "急出"]
        tag = random.choice(tags)
        
        optimized = f"{emoji} {self.title} {tag}"
        
        # 确保不超过 20 字
        if len(optimized) > 20:
            optimized = optimized[:19]
        
        return optimized
    
    def generate_description(self) -> str:
        """
        生成优化描述
        
        Returns:
            优化后的描述
        """
        if len(self.description) >= 100:
            return self.description
        
        # 添加商品详情模板
        template = f"""{self.description}

【商品详情】
✅ 新旧程度：{self.condition}
✅ 配送方式：{self.delivery}
✅ 所在地区：{self.location or '上海'}

【购买须知】
📦 包邮发货，请放心购买
💬 有任何问题欢迎咨询
🤝 支持闲鱼担保交易
"""
        return template.strip()


class XianyuPublish:
    """闲鱼发布类"""
    
    def __init__(self, browser: XianyuBrowser):
        """
        初始化发布模块
        
        Args:
            browser: 浏览器实例
        """
        self.browser = browser
        logger.info("发布模块已初始化")
    
    async def publish(self, params: PublishParams) -> tuple[bool, str]:
        """
        发布商品
        
        Args:
            params: 发布参数
            
        Returns:
            (是否成功，商品 ID 或错误信息)
        """
        logger.info(f"开始发布商品：{params.title}")
        
        if not self.browser.page:
            return False, "浏览器未启动"
        
        # 验证参数
        is_valid, error_msg = params.validate()
        if not is_valid:
            logger.error(f"参数验证失败：{error_msg}")
            return False, error_msg
        
        try:
            # 1. 打开发布页面
            publish_url = "https://www.goofish.com/publish"
            logger.info(f"打开发布页面：{publish_url}")
            await self.browser.page.goto(publish_url, wait_until="networkidle", timeout=30000)
            await self.browser.page.wait_for_timeout(3000)
            
            # 2. 上传图片
            logger.info("上传图片...")
            await self._upload_images(params.images)
            
            # 3. 填写标题
            logger.info("填写标题...")
            await self._fill_title(params.title)
            
            # 4. 填写描述
            logger.info("填写描述...")
            await self._fill_description(params.description)
            
            # 5. 填写价格
            logger.info("填写价格...")
            await self._fill_price(params.price)
            
            # 6. 选择分类
            if params.category:
                logger.info("选择分类...")
                await self._select_category(params.category)
            
            # 7. 选择地区
            if params.location:
                logger.info("选择地区...")
                await self._select_location(params.location)
            
            # 8. 选择新旧程度
            logger.info("选择新旧程度...")
            await self._select_condition(params.condition)
            
            # 9. 选择配送方式
            logger.info("选择配送方式...")
            await self._select_delivery(params.delivery)
            
            # 10. 添加标签
            if params.tags:
                logger.info("添加标签...")
                await self._add_tags(params.tags)
            
            # 11. 声明原创（如果需要）
            if params.is_original:
                logger.info("声明原创...")
                await self._mark_original()
            
            # 12. 提交发布
            logger.info("提交发布...")
            success, result = await self._submit_publish()
            
            if success:
                logger.success(f"发布成功！商品 ID: {result}")
                return True, result
            else:
                logger.error(f"发布失败：{result}")
                return False, result
            
        except Exception as e:
            logger.error(f"发布过程出错：{e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    async def _upload_images(self, image_paths: List[str]) -> None:
        """上传图片"""
        if not self.browser.page:
            return
        
        # 找到上传按钮
        upload_button = await self.browser.page.query_selector(
            'input[type="file"], .upload-button, .add-image'
        )
        
        if upload_button:
            # 设置多个文件
            image_files = [str(Path(p).absolute()) for p in image_paths if Path(p).exists()]
            if image_files:
                await upload_button.set_input_files(image_files)
                logger.info(f"已上传 {len(image_files)} 张图片")
                await self.browser.page.wait_for_timeout(2000)  # 等待上传完成
    
    async def _fill_title(self, title: str) -> None:
        """填写标题"""
        if not self.browser.page:
            return
        
        title_input = await self.browser.page.query_selector(
            'input[placeholder*="标题"], input[name="title"], .title-input'
        )
        
        if title_input:
            await title_input.fill(title)
    
    async def _fill_description(self, description: str) -> None:
        """填写描述"""
        if not self.browser.page:
            return
        
        desc_input = await self.browser.page.query_selector(
            'textarea[placeholder*="描述"], textarea[name="description"], .description-input'
        )
        
        if desc_input:
            await desc_input.fill(description)
    
    async def _fill_price(self, price: float) -> None:
        """填写价格"""
        if not self.browser.page:
            return
        
        price_input = await self.browser.page.query_selector(
            'input[placeholder*="价格"], input[name="price"], .price-input'
        )
        
        if price_input:
            await price_input.fill(str(price))
    
    async def _select_category(self, category: str) -> None:
        """选择分类"""
        if not self.browser.page:
            return
        
        # TODO: 实现分类选择逻辑
        logger.debug(f"选择分类：{category}")
    
    async def _select_location(self, location: str) -> None:
        """选择地区"""
        if not self.browser.page:
            return
        
        # TODO: 实现地区选择逻辑
        logger.debug(f"选择地区：{location}")
    
    async def _select_condition(self, condition: str) -> None:
        """选择新旧程度"""
        if not self.browser.page:
            return
        
        # TODO: 实现新旧程度选择逻辑
        logger.debug(f"选择新旧程度：{condition}")
    
    async def _select_delivery(self, delivery: str) -> None:
        """选择配送方式"""
        if not self.browser.page:
            return
        
        # TODO: 实现配送方式选择逻辑
        logger.debug(f"选择配送方式：{delivery}")
    
    async def _add_tags(self, tags: List[str]) -> None:
        """添加标签"""
        if not self.browser.page:
            return
        
        # TODO: 实现标签添加逻辑
        logger.debug(f"添加标签：{tags}")
    
    async def _mark_original(self) -> None:
        """声明原创"""
        if not self.browser.page:
            return
        
        # TODO: 实现原创声明逻辑
        logger.debug("声明原创")
    
    async def _submit_publish(self) -> tuple[bool, str]:
        """
        提交发布
        
        Returns:
            (是否成功，商品 ID 或错误信息)
        """
        if not self.browser.page:
            return False, "浏览器未启动"
        
        try:
            # 找到发布按钮
            submit_button = await self.browser.page.query_selector(
                'button[type="submit"], .submit-button, button:has-text("发布")'
            )
            
            if submit_button:
                # 点击发布
                await submit_button.click()
                await self.browser.page.wait_for_timeout(3000)
                
                # 检查发布结果
                current_url = self.browser.page.url
                
                # 如果跳转到商品详情页，说明发布成功
                if '/detail/' in current_url:
                    # 提取商品 ID
                    item_id = current_url.split('/detail/')[-1].split('?')[0]
                    return True, item_id
                
                # 检查是否有错误提示
                error_el = await self.browser.page.query_selector('.error-message, .toast-error')
                if error_el:
                    error_text = await error_el.inner_text()
                    return False, error_text
                
                # 默认认为成功
                return True, "published"
            
            return False, "未找到发布按钮"
            
        except Exception as e:
            return False, str(e)
    
    async def edit_item(self, item_id: str, updates: Dict[str, Any]) -> tuple[bool, str]:
        """
        编辑商品
        
        Args:
            item_id: 商品 ID
            updates: 更新内容
            
        Returns:
            (是否成功，消息)
        """
        logger.info(f"编辑商品 {item_id}")
        # TODO: 实现编辑逻辑
        return False, "功能开发中"
    
    async def delete_item(self, item_id: str) -> tuple[bool, str]:
        """
        下架商品
        
        Args:
            item_id: 商品 ID
            
        Returns:
            (是否成功，消息)
        """
        logger.info(f"下架商品 {item_id}")
        # TODO: 实现下架逻辑
        return False, "功能开发中"
    
    async def batch_publish(self, items: List[PublishParams]) -> List[tuple[bool, str]]:
        """
        批量发布
        
        Args:
            items: 商品列表
            
        Returns:
            发布结果列表
        """
        logger.info(f"批量发布 {len(items)} 个商品")
        
        results = []
        for i, item in enumerate(items):
            logger.info(f"发布第 {i+1}/{len(items)} 个商品")
            success, result = await self.publish(item)
            results.append((success, result))
            
            # 间隔等待，避免触发风控
            if i < len(items) - 1:
                await self.browser.page.wait_for_timeout(30000)  # 30 秒间隔
        
        return results
