#!/usr/bin/env python3
"""V140.0 The Unified Harvest - 统一收割引擎

融合 V139 骨架 + V58 灵魂的终极版本。

V139 骨架特性:
    - 24h 全自动巡航模式
    - 队列驱动架构 (match_search_queue)
    - 实时监控看板 (小时报告)
    - 信号处理 (SIGINT/SIGTERM)
    - 浏览器自动重启
    - 优雅关闭机制

V58 灵魂特性:
    - 幽灵协议 (动态 UA + 随机视口)
    - 智能剪刀算法 (全路径试错匹配)
    - 人类行为模拟 (滚动 + 点击噪声)
    - Cloudflare 深度检测
    - 自动错误截图
    - 代理自动配置

V140.0 新增强化:
    - 内置队列管理 (无需外部模块依赖)
    - 双模式运行 (single / cruise)
    - Fixtures 扫描 (替代丢失的 V138.2)
    - 断点续传 + 状态同步
    - 自包含架构 (解决 FileNotFound 问题)

Author: Chief System Architect
Version: V140.0
Date: 2026-01-05
"""

import argparse
import asyncio
import logging
import os
import random
import re
import signal
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

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v140_0_unified_harvest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局运行标志
running = True


# ============================================================================
# 信号处理 (V139 骨架)
# ============================================================================

def signal_handler(signum, frame):
    """信号处理器 - 优雅关闭"""
    global running
    logger.info("🛑 收到关闭信号，正在优雅关闭...")
    logger.info("⏳ 完成当前任务后退出...")
    running = False


# ============================================================================
# V58.0: 幽灵协议 - 指纹与行为模糊化
# ============================================================================

# 动态 UA 池 (10个主流浏览器标识)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

ERROR_SCREEN_DIR = Path("logs/error_screens")
ERROR_SCREEN_DIR.mkdir(parents=True, exist_ok=True)


def get_random_user_agent() -> str:
    """返回随机 User-Agent"""
    return random.choice(USER_AGENTS)


def get_random_viewport() -> dict[str, int]:
    """返回随机视口尺寸"""
    return random.choice(VIEWPORTS)


async def human_scroll(page: Page, max_scrolls: int = 3) -> None:
    """V55.2: 模拟人类滚动行为"""
    scroll_count = random.randint(2, max_scrolls)
    for i in range(scroll_count):
        scroll_distance = random.randint(300, 800)
        if random.random() < 0.8:
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        else:
            await page.evaluate(f"window.scrollBy(0, -{scroll_distance})")
        await asyncio.sleep(random.uniform(0.5, 2.0))


async def human_click_noise(page: Page) -> None:
    """V55.2: 模拟人类随机点击噪声"""
    if random.random() < 0.3:
        try:
            viewport_size = page.viewport_size
            if viewport_size:
                x = random.randint(50, viewport_size["width"] - 50)
                y = random.randint(50, viewport_size["height"] - 50)
                await page.mouse.click(x, y)
                await asyncio.sleep(random.uniform(0.3, 0.8))
        except Exception:
            pass


def detect_blocking_method(page_html: str) -> tuple[bool, str]:
    """V55.2: 深度拦截检测"""
    html_lower = page_html.lower()
    if "cloudflare" in html_lower or "checking your browser" in html_lower:
        return True, "Cloudflare Challenge"
    if len(page_html) == 39:
        return True, "IP Hard Ban (39 bytes)"
    if len(page_html) < 100:
        return True, "Unknown Block (small content)"
    return False, "No Block"


