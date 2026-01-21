#!/usr/bin/env python3
"""
V26.8 Production Service - 全自动生产预测服务（联赛专项模型版）
================================================================

闭环流程:
1. 使用 IncrementalCollector 抓取未来 24 小时内的英超/西甲比赛
2. 使用 ModelDispatcher 自动选择合适的模型（专项 vs 通用）进行预测
3. 将预测出的"高价值（High Confidence）"比赛保存到 data/forecasts/today.csv

V26.8 新增特性:
- 自动联赛检测（支持英超、西甲、意甲、德甲、法甲）
- 优先使用联赛专项模型，回退使用通用 V26.7 模型
- today.csv 报告中标注模型来源（专项/通用）

验收标准:
- 运行一个命令，直接在 data/forecasts/ 下看到今晚真实英超比赛的预测概率
- 报告中显示每场比赛使用了哪种模型

Author: ML Architect
Date: 2025-12-28
Version: 26.8 (League Specialized)
"""

import csv
from datetime import datetime, timedelta
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.ml.engine import ModelDispatcher, Predictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

FORECAST_DIR = Path("data/forecasts")
FORECAST_FILE = FORECAST_DIR / "today.csv"

# 高置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 0.55  # 最大概率 >= 55%

# 目标联赛
TARGET_LEAGUES = ["Premier League", "La Liga"]


