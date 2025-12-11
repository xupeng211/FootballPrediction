#!/usr/bin/env python3
"""
L2数据模式定义 (Pydantic V2 Models)
L2 Data Schema Definitions using Pydantic V2

定义L2数据处理所需的所有数据模型，包括：
- 赔率数据 (Odds)
- 裁判信息 (Referee)
- 详细统计数据 (Match Statistics)
- 阵容信息 (Lineups)
- 比赛事件 (Match Events)
- 射门数据 (Shot Data)
- 球员评分 (Player Ratings)

作者: L2重构团队
创建时间: 2025-12-10
版本: 2.0.0 (Pydantic V2升级)
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ============ 基础枚举定义 ============


class MatchStatus(str, Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    HALFTIME = "halftime"
    FULLTIME = "FT"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"
    FINISHED = "finished"


class CardType(str, Enum):
    """牌型枚举"""

    YELLOW = "yellow"
    RED = "red"
    YELLOW_RED = "yellow_red"


class EventType(str, Enum):
    """比赛事件类型"""

    GOAL = "Goal"
    OWN_GOAL = "OwnGoal"
    PENALTY_GOAL = "PenaltyGoal"
    MISSSED_PENALTY = "MissedPenalty"
    CARD = "Card"
    SUBSTITUTION = "Substitution"
    VAR = "Var"


# ============ 基础数据模型定义 ============


class ShotData(BaseModel):
    """射门数据模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    minute: int = Field(0, ge=0, le=120, description="射门发生分钟")
    player_name: Optional[str] = Field(None, description="射门球员姓名")
    team_id: str = Field(..., description="球队ID")
    x: float = Field(0.0, description="球场X坐标(0-100)")
    y: float = Field(0.0, description="球场Y坐标(0-100)")
    is_on_target: bool = Field(False, description="是否射正")
    expected_goals: float = Field(0.0, ge=0.0, description="期望进球值(xG)")
    shot_type: Optional[str] = Field(None, description="射门类型")
    is_goal: bool = Field(False, description="是否进球")
    is_blocked: bool = Field(False, description="是否被封堵")


class L2PlayerRating(BaseModel):
    """L2球员评分模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    player_id: str = Field(..., description="球员ID")
    player_name: str = Field("", description="球员姓名")
    rating: float = Field(0.0, ge=0.0, le=10.0, description="球员评分")
    position: Optional[str] = Field(None, description="场上位置")
    minutes_played: Optional[int] = Field(None, ge=0, description="出场时间")


class OddsData(BaseModel):
    """赔率数据模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    home_win: Optional[float] = Field(None, description="主胜赔率", gt=0)
    draw: Optional[float] = Field(None, description="平局赔率", gt=0)
    away_win: Optional[float] = Field(None, description="客胜赔率", gt=0)
    asian_handicap: Optional[Dict[str, float]] = Field(None, description="亚盘赔率")
    over_under: Optional[float] = Field(None, description="大小球赔率")
    both_teams_score: Optional[Dict[str, float]] = Field(
        None, description="两队都得分赔率"
    )
    provider: Optional[str] = Field(None, description="赔率提供商")
    snapshot_time: Optional[str] = Field(None, description="赔率快照时间")


class RefereeInfo(BaseModel):
    """裁判信息模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    name: Optional[str] = Field(None, description="裁判姓名")
    nationality: Optional[str] = Field(None, description="裁判国籍")
    age: Optional[int] = Field(None, description="裁判年龄", ge=0)
    matches_officiated: Optional[int] = Field(None, description="执法场次", ge=0)
    yellow_cards_per_game: Optional[float] = Field(None, description="场均黄牌", ge=0)
    red_cards_per_game: Optional[float] = Field(None, description="场均红牌", ge=0)


class PlayerStats(BaseModel):
    """球员统计数据"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    player_id: Optional[str] = Field(None, description="球员ID")
    player_name: Optional[str] = Field(None, description="球员姓名")
    position: Optional[str] = Field(None, description="场上位置")
    shirt_number: Optional[int] = Field(None, description="球衣号码", ge=0, le=99)
    goals: int = Field(0, description="进球数", ge=0)
    assists: int = Field(0, description="助攻数", ge=0)
    yellow_cards: int = Field(0, description="黄牌数", ge=0)
    red_cards: int = Field(0, description="红牌数", ge=0)
    shots: int = Field(0, description="射门次数", ge=0)
    shots_on_target: int = Field(0, description="射正次数", ge=0)
    passes: int = Field(0, description="传球次数", ge=0)
    pass_accuracy: Optional[float] = Field(None, description="传球成功率", ge=0, le=100)
    minutes_played: Optional[int] = Field(None, description="出场时间", ge=0)
    rating: Optional[float] = Field(None, description="球员评分", ge=0, le=10)
    stats: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="其他统计数据"
    )

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """验证评分范围"""
        if v is not None and (v < 0 or v > 10):
            raise ValueError("球员评分必须在0-10之间")
        return v


