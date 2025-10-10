"""
League data models
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LeagueInfo(BaseModel):
    """League information model."""

    id: int
    name: str
    country: str
    season: Optional[str] = None

    class Config:
        from_attributes = True
