"""简化的特征计算器.

实现基础足球预测特征计算，包括：
- 基础信息特征
- 近期战绩特征
- 历史交锋特征
"""

import logging
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SimpleFeatureCalculator:
    """简化的特征计算器."""

    def __init__(self, matches_df: pd.DataFrame):
        """初始化特征计算器.

        Args:
            matches_df: 包含所有比赛数据的DataFrame
        """
        self.matches_df = matches_df.copy()
        self.matches_df["match_date"] = pd.to_datetime(self.matches_df["match_date"])
        # 确保按日期排序
        self.matches_df = self.matches_df.sort_values("match_date").reset_index(
            drop=True
        )
        logger.info(f"已加载 {len(self.matches_df)} 条比赛数据")

    def calculate_match_result(self, row: pd.Series) -> int:
        """计算比赛结果.

        Args:
            row: 比赛数据行

        Returns:
            int: 0=Draw, 1=HomeWin, 2=AwayWin
        """
        home_score = row.get("home_score", 0)
        away_score = row.get("away_score", 0)

        if home_score > away_score:
            return 1  # HomeWin
        elif away_score > home_score:
            return 2  # AwayWin
        else:
            return 0  # Draw

    def get_team_previous_matches(
        self, team_id: int, match_date: datetime, limit: int = 5
    ) -> pd.DataFrame:
        """获取指定球队在特定日期之前的最近比赛.

        Args:
            team_id: 球队ID
            match_date: 当前比赛日期
            limit: 返回的比赛数量限制

        Returns:
            pd.DataFrame: 该队之前的比赛记录
        """
        # 获取该队作为主队或客队的所有比赛，且日期早于当前比赛
        previous_matches = (
            self.matches_df[
                (
                    (self.matches_df["home_team_id"] == team_id)
                    | (self.matches_df["away_team_id"] == team_id)
                )
                & (self.matches_df["match_date"] < match_date)
            ]
            .sort_values("match_date", ascending=False)
            .head(limit)
        )

        return previous_matches

    def calculate_team_recent_stats(
        self, team_id: int, match_date: datetime
    ) -> tuple[int, float]:
        """计算球队近期战绩.

        Args:
            team_id: 球队ID
            match_date: 当前比赛日期

        Returns:
            tuple[int, float]: (最近5场积分, 最近5场平均进球数)
        """
        previous_matches = self.get_team_previous_matches(team_id, match_date, 5)

        if len(previous_matches) == 0:
            return 0, 0.0

        total_points = 0
        total_goals = 0

        for _, match in previous_matches.iterrows():
            # 判断该队是主队还是客队
            if match["home_team_id"] == team_id:
                team_score = match["home_score"]
            else:
                team_score = match["away_score"]

            opponent_score = (
                match["away_score"]
                if match["home_team_id"] == team_id
                else match["home_score"]
            )

            # 计算积分
            if team_score > opponent_score:
                total_points += 3  # 胜利
            elif team_score == opponent_score:
                total_points += 1  # 平局

            # 计算进球数
            total_goals += team_score or 0

        avg_goals = total_goals / len(previous_matches)

        return total_points, avg_goals

    def calculate_team_rest_days(self, team_id: int, match_date: datetime) -> int:
        """计算球队休息天数.

        Args:
            team_id: 球队ID
            match_date: 当前比赛日期

        Returns:
            int: 休息天数（最大值为14天）
        """
        # 获取上一场比赛
        previous_match = self.get_team_previous_matches(team_id, match_date, 1)

        if len(previous_match) == 0:
            # 赛季首场，默认充分休息
            return 14

        last_match_date = previous_match.iloc[0]["match_date"]
        rest_days = (match_date - last_match_date).days

        # 最大值为14天
        return min(rest_days, 14)

    def calculate_team_advanced_stats(
        self, team_id: int, match_date: datetime
    ) -> tuple[int, float, int, float]:
        """计算球队高级统计特征.

        Args:
            team_id: 球队ID
            match_date: 当前比赛日期

        Returns:
            tuple[int, float, int, float]: (最近5场净胜球, 最近5场胜率, 当前连胜场次, 休息天数)
        """
        previous_matches = self.get_team_previous_matches(team_id, match_date, 5)

        if len(previous_matches) == 0:
            return 0, 0.0, 0, 14

        # 净胜球和胜率计算
        goal_diff_sum = 0
        wins = 0
        total_matches = len(previous_matches)

        for _, match in previous_matches.iterrows():
            # 判断该队是主队还是客队
            if match["home_team_id"] == team_id:
                team_score = match["home_score"]
                opponent_score = match["away_score"]
            else:
                team_score = match["away_score"]
                opponent_score = match["home_score"]

            # 净胜球
            goal_diff = (team_score or 0) - (opponent_score or 0)
            goal_diff_sum += goal_diff

            # 胜率统计
            if team_score > opponent_score:
                wins += 1

        win_rate = wins / total_matches

        # 计算当前连胜场次（需要查看更多历史记录）
        win_streak = self.calculate_win_streak(team_id, match_date)

        # 休息天数
        rest_days = self.calculate_team_rest_days(team_id, match_date)

        return goal_diff_sum, win_rate, win_streak, rest_days

    def calculate_win_streak(self, team_id: int, match_date: datetime) -> int:
        """计算当前连胜场次.

        Args:
            team_id: 球队ID
            match_date: 当前比赛日期

        Returns:
            int: 连胜场次（正数为连胜，负数为连败，0为无连胜）
        """
        previous_matches = self.get_team_previous_matches(
            team_id, match_date, 20
        )  # 查看更多历史记录

        if len(previous_matches) == 0:
            return 0

        streak = 0
        for _, match in previous_matches.iterrows():
            # 判断该队是主队还是客队
            if match["home_team_id"] == team_id:
                team_score = match["home_score"]
                opponent_score = match["away_score"]
            else:
                team_score = match["away_score"]
                opponent_score = match["home_score"]

            # 判断比赛结果
            if team_score > opponent_score:
                if streak >= 0:
                    streak += 1
                else:
                    streak = 1  # 重置为连胜
            elif team_score < opponent_score:
                if streak <= 0:
                    streak -= 1
                else:
                    streak = -1  # 重置为连败
            else:  # 平局
                break  # 连胜/连败被平局打断

        return streak

    def get_h2h_matches(
        self, home_team_id: int, away_team_id: int, match_date: datetime, limit: int = 3
    ) -> pd.DataFrame:
        """获取两支球队历史交锋记录.

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            match_date: 当前比赛日期
            limit: 返回的比赛数量限制

        Returns:
            pd.DataFrame: 历史交锋记录
        """
        # 获取两支球队的历史交锋记录（不考虑主客场）
        h2h_matches = (
            self.matches_df[
                (
                    (
                        (self.matches_df["home_team_id"] == home_team_id)
                        & (self.matches_df["away_team_id"] == away_team_id)
                    )
                    | (
                        (self.matches_df["home_team_id"] == away_team_id)
                        & (self.matches_df["away_team_id"] == home_team_id)
                    )
                )
                & (self.matches_df["match_date"] < match_date)
            ]
            .sort_values("match_date", ascending=False)
            .head(limit)
        )

        return h2h_matches

    def calculate_h2h_stats(
        self, home_team_id: int, away_team_id: int, match_date: datetime
    ) -> int:
        """计算历史交锋统计.

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            match_date: 当前比赛日期

        Returns:
            int: 最近3次交手中主队获胜次数
        """
        h2h_matches = self.get_h2h_matches(home_team_id, away_team_id, match_date, 3)

        home_wins = 0

        for _, match in h2h_matches.iterrows():
            # 判断主队在哪一方
            if match["home_team_id"] == home_team_id:
                # 主队就是home_team_id
                if match["home_score"] > match["away_score"]:
                    home_wins += 1
            else:
                # 主队是away_team_id（也就是客队在当前比赛中）
                if match["away_score"] > match["home_score"]:
                    home_wins += 1

        return home_wins

    def calculate_features_for_match(self, row: pd.Series) -> dict:
        """为单场比赛计算所有特征.

        Args:
            row: 比赛数据行

        Returns:
            dict: 包含所有特征的字典
        """
        features = {}

        # 基础信息特征
        features["match_id"] = row["match_id"]  # 添加match_id字段
        features["home_team_id"] = row["home_team_id"]
        features["away_team_id"] = row["away_team_id"]
        features["match_date"] = row["match_date"]
        features["match_result"] = self.calculate_match_result(row)

        # 近期战绩特征
        home_points, home_avg_goals = self.calculate_team_recent_stats(
            row["home_team_id"], row["match_date"]
        )
        away_points, away_avg_goals = self.calculate_team_recent_stats(
            row["away_team_id"], row["match_date"]
        )

        features["home_last_5_points"] = home_points
        features["away_last_5_points"] = away_points
        features["home_last_5_avg_goals"] = home_avg_goals
        features["away_last_5_avg_goals"] = away_avg_goals

        # 高级特征：体能、实力、士气
        home_advanced = self.calculate_team_advanced_stats(
            row["home_team_id"], row["match_date"]
        )
        away_advanced = self.calculate_team_advanced_stats(
            row["away_team_id"], row["match_date"]
        )

        # 解包高级特征
        (home_goal_diff, home_win_rate, home_win_streak, home_rest_days) = home_advanced
        (away_goal_diff, away_win_rate, away_win_streak, away_rest_days) = away_advanced

        # 实力特征：净胜球
        features["home_last_5_goal_diff"] = home_goal_diff
        features["away_last_5_goal_diff"] = away_goal_diff

        # 士气特征：连胜场次
        features["home_win_streak"] = home_win_streak
        features["away_win_streak"] = away_win_streak

        # 胜率特征
        features["home_last_5_win_rate"] = home_win_rate
        features["away_last_5_win_rate"] = away_win_rate

        # 体能特征：休息天数
        features["home_rest_days"] = home_rest_days
        features["away_rest_days"] = away_rest_days

        # 历史交锋特征
        h2h_home_wins = self.calculate_h2h_stats(
            row["home_team_id"], row["away_team_id"], row["match_date"]
        )
        features["h2h_last_3_home_wins"] = h2h_home_wins

        return features

    def generate_features_dataset(self) -> pd.DataFrame:
        """生成包含所有特征的完整数据集.

        Returns:
            pd.DataFrame: 包含所有特征的数据集
        """
        features_list = []

        logger.info("开始计算特征...")

        for idx, row in self.matches_df.iterrows():
            if idx % 50 == 0:
                logger.info(f"已处理 {idx}/{len(self.matches_df)} 条记录")

            try:
                features = self.calculate_features_for_match(row)
                features_list.append(features)
            except Exception as e:
                logger.error(f"计算第 {idx} 条记录特征失败: {e}")
                continue

        logger.info("特征计算完成")

        return pd.DataFrame(features_list)

    def validate_features(self, features_df: pd.DataFrame) -> bool:
        """验证生成的特征数据.

        Args:
            features_df: 特征数据DataFrame

        Returns:
            bool: 验证是否通过
        """
        # 检查必需的列是否存在（包含新的高级特征）
        required_columns = [
            "home_team_id",
            "away_team_id",
            "match_date",
            "match_result",
            "home_last_5_points",
            "away_last_5_points",
            "home_last_5_avg_goals",
            "away_last_5_avg_goals",
            "h2h_last_3_home_wins",
            # 新增的高级特征
            "home_last_5_goal_diff",
            "away_last_5_goal_diff",
            "home_win_streak",
            "away_win_streak",
            "home_last_5_win_rate",
            "away_last_5_win_rate",
            "home_rest_days",
            "away_rest_days",
        ]

        missing_columns = [
            col for col in required_columns if col not in features_df.columns
        ]
        if missing_columns:
            logger.error(f"缺少必需的特征列: {missing_columns}")
            return False

        # 检查数据是否为空
        if len(features_df) == 0:
            logger.error("生成的特征数据为空")
            return False

        # 检查第一场比赛的特征（应该是0或默认值）
        first_match = features_df.iloc[0]
        if (
            first_match["home_last_5_points"] != 0
            or first_match["away_last_5_points"] != 0
        ):
            logger.warning("第一场比赛的近期积分不为0，可能存在数据泄露")

        # 验证新特征的合理性
        logger.info("=== 高级特征统计 ===")
        logger.info(f"休息天数分布: 主队 {features_df['home_rest_days'].describe()}")
        logger.info(
            f"净胜球分布: 主队 {features_df['home_last_5_goal_diff'].describe()}"
        )
        logger.info(f"胜率分布: 主队 {features_df['home_last_5_win_rate'].describe()}")
        logger.info(f"连胜分布: 主队 {features_df['home_win_streak'].describe()}")

        logger.info(
            f"特征验证通过，共生成 {len(features_df)} 条特征记录，包含 {len(required_columns) - 4} 个预测特征"
        )
        return True