class TeamStats(BaseModel):
    """球队统计数据"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    possession: Optional[float] = Field(None, ge=0, le=100, description="控球率(%)")
    shots: int = Field(0, ge=0, description="射门次数")
    shots_on_target: int = Field(0, ge=0, description="射正次数")
    corners: int = Field(0, ge=0, description="角球数")
    fouls: int = Field(0, ge=0, description="犯规次数")
    offsides: int = Field(0, ge=0, description="越位数")
    yellow_cards: int = Field(0, ge=0, description="黄牌数")
    red_cards: int = Field(0, ge=0, description="红牌数")
    saves: int = Field(0, ge=0, description="扑救数")
    expected_goals: float = Field(0.0, ge=0, description="期望进球数(xG)")
    big_chances_created: int = Field(0, ge=0, description="创造大机会数")
    big_chances_missed: int = Field(0, ge=0, description="错失大机会数")
    passes: int = Field(0, ge=0, description="传球次数")
    pass_accuracy: Optional[float] = Field(
        None, ge=0, le=100, description="传球成功率(%)"
    )
    tackles: int = Field(0, ge=0, description="抢断次数")
    interceptions: int = Field(0, ge=0, description="拦截次数")
    aerials_won: Optional[int] = Field(None, ge=0, description="高空球争胜数")
    blocked_shots: Optional[int] = Field(None, ge=0, description="被封堵射门数")
    clearances: Optional[int] = Field(None, ge=0, description="解围次数")
    touches: Optional[int] = Field(None, ge=0, description="触球次数")
    counter_attacks: Optional[int] = Field(
        None, ge=0, description="快速反击次数，FotMob V2+支持"
    )
    through_balls: Optional[int] = Field(
        None, ge=0, description="直塞球次数，FotMob V2+支持"
    )
    long_balls: Optional[int] = Field(
        None, ge=0, description="长传次数，FotMob V2+支持"
    )
    crosses: Optional[int] = Field(None, ge=0, description="传中次数，FotMob V2+支持")


class MatchEvent(BaseModel):
    """比赛事件模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    event_id: Optional[str] = Field(None, description="事件ID")
    event_type: EventType = Field(..., description="事件类型")
    minute: int = Field(..., ge=0, le=120, description="事件发生分钟")
    team: str = Field(..., description="球队 (home/away)")
    player: Optional[str] = Field(None, description="相关球员")
    second_player: Optional[str] = Field(None, description="第二相关球员(如换人)")
    card_type: Optional[CardType] = Field(None, description="牌型")
    is_own_goal: Optional[bool] = Field(None, description="是否乌龙球")
    is_penalty: bool = Field(False, description="是否点球")
    description: Optional[str] = Field(None, description="事件描述")
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="事件详细信息"
    )


