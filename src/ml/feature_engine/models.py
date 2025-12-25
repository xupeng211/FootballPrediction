"""
Data Models - Pydantic 数据模型定义
====================================

使用 Pydantic V2 进行严格的数据验证和序列化。
所有外部数据在进入特征提取流程前必须通过 Schema 校验。

设计原则:
    - 类型安全: 所有字段都有明确类型注解
    - 验证优先: 数据进入系统前必须通过校验
    - 金融级精度: 关键指标使用 Decimal 类型
    - 向后兼容: 支持可选字段和默认值

作者: FootballPrediction Architecture Team
版本: V21.0-alpha
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


# ============================================================================
# 枚举类型定义
# ============================================================================

class MatchStatus(str, Enum):
    """比赛状态枚举"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class HomeAway(str, Enum):
    """主客队标识"""
    HOME = "home"
    AWAY = "away"


class LeagueTier(str, Enum):
    """联赛等级（用于哨兵机制）"""
    TOP_5 = "top_5"          # 五大联赛
    TOP_TIER = "top_tier"    # 顶级联赛
    SECOND_TIER = "second_tier"  # 次级联赛


# ============================================================================
# 基础数据模型
# ============================================================================

class TeamStats(BaseModel):
    """
    球队统计数据模型

    对应 FotMob API 的 teamData 结构
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    # 基础统计
    shots_total: Optional[int] = Field(None, alias="shotsTotal")
    shots_on_target: Optional[int] = Field(None, alias="shotsOnTarget")
    possession: Optional[float] = Field(None, ge=0, le=100)
    corners: Optional[int] = None
    offsides: Optional[int] = None
    fouls: Optional[int] = None

    # 高级统计
    expected_goals: Optional[float] = Field(None, ge=0, alias="expectedGoals")
    expected_goals_from_shots: Optional[float] = Field(
        None, ge=0, alias="expectedGoalsFromShots"
    )
    total_passes: Optional[int] = Field(None, ge=0, alias="totalPasses")
    accurate_passes: Optional[int] = Field(None, ge=0, alias="accuratePasses")
    team_rating: Optional[float] = Field(None, ge=0, le=10, alias="teamRating")

    # 动量指标
    momentum_scores: Optional[list[float]] = Field(default_factory=list)

    @field_validator("possession")
    @classmethod
    def validate_possession(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("控球率必须在 0-100 之间")
        return v


class PlayerStats(BaseModel):
    """
    球员统计数据模型

    对应 FotMob API 的 playerData 结构

    V22.0 扩展:
        - 新增身价字段（market_value）
        - 新增年龄字段（age）
        - 新增高级传球字段（final_third_passes, long_passes, crosses 等）
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    player_id: Optional[str] = Field(None, alias="playerId")
    player_name: Optional[str] = Field(None, alias="playerName")
    team_id: Optional[str] = Field(None, alias="teamId")
    jersey_number: Optional[int] = Field(None, ge=1, le=99, alias="jerseyNumber")
    is_starter: Optional[bool] = Field(None, alias="isStarter")

    # 场上表现
    minutes_played: Optional[int] = Field(None, ge=0, le=120, alias="minutesPlayed")
    expected_goals: Optional[float] = Field(None, ge=0, alias="expectedGoals")
    total_shots: Optional[int] = Field(None, ge=0, alias="totalShots")
    touches: Optional[int] = Field(None, ge=0)
    accurate_passes: Optional[int] = Field(None, ge=0, alias="accuratePasses")

    # ========== V22.0 新增：身价与年龄 ==========
    market_value: Optional[float] = Field(None, ge=0, alias="marketValue")  # 百万欧元
    age: Optional[int] = Field(None, ge=16, le=50)  # 球员年龄

    # ========== V22.0 新增：高级传球数据 ==========
    # 区域传球
    final_third_passes: Optional[int] = Field(None, ge=0, alias="finalThirdPasses")
    accurate_final_third_passes: Optional[int] = Field(None, ge=0, alias="accurateFinalThirdPasses")
    middle_third_passes: Optional[int] = Field(None, ge=0, alias="middleThirdPasses")
    accurate_middle_third_passes: Optional[int] = Field(None, ge=0, alias="accurateMiddleThirdPasses")
    defensive_third_passes: Optional[int] = Field(None, ge=0, alias="defensiveThirdPasses")
    accurate_defensive_third_passes: Optional[int] = Field(None, ge=0, alias="accurateDefensiveThirdPasses")

    # 传球 DNA（短中长传）
    short_passes: Optional[int] = Field(None, ge=0, alias="shortPasses")
    medium_passes: Optional[int] = Field(None, ge=0, alias="mediumPasses")
    long_passes: Optional[int] = Field(None, ge=0, alias="longPasses")
    accurate_long_passes: Optional[int] = Field(None, ge=0, alias="accurateLongPasses")

    # 传中与直塞
    crosses: Optional[int] = Field(None, ge=0, alias="crosses")
    accurate_crosses: Optional[int] = Field(None, ge=0, alias="accurateCrosses")
    through_balls: Optional[int] = Field(None, ge=0, alias="throughBalls")
    accurate_through_balls: Optional[int] = Field(None, ge=0, alias="accurateThroughBalls")

    # 纵向推进
    forward_passes: Optional[int] = Field(None, ge=0, alias="forwardPasses")
    backward_passes: Optional[int] = Field(None, ge=0, alias="backwardPasses")
    vertical_progression: Optional[float] = Field(None, ge=0, alias="verticalProgression")

    # 创造机会
    key_passes: Optional[int] = Field(None, ge=0, alias="keyPasses")
    big_chances_created: Optional[int] = Field(None, ge=0, alias="bigChancesCreated")

    # ========== V23.0 新增：球员评分 ==========
    team_rating: Optional[float] = Field(None, ge=0, le=10, alias="teamRating")  # 球员评分


