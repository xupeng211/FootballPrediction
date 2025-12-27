#!/usr/bin/env python3
"""
V19.2 积分榜动态计算器

从比赛历史数据实时计算每场比赛时的积分榜状态
确保无数据泄露，只使用该场比赛之前的历史数据
"""

import logging
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

# V19.3: 模块级常量（可在模块级函数中使用）
DEFAULT_LATENCY_MINUTES = 120  # 默认下注时延（2 小时）


@dataclass
class TeamStandings:
    """球队积分榜状态"""

    position: int
    points: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    form: str  # 最近5场结果，如 "WWLDL"

    def get_form_points(self) -> int:
        """计算最近5场得分"""
        form_points = 0
        for result in self.form:
            if result == "W":
                form_points += 3
            elif result == "D":
                form_points += 1
        return form_points


class StandingsCalculator:
    """
    积分榜动态计算器

    核心功能：
    1. 根据比赛历史实时计算积分榜
    2. 无数据泄露：只使用目标比赛之前的数据
    3. 支持任意时间点的积分榜查询
    4. 模拟下注窗口时延（betting window latency）
    5. V19.3 加固：联赛隔离（league_id 过滤）

    时延机制：
    - latency_minutes: 下注时延（分钟），默认 120
    - 在计算积分榜时，只使用比目标比赛时间早 latency_minutes 分钟的比赛
    - 模拟真实场景：开球前 2 小时下注，此时上一场比赛可能还未结束

    联赛隔离：
    - league_id: 联赛标识符，确保跨联赛球队不产生积分关联
    - 如果 DataFrame 中包含多个联赛，建议按联赛分组后分别创建计算器实例
    """

    # 胜负平积分
    POINTS_WIN = 3
    POINTS_DRAW = 1
    POINTS_LOSS = 0

    def __init__(self, latency_minutes: int = DEFAULT_LATENCY_MINUTES, league_id: str | None = None):
        """
        初始化积分榜计算器

        Args:
            latency_minutes: 下注时延（分钟），默认 120（2 小时）
                模拟在比赛开球前 latency_minutes 分钟下注的场景
            league_id: 联赛标识符（可选）。如果提供，只计算该联赛的积分榜
        """
        self.matches_cache: list[dict] = []
        self.standings_history: dict[str, list[TeamStandings]] = defaultdict(list)
        self.is_initialized = False
        self.latency_minutes = latency_minutes
        self.league_id = league_id  # V19.3: 联赛隔离

        if league_id:
            logger.info(f"积分榜计算器初始化完成（时延: {latency_minutes} 分钟，联赛: {league_id}）")
        else:
            logger.info(f"积分榜计算器初始化完成（时延: {latency_minutes} 分钟，未指定联赛）")

    def initialize_from_dataframe(self, df: pd.DataFrame) -> None:
        """
        从 DataFrame 初始化计算器

        Args:
            df: 包含比赛数据的 DataFrame，需包含以下列：
                - home_team, away_team: 球队名称
                - match_time: 比赛时间
                - home_score, away_score: 比分
                - id: 比赛唯一标识符（用于次要排序）
                - league_id: 联赛标识符（可选，V19.3 新增）

        排序规则：
            1. 主排序：match_time（时间顺序）
            2. 次要排序：id（确保相同时间的比赛有确定顺序）

        V19.3 联赛隔离：
            - 如果指定了 league_id，只加载该联赛的比赛
            - 如果 DataFrame 中有多个联赛，会发出警告
        """
        logger.info(f"从 {len(df)} 场比赛初始化积分榜计算器...")

        # V19.3: 联赛隔离检查
        if "league_id" in df.columns:
            unique_leagues = df["league_id"].dropna().unique()
            if len(unique_leagues) > 1:
                logger.warning(f"⚠️ DataFrame 中包含 {len(unique_leagues)} 个不同联赛: {unique_leagues}")
                if self.league_id is not None:
                    logger.info(f"   只加载联赛 {self.league_id} 的比赛")
                    df = df[df["league_id"] == self.league_id].copy()
                else:
                    logger.warning("   未指定 league_id，将跨联赛计算积分榜（可能导致同名球队混淆）")
            elif len(unique_leagues) == 1:
                detected_league = unique_leagues[0]
                if self.league_id is not None and self.league_id != detected_league:
                    logger.warning(f"⚠️ 指定的联赛 {self.league_id} 与数据中的联赛 {detected_league} 不匹配")
                self.league_id = detected_league
                logger.info(f"   检测到联赛: {detected_league}")

        # V19.2 加固：使用次要排序键确保确定性
        # 如果有多场比赛同时开始，id 决定它们的相对顺序
        # 如果没有 id 列，只按 match_time 排序
        sort_keys = ["match_time"]
        if "id" in df.columns:
            sort_keys.append("id")
        df_sorted = df.sort_values(sort_keys).copy()

        self.matches_cache = []
        for _, row in df_sorted.iterrows():
            self.matches_cache.append(
                {
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                    "match_time": pd.to_datetime(row["match_time"]),
                    "home_score": int(row["home_score"]) if pd.notna(row["home_score"]) else None,
                    "away_score": int(row["away_score"]) if pd.notna(row["away_score"]) else None,
                    "id": row.get("id", None),  # 保留原始 id 用于调试
                    "league_id": row.get("league_id", None),  # V19.3: 联赛标识符
                }
            )

        self.is_initialized = True
        logger.info(f"✅ 积分榜计算器初始化完成，已加载 {len(self.matches_cache)} 场比赛")
        logger.info("   排序规则: ['match_time', 'id']（确定性排序）")
        if self.league_id:
            logger.info(f"   联赛隔离: {self.league_id}")

    def get_standings_at_match(self, match_idx: int) -> dict[str, TeamStandings]:
        """
        获取指定比赛时的积分榜（不包含该场比赛结果）

        V19.2 加固：考虑下注时延
        - 只使用比目标比赛开球时间早 latency_minutes 分钟的比赛结果
        - 模拟真实场景：开球前 2 小时下注，此时上一场比赛可能还未结束

        Args:
            match_idx: 比赛索引（在按时间排序的 matches_cache 中）

        Returns:
            Dict[str, TeamStandings]: 球队名 -> 积分榜状态
        """
        if not self.is_initialized:
            raise ValueError("计算器未初始化，请先调用 initialize_from_dataframe")

        # 获取目标比赛的开球时间
        if match_idx >= len(self.matches_cache):
            raise ValueError(f"match_idx {match_idx} 超出范围 (max: {len(self.matches_cache) - 1})")

        target_match_time = self.matches_cache[match_idx]["match_time"]

        # V19.2: 计算时延截止时间（只能使用此时之前的比赛结果）
        cutoff_time = target_match_time - pd.Timedelta(minutes=self.latency_minutes)

        # 计算该比赛之前的所有比赛结果
        standings = {}
        excluded_matches = 0  # 被时延排除的比赛数

        for i in range(match_idx):
            match = self.matches_cache[i]
            match_time = match["match_time"]

            # V19.2: 时延检查 - 只使用开球时间早于截止时间的比赛
            if match_time >= cutoff_time:
                # 这场比赛在时延窗口内，其结果不应被获取到
                excluded_matches += 1
                logger.debug(
                    f"[LATENCY] Match[{i}] at {match_time} "
                    f"excluded (cutoff: {cutoff_time}, latency: {self.latency_minutes}min)"
                )
                continue

            if match["home_score"] is None or match["away_score"] is None:
                continue  # 跳过没有比分的比赛

            home = match["home_team"]
            away = match["away_team"]
            home_goals = match["home_score"]
            away_goals = match["away_score"]

            # 更新主队积分榜
            if home not in standings:
                standings[home] = TeamStandings(
                    position=0,
                    points=0,
                    played=0,
                    won=0,
                    drawn=0,
                    lost=0,
                    goals_for=0,
                    goals_against=0,
                    goal_difference=0,
                    form="",
                )

            # 更新客队积分榜
            if away not in standings:
                standings[away] = TeamStandings(
                    position=0,
                    points=0,
                    played=0,
                    won=0,
                    drawn=0,
                    lost=0,
                    goals_for=0,
                    goals_against=0,
                    goal_difference=0,
                    form="",
                )

            # 更新统计数据
            standings[home].played += 1
            standings[away].played += 1
            standings[home].goals_for += home_goals
            standings[home].goals_against += away_goals
            standings[away].goals_for += away_goals
            standings[away].goals_against += home_goals

            # 更新胜负平
            if home_goals > away_goals:
                standings[home].won += 1
                standings[home].points += self.POINTS_WIN
                standings[away].lost += 1
                standings[away].points += self.POINTS_LOSS

                # 更新走势
                self._update_form(standings[home], "W")
                self._update_form(standings[away], "L")

            elif home_goals < away_goals:
                standings[away].won += 1
                standings[away].points += self.POINTS_WIN
                standings[home].lost += 1
                standings[home].points += self.POINTS_LOSS

                # 更新走势
                self._update_form(standings[home], "L")
                self._update_form(standings[away], "W")

            else:  # 平局
                standings[home].drawn += 1
                standings[home].points += self.POINTS_DRAW
                standings[away].drawn += 1
                standings[away].points += self.POINTS_DRAW

                # 更新走势
                self._update_form(standings[home], "D")
                self._update_form(standings[away], "D")

        # 记录时延统计
        if excluded_matches > 0:
            logger.info(
                f"[LATENCY] Match[{match_idx}] @ {target_match_time}: "
                f"{excluded_matches} 场比赛被时延排除 (latency={self.latency_minutes}min)"
            )

        # 计算净胜球和排名
        for team in standings.values():
            team.goal_difference = team.goals_for - team.goals_against

        # 按积分、净胜球、进球数排序
        sorted_teams = sorted(
            standings.items(), key=lambda x: (x[1].points, x[1].goal_difference, x[1].goals_for), reverse=True
        )

        # 分配排名
        for position, (team_name, _) in enumerate(sorted_teams, start=1):
            standings[team_name].position = position

        return standings

    def _update_form(self, team: TeamStandings, result: str) -> None:
        """更新球队最近5场走势"""
        team.form = result + team.form
        if len(team.form) > 5:
            team.form = team.form[:5]

    def get_team_stats_at_match(self, match_idx: int, team_name: str) -> dict | None:
        """
        获取指定球队在指定比赛时的积分榜统计

        Returns:
            Dict or None: 如果球队未找到返回 None
        """
        standings = self.get_standings_at_match(match_idx)

        if team_name not in standings:
            return None

        team = standings[team_name]
        return {
            "position": team.position,
            "points": team.points,
            "played": team.played,
            "won": team.won,
            "drawn": team.drawn,
            "lost": team.lost,
            "goals_for": team.goals_for,
            "goals_against": team.goals_against,
            "goal_difference": team.goal_difference,
            "form": team.form,
            "form_points": team.get_form_points(),
            "win_rate": team.won / team.played if team.played > 0 else 0.0,
            "loss_rate": team.lost / team.played if team.played > 0 else 0.0,
        }


# 全局单例
_global_calculator: StandingsCalculator | None = None


def get_global_calculator() -> StandingsCalculator:
    """获取全局积分榜计算器"""
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = StandingsCalculator()
    return _global_calculator


def initialize_global_calculator(
    df: pd.DataFrame, latency_minutes: int = DEFAULT_LATENCY_MINUTES, league_id: str | None = None
) -> StandingsCalculator:
    """
    初始化全局积分榜计算器

    Args:
        df: 包含比赛数据的 DataFrame
        latency_minutes: 下注时延（分钟）
        league_id: 联赛标识符（可选，V19.3 新增）

    Returns:
        StandingsCalculator: 初始化后的计算器实例
    """
    global _global_calculator
    _global_calculator = StandingsCalculator(latency_minutes=latency_minutes, league_id=league_id)
    _global_calculator.initialize_from_dataframe(df)
    return _global_calculator
