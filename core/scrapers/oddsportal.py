#!/usr/bin/env python3
"""V151.1 OddsPortal Scraper - Hash Hunting + Fault Tolerance.

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
    - V30.0 Fault Tolerance: 15s timeout for improved success rate (3s → 15s)
    - V150.53 Random Scroll: Enhanced stealth with random wheel deltas
    - V151.1 Hash Hunting: Search match URL by team names

Example:
    >>> from core.scrapers.oddsportal import OddsPortalScraper
    >>> scraper = OddsPortalScraper()
    >>> result = await scraper.fetch_snapshot("nsbKWw0O")
    >>> print(result["data"]["home"][0]["beijing_time"])
    '2024-04-27 15:30:00'
    >>> # V151.1: 搜索模式
    >>> search_result = await scraper.search_match_url("Real Madrid", "Barcelona")

Author: 高级反爬虫专家 & 性能优化工程师
Version: V151.1 (Hash Hunting Edition)
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
from playwright.async_api import Browser, Page

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
    # V36.4: 备选CSS选择器，用于西甲等特殊联赛
    fallback_selectors: List[str] = None

    def __post_init__(self):
        if self.fallback_selectors is None:
            self.fallback_selectors = [
                "div.flex-center.flex-col.font-bold",   # 主选择器
                "div.flex-center.flex-col",             # 备选1: 缺少font-bold
                "td[class*='odds']",                   # 备选2: 传统table结构
                ".odds-cell",                           # 备选3: 通用类
            ]

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
    """IP 熔断器管理器 (V30.3: 智能黑名单机制)"""

    # V30.3: 常量定义
    FORBIDDEN_THRESHOLD = 3  # 连续 3 次 403 错误触发黑名单
    BLACKLIST_TIMEOUT_MINUTES = 15  # 黑名单持续时间（分钟）

    def __init__(self, config: CircuitBreakerConfig, proxy_pool: List[str]):
        self.config = config
        self.proxy_pool = proxy_pool
        self.failed_counts: Dict[str, int] = defaultdict(int)
        self.cooldown_until: Dict[str, datetime] = {}
        self.tripped_count = 0

        # V30.3: 智能黑名单机制
        self.forbidden_counts: Dict[str, int] = defaultdict(int)  # 403 错误计数
        self.blacklist_until: Dict[str, datetime] = {}  # 黑名单过期时间

    def is_available(self, proxy: str) -> bool:
        """检查代理是否可用"""
        beijing_tz = timezone(timedelta(hours=8))

        # V30.3: 检查黑名单（优先级最高）
        if proxy in self.blacklist_until:
            if datetime.now(beijing_tz) < self.blacklist_until[proxy]:
                return False
            else:
                # 黑名单过期，清除记录
                del self.blacklist_until[proxy]
                self.forbidden_counts[proxy] = 0
                logger.info(f"🟢 代理 {proxy} 黑名单已解除")

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
        # V30.3: 成功时重置 403 计数
        self.forbidden_counts[proxy] = 0

    def record_failure(self, proxy: str, error_type: str) -> None:
        """记录失败"""
        self.failed_counts[proxy] += 1

        # V30.3: 检查是否为 403 Forbidden 错误
        if error_type == "HTTP_ERROR_403" or "403" in str(error_type):
            self.forbidden_counts[proxy] += 1
            logger.warning(f"⚠️ 代理 {proxy} 403 错误计数: {self.forbidden_counts[proxy]}/{self.FORBIDDEN_THRESHOLD}")

            # 连续 3 次 403 错误 → 黑名单
            if self.forbidden_counts[proxy] >= self.FORBIDDEN_THRESHOLD:
                beijing_tz = timezone(timedelta(hours=8))
                blacklist_end = datetime.now(beijing_tz) + timedelta(minutes=self.BLACKLIST_TIMEOUT_MINUTES)
                self.blacklist_until[proxy] = blacklist_end

                timestamp = blacklist_end.strftime("%Y-%m-%d %H:%M:%S")
                logger.error(
                    f"🚨 代理 {proxy} 已加入黑名单至 {timestamp} "
                    f"(连续 403 错误: {self.forbidden_counts[proxy]})"
                )
                return  # 已加入黑名单，不再触发普通熔断

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
        blacklisted = len(self.blacklist_until)

        return {
            "total_proxies": len(self.proxy_pool),
            "active_proxies": active,
            "tripped_proxies": self.tripped_count,
            "blacklisted_proxies": blacklisted,  # V30.3
            "availability_rate": f"{active/len(self.proxy_pool)*100:.1f}%",
        }

    def get_available_proxy(self) -> Optional[str]:
        """获取可用代理"""
        for proxy in self.proxy_pool:
            if self.is_available(proxy):
                return proxy
        return None

    def reset_all_proxies(self) -> Dict[str, Any]:
        """V32.0: 强制复位所有代理状态

        清除所有黑名单、冷却期和失败计数，用于一键恢复代理池。

        Returns:
            复位摘要字典，包含清除的统计信息

        Example:
            >>> manager.reset_all_proxies()
            {
                'blacklisted_cleared': 2,
                'cooldown_cleared': 1,
                'total_cleared': 3
            }
        """
        blacklisted_cleared = len(self.blacklist_until)
        cooldown_cleared = len(self.cooldown_until)

        # 清除所有状态
        self.blacklist_until.clear()
        self.forbidden_counts.clear()
        self.cooldown_until.clear()
        self.failed_counts.clear()

        # 记录日志
        logger.info("🔄 代理池已强制复位")
        logger.info(f"   清除黑名单: {blacklisted_cleared} 个")
        logger.info(f"   清除冷却期: {cooldown_cleared} 个")
        logger.info(f"   总清除: {blacklisted_cleared + cooldown_cleared} 个")

        return {
            "blacklisted_cleared": blacklisted_cleared,
            "cooldown_cleared": cooldown_cleared,
            "total_cleared": blacklisted_cleared + cooldown_cleared,
        }


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
    """变盘数据提取器 - V151.2 支持自定义超时"""

    def __init__(self, page: Page, config: ExtractionConfig, delay_config: DelayConfig = None, custom_timeout_ms: int = 15000):
        self.page = page
        self.config = config
        self.delay_config = delay_config or DelayConfig()
        self.custom_timeout_ms = custom_timeout_ms  # V151.2: 自定义超时（用于 malformed 重试）

    async def extract_complete_history(self, bet_type: str, cell_locator) -> List[Dict[str, Any]]:
        """
        提取完整的历史变盘记录（含滚动）
        V151.2: 支持自定义超时（malformed 重试使用 30s，正常采集使用 15s）

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
            # V36.3: 使用配置中的 hover_wait 而非硬编码值
            await asyncio.sleep(self.delay_config.hover_wait)

            # V151.2: 使用自定义超时（malformed 重试 30s，正常采集 15s）
            try:
                modal = self.page.locator(self.config.modal_selector).first
                await modal.wait_for(state="visible", timeout=self.custom_timeout_ms)
            except Exception:
                # V36.5: La Liga 等联赛没有历史变盘 modal，回退到提取当前可见赔率
                logger.debug(f"[{bet_type}] 无变盘数据（{self.custom_timeout_ms/1000}s内未弹出），尝试提取当前可见赔率")
                return await self._extract_current_visible_odds(bet_type, cell_locator)

            # 获取弹窗容器
            modal_container = self.page.locator(self.config.modal_selector).locator("xpath=ancestor::div[3]")

            # V151.2: 使用自定义超时提取
            html = await modal_container.inner_html(timeout=self.custom_timeout_ms)
            soup = BeautifulSoup(html, "html.parser")

            timestamps = soup.select("div.flex.flex-col.gap-1 > div.flex.gap-3 > div.font-normal")
            odds_values = soup.select("div.flex.flex-col.gap-1 + div.flex.flex-col.gap-1 > div.font-bold")

            initial_count = len(timestamps)
            data = self._parse_odds_data(timestamps, odds_values)

            # 滚动加载更多
            if self.config.enable_aggressive_scroll:
                await self._aggressive_scroll(modal_container)

                # V151.2: 使用自定义超时再次提取
                html = await modal_container.inner_html(timeout=self.custom_timeout_ms)
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

    async def _extract_current_visible_odds(self, bet_type: str, cell_locator) -> List[Dict[str, Any]]:
        """
        V36.5: 提取当前可见的赔率值（回退方案）
        用于 La Liga 等没有历史变盘 modal 的联赛

        Args:
            bet_type: 投注类型 (home/draw/away)
            cell_locator: 赔率单元格定位器

        Returns:
            单条当前赔率记录
        """
        try:
            # 获取当前可见的文本内容
            text_content = await cell_locator.inner_text(timeout=5000)

            # 清理文本，提取赔率值
            odds_value = text_content.strip()

            # 验证是否为有效的赔率格式（正数，通常 1.01 - 100.00）
            try:
                odds_float = float(odds_value)
                if not (1.01 <= odds_float <= 100.00):
                    logger.warning(f"[{bet_type}] 可见赔率值异常: {odds_value}")
                    return []
            except ValueError:
                logger.warning(f"[{bet_type}] 可见赔率值无法解析: {odds_value}")
                return []

            # 获取当前北京时间
            beijing_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M")

            # 返回与历史数据相同格式的单条记录
            result = [{
                "original_time": current_time,
                "beijing_time": current_time,
                "odds": odds_value,
                "timezone_info": "Current (No History)",
                "is_current_only": True  # 标记这是当前赔率，非历史数据
            }]

            logger.info(f"[{bet_type}] ✅ 提取当前可见赔率: {odds_value}")
            return result

        except Exception as e:
            logger.error(f"[{bet_type}] 提取当前可见赔率失败: {e}")
            return []

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
        slow_mo: int = 0,
    ) -> AsyncGenerator[Tuple[Browser, Page], None]:
        """创建隐身浏览器上下文

        Args:
            proxy: 代理服务器 (None = 自动选择)
            headless: 是否无头模式
            slow_mo: 慢动作延迟（毫秒），用于调试观察

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
                args=["--disable-blink-features=AutomationControlled"],
                slow_mo=slow_mo  # V40.6.1: 支持慢动作模式
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
        custom_timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """执行核心逻辑：导航 -> 定位 Pinnacle 行 -> Hover 触发 -> 解析 JSON 赔率

        Args:
            match_id: 8 位短哈希 ID
            home_team: 主队名称
            away_team: 客队名称
            url: 完整 URL (可选，如不提供则自动构建)
            headless: 是否无头模式
            custom_timeout_ms: V151.2 自定义超时时间（毫秒）- 用于 malformed 重试

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

                # V36.4: CSS 选择器回退机制（应对西甲等特殊联赛页面结构）
                selectors_to_try = [
                    self.config.extraction.odds_cells_selector  # 主选择器
                ] + self.config.extraction.fallback_selectors   # 回退选择器

                odds_cells = None
                cell_count = 0
                successful_selector = None

                for idx, selector in enumerate(selectors_to_try):
                    selector_type = "主选择器" if idx == 0 else f"回退选择器 #{idx}"
                    logger.info(f"[{match_id}] 尝试 {selector_type}: {selector}")

                    test_cells = first_row.locator(selector)
                    test_count = await test_cells.count()

                    logger.info(f"[{match_id}] {selector_type} 找到 {test_count} 个单元格")

                    if test_count >= 3:
                        odds_cells = test_cells
                        cell_count = test_count
                        successful_selector = selector
                        logger.info(f"[{match_id}] ✅ 使用 {selector_type}: {selector}")
                        break

                if cell_count < 3:
                    # V36.4: 提供详细的失败信息（所有选择器都失败）
                    selector_summary = "; ".join([
                        f"{'主' if idx == 0 else f'回退#{idx}'}: sel='{sel}' count={await first_row.locator(sel).count()}"
                        for idx, sel in enumerate(selectors_to_try)
                    ])
                    raise Exception(
                        f"V36.4: 所有选择器均无法找到完整赔率数据 (cell_count={cell_count} < 3)\n"
                        f"详细尝试: {selector_summary}"
                    )

                # V151.2: 传递自定义超时给提取器（malformed 重试 30s，正常采集 15s）
                timeout_ms = custom_timeout_ms if custom_timeout_ms else 15000
                extractor = OddsMovementExtractor(page, self.config.extraction, self.config.delays, custom_timeout_ms=timeout_ms)
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

    async def search_match_url(
        self,
        home_team: str,
        away_team: str,
        league_hint: Optional[str] = None,
        headless: bool = True,
    ) -> Dict[str, Any]:
        """V151.2: 通过 OddsPortal 搜索功能获取真实哈希 URL（深度加固版）

        核心逻辑:
        1. 访问 OddsPortal 搜索页面（带联赛提示）
        2. 输入对阵名称 + 联赛名称 (如 "Real Madrid vs Barcelona La Liga")
        3. 点击搜索结果
        4. 验证 URL 深度匹配（必须包含队名 Slug）
        5. 从重定向后的 URL 中提取真实哈希

        Args:
            home_team: 主队名称
            away_team: 客队名称
            league_hint: 联赛提示 (可选，推荐使用以提高精度)
            headless: 是否无头模式

        Returns:
            {
                "success": True/False,
                "url": "https://www.oddsportal.com/football/.../hash/",
                "match_id": "8位哈希",
                "home_team": "标准化后的主队名",
                "away_team": "标准化后的客队名",
                "proxy": "使用的代理",
                "error": None (如果失败)
            }
        """
        import re
        import unicodedata

        # V151.2: 搜索词增强 - 追加联赛名称
        search_query = f"{home_team} {away_team}"
        if league_hint:
            search_query = f"{search_query} {league_hint}"
        search_url = f"{self.BASE_URL}/search/{search_query.replace(' ', '-')}"

        # V151.2: 预计算队名 Slug（用于深度匹配）
        def slugify(name: str) -> str:
            """将队名转换为 URL slug 格式"""
            # Unicode 规范化 (NFD 分解)
            normalized = unicodedata.normalize('NFD', name)
            # 移除变音符号
            ascii_only = ''.join(
                c for c in normalized
                if unicodedata.category(c) != 'Mn'
            )
            # 转小写，空格转连字符
            return ascii_only.lower().replace(' ', '-').replace("'", '')

        home_slug = slugify(home_team)
        away_slug = slugify(away_team)

        proxy = self.circuit_breaker.get_available_proxy()
        if proxy is None:
            return {
                "success": False,
                "url": None,
                "match_id": None,
                "home_team": home_team,
                "away_team": away_team,
                "proxy": None,
                "error": "无可用代理"
            }

        logger.info(f"[搜索] 开始搜索: {home_team} vs {away_team}" + (f" ({league_hint})" if league_hint else ""))
        logger.info(f"[搜索] 搜索 URL: {search_url}")
        logger.info(f"[搜索] 预期 Slug: {home_slug} / {away_slug}")

        try:
            async with self.stealth_context(proxy=proxy, headless=headless) as (browser, page):
                # 步骤 1: 访问搜索页面
                logger.info("[搜索] 步骤 1: 访问搜索页面...")
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

                # 步骤 2: 等待搜索结果加载
                logger.info("[搜索] 步骤 2: 等待搜索结果...")
                await asyncio.sleep(5)

                # 步骤 3: 查找比赛结果链接
                logger.info("[搜索] 步骤 3: 查找比赛结果...")

                # 尝试多种选择器
                selectors = [
                    f"a:has-text('{home_team}')",
                    f"div[data-name] a:has-text('{home_team}')",
                    "table tr a[href*='/football/']",
                    "div.search-result a[href*='/football/']",
                ]

                match_link = None
                for selector in selectors:
                    try:
                        elements = await page.locator(selector).all()
                        for element in elements:
                            href = await element.get_attribute("href")
                            if href and "/football/" in href:
                                # 检查是否包含两队名称
                                text = await element.inner_text()
                                if (home_team.lower() in text.lower() and
                                    away_team.lower() in text.lower()):
                                    match_link = element
                                    logger.info(f"[搜索] 找到匹配结果: {text.strip()}")
                                    break
                        if match_link:
                            break
                    except Exception:
                        continue

                if not match_link:
                    # 如果没找到，尝试使用更通用的搜索
                    logger.warning("[搜索] 未找到精确匹配，尝试通用搜索...")
                    match_link = page.locator("a[href*='/football/']").first

                # 步骤 4: 点击链接并获取最终 URL
                if match_link:
                    logger.info("[搜索] 步骤 4: 点击链接...")
                    await match_link.click()
                    await asyncio.sleep(3)

                    # 获取当前 URL (应该包含哈希)
                    final_url = page.url
                    logger.info(f"[搜索] 最终 URL: {final_url}")

                    # V151.2: URL 深度匹配验证
                    # 检查 URL 是否包含两队名称的 slug
                    url_lower = final_url.lower()
                    contains_home = home_slug in url_lower
                    contains_away = away_slug in url_lower

                    logger.info(f"[搜索] 深度匹配: home_slug={home_slug} ({contains_home}), away_slug={away_slug} ({contains_away})")

                    if not (contains_home and contains_away):
                        logger.error("[搜索] ❌ URL 深度匹配失败！URL 不包含预期的队名 Slug")
                        logger.error(f"[搜索]    预期: {home_slug} 和 {away_slug}")
                        logger.error(f"[搜索]    实际 URL: {final_url}")
                        return {
                            "success": False,
                            "url": final_url,
                            "match_id": None,
                            "home_team": home_team,
                            "away_team": away_team,
                            "proxy": proxy,
                            "error": f"URL 深度匹配失败: 不包含队名 Slug (预期: {home_slug}/{away_slug})"
                        }

                    # 从 URL 中提取哈希
                    # V151.2: 支持带锚点的 URL（如 #1X2;2）
                    # V40.6: 修复正则 - 哈希在队名组合末尾（如 aston-villa-everton-QqZ8ajtB）
                    # 先尝试移除锚点
                    url_without_anchor = final_url.split('#')[0]
                    # 修复：匹配连字符后的 8-12 位哈希（支持混合大小写）
                    hash_match = re.search(r'-([a-zA-Z0-9]{8,12})/?(?:#|$)', url_without_anchor)
                    if hash_match:
                        match_id = hash_match.group(1)
                        logger.info(f"[搜索] ✅ 成功提取哈希: {match_id}")

                        return {
                            "success": True,
                            "url": final_url,
                            "match_id": match_id,
                            "home_team": home_team,
                            "away_team": away_team,
                            "proxy": proxy,
                            "error": None
                        }
                    else:
                        logger.warning(f"[搜索] ⚠️ 无法从 URL 中提取哈希: {final_url}")
                        return {
                            "success": False,
                            "url": final_url,
                            "match_id": None,
                            "home_team": home_team,
                            "away_team": away_team,
                            "proxy": proxy,
                            "error": "无法从 URL 中提取哈希"
                        }
                else:
                    logger.error("[搜索] ❌ 未找到比赛结果")
                    return {
                        "success": False,
                        "url": None,
                        "match_id": None,
                        "home_team": home_team,
                        "away_team": away_team,
                        "proxy": proxy,
                        "error": "未找到比赛结果"
                    }

        except Exception as e:
            logger.error(f"[搜索] ❌ 搜索失败: {e}")
            return {
                "success": False,
                "url": None,
                "match_id": None,
                "home_team": home_team,
                "away_team": away_team,
                "proxy": proxy,
                "error": str(e)
            }


