"""
数据服务模块 - 为API测试提供Mock接口
Data Services Module - Mock Interface for API Tests
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class MatchService:
    """比赛服务 - 为测试提供Mock接口"""

    @staticmethod
    def get_matches(limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """获取比赛列表"""
        return {
            "matches": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_match_by_id(match_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取比赛"""
        return None


@dataclass
class TeamService:
    """球队服务 - 为测试提供Mock接口"""

    @staticmethod
    def get_teams(limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """获取球队列表"""
        return {
            "teams": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_team_by_id(team_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取球队"""
        return None


@dataclass
class LeagueService:
    """联赛服务 - 为测试提供Mock接口"""

    @staticmethod
    def get_leagues(limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """获取联赛列表"""
        return {
            "leagues": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }


@dataclass
class OddsService:
    """赔率服务 - 为测试提供Mock接口"""

    @staticmethod
    def get_odds(match_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取赔率数据"""
        return []


@dataclass
class MonitoringService:
    """监控服务 - 为测试提供Mock接口"""

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """获取系统统计"""
        return {
            "system": {
                "cpu_percent": 25.5,
                "memory_percent": 45.2,
                "uptime": "24h 30m",
                "active_connections": 150,
            },
            "api": {
                "requests_per_minute": 120,
                "average_response_time": 85.5,
                "error_rate": 0.02,
            }
        }


@dataclass
class VersionService:
    """版本服务 - 为测试提供Mock接口"""

    @staticmethod
    def get_version() -> Dict[str, Any]:
        """获取API版本信息"""
        return {
            "version": "2.0.0",
            "build": "20251115-0930",
            "api_version": "v1",
            "status": "stable",
        }


@dataclass
class QueueService:
    """队列服务 - 为测试提供Mock接口"""

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "status": "active",
            "queues": {
                "predictions": {
                    "pending": 5,
                    "processing": 2,
                    "completed": 150,
                    "failed": 1,
                },
                "notifications": {
                    "pending": 0,
                    "processing": 0,
                    "completed": 75,
                    "failed": 0,
                }
            },
            "workers": {
                "active": 3,
                "idle": 2,
                "total": 5,
            }
        }