class MatchContext(BaseModel):
    """
    比赛上下文信息（V21.0 深度爆破版）

    包含比赛时间、场地、裁判、天气等环境因素
    支持 JSON 路径解析: content.matchFacts.info.*

    V23.0 新增:
        - odds: 市场赔率信息（支持 MarketOddsProcessor）
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    # 时间信息（从 matchTimeUTCDate 解析）
    match_time: Optional[datetime] = Field(None, alias="matchTime")
    kickoff_time: Optional[str] = Field(None, alias="kickoffTime")  # "12:30"

    # 场地信息（从 venue.* 解析）
    venue: Optional[str] = None  # 体育场名称
    venue_capacity: Optional[int] = Field(None, ge=0, alias="venueCapacity")
    venue_attendance: Optional[int] = Field(None, ge=0, alias="venueAttendance")  # V21.0 新增: 观众人数
    is_neutral: Optional[bool] = Field(None, alias="isNeutral")

    # 裁判信息（从 matchFacts.info.referee 解析）
    referee_id: Optional[str] = Field(None, alias="refereeId")
    referee_name: Optional[str] = Field(None, alias="refereeName")
    referee_nationality: Optional[str] = Field(None, alias="refereeNationality")  # V21.0 新增
    referee_strictness: Optional[float] = Field(
        None, ge=0, le=1, alias="refereeStrictness"
    )  # 历史场均黄牌数

    # 天气信息（预留，需要天气 API）
    weather_temperature: Optional[float] = Field(None, alias="weatherTemperature")
    weather_condition: Optional[str] = Field(None, alias="weatherCondition")
    weather_wind_speed: Optional[float] = Field(None, ge=0, alias="weatherWindSpeed")  # V21.0 新增
    weather_humidity: Optional[float] = Field(None, ge=0, le=100, alias="weatherHumidity")  # V21.0 新增

    # 赛程背景
    is_cup_match: Optional[bool] = Field(None, alias="isCupMatch")
    days_since_last_match: Optional[int] = Field(None, ge=0, alias="daysSinceLastMatch")

    # V21.0 新增: 比赛重要性（用于权重调整）
    match_importance: Optional[float] = Field(default=0.5, ge=0, le=1)

    # ========== V23.0 新增：市场赔率信息 ==========
    # 赔率数据（支持多种来源）
    # 格式: {"home": 2.50, "draw": 3.20, "away": 2.80} 或 {"providers": [...]}
    odds: Optional[Dict[str, Any]] = None


class LineupInfo(BaseModel):
    """
    阵容信息模型（V21.0 新增）

    用于分析阵容稳定性和首发预测
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    # 阵容统计
    formation: Optional[str] = None  # "4-3-3"
    starters_count: Optional[int] = Field(None, ge=11, le=11, alias="startersCount")
    substitutes_count: Optional[int] = Field(None, ge=0, alias="substitutesCount")

    # 阵容稳定性指标
    unchanged_lineup: bool = Field(False, alias="unchangedLineup")
    changes_from_last_match: Optional[int] = Field(None, ge=0, alias="changesFromLastMatch")

    # 阵容价值（预估，单位：百万欧元）
    total_market_value: Optional[float] = Field(None, ge=0, alias="totalMarketValue")
    avg_market_value: Optional[float] = Field(None, ge=0, alias="avgMarketValue")

    # 球员列表
    players: list[PlayerStats] = Field(default_factory=list)


# ============================================================================
# 核心数据模型
# ============================================================================