# ==============================================================================
# V40.6: Results Page Dynamic Loading (暴力滚动 + 循环点击策略)
# ==============================================================================

    async def detect_show_more_button(
        self,
        page: Page,
        current_page_num: int = 1,
        visited_pages: set = None
    ) -> Optional[Locator]:
        """V40.6: 检测 Show More 按钮

        V40.6.1 更新: 支持"Show More"按钮和分页链接两种模式
                     智能选择下一个未访问的页码

        Args:
            page: Playwright Page 对象
            current_page_num: 当前页码
            visited_pages: 已访问的页码集合

        Returns:
            按钮 Locator 对象，如果不存在返回 None
        """
        if visited_pages is None:
            visited_pages = {1}

        # 首先尝试检测分页链接（OddsPortal 使用分页）
        try:
            pagination_links = await page.locator('.pagination a').all()
            if pagination_links and len(pagination_links) > 1:
                # V40.6.1: 查找下一个未访问的页码
                for link in pagination_links:
                    text = await link.inner_text()
                    text = text.strip()

                    # 尝试解析为数字
                    if text.isdigit():
                        page_num = int(text)
                        # 只返回未访问过的页码，且按顺序访问
                        if page_num not in visited_pages and page_num > current_page_num:
                            logger.debug(f"[V40.6.1] 🔍 找到未访问的分页链接: 第 {page_num} 页")
                            return link
                    elif text.lower() == 'next':
                        # "Next"链接作为最后选择
                        logger.debug(f"[V40.6.1] 🔍 找到 Next 分页链接")
                        return link
        except Exception as e:
            logger.debug(f"[V40.6.1] ⚠️ 分页检测失败: {e}")

        # 如果没有分页，尝试传统的"Show More"按钮
        selectors = [
            # V40.10: 优先使用 ID 选择器（法甲等页面使用）
            "#show-more-btn",
            "#showMoreButton",
            "#load-more-btn",
            # V40.6.1: 扩展选择器列表
            ".eventRow-showMore",
            ".show-more",
            "[data-testid='show-more']",
            "button:has-text('Show more')",
            "button:has-text('Show More')",
            "button:has-text('show more')",
            "button:has-text('Load more')",
            "button:has-text('Load More')",
            "a:has-text('Show more')",
            "a:has-text('Show More')",
            # 尝试更通用的选择器
            ".show-more-button",
            ".load-more",
            ".load-more-button",
            "[data-action='show-more']",
            "div:has-text('Show more')",
            "div:has-text('Load more')",
            "span:has-text('Show more')",
            "span:has-text('Load more')",
            # 尝试文字匹配
            "text=Show more",
            "text=Show More",
            "text=show more",
            "text=Load more",
            "text=Load More",
        ]

        for selector in selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0:
                    is_visible = await button.is_visible()
                    if is_visible:
                        logger.debug(f"[V40.6.1] 🔍 找到 Show More 按钮: {selector}")
                        return button
            except Exception:
                continue

        # V40.6.1: 如果没有找到按钮，尝试滚动到页面底部后再次检测
        logger.debug(f"[V40.6.1] 🔄 未找到 Show More 按钮，尝试滚动到页面底部")
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            for selector in selectors:
                try:
                    button = page.locator(selector).first
                    if await button.count() > 0:
                        is_visible = await button.is_visible()
                        if is_visible:
                            logger.info(f"[V40.6.1] 🔍 滚动后找到 Show More 按钮: {selector}")
                            return button
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"[V40.6.1] ⚠️ 滚动检测失败: {e}")

        return None

    async def is_page_height_stable(
        self,
        page: Page,
        height_history: List[int],
        current_height: int,
        stable_threshold: int = 3,
        height_tolerance: int = 100
    ) -> bool:
        """V40.6: 检测页面高度是否稳定

        Args:
            page: Playwright Page 对象
            height_history: 高度历史记录
            current_height: 当前高度
            stable_threshold: 页面高度稳定阈值（连续N次高度不变视为稳定）
            height_tolerance: 高度容忍度（像素）

        Returns:
            True 如果页面高度稳定
        """
        if len(height_history) < stable_threshold:
            return False

        # 检查最近 N 次高度变化是否在容忍范围内
        recent_heights = height_history[-stable_threshold:]
        min_height = min(recent_heights)
        max_height = max(recent_heights)
        height_diff = max_height - min_height

        return height_diff <= height_tolerance

    async def get_match_count_from_results_page(self, page: Page) -> int:
        """V40.6: 从 Results 页面获取比赛数量

        Args:
            page: Playwright Page 对象

        Returns:
            比赛数量
        """
        try:
            # 尝试多个可能的选择器
            selectors = [
                "table.participants tr",
                ".eventRow",
                "[data-testid='match-row']",
                "tr.match-row",
            ]

            for selector in selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        return count
                except Exception:
                    continue

            # 如果所有选择器都失败，使用页面高度估算
            height = await page.evaluate("() => document.body.scrollHeight")
            estimated_count = height // 100  # 粗略估算
            return max(estimated_count, 30)

        except Exception:
            # 默认返回 30（初始加载量）
            return 30

    async def harvest_results_page(
        self,
        results_url: str,
        min_matches: int = 300,
        max_iterations: int = 50,
        headless: bool = True,
        slow_mo: int = 0,
    ) -> Dict[str, Any]:
        """V40.6.1: 暴力滚动 + 循环点击策略 - 采集 Results 页面所有比赛

        Args:
            results_url: Results 页面 URL (例如: https://www.oddsportal.com/football/england/premier-league-2023-2024/results/)
            min_matches: 最小比赛数量目标
            max_iterations: 最大迭代次数（防止无限循环）
            headless: 是否无头模式
            slow_mo: 慢动作延迟（毫秒），用于调试观察

        Returns:
            {
                "success": True/False,
                "final_match_count": int,
                "iterations": int,
                "termination_reason": str,
                "match_urls": List[str],  # 所有比赛的 URL
                "match_count_history": List[int],  # V40.6.1: 比赛数量历史
                "error": Optional[str]
            }
        """
        start_time = datetime.now(timezone.utc)
        height_history: List[int] = []
        match_count_history: List[int] = []  # V40.6.1: 追踪比赛数量变化
        no_progress_count: int = 0  # V40.6.1: 无进展计数器
        iterations = 0
        termination_reason = "unknown"
        error = None
        match_urls: List[str] = []

        try:
            async with self.stealth_context(headless=headless, slow_mo=slow_mo) as (browser, page):
                logger.info(f"[V40.6.1] 🎯 开始采集 Results 页面: {results_url}")
                logger.info(f"[V40.6.1] 🎯 目标: 最小 {min_matches} 场比赛")

                # 步骤 1: 导航到 Results 页面
                await page.goto(results_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                await self.behavior_simulator.simulate_reading(page)

                # 步骤 2: 获取初始高度和比赛数量
                initial_height = await page.evaluate("() => document.body.scrollHeight")
                height_history.append(initial_height)
                initial_match_count = await self.get_match_count_from_results_page(page)
                match_count_history.append(initial_match_count)
                logger.info(f"[V40.6.1] 📏 初始页面高度: {initial_height}px")
                logger.info(f"[V40.6.1] 📊 初始比赛数量: {initial_match_count}")

                # V40.6.2: 提取第 1 页的比赛 URL（使用 XPath 宽泛选择 + 手动过滤）
                try:
                    # 获取所有包含横杠的链接
                    initial_links = await page.locator("//a[contains(@href, '-')]").all()
                    for link in initial_links:
                        href = await link.get_attribute("href")
                        # V40.6.2: 修复哈希检测 - 使用横杠数量而非 /-/ 模式
                        if href and href.count("-") >= 4:  # 比赛链接通常有 4+ 个横杠
                            full_url = self.BASE_URL + href if href.startswith("/") else href
                            if full_url not in match_urls:
                                match_urls.append(full_url)
                    logger.info(f"[V40.6.2] 📦 第 1 页提取 {len(match_urls)} 个唯一 URL")
                except Exception as e:
                    logger.warning(f"[V40.6.2] ⚠️ 提取第 1 页 URL 失败: {e}")

                # V40.6.1: 初始滚动到页面底部（触发动态加载）
                logger.info(f"[V40.6.1] 🔄 初始滚动到页面底部")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # 重新获取滚动后的比赛数量
                after_scroll_match_count = await self.get_match_count_from_results_page(page)
                match_count_history.append(after_scroll_match_count)
                logger.info(f"[V40.6.1] 📊 滚动后比赛数量: {after_scroll_match_count}")

                # V40.6.1: 慢动作模式（用于观察）
                if slow_mo > 0:
                    logger.info(f"[V40.6.1] 🔍 慢动作模式: {slow_mo}ms 延迟")

                # 步骤 3: 循环点击 Show More 按钮 / 分页链接
                no_button_count = 0  # V40.6.1: 连续未找到按钮的次数
                current_page_num = 1  # V40.6.1: 当前页码
                visited_pages = {1}  # V40.6.1: 已访问的页码
                prev_url_count = 0  # V40.6.2: 上一次迭代的 URL 数量

                while iterations < max_iterations:
                    iterations += 1
                    prev_match_count = match_count_history[-1] if match_count_history else 0

                    # 检测 Show More 按钮 / 分页链接
                    # V40.6.1: 优先查找下一个未访问的页码链接
                    show_more_button = await self.detect_show_more_button(page, current_page_num, visited_pages)

                    if show_more_button is None:
                        no_button_count += 1
                        logger.info(f"[V40.6.1] ⚠️ 未找到 Show More 按钮 (第 {no_button_count} 次)")

                        current_match_count = await self.get_match_count_from_results_page(page)
                        if current_match_count >= min_matches:
                            termination_reason = "button_disappeared_min_matches_reached"
                            logger.info(f"[V40.6.1] ✅ Show More 按钮消失，已达到最小比赛数量: {current_match_count}")
                            break
                        elif no_button_count >= 5:  # V40.6.1: 连续 5 次未找到按钮才终止
                            termination_reason = "no_button_found"
                            logger.warning(f"[V40.6.1] ⚠️ 连续 5 次未找到 Show More 按钮，终止采集")
                            break

                        # 尝试滚动后再检测
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(1)
                        continue
                    else:
                        no_button_count = 0  # 重置计数器

                    # 点击 Show More 按钮 / 分页链接
                    if show_more_button is not None:
                        try:
                            # V40.6.1: 检查是否是分页链接
                            is_pagination = False
                            target_page_num = current_page_num

                            try:
                                button_text = await show_more_button.inner_text()
                                button_text = button_text.strip()

                                is_pagination = button_text.isdigit() or button_text.lower() == 'next'

                                if is_pagination and button_text.isdigit():
                                    target_page_num = int(button_text)
                                    logger.info(f"[V40.6.1] 🔘 点击分页链接: 第 {target_page_num} 页 (迭代 {iterations})")
                                    visited_pages.add(target_page_num)
                                    current_page_num = target_page_num
                                elif is_pagination and button_text.lower() == 'next':
                                    logger.info(f"[V40.6.1] 🔘 点击 Next 分页链接 (迭代 {iterations})")
                                    current_page_num += 1
                                    visited_pages.add(current_page_num)
                                else:
                                    logger.info(f"[V40.6.1] 🔘 点击 Show More 按钮 (迭代 {iterations})")
                            except:
                                logger.info(f"[V40.6.1] 🔘 点击 Show More 按钮 (迭代 {iterations})")

                            await show_more_button.click()

                            # V40.6.2: 等待页面导航或内容加载（增强版）
                            if is_pagination:
                                # 分页链接会导致页面导航，等待加载完成
                                logger.info(f"[V40.6.2] ⏳ 等待页面导航...")
                                try:
                                    await page.wait_for_load_state("networkidle", timeout=15000)
                                except:
                                    await asyncio.sleep(3)  # 备用等待

                                # V40.6.2: 关键修复 - 额外等待内容渲染
                                logger.info(f"[V40.6.2] 🔄 等待内容渲染...")
                                await asyncio.sleep(2)

                                # V40.6.2: 滚动触发内容加载
                                logger.info(f"[V40.6.2] 🔄 滚动触发内容加载...")
                                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                await asyncio.sleep(2)
                            else:
                                # Show More 按钮只会加载内容，不会导航
                                if slow_mo > 0:
                                    await asyncio.sleep(slow_mo / 1000)
                                else:
                                    await asyncio.sleep(0.5)
                                await self.behavior_simulator.natural_scroll(page)

                            # 滚动到页面底部
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await asyncio.sleep(1)

                            # V40.6.2: 提取当前页面的比赛 URL（累积模式 + 修复的选择器）
                            try:
                                # 获取所有包含横杠的链接
                                page_links = await page.locator("//a[contains(@href, '-')]").all()
                                page_urls_count = 0
                                for link in page_links:
                                    href = await link.get_attribute("href")
                                    # V40.6.2: 修复哈希检测 - 使用横杠数量而非 /-/ 模式
                                    if href and href.count("-") >= 4:  # 比赛链接通常有 4+ 个横杠
                                        full_url = self.BASE_URL + href if href.startswith("/") else href
                                        if full_url not in match_urls:
                                            match_urls.append(full_url)
                                        page_urls_count += 1

                                logger.info(f"[V40.6.2] 📦 当前页面提取 {page_urls_count} 个 URL，总计 {len(match_urls)} 个唯一 URL")
                            except Exception as e:
                                logger.warning(f"[V40.6.2] ⚠️ 提取页面 URL 失败: {e}")

                        except Exception as e:
                            error = f"点击按钮失败: {e}"
                            termination_reason = "click_error"
                            logger.error(f"[V40.6.1] ❌ {error}")
                            break

                    # 检查页面高度
                    current_height = await page.evaluate("() => document.body.scrollHeight")
                    height_history.append(current_height)

                    # 获取当前比赛数量
                    current_match_count = await self.get_match_count_from_results_page(page)
                    match_count_history.append(current_match_count)

                    # V40.6.2: 熔断机制 - 检查累积 URL 数量增长（而非单页数量）
                    url_count_diff = len(match_urls) - prev_url_count

                    if url_count_diff == 0:
                        no_progress_count += 1
                        logger.info(f"[V40.6.2] ⚠️ 无进展计数: {no_progress_count}/3 (当前 URL: {len(match_urls)})")
                        if no_progress_count >= 3:
                            termination_reason = "no_progress_termination"
                            logger.warning(f"[V40.6.2] 🛑 熔断触发: 连续 3 次无进展，终止采集")
                            logger.warning(f"[V40.6.2] 📊 已捕获 URL: {len(match_urls)} 个")

                            # V40.6.1: "死后现场"截图
                            try:
                                from pathlib import Path
                                crash_site_path = Path("logs/v40_6_1_crash_site.png")
                                crash_site_path.parent.mkdir(parents=True, exist_ok=True)
                                await page.screenshot(path=str(crash_site_path), full_page=True)
                                logger.info(f"[V40.6.1] 📸 死后现场截图已保存: {crash_site_path}")
                            except Exception as e:
                                logger.error(f"[V40.6.1] ⚠️ 截图失败: {e}")

                            break
                    else:
                        no_progress_count = 0  # 重置计数器
                        logger.info(f"[V40.6.2] 📈 进展: +{url_count_diff} 个 URL (总计: {len(match_urls)})")

                    # 更新 prev_url_count 为下一次迭代做准备
                    prev_url_count = len(match_urls)

                    # V40.6.2: 禁用页面高度稳定检查（分页模式下不准确）
                    # 分页后页面高度自然稳定，但不代表没有更多内容
                    # 只有在找不到按钮时才停止

                    # 检查比赛数量
                    if current_match_count >= min_matches:
                        termination_reason = "min_matches_reached"
                        logger.info(f"[V40.6.1] ✅ 已达到最小比赛数量: {current_match_count}")
                        break

                    if iterations % 5 == 0:
                        logger.info(f"[V40.6.1] 🔄 进度: 迭代 {iterations}, 当前比赛: {current_match_count}, 页面高度: {current_height}px")

                # 步骤 4: 最终统计
                # V40.6.1: 使用累积的唯一 URL 数量作为最终比赛数量
                final_match_count = len(match_urls)
                logger.info(f"[V40.6.1] 📊 最终唯一 URL 数量: {final_match_count}")
                logger.info(f"[V40.6.1] 📜 比赛数量历史（各页）: {match_count_history}")

                # 提取比赛链接（已累积，这里只是为了日志输出）
                logger.info(f"[V40.6.1] 🔗 已收集 {len(match_urls)} 个唯一比赛链接")

                success = final_match_count >= min_matches

                return {
                    "success": success,
                    "final_match_count": final_match_count,
                    "iterations": iterations,
                    "termination_reason": termination_reason,
                    "match_urls": match_urls,
                    "match_count_history": match_count_history,  # V40.6.1
                    "error": error
                }

        except Exception as e:
            error = str(e)
            logger.error(f"[V40.6.1] ❌ 采集 Results 页面失败: {e}")
            return {
                "success": False,
                "final_match_count": match_count_history[-1] if match_count_history else 0,
                "iterations": iterations,
                "termination_reason": "exception",
                "match_urls": match_urls,
                "match_count_history": match_count_history,
                "error": error
            }


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
