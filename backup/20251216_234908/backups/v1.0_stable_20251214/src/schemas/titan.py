"""
Titan007 (球探网) API 数据模型

定义 Titan API 返回的原始 JSON 数据结构和枚举类型。
"""

from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CompanyID(int, Enum):
    """博彩公司ID枚举"""

    WILLIAM_HILL = 3  # 威廉希尔
    BET365 = 8  # Bet365
    LIVE = 14  # Live
    PINNACLE = 17  # Pinnacle（皇冠）


class TitanTeamInfo(BaseModel):
    """Titan API 球队基本信息"""

    name: str = Field(description="球队名称")
    tid: int = Field(description="Titan 球队ID")


class TitanMatchInfo(BaseModel):
    """Titan API 比赛基本信息（用于ID对齐）"""

    match_id: str = Field(alias="matchid", description="Titan 比赛ID")
    league_id: str = Field(alias="leagueid", description="联赛ID")
    league_name: str = Field(alias="leaguename", description="联赛名称")
    home_team: TitanTeamInfo = Field(alias="hometeam", description="主队信息")
    away_team: TitanTeamInfo = Field(alias="awayteam", description="客队信息")
    match_date: datetime = Field(alias="matchdate", description="比赛日期")
    match_time: Optional[str] = Field(
        alias="matchtime", default=None, description="比赛时间"
    )

    @field_validator("match_date", mode="before")
    @classmethod
    def parse_match_date(cls, v: str) -> datetime:
        """解析日期字符串，格式: YYYY-MM-DD"""
        if isinstance(v, datetime):
            return v
        return datetime.strptime(v, "%Y-%m-%d")


class EuroOddsRecord(BaseModel):
    """欧赔单条记录"""

    company_id: CompanyID = Field(alias="companyid")
    company_name: str = Field(alias="companyname")
    home_win: float = Field(alias="homeodds", ge=1.0)
    draw: float = Field(alias="drawodds", ge=1.0)
    away_win: float = Field(alias="awayodds", ge=1.0)
    kelly_home: Optional[float] = Field(alias="kelly_home", default=None)
    kelly_draw: Optional[float] = Field(alias="kelly_draw", default=None)
    kelly_away: Optional[float] = Field(alias="kelly_away", default=None)
    last_updated: datetime = Field(alias="updatetime")


class AsianHandicapRecord(BaseModel):
    """亚盘单条记录"""

    company_id: CompanyID = Field(alias="companyid")
    company_name: str = Field(alias="companyname")
    upper_odds: float = Field(alias="upperodds", ge=0.0)
    handicap: str = Field(alias="handicap")  # e.g., "0.25", "0.5"
    lower_odds: float = Field(alias="lowerodds", ge=0.0)
    last_updated: datetime = Field(alias="updatetime")


class OverUnderRecord(BaseModel):
    """大小球单条记录"""

    company_id: CompanyID = Field(alias="companyid")
    company_name: str = Field(alias="companyname")
    over_odds: float = Field(alias="overodds", ge=0.0)
    handicap: str = Field(alias="handicap")  # e.g., "2.5", "3.0"
    under_odds: float = Field(alias="underodds", ge=0.0)
    last_updated: datetime = Field(alias="updatetime")


class EuroOddsResponse(BaseModel):
    """欧赔API响应"""

    match_id: str = Field(alias="matchid")
    success: bool
    data: List[EuroOddsRecord]
    message: Optional[str] = None


class AsianOddsResponse(BaseModel):
    """亚盘API响应"""

    match_id: str = Field(alias="matchid")
    success: bool
    data: List[AsianHandicapRecord]
    message: Optional[str] = None


class OverUnderResponse(BaseModel):
    """大小球API响应"""

    match_id: str = Field(alias="matchid")
    success: bool
    data: List[OverUnderRecord]
    message: Optional[str] = None


# 模糊匹配相关 Schema
class FotMobMatchInfo(BaseModel):
    """FotMob 比赛基本信息（用于ID对齐）"""

    fotmob_id: str = Field(description="FotMob 比赛ID")
    home_team: str = Field(description="主队名称")
    away_team: str = Field(description="客队名称")
    match_date: datetime = Field(description="比赛日期")
    competition_name: Optional[str] = Field(default=None, description="联赛名称")


class MatchAlignmentResult(BaseModel):
    """ID对齐结果"""

    fotmob_id: str
    titan_id: str
    home_team_fotmob: str
    home_team_titan: str
    away_team_fotmob: str
    away_team_titan: str
    confidence_score: float = Field(
        ge=0.0, le=100.0, description="模糊匹配置信度 (0-100)"
    )
    match_date: datetime
    is_aligned: bool = Field(description="是否成功对齐")

    class Config:
        json_schema_extra = {
            "example": {
                "fotmob_id": "4193497",
                "titan_id": "2971465",
                "home_team_fotmob": "Man City",
                "home_team_titan": "Manchester City",
                "away_team_fotmob": "Liverpool",
                "away_team_titan": "Liverpool",
                "confidence_score": 95.0,
                "match_date": "2024-01-01",
                "is_aligned": True,
            }
        }
