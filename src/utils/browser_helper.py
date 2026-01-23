"""V41.832: Browser Helper Utilities.

提供 Playwright 浏览器操作的通用辅助方法，包括：
- 分页控制
- 内容锁验证
- 滚动操作
- 元素定位策略

Author: Senior Lead Data Architect
Version: V41.832 "Production Blueprint"
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Final

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.config.crawler_config import ODDSPORTAL_CONFIG

logger = logging.getLogger(__name__)


# Constants
MAX_PAGE_NUMBER: Final[int] = 99


class PaginationStrategy:
    """分页按钮定位策略."""

    TEXT_IS: Final[str] = "text-is"
    HAS_TEXT: Final[str] = "has_text"
    HREF_CONTAINS: Final[str] = "href*"


class BrowserHelper:
    """Playwright 浏览器操作辅助类.

    提供:
    - 分页控制
    - 内容锁验证
    - 滚动操作
    - 多策略元素定位
    """

    def __init__(self, page: Page) -> None:
        """初始化浏览器辅助类.

        Args:
            page: Playwright Page 对象
        """
        self.page = page
        self._current_first_match: str | None = None

    async def scroll_to_bottom(self, max_wait: int = 3) -> bool:
        """滚动到页面底部并等待分页条加载.

        Args:
            max_wait: 最大等待时间（秒）

        Returns:
            是否成功滚动到底部

        Raises:
            PlaywrightTimeoutError: 页面滚动超时
        """
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(max_wait)
            logger.debug("[BrowserHelper][scroll_to_bottom] Scrolled to bottom")
            return True
        except PlaywrightTimeoutError as e:
            logger.warning(f"[BrowserHelper][scroll_to_bottom] Timeout: {e}")
            return False

    async def wait_for_content_lock(
        self,
        min_matches: int = ODDSPORTAL_CONFIG.MIN_MATCHES_PER_PAGE,
        max_wait: int = ODDSPORTAL_CONFIG.CONTENT_LOCK_MAX_WAIT,
    ) -> bool:
        """等待内容填充达到最小比赛数量（内容锁）.

        Args:
            min_matches: 最小比赛数量阈值
            max_wait: 最大等待时间（秒）

        Returns:
            是否达到内容锁条件
        """
        logger.info(
            f"[BrowserHelper][wait_for_content_lock] Waiting for >={min_matches} matches (max {max_wait}s)"
        )

        for i in range(max_wait):
            await asyncio.sleep(1)
            row_count = await self.page.locator(ODDSPORTAL_CONFIG.SELECTOR_EVENT_ROWS).count()
            if row_count >= min_matches:
                logger.info(
                    f"[BrowserHelper][wait_for_content_lock] ✅ Content locked with {row_count} rows"
                )
                return True

        row_count = await self.page.locator(ODDSPORTAL_CONFIG.SELECTOR_EVENT_ROWS).count()
        logger.warning(
            f"[BrowserHelper][wait_for_content_lock] ⚠️ Timeout: only {row_count} rows (expected >={min_matches})"
        )
        return False

    def get_page_button_locator(self, page_num: int) -> Locator:
        """使用多策略定位分页按钮.

        Args:
            page_num: 目标页码

        Returns:
            按钮定位器

        Raises:
            ValueError: 页码无效
        """
        if page_num < 1 or page_num > MAX_PAGE_NUMBER:
            raise ValueError(f"Invalid page number: {page_num}")

        # 策略 1: 精确文本匹配
        selector = (
            f"{ODDSPORTAL_CONFIG.SELECTOR_PAGINATION} a:{PaginationStrategy.TEXT_IS}('{page_num}')"
        )
        locator = self.page.locator(selector)

        logger.debug(f"[BrowserHelper][get_page_button_locator] Using selector: {selector}")
        return locator

    async def click_page_button(
        self,
        page_num: int,
        timeout: int = ODDSPORTAL_CONFIG.CLICK_TIMEOUT,
    ) -> bool:
        """点击分页按钮并等待内容加载.

        Args:
            page_num: 目标页码
            timeout: 点击超时时间（毫秒）

        Returns:
            是否成功点击并加载内容

        Raises:
            PlaywrightTimeoutError: 点击超时
            ValueError: 页码无效
        """
        logger.info(f"[BrowserHelper][click_page_button] Clicking Page {page_num} button")

        try:
            button = self.get_page_button_locator(page_num)
            await button.click(timeout=timeout * 1000)
            logger.info(
                f"[BrowserHelper][click_page_button] ✅ Page {page_num} clicked successfully"
            )
            return True
        except PlaywrightTimeoutError as e:
            logger.warning(
                f"[BrowserHelper][click_page_button] ⚠️ Timeout clicking Page {page_num}: {e}"
            )
            return False

    async def get_first_match_name(self) -> str | None:
        """获取页面第一场比赛的名称（用于 Ghost Detection）.

        Returns:
            第一场比赛名称，未找到返回 None
        """
        try:
            # 只匹配真正的比赛链接（包含 hash）
            pattern = r'<a\s+href="/football/[^/]+/[^-]+-\d{4}-\d{4}/[^"]+-[A-Za-z0-9]{8,10}/"[^>]*>([^<]+)</a>'
            html = await self.page.content()
            match = re.search(pattern, html)
            return match.group(1) if match else None
        except Exception as e:
            logger.warning(f"[BrowserHelper][get_first_match_name] Failed to extract: {e}")
            return None

    @property
    def current_first_match(self) -> str | None:
        """获取当前页第一场比赛名称."""
        return self._current_first_match

    async def detect_ghost_page(self, expected_first_match: str) -> bool:
        """检测是否遇到 Ghost Page（内容未变化的假翻页）.

        Args:
            expected_first_match: 期望的第一场比赛名称

        Returns:
            是否为 Ghost Page
        """
        actual_first_match = await self.get_first_match_name()
        is_ghost = actual_first_match == expected_first_match

        if is_ghost:
            logger.warning(
                f"[BrowserHelper][detect_ghost_page] ⚠️ Ghost Page detected! First match: {actual_first_match}"
            )
        else:
            self._current_first_match = actual_first_match

        return is_ghost