class ProductionService:
    """
    V26.8 生产预测服务

    实现全自动闭环预测流程，支持联赛专项模型自动分发。
    """

    def __init__(self, model_type: str = "v26_7_aligned", use_model_dispatcher: bool = True):
        """
        初始化生产服务

        Args:
            model_type: 模型类型 (v26_7_aligned, v26_mini) - 仅在不使用 dispatcher 时有效
            use_model_dispatcher: 是否使用模型分发器（默认True，启用联赛专项模型）
        """
        self.model_type = model_type
        self.use_model_dispatcher = use_model_dispatcher

        # 初始化预测器
        if use_model_dispatcher:
            logger.info("初始化 V26.8 ModelDispatcher（联赛专项模型分发器）...")
            self.predictor = ModelDispatcher()
            self.model_version = "26.8"
        else:
            logger.info(f"初始化 {model_type} 预测器...")
            if model_type == "v26_7_aligned":
                self.predictor = Predictor.create_v26_7_aligned()
            else:
                self.predictor = Predictor.create_v26_mini()
            self.model_version = "26.7"

        # 数据库连接参数
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

        # 确保输出目录存在
        FORECAST_DIR.mkdir(parents=True, exist_ok=True)

    def _get_upcoming_matches(self, hours_ahead: int = 24) -> list[dict]:
        """
        获取未来 N 小时内的比赛

        Args:
            hours_ahead: 向前查找的小时数

        Returns:
            比赛列表
        """
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # 计算时间范围
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(hours=hours_ahead)

            logger.info(f"查询时间范围: {start_time} ~ {end_time}")

            cur.execute(
                """
                SELECT
                    m.match_id,
                    m.external_id,
                    m.league_name,
                    m.home_team,
                    m.away_team,
                    m.match_time,
                    m.status
                FROM matches m
                WHERE m.match_time BETWEEN %s AND %s
                    AND m.league_name = ANY(%s)
                    AND m.status NOT IN ('finished', 'cancelled')
                ORDER BY m.match_time ASC
            """,
                (start_time, end_time, TARGET_LEAGUES),
            )

            matches = [dict(row) for row in cur.fetchall()]

            logger.info(f"找到 {len(matches)} 场未来 {hours_ahead} 小时内的比赛")
            for m in matches:
                logger.info(
                    f"  - {m['league_name']}: {m['home_team']} vs {m['away_team']} @ {m['match_time']}"
                )

            return matches

        finally:
            cur.close()
            conn.close()

    def _fetch_raw_data_for_matches(self, matches: list[dict]) -> dict[int, dict]:
        """
        从数据库获取比赛的原始 JSON 数据

        Args:
            matches: 比赛列表

        Returns:
            {external_id: raw_data} 映射
        """
        if not matches:
            return {}

        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            external_ids = [str(m["external_id"]) for m in matches]
            placeholders = ",".join(["%s"] * len(external_ids))

            cur.execute(
                f"""
                SELECT external_id, raw_data
                FROM raw_match_data
                WHERE external_id IN ({placeholders})
            """,
                external_ids,
            )

            raw_data_map = {row["external_id"]: row["raw_data"] for row in cur.fetchall()}

            logger.info(f"获取到 {len(raw_data_map)}/{len(matches)} 场比赛的原始数据")

            return raw_data_map

        finally:
            cur.close()
            conn.close()

    def predict_upcoming_matches(
        self, hours_ahead: int = 24, min_confidence: float = HIGH_CONFIDENCE_THRESHOLD
    ) -> list[dict]:
        """
        预测未来 N 小时内的比赛

        Args:
            hours_ahead: 向前查找的小时数
            min_confidence: 最小置信度阈值

        Returns:
            高置信度预测结果列表
        """
        logger.info("=" * 60)
        logger.info(f"V26.7 生产预测: 未来 {hours_ahead} 小时")
        logger.info("=" * 60)

        # 1. 获取未来比赛
        matches = self._get_upcoming_matches(hours_ahead=hours_ahead)

        if not matches:
            logger.warning("没有找到符合条件的比赛")
            return []

        # 2. 获取原始数据
        raw_data_map = self._fetch_raw_data_for_matches(matches)

        if not raw_data_map:
            logger.error("无法获取任何原始数据，请先运行数据采集")
            return []

        # 3. 批量预测
        predictions = []

        for match in matches:
            external_id = str(match["external_id"])

            if external_id not in raw_data_map:
                logger.warning(f"跳过 Match {external_id}: 无原始数据")
                continue

            try:
                raw_data = raw_data_map[external_id]

                # 添加联赛信息到原始数据（供 ModelDispatcher 使用）
                if self.use_model_dispatcher:
                    raw_data_with_league = {
                        **raw_data,
                        "league_id": match.get("league_id"),
                        "league_name": match.get("league_name"),
                    }
                    result = self.predictor.predict(raw_data_with_league)
                else:
                    result = self.predictor.predict(raw_data)

                # 提取置信度
                confidence = result["confidence"]
                is_high_confidence = confidence >= min_confidence

                # 构建预测记录（V26.8 增强版）
                prediction_record = {
                    "match_id": match["match_id"],
                    "external_id": external_id,
                    "league": match["league_name"],
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "match_time": match["match_time"].isoformat() if match["match_time"] else None,
                    "prediction": result["prediction"],
                    "prob_away": result["probabilities"]["Away"],
                    "prob_draw": result["probabilities"]["Draw"],
                    "prob_home": result["probabilities"]["Home"],
                    "confidence": confidence,
                    "high_confidence": is_high_confidence,
                    "forecast_time": datetime.now().isoformat(),
                }

                # V26.8 新增：模型来源标注
                if self.use_model_dispatcher:
                    prediction_record["model_source"] = result.get("model_source", "v26_7_aligned")
                    prediction_record["model_type"] = result.get("model_type", "general")
                    prediction_record["league_specific"] = result.get("league_specific", False)
                    prediction_record["league_id"] = result.get("league_id")
                else:
                    prediction_record["model_source"] = self.model_type
                    prediction_record["model_type"] = "single"
                    prediction_record["league_specific"] = False
                    prediction_record["league_id"] = None

                predictions.append(prediction_record)

                # 高亮高置信度预测
                model_info = (
                    f" [{result.get('model_source', 'N/A')}]" if self.use_model_dispatcher else ""
                )
                if is_high_confidence:
                    logger.info(
                        f"✨ 高置信度{model_info}: {match['home_team']} vs {match['away_team']} "
                        f"-> {result['prediction']} ({confidence:.2%})"
                    )
                else:
                    logger.info(
                        f"  低置信度{model_info}: {match['home_team']} vs {match['away_team']} "
                        f"-> {result['prediction']} ({confidence:.2%})"
                    )

            except Exception as e:
                logger.exception(f"预测 Match {external_id} 失败: {e}")
                continue

        return predictions

    def save_forecasts(self, predictions: list[dict], output_path: Path = FORECAST_FILE) -> None:
        """
        保存预测结果到 CSV

        Args:
            predictions: 预测结果列表
            output_path: 输出文件路径
        """
        if not predictions:
            logger.warning("没有预测结果需要保存")
            return

        # 过滤高置信度预测
        high_confidence_predictions = [p for p in predictions if p["high_confidence"]]

        logger.info(f"保存 {len(high_confidence_predictions)}/{len(predictions)} 条高置信度预测")

        # 准备 CSV 数据（V26.8 增强版）
        fieldnames = [
            "match_id",
            "external_id",
            "league",
            "home_team",
            "away_team",
            "match_time",
            "prediction",
            "prob_away",
            "prob_draw",
            "prob_home",
            "confidence",
            "forecast_time",
            # V26.8 新增字段
            "model_source",
            "model_type",
            "league_specific",
            "league_id",
        ]

        # 写入 CSV
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for pred in high_confidence_predictions:
                row = {k: pred[k] for k in fieldnames}
                writer.writerow(row)

        logger.info(f"✅ 预测已保存: {output_path}")

    def run(self, hours_ahead: int = 24, min_confidence: float = HIGH_CONFIDENCE_THRESHOLD) -> int:
        """
        运行完整的生产预测流程

        Args:
            hours_ahead: 向前查找的小时数
            min_confidence: 最小置信度阈值

        Returns:
            高置信度预测数量
        """
        # 预测
        predictions = self.predict_upcoming_matches(
            hours_ahead=hours_ahead, min_confidence=min_confidence
        )

        if not predictions:
            logger.warning("未生成任何预测")
            return 0

        # 保存
        self.save_forecasts(predictions)

        # 统计
        high_conf_count = sum(1 for p in predictions if p["high_confidence"])

        logger.info("\n" + "=" * 60)
        logger.info("预测摘要")
        logger.info("=" * 60)
        logger.info(f"总预测数: {len(predictions)}")
        logger.info(f"高置信度: {high_conf_count}")
        logger.info(f"置信度阈值: {min_confidence:.2%}")
        logger.info(f"输出文件: {FORECAST_FILE}")
        logger.info("=" * 60)

        return high_conf_count


