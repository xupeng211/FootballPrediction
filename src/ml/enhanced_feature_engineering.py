#!/usr/bin/env python3
"""
Enhanced Feature Engineering for Football Prediction
足球预测增强特征工程模块

根据SRS要求，实现基础特征提取算法，包括：
- 进球数特征
- 主客场状态特征
- 赔率变化特征
- 球队实力评估特征
- 历史对战记录特征
- 伤病情况特征（预留接口）

生成时间: 2025-10-29 03:55:00
"""

import asyncio
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum

from src.core.logging_system import get_logger

logger = get_logger(__name__)


class MatchOutcome(Enum):
    """比赛结果枚举"""

    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"


@dataclass
class TeamMatchHistory:
    """球队比赛历史数据"""

    team_id: str
    team_name: str
    recent_matches: List[Dict] = field(default_factory=list)
    goals_scored_history: List[int] = field(default_factory=list)
    goals_conceded_history: List[int] = field(default_factory=list)
    home_matches: List[Dict] = field(default_factory=list)
    away_matches: List[Dict] = field(default_factory=list)

    def get_recent_form(self, n_matches: int = 5) -> List[str]:
        """获取最近状态"""
        form = []
        for match in self.recent_matches[:n_matches]:
            if match["result"] == MatchOutcome.HOME_WIN.value:
                form.append("W")
            elif match["result"] == MatchOutcome.DRAW.value:
                form.append("D")
            else:
                form.append("L")
        return form

    def get_avg_goals_scored(self, n_matches: int = 10) -> float:
        """获取平均进球数"""
        if not self.goals_scored_history:
            return 0.0
        recent_goals = self.goals_scored_history[:n_matches]
        return sum(recent_goals) / len(recent_goals)

    def get_avg_goals_conceded(self, n_matches: int = 10) -> float:
        """获取平均失球数"""
        if not self.goals_conceded_history:
            return 0.0
        recent_goals = self.goals_conceded_history[:n_matches]
        return sum(recent_goals) / len(recent_goals)


@dataclass
class HeadToHeadRecord:
    """历史对战记录"""

    home_team_id: str
    away_team_id: str
    total_matches: int = 0
    home_wins: int = 0
    away_wins: int = 0
    draws: int = 0
    home_goals: int = 0
    away_goals: int = 0
    recent_matches: List[Dict] = field(default_factory=list)

    def get_head_to_head_features(self) -> Dict[str, float]:
        """获取对战特征"""
        if self.total_matches == 0:
            return {
                "h2h_total_matches": 0,
                "h2h_home_win_rate": 0.0,
                "h2h_away_win_rate": 0.0,
                "h2h_draw_rate": 0.0,
                "h2h_avg_home_goals": 0.0,
                "h2h_avg_away_goals": 0.0,
                "h2h_goal_difference": 0.0,
            }

        return {
            "h2h_total_matches": self.total_matches,
            "h2h_home_win_rate": self.home_wins / self.total_matches,
            "h2h_away_win_rate": self.away_wins / self.total_matches,
            "h2h_draw_rate": self.draws / self.total_matches,
            "h2h_avg_home_goals": self.home_goals / self.total_matches,
            "h2h_avg_away_goals": self.away_goals / self.total_matches,
            "h2h_goal_difference": (self.home_goals - self.away_goals)
            / self.total_matches,
        }


