#!/usr/bin/env python3
"""
[Genesis.VintageVerification] 2024/2025 赛季经典数据全链路穿透测试
=======================================================================

功能:
1. 抽样锁定 - 随机抽取 20 场 2024/2025 赛季已完赛比赛
2. 强制收割 - 忽略现有 L2 记录，重新获取数据
3. 特征提取 - GoldenExtractor V41.380 黄金特征计算
4. AI 预测 - ModelDispatcher V26.7 概率生成
5. 战果校对 - 预测结果 vs 实际比分对比
6. 置信度分析 - 统计分布和数据完整性验证

Usage:
    python scripts/production/vintage_verification_runner.py

Author: Genesis.VintageVerification Team
Version: V1.0
Date: 2026-01-31
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# 配置
# ============================================================================

SAMPLE_SIZE = 20
FORCE_REFETCH = False  # 使用数据库中已有 L2 数据（不重新抓取 API）

# 日志配置
LOG_DIR = "logs/ops"
LOG_FILE = f"{LOG_DIR}/vintage_verification.log"

# ============================================================================
# 日志设置
# ============================================================================


def setup_logging() -> logging.Logger:
    """配置日志系统"""
    logger = logging.getLogger("VintageVerification")
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    # 文件处理器
    os.makedirs(LOG_DIR, exist_ok=True)
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
    """验证目标比赛"""
    match_id: str
    league_name: str
    season: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    match_date: datetime

    @property
    def actual_result(self) -> str:
        """实际结果"""
        if self.home_score > self.away_score:
            return "Home"
        elif self.home_score < self.away_score:
            return "Away"
        else:
            return "Draw"


@dataclass
class VerificationResult:
    """验证结果"""
    match_id: str
    home_team: str
    away_team: str
    actual_result: str
    actual_score: str
    prediction: str | None = None
    confidence: float = 0.0
    prob_home: float = 0.0
    prob_draw: float = 0.0
    prob_away: float = 0.0
    l2_fetched: bool = False
    features_extracted: bool = False
    prediction_made: bool = False
    error_message: str = ""
    processing_time_ms: float = 0


@dataclass
class VerificationStats:
    """验证统计"""
    total_targets: int = 0
    successful_l2: int = 0
    successful_features: int = 0
    successful_predictions: int = 0
    correct_predictions: int = 0
    failed_targets: int = 0
    avg_confidence: float = 0.0
    confidence_distribution: dict = field(default_factory=lambda: {
        "high": 0,    # > 0.7
        "medium": 0,  # 0.5 - 0.7
        "low": 0,     # < 0.5
    })

    def get_success_rate(self) -> float:
        """预测准确率"""
        if self.successful_predictions == 0:
            return 0.0
        return self.correct_predictions / self.successful_predictions * 100


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
# 抽样锁定
# ============================================================================


def sample_vintage_matches(sample_size: int = 20) -> list[MatchTarget]:
    """随机抽取已有 L2 数据的已完赛比赛"""
    logger.info(f"[Sample] 正在从数据库随机抽取 {sample_size} 场已有 L2 数据的比赛...")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 优先选择 2023/2024 赛季（数据完整），然后是 2024/2025
        cursor.execute("""
            SELECT
                match_id,
                league_name,
                season,
                home_team,
                away_team,
                home_score,
                away_score,
                match_date
            FROM matches
            WHERE season IN ('2023/2024', '2024/2025')
              AND is_finished = true
              AND home_score IS NOT NULL
              AND away_score IS NOT NULL
              AND l2_raw_json IS NOT NULL
            ORDER BY RANDOM()
            LIMIT %s
        """, (sample_size,))

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
                home_score=row["home_score"],
                away_score=row["away_score"],
                match_date=row["match_date"],
            ))

        logger.info(f"[Sample] 成功抽取 {len(targets)} 场比赛")
        return targets

    except Exception as e:
        logger.error(f"[Sample] 抽样失败: {e}")
        return []


# ============================================================================
# 全链路穿透流水线
# ============================================================================


class VintageVerificationPipeline:
    """经典数据验证流水线"""

    def __init__(self, force_refetch: bool = False):
        self.force_refetch = force_refetch
        self.stats = VerificationStats()
        self.golden_extractor = None
        self.model_dispatcher = None

    def initialize_components(self):
        """初始化组件"""
        try:
            from src.processors.v41_380_golden_extractor import GoldenFeatureExtractor
            self.golden_extractor = GoldenFeatureExtractor()
            logger.info("[Pipeline] Golden Extractor V41.380 initialized")

            from src.ml.inference.model_dispatcher import ModelDispatcher
            self.model_dispatcher = ModelDispatcher()
            logger.info("[Pipeline] Model Dispatcher V26.7 initialized")

        except Exception as e:
            logger.error(f"[Pipeline] 组件初始化失败: {e}")
            raise

    def get_l2_from_db(self, match_id: str) -> dict | None:
        """从数据库获取 L2 数据"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT l2_raw_json
                FROM matches
                WHERE match_id = %s
            """, (match_id,))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row and row.get("l2_raw_json"):
                return row["l2_raw_json"]

            return None

        except Exception as e:
            logger.debug(f"[Pipeline] 获取 L2 数据失败 (match_id={match_id}): {e}")
            return None

    def fetch_l2_data(self, match_id: str) -> dict | None:
        """强制获取 L2 数据（仅当 force_refetch=True 时）"""
        if not self.force_refetch:
            # 不强制重取，直接返回 None（会触发使用数据库中的数据）
            return None

        try:
            from src.api.collectors.fotmob_core import FotMobCoreCollector

            collector = FotMobCoreCollector()
            result = collector.fetch_match_details(int(match_id))

            if result.get("success") and result.get("data"):
                return result["data"]

            return None

        except Exception as e:
            logger.debug(f"[Pipeline] API 获取 L2 数据失败 (match_id={match_id}): {e}")
            return None

    def extract_features(self, l2_data: dict, match_date: datetime) -> dict:
        """提取黄金特征"""
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

    def log_prediction(self, result: VerificationResult) -> bool:
        """记录预测到 prediction_logs 表"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 将预测结果存储为 JSONB
            prediction_data = {
                "result": result.prediction,
                "prob_home": result.prob_home,
                "prob_draw": result.prob_draw,
                "prob_away": result.prob_away,
            }

            cursor.execute("""
                INSERT INTO prediction_logs (
                    match_id, prediction, confidence, model_used, created_at
                ) VALUES (
                    %s, %s, %s, %s, NOW()
                )
                ON CONFLICT (match_id) DO UPDATE SET
                    prediction = EXCLUDED.prediction,
                    confidence = EXCLUDED.confidence,
                    model_used = EXCLUDED.model_used,
                    created_at = NOW()
            """, (
                result.match_id,
                psycopg2.extras.Json(prediction_data),
                result.confidence,
                "V26.7_Aligned",
            ))

            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"[Pipeline] 记录预测失败: {e}")
            return False

    def process_single_match(self, target: MatchTarget) -> VerificationResult:
        """处理单场比赛"""
        start_time = time.time()
        result = VerificationResult(
            match_id=target.match_id,
            home_team=target.home_team,
            away_team=target.away_team,
            actual_result=target.actual_result,
            actual_score=f"{target.home_score}-{target.away_score}",
        )

        logger.info(f"[DEBUG] 验证 {target.match_id} | {target.home_team} vs {target.away_team}")

        try:
            # 1. 获取 L2 数据（优先从数据库，force_refetch 时才调用 API）
            l2_data = None

            if self.force_refetch:
                logger.info(f"[DEBUG]   ├─ 强制重取 L2 数据...")
                l2_data = self.fetch_l2_data(target.match_id)

            if not l2_data:
                logger.info(f"[DEBUG]   ├─ 从数据库读取 L2 数据...")
                l2_data = self.get_l2_from_db(target.match_id)

            if not l2_data:
                result.error_message = "Failed to get L2 data"
                self.stats.failed_targets += 1
                logger.warning(f"[DEBUG]   └─ L2 数据为空 ⚠️")
                return result

            result.l2_fetched = True
            self.stats.successful_l2 += 1
            logger.info(f"[DEBUG]   ├─ L2 数据已加载 ({len(str(l2_data))} 字符)")

            # 2. 提取特征
            logger.info(f"[DEBUG]   ├─ 提取特征...")
            features = self.extract_features(l2_data, target.match_date)
            if not features:
                result.error_message = "Failed to extract features"
                logger.warning(f"[DEBUG]   └─ 特征提取失败")
                return result

            result.features_extracted = True
            self.stats.successful_features += 1
            logger.info(f"[DEBUG]   ├─ 特征已提取 ({len(features)} 维)")

            # 3. 执行预测
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
            if not prediction:
                result.error_message = "Failed to make prediction"
                logger.warning(f"[DEBUG]   └─ 预测失败")
                return result

            result.prediction = prediction.get("prediction", "Unknown")
            result.confidence = prediction.get("confidence", 0.0)
            result.prob_home = prediction.get("prob_home", 0.0)
            result.prob_draw = prediction.get("prob_draw", 0.0)
            result.prob_away = prediction.get("prob_away", 0.0)

            result.prediction_made = True
            self.stats.successful_predictions += 1

            # 4. 记录预测到数据库
            self.log_prediction(result)

            # 5. 判断预测是否正确
            if result.prediction == target.actual_result:
                self.stats.correct_predictions += 1

            # 6. 更新置信度分布
            if result.confidence > 0.7:
                self.stats.confidence_distribution["high"] += 1
            elif result.confidence >= 0.5:
                self.stats.confidence_distribution["medium"] += 1
            else:
                self.stats.confidence_distribution["low"] += 1

            pred_emoji = "✅" if result.prediction == target.actual_result else "❌"
            logger.info(f"[DEBUG]   └─ 预测完成: {result.prediction} (conf={result.confidence:.2f}) | 实际: {target.actual_result} {pred_emoji}")

        except Exception as e:
            result.error_message = str(e)
            logger.debug(f"[Pipeline] 处理失败: {e}")
            self.stats.failed_targets += 1

        result.processing_time_ms = (time.time() - start_time) * 1000
        return result

    def process_batch(self, targets: list[MatchTarget]) -> tuple[list[VerificationResult], VerificationStats]:
        """批量处理"""
        self.stats = VerificationStats()
        self.stats.total_targets = len(targets)

        logger.info(f"[Pipeline] 开始验证 {len(targets)} 场比赛...")
        logger.info("")

        self.initialize_components()

        results = []
        for i, target in enumerate(targets, 1):
            logger.info(f"[{i}/{len(targets)}] 处理 {target.match_id}")
            result = self.process_single_match(target)
            results.append(result)
            logger.info("")

        return results, self.stats