def load_data_from_database() -> pd.DataFrame:
    """从数据库加载比赛数据."""
    try:
        import os
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # 优先读取环境变量 DATABASE_URL
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            # 回退逻辑：使用单独的环境变量
            db_user = os.getenv("POSTGRES_USER", "postgres")
            db_password = os.getenv("POSTGRES_PASSWORD", "football_prediction_2024")
            db_host = os.getenv("DB_HOST", "db")  # Docker里是 db，不是localhost
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("POSTGRES_DB", "football_prediction")
            db_url = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )

        # Pandas 需要同步驱动，移除 asyncpg
        if "+asyncpg" in db_url:
            db_url = db_url.replace("+asyncpg", "")

        conn = psycopg2.connect(db_url)
        query = """
        SELECT
            m.id as match_id,
            m.home_team_id,
            m.away_team_id,
            m.home_score,
            m.away_score,
            m.status,
            m.match_date,
            t1.name as home_team_name,
            t2.name as away_team_name
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.id
        JOIN teams t2 ON m.away_team_id = t2.id
        WHERE m.status = 'FINISHED'
        ORDER BY m.match_date
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        logger.info(f"从数据库加载了 {len(df)} 条比赛记录")
        return df

    except Exception as e:
        logger.error(f"从数据库加载数据失败: {e}")
        # 返回空DataFrame或抛出异常
        return pd.DataFrame()


def save_features_to_csv(
    features_df: pd.DataFrame, filepath: str = "data/dataset_v1.csv"
):
    """将特征数据保存为CSV文件.

    Args:
        features_df: 特征数据DataFrame
        filepath: 保存路径
    """
    try:
        # 确保目录存在
        import os

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        features_df.to_csv(filepath, index=False)
        logger.info(f"特征数据已保存到 {filepath}")

        # 显示前几行数据
        logger.info("特征数据预览:")
        logger.debug(f"特征数据前几行:\n{features_df.head()}")
        logger.info(f"数据形状: {features_df.shape}")
        logger.info(f"特征列: {list(features_df.columns)}")

    except Exception as e:
        logger.error(f"保存特征数据失败: {e}")
        raise
