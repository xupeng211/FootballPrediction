"""
V41.350 Browser Manager - Production-Grade Browser Singleton
============================================================

Migrated from V41.291 Hardware Exorcist - Core browser management logic.

Core improvements:
- All workers share ONE Browser instance (memory reduction: 1.2GB -> ~300MB)
- Each match uses isolated BrowserContext
- Anti-modal script injection
- Connection pool support

Usage:
    from src.scrapers import BrowserManager

    manager = BrowserManager(proxy_port=7892)
    await manager.initialize()

    # Create context for each worker
    context = await manager.create_context()
    page = await context.new_page()

    # Cleanup context (preserve browser)
    await manager.cleanup_context(context)

    # Cleanup browser once at end
    await manager.cleanup()

Author: V41.350 SRE Team
Version: V41.350 "The Great Consolidation"
Migrated from: V41.291 "Hardware Exorcist"
"""

from __future__ import annotations

import logging

from playwright.async_api import Browser, BrowserContext, async_playwright

from src.config_unified import get_config

logger = logging.getLogger("BrowserManager")


# =============================================================================
# V41.350 Browser Manager (Singleton)
# =============================================================================


class BrowserManager:
    """
    V41.350: Browser Manager (Singleton Pattern)

    Core improvements:
    - All workers share ONE Browser instance
    - Each match uses isolated BrowserContext
    - Memory usage reduced from 1.2GB to ~300MB

    Configuration (from harvester_settings.json):
    - proxy_port: Default 7892
    - headless: Default True
    - disable_gpu: Default True (memory optimization)
    """

    def __init__(self, proxy_port: int = 7892, headless: bool = True, disable_gpu: bool = True):
        self.settings = get_config()
        self.proxy_port = proxy_port
        self.headless = headless
        self.disable_gpu = disable_gpu

        # Singleton instance
        self.playwright = None
        self.browser: Browser | None = None

        # Statistics
        self.context_count = 0
        self.page_count = 0

        # Initialization flag
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize global Browser (once only)

        V41.350: This method is idempotent - safe to call multiple times.
        """
        if self._initialized:
            logger.debug("Browser already initialized")
            return

        logger.info("V41.350: Initializing BROWSER SINGLETON (shared by all workers)")

        proxy_config = {
            "server": f"http://{self.settings.proxy.wsl2_bridge_host}:{self.proxy_port}"
        }

        self.playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

        # V41.291: Disable GPU to reduce memory
        if self.disable_gpu:
            launch_args.append("--disable-gpu")

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            proxy=proxy_config,
            args=launch_args,
        )

        self._initialized = True
        logger.info("V41.350: Browser singleton initialized - READY FOR WORKERS")

    async def create_context(
        self,
        viewport: dict | None = None,
        user_agent: str | None = None,
        locale: str = "en-US",
        timezone_id: str = "Europe/London",
    ) -> BrowserContext:
        """
        Create isolated BrowserContext for single worker

        Each Context has independent Cookie/Cache/Session,
        but shares underlying Browser process (saves memory)

        Args:
            viewport: Viewport size (default: 1920x1080)
            user_agent: User agent string
            locale: Browser locale (default: en-US)
            timezone_id: Timezone ID (default: Europe/London)

        Returns:
            BrowserContext: Isolated context for scraping
        """
        if not self._initialized or self.browser is None:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        if viewport is None:
            viewport = {"width": 1920, "height": 1080}

        if user_agent is None:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

        context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale=locale,
            timezone_id=timezone_id,
            java_script_enabled=True,
        )

        # V41.281: Inject anti-modal script
        await self._inject_anti_modal_script(context)

        self.context_count += 1
        logger.debug(f"V41.350: Context #{self.context_count} created")

        return context

    async def _inject_anti_modal_script(self, context: BrowserContext) -> None:
        """
        Inject anti-modal script to Context

        V41.281: Remove cookie banners, consent modals, and popups
        """
        anti_modal_script = """
        (function() {
            'use strict';
            const modalSelectors = [
                '[id*="cookie"]', '[class*="cookie"]',
                '[id*="consent"]', '[class*="consent"]',
                '[role="dialog"]', '[role="alertdialog"]',
                '.modal', '.popup', '.overlay'
            ];
            function removeModals() {
                modalSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        el.style.display = 'none !important';
                        el.remove();
                    });
                });
            }
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            const element = node;
                            modalSelectors.forEach(selector => {
                                if (element.matches && element.matches(selector)) {
                                    element.style.display = 'none !important';
                                    element.remove();
                                }
                            });
                        }
                    });
                });
            });
            removeModals();
            observer.observe(document.documentElement, {childList: true, subtree: true});
            console.log('[V41.350] Anti-modal script injected');
        })();
        """
        await context.add_init_script(anti_modal_script)
        logger.debug("V41.350: Anti-modal script injected")

    async def inject_consent_cookie(
        self,
        context: BrowserContext,
        url: str,
        cookie_name: str = "OptanonAlertBoxClosed",
        cookie_value: str = "2024-01-01T00:00:00.000Z",
    ) -> None:
        """
        Inject consent cookie to bypass cookie banners

        Args:
            context: BrowserContext instance
            url: Target URL (for domain extraction)
            cookie_name: Cookie name (default: OptanonAlertBoxClosed)
            cookie_value: Cookie value (default: past date to dismiss banner)
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path

        await context.add_cookies(
            [
                {
                    "name": cookie_name,
                    "value": cookie_value,
                    "domain": domain,
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax",
                }
            ]
        )
        logger.debug(f"V41.350: Consent cookie injected for {domain}")

    async def cleanup_context(self, context: BrowserContext) -> None:
        """
        Cleanup single Context

        V41.350: This preserves the global Browser instance.
        """
        try:
            await context.close()
            logger.debug("V41.350: Context closed")
        except Exception as e:
            logger.warning(f"V41.350: Context cleanup warning: {e}")

    async def cleanup(self) -> None:
        """
        Cleanup global Browser (call once at program end)

        V41.350: This should be called once when shutting down the application.
        """
        logger.info("V41.350: Cleaning up BROWSER SINGLETON...")

        if self.browser:
            try:
                if self.browser.is_connected():
                    await self.browser.close()
                logger.info(f"V41.350: Browser closed (served {self.context_count} contexts)")
            except Exception as e:
                logger.warning(f"V41.350: Browser cleanup warning: {e}")
            finally:
                self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
                logger.info("V41.350: Playwright stopped")
            except Exception as e:
                logger.warning(f"V41.350: Playwright cleanup warning: {e}")
            finally:
                self.playwright = None

        self._initialized = False
        logger.info("V41.350: Browser singleton cleanup complete")

    @property
    def is_initialized(self) -> bool:
        """Check if browser is initialized"""
        return self._initialized and self.browser is not None


# =============================================================================
# V41.350 Browser Context Manager (Helper)
# =============================================================================


class BrowserContextManager:
    """
    V41.350: Context Manager Helper

    Convenient context manager for temporary browser contexts.

    Usage:
        async with BrowserContextManager(browser_manager) as (context, page):
            await page.goto("https://example.com")
            # ... do scraping
        # Context automatically cleaned up
    """

    def __init__(self, browser_manager: BrowserManager, url: str | None = None):
        self.browser_manager = browser_manager
        self.url = url
        self.context: BrowserContext | None = None
        self.page = None

    async def __aenter__(self):
        self.context = await self.browser_manager.create_context()

        # Inject consent cookie if URL provided
        if self.url:
            await self.browser_manager.inject_consent_cookie(self.context, self.url)

        self.page = await self.context.new_page()
        return self.context, self.page

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            try:
                if not self.page.is_closed():
                    await self.page.close()
            except Exception:
                pass

        if self.context:
            await self.browser_manager.cleanup_context(self.context)
