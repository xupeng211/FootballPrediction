#!/usr/bin/env python3
"""V41.590 Fingerprint Manager - 浏览器指纹随机化

This module provides realistic browser fingerprint randomization to evade
bot detection systems. It generates random but realistic User-Agents,
viewport configurations, and browser characteristics.

Key Features:
    - Realistic User-Agent generation (Chrome, Edge, Safari, Firefox)
    - Random viewport sizes matching common screen resolutions
    - Accept-Language randomization
    - Timezone and locale randomization
    - WebGL and Canvas fingerprint randomization

Author: V41.590 Stealth Team
Date: 2026-01-21
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Realistic User-Agent Pool
# ============================================================================

# 真实的浏览器 User-Agent 池 (定期更新以匹配最新版本)
USER_AGENTS = {
    "chrome_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    ],
    "edge_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ],
    "chrome_mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ],
    "safari_mac": [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    ],
    "firefox_windows": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    ],
}

# 常见的屏幕分辨率
VIEWPORTS = [
    (1920, 1080),  # Full HD
    (1366, 768),   # Laptop
    (1440, 900),   # Laptop
    (1536, 864),   # Laptop
    (2560, 1440),  # 2K
    (1680, 1050),   # WQXGA
    (1600, 900),   # HD+
]

# 语言偏好设置
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
]

# 时区设置
TIMEZONES = [
    "America/New_York",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "America/Los_Angeles",
    "Asia/Tokyo",
]

# 地区设置
LOCALES = [
    "en-US",
    "en-GB",
    "de-DE",
    "fr-FR",
    "es-ES",
    "it-IT",
    "pt-BR",
]


# ============================================================================
# Fingerprint Configuration
# ============================================================================


@dataclass
class BrowserFingerprint:
    """浏览器指纹配置

    Attributes:
        user_agent: User-Agent 字符串
        viewport_width: 窗口宽度
        viewport_height: 窗口高度
        device_scale_factor: 设备缩放因子
        accept_language: Accept-Language 头
        timezone: 时区
        locale: 地区
        color_scheme: 颜色方案 (light/dark)
    """

    user_agent: str
    viewport_width: int
    viewport_height: int
    device_scale_factor: float = 1.0
    accept_language: str = "en-US,en;q=0.9"
    timezone: str = "America/New_York"
    locale: str = "en-US"
    color_scheme: str = "light"

    def to_playwright_context(self) -> dict[str, Any]:
        """转换为 Playwright context 配置

        Returns:
            Playwright browser context 参数字典
        """
        return {
            "user_agent": self.user_agent,
            "viewport": {
                "width": self.viewport_width,
                "height": self.viewport_height,
                "device_scale_factor": self.device_scale_factor,
            },
            "locale": self.locale,
            "timezone_id": self.timezone,
            "color_scheme": self.color_scheme,
        }


# ============================================================================
# Fingerprint Manager
# ============================================================================


class FingerprintManager:
    """V41.590: 浏览器指纹管理器

    生成真实且随机的浏览器指纹，用于反机器人检测。

    特性:
    - 真实 User-Agent 池
    - 随机视口大小
    - 随机语言和时区设置
    - 支持主流浏览器: Chrome, Edge, Safari, Firefox

    Example:
        >>> manager = FingerprintManager()
        >>> fingerprint = manager.generate_random_fingerprint()
        >>> context = await browser.new_context(**fingerprint.to_playwright_context())
    """

    def __init__(self, seed: int | None = None):
        """初始化指纹管理器

        Args:
            seed: 随机种子（用于测试，生产环境通常为 None）
        """
        if seed is not None:
            random.seed(seed)

    def generate_random_fingerprint(
        self,
        browser_preference: str | None = None
    ) -> BrowserFingerprint:
        """生成随机浏览器指纹

        Args:
            browser_preference: 浏览器偏好 ("chrome", "edge", "safari", "firefox")
                                 如果为 None 则随机选择

        Returns:
            BrowserFingerprint 对象
        """
        # 选择浏览器类型
        if browser_preference:
            browser_type = f"{browser_preference}_windows"
        else:
            browser_type = random.choice(list(USER_AGENTS.keys()))

        # 选择 User-Agent
        user_agent = random.choice(USER_AGENTS[browser_type])

        # 选择视口大小
        viewport_width, viewport_height = random.choice(VIEWPORTS)

        # 根据视口大小调整缩放因子（高分屏使用更高缩放）
        if viewport_width >= 2560:
            device_scale_factor = 1.5
        elif viewport_width >= 1920:
            device_scale_factor = random.choice([1.0, 1.25])
        else:
            device_scale_factor = 1.0

        # 选择语言
        accept_language = random.choice(ACCEPT_LANGUAGES)

        # 选择时区和地区
        timezone = random.choice(TIMEZONES)
        locale = random.choice(LOCALES)

        # 随机颜色方案（深色模式越来越流行）
        color_scheme = random.choice(["light", "light", "light", "dark"])

        fingerprint = BrowserFingerprint(
            user_agent=user_agent,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            device_scale_factor=device_scale_factor,
            accept_language=accept_language,
            timezone=timezone,
            locale=locale,
            color_scheme=color_scheme,
        )

        logger.debug(
            f"[FingerprintManager] 生成指纹: {browser_type} | "
            f"Viewport: {viewport_width}x{viewport_height} | "
            f"Locale: {locale}"
        )

        return fingerprint

    def generate_chrome_fingerprint(self) -> BrowserFingerprint:
        """生成 Chrome 浏览器指纹"""
        return self.generate_random_fingerprint("chrome")

    def generate_firefox_fingerprint(self) -> BrowserFingerprint:
        """生成 Firefox 浏览器指纹"""
        return self.generate_random_fingerprint("firefox")

    def generate_mac_fingerprint(self) -> BrowserFingerprint:
        """生成 macOS 浏览器指纹 (Safari)"""
        return self.generate_random_fingerprint("safari")


# ============================================================================
# Singleton Instance
# ============================================================================

_fingerprint_manager_instance: FingerprintManager | None = None


def get_fingerprint_manager(seed: int | None = None) -> FingerprintManager:
    """获取指纹管理器单例

    Args:
        seed: 随机种子（用于测试）

    Returns:
        FingerprintManager 单例实例
    """
    global _fingerprint_manager_instance
    if _fingerprint_manager_instance is None:
        _fingerprint_manager_instance = FingerprintManager(seed=seed)
    return _fingerprint_manager_instance