class L2MatchEvent(BaseModel):
    """L2比赛事件模型 (简化版，用于L2Parser)"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    event_type: str = Field(..., description="事件类型")
    minute: int = Field(..., ge=0, le=120, description="事件发生分钟")
    player_name: str = Field("", description="相关球员")
    team_id: str = Field("", description="球队ID")
    description: Optional[str] = Field(None, description="事件描述")
    is_goal: bool = Field(False, description="是否进球")
    is_own_goal: Optional[bool] = Field(None, description="是否乌龙球")
    card_type: Optional[str] = Field(None, description="牌型")
    substituted_player: Optional[str] = Field(None, description="被换下球员")


class WeatherInfo(BaseModel):
    """天气信息模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    temperature: Optional[float] = Field(None, description="温度(摄氏度)")
    humidity: Optional[float] = Field(None, ge=0, le=100, description="湿度(%)")
    wind_speed: Optional[float] = Field(None, ge=0, description="风速(km/h)")
    wind_direction: Optional[str] = Field(None, description="风向")
    weather_condition: Optional[str] = Field(None, description="天气状况")
    precipitation: Optional[float] = Field(None, ge=0, description="降水量(mm)")
    condition: Optional[str] = Field(None, description="天气条件描述")


class StadiumInfo(BaseModel):
    """球场信息模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    name: Optional[str] = Field(None, description="球场名称")
    city: Optional[str] = Field(None, description="所在城市")
    capacity: Optional[int] = Field(None, ge=0, description="容量")
    surface: Optional[str] = Field(None, description="场地类型")
    attendance: Optional[int] = Field(None, ge=0, description="现场观众数")
    country: Optional[str] = Field(None, description="所在国家")


class LineupPlayer(BaseModel):
    """阵容球员模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    id: Optional[str] = Field(None, description="球员ID")
    name: str = Field(..., description="球员姓名")
    fullName: Optional[str] = Field(None, description="球员全名")
    shirtNumber: Optional[int] = Field(None, ge=0, le=99, description="球衣号码")
    position: str = Field(..., description="位置")
    positionId: Optional[int] = Field(None, description="位置ID")
    is_starting: bool = Field(True, description="是否首发")
    captain: bool = Field(False, description="是否队长")
    substitute_on_minute: Optional[int] = Field(None, ge=0, description="上场时间")
    substitute_off_minute: Optional[int] = Field(None, ge=0, description="下场时间")
    rating: Optional[Dict[str, Any]] = Field(None, description="球员评分")


class TeamLineup(BaseModel):
    """球队阵容模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        populate_by_name=True,
    )

    formation: Optional[str] = Field(None, description="阵型")
    starters: List[Dict[str, Any]] = Field(default_factory=list, description="首发阵容")
    substitutes: List[Dict[str, Any]] = Field(
        default_factory=list, description="替补球员"
    )
    manager: Optional[str] = Field(None, description="主教练")
    formation_image: Optional[str] = Field(None, description="阵型图")


class Lineup(BaseModel):
    """阵容模型 (兼容版本)"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        populate_by_name=True,
    )

    formation: Optional[str] = Field(None, description="阵型")
    starters: List[Dict[str, Any]] = Field(default_factory=list, description="首发阵容")
    formation_image: Optional[str] = Field(None, description="阵型图")


# ============ 核心数据模型 ============


class L2MatchData(BaseModel):
    """L2比赛详情核心数据模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    match_id: str = Field(..., description="比赛ID")
    fotmob_id: str = Field(..., description="FotMob比赛ID")
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    home_score: int = Field(0, ge=0, le=100, description="主队得分")
    away_score: int = Field(0, ge=0, le=100, description="客队得分")
    status: str = Field("scheduled", description="比赛状态")
    kickoff_time: Optional[datetime] = Field(None, description="开球时间")

    # 比赛环境信息
    stadium_info: Optional[StadiumInfo] = Field(None, description="场地信息")
    referee_info: Optional[RefereeInfo] = Field(None, description="裁判信息")
    weather_info: Optional[WeatherInfo] = Field(None, description="天气信息")

    # 核心统计数据
    home_stats: TeamStats = Field(default_factory=TeamStats, description="主队统计")
    away_stats: TeamStats = Field(default_factory=TeamStats, description="客队统计")

    # 比赛事件时间轴
    events: List[L2MatchEvent] = Field(default_factory=list, description="比赛事件")

    # 射门分布图
    shot_map: List[ShotData] = Field(default_factory=list, description="射门分布图")

    # 阵容信息
    home_lineup: Optional[Union[TeamLineup, Lineup]] = Field(
        None, description="主队阵容"
    )
    away_lineup: Optional[Union[TeamLineup, Lineup]] = Field(
        None, description="客队阵容"
    )

    # 球员评分数据
    player_ratings: Dict[str, L2PlayerRating] = Field(
        default_factory=dict, description="球员评分"
    )

    # 赔率数据
    odds_data: Optional[OddsData] = Field(None, description="赔率数据")

    # 元数据
    data_source: str = Field("fotmob", description="数据源")
    collected_at: Union[datetime, str] = Field(
        default_factory=datetime.utcnow, description="采集时间"
    )
    data_completeness_score: float = Field(
        0.0, ge=0, le=1, description="数据完整性评分"
    )

    @model_validator(mode="after")
    def validate_scores_consistency(self) -> "L2MatchData":
        """验证比分一致性"""
        if self.status == "scheduled" and (self.home_score > 0 or self.away_score > 0):
            raise ValueError("未开始的比赛比分应该为0")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于数据库存储"""
        data = self.model_dump(exclude_none=True)

        # 处理datetime序列化
        if isinstance(data.get("collected_at"), datetime):
            data["collected_at"] = data["collected_at"].isoformat()
        if isinstance(data.get("kickoff_time"), datetime):
            data["kickoff_time"] = data["kickoff_time"].isoformat()

        return data


