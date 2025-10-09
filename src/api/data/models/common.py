"""
通用数据模型
Common Data Models
"""




class TeamInfo(BaseModel):
    """球队信息模型"""

    id: int
    name: str
    country: Optional[str]
    founded_year: Optional[int]
    stadium: Optional[str]
    logo_url: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class LeagueInfo(BaseModel):
    """联赛信息模型"""

    id: int
    name: str
    country: str
    season: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class MatchInfo(BaseModel):
    """比赛信息模型"""

    id: int
    home_team: TeamInfo
    away_team: TeamInfo
    league: LeagueInfo
    match_time: datetime
    match_status: str
    venue: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    home_half_score: Optional[int]
    away_half_score: Optional[int]

    class Config:
        from_attributes = True


class OddsInfo(BaseModel):
    """赔率信息模型"""

    match_id: int
    bookmaker: str
    market_type: str


    home_win_odds: Optional[float]
    draw_odds: Optional[float]
    away_win_odds: Optional[float]
    over_line: Optional[float]
    over_odds: Optional[float]
    under_odds: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True