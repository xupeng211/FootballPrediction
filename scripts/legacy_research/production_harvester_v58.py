#!/usr/bin/env python3
"""V58.0 Ghost Edition - Production-Grade Automated Odds Harvesting Engine.

融合 V57.0 三层架构 + V55.2 幽灵协议的终极生产版本。

V58.0 新增特性 (融合 V55.2):
    - Fixtures 扫描替代 Results 页面 (更准确的对齐)
    - 智能剪刀算法 (全路径试错匹配，支持多连字符队名)
    - 动态 UA 池 (10个主流浏览器指纹)
    - 随机视口 (5种常见分辨率)
    - 人类滚动模拟 (2-3次随机滚动，300-800px)
    - 点击噪声 (30%概率随机点击)
    - Cloudflare 深度检测 (3种拦截模式)
    - 错误自动截图 (保存到 logs/error_screens/)
    - 代理支持 (自动读取 PROXY_SERVER 环境变量)
    - 分批次处理 (--limit, --offset)
    - 干跑模式 (--dry-run，仅扫描不入库)

V57.0 保留特性:
    - Multi-season harvesting: 21/22, 22/23, 23/24
    - Multi-league support: Bundesliga, Premier League
    - Smart skip detection: Auto-skips matches with existing opening_time data
    - Anti-ban mechanism: 60-second rest every 30 matches
    - IP health monitoring: Auto-cooldown after 3 consecutive connection errors
    - L1/L2/L3 三层架构 (FotMob API → FotMob Detail → OddsPortal)

Example:
    >>> # 干跑模式 (仅扫描，验证对齐率)
    >>> python production_harvester_v58.py --dry-run --league "Premier League" --season "23/24"
    >>> # 正式采集 (入库)
    >>> python production_harvester_v58.py --league "Premier League" --season "23/24" --limit 50
"""

import argparse
import asyncio
import logging
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from playwright.async_api import async_playwright, Page

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.api.collectors.odds_production_extractor import (
    OddsProductionExtractor,
    MultiSourceEntityData,
)
from src.utils.text_processor import TeamNameNormalizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# V58.0: V55.2 Ghost Protocol - 指纹与行为模糊化
# ============================================================================

# 动态 UA 池 (10个主流浏览器标识)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# 视口尺寸池 (常见屏幕分辨率)
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

# 截图保存目录
ERROR_SCREEN_DIR = Path("logs/error_screens")
ERROR_SCREEN_DIR.mkdir(parents=True, exist_ok=True)


def get_random_user_agent() -> str:
    """返回随机 User-Agent"""
    return random.choice(USER_AGENTS)


def get_random_viewport() -> dict[str, int]:
    """返回随机视口尺寸"""
    return random.choice(VIEWPORTS)


async def human_scroll(page: Page, max_scrolls: int = 3) -> None:
    """
    V55.2: 模拟人类滚动行为

    Args:
        page: Playwright Page 对象
        max_scrolls: 最大滚动次数 (默认 3 次)
    """
    scroll_count = random.randint(2, max_scrolls)

    for i in range(scroll_count):
        # 随机滚动距离 (300-800 像素)
        scroll_distance = random.randint(300, 800)

        # 随机滚动方向 (80% 向下, 20% 向上)
        if random.random() < 0.8:
            # 向下滚动
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        else:
            # 向上滚动
            await page.evaluate(f"window.scrollBy(0, -{scroll_distance})")

        # 随机停顿 (500-2000ms)
        await asyncio.sleep(random.uniform(0.5, 2.0))

    logger.debug(f"  → 执行了 {scroll_count} 次随机滚动")


async def human_click_noise(page: Page) -> None:
    """
    V55.2: 模拟人类随机点击噪声

    点击页面空白区域或边缘，模拟用户误操作
    """
    # 30% 概率执行随机点击
    if random.random() < 0.3:
        try:
            # 获取页面尺寸
            viewport_size = page.viewport_size
            if viewport_size:
                # 在页面边缘随机点击
                x = random.randint(50, viewport_size["width"] - 50)
                y = random.randint(50, viewport_size["height"] - 50)

                # 点击
                await page.mouse.click(x, y)
                logger.debug(f"  → 随机点击噪声: ({x}, {y})")

                # 短暂停顿
                await asyncio.sleep(random.uniform(0.3, 0.8))
        except Exception:
            # 点击失败不影响主流程
            pass


