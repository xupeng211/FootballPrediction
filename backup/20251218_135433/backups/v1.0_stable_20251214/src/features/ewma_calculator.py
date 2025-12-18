"""
EWMA计算器 - 指数加权移动平均特征工程
Chief Data Scientist: 基于时间衰减的高性能球队实力评估

核心优势:
- 对数据断档不敏感 (适用于当前39.4%覆盖率)
- 近期比赛权重更高 (捕捉当前状态)
- 计算效率高 (O(n)时间复杂度)
- 数学基础扎实 (统计学经典方法)
"""

import pandas as pd
import numpy as np
from typing import Any
import logging

logger = logging.getLogger(__name__)


class EWMACalculator:
    """
    指数加权移动平均计算器

    核心原理:
    - 近期比赛权重指数级增长
    - 时间序列平滑处理
    - 对数据缺失具有鲁棒性
    """

    def __init__(
        self, spans: list[int] | None = None, min_matches: int = 3, adjust: bool = True
    ):
        """
        初始化EWMA计算器

        Args:
            spans: EWMA跨度列表，控制平滑程度 [5场, 10场, 20场]
            min_matches: 计算EWMA所需的最少比赛数
            adjust: 是否调整初始值
        """
        # 使用默认值避免可变默认参数
        if spans is None:
            spans = [5, 10, 20]

        self.spans = spans
        self.min_matches = min_matches
        self.adjust = adjust

        # EWMA参数计算
        self.alphas = {span: 2 / (span + 1) for span in spans}

        logger.info(f"🧠 EWMA计算器初始化: spans={spans}, min_matches={min_matches}")

    def calculate_points(
        self, home_score: int, away_score: int, is_home: bool
    ) -> float:
        """
        计算比赛得分

        Args:
            home_score: 主队进球
            away_score: 客队进球
            is_home: 是否为主队

        Returns:
            得分 (胜=3, 平=1, 负=0)
        """
        if is_home:
            goal_diff = home_score - away_score
        else:
            goal_diff = away_score - home_score

        if goal_diff > 0:
            return 3.0  # 胜利
        elif goal_diff == 0:
            return 1.0  # 平局
        else:
            return 0.0  # 失败

    def prepare_team_matches(
        self, matches_df: pd.DataFrame, team_id: int, team_name: str
    ) -> pd.DataFrame:
        """
        准备特定球队的比赛数据

        Args:
            matches_df: 比赛数据DataFrame
            team_id: 球队ID
            team_name: 球队名称

        Returns:
            处理后的球队比赛数据
        """
        logger.debug(f"🔍 准备球队 {team_name} (ID: {team_id}) 的比赛数据")

        # 筛选该球队的所有比赛
        team_matches = matches_df[
            (matches_df["home_team_id"] == team_id)
            | (matches_df["away_team_id"] == team_id)
        ].copy()

        # 按时间排序
        team_matches = team_matches.sort_values("match_date").reset_index(drop=True)

        # 添加比赛信息
        team_matches["is_home"] = team_matches["home_team_id"] == team_id
        team_matches["team_goals"] = np.where(
            team_matches["is_home"],
            team_matches["home_score"],
            team_matches["away_score"],
        )
        team_matches["team_conceded"] = np.where(
            team_matches["is_home"],
            team_matches["away_score"],
            team_matches["home_score"],
        )
        team_matches["team_points"] = team_matches.apply(
            lambda row: self.calculate_points(
                row["home_score"], row["away_score"], row["is_home"]
            ),
            axis=1,
        )

        # 添加比赛序号
        team_matches["match_number"] = range(1, len(team_matches) + 1)

        logger.debug(f"✅ 球队 {team_name} 准备完成: {len(team_matches)} 场比赛")

        return team_matches

    def calculate_team_ewma(
        self, team_matches: pd.DataFrame, team_name: str
    ) -> dict[str, Any]:
        """
        计算球队的EWMA指标

        Args:
            team_matches: 球队比赛数据
            team_name: 球队名称

        Returns:
            EWMA指标字典
        """
        if len(team_matches) < self.min_matches:
            logger.warning(
                f"⚠️ 球队 {team_name} 比赛数量不足 ({len(team_matches)} < {self.min_matches})"
            )
            return self._get_empty_ewma_dict(team_name)

        logger.debug(f"📊 计算球队 {team_name} 的EWMA指标")

        # 初始化结果字典
        ewma_results = {
            "team_name": team_name,
            "team_id": (
                team_matches["home_team_id"].iloc[0]
                if team_matches["is_home"].iloc[0]
                else team_matches["away_team_id"].iloc[0]
            ),
            "total_matches": len(team_matches),
            "latest_date": team_matches["match_date"].max(),
            "ewma_features": {},
        }

        # 计算各种跨度的EWMA
        for span in self.spans:
            alpha = self.alphas[span]

            # 计算进球、失球、得分的EWMA
            ewma_goals = (
                team_matches["team_goals"]
                .ewm(alpha=alpha, adjust=self.adjust, min_periods=self.min_matches)
                .mean()
            )

            ewma_conceded = (
                team_matches["team_conceded"]
                .ewm(alpha=alpha, adjust=self.adjust, min_periods=self.min_matches)
                .mean()
            )

            ewma_points = (
                team_matches["team_points"]
                .ewm(alpha=alpha, adjust=self.adjust, min_periods=self.min_matches)
                .mean()
            )

            # 保存最新EWMA值
            ewma_results["ewma_features"][f"ewma_goals_scored_{span}"] = (
                ewma_goals.iloc[-1] if len(ewma_goals) > 0 else 0.0
            )
            ewma_results["ewma_features"][f"ewma_goals_conceded_{span}"] = (
                ewma_conceded.iloc[-1] if len(ewma_conceded) > 0 else 0.0
            )
            ewma_results["ewma_features"][f"ewma_points_{span}"] = (
                ewma_points.iloc[-1] if len(ewma_points) > 0 else 0.0
            )

            logger.debug(
                f"   span={span}: goals={ewma_results['ewma_features'][f'ewma_goals_scored_{span}']:.2f}, "
                f"conceded={ewma_results['ewma_features'][f'ewma_goals_conceded_{span}']:.2f}, "
                f"points={ewma_results['ewma_features'][f'ewma_points_{span}']:.2f}"
            )

        # 计算附加指标
        latest_span = self.spans[0]  # 使用最小跨度计算实时状态

        # 攻击力评级 (基于EWMA进球)
        ewma_results["attack_rating"] = self._calculate_attack_rating(
            ewma_results["ewma_features"][f"ewma_goals_scored_{latest_span}"]
        )

        # 防守力评级 (基于EWMA失球)
        ewma_results["defense_rating"] = self._calculate_defense_rating(
            ewma_results["ewma_features"][f"ewma_goals_conceded_{latest_span}"]
        )

        # 综合实力评级
        ewma_results["overall_rating"] = (
            ewma_results["attack_rating"] + ewma_results["defense_rating"]
        ) / 2

        # 近期状态趋势 (最近5场vs之前10场的对比)
        if len(team_matches) >= 15:
            recent_form = team_matches.tail(5)
            previous_form = team_matches.iloc[-15:-5]

            recent_points_per_game = recent_form["team_points"].mean()
            previous_points_per_game = previous_form["team_points"].mean()

            ewma_results["form_trend"] = (
                recent_points_per_game - previous_points_per_game
            )
        else:
            ewma_results["form_trend"] = 0.0

        logger.debug(f"✅ 球队 {team_name} EWMA计算完成")

        return ewma_results

    def _get_empty_ewma_dict(self, team_name: str) -> dict[str, Any]:
        """获取空的EWMA结果字典"""
        empty_result = {
            "team_name": team_name,
            "team_id": None,
            "total_matches": 0,
            "latest_date": None,
            "ewma_features": {},
            "attack_rating": 0.0,
            "defense_rating": 0.0,
            "overall_rating": 0.0,
            "form_trend": 0.0,
        }

        # 为每个跨度添加空的EWMA特征
        for span in self.spans:
            empty_result["ewma_features"][f"ewma_goals_scored_{span}"] = 0.0
            empty_result["ewma_features"][f"ewma_goals_conceded_{span}"] = 0.0
            empty_result["ewma_features"][f"ewma_points_{span}"] = 0.0

        return empty_result

    def _calculate_attack_rating(self, ewma_goals_scored: float) -> float:
        """
        计算攻击力评级 (0-100分)

        Args:
            ewma_goals_scored: EWMA进球数

        Returns:
            攻击力评级
        """
        # 基于历史数据的评分标准
        if ewma_goals_scored >= 2.5:
            return 90 + min(10, (ewma_goals_scored - 2.5) * 10)  # 90-100分: 超强攻击
        elif ewma_goals_scored >= 2.0:
            return 80 + (ewma_goals_scored - 2.0) * 20  # 80-90分: 强攻击
        elif ewma_goals_scored >= 1.5:
            return 70 + (ewma_goals_scored - 1.5) * 20  # 70-80分: 中等偏上
        elif ewma_goals_scored >= 1.0:
            return 50 + (ewma_goals_scored - 1.0) * 40  # 50-70分: 中等
        elif ewma_goals_scored >= 0.5:
            return 30 + (ewma_goals_scored - 0.5) * 40  # 30-50分: 中等偏下
        else:
            return max(0, ewma_goals_scored * 60)  # 0-30分: 攻击力弱

    def _calculate_defense_rating(self, ewma_goals_conceded: float) -> float:
        """
        计算防守力评级 (0-100分，失球越少分数越高)

        Args:
            ewma_goals_conceded: EWMA失球数

        Returns:
            防守力评级
        """
        # 防守力评分: 失球越少分数越高
        if ewma_goals_conceded <= 0.5:
            return 95  # 铜墙铁壁
        elif ewma_goals_conceded <= 0.8:
            return 90 - (ewma_goals_conceded - 0.5) * 50  # 85-95分
        elif ewma_goals_conceded <= 1.2:
            return 80 - (ewma_goals_conceded - 0.8) * 25  # 70-85分
        elif ewma_goals_conceded <= 1.8:
            return 60 - (ewma_goals_conceded - 1.2) * 33  # 40-70分
        elif ewma_goals_conceded <= 2.5:
            return 20 - (ewma_goals_conceded - 1.8) * 43  # 0-40分
        else:
            return max(0, 20 - (ewma_goals_conceded - 2.5) * 10)  # 防守漏洞

    async def calculate_all_teams_ewma(
        self, matches_df: pd.DataFrame
    ) -> list[dict[str, Any]]:
        """
        计算所有球队的EWMA指标

        Args:
            matches_df: 比赛数据DataFrame

        Returns:
            所有球队的EWMA指标列表
        """
        logger.info(f"🚀 开始计算所有球队EWMA指标 (总比赛数: {len(matches_df)})")

        # 获取所有唯一球队
        home_teams = matches_df[["home_team_id", "home_team_name"]].drop_duplicates()
        away_teams = matches_df[["away_team_id", "away_team_name"]].drop_duplicates()

        # 重命名列以便合并
        home_teams.columns = ["team_id", "team_name"]
        away_teams.columns = ["team_id", "team_name"]

        # 合并获取所有球队
        all_teams = pd.concat([home_teams, away_teams]).drop_duplicates(
            subset=["team_id"]
        )

        logger.info(f"📊 发现 {len(all_teams)} 个独特球队")

        # 计算每个球队的EWMA
        all_ewma_results = []

        for idx, (_, team_row) in enumerate(all_teams.iterrows()):
            team_id = team_row["team_id"]
            team_name = team_row["team_name"]

            logger.info(f"🔧 处理球队 {idx + 1}/{len(all_teams)}: {team_name}")

            # 准备球队比赛数据
            team_matches = self.prepare_team_matches(matches_df, team_id, team_name)

            # 计算EWMA指标
            ewma_result = self.calculate_team_ewma(team_matches, team_name)
            all_ewma_results.append(ewma_result)

        logger.info(f"✅ 所有球队EWMA计算完成，共 {len(all_ewma_results)} 个球队")

        return all_ewma_results

    def generate_features_dataframe(
        self, ewma_results: list[dict[str, Any]]
    ) -> pd.DataFrame:
        """
        生成特征DataFrame

        Args:
            ewma_results: EWMA结果列表

        Returns:
            特征DataFrame
        """
        logger.info(f"📊 生成特征DataFrame ({len(ewma_results)} 个球队)")

        # 展开ewma_features
        features_data = []

        for result in ewma_results:
            team_features = {
                "team_id": result["team_id"],
                "team_name": result["team_name"],
                "total_matches": result["total_matches"],
                "latest_date": result["latest_date"],
                "attack_rating": result["attack_rating"],
                "defense_rating": result["defense_rating"],
                "overall_rating": result["overall_rating"],
                "form_trend": result["form_trend"],
            }

            # 添加EWMA特征
            team_features.update(result["ewma_features"])

            features_data.append(team_features)

        df = pd.DataFrame(features_data)

        # 按综合实力排序
        df = df.sort_values("overall_rating", ascending=False)

        logger.info(f"✅ 特征DataFrame生成完成: {df.shape}")

        return df

    def print_summary_statistics(self, features_df: pd.DataFrame):
        """
        打印EWMA特征统计摘要

        Args:
            features_df: 特征DataFrame
        """
        logger.info("📋 EWMA特征统计摘要:")

        top_teams = features_df.nlargest(10, "overall_rating")[
            ["team_name", "overall_rating", "attack_rating", "defense_rating"]
        ]
        for _, _team in top_teams.iterrows():
            pass

        # EWMA特征统计
        ewma_cols = [col for col in features_df.columns if "ewma_" in col]
        if ewma_cols:
            features_df[ewma_cols].describe().round(3)
