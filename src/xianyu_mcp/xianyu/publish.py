"""
发布模块

实现闲鱼商品发布、编辑、下架等功能
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import re
from loguru import logger

from .browser import XianyuBrowser
from .login import XianyuLogin


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
[商品状态] {self.condition}
[配送方式] {self.delivery}
[所在地区] {self.location or '上海'}

【购买须知】
[发货说明] 包邮发货，请放心购买
[沟通说明] 有任何问题欢迎咨询
[交易方式] 支持闲鱼担保交易
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
        self._cookies_loaded = False
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
            await self._prepare_publish_form(params)
            
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

    async def precheck_publish(self, params: PublishParams) -> Dict[str, Any]:
        """
        试填发布表单并返回可发布性检查结果，不真正提交。

        Args:
            params: 发布参数

        Returns:
            预检查结果
        """
        logger.info(f"预检查发布商品：{params.title}")

        if not self.browser.page:
            return {
                "success": False,
                "ready_to_submit": False,
                "message": "浏览器未启动",
                "blockers": ["浏览器未启动"],
            }

        is_valid, error_msg = params.validate()
        if not is_valid:
            return {
                "success": False,
                "ready_to_submit": False,
                "message": error_msg,
                "blockers": [error_msg],
            }

        try:
            await self._prepare_publish_form(params)
            state = await self._inspect_publish_state()
            state["success"] = True
            return state
        except Exception as e:
            logger.error(f"预检查发布失败：{e}")
            return {
                "success": False,
                "ready_to_submit": False,
                "message": str(e),
                "blockers": [str(e)],
            }

    async def _prepare_publish_form(self, params: PublishParams) -> None:
        """按当前网页结构填充发布表单。"""
        await self._ensure_publish_page()

        logger.info("上传图片...")
        await self._upload_images(params.images)

        logger.info("填写标题...")
        await self._fill_title(params.title)

        logger.info("填写描述...")
        await self._fill_description(params.generate_description(), title=params.title)

        logger.info("填写价格...")
        await self._fill_price(params.price)

        if params.category:
            logger.info("选择分类...")
            await self._select_category(params.category)

        if params.location:
            logger.info("选择地区...")
            await self._select_location(params.location)

        logger.info("选择新旧程度...")
        await self._select_condition(params.condition)

        logger.info("选择配送方式...")
        await self._select_delivery(params.delivery)

        if params.tags:
            logger.info("添加标签...")
            await self._add_tags(params.tags)

        if params.is_original:
            logger.info("声明原创...")
            await self._mark_original()

    async def _inspect_publish_state(self) -> Dict[str, Any]:
        """检查当前发布表单是否可提交。"""
        submit_button = await self._first_visible_locator([
            "button.publish-button--KBpTVopQ",
            "[class*='publish-button']",
            'button[type="submit"]',
            'button:has-text("发布")',
        ])
        button_class = await submit_button.get_attribute("class") if submit_button else ""
        button_text = (await submit_button.inner_text()).strip() if submit_button else ""
        blockers = await self._get_publish_blockers()
        blocker_flags = self._get_blocker_flags(blockers)
        ready_to_submit = bool(submit_button) and "disabled" not in (button_class or "").lower() and not blockers

        message = "可提交" if ready_to_submit else "当前表单仍不可提交"
        if blockers:
            message = "；".join(dict.fromkeys(blockers))

        return {
            "ready_to_submit": ready_to_submit,
            "message": message,
            "blockers": list(dict.fromkeys(blockers)),
            "button_text": button_text,
            "button_enabled": ready_to_submit if submit_button else False,
            "web_publish_supported": not blocker_flags["requires_app"],
            "requires_app": blocker_flags["requires_app"],
            "emoji_blocked": blocker_flags["emoji_blocked"],
            "category_unsupported": blocker_flags["category_unsupported"],
        }

    async def _ensure_cookies_loaded(self) -> None:
        """确保已尝试加载登录 Cookie。"""
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")

        if self._cookies_loaded:
            return

        try:
            login = XianyuLogin(self.browser)
            self._cookies_loaded = await login.load_cookies()
        except Exception as e:
            logger.debug(f"加载 Cookie 失败：{e}")
            self._cookies_loaded = False

    async def _ensure_publish_page(self) -> None:
        """确保当前位于已登录的发布页。"""
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")

        await self._ensure_cookies_loaded()

        publish_url = "https://www.goofish.com/publish"
        if "/publish" not in self.browser.page.url:
            logger.info(f"打开发布页面：{publish_url}")
            await self.browser.page.goto(publish_url, wait_until="networkidle", timeout=30000)
            await self.browser.page.wait_for_timeout(3000)

    async def _ensure_edit_page(self, item_id: str) -> None:
        """打开指定商品的编辑页。"""
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")

        await self._ensure_cookies_loaded()
        edit_url = f"https://www.goofish.com/publish?itemId={item_id}"
        logger.info(f"打开编辑页面：{edit_url}")
        await self.browser.page.goto(edit_url, wait_until="networkidle", timeout=30000)
        await self.browser.page.wait_for_timeout(3000)

        body_text = await self.browser.page.evaluate(
            "() => document.body && document.body.innerText ? document.body.innerText : ''"
        )
        if "商品不存在" in body_text or "宝贝不存在" in body_text:
            raise RuntimeError("未找到可编辑的商品")

    async def _ensure_item_page(self, item_id: str) -> None:
        """打开指定商品详情页。"""
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")

        await self._ensure_cookies_loaded()
        item_url = f"https://www.goofish.com/item?id={item_id}"
        logger.info(f"打开商品详情页：{item_url}")
        await self.browser.page.goto(item_url, wait_until="networkidle", timeout=30000)
        await self.browser.page.wait_for_timeout(3000)

    async def _first_visible_locator(self, selectors: List[str]):
        """返回第一个可见的定位器。"""
        if not self.browser.page:
            return None

        for selector in selectors:
            locator = self.browser.page.locator(selector)
            count = await locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if await candidate.is_visible():
                        return candidate
                except Exception:
                    continue

        return None

    async def _first_visible_text_locator(self, texts: List[str]):
        """返回第一个可见的文本定位器。"""
        if not self.browser.page:
            return None

        for text in texts:
            locator = self.browser.page.locator(f"text={text}")
            count = await locator.count()
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if await candidate.is_visible():
                        return candidate
                except Exception:
                    continue

        return None

    def _sanitize_publish_text(self, text: str) -> str:
        """移除网页发布不支持的字符（如 emoji）。"""
        # Goofish 网页发布会直接拦截 emoji，保守移除非 BMP 字符
        return re.sub(r"[\U00010000-\U0010FFFF]", "", text)

    def _get_blocker_flags(self, blockers: List[str]) -> Dict[str, bool]:
        """把已知阻塞文案映射成结构化状态。"""
        unique_blockers = set(blockers)
        return {
            "requires_app": "请使用闲鱼APP扫码继续发布" in unique_blockers,
            "emoji_blocked": "商品描述不能包含emoji" in unique_blockers,
            "category_unsupported": "网页版暂不支持发布此分类" in unique_blockers,
        }

    async def _click_locator(self, locator, wait_ms: int = 800) -> bool:
        """尽量稳定地点击元素，依次尝试常规点击、强制点击和 JS 点击。"""
        if not locator:
            return False

        click_attempts = (
            {"timeout": 3000},
            {"timeout": 3000, "force": True},
        )
        for kwargs in click_attempts:
            try:
                await locator.click(**kwargs)
                if self.browser.page:
                    await self.browser.page.wait_for_timeout(wait_ms)
                return True
            except Exception:
                continue

        try:
            await locator.evaluate("(node) => node.click()")
            if self.browser.page:
                await self.browser.page.wait_for_timeout(wait_ms)
            return True
        except Exception:
            return False

    async def _get_publish_blockers(self) -> List[str]:
        """收集当前发布页的显式阻塞提示。"""
        if not self.browser.page:
            return []

        body_text = await self.browser.page.evaluate(
            "() => document.body && document.body.innerText ? document.body.innerText : ''"
        )
        blockers = []

        known_messages = [
            "商品描述不能包含emoji",
            "网页版暂不支持发布此分类",
            "请使用闲鱼APP扫码继续发布",
        ]
        for message in known_messages:
            if message in body_text:
                blockers.append(message)

        return blockers

    async def _read_current_description(self) -> str:
        """读取当前编辑器中的描述文本。"""
        if not self.browser.page:
            return ""

        desc_input = await self._first_visible_locator([
            "div[contenteditable='true']",
            "[class*='editor']",
            'textarea[placeholder*="描述"]',
            'textarea[name="description"]',
            '.description-input',
        ])
        if not desc_input:
            return ""

        try:
            tag_name = await desc_input.evaluate("el => el.tagName")
            if tag_name == "DIV":
                return (
                    await desc_input.evaluate(
                        "(el) => (el.innerText || el.textContent || '').trim()"
                    )
                ).strip()
            value = await desc_input.input_value()
            return value.strip()
        except Exception:
            return ""

    async def _find_action_button(self, labels: List[str]):
        """在卖家操作区里寻找按钮。"""
        if not self.browser.page:
            return None

        containers = [
            self.browser.page.locator("[class*='sellerButtonGroup']"),
            self.browser.page.locator("[class*='buttons']"),
            self.browser.page.locator("[class*='item-main-container']"),
        ]
        for container in containers:
            try:
                if not await container.count():
                    continue
                for label in labels:
                    candidate = container.locator(f"text={label}")
                    if await candidate.count():
                        for index in range(await candidate.count()):
                            button = candidate.nth(index)
                            if await button.is_visible():
                                return button
            except Exception:
                continue

        return await self._first_visible_text_locator(labels)

    async def _confirm_modal(self, confirm_text: str = "确定") -> bool:
        """确认当前弹窗。"""
        if not self.browser.page:
            return False

        for selector in [
            f".ant-modal-root button:has-text('{confirm_text}')",
            f".ant-modal-content button:has-text('{confirm_text}')",
            f"button:has-text('{confirm_text}')",
        ]:
            locator = self.browser.page.locator(selector)
            try:
                if await locator.count() and await locator.first.is_visible():
                    return await self._click_locator(locator.first, wait_ms=1200)
            except Exception:
                continue
        return False
    
    async def _upload_images(self, image_paths: List[str]) -> None:
        """上传图片"""
        if not self.browser.page:
            return

        upload_input = None
        for selector in [
            'input[type="file"]',
            '.upload-button input[type="file"]',
            '.add-image input[type="file"]',
        ]:
            locator = self.browser.page.locator(selector)
            if await locator.count():
                upload_input = locator.first
                break

        if upload_input:
            image_files = [str(Path(p).absolute()) for p in image_paths if Path(p).exists()]
            if not image_files:
                raise RuntimeError("没有可上传的图片文件")

            await upload_input.set_input_files(image_files)
            logger.info(f"已上传 {len(image_files)} 张图片")
            await self.browser.page.wait_for_timeout(2500)

            # 等待上传区发生变化，避免马上进入下一步
            await self.browser.page.wait_for_timeout(1500)
            return

        raise RuntimeError("未找到图片上传控件")
    
    async def _fill_title(self, title: str) -> None:
        """填写标题"""
        if not self.browser.page:
            return

        title_input = await self._first_visible_locator([
            'input[placeholder*="标题"]',
            'input[name="title"]',
            '.title-input',
        ])

        if title_input:
            await title_input.fill(title)
            return

        # 当前发布页主要依赖描述智能识别标题，没有独立标题输入框
        logger.debug("当前发布页未发现独立标题输入框，将使用描述内容辅助生成标题")

    async def _fill_description(self, description: str, title: str = "") -> None:
        """填写描述"""
        if not self.browser.page:
            return

        final_text = self._sanitize_publish_text(description.strip())
        if title and title not in final_text:
            final_text = self._sanitize_publish_text(f"{title}\n{final_text}".strip())

        desc_input = await self._first_visible_locator([
            "div[contenteditable='true']",
            "[class*='editor']",
            'textarea[placeholder*="描述"]',
            'textarea[name="description"]',
            '.description-input',
        ])

        if not desc_input:
            raise RuntimeError("未找到描述输入区域")

        tag_name = await desc_input.evaluate("el => el.tagName")
        if tag_name == "DIV":
            await desc_input.click()
            await self.browser.page.keyboard.press("Control+A")
            await self.browser.page.keyboard.type(final_text)
        else:
            await desc_input.fill(final_text)

        await self.browser.page.wait_for_timeout(500)
    
    async def _fill_price(self, price: float) -> None:
        """填写价格"""
        if not self.browser.page:
            return

        price_inputs = self.browser.page.locator("input.ant-input")
        count = await price_inputs.count()
        for index in range(count):
            item = price_inputs.nth(index)
            try:
                if not await item.is_visible():
                    continue
                placeholder = await item.get_attribute("placeholder") or ""
                if placeholder != "0.00":
                    continue
                await item.fill("")
                await item.type(f"{price:.2f}".rstrip("0").rstrip("."))
                await self.browser.page.wait_for_timeout(300)
                return
            except Exception:
                continue

        raise RuntimeError("未找到价格输入框")
    
    async def _select_category(self, category: str) -> None:
        """选择分类"""
        if not self.browser.page:
            return

        # 当前页面由描述和图片智能识别属性，暂不强制失败
        logger.debug(f"当前发布页未发现稳定分类入口，跳过手动分类：{category}")
    
    async def _select_location(self, location: str) -> None:
        """选择地区"""
        if not self.browser.page:
            return

        trigger = await self._first_visible_locator([
            "text=请选择地址",
            "[class*='addressWrap']",
            "[class*='address--']",
        ])
        if not trigger:
            logger.debug("未找到地址选择入口，跳过地区设置")
            return

        if not await self._click_locator(trigger, wait_ms=1000):
            logger.debug("点击地址选择入口失败，跳过地区设置")
            return

        search_input = await self._first_visible_locator([
            "input[placeholder*='搜索地点']",
            "input[placeholder*='搜索']",
        ])
        if search_input and location:
            try:
                await search_input.fill(location)
                await self.browser.page.wait_for_timeout(1000)

                suggestions = self.browser.page.locator(".auto-item")
                suggestion_count = await suggestions.count()
                if suggestion_count > 0:
                    for index in range(suggestion_count):
                        item = suggestions.nth(index)
                        text = (await item.inner_text()).strip()
                        if location in text or text in location:
                            if await self._click_locator(item, wait_ms=1000):
                                return
                    if await self._click_locator(suggestions.nth(0), wait_ms=1000):
                        return
            except Exception as e:
                logger.debug(f"搜索地区失败，改用附近地址：{e}")

        options = self.browser.page.locator("[class*='addressItem']")
        count = await options.count()
        if count > 0:
            # 优先点首个匹配项，否则点第一个附近地址
            target = None
            for index in range(count):
                item = options.nth(index)
                text = (await item.inner_text()).strip()
                if location and location in text:
                    target = item
                    break
            if target is None:
                target = options.nth(0)
            if await self._click_locator(target, wait_ms=1000):
                return

        logger.debug("地址弹窗中未找到可选地址")
    
    async def _select_condition(self, condition: str) -> None:
        """选择新旧程度"""
        if not self.browser.page:
            return

        # 当前发布页主表单未暴露稳定的新旧程度控件，先做最佳努力匹配
        if condition:
            locator = self.browser.page.locator(f"text={condition}")
            if await locator.count():
                try:
                    await locator.first.click()
                    await self.browser.page.wait_for_timeout(500)
                    return
                except Exception:
                    pass
        logger.debug(f"当前发布页未发现稳定新旧程度入口，跳过：{condition}")
    
    async def _select_delivery(self, delivery: str) -> None:
        """选择配送方式"""
        if not self.browser.page:
            return

        normalized = delivery.strip()
        mapping = {
            "包邮": "包邮",
            "按距离计费": "按距离计费",
            "一口价": "一口价",
            "无需邮寄": "无需邮寄",
        }
        target_text = mapping.get(normalized, "包邮")

        radio = self.browser.page.locator(".ant-radio-wrapper").filter(has_text=target_text)
        if await radio.count():
            await radio.first.click()
            await self.browser.page.wait_for_timeout(500)
            return

        logger.debug(f"未找到配送方式选项，保持默认：{target_text}")
    
    async def _add_tags(self, tags: List[str]) -> None:
        """添加标签"""
        if not self.browser.page:
            return

        # 当前发布页无稳定标签入口，先记录跳过
        logger.debug(f"当前发布页未发现稳定标签入口，跳过：{tags}")
    
    async def _mark_original(self) -> None:
        """声明原创"""
        if not self.browser.page:
            return

        switch_button = await self._first_visible_locator([
            ".ant-switch",
            "button.ant-switch",
        ])
        if switch_button:
            try:
                aria_checked = await switch_button.get_attribute("aria-checked")
                if aria_checked != "true":
                    await switch_button.click()
                    await self.browser.page.wait_for_timeout(500)
                return
            except Exception:
                pass

        logger.debug("当前发布页未发现稳定原创开关，跳过")
    
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
            submit_button = await self._first_visible_locator([
                "button.publish-button--KBpTVopQ",
                "[class*='publish-button']",
                'button[type="submit"]',
                'button:has-text("发布")',
            ])

            if not submit_button:
                return False, "未找到发布按钮"

            blockers = await self._get_publish_blockers()
            if blockers:
                return False, "；".join(dict.fromkeys(blockers))

            button_class = await submit_button.get_attribute("class") or ""
            if "disabled" in button_class.lower():
                return False, "发布按钮仍处于禁用状态，请检查图片、描述、价格和地址是否已填写完整"

            await submit_button.click()
            await self.browser.page.wait_for_timeout(3000)

            current_url = self.browser.page.url
            match = re.search(r"[?&]id=(\d+)", current_url)
            if match and "/item" in current_url:
                return True, match.group(1)

            if "/detail/" in current_url:
                item_id = current_url.split('/detail/')[-1].split('?')[0]
                return True, item_id

            error_el = await self._first_visible_locator([
                ".error-message",
                ".toast-error",
                ".ant-message-error",
                ".ant-notification-notice-description",
            ])
            if error_el:
                error_text = (await error_el.inner_text()).strip()
                if error_text:
                    return False, error_text

            # 保守返回：按钮可点但未识别到详情页，说明已触发提交
            return True, "submitted"
            
        except Exception as e:
            return False, str(e)
    
    async def edit_item(
        self,
        item_id: str,
        updates: Dict[str, Any],
        dry_run: bool = False,
    ) -> tuple[bool, Any]:
        """
        编辑商品
        
        Args:
            item_id: 商品 ID
            updates: 更新内容
            dry_run: 是否仅试填，不提交
            
        Returns:
            (是否成功，消息)
        """
        logger.info(f"编辑商品 {item_id}")
        if not self.browser.page:
            return False, "浏览器未启动"

        if not item_id:
            return False, "商品 ID 不能为空"

        if not updates:
            return False, "至少需要提供一项更新内容"

        try:
            await self._ensure_edit_page(item_id)

            pending_description = updates.get("description")
            pending_title = updates.get("title")

            if updates.get("images"):
                logger.info("更新图片...")
                await self._upload_images(updates["images"])

            if pending_title and not pending_description:
                current_description = await self._read_current_description()
                pending_description = current_description or pending_title

            if pending_description is not None:
                logger.info("更新描述...")
                await self._fill_description(str(pending_description), title=str(pending_title or ""))
            elif pending_title:
                logger.info("更新标题...")
                await self._fill_title(str(pending_title))

            if "price" in updates and updates["price"] is not None:
                logger.info("更新价格...")
                await self._fill_price(float(updates["price"]))

            if updates.get("location"):
                logger.info("更新地区...")
                await self._select_location(str(updates["location"]))

            if updates.get("condition"):
                logger.info("更新新旧程度...")
                await self._select_condition(str(updates["condition"]))

            if updates.get("delivery"):
                logger.info("更新配送方式...")
                await self._select_delivery(str(updates["delivery"]))

            if "tags" in updates and updates.get("tags"):
                logger.info("更新标签...")
                await self._add_tags(list(updates["tags"]))

            if updates.get("is_original"):
                logger.info("更新原创声明...")
                await self._mark_original()

            if dry_run:
                state = await self._inspect_publish_state()
                state["success"] = True
                state["item_id"] = item_id
                state["mode"] = "edit"
                return True, state

            logger.info("提交编辑...")
            success, result = await self._submit_publish()
            if not success:
                return False, result
            return True, item_id if result == "submitted" else result
        except Exception as e:
            logger.error(f"编辑商品失败：{e}")
            return False, str(e)
    
    async def delete_item(
        self,
        item_id: str,
        force_delete: bool = False,
        dry_run: bool = False,
    ) -> tuple[bool, str]:
        """
        下架商品
        
        Args:
            item_id: 商品 ID
            force_delete: 当无法下架时是否尝试删除
            dry_run: 是否仅检查按钮和确认弹窗，不真正执行
            
        Returns:
            (是否成功，消息)
        """
        logger.info(f"下架商品 {item_id}")
        if not self.browser.page:
            return False, "浏览器未启动"

        if not item_id:
            return False, "商品 ID 不能为空"

        try:
            await self._ensure_item_page(item_id)

            action_button = await self._find_action_button(["下架"])
            action_name = "下架"

            if not action_button and force_delete:
                action_button = await self._find_action_button(["删除"])
                action_name = "删除"

            if not action_button:
                if await self._find_action_button(["删除"]):
                    return False, "当前商品未找到“下架”按钮，可能已下架；如需彻底删除请设置 force_delete=True"
                return False, "未找到可用的下架按钮"

            if not await self._click_locator(action_button, wait_ms=1000):
                return False, f"点击“{action_name}”按钮失败"

            body_text = await self.browser.page.evaluate(
                "() => document.body && document.body.innerText ? document.body.innerText : ''"
            )
            if "确定要下架这个宝贝吗" in body_text or "确定要删除这个宝贝吗" in body_text:
                if dry_run:
                    cancel_button = await self._first_visible_text_locator(["取消"])
                    if cancel_button:
                        await self._click_locator(cancel_button, wait_ms=600)
                    return True, f"已定位“{action_name}”确认弹窗"
                if not await self._confirm_modal("确定"):
                    return False, f"未找到“{action_name}”确认按钮"
            elif dry_run:
                return True, f"已定位“{action_name}”按钮"

            await self.browser.page.wait_for_timeout(3000)

            refreshed_text = await self.browser.page.evaluate(
                "() => document.body && document.body.innerText ? document.body.innerText : ''"
            )

            if action_name == "下架":
                if "确定要下架这个宝贝吗" in refreshed_text:
                    return False, "下架确认后页面仍停留在确认弹窗，可能未执行成功"
                return True, "商品已下架"

            if "确定要删除这个宝贝吗" in refreshed_text:
                return False, "删除确认后页面仍停留在确认弹窗，可能未执行成功"
            return True, "商品已删除"
        except Exception as e:
            logger.error(f"下架商品失败：{e}")
            return False, str(e)
    
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
