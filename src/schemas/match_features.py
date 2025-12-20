#!/usr/bin/env python3
"""
Match Features Pydantic Schema - 106个字段的类型安全模型
确保数据质量和类型验证
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class WeatherCondition(str, Enum):
    """天气状况枚举"""

    SUNNY = "sunny"
    RAINY = "rainy"
    CLOUDY = "cloudy"
    SNOWY = "snowy"
    WINDY = "windy"
    UNKNOWN = "unknown"


class FeatureVersion(str, Enum):
    """特征版本枚举"""

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class DataSource(str, Enum):
    """数据源枚举"""

    FOTMOB_API = "fotmob_api"
    BET365_API = "bet365_api"
    MANUAL = "manual"
    IMPORTED = "imported"


class MatchFeatures(BaseModel):
    """
    比赛特征模型 - 106个字段的完整定义
    类型安全的数据验证和序列化
    """

    # ==================== 基础字段 (10个) ====================
    external_id: str = Field(..., description="比赛外部ID")
    match_time: datetime = Field(..., description="比赛时间")
    home_team: str = Field(..., min_length=1, max_length=100, description="主队名称")
    away_team: str = Field(..., min_length=1, max_length=100, description="客队名称")
    league_id: Optional[str] = Field(None, max_length=20, description="联赛ID")
    league_name: Optional[str] = Field(None, max_length=100, description="联赛名称")
    season: Optional[str] = Field(None, max_length=20, description="赛季")
    status: Optional[str] = Field(None, max_length=50, description="比赛状态")
    home_score: Optional[int] = Field(None, ge=0, description="主队得分")
    away_score: Optional[int] = Field(None, ge=0, description="客队得分")

    # ==================== xG相关特征 (10个) ====================
    home_xg: Optional[float] = Field(None, ge=0.0, description="主队期望进球数")
    away_xg: Optional[float] = Field(None, ge=0.0, description="客队期望进球数")
    xg_total: Optional[float] = Field(None, ge=0.0, description="总期望进球数")
    xg_diff: Optional[float] = Field(None, description="期望进球差值")
    home_xg_first_half: Optional[float] = Field(None, ge=0.0, description="上半场主队期望进球数")
    away_xg_first_half: Optional[float] = Field(None, ge=0.0, description="上半场客队期望进球数")
    xg_total_first_half: Optional[float] = Field(None, ge=0.0, description="上半场总期望进球数")
    home_xg_second_half: Optional[float] = Field(None, ge=0.0, description="下半场主队期望进球数")
    away_xg_second_half: Optional[float] = Field(None, ge=0.0, description="下半场客队期望进球数")
    xg_total_second_half: Optional[float] = Field(None, ge=0.0, description="下半场总期望进球数")
    xg_dynamic_trend: Optional[str] = Field(None, max_length=20, description="xG动态趋势")

    # ==================== 控球率特征 (8个) ====================
    home_possession: Optional[float] = Field(None, ge=0.0, le=100.0, description="主队控球率(%)")
    away_possession: Optional[float] = Field(None, ge=0.0, le=100.0, description="客队控球率(%)")
    possession_diff: Optional[float] = Field(None, ge=-100.0, le=100.0, description="控球率差值")
    home_possession_first_half: Optional[float] = Field(None, ge=0.0, le=100.0, description="上半场主队控球率")
    away_possession_first_half: Optional[float] = Field(None, ge=0.0, le=100.0, description="上半场客队控球率")
    possession_first_half_diff: Optional[float] = Field(None, ge=-100.0, le=100.0, description="上半场控球率差值")
    home_possession_second_half: Optional[float] = Field(None, ge=0.0, le=100.0, description="下半场主队控球率")
    away_possession_second_half: Optional[float] = Field(None, ge=0.0, le=100.0, description="下半场客队控球率")
    possession_second_half_diff: Optional[float] = Field(None, ge=-100.0, le=100.0, description="下半场控球率差值")

    # ==================== 射门数据 (12个) ====================
    home_shots_total: Optional[int] = Field(None, ge=0, description="主队总射门数")
    away_shots_total: Optional[int] = Field(None, ge=0, description="客队总射门数")
    shots_total_diff: Optional[int] = Field(None, description="总射门数差值")
    home_shots_on_target: Optional[int] = Field(None, ge=0, description="主队射正数")
    away_shots_on_target: Optional[int] = Field(None, ge=0, description="客队射正数")
    shots_on_target_diff: Optional[int] = Field(None, description="射正数差值")
    home_shots_off_target: Optional[int] = Field(None, ge=0, description="主队射偏数")
    away_shots_off_target: Optional[int] = Field(None, ge=0, description="客队射偏数")
    shots_off_target_diff: Optional[int] = Field(None, description="射偏数差值")
    home_shots_blocked: Optional[int] = Field(None, ge=0, description="主队被封堵射门数")
    away_shots_blocked: Optional[int] = Field(None, ge=0, description="客队被封堵射门数")
    shots_blocked_diff: Optional[int] = Field(None, description="被封堵射门数差值")
    home_shot_accuracy: Optional[float] = Field(None, ge=0.0, le=100.0, description="主队射门准确率")
    away_shot_accuracy: Optional[float] = Field(None, ge=0.0, le=100.0, description="客队射门准确率")
    shot_accuracy_diff: Optional[float] = Field(None, ge=-100.0, le=100.0, description="射门准确率差值")

    # ==================== 角球数据 (8个) ====================
    home_corners: Optional[int] = Field(None, ge=0, description="主队角球数")
    away_corners: Optional[int] = Field(None, ge=0, description="客队角球数")
    corners_diff: Optional[int] = Field(None, description="角球数差值")
    home_corners_first_half: Optional[int] = Field(None, ge=0, description="上半场主队角球数")
    away_corners_first_half: Optional[int] = Field(None, ge=0, description="上半场客队角球数")
    corners_first_half_diff: Optional[int] = Field(None, description="上半场角球数差值")
    home_corners_second_half: Optional[int] = Field(None, ge=0, description="下半场主队角球数")
    away_corners_second_half: Optional[int] = Field(None, ge=0, description="下半场客队角球数")
    corners_second_half_diff: Optional[int] = Field(None, description="下半场角球数差值")

    # ==================== 犯规数据 (6个) ====================
    home_fouls: Optional[int] = Field(None, ge=0, description="主队犯规数")
    away_fouls: Optional[int] = Field(None, ge=0, description="客队犯规数")
    fouls_diff: Optional[int] = Field(None, description="犯规数差值")
    home_yellow_cards: Optional[int] = Field(None, ge=0, description="主队黄牌数")
    away_yellow_cards: Optional[int] = Field(None, ge=0, description="客队黄牌数")
    yellow_cards_diff: Optional[int] = Field(None, description="黄牌数差值")
    home_red_cards: Optional[int] = Field(None, ge=0, description="主队红牌数")
    away_red_cards: Optional[int] = Field(None, ge=0, description="客队红牌数")
    red_cards_diff: Optional[int] = Field(None, description="红牌数差值")

    # ==================== 越位数据 (3个) ====================
    home_offsides: Optional[int] = Field(None, ge=0, description="主队越位数")
    away_offsides: Optional[int] = Field(None, ge=0, description="客队越位数")
    offsides_diff: Optional[int] = Field(None, description="越位数差值")

    # ==================== 传球数据 (9个) ====================
    home_passes: Optional[int] = Field(None, ge=0, description="主队传球数")
    away_passes: Optional[int] = Field(None, ge=0, description="客队传球数")
    passes_diff: Optional[int] = Field(None, description="传球数差值")
    home_pass_accuracy: Optional[float] = Field(None, ge=0.0, le=100.0, description="主队传球准确率")
    away_pass_accuracy: Optional[float] = Field(None, ge=0.0, le=100.0, description="客队传球准确率")
    pass_accuracy_diff: Optional[float] = Field(None, ge=-100.0, le=100.0, description="传球准确率差值")
    home_successful_passes: Optional[int] = Field(None, ge=0, description="主队成功传球数")
    away_successful_passes: Optional[int] = Field(None, ge=0, description="客队成功传球数")
    successful_passes_diff: Optional[int] = Field(None, description="成功传球数差值")

    # ==================== 头球数据 (5个) ====================
    home_aerial_won: Optional[int] = Field(None, ge=0, description="主队头球成功次数")
    away_aerial_won: Optional[int] = Field(None, ge=0, description="客队头球成功次数")
    aerial_won_diff: Optional[int] = Field(None, description="头球成功次数差值")
    home_aerial_won_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="主队头球成功率")
    away_aerial_won_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="客队头球成功率")
    aerial_won_percentage_diff: Optional[float] = Field(None, ge=-100.0, le=100.0, description="头球成功率差值")

    # ==================== 赔率数据 (13个) ====================
    home_opening_odds: Optional[float] = Field(None, ge=0.0, description="主队开盘赔率")
    away_opening_odds: Optional[float] = Field(None, ge=0.0, description="客队开盘赔率")
    draw_odds: Optional[float] = Field(None, ge=0.0, description="平局开盘赔率")
    home_current_odds: Optional[float] = Field(None, ge=0.0, description="主队当前赔率")
    away_current_odds: Optional[float] = Field(None, ge=0.0, description="客队当前赔率")
    draw_current_odds: Optional[float] = Field(None, ge=0.0, description="平局当前赔率")
    odds_movement_home: Optional[float] = Field(None, description="主队赔率变化")
    odds_movement_away: Optional[float] = Field(None, description="客队赔率变化")
    odds_movement_draw: Optional[float] = Field(None, description="平局赔率变化")
    implied_home_win_prob: Optional[float] = Field(None, ge=0.0, le=1.0, description="主队隐胜概率")
    implied_away_win_prob: Optional[float] = Field(None, ge=0.0, le=1.0, description="客队隐胜概率")
    implied_draw_prob: Optional[float] = Field(None, ge=0.0, le=1.0, description="平局隐胜概率")

    # ==================== 市场数据 (3个) ====================
    total_over_under: Optional[float] = Field(None, gt=0.0, description="大小球盘口")
    asian_handicap: Optional[float] = Field(None, description="亚洲盘口")
    both_teams_to_score_odds: Optional[float] = Field(None, gt=0.0, description="双方进球赔率")

    # ==================== 历史H2H数据 (5个) ====================
    home_team_h2h_wins: Optional[int] = Field(None, ge=0, description="主队历史交锋胜场")
    away_team_h2h_wins: Optional[int] = Field(None, ge=0, description="客队历史交锋胜场")
    h2h_draws: Optional[int] = Field(None, ge=0, description="历史交锋平场")
    home_team_h2h_goals: Optional[int] = Field(None, ge=0, description="主队历史交锋进球数")
    away_team_h2h_goals: Optional[int] = Field(None, ge=0, description="客队历史交锋进球数")

    # ==================== 近期状态数据 (6个) ====================
    home_team_form_points: Optional[int] = Field(None, description="主队近期积分")
    away_team_form_points: Optional[int] = Field(None, description="客队近期积分")
    home_team_recent_goals: Optional[int] = Field(None, ge=0, description="主队近期进球数")
    away_team_recent_goals: Optional[int] = Field(None, ge=0, description="客队近期进球数")
    home_team_recent_conceded: Optional[int] = Field(None, ge=0, description="主队近期失球数")
    away_team_recent_conceded: Optional[int] = Field(None, ge=0, description="客队近期失球数")

    # ==================== 天气和场地数据 (3个) ====================
    weather_condition: Optional[WeatherCondition] = Field(None, description="天气状况")
    temperature: Optional[float] = Field(None, description="温度(摄氏度)")
    home_advantage_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="主场优势评分")

    # ==================== 高级技术统计 (6个) ====================
    expected_assists_home: Optional[float] = Field(None, ge=0.0, description="主队期望助攻数")
    expected_assists_away: Optional[float] = Field(None, ge=0.0, description="客队期望助攻数")
    big_chances_home: Optional[int] = Field(None, ge=0, description="主队大机会数")
    big_chances_away: Optional[int] = Field(None, ge=0, description="客队大机会数")
    big_chances_missed_home: Optional[int] = Field(None, ge=0, description="主队错失大机会数")
    big_chances_missed_away: Optional[int] = Field(None, ge=0, description="客队错失大机会数")

    # ==================== 裁判和VAR数据 (2个) ====================
    referee_name: Optional[str] = Field(None, max_length=100, description="裁判姓名")
    var_used: Optional[bool] = Field(None, description="是否使用VAR")

    # ==================== 元数据 (9个) ====================
    raw_data_source: DataSource = Field(DataSource.FOTMOB_API, description="数据源")
    feature_version: FeatureVersion = Field(FeatureVersion.V1_0, description="特征版本")
    feature_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="特征质量评分")
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="提取置信度")
    data_completeness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="数据完整性评分")
    extracted_at: datetime = Field(default_factory=datetime.now, description="提取时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            WeatherCondition: lambda v: v.value,
            DataSource: lambda v: v.value,
            FeatureVersion: lambda v: v.value,
        },
    )

    xg_total: Optional[float] = Field(default=None, description="总xG")
    xg_diff: Optional[float] = Field(default=None, description="xG差值")
    possession_diff: Optional[float] = Field(default=None, description="控球率差值")

    @computed_field
    @property
    def total_features_count(self) -> int:
        """总特征数量"""
        return 106

    @computed_field
    @property
    def has_complete_xg_data(self) -> bool:
        """是否有完整的xG数据"""
        return all(
            [self.home_xg is not None, self.away_xg is not None, self.xg_total is not None, self.xg_diff is not None]
        )

    @computed_field
    @property
    def has_complete_odds_data(self) -> bool:
        """是否有完整的赔率数据"""
        return all([self.home_opening_odds is not None, self.away_opening_odds is not None, self.draw_odds is not None])


class MatchFeaturesTrainingBatch(BaseModel):
    """批量比赛特征模型"""

    features: list[MatchFeatures]
    batch_id: str
    batch_size: int
    total_processed: int
    processing_time_seconds: float

    @field_validator("batch_size", mode="before")
    @classmethod
    def validate_batch_size(cls, v, info):
        """验证批次大小"""
        values = info.data if hasattr(info, "data") else {}
        if "features" in values:
            return len(values["features"])
        return v

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class FeatureExtractionRequest(BaseModel):
    """特征提取请求模型"""

    match_ids: list[str]
    extraction_mode: str = Field("full", pattern="^(full|incremental)$")
    batch_size: int = Field(50, ge=1, le=1000)
    use_cache: bool = True
    extract_advanced_features: bool = True


class FeatureExtractionResponse(BaseModel):
    """特征提取响应模型"""

    request_id: str
    status: str = Field(..., pattern="^(success|partial|failed)$")
    processed_count: int
    total_count: int
    success_count: int
    failed_count: int
    processing_time_seconds: float
    features: Optional[list[MatchFeatures]] = None
    errors: Optional[list[str]] = None
    metadata: Optional[Dict[str, Any]] = None


# 导出的便捷函数
def create_match_features_from_dict(data: Dict[str, Any]) -> MatchFeatures:
    """从字典创建MatchFeatures实例"""
    return MatchFeatures(**data)


def validate_feature_completeness(features: MatchFeatures) -> float:
    """验证特征完整性并返回完整性分数"""
    total_fields = 106
    non_null_fields = sum(1 for field, value in features.model_dump().items() if value is not None and value != "")
    return non_null_fields / total_fields


if __name__ == "__main__":
    # 测试模型
    test_data = {
        "external_id": "test_123",
        "match_time": "2024-01-15T20:00:00Z",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "home_xg": 1.5,
        "away_xg": 1.2,
        "home_possession": 55.0,
        "away_possession": 45.0,
        "home_opening_odds": 2.15,
        "away_opening_odds": 3.40,
        "draw_odds": 3.20,
    }

    features = create_match_features_from_dict(test_data)
    print(f"✅ 创建特征模型成功!")
    print(f"📊 总特征数: {features.total_features_count}")
    print(f"🎯 xG数据完整: {features.has_complete_xg_data}")
    print(f"💰 赔率数据完整: {features.has_complete_odds_data}")
    print(f"📈 特征完整性: {validate_feature_completeness(features):.2%}")
