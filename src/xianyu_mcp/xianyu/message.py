"""
消息模块

实现闲鱼消息获取、自动回复、智能议价等功能
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json
import re
from loguru import logger

from .browser import XianyuBrowser
from .login import XianyuLogin
from ..config import settings


@dataclass
class Message:
    """消息数据结构"""
    id: str = ""
    conversation_id: str = ""
    from_user_id: str = ""
    from_user_name: str = ""
    from_user_avatar: str = ""
    content: str = ""
    timestamp: Optional[datetime] = None
    is_read: bool = False
    is_from_me: bool = False
    item_id: str = ""  # 关联商品 ID
    item_title: str = ""  # 关联商品标题
    message_type: str = "text"  # text, image, system
    reply_to: Optional[str] = None  # 回复的消息 ID
    source: str = "unknown"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "from_user_id": self.from_user_id,
            "from_user_name": self.from_user_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_read": self.is_read,
            "is_from_me": self.is_from_me,
            "message_type": self.message_type,
            "item_id": self.item_id,
            "item_title": self.item_title,
            "source": self.source,
        }


@dataclass
class Conversation:
    """会话数据结构"""
    id: str = ""
    user_id: str = ""
    user_name: str = ""
    user_avatar: str = ""
    last_message: str = ""
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    item_id: str = ""
    item_title: str = ""
    session_type: int = 0
    can_send: bool = True
    source: str = "unknown"
    has_context: bool = False
    last_opened_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "last_message": self.last_message,
            "unread_count": self.unread_count,
            "item_id": self.item_id,
            "item_title": self.item_title,
            "session_type": self.session_type,
            "can_send": self.can_send,
            "source": self.source,
            "has_context": self.has_context,
            "last_opened_at": self.last_opened_at.isoformat() if self.last_opened_at else None,
        }


class XianyuMessage:
    """闲鱼消息类"""
    
    def __init__(self, browser: XianyuBrowser):
        """
        初始化消息模块
        
        Args:
            browser: 浏览器实例
        """
        self.browser = browser
        self.reply_templates = {
            "greeting": "你好，商品还在的~",
            "price_confirm": "价格就是标价哦，可以小刀",
            "shipping": "包邮的，放心购买",
            "condition": "商品很新，没怎么用过",
            "location": "我在 {location}，可以自提",
            "bargain_accept": "好的，那就 {price} 元给你吧",
            "bargain_reject": "抱歉，这个价格已经很低了",
            "sold_out": "不好意思，已经卖出了",
        }
        self._cookies_loaded = False
        self._im_block_reason = ""
        self._api_cache: Dict[str, Dict[str, Any]] = {}
        self._message_api_cache: Dict[str, Dict[str, Any]] = {}
        self._conversation_context_cache: Dict[str, Dict[str, str]] = {}
        self._conversation_last_opened_cache: Dict[str, datetime] = {}
        self._response_listener_registered = False
        self._register_response_listener()
        logger.info("消息模块已初始化")

    def _register_response_listener(self) -> None:
        """注册 IM 页面接口响应监听器。"""
        if self._response_listener_registered or not self.browser.page:
            return

        def on_response(response):
            asyncio.create_task(self._capture_api_response(response))

        self.browser.page.on("response", on_response)
        self._response_listener_registered = True

    async def _capture_api_response(self, response) -> None:
        """缓存 IM 相关 mtop 接口响应。"""
        url = response.url
        if "/h5/mtop." not in url:
            return

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            return

        try:
            payload = await response.json()
        except Exception:
            return

        api_name = payload.get("api")
        if not api_name:
            return

        self._api_cache[api_name] = payload

        if api_name == "mtop.taobao.idlemessage.pc.message.sync":
            self._cache_message_sync_payload(payload)

    def _cache_message_sync_payload(self, payload: Dict[str, Any]) -> None:
        """按 sessionId 缓存消息同步接口结果。"""
        data = payload.get("data", {})
        candidates: List[Dict[str, Any]] = []

        fetchs = data.get("fetchs")
        if isinstance(fetchs, list):
            candidates.extend(fetch for fetch in fetchs if isinstance(fetch, dict))
        elif isinstance(data, dict):
            candidates.append(data)

        for entry in candidates:
            session_id = entry.get("sessionId") or data.get("sessionId")
            if session_id:
                self._message_api_cache[str(session_id)] = entry

    async def _ensure_im_page(self) -> None:
        """确保当前位于消息页。"""
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")

        if not self._cookies_loaded:
            try:
                login = XianyuLogin(self.browser)
                self._cookies_loaded = await login.load_cookies()
            except Exception as e:
                logger.debug(f"加载 Cookie 失败：{e}")
                self._cookies_loaded = False

        if "/im" not in self.browser.page.url:
            await self.browser.page.goto("https://www.goofish.com/im", wait_until="networkidle", timeout=30000)
            await self.browser.page.wait_for_timeout(3000)

        self._im_block_reason = await self._detect_im_block_reason()

    def _get_conversations_from_api_cache(self, limit: int) -> List[Conversation]:
        """优先从 session.sync 接口缓存解析会话列表。"""
        payload = self._api_cache.get("mtop.taobao.idlemessage.pc.session.sync", {})
        sessions = payload.get("data", {}).get("sessions", [])
        conversations: List[Conversation] = []

        for index, entry in enumerate(sessions[:limit]):
            session = entry.get("session", {})
            summary = entry.get("message", {}).get("summary", {})
            user_info = session.get("userInfo", {})
            owner_info = session.get("ownerInfo", {})
            session_type = int(session.get("sessionType", 0) or 0)
            user_type = int(user_info.get("type", 0) or 0)
            can_send = session_type not in {3} and user_type not in {10}

            conv = Conversation(
                id=str(session.get("sessionId", index)),
                user_id=str(user_info.get("userId", "")),
                user_name=user_info.get("nick", "") or owner_info.get("fishNick", ""),
                user_avatar=user_info.get("logo", ""),
                last_message=summary.get("summary", ""),
                unread_count=int(summary.get("unread", 0) or 0),
                session_type=session_type,
                can_send=can_send,
                source="api",
            )

            ts = summary.get("ts")
            if ts:
                try:
                    conv.last_message_time = datetime.fromtimestamp(ts / 1000)
                except Exception:
                    pass

            conversations.append(conv)

        return conversations

    def _find_cached_conversation(self, target: str) -> Optional[Conversation]:
        """从接口缓存中查找会话。"""
        for conversation in self._get_conversations_from_api_cache(limit=200):
            if target in {conversation.id, conversation.user_id}:
                return conversation
        return None

    def _get_cached_conversation_index(self, target: str) -> Optional[int]:
        """返回接口缓存中会话的顺序索引。"""
        for index, conversation in enumerate(self._get_conversations_from_api_cache(limit=200)):
            if target in {conversation.id, conversation.user_id}:
                return index
        return None

    def _get_unread_count_from_api_cache(self) -> Optional[int]:
        """优先从 redpoint.query 接口缓存获取未读总数。"""
        payload = self._api_cache.get("mtop.taobao.idlemessage.pc.redpoint.query", {})
        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        total = data.get("total")
        if total is None:
            return None

        try:
            return int(total)
        except (TypeError, ValueError):
            return None

    def _extract_message_text(self, raw_value: Any) -> str:
        """从 mtop 消息体中提取可读文本。"""
        if raw_value is None:
            return ""

        if isinstance(raw_value, bool):
            return ""

        if isinstance(raw_value, (int, float)):
            return ""

        if isinstance(raw_value, str):
            text = raw_value.strip()
            if not text:
                return ""

            if text.startswith("{") or text.startswith("["):
                try:
                    return self._extract_message_text(json.loads(text))
                except Exception:
                    return text

            return text

        if isinstance(raw_value, list):
            parts = [self._extract_message_text(item) for item in raw_value]
            parts = [part for part in parts if part]
            return "\n".join(parts)

        if isinstance(raw_value, dict):
            if "textCard" in raw_value and isinstance(raw_value["textCard"], dict):
                text_card = raw_value["textCard"]
                parts = [
                    self._extract_message_text(text_card.get("title")),
                    self._extract_message_text(text_card.get("content")),
                ]
                parts = [part for part in parts if part]
                if parts:
                    return "\n".join(parts)

            if any(key in raw_value for key in ["title", "content"]):
                parts = [
                    self._extract_message_text(raw_value.get("title")),
                    self._extract_message_text(raw_value.get("content")),
                ]
                parts = [part for part in parts if part]
                if parts:
                    return "\n".join(parts)

            for key in ["text", "content", "title", "summary", "desc", "description", "value"]:
                text = self._extract_message_text(raw_value.get(key))
                if text:
                    return text

            for key, value in raw_value.items():
                if key in {"contentType", "actionType", "iosActionStyle", "showGuideAlways", "type", "version"}:
                    continue
                text = self._extract_message_text(value)
                if text:
                    return text

        return str(raw_value).strip()

    def _build_message_from_api_entry(
        self,
        conversation_id: str,
        entry: Dict[str, Any],
        session_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Message]:
        """将单条接口消息转换为 Message。"""
        msg = Message()
        msg.id = str(
            entry.get("messageUuid")
            or entry.get("messageId")
            or entry.get("id")
            or ""
        )
        msg.conversation_id = conversation_id

        sender_info = entry.get("senderInfo", {}) if isinstance(entry.get("senderInfo"), dict) else {}
        msg.from_user_id = str(
            sender_info.get("userId")
            or entry.get("fromUserId")
            or entry.get("senderId")
            or ""
        )
        msg.from_user_name = (
            sender_info.get("nick")
            or sender_info.get("displayName")
            or entry.get("fromUserName")
            or ""
        )
        msg.from_user_avatar = sender_info.get("logo", "")
        msg.content = self._extract_message_text(
            entry.get("content")
            or entry.get("summary")
            or entry.get("text")
            or entry.get("body")
        )
        msg.message_type = str(
            entry.get("msgType")
            or entry.get("messageType")
            or entry.get("arg1")
            or entry.get("type")
            or "text"
        )
        msg.source = "api"

        ts = entry.get("timeStamp") or entry.get("ts") or entry.get("timestamp")
        if ts:
            try:
                if isinstance(ts, str) and ts.isdigit():
                    ts = int(ts)
                if isinstance(ts, (int, float)):
                    if ts > 10_000_000_000:
                        ts = ts / 1000
                    msg.timestamp = datetime.fromtimestamp(ts)
            except Exception:
                pass

        read_flag = entry.get("isRead")
        if read_flag is None:
            read_flag = entry.get("read")
        msg.is_read = bool(read_flag) if read_flag is not None else False

        out_flags = [
            entry.get("fromSelf"),
            entry.get("isSelf"),
            entry.get("out"),
            entry.get("isOut"),
        ]
        if any(flag is True for flag in out_flags):
            msg.is_from_me = True
        elif str(entry.get("direction", "")).lower() in {"out", "send", "sent"}:
            msg.is_from_me = True
        elif session_context:
            owner_info = session_context.get("ownerInfo", {})
            owner_user_id = str(
                owner_info.get("userId")
                or owner_info.get("fishUserId")
                or ""
            )
            if owner_user_id and msg.from_user_id and owner_user_id == msg.from_user_id:
                msg.is_from_me = True

        if not msg.content and not msg.from_user_name and not msg.id:
            return None

        return msg

    def _get_messages_from_api_cache(self, conversation_id: str, limit: int) -> List[Message]:
        """优先从 message.sync 接口缓存解析消息列表。"""
        payload = self._message_api_cache.get(conversation_id)
        if not payload:
            fallback = self._api_cache.get("mtop.taobao.idlemessage.pc.message.sync", {})
            data = fallback.get("data", {})
            if str(data.get("sessionId", "")) == conversation_id:
                payload = data
            else:
                fetchs = data.get("fetchs", [])
                if isinstance(fetchs, list):
                    for entry in fetchs:
                        if str(entry.get("sessionId", "")) == conversation_id:
                            payload = entry
                            break

        if not payload:
            return []

        raw_messages = payload.get("messages", [])
        if not isinstance(raw_messages, list):
            return []

        session_context = payload.get("sessionInfo", {})
        messages: List[Message] = []
        for entry in raw_messages[-limit:]:
            if not isinstance(entry, dict):
                continue
            msg = self._build_message_from_api_entry(conversation_id, entry, session_context=session_context)
            if msg:
                messages.append(msg)

        return messages

    def _extract_headinfo_context(self) -> Dict[str, str]:
        """从当前 headinfo 接口缓存提取商品上下文。"""
        payload = self._api_cache.get("mtop.idle.trade.pc.message.headinfo", {})
        data = payload.get("data", {})
        common_data = data.get("commonData", {})

        item_id = str(common_data.get("itemId") or "")
        item_title = ""

        item_pre_info = common_data.get("itemPreInfo")
        if isinstance(item_pre_info, str) and item_pre_info:
            try:
                parsed = json.loads(item_pre_info)
            except Exception:
                parsed = {}
            if isinstance(parsed, dict):
                item_title = str(parsed.get("title") or "")
                if not item_id:
                    item_id = str(parsed.get("itemId") or "")

        return {
            "item_id": item_id,
            "item_title": item_title,
        }

    def _cache_current_conversation_context(self, conversation_id: str) -> Dict[str, str]:
        """把当前 headinfo 缓存绑定到指定会话。"""
        context = self._extract_headinfo_context()
        if context.get("item_id") or context.get("item_title"):
            self._conversation_context_cache[conversation_id] = context
        return self._conversation_context_cache.get(conversation_id, context)

    def _mark_conversation_opened(self, conversation_id: str) -> None:
        """记录会话最近一次被打开的时间。"""
        self._conversation_last_opened_cache[conversation_id] = datetime.now()

    async def _detect_im_block_reason(self) -> str:
        """检测 IM 页面是否被风控或验证码拦截。"""
        if not self.browser.page:
            return "浏览器未启动"

        body_text = await self.browser.page.evaluate(
            "() => (document.body && document.body.innerText ? document.body.innerText : '').slice(0, 3000)"
        )

        if any(keyword in body_text for keyword in ["请按住滑块", "拖动到最右边", "验证码", "安全验证"]):
            return "闲鱼 IM 页面触发了安全验证，当前会话数据被拦截"

        challenge_frame = await self.browser.page.query_selector("iframe[src*='punish'], iframe[src*='captcha']")
        if challenge_frame:
            return "闲鱼 IM 页面触发了验证码挑战，当前会话数据无法直接加载"

        return ""

    async def _ensure_im_ready(self, verification_timeout: Optional[int] = None) -> bool:
        """确保 IM 页面可用；如触发验证则在有头模式下等待人工完成。"""
        verification_timeout = verification_timeout or settings.im_verification_timeout
        await self._ensure_im_page()

        if not self._im_block_reason:
            return True

        # 无头模式无法进行人工交互，直接返回明确错误
        if self.browser.headless:
            self._im_block_reason = (
                f"{self._im_block_reason}；当前为无头模式，无法完成人工验证，请使用有头模式重试"
            )
            return False

        logger.warning(self._im_block_reason)
        logger.warning(f"请在浏览器中手动完成验证，最多等待 {verification_timeout} 秒")

        elapsed = 0
        interval_ms = 2000
        while elapsed < verification_timeout:
            await self.browser.page.wait_for_timeout(interval_ms)
            elapsed += interval_ms // 1000

            self._im_block_reason = await self._detect_im_block_reason()
            if not self._im_block_reason:
                logger.success("IM 页面验证已完成，继续执行后续操作")
                return True

        self._im_block_reason = (
            f"{self._im_block_reason}；等待人工验证超时（{verification_timeout} 秒）"
        )
        logger.error(self._im_block_reason)
        return False

    def get_last_block_reason(self) -> str:
        """返回最近一次 IM 阻塞原因。"""
        return self._im_block_reason
    
    async def get_conversations(self, limit: int = 20) -> List[Conversation]:
        """
        获取会话列表
        
        Args:
            limit: 数量限制
            
        Returns:
            会话列表
        """
        logger.info(f"获取会话列表，限制：{limit}")
        
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")
        
        try:
            # 先打开页面并采集接口响应
            await self._ensure_im_page()

            conversations = self._get_conversations_from_api_cache(limit)
            if conversations:
                logger.info(f"通过接口缓存获取到 {len(conversations)} 个会话")
                if len(conversations) >= limit:
                    return self._apply_cached_context_to_conversations(conversations)

                if not self._im_block_reason:
                    dom_conversations = await self._parse_conversations(limit)
                    conversations = self._merge_conversations(conversations, dom_conversations, limit)
                return self._apply_cached_context_to_conversations(conversations)

            if self._im_block_reason:
                logger.warning(self._im_block_reason)
                return []
            
            # 解析会话列表
            conversations = await self._parse_conversations(limit)
            
            logger.info(f"找到 {len(conversations)} 个会话")
            return self._apply_cached_context_to_conversations(conversations)
            
        except Exception as e:
            logger.error(f"获取会话失败：{e}")
            return []

    def _merge_conversations(
        self,
        api_conversations: List[Conversation],
        dom_conversations: List[Conversation],
        limit: int,
    ) -> List[Conversation]:
        """合并接口和 DOM 会话，优先保留接口结果。"""
        merged: List[Conversation] = list(api_conversations)
        seen_keys = {
            (conv.user_name.strip(), conv.last_message.strip())
            for conv in api_conversations
        }

        for conv in dom_conversations:
            key = (conv.user_name.strip(), conv.last_message.strip())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            merged.append(conv)
            if len(merged) >= limit:
                break

        return self._rank_conversations(merged)[:limit]

    def _rank_conversations(self, conversations: List[Conversation]) -> List[Conversation]:
        """按可操作性对会话排序。"""
        def sort_key(conv: Conversation):
            last_opened = conv.last_opened_at.timestamp() if conv.last_opened_at else 0.0
            last_message = conv.last_message_time.timestamp() if conv.last_message_time else 0.0
            return (
                1 if conv.can_send else 0,
                1 if conv.has_context else 0,
                1 if conv.unread_count > 0 else 0,
                last_opened,
                last_message,
            )

        return sorted(conversations, key=sort_key, reverse=True)

    def _apply_cached_context_to_conversations(
        self,
        conversations: List[Conversation],
    ) -> List[Conversation]:
        """把已缓存的商品上下文补到会话列表。"""
        for conv in conversations:
            context = self._conversation_context_cache.get(conv.id, {})
            if not context:
                context = {}
            if not conv.item_id:
                conv.item_id = context.get("item_id", "")
            if not conv.item_title:
                conv.item_title = context.get("item_title", "")
            conv.has_context = bool(conv.item_id or conv.item_title)

            last_opened_at = self._conversation_last_opened_cache.get(conv.id)
            if last_opened_at:
                conv.last_opened_at = last_opened_at
        return self._rank_conversations(conversations)
    
    async def _parse_conversations(self, limit: int) -> List[Conversation]:
        """解析会话列表"""
        conversations = []
        
        try:
            if not await self._ensure_im_ready():
                logger.warning(self._im_block_reason)
                return []

            # 先等会话列表容器挂载，再查询虚拟列表里的会话项
            await self.browser.page.wait_for_selector(
                "[class*='conversation-list'], [class*='conv-list-scroll']",
                state="attached",
                timeout=10000
            )

            items = await self.browser.page.query_selector_all(
                "[class*='conversation-list'] [class*='conversation-item'], [class*='conversation-item']"
            )
            if not items:
                await self.browser.page.wait_for_timeout(2000)
                items = await self.browser.page.query_selector_all("[class*='conversation-item']")
            
            for i, item in enumerate(items[:limit]):
                try:
                    conv = await self._parse_single_conversation(item)
                    if conv:
                        if not conv.id:
                            conv.id = f"dom:{i}"
                        conversations.append(conv)
                except Exception as e:
                    logger.debug(f"解析会话失败：{e}")
                    continue
            
        except Exception as e:
            logger.error(f"解析会话列表失败：{e}")
        
        return conversations
    
    async def _parse_single_conversation(self, item) -> Optional[Conversation]:
        """解析单个会话"""
        try:
            conv = Conversation()
            
            text = (await item.inner_text()).strip()
            if not text:
                return None

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if not lines:
                return None

            # 当前页面未暴露稳定 id，优先读取 data-*，否则用列表索引占位
            for attr_name in ["data-id", "data-key", "data-conversation-id", "data-session-id"]:
                attr_value = await item.get_attribute(attr_name)
                if attr_value:
                    conv.id = attr_value
                    break

            # 会话结构一般为：用户名 / 最后一条消息 / 时间
            conv.user_name = lines[0]
            if len(lines) >= 3:
                conv.last_message_time = self._parse_time_text(lines[-1])
                conv.last_message = " ".join(lines[1:-1]).strip()
            elif len(lines) == 2:
                possible_time = self._parse_time_text(lines[-1])
                if possible_time:
                    conv.last_message_time = possible_time
                else:
                    conv.last_message = lines[-1]

            # 提取未读数
            unread_el = await item.query_selector(".ant-badge-count, [class*='badge-count'], sup")
            if unread_el:
                unread_text = await unread_el.inner_text()
                match = re.search(r"\d+", unread_text)
                if match:
                    conv.unread_count = int(match.group())

            # 提取头像
            avatar_el = await item.query_selector("img, .avatar img")
            if avatar_el:
                conv.user_avatar = await avatar_el.get_attribute("src") or ""

            conv.source = "dom"

            # DOM 会话没有稳定 session 元数据时，按常见系统会话名称做保守推断
            if conv.user_name in {"通知消息", "系统消息"}:
                conv.can_send = False
                conv.session_type = 3

            return conv
            
        except Exception as e:
            logger.debug(f"解析单个会话失败：{e}")
            return None
    
    async def get_messages(self, conversation_id: str, limit: int = 50) -> List[Message]:
        """
        获取会话消息
        
        Args:
            conversation_id: 会话 ID
            limit: 数量限制
            
        Returns:
            消息列表
        """
        logger.info(f"获取会话 {conversation_id} 的消息")
        
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")
        
        try:
            await self._ensure_im_page()

            cached_messages = self._get_messages_from_api_cache(conversation_id, limit)
            if cached_messages:
                logger.info(f"通过接口缓存获取到 {len(cached_messages)} 条消息")
                return cached_messages

            if not await self._ensure_im_ready():
                logger.warning(self._im_block_reason)
                return []

            # 打开会话
            await self._open_conversation(conversation_id)
            for _ in range(5):
                await self.browser.page.wait_for_timeout(1000)
                cached_messages = self._get_messages_from_api_cache(conversation_id, limit)
                if cached_messages:
                    logger.info(f"通过接口缓存获取到 {len(cached_messages)} 条消息")
                    return cached_messages

            context = self._cache_current_conversation_context(conversation_id)
            
            # 解析消息
            messages = await self._parse_messages(limit)
            for msg in messages:
                if not msg.conversation_id:
                    msg.conversation_id = conversation_id
                if context:
                    if not msg.item_id:
                        msg.item_id = context.get("item_id", "")
                    if not msg.item_title:
                        msg.item_title = context.get("item_title", "")
            
            logger.info(f"找到 {len(messages)} 条消息")
            return messages
            
        except Exception as e:
            logger.error(f"获取消息失败：{e}")
            return []

    async def warm_conversation_context(self, conversation_id: str) -> Dict[str, str]:
        """
        预热指定会话的商品上下文。

        Args:
            conversation_id: 会话 ID

        Returns:
            已缓存的商品上下文字典
        """
        logger.info(f"预热会话 {conversation_id} 的商品上下文")

        if not self.browser.page:
            raise RuntimeError("浏览器未启动")

        try:
            await self._ensure_im_page()
            if not await self._ensure_im_ready():
                logger.warning(self._im_block_reason)
                return {}

            await self._open_conversation(conversation_id)
            await self.browser.page.wait_for_timeout(1500)
            return self._cache_current_conversation_context(conversation_id)
        except Exception as e:
            logger.error(f"预热会话上下文失败：{e}")
            return {}
    
    async def _open_conversation(self, conversation_id: str) -> None:
        """打开会话"""
        if not self.browser.page:
            raise RuntimeError("浏览器未启动")

        await self._ensure_im_page()

        await self.browser.page.wait_for_selector("[class*='conversation-item']", timeout=10000)
        items = await self.browser.page.query_selector_all("[class*='conversation-item']")
        if not items:
            raise RuntimeError("未找到会话列表")

        cached_conversation = self._find_cached_conversation(conversation_id)
        cached_index = self._get_cached_conversation_index(conversation_id)
        dom_index = None
        if conversation_id.startswith("dom:"):
            suffix = conversation_id.split(":", 1)[1]
            if suffix.isdigit():
                dom_index = int(suffix)

        # 优先按稳定属性和已缓存会话信息匹配；最后才按索引回退
        target_item = None
        for item in items:
            for attr_name in ["data-id", "data-key", "data-conversation-id", "data-session-id"]:
                attr_value = await item.get_attribute(attr_name)
                if attr_value and attr_value == conversation_id:
                    target_item = item
                    break
            if target_item:
                break

            text = (await item.inner_text()).strip()
            if conversation_id in text:
                target_item = item
                break

            if cached_conversation and cached_conversation.user_name and cached_conversation.user_name in text:
                target_item = item
                break

        if target_item is None and cached_index is not None and 0 <= cached_index < len(items):
            target_item = items[cached_index]

        if target_item is None and dom_index is not None and 0 <= dom_index < len(items):
            target_item = items[dom_index]

        if not target_item and not cached_conversation and conversation_id.isdigit():
            idx = int(conversation_id)
            if 0 <= idx < len(items):
                target_item = items[idx]

        if not target_item:
            raise RuntimeError(f"未找到会话：{conversation_id}")

        await target_item.click()
        self._mark_conversation_opened(conversation_id)
        logger.debug(f"打开会话：{conversation_id}")
    
    async def _parse_messages(self, limit: int) -> List[Message]:
        """解析消息列表"""
        messages = []
        
        try:
            # 等待消息列表加载
            await self.browser.page.wait_for_selector(
                "[class*='message-row'], .ant-list-items .ant-list-item",
                timeout=10000
            )

            # 优先只取顶层列表项，避免同时抓到嵌套的 message-row 导致重复
            items = await self.browser.page.query_selector_all(".ant-list-items .ant-list-item")
            if not items:
                items = await self.browser.page.query_selector_all("[class*='message-row']")

            seen_signatures = set()
            
            for item in items[-limit:]:
                try:
                    msg = await self._parse_single_message(item)
                    if msg:
                        signature = (
                            msg.from_user_name.strip(),
                            msg.content.strip(),
                            bool(msg.is_from_me),
                            msg.timestamp.isoformat() if msg.timestamp else "",
                        )
                        if signature in seen_signatures:
                            continue
                        seen_signatures.add(signature)
                        messages.append(msg)
                except Exception as e:
                    logger.debug(f"解析消息失败：{e}")
                    continue
            
        except Exception as e:
            logger.error(f"解析消息列表失败：{e}")
        
        return messages

    async def _find_message_input(self):
        """定位消息输入框。"""
        selectors = [
            "textarea[placeholder*='输入消息']",
            "textarea[placeholder*='请输入消息']",
            "textarea[placeholder*='输入']",
            "textarea",
            "div[contenteditable='true']",
            "[role='textbox']",
            "input[name='message']",
        ]

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

    async def _find_send_button(self):
        """定位发送按钮。"""
        selectors = [
            "button:has-text('发送')",
            "button:has-text('发 送')",
            "[class*='sendbox'] button",
            "[class*='send-button']",
            "button[type='submit']",
        ]

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
    
    async def _parse_single_message(self, item) -> Optional[Message]:
        """解析单条消息"""
        try:
            msg = Message()
            msg.source = "dom"
            
            # 提取内容
            content_selectors = [
                "[class*='message-content'] [class*='message-text']",
                "[class*='message-content']",
                "[class*='message-text']",
                "[class*='msg-dx-content']",
                "[class*='msg-dx-title']",
                ".tpl-wrapper",
            ]

            content_parts: List[str] = []
            for selector in content_selectors:
                elements = await item.query_selector_all(selector)
                for el in elements:
                    text = (await el.inner_text()).strip()
                    if not text:
                        continue
                    cleaned_lines = [
                        line.strip()
                        for line in text.splitlines()
                        if line.strip() and line.strip() not in {"已读", "未读"}
                    ]
                    cleaned = "\n".join(cleaned_lines).strip()
                    if cleaned and cleaned not in content_parts:
                        content_parts.append(cleaned)

            if content_parts:
                content_parts.sort(
                    key=lambda value: (len(value), value.count("\n")),
                    reverse=True,
                )
                msg.content = content_parts[0]

            if not msg.content:
                raw_text = (await item.inner_text()).strip()
                lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
                if lines:
                    filtered = [
                        line
                        for line in lines
                        if line not in {"已读", "未读"} and not self._parse_time_text(line)
                    ]
                    if filtered:
                        msg.content = "\n".join(filtered[1:] if len(filtered) > 1 else filtered).strip()

            if not msg.content:
                return None

            # 判断是否是自己发的
            if await item.query_selector("[class*='msg-text-right'], [class*='read-status-text']"):
                msg.is_from_me = True

            # 提取用户名（左侧消息通常含用户名，右侧通常是自己）
            lines = [line.strip() for line in (await item.inner_text()).splitlines() if line.strip()]
            if lines:
                first_line = lines[0]
                if first_line not in {"已读", "未读"} and first_line not in msg.content:
                    msg.from_user_name = first_line

            # 提取时间（只在系统时间项里能读到，普通消息不强行伪造）
            for line in lines:
                parsed_time = self._parse_time_text(line)
                if parsed_time:
                    msg.timestamp = parsed_time
                    break

            msg.is_read = bool(await item.query_selector("[class*='read-status-text']"))

            return msg
            
        except Exception as e:
            logger.debug(f"解析单条消息失败：{e}")
            return None
    
    async def send_reply(self, user_id: str, content: str) -> tuple[bool, str]:
        """
        发送回复
        
        Args:
            user_id: 用户 ID
            content: 回复内容
            
        Returns:
            (是否成功，消息)
        """
        logger.info(f"发送回复给 {user_id}: {content[:50]}...")
        
        if not self.browser.page:
            return False, "浏览器未启动"
        
        try:
            await self._ensure_im_page()

            cached_conversation = self._find_cached_conversation(user_id)
            if cached_conversation and not cached_conversation.can_send:
                return False, "当前会话是系统消息或不可发送会话，请换一个普通聊天会话"

            if not await self._ensure_im_ready():
                return False, self._im_block_reason

            # 打开会话
            await self._open_conversation(user_id)
            await self.browser.page.wait_for_timeout(1000)
            
            # 找到输入框
            input_el = await self._find_message_input()
            
            if input_el:
                try:
                    await input_el.fill(content)
                except Exception:
                    await input_el.click()
                    await self.browser.page.keyboard.press("Control+A")
                    await self.browser.page.keyboard.type(content)
                await self.browser.page.wait_for_timeout(500)
                
                # 找到发送按钮
                send_btn = await self._find_send_button()
                
                if send_btn:
                    try:
                        await send_btn.click()
                    except Exception as e:
                        logger.debug(f"点击发送按钮失败，尝试回车发送：{e}")
                        await self.browser.page.keyboard.press("Enter")
                else:
                    await self.browser.page.keyboard.press("Enter")

                await self.browser.page.wait_for_timeout(1000)
                logger.success("发送成功")
                return True, "发送成功"

            return False, "未找到输入框"
            
        except Exception as e:
            logger.error(f"发送回复失败：{e}")
            return False, str(e)
    
    async def auto_reply(self, user_id: str, message: str) -> tuple[bool, str]:
        """
        自动回复
        
        Args:
            user_id: 用户 ID
            message: 收到的消息
            
        Returns:
            (是否成功，回复内容)
        """
        logger.info(f"自动回复 {user_id}: {message[:50]}...")
        
        # 生成回复
        reply = self.generate_reply(message)
        
        # 发送回复
        success, result = await self.send_reply(user_id, reply)
        
        if success:
            logger.success(f"自动回复成功：{reply}")
            return True, reply
        else:
            logger.error(f"自动回复失败：{result}")
            return False, result
    
    def generate_reply(self, message: str, context: Optional[Dict] = None) -> str:
        """
        智能生成回复（带上下文理解）
        
        Args:
            message: 收到的消息
            context: 上下文信息（可选）
            
        Returns:
            回复内容
        """
        message_lower = message.lower()
        
        # 多关键词组合匹配（更智能）
        
        # 1. 问候类
        if any(kw in message_lower for kw in ["在吗", "还在", "还有", "有人吗"]):
            return self.reply_templates["greeting"]
        
        # 2. 价格咨询（结合多个关键词）
        price_keywords = ["价格", "多少钱", "便宜", "贵", "价位"]
        if any(kw in message_lower for kw in price_keywords):
            # 如果提到"最低"，给出底价
            if "最低" in message_lower or "底价" in message_lower:
                return "最低可以给你包邮，不能再少了哦~"
            return self.reply_templates["price_confirm"]
        
        # 3. 运费咨询
        shipping_keywords = ["包邮", "运费", "快递", "邮费", "发货"]
        if any(kw in message_lower for kw in shipping_keywords):
            # 根据地区判断
            if any(area in message_lower for area in ["新疆", "西藏", "内蒙", "甘肃"]):
                return "偏远地区需要补运费差价哦，其他地区都包邮~"
            return self.reply_templates["shipping"]
        
        # 4. 商品状态
        condition_keywords = ["新旧", "几成新", "状态", "用过", "瑕疵", "划痕"]
        if any(kw in message_lower for kw in condition_keywords):
            # 根据具体描述回复
            if "瑕疵" in message_lower or "划痕" in message_lower:
                return "商品很新，没有任何瑕疵，请放心~"
            return self.reply_templates["condition"]
        
        # 5. 地区位置
        location_keywords = ["哪里", "地址", "位置", "在哪", "自提"]
        if any(kw in message_lower for kw in location_keywords):
            location = context.get("location", "上海") if context else "上海"
            if "自提" in message_lower:
                return f"可以自提的，我在{location}，具体地址私聊发你~"
            return self.reply_templates["location"].format(location=location)
        
        # 6. 议价（智能判断）
        bargain_keywords = ["刀", "砍价", "便宜点", "少点", "优惠", "折扣"]
        if any(kw in message_lower for kw in bargain_keywords):
            # 提取具体金额
            import re
            price_match = re.search(r'(\d+)', message)
            if price_match:
                offered_price = int(price_match.group(1))
                # 这里应该获取商品原价，暂时用固定逻辑
                if offered_price >= 100:
                    return f"{offered_price}元有点低，最低{int(offered_price * 1.1)}元可以吗？"
                else:
                    return "这个价格已经很低了，不再议价了哦~"
            else:
                # 没有具体金额
                if "大刀" in message_lower:
                    return "抱歉，小刀可以，大刀不行~"
                elif "小刀" in message_lower:
                    return "小刀可以，你说个价格~"
                else:
                    return "可以小刀，你说个心理价位~"
        
        # 7. 是否卖出
        if any(kw in message_lower for kw in ["卖出", "卖掉", "还有吗", "没了"]):
            return "还在的，可以直接拍~"
        
        # 8. 能否退换
        if any(kw in message_lower for kw in ["退换", "退货", "换货", "售后"]):
            return "个人闲置物品，非真假问题不退换，请理解~"
        
        # 9. 能否见面交易
        if any(kw in message_lower for kw in ["见面", "面交", "当面"]):
            return "可以面交的，约个方便的时间地点~"
        
        # 10. 默认回复（友好）
        default_replies = [
            "你好，有什么可以帮你的吗？😊",
            "在的，请问想了解什么呢？",
            "你好呀，商品详情都在页面上哦~",
        ]
        import random
        return random.choice(default_replies)
    
    def analyze_buyer_intent(self, messages: List[str]) -> Dict[str, float]:
        """
        分析买家意向
        
        Args:
            messages: 消息历史
            
        Returns:
            意向分析结果
        """
        intent_scores = {
            "price_sensitivity": 0.0,  # 价格敏感度
            "purchase_intent": 0.0,     # 购买意向
            "urgency": 0.0,             # 紧急程度
        }
        
        all_text = " ".join(messages).lower()
        
        # 价格敏感度
        price_keywords = ["便宜", "贵", "刀", "砍价", "优惠", "折扣"]
        price_count = sum(1 for kw in price_keywords if kw in all_text)
        intent_scores["price_sensitivity"] = min(price_count * 0.2, 1.0)
        
        # 购买意向
        purchase_keywords = ["拍", "买", "要", "下单", "怎么买", "链接"]
        purchase_count = sum(1 for kw in purchase_keywords if kw in all_text)
        intent_scores["purchase_intent"] = min(purchase_count * 0.3, 1.0)
        
        # 紧急程度
        urgency_keywords = ["急", "马上", "今天", "现在", "尽快"]
        urgency_count = sum(1 for kw in urgency_keywords if kw in all_text)
        intent_scores["urgency"] = min(urgency_count * 0.3, 1.0)
        
        return intent_scores
    
    async def get_unread_count(self) -> int:
        """
        获取未读消息数
        
        Returns:
            未读消息数
        """
        if not self.browser.page:
            return 0
        
        try:
            await self._ensure_im_page()

            api_total = self._get_unread_count_from_api_cache()
            if api_total is not None:
                return api_total

            if self._im_block_reason:
                logger.warning(self._im_block_reason)
                return 0

            # 查找未读标记
            unread_els = await self.browser.page.query_selector_all(
                ".ant-badge-count, [class*='badge-count'], [class*='conversation-item'] sup"
            )
            total = 0
            
            for el in unread_els:
                try:
                    text = await el.inner_text()
                    match = re.search(r"\d+", text)
                    if match:
                        total += int(match.group())
                except:
                    continue
            
            return total
            
        except Exception as e:
            logger.error(f"获取未读数失败：{e}")
            return 0
    
    async def mark_as_read(self, conversation_id: str) -> bool:
        """
        标记为已读
        
        Args:
            conversation_id: 会话 ID
            
        Returns:
            是否成功
        """
        logger.info(f"标记会话 {conversation_id} 为已读")
        try:
            await self._open_conversation(conversation_id)
            await self.browser.page.wait_for_timeout(1000)
            return True
        except Exception as e:
            logger.error(f"标记已读失败：{e}")
            return False

    def _parse_time_text(self, text: str) -> Optional[datetime]:
        """解析消息页常见的时间文本。"""
        text = text.strip()
        if not text:
            return None

        now = datetime.now()
        patterns = [
            (r"^\d{2}-\d{2}$", lambda v: datetime.strptime(f"{now.year}-{v}", "%Y-%m-%d")),
            (r"^\d{2}-\d{2}\s+\d{2}:\d{2}$", lambda v: datetime.strptime(f"{now.year}-{v}", "%Y-%m-%d %H:%M")),
            (r"^\d{4}-\d{2}-\d{2}$", lambda v: datetime.strptime(v, "%Y-%m-%d")),
            (r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$", lambda v: datetime.strptime(v, "%Y-%m-%d %H:%M")),
        ]

        for pattern, parser in patterns:
            if re.match(pattern, text):
                try:
                    return parser(text)
                except ValueError:
                    return None

        if text.endswith("小时前"):
            match = re.search(r"(\d+)", text)
            if match:
                return now.replace(minute=0, second=0, microsecond=0)

        return None
