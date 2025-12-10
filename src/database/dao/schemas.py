"""
DAO层的Pydantic模式定义
DAO Layer Pydantic Schema Definitions

定义用于数据传输和验证的Pydantic模型。
这些模型用于DAO层的输入输出接口。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class MatchBase(BaseModel):
    """比赛基础模式"""

    home_team_id: int = Field(..., description="主队ID")
    away_team_id: int = Field(..., description="客队ID")
    home_team_name: str = Field(..., min_length=1, max_length=100, description="主队名称")
    away_team_name: str = Field(..., min_length=1, max_length=100, description="客队名称")
    league_id: Optional[int] = Field(None, description="联赛ID")
    match_time: datetime = Field(..., description="比赛时间")
    match_date: Optional[datetime] = Field(None, description="比赛日期")
    venue: Optional[str] = Field(None, max_length=200, description="比赛场地")
    status: str = Field("scheduled", description="比赛状态")
    home_score: Optional[int] = Field(0, description="主队得分")
    away_score: Optional[int] = Field(0, description="客队得分")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """验证比赛状态"""
        allowed_statuses = ['scheduled', 'live', 'finished', 'postponed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'比赛状态必须是以下之一: {allowed_statuses}')
        return v


class MatchCreate(MatchBase):
    """创建比赛模式"""

    pass


class MatchUpdate(BaseModel):
    """更新比赛模式"""

    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_team_name: Optional[str] = Field(None, min_length=1, max_length=100)
    away_team_name: Optional[str] = Field(None, min_length=1, max_length=100)
    league_id: Optional[int] = None
    match_time: Optional[datetime] = None
    match_date: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """验证比赛状态"""
        if v is None:
            return v
        allowed_statuses = ['scheduled', 'live', 'finished', 'postponed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'比赛状态必须是以下之一: {allowed_statuses}')
        return v


class MatchResponse(MatchBase):
    """比赛响应模式"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Odds相关Schemas ====================

class OddsBase(BaseModel):
    """赔率基础模式"""

    match_id: int = Field(..., description="比赛ID")
    bookmaker: str = Field(..., min_length=1, max_length=100, description="博彩公司名称")

    # 基础赔率字段
    home_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0, description="主胜赔率")
    draw: Optional[Decimal] = Field(None, ge=1.0, le=1000.0, description="平局赔率")
    away_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0, description="客胜赔率")

    # 扩展赔率字段
    over_under: Optional[Decimal] = Field(None, ge=1.0, le=1000.0, description="大小球赔率")
    asian_handicap: Optional[Decimal] = Field(None, description="亚洲让分盘")

    # 实时性字段
    live_odds: bool = Field(False, description="是否为实时赔率")
    confidence_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, description="赔率可信度 (0-1)")

    # 市场深度
    total_volume: Optional[Decimal] = Field(None, ge=0, description="总交易量")
    home_win_volume: Optional[Decimal] = Field(None, ge=0, description="主胜交易量")
    draw_volume: Optional[Decimal] = Field(None, ge=0, description="平局交易量")
    away_win_volume: Optional[Decimal] = Field(None, ge=0, description="客胜交易量")

    # 价格变动追踪
    volatility_index: Optional[Decimal] = Field(None, ge=0.0, description="波动指数")

    # 数据质量指标
    data_quality_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0, description="数据质量分数")
    source_reliability: Optional[str] = Field(None, max_length=20, description="数据源可靠性")

    @field_validator('bookmaker')
    @classmethod
    def validate_bookmaker(cls, v):
        """验证博彩公司名称"""
        allowed_bookmakers = [
            'Bet365', 'William Hill', 'Betfair', 'Paddy Power',
            'Ladbrokes', 'Coral', 'Betway', '888sport',
            'Unibet', 'Sky Bet', 'Betfred', 'Pinnacle'
        ]
        # 允许自定义，但给出警告
        if v and v not in allowed_bookmakers:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"未知博彩公司: {v}，请确认数据来源可靠性")
        return v

    @field_validator('home_win', 'draw', 'away_win')
    @classmethod
    def validate_odds_range(cls, v):
        """验证赔率范围合理性"""
        if v is not None:
            if v <= 1.0:
                raise ValueError('赔率不能小于等于1.0')
            if v > 1000.0:
                raise ValueError('赔率不能大于1000.0')
        return v


class OddsCreate(OddsBase):
    """创建赔率数据模式"""

    last_updated: datetime = Field(..., description="最后更新时间")
    bet_type: Optional[str] = Field(None, max_length=50, description="投注类型")
    odds_value: Optional[Decimal] = Field(None, ge=1.0, le=1000.0, description="原始赔率值")

    @field_validator('last_updated')
    @classmethod
    def validate_last_updated_not_future(cls, v):
        """验证最后更新时间不能是未来"""
        if v > datetime.utcnow():
            raise ValueError('最后更新时间不能是未来时间')
        return v