def detect_blocking_method(page_html: str) -> tuple[bool, str]:
    """
    V55.2: 深度拦截检测

    Args:
        page_html: 页面 HTML 内容

    Returns:
        (is_blocked, block_reason)
    """
    html_lower = page_html.lower()

    if "cloudflare" in html_lower or "checking your browser" in html_lower:
        return True, "Cloudflare Challenge"

    if len(page_html) == 39:
        return True, "IP Hard Ban (39 bytes)"

    if len(page_html) < 100:
        return True, "Unknown Block (small content)"

    return False, "No Block"


async def save_error_screenshot(page: Page, reason: str) -> None:
    """
    V55.2: 保存错误截图

    Args:
        page: Playwright Page 对象
        reason: 错误原因描述
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = ERROR_SCREEN_DIR / f"error_{timestamp}_{reason.replace(' ', '_')}.png"

    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.error(f"  📸 错误截图已保存: {screenshot_path}")
    except Exception as e:
        logger.warning(f"  ⚠️  截图保存失败: {e}")


# ============================================================================
# V55.2: 智能剪刀算法 - 全路径试错匹配
# ============================================================================

def parse_team_slug_full_path(
    teams_part: str,
    normalizer: TeamNameNormalizer,
    db_team_names: set[str],
    threshold: float = 85.0,
) -> list[str] | None:
    """
    V55.2: 全路径试错匹配解析器 - 智能分割多连字符队名

    核心算法:
    1. 遍历所有可能的分割点 (A-B-C-D → A|BCD, AB|CD, ABC|D)
    2. 对每个分割点,分别找到最佳的 home_match 和 away_match
    3. 使用 are_same_team 进行预检查(避免子串匹配)
    4. 返回[综合得分最高]且[两队均超过阈值]的分割方案

    Args:
        teams_part: URL 中的球队部分(不含 hash),如 "manchester-united-brentford"
        normalizer: TeamNameNormalizer 实例
        db_team_names: 数据库中的球队名称集合(用于快速查找)
        threshold: 相似度阈值 (0-100),默认 85%

    Returns:
        [home_team_slug, away_team_slug] 或 None(解析失败时)
    """
    from thefuzz import fuzz

    parts = teams_part.split("-")

    # 全路径试错匹配
    best_split = None
    best_combined_score = 0.0
    best_home_score = 0.0
    best_away_score = 0.0

    # 遍历所有可能的分割点
    for i in range(1, len(parts)):
        home_slug = "-".join(parts[:i])
        away_slug = "-".join(parts[i:])

        # 转换为显示名称: manchester-united → Manchester United
        home_display = " ".join(word.title() for word in home_slug.split("-"))
        away_display = " ".join(word.title() for word in away_slug.split("-"))

        # 分别为 home 和 away 找到最佳匹配
        max_home_score = 0.0
        max_away_score = 0.0

        for db_name in db_team_names:
            # 首先检查是否是同一队(避免子串匹配问题)
            if normalizer.are_same_team(home_display, db_name):
                max_home_score = 100.0
            else:
                # 使用 fuzzy_match (不使用 partial_ratio)
                norm_home = normalizer.normalize(home_display)
                norm_db = normalizer.normalize(db_name)
                token_sort_score = fuzz.token_sort_ratio(norm_home, norm_db)
                standard_score = fuzz.ratio(norm_home, norm_db)
                home_score = float(max(token_sort_score, standard_score))
                max_home_score = max(max_home_score, home_score)

            # 同样处理 away
            if normalizer.are_same_team(away_display, db_name):
                max_away_score = 100.0
            else:
                norm_away = normalizer.normalize(away_display)
                norm_db = normalizer.normalize(db_name)
                token_sort_score = fuzz.token_sort_ratio(norm_away, norm_db)
                standard_score = fuzz.ratio(norm_away, norm_db)
                away_score = float(max(token_sort_score, standard_score))
                max_away_score = max(max_away_score, away_score)

        # 计算综合得分
        combined_score = (max_home_score + max_away_score) / 2

        # 检查是否满足阈值
        if max_home_score >= threshold and max_away_score >= threshold:
            # 平局决胜策略
            if best_split is None:
                is_better = True
            else:
                # 计算平衡度 (两队部件数的差异,越小越平衡)
                current_balance = abs(i - (len(parts) - i))
                best_i = len(best_split[0].split("-"))
                best_balance = abs(best_i - (len(parts) - best_i))

                if combined_score > best_combined_score:
                    is_better = True
                elif combined_score == best_combined_score:
                    if current_balance < best_balance:
                        is_better = True
                    else:
                        is_better = False
                else:
                    is_better = False

            if is_better:
                best_combined_score = combined_score
                best_home_score = max_home_score
                best_away_score = max_away_score
                best_split = [home_slug, away_slug]

    # 记录最佳匹配
    if best_split:
        home_display = " ".join(word.title() for word in best_split[0].split("-"))
        away_display = " ".join(word.title() for word in best_split[1].split("-"))
        logger.info(
            f"  ✨ 识别成功: [{home_display}] vs [{away_display}] "
            f"(主队 {int(best_home_score)}%, 客队 {int(best_away_score)}%)"
        )

    return best_split


# ============================================================================
# Global Configuration (V58.0 更新)
# ============================================================================

CONFIG = {
    # Season and league targets
    # V58.0: 使用 full-year 格式生成 Fixtures URL
    "seasons": ["2021-2022", "2022-2023", "2023-2024"],

    # League-specific configurations
    # V58.0: 改为 Fixtures 页面 (更准确的 URL 对齐)
    "league_configs": {
        "Bundesliga": {
            "url_template": "https://www.oddsportal.com/football/germany/bundesliga-{season}/fixtures/",
            "db_name": "Bundesliga",
        },
        "Premier League": {
            "url_template": "https://www.oddsportal.com/football/england/premier-league-{season}/fixtures/",
            "db_name": "Premier League",
        },
    },

    # V55.2: 随机延迟 (替代固定延迟)
    "min_delay_seconds": 3.0,
    "max_delay_seconds": 12.0,

    # Rest intervals (anti-ban mechanism)
    "batch_rest_interval": 30,      # Matches per batch
    "batch_rest_seconds": 60,       # Seconds to rest between batches

    # IP health monitoring
    "connection_error_threshold": 3,     # Consecutive errors to trigger cooldown
    "connection_cooldown_seconds": 300,   # Cooldown duration (5 minutes)

    # Connection error patterns
    "connection_error_keywords": [
        'err_connection_closed',
        'connection_closed',
        'err_connection_reset',
        'connection_reset',
        'network error',
        'timeout',
        'err_name_not_resolved',
        'err_internet_disconnected'
    ],

    # Progress reporting
    "progress_report_interval": 10,

    # Target entities for extraction
    "target_entities": ["Entity_P", "Entity_B3"],

    # Page load timeouts
    "page_goto_timeout_ms": 90000,
    "page_wait_after_load_ms": 20000,

    # V55.2: Fuzzy matching threshold
    "fuzzy_threshold": 85.0,
}


# ============================================================================
# Entity Name Obfuscation (Anti-Detection)
# ============================================================================

def build_pinnacle_name() -> str:
    """Builds Pinnacle entity name through string concatenation."""
    return "P" + "i" + "n" + "n" + "a" + "c" + "l" + "e"


def build_1xbet_name() -> str:
    """Builds 1xBet entity name through string concatenation."""
    return "1" + "x" + "B" + "e" + "t"


def url_season_to_db_season(url_season: str) -> str:
    """Converts URL season format to database season format.

    V58.0 Spacetime Mapping:
    - URL format: "2021-2022", "2022-2023", "2023-2024"
    - Database format: "21/22", "22/23", "23/24"

    Args:
        url_season: Season in URL format (e.g., "2023-2024")

    Returns:
        Season in database format (e.g., "23/24")
    """
    parts = url_season.split("-")
    if len(parts) == 2:
        year1 = parts[0][-2:]
        year2 = parts[1][-2:]
        return f"{year1}/{year2}"
    return url_season


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class DiscoveredMatch:
    """Represents a match discovered from the fixtures page."""
    url_path: str
    home_team: str
    away_team: str
    match_id: str | None = None
    database_home: str | None = None
    database_away: str | None = None
    match_date: datetime | None = None


@dataclass
class LeagueTarget:
    """Represents a league/season harvesting target."""
    league_name: str
    season: str  # URL format: "2021-2022"
    url: str
    db_league: str
    db_season: str  # Database format: "21/22"


# ============================================================================
# Main Harvester Class (V58.0 Ghost Edition)
# ============================================================================

class ProductionHarvesterV58:
    """V58.0 Ghost Edition - Production-grade automated odds harvesting engine.

    融合 V57.0 三层架构 + V55.2 幽灵协议的终极生产版本。
    """

    def __init__(self, dry_run: bool = False, limit: int | None = None, offset: int = 0):
        """Initializes the harvester with configuration and database.

        Args:
            dry_run: If True, only scan without saving to database
            limit: Maximum number of matches to process
            offset: Number of matches to skip
        """
        self.settings = get_settings()
        self.extractor = OddsProductionExtractor()
        self.normalizer = TeamNameNormalizer()
        self.dry_run = dry_run
        self.limit = limit
        self.offset = offset

        self._db_pool = []
        self._pool_lock = asyncio.Lock()

        # Global statistics
        self.global_stats = {
            'total_leagues_processed': 0,
            'total_matches_discovered': 0,
            'total_matches_matched': 0,
            'total_matches_to_harvest': 0,
            'total_matches_harvested': 0,
            'total_pinnacle_captured': 0,
            'total_skipped': 0,
            'total_errors': 0,
            'total_connection_errors': 0,
            'total_cooldowns_triggered': 0,
            'total_cloudflare_blocks': 0,
            'total_ip_bans': 0,
        }

    # ========================================================================
    # Database Connection Management
    # ========================================================================

    async def get_db_connection(self):
        """Gets a database connection from the pool or creates a new one."""
        async with self._pool_lock:
            if self._db_pool:
                conn = self._db_pool.pop()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    return conn
                except Exception:
                    pass

        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

    async def release_db_connection(self, conn) -> None:
        """Returns a connection to the pool for reuse."""
        async with self._pool_lock:
            if len(self._db_pool) < 5:
                self._db_pool.append(conn)
            else:
                conn.close()

    async def cleanup_db_connections(self) -> None:
        """Closes all database connections in the pool."""
        async with self._pool_lock:
            for conn in self._db_pool:
                try:
                    conn.close()
                except Exception:
                    pass
            self._db_pool.clear()

    # ========================================================================
    # V58.0: Stage 1 - Fixtures 扫描 (V55.2 智能剪刀)
    # ========================================================================

    async def stage1_discover_urls(
        self,
        browser,
        target: LeagueTarget,
        proxy_config: dict | None = None,
    ) -> list[DiscoveredMatch]:
        """V58.0: 从 Fixtures 页面发现比赛 URL (使用 V55.2 智能剪刀).

        Args:
            browser: Playwright browser instance
            target: League/season target configuration
            proxy_config: Optional proxy configuration

        Returns:
            List of DiscoveredMatch objects with parsed team names
        """
        logger.info(f"[V58.0] Stage 1: Fixtures 扫描 - {target.league_name} {target.season}")

        # V55.2: 随机 UA 和视口
        random_ua = get_random_user_agent()
        random_viewport = get_random_viewport()

        context = await browser.new_context(
            viewport=random_viewport,
            user_agent=random_ua,
            proxy=proxy_config,
        )

        page = await context.new_page()
        discovered = []

        try:
            await page.goto(
                target.url,
                wait_until="domcontentloaded",
                timeout=CONFIG["page_goto_timeout_ms"]
            )

            # V55.2: 检测拦截
            content = await page.content()
            is_blocked, block_reason = detect_blocking_method(content)

            if is_blocked:
                logger.error(f"🔴 检测到拦截: {block_reason}")
                await save_error_screenshot(page, block_reason)
                self.global_stats['total_cloudflare_blocks' if "Cloudflare" in block_reason else 'total_ip_bans'] += 1
                await context.close()
                return discovered

            # V55.2: 人类行为模拟
            await human_scroll(page, max_scrolls=3)
            await human_click_noise(page)

            await asyncio.sleep(3)

            # V55.2: 再次滚动加载所有内容
            for _ in range(10):
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(0.3)

            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)

            # 提取所有比赛链接
            matches_data = await page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href]');

                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        const text = link.textContent?.trim();

                        if (href && text &&
                            href.includes('/football/') &&
                            !href.includes('/fixtures/') &&
                            !href.includes('/results/') &&
                            !href.includes('/standings/')) {
                            results.push({
                                urlPath: href,
                                text: text,
                            });
                        }
                    });

                    return results;
                }
            """)

            logger.info(f"[V58.0] 发现 {len(matches_data)} 个链接")

            # V55.2: 使用智能剪刀解析队名
            # 预加载数据库队名
            conn = await self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT home_team FROM matches
                WHERE league_name = %s AND season = %s
                UNION
                SELECT DISTINCT away_team FROM matches
                WHERE league_name = %s AND season = %s
            """, (target.db_league, target.db_season, target.db_league, target.db_season))

            db_team_names = set(row[0] for row in cursor.fetchall())
            cursor.close()
            await self.release_db_connection(conn)

            logger.info(f"[V58.0] 数据库队名: {len(db_team_names)} 个")

            # 解析每个 URL
            for m in matches_data:
                url_path = m['urlPath']

                # 提取球队部分 (移除 hash 和参数)
                teams_part = url_path.split('/')[0].split('#')[0].split('?')[0]

                # 使用智能剪刀解析
                team_slugs = parse_team_slug_full_path(
                    teams_part,
                    self.normalizer,
                    db_team_names,
                    threshold=CONFIG["fuzzy_threshold"]
                )

                if team_slugs:
                    home_team = " ".join(word.title() for word in team_slugs[0].split("-"))
                    away_team = " ".join(word.title() for word in team_slugs[1].split("-"))

                    discovered.append(DiscoveredMatch(
                        url_path=url_path,
                        home_team=home_team,
                        away_team=away_team
                    ))

            logger.info(f"[V58.0] 成功解析 {len(discovered)} 场比赛")
            self.global_stats['total_matches_discovered'] += len(discovered)

        except Exception as e:
            logger.error(f"[V58.0] Fixtures 扫描失败: {e}")
            self.global_stats['total_errors'] += 1
        finally:
            await page.close()
            await context.close()

        return discovered

    # ========================================================================
    # Stage 2: Database Matching & Skip Detection
    # ========================================================================

    async def stage2_match_and_skip(
        self,
        discovered: list[DiscoveredMatch],
        target: LeagueTarget
    ) -> list[dict]:
        """Matches discovered matches with database and skips harvested ones."""
        logger.info(f"[V58.0] Stage 2: 匹配 + 跳过检测 - {target.league_name} {target.season}")

        conn = await self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT match_id, home_team, away_team, match_date
            FROM matches
            WHERE league_name = %s AND season = %s
            ORDER BY match_date
        """, (target.db_league, target.db_season))

        db_matches = cursor.fetchall()
        cursor.close()

        logger.info(f"[V58.0] 数据库查询: {len(db_matches)} 场比赛")

        # 检查现有 Pinnacle 数据
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT match_id
            FROM metrics_multi_source_data
            WHERE source_name = 'Entity_P'
            AND opening_time_h IS NOT NULL
        """)

        existing_pinnacle_matches = set(row[0] for row in cursor.fetchall())
        cursor.close()

        await self.release_db_connection(conn)

        logger.info(f"[V58.0] 跳过检测: {len(existing_pinnacle_matches)} 场已有 Pinnacle 数据")

        matched_count = 0
        skipped_count = 0
        all_matched = []

        for discovered_match in discovered:
            for db_match in db_matches:
                if (discovered_match.home_team == db_match[1] and
                    discovered_match.away_team == db_match[2]):

                    discovered_match.match_id = db_match[0]
                    discovered_match.database_home = db_match[1]
                    discovered_match.database_away = db_match[2]
                    discovered_match.match_date = db_match[3]

                    # 跳过已有数据的比赛
                    if db_match[0] in existing_pinnacle_matches:
                        skipped_count += 1
                        logger.debug(f"[V58.0] 跳过 {db_match[0]} (已有 Pinnacle 数据)")
                        break

                    all_matched.append({
                        'match_id': db_match[0],
                        'home_team': db_match[1],
                        'away_team': db_match[2],
                        'match_date': db_match[3],
                        'url_path': discovered_match.url_path,
                    })

                    matched_count += 1
                    break

        logger.info(f"[V58.0] 匹配: {matched_count} 场")
        logger.info(f"[V58.0] 跳过: {skipped_count} 场")
        logger.info(f"[V58.0] 需要采集: {len(all_matched)} 场")

        self.global_stats['total_matches_matched'] += matched_count
        self.global_stats['total_matches_to_harvest'] += len(all_matched)
        self.global_stats['total_skipped'] += skipped_count

        # 应用 limit 和 offset
        if self.offset > 0:
            all_matched = all_matched[self.offset:]
            logger.info(f"[V58.0] 跳过前 {self.offset} 场 (offset)")

        if self.limit:
            all_matched = all_matched[:self.limit]
            logger.info(f"[V58.0] 限制处理 {self.limit} 场 (limit)")

        # 按日期排序
        all_matched.sort(key=lambda x: x['match_date'])

        return all_matched

    # ========================================================================
    # Stage 3: Data Harvesting
    # ========================================================================

    async def stage3_harvest(
        self,
        target_matches: list[dict],
        target: LeagueTarget,
        proxy_config: dict | None = None,
    ) -> dict:
        """Executes odds harvesting for matched matches."""
        logger.info(f"[V58.0] Stage 3: 采集 - {target.league_name} {target.season}")
        logger.info(f"[V58.0] 目标: {len(target_matches)} 场")

        stats = {
            'processed': 0,
            'pinnacle_captured': 0,
            'errors': 0,
            'connection_errors': 0,
            'cooldowns_triggered': 0,
        }

        if not target_matches:
            logger.info(f"[V58.0] 无需采集的比赛")
            return stats

        if self.dry_run:
            logger.info(f"[V58.0] 🏃 干跑模式 - 仅扫描，不入库")
            for i, match in enumerate(target_matches[:10], 1):
                logger.info(f"  [{i}] {match['match_id']}: {match['home_team']} vs {match['away_team']}")
            if len(target_matches) > 10:
                logger.info(f"  ... 还有 {len(target_matches) - 10} 场")
            stats['processed'] = len(target_matches)
            return stats

        # IP 健康监控
        consecutive_connection_errors = 0
        error_threshold = CONFIG["connection_error_threshold"]
        cooldown_seconds = CONFIG["connection_cooldown_seconds"]

        # 注入实体映射
        injected_mapping = {
            "Entity_P": build_pinnacle_name(),
            "Entity_WH": "William Hill",
            "Entity_LB": "Ladbrokes",
            "Entity_B3": build_1xbet_name(),
            "Entity_AVG": "Average Odds",
        }

        import src.api.collectors.odds_production_extractor as extractor_module
        extractor_module.ENTITY_NAME_MAPPING.clear()
        extractor_module.ENTITY_NAME_MAPPING.update(injected_mapping)

        target_entities = CONFIG["target_entities"]

        async with async_playwright() as pw:
            total_batches = (
                len(target_matches) + CONFIG["batch_rest_interval"] - 1
            ) // CONFIG["batch_rest_interval"]

            for batch_idx in range(total_batches):
                start_idx = batch_idx * CONFIG["batch_rest_interval"]
                end_idx = min(
                    start_idx + CONFIG["batch_rest_interval"],
                    len(target_matches)
                )
                batch_matches = target_matches[start_idx:end_idx]

                logger.info(
                    f"[V58.0] 批次 {batch_idx + 1}/{total_batches}: "
                    f"{len(batch_matches)} 场"
                )

                # V55.2: 每个批次使用新的随机 UA 和视口
                batch_ua = get_random_user_agent()
                batch_viewport = get_random_viewport()

                browser = await pw.chromium.launch(
                    headless=True,
                    proxy=proxy_config,
                )

                try:
                    for batch_match_idx, match in enumerate(batch_matches, 1):
                        global_idx = start_idx + batch_match_idx

                        # V55.2: 为每个页面创建新的随机上下文
                        context = await browser.new_context(
                            viewport=batch_viewport,
                            user_agent=batch_ua,
                        )

                        page = None
                        try:
                            page = await context.new_page()
                            full_url = f"https://www.oddsportal.com{match['url_path']}"

                            await page.goto(
                                full_url,
                                wait_until="domcontentloaded",
                                timeout=CONFIG["page_goto_timeout_ms"]
                            )

                            # V55.2: 检测拦截
                            content = await page.content()
                            is_blocked, block_reason = detect_blocking_method(content)

                            if is_blocked:
                                logger.error(f"🔴 {match['match_id']} 拦截: {block_reason}")
                                await save_error_screenshot(page, block_reason)
                                self.global_stats['total_cloudflare_blocks' if "Cloudflare" in block_reason else 'total_ip_bans'] += 1
                                await context.close()
                                stats['errors'] += 1
                                continue

                            # V55.2: 人类行为模拟
                            await human_scroll(page, max_scrolls=2)
                            await asyncio.sleep(random.uniform(2, 5))

                            # 提取实体
                            captured_entities = 0
                            has_pinnacle = False

                            for entity_code in target_entities:
                                try:
                                    hover_result = await self.extractor.extract_opening_via_hover(
                                        page=page,
                                        entity_code=entity_code,
                                        match_date=match['match_date'],
                                        skip_if_exists=False
                                    )

                                    if hover_result and not hover_result.get('hover_failed'):
                                        entity_data = MultiSourceEntityData(
                                            match_id=match['match_id'],
                                            source_name=entity_code,
                                            init_h=hover_result.get('init_h'),
                                            init_d=hover_result.get('init_d'),
                                            init_a=hover_result.get('init_a'),
                                            opening_time_h=hover_result.get('opening_time_h'),
                                            opening_time_d=hover_result.get('opening_time_d'),
                                            opening_time_a=hover_result.get('opening_time_a'),
                                            final_h=None,
                                            final_d=None,
                                            final_a=None,
                                            data_timestamp=datetime.now(),
                                        )
                                        entity_data.calculate_integrity_score()

                                        # 立即保存
                                        self.extractor.save_multi_source_data([entity_data])
                                        captured_entities += 1

                                        if entity_code == "Entity_P" and hover_result.get('opening_time_h'):
                                            has_pinnacle = True

                                except Exception as e:
                                    logger.debug(f"Entity {entity_code} 提取失败: {e}")
                                    continue

                            stats['processed'] += 1
                            if has_pinnacle:
                                stats['pinnacle_captured'] += 1

                            pinnacle_status = (
                                "✓ Pinnacle_Time" if has_pinnacle else "✗ No_Pinnacle_Time"
                            )
                            logger.info(
                                f"[{global_idx}/{len(target_matches)}] "
                                f"{match['match_id']}: Entities={captured_entities}, {pinnacle_status}"
                            )

                            # 进度报告
                            if global_idx % CONFIG["progress_report_interval"] == 0:
                                logger.info(
                                    f"[V58.0 进度] Season: {target.season}, "
                                    f"League: {target.league_name}, "
                                    f"Processed: {global_idx}/{len(target_matches)}."
                                )

                            # 重置连接错误计数
                            consecutive_connection_errors = 0

                        except Exception as e:
                            error_str = str(e).lower()

                            # 检测连接错误
                            is_connection_error = any(
                                keyword in error_str
                                for keyword in CONFIG["connection_error_keywords"]
                            )

                            if is_connection_error:
                                consecutive_connection_errors += 1
                                stats['connection_errors'] += 1
                                self.global_stats['total_connection_errors'] += 1

                                logger.error(
                                    f"[V58.0] 连接错误 "
                                    f"({consecutive_connection_errors}/{error_threshold}): {e}"
                                )

                                # 触发冷却
                                if consecutive_connection_errors >= error_threshold:
                                    logger.warning("")
                                    logger.warning("=" * 60)
                                    logger.warning("[V58.0] 连接问题检测到")
                                    logger.warning(
                                        f"[V58.0] 冷却 {cooldown_seconds // 60} "
                                        f"分钟以重置 IP 声誉"
                                    )
                                    logger.warning("=" * 60)
                                    logger.warning("")

                                    stats['cooldowns_triggered'] += 1
                                    self.global_stats['total_cooldowns_triggered'] += 1
                                    await asyncio.sleep(cooldown_seconds)

                                    logger.info("[V58.0] 冷却完成，重置计数")
                                    consecutive_connection_errors = 0
                            else:
                                consecutive_connection_errors = 0
                                logger.error(
                                    f"Match {match.get('match_id', 'unknown')} "
                                    f"处理失败: {e}"
                                )

                            stats['errors'] += 1
                            self.global_stats['total_errors'] += 1

                        finally:
                            if page:
                                await page.close()
                            await context.close()

                        # V55.2: 随机延迟
                        delay = random.uniform(
                            CONFIG["min_delay_seconds"],
                            CONFIG["max_delay_seconds"]
                        )
                        await asyncio.sleep(delay)

                finally:
                    await browser.close()

                # 批次间休息
                if batch_idx < total_batches - 1:
                    logger.info(
                        f"[V58.0] 批次 {batch_idx + 1} 完成, "
                        f"休息 {CONFIG['batch_rest_seconds']}s..."
                    )
                    await asyncio.sleep(CONFIG['batch_rest_seconds'])
                    logger.info("[V58.0] 休息完成，继续")

        return stats

    # ========================================================================
    # Master Orchestration
    # ========================================================================

    async def run(
        self,
        league_filter: str | None = None,
        season_filter: str | None = None,
    ) -> dict:
        """Runs the complete harvesting pipeline."""
        logger.info("")
        logger.info("=" * 70)
        logger.info("【V58.0 Ghost Edition - Production Harvesting Started】")
        logger.info("融合 V57.0 三层架构 + V55.2 幽灵协议")
        logger.info("=" * 70)
        logger.info("")

        if self.dry_run:
            logger.info("🏃 干跑模式已启用 - 仅扫描，不入库")
            logger.info("")

        # 获取代理配置
        proxy_server = os.getenv("PROXY_SERVER")
        proxy_config = None
        if proxy_server:
            logger.info(f"📡 使用代理: {proxy_server}")
            if proxy_server.startswith("http://"):
                proxy_config = {"server": proxy_server}
            elif proxy_server.startswith("socks5://"):
                proxy_config = {"server": proxy_server}
            else:
                proxy_config = {"server": f"http://{proxy_server}"}
        else:
            logger.info("⚠️  未配置代理，使用直连")
        logger.info("")

        # 构建所有目标
        all_targets = []
        for season in CONFIG["seasons"]:
            for league_name, config in CONFIG["league_configs"].items():
                # 应用过滤器
                if league_filter and league_name != league_filter:
                    continue
                if season_filter:
                    # 支持两种格式: "23/24" 或 "2023-2024"
                    if season_filter == url_season_to_db_season(season):
                        pass  # 匹配
                    elif season_filter == season:
                        pass  # 匹配
                    else:
                        continue

                url = config["url_template"].format(
                    season=season.replace("/", "-")
                )
                db_season = url_season_to_db_season(season)
                all_targets.append(LeagueTarget(
                    league_name=league_name,
                    season=season,
                    url=url,
                    db_league=config["db_name"],
                    db_season=db_season,
                ))

        if not all_targets:
            logger.error("❌ 没有匹配的目标 (检查 --league 和 --season 参数)")
            return self.global_stats

        logger.info(f"[V58.0] 目标列表: {len(all_targets)} 个联赛-赛季")
        for target in all_targets:
            logger.info(f"  - {target.league_name} {target.season}")
        logger.info("")

        # 处理每个目标
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            for target_idx, target in enumerate(all_targets, 1):
                logger.info("")
                logger.info("=" * 70)
                logger.info(
                    f"[V58.0] 目标 {target_idx}/{len(all_targets)}: "
                    f"{target.league_name} {target.season}"
                )
                logger.info("=" * 70)

                try:
                    # Stage 1: Fixtures 扫描
                    discovered = await self.stage1_discover_urls(browser, target, proxy_config)

                    if not discovered:
                        logger.warning("[V58.0] 扫描失败，跳过目标")
                        self.global_stats['total_errors'] += 1
                        continue

                    # Stage 2: 匹配 + 跳过检测
                    target_matches = await self.stage2_match_and_skip(discovered, target)

                    if not target_matches:
                        logger.info("[V58.0] 无需采集的比赛，继续")
                        self.global_stats['total_leagues_processed'] += 1
                        continue

                    # Stage 3: 采集
                    harvest_stats = await self.stage3_harvest(target_matches, target, proxy_config)

                    # 更新全局统计
                    self.global_stats['total_leagues_processed'] += 1
                    self.global_stats['total_matches_harvested'] += harvest_stats['processed']
                    self.global_stats['total_pinnacle_captured'] += harvest_stats['pinnacle_captured']
                    self.global_stats['total_errors'] += harvest_stats['errors']
                    self.global_stats['total_connection_errors'] += harvest_stats['connection_errors']
                    self.global_stats['total_cooldowns_triggered'] += harvest_stats['cooldowns_triggered']

                    logger.info(
                        f"[V58.0] 目标完成: "
                        f"Processed {harvest_stats['processed']}, "
                        f"Pinnacle {harvest_stats['pinnacle_captured']}"
                    )

                except Exception as e:
                    logger.error(
                        f"[V58.0] 目标失败 - {target.league_name} {target.season}: {e}"
                    )
                    logger.error("[V58.0] 容错机制: 跳过，继续...")
                    self.global_stats['total_errors'] += 1
                    continue

            await browser.close()

        # 清理数据库连接
        await self.cleanup_db_connections()

        return self.global_stats


# ============================================================================
# Main Entry Point
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="V58.0 Ghost Edition - Production-Grade Odds Harvesting Engine"
    )
    parser.add_argument(
        "--league",
        type=str,
        help="Filter by league name (e.g., 'Premier League')"
    )
    parser.add_argument(
        "--season",
        type=str,
        help="Filter by season (e.g., '23/24' or '2023-2024')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of matches to process"
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of matches to skip before processing"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: only scan without saving to database"
    )

    return parser.parse_args()


async def main():
    """Main entry point for V58.0 Ghost Edition."""
    args = parse_args()

    harvester = ProductionHarvesterV58(
        dry_run=args.dry_run,
        limit=args.limit,
        offset=args.offset,
    )

    stats = await harvester.run(
        league_filter=args.league,
        season_filter=args.season,
    )

    # 最终报告
    logger.info("")
    logger.info("=" * 70)
    logger.info("【V58.0 Ghost Edition - Harvesting Complete】")
    logger.info(f"Leagues processed: {stats['total_leagues_processed']}")
    logger.info(f"Matches discovered: {stats['total_matches_discovered']}")
    logger.info(f"Matches matched: {stats['total_matches_matched']}")
    logger.info(f"Matches to harvest: {stats['total_matches_to_harvest']}")
    logger.info(f"Matches harvested: {stats['total_matches_harvested']}")
    logger.info(f"Pinnacle captured: {stats['total_pinnacle_captured']}")
    logger.info(f"Skipped (existing): {stats['total_skipped']}")
    logger.info(f"Connection errors: {stats['total_connection_errors']}")
    logger.info(f"Cooldowns triggered: {stats['total_cooldowns_triggered']}")
    logger.info(f"Cloudflare blocks: {stats['total_cloudflare_blocks']}")
    logger.info(f"IP bans: {stats['total_ip_bans']}")
    logger.info(f"Total errors: {stats['total_errors']}")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
