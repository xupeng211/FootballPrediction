#!/usr/bin/env python3
"""
V41.239 "Automated Match Discovery" - 跨源赛程自动对齐

功能：
    A. 待办池提取 - 从数据库筛选未来 48 小时且无赔率记录的比赛
    B. 智能 URL 生成 - 基于队名和日期动态生成 OddsPortal 搜索 URL
    C. 批量作业分发 - 生产者-消费者模式调用 bin/odds_sync

依赖：
    - psycopg2: 数据库连接
    - src.config_unified: 统一配置
    - bin/odds_sync: V41.236 生产入口

使用方式：
    # 扫描并分发（干跑模式）
    python scripts/ops/auto_odds_discover.py --dry-run

    # 执行采集
    python scripts/ops/auto_odds_discover.py --concurrent 3

    # 指定时间窗口（小时）
    python scripts/ops/auto_odds_discover.py --hours 72

作者：V41.239 Integration Team
版本：V41.239
日期：2026-01-19
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_config

# =============================================================================
# 配置与日志
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("V41.239")

# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class PendingMatch:
    """待采集比赛数据"""

    match_id: str
    home_team: str
    away_team: str
    match_date: datetime
    league_name: str
    season: str


@dataclass
class DiscoveryResult:
    """发现结果"""

    total_queued: int = 0
    urls_resolved: int = 0
    urls_failed: int = 0
    processing_errors: int = 0
    candidates_by_league: dict[str, int] = field(default_factory=dict)

    def to_summary(self) -> str:
        """生成摘要报告"""
        lines = [
            "═══════════════════════════════════════════════════════════════",
            "  V41.239 Automated Match Discovery - Execution Summary",
            "═══════════════════════════════════════════════════════════════",
            f"  Matches Queued:    {self.total_queued}",
            f"  URLs Resolved:     {self.urls_resolved}",
            f"  URLs Failed:       {self.urls_failed}",
            f"  Processing Errors: {self.processing_errors}",
            "",
            "  By League:",
        ]

        for league, count in sorted(self.candidates_by_league.items()):
            lines.append(f"    - {league}: {count}")

        lines.append("═══════════════════════════════════════════════════════════════")
        return "\n".join(lines)


# =============================================================================
# A. 待办池提取器
# =============================================================================


class PendingPoolExtractor:
    """
    待办池提取器

    从 matches 表中筛选出：
    1. 指定时间窗口内的比赛（支持历史回填）
    2. 在 match_odds_intelligence 表中无记录
    """

    def __init__(self, time_window_hours: int = 48, catch_up_mode: bool = False):
        """
        初始化提取器

        Args:
            time_window_hours: 时间窗口（小时），默认 48
            catch_up_mode: 历史回填模式（扫描过去 7 天），默认 False
        """
        self.time_window_hours = time_window_hours
        self.catch_up_mode = catch_up_mode
        self.config = get_config()

    def extract(self) -> list[PendingMatch]:
        """
        提取待办比赛

        Returns:
            待办比赛列表
        """
        conn = psycopg2.connect(
            host=self.config.database.host,
            database=self.config.database.name,
            user=self.config.database.user,
            password=self.config.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        try:
            cursor = conn.cursor()

            # 计算时间范围
            now = datetime.now()
            if self.catch_up_mode:
                # V41.240 Catch-up Mode: 扫描过去 7 天到未来 48 小时
                time_start = now - timedelta(days=7)
                time_end = now + timedelta(hours=self.time_window_hours)
            else:
                # 标准模式: 从现在到未来 N 小时
                time_start = now
                time_end = now + timedelta(hours=self.time_window_hours)

            logger.info(f"Scanning matches from {time_start} to {time_end}")

            # 查询待办比赛（LEFT JOIN 筛选无赔率记录的）
            query = """
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.league_name,
                    m.season
                FROM matches m
                LEFT JOIN match_odds_intelligence oi
                    ON m.match_id = oi.match_id
                WHERE m.match_date BETWEEN %s AND %s
                    AND oi.match_id IS NULL
                ORDER BY m.match_date ASC
            """

            cursor.execute(query, (time_start, time_end))
            rows = cursor.fetchall()

            pending_matches = [
                PendingMatch(
                    match_id=row["match_id"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    match_date=row["match_date"],
                    league_name=row["league_name"],
                    season=row["season"],
                )
                for row in rows
            ]

            logger.info(f"Found {len(pending_matches)} matches without odds data")
            return pending_matches

        finally:
            conn.close()


# =============================================================================
# B. V41.243 动态 URL 生成器（LeagueRouter 集成）
# =============================================================================


class OddsPortalURLGenerator:
    """
    V41.243 OddsPortal URL 生成器 - 零硬编码版

    使用 LeagueRouter 动态解析联赛 URL，支持全球联赛、杯赛、世界杯
    """

    def __init__(self):
        """初始化生成器（延迟加载 LeagueRouter）"""
        self._router = None

    @property
    def router(self):
        """延迟加载 LeagueRouter"""
        if self._router is None:
            from src.services.league_router import LeagueRouter
            self._router = LeagueRouter()
        return self._router

    def generate_search_urls(self, match: PendingMatch) -> list[str]:
        """
        V41.243 为比赛生成可能的搜索 URL（动态路由版）

        策略层级：
        1. LeagueRouter 动态解析（支持全球联赛）
        2. 杯赛变体路由
        3. 队名搜索兜底

        Args:
            match: 待办比赛

        Returns:
            URL 列表（按优先级排序）
        """
        urls = []

        # 策略 1: LeagueRouter 动态解析
        try:
            resolved_urls = self.router.resolve_with_fallback(
                league_name=match.league_name,
                home_team=match.home_team,
                away_team=match.away_team,
                season=match.season,
            )
            urls.extend(resolved_urls)
        except Exception as e:
            logger.debug(f"LeagueRouter resolution failed: {e}")

        # 去重
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls


# =============================================================================
# C. 批量作业分发器（生产者-消费者模式）
# =============================================================================


class JobDispatcher:
    """
    作业分发器

    使用生产者-消费者模式批量调用 bin/odds_sync
    """

    def __init__(
        self,
        max_workers: int = 3,
        proxy_port: int = 7892,
        timeout_seconds: int = 300,
        dry_run: bool = False,
    ):
        """
        初始化分发器

        Args:
            max_workers: 最大并发数（防止代理过载）
            proxy_port: 代理端口
            timeout_seconds: 单任务超时
            dry_run: 干跑模式（仅打印，不实际执行）
        """
        self.max_workers = max_workers
        self.proxy_port = proxy_port
        self.timeout_seconds = timeout_seconds
        self.dry_run = dry_run
        self.results = DiscoveryResult()
        self._lock = Lock()

        # bin/odds_sync 路径
        self.odds_sync_script = project_root / "bin" / "odds_sync"

        if not self.odds_sync_script.exists():
            raise FileNotFoundError(f"odds_sync script not found: {self.odds_sync_script}")

    def dispatch(self, matches: list[PendingMatch]) -> DiscoveryResult:
        """
        分发作业

        Args:
            matches: 待办比赛列表

        Returns:
            发现结果
        """
        self.results.total_queued = len(matches)

        if not matches:
            logger.warning("No matches to process")
            return self.results

        # 按联赛分组（用于统计）
        league_counts: dict[str, int] = defaultdict(int)
        for match in matches:
            league_counts[match.league_name] += 1

        self.results.candidates_by_league = dict(league_counts)

        logger.info(f"Dispatching {len(matches)} matches with {self.max_workers} workers")

        if self.dry_run:
            return self._dispatch_dry_run(matches)

        # 生产者-消费者模式
        job_queue: Queue[tuple[PendingMatch, str]] = Queue()

        # 生产者：生成作业
        producer_thread = Thread(
            target=self._producer,
            args=(matches, job_queue),
            daemon=True,
        )
        producer_thread.start()

        # 消费者：执行作业
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            while True:
                try:
                    match, url = job_queue.get(timeout=1)

                    future = executor.submit(
                        self._worker,
                        match,
                        url,
                    )
                    futures.append(future)

                    job_queue.task_done()

                except Empty:
                    if not producer_thread.is_alive():
                        break

        # 等待所有任务完成
        producer_thread.join()

        return self.results

    def _producer(self, matches: list[PendingMatch], queue: Queue):
        """生产者：生成 URL 并加入队列"""
        url_generator = OddsPortalURLGenerator()

        for match in matches:
            urls = url_generator.generate_search_urls(match)

            # 取第一个 URL（优先级最高）
            if urls:
                queue.put((match, urls[0]))

    def _worker(self, match: PendingMatch, url: str) -> bool:
        """消费者：执行单个采集任务"""
        cmd = [
            str(self.odds_sync_script),
            "--url", url,
            "--proxy-port", str(self.proxy_port),
            "--log-level", "WARNING",  # 减少日志噪音
        ]

        logger.info(f"Processing {match.match_id}: {match.home_team} vs {match.away_team}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=str(project_root),
            )

            if result.returncode == 0:
                with self._lock:
                    self.results.urls_resolved += 1
                logger.info(f"✓ {match.match_id} completed")
                return True
            else:
                with self._lock:
                    self.results.urls_failed += 1
                logger.warning(f"✗ {match.match_id} failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            with self._lock:
                self.results.processing_errors += 1
            logger.error(f"✗ {match.match_id} timeout")
            return False

        except Exception as e:
            with self._lock:
                self.results.processing_errors += 1
            logger.error(f"✗ {match.match_id} error: {e}")
            return False

    def _dispatch_dry_run(self, matches: list[PendingMatch]) -> DiscoveryResult:
        """干跑模式：仅打印"""
        url_generator = OddsPortalURLGenerator()

        for match in matches:
            urls = url_generator.generate_search_urls(match)

            print(f"\n{'='*70}")
            print(f"Match: {match.home_team} vs {match.away_team}")
            print(f"League: {match.league_name}")
            print(f"Date: {match.match_date}")
            print(f"Generated URLs:")
            for i, url in enumerate(urls, 1):
                print(f"  {i}. {url}")
            print(f"{'='*70}")

            # 统计
            self.results.urls_resolved = len(matches)

        return self.results


# =============================================================================
# 主程序
# =============================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="V41.239 Automated Match Discovery - 跨源赛程自动对齐",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    # 干跑模式（仅打印 URL）
    python scripts/ops/auto_odds_discover.py --dry-run

    # 执行采集（3 并发）
    python scripts/ops/auto_odds_discover.py --concurrent 3

    # 自定义时间窗口（72 小时）
    python scripts/ops/auto_odds_discover.py --hours 72

    # 指定代理端口
    python scripts/ops/auto_odds_discover.py --proxy-port 7893
        """,
    )

    parser.add_argument(
        "--hours",
        type=int,
        default=48,
        help="时间窗口（小时），默认 48",
    )

    parser.add_argument(
        "--concurrent",
        type=int,
        default=3,
        help="最大并发数（防止代理过载），默认 3",
    )

    parser.add_argument(
        "--proxy-port",
        type=int,
        default=7892,
        help="代理端口，默认 7892",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="单任务超时（秒），默认 300",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式（仅打印 URL，不实际执行）",
    )

    parser.add_argument(
        "--catch-up",
        action="store_true",
        help="V41.240 Catch-up Mode: 扫描过去 7 天的历史数据",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别，默认 INFO",
    )

    return parser.parse_args()


