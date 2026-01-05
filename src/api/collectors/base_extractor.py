#!/usr/bin/env python3
"""V144.2 Base Extractor - Anti-Detection Foundation (Stable Baseline).

This module provides the base extraction class with integrated "Ghost Protocol"
capabilities from V140.0. It serves as the foundation for all web scraping
operations in the FootballPrediction system.

Core Features (Ghost Protocol - V55.2):
    - Dynamic UA Pool: 10 mainstream browser fingerprints
    - Random Viewport: 5 common screen resolutions
    - Human Behavior Simulation: Scroll + click noise
    - Deep Interception Detection: Cloudflare, IP ban detection
    - Auto Error Screenshot: Saves to logs/error_screens/
    - WSL2 Auto Proxy Discovery: Automatic proxy configuration

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
from datetime import datetime
import logging
import os
from pathlib import Path
import random
from typing import Any

from playwright.async_api import Browser, Page

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


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
        """
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
                # Try common proxy ports
                common_ports = [7890, 10808, 10809, 7891, 1087]
                for port in common_ports:
                    proxy_url = f"http://{wsl_host}:{port}"
                    logger.info(f"  🔍 WSL2 自动探测: 尝试 {proxy_url}")
                    # Quick connectivity test
                    if self._test_proxy_connection(proxy_url):
                        logger.info(f"  ✓ WSL2 代理成功: {proxy_url}")
                        return {"server": proxy_url}
                logger.info(f"  ℹ️  WSL2 宿主机 IP: {wsl_host}，但常用端口均无响应")

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
        **kwargs: Any,
    ) -> tuple[Any, Any]:
        """V144.0 Enhanced: Create a browser context with Ghost Protocol enabled.

        This method integrates:
        - Random User-Agent and viewport
        - playwright-stealth for advanced anti-detection
        - V144.0 Fingerprint randomization (Canvas, WebGL, Navigator)

        Args:
            browser: Playwright Browser object
            enable_stealth: Whether to apply playwright-stealth (default: True)
            enable_fingerprint_randomization: Whether to apply V144.0 randomization (default: True)
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

        # Apply Ghost Protocol defaults with V144.0 enhancements
        ghost_kwargs = {
            "user_agent": self.get_random_user_agent(),
            "viewport": self.get_random_viewport(),
            "proxy": self.proxy_config,
            # Additional anti-fingerprinting options
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "color_scheme": "light",
        }
        ghost_kwargs.update(kwargs)

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

        return context, page
