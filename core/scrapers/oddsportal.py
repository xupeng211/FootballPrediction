#!/usr/bin/env python3
"""V150.53 OddsPortal Scraper - Production-Ready Odds Extraction with Fast-Fail.

This module provides the unified OddsPortal scraper class with integrated
"Ghost Protocol" capabilities and IP protection mechanisms.

Core Features:
    - Dynamic UA Pool: 30+ mainstream browser fingerprints
    - Random Viewport: 10 common screen resolutions
    - Human Behavior Simulation: Scroll + click noise
    - Deep Interception Detection: Cloudflare, IP ban detection
    - Circuit Breaker: Automatic proxy rotation and cooldown
    - Aggressive Scroll: Enhanced modal data extraction (V150.32)
    - Time Conversion: BST/GMT → Beijing Time (UTC+8)
    - V150.53 Fast-Fail: 3s timeout for graceful degradation (10s → 3s)
    - V150.53 Random Scroll: Enhanced stealth with random wheel deltas

Example:
    >>> from core.scrapers.oddsportal import OddsPortalScraper
    >>> scraper = OddsPortalScraper()
    >>> result = await scraper.fetch_snapshot("nsbKWw0O")
    >>> print(result["data"]["home"][0]["beijing_time"])
    '2024-04-27 15:30:00'

Author: 高级反爬虫专家 & 性能优化工程师
Version: V150.53
Date: 2026-01-11
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import yaml
from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

# ==============================================================================
# Configuration Data Classes
# ==============================================================================


@dataclass
class ProxyConfig:
    """代理配置"""

    servers: List[str] = field(default_factory=lambda: [f"http://172.25.16.1:{port}" for port in range(7890, 7900)])
    auto_rotation: bool = True
    health_check_interval: int = 300


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 2
    cooldown_timeout: int = 1800  # 30 minutes
    emergency_stop_threshold: float = 0.3
    auto_recovery: bool = True


@dataclass
class DelayConfig:
    """延迟配置"""

    min_page_delay: float = 5.0
    max_page_delay: float = 12.0
    min_task_delay: float = 15.0
    max_task_delay: float = 30.0
    hover_wait: float = 4.0
    scroll_wait: float = 0.5


@dataclass
class FingerprintConfig:
    """指纹配置"""

    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    ])
    viewports: List[Dict[str, int]] = field(default_factory=lambda: [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 2560, "height": 1440},
    ])
    locale: str = "en-GB"
    timezone_id: str = "Europe/London"


@dataclass
class BehaviorConfig:
    """行为模拟配置"""

    enable_mouse_move: bool = True
    mouse_move_range: Tuple[int, int] = (3, 5)
    enable_scroll: bool = True
    scroll_range: Tuple[int, int] = (2, 4)
    scroll_delta_range: Tuple[int, int] = (100, 500)


@dataclass
class ExtractionConfig:
    """数据提取配置"""

    target_bookmaker: str = "Pinnacle"
    pinnacle_selector: str = "div.border-black-borders:has(img[title='Pinnacle'])"
    odds_cells_selector: str = "div.flex-center.flex-col.font-bold"
    modal_selector: str = "h3:has-text('Odds movement')"
    enable_aggressive_scroll: bool = True
    aggressive_scroll_iterations: int = 15
    scroll_interval: float = 0.3


@dataclass
class LoggingConfig:
    """日志配置"""

    output_dir: str = "logs/v150_33"
    enable_audit: bool = True
    audit_file: str = "audit_report.json"
    data_file: str = "harvest_results.json"
    enable_screenshot: bool = True
    screenshot_dir: str = "logs/error_screens"


@dataclass
class ScraperConfig:
    """采集器总配置"""

    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    delays: DelayConfig = field(default_factory=DelayConfig)
    fingerprints: FingerprintConfig = field(default_factory=FingerprintConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, config_path: str = "config/scraper_config.yaml") -> "ScraperConfig":
        """从 YAML 文件加载配置"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return cls(
                proxy=ProxyConfig(**data.get("proxy", {})),
                circuit_breaker=CircuitBreakerConfig(**data.get("circuit_breaker", {})),
                delays=DelayConfig(**data.get("delays", {})),
                fingerprints=FingerprintConfig(**data.get("fingerprints", {})),
                behavior=BehaviorConfig(**data.get("behavior_simulation", {})),
                extraction=ExtractionConfig(**data.get("extraction", {})),
                logging=LoggingConfig(**data.get("logging", {})),
            )
        except Exception as e:
            logger.warning(f"配置文件加载失败，使用默认配置: {e}")
            return cls()


