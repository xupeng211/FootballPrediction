#!/usr/bin/env python3
"""
V18.0 赛前特征提取器
提供积分榜排名和近期走势等赛前可获得特征
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class PrematchFeatureExtractor:
    """
    赛前特征提取器

    特征类型:
    1. 积分榜排名特征 (Table Position Features)
       - home_table_position: 主队赛前积分榜排名
       - away_table_position: 客队赛前积分榜排名
       - table_position_diff: 排名差异 (主队排名 - 客队排名)
       - home_points: 主队赛前积分
       - away_points: 客队赛前积分
       - points_diff: 积分差异

    2. 近 5 场走势特征 (Recent Form Features)
       - home_recent_form_points: 主队近 5 场积分 (15/12/9/6/3/0)
       - away_recent_form_points: 客队近 5 场积分
       - home_recent_form_weighted: 主队近 5 场加权积分 (权重递减)
       - away_recent_form_weighted: 客队近 5 场加权积分
       - home_unbeaten_streak: 主队连续不败场次
       - away_unbeaten_streak: 客队连续不败场次
    """

    # V18.0 赛前特征列表（8维）
    PREMATCH_FEATURES = [
        # 积分榜特征（6个）
        "home_table_position",
        "away_table_position",
        "table_position_diff",
        "home_points",
        "away_points",
        "points_diff",
        # 近期走势特征（2个）
        "home_recent_form_points",
        "away_recent_form_points",
    ]

    # 积分规则
    POINTS_MAP = {
        "H": 3,  # 主场获胜
        "A": 3,  # 客场获胜（作为主队时）
        "D": 1,  # 平局
    }

    def __init__(self):
        """初始化特征提取器"""
        self.label_mapping = {"H": 3, "D": 1, "A": 0}  # 主场视角的积分

    def _get_match_points(self, row: pd.Series, team: str) -> int:
        """
        获取指定球队在指定比赛中的积分

        Args:
            row: 比赛数据行
            team: 球队名称

        Returns:
            积分值 (3/1/0)
        """
        home_team = row["home_team"]
        away_team = row["away_team"]
        result = row["actual_result"]

        if team == home_team:
            return self.POINTS_MAP.get(result, 0)
        if team == away_team:
            # 客队视角: H=0, D=1, A=3
            if result == "H":
                return 0
            if result == "D":
                return 1
            if result == "A":
                return 3
        return 0

    def calculate_table_position(self, df: pd.DataFrame, match_idx: int) -> dict[str, int]:
        """
        计算指定比赛时的积分榜排名

        Args:
            df: 按时间排序的比赛数据
            match_idx: 比赛索引

        Returns:
            积分榜特征字典
        """
        # 获取当前比赛之前的所有比赛
        before_matches = df.iloc[:match_idx]

        if len(before_matches) == 0:
            # 第一场比赛，没有历史数据
            return {
                "home_table_position": 10,  # 默认中间位置
                "away_table_position": 10,
                "table_position_diff": 0,
                "home_points": 0,
                "away_points": 0,
                "points_diff": 0,
            }

        current_match = df.iloc[match_idx]
        home_team = current_match["home_team"]
        away_team = current_match["away_team"]

        # 计算每支球队在当前比赛前的积分
        team_points = {}
        team_played = {}

        for _, row in before_matches.iterrows():
            home = row["home_team"]
            away = row["away_team"]
            result = row["actual_result"]

            # 主队积分
            if home not in team_points:
                team_points[home] = 0
                team_played[home] = 0
            team_points[home] += self.POINTS_MAP.get(result, 0)
            team_played[home] += 1

            # 客队积分
            if away not in team_points:
                team_points[away] = 0
                team_played[away] = 0
            if result == "H":
                team_points[away] += 0
            elif result == "D":
                team_points[away] += 1
            elif result == "A":
                team_points[away] += 3
            team_played[away] += 1

        # 计算排名（按积分排序，积分相同按比赛场次排序）
        sorted_teams = sorted(
            team_points.keys(), key=lambda t: (team_points[t], -team_played[t]), reverse=True
        )

        # 获取主客队排名
        home_pos = sorted_teams.index(home_team) + 1 if home_team in sorted_teams else 20
        away_pos = sorted_teams.index(away_team) + 1 if away_team in sorted_teams else 20

        # 获取主客队积分
        home_pts = team_points.get(home_team, 0)
        away_pts = team_points.get(away_team, 0)

        return {
            "home_table_position": home_pos,
            "away_table_position": away_pos,
            "table_position_diff": home_pos - away_pos,
            "home_points": home_pts,
            "away_points": away_pts,
            "points_diff": home_pts - away_pts,
        }

    def calculate_recent_form(
        self, df: pd.DataFrame, match_idx: int, window: int = 5
    ) -> dict[str, float]:
        """
        计算近 N 场走势特征

        Args:
            df: 按时间排序的比赛数据
            match_idx: 比赛索引
            window: 场次窗口

        Returns:
            近期走势特征字典
        """
        current_match = df.iloc[match_idx]
        home_team = current_match["home_team"]
        away_team = current_match["away_team"]
        match_time = current_match["match_time"]

        # 获取主队近 N 场比赛
        home_recent = []
        for i in range(match_idx - 1, max(-1, match_idx - window - 1), -1):
            row = df.iloc[i]
            if row["match_time"] >= match_time:
                continue
            if row["home_team"] == home_team or row["away_team"] == home_team:
                points = self._get_match_points(row, home_team)
                home_recent.append(points)

        # 获取客队近 N 场比赛
        away_recent = []
        for i in range(match_idx - 1, max(-1, match_idx - window - 1), -1):
            row = df.iloc[i]
            if row["match_time"] >= match_time:
                continue
            if row["home_team"] == away_team or row["away_team"] == away_team:
                points = self._get_match_points(row, away_team)
                away_recent.append(points)

        # 计算积分
        home_recent_points = sum(home_recent) if home_recent else 0
        away_recent_points = sum(away_recent) if away_recent else 0

        # 计算加权积分（最近比赛权重更高）
        weights = [1.0, 0.9, 0.8, 0.7, 0.6][: len(home_recent)]
        home_weighted = sum(p * w for p, w in zip(home_recent, weights, strict=False))

        weights = [1.0, 0.9, 0.8, 0.7, 0.6][: len(away_recent)]
        away_weighted = sum(p * w for p, w in zip(away_recent, weights, strict=False))

        # 计算连续不败场次
        home_unbeaten = 0
        for points in home_recent:
            if points > 0:
                home_unbeaten += 1
            else:
                break

        away_unbeaten = 0
        for points in away_recent:
            if points > 0:
                away_unbeaten += 1
            else:
                break

        return {
            "home_recent_form_points": home_recent_points,
            "away_recent_form_points": away_recent_points,
            "home_recent_form_weighted": home_weighted,
            "away_recent_form_weighted": away_weighted,
            "home_unbeaten_streak": home_unbeaten,
            "away_unbeaten_streak": away_unbeaten,
        }

    def extract_prematch_features(self, df: pd.DataFrame, recent_window: int = 5) -> pd.DataFrame:
        """
        提取完整的赛前特征数据集

        Args:
            df: 按时间排序的比赛数据
            recent_window: 近期场次数窗口

        Returns:
            包含赛前特征的 DataFrame
        """
        logger.info("=" * 60)
        logger.info("V18.0 赛前特征提取")
        logger.info("=" * 60)
        logger.info(f"📊 近期窗口: {recent_window} 场")

        prematch_features = []

        for idx in range(len(df)):
            try:
                # 积分榜特征
                table_features = self.calculate_table_position(df, idx)

                # 近期走势特征
                form_features = self.calculate_recent_form(df, idx, recent_window)

                # 合并特征
                features = {
                    "match_id": df.iloc[idx]["external_id"],
                    **table_features,
                    **form_features,
                }

                prematch_features.append(features)

                if (idx + 1) % 50 == 0:
                    logger.info(f"  处理进度: {idx + 1}/{len(df)}")

            except Exception as e:
                logger.warning(f"⚠️  比赛索引 {idx} 提取失败: {e}")
                continue

        result_df = pd.DataFrame(prematch_features)
        logger.info(f"✅ 赛前特征提取完成: {len(result_df)} 场")
        logger.info(f"✅ 特征维度: {len(self.PREMATCH_FEATURES)}")

        return result_df


def main():
    """测试函数"""
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    from src.core.pipeline import V17ProductionPipeline

    # 提取比赛数据
    pipeline = V17ProductionPipeline()
    df = pipeline.extract_match_data()

    # 提取赛前特征
    extractor = PrematchFeatureExtractor()
    extractor.extract_prematch_features(df)

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    sys.exit(main())
