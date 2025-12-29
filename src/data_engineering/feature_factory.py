"""
V35.0 生产级特征工厂 - 核心架构固化版
==========================================

整合经过验证的核心特征工程逻辑：
- ELO Engine (K=32)
- Dynamic Table Manager (积分榜)
- Fatigue Tracker (疲劳度)
- Efficiency Engine (战术效率)

作者: V35.0 Architecture Team
日期: 2025-12-28
版本: V35.0 Production
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ELOEngine:
    """
    ELO 评分引擎

    算法: 标准 ELO 更新公式
    - K 因子: 32
    - 初始分: 1500
    - 预期胜率: E_a = 1 / (1 + 10^((R_b - R_a) / 400))
    - 更新: R'_a = R_a + K * (S_a - E_a)
    """

    k_factor: float = 32.0
    initial_rating: float = 1500.0
    ratings: dict[str, float] = field(default_factory=dict)

    def get_rating(self, team: str) -> float:
        """获取球队当前 ELO 评分"""
        if team not in self.ratings:
            self.ratings[team] = self.initial_rating
        return self.ratings[team]

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """计算预期胜率"""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def update(self, home_team: str, away_team: str, result: str) -> tuple[float, float]:
        """
        根据比赛结果更新 ELO 评分

        Args:
            home_team: 主队名称
            away_team: 客队名称
            result: 比赛结果 ('home', 'draw', 'away')

        Returns:
            (home_rating_new, away_rating_new) 更新后的评分
        """
        rating_home = self.get_rating(home_team)
        rating_away = self.get_rating(away_team)

        # 主场优势调整
        home_advantage = 20.0
        e_home = self.expected_score(rating_home + home_advantage, rating_away)
        e_away = 1.0 - e_home

        # 实际得分
        if result == "home":
            s_home, s_away = 1.0, 0.0
        elif result == "away":
            s_home, s_away = 0.0, 1.0
        else:  # draw
            s_home, s_away = 0.5, 0.5

        # 更新评分
        self.ratings[home_team] = rating_home + self.k_factor * (s_home - e_home)
        self.ratings[away_team] = rating_away + self.k_factor * (s_away - e_away)

        return self.ratings[home_team], self.ratings[away_team]

    def get_pre_match_ratings(self, home_team: str, away_team: str) -> tuple[float, float, float]:
        """
        获取赛前 ELO 评分（不更新）

        Returns:
            (home_rating, away_rating, gap)
        """
        rating_home = self.get_rating(home_team)
        rating_away = self.get_rating(away_team)
        gap = rating_home - rating_away
        return rating_home, rating_away, gap


@dataclass
class TableManager:
    """
    动态积分榜管理器

    实时跟踪每支球队的:
    - 比赛场次
    - 积分 (3/1/0)
    - 进球数
    - 失球数
    - 净胜球
    - 排名
    """

    @dataclass
    class TeamRecord:
        matches: int = 0
        points: int = 0
        goals_for: int = 0
        goals_against: int = 0

        @property
        def goal_difference(self) -> int:
            return self.goals_for - self.goals_against

    records: dict[str, TeamRecord] = field(default_factory=dict)

    def get_record(self, team: str) -> TeamRecord:
        """获取球队记录"""
        if team not in self.records:
            self.records[team] = self.TeamRecord()
        return self.records[team]

    def get_pre_match_stats(self, team: str) -> tuple[int, int, int, int, int]:
        """
        获取赛前统计（不更新）

        Returns:
            (matches, points, gf, ga, gd)
        """
        record = self.get_record(team)
        return (
            record.matches,
            record.points,
            record.goals_for,
            record.goals_against,
            record.goal_difference,
        )

    def update_by_result(self, home_team: str, away_team: str, result: str) -> None:
        """
        根据比赛结果更新积分榜

        Args:
            home_team: 主队名称
            away_team: 客队名称
            result: 比赛结果 ('home', 'draw', 'away')
        """
        home_rec = self.get_record(home_team)
        home_rec.matches += 1
        if result == "home":
            home_rec.points += 3

        away_rec = self.get_record(away_team)
        away_rec.matches += 1
        if result == "away":
            away_rec.points += 3
        elif result == "draw":
            home_rec.points += 1
            away_rec.points += 1

    def get_rankings(self) -> dict[str, int]:
        """
        计算当前排名

        排序规则:
        1. 积分 (降序)
        2. 场次 (升序 - 同分时场次少排名高)
        """
        teams = list(self.records.keys())
        teams.sort(
            key=lambda t: (
                -self.records[t].points,
                self.records[t].matches,
            )
        )
        return {team: i + 1 for i, team in enumerate(teams)}


@dataclass
class FatigueTracker:
    """
    疲劳度追踪器

    跟踪每支球队的上场比赛时间，计算休息天数
    """

    last_match_date: dict[str, datetime | None] = field(default_factory=dict)

    def get_rest_days(self, team: str, current_date: datetime) -> int:
        """
        获取休息天数

        Returns:
            休息天数（首场比赛返回 7 天默认值）
        """
        if team not in self.last_match_date:
            return 7

        last_date = self.last_match_date[team]
        delta = current_date - last_date
        return max(0, delta.days)

    def update(self, home_team: str, away_team: str, match_date: datetime) -> None:
        """更新比赛日期"""
        self.last_match_date[home_team] = match_date
        self.last_match_date[away_team] = match_date


@dataclass
class EfficiencyEngine:
    """
    战术效率引擎

    计算球队的进攻效率和防守效率
    """

    team_history: dict[str, dict] = field(default_factory=dict)
    window_size: int = 5

    def _get_team_history(self, team: str) -> dict:
        """获取球队历史数据"""
        if team not in self.team_history:
            self.team_history[team] = {
                "recent_matches": [],
                "goals_for": [],
                "goals_against": [],
                "xg_for": [],
                "xg_against": [],
            }
        return self.team_history[team]

    def calculate_scoring_efficiency(self, team: str) -> float:
        """
        计算进攻效率：实际进球 / 预期 xG

        Returns:
            效率值（>1 表示高效，<1 表示低效）
        """
        history = self._get_team_history(team)
        recent = history["recent_matches"][-self.window_size :]

        if not recent:
            return 1.0

        total_goals = sum([r["goals_for"] for r in recent])
        total_xg = sum([r["xg_for"] for r in recent])

        if total_xg < 0.1:
            return 1.0

        return total_goals / total_xg

    def calculate_save_efficiency(self, team: str) -> float:
        """
        计算守门效率：预期失球 / 实际失球

        Returns:
            效率值（>1 表示防守出色）
        """
        history = self._get_team_history(team)
        recent = history["recent_matches"][-self.window_size :]

        if not recent:
            return 1.0

        total_goals_against = sum([r["goals_against"] for r in recent])
        total_xg_against = sum([r["xg_against"] for r in recent])

        if total_goals_against < 0.1:
            return 1.0

        return total_xg_against / total_goals_against

    def calculate_form_momentum(self, team: str) -> float:
        """
        计算近期势头

        Returns:
            近期得分（胜3分，平1分，负0分）
        """
        history = self._get_team_history(team)
        recent = history["recent_matches"][-self.window_size :]

        if not recent:
            return 0.0

        momentum = 0
        for r in recent:
            if r["result"] == "home" and r["is_home"]:
                momentum += 3
            elif r["result"] == "away" and not r["is_home"]:
                momentum += 3
            elif r["result"] == "draw":
                momentum += 1

        return momentum

    def update(self, row: pd.Series) -> None:
        """更新球队历史数据"""
        home_team = row["home_team"]
        away_team = row["away_team"]
        result = row["result"]

        # 提取数据
        home_goals = row.get("home_score", 0)
        away_goals = row.get("away_score", 0)
        home_xg = row.get("home_xg", home_goals)
        away_xg = row.get("away_xg", away_goals)

        # 更新主队历史
        home_history = self._get_team_history(home_team)
        home_history["recent_matches"].append(
            {
                "goals_for": home_goals,
                "goals_against": away_goals,
                "xg_for": home_xg,
                "xg_against": away_xg,
                "result": result,
                "is_home": True,
            }
        )

        # 更新客队历史
        away_history = self._get_team_history(away_team)
        away_history["recent_matches"].append(
            {
                "goals_for": away_goals,
                "goals_against": home_goals,
                "xg_for": away_xg,
                "xg_against": home_xg,
                "result": result,
                "is_home": False,
            }
        )


@dataclass
class FeatureFactory:
    """
    V35.0 生产级特征工厂

    整合 ELO、积分榜、疲劳度、效率引擎
    按时间顺序生成真实的赛前特征
    """

    elo_engine: ELOEngine = field(default_factory=ELOEngine)
    table_manager: TableManager = field(default_factory=TableManager)
    fatigue_tracker: FatigueTracker = field(default_factory=FatigueTracker)
    efficiency_engine: EfficiencyEngine = field(default_factory=EfficiencyEngine)

    # V35.0 核心特征列表
    V35_FEATURES: list[str] = field(
        default_factory=lambda: [
            # ELO 特征
            "home_elo_pre",
            "away_elo_pre",
            "elo_gap_pre",
            # 积分榜特征
            "home_points_pre",
            "away_points_pre",
            "points_diff_pre",
            "home_rank_pre",
            "away_rank_pre",
            "rank_diff_pre",
            # 疲劳度特征
            "home_rest_days_pre",
            "away_rest_days_pre",
            "rest_days_diff_pre",
            # 效率特征
            "home_scoring_efficiency",
            "away_scoring_efficiency",
            "scoring_efficiency_diff",
            "home_save_efficiency",
            "away_save_efficiency",
            "save_efficiency_diff",
            "home_form_momentum",
            "away_form_momentum",
            "momentum_diff",
        ]
    )

    def process_match(self, row: pd.Series) -> dict:
        """
        处理单场比赛

        流程:
        1. 提取赛前特征（ELO、积分榜、疲劳度、效率）
        2. 比赛结束后更新所有引擎状态

        Args:
            row: 比赛数据行

        Returns:
            赛前特征字典
        """
        match_date = pd.to_datetime(row["match_date"])
        home_team = row["home_team"]
        away_team = row["away_team"]
        result = row["result"]

        # 步骤 1: 提取赛前特征
        pre_features = {}

        # ELO 特征
        home_elo, away_elo, elo_gap = self.elo_engine.get_pre_match_ratings(home_team, away_team)
        pre_features["home_elo_pre"] = home_elo
        pre_features["away_elo_pre"] = away_elo
        pre_features["elo_gap_pre"] = elo_gap

        # 积分榜特征
        (
            home_matches,
            home_points,
            home_gf,
            home_ga,
            home_gd,
        ) = self.table_manager.get_pre_match_stats(home_team)
        (
            away_matches,
            away_points,
            away_gf,
            away_ga,
            away_gd,
        ) = self.table_manager.get_pre_match_stats(away_team)

        pre_features["home_points_pre"] = home_points
        pre_features["away_points_pre"] = away_points
        pre_features["points_diff_pre"] = home_points - away_points

        # 排名
        rankings = self.table_manager.get_rankings()
        pre_features["home_rank_pre"] = rankings.get(home_team, 999)
        pre_features["away_rank_pre"] = rankings.get(away_team, 999)
        pre_features["rank_diff_pre"] = pre_features["away_rank_pre"] - pre_features["home_rank_pre"]

        # 疲劳度特征
        home_rest = self.fatigue_tracker.get_rest_days(home_team, match_date)
        away_rest = self.fatigue_tracker.get_rest_days(away_team, match_date)
        pre_features["home_rest_days_pre"] = home_rest
        pre_features["away_rest_days_pre"] = away_rest
        pre_features["rest_days_diff_pre"] = home_rest - away_rest

        # 效率特征
        home_se = self.efficiency_engine.calculate_scoring_efficiency(home_team)
        away_se = self.efficiency_engine.calculate_scoring_efficiency(away_team)
        pre_features["home_scoring_efficiency"] = home_se
        pre_features["away_scoring_efficiency"] = away_se
        pre_features["scoring_efficiency_diff"] = home_se - away_se

        home_save = self.efficiency_engine.calculate_save_efficiency(home_team)
        away_save = self.efficiency_engine.calculate_save_efficiency(away_team)
        pre_features["home_save_efficiency"] = home_save
        pre_features["away_save_efficiency"] = away_save
        pre_features["save_efficiency_diff"] = home_save - away_save

        home_mom = self.efficiency_engine.calculate_form_momentum(home_team)
        away_mom = self.efficiency_engine.calculate_form_momentum(away_team)
        pre_features["home_form_momentum"] = home_mom
        pre_features["away_form_momentum"] = away_mom
        pre_features["momentum_diff"] = home_mom - away_mom

        # 步骤 2: 比赛结束后更新状态
        self.elo_engine.update(home_team, away_team, result)
        self.table_manager.update_by_result(home_team, away_team, result)
        self.fatigue_tracker.update(home_team, away_team, match_date)
        self.efficiency_engine.update(row)

        return pre_features

    def build_all_features(self, df: pd.DataFrame, output_path: Path | None = None) -> pd.DataFrame:
        """
        为整个数据集生成特征

        Args:
            df: 原始数据集，必须包含列: match_date, home_team, away_team, result
            output_path: 输出路径（可选）

        Returns:
            增强后的数据集
        """
        logger.info("=" * 70)
        logger.info("V35.0 生产级特征工厂 - 特征生成")
        logger.info("=" * 70)

        # 按时间排序（关键！）
        df_sorted = df.sort_values("match_date").reset_index(drop=True)
        logger.info(f"✅ 数据已按时间排序: {df_sorted['match_date'].min()} ~ {df_sorted['match_date'].max()}")

        # 初始化特征列
        for feat in self.V35_FEATURES:
            df_sorted[feat] = np.nan

        # 逐场比赛处理
        logger.info(f"\n开始处理 {len(df_sorted)} 场比赛...")

        success_count = 0
        failed_count = 0

        for i, row in df_sorted.iterrows():
            try:
                pre_features = self.process_match(row)

                for feat, value in pre_features.items():
                    df_sorted.at[i, feat] = value

                success_count += 1

                if (i + 1) % 1000 == 0:
                    logger.info(f"  进度: {i + 1}/{len(df_sorted)} ({(i + 1) / len(df_sorted) * 100:.1f}%)")

            except Exception as e:
                failed_count += 1
                match_id = row.get("match_id", f"index_{i}")
                logger.warning(f"⚠️  比赛处理失败 (ID: {match_id}, 索引: {i}): {e}")
                # 继续处理下一场比赛，不中断流水线
                continue

        logger.info(f"✅ 特征生成完成: 成功 {success_count}, 失败 {failed_count}")

        if failed_count > 0:
            logger.warning(f"⚠️  有 {failed_count} 场比赛处理失败，已跳过")

        # 验证特征质量
        self._validate_features(df_sorted)

        # 保存数据
        if output_path is None:
            output_path = Path(__file__).parent.parent.parent / "data/processed/V35_PRODUCTION_GOLD.parquet"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_sorted.to_parquet(output_path, index=False)
        logger.info(f"\n✅ 数据已保存: {output_path}")

        return df_sorted

    def _validate_features(self, df: pd.DataFrame) -> None:
        """验证特征质量"""
        logger.info("\n" + "=" * 70)
        logger.info("特征质量验证")
        logger.info("=" * 70)

        logger.info(f"\n【V35.0 核心特征 ({len(self.V35_FEATURES)} 维)】")
        for i, feat in enumerate(self.V35_FEATURES, 1):
            fill_rate = df[feat].notnull().sum() / len(df) * 100
            mean_val = df[feat].mean()
            std_val = df[feat].std()
            logger.info(f"  {i:2d}. {feat:30s}: 填充率 {fill_rate:5.1f}%, 均值 {mean_val:7.2f}, 标准差 {std_val:7.2f}")


def create_feature_factory() -> FeatureFactory:
    """工厂函数：创建特征工厂实例"""
    return FeatureFactory()


# 导出
__all__ = [
    "FeatureFactory",
    "ELOEngine",
    "TableManager",
    "FatigueTracker",
    "EfficiencyEngine",
    "create_feature_factory",
]
