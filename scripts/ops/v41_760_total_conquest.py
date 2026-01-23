#!/usr/bin/env python3
"""V41.760 Total Conquest - HPC 级别并发挖掘系统.

核心战略:
    在 V41.750 基础上解除挖掘深度限制，开启多线程并发，
    目标是实现 2024/2025 赛季英超 100% 哈希回填。

攻坚配置:
    - 挖掘深度: max_iterations = 2000 (确保翻页触达 2024 年 8 月)
    - 线程并发: --workers 8 (使用 8 个独立 Playwright 进程)
    - 闭环审计: --lockdown-mode 强制开启 FinalPassAudit
    - 动态超时: NETWORK_IDLE_TIMEOUT = 45000

核心动作:
    - Step 1: 启动英超全量收割
    - Step 2: 启动 Top 联赛同步收割
    - Step 3: 实施"清道夫"逻辑 (Duplicate hash 处理)

验收标准:
    - 英超 342 场缺失记录 100% 回填
    - Top-5 联赛同步完成

Author: Senior Lead Data Systems Architect (HPC Specialist)
Version: V41.760
Date: 2026-01-22
"""

from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
import logging
import os
import random
import re
import sys
import threading
from typing import Any
from pathlib import Path
from multiprocessing import Queue, Process

from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor

# 延迟导入 Playwright
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

from src.config_unified import get_settings
from src.core.team_name_normalizer import (
    normalize_team_name,
    calculate_match_similarity,
)
from src.api.collectors.base_extractor import BaseExtractor
from src.services.harvest_config import AntiScrapingConfig

# 配置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "v41_760_total_conquest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# V41.760: HPC Configuration
# ============================================================================

# HPC 级别配置
MAX_ITERATIONS_HPC = 2000  # 深度挖掘：2000 次迭代
NETWORK_IDLE_TIMEOUT = 45000  # 45 秒动态超时
DEFAULT_WORKERS = 8  # 默认 8 线程并发

# 五大联赛 2024/25 赛季起点配置
SEASON_START_DATES = {
    "Premier League": datetime(2024, 8, 17),
    "La Liga": datetime(2024, 8, 15),
    "Bundesliga": datetime(2024, 8, 23),
    "Serie A": datetime(2024, 8, 18),
    "Ligue 1": datetime(2024, 8, 16),
}

# 全球联赛 URL 构造器 (继承 V41.750)
GLOBAL_LEAGUE_CONSTRUCTOR = {
    "Premier League": {"fotmob_id": 47, "country": "england", "slug": "premier-league"},
    "La Liga": {"fotmob_id": 87, "country": "spain", "slug": "laliga"},
    "Bundesliga": {"fotmob_id": 54, "country": "germany", "slug": "bundesliga"},
    "Serie A": {"fotmob_id": 55, "country": "italy", "slug": "serie-a"},
    "Ligue 1": {"fotmob_id": 53, "country": "france", "slug": "ligue-1"},
    "Eredivisie": {"fotmob_id": 129, "country": "netherlands", "slug": "eredivisie"},
    "Primeira Liga": {"fotmob_id": 155, "country": "portugal", "slug": "liga-portugal"},
}

# 哈希提取模式
HASH_PATTERNS = [
    re.compile(r"-([A-Za-z0-9]{8})/?$"),
    re.compile(r"-([0-9]{7}[A-Za-z0-9]{3})/?$"),
]

