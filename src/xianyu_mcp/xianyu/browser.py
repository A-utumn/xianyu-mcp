"""
浏览器管理模块

负责浏览器的启动、关闭、页面导航等功能
"""

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pathlib import Path
from loguru import logger
from typing import Optional

from ..config import settings


class XianyuBrowser:
    """闲鱼浏览器管理类"""
    
    def __init__(
        self,
        user_data_dir: Optional[Path] = None,
        headless: Optional[bool] = None
    ):
        """
        初始化浏览器
        
        Args:
            user_data_dir: 用户数据目录（用于保存 Cookie 和登录状态）
            headless: 是否无头模式
        """
        self.user_data_dir = user_data_dir or settings.user_data_dir
        self.headless = headless if headless is not None else settings.headless
        self.browser: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        
        logger.info(f"初始化浏览器 - 用户数据目录：{self.user_data_dir}, 无头模式：{self.headless}")
    
    async def launch(self) -> None:
        """启动浏览器"""
        try:
            logger.info("正在启动浏览器...")
            
            # 确保用户数据目录存在
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            
            # 启动 Playwright
            self._playwright = await async_playwright().start()
            
            # 启动浏览器（使用持久化上下文）
            self.browser = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                viewport={
                    "width": settings.viewport_width,
                    "height": settings.viewport_height
                },
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                accept_downloads=True,
                args=[
                    "--disable-blink-features=AutomationControlled",  # 反检测
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            
            # 获取默认页面
            self.page = self.browser.pages[0]
            
            # 注入反检测脚本
            await self._inject_stealth_script()
            
            logger.info("浏览器启动成功")
            
        except Exception as e:
            logger.error(f"浏览器启动失败：{e}")
            await self.close()
            raise
    
    async def _inject_stealth_script(self) -> None:
        """注入反检测脚本"""
        if self.page:
            await self.page.add_init_script("""
                // 隐藏 webdriver 特征
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // 隐藏自动化特征
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });
            """)
            logger.debug("已注入反检测脚本")
    
    async def goto_xianyu(self) -> None:
        """打开闲鱼网页"""
        if not self.page:
            raise RuntimeError("浏览器未启动")
        
        logger.info(f"正在打开闲鱼：{settings.xianyu_url}")
        await self.page.goto(settings.xianyu_url, wait_until="networkidle", timeout=settings.page_load_timeout * 1000)
        logger.info("闲鱼页面加载完成")
    
    async def goto(self, url: str) -> None:
        """
        导航到指定 URL
        
        Args:
            url: 目标 URL
        """
        if not self.page:
            raise RuntimeError("浏览器未启动")
        
        logger.info(f"正在导航到：{url}")
        await self.page.goto(url, wait_until="networkidle", timeout=settings.page_load_timeout * 1000)
    
    async def screenshot(self, path: str) -> None:
        """
        截图
        
        Args:
            path: 保存路径
        """
        if not self.page:
            raise RuntimeError("浏览器未启动")
        
        await self.page.screenshot(path=path)
        logger.info(f"截图已保存到：{path}")
    
    async def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("浏览器上下文已关闭")
            
            if self._playwright:
                await self._playwright.stop()
                logger.info("Playwright 已停止")
            
            self.browser = None
            self.page = None
            self._playwright = None
            
        except Exception as e:
            logger.error(f"关闭浏览器时出错：{e}")
    
    async def __aenter__(self):
        """异步上下文管理器 - 进入"""
        await self.launch()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器 - 退出"""
        await self.close()
