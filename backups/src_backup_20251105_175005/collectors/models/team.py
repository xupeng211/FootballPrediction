"""
Team model for data collection
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Team:
    """类文档字符串"""

    pass  # 添加pass语句
    """Team data model"""

    id: int
    name: str
    short_name: str | None = None
    country: str = ""
    league: str = ""
    founded_year: int | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """函数文档字符串"""
        # 添加pass语句
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "country": self.country,
            "league": self.league,
            "founded_year": self.founded_year,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Team":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            short_name=data.get("short_name"),
            country=data.get("country", ""),
            league=data.get("league", ""),
            founded_year=data.get("founded_year"),
            metadata=data.get("metadata", {}),
        )
