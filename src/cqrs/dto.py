"""
数据传输对象
Data Transfer Objects

定义CQRS模式中使用的DTO。
Defines DTOs used in CQRS pattern.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


@dataclass
class PredictionDTO:
    """预测DTO"""

    id: int
    match_id: int
    user_id: int
    predicted_home: int
    predicted_away: int
    confidence: float
    strategy_used: Optional[str] = None
    points_earned: Optional[int] = None
    accuracy_score: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "match_id": self.match_id,
            "user_id": self.user_id,
            "predicted_home": self.predicted_home,
            "predicted_away": self.predicted_away,
            "confidence": float(self.confidence) if self.confidence else None,
            "strategy_used": self.strategy_used,
            "points_earned": self.points_earned,
            "accuracy_score": float(self.accuracy_score)
            if self.accuracy_score
            else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class UserDTO:
    """用户DTO"""

    id: int
    username: str
    email: str
    is_active: bool
    total_points: int
    prediction_count: int
    success_rate: float
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "total_points": self.total_points,
            "prediction_count": self.prediction_count,
            "success_rate": float(self.success_rate),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


@dataclass
class MatchDTO:
    """比赛DTO"""

    id: int
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    match_date: datetime
    status: str
    competition: Optional[str] = None
    venue: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "match_date": self.match_date.isoformat(),
            "status": self.status,
            "competition": self.competition,
            "venue": self.venue,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class PredictionStatsDTO:
    """预测统计DTO"""

    user_id: int
    total_predictions: int
    successful_predictions: int
    success_rate: float
    total_points: int
    average_confidence: float
    strategy_breakdown: Dict[str, Dict[str, Any]]
    recent_performance: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "total_predictions": self.total_predictions,
            "successful_predictions": self.successful_predictions,
            "success_rate": float(self.success_rate),
            "total_points": self.total_points,
            "average_confidence": float(self.average_confidence),
            "strategy_breakdown": self.strategy_breakdown,
            "recent_performance": self.recent_performance,
        }


@dataclass
class MatchStatsDTO:
    """比赛统计DTO"""

    match_id: int
    total_predictions: int
    prediction_distribution: Dict[str, int]
    average_confidence: float
    home_win_percentage: float
    draw_percentage: float
    away_win_percentage: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "match_id": self.match_id,
            "total_predictions": self.total_predictions,
            "prediction_distribution": self.prediction_distribution,
            "average_confidence": float(self.average_confidence),
            "home_win_percentage": float(self.home_win_percentage),
            "draw_percentage": float(self.draw_percentage),
            "away_win_percentage": float(self.away_win_percentage),
        }


@dataclass
class CommandResult:
    """命令执行结果"""

    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

    @classmethod
    def success_result(
        cls, data: Any = None, message: str = "操作成功"
    ) -> "CommandResult":
        """创建成功结果"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def failure_result(
        cls, errors: List[str], message: str = "操作失败"
    ) -> "CommandResult":
        """创建失败结果"""
        return cls(success=False, message=message, errors=errors)
