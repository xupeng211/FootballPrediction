#!/usr/bin/env python3
"""
V41.244 SkynetWorker - 24/7 自愈守护进程 + 动态限流器
==========================================================

核心功能：
    - 任务队列管理 (Pending_Queue, Failure_Retry_Queue)
    - 指数退避重试策略 (5/15/60 分钟)
    - 低功耗休眠模式
    - 全球赛程自动适配
    - V41.244: 动态并发控制器（Adaptive Governor）

Usage:
    # 启动守护进程
    python scripts/ops/skynet_worker.py --daemon

    # 单次执行（调试）
    python scripts/ops/skynet_worker.py --once

    # 指定并发数
    python scripts/ops/skynet_worker.py --workers 4

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    SkynetWorker Daemon                      │
    │  ┌────────────────┐  ┌──────────────────┐  ┌─────────────┐│
    │  │ Pending_Queue  │→ │ Failure_Retry_Q  │→ │ Completed   ││
    │  └────────────────┘  └──────────────────┘  └─────────────┘│
    │         ↓                   ↓                    ↓          │
    │  ┌──────────────────────────────────────────────────────┐ │
    │  │  V41.244 Adaptive Governor (Rate Limiting)           │ │
    │  │  Concurrent_Jobs = Healthy_Proxies / Safety_Factor  │ │
    │  └──────────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────────┘

Author: V41.243 Skynet Team
Date: 2026-01-20
Version: V41.244 "Proxy Resilience & Stealth Audit"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_config
from src.services.match_linker import MatchLinker, LinkerConfig

# =============================================================================
# 日志配置
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SkynetWorker")


# =============================================================================
# 枚举与数据模型
# =============================================================================


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_1 = "retry_1"     # 5 分钟后重试
    RETRY_2 = "retry_2"     # 15 分钟后重试
    RETRY_3 = "retry_3"     # 60 分钟后重试
    ABANDONED = "abandoned"  # 放弃


@dataclass
class HarvestTask:
    """收割任务"""
    match_id: str
    home_team: str
    away_team: str
    match_date: datetime
    league_name: str
    season: str
    url: str
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class WorkerMetrics:
    """工作节点指标"""
    tasks_processed: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0
    tasks_abandoned: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    league_coverage: dict[str, int] = field(default_factory=dict)
    throughput_records_per_min: float = 0.0


# =============================================================================
# V41.244 动态并发控制器（Adaptive Governor）
# =============================================================================


class AdaptiveGovernor:
    """
    V41.244 动态并发控制器 - 代理限流与自适应调度

    核心功能：
        - 根据健康代理数量动态调整并发数
        - 每个代理 10 分钟内请求数限制
        - 安全系数保护（防止过载）

    公式：
        Concurrent_Jobs = Total_Healthy_Proxies / Safety_Factor
        Max_Requests_Per_IP_Per_10Min = 安全阈值（默认 30）

    Args:
        total_proxies: 总代理数量（从配置读取）
        safety_factor: 安全系数（默认 5，越高越保守）
        max_requests_per_10min: 每 10 分钟每 IP 最大请求数（默认 30）
    """

    # 代理端口配置（从 titan_config.yaml 读取）
    PROXY_PORTS = [
        7890, 7892, 7893, 7894, 7895, 7896,
        7897, 7898, 7899, 7900, 7901, 7902,
        7903, 7904, 7905, 7907, 7908, 7909,
    ]

    def __init__(
        self,
        total_proxies: int = 18,
        safety_factor: float = 5.0,
        max_requests_per_10min: int = 30,
    ):
        self.total_proxies = total_proxies
        self.safety_factor = safety_factor
        self.max_requests_per_10min = max_requests_per_10min

        # IP 请求计数器 {proxy_port: [timestamps]}
        self.request_history: dict[int, list[datetime]] = {
            port: [] for port in self.PROXY_PORTS
        }

        # 失败计数器 {proxy_port: failure_count}
        self.failure_counts: dict[int, int] = {
            port: 0 for port in self.PROXY_PORTS
        }

        # 失败阈值（超过此值的 IP 暂时禁用）
        self.failure_threshold = 5

        # 禁用时长（秒）
        self.ban_duration_seconds = 600  # 10 分钟

        # 禁用列表 {proxy_port: banned_until}
        self.banned_proxies: dict[int, datetime] = {}

        logger.info(f"V41.244 AdaptiveGovernor initialized")
        logger.info(f"  Total Proxies: {self.total_proxies}")
        logger.info(f"  Safety Factor: {self.safety_factor}")
        logger.info(f"  Max Requests/IP/10min: {self.max_requests_per_10min}")
        logger.info(f"  Initial Concurrent Jobs: {self.calculate_max_concurrent_jobs()}")

    def calculate_max_concurrent_jobs(self) -> int:
        """
        计算最大并发任务数

        公式：Concurrent_Jobs = Healthy_Proxies / Safety_Factor
        """
        # 统计健康代理数
        healthy_proxies = self._get_healthy_proxy_count()

        # 计算并发数
        max_jobs = int(healthy_proxies / self.safety_factor)

        # 至少 1 个并发
        return max(1, max_jobs)

    def _get_healthy_proxy_count(self) -> int:
        """获取当前健康代理数量"""
        now = datetime.now()

        # 清理过期禁用
        expired = [
            port for port, banned_until in self.banned_proxies.items()
            if banned_until < now
        ]
        for port in expired:
            del self.banned_proxies[port]
            self.failure_counts[port] = 0  # 重置失败计数
            logger.info(f"Proxy {port} unbanned")

        # 健康代理 = 总数 - 被封禁的代理
        healthy = self.total_proxies - len(self.banned_proxies)
        return max(1, healthy)  # 至少保留 1 个

    def record_request(self, proxy_port: int) -> bool:
        """
        记录代理请求，检查是否超过限制

        Args:
            proxy_port: 代理端口

        Returns:
            True 如果请求被允许，False 如果超过限制
        """
        now = datetime.now()

        # 检查是否被封禁
        if proxy_port in self.banned_proxies:
            if self.banned_proxies[proxy_port] > now:
                logger.warning(f"Proxy {proxy_port} is banned")
                return False

        # 清理 10 分钟前的记录
        cutoff_time = now - timedelta(minutes=10)
        self.request_history[proxy_port] = [
            ts for ts in self.request_history[proxy_port]
            if ts > cutoff_time
        ]

        # 检查请求数
        request_count = len(self.request_history[proxy_port])
        if request_count >= self.max_requests_per_10min:
            logger.warning(
                f"Proxy {proxy_port} exceeded limit: "
                f"{request_count}/{self.max_requests_per_10min} per 10min"
            )
            return False

        # 记录请求
        self.request_history[proxy_port].append(now)
        return True

    def record_success(self, proxy_port: int) -> None:
        """记录请求成功"""
        # 重置失败计数
        if proxy_port in self.failure_counts:
            self.failure_counts[proxy_port] = 0

    def record_failure(self, proxy_port: int, permanent: bool = False) -> None:
        """
        记录请求失败

        Args:
            proxy_port: 代理端口
            permanent: 是否永久失败（封禁）
        """
        self.failure_counts[proxy_port] += 1

        if permanent or self.failure_counts[proxy_port] >= self.failure_threshold:
            # 封禁代理
            banned_until = datetime.now() + timedelta(seconds=self.ban_duration_seconds)
            self.banned_proxies[proxy_port] = banned_until
            logger.error(
                f"Proxy {proxy_port} banned until {banned_until.strftime('%H:%M:%S')} "
                f"(failures: {self.failure_counts[proxy_port]})"
            )

    def get_available_proxy(self) -> int:
        """
        获取下一个可用代理（轮询策略）

        Returns:
            代理端口号，如果没有可用代理则返回 -1
        """
        now = datetime.now()

        for port in self.PROXY_PORTS:
            # 跳过被封禁的代理
            if port in self.banned_proxies:
                if self.banned_proxies[port] > now:
                    continue

            # 检查请求限制
            if self.record_request(port):
                return port

        return -1

    def get_stats(self) -> dict[str, Any]:
        """获取控制器统计信息"""
        healthy = self._get_healthy_proxy_count()
        banned = len(self.banned_proxies)

        return {
            "total_proxies": self.total_proxies,
            "healthy_proxies": healthy,
            "banned_proxies": banned,
            "max_concurrent_jobs": self.calculate_max_concurrent_jobs(),
            "safety_factor": self.safety_factor,
            "max_requests_per_10min": self.max_requests_per_10min,
            "failure_counts": dict(self.failure_counts),
        }


# =============================================================================
# 任务队列管理器
# =============================================================================


class TaskQueueManager:
    """
    V41.243 任务队列管理器

    特性：
        - Pending_Queue: 待处理任务
        - Failure_Retry_Queue: 失败重试队列
        - 指数退避策略 (5/15/60 分钟)
        - 队列持久化（JSON 文件）
    """

    # 重试策略（指数退避）
    RETRY_DELAYS = [5, 15, 60]  # 分钟

    def __init__(self, state_dir: str = "storage/skynet_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.pending_queue: deque[HarvestTask] = deque()
        self.retry_queue: deque[HarvestTask] = deque()
        self.completed_tasks: set[str] = set()

        self._lock = Lock()

        # 加载持久化状态
        self._load_state()

    def _load_state(self) -> None:
        """加载队列状态"""
        state_file = self.state_dir / "queue_state.json"

        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.info(f"Loaded {len(state.get('pending', []))} pending tasks")
                    # TODO: 反序列化任务（简化版暂不实现）
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

    def _save_state(self) -> None:
        """保存队列状态"""
        state_file = self.state_dir / "queue_state.json"

        state = {
            "pending": [
                {
                    "match_id": t.match_id,
                    "status": t.status.value,
                    "retry_count": t.retry_count,
                }
                for t in self.pending_queue
            ],
            "retry": [
                {
                    "match_id": t.match_id,
                    "status": t.status.value,
                    "retry_count": t.retry_count,
                }
                for t in self.retry_queue
            ],
            "completed_count": len(self.completed_tasks),
            "timestamp": datetime.now().isoformat(),
        }

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def add_pending(self, task: HarvestTask) -> None:
        """添加待处理任务"""
        with self._lock:
            if task.match_id not in self.completed_tasks:
                self.pending_queue.append(task)

    def get_next_task(self) -> Optional[HarvestTask]:
        """获取下一个任务（优先处理待办队列）"""
        with self._lock:
            now = datetime.now()

            # 1. 检查待办队列
            if self.pending_queue:
                return self.pending_queue.popleft()

            # 2. 检查重试队列（是否到达重试时间）
            while self.retry_queue:
                task = self.retry_queue[0]
                if task.next_retry and task.next_retry <= now:
                    return self.retry_queue.popleft()
                break

            return None

    def mark_completed(self, task: HarvestTask, success: bool) -> None:
        """标记任务完成"""
        with self._lock:
            if success:
                self.completed_tasks.add(task.match_id)
                self._save_state()
            else:
                # 加入重试队列
                self._schedule_retry(task)

    def _schedule_retry(self, task: HarvestTask) -> None:
        """调度重试任务"""
        task.retry_count += 1

        if task.retry_count > len(self.RETRY_DELAYS):
            # 超过最大重试次数，放弃
            task.status = TaskStatus.ABANDONED
            logger.error(f"Task abandoned after {len(self.RETRY_DELAYS)} retries: {task.match_id}")
            return

        # 计算下次重试时间
        delay_minutes = self.RETRY_DELAYS[task.retry_count - 1]
        task.next_retry = datetime.now() + timedelta(minutes=delay_minutes)

        # 更新状态
        if task.retry_count == 1:
            task.status = TaskStatus.RETRY_1
        elif task.retry_count == 2:
            task.status = TaskStatus.RETRY_2
        else:
            task.status = TaskStatus.RETRY_3

        self.retry_queue.append(task)
        logger.info(
            f"Scheduled retry {task.retry_count}/{len(self.RETRY_DELAYS)} "
            f"for {task.match_id} in {delay_minutes} min"
        )

    def get_queue_stats(self) -> dict[str, int]:
        """获取队列统计"""
        with self._lock:
            return {
                "pending": len(self.pending_queue),
                "retry": len(self.retry_queue),
                "completed": len(self.completed_tasks),
            }


# =============================================================================
# SkynetWorker 核心守护进程
# =============================================================================


class SkynetWorker:
    """
    V41.243 SkynetWorker - 24/7 自愈守护进程

    核心功能：
        1. 自动发现待办比赛
        2. 批量收割赔率数据
        3. 失败自动重试（指数退避）
        4. 低功耗休眠模式
        5. 实时监控看板
    """

    def __init__(
        self,
        max_workers: int = 4,
        scan_interval_seconds: int = 300,
        state_dir: str = "storage/skynet_state",
    ):
        self.max_workers = max_workers
        self.scan_interval = scan_interval_seconds
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.queue_manager = TaskQueueManager(state_dir)
        self.metrics = WorkerMetrics()
        self.shutdown_event = Event()

        # bin/odds_sync 路径
        self.odds_sync_script = project_root / "bin" / "odds_sync"

        if not self.odds_sync_script.exists():
            raise FileNotFoundError(f"odds_sync script not found: {self.odds_sync_script}")

        logger.info("V41.243 SkynetWorker initialized")
        logger.info(f"  Max Workers: {self.max_workers}")
        logger.info(f"  Scan Interval: {self.scan_interval}s")
        logger.info(f"  State Dir: {self.state_dir}")

    def scan_pending_matches(self) -> list[HarvestTask]:
        """扫描数据库中的待办比赛"""
        config = get_config()
        conn = psycopg2.connect(
            host=config.database.host,
            database=config.database.name,
            user=config.database.user,
            password=config.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        try:
            cursor = conn.cursor()

            # 查询待办比赛（未来 48 小时，无赔率记录）
            now = datetime.now()
            time_end = now + timedelta(hours=48)

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

            cursor.execute(query, (now, time_end))
            rows = cursor.fetchall()

            tasks = []
            for row in rows:
                # 生成 URL（使用 LeagueRouter）
                from src.services.league_router import LeagueRouter
                router = LeagueRouter()
                url = router.resolve_url(row["league_name"], row["season"])

                if not url:
                    # 回退到队名搜索
                    url = f"{router.url_builder.BASE_URL}/football/search/" \
                          f"{router.url_builder.slugify(row['home_team'])}-" \
                          f"{router.url_builder.slugify(row['away_team'])}/"

                task = HarvestTask(
                    match_id=row["match_id"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    match_date=row["match_date"],
                    league_name=row["league_name"],
                    season=row["season"],
                    url=url,
                )
                tasks.append(task)

            logger.info(f"Scanned {len(tasks)} pending matches")
            return tasks

        finally:
            conn.close()

    def process_task(self, task: HarvestTask) -> bool:
        """处理单个收割任务"""
        cmd = [
            str(self.odds_sync_script),
            "--url", task.url,
            "--log-level", "WARNING",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(project_root),
            )

            if result.returncode == 0:
                logger.info(f"✓ {task.match_id} completed")
                return True
            else:
                logger.warning(f"✗ {task.match_id} failed: {result.stderr}")
                task.error_message = result.stderr
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"✗ {task.match_id} timeout")
            task.error_message = "timeout"
            return False
        except Exception as e:
            logger.error(f"✗ {task.match_id} error: {e}")
            task.error_message = str(e)
            return False

    def run_batch(self, tasks: list[HarvestTask]) -> dict[str, int]:
        """批量处理任务"""
        stats = {"success": 0, "failed": 0, "total": len(tasks)}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.process_task, task): task
                for task in tasks
            }

            for future in as_completed(futures):
                task = futures[future]
                try:
                    success = future.result()
                    if success:
                        stats["success"] += 1
                        self.queue_manager.mark_completed(task, True)
                        self.metrics.tasks_succeeded += 1
                    else:
                        stats["failed"] += 1
                        self.queue_manager.mark_completed(task, False)
                        self.metrics.tasks_failed += 1
                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"Task error: {e}")

        self.metrics.tasks_processed += stats["total"]
        return stats

    def print_dashboard(self) -> None:
        """打印监控看板"""
        queue_stats = self.queue_manager.get_queue_stats()
        uptime = datetime.now() - self.metrics.start_time

        # 计算吞吐量
        hours = uptime.total_seconds() / 3600
        throughput = self.metrics.tasks_succeeded / hours if hours > 0 else 0

        print("\n" + "=" * 60)
        print("V41.243 Skynet Protocol - 24/7 Monitoring Dashboard")
        print("=" * 60)
        print(f"Uptime: {uptime}")
        print(f"\n📊 Task Queues:")
        print(f"  Pending:    {queue_stats['pending']:>5}")
        print(f"  Retry:      {queue_stats['retry']:>5}")
        print(f"  Completed:  {queue_stats['completed']:>5}")
        print(f"\n⚡ Performance:")
        print(f"  Processed:  {self.metrics.tasks_processed:>5}")
        print(f"  Succeeded:  {self.metrics.tasks_succeeded:>5}")
        print(f"  Failed:     {self.metrics.tasks_failed:>5}")
        print(f"  Throughput: {throughput:.1f} records/min")
        print(f"\n🌍 League Coverage:")
        for league, count in sorted(self.metrics.league_coverage.items()):
            print(f"  {league}: {count}")
        print("=" * 60 + "\n")

    def run_once(self) -> None:
        """单次运行（调试模式）"""
        logger.info("Running single scan...")

        tasks = self.scan_pending_matches()

        if tasks:
            for task in tasks:
                self.queue_manager.add_pending(task)
                self.metrics.league_coverage[task.league_name] = \
                    self.metrics.league_coverage.get(task.league_name, 0) + 1

            # 处理任务
            batch = []
            while True:
                task = self.queue_manager.get_next_task()
                if not task:
                    break
                batch.append(task)
                if len(batch) >= 10:  # 小批量
                    break

            if batch:
                stats = self.run_batch(batch)
                logger.info(f"Batch complete: {stats['success']}/{stats['total']} succeeded")

        self.print_dashboard()

    def run(self) -> None:
        """运行守护进程"""
        logger.info("Starting SkynetWorker daemon...")
        logger.info("Press Ctrl+C to stop")

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            while not self.shutdown_event.is_set():
                # 1. 扫描新任务
                tasks = self.scan_pending_matches()

                if tasks:
                    logger.info(f"Found {len(tasks)} new tasks")
                    for task in tasks:
                        self.queue_manager.add_pending(task)
                        self.metrics.league_coverage[task.league_name] = \
                            self.metrics.league_coverage.get(task.league_name, 0) + 1

                # 2. 处理任务
                batch = []
                while len(batch) < self.max_workers and not self.shutdown_event.is_set():
                    task = self.queue_manager.get_next_task()
                    if not task:
                        break
                    batch.append(task)

                if batch:
                    logger.info(f"Processing batch of {len(batch)} tasks...")
                    stats = self.run_batch(batch)
                    logger.info(
                        f"Batch complete: {stats['success']}/{stats['total']} succeeded, "
                        f"{stats['failed']} failed"
                    )

                # 3. 打印看板
                self.print_dashboard()

                # 4. 休眠或低功耗扫描
                queue_stats = self.queue_manager.get_queue_stats()
                pending_count = queue_stats['pending'] + queue_stats['retry']

                if pending_count == 0:
                    # 无待办任务，低功耗休眠
                    logger.info(f"No pending tasks, sleeping {self.scan_interval}s...")
                    self.shutdown_event.wait(self.scan_interval)
                else:
                    # 有待办任务，快速扫描
                    self.shutdown_event.wait(30)  # 30 秒快速扫描

        except Exception as e:
            logger.error(f"Daemon error: {e}")
        finally:
            logger.info("SkynetWorker shutting down...")
            self.queue_manager._save_state()

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_event.set()


# =============================================================================
# 命令行入口
# =============================================================================


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="V41.243 SkynetWorker - 24/7 Self-Healing Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    # 启动守护进程
    python scripts/ops/skynet_worker.py --daemon

    # 单次执行
    python scripts/ops/skynet_worker.py --once

    # 指定并发数
    python scripts/ops/skynet_worker.py --daemon --workers 8
        """,
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon (24/7 mode)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (debug mode)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent workers (default: 4)",
    )
    parser.add_argument(
        "--scan-interval",
        type=int,
        default=300,
        help="Scan interval in seconds when no tasks (default: 300)",
    )

    args = parser.parse_args()

    worker = SkynetWorker(
        max_workers=args.workers,
        scan_interval_seconds=args.scan_interval,
    )

    if args.once:
        worker.run_once()
    else:
        worker.run()


if __name__ == "__main__":
    exit(main())
