#!/usr/bin/env python3
"""V120.0 Phase 2: Concurrent Discovery Cluster with Circuit Breaker.

Production-grade cluster discovery system with:
- Multi-worker concurrent processing (via asyncio tasks)
- Circuit breaker (10 consecutive failures -> abort)
- Real-time monitoring and ETA calculation
- FOR UPDATE SKIP LOCKED for concurrent safety

Usage:
    # Stress test with 2 workers, 10 matches
    python scripts/run_discovery_cluster.py --workers 2 --limit 10

    # Full production run with 4 workers
    python scripts/run_discovery_cluster.py --workers 4

    # Background mode with custom delay
    nohup python scripts/run_discovery_cluster.py --workers 4 --delay-min 8 --delay-max 15 > logs/discovery_cluster.log 2>&1 &
"""

import argparse
import asyncio
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
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
        logging.FileHandler("logs/v120_discovery_cluster.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Circuit breaker constants
CIRCUIT_BREAKER_THRESHOLD = 10  # Trigger abort after N consecutive failures

# Alert colors for terminal
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitBreaker:
    """熔断器 - 连续失败时触发系统停止."""

    def __init__(self, threshold: int = CIRCUIT_BREAKER_THRESHOLD):
        """初始化熔断器."""
        self.threshold = threshold
        self.consecutive_failures = 0
        self.last_failure_time: datetime | None = None
        self.is_tripped = False

    def record_success(self) -> None:
        """记录成功，重置失败计数."""
        self.consecutive_failures = 0
        self.is_tripped = False

    def record_failure(self) -> bool:
        """记录失败，检查是否需要熔断."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()

        if self.consecutive_failures >= self.threshold:
            self.is_tripped = True
            return True
        return False

    def should_abort(self) -> bool:
        """检查是否应该中止执行."""
        return self.is_tripped


# ============================================================================
# Task Queue Manager
# ============================================================================

class TaskQueueManager:
    """任务队列管理器 - 支持并发安全."""

    def __init__(self, settings):
        """初始化队列管理器."""
        self.settings = settings

    def get_pending_tasks(self, limit: int) -> list[dict]:
        """获取待处理任务 (并发安全)."""
        conn = self._get_connection()
        cursor = conn.cursor()

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
        """批量更新状态为 SEARCHING."""
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

    def update_task_success(self, match_id: str, discovered_url: str) -> None:
        """标记任务成功."""
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

        cursor.execute("""
            UPDATE matches
            SET oddsportal_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
        """, (discovered_url, match_id))

        conn.commit()
        cursor.close()
        conn.close()

    def update_task_failed(self, match_id: str, error_message: str) -> tuple[bool, int]:
        """标记任务失败.

        Returns:
            (is_permanent_failure, retry_count)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

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
            RETURNING status, retry_count, max_retries
        """, (error_message[:500], match_id))

        row = cursor.fetchone()
        final_status = row[0]
        retry_count = row[1]
        max_retries = row[2]

        conn.commit()
        cursor.close()
        conn.close()

        is_permanent = (final_status == 'FAILED')
        return is_permanent, retry_count

    def get_queue_statistics(self) -> dict[str, int]:
        """获取队列统计."""
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

    def get_eta_stats(self) -> dict[str, Any]:
        """获取 ETA 计算所需统计数据."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 待处理数量
        cursor.execute("""
            SELECT COUNT(*) FROM match_search_queue
            WHERE status = 'PENDING'
               OR (status = 'FAILED' AND retry_count < max_retries)
        """)
        pending = cursor.fetchone()[0]

        # 过去 15 分钟的成功数量
        fifteen_min_ago = datetime.now() - timedelta(minutes=15)
        cursor.execute("""
            SELECT COUNT(*) FROM match_search_queue
            WHERE status = 'SUCCESS'
              AND updated_at > %s
        """, (fifteen_min_ago,))
        success_count_15min = cursor.fetchone()[0]

        # 平均每个任务耗时
        cursor.execute("""
            SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))
            FROM match_search_queue
            WHERE status = 'SUCCESS'
              AND updated_at > %s
        """, (fifteen_min_ago,))
        avg_time = cursor.fetchone()[0] or 0

        cursor.close()
        conn.close()

        success_rate = success_count_15min / 15 if success_count_15min > 0 else 0
        eta_seconds = pending / success_rate if success_rate > 0 else None

        return {
            "pending": pending,
            "success_rate_15min": success_rate,
            "success_count_15min": success_count_15min,
            "avg_time_per_task": avg_time,
            "eta_seconds": eta_seconds
        }

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
# Discovery Worker
# ============================================================================

async def search_match_v121(
    page: Page,
    home_team: str,
    away_team: str,
    match_date: datetime,
    base_url: str
) -> dict[str, Any]:
    """V121.0 天眼搜索引擎 - 搜索优先 + 时域扩展 + 深度名字对齐.

    核心升级:
    1. 搜索优先策略 - 直接搜索作为第一入口
    2. 时域范围扩展 - D-1, D, D+1 三天探测
    3. 深度名字对齐 - 阈值降至 60%，支持模糊匹配
    4. 双重重定向捕获 - 自动重定向 + 结果列表匹配

    Args:
        page: Playwright Page 对象
        home_team: 主队名称
        away_team: 客队名称
        match_date: 比赛日期
        base_url: OddsPortal 基础 URL

    Returns:
        搜索结果字典 {url, search_method, error}
    """
    result = {
        "url": None,
        "search_method": None,
        "error": None
    }

    try:
        # ====================================================================
        # V121.0 Phase 1: 搜索优先策略 (Search-First Strategy)
        # ====================================================================

        # 规范化球队名 - 核心词提取
        normalizer = TeamNameNormalizer()
        home_core = normalizer.normalize(home_team)
        away_core = normalizer.normalize(away_team)

        # V121.0: 降低匹配阈值到 60% (针对历史数据放宽标准)
        MATCH_THRESHOLD = 60

        # 构建搜索查询 - 多种格式尝试
        search_queries = [
            f"{home_core} {away_core}",  # 核心词搜索
            f"{home_team} {away_team}",   # 全名搜索
            f"{home_core}+{away_core}",   # 加号连接
        ]

        # V121.0: 时域扩展 - 准备多个日期
        from datetime import timedelta
        search_dates = [
            match_date - timedelta(days=1),  # D-1
            match_date,                       # D (目标日期)
            match_date + timedelta(days=1),  # D+1
        ]

        logger.debug(f"[V121.0] Searching: {home_team} vs {away_team} on {match_date}")

        # ====================================================================
        # V121.0 Phase 2: 直接搜索优先 (Direct Search First)
        # ====================================================================

        for date_offset, search_date in enumerate(search_dates):
            date_label = ["D-1", "D", "D+1"][date_offset]
            date_str = search_date.strftime("%Y-%m-%d")
            year_str = search_date.strftime("%Y")

            for query_idx, search_query in enumerate(search_queries):
                try:
                    # V121.0: 使用 OddsPortal 搜索页面
                    search_url = f"{base_url}/search/{quote(search_query)}/"
                    logger.debug(f"[V121.0] [{date_label}] Query {query_idx + 1}: {search_url}")

                    await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)

                    # V121.0 Phase 3: 双重重定向捕获
                    # 检查是否自动重定向到比赛页面
                    current_url = page.url
                    if "/match/" in current_url:
                        # 验证页面是否包含相关内容
                        page_text = await page.text_content()
                        if page_text:
                            page_text_lower = page_text.lower()
                            # 检查球队名是否在页面中
                            home_found = home_core in page_text_lower or home_team.lower() in page_text_lower
                            away_found = away_core in page_text_lower or away_team.lower() in page_text_lower

                            if home_found and away_found:
                                result["url"] = current_url
                                result["search_method"] = f"search_redirect_{date_label}_q{query_idx + 1}"
                                logger.info(f"  ✅ [V121.0] Found via redirect: {current_url}")
                                return result

                    # V121.0 Phase 4: 搜索结果列表匹配
                    # 查找所有比赛链接
                    match_links = await page.query_selector_all("a[href*='/match/']")

                    for link_idx, link in enumerate(match_links[:20]):  # 增加到前 20 个结果
                        try:
                            href = await link.get_attribute("href")
                            text = await link.text_content()

                            if not text or not href:
                                continue

                            # V121.0: 深度名字对齐
                            text_core = normalizer.normalize(text)

                            # 计算相似度
                            home_sim = fuzz.partial_ratio(home_core, text_core)
                            away_sim = fuzz.partial_ratio(away_core, text_core)

                            # 同时检查全名相似度
                            home_sim_full = fuzz.partial_ratio(home_team.lower(), text.lower())
                            away_sim_full = fuzz.partial_ratio(away_team.lower(), text.lower())

                            # 使用最高的相似度分数
                            max_home_sim = max(home_sim, home_sim_full)
                            max_away_sim = max(away_sim, away_sim_full)

                            # V121.0: 阈值降至 60%
                            if max_home_sim >= MATCH_THRESHOLD and max_away_sim >= MATCH_THRESHOLD:
                                result["url"] = urljoin(base_url, href)
                                result["search_method"] = f"search_results_{date_label}_q{query_idx + 1}_l{link_idx + 1}"
                                logger.info(f"  ✅ [V121.0] Found: {result['url']}")
                                logger.info(f"     Similarity: Home={max_home_sim:.0f}%, Away={max_away_sim:.0f}%")
                                logger.info(f"     Query: {text[:80]}")
                                return result

                            # 额外匹配策略：只要一个队名匹配度极高，且包含另一个队的部分名称
                            if max_home_sim >= 75:
                                # 检查文本是否包含客队的部分名称
                                away_parts = away_core.split()
                                for part in away_parts:
                                    if len(part) >= 3 and part in text_core:
                                        result["url"] = urljoin(base_url, href)
                                        result["search_method"] = f"search_partial_{date_label}_q{query_idx + 1}"
                                        logger.info(f"  ✅ [V121.0] Found (partial): {result['url']}")
                                        logger.info(f"     Similarity: Home={max_home_sim:.0f}%, Away=partial")
                                        return result

                            if max_away_sim >= 75:
                                home_parts = home_core.split()
                                for part in home_parts:
                                    if len(part) >= 3 and part in text_core:
                                        result["url"] = urljoin(base_url, href)
                                        result["search_method"] = f"search_partial_{date_label}_q{query_idx + 1}"
                                        logger.info(f"  ✅ [V121.0] Found (partial): {result['url']}")
                                        logger.info(f"     Similarity: Home=partial, Away={max_away_sim:.0f}%")
                                        return result

                        except Exception:
                            continue

                except Exception as e:
                    logger.debug(f"[V121.0] Search query failed: {e}")
                    continue

        # ====================================================================
        # V121.0 Phase 5: 档案页兜底 (Archive Page Fallback)
        # ====================================================================

        # 只有在搜索全部失败后才尝试档案页（2024年后可能无效）
        year_str = match_date.strftime("%Y")
        date_str = match_date.strftime("%Y-%m-%d")

        archive_url = f"{base_url}/football/{year_str}/{date_str[5:7]}/{date_str[8:10]}/"
        logger.debug(f"[V121.0] Archive fallback: {archive_url}")

        try:
            await page.goto(archive_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            match_links = await page.query_selector_all("a[href*='/match/']")

            for link in match_links:
                href = await link.get_attribute("href")
                text = await link.text_content()

                if not text:
                    continue

                text_core = normalizer.normalize(text)

                home_sim = fuzz.partial_ratio(home_core, text_core)
                away_sim = fuzz.partial_ratio(away_core, text_core)

                if home_sim >= MATCH_THRESHOLD and away_sim >= MATCH_THRESHOLD:
                    result["url"] = urljoin(base_url, href)
                    result["search_method"] = "archive_fuzz_fallback"
                    logger.info(f"  ✅ [V121.0] Found via archive fallback: {result['url']}")
                    return result

        except Exception as e:
            logger.debug(f"[V121.0] Archive fallback failed: {e}")

        # 全部失败
        result["search_method"] = "not_found_v121"
        logger.warning(f"  ❌ [V121.0] Not found: {home_team} vs {away_team} ({date_str})")
        return result

    except Exception as e:
        result["error"] = str(e)
        result["search_method"] = "error_v121"
        logger.error(f"  ❌ [V121.0] Error: {e}")
        return result


async def search_match(
    page: Page,
    home_team: str,
    away_team: str,
    match_date: datetime,
    base_url: str
) -> dict[str, Any]:
    """搜索比赛 URL - V121.0 天眼引擎入口."""
    return await search_match_v121(page, home_team, away_team, match_date, base_url)


async def worker(
    worker_id: int,
    settings,
    batch_size: int,
    delay_min: float,
    delay_max: float,
    circuit_breaker: CircuitBreaker,
    shared_stats: dict[str, int],
    stop_event: asyncio.Event,
    global_limit: int | None = None
) -> dict[str, int]:
    """Worker 协程."""
    stats = {
        "worker_id": worker_id,
        "total": 0,
        "success": 0,
        "failed": 0,
        "not_found": 0
    }

    queue_manager = TaskQueueManager(settings)
    base_url = "https://www.oddsportal.com"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        while not stop_event.is_set():
            # 检查全局限制
            if global_limit is not None and shared_stats["total_processed"] >= global_limit:
                logger.info(f"[Worker-{worker_id}] 达到全局处理限制 {global_limit}")
                break

            if circuit_breaker.should_abort():
                logger.warning(f"[Worker-{worker_id}] 熔断器已触发，停止工作")
                break

            # 获取任务
            tasks = queue_manager.get_pending_tasks(batch_size)

            if not tasks:
                logger.info(f"[Worker-{worker_id}] 没有更多任务")
                break

            # 更新状态
            match_ids = [t["match_id"] for t in tasks]
            queue_manager.update_status_to_searching(match_ids)

            for task in tasks:
                # 检查全局限制
                if global_limit is not None and shared_stats["total_processed"] >= global_limit:
                    break

                if stop_event.is_set() or circuit_breaker.should_abort():
                    break

                match_id = task["match_id"]
                home_team = task["home_team"]
                away_team = task["away_team"]
                match_date = task["match_date"]

                logger.info(f"[Worker-{worker_id}] {match_id}: {home_team} vs {away_team}")

                # 执行搜索
                result = await search_match(page, home_team, away_team, match_date, base_url)

                stats["total"] += 1
                shared_stats["total_processed"] += 1

                # 更新结果
                if result["url"]:
                    queue_manager.update_task_success(match_id, result["url"])
                    stats["success"] += 1
                    shared_stats["total_success"] += 1

                    # 重置熔断器
                    circuit_breaker.record_success()

                elif result["error"]:
                    queue_manager.update_task_failed(match_id, result["error"])
                    stats["failed"] += 1

                    # 检查熔断器
                    if circuit_breaker.record_failure():
                        logger.error(f"[Worker-{worker_id}] 达到连续失败阈值，触发熔断！")
                        stop_event.set()
                        break

                else:
                    queue_manager.update_task_failed(match_id, "URL not found")
                    stats["not_found"] += 1

                    # 未找到重置熔断器（可能是正常情况）
                    circuit_breaker.record_success()

                # 延迟
                delay = random.uniform(delay_min, delay_max)
                await asyncio.sleep(delay)

        await browser.close()

    return stats


# ============================================================================
# Main Entry Point
# ============================================================================

def print_circuit_breaker_alert(failure_count: int):
    """打印熔断器红色警报."""
    print()
    print("=" * 80)
    print(f"{RED}{BOLD}⚠️  CIRCUIT BREAKER TRIGGERED! ⚠️{RESET}")
    print("=" * 80)
    print(f"{RED}{BOLD}连续失败次数: {failure_count}{RESET}")
    print(f"{RED}{BOLD}系统检测到异常，可能原因:{RESET}")
    print(f"{RED}  - OddsPortal 风控升级（IP 被封）{RESET}")
    print(f"{RED}  - 代理失效（Proxy Down）{RESET}")
    print(f"{RED}  - 网络连接异常{RESET}")
    print()
    print(f"{YELLOW}{BOLD}建议操作:{RESET}")
    print(f"{YELLOW}  1. 检查网络连接{RESET}")
    print(f"{YELLOW}  2. 更换代理 IP{RESET}")
    print(f"{YELLOW}  3. 等待冷却期后重试{RESET}")
    print("=" * 80)
    print()


def print_eta_report(queue_stats: dict, eta_stats: dict):
    """打印 ETA 报告."""
    print()
    print("=" * 80)
    print("📊 实时监控面板")
    print("=" * 80)

    # 队列状态
    print("\n队列状态:")
    pending = queue_stats.get("PENDING", 0)
    searching = queue_stats.get("SEARCHING", 0)
    success = queue_stats.get("SUCCESS", 0)
    failed = queue_stats.get("FAILED", 0)
    total = pending + searching + success + failed

    print(f"  PENDING:   {pending:5} ({pending/total*100 if total > 0 else 0:5.1f}%)")
    print(f"  SEARCHING: {searching:5} ({searching/total*100 if total > 0 else 0:5.1f}%)")
    print(f"  SUCCESS:   {success:5} ({success/total*100 if total > 0 else 0:5.1f}%)")
    print(f"  FAILED:    {failed:5} ({failed/total*100 if total > 0 else 0:5.1f}%)")
    print(f"  TOTAL:     {total:5}")

    # ETA
    print("\n完工预估 (ETA):")
    print(f"  待处理任务: {eta_stats['pending']}")
    print(f"  过去 15 分钟成功: {eta_stats['success_count_15min']} 场")
    print(f"  成功率: {eta_stats['success_rate_15min']:.2f} 场/分钟")

    if eta_stats['eta_seconds']:
        eta_hours = eta_stats['eta_seconds'] / 3600
        print(f"  预计剩余时间: {eta_hours:.1f} 小时")
    else:
        print(f"  预计剩余时间: 计算中...")

    print("=" * 80)
    print()


async def main_async(args):
    """异步主入口."""
    logger.info("=" * 80)
    logger.info("V120.0 Phase 2: Concurrent Discovery Cluster")
    logger.info("=" * 80)
    logger.info(f"Worker 数量: {args.workers}")
    logger.info(f"延迟范围: {args.delay_min}-{args.delay_max} 秒")
    logger.info(f"熔断阈值: {CIRCUIT_BREAKER_THRESHOLD} 连续失败")

    # 获取配置
    settings = get_settings()
    queue_manager = TaskQueueManager(settings)

    # 打印初始状态
    queue_stats = queue_manager.get_queue_statistics()
    logger.info(f"\n初始队列状态: {queue_stats}")

    # 共享状态
    shared_stats = {
        "total_processed": 0,
        "total_success": 0
    }

    # 熔断器
    circuit_breaker = CircuitBreaker()

    # 停止事件
    stop_event = asyncio.Event()

    # 启动 workers
    start_time = time.time()

    worker_tasks = []
    for i in range(args.workers):
        task = asyncio.create_task(
            worker(
                i + 1,
                settings,
                args.batch_size,
                args.delay_min,
                args.delay_max,
                circuit_breaker,
                shared_stats,
                stop_event,
                args.limit
            )
        )
        worker_tasks.append(task)

    # 等待所有 worker 完成
    try:
        results = await asyncio.gather(*worker_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Worker 异常: {result}")
            elif isinstance(result, dict):
                logger.info(f"Worker-{result['worker_id']} 完成: {result}")

    except KeyboardInterrupt:
        logger.warning("收到中断信号，正在停止 workers...")
        stop_event.set()

    elapsed = time.time() - start_time

    # 打印最终统计
    logger.info("\n" + "=" * 80)
    logger.info("集群运行完成")
    logger.info("=" * 80)
    logger.info(f"总耗时: {elapsed/60:.1f} 分钟")
    logger.info(f"总处理: {shared_stats['total_processed']} 场")
    logger.info(f"总成功: {shared_stats['total_success']} 场")

    # 检查熔断器
    if circuit_breaker.should_abort():
        print_circuit_breaker_alert(circuit_breaker.consecutive_failures)
        sys.exit(1)

    # 打印 ETA 报告
    final_queue_stats = queue_manager.get_queue_statistics()
    eta_stats = queue_manager.get_eta_stats()
    print_eta_report(final_queue_stats, eta_stats)

    # 成功率检查
    success_rate = shared_stats['total_success'] / shared_stats['total_processed'] if shared_stats['total_processed'] > 0 else 0
    if success_rate < 0.5:
        logger.warning(f"⚠️  成功率较低 ({success_rate*100:.1f}%)，建议检查配置")


def main():
    """主入口点."""
    parser = argparse.ArgumentParser(
        description="V120.0 Phase 2: Concurrent Discovery Cluster with Circuit Breaker"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Worker 数量 (default: 2)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="每批处理任务数 (default: 5)"
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=8.0,
        help="最小请求延迟 (秒, default: 8.0)"
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=15.0,
        help="最大请求延迟 (秒, default: 15.0)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="总处理限制 (测试用)"
    )
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
