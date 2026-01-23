"""V41.832: Crawler Configuration.

集中管理所有爬虫相关的配置常量，包括：
- CSS Selectors
- URL 模板
- 超时设置
- 重试参数
- 内容锁阈值

Author: Senior Lead Data Architect
Version: V41.832 "Production Blueprint"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class OddsPortalConfig:
    """OddsPortal 归档爬虫配置."""

    # URL Templates
    BASE_URL: Final[str] = "https://www.oddsportal.com"
    RESULTS_PATH: Final[str] = "/football/{country}/{league}-{season}/results/"

    # CSS Selectors
    SELECTOR_PAGINATION: Final[str] = ".pagination"
    SELECTOR_EVENT_ROWS: Final[str] = "tbody.eventHolder tr"
    SELECTOR_EVENT_LINK: Final[str] = "a[href*='/football/']"

    # Content Lock Thresholds
    MIN_MATCHES_PER_PAGE: Final[int] = 40
    MIN_MATCHES_LAST_PAGE: Final[int] = 1

    # Timeouts (seconds)
    PAGE_LOAD_TIMEOUT: Final[int] = 30
    CLICK_TIMEOUT: Final[int] = 10
    CONTENT_LOCK_MAX_WAIT: Final[int] = 10
    NAVIGATION_TIMEOUT: Final[int] = 60

    # Retry Configuration
    MAX_RETRIES: Final[int] = 3
    RETRY_DELAY: Final[int] = 2

    # Regex Patterns
    THREE_SEGMENT_PATTERN: Final[str] = (
        r"/football/[^/]+/[^-]+-\d{4}-\d{4}/([A-Za-z0-9-]+)-([A-Za-z0-9]{8,10})/"
    )

    # Database
    MAPPING_METHOD: Final[str] = "v41.832_production_ready"

    # Similarity Thresholds
    MIN_SIMILARITY: Final[float] = 0.6
    MIN_CONFIDENCE: Final[float] = 0.65


@dataclass(frozen=True)
class BrowserConfig:
    """浏览器配置."""

    # User Agent
    USER_AGENT: Final[str] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Viewport
    VIEWPORT_WIDTH: Final[int] = 1920
    VIEWPORT_HEIGHT: Final[int] = 1080

    # Page Load Strategy
    WAIT_UNTIL: Final[str] = "domcontentloaded"


# Default configuration instances
ODDSPORTAL_CONFIG = OddsPortalConfig()
BROWSER_CONFIG = BrowserConfig()