class EnhancedFeatureEngineer:
    """增强特征工程器

    实现SRS要求的所有特征提取功能：
    - 基础统计特征
    - 近期状态特征
    - 主客场特征
    - 历史对战特征
    - 赔率特征
    - 球队实力评估特征
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.team_histories: Dict[str, TeamMatchHistory] = {}
        self.head_to_head_records: Dict[Tuple[str, str], HeadToHeadRecord] = {}
        self.feature_cache: Dict[str, Dict[str, float]] = {}
        self.cached_features: Dict[str, Any] = {}

    def initialize_team_histories(self, matches_data: List[Dict]) -> None:
        """初始化球队历史数据"""
        self.logger.info("开始初始化球队历史数据...")

        for match in matches_data:
            home_team_id = str(match.get("home_team_id"))
            away_team_id = str(match.get("away_team_id"))

            # 初始化球队历史（如果不存在）
            if home_team_id not in self.team_histories:
                self.team_histories[home_team_id] = TeamMatchHistory(
                    team_id=home_team_id,
                    team_name=match.get("home_team_name", f"Team_{home_team_id}"),
                )

            if away_team_id not in self.team_histories:
                self.team_histories[away_team_id] = TeamMatchHistory(
                    team_id=away_team_id,
                    team_name=match.get("away_team_name", f"Team_{away_team_id}"),
                )

            # 添加比赛记录
            self._add_match_to_history(match, home_team_id, away_team_id)

        self.logger.info(f"完成初始化，共处理 {len(matches_data)} 场比赛")

    def _add_match_to_history(
        self, match: Dict, home_team_id: str, away_team_id: str
    ) -> None:
        """将比赛添加到历史记录"""
        home_score = int(match.get("home_score", 0))
        away_score = int(match.get("away_score", 0))
        match_date = match.get("match_date", datetime.now())

        # 确定比赛结果
        if home_score > away_score:
            result = MatchOutcome.HOME_WIN.value
        elif home_score < away_score:
            result = MatchOutcome.AWAY_WIN.value
        else:
            result = MatchOutcome.DRAW.value

        # 添加到主队历史
        home_match_record = {
            "opponent_id": away_team_id,
            "opponent_name": match.get("away_team_name", f"Team_{away_team_id}"),
            "is_home": True,
            "home_score": home_score,
            "away_score": away_score,
            "result": result,
            "match_date": match_date,
            "goals_for": home_score,
            "goals_against": away_score,
        }

        self.team_histories[home_team_id].recent_matches.append(home_match_record)
        self.team_histories[home_team_id].goals_scored_history.append(home_score)
        self.team_histories[home_team_id].goals_conceded_history.append(away_score)
        self.team_histories[home_team_id].home_matches.append(home_match_record)

        # 添加到客队历史
        away_match_record = home_match_record.copy()
        away_match_record.update(
            {
                "opponent_id": home_team_id,
                "opponent_name": match.get("home_team_name", f"Team_{home_team_id}"),
                "is_home": False,
                "goals_for": away_score,
                "goals_against": home_score,
            }
        )

        # 更新客队的结果（相对客队而言）
        if result == MatchOutcome.HOME_WIN.value:
            away_match_record["result"] = MatchOutcome.AWAY_WIN.value
        elif result == MatchOutcome.AWAY_WIN.value:
            away_match_record["result"] = MatchOutcome.HOME_WIN.value
        # 平局结果不变

        self.team_histories[away_team_id].recent_matches.append(away_match_record)
        self.team_histories[away_team_id].goals_scored_history.append(away_score)
        self.team_histories[away_team_id].goals_conceded_history.append(home_score)
        self.team_histories[away_team_id].away_matches.append(away_match_record)

        # 更新历史对战记录
        h2h_key = (home_team_id, away_team_id)
        if h2h_key not in self.head_to_head_records:
            self.head_to_head_records[h2h_key] = HeadToHeadRecord(
                home_team_id=home_team_id, away_team_id=away_team_id
            )

        h2h = self.head_to_head_records[h2h_key]
        h2h.total_matches += 1
        h2h.home_goals += home_score
        h2h.away_goals += away_score
        h2h.recent_matches.append(home_match_record)

        if result == MatchOutcome.HOME_WIN.value:
            h2h.home_wins += 1
        elif result == MatchOutcome.AWAY_WIN.value:
            h2h.away_wins += 1
        else:
            h2h.draws += 1

    def calculate_basic_features(self, match: Dict) -> Dict[str, float]:
        """计算基础特征

        Args:
            match: 比赛数据字典

        Returns:
            基础特征字典
        """
        home_team_id = str(match.get("home_team_id"))
        str(match.get("away_team_id"))

        features = {}

        # 1. 主场优势特征
        features["home_advantage"] = 1.0  # 主场固定设为1.0
        features["is_neutral_venue"] = 0.0  # 是否中立场地（默认不是）

        # 2. 比赛重要性特征（根据联赛类型）
        league_name = match.get("league_name", "").lower()
        if any(keyword in league_name for keyword in ["champions", "europa", "cup"]):
                features["match_importance"] = 1.0  # 重要比赛
        elif any(
            keyword in league_name
            for keyword in ["premier", "la liga", "bundesliga", "serie a"]
        ):
                features["match_importance"] = 0.8  # 主要联赛
        else:
                features["match_importance"] = 0.6  # 其他联赛

        # 3. 时间特征
        match_date = match.get("match_date", datetime.now())
        if isinstance(match_date, str):
            match_date = datetime.fromisoformat(match_date)

        features["day_of_week"] = match_date.weekday() / 6.0  # 0-6 -> 0-1
        features["month"] = match_date.month / 12.0  # 1-12 -> 0-1
        features["days_since_last_match"] = self._calculate_days_since_last_match(
            home_team_id, match_date
        )

        return features

    def calculate_team_strength_features(self, match: Dict) -> Dict[str, float]:
        """计算球队实力特征

        Args:
            match: 比赛数据字典

        Returns:
            球队实力特征字典
        """
        home_team_id = str(match.get("home_team_id"))
        away_team_id = str(match.get("away_team_id"))

        features = {}

        # 主队实力特征
        if home_team_id in self.team_histories:
            home_history = self.team_histories[home_team_id]

            # 近期状态
            home_form = home_history.get_recent_form(5)
            features["home_recent_wins"] = home_form.count("W") / 5.0
            features["home_recent_draws"] = home_form.count("D") / 5.0
            features["home_recent_losses"] = home_form.count("L") / 5.0

            # 进球能力
            features["home_avg_goals_scored"] = home_history.get_avg_goals_scored(10)
            features["home_avg_goals_conceded"] = home_history.get_avg_goals_conceded(
                10
            )
            features["home_goal_difference"] = (
                features["home_avg_goals_scored"] - features["home_avg_goals_conceded"]
            )

            # 主客场表现
            if home_history.home_matches:
                home_home_goals = [
                    m["goals_for"] for m in home_history.home_matches[:5]
                ]
                home_home_conceded = [
                    m["goals_against"] for m in home_history.home_matches[:5]
                ]
                features["home_home_avg_goals"] = sum(home_home_goals) / len(
                    home_home_goals
                )
                features["home_home_avg_conceded"] = sum(home_home_conceded) / len(
                    home_home_conceded
                )
            else:
                features["home_home_avg_goals"] = 0.0
                features["home_home_avg_conceded"] = 0.0

        # 客队实力特征
        if away_team_id in self.team_histories:
            away_history = self.team_histories[away_team_id]

            # 近期状态
            away_form = away_history.get_recent_form(5)
            features["away_recent_wins"] = away_form.count("W") / 5.0
            features["away_recent_draws"] = away_form.count("D") / 5.0
            features["away_recent_losses"] = away_form.count("L") / 5.0

            # 进球能力
            features["away_avg_goals_scored"] = away_history.get_avg_goals_scored(10)
            features["away_avg_goals_conceded"] = away_history.get_avg_goals_conceded(
                10
            )
            features["away_goal_difference"] = (
                features["away_avg_goals_scored"] - features["away_avg_goals_conceded"]
            )

            # 客场表现
            if away_history.away_matches:
                away_away_goals = [
                    m["goals_for"] for m in away_history.away_matches[:5]
                ]
                away_away_conceded = [
                    m["goals_against"] for m in away_history.away_matches[:5]
                ]
                features["away_away_avg_goals"] = sum(away_away_goals) / len(
                    away_away_goals
                )
                features["away_away_avg_conceded"] = sum(away_away_conceded) / len(
                    away_away_conceded
                )
            else:
                features["away_away_avg_goals"] = 0.0
                features["away_away_avg_conceded"] = 0.0

        # 实力对比特征
        if home_team_id in self.team_histories and away_team_id in self.team_histories:

            features["strength_difference"] = features.get(
                "home_goal_difference", 0
            ) - features.get("away_goal_difference", 0)

            features["home_advantage_adjusted"] = features.get(
                "home_home_avg_goals", 0
            ) - features.get("away_away_avg_goals", 0)

        return features

    def calculate_head_to_head_features(self, match: Dict) -> Dict[str, float]:
        """计算历史对战特征

        Args:
            match: 比赛数据字典

        Returns:
            历史对战特征字典
        """
        home_team_id = str(match.get("home_team_id"))
        away_team_id = str(match.get("away_team_id"))

        # 获取对战记录
        h2h_key = (home_team_id, away_team_id)
        reverse_h2h_key = (away_team_id, home_team_id)

        h2h_features = {}

        if h2h_key in self.head_to_head_records:
            h2h_features = self.head_to_head_records[
                h2h_key
            ].get_head_to_head_features()
        elif reverse_h2h_key in self.head_to_head_records:
            # 如果找到反向记录，转换为主队视角
            reverse_h2h = self.head_to_head_records[reverse_h2h_key]
            original_features = reverse_h2h.get_head_to_head_features()

            h2h_features = {
                "h2h_total_matches": original_features["h2h_total_matches"],
                "h2h_home_win_rate": original_features["h2h_away_win_rate"],  # 交换
                "h2h_away_win_rate": original_features["h2h_home_win_rate"],  # 交换
                "h2h_draw_rate": original_features["h2h_draw_rate"],
                "h2h_avg_home_goals": original_features["h2h_avg_away_goals"],  # 交换
                "h2h_avg_away_goals": original_features["h2h_avg_home_goals"],  # 交换
                "h2h_goal_difference": -original_features[
                    "h2h_goal_difference"
                ],  # 反向
            }
        else:
            # 没有对战记录，使用默认值
            h2h_features = {
                "h2h_total_matches": 0,
                "h2h_home_win_rate": 0.33,
                "h2h_away_win_rate": 0.33,
                "h2h_draw_rate": 0.34,
                "h2h_avg_home_goals": 1.2,
                "h2h_avg_away_goals": 1.1,
                "h2h_goal_difference": 0.1,
            }

        return h2h_features

    def calculate_odds_features(self, match: Dict) -> Dict[str, float]:
        """计算赔率特征

        Args:
            match: 比赛数据字典

        Returns:
            赔率特征字典
        """
        features = {}

        # 获取赔率数据
        home_odds = match.get("home_win_odds")
        draw_odds = match.get("draw_odds")
        away_odds = match.get("away_win_odds")

        if all(odds is not None for odds in [home_odds, draw_odds, away_odds]):
            # 转换为概率
            home_prob = 1.0 / home_odds
            draw_prob = 1.0 / draw_odds
            away_prob = 1.0 / away_odds
            total_prob = home_prob + draw_prob + away_prob

            # 标准化概率
            features["odds_home_win_prob"] = home_prob / total_prob
            features["odds_draw_prob"] = draw_prob / total_prob
            features["odds_away_win_prob"] = away_prob / total_prob

            # 赔率特征
            features["odds_home_win"] = home_odds
            features["odds_draw"] = draw_odds
            features["odds_away_win"] = away_odds

            # 赔率差异特征
            features["odds_favorite_margin"] = min(
                features["odds_home_win_prob"] - features["odds_away_win_prob"],
                features["odds_away_win_prob"] - features["odds_home_win_prob"],
            )

            # 赔率市场信心
            features["odds_market_confidence"] = max(
                features["odds_home_win_prob"],
                features["odds_draw_prob"],
                features["odds_away_win_prob"],
            )
        else:
            # 默认赔率特征
            features.update(
                {
                    "odds_home_win_prob": 0.45,
                    "odds_draw_prob": 0.30,
                    "odds_away_win_prob": 0.25,
                    "odds_home_win": 2.2,
                    "odds_draw": 3.3,
                    "odds_away_win": 4.0,
                    "odds_favorite_margin": 0.2,
                    "odds_market_confidence": 0.45,
                }
            )

        return features

    def calculate_injury_features(self, match: Dict) -> Dict[str, float]:
        """计算伤病情况特征（预留接口）

        Args:
            match: 比赛数据字典

        Returns:
            伤病特征字典
        """
        features = {
            "home_key_players_missing": 0.0,  # 主队关键球员缺失数
            "away_key_players_missing": 0.0,  # 客队关键球员缺失数
            "home_squad_depth": 1.0,  # 主队阵容深度评分
            "away_squad_depth": 1.0,  # 客队阵容深度评分
            "injury_impact_home": 0.0,  # 伤病对主队的影响
            "injury_impact_away": 0.0,  # 伤病对客队的影响
        }

        # TODO: 实现真实的伤病数据处理逻辑
        # 这里需要从数据源获取伤病信息

        return features

    def _calculate_days_since_last_match(
        self, team_id: str, current_date: datetime
    ) -> float:
        """计算距离上次比赛的天数"""
        if team_id not in self.team_histories:
            return 7.0  # 默认7天

        team_history = self.team_histories[team_id]
        if not team_history.recent_matches:
            return 7.0

        last_match_date = team_history.recent_matches[0].get("match_date", current_date)
        if isinstance(last_match_date, str):
            last_match_date = datetime.fromisoformat(last_match_date)

        days_diff = (current_date - last_match_date).days
        return max(0.0, min(days_diff / 30.0, 1.0))  # 标准化到0-1范围

    async def extract_all_features(self, match: Dict) -> Dict[str, float]:
        """提取所有特征

        Args:
            match: 比赛数据字典

        Returns:
            完整的特征字典
        """
        try:
            # 生成特征缓存键
            cache_key =
    f"{match.get('home_team_id')}_{match.get('away_team_id')}_{match.get('match_date')}"

            # 检查缓存
            if cache_key in self.feature_cache:
                return self.feature_cache[cache_key]

            # 计算各类特征
            features = {}
            features.update(self.calculate_basic_features(match))
            features.update(self.calculate_team_strength_features(match))
            features.update(self.calculate_head_to_head_features(match))
            features.update(self.calculate_odds_features(match))
            features.update(self.calculate_injury_features(match))

            # 缓存特征
            self.feature_cache[cache_key] = features

            self.logger.debug(f"为比赛 {cache_key} 提取了 {len(features)} 个特征")
            return features

        except Exception as e:
            self.logger.error(f"特征提取失败: {e}")
            return {}

    async def extract_features_batch(self, matches: List[Dict]) -> pd.DataFrame:
        """批量提取特征

        Args:
            matches: 比赛数据列表

        Returns:
            特征DataFrame
        """
        self.logger.info(f"开始批量提取 {len(matches)} 场比赛的特征...")

        features_list = []
        for match in matches:
            features = await self.extract_all_features(match)
            if features:
                features["match_id"] = match.get("match_id")
                features["home_team_id"] = match.get("home_team_id")
                features["away_team_id"] = match.get("away_team_id")
                features_list.append(features)

        if features_list:
            df = pd.DataFrame(features_list)
            self.logger.info(f"批量特征提取完成，特征维度: {df.shape}")
            return df
        else:
            self.logger.warning("没有提取到任何特征")
            return pd.DataFrame()

    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        sample_features = {
            # 基础特征
            "home_advantage",
            "is_neutral_venue",
            "match_importance",
            "day_of_week",
            "month",
            "days_since_last_match",
            # 主队实力特征
            "home_recent_wins",
            "home_recent_draws",
            "home_recent_losses",
            "home_avg_goals_scored",
            "home_avg_goals_conceded",
            "home_goal_difference",
            "home_home_avg_goals",
            "home_home_avg_conceded",
            # 客队实力特征
            "away_recent_wins",
            "away_recent_draws",
            "away_recent_losses",
            "away_avg_goals_scored",
            "away_avg_goals_conceded",
            "away_goal_difference",
            "away_away_avg_goals",
            "away_away_avg_conceded",
            # 实力对比特征
            "strength_difference",
            "home_advantage_adjusted",
            # 历史对战特征
            "h2h_total_matches",
            "h2h_home_win_rate",
            "h2h_away_win_rate",
            "h2h_draw_rate",
            "h2h_avg_home_goals",
            "h2h_avg_away_goals",
            "h2h_goal_difference",
            # 赔率特征
            "odds_home_win_prob",
            "odds_draw_prob",
            "odds_away_win_prob",
            "odds_home_win",
            "odds_draw",
            "odds_away_win",
            "odds_favorite_margin",
            "odds_market_confidence",
            # 伤病特征
            "home_key_players_missing",
            "away_key_players_missing",
            "home_squad_depth",
            "away_squad_depth",
            "injury_impact_home",
            "injury_impact_away",
        }

        return sorted(list(sample_features))


# 创建全局实例
enhanced_feature_engineer = EnhancedFeatureEngineer()


async def main():
    """主函数示例"""
    # 示例数据
    sample_matches = [
        {
            "match_id": "1",
            "home_team_id": "team1",
            "away_team_id": "team2",
            "home_team_name": "Manchester United",
            "away_team_name": "Liverpool",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2025-10-29T20:00:00",
            "league_name": "Premier League",
            "home_win_odds": 2.1,
            "draw_odds": 3.4,
            "away_win_odds": 3.8,
        },
        {
            "match_id": "2",
            "home_team_id": "team2",
            "away_team_id": "team3",
            "home_team_name": "Liverpool",
            "away_team_name": "Chelsea",
            "home_score": 1,
            "away_score": 1,
            "match_date": "2025-10-28T19:30:00",
            "league_name": "Premier League",
            "home_win_odds": 2.5,
            "draw_odds": 3.2,
            "away_win_odds": 2.9,
        },
    ]

    # 初始化特征工程器
    engineer = EnhancedFeatureEngineer()
    engineer.initialize_team_histories(sample_matches)

    # 提取特征
    for match in sample_matches:
        features = await engineer.extract_all_features(match)
        print(f"Match {match['match_id']} features:")
        for key, value in features.items():
            print(f"  {key}: {value:.4f}")
        print()

    # 批量提取特征
    features_df = await engineer.extract_features_batch(sample_matches)
    print("批量特征提取结果:")
    print(features_df.head())


if __name__ == "__main__":
    asyncio.run(main())