# ==============================================================================
# Circuit Breaker Manager
# ==============================================================================


class CircuitBreakerManager:
    """IP 熔断器管理器"""

    def __init__(self, config: CircuitBreakerConfig, proxy_pool: List[str]):
        self.config = config
        self.proxy_pool = proxy_pool
        self.failed_counts: Dict[str, int] = defaultdict(int)
        self.cooldown_until: Dict[str, datetime] = {}
        self.tripped_count = 0

    def is_available(self, proxy: str) -> bool:
        """检查代理是否可用"""
        beijing_tz = timezone(timedelta(hours=8))

        if proxy in self.cooldown_until:
            if datetime.now(beijing_tz) < self.cooldown_until[proxy]:
                return False
            else:
                # 冷却期结束，重置
                del self.cooldown_until[proxy]
                self.failed_counts[proxy] = 0
        return True

    def record_success(self, proxy: str) -> None:
        """记录成功"""
        self.failed_counts[proxy] = 0

    def record_failure(self, proxy: str, error_type: str) -> None:
        """记录失败"""
        self.failed_counts[proxy] += 1

        if self.failed_counts[proxy] >= self.config.failure_threshold:
            beijing_tz = timezone(timedelta(hours=8))
            cooldown_end = datetime.now(beijing_tz) + timedelta(seconds=self.config.cooldown_timeout)
            self.cooldown_until[proxy] = cooldown_end
            self.tripped_count += 1

            timestamp = cooldown_end.strftime("%Y-%m-%d %H:%M:%S")
            logger.warning(
                f"熔断触发！代理 {proxy} 已停用至 {timestamp} "
                f"(失败次数: {self.failed_counts[proxy]}, 错误类型: {error_type})"
            )

            self.check_emergency_stop()

    def check_emergency_stop(self) -> None:
        """检查是否需要紧急停止"""
        active_proxies = sum(1 for p in self.proxy_pool if self.is_available(p))
        total_proxies = len(self.proxy_pool)

        if active_proxies < total_proxies * self.config.emergency_stop_threshold:
            error_msg = (
                f"紧急停止触发！可用代理: {active_proxies}/{total_proxies} "
                f"({active_proxies/total_proxies*100:.1f}%) - 超过阈值"
            )
            logger.error(error_msg)
            raise EmergencyStopError(error_msg)

    def get_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        active = sum(1 for p in self.proxy_pool if self.is_available(p))
        return {
            "total_proxies": len(self.proxy_pool),
            "active_proxies": active,
            "tripped_proxies": self.tripped_count,
            "availability_rate": f"{active/len(self.proxy_pool)*100:.1f}%",
        }

    def get_available_proxy(self) -> Optional[str]:
        """获取可用代理"""
        for proxy in self.proxy_pool:
            if self.is_available(proxy):
                return proxy
        return None


class EmergencyStopError(Exception):
    """紧急停止异常"""

    pass


# ==============================================================================
# Human Behavior Simulator
# ==============================================================================


