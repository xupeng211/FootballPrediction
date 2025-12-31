#!/usr/bin/env python3
"""
V51.1 赛前特征计算引擎 (Pre-match Feature Calculator)
====================================================
核心功能:
1. 从 raw_match_data 提取 V51.0 原始特征并存储到 feature_snapshots
2. 计算赛前滚动统计 (实力底蕴、即时状态、主客场、疲劳度)
3. 存储到 prematch_features 表
4. 确保时空隔离 (before_match_time 约束)

Author: ML Platform Team
Version: V51.1
Date: 2025-12-31
"""

import multiprocessing as mp
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import psycopg2
import structlog
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class PreMatchFeatures:
    """赛前特征数据类"""

    # 比赛基础信息
    match_id: str
    match_date: datetime
    home_team: str
    away_team: str
    league_name: str = ""
    season: str = ""

    # 实力底蕴特征 (10 维)
    home_rolling_xg: float | None = None
    home_rolling_xg_std: float | None = None
    home_rolling_shots_on_target: float | None = None
    home_rolling_shots_on_target_std: float | None = None
    home_rolling_possession: float | None = None
    home_rolling_possession_std: float | None = None
    home_rolling_team_rating: float | None = None
    home_rolling_team_rating_std: float | None = None
    rolling_xg_diff: float | None = None
    rolling_possession_diff: float | None = None

    # 即时状态特征 (6 维)
    home_recent_form_points: float | None = None
    home_recent_goals_scored: float | None = None
    home_recent_goals_conceded: float | None = None
    home_recent_win_rate: float | None = None
    home_recent_trend: str | None = None  # 'ascending'/'descending'/'stable'
    momentum_gap: float | None = None

    # 主客场特征 (10 维)
    home_home_win_rate: float | None = None
    home_home_goals_scored: float | None = None
    home_home_goals_conceded: float | None = None
    home_away_win_rate: float | None = None
    home_away_goals_scored: float | None = None
    home_away_goals_conceded: float | None = None
    home_advantage: float | None = None
    away_away_win_rate: float | None = None
    away_away_goals_scored: float | None = None
    away_away_goals_conceded: float | None = None
    venue_bias: float | None = None

    # 疲劳度特征 (8 维)
    home_fatigue_index: float | None = None
    away_fatigue_index: float | None = None
    fatigue_diff: float | None = None
    home_rest_days: float | None = None
    away_rest_days: float | None = None
    rest_days_diff: float | None = None
    home_matches_7days: int | None = None
    away_matches_7days: int | None = None

    # 积分榜特征 (7 维)
    home_table_position: int | None = None
    away_table_position: int | None = None
    table_position_diff: int | None = None
    home_points: float | None = None
    away_points: float | None = None
    points_diff: float | None = None

    # ELO 评分特征 (2 维)
    raw_elo_gap: float | None = None
    adjusted_elo_gap: float | None = None

    # 质量指标
    home_history_count: int = 0
    away_history_count: int = 0
    is_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class PreMatchFeatureCalculator:
    """
    V51.1 赛前特征计算引擎

    核心特性:
    1. 严格时空隔离 (before_match_time 约束)
    2. 可追溯计算 (记录所有中间结果)
    3. 质量自检 (history_count 检查)
    4. 高性能查询 (使用连接池 + 批量处理)
    """

    def __init__(
        self,
        rolling_window: int = 10,
        recent_window: int = 3,
        min_history: int = 5,
        feature_version: str = "V51.1",
    ):
        """
        初始化计算引擎

        Args:
            rolling_window: 滚动窗口大小 (默认 10 场)
            recent_window: 近期窗口大小 (默认 3 场)
            min_history: 最低历史比赛要求
            feature_version: 特征版本
        """
        self.rolling_window = rolling_window
        self.recent_window = recent_window
        self.min_history = min_history
        self.feature_version = feature_version

        # 数据库连接
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

        logger.info(
            "V51.1 赛前特征计算器已初始化",
            rolling_window=rolling_window,
            recent_window=recent_window,
            min_history=min_history,
        )

    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.conn_params)

    def get_team_history(
        self,
        team_name: str,
        before_match_time: datetime,
        venue: str | None = None,  # 'home'/'away'/None(全部)
        conn=None,
    ) -> pd.DataFrame:
        """
        获取球队历史比赛（时空隔离）

        Args:
            team_name: 球队名称
            before_match_time: 时空隔离时间点
            venue: 场地过滤 ('home'/'away'/None)
            conn: 数据库连接

        Returns:
            历史比赛 DataFrame
        """
        should_close = conn is None
        if conn is None:
            conn = self.get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 基础查询
                query = """
                    SELECT
                        m.match_id,
                        m.match_date,
                        m.home_team,
                        m.away_team,
                        m.home_score,
                        m.away_score,
                        m.status,
                        r.raw_data
                    FROM matches m
                    INNER JOIN raw_match_data r
                        ON m.match_id = r.match_id
                    WHERE m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                      AND m.match_date < %s
                """

                params = [before_match_time]

                # 场地过滤
                if venue == "home":
                    query += " AND m.home_team = %s"
                    params.append(team_name)
                elif venue == "away":
                    query += " AND m.away_team = %s"
                    params.append(team_name)
                else:
                    query += " AND (m.home_team = %s OR m.away_team = %s)"
                    params.extend([team_name, team_name])

                # 排序和限制
                query += " ORDER BY m.match_date DESC LIMIT %s"
                params.append(self.rolling_window * 2)  # 多取一些，后续过滤

                cur.execute(query, params)
                rows = cur.fetchall()

                if not rows:
                    return pd.DataFrame()

                # 转换为 DataFrame
                df = pd.DataFrame([dict(row) for row in rows])

                # 提取球队数据（区分主客场）
                df["is_home"] = df["home_team"] == team_name

                # 提取统计指标 - 计算球队和对手的比分
                df["team_score"] = df.apply(
                    lambda row: row["home_score"] if row["is_home"] else row["away_score"],
                    axis=1,
                )
                df["opponent_score"] = df.apply(
                    lambda row: row["away_score"] if row["is_home"] else row["home_score"],
                    axis=1,
                )

                # 计算积分
                df["points"] = df.apply(
                    lambda row: (
                        3
                        if row["team_score"] > row["opponent_score"]
                        else 1
                        if row["team_score"] == row["opponent_score"]
                        else 0
                    ),
                    axis=1,
                )

                return df

        finally:
            if should_close:
                conn.close()

    def extract_stats_from_raw_data(
        self,
        raw_data: dict,
        is_home: bool,
    ) -> dict[str, float]:
        """
        从 raw_match_data.raw_data 提取统计指标

        数据结构:
            raw_data = {
                "stats": {
                    "xg": [home_value, away_value],
                    "possession": [home_value, away_value],
                    "shots_on_target": [home_value, away_value],
                    ...
                }
            }

        Args:
            raw_data: V51.0 原始数据 (JSONB)
            is_home: 是否为主队

        Returns:
            统计指标字典
        """
        stats = {}

        # 获取 stats 字段
        stats_data = raw_data.get("stats", {})
        if not stats_data:
            return stats

        # 数组索引：主队=0，客队=1
        idx = 0 if is_home else 1

        # 提取 xG
        if "xg" in stats_data:
            xg_array = stats_data["xg"]
            if isinstance(xg_array, list) and len(xg_array) > idx:
                try:
                    stats["xg"] = float(xg_array[idx])
                except (ValueError, TypeError):
                    pass

        # 提取射正
        if "shots_on_target" in stats_data:
            shots_array = stats_data["shots_on_target"]
            if isinstance(shots_array, list) and len(shots_array) > idx:
                try:
                    stats["shots_on_target"] = float(shots_array[idx])
                except (ValueError, TypeError):
                    pass

        # 提取控球率
        if "possession" in stats_data:
            possession_array = stats_data["possession"]
            if isinstance(possession_array, list) and len(possession_array) > idx:
                try:
                    stats["possession"] = float(possession_array[idx])
                except (ValueError, TypeError):
                    pass

        # 提取评分
        if "team_rating" in stats_data:
            rating_array = stats_data["team_rating"]
            if isinstance(rating_array, list) and len(rating_array) > idx:
                try:
                    stats["team_rating"] = float(rating_array[idx])
                except (ValueError, TypeError):
                    pass

        return stats

    def calculate_strength_features(
        self,
        history_df: pd.DataFrame,
        is_home: bool,
    ) -> dict[str, float]:
        """
        计算实力底蕴特征 (Past 10 matches average)

        Args:
            history_df: 历史比赛数据
            is_home: 是否为主队

        Returns:
            实力特征字典
        """
        if history_df.empty:
            return {}

        features = {}

        # 提取统计指标
        stats_list = []
        for _, row in history_df.iterrows():
            raw_data = row.get("raw_data", {})
            if isinstance(raw_data, str):
                import json

                raw_data = json.loads(raw_data)
            stats = self.extract_stats_from_raw_data(raw_data, row["is_home"])
            stats_list.append(stats)

        stats_df = pd.DataFrame(stats_list)

        # 计算滚动平均和标准差
        for metric in ["xg", "shots_on_target", "possession", "team_rating"]:
            if metric in stats_df.columns:
                values = stats_df[metric].dropna()
                if len(values) > 0:
                    prefix = "home" if is_home else "away"
                    features[f"{prefix}_rolling_{metric}"] = float(values.mean())
                    features[f"{prefix}_rolling_{metric}_std"] = float(values.std()) if len(values) > 1 else 0.0

        return features

    def calculate_recent_form_features(
        self,
        history_df: pd.DataFrame,
        is_home: bool,
    ) -> dict[str, float]:
        """
        计算即时状态特征 (Past 3 matches trend)

        Args:
            history_df: 历史比赛数据
            is_home: 是否为主队

        Returns:
            状态特征字典
        """
        if history_df.empty:
            return {}

        # 取最近 N 场
        recent_df = history_df.head(self.recent_window)

        features = {}

        prefix = "home" if is_home else "away"

        # 积分
        features[f"{prefix}_recent_form_points"] = float(recent_df["points"].sum())

        # 进球/失球
        features[f"{prefix}_recent_goals_scored"] = float(recent_df["team_score"].sum())
        features[f"{prefix}_recent_goals_conceded"] = float(recent_df["opponent_score"].sum())

        # 胜率
        wins = (recent_df["points"] == 3).sum()
        features[f"{prefix}_recent_win_rate"] = float(wins / len(recent_df))

        # 趋势判断
        if len(recent_df) >= 2:
            recent_points = recent_df["points"].tolist()
            if recent_points[0] > recent_points[-1]:
                features[f"{prefix}_recent_trend"] = "ascending"
            elif recent_points[0] < recent_points[-1]:
                features[f"{prefix}_recent_trend"] = "descending"
            else:
                features[f"{prefix}_recent_trend"] = "stable"
        else:
            features[f"{prefix}_recent_trend"] = "stable"

        return features

    def calculate_venue_features(self, team_name: str, before_match_time: datetime, conn=None) -> dict[str, float]:
        """
        计算主客场特定特征

        Args:
            team_name: 球队名称
            before_match_time: 时空隔离时间点
            conn: 数据库连接

        Returns:
            主客场特征字典
        """
        features = {}

        # 主场数据
        home_df = self.get_team_history(team_name, before_match_time, venue="home", conn=conn)
        if not home_df.empty:
            features["home_home_win_rate"] = float((home_df["points"] == 3).sum() / len(home_df))
            features["home_home_goals_scored"] = float(home_df["team_score"].mean())
            features["home_home_goals_conceded"] = float(home_df["opponent_score"].mean())

        # 客场数据
        away_df = self.get_team_history(team_name, before_match_time, venue="away", conn=conn)
        if not away_df.empty:
            features["home_away_win_rate"] = float((away_df["points"] == 3).sum() / len(away_df))
            features["home_away_goals_scored"] = float(away_df["team_score"].mean())
            features["home_away_goals_conceded"] = float(away_df["opponent_score"].mean())

        return features

    def calculate_fatigue_features(self, team_name: str, before_match_time: datetime, conn=None) -> dict[str, float]:
        """
        计算疲劳度特征

        Args:
            team_name: 球队名称
            before_match_time: 时空隔离时间点
            conn: 数据库连接

        Returns:
            疲劳度特征字典，键名使用 "home" 前缀，由调用方决定是否重命名
        """
        # 获取历史比赛（不限场地）
        history_df = self.get_team_history(team_name, before_match_time, conn=conn)

        if history_df.empty:
            return {}

        features = {}

        # 注意：这里使用 "home" 作为默认前缀
        # 调用方负责将 "home_" 重命名为 "away_"
        prefix = "home"

        # 计算比赛密度
        seven_days_ago = before_match_time - timedelta(days=7)

        # 7 天内比赛数 - 确保比较时都是 datetime 类型
        match_dates = pd.to_datetime(history_df["match_date"])
        matches_7days = history_df[match_dates >= seven_days_ago]
        features[f"{prefix}_matches_7days"] = int(len(matches_7days))

        # 疲劳度指数 (7 天内比赛数 / 7)
        features[f"{prefix}_fatigue_index"] = float(min(len(matches_7days) / 7.0, 1.0))

        # 休息天数 (距离上一场)
        if len(history_df) > 0:
            try:
                last_match_date = pd.to_datetime(history_df.iloc[0]["match_date"])
                if pd.notna(last_match_date):
                    rest_days = (before_match_time - last_match_date).days
                    features[f"{prefix}_rest_days"] = float(rest_days)
                else:
                    features[f"{prefix}_rest_days"] = 999.0
            except Exception:
                features[f"{prefix}_rest_days"] = 999.0
        else:
            features[f"{prefix}_rest_days"] = 999.0  # 无历史，视为充分休息

        return features

    def _compute_team_features(
        self,
        team_name: str,
        before_match_time: datetime,
        is_home_team: bool,
        conn=None,
    ) -> dict[str, Any]:
        """
        计算单个球队的特征（内部辅助函数）

        Args:
            team_name: 球队名称
            before_match_time: 时空隔离时间点
            is_home_team: 是否为主队
            conn: 数据库连接

        Returns:
            特征字典
        """
        features = {}

        history = self.get_team_history(team_name, before_match_time, conn=conn)

        if history.empty:
            return features

        # 实力特征
        strength = self.calculate_strength_features(history, is_home=is_home_team)
        for k, v in strength.items():
            features[k] = v

        # 状态特征
        recent = self.calculate_recent_form_features(history, is_home=is_home_team)
        for k, v in recent.items():
            features[k] = v

        # 主客场特征
        venue = self.calculate_venue_features(team_name, before_match_time, conn=conn)
        for k, v in venue.items():
            if is_home_team:
                # 主队: 保持原键名 (home_home_*, home_away_*)
                features[k] = v
            else:
                # 客队: 重命名 (home_home_* → away_home_*, home_away_* → away_away_*)
                if k.startswith("home_home_"):
                    features[k.replace("home_home_", "away_home_")] = v
                elif k.startswith("home_away_"):
                    features[k.replace("home_away_", "away_away_")] = v

        # 疲劳度特征
        fatigue = self.calculate_fatigue_features(team_name, before_match_time, conn=conn)
        for k, v in fatigue.items():
            if is_home_team:
                # 主队: 保持原键名 (home_*)
                features[k] = v
            else:
                # 客队: 重命名 (home_* → away_*)
                features[k.replace("home_", "away_")] = v

        return features

    def _compute_difference_features(self, features: PreMatchFeatures) -> None:
        """
        计算差值特征（内部辅助函数）

        Args:
            features: 赛前特征对象（原地修改）
        """

        def safe_diff(val1, val2):
            if val1 is not None and val2 is not None:
                return val1 - val2
            return None

        features.rolling_xg_diff = safe_diff(
            getattr(features, "home_rolling_xg", None), getattr(features, "away_rolling_xg", None)
        )

        features.rolling_possession_diff = safe_diff(
            getattr(features, "home_rolling_possession", None), getattr(features, "away_rolling_possession", None)
        )

        features.momentum_gap = safe_diff(
            getattr(features, "home_recent_form_points", None), getattr(features, "away_recent_form_points", None)
        )

        features.fatigue_diff = safe_diff(
            getattr(features, "home_fatigue_index", None), getattr(features, "away_fatigue_index", None)
        )

        features.rest_days_diff = safe_diff(
            getattr(features, "home_rest_days", None), getattr(features, "away_rest_days", None)
        )

        features.home_advantage = safe_diff(
            getattr(features, "home_home_win_rate", None), getattr(features, "away_away_win_rate", None)
        )

    def calculate_prematch_features(
        self,
        match_id: str,
        match_date: datetime,
        home_team: str,
        away_team: str,
        league_name: str = "",
        season: str = "",
        conn=None,
    ) -> PreMatchFeatures:
        """
        计算单场比赛的完整赛前特征

        Args:
            match_id: 比赛 ID
            match_date: 比赛时间
            home_team: 主队
            away_team: 客队
            league_name: 联赛名称
            season: 赛季
            conn: 数据库连接

        Returns:
            赛前特征对象
        """
        # 数据验证
        if match_date is None:
            raise ValueError(f"match_date 不能为 None (match_id: {match_id})")
        if not home_team or not away_team:
            raise ValueError(f"home_team/away_team 不能为空 (match_id: {match_id})")

        features = PreMatchFeatures(
            match_id=match_id,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
            league_name=league_name,
            season=season,
        )

        # 时空隔离协议
        before_match_time = match_date

        # 主队特征
        home_history = self.get_team_history(home_team, before_match_time, conn=conn)
        features.home_history_count = len(home_history)
        home_features = self._compute_team_features(home_team, before_match_time, True, conn)
        for k, v in home_features.items():
            setattr(features, k, v)

        # 客队特征
        away_history = self.get_team_history(away_team, before_match_time, conn=conn)
        features.away_history_count = len(away_history)
        away_features = self._compute_team_features(away_team, before_match_time, False, conn)
        for k, v in away_features.items():
            setattr(features, k, v)

        # 差值特征
        self._compute_difference_features(features)

        # 质量检查
        features.is_valid = (
            features.home_history_count >= self.min_history and features.away_history_count >= self.min_history
        )

        return features

    def save_to_database(self, features: PreMatchFeatures, conn=None) -> bool:
        """
        保存赛前特征到数据库

        Args:
            features: 赛前特征对象
            conn: 数据库连接

        Returns:
            是否保存成功
        """
        should_close = conn is None
        if conn is None:
            conn = self.get_connection()

        try:
            with conn.cursor() as cur:
                # 基础列（始终包含）
                base_columns = [
                    "match_id",
                    "match_date",
                    "home_team",
                    "away_team",
                    "league_name",
                    "season",
                    "home_history_count",
                    "away_history_count",
                    "is_valid",
                ]

                # 构建完整列列表
                columns = base_columns.copy()

                # 添加所有特征列（包括 None 值）
                for k in features.to_dict().keys():
                    if k not in columns:
                        columns.append(k)

                # 添加 feature_version（必需字段）
                if "feature_version" not in columns:
                    columns.append("feature_version")

                # 构建值列表
                values = []
                placeholders = []
                for col in columns:
                    if col == "feature_version":
                        # 使用计算器的 feature_version
                        value = self.feature_version
                    else:
                        value = getattr(features, col, None)
                    values.append(value)
                    placeholders.append("%s")

                # 插入数据
                query = f"""
                    INSERT INTO prematch_features ({", ".join(columns)})
                    VALUES ({", ".join(placeholders)})
                    ON CONFLICT (match_id, feature_version)
                    DO UPDATE SET
                        computed_at = CURRENT_TIMESTAMP,
                        is_valid = EXCLUDED.is_valid
                """

                cur.execute(query, values)
                conn.commit()

                return True

        except Exception as e:
            logger.error(
                "保存赛前特征失败",
                match_id=features.match_id,
                error=str(e),
            )
            conn.rollback()
            return False

        finally:
            if should_close:
                conn.close()

    def batch_calculate(
        self,
        limit: int | None = None,
        league_name: str | None = None,
    ) -> dict[str, Any]:
        """
        批量计算赛前特征

        Args:
            limit: 限制数量
            league_name: 联赛名称过滤

        Returns:
            统计信息字典
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查询比赛列表
                query = """
                    SELECT m.match_id, m.match_date, m.home_team, m.away_team, m.league_name, m.season
                    FROM matches m
                    WHERE m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                """

                params = []

                if league_name:
                    query += " AND m.league_name = %s"
                    params.append(league_name)

                query += " ORDER BY m.match_date DESC"

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)

                cur.execute(query, params)
                matches = cur.fetchall()

                logger.info(f"开始批量计算 {len(matches)} 场比赛的赛前特征")

                success_count = 0
                failed_count = 0
                invalid_count = 0

                for match in matches:
                    try:
                        features = self.calculate_prematch_features(
                            match_id=match["match_id"],
                            match_date=match["match_date"],
                            home_team=match["home_team"],
                            away_team=match["away_team"],
                            league_name=match.get("league_name", ""),
                            season=match.get("season", ""),
                            conn=conn,
                        )

                        if self.save_to_database(features, conn=conn):
                            success_count += 1
                            if not features.is_valid:
                                invalid_count += 1
                        else:
                            failed_count += 1

                    except Exception as e:
                        logger.error(
                            "计算赛前特征失败",
                            match_id=match["match_id"],
                            error=str(e),
                        )
                        failed_count += 1

                logger.info(
                    "批量计算完成",
                    total=len(matches),
                    success=success_count,
                    failed=failed_count,
                    invalid=invalid_count,
                )

                return {
                    "total": len(matches),
                    "success": success_count,
                    "failed": failed_count,
                    "invalid": invalid_count,
                }

        finally:
            conn.close()


def process_single_match(args, conn_params):
    """
    单场比赛特征计算的包装函数（用于多进程）
    """
    match_id, match_date, home_team, away_team, league_name, season = args

    calculator = PreMatchFeatureCalculator()

    # 创建独立连接

    conn_params_with_decode = conn_params.copy()
    if isinstance(conn_params_with_decode.get("password"), str):
        pass  # 已经是字符串
    else:
        # SecretStr 对象
        from pydantic import SecretStr

        if isinstance(conn_params_with_decode.get("password"), SecretStr):
            conn_params_with_decode["password"] = conn_params_with_decode["password"].get_secret_value()

    conn = psycopg2.connect(**conn_params_with_decode)

    try:
        features = calculator.calculate_prematch_features(
            match_id=match_id,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
            league_name=league_name,
            season=season,
            conn=conn,
        )

        # 保存
        calculator.save_to_database(features, conn=conn)

        return {"match_id": match_id, "success": True, "is_valid": features.is_valid}
    except Exception as e:
        logger.error(f"处理比赛 {match_id} 失败: {e}")
        return {"match_id": match_id, "success": False, "error": str(e)}
    finally:
        conn.close()


def batch_calculate_parallel(
    limit: int = 100,
    league_name: str | None = None,
    num_processes: int = 4,
) -> dict[str, Any]:
    """
    多进程并行计算赛前特征

    Args:
        limit: 限制数量
        league_name: 联赛名称
        num_processes: 进程数

    Returns:
        统计信息字典
    """
    settings = get_settings()
    # 处理 SecretStr 类型的密码
    password_value = (
        settings.database.password.get_secret_value()
        if hasattr(settings.database.password, "get_secret_value")
        else settings.database.password
    )

    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": password_value,
    }

    # 获取比赛列表
    conn = psycopg2.connect(**conn_params)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT m.match_id, m.match_date, m.home_team, m.away_team, m.league_name, m.season
                FROM matches m
                WHERE m.status = 'finished'
                  AND m.home_score IS NOT NULL
                  AND m.away_score IS NOT NULL
            """

            params = []
            if league_name:
                query += " AND m.league_name = %s"
                params.append(league_name)

            query += " ORDER BY m.match_date DESC"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            matches = cur.fetchall()

            match_args = [
                (
                    m["match_id"],
                    m["match_date"],
                    m["home_team"],
                    m["away_team"],
                    m.get("league_name", ""),
                    m.get("season", ""),
                )
                for m in matches
            ]

    finally:
        conn.close()

    logger.info(f"开始并行计算 {len(match_args)} 场比赛的赛前特征 (进程数: {num_processes})")

    # 使用进程池并行计算
    with mp.Pool(processes=num_processes) as pool:
        # 准备 conn_params（序列化处理）
        conn_params_copy = conn_params.copy()
        if hasattr(conn_params_copy["password"], "get_secret_value"):
            conn_params_copy["password"] = conn_params_copy["password"].get_secret_value()

        results = pool.starmap(process_single_match, [(args, conn_params_copy) for args in match_args])

    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    failed_count = sum(1 for r in results if not r["success"])
    invalid_count = sum(1 for r in results if not r.get("is_valid"))

    logger.info(
        "并行计算完成",
        total=len(match_args),
        success=success_count,
        failed=failed_count,
        invalid=invalid_count,
    )

    return {
        "total": len(match_args),
        "success": success_count,
        "failed": failed_count,
        "invalid": invalid_count,
    }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V51.1 赛前特征计算引擎",
    )
    parser.add_argument("--limit", type=int, default=100, help="计算比赛数量")
    parser.add_argument("--league", type=str, help="联赛名称过滤")
    parser.add_argument("--parallel", action="store_true", help="启用多进程并行")
    parser.add_argument("--processes", type=int, default=4, help="并行进程数")

    args = parser.parse_args()

    if args.parallel:
        stats = batch_calculate_parallel(
            limit=args.limit,
            league_name=args.league,
            num_processes=args.processes,
        )
    else:
        calculator = PreMatchFeatureCalculator(
            rolling_window=10,
            recent_window=3,
            min_history=5,
        )

        stats = calculator.batch_calculate(
            limit=args.limit,
            league_name=args.league,
        )

    print("\n" + "=" * 60)
    print("V51.1 赛前特征计算摘要")
    print("=" * 60)
    print(f"总计: {stats['total']} 场")
    print(f"成功: {stats['success']} 场")
    print(f"失败: {stats['failed']} 场")
    print(f"无效: {stats['invalid']} 场 (历史不足)")
    print("=" * 60)


if __name__ == "__main__":
    main()
