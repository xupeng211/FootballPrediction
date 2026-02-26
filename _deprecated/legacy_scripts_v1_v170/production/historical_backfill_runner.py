#!/usr/bin/env python3
"""
[Genesis.HistoricalBackfill] historical_backfill_runner.py
=============================================================

近 30 天已完赛历史数据回填脚本。

功能:
1. 目标锁定 - 筛选过去 30 天内已完赛但缺少 L2 数据的比赛
2. 深度收割 - L2 抓取 + 黄金特征提取 + 回测预测
3. 闭环验证 - 数据完整性检查和结果摘要

Usage:
    python scripts/production/historical_backfill_runner.py

Author: Genesis.HistoricalBackfill Team
Version: V1.0
Date: 2026-01-31
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

# 添加项目根目录到 Python 路径
# 获取项目根目录 (scripts/production -> scripts -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# 配置
# ============================================================================

# 并发配置
MAX_WORKERS = 5
BATCH_SIZE = 50  # 每 50 场打印一次进度

# 时间范围（天）
LOOKBACK_DAYS = 30

# 日志配置
LOG_DIR = "logs/ops"
LOG_FILE = f"{LOG_DIR}/historical_backfill.log"

# ============================================================================
# 日志设置
# ============================================================================


def setup_logging() -> logging.Logger:
    """配置日志系统"""
    logger = logging.getLogger("HistoricalBackfill")
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    # 文件处理器
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class MatchTarget:
    """回填目标比赛"""
    match_id: str
    league_name: str
    season: str
    home_team: str
    away_team: str
    match_date: datetime
    is_finished: bool

    def __hash__(self) -> int:
        return hash(self.match_id)


@dataclass
class BackfillResult:
    """回填结果"""
    match_id: str
    success: bool
    l2_fetched: bool = False
    features_extracted: bool = False
    prediction_made: bool = False
    error_message: str = ""
    processing_time_ms: float = 0


@dataclass
class BackfillStats:
    """回填统计"""
    total_targets: int = 0
    processed_targets: int = 0
    successful_l2: int = 0
    successful_features: int = 0
    successful_predictions: int = 0
    failed_targets: int = 0
    skipped_targets: int = 0
    start_time: float = field(default_factory=time.time)

    def get_elapsed(self) -> float:
        return time.time() - self.start_time


# ============================================================================
# 数据库连接
# ============================================================================


def get_db_connection():
    """获取数据库连接"""
    from src.config_unified import get_settings

    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


# ============================================================================
# 目标锁定
# ============================================================================


def find_backfill_targets(lookback_days: int = 30) -> list[MatchTarget]:
    """
    筛选需要回填的比赛

    条件:
    1. match_date 在过去 N 天内
    2. is_finished = true (已完赛)
    3. l2_raw_json 为空

    Returns:
        MatchTarget 列表
    """
    logger.info(f"[Target] 正在筛选过去 {lookback_days} 天内已完赛但缺少 L2 数据的比赛...")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                match_id,
                league_name,
                season,
                home_team,
                away_team,
                match_date,
                is_finished
            FROM matches
            WHERE match_date >= NOW() - INTERVAL '%s days'
              AND match_date <= NOW()
              AND is_finished = true
              AND (l2_raw_json IS NULL OR l2_raw_json::text = '')
            ORDER BY match_date DESC
        """, (lookback_days,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        targets = []
        for row in rows:
            targets.append(MatchTarget(
                match_id=row["match_id"],
                league_name=row["league_name"],
                season=row["season"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                match_date=row["match_date"],
                is_finished=row["is_finished"],
            ))

        logger.info(f"[Target] 发现 {len(targets)} 场比赛需要回填 L2 数据")
        return targets

    except Exception as e:
        logger.error(f"[Target] 筛选失败: {e}")
        return []


# ============================================================================
# 深度收割流水线
# ============================================================================


class HistoricalBackfillPipeline:
    """历史数据回填流水线"""

    def __init__(self):
        self.stats = BackfillStats()
        self.stats_lock = Lock()
        self.golden_extractor = None
        self.model_dispatcher = None

    def initialize_components(self):
        """初始化组件"""
        try:
            from src.processors.v41_380_golden_extractor import GoldenFeatureExtractor
            self.golden_extractor = GoldenFeatureExtractor()
            logger.info("[Pipeline] Golden Extractor initialized")

            from src.ml.inference.model_dispatcher import ModelDispatcher
            self.model_dispatcher = ModelDispatcher()
            logger.info("[Pipeline] Model Dispatcher initialized")

        except Exception as e:
            logger.error(f"[Pipeline] 组件初始化失败: {e}")
            raise

    def check_has_l2(self, match_id: str) -> bool:
        """检查是否已有 L2 数据"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT l2_raw_json IS NOT NULL AND l2_raw_json::text != '' AS has_data
                FROM matches
                WHERE match_id = %s
            """, (match_id,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return result and result.get("has_data", False)

        except Exception as e:
            logger.debug(f"[Pipeline] 检查 L2 状态失败: {e}")
            return False

    def fetch_l2_data(self, match_id: str) -> dict | None:
        """获取 L2 数据"""
        try:
            from src.api.collectors.fotmob_core import FotMobCoreCollector

            collector = FotMobCoreCollector()
            result = collector.fetch_match_details(int(match_id))

            if result.get("success") and result.get("data"):
                return result["data"]

            return None

        except Exception as e:
            logger.debug(f"[Pipeline] 获取 L2 数据失败 (match_id={match_id}): {e}")
            return None

    def save_l2_to_db(self, match_id: str, l2_data: dict) -> bool:
        """保存 L2 数据到数据库"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE matches
                SET l2_raw_json = %s,
                    collected_at = NOW()
                WHERE match_id = %s
            """, (psycopg2.extras.Json(l2_data), match_id))

            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"[Pipeline] 保存 L2 数据失败 (match_id={match_id}): {e}")
            return False

    def extract_features(self, l2_data: dict, match_date: datetime) -> dict:
        """提取特征"""
        if not self.golden_extractor:
            self.initialize_components()

        try:
            features = self.golden_extractor.extract_all_golden_features(l2_data, match_date)
            return features
        except Exception as e:
            logger.debug(f"[Pipeline] 特征提取失败: {e}")
            return {}

    def make_prediction(self, match_data: dict) -> dict | None:
        """执行预测"""
        if not self.model_dispatcher:
            self.initialize_components()

        try:
            result = self.model_dispatcher.predict(match_data)
            return result
        except Exception as e:
            logger.debug(f"[Pipeline] 预测失败: {e}")
            return None

    def process_single_match(self, target: MatchTarget) -> BackfillResult:
        """处理单场比赛"""
        start_time = time.time()
        result = BackfillResult(match_id=target.match_id, success=False)

        logger.info(f"[DEBUG] 🔍 回填 {target.match_id} | {target.home_team} vs {target.away_team}")

        try:
            # 1. 检查是否已有 L2 数据
            if self.check_has_l2(target.match_id):
                result.error_message = "Already has L2 data (skip)"
                with self.stats_lock:
                    self.stats.skipped_targets += 1
                logger.info(f"[DEBUG]   └─ 已跳过 (有 L2 数据)")
                return result

            # 2. 获取 L2 数据
            logger.info(f"[DEBUG]   ├─ 获取 L2 数据...")
            l2_data = self.fetch_l2_data(target.match_id)
            if not l2_data:
                result.error_message = "Failed to fetch L2 data"
                with self.stats_lock:
                    self.stats.failed_targets += 1
                logger.warning(f"[DEBUG]   └─ L2 数据为空 ⚠️")
                return result

            # 3. 保存 L2 数据到数据库
            if not self.save_l2_to_db(target.match_id, l2_data):
                result.error_message = "Failed to save L2 data"
                with self.stats_lock:
                    self.stats.failed_targets += 1
                return result

            result.l2_fetched = True
            logger.info(f"[DEBUG]   ├─ L2 数据已保存")

            # 4. 提取特征
            logger.info(f"[DEBUG]   ├─ 提取特征...")
            features = self.extract_features(l2_data, target.match_date)
            if features:
                result.features_extracted = True
                with self.stats_lock:
                    self.stats.successful_features += 1
                logger.info(f"[DEBUG]   ├─ 特征已提取 ({len(features)} 维)")
            else:
                logger.info(f"[DEBUG]   ├─ 特征提取失败 (继续)")

            # 5. 执行预测
            logger.info(f"[DEBUG]   ├─ 执行预测...")
            match_data = {
                "match_id": target.match_id,
                "league_name": target.league_name,
                "home_team": target.home_team,
                "away_team": target.away_team,
                "season": target.season,
                **features,
            }

            prediction = self.make_prediction(match_data)
            if prediction:
                result.prediction_made = True
                with self.stats_lock:
                    self.stats.successful_predictions += 1

                pred_result = prediction.get("prediction", "Unknown")
                confidence = prediction.get("confidence", 0)
                logger.info(f"[DEBUG]   └─ 预测完成: {pred_result} (conf={confidence:.2f})")
            else:
                logger.info(f"[DEBUG]   └─ 预测失败 (继续)")

            result.success = True
            with self.stats_lock:
                self.stats.successful_l2 += 1

        except Exception as e:
            result.error_message = str(e)
            logger.debug(f"[Pipeline] 处理失败: {e}")

            with self.stats_lock:
                self.stats.failed_targets += 1

        result.processing_time_ms = (time.time() - start_time) * 1000

        with self.stats_lock:
            self.stats.processed_targets += 1

        return result

    def process_batch(self, targets: list[MatchTarget]) -> BackfillStats:
        """批量处理"""
        self.stats = BackfillStats()
        self.stats.total_targets = len(targets)

        logger.info(f"[Pipeline] 开始回填 {len(targets)} 场比赛 (并发={MAX_WORKERS})...")

        self.initialize_components()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self.process_single_match, target): target
                for target in targets
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1

                if completed % BATCH_SIZE == 0:
                    logger.info(
                        f"[Pipeline] 进度: {completed}/{len(targets)} ({completed * 100 // len(targets)}%) | "
                        f"L2成功: {self.stats.successful_l2} | "
                        f"预测成功: {self.stats.successful_predictions} | "
                        f"失败: {self.stats.failed_targets} | "
                        f"跳过: {self.stats.skipped_targets}"
                    )

        # 最终统计
        elapsed = self.stats.get_elapsed()
        logger.info(f"[Pipeline] 回填完成!")
        logger.info(f"  总场次: {self.stats.total_targets}")
        logger.info(f"  已处理: {self.stats.processed_targets}")
        logger.info(f"  L2成功: {self.stats.successful_l2}")
        logger.info(f"  特征提取: {self.stats.successful_features}")
        logger.info(f"  预测成功: {self.stats.successful_predictions}")
        logger.info(f"  失败: {self.stats.failed_targets}")
        logger.info(f"  跳过: {self.stats.skipped_targets}")
        logger.info(f"  耗时: {elapsed:.1f}秒")

        return self.stats