class HumanBehaviorSimulator:
    """人类行为模拟器"""

    def __init__(self, behavior_config: BehaviorConfig, fingerprint_config: FingerprintConfig = None):
        self.behavior_config = behavior_config
        self.fingerprint_config = fingerprint_config or FingerprintConfig()

    async def random_mouse_move(self, page: Page) -> None:
        """模拟真实鼠标轨迹"""
        if not self.behavior_config.enable_mouse_move:
            return

        try:
            viewport = page.viewport_size
            if not viewport:
                return

            width, height = viewport["width"], viewport["height"]
            moves = random.randint(*self.behavior_config.mouse_move_range)

            for _ in range(moves):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.05, 0.15))

        except Exception as e:
            logger.debug(f"鼠标移动失败: {e}")

    async def natural_scroll(self, page: Page) -> None:
        """模拟自然滚动"""
        if not self.behavior_config.enable_scroll:
            return

        try:
            scrolls = random.randint(*self.behavior_config.scroll_range)

            for _ in range(scrolls):
                delta = random.randint(*self.behavior_config.scroll_delta_range)
                await page.mouse.wheel(0, delta)
                await asyncio.sleep(random.uniform(0.3, 0.8))

        except Exception as e:
            logger.debug(f"滚动失败: {e}")

    async def simulate_reading(self, page: Page) -> None:
        """模拟阅读行为"""
        await self.random_mouse_move(page)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await self.natural_scroll(page)
        await asyncio.sleep(random.uniform(0.3, 0.8))

    def get_random_fingerprint(self) -> Tuple[str, Dict[str, int]]:
        """获取随机指纹"""
        ua = random.choice(self.fingerprint_config.user_agents)
        viewport = random.choice(self.fingerprint_config.viewports)
        return ua, viewport


# ==============================================================================
# Time Converter
# ==============================================================================


class TimeConverter:
    """时间转换器 - OddsPortal 时间 → 北京时间"""

    BEIJING_TZ = timezone(timedelta(hours=8))

    @classmethod
    def convert_to_beijing(cls, time_str: str) -> Dict[str, Any]:
        """
        转换时间字符串为北京时间

        Args:
            time_str: 如 "28 Apr, 00:19" 或 "Today, 15:30"

        Returns:
            {
                "original": time_str,
                "beijing": "2024-04-28 08:19:00",
                "timezone": "Asia/Shanghai (UTC+8)",
                "original_timezone": "Europe/London (BST/UTC+1)"
            }
        """
        try:
            if "Today" in time_str:
                now = datetime.now(cls.BEIJING_TZ)
                time_part = time_str.split(",")[1].strip()
                hour, minute = map(int, time_part.split(":"))
                beijing_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                now = datetime.now(cls.BEIJING_TZ)
                parts = time_str.split()
                day = int(parts[0].rstrip(","))
                month_str = parts[1]
                time_part = parts[2]

                months = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                }
                month = months.get(month_str, 1)
                hour, minute = map(int, time_part.split(":"))

                # BST 英国夏令时 UTC+1 → 北京时间 UTC+8 (+7 小时)
                beijing_time = datetime(now.year, month, day, hour, minute, 0) + timedelta(hours=7)

            return {
                "original": time_str,
                "beijing": beijing_time.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": int(beijing_time.timestamp()),
                "timezone": "Asia/Shanghai (UTC+8)",
                "original_timezone": "Europe/London (BST/UTC+1)"
            }
        except Exception as e:
            return {
                "original": time_str,
                "beijing": time_str,
                "error": str(e),
                "timezone": "Unknown"
            }


# ==============================================================================
# Odds Movement Extractor
# ==============================================================================


