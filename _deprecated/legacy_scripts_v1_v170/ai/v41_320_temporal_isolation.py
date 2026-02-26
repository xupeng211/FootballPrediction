#!/usr/bin/env python3
"""
V41.320 "Temporal Isolation" - 时空隔离特征提取器
=====================================================

核心原则: 彻底根除数据泄露，只用"过去"预测"未来"

核心逻辑:
    对于比赛 T（目标预测）：
    - 特征来源 = T 之前的比赛历史 (T-1, T-2, ..., T-N)
    - 禁止读取比赛 T 本身的 technical_features（赛后数据）
    - 赔率数据 = 可用（赛前已知）

滚动窗口设计:
    - 过去 5 场比赛的滚动统计
    - 赛季累计统计（本赛季截至 T-1）
    - 历史交锋统计（H2H）

输出规格:
    - Leakage Removed: YES
    - Real Prediction Accuracy: [X%]
    - Edge over Bookies: [Y%]

Author: Lead Data Scientist & Risk Controller
Version: V41.320 (Temporal Isolation)
Date: 2026-01-21
"""

# ============================================================================
# 标准库导入
# ============================================================================
import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# 第三方库导入
# ============================================================================
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import structlog
from tqdm import tqdm

# ============================================================================
# 本地模块导入
# ============================================================================
from src.config_unified import get_settings

logger = structlog.get_logger(__name__)


# ============================================================================
# V41.320 数据类定义
# ============================================================================


@dataclass
class TemporalExtractionStats:
    """V41.320 时空隔离提取统计"""

    # 数据来源统计
    total_matches_db: int = 0
    samples_with_history: int = 0
    samples_insufficient_history: int = 0  # 历史数据不足的样本

    # 特征统计
    total_features_extracted: int = 0
    feature_matrix_shape: tuple = (0, 0)

    # 标签统计
    label_distribution: dict[str, int] = field(default_factory=dict)

    # 时间统计
    extraction_time_ms: float = 0.0

    def __str__(self) -> str:
        return (
            f"V41.320 时空隔离提取统计:\n"
            f"  数据库比赛: {self.total_matches_db} 场\n"
            f"  可用样本（有历史）: {self.samples_with_history} 场\n"
            f"  历史不足样本: {self.samples_insufficient_history} 场\n"
            f"  特征维度: {self.feature_matrix_shape[1]}\n"
            f"  特征矩阵: {self.feature_matrix_shape[0]} x {self.feature_matrix_shape[1]}\n"
            f"  标签分布: H={self.label_distribution.get('H', 0)}, "
            f"D={self.label_distribution.get('D', 0)}, "
            f"A={self.label_distribution.get('A', 0)}\n"
            f"  提取耗时: {self.extraction_time_ms:.0f}ms"
        )


