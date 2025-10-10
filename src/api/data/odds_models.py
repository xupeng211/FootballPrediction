"""
Odds data models
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class OddsInfo(BaseModel):
    """Odds information model."""

    id: int
    match_id: int
    home_win: Optional[float] = None
    draw: Optional[float] = None
    away_win: Optional[float] = None
    source: Optional[str] = None
    updated_at: Optional[datetime] = None