# ============================================================================
# 闭环验证
# ============================================================================


def final_audit(stats: BackfillStats):
    """最终审计"""
    logger.info("\n" + "=" * 60)
    logger.info("[Audit] 闭环验证")
    logger.info("-" * 40)

    # 检查数据库中的 L2 数据完整性
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 统计过去 30 天内的 L2 数据完整性
        cursor.execute("""
            SELECT
                COUNT(*) as total_matches,
                COUNT(DISTINCT CASE WHEN l2_raw_json IS NOT NULL AND l2_raw_json::text != '' THEN match_id END) as with_l2
            FROM matches
            WHERE match_date >= NOW() - INTERVAL '30 days'
              AND is_finished = true
        """)

        row = cursor.fetchone()
        total = row["total_matches"]
        with_l2 = row["with_l2"]
        integrity_pct = (with_l2 / total * 100) if total > 0 else 0

        logger.info(f"  过去 30 天已完赛比赛: {total} 场")
        logger.info(f"  有 L2 数据: {with_l2} 场")
        logger.info(f"  L2 完整性: {integrity_pct:.1f}%")

        # 随机抽取一场已完赛比赛展示预测结果
        cursor.execute("""
            SELECT
                m.match_id,
                m.home_team,
                m.away_team,
                m.home_score,
                m.away_score,
                m.l2_raw_json IS NOT NULL as has_l2
            FROM matches m
            WHERE m.match_date >= NOW() - INTERVAL '30 days'
              AND m.is_finished = true
              AND m.l2_raw_json IS NOT NULL
              AND m.l2_raw_json::text != ''
            ORDER BY RANDOM()
            LIMIT 1
        """)

        sample = cursor.fetchone()
        if sample:
            logger.info(f"\n  📊 随机样本展示:")
            logger.info(f"     比赛: {sample['home_team']} {sample['home_score']} - {sample['away_score']} {sample['away_team']}")
            logger.info(f"     Match ID: {sample['match_id']}")
            logger.info(f"     L2 数据: {'✅ 有' if sample['has_l2'] else '❌ 无'}")

        cursor.close()
        conn.close()

        logger.info("=" * 60)
        logger.info(f"[Audit] L2 Data integrity: {integrity_pct:.1f}%")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"[Audit] 审计失败: {e}")


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主函数"""
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║     [Genesis.HistoricalBackfill] Historical Data Backfill   ║
    ║                                                            ║
    ║  1. 目标锁定 - 筛选过去 30 天已完赛但缺少 L2 数据的比赛     ║
    ║  2. 深度收割 - L2 抓取 + 黄金特征 + 回测预测                   ║
    ║  3. 闭环验证 - 数据完整性检查和结果摘要                       ║
    ╚════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("=" * 60)
    logger.info("[Genesis.HistoricalBackfill] 脚本启动")
    logger.info("=" * 60)
    logger.info(f"回溯天数: {LOOKBACK_DAYS}")
    logger.info(f"并发度: {MAX_WORKERS}")
    logger.info("-" * 40)

    total_start = time.time()

    try:
        # Step 1: 目标锁定
        logger.info("\n[Step 1] 目标锁定...")
        logger.info("-" * 40)
        targets = find_backfill_targets(LOOKBACK_DAYS)

        if not targets:
            logger.warning("[Step 1] 未发现需要回填的比赛，脚本退出")
            return

        # Step 2: 深度收割
        logger.info("\n[Step 2] 深度收割...")
        logger.info("-" * 40)

        pipeline = HistoricalBackfillPipeline()
        stats = pipeline.process_batch(targets)

        # Step 3: 闭环验证
        final_audit(stats)

        # 最终报告
        total_elapsed = time.time() - total_start
        l2_integrity = stats.successful_l2 / max(stats.processed_targets, 1) * 100

        logger.info("\n" + "=" * 60)
        logger.info("[Genesis.HistoricalBackfill] 回填完成")
        logger.info("=" * 60)
        logger.info(f"总耗时: {total_elapsed:.1f}秒")
        logger.info(f"处理结果: {stats.processed_targets} 场")
        logger.info(f"L2 完整性: {l2_integrity:.1f}%")
        logger.info("=" * 60)

        print(f"\n[Genesis.HistoricalBackfill] BACKFILL COMPLETE. {stats.processed_targets} matches processed. L2 Data integrity: {l2_integrity:.1f}%. Ready for Live prediction.")

    except KeyboardInterrupt:
        logger.warning("\n[Genesis.HistoricalBackfill] 用户中断执行")
    except Exception as e:
        logger.error(f"\n[Genesis.HistoricalBackfill] 执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