def main():
    """主程序入口"""
    args = parse_args()

    # 设置日志级别
    logger.setLevel(getattr(logging, args.log_level))

    logger.info("=" * 70)
    logger.info("V41.239 Automated Match Discovery - 启动")
    logger.info("=" * 70)
    logger.info(f"Configuration:")
    logger.info(f"  Time Window: {args.hours} hours")
    logger.info(f"  Catch-up Mode: {args.catch_up}")
    logger.info(f"  Max Workers: {args.concurrent}")
    logger.info(f"  Proxy Port: {args.proxy_port}")
    logger.info(f"  Timeout: {args.timeout}s")
    logger.info(f"  Dry Run: {args.dry_run}")
    logger.info("=" * 70)

    # A. 提取待办池
    extractor = PendingPoolExtractor(
        time_window_hours=args.hours,
        catch_up_mode=args.catch_up
    )
    pending_matches = extractor.extract()

    if not pending_matches:
        logger.info("No pending matches found. Exiting.")
        return 0

    # C. 分发作业
    dispatcher = JobDispatcher(
        max_workers=args.concurrent,
        proxy_port=args.proxy_port,
        timeout_seconds=args.timeout,
        dry_run=args.dry_run,
    )

    results = dispatcher.dispatch(pending_matches)

    # 打印摘要
    print("\n" + results.to_summary())

    return 0


if __name__ == "__main__":
    sys.exit(main())