class MatchData(BaseModel):
    """
    比赛数据主模型

    所有外部数据必须经过此模型校验才能进入特征提取流程。
    设计为不可变（frozen=True），防止意外修改。

    Attributes:
        match_id: 比赛唯一标识
        league_id: 联赛 ID
        season: 赛季标识（如 "2324"）
        home_team: 主队名称
        away_team: 客队名称
        status: 比赛状态
        home_score: 主队得分
        away_score: 客队得分
        home_stats: 主队统计数据
        away_stats: 客队统计数据
        context: 比赛上下文（可选）
        home_lineup: 主队阵容（可选）
        away_lineup: 客队阵容（可选）
        raw_data: 原始 JSON 数据（用于调试）
    """
    model_config = ConfigDict(
        frozen=True,  # 不可变
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # 核心标识
    match_id: str = Field(..., min_length=1)
    league_id: str = Field(..., min_length=1)
    season: str = Field(..., pattern=r"^\d{4}$")

    # 球队信息
    home_team: str = Field(..., min_length=1)
    away_team: str = Field(..., min_length=1)

    # 比赛状态
    status: MatchStatus = MatchStatus.SCHEDULED
    home_score: Optional[int] = Field(None, ge=0)
    away_score: Optional[int] = Field(None, ge=0)

    # 统计数据
    home_stats: Optional[TeamStats] = None
    away_stats: Optional[TeamStats] = None

    # V21.0 新增字段
    context: Optional[MatchContext] = None
    home_lineup: Optional[LineupInfo] = None
    away_lineup: Optional[LineupInfo] = None

    # 元数据
    raw_data: Optional[dict[str, Any]] = Field(
        default_factory=dict, exclude=True
    )  # 不导出到 JSON

    @field_validator("season")
    @classmethod
    def validate_season(cls, v: str) -> str:
        if len(v) != 4 or not v.isdigit():
            raise ValueError("season 必须是 4 位数字，如 '2324'")
        return v

    def get_team_stats(self, side: HomeAway) -> Optional[TeamStats]:
        """获取指定球队的统计数据"""
        return self.home_stats if side == HomeAway.HOME else self.away_stats

    def get_team_lineup(self, side: HomeAway) -> Optional[LineupInfo]:
        """获取指定球队的阵容信息"""
        return self.home_lineup if side == HomeAway.HOME else self.away_lineup


# ============================================================================
# 特征向量模型
# ============================================================================

class FeatureVector(BaseModel):
    """
    特征向量模型

    用于标准化特征输出，确保所有特征都有明确的类型和范围约束。
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        # 允许额外字段（便于扩展）
        extra="allow",
    )

    # 元数据
    match_id: str = Field(..., min_length=1)
    feature_version: str = Field(default="21.0.0")
    extracted_at: datetime = Field(default_factory=datetime.now)

    # 特征数据（动态字段，通过 extra="allow" 支持）
    # 建议的命名规范:
    #   - home_xg, away_xg (主客队特征)
    #   - momentum_* (动量特征)
    #   - lineup_* (阵容特征)
    #   - context_* (上下文特征)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（移除元数据）"""
        data = self.model_dump(exclude={"match_id", "feature_version", "extracted_at"})
        return data

    def to_flat_dict(self) -> dict[str, Any]:
        """转换为扁平字典（包含元数据）"""
        return self.model_dump()


# ============================================================================
# 处理上下文模型
# ============================================================================

class ProcessingContext(BaseModel):
    """
    处理上下文模型

    用于在处理器之间传递共享状态和配置。
    支持断点续传和增量处理。

    Attributes:
        match_id: 当前比赛 ID
        session_id: 会话 ID（用于追踪）
        cache: 共享缓存（处理器可读写）
        metadata: 元数据（只读）
        options: 配置选项
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,  # 允许任意类型的缓存
    )

    # 追踪信息
    match_id: Optional[str] = None
    session_id: Optional[str] = Field(default_factory=lambda: f"session_{datetime.now().timestamp()}")

    # 共享状态
    cache: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)

    # 断点续传支持
    checkpoint: dict[str, str] = Field(default_factory=dict)  # 处理器名 -> 状态
    completed_processors: set[str] = Field(default_factory=set)

    def get_option(self, key: str, default: Any = None) -> Any:
        """获取配置选项"""
        return self.options.get(key, default)

    def set_option(self, key: str, value: Any) -> None:
        """设置配置选项"""
        self.options[key] = value

    def get_cached(self, key: str, default: Any = None) -> Any:
        """从缓存获取数据"""
        return self.cache.get(key, default)

    def set_cached(self, key: str, value: Any) -> None:
        """设置缓存数据"""
        self.cache[key] = value

    def mark_completed(self, processor_name: str) -> None:
        """标记处理器已完成"""
        self.completed_processors.add(processor_name)

    def is_completed(self, processor_name: str) -> bool:
        """检查处理器是否已完成"""
        return processor_name in self.completed_processors


# ============================================================================
# 导入列表
# ============================================================================

__all__ = [
    # 枚举
    "MatchStatus",
    "HomeAway",
    "LeagueTier",
    # 数据模型
    "MatchData",
    "TeamStats",
    "PlayerStats",
    "MatchContext",
    "LineupInfo",
    "FeatureVector",
    "ProcessingContext",
]
