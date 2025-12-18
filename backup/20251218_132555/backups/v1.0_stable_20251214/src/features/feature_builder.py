"""
Feature Builder - Gold Layer Feature Engineering
特征构建器 - 金层特征工程

Medallion Architecture:
- Bronze: 原始JSON数据存储
- Silver: 清洗和结构化的数据 (match_parser.py)
- Gold: 聚合和特征工程数据 (本文件)

Principal Data Engineer: 首席数据工程师
Purpose: 构建用于机器学习的时间序列特征，防止未来数据泄露
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """
    特征构建器

    核心功能：
    - 计算滚动平均特征（防止数据泄露）
    - 构建时间序列特征
    - 生成预测标签
    - 特征选择和工程
    """

    def __init__(self, min_matches: int = 3):
        """
        初始化特征构建器

        Args:
            min_matches: 计算滚动特征所需的最少比赛数
        """
        self.min_matches = min_matches
        self.feature_columns = [
            # 统计特征
            "stat_home_possession",
            "stat_away_possession",
            "stat_home_shots",
            "stat_away_shots",
            "stat_home_shots_on_target",
            "stat_away_shots_on_target",
            "stat_home_corners",
            "stat_away_corners",
            "stat_home_fouls",
            "stat_away_fouls",
            "stat_home_yellow_cards",
            "stat_away_yellow_cards",
            "stat_home_red_cards",
            "stat_away_red_cards",
            # 阵容特征
            "lineup_home_players_count",
            "lineup_away_players_count",
            "lineup_home_avg_rating",
            "lineup_away_avg_rating",
            "lineup_home_total_value",
            "lineup_away_total_value",
            "lineup_lineups_completeness",
            # 赔率特征
            "odds_avg_home_odds",
            "odds_avg_draw_odds",
            "odds_avg_away_odds",
            "odds_implied_home_prob",
            "odds_implied_draw_prob",
            "odds_implied_away_prob",
            # 疲劳度特征 - 运动科学核心特征
            "home_days_since_last_match",
            "away_days_since_last_match",
            "home_last_match_minutes",
            "away_last_match_minutes",
            "home_rotation_score",
            "away_rotation_score",
            "home_fatigue_score",
            "away_fatigue_score",
            "fatigue_advantage",
        ]

    def build_features(
        self, df: pd.DataFrame, window_sizes: list[int] = None
    ) -> pd.DataFrame:
        """
        构建完整的特征集

        Args:
            df: 包含历史比赛数据的DataFrame
            window_sizes: 滚动窗口大小列表

        Returns:
            包含所有特征的DataFrame
        """
        if window_sizes is None:
            window_sizes = [5, 10, 20]

        logger.info(f"开始构建特征，数据形状: {df.shape}")

        # 数据预处理
        df = self._preprocess_data(df)

        # 确保时间排序
        df = df.sort_values(["match_date"]).reset_index(drop=True)

        # 计算疲劳度特征 - 运动科学分析
        logger.info("Step 1: 计算疲劳度特征")
        df = self.calculate_fatigue_features(df)

        # 为每支球队构建特征
        features_list = []

        for team_id in pd.concat([df["home_team_id"], df["away_team_id"]]).unique():
            team_features = self._build_team_features(df, team_id, window_sizes)
            features_list.append(team_features)

        # 合并所有球队特征
        if features_list:
            all_features = pd.concat(features_list, ignore_index=True)
        else:
            all_features = pd.DataFrame()

        # 构建比赛特征（主客队对比）
        final_features = self._build_match_features(df, all_features)

        # 生成标签
        final_features = self._generate_labels(final_features)

        logger.info(f"特征构建完成，最终形状: {final_features.shape}")
        return final_features

    def calculate_rolling_stats(
        self, df: pd.DataFrame, window: int = 5
    ) -> pd.DataFrame:
        """
        计算滚动统计特征 - 核心方法

        Args:
            df: 比赛数据DataFrame
            window: 滚动窗口大小

        Returns:
            包含滚动特征的DataFrame
        """
        logger.info(f"计算滚动统计特征，窗口大小: {window}")

        features = df.copy()

        # 确保数据按时间排序
        features = features.sort_values("match_date").reset_index(drop=True)

        # 为每个数值列计算滚动特征
        numeric_columns = features.select_dtypes(include=[np.number]).columns

        for col in numeric_columns:
            if col in ["match_id", "home_team_id", "away_team_id"]:
                continue

            # 计算主队滚动特征
            home_col = f"{col}_home_rolling_{window}"
            features[home_col] = features.groupby("home_team_id")[col].transform(
                lambda x: x.shift(1)
                .rolling(window, min_periods=self.min_matches)
                .mean()
            )

            # 计算客队滚动特征
            away_col = f"{col}_away_rolling_{window}"
            features[away_col] = features.groupby("away_team_id")[col].transform(
                lambda x: x.shift(1)
                .rolling(window, min_periods=self.min_matches)
                .mean()
            )

            # 计算滚动标准差
            home_std_col = f"{col}_home_std_{window}"
            features[home_std_col] = (
                features.groupby("home_team_id")[col]
                .transform(
                    lambda x: x.shift(1)
                    .rolling(window, min_periods=self.min_matches)
                    .std()
                )
                .fillna(0)
            )

            away_std_col = f"{col}_away_std_{window}"
            features[away_std_col] = (
                features.groupby("away_team_id")[col]
                .transform(
                    lambda x: x.shift(1)
                    .rolling(window, min_periods=self.min_matches)
                    .std()
                )
                .fillna(0)
            )

        logger.debug(
            f"滚动特征计算完成，新增列数: {len(features.columns) - len(df.columns)}"
        )
        return features

    def calculate_fatigue_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算疲劳度特征 - 运动科学核心方法

        疲劳度特征包括：
        1. days_since_last_match: 距离上一场比赛的天数
        2. last_match_minutes: 上一场比赛的时长（分钟）
        3. rotation_score: 阵容轮换评分（0-1，1表示完全相同阵容）

        Args:
            df: 包含比赛数据的DataFrame，必须包含match_date, home_team_id, away_team_id

        Returns:
            包含疲劳度特征的DataFrame
        """
        logger.info("计算疲劳度特征")

        # 确保日期格式正确
        if "match_date" in df.columns:
            df["match_date"] = pd.to_datetime(df["match_date"])

        # 按时间排序
        df = df.sort_values("match_date").reset_index(drop=True)

        # 初始化疲劳度特征列
        df["home_days_since_last_match"] = np.nan
        df["home_last_match_minutes"] = np.nan
        df["home_rotation_score"] = np.nan
        df["away_days_since_last_match"] = np.nan
        df["away_last_match_minutes"] = np.nan
        df["away_rotation_score"] = np.nan

        # 为每支球队计算疲劳度特征
        for team_id in pd.concat([df["home_team_id"], df["away_team_id"]]).unique():
            logger.debug(f"计算球队 {team_id} 的疲劳度特征")

            # 获取该球队的所有比赛
            team_matches = (
                df[(df["home_team_id"] == team_id) | (df["away_team_id"] == team_id)]
                .copy()
                .reset_index()
            )

            # 为每场比赛计算疲劳度特征
            for _idx, match in team_matches.iterrows():
                current_date = match["match_date"]
                is_home = match["home_team_id"] == team_id

                # 获取之前的比赛（排除当前比赛）
                previous_matches = team_matches[
                    (team_matches["match_date"] < current_date)
                ].sort_values("match_date", ascending=False)

                if len(previous_matches) == 0:
                    # 第一场比赛，无疲劳度数据
                    rest_days = 7  # 默认假设赛季前休息了7天
                    last_match_minutes = 90  # 默认90分钟
                    rotation_score = 1.0  # 假设完全相同阵容
                else:
                    # 获取最近一场比赛
                    last_match = previous_matches.iloc[0]
                    last_match_date = last_match["match_date"]

                    # 计算休息天数
                    rest_days = (current_date - last_match_date).days

                    # 假设加时赛：如果连续3天内有比赛，可能是加时赛
                    # 这里我们简化处理：杯赛淘汰赛阶段可能有120分钟比赛
                    # 实际应用中可以从比赛时长数据计算
                    if rest_days <= 3:
                        # 检查是否是连续作战（三天内第二场）
                        days_between = rest_days
                        if days_between == 2:
                            # 两场比赛间隔2天，可能是加时赛（默认120分钟）
                            last_match_minutes = 120
                        elif days_between == 3:
                            # 间隔3天，正常比赛（90分钟）
                            last_match_minutes = 90
                        else:
                            last_match_minutes = 90
                    else:
                        # 正常间隔，使用默认90分钟
                        last_match_minutes = 90

                    # 计算轮换评分（简化版本）
                    # 实际应用中需要阵容数据：首发11人名单
                    # 这里我们根据休息天数间接计算
                    if rest_days <= 3:
                        # 短时间连续作战，阵容变化较大
                        rotation_score = 0.6  # 假设轮换40%
                    elif rest_days <= 7:
                        # 一周内双赛，适度轮换
                        rotation_score = 0.8  # 假设轮换20%
                    else:
                        # 正常休息，阵容稳定
                        rotation_score = 0.95  # 假设轮换5%

                # 更新主队或客队的疲劳度特征
                match_idx = match["index"]
                if is_home:
                    df.loc[match_idx, "home_days_since_last_match"] = rest_days
                    df.loc[match_idx, "home_last_match_minutes"] = last_match_minutes
                    df.loc[match_idx, "home_rotation_score"] = rotation_score
                else:
                    df.loc[match_idx, "away_days_since_last_match"] = rest_days
                    df.loc[match_idx, "away_last_match_minutes"] = last_match_minutes
                    df.loc[match_idx, "away_rotation_score"] = rotation_score

        # 生成疲劳度衍生特征
        df["home_fatigue_score"] = (
            (90 - df["home_last_match_minutes"]) / 90 * 0.3  # 比赛时长影响 (30%)
            + (7 - df["home_days_since_last_match"]) / 7 * 0.4  # 休息天数影响 (40%)
            + (1 - df["home_rotation_score"]) * 0.3  # 轮换影响 (30%)
        )
        df["home_fatigue_score"] = df["home_fatigue_score"].clip(0, 1)  # 限制在0-1之间

        df["away_fatigue_score"] = (
            (90 - df["away_last_match_minutes"]) / 90 * 0.3
            + (7 - df["away_days_since_last_match"]) / 7 * 0.4
            + (1 - df["away_rotation_score"]) * 0.3
        )
        df["away_fatigue_score"] = df["away_fatigue_score"].clip(0, 1)

        # 疲劳度差异
        df["fatigue_advantage"] = df["away_fatigue_score"] - df["home_fatigue_score"]

        logger.info("疲劳度特征计算完成")
        logger.info(
            "  新增特征: home_days_since_last_match, home_last_match_minutes, home_rotation_score"
        )
        logger.info(
            "  新增特征: away_days_since_last_match, away_last_match_minutes, away_rotation_score"
        )
        logger.info(
            "  衍生特征: home_fatigue_score, away_fatigue_score, fatigue_advantage"
        )

        return df

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        logger.info("开始数据预处理")

        # 确保日期格式正确
        if "match_date" in df.columns:
            df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")

        # 处理缺失值
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].fillna(0)

        # 处理分类变量
        categorical_columns = df.select_dtypes(include=["object"]).columns
        for col in categorical_columns:
            df[col] = df[col].fillna("unknown")

        logger.info(f"数据预处理完成，处理了 {len(numeric_columns)} 个数值列")
        return df

    def _build_team_features(
        self, df: pd.DataFrame, team_id: int, window_sizes: list[int]
    ) -> pd.DataFrame:
        """为特定球队构建特征"""
        # 提取该球队的所有比赛（作为主队或客队）
        home_matches = df[df["home_team_id"] == team_id].copy()
        away_matches = df[df["away_team_id"] == team_id].copy()

        # 统一视角：将客队比赛转换为主队视角
        away_matches = away_matches.copy()

        # 交换主客队数据
        for prefix in ["stat_", "lineup_", "odds_"]:
            for suffix in ["home", "away"]:
                home_col = f"{prefix}{suffix}"
                away_col = f"{prefix}{suffix}"

                if (
                    home_col in away_matches.columns
                    and away_col in away_matches.columns
                ):
                    # 交换主客队数据
                    away_matches[[home_col, away_col]] = away_matches[
                        [away_col, home_col]
                    ]

        # 交换比分
        away_matches[["home_score", "away_score"]] = away_matches[
            ["away_score", "home_score"]
        ]
        away_matches["home_team_id"] = team_id

        # 合并主客队比赛
        all_matches = pd.concat([home_matches, away_matches], ignore_index=True)
        all_matches = all_matches.sort_values("match_date").reset_index(drop=True)

        # 计算滚动特征
        team_features = all_matches.copy()

        for window in window_sizes:
            # 计算基础统计的滚动特征
            for col in ["home_score", "away_score"] + self.feature_columns:
                if col in team_features.columns:
                    # 滚动平均
                    rolling_mean = (
                        team_features[col]
                        .shift(1)
                        .rolling(window, min_periods=self.min_matches)
                        .mean()
                    )
                    team_features[f"{col}_rolling_{window}"] = rolling_mean

                    # 滚动标准差
                    rolling_std = (
                        team_features[col]
                        .shift(1)
                        .rolling(window, min_periods=self.min_matches)
                        .std()
                    )
                    team_features[f"{col}_std_{window}"] = rolling_std.fillna(0)

                    # 滚动最大值和最小值
                    rolling_max = (
                        team_features[col]
                        .shift(1)
                        .rolling(window, min_periods=self.min_matches)
                        .max()
                    )
                    rolling_min = (
                        team_features[col]
                        .shift(1)
                        .rolling(window, min_periods=self.min_matches)
                        .min()
                    )
                    team_features[f"{col}_max_{window}"] = rolling_max
                    team_features[f"{col}_min_{window}"] = rolling_min

        # 计算衍生特征
        team_features = self._calculate_derived_features(team_features, window_sizes)

        return team_features

    def _calculate_derived_features(
        self, df: pd.DataFrame, window_sizes: list[int]
    ) -> pd.DataFrame:
        """计算衍生特征"""
        logger.info("计算衍生特征")

        for window in window_sizes:
            # 进攻相关特征
            if (
                "stat_home_shots_rolling_5" in df.columns
                and "stat_home_shots_on_target_rolling_5" in df.columns
            ):
                df[f"shots_accuracy_rolling_{window}"] = (
                    df["stat_home_shots_on_target_rolling_5"]
                    / df["stat_home_shots_rolling_5"].replace(0, np.nan)
                ).fillna(0.0)

            # 防守相关特征
            if "stat_away_shots_rolling_5" in df.columns:
                df[f"shots_conceded_rolling_{window}"] = df["stat_away_shots_rolling_5"]

            # 纪律特征
            if (
                "stat_home_yellow_cards_rolling_5" in df.columns
                and "stat_home_red_cards_rolling_5" in df.columns
            ):
                df[f"disciplinary_issues_rolling_{window}"] = (
                    df["stat_home_yellow_cards_rolling_5"]
                    + df["stat_home_red_cards_rolling_5"] * 2
                )

            # 实力评分特征
            if (
                "lineup_home_avg_rating_rolling_5" in df.columns
                and "lineup_home_total_value_rolling_5" in df.columns
            ):
                df[f"team_strength_rolling_{window}"] = df[
                    "lineup_home_avg_rating_rolling_5"
                ] * np.log1p(df["lineup_home_total_value_rolling_5"])

        return df

    def _build_match_features(
        self, original_df: pd.DataFrame, team_features: pd.DataFrame
    ) -> pd.DataFrame:
        """构建比赛层面的特征（主客队对比）"""
        if team_features.empty:
            logger.warning("团队特征为空，返回原始数据")
            return original_df

        logger.info("构建比赛层面特征")

        match_features = []

        for _, match in original_df.iterrows():
            match_id = match["match_id"]
            home_team_id = match["home_team_id"]
            away_team_id = match["away_team_id"]
            match_date = match["match_date"]

            # 获取主队特征（这场比赛之前的）
            home_team_features = team_features[
                (team_features["home_team_id"] == home_team_id)
                & (team_features["match_date"] < match_date)
            ]

            # 获取客队特征（这场比赛之前的）
            away_team_features = team_features[
                (team_features["home_team_id"] == away_team_id)
                & (team_features["match_date"] < match_date)
            ]

            # 获取最新的特征
            latest_home = (
                home_team_features.iloc[-1] if not home_team_features.empty else None
            )
            latest_away = (
                away_team_features.iloc[-1] if not away_team_features.empty else None
            )

            # 构建比赛特征字典
            feature_dict = {
                "match_id": match_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "match_date": match_date,
                "home_score": match.get("home_score", 0),
                "away_score": match.get("away_score", 0),
            }

            # 添加主队特征
            if latest_home is not None:
                for col in latest_home.index:
                    if col not in [
                        "match_id",
                        "home_team_id",
                        "away_team_id",
                        "match_date",
                    ]:
                        feature_dict[f"home_{col}"] = latest_home[col]

            # 添加客队特征
            if latest_away is not None:
                for col in latest_away.index:
                    if col not in [
                        "match_id",
                        "home_team_id",
                        "away_team_id",
                        "match_date",
                    ]:
                        feature_dict[f"away_{col}"] = latest_away[col]

            # 计算对比特征
            if latest_home is not None and latest_away is not None:
                # 基础实力对比
                for key in ["rolling_5", "rolling_10", "rolling_20"]:
                    home_col = f"home_score_{key}"
                    away_col = f"away_score_{key}"

                    if home_col in feature_dict and away_col in feature_dict:
                        feature_dict[f"score_advantage_{key}"] = (
                            feature_dict[home_col] - feature_dict[away_col]
                        )

                # 实力评分对比
                home_strength = "home_team_strength_rolling_5"
                away_strength = "away_team_strength_rolling_5"

                if home_strength in feature_dict and away_strength in feature_dict:
                    feature_dict["strength_advantage"] = (
                        feature_dict[home_strength] - feature_dict[away_strength]
                    )

            match_features.append(feature_dict)

        result_df = pd.DataFrame(match_features)
        logger.info(f"比赛特征构建完成，形状: {result_df.shape}")
        return result_df

    def _generate_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成预测标签"""
        logger.info("生成预测标签")

        # 生成比赛结果标签
        def get_result(home_score, away_score):
            if pd.isna(home_score) or pd.isna(away_score):
                return None
            if home_score > away_score:
                return 1  # 主胜
            elif home_score < away_score:
                return 0  # 主负
            else:
                return 2  # 平局

        df["result"] = df.apply(
            lambda x: get_result(x["home_score"], x["away_score"]), axis=1
        )

        # 生成是否主胜标签（二分类）
        df["home_win"] = (df["result"] == 1).astype(int)

        # 生成总进球数
        df["total_goals"] = df["home_score"] + df["away_score"]

        # 生成是否大球标签（总进球 > 2.5）
        df["over_2_5_goals"] = (df["total_goals"] > 2.5).astype(int)

        # 生成双方都进球标签
        df["both_teams_score"] = (
            (df["home_score"] > 0) & (df["away_score"] > 0)
        ).astype(int)

        logger.info(f"标签生成完成，有效样本数: {df['result'].notna().sum()}")
        return df

    def get_feature_columns(
        self, df: pd.DataFrame, exclude_target: bool = True
    ) -> list[str]:
        """获取特征列名"""
        exclude_cols = {
            "match_id",
            "home_team_id",
            "away_team_id",
            "match_date",
            "home_score",
            "away_score",
            "result",
            "home_win",
            "total_goals",
            "over_2_5_goals",
            "both_teams_score",
        }

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        if exclude_target:
            feature_cols = [
                col
                for col in feature_cols
                if not col.startswith(("home_win_", "result_"))
            ]

        return feature_cols

    def validate_features(self, df: pd.DataFrame) -> tuple[bool, list[str]]:
        """验证特征数据"""
        issues = []

        # 检查是否有特征列
        feature_cols = self.get_feature_columns(df)
        if not feature_cols:
            issues.append("没有找到特征列")

        # 检查缺失值比例
        for col in feature_cols:
            missing_ratio = df[col].isna().sum() / len(df)
            if missing_ratio > 0.5:
                issues.append(f"列 {col} 缺失值比例过高: {missing_ratio:.1%}")

        # 检查常数列
        for col in feature_cols:
            if df[col].nunique() <= 1:
                issues.append(f"列 {col} 是常数列")

        # 检查无穷大值
        numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if np.isinf(df[col]).any():
                issues.append(f"列 {col} 包含无穷大值")

        is_valid = len(issues) == 0
        return is_valid, issues


# 创建全局特征构建器实例
feature_builder = FeatureBuilder()