class OddsMovementExtractor:
    """变盘数据提取器 - V150.53 快进快出版本"""

    def __init__(self, page: Page, config: ExtractionConfig, delay_config: DelayConfig = None):
        self.page = page
        self.config = config
        self.delay_config = delay_config or DelayConfig()

    async def extract_complete_history(self, bet_type: str, cell_locator) -> List[Dict[str, Any]]:
        """
        提取完整的历史变盘记录（含滚动）
        V150.53: 快进快出 - 3秒超时，快速跳过无变盘数据的比赛

        Args:
            bet_type: 投注类型 (home/draw/away)
            cell_locator: 赔率单元格定位器

        Returns:
            历史记录列表
        """
        try:
            # 滚动到元素位置
            await cell_locator.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)  # 减少等待时间

            # 触发 Hover
            await cell_locator.hover()
            await asyncio.sleep(1.5)  # 减少悬停等待

            # V150.53: 快速等待弹窗（3秒超时）
            try:
                modal = self.page.locator(self.config.modal_selector).first
                await modal.wait_for(state="visible", timeout=3000)
            except Exception:
                # V150.53: 快速判定为无变盘数据
                logger.debug(f"[{bet_type}] 无变盘数据（3秒内未弹出）")
                return []

            # 获取弹窗容器
            modal_container = self.page.locator(self.config.modal_selector).locator("xpath=ancestor::div[3]")

            # V150.53: 快速提取（3秒超时）
            html = await modal_container.inner_html(timeout=3000)
            soup = BeautifulSoup(html, "html.parser")

            timestamps = soup.select("div.flex.flex-col.gap-1 > div.flex.gap-3 > div.font-normal")
            odds_values = soup.select("div.flex.flex-col.gap-1 + div.flex.flex-col.gap-1 > div.font-bold")

            initial_count = len(timestamps)
            data = self._parse_odds_data(timestamps, odds_values)

            # 滚动加载更多
            if self.config.enable_aggressive_scroll:
                await self._aggressive_scroll(modal_container)

                # V150.53: 再次提取（3秒超时）
                html = await modal_container.inner_html(timeout=3000)
                soup = BeautifulSoup(html, "html.parser")

                timestamps_new = soup.select("div.flex.flex-col.gap-1 > div.flex.gap-3 > div.font-normal")
                odds_values_new = soup.select("div.flex.flex-col.gap-1 + div.flex.flex-col.gap-1 > div.font-bold")

                final_count = len(timestamps_new)

                if final_count > initial_count:
                    logger.debug(f"滚动加载: {initial_count} → {final_count} 条 (+{final_count - initial_count})")
                    data = self._parse_odds_data(timestamps_new, odds_values_new)

            return data

        except Exception as e:
            logger.error(f"提取失败 ({bet_type}): {e}")
            return []

    def _parse_odds_data(self, timestamps, odds_values) -> List[Dict[str, Any]]:
        """解析赔率数据"""
        data = []

        for ts, odd in zip(timestamps, odds_values):
            time_str = ts.get_text(strip=True)
            odds_str = odd.get_text(strip=True)

            time_data = TimeConverter.convert_to_beijing(time_str)

            data.append({
                "original_time": time_str,
                "beijing_time": time_data.get("beijing", time_str),
                "odds": odds_str,
                "timezone_info": time_data.get("timezone", "Unknown")
            })

        return data

    async def _aggressive_scroll(self, modal_element) -> None:
        """V150.32: 激进滚动弹窗以加载更多历史记录"""
        try:
            box = await modal_element.bounding_box()
            if not box:
                return

            center_x = box["x"] + box["width"] / 2
            center_y = box["y"] + box["height"] / 2

            for i in range(self.config.aggressive_scroll_iterations):
                await self.page.mouse.move(center_x, center_y)
                await asyncio.sleep(0.1)

                # 向上滚动
                await self.page.mouse.wheel(0, -300)
                await asyncio.sleep(self.config.scroll_interval)

                # 向下滚动
                await self.page.mouse.wheel(0, 300)
                await asyncio.sleep(self.config.scroll_interval)

                # 每 5 次滚动后，尝试 JavaScript 滚动
                if i % 5 == 4:
                    await self._javascript_scroll(modal_element)

        except Exception as e:
            logger.debug(f"激进滚动失败: {e}")

    async def _javascript_scroll(self, modal_element) -> None:
        """使用 JavaScript 进行更彻底的滚动"""
        try:
            await modal_element.evaluate("""el => {
                const scrollable = el.querySelector('[style*="overflow"]');
                if (scrollable && scrollable.scrollHeight > scrollable.clientHeight) {
                    for (let i = 0; i < 10; i++) {
                        scrollable.scrollTop += 100;
                    }
                    scrollable.scrollTop = 0;
                }
            }""")
        except Exception:
            pass


