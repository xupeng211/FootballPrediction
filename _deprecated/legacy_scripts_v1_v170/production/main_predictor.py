#!/usr/bin/env python3
"""
FootballPrediction - 统一预测入口
=================================

Production-grade 预测脚本，整合 V26.8 模型的所有预测功能。

运行模式:
    --mode legacy      : 全量预测所有 scheduled 比赛（默认）
    --mode chunked     : 分片处理（chunk_size=500）避免内存溢出
    --mode smart       : 仅预测未来比赛 + 高价值投注标记

    --chunk-size N     : 自定义分片大小（默认 500）
    --output PATH      : 自定义输出路径（默认 predictions/）

使用示例:
    # 标准全量预测
    python -m scripts.production.main_predictor --mode legacy

    # 分片处理大规模数据
    python -m scripts.production.main_predictor --mode chunked --chunk-size 1000

    # 仅预测未来比赛（推荐）
    python -m scripts.production.main_predictor --mode smart

Author: FootballPrediction Ops Team
Version: 1.0.0
Date: 2025-12-31
"""

import argparse
import gc
import logging
import os
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Iterator, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.ml.engine import ModelDispatcher


# ============================================================================
# 枚举和配置
# ============================================================================


class PredictionMode(Enum):
    """预测模式"""
    LEGACY = "legacy"   # 全量预测，不过滤时间
    CHUNKED = "chunked" # 分片处理，不过滤时间
    SMART = "smart"     # 仅未来比赛 + 高价值标记


class HighValueConfig:
    """高价值投注配置"""
    CONFIDENCE_THRESHOLD = 0.60  # 置信度 > 60%
    ROI_THRESHOLD = 0.05  # 预期 ROI > 5%


# ============================================================================
# 日志配置
# ============================================================================


def setup_logging(verbose: bool = False) -> logging.Logger:
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        force=True
    )
    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


# ============================================================================
# 主预测器
# ============================================================================


