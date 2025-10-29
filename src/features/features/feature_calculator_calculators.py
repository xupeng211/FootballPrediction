"""
特征计算器
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, deque

from src.core.logging_system import get_logger

logger = get_logger(__name__)


@dataclass
class MatchResult:
    """比赛结果数据类"""

    match_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    match_date: datetime
    league: str
    home_win: bool
    draw: bool
    away_win: bool
    home_goals: int
    away_goals: int
    total_goals: int
    goal_difference: int


@dataclass
class TeamStats:
    """球队统计数据类"""

    team: str
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_scored: int
    goals_conceded: int
    points: int
    recent_form: List[str]  # 最近5场比赛结果：W/D/L
    avg_goals_scored: float
    avg_goals_conceded: float
    clean_sheets: int
    failed_to_score: int


class FeatureCalculator:
    """特征计算器

    负责计算各种特征的核心类，支持：
    - 近期战绩特征计算
    - 历史对战特征计算
    - 赔率特征计算
    - 批量计算和缓存优化"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.team_stats_cache = {}
        self.head_to_head_cache = {}
        self.features_cache = {}

    def calculate_team_form_features(
        self, team: str, matches: List[MatchResult], last_n_matches: int = 5
    ) -> Dict[str, float]:
        """计算球队近期状态特征

        Args:
            team: 球队名称
            matches: 比赛结果列表
            last_n_matches: 考虑的最近比赛数量

        Returns:
            球队状态特征字典
        """
        try:
            # 获取该球队的比赛
            team_matches = []
            for match in matches:
                if match.home_team == team or match.away_team == team:
                    team_matches.append(match)

            # 按日期排序，获取最近的比赛
            team_matches.sort(key=lambda x: x.match_date, reverse=True)
            recent_matches = team_matches[:last_n_matches]

            if not recent_matches:
                return self._get_default_form_features()

            features = {}

            # 1. 计算最近N场比赛的结果统计
            wins = draws = losses = 0
            goals_scored = goals_conceded = 0
            clean_sheets = failed_to_score = 0

            for match in recent_matches:
                is_home = match.home_team == team

                # 确定比赛结果
                if is_home:
                    team_score = match.home_score
                    opponent_score = match.away_score
                    win = match.home_win
                    draw = match.draw
                else:
                    team_score = match.away_score
                    opponent_score = match.home_score
                    win = match.away_win
                    draw = match.draw

                # 统计结果
                if win:
                    wins += 1
                elif draw:
                    draws += 1
                else:
                    losses += 1

                # 统计进球
                goals_scored += team_score
                goals_conceded += opponent_score

                # 统计零封和未进球
                if opponent_score == 0:
                    clean_sheets += 1
                if team_score == 0:
                    failed_to_score += 1

            # 计算特征值
            total_matches = len(recent_matches)
            features["form_win_rate"] = wins / total_matches
            features["form_draw_rate"] = draws / total_matches
            features["form_loss_rate"] = losses / total_matches
            features["form_avg_goals_scored"] = goals_scored / total_matches
            features["form_avg_goals_conceded"] = goals_conceded / total_matches
            features["form_goal_difference"] = (
                goals_scored - goals_conceded
            ) / total_matches
            features["form_clean_sheet_rate"] = clean_sheets / total_matches
            features["form_scoring_rate"] = (
                total_matches - failed_to_score
            ) / total_matches

            # 2. 计算近期状态趋势（最近3场 vs 之前3场）
            if len(recent_matches) >= 6:
                recent_3 = recent_matches[:3]
                previous_3 = recent_matches[3:6]

                recent_points = self._calculate_points(recent_3, team)
                previous_points = self._calculate_points(previous_3, team)

                features["form_trend"] = (
                    recent_points - previous_points
                ) / 9.0  # 标准化到[-1,1]
            else:
                features["form_trend"] = 0.0

            # 3. 计算状态一致性（方差）
            points_per_match = []
            for match in recent_matches:
                is_home = match.home_team == team
                if is_home:
                    win = match.home_win
                    draw = match.draw
                else:
                    win = match.away_win
                    draw = match.draw

                if win:
                    points = 3
                elif draw:
                    points = 1
                else:
                    points = 0

                points_per_match.append(points)

            if len(points_per_match) > 1:
                features["form_consistency"] = 1.0 - (np.std(points_per_match) / 3.0)
            else:
                features["form_consistency"] = 0.5

            # 4. 计算连续表现
            features["form_current_streak"] = self._calculate_current_streak(
                recent_matches, team
            )

            self.logger.debug(
                f"计算球队 {team} 的状态特征: {len(recent_matches)} 场比赛"
            )
            return features

        except Exception as e:
            self.logger.error(f"计算球队状态特征失败: {e}")
            return self._get_default_form_features()

    def calculate_head_to_head_features(
        self,
        home_team: str,
        away_team: str,
        matches: List[MatchResult],
        last_n_matches: int = 10,
    ) -> Dict[str, float]:
        """计算历史对战特征

        Args:
            home_team: 主队名称
            away_team: 客队名称
            matches: 比赛结果列表
            last_n_matches: 考虑的最近对战数量

        Returns:
            历史对战特征字典
        """
        try:
            # 获取两队之间的对战记录
            h2h_matches = []
            for match in matches:
                if (match.home_team == home_team and match.away_team == away_team) or (
                    match.home_team == away_team and match.away_team == home_team
                ):
                    h2h_matches.append(match)

            # 按日期排序，获取最近的对战
            h2h_matches.sort(key=lambda x: x.match_date, reverse=True)
            recent_h2h = h2h_matches[:last_n_matches]

            if not recent_h2h:
                return self._get_default_h2h_features()

            features = {}

            # 1. 统计主队对战成绩
            home_wins = home_draws = home_losses = 0
            home_goals = away_goals = 0

            for match in recent_h2h:
                if match.home_team == home_team:
                    # 主队在家门口作战
                    if match.home_win:
                        home_wins += 1
                    elif match.draw:
                        home_draws += 1
                    else:
                        home_losses += 1

                    home_goals += match.home_score
                    away_goals += match.away_score
                else:
                    # 主队客场作战
                    if match.away_win:
                        home_wins += 1
                    elif match.draw:
                        home_draws += 1
                    else:
                        home_losses += 1

                    home_goals += match.away_score
                    away_goals += match.home_score

            total_matches = len(recent_h2h)

            # 2. 计算对战特征
            features["h2h_home_win_rate"] = home_wins / total_matches
            features["h2h_draw_rate"] = home_draws / total_matches
            features["h2h_home_loss_rate"] = home_losses / total_matches
            features["h2h_avg_home_goals"] = home_goals / total_matches
            features["h2h_avg_away_goals"] = away_goals / total_matches
            features["h2h_total_goals_avg"] = (home_goals + away_goals) / total_matches
            features["h2h_goal_difference"] = (home_goals - away_goals) / total_matches

            # 3. 计算主场优势对战
            home_venue_matches = [m for m in recent_h2h if m.home_team == home_team]
            if home_venue_matches:
                home_venue_wins = sum(1 for m in home_venue_matches if m.home_win)
                features["h2h_home_venue_advantage"] = home_venue_wins / len(
                    home_venue_matches
                )
            else:
                features["h2h_home_venue_advantage"] = 0.5

            # 4. 计算对战趋势（最近3场 vs 之前3场）
            if len(recent_h2h) >= 6:
                recent_3 = recent_h2h[:3]
                previous_3 = recent_h2h[3:6]

                recent_points = self._calculate_h2h_points(recent_3, home_team)
                previous_points = self._calculate_h2h_points(previous_3, home_team)

                features["h2h_trend"] = (recent_points - previous_points) / 9.0
            else:
                features["h2h_trend"] = 0.0

            # 5. 计算对战一致性
            if len(recent_h2h) >= 3:
                outcomes = []
                for match in recent_h2h:
                    if match.home_team == home_team:
                        if match.home_win:
                            outcomes.append(3)  # 胜
                        elif match.draw:
                            outcomes.append(1)  # 平
                        else:
                            outcomes.append(0)  # 负
                    else:
                        if match.away_win:
                            outcomes.append(3)
                        elif match.draw:
                            outcomes.append(1)
                        else:
                            outcomes.append(0)

                features["h2h_consistency"] = 1.0 - (np.std(outcomes) / 3.0)
            else:
                features["h2h_consistency"] = 0.5

            self.logger.debug(
                f"计算 {home_team} vs {away_team} 历史对战特征: {len(recent_h2h)} 场比赛"
            )
            return features

        except Exception as e:
            self.logger.error(f"计算历史对战特征失败: {e}")
            return self._get_default_h2h_features()

    def calculate_team_stats_features(
        self, team: str, matches: List[MatchResult], all_matches: List[MatchResult]
    ) -> Dict[str, float]:
        """计算球队统计数据特征

        Args:
            team: 球队名称
            matches: 该球队参与的比赛
            all_matches: 所有比赛（用于计算联盟平均值）

        Returns:
            球队统计特征字典
        """
        try:
            # 计算球队基础统计
            team_stats = self._calculate_team_stats(team, matches)

            if team_stats.matches_played == 0:
                return self._get_default_stats_features()

            features = {}

            # 1. 基础统计特征
            features["stats_win_rate"] = team_stats.wins / team_stats.matches_played
            features["stats_draw_rate"] = team_stats.draws / team_stats.matches_played
            features["stats_loss_rate"] = team_stats.losses / team_stats.matches_played
            features["stats_points_per_game"] = (
                team_stats.points / team_stats.matches_played
            )
            features["stats_avg_goals_scored"] = team_stats.avg_goals_scored
            features["stats_avg_goals_conceded"] = team_stats.avg_goals_conceded
            features["stats_goal_difference_per_game"] = (
                team_stats.avg_goals_scored - team_stats.avg_goals_conceded
            )

            # 2. 防守和进攻能力
            features["stats_clean_sheet_rate"] = (
                team_stats.clean_sheets / team_stats.matches_played
            )
            features["stats_scoring_rate"] = (
                team_stats.matches_played - team_stats.failed_to_score
            ) / team_stats.matches_played

            # 3. 进攻效率
            if team_stats.avg_goals_scored > 0:
                features["stats_offensive_efficiency"] = min(
                    team_stats.avg_goals_scored / 2.0, 1.0
                )
            else:
                features["stats_offensive_efficiency"] = 0.0

            # 4. 防守稳定性
            if team_stats.avg_goals_conceded > 0:
                features["stats_defensive_stability"] = max(
                    1.0 - (team_stats.avg_goals_conceded / 2.0), 0.0
                )
            else:
                features["stats_defensive_stability"] = 1.0

            # 5. 综合实力评分
            features["stats_overall_strength"] = (
                features["stats_win_rate"] * 0.4
                + features["stats_offensive_efficiency"] * 0.3
                + features["stats_defensive_stability"] * 0.3
            )

            # 6. 计算相对联盟平均水平（如果有足够数据）
            if all_matches:
                league_features = self._calculate_league_averages(all_matches)
                if league_features:
                    features["stats_relative_attack"] = features[
                        "stats_avg_goals_scored"
                    ] / league_features.get("avg_goals_scored", 1.0)
                    features["stats_relative_defense"] = league_features.get(
                        "avg_goals_conceded", 1.0
                    ) / max(features["stats_avg_goals_conceded"], 0.1)
                    features["stats_relative_points"] = features[
                        "stats_points_per_game"
                    ] / league_features.get("points_per_game", 1.0)
                else:
                    features["stats_relative_attack"] = 1.0
                    features["stats_relative_defense"] = 1.0
                    features["stats_relative_points"] = 1.0
            else:
                features["stats_relative_attack"] = 1.0
                features["stats_relative_defense"] = 1.0
                features["stats_relative_points"] = 1.0

            self.logger.debug(
                f"计算球队 {team} 统计特征: {team_stats.matches_played} 场比赛"
            )
            return features

        except Exception as e:
            self.logger.error(f"计算球队统计特征失败: {e}")
            return self._get_default_stats_features()

    def calculate_ranking_features(
        self, team: str, league_table: List[Dict]
    ) -> Dict[str, float]:
        """计算排名相关特征

        Args:
            team: 球队名称
            league_table: 联赛积分榜数据

        Returns:
            排名特征字典
        """
        try:
            if not league_table:
                return self._get_default_ranking_features()

            # 找到球队在积分榜中的位置
            team_position = None
            team_data = None

            for i, club_data in enumerate(league_table):
                if club_data.get("team") == team:
                    team_position = i + 1  # 排名从1开始
                    team_data = club_data
                    break

            if not team_data or team_position is None:
                return self._get_default_ranking_features()

            total_teams = len(league_table)
            features = {}

            # 1. 基础排名特征
            features["ranking_position"] = team_position
            features["ranking_normalized"] = (total_teams - team_position) / (
                total_teams - 1
            )  # 标准化到[0,1]
            features["ranking_points"] = team_data.get("points", 0)
            features["ranking_goal_difference"] = team_data.get("goal_difference", 0)

            # 2. 排名分区
            if team_position <= total_teams * 0.25:  # 前25%
                features["ranking_tier"] = 1.0  # 顶级球队
            elif team_position <= total_teams * 0.5:  # 前50%
                features["ranking_tier"] = 0.75  # 上游球队
            elif team_position <= total_teams * 0.75:  # 前75%
                features["ranking_tier"] = 0.5  # 中游球队
            else:
                features["ranking_tier"] = 0.25  # 下游球队

            # 3. 与上下名次差距
            if team_position > 1:
                above_team = league_table[team_position - 2]
                points_above = above_team.get("points", 0) - team_data.get("points", 0)
                features["ranking_gap_to_above"] = max(points_above, 0)
            else:
                features["ranking_gap_to_above"] = 0

            if team_position < total_teams:
                below_team = league_table[team_position]
                points_below = team_data.get("points", 0) - below_team.get("points", 0)
                features["ranking_gap_to_below"] = max(points_below, 0)
            else:
                features["ranking_gap_to_below"] = 0

            # 4. 排名趋势（如果有历史数据）
            features["ranking_promotion_contender"] = 1.0 if team_position <= 2 else 0.0
            features["ranking_europe_contender"] = 1.0 if team_position <= 6 else 0.0
            features["ranking_relegation_risk"] = (
                1.0 if team_position >= (total_teams - 3) else 0.0
            )

            self.logger.debug(
                f"计算球队 {team} 排名特征: 位置 {team_position}/{total_teams}"
            )
            return features

        except Exception as e:
            self.logger.error(f"计算排名特征失败: {e}")
            return self._get_default_ranking_features()

    def calculate_match_importance_features(
        self, home_team: str, away_team: str, league: str, stage: str = None
    ) -> Dict[str, float]:
        """计算比赛重要性特征

        Args:
            home_team: 主队名称
            away_team: 客队名称
            league: 联赛名称
            stage: 比赛阶段

        Returns:
            比赛重要性特征字典
        """
        try:
            features = {}

            # 1. 联赛重要性权重
            league_weights = {
                "Premier League": 1.0,
                "La Liga": 1.0,
                "Bundesliga": 0.95,
                "Serie A": 0.95,
                "Ligue 1": 0.9,
                "Champions League": 1.2,
                "Europa League": 1.1,
                "FA Cup": 0.8,
                "DFB-Pokal": 0.7,
                "Copa del Rey": 0.7,
                "Coppa Italia": 0.7,
                "Coupe de France": 0.6,
            }

            features["importance_league_weight"] = league_weights.get(league, 0.5)

            # 2. 比赛阶段重要性
            if stage:
                if "group" in stage.lower():
                    features["importance_stage_weight"] = 0.7
                elif "round of 16" in stage.lower() or "last 16" in stage.lower():
                    features["importance_stage_weight"] = 0.85
                elif "quarter" in stage.lower():
                    features["importance_stage_weight"] = 0.9
                elif "semi" in stage.lower():
                    features["importance_stage_weight"] = 0.95
                elif "final" in stage.lower():
                    features["importance_stage_weight"] = 1.2
                else:
                    features["importance_stage_weight"] = 0.8
            else:
                # 联赛比赛，根据时间推断重要性
                current_month = datetime.now().month
                if current_month >= 8:  # 赛季初期
                    features["importance_stage_weight"] = 0.7
                elif current_month >= 12:  # 赛季中期
                    features["importance_stage_weight"] = 0.85
                elif current_month >= 4:  # 赛季末期
                    features["importance_stage_weight"] = 1.0
                else:
                    features["importance_stage_weight"] = 0.8

            # 3. 对阵重要性（基于球队实力差距）
            # 这里简化处理，实际应该根据球队排名计算
            features["importance_rivalry_weight"] = 0.8  # 默认值

            # 4. 综合重要性评分
            features["importance_overall"] = (
                features["importance_league_weight"] * 0.4
                + features["importance_stage_weight"] * 0.4
                + features["importance_rivalry_weight"] * 0.2
            )

            return features

        except Exception as e:
            self.logger.error(f"计算比赛重要性特征失败: {e}")
            return {"importance_overall": 0.5}

    def calculate_all_features(
        self,
        home_team: str,
        away_team: str,
        matches: List[MatchResult],
        league_table: List[Dict] = None,
        league: str = None,
    ) -> Dict[str, float]:
        """计算所有特征的统一接口

        Args:
            home_team: 主队名称
            away_team: 客队名称
            matches: 比赛数据
            league_table: 联赛积分榜
            league: 联赛名称

        Returns:
            完整特征字典
        """
        try:
            all_features = {}

            # 1. 主队状态特征
            home_form = self.calculate_team_form_features(home_team, matches)
            all_features.update({f"home_{k}": v for k, v in home_form.items()})

            # 2. 客队状态特征
            away_form = self.calculate_team_form_features(away_team, matches)
            all_features.update({f"away_{k}": v for k, v in away_form.items()})

            # 3. 历史对战特征
            h2h_features = self.calculate_head_to_head_features(
                home_team, away_team, matches
            )
            all_features.update(h2h_features)

            # 4. 主队统计特征
            home_matches = [
                m
                for m in matches
                if m.home_team == home_team or m.away_team == home_team
            ]
            home_stats = self.calculate_team_stats_features(
                home_team, home_matches, matches
            )
            all_features.update({f"home_{k}": v for k, v in home_stats.items()})

            # 5. 客队统计特征
            away_matches = [
                m
                for m in matches
                if m.home_team == away_team or m.away_team == away_team
            ]
            away_stats = self.calculate_team_stats_features(
                away_team, away_matches, matches
            )
            all_features.update({f"away_{k}": v for k, v in away_stats.items()})

            # 6. 排名特征
            if league_table:
                home_ranking = self.calculate_ranking_features(home_team, league_table)
                away_ranking = self.calculate_ranking_features(away_team, league_table)
                all_features.update({f"home_{k}": v for k, v in home_ranking.items()})
                all_features.update({f"away_{k}": v for k, v in away_ranking.items()})

            # 7. 比赛重要性特征
            if league:
                importance_features = self.calculate_match_importance_features(
                    home_team, away_team, league
                )
                all_features.update(importance_features)

            # 8. 计算对比特征
            all_features.update(self._calculate_comparison_features(all_features))

            self.logger.info(
                f"计算 {home_team} vs {away_team} 完整特征: {len(all_features)} 个特征"
            )
            return all_features

        except Exception as e:
            self.logger.error(f"计算完整特征失败: {e}")
            return {}

    # ==================== 私有辅助方法 ====================

    def _get_default_form_features(self) -> Dict[str, float]:
        """获取默认状态特征"""
        return {
            "form_win_rate": 0.33,
            "form_draw_rate": 0.33,
            "form_loss_rate": 0.34,
            "form_avg_goals_scored": 1.0,
            "form_avg_goals_conceded": 1.0,
            "form_goal_difference": 0.0,
            "form_clean_sheet_rate": 0.2,
            "form_scoring_rate": 0.8,
            "form_trend": 0.0,
            "form_consistency": 0.5,
            "form_current_streak": 0,
        }

    def _get_default_h2h_features(self) -> Dict[str, float]:
        """获取默认历史对战特征"""
        return {
            "h2h_home_win_rate": 0.33,
            "h2h_draw_rate": 0.33,
            "h2h_home_loss_rate": 0.34,
            "h2h_avg_home_goals": 1.0,
            "h2h_avg_away_goals": 1.0,
            "h2h_total_goals_avg": 2.0,
            "h2h_goal_difference": 0.0,
            "h2h_home_venue_advantage": 0.5,
            "h2h_trend": 0.0,
            "h2h_consistency": 0.5,
        }

    def _get_default_stats_features(self) -> Dict[str, float]:
        """获取默认统计特征"""
        return {
            "stats_win_rate": 0.33,
            "stats_draw_rate": 0.33,
            "stats_loss_rate": 0.34,
            "stats_points_per_game": 1.33,
            "stats_avg_goals_scored": 1.0,
            "stats_avg_goals_conceded": 1.0,
            "stats_goal_difference_per_game": 0.0,
            "stats_clean_sheet_rate": 0.2,
            "stats_scoring_rate": 0.8,
            "stats_offensive_efficiency": 0.5,
            "stats_defensive_stability": 0.5,
            "stats_overall_strength": 0.5,
            "stats_relative_attack": 1.0,
            "stats_relative_defense": 1.0,
            "stats_relative_points": 1.0,
        }

    def _get_default_ranking_features(self) -> Dict[str, float]:
        """获取默认排名特征"""
        return {
            "ranking_position": 10,
            "ranking_normalized": 0.5,
            "ranking_points": 0,
            "ranking_goal_difference": 0,
            "ranking_tier": 0.5,
            "ranking_gap_to_above": 3,
            "ranking_gap_to_below": 3,
            "ranking_promotion_contender": 0,
            "ranking_europe_contender": 0,
            "ranking_relegation_risk": 0,
        }

    def _calculate_points(self, matches: List[MatchResult], team: str) -> int:
        """计算指定球队在指定比赛中的积分"""
        points = 0
        for match in matches:
            is_home = match.home_team == team

            if is_home:
                if match.home_win:
                    points += 3
                elif match.draw:
                    points += 1
            else:
                if match.away_win:
                    points += 3
                elif match.draw:
                    points += 1
        return points

    def _calculate_h2h_points(self, matches: List[MatchResult], team: str) -> int:
        """计算在对战比赛中指定球队的积分"""
        return self._calculate_points(matches, team)

    def _calculate_current_streak(self, matches: List[MatchResult], team: str) -> float:
        """计算当前连续表现"""
        if not matches:
            return 0.0

        streak = 0
        for match in matches:
            is_home = match.home_team == team

            if is_home:
                if match.home_win:
                    streak += 1
                elif match.draw:
                    streak += 0.5
                else:
                    break
            else:
                if match.away_win:
                    streak += 1
                elif match.draw:
                    streak += 0.5
                else:
                    break

        # 标准化到[-1, 1]范围
        return min(max(streak / 5.0, -1.0), 1.0)

    def _calculate_team_stats(self, team: str, matches: List[MatchResult]) -> TeamStats:
        """计算球队统计数据"""
        if not matches:
            return TeamStats(team, 0, 0, 0, 0, 0, 0, 0, [], 0, 0, 0, 0)

        wins = draws = losses = 0
        goals_scored = goals_conceded = 0
        recent_form = []

        matches.sort(key=lambda x: x.match_date, reverse=True)

        for match in matches[:10]:  # 最近10场
            is_home = match.home_team == team

            if is_home:
                team_score = match.home_score
                opponent_score = match.away_score
                win = match.home_win
                draw = match.draw
            else:
                team_score = match.away_score
                opponent_score = match.home_score
                win = match.away_win
                draw = match.draw

            # 统计结果
            if win:
                wins += 1
                recent_form.append("W")
            elif draw:
                draws += 1
                recent_form.append("D")
            else:
                losses += 1
                recent_form.append("L")

            goals_scored += team_score
            goals_conceded += opponent_score

        total_matches = len(matches)
        points = wins * 3 + draws
        avg_goals_scored = goals_scored / total_matches
        avg_goals_conceded = goals_conceded / total_matches

        clean_sheets = sum(
            1 for m in matches if m.away_score == 0 if m.home_team == team
        ) + sum(1 for m in matches if m.home_score == 0 if m.away_team == team)

        failed_to_score = sum(
            1 for m in matches if m.home_score == 0 if m.home_team == team
        ) + sum(1 for m in matches if m.away_score == 0 if m.away_team == team)

        return TeamStats(
            team=team,
            matches_played=total_matches,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
            points=points,
            recent_form=recent_form[:5],
            avg_goals_scored=avg_goals_scored,
            avg_goals_conceded=avg_goals_conceded,
            clean_sheets=clean_sheets,
            failed_to_score=failed_to_score,
        )

    def _calculate_league_averages(
        self, all_matches: List[MatchResult]
    ) -> Dict[str, float]:
        """计算联盟平均水平"""
        if not all_matches:
            return {}

        total_goals = 0
        total_matches = len(all_matches)
        teams_goals = defaultdict(lambda: {"scored": 0, "conceded": 0, "matches": 0})

        for match in all_matches:
            total_goals += match.total_goals

            teams_goals[match.home_team]["scored"] += match.home_score
            teams_goals[match.home_team]["conceded"] += match.away_score
            teams_goals[match.home_team]["matches"] += 1

            teams_goals[match.away_team]["scored"] += match.away_score
            teams_goals[match.away_team]["conceded"] += match.home_score
            teams_goals[match.away_team]["matches"] += 1

        avg_goals_scored = total_goals / (total_matches * 2)
        avg_goals_conceded = avg_goals_scored

        # 计算平均积分
        team_points = []
        for team, stats in teams_goals.items():
            # 简化计算：假设进球数和积分相关
            points = stats["scored"] * 3 - stats["conceded"]
            team_points.append(max(points, 0) / stats["matches"])

        avg_points_per_game = np.mean(team_points) if team_points else 1.33

        return {
            "avg_goals_scored": avg_goals_scored,
            "avg_goals_conceded": avg_goals_conceded,
            "points_per_game": avg_points_per_game,
        }

    def _calculate_comparison_features(
        self, all_features: Dict[str, float]
    ) -> Dict[str, float]:
        """计算主客队对比特征"""
        comparison_features = {}

        try:
            # 1. 实力对比
            home_strength = all_features.get("home_stats_overall_strength", 0.5)
            away_strength = all_features.get("away_stats_overall_strength", 0.5)
            comparison_features["diff_strength"] = home_strength - away_strength

            # 2. 进攻对比
            home_attack = all_features.get("home_stats_avg_goals_scored", 1.0)
            away_attack = all_features.get("away_stats_avg_goals_scored", 1.0)
            comparison_features["diff_attack"] = home_attack - away_attack

            # 3. 防守对比
            home_defense = all_features.get("home_stats_avg_goals_conceded", 1.0)
            away_defense = all_features.get("away_stats_avg_goals_conceded", 1.0)
            comparison_features["diff_defense"] = (
                away_defense - home_defense
            )  # 防守失球越少越好

            # 4. 状态对比
            home_form = all_features.get("home_form_win_rate", 0.33)
            away_form = all_features.get("away_form_win_rate", 0.33)
            comparison_features["diff_form"] = home_form - away_form

            # 5. 排名对比
            home_ranking = all_features.get("home_ranking_normalized", 0.5)
            away_ranking = all_features.get("away_ranking_normalized", 0.5)
            comparison_features["diff_ranking"] = home_ranking - away_ranking

            # 6. 主场优势
            home_venue = all_features.get("h2h_home_venue_advantage", 0.5)
            comparison_features["home_advantage"] = (
                home_venue - 0.5
            ) * 2  # 标准化到[-1,1]

        except Exception as e:
            self.logger.warning(f"计算对比特征失败: {e}")

        return comparison_features