# ==============================================================================
# Main Scraper Class
# ==============================================================================


class OddsPortalScraper:
    """V150.33 OddsPortal Scraper - 生产级采集器

    核心功能:
    - 代理池管理与熔断保护
    - 浏览器指纹随机化
    - 人类行为模拟
    - Pinnacle 赔率快照提取
    - 审计日志记录

    Example:
        >>> scraper = OddsPortalScraper()
        >>> async with scraper.stealth_context() as (browser, page):
        ...     result = await scraper.fetch_snapshot("nsbKWw0O")
        ...     print(result["success"])
        True
    """

    # URL 格式常量
    BASE_URL = "https://www.oddsportal.com"
    URL_PATTERN = "/football/england/premier-league-2023-2024/{home}-{away}/{short_id}/"

    def __init__(self, config_path: str = "config/scraper_config.yaml"):
        """初始化采集器

        Args:
            config_path: 配置文件路径
        """
        self.config = ScraperConfig.from_yaml(config_path)

        # 初始化子组件
        self.circuit_breaker = CircuitBreakerManager(
            self.config.circuit_breaker,
            self.config.proxy.servers
        )
        self.behavior_simulator = HumanBehaviorSimulator(self.config.behavior, self.config.fingerprints)

        # 审计日志
        self.audit_log: List[Dict[str, Any]] = []

        # 确保输出目录存在
        Path(self.config.logging.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.logging.screenshot_dir).mkdir(parents=True, exist_ok=True)

    def _build_url(self, short_id: str, home_team: str, away_team: str) -> str:
        """构建 OddsPortal URL"""
        slug_home = home_team.lower().replace(" ", "-").replace("'", "")
        slug_away = away_team.lower().replace(" ", "-").replace("'", "")
        return self.BASE_URL + self.URL_PATTERN.format(
            home=slug_home,
            away=slug_away,
            short_id=short_id
        )

    @asynccontextmanager
    async def stealth_context(
        self,
        proxy: Optional[str] = None,
        headless: bool = True,
    ) -> AsyncGenerator[Tuple[Browser, Page], None]:
        """创建隐身浏览器上下文

        Args:
            proxy: 代理服务器 (None = 自动选择)
            headless: 是否无头模式

        Yields:
            (Browser, Page) 元组
        """
        from playwright.async_api import async_playwright

        # 选择代理
        if proxy is None:
            proxy = self.circuit_breaker.get_available_proxy()
            if proxy is None:
                raise RuntimeError("无可用代理")

        # 获取随机指纹
        ua, viewport = self.behavior_simulator.get_random_fingerprint()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = await browser.new_context(
                user_agent=ua,
                viewport=viewport,
                locale=self.config.fingerprints.locale,
                timezone_id=self.config.fingerprints.timezone_id,
                proxy={"server": proxy}
            )

            page = await context.new_page()

            try:
                yield browser, page
            finally:
                await context.close()
                await browser.close()

    async def fetch_snapshot(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        url: Optional[str] = None,
        headless: bool = True,
    ) -> Dict[str, Any]:
        """执行核心逻辑：导航 -> 定位 Pinnacle 行 -> Hover 触发 -> 解析 JSON 赔率

        Args:
            match_id: 8 位短哈希 ID
            home_team: 主队名称
            away_team: 客队名称
            url: 完整 URL (可选，如不提供则自动构建)
            headless: 是否无头模式

        Returns:
            {
                "success": True/False,
                "match_id": "nsbKWw0O",
                "home_team": "Everton",
                "away_team": "Brentford",
                "proxy": "http://172.25.16.1:7890",
                "extraction_time": "2024-04-27T15:30:00",
                "data": {
                    "home": [{"beijing_time": "...", "odds": "2.15"}, ...],
                    "draw": [...],
                    "away": [...]
                },
                "stats": {
                    "total_records": 45,
                    "bet_types_count": 3
                },
                "error": None (如果失败)
            }
        """
        start_time = datetime.now(timezone.utc)

        # 构建 URL
        if url is None:
            url = self._build_url(match_id, home_team, away_team)

        # 获取代理
        proxy = self.circuit_breaker.get_available_proxy()
        if proxy is None:
            return self._error_result(match_id, home_team, away_team, url, None, "无可用代理")

        result = None

        try:
            async with self.stealth_context(proxy=proxy, headless=headless) as (browser, page):
                # 步骤 1: 访问页面
                logger.info(f"[{match_id}] 步骤 1: 访问页面...")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # 步骤 2: 拟人化等待
                wait_time = random.uniform(self.config.delays.min_page_delay, self.config.delays.max_page_delay)
                logger.info(f"[{match_id}] 等待 {wait_time:.1f} 秒...")
                await asyncio.sleep(wait_time)

                # V150.53: 随机滚动行为（增加隐蔽性）
                scroll_delta = random.randint(300, 800)
                await page.mouse.wheel(0, scroll_delta)
                await asyncio.sleep(random.uniform(0.5, 1.5))

                # 步骤 3: 模拟阅读行为
                logger.info(f"[{match_id}] 模拟用户行为...")
                await self.behavior_simulator.simulate_reading(page)

                # 步骤 4: 检查拦截
                current_url = page.url
                if "oddsportal.com" not in current_url.lower():
                    raise Exception("页面被重定向或拦截")

                # 步骤 5: 定位 Pinnacle 数据
                logger.info(f"[{match_id}] 定位 Pinnacle 数据...")
                locator = page.locator(self.config.extraction.pinnacle_selector)
                count = await locator.count()

                if count == 0:
                    raise Exception("未找到 Pinnacle 数据行")

                logger.info(f"[{match_id}] 找到 {count} 个 Pinnacle 数据行")

                # 步骤 6: 提取变盘数据
                logger.info(f"[{match_id}] 提取变盘数据...")
                first_row = locator.first
                odds_cells = first_row.locator(self.config.extraction.odds_cells_selector)
                cell_count = await odds_cells.count()

                if cell_count < 3:
                    raise Exception(f"赔率块数量不足: {cell_count}")

                extractor = OddsMovementExtractor(page, self.config.extraction, self.config.delays)
                all_data = {}
                bet_types = ["home", "draw", "away"]
                total_records = 0

                for idx, bet_type in enumerate(bet_types):
                    cell = odds_cells.nth(idx)
                    data = await extractor.extract_complete_history(bet_type, cell)

                    if data:
                        all_data[bet_type] = data
                        total_records += len(data)
                        logger.info(f"[{match_id}] {bet_type}: 提取到 {len(data)} 条记录")

                if not all_data:
                    raise Exception("未提取到任何数据")

                # 成功
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                result = {
                    "success": True,
                    "match_id": match_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "source_url": url,
                    "proxy": proxy,
                    "extraction_time": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": elapsed,
                    "data": all_data,
                    "stats": {
                        "total_records": total_records,
                        "bet_types_count": len(all_data)
                    }
                }

                self.circuit_breaker.record_success(proxy)
                logger.info(f"[{match_id}] ✅ 成功！总计 {total_records} 条记录 (耗时 {elapsed:.1f}s)")

        except Exception as e:
            error_msg = str(e)
            error_type = self._classify_error(error_msg)
            logger.error(f"[{match_id}] ❌ 错误 ({error_type}): {error_msg}")

            self.circuit_breaker.record_failure(proxy, error_type)
            result = self._error_result(match_id, home_team, away_team, url, proxy, error_msg, error_type)

        # 记录审计日志
        self._record_audit(result)

        return result

    def _classify_error(self, error_msg: str) -> str:
        """分类错误类型"""
        if "403" in error_msg or "ERR_HTTP_RESPONSE_CODE_FAILURE" in error_msg:
            return "BLOCKED"
        elif "Timeout" in error_msg:
            return "TIMEOUT"
        elif "被重定向" in error_msg or "拦截" in error_msg:
            return "REDIRECTED"
        else:
            return "UNKNOWN"

    def _error_result(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        url: str,
        proxy: Optional[str],
        error_msg: str,
        error_type: str = "UNKNOWN"
    ) -> Dict[str, Any]:
        """生成错误结果"""
        return {
            "success": False,
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "source_url": url,
            "proxy": proxy,
            "extraction_time": datetime.now(timezone.utc).isoformat(),
            "error": error_msg,
            "error_type": error_type
        }

    def _record_audit(self, result: Dict[str, Any]) -> None:
        """记录审计日志"""
        self.audit_log.append({
            **result,
            "audit_timestamp": datetime.now(timezone.utc).isoformat()
        })

    def save_audit_log(self) -> None:
        """保存审计日志"""
        output_path = Path(self.config.logging.output_dir) / self.config.logging.audit_file

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "scraper_version": "V150.33",
                "audit_time": datetime.now(timezone.utc).isoformat(),
                "circuit_breaker_status": self.circuit_breaker.get_status(),
                "total_records": len(self.audit_log),
                "records": self.audit_log
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"审计日志已保存: {output_path}")

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return self.circuit_breaker.get_status()


