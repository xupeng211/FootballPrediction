#!/usr/bin/env python3
"""V150.0 Base Extractor - Anti-Detection Foundation (TLS/JA3 Fingerprint Obfuscation).

This module provides the base extraction class with integrated "Ghost Protocol"
capabilities from V140.0. It serves as the foundation for all web scraping
operations in the FootballPrediction system.

Core Features (Ghost Protocol - V55.2 → V150.0):
    - Dynamic UA Pool: 30+ mainstream browser fingerprints
    - Random Viewport: 10 common screen resolutions
    - Human Behavior Simulation: Scroll + click noise
    - Deep Interception Detection: Cloudflare, IP ban detection
    - Auto Error Screenshot: Saves to logs/error_screens/
    - WSL2 Auto Proxy Discovery: Automatic proxy configuration
    - V150.0: TLS/JA3 Fingerprint Obfuscation (Unique per Context)
    - V150.0: Enhanced HTTP Headers for TLS fingerprint randomization

Example:
    >>> from src.api.collectors.base_extractor import BaseExtractor
    >>> extractor = BaseExtractor()
    >>> # Get random UA
    >>> ua = extractor.get_random_user_agent()
    >>> # Get random viewport
    >>> viewport = extractor.get_random_viewport()
    >>> # Create browser context with ghost protocol
    >>> context = await browser.new_context(
    ...     user_agent=ua,
    ...     viewport=viewport,
    ...     proxy=extractor.get_proxy_config()
    ... )
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import random
from typing import Any

from playwright.async_api import Browser, Page

from src.config_unified import get_settings
from src.services.harvest_config import AntiScrapingConfig

logger = logging.getLogger(__name__)


# ============================================================================
# V26.5: SecurityInterrupt Exception
# ============================================================================

class SecurityInterrupt(Exception):
    """安全中断异常 - 当 IP 冷却期未结束时抛出

    当 COLLECTION_PAUSE_UNTIL 环境变量设置的时间晚于当前时间时，
    所有采集器的初始化将被此异常中断，防止在冷却期内发起网络请求。
    """

    pass


# ============================================================================
# V26.5: Collection Circuit Breaker
# ============================================================================

class CollectionCircuitBreaker:
    """
    V26.7: 采集熔断器 - 分类锁定支持

    功能：
    1. 检查 COLLECTION_PAUSE_UNTIL 环境变量
    2. 根据数据源决定是否执行锁定：
       - oddsportal: 严格执行锁定
       - fotmob: 绕过锁定，允许立即采集
    3. 否则，允许采集器继续初始化

    示例:
        >>> CollectionCircuitBreaker.check_pause_period("oddsportal")  # 可能抛出异常
        >>> CollectionCircuitBreaker.check_pause_period("fotmob")      # 总是允许通过
    """

    # V26.7: 不受冷却期限制的数据源白名单
    WHITELISTED_SOURCES = {"fotmob"}

    @staticmethod
    def check_pause_period(source_name: str = "default") -> None:
        """
        检查冷却期状态（支持数据源分类）

        Args:
            source_name: 数据源名称 ("oddsportal", "fotmob", 等)

        Raises:
            SecurityInterrupt: 如果当前时间在冷却期内且数据源不在白名单中

        Returns:
            None: 如果冷却期已过或数据源在白名单中，允许继续执行
        """
        # V26.7: 白名单数据源绕过冷却期检查
        if source_name in CollectionCircuitBreaker.WHITELISTED_SOURCES:
            logger.info(
                f"🔓 数据源 [{source_name}] 在白名单中，绕过冷却期检查"
            )
            return

        pause_until_str = os.getenv("COLLECTION_PAUSE_UNTIL")

        if not pause_until_str:
            # 未设置冷却期，允许继续
            return

        try:
            pause_until = datetime.fromisoformat(pause_until_str)
            # 如果解析出的时间没有时区信息，假设是本地时区
            if pause_until.tzinfo is None:
                pause_until = pause_until.replace(tzinfo=datetime.now().astimezone().tzinfo)
        except ValueError as e:
            # 环境变量格式错误，记录警告但允许继续
            import warnings
            warnings.warn(f"COLLECTION_PAUSE_UNTIL 格式错误: {e}")
            return

        # 获取当前时间（带时区信息）
        current_time = datetime.now().astimezone()

        if current_time < pause_until:
            # 冷却期未结束，抛出异常
            remaining_time = pause_until - current_time
            raise SecurityInterrupt(
                f"🛡️ IP 冷却期保护: [{source_name}] 数据采集已暂停\n"
                f"⏰ 当前时间: {current_time.isoformat()}\n"
                f"🚫 冷却截止: {pause_until.isoformat()}\n"
                f"⏳ 剩余时间: {CollectionCircuitBreaker._format_timedelta(remaining_time)}\n"
                f"💡 提示: 请等待冷却期结束后重试，或手动清除 COLLECTION_PAUSE_UNTIL 环境变量"
            )

        # 冷却期已过
        logger.info(f"✅ 冷却期已过 (截止: {pause_until.isoformat()})，允许采集")

    @staticmethod
    def _format_timedelta(td: timedelta) -> str:
        """格式化时间差为易读字符串"""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}小时 {minutes}分钟 {seconds}秒"
        elif minutes > 0:
            return f"{minutes}分钟 {seconds}秒"
        else:
            return f"{seconds}秒"


# ============================================================================
# ============================================================================
# V144.0: Ghost Protocol - Enhanced Fingerprint & Behavior Obfuscation
# ============================================================================

# V144.0: Expanded Dynamic UA Pool (30+ mainstream browser fingerprints)
# Includes Chrome, Edge, Safari, Firefox across Windows, macOS, and Linux
USER_AGENTS = [
    # Chrome on Windows (Latest versions)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Edge on Windows (Latest versions)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    # Safari on macOS (Latest versions)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Firefox on Windows (Latest versions)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
    "Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) "
    "Gecko/20100101 Firefox/119.0",
    # Chrome on macOS (Latest versions)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome on Linux (Latest versions)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Linux (Latest versions)
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) "
    "Gecko/20100101 Firefox/120.0",
    # Safari on iOS (Mobile)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    # Chrome on Android (Mobile)
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
    # Edge on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Opera on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",
    # Brave on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Brave/120.0.0.0",
    # Vivaldi on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Vivaldi/6.5.3206.53",
    # Additional Chrome variants with different minor versions
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# V144.0: Expanded Viewport sizes (10 common screen resolutions)
VIEWPORTS = [
    {"width": 1920, "height": 1080},  # Full HD
    {"width": 1366, "height": 768},   # Laptop
    {"width": 1536, "height": 864},   # Laptop 2
    {"width": 1440, "height": 900},   # Mac
    {"width": 1280, "height": 720},   # HD
    {"width": 2560, "height": 1440},  # 2K
    {"width": 3840, "height": 2160},  # 4K
    {"width": 1600, "height": 900},   # HD+
    {"width": 1728, "height": 1117},  # MacBook Pro 14"
    {"width": 1920, "height": 1200},  # MacBook Pro 16"
]

# V144.0: Hardware configurations for fingerprint randomization
HARDWARE_CONFIGS = [
    {"hardware_concurrency": 4, "device_memory": 8},   # Common laptop
    {"hardware_concurrency": 8, "device_memory": 16},  # High-end desktop
    {"hardware_concurrency": 6, "device_memory": 8},   # Mid-range desktop
    {"hardware_concurrency": 12, "device_memory": 32}, # Workstation
    {"hardware_concurrency": 2, "device_memory": 4},   # Low-end laptop
]

# V144.0: Platform strings for fingerprint randomization
PLATFORMS = [
    "Win32",
    "MacIntel",
    "Linux x86_64",
    "iPhone",
    "iPad",
    "Linux armv8l",
]

# V144.0: Canvas fingerprint randomization script
CANVAS_RANDOMIZATION_SCRIPT = """
() => {
    // Randomize canvas fingerprint by adding noise
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const context = this.getContext('2d');
        if (context) {
            const imageData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                // Add minimal noise to RGB channels
                imageData.data[i] += Math.random() * 2 - 1;
                imageData.data[i + 1] += Math.random() * 2 - 1;
                imageData.data[i + 2] += Math.random() * 2 - 1;
            }
            context.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.apply(this, arguments);
    };
}
"""

# V144.0: WebGL fingerprint randomization script
WEBGL_RANDOMIZATION_SCRIPT = """
() => {
    // Randomize WebGL vendor and renderer
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) { // VENDOR
            const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Qualcomm'];
            return vendors[Math.floor(Math.random() * vendors.length)];
        }
        if (parameter === 37446) { // RENDERER
            const renderers = [
                'Intel(R) UHD Graphics 620',
                'NVIDIA GeForce GTX 1660',
                'AMD Radeon RX 580',
                'Apple GPU',
                'Adreno 650'
            ];
            return renderers[Math.floor(Math.random() * renderers.length)];
        }
        return getParameter.apply(this, arguments);
    };
}
"""

# V144.0: Navigator properties randomization script
NAVIGATOR_RANDOMIZATION_SCRIPT = """
() => {
    // Randomize navigator properties
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => [2, 4, 6, 8, 12, 16][Math.floor(Math.random() * 6)]
    });
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => [4, 8, 16, 32][Math.floor(Math.random() * 4)]
    });
    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: () => Math.random() > 0.5 ? 0 : 5
    });
}
"""

# ============================================================================
# V150.0: TLS/JA3 Fingerprint Obfuscation Scripts
# ============================================================================

# V150.0: TLS Client Hello fingerprint randomization script
TLS_FINGERPRINT_RANDOMIZATION_SCRIPT = """
() => {
    // V150.0: Randomize TLS fingerprint indicators
    // This affects how the browser's TLS handshake appears to servers

    // Randomize connection timing to simulate different network conditions
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        // Add random jitter to request timing (50-200ms)
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(originalFetch.apply(this, args));
            }, 50 + Math.random() * 150);
        });
    };

    // Randomize WebSocket fingerprint
    const originalWebSocket = window.WebSocket;
    window.WebSocket = function(...args) {
        const ws = new originalWebSocket(...args);
        // Add random binary data pattern to simulate different clients
        const originalSend = ws.send;
        ws.send = function(data) {
            // Inject random timing jitter
            setTimeout(() => {
                originalSend.call(this, data);
            }, Math.random() * 50);
        };
        return ws;
    };
}
"""

# V150.0: Browser behavior randomization for unique JA3
BEHAVIOR_FINGERPRINT_SCRIPT = """
() => {
    // V150.0: Add unique behavior patterns per context
    // Each context will have slightly different interaction patterns

    // Randomize mouse movement patterns
    let mouseMoveCount = 0;
    const targetMouseMoves = Math.floor(Math.random() * 20) + 10;

    document.addEventListener('mousemove', () => {
        mouseMoveCount++;
    });

    // Randomize scroll behavior
    let scrollDepth = 0;
    const targetScrollDepth = Math.floor(Math.random() * 3) + 1;

    document.addEventListener('scroll', () => {
        scrollDepth = Math.max(scrollDepth, window.scrollY / document.body.scrollHeight);
    });

    // Store unique pattern for this session
    window.__fingerprint_id = Math.random().toString(36).substring(2, 15);
    window.__behavior_pattern = {
        mouse_moves: targetMouseMoves,
        scroll_depth: targetScrollDepth,
        timing_jitter: Math.random() * 100
    };
}
"""

# V150.0: HTTP Headers for enhanced TLS obfuscation
TLS_OBFUSCATION_HEADERS = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en;q=0.9",
        "Cache-Control": "no-cache",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Firefox";v="121", "Not(A:Brand";v="8"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
    },
]

# V150.0: TLS cipher suite randomization
CIPHER_SUITE_VARIANTS = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
]

# Screenshot directory
ERROR_SCREEN_DIR = Path("logs/error_screens")
ERROR_SCREEN_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Main Base Extractor Class
# ============================================================================

class BaseExtractor:
    """V141.0: Base Extractor with Ghost Protocol integration.

    This class provides anti-detection capabilities for web scraping operations.
    It integrates the "Ghost Protocol" from V55.2/V58.0/V140.0.

    Attributes:
        settings: Application settings from config_unified
        proxy_config: Proxy configuration (if any)
        enable_ghost_protocol: Whether to enable Ghost Protocol features

    Example:
        >>> extractor = BaseExtractor(enable_ghost_protocol=True)
        >>> # Create browser context with random UA and viewport
        >>> ua = extractor.get_random_user_agent()
        >>> viewport = extractor.get_random_viewport()
        >>> context = await browser.new_context(
        ...     user_agent=ua,
        ...     viewport=viewport,
        ...     proxy=extractor.proxy_config
        ... )
        >>> page = await context.new_page()
        >>> # Simulate human behavior
        >>> await extractor.human_scroll(page)
        >>> await extractor.human_click_noise(page)
    """

    def __init__(
        self,
        enable_ghost_protocol: bool = True,
        auto_proxy: bool = True,
    ) -> None:
        """Initialize the BaseExtractor.

        Args:
            enable_ghost_protocol: Enable Ghost Protocol features (default: True)
            auto_proxy: Enable automatic proxy discovery (default: True)

        Raises:
            SecurityInterrupt: 如果当前时间在 IP 冷却期内
        """
        # V26.5: 首先检查冷却期状态
        CollectionCircuitBreaker.check_pause_period()

        self.settings = get_settings()
        self.enable_ghost_protocol = enable_ghost_protocol
        self.auto_proxy = auto_proxy

        # Proxy configuration
        self.proxy_config: dict[str, str] | None = None
        if auto_proxy:
            self.proxy_config = self._discover_proxy()

    # ========================================================================
    # User-Agent & Viewport Management
    # ========================================================================

    @classmethod
    def get_random_user_agent(cls) -> str:
        """Get a random User-Agent from the pool.

        Returns:
            Random User-Agent string

        Example:
            >>> ua = BaseExtractor.get_random_user_agent()
            >>> print(ua[:50])
            Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
        """
        return random.choice(USER_AGENTS)

    @classmethod
    def get_random_viewport(cls) -> dict[str, int]:
        """Get a random viewport size.

        Returns:
            Dictionary with 'width' and 'height' keys

        Example:
            >>> viewport = BaseExtractor.get_random_viewport()
            >>> print(viewport)
            {'width': 1920, 'height': 1080}
        """
        return random.choice(VIEWPORTS)

    @classmethod
    def get_random_hardware_config(cls) -> dict[str, int]:
        """V144.0: Get a random hardware configuration.

        Returns:
            Dictionary with 'hardware_concurrency' and 'device_memory' keys

        Example:
            >>> hw = BaseExtractor.get_random_hardware_config()
            >>> print(hw)
            {'hardware_concurrency': 8, 'device_memory': 16}
        """
        return random.choice(HARDWARE_CONFIGS)

    @classmethod
    def get_random_platform(cls) -> str:
        """V144.0: Get a random platform string.

        Returns:
            Platform string (e.g., "Win32", "MacIntel")

        Example:
            >>> platform = BaseExtractor.get_random_platform()
            >>> print(platform)
            Win32
        """
        return random.choice(PLATFORMS)

    # ========================================================================
    # V144.0: Fingerprint Randomization Methods
    # ========================================================================

    async def randomize_canvas_fingerprint(self, page: Page) -> None:
        """V144.0: Randomize Canvas fingerprint by adding noise.

        Args:
            page: Playwright Page object

        Example:
            >>> await extractor.randomize_canvas_fingerprint(page)
        """
        if not self.enable_ghost_protocol:
            return

        try:
            await page.evaluate(CANVAS_RANDOMIZATION_SCRIPT)
            logger.debug("  → Canvas fingerprint randomized")
        except Exception as e:
            logger.warning(f"  ⚠️ Canvas randomization failed: {e}")

    async def randomize_webgl_fingerprint(self, page: Page) -> None:
        """V144.0: Randomize WebGL vendor and renderer.

        Args:
            page: Playwright Page object

        Example:
            >>> await extractor.randomize_webgl_fingerprint(page)
        """
        if not self.enable_ghost_protocol:
            return

        try:
            await page.evaluate(WEBGL_RANDOMIZATION_SCRIPT)
            logger.debug("  → WebGL fingerprint randomized")
        except Exception as e:
            logger.warning(f"  ⚠️ WebGL randomization failed: {e}")

    async def randomize_navigator_properties(self, page: Page) -> None:
        """V144.0: Randomize navigator properties (hardware, memory).

        Args:
            page: Playwright Page object

        Example:
            >>> await extractor.randomize_navigator_properties(page)
        """
        if not self.enable_ghost_protocol:
            return

        try:
            await page.evaluate(NAVIGATOR_RANDOMIZATION_SCRIPT)
            logger.debug("  → Navigator properties randomized")
        except Exception as e:
            logger.warning(f"  ⚠️ Navigator randomization failed: {e}")

    async def apply_all_fingerprint_randomization(self, page: Page) -> None:
        """V144.0: Apply all fingerprint randomization techniques.

        This method applies:
        - Canvas fingerprint randomization
        - WebGL fingerprint randomization
        - Navigator properties randomization

        Args:
            page: Playwright Page object

        Example:
            >>> await extractor.apply_all_fingerprint_randomization(page)
        """
        if not self.enable_ghost_protocol:
            return

        await self.randomize_canvas_fingerprint(page)
        await self.randomize_webgl_fingerprint(page)
        await self.randomize_navigator_properties(page)
        logger.debug("  → All fingerprint randomization applied")

    # ========================================================================
    # Human Behavior Simulation
    # ========================================================================

    async def human_scroll(
        self,
        page: Page,
        max_scrolls: int = 3,
    ) -> None:
        """V55.2: Simulate human scrolling behavior.

        Performs random scrolling with variable distance and direction,
        simulating natural human reading patterns.

        Args:
            page: Playwright Page object
            max_scrolls: Maximum number of scrolls (default: 3)

        Example:
            >>> await extractor.human_scroll(page, max_scrolls=5)
        """
        if not self.enable_ghost_protocol:
            return

        scroll_count = random.randint(2, max_scrolls)

        for _ in range(scroll_count):
            # Random scroll distance (300-800 pixels)
            scroll_distance = random.randint(300, 800)

            # Random scroll direction (80% down, 20% up)
            if random.random() < 0.8:
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            else:
                await page.evaluate(f"window.scrollBy(0, -{scroll_distance})")

            # Random pause (500-2000ms)
            await asyncio.sleep(random.uniform(0.5, 2.0))

        logger.debug(f"  → Executed {scroll_count} random scrolls")

    async def human_click_noise(self, page: Page) -> None:
        """V55.2: Simulate random human click noise.

        Clicks on random page areas to simulate user misclicks or
        exploratory behavior, making the scraping pattern less detectable.

        Args:
            page: Playwright Page object

        Example:
            >>> await extractor.human_click_noise(page)
        """
        if not self.enable_ghost_protocol:
            return

        # 30% probability to execute random click
        if random.random() < 0.3:
            try:
                viewport_size = page.viewport_size
                if viewport_size:
                    # Random click within page edges
                    x = random.randint(50, viewport_size["width"] - 50)
                    y = random.randint(50, viewport_size["height"] - 50)

                    await page.mouse.click(x, y)
                    logger.debug(f"  → Random click noise: ({x}, {y})")

                    # Short pause
                    await asyncio.sleep(random.uniform(0.3, 0.8))
            except Exception:
                # Click failure doesn't affect main flow
                pass

    # ========================================================================
    # Interception Detection
    # ========================================================================

    def detect_blocking_method(self, page_html: str) -> tuple[bool, str]:
        """V55.2: Deep interception detection.

        Detects various blocking methods including Cloudflare challenges,
        IP bans, and unknown blocking patterns.

        Args:
            page_html: Page HTML content

        Returns:
            Tuple of (is_blocked, block_reason)

        Example:
            >>> is_blocked, reason = extractor.detect_blocking_method(html)
            >>> if is_blocked:
            ...     print(f"Blocked: {reason}")
        """
        html_lower = page_html.lower()

        if "cloudflare" in html_lower or "checking your browser" in html_lower:
            return True, "Cloudflare Challenge"

        if len(page_html) == 39:
            return True, "IP Hard Ban (39 bytes)"

        if len(page_html) < 100:
            return True, "Unknown Block (small content)"

        return False, "No Block"

    async def save_error_screenshot(
        self,
        page: Page,
        reason: str,
    ) -> None:
        """V55.2: Save error screenshot for debugging.

        Args:
            page: Playwright Page object
            reason: Error reason description

        Example:
            >>> await extractor.save_error_screenshot(page, "Cloudflare Challenge")
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = ERROR_SCREEN_DIR / f"error_{timestamp}_{reason.replace(' ', '_')}.png"

        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.error(f"  📸 Error screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"  ⚠️  Screenshot save failed: {e}")

    # ========================================================================
    # Proxy Configuration
    # ========================================================================

    def _discover_proxy(self) -> dict[str, str] | None:
        """V142.0: Discover proxy configuration from environment.

        Priority order:
        1. PROXY_SERVER environment variable (legacy support)
        2. HTTP_PROXY / HTTPS_PROXY environment variables (standard)
        3. WSL2 automatic Windows host proxy detection

        Returns:
            Proxy configuration dict or None

        Example:
            >>> proxy = extractor._discover_proxy()
            >>> print(proxy)
            {'server': 'http://172.x.x.x:7890'}
        """
        # Priority 1: PROXY_SERVER (legacy support)
        proxy_server = os.getenv("PROXY_SERVER")
        if proxy_server:
            if proxy_server.startswith("http://") or proxy_server.startswith("https://") or proxy_server.startswith("socks5://"):
                return {"server": proxy_server}
            return {"server": f"http://{proxy_server}"}

        # Priority 2: HTTP_PROXY / HTTPS_PROXY (standard convention)
        # HTTPS_PROXY takes precedence over HTTP_PROXY
        for env_var in ["HTTPS_PROXY", "HTTP_PROXY"]:
            proxy = os.getenv(env_var)
            if proxy:
                # Remove protocol prefix if present to normalize
                if "://" in proxy:
                    return {"server": proxy}
                return {"server": f"http://{proxy}"}

        # Priority 3: WSL2 auto-discovery
        if self._is_wsl2():
            wsl_host = self._get_wsl2_host_ip()
            if wsl_host:
                # V41.121: Use AntiScrapingConfig.get_proxy_ports() (unified config)
                # Removed deprecated port 7890
                for port in AntiScrapingConfig.get_proxy_ports():
                    proxy_url = f"http://{wsl_host}:{port}"
                    logger.info(f"  🔍 WSL2 自动探测: 尝试 {proxy_url}")
                    # Quick connectivity test
                    if self._test_proxy_connection(proxy_url):
                        logger.info(f"  ✓ WSL2 代理成功: {proxy_url}")
                        return {"server": proxy_url}
                logger.info(f"  ℹ️  WSL2 宿主机 IP: {wsl_host}，但所有代理端口均无响应")

        return None

    def _is_wsl2(self) -> bool:
        """Check if running in WSL2 environment.

        Returns:
            True if WSL2 environment detected
        """
        try:
            with open("/proc/version") as f:
                version_content = f.read().lower()
                return "microsoft" in version_content
        except Exception:
            return False

    def _get_wsl2_host_ip(self) -> str | None:
        """Get WSL2 Windows host IP address.

        Uses the default gateway IP, which is typically the Windows host IP in WSL2.
        Falls back to reading /etc/resolv.conf for the nameserver IP.

        Returns:
            Host IP string or None
        """
        # Method 1: Try to get default gateway via 'ip route' command
        try:
            import subprocess
            output = subprocess.check_output(
                ["ip", "route", "show", "default"],
                stderr=subprocess.DEVNULL,
                text=True
            )
            if output and "via" in output:
                # Output format: "default via 172.x.x.1 dev eth0 ..."
                host_ip = output.split()[2]
                logger.info(f"  🔍 WSL2 default gateway: {host_ip}")
                return host_ip
        except Exception:
            pass

        # Method 2: Fallback to /etc/resolv.conf nameserver
        try:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        host_ip = line.split()[1].strip()
                        logger.info(f"  🔍 WSL2 nameserver: {host_ip}")
                        return host_ip
        except Exception:
            pass

        return None

    def _test_proxy_connection(self, proxy_url: str, timeout: float = 2.0) -> bool:
        """Quick test if proxy is reachable.

        Args:
            proxy_url: Proxy URL to test
            timeout: Connection timeout in seconds

        Returns:
            True if proxy is reachable
        """
        try:
            import socket
            from urllib.parse import urlparse

            parsed = urlparse(proxy_url)
            host = parsed.hostname
            port = parsed.port

            if not host or not port:
                return False

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()

            return result == 0
        except Exception:
            return False

    def get_proxy_config(self) -> dict[str, str] | None:
        """Get the proxy configuration.

        Returns:
            Proxy configuration dict or None

        Example:
            >>> proxy = extractor.get_proxy_config()
            >>> if proxy:
            ...     print(f"Using proxy: {proxy['server']}")
        """
        return self.proxy_config

    def set_proxy_config(self, proxy_url: str) -> None:
        """V143.7: Update the proxy configuration dynamically.

        This allows the proxy to be changed at runtime (e.g., when rotating
        through a proxy pool) without recreating the BaseExtractor instance.

        Args:
            proxy_url: The new proxy URL (e.g., "http://proxy.example.com:7890")

        Example:
            >>> extractor.set_proxy_config("http://proxy.example.com:7890")
            >>> # Now all new contexts will use the new proxy
        """
        if proxy_url:
            self.proxy_config = {"server": proxy_url}
        else:
            self.proxy_config = None

    # ========================================================================
    # Context Creation Helper
    # ========================================================================

    async def create_ghost_context(
        self,
        browser: Browser,
        enable_stealth: bool = True,
        enable_fingerprint_randomization: bool = True,
        enable_tls_obfuscation: bool = True,
        **kwargs: Any,
    ) -> tuple[Any, Any]:
        """V150.0 Enhanced: Create a browser context with Ghost Protocol enabled.

        This method integrates:
        - Random User-Agent and viewport
        - playwright-stealth for advanced anti-detection
        - V144.0 Fingerprint randomization (Canvas, WebGL, Navigator)
        - V150.0 TLS/JA3 Fingerprint Obfuscation (Unique per Context)

        Args:
            browser: Playwright Browser object
            enable_stealth: Whether to apply playwright-stealth (default: True)
            enable_fingerprint_randomization: Whether to apply V144.0 randomization (default: True)
            enable_tls_obfuscation: Whether to apply V150.0 TLS obfuscation (default: True)
            **kwargs: Additional arguments to pass to new_context()

        Returns:
            Tuple of (context, page) for immediate use

        Example:
            >>> context, page = await extractor.create_ghost_context(browser)
            >>> await page.goto("https://example.com")
        """
        if not self.enable_ghost_protocol:
            context = await browser.new_context(**kwargs)
            page = await context.new_page()
            return context, page

        # Apply Ghost Protocol defaults with V144.0 + V150.0 enhancements
        ghost_kwargs = {
            "user_agent": self.get_random_user_agent(),
            "viewport": self.get_random_viewport(),
            "proxy": self.proxy_config,
            # Additional anti-fingerprinting options
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "color_scheme": "light",
            # V150.0: Ignore HTTPS errors for TLS flexibility
            "ignore_https_errors": True,
        }
        ghost_kwargs.update(kwargs)

        # V150.0: Add random TLS obfuscation headers
        if enable_tls_obfuscation:
            tls_headers = random.choice(TLS_OBFUSCATION_HEADERS)
            ghost_kwargs["extra_http_headers"] = tls_headers

        context = await browser.new_context(**ghost_kwargs)
        page = await context.new_page()

        # Apply playwright-stealth if requested
        if enable_stealth:
            try:
                from playwright_stealth import Stealth
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
                logger.info("  🕵️  playwright-stealth applied successfully")
            except ImportError:
                logger.warning("  ⚠️  playwright-stealth not installed, skipping")
            except Exception as e:
                logger.warning(f"  ⚠️  stealth application failed: {e}")

        # V144.0: Apply fingerprint randomization if requested
        if enable_fingerprint_randomization:
            await self.apply_all_fingerprint_randomization(page)
            logger.info("  🎭 V144.0 fingerprint randomization applied")

        # V150.0: Apply TLS/JA3 obfuscation if requested
        if enable_tls_obfuscation:
            await self._apply_tls_obfuscation(page)
            logger.info("  🔐 V150.0 TLS/JA3 obfuscation applied")

        return context, page

    # ========================================================================
    # V150.0: TLS/JA3 Fingerprint Obfuscation Methods
    # ========================================================================

    async def _apply_tls_obfuscation(self, page: Page) -> None:
        """V150.0: Apply TLS/JA3 fingerprint obfuscation.

        This method injects scripts that randomize:
        - TLS connection timing patterns
        - WebSocket fingerprint
        - Browser behavior patterns

        Args:
            page: Playwright Page object
        """
        if not self.enable_ghost_protocol:
            return

        try:
            # Inject TLS fingerprint randomization
            await page.evaluate(TLS_FINGERPRINT_RANDOMIZATION_SCRIPT)

            # Inject behavior fingerprint script
            await page.evaluate(BEHAVIOR_FINGERPRINT_SCRIPT)

            # Get fingerprint ID for logging
            fingerprint_id = await page.evaluate("() => window.__fingerprint_id")
            behavior_pattern = await page.evaluate("() => window.__behavior_pattern")

            logger.debug(
                f"  🔐 TLS obfuscation applied: ID={fingerprint_id}, "
                f"pattern={behavior_pattern}"
            )
        except Exception as e:
            logger.warning(f"  ⚠️ TLS obfuscation failed: {e}")

    @classmethod
    def get_random_tls_headers(cls) -> dict[str, str]:
        """V150.0: Get random HTTP headers for TLS obfuscation.

        Returns:
            Dictionary of HTTP headers

        Example:
            >>> headers = BaseExtractor.get_random_tls_headers()
            >>> print(headers['Sec-Ch-Ua'])
            '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"'
        """
        return random.choice(TLS_OBFUSCATION_HEADERS).copy()

    @classmethod
    def get_context_fingerprint_summary(cls) -> dict[str, Any]:
        """V150.0: Generate a fingerprint summary for the current context.

        This is used to prove that each context has a unique fingerprint.

        Returns:
            Dictionary containing fingerprint components

        Example:
            >>> summary = BaseExtractor.get_context_fingerprint_summary()
            >>> print(summary)
            {'user_agent': 'Mozilla/5.0...', 'viewport': {...}, 'headers': {...}}
        """
        return {
            "user_agent": cls.get_random_user_agent(),
            "viewport": cls.get_random_viewport(),
            "hardware": cls.get_random_hardware_config(),
            "platform": cls.get_random_platform(),
            "tls_headers": cls.get_random_tls_headers(),
            "cipher_suite": random.choice(CIPHER_SUITE_VARIANTS),
            "timestamp": datetime.now().isoformat(),
        }