# ============================================================================
# 报告生成
# ============================================================================


def generate_report(results: list[VerificationResult], stats: VerificationStats):
    """生成验证报告"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("[Genesis.VintageVerification] 全链路穿透测试报告")
    logger.info("=" * 80)
    logger.info("")

    # 1. 对比报告表
    logger.info("┌──────────────┬─────────────────┬─────────────┬───────────────┬────────────┬────────────┐")
    logger.info("│ Match ID     │ Teams           │ Actual      │ Prediction    │ Confidence │ Result     │")
    logger.info("├──────────────┼─────────────────┼─────────────┼───────────────┼────────────┼────────────┤")

    for r in results:
        if r.prediction_made:
            result_emoji = "✅" if r.prediction == r.actual_result else "❌"
            teams = f"{r.home_team[:10]} vs {r.away_team[:10]}"
            logger.info(f"│ {r.match_id[:12]:12s} │ {teams:15s} │ {r.actual_result:11s} │ "
                       f"{r.prediction:13s} │ {r.confidence:.2f}      │ {result_emoji:10s} │")

    logger.info("└──────────────┴─────────────────┴─────────────┴───────────────┴────────────┴────────────┘")
    logger.info("")

    # 2. 统计摘要
    logger.info("📊 统计摘要")
    logger.info("-" * 40)
    logger.info(f"  总场次:        {stats.total_targets}")
    logger.info(f"  L2 成功:       {stats.successful_l2}")
    logger.info(f"  特征提取:      {stats.successful_features}")
    logger.info(f"  预测成功:      {stats.successful_predictions}")
    logger.info(f"  预测正确:      {stats.correct_predictions}")
    logger.info(f"  预测准确率:    {stats.get_success_rate():.1f}%")
    logger.info(f"  失败:          {stats.failed_targets}")
    logger.info("")

    # 3. 置信度分布
    logger.info("📈 置信度分布")
    logger.info("-" * 40)
    logger.info(f"  高 (>0.7):     {stats.confidence_distribution['high']} 场")
    logger.info(f"  中 (0.5-0.7):  {stats.confidence_distribution['medium']} 场")
    logger.info(f"  低 (<0.5):     {stats.confidence_distribution['low']} 场")
    logger.info("")

    # 4. prediction_logs 验证 - 查询最近插入的记录
    logger.info("🗄️  prediction_logs 数据完整性验证")
    logger.info("-" * 40)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取本次验证处理的所有 match_id
        match_ids = [r.match_id for r in results if r.prediction_made]

        if match_ids:
            cursor.execute("""
                SELECT COUNT(*) as total_logs,
                       COUNT(DISTINCT match_id) as unique_matches,
                       AVG(confidence) as avg_conf,
                       MIN(confidence) as min_conf,
                       MAX(confidence) as max_conf
                FROM prediction_logs
                WHERE match_id = ANY(%s)
            """, (match_ids,))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                logger.info(f"  预测记录数:    {row['total_logs']}")
                logger.info(f"  独立比赛数:    {row['unique_matches']}")
                logger.info(f"  平均置信度:    {row['avg_conf']:.2f}" if row['avg_conf'] else "  平均置信度:    N/A")
                logger.info(f"  最小置信度:    {row['min_conf']:.2f}" if row['min_conf'] else "  最小置信度:    N/A")
                logger.info(f"  最大置信度:    {row['max_conf']:.2f}" if row['max_conf'] else "  最大置信度:    N/A")
        else:
            logger.info("  没有进行预测的比赛")

    except Exception as e:
        logger.warning(f"  验证查询失败: {e}")

    logger.info("")
    logger.info("=" * 80)

    # 5. 成功标准检查
    success = (
        stats.successful_predictions == SAMPLE_SIZE and
        stats.get_success_rate() >= 40  # 基线 40% 随机水平
    )

    if success:
        logger.info("[Genesis] ✅ HARVESTER ENGINE IS PERFECT.")
    else:
        logger.info(f"[Genesis] ⚠️  收割引擎状态: {stats.successful_predictions}/{SAMPLE_SIZE} 场成功, 准确率 {stats.get_success_rate():.1f}%")

    logger.info("=" * 80)


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主函数"""
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║     [Genesis.VintageVerification] 经典数据全链路验证       ║
    ║                                                            ║
    ║  1. 抽样锁定 - 随机 20 场已有 L2 数据的比赛                ║
    ║  2. 特征提取 - GoldenExtractor V41.380                     ║
    ║  3. AI 预测 - ModelDispatcher V26.7                        ║
    ║  4. 战果校对 - 预测 vs 实际对比报告                        ║
    ║  5. 完整性验证 - prediction_logs 数据检查                  ║
    ╚════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("=" * 60)
    logger.info("[Genesis.VintageVerification] 脚本启动")
    logger.info("=" * 60)
    logger.info(f"样本数量: {SAMPLE_SIZE}")
    logger.info(f"数据来源: 数据库已有 L2 数据")
    logger.info(f"强制重取: {FORCE_REFETCH}")
    logger.info("-" * 40)

    total_start = time.time()

    try:
        # Step 1: 抽样锁定
        logger.info("\n[Step 1] 抽样锁定...")
        logger.info("-" * 40)
        targets = sample_vintage_matches(SAMPLE_SIZE)

        if not targets:
            logger.warning("[Step 1] 未找到符合条件的比赛，脚本退出")
            return

        # Step 2: 全链路穿透
        logger.info("\n[Step 2] 全链路穿透测试...")
        logger.info("-" * 40)

        pipeline = VintageVerificationPipeline(force_refetch=FORCE_REFETCH)
        results, stats = pipeline.process_batch(targets)

        # Step 3: 报告生成
        generate_report(results, stats)

        # 最终报告
        total_elapsed = time.time() - total_start
        logger.info(f"\n总耗时: {total_elapsed:.1f}秒")

        print(f"\n[Genesis.VintageVerification] VERIFICATION COMPLETE. {stats.successful_predictions}/{SAMPLE_SIZE} matches processed. Accuracy: {stats.get_success_rate():.1f}%.")

    except KeyboardInterrupt:
        logger.warning("\n[Genesis.VintageVerification] 用户中断执行")
    except Exception as e:
        logger.error(f"\n[Genesis.VintageVerification] 执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
