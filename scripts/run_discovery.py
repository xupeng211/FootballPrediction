#!/usr/bin/env python3
"""V120.0 Phase 3: Queue-Based Discovery Engine with Checkpoint/Resume.

Production-grade URL discovery system with:
- Queue-based task management
- Checkpoint/resume capability
- State machine (PENDING -> SEARCHING -> SUCCESS/FAILED)
- Automatic retry logic

Usage:
    # Run discovery (processes batch of 50 by default)
    python scripts/run_discovery.py --batch-size 50

    # Run with custom delay
    python scripts/run_discovery.py --delay 10 --batch-size 100

    # Dry-run (simulate without updating database)
    python scripts/run_discovery.py --dry-run --limit 10
"""

import argparse
import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, quote

import psycopg2
from playwright.async_api import async_playwright, Page
from thefuzz import fuzz

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.crawler_settings import get_crawler_settings
from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/v120_discovery.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Task Queue Manager
# ============================================================================

class TaskQueueManager:
    """V120.0: 任务队列管理器.

    负责从 match_search_queue 获取任务、更新状态、处理重试逻辑。
    """

    def __init__(self, settings):
        """初始化队列管理器.

        Args:
            settings: 统一配置对象
        """
        self.settings = settings
        self.crawler_config = get_crawler_settings()

    def get_pending_tasks(self, limit: int) -> list[dict]:
        """获取待处理任务.

        Args:
            limit: 获取任务数量

        Returns:
            任务列表，每个任务包含 match_id, home_team, away_team, match_date
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 使用 FOR UPDATE SKIP LOCKED 实现并发安全
        cursor.execute("""
            SELECT
                q.match_id,
                m.home_team,
                m.away_team,
                m.match_date
            FROM match_search_queue q
            JOIN matches m ON q.match_id = m.match_id
            WHERE q.status = 'PENDING'
               OR (q.status = 'FAILED' AND q.retry_count < q.max_retries)
            ORDER BY q.updated_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, (limit,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [
            {
                "match_id": row[0],
                "home_team": row[1],
                "away_team": row[2],
                "match_date": row[3]
            }
            for row in rows
        ]

    def update_status_to_searching(self, match_ids: list[str]) -> None:
        """批量更新任务状态为 SEARCHING.

        Args:
            match_ids: 比赛 ID 列表
        """
        if not match_ids:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE match_search_queue
            SET status = 'SEARCHING',
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = ANY(%s)
        """, (match_ids,))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Updated {len(match_ids)} tasks to SEARCHING")

    def update_task_success(
        self,
        match_id: str,
        discovered_url: str
    ) -> None:
        """标记任务成功.

        Args:
            match_id: 比赛 ID
            discovered_url: 发现的 URL
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE match_search_queue
            SET status = 'SUCCESS',
                discovered_url = %s,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
        """, (discovered_url, match_id))

        # 同时更新 matches 表
        cursor.execute("""
            UPDATE matches
            SET oddsportal_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
        """, (discovered_url, match_id))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ Task {match_id}: SUCCESS (url={discovered_url})")

    def update_task_failed(
        self,
        match_id: str,
        error_message: str
    ) -> None:
        """标记任务失败.

        Args:
            match_id: 比赛 ID
            error_message: 错误信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 增加重试计数
        cursor.execute("""
            UPDATE match_search_queue
            SET status = CASE
                    WHEN retry_count + 1 >= max_retries THEN 'FAILED'
                    ELSE 'PENDING'
                END,
                retry_count = retry_count + 1,
                last_error = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
        """, (error_message[:500], match_id))  # 限制错误信息长度

        conn.commit()

        # 检查最终状态
        cursor.execute("""
            SELECT status, retry_count, max_retries
            FROM match_search_queue
            WHERE match_id = %s
        """, (match_id,))

        row = cursor.fetchone()
        final_status = row[0]
        retry_count = row[1]
        max_retries = row[2]

        cursor.close()
        conn.close()

        if final_status == 'PENDING':
            logger.info(f"⚠️  Task {match_id}: Will retry ({retry_count}/{max_retries})")
        else:
            logger.error(f"❌ Task {match_id}: FAILED permanently ({retry_count}/{max_retries})")

    def get_queue_statistics(self) -> dict[str, int]:
        """获取队列统计信息.

        Returns:
            各状态任务数量
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM match_search_queue
            GROUP BY status
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return {row[0]: row[1] for row in rows}

    def print_statistics(self) -> None:
        """打印队列统计."""
        stats = self.get_queue_statistics()

        logger.info("\n" + "=" * 60)
        logger.info("队列状态统计:")
        logger.info("-" * 60)

        total = sum(stats.values())
        for status in ["PENDING", "SEARCHING", "SUCCESS", "FAILED"]:
            count = stats.get(status, 0)
            percentage = (count / total * 100) if total > 0 else 0
            logger.info(f"  {status:12} {count:5} ({percentage:5.1f}%)")

        logger.info("-" * 60)
        logger.info(f"  {'TOTAL':12} {total:5}")
        logger.info("=" * 60)

    def _get_connection(self):
        """获取数据库连接."""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value()
        )


# ============================================================================
# Discovery Engine
# ============================================================================

class QueueBasedDiscoveryEngine:
    """V120.0: 基于队列的发现引擎.

    整合任务队列管理和 URL 发现逻辑。
    """

    def __init__(
        self,
        settings,
        dry_run: bool = False
    ):
        """初始化发现引擎.

        Args:
            settings: 统一配置
            dry_run: 是否为模拟运行
        """
        self.settings = settings
        self.crawler_config = get_crawler_settings()
        self.dry_run = dry_run

        self.queue_manager = TaskQueueManager(settings)
        self.base_url = "https://www.oddsportal.com"

        # 获取配置参数
        self.request_delay_min = self.crawler_config.network.request_delay_min
        self.request_delay_max = self.crawler_config.network.request_delay_max

        logger.info(f"配置: 延迟 {self.request_delay_min}-{self.request_delay_max}s")
        logger.info(f"模式: {'DRY-RUN' if dry_run else 'LIVE'}")

    async def search_match(
        self,
        page: Page,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> dict[str, Any]:
        """搜索比赛 URL.

        Args:
            page: Playwright Page 对象
            home_team: 主队
            away_team: 客队
            match_date: 比赛日期

        Returns:
            搜索结果字典
        """
        date_str = match_date.strftime("%Y-%m-%d")
        year_str = match_date.strftime("%Y")

        result = {
            "url": None,
            "search_method": None,
            "error": None
        }

        try:
            # 方法 1: 档案页浏览
            archive_url = f"{self.base_url}/football/{year_str}/{date_str[5:7]}/{date_str[8:10]}/"

            await page.goto(archive_url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(2)

            match_links = await page.query_selector_all("a[href*='/match/']")

            for link in match_links:
                href = await link.get_attribute("href")
                text = await link.text_content()

                if not text:
                    continue

                home_norm = TeamNameNormalizer.normalize(home_team)
                away_norm = TeamNameNormalizer.normalize(away_team)
                text_norm = TeamNameNormalizer.normalize(text)

                home_sim = fuzz.partial_ratio(home_norm, text_norm)
                away_sim = fuzz.partial_ratio(away_norm, text_norm)

                if home_sim >= 65 and away_sim >= 65:
                    result["url"] = urljoin(self.base_url, href)
                    result["search_method"] = "archive_fuzz"
                    logger.info(f"  ✅ Found: {result['url']}")
                    return result

            # 方法 2: 搜索页面
            search_query = f"{home_team} {away_team}"
            search_url = f"{self.base_url}/search/{quote(search_query)}/"

            await page.goto(search_url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(3)

            if "/match/" in page.url:
                result["url"] = page.url
                result["search_method"] = "search_redirect"
                logger.info(f"  ✅ Redirect: {result['url']}")
                return result

            match_links = await page.query_selector_all("a[href*='/match/']")

            for link in match_links[:10]:
                href = await link.get_attribute("href")
                text = await link.text_content()

                if not text:
                    continue

                home_norm = TeamNameNormalizer.normalize(home_team)
                away_norm = TeamNameNormalizer.normalize(away_team)
                text_norm = TeamNameNormalizer.normalize(text)

                home_sim = fuzz.partial_ratio(home_norm, text_norm)
                away_sim = fuzz.partial_ratio(away_norm, text_norm)

                if home_sim >= 65 and away_sim >= 65:
                    result["url"] = urljoin(self.base_url, href)
                    result["search_method"] = "search_results"
                    logger.info(f"  ✅ Found in search: {result['url']}")
                    return result

            result["search_method"] = "not_found"
            return result

        except Exception as e:
            result["error"] = str(e)
            result["search_method"] = "error"
            logger.error(f"  ❌ Error: {e}")
            return result

    async def process_batch(self, tasks: list[dict]) -> dict[str, int]:
        """处理一批任务.

        Args:
            tasks: 任务列表

        Returns:
            处理结果统计
        """
        stats = {
            "total": len(tasks),
            "success": 0,
            "failed": 0,
            "not_found": 0
        }

        if self.dry_run:
            logger.info("[DRY-RUN] 模拟处理，不更新数据库")
            for task in tasks:
                match_id = task["match_id"]
                logger.info(f"  [{task['match_id']}] {task['home_team']} vs {task['away_team']}")
            return stats

        # 更新状态为 SEARCHING
        match_ids = [t["match_id"] for t in tasks]
        self.queue_manager.update_status_to_searching(match_ids)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for i, task in enumerate(tasks, 1):
                match_id = task["match_id"]
                home_team = task["home_team"]
                away_team = task["away_team"]
                match_date = task["match_date"]

                logger.info(f"[{i}/{len(tasks)}] {match_id}: {home_team} vs {away_team}")

                # 执行搜索
                result = await self.search_match(page, home_team, away_team, match_date)

                # 更新结果
                if result["url"]:
                    self.queue_manager.update_task_success(match_id, result["url"])
                    stats["success"] += 1
                elif result["error"]:
                    self.queue_manager.update_task_failed(match_id, result["error"])
                    stats["failed"] += 1
                else:
                    self.queue_manager.update_task_failed(match_id, "URL not found")
                    stats["not_found"] += 1

                # 请求延迟
                delay = asyncio.create_task(self._delay())
                await delay

            await browser.close()

        return stats

    async def _delay(self) -> None:
        """随机延迟."""
        import random
        delay = random.uniform(self.request_delay_min, self.request_delay_max)
        await asyncio.sleep(delay)


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """V120.0: 主入口点."""
    parser = argparse.ArgumentParser(
        description="V120.0 Phase 3: Queue-Based Discovery Engine"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="每批处理的任务数 (default: 50)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=None,
        help="请求延迟覆盖 (秒)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不更新数据库"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制处理数量 (测试用)"
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("V120.0 Phase 3: Queue-Based Discovery Engine")
    logger.info("=" * 80)

    # 获取配置
    settings = get_settings()
    crawler_config = get_crawler_settings()

    # 应用延迟覆盖
    if args.delay:
        crawler_config.network.request_delay_min = float(args.delay)
        crawler_config.network.request_delay_max = float(args.delay)

    # 创建引擎
    engine = QueueBasedDiscoveryEngine(settings, dry_run=args.dry_run)

    # 打印初始统计
    engine.queue_manager.print_statistics()

    # 获取待处理任务
    batch_size = args.limit if args.limit else args.batch_size
    tasks = engine.queue_manager.get_pending_tasks(batch_size)

    if not tasks:
        logger.info("没有待处理任务")
        return

    logger.info(f"\n获取到 {len(tasks)} 个待处理任务")
    logger.info("开始处理...\n")

    # 处理批次
    stats = await engine.process_batch(tasks)

    # 打印结果
    logger.info("\n" + "=" * 80)
    logger.info("批次处理完成")
    logger.info("-" * 80)
    logger.info(f"  成功:    {stats['success']:5}")
    logger.info(f"  失败:    {stats['failed']:5}")
    logger.info(f"  未找到:  {stats['not_found']:5}")
    logger.info(f"  总计:    {stats['total']:5}")
    logger.info("=" * 80)

    # 打印更新后的统计
    engine.queue_manager.print_statistics()


if __name__ == "__main__":
    asyncio.run(main())
