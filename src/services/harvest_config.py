#!/usr/bin/env python3
"""
V41.66 统一收割配置模块
===========================

本模块提供工业级的数据采集配置管理，整合 V41.59-V41.65 的所有防爬补丁逻辑。

设计原则：
- 单一配置源：所有防爬参数集中管理，禁止硬编码
- 可测试性：配置与逻辑分离，便于单元测试
- 可维护性：清晰的配置结构，易于调整和扩展
- 自愈能力：熔断机制和故障保护

Author: 资深软件质量工程专家 (QA) & 架构师
Version: V41.66
Date: 2026-01-14
"""

from dataclasses import dataclass, field
from typing import ClassVar
import re


@dataclass
class AntiScrapingConfig:
    """
    反爬对抗配置 - V41.66 统一管理

    整合 V41.59-V41.65 的所有防爬补丁逻辑，提供清晰、可测试的配置接口。

    配置说明：
    -----------

    1. User-Agent 轮换池 (50+ 量)
       目的：模拟真实用户浏览器，避免被识别为爬虫
       覆盖：Chrome, Firefox, Edge, Safari 多版本组合
       平台：Windows, macOS, Linux

    2. 视口尺寸池 (8 种)
       目的：随机化浏览器窗口大小，模拟不同设备
       范围：1024x768 到 1920x1080

    3. 随机延迟配置
       目的：模拟人类操作节奏，避免机器行为特征
       - initial_delay: 5-9 秒（页面加载后等待）
       - page_delay: 4-8 秒（翻页间隔）
       - cooldown: 60-120 秒（收割后冷却）

    4. 代理端口配置 (6 个物理 IP)
       目的：IP 轮换，分散请求，降低单 IP 封禁风险
       端口：7891-7896（严格匹配 Clash 配置）
       严禁：7890 端口（已弃用）

    5. 熔断机制配置
       目的：检测 Shadow Ban，自动停止以保护 IP
       触发：连续 3 页空数据且标题正常
       行为：立即退出 (sys.exit(1))

    测试覆盖：
    ----------
    - tests/infrastructure/test_proxy_and_circuit_breaker.py
    - IP 独立性测试
    - 熔断逻辑测试
    """

    # User-Agent 轮换池（50+ 量，覆盖主流浏览器和版本）
    USER_AGENTS: ClassVar[list[str]] = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox on Linux
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Additional Windows variants
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
        # Additional macOS variants
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Additional Edge variants
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.0.0",
        # Additional Safari variants
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Additional Linux variants
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
        # Chrome variations
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        # Firefox variations
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
        # Edge variations
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.0.0",
        # Safari mobile
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Mix of other versions
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:114.0) Gecko/20100101 Firefox/114.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    ]

    # 视口尺寸池（随机化窗口大小）
    VIEWPORT_SIZES: ClassVar[list[dict[str, int]]] = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1680, "height": 1050},
        {"width": 1600, "height": 900},
        {"width": 1280, "height": 720},
        {"width": 1024, "height": 768},
    ]

    # V41.66: 随机延迟配置（V41.64-V41.65 优化）
    # 目的：模拟人类操作节奏，避免机器行为特征
    #
    # 为什么是 5-9 秒？
    # - 5 秒：足够页面加载完毕（OddsPortal 页面较重）
    # - 9 秒：不超过用户容忍度，避免显得异常
    # - 随机化：避免固定间隔被识别为爬虫特征
    INITIAL_DELAY_MIN: ClassVar[float] = 5.0
    INITIAL_DELAY_MAX: ClassVar[float] = 9.0

    # 翻页延迟（4-8 秒）
    # 为什么是 4-8 秒？
    # - 4 秒：翻页操作最小延迟（避免触发频率限制）
    # - 8 秒：模拟用户浏览时间
    PAGE_DELAY_MIN: ClassVar[float] = 4.0
    PAGE_DELAY_MAX: ClassVar[float] = 8.0

    # 收割冷却（60-120 秒）
    # 为什么是 60-120 秒？
    # - 60 秒：最小冷却时间（模拟用户休息）
    # - 120 秒：最大冷却时间（降低请求密度）
    # - 目的：避免短时间内大量请求触发反爬保护
    COOLDOWN_MIN: ClassVar[int] = 60
    COOLDOWN_MAX: ClassVar[int] = 120

    # V41.66: 代理端口配置（6 个物理 IP）
    # 目的：IP 轮换，分散请求，降低单 IP 封禁风险
    #
    # 重要说明：
    # - 7891-7896：6 个真实物理 IP（与 Clash 配置一致）
    # - 7890 端口已弃用（严禁使用）
    PROXY_PORTS: ClassVar[list[int]] = [7891, 7892, 7893, 7894, 7895, 7896]
    DEPRECATED_PROXY_PORT: ClassVar[int] = 7890  # 已弃用，禁止使用

    # V41.66: 熔断机制配置
    # 目的：检测 Shadow Ban，自动停止以保护 IP
    #
    # 触发条件：
    # - 连续 3 页提取到 0 场比赛
    # - 页面标题包含 "Results"（说明页面正常加载，但数据被屏蔽）
    #
    # 为什么是 3 次？
    # - 1 次：可能是网络波动或页面加载问题
    # - 2 次：继续观察，确认问题
    # - 3 次：确认 Shadow Ban，立即停止避免 IP 被永久封禁
    #
    # 行为：
    # - 记录 FATAL ERROR 日志
    # - sys.exit(1) 强制退出
    CIRCUIT_BREAKER_THRESHOLD: ClassVar[int] = 3
    SHADOW_BAN_INDICATOR: ClassVar[str] = "Results"  # 页面标题中的关键词

    # V41.66: 浏览器指纹配置
    # 目的：增强浏览器真实感，绕过反爬检测
    #
    # 配置说明：
    # - ignore_default_args：移除自动化特征标识
    # - locale：随机化地区设置（en-US, en-GB, en-CA）
    # - timezone_id：随机化时区（欧洲主要城市）
    BROWSER_IGNORE_DEFAULT_ARGS: ClassVar[list[str]] = ["--enable-automation"]
    BROWSER_LOCALES: ClassVar[list[str]] = ["en-US", "en-GB", "en-CA"]
    BROWSER_TIMEZONES: ClassVar[list[str]] = [
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Madrid",
        "Europe/Rome",
    ]

    # V41.66: 爬取超时配置
    PAGE_LOAD_TIMEOUT: ClassVar[int] = 30000  # 30 秒
    NAVIGATION_TIMEOUT: ClassVar[int] = 30000  # 30 秒

    @classmethod
    def get_random_user_agent(cls) -> str:
        """
        获取随机 User-Agent

        Returns:
            随机选择的 User-Agent 字符串
        """
        import random
        return random.choice(cls.USER_AGENTS)

    @classmethod
    def get_random_viewport(cls) -> dict[str, int]:
        """
        获取随机视口尺寸

        Returns:
            包含 width 和 height 的字典
        """
        import random
        return random.choice(cls.VIEWPORT_SIZES)

    @classmethod
    def get_random_locale(cls) -> str:
        """
        获取随机地区设置

        Returns:
            随机选择的 locale 字符串
        """
        import random
        return random.choice(cls.BROWSER_LOCALES)

    @classmethod
    def get_random_timezone(cls) -> str:
        """
        获取随机时区设置

        Returns:
            随机选择的 timezone_id 字符串
        """
        import random
        return random.choice(cls.BROWSER_TIMEZONES)

    @classmethod
    def validate_proxy_port(cls, port: int) -> bool:
        """
        验证代理端口是否有效

        Args:
            port: 代理端口号

        Returns:
            True 如果端口有效，False 如果端口已弃用或不在允许列表中

        Raises:
            ValueError: 如果端口已弃用（7890）
        """
        if port == cls.DEPRECATED_PROXY_PORT:
            raise ValueError(f"代理端口 {port} 已弃用，禁止使用")

        return port in cls.PROXY_PORTS


