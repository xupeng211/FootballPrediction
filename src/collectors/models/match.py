"""
Match model for data collection
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Match:
    """Match data model"""

    id: int
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    match_date: Optional[datetime] = None
    league: str = ""
    status: str = "scheduled"
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "match_date": self.match_date.isoformat() if self.match_date else None,
            "league": self.league,
            "status": self.status,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Match":
        """Create from dictionary"""
        match_date = data.get("match_date")
        if isinstance(match_date, str):
            from datetime import datetime
            match_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            home_team=data["home_team"],
            away_team=data["away_team"],
            home_score=data.get("home_score"),
            away_score=data.get("away_score"),
            match_date=match_date,
            league=data.get("league", ""),
            status=data.get("status", "scheduled"),
            metadata=data.get("metadata", {})
        )