class L2DataProcessingResult(BaseModel):
    """L2数据处理结果模型"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="allow",
        use_enum_values=True,
    )

    success: bool = Field(..., description="处理是否成功")
    data: Optional[L2MatchData] = Field(None, description="处理后的数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    processing_stats: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="处理统计信息"
    )
    parsed_sections: Optional[List[str]] = Field(
        default_factory=list, description="已解析的部分"
    )


# ============ 数据验证模型 ============


class L2DataValidationRule(BaseModel):
    """L2数据验证规则"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    field_name: str = Field(..., description="字段名称")
    required: bool = Field(True, description="是否必需")
    validation_type: str = Field(..., description="验证类型")
    min_value: Optional[Union[int, float]] = Field(None, description="最小值")
    max_value: Optional[Union[int, float]] = Field(None, description="最大值")
    allowed_values: Optional[List[str]] = Field(None, description="允许的值列表")


class L2DataValidationResult(BaseModel):
    """L2数据验证结果"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    is_valid: bool = Field(..., description="数据是否有效")
    errors: List[str] = Field(default_factory=list, description="验证错误列表")
    warnings: List[str] = Field(default_factory=list, description="验证警告列表")
    missing_fields: List[str] = Field(default_factory=list, description="缺失字段列表")
    data_completeness_score: float = Field(
        0.0, ge=0, le=1, description="数据完整性评分"
    )


# ============ 兼容性别名 ============
# 为了向后兼容以及适配 L2Parser 的引用，提供以下别名

L2ShotData = ShotData
L2MatchEvent = L2MatchEvent
L2TeamStats = TeamStats
L2OddsData = OddsData
L2TeamLineup = TeamLineup
L2LineupPlayer = LineupPlayer
L2WeatherInfo = WeatherInfo
L2StadiumInfo = StadiumInfo
L2RefereeInfo = RefereeInfo
L2PlayerStats = PlayerStats


# ============ 导出所有模型 ============
__all__ = [
    # 枚举
    "MatchStatus",
    "CardType",
    "EventType",
    # 基础数据模型
    "ShotData",
    "L2PlayerRating",
    "OddsData",
    "RefereeInfo",
    "PlayerStats",
    "TeamStats",
    "MatchEvent",
    "L2MatchEvent",
    "WeatherInfo",
    "StadiumInfo",
    "LineupPlayer",
    "TeamLineup",
    "Lineup",
    # 兼容性别名
    "L2ShotData",
    "L2MatchEvent",
    "L2TeamStats",
    "L2OddsData",
    "L2TeamLineup",
    "L2LineupPlayer",
    "L2WeatherInfo",
    "L2StadiumInfo",
    "L2RefereeInfo",
    "L2PlayerStats",
    # 核心数据模型
    "L2MatchData",
    "L2DataProcessingResult",
    # 验证模型
    "L2DataValidationRule",
    "L2DataValidationResult",
]