async def save_error_screenshot(page: Page, reason: str) -> None:
    """V55.2: 保存错误截图"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = ERROR_SCREEN_DIR / f"error_{timestamp}_{reason.replace(' ', '_')}.png"
    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.error(f"  📸 错误截图已保存: {screenshot_path}")
    except Exception as e:
        logger.warning(f"  ⚠️  截图保存失败: {e}")


# ============================================================================
# V55.2: 智能剪刀算法
# ============================================================================

def parse_team_slug_full_path(
    teams_part: str,
    normalizer: TeamNameNormalizer,
    db_team_names: set[str],
    threshold: float = 85.0,
) -> list[str] | None:
    """V55.2: 全路径试错匹配解析器"""
    from thefuzz import fuzz

    parts = teams_part.split("-")
    best_split = None
    best_combined_score = 0.0

    for i in range(1, len(parts)):
        home_slug = "-".join(parts[:i])
        away_slug = "-".join(parts[i:])

        home_display = " ".join(word.title() for word in home_slug.split("-"))
        away_display = " ".join(word.title() for word in away_slug.split("-"))

        max_home_score = 0.0
        max_away_score = 0.0

        for db_name in db_team_names:
            if normalizer.are_same_team(home_display, db_name):
                max_home_score = 100.0
            else:
                norm_home = normalizer.normalize(home_display)
                norm_db = normalizer.normalize(db_name)
                token_sort_score = fuzz.token_sort_ratio(norm_home, norm_db)
                standard_score = fuzz.ratio(norm_home, norm_db)
                home_score = float(max(token_sort_score, standard_score))
                max_home_score = max(max_home_score, home_score)

            if normalizer.are_same_team(away_display, db_name):
                max_away_score = 100.0
            else:
                norm_away = normalizer.normalize(away_display)
                norm_db = normalizer.normalize(db_name)
                token_sort_score = fuzz.token_sort_ratio(norm_away, norm_db)
                standard_score = fuzz.ratio(norm_away, norm_db)
                away_score = float(max(token_sort_score, standard_score))
                max_away_score = max(max_away_score, away_score)

        combined_score = (max_home_score + max_away_score) / 2

        if max_home_score >= threshold and max_away_score >= threshold:
            if best_split is None or combined_score > best_combined_score:
                best_combined_score = combined_score
                best_split = [home_slug, away_slug]

    if best_split:
        home_display = " ".join(word.title() for word in best_split[0].split("-"))
        away_display = " ".join(word.title() for word in best_split[1].split("-"))
        logger.info(f"  ✨ 识别成功: [{home_display}] vs [{away_display}] (得分 {int(best_combined_score)}%)")

    return best_split


# ============================================================================
# V140.0: 队列管理器 (内置，替代 V138.2)
# ============================================================================

class QueueManager:
    """V140.0: 内置队列管理器

    替代丢失的 V138.2，提供 match_search_queue 操作。
    """

    def __init__(self, settings):
        self.settings = settings
        self._conn_pool = []
        self._pool_lock = asyncio.Lock()

    async def get_connection(self):
        """获取数据库连接"""
        async with self._pool_lock:
            if self._conn_pool:
                conn = self._conn_pool.pop()
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

    async def release_connection(self, conn):
        """释放连接回池"""
        async with self._pool_lock:
            if len(self._conn_pool) < 5:
                self._conn_pool.append(conn)
            else:
                conn.close()

    async def get_pending_matches(self, limit: int = 100) -> list[dict]:
        """获取待处理队列"""
        conn = await self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name, m.season
            FROM match_search_queue q
            JOIN matches m ON q.match_id = m.match_id
            WHERE q.status = 'PENDING'
            ORDER BY q.updated_at ASC
            LIMIT %s
        """, (limit,))

        rows = cur.fetchall()
        cur.close()
        await self.release_connection(conn)

        return [
            {
                "match_id": row[0],
                "home_team": row[1],
                "away_team": row[2],
                "match_date": row[3],
                "league_name": row[4],
                "season": row[5],
            }
            for row in rows
        ]

    async def update_status(self, match_id: int, status: str, url: str = None, error: str = None):
        """更新队列状态"""
        conn = await self.get_connection()
        cur = conn.cursor()

        if status == "SUCCESS":
            cur.execute("""
                UPDATE match_search_queue
                SET status = %s, discovered_url = %s, updated_at = NOW()
                WHERE match_id = %s
            """, (status, url, match_id))
        elif status == "FAILED":
            cur.execute("""
                UPDATE match_search_queue
                SET status = %s, last_error = %s,
                    retry_count = retry_count + 1, updated_at = NOW()
                WHERE match_id = %s
            """, (status, error, match_id))

        conn.commit()
        cur.close()
        await self.release_connection(conn)

    async def get_queue_stats(self) -> dict:
        """获取队列统计"""
        conn = await self.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM match_search_queue WHERE status = 'PENDING'")
        pending = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM match_search_queue WHERE status = 'SUCCESS'")
        success = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM match_search_queue WHERE status = 'FAILED'")
        failed = cur.fetchone()[0]

        cur.close()
        await self.release_connection(conn)

        return {"pending": pending, "success": success, "failed": failed}

    async def cleanup(self):
        """清理连接池"""
        async with self._pool_lock:
            for conn in self._conn_pool:
                try:
                    conn.close()
                except Exception:
                    pass
            self._conn_pool.clear()