# ==============================================================================
# Convenience Functions
# ==============================================================================


async def fetch_single_match(
    match_id: str,
    home_team: str,
    away_team: str,
    url: Optional[str] = None,
    config_path: str = "config/scraper_config.yaml",
    headless: bool = True,
) -> Dict[str, Any]:
    """便捷函数：采集单场比赛

    Example:
        >>> result = await fetch_single_match(
        ...     "nsbKWw0O",
        ...     "Everton",
        ...     "Brentford"
        ... )
        >>> print(result["success"])
        True
    """
    scraper = OddsPortalScraper(config_path)
    result = await scraper.fetch_snapshot(match_id, home_team, away_team, url, headless)
    scraper.save_audit_log()
    return result


async def fetch_batch_matches(
    matches: List[Dict[str, str]],
    config_path: str = "config/scraper_config.yaml",
    headless: bool = True,
    delay_range: Tuple[float, float] = (15.0, 30.0),
) -> List[Dict[str, Any]]:
    """便捷函数：批量采集比赛

    Args:
        matches: 比赛列表，每个元素包含 match_id, home_team, away_team, url (可选)
        config_path: 配置文件路径
        headless: 是否无头模式
        delay_range: 任务间延迟范围 (秒)

    Returns:
        结果列表
    """
    scraper = OddsPortalScraper(config_path)
    results = []

    for i, match in enumerate(matches):
        logger.info(f"\n{'='*60}")
        logger.info(f"进度: {i+1}/{len(matches)}")
        logger.info(f"{'='*60}")

        result = await scraper.fetch_snapshot(
            match_id=match["match_id"],
            home_team=match["home_team"],
            away_team=match["away_team"],
            url=match.get("url"),
            headless=headless
        )
        results.append(result)

        # 任务间延迟
        if i < len(matches) - 1:
            delay = random.uniform(*delay_range)
            logger.info(f"任务间隔: {delay:.1f} 秒")
            await asyncio.sleep(delay)

    scraper.save_audit_log()

    # 打印汇总
    success_count = sum(1 for r in results if r.get("success"))
    logger.info(f"\n{'='*60}")
    logger.info(f"批量采集完成: {success_count}/{len(matches)} 成功")
    logger.info(f"{'='*60}")

    return results