class UnifiedPredictor:
    """
    统一预测器 - 整合 V26.8 模型的所有预测功能
    """

    # 联赛模型映射
    LEAGUE_MODEL_MAPPING = {
        "Premier League": "v26.8_epl_production",
        "La Liga": "v26.8_la_liga_production",
        "Ligue 1": "v26.8_ligue1_production",
        "Bundesliga": "v26.8_bund_production",
    }

    def __init__(
        self,
        mode: PredictionMode = PredictionMode.SMART,
        chunk_size: int = 500,
        output_dir: Optional[Path] = None
    ):
        """
        初始化预测器

        Args:
            mode: 预测模式
            chunk_size: 分片大小（用于 CHUNKED 和 SMART 模式）
            output_dir: 输出目录
        """
        self.mode = mode
        self.chunk_size = chunk_size
        self.output_dir = output_dir or Path("predictions")

        self.settings = get_settings()
        self.dispatcher: Optional[ModelDispatcher] = None
        self._conn: Optional[psycopg2.extensions.connection] = None

        # 统计信息
        self._total_processed = 0
        self._total_success = 0
        self._total_error = 0

    def get_connection(self) -> psycopg2.extensions.connection:
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def load_model(self) -> bool:
        """加载 V26.8 ModelDispatcher"""
        logger.info("=" * 60)
        logger.info("加载 V26.8 ModelDispatcher")
        logger.info("=" * 60)

        try:
            self.dispatcher = ModelDispatcher()
            logger.info("✓ ModelDispatcher 已加载")
            logger.info(f"  支持的联赛: {list(self.LEAGUE_MODEL_MAPPING.keys())}")
            logger.info(f"  通用回退: v26.7_aligned_production")
            return True
        except Exception as e:
            logger.error(f"✗ 模型加载失败: {e}")
            return False

    def _build_query(self) -> tuple[str, list]:
        """
        构建查询 SQL

        Returns:
            (query, params): SQL 查询和参数
        """
        base_select = """
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.match_date,
                m.league_id,
                m.league_name,
                m.status
            FROM matches m
        """

        where_clauses = ["m.status = 'scheduled'"]
        params = []

        # SMART 模式：仅获取未来比赛
        if self.mode == PredictionMode.SMART:
            where_clauses.append("m.match_date >= CURRENT_TIMESTAMP")

        query = f"{base_select} WHERE {' AND '.join(where_clauses)}"

        # 添加排序
        if self.mode == PredictionMode.SMART:
            query += " ORDER BY m.match_date ASC"
        else:
            query += " ORDER BY m.match_date DESC"

        return query, params

    def get_total_count(self) -> int:
        """获取待预测比赛总数"""
        conn = self.get_connection()
        with conn.cursor() as cursor:
            query, params = self._build_query()
            count_query = f"SELECT COUNT(*) as total FROM ({query}) AS subq"
            cursor.execute(count_query, params)
            result = cursor.fetchone()
            return result['total'] if result else 0

    def fetch_matches_chunked(self, offset: int = 0) -> Iterator[pd.DataFrame]:
        """
        分片获取比赛数据

        Args:
            offset: 起始偏移量

        Yields:
            DataFrame: 每个分片的比赛数据
        """
        conn = self.get_connection()
        query, params = self._build_query()

        # 添加 LIMIT/OFFSET
        query += " LIMIT %s OFFSET %s"
        params.extend([self.chunk_size, offset])

        while True:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                matches_data = cursor.fetchall()

                if not matches_data:
                    break

                chunk_df = pd.DataFrame(matches_data)
                mode_name = self.mode.value.upper()
                logger.info(f"📦 [{mode_name}] 读取分片: {len(chunk_df)} 场比赛 (offset: {offset})")

                yield chunk_df

                # 更新偏移量
                offset += self.chunk_size
                params[-1] = offset  # 更新 OFFSET 参数

                if len(matches_data) < self.chunk_size:
                    break

    def fetch_all_matches(self) -> pd.DataFrame:
        """获取所有比赛（LEGACY 模式）"""
        conn = self.get_connection()
        query, params = self._build_query()

        with conn.cursor() as cursor:
            cursor.execute(query, params)
            matches = pd.DataFrame(cursor.fetchall())

        logger.info(f"✓ [LEGACY] 获取到 {len(matches)} 场待预测比赛")
        return matches

    def calculate_expected_roi(
        self,
        prediction: str,
        prob_home: float,
        prob_draw: float,
        prob_away: float
    ) -> float:
        """
        计算预期 ROI

        Args:
            prediction: 预测结果 (Home/Draw/Away)
            prob_home: 主胜概率
            prob_draw: 平局概率
            prob_away: 客胜概率

        Returns:
            预期 ROI
        """
        # 根据预测结果选择对应概率
        prob_map = {"Home": prob_home, "Draw": prob_draw, "Away": prob_away}
        pred_prob = prob_map.get(prediction, 0.33)

        if pred_prob <= 0:
            return 0.0

        # 公平赔率（无利润）
        fair_odds = 1 / pred_prob
        # 预期 ROI = (公平赔率 * 概率 - 1)
        expected_roi = (fair_odds * pred_prob - 1)

        return max(0.0, expected_roi)  # 避免负 ROI

    def predict_single(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        预测单场比赛

        Args:
            match_data: 比赛数据字典

        Returns:
            预测结果字典
        """
        prediction_input = {
            "match_id": match_data["match_id"],
            "league_id": match_data.get("league_id"),
            "league_name": match_data["league_name"],
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "match_time": match_data["match_date"].isoformat() if pd.notna(match_data["match_date"]) else None,
        }

        try:
            result = self.dispatcher.predict(prediction_input)

            prob_home = result["probabilities"]["Home"]
            prob_draw = result["probabilities"]["Draw"]
            prob_away = result["probabilities"]["Away"]

            # 计算预期 ROI（SMART 模式）
            expected_roi = 0.0
            is_high_value = False

            if self.mode == PredictionMode.SMART:
                expected_roi = self.calculate_expected_roi(
                    result["prediction"], prob_home, prob_draw, prob_away
                )
                is_high_value = (
                    result["confidence"] > HighValueConfig.CONFIDENCE_THRESHOLD
                    and expected_roi > HighValueConfig.ROI_THRESHOLD
                )

            return {
                "match_id": match_data["match_id"],
                "external_id": match_data.get("external_id", ""),
                "league": match_data["league_name"],
                "home_team": match_data["home_team"],
                "away_team": match_data["away_team"],
                "match_date": match_data["match_date"],
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "prob_home": prob_home,
                "prob_draw": prob_draw,
                "prob_away": prob_away,
                "model_used": result.get("model_type", "v26_7_aligned"),
                "expected_roi": expected_roi,
                "is_high_value": is_high_value,
                "status": "success",
                "error": "",
            }

        except Exception as e:
            logger.warning(f"预测失败 {match_data['match_id']}: {e}")
            return {
                "match_id": match_data["match_id"],
                "external_id": match_data.get("external_id", ""),
                "league": match_data["league_name"],
                "home_team": match_data["home_team"],
                "away_team": match_data["away_team"],
                "match_date": match_data["match_date"],
                "prediction": "Draw",
                "confidence": 0.33,
                "prob_home": 0.33,
                "prob_draw": 0.34,
                "prob_away": 0.33,
                "model_used": "fallback",
                "expected_roi": 0.0,
                "is_high_value": False,
                "status": "error",
                "error": str(e),
            }

    def process_chunk(self, chunk_df: pd.DataFrame) -> pd.DataFrame:
        """
        处理单个分片

        Args:
            chunk_df: 分片数据

        Returns:
            预测结果 DataFrame
        """
        results = []
        chunk_success = 0
        chunk_error = 0

        for _, match in chunk_df.iterrows():
            result = self.predict_single(match.to_dict())
            results.append(result)

            if result["status"] == "success":
                chunk_success += 1
            else:
                chunk_error += 1

        # 更新全局计数器
        self._total_processed += len(chunk_df)
        self._total_success += chunk_success
        self._total_error += chunk_error

        # 进度摘要
        logger.info(f"✓ 分片完成: {chunk_success} 成功, {chunk_error} 失败")
        logger.info(f"📊 总进度: {self._total_processed} 场 (成功: {self._total_success}, 失败: {self._total_error})")

        return pd.DataFrame(results)

    def predict_all(self) -> pd.DataFrame:
        """
        执行全量预测

        Returns:
            完整预测结果 DataFrame
        """
        mode_name = self.mode.value.upper()
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"执行 [{mode_name}] 预测")
        logger.info("=" * 60)

        # 获取总数
        total_count = self.get_total_count()
        logger.info(f"📋 待预测比赛总数: {total_count}")

        if self.mode in [PredictionMode.CHUNKED, PredictionMode.SMART]:
            logger.info(f"📦 分片大小: {self.chunk_size}")
            logger.info(f"🔢 预计分片数: {(total_count + self.chunk_size - 1) // self.chunk_size}")
        logger.info("")

        # 处理模式
        if self.mode == PredictionMode.LEGACY:
            # LEGACY 模式：一次性获取所有数据
            matches = self.fetch_all_matches()
            if len(matches) == 0:
                return pd.DataFrame()

            all_results = []
            for idx, match in matches.iterrows():
                result = self.predict_single(match.to_dict())
                all_results.append(result)

                # 进度显示
                if (idx + 1) % 100 == 0 or (idx + 1) == len(matches):
                    success = sum(1 for r in all_results if r["status"] == "success")
                    error = sum(1 for r in all_results if r["status"] == "error")
                    logger.info(f"  进度: {idx + 1}/{len(matches)} (成功: {success}, 失败: {error})")

            final_df = pd.DataFrame(all_results)

        else:
            # CHUNKED/SMART 模式：分片处理
            all_results = []
            offset = 0

            for chunk_df in self.fetch_matches_chunked(offset):
                chunk_results = self.process_chunk(chunk_df)
                all_results.append(chunk_results)

                # 显式清理内存
                del chunk_df
                del chunk_results
                gc.collect()

            # 合并所有结果
            if all_results:
                final_df = pd.concat(all_results, ignore_index=True)
            else:
                final_df = pd.DataFrame()

        # 输出统计
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✓ [{mode_name}] 预测完成")
        logger.info(f"  总处理: {self._total_processed} 场")
        logger.info(f"  成功: {self._total_success} 场")
        logger.info(f"  失败: {self._total_error} 场")
        logger.info("=" * 60)

        return final_df

    def save_predictions(self, df: pd.DataFrame, output_path: str):
        """保存预测结果到 CSV"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("保存预测结果")
        logger.info("=" * 60)

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 选择输出列
        output_columns = [
            "match_id", "external_id", "league", "home_team", "away_team",
            "match_date", "prediction", "confidence",
            "prob_home", "prob_draw", "prob_away",
            "model_used", "status",
        ]

        # SMART 模式额外列
        if self.mode == PredictionMode.SMART:
            output_columns.extend(["expected_roi", "is_high_value"])

        df_output = df[output_columns].copy()

        # 格式化日期
        df_output["match_date"] = pd.to_datetime(df_output["match_date"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        # 格式化概率和 ROI
        for col in ["prob_home", "prob_draw", "prob_away", "confidence"]:
            if col in df_output.columns:
                df_output[col] = df_output[col].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")

        if "expected_roi" in df_output.columns:
            df_output["expected_roi"] = df_output["expected_roi"].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "0.00%")

        if "is_high_value" in df_output.columns:
            df_output["is_high_value"] = df_output["is_high_value"].apply(lambda x: "TRUE" if x else "FALSE")

        # 保存
        df_output.to_csv(output_path, index=False, encoding="utf-8")

        logger.info(f"✓ 预测结果已保存: {output_path}")
        logger.info(f"  总记录数: {len(df_output)}")

    def generate_summary_report(self, df: pd.DataFrame, output_path: str):
        """生成预测摘要报告"""
        report_path = output_path.replace(".csv", "_summary.txt")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"V26.8 {self.mode.value.upper()} 预测报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"预测模式: {self.mode.value}\n")
            if self.mode in [PredictionMode.CHUNKED, PredictionMode.SMART]:
                f.write(f"分片大小: {self.chunk_size}\n")
            f.write(f"预测总数: {len(df)}\n")
            f.write(f"成功预测: {self._total_success}\n")
            f.write(f"失败预测: {self._total_error}\n")
            f.write("\n")

            success_df = df[df["status"] == "success"]
            if len(success_df) > 0:
                f.write("预测分布:\n")
                f.write("-" * 40 + "\n")
                for pred in ["Home", "Draw", "Away"]:
                    count = len(success_df[success_df["prediction"] == pred])
                    pct = count / len(success_df) * 100
                    f.write(f"  {pred:8s}: {count:4d} ({pct:5.1f}%)\n")

                f.write("\n置信度统计:\n")
                f.write("-" * 40 + "\n")
                f.write(f"  平均: {success_df['confidence'].mean():.2%}\n")
                f.write(f"  最高: {success_df['confidence'].max():.2%}\n")
                f.write(f"  最低: {success_df['confidence'].min():.2%}\n")

                # SMART 模式额外统计
                if self.mode == PredictionMode.SMART and "expected_roi" in success_df.columns:
                    f.write("\n预期 ROI 统计:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"  平均: {success_df['expected_roi'].mean():.2%}\n")
                    f.write(f"  最高: {success_df['expected_roi'].max():.2%}\n")

                    high_value_df = success_df[success_df["is_high_value"] == True]
                    f.write("\n高价值投注机会:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"  数量: {len(high_value_df)}\n")
                    f.write(f"  占比: {len(high_value_df)/len(success_df)*100:.1f}%\n")
                    f.write(f"  置信度阈值: >{HighValueConfig.CONFIDENCE_THRESHOLD*100:.0f}%\n")
                    f.write(f"  ROI 阈值: >{HighValueConfig.ROI_THRESHOLD*100:.0f}%\n")

            f.write("\n联赛分布:\n")
            f.write("-" * 40 + "\n")
            league_counts = df["league"].value_counts()
            for league, count in league_counts.items():
                f.write(f"  {league}: {count}\n")

            if "model_used" in df.columns:
                f.write("\n模型使用分布:\n")
                f.write("-" * 40 + "\n")
                model_counts = df["model_used"].value_counts()
                for model, count in model_counts.items():
                    f.write(f"  {model}: {count}\n")

        logger.info(f"✓ 摘要报告已保存: {report_path}")


# ============================================================================
# CLI 接口
# ============================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="FootballPrediction 统一预测入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式:
  --mode legacy      全量预测所有 scheduled 比赛（默认）
  --mode chunked     分片处理避免内存溢出
  --mode smart       仅预测未来比赛 + 高价值标记

使用示例:
  python -m scripts.production.main_predictor --mode smart
  python -m scripts.production.main_predictor --mode chunked --chunk-size 1000
        """
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["legacy", "chunked", "smart"],
        default="smart",
        help="预测模式 (默认: smart)"
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="分片大小 (默认: 500)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出目录 (默认: predictions/)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细日志输出"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 设置日志
    global logger
    logger = setup_logging(verbose=args.verbose)

    logger.info("")
    logger.info("=" * 60)
    logger.info("FootballPrediction - 统一预测入口")
    logger.info("=" * 60)
    logger.info(f"模式: {args.mode.upper()}")
    logger.info("")

    # 创建预测器
    mode = PredictionMode(args.mode)
    output_dir = Path(args.output) if args.output else Path("predictions")
    predictor = UnifiedPredictor(mode=mode, chunk_size=args.chunk_size, output_dir=output_dir)

    # 1. 加载模型
    if not predictor.load_model():
        logger.error("模型加载失败，无法继续")
        sys.exit(1)

    # 2. 执行预测
    results_df = predictor.predict_all()

    if len(results_df) == 0:
        logger.warning("没有预测结果")
        sys.exit(0)

    # 3. 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{args.mode}_predict_{timestamp}.csv"
    output_path = output_dir / output_filename

    predictor.save_predictions(results_df, str(output_path))

    # 4. 生成摘要报告
    predictor.generate_summary_report(results_df, str(output_path))

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ 预测流程完成")
    logger.info("=" * 60)
    logger.info("")
    logger.info("输出文件:")
    logger.info(f"  - {output_path}")
    logger.info(f"  - {output_path.replace('.csv', '_summary.txt')}")
    logger.info("")


if __name__ == "__main__":
    main()
