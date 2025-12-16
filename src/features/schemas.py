#!/usr/bin/env python3
"""
特征工程 Schema 定义

使用 Pydantic 定义机器学习特征的数据结构和验证规则。
确保特征的类型安全、完整性，并提供详细的字段描述。

主要 Schema:
- MatchFeatureSet: 完整的比赛特征集
- TeamFormFeatures: 球队形态特征
- OddsFeatures: 赔率特征
- PerformanceFeatures: 性能统计特征
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import numpy as np
import pandas as pd


class MatchResult(str, Enum):
    """比赛结果枚举"""
    HOME_WIN = "HOME_WIN"
    AWAY_WIN = "AWAY_WIN"
    DRAW = "DRAW"


class MatchStatus(str, Enum):
    """比赛状态枚举"""
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"


class TeamFormFeatures(BaseModel):
    """
    球队形态特征

    包含球队在指定时间窗口内的表现统计
    """

    # 基础形态统计
    matches_played: int = Field(
        ge=0,
        description="计算形态的比赛场次"
    )

    wins: int = Field(
        ge=0,
        description="获胜场次"
    )

    draws: int = Field(
        ge=0,
        description="平局场次"
    )

    losses: int = Field(
        ge=0,
        description="失败场次"
    )

    # 得分统计
    goals_scored: int = Field(
        ge=0,
        description="总进球数"
    )

    goals_conceded: int = Field(
        ge=0,
        description="总失球数"
    )

    goal_difference: int = Field(
        description="净胜球数"
    )

    # 比赛得分 (3分制)
    points: int = Field(
        ge=0,
        description="积分 (胜3分, 平1分, 负0分)"
    )

    # 比赛得分 (基于历史重要性)
    weighted_points: float = Field(
        ge=0,
        description="加权积分 (考虑比赛时间权重)"
    )

    # 平局统计 (用于预测模型)
    avg_goals_scored: float = Field(
        ge=0,
        description="平均进球数"
    )

    avg_goals_conceded: float = Field(
        ge=0,
        description="平均失球数"
    )

    # 特殊场景统计
    clean_sheets: int = Field(
        ge=0,
        description="零失球场次"
    )

    failed_to_score: int = Field(
        ge=0,
        description="未进球场次"
    )

    # 连胜/连败统计
    current_win_streak: int = Field(
        description="当前连胜场次"
    )

    current_unbeaten_streak: int = Field(
        description="当前不败场次"
    )

    @validator('goal_difference', pre=True, always=True)
    def calculate_goal_difference(cls, v, values):
        """计算净胜球数"""
        goals_scored = values.get('goals_scored', 0)
        goals_conceded = values.get('goals_conceded', 0)
        return goals_scored - goals_conceded

    @validator('points', pre=True, always=True)
    def calculate_points(cls, v, values):
        """计算积分"""
        wins = values.get('wins', 0)
        draws = values.get('draws', 0)
        return wins * 3 + draws

    @validator('avg_goals_scored', pre=True, always=True)
    def calculate_avg_goals_scored(cls, v, values):
        """计算平均进球数"""
        matches_played = values.get('matches_played', 0)
        goals_scored = values.get('goals_scored', 0)
        return goals_scored / max(matches_played, 1)

    @validator('avg_goals_conceded', pre=True, always=True)
    def calculate_avg_goals_conceded(cls, v, values):
        """计算平均失球数"""
        matches_played = values.get('matches_played', 0)
        goals_conceded = values.get('goals_conceded', 0)
        return goals_conceded / max(matches_played, 1)

    def get_form_score(self) -> float:
        """获取形态得分 (0-100)"""
        if self.matches_played == 0:
            return 0.0

        # 基础得分: 积分/最大可能积分
        max_points = self.matches_played * 3
        base_score = (self.points / max_points) * 100

        # 调整因子: 进球差表现
        goal_diff_factor = min(max(self.goal_difference / 10, -1), 1) * 10

        # 调整因子: 连胜/连败表现
        streak_factor = min(max(self.current_win_streak * 2, -10), 10)

        return max(0, min(100, base_score + goal_diff_factor + streak_factor))


class XGFeatures(BaseModel):
    """
    期望进球 (xG) 特征

    包含球队的xG统计数据和效率分析
    """

    # xG基础统计
    total_xg: float = Field(
        ge=0,
        description="总期望进球数"
    )

    total_goals: int = Field(
        ge=0,
        description="实际进球数"
    )

    # xG效率指标
    xg_efficiency: float = Field(
        description="xG效率 (实际进球/xG)"
    )

    # 平均值统计
    avg_xg_per_match: float = Field(
        ge=0,
        description="平均每场比赛xG"
    )

    avg_goals_per_match: float = Field(
        ge=0,
        description="平均每场比赛实际进球"
    )

    # 高质量机会统计
    big_chances_created: int = Field(
        ge=0,
        description="创造的大好机会数"
    )

    big_chances_converted: int = Field(
        ge=0,
        description="转化为进球的大好机会数"
    )

    big_chance_conversion_rate: float = Field(
        ge=0,
        le=1,
        description="大好机会转化率"
    )

    # xG趋势
    xg_trend_5: float = Field(
        description="最近5场比赛xG趋势"
    )

    xg_trend_3: float = Field(
        description="最近3场比赛xG趋势"
    )

    @validator('xg_efficiency', pre=True, always=True)
    def calculate_xg_efficiency(cls, v, values):
        """计算xG效率"""
        total_xg = values.get('total_xg', 0)
        total_goals = values.get('total_goals', 0)
        return total_goals / max(total_xg, 0.01)  # 避免0除法

    @validator('avg_xg_per_match', pre=True, always=True)
    def calculate_avg_xg_per_match(cls, v, values):
        """计算平均每场比赛xG"""
        matches = len(values.get('matches_list', []))
        total_xg = values.get('total_xg', 0)
        return total_xg / max(matches, 1)

    @validator('avg_goals_per_match', pre=True, always=True)
    def calculate_avg_goals_per_match(cls, v, values):
        """计算平均每场比赛实际进球"""
        matches = len(values.get('matches_list', []))
        total_goals = values.get('total_goals', 0)
        return total_goals / max(matches, 1)

    @validator('big_chance_conversion_rate', pre=True, always=True)
    def calculate_big_chance_conversion_rate(cls, v, values):
        """计算大好机会转化率"""
        created = values.get('big_chances_created', 0)
        converted = values.get('big_chances_converted', 0)
        return converted / max(created, 1)


class OddsFeatures(BaseModel):
    """
    赔率特征

    包含赛前赔率信息和市场情绪分析
    """

    # 1X2赔率
    home_win_odds: Optional[float] = Field(
        default=None,
        gt=1,
        description="主胜赔率"
    )

    draw_odds: Optional[float] = Field(
        default=None,
        gt=1,
        description="平局赔率"
    )

    away_win_odds: Optional[float] = Field(
        default=None,
        gt=1,
        description="客胜赔率"
    )

    # 隐含概率
    home_win_implied_prob: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="主胜隐含概率"
    )

    draw_implied_prob: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="平局隐含概率"
    )

    away_win_implied_prob: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="客胜隐含概率"
    )

    # 归一化特征 (用于模型)
    home_win_normalized: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="归一化主胜概率"
    )

    draw_normalized: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="归一化平局概率"
    )

    away_win_normalized: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="归一化客胜概率"
    )

    # 市场情绪指标
    bookmaker_margin: Optional[float] = Field(
        default=None,
        ge=0,
        description="博彩公司利润率"
    )

    favorite_team: Optional[str] = Field(
        default=None,
        description="受青睐球队 (HOME/AWAY)"
    )

    odds_consistency: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="赔率一致性指标"
    )

    @validator('home_win_implied_prob', pre=True, always=True)
    def calculate_home_win_prob(cls, v, values):
        """计算主胜隐含概率"""
        odds = values.get('home_win_odds')
        if odds and odds > 1:
            return 1.0 / odds
        return None

    @validator('draw_implied_prob', pre=True, always=True)
    def calculate_draw_prob(cls, v, values):
        """计算平局隐含概率"""
        odds = values.get('draw_odds')
        if odds and odds > 1:
            return 1.0 / odds
        return None

    @validator('away_win_implied_prob', pre=True, always=True)
    def calculate_away_win_prob(cls, v, values):
        """计算客胜隐含概率"""
        odds = values.get('away_win_odds')
        if odds and odds > 1:
            return 1.0 / odds
        return None

    @validator('home_win_normalized', pre=True, always=True)
    def calculate_home_normalized(cls, v, values):
        """计算归一化主胜概率"""
        prob = values.get('home_win_implied_prob')
        draw_prob = values.get('draw_implied_prob')
        away_prob = values.get('away_win_implied_prob')
        if prob is not None and draw_prob is not None and away_prob is not None:
            total_prob = prob + draw_prob + away_prob
            return prob / max(total_prob, 1)
        return None

    @validator('draw_normalized', pre=True, always=True)
    def calculate_draw_normalized(cls, v, values):
        """计算归一化平局概率"""
        prob = values.get('draw_implied_prob')
        home_prob = values.get('home_win_implied_prob')
        away_prob = values.get('away_win_implied_prob')
        if prob is not None and home_prob is not None and away_prob is not None:
            total_prob = prob + home_prob + away_prob
            return prob / max(total_prob, 1)
        return None

    @validator('away_win_normalized', pre=True, always=True)
    def calculate_away_normalized(cls, v, values):
        """计算归一化客胜概率"""
        prob = values.get('away_win_implied_prob')
        home_prob = values.get('home_win_implied_prob')
        draw_prob = values.get('draw_implied_prob')
        if prob is not None and home_prob is not None and draw_prob is not None:
            total_prob = prob + home_prob + draw_prob
            return prob / max(total_prob, 1)
        return None


class MatchFeatureSet(BaseModel):
    """
    比赛特征集 - 完整的机器学习特征

    包含用于预测模型的所有特征字段，遵循严格的数据验证规则。
    """

    # 基础信息
    match_id: str = Field(
        min_length=1,
        description="比赛唯一标识符"
    )

    home_team_id: str = Field(
        min_length=1,
        description="主队ID"
    )

    away_team_id: str = Field(
        min_length=1,
        description="客队ID"
    )

    match_date: datetime = Field(
        description="比赛日期时间"
    )

    venue: Optional[str] = Field(
        default=None,
        description="比赛场馆"
    )

    # 球队形态特征
    home_form_last5: TeamFormFeatures = Field(
        description="主队最近5场比赛形态特征"
    )

    away_form_last5: TeamFormFeatures = Field(
        description="客队最近5场比赛形态特征"
    )

    home_form_last3: TeamFormFeatures = Field(
        description="主队最近3场比赛形态特征"
    )

    away_form_last3: TeamFormFeatures = Field(
        description="客队最近3场比赛形态特征"
    )

    # xG特征
    home_xg_last5: XGFeatures = Field(
        description="主队最近5场比赛xG特征"
    )

    away_xg_last5: XGFeatures = Field(
        description="客队最近5场比赛xG特征"
    )

    home_xg_last3: XGFeatures = Field(
        description="主队最近3场比赛xG特征"
    )

    away_xg_last3: XGFeatures = Field(
        description="客队最近3场比赛xG特征"
    )

    # 赔率特征
    odds: OddsFeatures = Field(
        description="赔率特征"
    )

    # H2H (历史交锋) 特征
    h2h_total_matches: int = Field(
        ge=0,
        description="历史交锋总场次"
    )

    h2h_home_wins: int = Field(
        ge=0,
        description="历史交锋主队胜场数"
    )

    h2h_away_wins: int = Field(
        ge=0,
        description="历史交锋客队胜场数"
    )

    h2h_draws: int = Field(
        ge=0,
        description="历史交锋平局场次"
    )

    h2h_home_win_rate: float = Field(
        ge=0,
        le=1,
        description="历史交锋主队胜率"
    )

    # 比赛结果 (用于训练数据)
    result: Optional[MatchResult] = Field(
        default=None,
        description="比赛结果 (仅训练数据可用)"
    )

    final_home_score: Optional[int] = Field(
        default=None,
        ge=0,
        description="最终主队得分 (仅训练数据可用)"
    )

    final_away_score: Optional[int] = Field(
        default=None,
        ge=0,
        description="最终客队得分 (仅训练数据可用)"
    )

    # 特征质量指标
    feature_completeness_score: float = Field(
        ge=0,
        le=1,
        description="特征完整性评分 (0-1)"
    )

    data_quality_flag: str = Field(
        pattern="^(HIGH|MEDIUM|LOW)$",
        description="数据质量标记"
    )

    @validator('h2h_home_win_rate', pre=True, always=True)
    def calculate_h2h_home_win_rate(cls, v, values):
        """计算历史交锋主队胜率"""
        total_matches = values.get('h2h_total_matches', 0)
        home_wins = values.get('h2h_home_wins', 0)
        return home_wins / max(total_matches, 1)

    def get_feature_vector(self) -> np.ndarray:
        """获取特征向量用于机器学习模型"""
        features = []

        # 球队形态特征得分
        features.append(self.home_form_last5.get_form_score() / 100)
        features.append(self.away_form_last5.get_form_score() / 100)
        features.append(self.home_form_last3.get_form_score() / 100)
        features.append(self.away_form_last3.get_form_score() / 100)

        # xG效率
        features.append(self.home_xg_last5.xg_efficiency)
        features.append(self.away_xg_last5.xg_efficiency)
        features.append(self.home_xg_last3.xg_efficiency)
        features.append(self.away_xg_last3.xg_efficiency)

        # 归一化赔率
        if self.odds.home_win_normalized is not None:
            features.append(self.odds.home_win_normalized)
            features.append(self.odds.draw_normalized)
            features.append(self.odds.away_win_normalized)
        else:
            features.extend([0.33, 0.34, 0.33])  # 默认均匀分布

        # H2H统计
        features.append(self.h2h_home_win_rate)
        features.append(min(self.h2h_total_matches / 50, 1.0))  # 归一化交锋场次

        return np.array(features)

    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        return [
            'home_form_score_5',
            'away_form_score_5',
            'home_form_score_3',
            'away_form_score_3',
            'home_xg_efficiency_5',
            'away_xg_efficiency_5',
            'home_xg_efficiency_3',
            'away_xg_efficiency_3',
            'odds_home_normalized',
            'odds_draw_normalized',
            'odds_away_normalized',
            'h2h_home_win_rate',
            'h2h_match_count_normalized'
        ]

    def validate_for_training(self) -> bool:
        """验证是否适用于训练数据"""
        # 检查是否有结果数据
        has_result = self.result is not None
        has_scores = (self.final_home_score is not None and
                      self.final_away_score is not None)

        # 检查特征质量
        has_good_quality = self.data_quality_flag in ['HIGH', 'MEDIUM']
        has_good_completeness = self.feature_completeness_score >= 0.7

        return has_result and has_scores and has_good_quality and has_good_completeness

    class Config:
        """Pydantic配置"""
        use_enum_values = True
        validate_assignment = True
        extra = 'forbid'  # 禁止额外字段
        json_schema_extra = {
            "example": {
                "match_id": "match_123",
                "home_team_id": "team_456",
                "away_team_id": "team_789",
                "match_date": "2024-01-15T15:00:00Z",
                "home_form_last5": {
                    "matches_played": 5,
                    "wins": 3,
                    "draws": 1,
                    "losses": 1,
                    "goals_scored": 8,
                    "goals_conceded": 4
                },
                "away_form_last5": {
                    "matches_played": 5,
                    "wins": 2,
                    "draws": 2,
                    "losses": 1,
                    "goals_scored": 6,
                    "goals_conceded": 5
                },
                "odds": {
                    "home_win_odds": 2.10,
                    "draw_odds": 3.40,
                    "away_win_odds": 3.80
                },
                "h2h_total_matches": 10,
                "h2h_home_wins": 6,
                "h2h_away_wins": 2,
                "h2h_draws": 2,
                "feature_completeness_score": 0.95,
                "data_quality_flag": "HIGH"
            }
        }


# 特征工程配置类
class FeatureEngineeringConfig(BaseModel):
    """特征工程配置"""

    # 时间窗口配置
    form_windows: List[int] = Field(
        default=[3, 5, 10],
        description="形态特征计算时间窗口"
    )

    xg_windows: List[int] = Field(
        default=[3, 5],
        description="xG特征计算时间窗口"
    )

    # 数据质量阈值
    min_matches_for_form: int = Field(
        default=3,
        ge=1,
        description="计算形态特征所需的最少比赛场次"
    )

    min_matches_for_xg: int = Field(
        default=2,
        ge=1,
        description="计算xG特征所需的最少比赛场次"
    )

    # 特征质量评分权重
    completeness_weights: Dict[str, float] = Field(
        default={
            "form_features": 0.3,
            "xg_features": 0.3,
            "odds_features": 0.2,
            "h2h_features": 0.2
        },
        description="特征完整性评分权重"
    )

    # 默认值配置
    default_form_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="默认形态得分"
    )

    default_xg_efficiency: float = Field(
        default=1.0,
        ge=0,
        description="默认xG效率"
    )

    default_odds_prob: float = Field(
        default=0.33,
        ge=0,
        le=1,
        description="默认赔率概率"
    )


# 便捷工厂函数
def create_empty_feature_set(match_id: str, home_team_id: str, away_team_id: str,
                           match_date: datetime) -> MatchFeatureSet:
    """
    创建空的特征集，用于后续填充

    Args:
        match_id: 比赛ID
        home_team_id: 主队ID
        away_team_id: 客队ID
        match_date: 比赛日期

    Returns:
        MatchFeatureSet: 空的特征集
    """

    # 创建空的TeamFormFeatures
    empty_form = TeamFormFeatures(
        matches_played=0,
        wins=0,
        draws=0,
        losses=0,
        goals_scored=0,
        goals_conceded=0,
        goal_difference=0,
        points=0,
        weighted_points=0.0,
        avg_goals_scored=0.0,
        avg_goals_conceded=0.0,
        clean_sheets=0,
        failed_to_score=0,
        current_win_streak=0,
        current_unbeaten_streak=0
    )

    # 创建空的XGFeatures
    empty_xg = XGFeatures(
        total_xg=0.0,
        total_goals=0,
        xg_efficiency=0.0,
        avg_xg_per_match=0.0,
        avg_goals_per_match=0.0,
        big_chances_created=0,
        big_chances_converted=0,
        big_chance_conversion_rate=0.0,
        xg_trend_5=0.0,
        xg_trend_3=0.0
    )

    # 创建空的OddsFeatures
    empty_odds = OddsFeatures()

    return MatchFeatureSet(
        match_id=match_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        match_date=match_date,
        home_form_last5=empty_form,
        away_form_last5=empty_form,
        home_form_last3=empty_form,
        away_form_last3=empty_form,
        home_xg_last5=empty_xg,
        away_xg_last5=empty_xg,
        home_xg_last3=empty_xg,
        away_xg_last3=empty_xg,
        odds=empty_odds,
        h2h_total_matches=0,
        h2h_home_wins=0,
        h2h_away_wins=0,
        h2h_draws=0,
        h2h_home_win_rate=0.0,
        feature_completeness_score=0.0,
        data_quality_flag="LOW"
    )


if __name__ == "__main__":
    # Schema验证测试
    print("🧪 特征Schema验证测试")

    try:
        # 测试正常数据
        from datetime import datetime

        feature_set = create_empty_feature_set(
            match_id="test_match",
            home_team_id="team_1",
            away_team_id="team_2",
            match_date=datetime.now()
        )

        print(f"✅ 空特征集创建成功: {feature_set.match_id}")
        print(f"   特征向量维度: {len(feature_set.get_feature_vector())}")
        print(f"   特征名称: {feature_set.get_feature_names()[:3]}...")

        # 测试特征向量
        vector = feature_set.get_feature_vector()
        print(f"   特征向量: {vector[:5]}...")

    except Exception as e:
        print(f"❌ Schema验证失败: {e}")
        raise