"""
Match data models
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MatchInfo(BaseModel):
    """Match information model."""

    id: int
    home_team: str
    away_team: str
    league: str
    date: datetime
    status: Optional[str] = None
    score: Optional[str] = None
    venue: Optional[str] = None
