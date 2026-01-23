#!/usr/bin/env python3
"""V41.600 Global Harvest - 全量高纯度数据收割

12 线程并发收割，强制调用 extract_all_entities_final_odds_concurrent，
严格执行 V41.560 准入标准，支持断点续传。

Usage:
    python scripts/ops/v41_600_full_harvest.py [--workers 12] [--resume] [--dry-run]

Author: V41.600 Global Harvest Team
Date: 2026-01-21
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright

from src.api.collectors.odds_models import MultiSourceEntityData
from src.api.collectors.odds_production_extractor import OddsProductionExtractor
from src.config_unified import get_settings
from src.core.behavior_simulator import get_behavior_simulator
from src.core.fingerprint_manager import get_fingerprint_manager
from src.core.proxy_manager import ProxyConfig, ProxyManager, get_proxy_manager
from src.core.self_healing import get_self_healing_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Database Helper
# ============================================================================


class DatabaseHelper:
    """数据库辅助类"""

    def __init__(self):
        settings = get_settings()
        self.db_config = settings.database

    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.db_config.host,
            database=self.db_config.name,
            user=self.db_config.user,
            password=self.db_config.password.get_secret_value(),
            cursor_factory=RealDictCursor
        )

    def get_oddsportal_url(self, match_id: str) -> str | None:
        """获取 match_id 对应的 OddsPortal URL

        Args:
            match_id: 比赛 ID

        Returns:
            OddsPortal URL 或 None
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT oddsportal_url
                    FROM matches_mapping
                    WHERE fotmob_id = %s
                    LIMIT 1
                    """,
                    (match_id,)
                )
                row = cur.fetchone()
                return row["oddsportal_url"] if row else None

    def save_odds_data(self, data: MultiSourceEntityData) -> bool:
        """保存赔率数据到数据库

        Args:
            data: MultiSourceEntityData 对象

        Returns:
            是否保存成功
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 检查是否已存在
                    cur.execute(
                        """
                        SELECT id FROM metrics_multi_source_data
                        WHERE match_id = %s AND source_name = %s
                        """,
                        (data.match_id, data.source_name)
                    )
                    existing = cur.fetchone()

                    if existing:
                        # 更新
                        cur.execute(
                            """
                            UPDATE metrics_multi_source_data
                            SET init_h = %s, init_d = %s, init_a = %s,
                                opening_time_h = %s, opening_time_d = %s, opening_time_a = %s,
                                final_h = %s, final_d = %s, final_a = %s,
                                final_time = %s, integrity_score = %s,
                                is_valid = %s, validation_error = %s,
                                updated_at = NOW()
                            WHERE match_id = %s AND source_name = %s
                            """,
                            (
                                data.init_h, data.init_d, data.init_a,
                                data.opening_time_h, data.opening_time_d, data.opening_time_a,
                                data.final_h, data.final_d, data.final_a,
                                data.final_time, data.calculate_integrity_score(),
                                True, None,
                                data.match_id, data.source_name
                            )
                        )
                    else:
                        # 插入
                        cur.execute(
                            """
                            INSERT INTO metrics_multi_source_data
                            (match_id, source_name, init_h, init_d, init_a,
                             opening_time_h, opening_time_d, opening_time_a,
                             final_h, final_d, final_a, final_time,
                             integrity_score, is_valid, validation_error)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                data.match_id, data.source_name,
                                data.init_h, data.init_d, data.init_a,
                                data.opening_time_h, data.opening_time_d, data.opening_time_a,
                                data.final_h, data.final_d, data.final_a,
                                data.final_time, data.calculate_integrity_score(),
                                True, None
                            )
                        )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False


# ============================================================================
# Progress Dashboard
# ============================================================================


@dataclass
class HarvestMetrics:
    """收割指标"""
    start_time: float = field(default_factory=time.time)
    total_targets: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    total_bookmakers_captured: int = 0
    last_update: float = field(default_factory=time.time)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return (self.success / self.processed) * 100

    @property
    def avg_bookmakers(self) -> float:
        if self.success == 0:
            return 0.0
        return self.total_bookmakers_captured / self.success

    @property
    def eta_seconds(self) -> float:
        if self.processed == 0:
            return 0.0
        rate = self.processed / self.elapsed_seconds
        if rate == 0:
            return 0.0
        remaining = self.total_targets - self.processed
        return remaining / rate

    @property
    def eta_str(self) -> str:
        eta = self.eta_seconds
        if eta < 60:
            return f"{eta:.0f}s"
        elif eta < 3600:
            return f"{eta/60:.1f}m"
        else:
            hours = int(eta // 3600)
            minutes = int((eta % 3600) / 60)
            return f"{hours}h {minutes}m"


class ProgressDashboard:
    """V41.600: 实时进度看板"""

    def __init__(self, metrics: HarvestMetrics):
        self.metrics = metrics
        self._lock = threading.Lock()
        self._last_refresh = 0

    def update(self, **kwargs):
        """更新指标"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.metrics, key):
                    setattr(self.metrics, key, value)
            self.metrics.last_update = time.time()

    def refresh(self):
        """刷新看板显示"""
        now = time.time()
        # 限制刷新频率 (每 0.5 秒最多一次)
        if now - self._last_refresh < 0.5:
            return
        self._last_refresh = now

        m = self.metrics

        # 清屏并打印
        os.system("clear" if os.name == "posix" else "cls")

        print(f"\n{'='*70}")
        print(f"V41.600 GLOBAL HARVEST - PROGRESS DASHBOARD")
        print(f"{'='*70}")
        print(f"开始时间: {datetime.fromtimestamp(m.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"已运行: {timedelta(seconds=int(m.elapsed_seconds))}")
        print(f"预计剩余: {m.eta_str}")
        print(f"\n📊 进度:")
        print(f"  目标总数: {m.total_targets}")
        print(f"  已处理: {m.processed} ({m.processed/m.total_targets*100 if m.total_targets else 0:.1f}%)")
        print(f"  ✅ 成功: {m.success}")
        print(f"  ❌ 失败: {m.failed}")
        print(f"  ⏭️  跳过: {m.skipped}")
        print(f"\n📈 质量指标:")
        print(f"  成功率: {m.success_rate:.1f}%")
        print(f"  平均博彩公司数: {m.avg_bookmakers:.1f}")
        print(f"  总博彩公司捕获: {m.total_bookmakers_captured}")

        # 进度条
        if m.total_targets > 0:
            progress = m.processed / m.total_targets
            bar_length = 50
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\n  [{bar}] {progress*100:.1f}%")

        print(f"{'='*70}\n")

    def print_final_report(self):
        """打印最终报告"""
        m = self.metrics
        print(f"\n{'='*70}")
        print(f"V41.600 GLOBAL HARVEST - FINAL REPORT")
        print(f"{'='*70}")
        print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {timedelta(seconds=int(m.elapsed_seconds))}")
        print(f"\n📊 最终统计:")
        print(f"  目标总数: {m.total_targets}")
        print(f"  已处理: {m.processed}")
        print(f"  ✅ 成功: {m.success}")
        print(f"  ❌ 失败: {m.failed}")
        print(f"  ⏭️  跳过: {m.skipped}")
        print(f"\n📈 质量指标:")
        print(f"  成功率: {m.success_rate:.1f}%")
        print(f"  平均博彩公司数: {m.avg_bookmakers:.1f}")
        print(f"  总博彩公司捕获: {m.total_bookmakers_captured}")
        print(f"{'='*70}\n")


# ============================================================================
# Checkpoint Manager (断点续传)
# ============================================================================


class CheckpointManager:
    """V41.600: 断点续传管理器"""

    def __init__(self, checkpoint_file: str = "data/v41_600_checkpoint.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self.processed_match_ids: set[str] = set()
        self.load()

    def load(self):
        """加载检查点"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    data = json.load(f)
                    self.processed_match_ids = set(data.get("processed_match_ids", []))
                logger.info(f"加载检查点: {len(self.processed_match_ids)} 条记录")
            except Exception as e:
                logger.warning(f"加载检查点失败: {e}")

    def save(self):
        """保存检查点"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "processed_count": len(self.processed_match_ids),
                "processed_match_ids": list(self.processed_match_ids),
            }
            with open(self.checkpoint_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"保存检查点失败: {e}")

    def is_processed(self, match_id: str) -> bool:
        """检查是否已处理"""
        return match_id in self.processed_match_ids

    def mark_processed(self, match_id: str):
        """标记为已处理"""
        self.processed_match_ids.add(match_id)

    def mark_success(self, match_id: str):
        """标记为成功"""
        self.mark_processed(match_id)

    def mark_failed(self, match_id: str):
        """标记为失败（也记录为已处理，避免重复失败）"""
        self.mark_processed(match_id)

    def get_remaining(self, all_targets: list) -> list:
        """获取未处理的目标"""
        return [t for t in all_targets if t.get("match_id") not in self.processed_match_ids]


# ============================================================================
# Harvest Worker
# ============================================================================


class HarvestWorker:
    """V41.600: 收割工作线程"""

    def __init__(
        self,
        worker_id: int,
        proxy_manager: ProxyManager,
        fingerprint_manager,
        behavior_simulator,
        db_helper: DatabaseHelper,
        checkpoint: CheckpointManager,
        dry_run: bool = False,
    ):
        self.worker_id = worker_id
        self.proxy_manager = proxy_manager
        self.fingerprint_manager = fingerprint_manager
        self.behavior_simulator = behavior_simulator
        self.db_helper = db_helper
        self.checkpoint = checkpoint
        self.dry_run = dry_run

        # 创建 extractor 实例
        self.extractor = OddsProductionExtractor()

    async def harvest_match(self, target: dict) -> dict:
        """收割单场比赛

        Args:
            target: 目标比赛字典

        Returns:
            收割结果字典
        """
        match_id = target["match_id"]

        # 检查是否已处理
        if self.checkpoint.is_processed(match_id):
            return {"match_id": match_id, "status": "skipped", "reason": "already_processed"}

        # 获取 OddsPortal URL
        url = self.db_helper.get_oddsportal_url(match_id)
        if not url:
            return {
                "match_id": match_id,
                "status": "failed",
                "reason": "no_oddsportal_url"
            }

        logger.info(f"[Worker {self.worker_id}] 收割 {match_id}: {url}")

        try:
            # 调用 extractor
            results = await self.extractor.extract_all_entities_final_odds_concurrent(
                url=url,
                match_id=match_id
            )

            if not results:
                return {
                    "match_id": match_id,
                    "status": "failed",
                    "reason": "no_data_extracted"
                }

            # V41.560 硬化验证
            valid_results = []
            for data in results:
                is_valid, error_msg = data.validate_v41_560_hardened()
                if is_valid:
                    valid_results.append(data)
                else:
                    logger.warning(f"[Worker {self.worker_id}] {match_id} {data.source_name} 未通过硬化验证: {error_msg}")

            if not valid_results:
                return {
                    "match_id": match_id,
                    "status": "failed",
                    "reason": "hardened_validation_failed"
                }

            # 保存数据
            saved_count = 0
            if not self.dry_run:
                for data in valid_results:
                    if self.db_helper.save_odds_data(data):
                        saved_count += 1

            self.checkpoint.mark_success(match_id)

            return {
                "match_id": match_id,
                "status": "success",
                "bookmakers_captured": len(valid_results),
                "bookmakers_saved": saved_count,
                "sources": [d.source_name for d in valid_results],
            }

        except Exception as e:
            logger.error(f"[Worker {self.worker_id}] {match_id} 收割失败: {e}")
            self.checkpoint.mark_failed(match_id)
            return {
                "match_id": match_id,
                "status": "failed",
                "reason": f"exception: {str(e)[:100]}"
            }


# ============================================================================
# Main Harvest Orchestrator
# ============================================================================


class GlobalHarvestOrchestrator:
    """V41.600: 全局收割编排器"""

    def __init__(
        self,
        targets_file: str = "data/v41_600_targets.json",
        workers: int = 12,
        proxies_file: str = "config/stealth/proxy_pool.txt",
        resume: bool = False,
        dry_run: bool = False,
    ):
        """初始化编排器

        Args:
            targets_file: 目标列表文件
            workers: 工作线程数
            proxies_file: 代理池文件
            resume: 是否断点续传
            dry_run: 是否干跑模式
        """
        self.targets_file = targets_file
        self.workers = workers
        self.proxies_file = proxies_file
        self.resume = resume
        self.dry_run = dry_run

        # 加载目标
        self.targets = self.load_targets()

        # 初始化指标
        self.metrics = HarvestMetrics(total_targets=len(self.targets))

        # 进度看板
        self.dashboard = ProgressDashboard(self.metrics)

        # 检查点管理器
        self.checkpoint = CheckpointManager()

        # 如果不续传，清空检查点
        if not resume:
            self.checkpoint.processed_match_ids.clear()
            self.checkpoint.save()

        # 过滤已处理的目标
        if resume:
            self.targets = self.checkpoint.get_remaining(self.targets)
            self.metrics.total_targets = len(self.targets)
            logger.info(f"断点续传: 剩余 {len(self.targets)} 个目标")

        # 初始化隐形模块
        self.proxy_manager = get_proxy_manager(proxies_file=proxies_file)
        self.fingerprint_manager = get_fingerprint_manager()
        self.behavior_simulator = get_behavior_simulator()
        self.self_healing_engine = get_self_healing_engine(
            proxy_manager=self.proxy_manager
        )

        # 数据库辅助
        self.db_helper = DatabaseHelper()

        logger.info(f"\n{'='*70}")
        logger.info("V41.600 GLOBAL HARVEST ORCHESTRATOR")
        logger.info(f"{'='*70}")
        logger.info(f"目标数量: {len(self.targets)}")
        logger.info(f"工作线程: {workers}")
        logger.info(f"代理数量: {self.proxy_manager.get_stats()['total_proxies']}")
        logger.info(f"断点续传: {'启用' if resume else '禁用'}")
        logger.info(f"干跑模式: {'启用' if dry_run else '禁用'}")
        logger.info(f"{'='*70}\n")

    def load_targets(self) -> list:
        """加载目标列表"""
        targets_path = Path(self.targets_file)
        if not targets_path.exists():
            logger.error(f"目标文件不存在: {self.targets_file}")
            return []

        with open(targets_path) as f:
            data = json.load(f)
            return data.get("targets", [])

    async def run(self):
        """运行收割任务"""
        logger.info("开始收割...")

        # 创建工作线程
        workers_list = [
            HarvestWorker(
                worker_id=i,
                proxy_manager=self.proxy_manager,
                fingerprint_manager=self.fingerprint_manager,
                behavior_simulator=self.behavior_simulator,
                db_helper=self.db_helper,
                checkpoint=self.checkpoint,
                dry_run=self.dry_run,
            )
            for i in range(self.workers)
        ]

        # 分配任务给工作线程
        for i, target in enumerate(self.targets):
            worker_id = i % self.workers
            worker = workers_list[worker_id]

            # 执行收割
            result = await worker.harvest_match(target)

            # 更新指标
            self.metrics.processed += 1
            if result["status"] == "success":
                self.metrics.success += 1
                self.metrics.total_bookmakers_captured += result.get("bookmakers_captured", 0)
            elif result["status"] == "failed":
                self.metrics.failed += 1
            else:
                self.metrics.skipped += 1

            # 每 10 个任务保存一次检查点
            if i % 10 == 0:
                self.checkpoint.save()

            # 刷新看板
            self.dashboard.refresh()

        # 最终保存
        self.checkpoint.save()

        # 打印最终报告
        self.dashboard.print_final_report()


async def main():
    """主函数"""
    parser = ArgumentParser(description="V41.600 Global Harvest")
    parser.add_argument(
        "--targets",
        type=str,
        default="data/v41_600_targets.json",
        help="目标列表文件路径"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=12,
        help="工作线程数 (默认: 12)"
    )
    parser.add_argument(
        "--proxies",
        type=str,
        default="config/stealth/proxy_pool.txt",
        help="代理池文件路径"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="断点续传"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式（不保存数据）"
    )

    args = parser.parse_args()

    # 创建编排器
    orchestrator = GlobalHarvestOrchestrator(
        targets_file=args.targets,
        workers=args.workers,
        proxies_file=args.proxies,
        resume=args.resume,
        dry_run=args.dry_run,
    )

    # 运行收割
    await orchestrator.run()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