# ============================================================================
# 便捷函数
# ============================================================================


def run_production_service(
    hours_ahead: int = 24,
    min_confidence: float = HIGH_CONFIDENCE_THRESHOLD,
    use_model_dispatcher: bool = True,
) -> int:
    """
    运行生产预测服务

    Args:
        hours_ahead: 向前查找的小时数
        min_confidence: 最小置信度阈值
        use_model_dispatcher: 是否使用模型分发器（V26.8 联赛专项模型）

    Returns:
        高置信度预测数量
    """
    service = ProductionService(
        model_type="v26_7_aligned", use_model_dispatcher=use_model_dispatcher
    )
    return service.run(hours_ahead=hours_ahead, min_confidence=min_confidence)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("V26.8 Production Service (League Specialized Models)")
    logger.info("=" * 60)

    # 运行预测（默认启用 ModelDispatcher）
    high_conf_count = run_production_service(
        hours_ahead=24, min_confidence=HIGH_CONFIDENCE_THRESHOLD
    )

    if high_conf_count > 0:
        logger.info(f"\n✅ 生产预测完成! 发现 {high_conf_count} 场高置信度比赛")
        logger.info(f"查看预测结果: cat {FORECAST_FILE}")
        return 0
    logger.warning("\n⚠️ 未发现高置信度比赛，可能需要:")
    logger.warning("  1. 先运行数据采集: python -m src.api.collectors.v51_incremental_collector")
    logger.warning("  2. 降低置信度阈值")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
