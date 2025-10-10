"""
Team data models
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TeamInfo(BaseModel):
    """Team information model."""

    id: int
    name: str
    league: Optional[str] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    venue: Optional[str] = None