@dataclass
class HarvestConfig:
    """
    收割配置 - V41.66 统一管理

    集成所有收割相关的配置参数，提供清晰的配置接口。
    """

    # 联赛配置
    league_name: str
    season: str
    tier: int = 1

    # 收割参数
    max_pages: int = 10
    headless: bool = True
    enable_ghost_protocol: bool = True

    # 防爬配置（使用 AntiScrapingConfig）
    anti_scraping: AntiScrapingConfig = field(default_factory=AntiScrapingConfig)

    def validate(self) -> bool:
        """
        验证配置有效性

        Returns:
            True 如果配置有效

        Raises:
            ValueError: 如果配置无效
        """
        if not self.league_name:
            raise ValueError("league_name 不能为空")

        if not self.season:
            raise ValueError("season 不能为空")

        if self.tier < 1 or self.tier > 3:
            raise ValueError(f"tier 必须在 1-3 之间，当前值: {self.tier}")

        if self.max_pages < 1:
            raise ValueError(f"max_pages 必须大于 0，当前值: {self.max_pages}")

        return True


# V41.66: 导出配置实例（向后兼容）
def get_default_anti_scraping_config() -> AntiScrapingConfig:
    """
    获取默认的反爬对抗配置

    Returns:
        AntiScrapingConfig 实例
    """
    return AntiScrapingConfig()