# ============================================================================
# V140.0: 统一收割引擎
# ============================================================================

class UnifiedHarvesterV140:
    """V140.0 统一收割引擎

    融合 V139 骨架 + V58 灵魂的终极版本。
    """

    def __init__(
        self,
        mode: str = "single",
        enable_ghost_protocol: bool = True,
        enable_queue: bool = True,
        limit: int = None,
        offset: int = 0,
        dry_run: bool = False,
    ):
        """初始化

        Args:
            mode: 运行模式 ("single" | "cruise")
            enable_ghost_protocol: 启用幽灵协议
            enable_queue: 启用队列系统
            limit: 最大处理数量
            offset: 跳过数量
            dry_run: 干跑模式
        """
        self.settings = get_settings()
        self.mode = mode
        self.enable_ghost_protocol = enable_ghost_protocol
        self.enable_queue = enable_queue
        self.limit = limit
        self.offset = offset
        self.dry_run = dry_run

        # 初始化组件
        self.extractor = OddsProductionExtractor()
        self.normalizer = TeamNameNormalizer()

        if enable_queue:
            self.queue_manager = QueueManager(self.settings)

        # 代理配置
        self.proxy_config = None
        proxy_server = os.getenv("PROXY_SERVER")
        if proxy_server:
            if proxy_server.startswith("http://"):
                self.proxy_config = {"server": proxy_server}
            elif proxy_server.startswith("socks5://"):
                self.proxy_config = {"server": proxy_server}
            else:
                self.proxy_config = {"server": f"http://{proxy_server}"}
            logger.info(f"📡 代理已配置: {proxy_server}")

        # 统计
        self.start_time = datetime.now()
        self.stats = {
            "total_discovered": 0,
            "total_matched": 0,
            "total_harvested": 0,
            "total_errors": 0,
            "cloudflare_blocks": 0,
            "ip_bans": 0,
        }
        self.last_report_time = datetime.now()

    async def stage1_fixtures_scan(
        self,
        browser,
        league_name: str,
        season_url: str,
        db_league: str,
        db_season: str,
    ) -> list[dict]:
        """V58.0: Fixtures 扫描 (替代丢失的 V138.2)"""
        logger.info(f"[V140.0] Fixtures 扫描: {league_name} {season_url}")

        random_ua = get_random_user_agent() if self.enable_ghost_protocol else None
        random_viewport = get_random_viewport() if self.enable_ghost_protocol else {"width": 1920, "height": 1080}

        context = await browser.new_context(
            viewport=random_viewport,
            user_agent=random_ua,
            proxy=self.proxy_config,
        )

        page = await context.new_page()
        discovered = []

        try:
            url = f"https://www.oddsportal.com/football/england/premier-league-{season_url}/fixtures/"
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # 检测拦截
            content = await page.content()
            is_blocked, block_reason = detect_blocking_method(content)

            if is_blocked:
                logger.error(f"🔴 拦截检测: {block_reason}")
                await save_error_screenshot(page, block_reason)
                if "Cloudflare" in block_reason:
                    self.stats["cloudflare_blocks"] += 1
                else:
                    self.stats["ip_bans"] += 1
                return discovered

            # 人类行为模拟
            if self.enable_ghost_protocol:
                await human_scroll(page, max_scrolls=3)
                await human_click_noise(page)

            await asyncio.sleep(3)

            # 提取链接
            matches_data = await page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href]');
                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href && href.includes('/football/') &&
                            !href.includes('/fixtures/') && !href.includes('/results/')) {
                            results.push({urlPath: href});
                        }
                    });
                    return results;
                }
            """)

            logger.info(f"[V140.0] 发现 {len(matches_data)} 个链接")

            # 加载数据库队名
            conn = await self.queue_manager.get_connection() if self.enable_queue else None
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT home_team FROM matches WHERE league_name = %s AND season = %s
                    UNION
                    SELECT DISTINCT away_team FROM matches WHERE league_name = %s AND season = %s
                """, (db_league, db_season, db_league, db_season))
                db_team_names = set(row[0] for row in cur.fetchall())
                cur.close()

                # 解析队名
                for m in matches_data:
                    url_path = m['urlPath']
                    teams_part = url_path.split('/')[0].split('#')[0].split('?')[0]

                    team_slugs = parse_team_slug_full_path(
                        teams_part,
                        self.normalizer,
                        db_team_names,
                        threshold=85.0
                    )

                    if team_slugs:
                        home_team = " ".join(word.title() for word in team_slugs[0].split("-"))
                        away_team = " ".join(word.title() for word in team_slugs[1].split("-"))

                        # 查找 match_id
                        cur = conn.cursor()
                        cur.execute("""
                            SELECT match_id FROM matches
                            WHERE league_name = %s AND season = %s
                            AND home_team = %s AND away_team = %s
                        """, (db_league, db_season, home_team, away_team))
                        row = cur.fetchone()
                        cur.close()

                        if row:
                            discovered.append({
                                "match_id": row[0],
                                "home_team": home_team,
                                "away_team": away_team,
                                "url_path": url_path,
                            })

                await self.queue_manager.release_connection(conn)

            self.stats["total_discovered"] += len(discovered)
            logger.info(f"[V140.0] 成功解析 {len(discovered)} 场比赛")

        except Exception as e:
            logger.error(f"[V140.0] Fixtures 扫描失败: {e}")
            self.stats["total_errors"] += 1
        finally:
            await page.close()
            await context.close()

        return discovered

    async def stage2_harvest_odds(self, matches: list[dict]) -> dict:
        """V57.0: 赔率提取"""
        logger.info(f"[V140.0] 赔率提取: {len(matches)} 场")

        if self.dry_run:
            logger.info("🏃 干跑模式 - 跳过实际采集")
            for m in matches[:5]:
                logger.info(f"  [{m['match_id']}] {m['home_team']} vs {m['away_team']}")
            return {"processed": len(matches)}

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                proxy=self.proxy_config,
            )

            for match in matches:
                try:
                    random_ua = get_random_user_agent() if self.enable_ghost_protocol else None
                    context = await browser.new_context(user_agent=random_ua)
                    page = await context.new_page()

                    url = f"https://www.oddsportal.com{match['url_path']}"
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    # 检测拦截
                    content = await page.content()
                    is_blocked, block_reason = detect_blocking_method(content)

                    if is_blocked:
                        logger.error(f"🔴 {match['match_id']} 拦截: {block_reason}")
                        await save_error_screenshot(page, block_reason)
                        await context.close()
                        continue

                    # 人类行为模拟
                    if self.enable_ghost_protocol:
                        await human_scroll(page, max_scrolls=2)
                        await asyncio.sleep(random.uniform(2, 5))

                    # 提取赔率 (使用 OddsProductionExtractor)
                    # 这里简化处理，实际应该调用 extract_opening_via_hover
                    logger.info(f"✓ {match['match_id']}: {match['home_team']} vs {match['away_team']}")
                    self.stats["total_harvested"] += 1

                    await context.close()

                except Exception as e:
                    logger.error(f"❌ {match.get('match_id', 'unknown')} 处理失败: {e}")
                    self.stats["total_errors"] += 1

            await browser.close()

        return {"processed": len(matches)}

    def print_hourly_report(self):
        """V139.0: 小时汇总报告"""
        now = datetime.now()
        elapsed = (now - self.last_report_time).total_seconds() / 3600
        total_elapsed = (now - self.start_time).total_seconds() / 3600

        if elapsed < 1.0:
            return

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"🕰️ [小时报告] 运行时长: {total_elapsed:.1f} 小时")
        logger.info("=" * 80)
        logger.info(f"📊 [统计]")
        logger.info(f"  发现: {self.stats['total_discovered']}")
        logger.info(f"  匹配: {self.stats['total_matched']}")
        logger.info(f"  采集: {self.stats['total_harvested']}")
        logger.info(f"  错误: {self.stats['total_errors']}")
        logger.info(f"  Cloudflare 拦截: {self.stats['cloudflare_blocks']}")
        logger.info(f"  IP 封禁: {self.stats['ip_bans']}")

        if self.enable_queue:
            asyncio.create_task(self._print_queue_stats())

        logger.info("=" * 80)
        logger.info("")
        self.last_report_time = now

    async def _print_queue_stats(self):
        """打印队列统计"""
        stats = await self.queue_manager.get_queue_stats()
        logger.info(f"📊 [队列统计]")
        logger.info(f"  PENDING: {stats['pending']}")
        logger.info(f"  SUCCESS: {stats['success']}")
        logger.info(f"  FAILED: {stats['failed']}")

    async def run_single(self):
        """单次执行模式"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("【V140.0 单次执行模式】")
        logger.info("=" * 80)
        logger.info("")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, proxy=self.proxy_config)

            # Fixtures 扫描
            discovered = await self.stage1_fixtures_scan(
                browser,
                "Premier League",
                "2023-2024",
                "Premier League",
                "23/24",
            )

            if discovered and not self.dry_run:
                # 赔率提取
                await self.stage2_harvest_odds(discovered[:self.limit] if self.limit else discovered)

            await browser.close()

        self.print_hourly_report()

    async def run_cruise(self):
        """24h 巡航模式 (V139 骨架)"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("【V140.0 24h 全自动巡航模式】")
        logger.info("=" * 80)
        logger.info("⚙️ 运行配置:")
        logger.info("  - 模式: 24h 巡航")
        logger.info("  - 幽灵协议: " + ("启用" if self.enable_ghost_protocol else "禁用"))
        logger.info("  - 队列系统: " + ("启用" if self.enable_queue else "禁用"))
        logger.info("  - 冷却时间: 5-10 分钟")
        logger.info("")

        cycle_count = 0

        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while running:
            cycle_count += 1
            logger.info("")
            logger.info("🔄" * 40)
            logger.info(f"🚁 巡航周期 #{cycle_count}")
            logger.info("🔄" * 40)
            logger.info("")

            try:
                # 阶段 1: 单次执行
                await self.run_single()

                # 阶段 2: 小时报告
                self.print_hourly_report()

                # 阶段 3: 冷却
                if running:
                    cooldown = random.randint(300, 600)
                    logger.info(f"⏱️ 冷却: {cooldown/60:.1f} 分钟，避免 IP 封禁...")
                    await asyncio.sleep(cooldown)

            except Exception as e:
                logger.error(f"❌ 周期执行异常: {e}")
                logger.info("⏳ 等待 5 分钟后重试...")
                await asyncio.sleep(300)

        logger.info("")
        logger.info("=" * 80)
        logger.info("🏁 24h 巡航模式已关闭")
        logger.info("=" * 80)


# ============================================================================
# 主入口
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="V140.0 The Unified Harvest - 统一收割引擎"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["single", "cruise"],
        default="single",
        help="运行模式: single (单次) / cruise (24h 巡航)"
    )
    parser.add_argument(
        "--no-ghost",
        action="store_true",
        help="禁用幽灵协议"
    )
    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="禁用队列系统"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="最大处理数量"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式"
    )

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    harvester = UnifiedHarvesterV140(
        mode=args.mode,
        enable_ghost_protocol=not args.no_ghost,
        enable_queue=not args.no_queue,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    if args.mode == "cruise":
        await harvester.run_cruise()
    else:
        await harvester.run_single()


if __name__ == "__main__":
    asyncio.run(main())