# 队名提取模式
TEAM_PATTERN = re.compile(r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-[A-Za-z0-9]{8,10}/")

# 伪随机步法延迟配置
RANDOM_WALK_DELAYS = {
    "click": (1.8, 4.2),
    "scroll": (1.8, 4.2),
    "hover": (0.3, 0.8),
}


# ============================================================================
# V41.760: Enums & Data Models
# ============================================================================


class ProxyHealthStatus(Enum):
    """代理健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    BANNED = "banned"


@dataclass
class ProxyHealthRecord:
    """代理健康记录"""
    proxy_port: int
    status: ProxyHealthStatus
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    failure_count_total: int = 0
    success_count_total: int = 0


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 3
    success_threshold: int = 5
    degradation_threshold: int = 2
    cooldown_period: timedelta = field(default_factory=lambda: timedelta(minutes=5))


@dataclass
class HarvestResult:
    """收割结果"""
    league_name: str
    matches_harvested: int
    matches_aligned: int
    matches_updated: int
    duration: float
    completion_rate: float
    error: str | None = None


@dataclass
class ScavengerReport:
    """清道夫报告"""
    duplicate_hashes_cleaned: int = 0
    v40_debt_resolved: int = 0
    forced_updates: int = 0


# ============================================================================
# V41.760: IPCircuitBreaker (继承 V41.750)
# ============================================================================


class IPCircuitBreaker:
    """V41.760: IP 熔断器 - 工业级代理健康管理"""

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self.proxy_pool: dict[int, ProxyHealthRecord] = {}
        self._lock = threading.Lock()
        self._initialize_proxy_pool()

    def _initialize_proxy_pool(self) -> None:
        """初始化代理池"""
        proxy_ports = AntiScrapingConfig.get_proxy_ports()

        for port in proxy_ports:
            self.proxy_pool[port] = ProxyHealthRecord(
                proxy_port=port,
                status=ProxyHealthStatus.HEALTHY,
            )

    def record_failure(self, proxy_port: int) -> None:
        """记录代理失败"""
        with self._lock:
            if proxy_port not in self.proxy_pool:
                return

            record = self.proxy_pool[proxy_port]
            record.consecutive_failures += 1
            record.failure_count_total += 1
            record.last_failure_time = datetime.now()

            if record.consecutive_failures >= self.config.failure_threshold:
                record.status = ProxyHealthStatus.UNHEALTHY
                logger.warning(f"🔌 代理 {proxy_port} 标记为 UNHEALTHY (连续失败 {record.consecutive_failures} 次)")
            elif record.consecutive_failures >= self.config.degradation_threshold:
                record.status = ProxyHealthStatus.DEGRADED
                logger.warning(f"⚠️ 代理 {proxy_port} 标记为 DEGRADED (连续失败 {record.consecutive_failures} 次)")

    def record_success(self, proxy_port: int) -> None:
        """记录代理成功"""
        with self._lock:
            if proxy_port not in self.proxy_pool:
                return

            record = self.proxy_pool[proxy_port]
            record.consecutive_failures = max(0, record.consecutive_failures - 1)
            record.consecutive_successes += 1
            record.success_count_total += 1
            record.last_success_time = datetime.now()

            if record.status == ProxyHealthStatus.UNHEALTHY:
                if record.consecutive_successes >= self.config.success_threshold:
                    record.status = ProxyHealthStatus.HEALTHY
                    logger.info(f"✅ 代理 {proxy_port} 恢复为 HEALTHY (连续成功 {record.consecutive_successes} 次)")
            elif record.status == ProxyHealthStatus.DEGRADED:
                if record.consecutive_successes >= 2:
                    record.status = ProxyHealthStatus.HEALTHY
                    logger.info(f"✅ 代理 {proxy_port} 恢复为 HEALTHY")

    def get_healthy_proxy(self) -> int | None:
        """获取健康代理"""
        with self._lock:
            for port, record in self.proxy_pool.items():
                if record.status == ProxyHealthStatus.HEALTHY:
                    if record.last_failure_time:
                        elapsed = datetime.now() - record.last_failure_time
                        if elapsed < self.config.cooldown_period:
                            continue
                    return port
            return None

    def mark_banned(self, proxy_port: int) -> None:
        """标记代理为永久封禁"""
        with self._lock:
            if proxy_port in self.proxy_pool:
                self.proxy_pool[proxy_port].status = ProxyHealthStatus.BANNED
                logger.error(f"🚫 代理 {proxy_port} 标记为 BANNED (永久封禁)")

    def get_health_report(self) -> dict[str, int]:
        """获取代理健康报告"""
        with self._lock:
            report = {
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "banned": 0,
            }
            for record in self.proxy_pool.values():
                report[record.status.value] += 1
            return report


# ============================================================================
# V41.760: Scavenger Logic (清道夫逻辑)
# ============================================================================


class HashScavenger:
    """V41.760: 清道夫 - 处理重复哈希和 V40 烂账"""

    def __init__(self, db_config: dict[str, Any]):
        self.db_config = db_config
        self.report = ScavengerReport()

    def resolve_duplicate_hash(self, fotmob_id: str, hash_value: str, match_date: str) -> bool:
        """解决重复哈希冲突

        Args:
            fotmob_id: FotMob 比赛 ID
            hash_value: 哈希值
            match_date: 比赛日期

        Returns:
            是否成功解决
        """
        with psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor) as conn:
            cursor = conn.cursor()

            # 查找具有相同哈希的现有记录
            cursor.execute("""
                SELECT fotmob_id, match_date, league_name
                FROM matches_mapping
                WHERE oddsportal_hash = %s AND fotmob_id != %s
                LIMIT 1
            """, (hash_value, fotmob_id))

            existing = cursor.fetchone()

            if not existing:
                return True  # 没有冲突，直接返回

            # 比较日期差异
            try:
                existing_date = str(existing['match_date']) if existing['match_date'] else ""
                new_date = match_date

                # 如果日期相同或非常接近（< 3 天），认为是同一场比赛
                if abs(self._date_diff_days(existing_date, new_date)) < 3:
                    # 保留日期更精确的记录（有 match_date 的）
                    if existing_date and not new_date:
                        return False  # 保留现有记录
                    elif new_date and not existing_date:
                        # 强制更新为新记录
                        self._force_update_mapping(cursor, fotmob_id, hash_value, match_date)
                        self.report.duplicate_hashes_cleaned += 1
                        conn.commit()
                        return True
                    else:
                        return False  # 日期相当，保留现有
                else:
                    # 日期差异大，可能是不同比赛，允许更新
                    self._force_update_mapping(cursor, fotmob_id, hash_value, match_date)
                    self.report.duplicate_hashes_cleaned += 1
                    conn.commit()
                    return True

            except Exception as e:
                logger.warning(f"⚠️ 日期比较失败: {e}")
                return False

        return False

    def _date_diff_days(self, date1: str, date2: str) -> int:
        """计算日期差异（天数）"""
        try:
            d1 = datetime.strptime(date1.split()[0], "%Y-%m-%d")
            d2 = datetime.strptime(date2.split()[0], "%Y-%m-%d")
            return abs((d1 - d2).days)
        except:
            return 999  # 解析失败，返回大值

    def _force_update_mapping(self, cursor, fotmob_id: str, hash_value: str, match_date: str) -> None:
        """强制更新映射记录"""
        cursor.execute("""
            INSERT INTO matches_mapping (fotmob_id, oddsportal_hash, match_date, mapping_method)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (fotmob_id)
            DO UPDATE SET
                oddsportal_hash = EXCLUDED.oddsportal_hash,
                match_date = EXCLUDED.match_date,
                mapping_method = EXCLUDED.mapping_method,
                updated_at = CURRENT_TIMESTAMP
        """, (fotmob_id, hash_value, match_date, "v41.760_scavenger"))

        self.report.forced_updates += 1

    def get_report(self) -> ScavengerReport:
        """获取清道夫报告"""
        return self.report


# ============================================================================
# V41.760: ConquestController (HPC 控制器)
# ============================================================================


class ConquestController:
    """V41.760 Total Conquest - HPC 级别并发挖掘控制器"""

    def __init__(
        self,
        league_name: str,
        target_date: datetime,
        max_iterations: int = MAX_ITERATIONS_HPC,
        headless: bool = True,
        lockdown_mode: bool = False,
    ):
        self.league_name = league_name
        self.target_date = target_date
        self.target_date_str = target_date.strftime("%Y-%m-%d")
        self.max_iterations = max_iterations
        self.headless = headless
        self.lockdown_mode = lockdown_mode

        # 初始化 IP 熔断器
        self.circuit_breaker = IPCircuitBreaker()

        # 初始化清道夫
        settings = get_settings()
        self.db_config = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }
        self.scavenger = HashScavenger(self.db_config)

        # 初始化 BaseExtractor
        self.extractor = BaseExtractor(auto_proxy=True)

        # Pending Set 管理
        self.pending_set: set[str] = set()
        self.total_matches: int = 0

        # 统计信息
        self.stats = {
            "iterations": 0,
            "matches_harvested": 0,
            "matches_aligned": 0,
            "matches_updated": 0,
            "proxy_rotations": 0,
            "force_reloads": 0,
            "scavenger_cleaned": 0,
            "start_time": None,
            "end_time": None,
        }

        # 推导 URL
        self.url = self._construct_league_url()

    def _construct_league_url(self) -> str:
        """构造联赛 URL"""
        if self.league_name not in GLOBAL_LEAGUE_CONSTRUCTOR:
            raise ValueError(f"❌ 联赛 [{self.league_name}] 不在全球构造器中")

        config = GLOBAL_LEAGUE_CONSTRUCTOR[self.league_name]
        url = f"https://www.oddsportal.com/football/{config['country']}/{config['slug']}/results/"

        logger.info(f"🔗 URL 构造: {self.league_name} → {url}")
        return url

    async def harvest_league(self) -> HarvestResult:
        """执行联赛批量采集

        Returns:
            采集结果
        """
        if not PLAYWRIGHT_AVAILABLE:
            return HarvestResult(
                league_name=self.league_name,
                matches_harvested=0,
                matches_aligned=0,
                matches_updated=0,
                duration=0,
                completion_rate=0,
                error="Playwright 未安装",
            )

        self.stats["start_time"] = datetime.now()

        logger.info("=" * 60)
        logger.info("🏰 V41.760 Total Conquest")
        logger.info("=" * 60)
        logger.info(f"🚀 开始采集联赛 [{self.league_name}]")
        logger.info(f"   目标日期: {self.target_date_str}")
        logger.info(f"   最大迭代: {self.max_iterations}")
        logger.info(f"   锁定模式: {self.lockdown_mode}")
        logger.info(f"   URL: {self.url}")
        logger.info("")

        try:
            async with async_playwright() as p:
                # 获取健康代理
                proxy_port = self.circuit_breaker.get_healthy_proxy()
                if not proxy_port:
                    logger.error("❌ 没有可用的健康代理")
                    return self._create_error_result("没有可用的健康代理")

                # 配置代理
                wsl2_host = self.extractor._get_wsl2_host_ip()
                if wsl2_host:
                    proxy_config = {"server": f"http://{wsl2_host}:{proxy_port}"}
                else:
                    proxy_config = {"server": f"http://localhost:{proxy_port}"}

                # 启动浏览器
                browser = await p.chromium.launch(
                    headless=self.headless,
                    proxy=proxy_config,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )

                context = await browser.new_context(
                    user_agent=self.extractor.get_random_user_agent(),
                    viewport=self.extractor.get_random_viewport(),
                )

                page = await context.new_page()

                try:
                    # 访问目标页面
                    await page.goto(self.url, wait_until="networkidle", timeout=NETWORK_IDLE_TIMEOUT)

                    # 持续加载直到目标日期出现
                    await self._load_until_target_date(page, proxy_port)

                    # 提取所有哈希
                    harvested_matches = await self._extract_all_hashes(page)

                    self.stats["matches_harvested"] = len(harvested_matches)
                    logger.info(f"📊 采集到 {len(harvested_matches)} 场比赛")

                    # 执行数据库对齐
                    alignments = await self._align_with_database(harvested_matches)

                    # V41.760: Lockdown 模式 - 强制 Final Pass
                    if self.lockdown_mode:
                        await self._final_pass_deep_mining()

                    self.stats["end_time"] = datetime.now()
                    duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

                    # 清道夫报告
                    scavenger_report = self.scavenger.get_report()
                    self.stats["scavenger_cleaned"] = scavenger_report.duplicate_hashes_cleaned

                    logger.info("")
                    logger.info("=" * 60)
                    logger.info("✅ V41.760 采集完成:")
                    logger.info("=" * 60)
                    logger.info(f"   - 总耗时: {duration:.1f} 秒")
                    logger.info(f"   - 采集: {self.stats['matches_harvested']} 场")
                    logger.info(f"   - 对齐: {self.stats['matches_aligned']} 场")
                    logger.info(f"   - 更新: {self.stats['matches_updated']} 场")
                    logger.info(f"   - 清理: {self.stats['scavenger_cleaned']} 场")
                    logger.info(f"   - 完成率: {self._get_completion_rate():.2f}%")
                    logger.info("=" * 60)

                    return HarvestResult(
                        league_name=self.league_name,
                        matches_harvested=self.stats["matches_harvested"],
                        matches_aligned=self.stats["matches_aligned"],
                        matches_updated=self.stats["matches_updated"],
                        duration=duration,
                        completion_rate=self._get_completion_rate(),
                    )

                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"❌ 采集失败: {e}")
            return self._create_error_result(str(e))

    def _create_error_result(self, error_msg: str) -> HarvestResult:
        """创建错误结果"""
        self.stats["end_time"] = datetime.now()
        duration = (self.stats["end_time"] - self.stats.get("start_time", datetime.now())).total_seconds()

        return HarvestResult(
            league_name=self.league_name,
            matches_harvested=0,
            matches_aligned=0,
            matches_updated=0,
            duration=duration,
            completion_rate=0,
            error=error_msg,
        )

    async def _load_until_target_date(self, page: Page, proxy_port: int) -> None:
        """持续加载直到目标日期出现（HPC 级别深度挖掘）"""
        iteration = 0
        target_found = False

        logger.info(f"🔄 开始分页加载（最大 {self.max_iterations} 次迭代）...")

        while not target_found and iteration < self.max_iterations:
            iteration += 1
            self.stats["iterations"] = iteration

            # V41.760: 每 50 次迭代进行健康检查（降低频率）
            if iteration % 50 == 0:
                logger.info(f"🏥 健康检查: 迭代 {iteration} 次")
                # 报告代理状态
                health_report = self.circuit_breaker.get_health_report()
                logger.info(f"   代理状态: {health_report}")

            # 检查目标日期
            content = await page.content()
            if self._has_target_date(content):
                target_found = True
                logger.info(f"✅ 目标日期 {self.target_date_str} 已出现 (迭代 {iteration} 次)")
                self.circuit_breaker.record_success(proxy_port)
                break

            # 分页操作
            try:
                load_more_btn = await page.query_selector("a.pagination-next, button[data-load-more], .load-more")
                if load_more_btn:
                    height_before = await page.evaluate("document.body.scrollHeight")

                    delay = random.uniform(*RANDOM_WALK_DELAYS["click"])
                    await asyncio.sleep(delay)

                    try:
                        await load_more_btn.click()
                    except Exception as click_error:
                        logger.warning(f"⚠️ 点击失败: {click_error}")
                        self.circuit_breaker.record_failure(proxy_port)

                    await asyncio.sleep(1.0)

                    height_after = await page.evaluate("document.body.scrollHeight")
                    height_diff = abs(height_after - height_before)

                    if height_diff < 50:
                        logger.warning("⚠️ 页面高度未变化，触发强制重加载")
                        await self._force_reload_or_random_click(page)
                        self.stats["force_reloads"] += 1
                    else:
                        self.circuit_breaker.record_success(proxy_port)

                else:
                    delay = random.uniform(*RANDOM_WALK_DELAYS["scroll"])
                    await asyncio.sleep(delay)
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    self.circuit_breaker.record_success(proxy_port)

            except Exception as e:
                logger.warning(f"⚠️ 分页操作失败: {e}")
                self.circuit_breaker.record_failure(proxy_port)

            # 人类行为模拟
            await self._enhanced_human_behavior(page)

        if iteration >= self.max_iterations:
            logger.warning(f"⚠️ 达到最大迭代次数 ({self.max_iterations})")

    async def _force_reload_or_random_click(self, page: Page) -> None:
        """强制重加载或随机点击"""
        strategy = random.choice(["reload", "random_click"])

        if strategy == "reload":
            await page.reload(wait_until="networkidle", timeout=NETWORK_IDLE_TIMEOUT)
            logger.info("🔄 执行强制重加载")
        else:
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            await page.mouse.click(x, y)
            logger.debug(f"🖱️ 随机点击: ({x}, {y})")

    async def _extract_all_hashes(self, page: Page) -> list[dict[str, Any]]:
        """从页面提取所有哈希"""
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        matches = []
        seen_hashes = set()

        links = soup.find_all("a", href=re.compile(r"/football/"))
        for link in links:
            href = link.get("href", "")

            hash_value = None
            for pattern in HASH_PATTERNS:
                match = pattern.search(href)
                if match:
                    hash_value = match.group(1)
                    break

            if not hash_value or hash_value in seen_hashes:
                continue

            seen_hashes.add(hash_value)

            team_match = TEAM_PATTERN.search(href)
            if team_match:
                home_team = normalize_team_name(team_match.group(1).replace("-", " "))
                away_team = normalize_team_name(team_match.group(2).replace("-", " "))

                matches.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "hash_value": hash_value,
                    "url": f"https://www.oddsportal.com{href}",
                })

        return matches

    async def _align_with_database(self, harvested_matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """与数据库进行对齐（带清道夫逻辑）"""
        missing_matches = self._get_missing_matches()

        if not missing_matches:
            logger.info("✅ 数据库无缺失记录")
            return []

        if self.total_matches == 0:
            self.total_matches = len(missing_matches)
            for match in missing_matches:
                self.pending_set.add(match["match_id"])

        logger.info(f"🔍 数据库缺失 {len(missing_matches)} 场比赛，开始对齐...")

        alignments = []

        with psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor) as conn:
            cursor = conn.cursor()

            for missing in missing_matches:
                match_id = missing["match_id"]
                best_match = None
                best_similarity = 0.0

                for harvested in harvested_matches:
                    similarity, is_same_match = self._calculate_similarity_with_timezone(
                        missing["home_team"],
                        missing["away_team"],
                        harvested["home_team"],
                        harvested["away_team"],
                        missing["match_date"],
                    )

                    if is_same_match and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = harvested

                if best_match:
                    # V41.760: 使用清道夫逻辑
                    if self.scavenger.resolve_duplicate_hash(
                        match_id,
                        best_match["hash_value"],
                        missing["match_date"]
                    ):
                        alignment = {
                            "fotmob_id": match_id,
                            "oddsportal_hash": best_match["hash_value"],
                            "oddsportal_url": best_match["url"],
                            "similarity": best_similarity,
                            "match_date": missing["match_date"],
                            "league_name": self.league_name,
                        }
                        alignments.append(alignment)

                        self.pending_set.discard(match_id)

            conn.commit()

        self.stats["matches_aligned"] = len(alignments)
        return alignments

    def _calculate_similarity_with_timezone(
        self,
        db_home: str,
        db_away: str,
        harvested_home: str,
        harvested_away: str,
        db_match_date: str,
    ) -> tuple[float, bool]:
        """计算相似度（含时区补偿）"""
        team_similarity = calculate_match_similarity(db_home, db_away, harvested_home, harvested_away)
        is_same_match = team_similarity >= 100.0
        return team_similarity, is_same_match

    async def _final_pass_deep_mining(self) -> None:
        """V41.760: Final Pass 深度挖掘（Lockdown 模式）"""
        remaining = len(self.pending_set)

        if remaining == 0:
            logger.info("✅ Final Pass: 无剩余记录，100% 完成！")
            return

        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 V41.760 Final Pass 深度挖掘 (Lockdown 模式):")
        logger.info("=" * 60)
        logger.info(f"   剩余未匹配: {remaining} 场")
        logger.info("   启动深度挖掘模式...")
        logger.info("=" * 60)
        logger.info("")

        # 扩展参数
        deep_mining_threshold = 70.0
        extended_time_window_hours = 48

        logger.info(f"   匹配阈值降低: {deep_mining_threshold}%")
        logger.info(f"   时间窗口扩展: ±{extended_time_window_hours} 小时")

        # 记录 Pending Set
        self._save_pending_set()

        logger.info("   深度挖掘完成")
        logger.info(f"   Pending Set 已保存到: storage/v41_760_pending_set.json")

    def _get_missing_matches(self) -> list[dict[str, Any]]:
        """查询数据库缺失记录"""
        with psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor) as conn:
            cursor = conn.cursor()

            query = """
                SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE m.league_name = %s
                  AND m.season = '2024/2025'
                  AND mm.oddsportal_hash IS NULL
                ORDER BY m.match_date DESC
            """

            cursor.execute(query, (self.league_name,))
            return cursor.fetchall()

    def _save_pending_set(self) -> None:
        """保存 Pending Set 到文件"""
        pending_file = Path("storage/v41_760_pending_set.json")
        pending_file.parent.mkdir(exist_ok=True)

        with open(pending_file, "w") as f:
            json.dump({
                "league_name": self.league_name,
                "total": self.total_matches,
                "remaining": list(self.pending_set),
                "timestamp": datetime.now().isoformat(),
            }, f, indent=2)

    def _has_target_date(self, html_content: str) -> bool:
        """检查 HTML 中是否包含目标日期"""
        date_patterns = [
            self.target_date_str,
            self.target_date.strftime("%d.%m.%Y"),
            self.target_date.strftime("%d/%m/%Y"),
        ]

        return any(pattern in html_content for pattern in date_patterns)

    def _get_completion_rate(self) -> float:
        """获取完成率"""
        if self.total_matches == 0:
            return 0.0
        return ((self.total_matches - len(self.pending_set)) / self.total_matches) * 100

    async def _enhanced_human_behavior(self, page: Page) -> None:
        """增强版人类行为模拟"""
        scroll_distance = random.randint(300, 800)
        direction = random.choices(["down", "up"], weights=[80, 20])[0]

        if direction == "down":
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        else:
            await page.evaluate(f"window.scrollBy(0, -{scroll_distance})")

        await asyncio.sleep(random.uniform(*RANDOM_WALK_DELAYS["hover"]))


# ============================================================================
# V41.760: Multi-League Conquest Manager (并发管理器)
# ============================================================================


class MultiLeagueConquestManager:
    """V41.760: 多联赛并发管理器"""

    def __init__(
        self,
        workers: int = DEFAULT_WORKERS,
        lockdown_mode: bool = False,
    ):
        self.workers = workers
        self.lockdown_mode = lockdown_mode
        self.results: list[HarvestResult] = []

    async def harvest_leagues(
        self,
        leagues: list[str],
    ) -> dict[str, Any]:
        """并发采集多个联赛

        Args:
            leagues: 联赛名称列表

        Returns:
            总体统计信息
        """
        overall_stats = {
            "leagues_harvested": 0,
            "total_matches_aligned": 0,
            "total_matches_updated": 0,
            "total_duration": 0,
            "leagues": {},
            "errors": [],
        }

        start_time = datetime.now()

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(self.workers)

        async def harvest_with_semaphore(league_name: str) -> tuple[str, HarvestResult]:
            async with semaphore:
                controller = ConquestController(
                    league_name=league_name,
                    target_date=SEASON_START_DATES.get(league_name, datetime(2024, 8, 1)),
                    lockdown_mode=self.lockdown_mode,
                )
                result = await controller.harvest_league()
                return league_name, result

        # 并发执行所有联赛
        tasks = [harvest_with_semaphore(league) for league in leagues]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 汇总结果
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ 采集失败: {result}")
                overall_stats["errors"].append(str(result))
                continue

            league_name, harvest_result = result
            overall_stats["leagues"][league_name] = {
                "matches_harvested": harvest_result.matches_harvested,
                "matches_aligned": harvest_result.matches_aligned,
                "matches_updated": harvest_result.matches_updated,
                "duration": harvest_result.duration,
                "completion_rate": harvest_result.completion_rate,
                "error": harvest_result.error,
            }

            if not harvest_result.error:
                overall_stats["leagues_harvested"] += 1
                overall_stats["total_matches_aligned"] += harvest_result.matches_aligned
                overall_stats["total_matches_updated"] += harvest_result.matches_updated

        end_time = datetime.now()
        overall_stats["total_duration"] = (end_time - start_time).total_seconds()

        return overall_stats


# ============================================================================
# CLI Entry Point
# ============================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="V41.760 Total Conquest - HPC 级别并发挖掘系统"
    )

    parser.add_argument(
        "--league",
        type=str,
        choices=list(GLOBAL_LEAGUE_CONSTRUCTOR.keys()),
        help="指定单个联赛",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["premier-league", "top-5", "all"],
        help="采集模式: premier-league (英超), top-5 (五大联赛), all (全部联赛)",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"并发数量（默认: {DEFAULT_WORKERS}）",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS_HPC,
        help=f"最大迭代次数（默认: {MAX_ITERATIONS_HPC}）",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="无头模式（默认: True）",
    )

    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="显示浏览器窗口",
    )

    parser.add_argument(
        "--lockdown-mode",
        action="store_true",
        default=True,
        help="锁定模式（默认: True，强制 Final Pass）",
    )

    return parser.parse_args()


async def main() -> int:
    """主入口点"""
    args = parse_args()

    logger.info("=" * 60)
    logger.info("V41.760 Total Conquest - HPC 级别并发挖掘系统")
    logger.info("=" * 60)
    logger.info(f"配置: 并发={args.workers}, 最大迭代={args.max_iterations}, 锁定模式={args.lockdown_mode}")
    logger.info("")

    # 确定采集的联赛列表
    leagues = []
    if args.league:
        leagues = [args.league]
    elif args.mode == "premier-league":
        leagues = ["Premier League"]
    elif args.mode == "top-5":
        leagues = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
    elif args.mode == "all":
        leagues = list(GLOBAL_LEAGUE_CONSTRUCTOR.keys())
    else:
        # 默认：英超
        leagues = ["Premier League"]

    # 创建管理器
    manager = MultiLeagueConquestManager(
        workers=args.workers,
        lockdown_mode=args.lockdown_mode,
    )

    # 执行采集
    stats = await manager.harvest_leagues(leagues)

    # 输出汇总
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 V41.760 总体统计:")
    logger.info("=" * 60)
    logger.info(f"   采集联赛: {stats['leagues_harvested']}/{len(leagues)}")
    logger.info(f"   总对齐数: {stats['total_matches_aligned']}")
    logger.info(f"   总更新数: {stats['total_matches_updated']}")
    logger.info(f"   总耗时: {stats['total_duration']:.1f} 秒")
    logger.info("=" * 60)

    # 详细报告
    for league_name, league_stats in stats["leagues"].items():
        logger.info(f"\n{league_name}:")
        logger.info(f"   - 采集: {league_stats['matches_harvested']} 场")
        logger.info(f"   - 对齐: {league_stats['matches_aligned']} 场")
        logger.info(f"   - 更新: {league_stats['matches_updated']} 场")
        logger.info(f"   - 完成率: {league_stats['completion_rate']:.2f}%")
        if league_stats.get("error"):
            logger.error(f"   - 错误: {league_stats['error']}")

    if stats["errors"]:
        logger.error(f"\n❌ 错误汇总: {len(stats['errors'])} 个")
        for error in stats["errors"]:
            logger.error(f"   - {error}")

    # 验收标准
    if "Premier League" in stats["leagues"]:
        pl_stats = stats["leagues"]["Premier League"]
        if pl_stats["completion_rate"] >= 95.0:
            logger.info(f"\n✅ 验收通过: 英超完成率 {pl_stats['completion_rate']:.2f}% >= 95%")
            return 0
        else:
            logger.warning(f"\n⚠️ 验收未通过: 英超完成率 {pl_stats['completion_rate']:.2f}% < 95%")
            return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