@dataclass
class TemporalDataset:
    """V41.320 时空隔离数据集"""

    # 特征矩阵
    X: np.ndarray

    # 标签向量 (0=H, 1=D, 2=A)
    y: np.ndarray

    # 元数据
    metadata: pd.DataFrame

    # 特征名称列表
    feature_names: list[str]

    # 统计信息
    stats: TemporalExtractionStats

    # 是否包含赔率特征
    has_odds_features: bool = False

    def save(self, output_dir: str | Path) -> None:
        """保存数据集到文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存特征矩阵
        np.save(output_dir / "X_features.npy", self.X)

        # 保存标签向量
        np.save(output_dir / "y_labels.npy", self.y)

        # 保存元数据
        self.metadata.to_csv(output_dir / "metadata.csv", index=False)

        # 保存特征名称
        with open(output_dir / "feature_names.json", "w") as f:
            json.dump(self.feature_names, f, indent=2)

        # 保存统计信息
        stats_dict = {
            "total_matches_db": self.stats.total_matches_db,
            "samples_with_history": self.stats.samples_with_history,
            "samples_insufficient_history": self.stats.samples_insufficient_history,
            "total_features_extracted": self.stats.total_features_extracted,
            "feature_matrix_shape": self.stats.feature_matrix_shape,
            "label_distribution": self.stats.label_distribution,
            "extraction_time_ms": self.stats.extraction_time_ms,
            "has_odds_features": self.has_odds_features,
            "leakage_removed": True,
        }
        with open(output_dir / "stats.json", "w") as f:
            json.dump(stats_dict, f, indent=2)

        logger.info(
            "数据集保存完成",
            output_dir=str(output_dir),
            X_shape=self.X.shape,
            y_shape=self.y.shape,
        )


# ============================================================================
# V41.320 滚动窗口特征计算器
# ============================================================================


class RollingWindowCalculator:
    """
    滚动窗口特征计算器

    核心功能:
        - 计算过去 N 场比赛的滚动统计
        - 计算赛季累计统计
        - 计算 H2H 统计
    """

    def __init__(self, window_size: int = 5):
        """
        初始化计算器

        Args:
            window_size: 滚动窗口大小（默认 5 场）
        """
        self.window_size = window_size

    def compute_team_form(
        self,
        team: str,
        target_match_date: datetime,
        history_df: pd.DataFrame,
    ) -> dict[str, Any]:
        """
        计算球队近期状态（过去 N 场）

        Args:
            team: 球队名称
            target_match_date: 目标比赛日期
            history_df: 历史比赛数据

        Returns:
            状态特征字典
        """
        # 筛选该球队在目标日期之前的比赛
        team_matches = history_df[
            ((history_df["home_team"] == team) | (history_df["away_team"] == team)) &
            (history_df["match_date"] < target_match_date)
        ].sort_values("match_date", ascending=False)

        # 最近 N 场
        recent_matches = team_matches.head(self.window_size)

        if recent_matches.empty:
            return self._empty_form_features()

        features = {}

        # 计算胜负统计
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0

        for _, match in recent_matches.iterrows():
            is_home = match["home_team"] == team
            home_score = match["home_score"]
            away_score = match["away_score"]

            if is_home:
                team_score = home_score
                opponent_score = away_score
            else:
                team_score = away_score
                opponent_score = home_score

            goals_for += team_score
            goals_against += opponent_score

            if team_score > opponent_score:
                wins += 1
            elif team_score == opponent_score:
                draws += 1
            else:
                losses += 1

        total = len(recent_matches)

        features["recent_win_rate"] = wins / total if total > 0 else 0.0
        features["recent_draw_rate"] = draws / total if total > 0 else 0.0
        features["recent_loss_rate"] = losses / total if total > 0 else 0.0
        features["recent_goals_for_avg"] = goals_for / total if total > 0 else 0.0
        features["recent_goals_against_avg"] = goals_against / total if total > 0 else 0.0
        features["recent_goal_diff_avg"] = (goals_for - goals_against) / total if total > 0 else 0.0
        features["recent_matches_played"] = total

        return features

    def compute_season_stats(
        self,
        team: str,
        target_match_date: datetime,
        history_df: pd.DataFrame,
        season: str,
    ) -> dict[str, Any]:
        """
        计算赛季累计统计

        Args:
            team: 球队名称
            target_match_date: 目标比赛日期
            history_df: 历史比赛数据
            season: 赛季

        Returns:
            赛季统计特征字典
        """
        # 筛选该球队在本赛季、目标日期之前的比赛
        season_matches = history_df[
            (history_df["season"] == season) &
            ((history_df["home_team"] == team) | (history_df["away_team"] == team)) &
            (history_df["match_date"] < target_match_date)
        ]

        if season_matches.empty:
            return self._empty_season_features()

        features = {}

        # 积分统计
        points = 0
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0

        for _, match in season_matches.iterrows():
            is_home = match["home_team"] == team
            home_score = match["home_score"]
            away_score = match["away_score"]

            if is_home:
                team_score = home_score
                opponent_score = away_score
            else:
                team_score = away_score
                opponent_score = home_score

            goals_for += team_score
            goals_against += opponent_score

            if team_score > opponent_score:
                wins += 1
                points += 3
            elif team_score == opponent_score:
                draws += 1
                points += 1
            else:
                losses += 1

        total = len(season_matches)

        features["season_points"] = points
        features["season_win_rate"] = wins / total if total > 0 else 0.0
        features["season_draw_rate"] = draws / total if total > 0 else 0.0
        features["season_goals_for_avg"] = goals_for / total if total > 0 else 0.0
        features["season_goals_against_avg"] = goals_against / total if total > 0 else 0.0
        features["season_goal_diff_avg"] = (goals_for - goals_against) / total if total > 0 else 0.0
        features["season_matches_played"] = total

        return features

    def compute_h2h_stats(
        self,
        home_team: str,
        away_team: str,
        target_match_date: datetime,
        history_df: pd.DataFrame,
    ) -> dict[str, Any]:
        """
        计算 H2H（历史交锋）统计

        Args:
            home_team: 主队
            away_team: 客队
            target_match_date: 目标比赛日期
            history_df: 历史比赛数据

        Returns:
            H2H 统计特征字典
        """
        # 筛选这两支球队之间的历史交锋
        h2h_matches = history_df[
            (((history_df["home_team"] == home_team) & (history_df["away_team"] == away_team)) |
             ((history_df["home_team"] == away_team) & (history_df["away_team"] == home_team))) &
            (history_df["match_date"] < target_match_date)
        ].sort_values("match_date", ascending=False)

        # 最近 N 场交锋
        recent_h2h = h2h_matches.head(self.window_size)

        if recent_h2h.empty:
            return self._empty_h2h_features()

        features = {}

        home_wins = 0
        draws = 0
        away_wins = 0

        for _, match in recent_h2h.iterrows():
            match_home_team = match["home_team"]
            home_score = match["home_score"]
            away_score = match["away_score"]

            if match_home_team == home_team:
                if home_score > away_score:
                    home_wins += 1
                elif home_score < away_score:
                    away_wins += 1
                else:
                    draws += 1
            else:
                if away_score > home_score:
                    home_wins += 1
                elif away_score < home_score:
                    away_wins += 1
                else:
                    draws += 1

        total = len(recent_h2h)

        features["h2h_home_win_rate"] = home_wins / total if total > 0 else 0.0
        features["h2h_draw_rate"] = draws / total if total > 0 else 0.0
        features["h2h_away_win_rate"] = away_wins / total if total > 0 else 0.0
        features["h2h_matches_played"] = total

        return features

    def _empty_form_features(self) -> dict[str, Any]:
        """空状态特征"""
        return {
            "recent_win_rate": 0.0,
            "recent_draw_rate": 0.0,
            "recent_loss_rate": 0.0,
            "recent_goals_for_avg": 0.0,
            "recent_goals_against_avg": 0.0,
            "recent_goal_diff_avg": 0.0,
            "recent_matches_played": 0,
        }

    def _empty_season_features(self) -> dict[str, Any]:
        """空赛季特征"""
        return {
            "season_points": 0,
            "season_win_rate": 0.0,
            "season_draw_rate": 0.0,
            "season_goals_for_avg": 0.0,
            "season_goals_against_avg": 0.0,
            "season_goal_diff_avg": 0.0,
            "season_matches_played": 0,
        }

    def _empty_h2h_features(self) -> dict[str, Any]:
        """空 H2H 特征"""
        return {
            "h2h_home_win_rate": 0.0,
            "h2h_draw_rate": 0.0,
            "h2h_away_win_rate": 0.0,
            "h2h_matches_played": 0,
        }


# ============================================================================
# V41.320 时空隔离特征提取器
# ============================================================================


class TemporalIsolationExtractor:
    """
    V41.320 时空隔离特征提取器

    核心原则:
        - 只使用目标比赛 T 之前的数据
        - 严禁读取比赛 T 本身的 technical_features
    """

    def __init__(
        self,
        min_history_matches: int = 5,
        include_odds: bool = False,
        season_filter: str | None = None,
        league_filter: str | None = None,
    ):
        """
        初始化提取器

        Args:
            min_history_matches: 最少历史比赛数
            include_odds: 是否包含赔率特征
            season_filter: 赛季过滤
            league_filter: 联赛过滤
        """
        self.min_history_matches = min_history_matches
        self.include_odds = include_odds
        self.season_filter = season_filter
        self.league_filter = league_filter

        self.calculator = RollingWindowCalculator(window_size=5)
        self.stats = TemporalExtractionStats()

        logger.info(
            "V41.320 时空隔离提取器初始化完成",
            min_history_matches=min_history_matches,
            include_odds=include_odds,
        )

    def _get_db_connection(self):
        """获取数据库连接"""
        settings = get_settings()
        return psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )

    def _load_all_matches(self) -> pd.DataFrame:
        """加载所有比赛数据（用于构建历史）"""
        conn = self._get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT
                    m.match_id,
                    m.league_name,
                    m.season,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.status,
                    m.home_score,
                    m.away_score
                FROM matches m
                WHERE m.status = 'FT'
                  AND m.home_score IS NOT NULL
                  AND m.away_score IS NOT NULL
            """

            params = []
            if self.season_filter:
                query += " AND m.season = %s"
                params.append(self.season_filter)
            if self.league_filter:
                query += " AND m.league_name = %s"
                params.append(self.league_filter)

            query += " ORDER BY m.match_date ASC"

            cur.execute(query, params)
            rows = cur.fetchall()

            df = pd.DataFrame(rows)

            self.stats.total_matches_db = len(df)

            logger.info("历史比赛加载完成", total_matches=len(df))

            return df

        finally:
            conn.close()

    def _load_odds_data(self) -> dict[str, dict]:
        """加载赔率数据"""
        conn = self._get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT
                    match_id,
                    closing_price,
                    initial_price
                FROM match_odds_intelligence
                WHERE closing_price IS NOT NULL
            """

            cur.execute(query)
            rows = cur.fetchall()

            odds_dict = {}
            for row in rows:
                match_id = row["match_id"]
                closing = row.get("closing_price")
                initial = row.get("initial_price")

                # 解析 JSON
                if closing:
                    try:
                        if isinstance(closing, str):
                            closing = json.loads(closing)
                        if isinstance(closing, list) and len(closing) >= 3:
                            odds_dict[match_id] = {
                                "closing_home": float(closing[0]),
                                "closing_draw": float(closing[1]),
                                "closing_away": float(closing[2]),
                            }
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

            logger.info("赔率数据加载完成", total_matches=len(odds_dict))

            return odds_dict

        finally:
            conn.close()

    def _extract_label(self, home_score: int, away_score: int) -> int:
        """提取标签"""
        if home_score > away_score:
            return 0  # H
        elif home_score < away_score:
            return 2  # A
        else:
            return 1  # D

    def extract(self) -> TemporalDataset:
        """执行时空隔离特征提取"""
        start_time = datetime.now()

        logger.info("开始 V41.320 时空隔离特征提取流程")

        # Step 1: 加载所有历史比赛
        logger.info("Step 1/4: 加载历史比赛数据")
        history_df = self._load_all_matches()

        if history_df.empty:
            logger.warning("没有历史比赛数据")
            return self._empty_dataset()

        # Step 2: 加载赔率数据（可选）
        odds_dict = {}
        if self.include_odds:
            logger.info("Step 2/4: 加载赔率数据")
            odds_dict = self._load_odds_data()

        # Step 3: 逐场比赛提取特征
        logger.info("Step 3/4: 时空隔离特征提取（滚动窗口）")

        features_list = []
        labels_list = []
        metadata_list = []

        label_counts = {"H": 0, "D": 0, "A": 0}

        # 按日期排序，确保时间顺序
        history_df = history_df.sort_values("match_date")

        for _, row in tqdm(history_df.iterrows(), total=len(history_df), desc="时空隔离提取"):
            match_id = row["match_id"]
            match_date = row["match_date"]
            home_team = row["home_team"]
            away_team = row["away_team"]
            season = row["season"]

            # 检查历史数据是否足够
            prior_matches = history_df[history_df["match_date"] < match_date]
            if len(prior_matches) < self.min_history_matches:
                self.stats.samples_insufficient_history += 1
                continue

            # 提取特征
            features = {}

            # 1. 主队近期状态
            home_form = self.calculator.compute_team_form(home_team, match_date, prior_matches)
            for k, v in home_form.items():
                features[f"home_{k}"] = v

            # 2. 客队近期状态
            away_form = self.calculator.compute_team_form(away_team, match_date, prior_matches)
            for k, v in away_form.items():
                features[f"away_{k}"] = v

            # 3. 主队赛季统计
            home_season = self.calculator.compute_season_stats(home_team, match_date, prior_matches, season)
            for k, v in home_season.items():
                features[f"home_season_{k}"] = v

            # 4. 客队赛季统计
            away_season = self.calculator.compute_season_stats(away_team, match_date, prior_matches, season)
            for k, v in away_season.items():
                features[f"away_season_{k}"] = v

            # 5. H2H 统计
            h2h = self.calculator.compute_h2h_stats(home_team, away_team, match_date, prior_matches)
            for k, v in h2h.items():
                features[f"h2h_{k}"] = v

            # 6. 赔率特征（可选）
            if self.include_odds and match_id in odds_dict:
                odds = odds_dict[match_id]
                features["odds_home"] = odds["closing_home"]
                features["odds_draw"] = odds["closing_draw"]
                features["odds_away"] = odds["closing_away"]
                features["implied_prob_home"] = 1.0 / odds["closing_home"]
                features["implied_prob_draw"] = 1.0 / odds["closing_draw"]
                features["implied_prob_away"] = 1.0 / odds["closing_away"]

            # 7. 主场优势（基于主队历史主场表现）
            home_recent_home = prior_matches[
                (prior_matches["home_team"] == home_team) &
                (prior_matches["match_date"] < match_date)
            ].tail(self.calculator.window_size)

            if not home_recent_home.empty:
                home_wins = sum(home_recent_home["home_score"] > home_recent_home["away_score"])
                features["home_recent_home_win_rate"] = home_wins / len(home_recent_home)
            else:
                features["home_recent_home_win_rate"] = 0.0

            # 提取标签
            label = self._extract_label(row["home_score"], row["away_score"])
            label_map = {0: "H", 1: "D", 2: "A"}
            label_counts[label_map[label]] += 1

            features_list.append(features)
            labels_list.append(label)

            # 元数据
            metadata_list.append({
                "match_id": match_id,
                "league_name": row["league_name"],
                "season": season,
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_date,
                "home_score": row["home_score"],
                "away_score": row["away_score"],
                "label": label,
                "label_name": label_map[label],
            })

            self.stats.samples_with_history += 1

        # Step 4: 构建特征矩阵
        logger.info("Step 4/4: 构建特征矩阵")
        df_features = pd.DataFrame(features_list)

        # 填充 NaN
        df_features = df_features.fillna(0.0)

        X = df_features.values
        y = np.array(labels_list)

        feature_names = df_features.columns.tolist()

        # 构建元数据
        df_metadata = pd.DataFrame(metadata_list)

        # 更新统计信息
        self.stats.total_features_extracted = len(feature_names)
        self.stats.feature_matrix_shape = X.shape
        self.stats.label_distribution = label_counts
        self.stats.extraction_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "V41.320 时空隔离提取完成",
            samples=X.shape[0],
            features=X.shape[1],
            label_distribution=label_counts,
            elapsed_ms=f"{self.stats.extraction_time_ms:.0f}",
        )

        return TemporalDataset(
            X=X,
            y=y,
            metadata=df_metadata,
            feature_names=feature_names,
            stats=self.stats,
            has_odds_features=self.include_odds,
        )

    def _empty_dataset(self) -> TemporalDataset:
        """返回空数据集"""
        return TemporalDataset(
            X=np.array([]),
            y=np.array([]),
            metadata=pd.DataFrame(),
            feature_names=[],
            stats=self.stats,
            has_odds_features=self.include_odds,
        )


# ============================================================================
# 命令行入口
# ============================================================================


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="V41.320 时空隔离特征提取器 - 彻底根除数据泄露",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 提取纯技术特征（无赔率）
  python scripts/ai/v41_320_temporal_isolation.py --pure-ai

  # 提取混合特征（技术 + 赔率）
  python scripts/ai/v41_320_temporal_isolation.py --with-odds

  # 只提取 2023/2024 赛季
  python scripts/ai/v41_320_temporal_isolation.py --pure-ai --season "2023/2024"

  # 自定义最小历史场次
  python scripts/ai/v41_320_temporal_isolation.py --pure-ai --min-history 3

  # 指定输出目录
  python scripts/ai/v41_320_temporal_isolation.py --pure-ai --output data/pilot_v320_pure
        """,
    )

    parser.add_argument(
        "--pure-ai",
        action="store_true",
        help="纯 AI 模式（不包含赔率特征）",
    )
    parser.add_argument(
        "--with-odds",
        action="store_true",
        help="包含赔率特征（Market-Hybrid）",
    )
    parser.add_argument(
        "--min-history",
        type=int,
        default=5,
        help="最少历史比赛数（默认: 5）",
    )
    parser.add_argument(
        "--season",
        type=str,
        help="赛季过滤（如 '2023/2024'）",
    )
    parser.add_argument(
        "--league",
        type=str,
        help="联赛过滤（如 'Premier League'）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/pilot_v320_pure",
        help="输出目录（默认: data/pilot_v320_pure）",
    )

    args = parser.parse_args()

    # 默认使用纯 AI 模式
    include_odds = args.with_odds

    if args.pure_ai:
        include_odds = False
        args.output = args.output.replace("_pure", "_pure").replace("_hybrid", "_pure")

    if args.with_odds:
        args.output = args.output.replace("_pure", "_hybrid")

    # 执行提取
    extractor = TemporalIsolationExtractor(
        min_history_matches=args.min_history,
        include_odds=include_odds,
        season_filter=args.season,
        league_filter=args.league,
    )

    dataset = extractor.extract()

    # 输出统计
    print("\n" + "=" * 60)
    print("V41.320 时空隔离特征提取报告")
    print("=" * 60)
    print(dataset.stats)
    print(f"\n  数据泄露已移除: YES")
    print(f"  包含赔率特征: {'YES' if include_odds else 'NO'}")
    print("=" * 60)

    # 保存数据集
    if dataset.X.shape[0] > 0:
        dataset.save(args.output)
        print(f"\n数据集已保存到: {args.output}/")
        print(f"  - X_features.npy: 特征矩阵 {dataset.X.shape}")
        print(f"  - y_labels.npy: 标签向量 {dataset.y.shape}")
        print(f"  - metadata.csv: 元数据")
        print(f"  - feature_names.json: 特征名称列表")
        print(f"  - stats.json: 统计信息")
        print("\n✅ 时空隔离特征提取完成！准备进入 Step 2: 模型训练")
    else:
        print("\n❌ 未找到有效样本，请检查数据库")


if __name__ == "__main__":
    main()