class OddsUpdate(BaseModel):
    """更新赔率数据模式"""

    home_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    draw: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    away_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    over_under: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    asian_handicap: Optional[Decimal] = Field(None)
    live_odds: Optional[bool] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    total_volume: Optional[Decimal] = Field(None, ge=0)
    home_win_volume: Optional[Decimal] = Field(None, ge=0)
    draw_volume: Optional[Decimal] = Field(None, ge=0)
    away_win_volume: Optional[Decimal] = Field(None, ge=0)
    volatility_index: Optional[Decimal] = Field(None, ge=0.0)
    data_quality_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    source_reliability: Optional[str] = Field(None, max_length=20)
    last_updated: Optional[datetime] = None


class OddsResponse(OddsBase):
    """赔率响应模式"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True
    price_movement: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class OddsHistoryBase(BaseModel):
    """赔率历史基础模式"""

    odds_id: int = Field(..., description="关联的赔率ID")

    # 基础赔率历史
    old_home_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    new_home_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    old_draw: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    new_draw: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    old_away_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    new_away_win: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)

    # 扩展赔率历史
    old_over_under: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    new_over_under: Optional[Decimal] = Field(None, ge=1.0, le=1000.0)
    old_asian_handicap: Optional[Decimal] = Field(None)
    new_asian_handicap: Optional[Decimal] = Field(None)

    # 历史记录字段
    old_total_volume: Optional[Decimal] = Field(None, ge=0)
    new_total_volume: Optional[Decimal] = Field(None, ge=0)
    old_confidence_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    new_confidence_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0)

    # 变动信息
    change_time: datetime = Field(..., description="变动时间")
    change_reason: Optional[str] = Field(None, max_length=500, description="变动原因")
    price_impact: Optional[str] = Field(None, description="价格影响程度")


class OddsHistoryCreate(OddsHistoryBase):
    """创建赔率历史记录模式"""
    pass


class OddsHistoryResponse(OddsHistoryBase):
    """赔率历史响应模式"""

    id: int

    class Config:
        from_attributes = True


class MarketAnalysisBase(BaseModel):
    """市场分析基础模式"""

    match_id: int = Field(..., description="比赛ID")
    bet_type: str = Field(..., min_length=1, max_length=50, description="投注类型")
    average_odds: Decimal = Field(..., ge=1.0, le=1000.0, description="平均赔率")
    min_odds: Decimal = Field(..., ge=1.0, le=1000.0, description="最低赔率")
    max_odds: Decimal = Field(..., ge=1.0, le=1000.0, description="最高赔率")
    bookmaker_count: int = Field(default=0, ge=0, description="博彩公司数量")
    market_confidence: Decimal = Field(default=0.5, ge=0.0, le=1.0, description="市场信心度")

    # 新增市场分析字段
    market_efficiency: Optional[Decimal] = Field(None, ge=0.0, le=1.0, description="市场效率")
    implied_probabilities: Optional[dict[str, Decimal]] = Field(None, description="隐含概率")
    market_bias: Optional[str] = Field(None, max_length=20, description="市场偏差")
    arbitrage_opportunity: bool = Field(default=False, description="套利机会")
    total_volume_analyzed: Optional[Decimal] = Field(None, ge=0, description="分析的总交易量")
    volatility_analysis: Optional[dict[str, Any]] = Field(None, description="波动性分析")

    @field_validator('bet_type')
    @classmethod
    def validate_bet_type(cls, v):
        """验证投注类型"""
        allowed_types = [
            'home_win', 'draw', 'away_win', 'over_2_5', 'under_2_5',
            'btts_yes', 'btts_no', 'asian_handicap', 'correct_score',
            'first_goalscorer', 'anytime_goalscorer'
        ]
        if v not in allowed_types:
            raise ValueError(f'投注类型必须是以下之一: {allowed_types}')
        return v


class MarketAnalysisCreate(MarketAnalysisBase):
    """创建市场分析模式"""

    analysis_time: datetime = Field(default_factory=datetime.utcnow, description="分析时间")


class MarketAnalysisResponse(MarketAnalysisBase):
    """市场分析响应模式"""

    id: int
    analysis_time: datetime

    class Config:
        from_attributes = True


# 导出所有模式
__all__ = [
    'MatchBase',
    'MatchCreate',
    'MatchUpdate',
    'MatchResponse',
    'OddsBase',
    'OddsCreate',
    'OddsUpdate',
    'OddsResponse',
    'OddsHistoryBase',
    'OddsHistoryCreate',
    'OddsHistoryResponse',
    'MarketAnalysisBase',
    'MarketAnalysisCreate',
    'MarketAnalysisResponse'
]
