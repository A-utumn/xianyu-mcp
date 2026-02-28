"""
登录模块

负责闲鱼账号的扫码登录、Cookie 管理、登录状态检测
"""

import json
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Optional

from .browser import XianyuBrowser
from ..config import settings


class XianyuLogin:
    """闲鱼登录管理类"""
    
    def __init__(self, browser: XianyuBrowser, cookie_file: Optional[Path] = None):
        """
        初始化登录管理
        
        Args:
            browser: 浏览器实例
            cookie_file: Cookie 文件路径
        """
        self.browser = browser
        self.cookie_file = cookie_file or settings.cookie_file
        
        logger.info(f"初始化登录管理 - Cookie 文件：{self.cookie_file}")
    
    async def login_with_qrcode(self, timeout: int = 60) -> bool:
        """
        扫码登录
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否登录成功
        """
        logger.info("开始扫码登录流程...")
        
        try:
            # 打开闲鱼首页
            await self.browser.goto_xianyu()
            
            # 等待页面加载
            await self.browser.page.wait_for_timeout(3000)
            
            logger.info("请在手机上打开闲鱼 APP 扫码登录...")
            logger.info(f"超时时间：{timeout}秒")
            
            # 等待登录（检测登录状态）
            start_time = datetime.now()
            while (datetime.now() - start_time).total_seconds() < timeout:
                # 检查是否已登录
                is_logged_in = await self.check_login_status()
                if is_logged_in:
                    logger.success("扫码登录成功！")
                    
                    # 保存 Cookie
                    await self.save_cookies()
                    return True
                
                # 等待一段时间后再次检查
                await self.browser.page.wait_for_timeout(2000)
            
            logger.error("扫码登录超时")
            return False
            
        except Exception as e:
            logger.error(f"扫码登录失败：{e}")
            return False
    
    async def check_login_status(self) -> bool:
        """
        检查登录状态
        
        Returns:
            bool: 是否已登录
        """
        if not self.browser.page:
            return False
        
        try:
            # 方法 1: 检查页面是否包含登录标识
            page_content = await self.browser.page.content()
            
            # 检查是否包含"我的"或用户信息（根据实际页面调整）
            if "我的" in page_content or "退出" in page_content:
                logger.info("检测到登录状态（页面内容）")
                return True
            
            # 方法 2: 检查 Cookie
            cookies = await self.browser.page.context.cookies()
            token_cookies = [c for c in cookies if "token" in c.get("name", "").lower()]
            
            if token_cookies:
                logger.info("检测到登录 Token")
                return True
            
            logger.debug("未检测到登录状态")
            return False
            
        except Exception as e:
            logger.error(f"检查登录状态失败：{e}")
            return False
    
    async def save_cookies(self) -> bool:
        """
        保存 Cookie 到文件
        
        Returns:
            bool: 是否保存成功
        """
        try:
            if not self.browser.page:
                logger.error("浏览器未启动，无法保存 Cookie")
                return False
            
            # 获取 Cookie
            cookies = await self.browser.page.context.cookies()
            
            # 确保目录存在
            self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存 Cookie
            cookie_data = {
                "cookies": cookies,
                "login_time": datetime.now().isoformat(),
                "user_agent": await self.browser.page.evaluate("navigator.userAgent"),
            }
            
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            logger.success(f"Cookie 已保存到：{self.cookie_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存 Cookie 失败：{e}")
            return False
    
    async def load_cookies(self) -> bool:
        """
        从文件加载 Cookie
        
        Returns:
            bool: 是否加载成功
        """
        try:
            if not self.cookie_file.exists():
                logger.info("Cookie 文件不存在")
                return False
            
            # 读取 Cookie
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            
            cookies = cookie_data.get("cookies", [])
            if not cookies:
                logger.warning("Cookie 文件为空")
                return False
            
            # 添加 Cookie 到浏览器
            await self.browser.page.context.add_cookies(cookies)
            
            logger.success(f"Cookie 已从 {self.cookie_file} 加载")
            return True
            
        except Exception as e:
            logger.error(f"加载 Cookie 失败：{e}")
            return False
    
    async def logout(self) -> bool:
        """
        退出登录（删除 Cookie 文件）
        
        Returns:
            bool: 是否成功
        """
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                logger.info("Cookie 文件已删除")
            
            # 清除浏览器 Cookie
            await self.browser.page.context.clear_cookies()
            logger.info("浏览器 Cookie 已清除")
            
            return True
            
        except Exception as e:
            logger.error(f"退出登录失败：{e}")
            return False
    
    async def auto_login(self) -> bool:
        """
        自动登录（优先使用 Cookie，失败则扫码）
        
        Returns:
            bool: 是否登录成功
        """
        logger.info("开始自动登录...")
        
        # 尝试加载 Cookie
        if await self.load_cookies():
            logger.info("尝试使用 Cookie 登录...")
            await self.browser.goto_xianyu()
            
            # 检查 Cookie 是否有效
            if await self.check_login_status():
                logger.success("Cookie 登录成功！")
                return True
            else:
                logger.warning("Cookie 已失效，需要重新登录")
        
        # Cookie 无效，使用扫码登录
        logger.info("使用扫码登录...")
        return await self.login_with_qrcode()
