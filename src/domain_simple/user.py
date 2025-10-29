"""
用户领域模型
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class UserRole(Enum):
    """用户角色"""

    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    ANALYST = "analyst"


class UserPreferences:
    """用户偏好设置"""

    def __init__(self):
        self.favorite_teams: List[int] = []
        self.favorite_leagues: List[int] = []
        self.notification_enabled = True
        self.email_notifications = True
        self.language = "zh-CN"
        self.timezone = "UTC+8"
        self.odds_format = "decimal"  # decimal, fractional, american

    def add_favorite_team(self, team_id: int) -> None:
        """添加喜欢的球队"""
        if team_id not in self.favorite_teams:
            self.favorite_teams.append(team_id)

    def remove_favorite_team(self, team_id: int) -> None:
        """移除喜欢的球队"""
        if team_id in self.favorite_teams:
            self.favorite_teams.remove(team_id)

    def add_favorite_league(self, league_id: int) -> None:
        """添加喜欢的联赛"""
        if league_id not in self.favorite_leagues:
            self.favorite_leagues.append(league_id)

    def remove_favorite_league(self, league_id: int) -> None:
        """移除喜欢的联赛"""
        if league_id in self.favorite_leagues:
            self.favorite_leagues.remove(league_id)


class UserStatistics:
    """用户统计数据"""

    def __init__(self):
        self.total_predictions = 0
        self.correct_predictions = 0
        self.total_profit_loss = 0.0
        self.best_streak = 0
        self.current_streak = 0
        self.average_odds = 0.0
        self.average_confidence = 0.0

    def update_prediction(
        self,
        is_correct: bool,
        profit_loss: float,
        odds: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> None:
        """更新预测统计"""
        self.total_predictions += 1

        if is_correct:
            self.correct_predictions += 1
            self.current_streak += 1
            if self.current_streak > self.best_streak:
                self.best_streak = self.current_streak
        else:
            self.current_streak = 0

        self.total_profit_loss += profit_loss

        # 更新平均值
        if odds:
            self.average_odds = (
                (self.average_odds * (self.total_predictions - 1)) + odds
            ) / self.total_predictions
        if confidence:
            self.average_confidence = (
                (self.average_confidence * (self.total_predictions - 1)) + confidence
            ) / self.total_predictions

    def get_accuracy_rate(self) -> float:
        """获取准确率"""
        if self.total_predictions == 0:
            return 0.0
        return (self.correct_predictions / self.total_predictions) * 100

    def get_roi(self) -> float:
        """获取投资回报率（假设每注1单位）"""
        if self.total_predictions == 0:
            return 0.0
        return (self.total_profit_loss / self.total_predictions) * 100


class User:
    """用户领域模型"""

    def __init__(
        self,
        id: Optional[int] = None,
        username: str = "",
        email: str = "",
        role: UserRole = UserRole.USER,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

        # 个人资料
        self.first_name = ""
        self.last_name = ""
        self.avatar_url = ""
        self.bio = ""

        # 状态
        self.is_active = True
        self.is_verified = False
        self.last_login: Optional[datetime] = None

        # 偏好和统计
        self.preferences = UserPreferences()
        self.statistics = UserStatistics()

        # 等级和成就
        self.level = 1
        self.experience_points = 0
        self.achievements: List[str] = []

        # 时间戳
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def get_full_name(self) -> str:
        """获取全名"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def is_premium(self) -> bool:
        """是否为高级用户"""
        return self.role in [UserRole.PREMIUM, UserRole.ADMIN, UserRole.ANALYST]

    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role == UserRole.ADMIN

    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login = datetime.now()
        self.updated_at = datetime.now()

    def add_experience(self, points: int) -> None:
        """添加经验值"""
        self.experience_points += points
        self._update_level()

    def _update_level(self) -> None:
        """更新等级（简单的等级计算）"""
        # 每100经验值升一级
        new_level = self.experience_points // 100 + 1
        if new_level > self.level:
            self.level = new_level

    def add_achievement(self, achievement: str) -> None:
        """添加成就"""
        if achievement not in self.achievements:
            self.achievements.append(achievement)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_premium": self.is_premium(),
            "is_admin": self.is_admin(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "preferences": {
                "favorite_teams": self.preferences.favorite_teams,
                "favorite_leagues": self.preferences.favorite_leagues,
                "notification_enabled": self.preferences.notification_enabled,
                "email_notifications": self.preferences.email_notifications,
                "language": self.preferences.language,
                "timezone": self.preferences.timezone,
                "odds_format": self.preferences.odds_format,
            },
            "statistics": {
                "total_predictions": self.statistics.total_predictions,
                "correct_predictions": self.statistics.correct_predictions,
                "accuracy_rate": self.statistics.get_accuracy_rate(),
                "total_profit_loss": self.statistics.total_profit_loss,
                "roi": self.statistics.get_roi(),
                "best_streak": self.statistics.best_streak,
                "current_streak": self.statistics.current_streak,
                "average_odds": self.statistics.average_odds,
                "average_confidence": self.statistics.average_confidence,
            },
            "level": self.level,
            "experience_points": self.experience_points,
            "achievements": self.achievements,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """从字典创建实例"""
        _user = cls(
            id=data.get("id"),
            username=data.get("username", ""),
            email=data.get("email", ""),
            role=UserRole(data.get("role", "user")),
        )

        # 设置个人资料
        _user.first_name = data.get("first_name", "")
        _user.last_name = data.get("last_name", "")
        _user.avatar_url = data.get("avatar_url", "")
        _user.bio = data.get("bio", "")

        # 设置状态
        _user.is_active = data.get("is_active", True)
        _user.is_verified = data.get("is_verified", False)

        # 设置等级和成就
        _user.level = data.get("level", 1)
        _user.experience_points = data.get("experience_points", 0)
        _user.achievements = data.get("achievements", [])

        # 设置偏好
        if "preferences" in data:
            pref = data["preferences"]
            _user.preferences.favorite_teams = pref.get("favorite_teams", [])
            _user.preferences.favorite_leagues = pref.get("favorite_leagues", [])
            _user.preferences.notification_enabled = pref.get("notification_enabled", True)
            _user.preferences.email_notifications = pref.get("email_notifications", True)
            _user.preferences.language = pref.get("language", "zh-CN")
            _user.preferences.timezone = pref.get("timezone", "UTC+8")
            _user.preferences.odds_format = pref.get("odds_format", "decimal")

        # 设置时间戳
        if data.get("created_at"):
            _user.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            _user.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_login"):
            _user.last_login = datetime.fromisoformat(data["last_login"])

        return _user

    def __str__(self) -> str:
        return f"User({self.username})"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role.value})>"


class UserProfile:
    """用户档案（扩展的用户信息）"""

    def __init__(self, user: User):
        self._user = user
        self.prediction_history: List[Dict[str, Any]] = []
        self.following: List[int] = []  # 关注的用户ID列表
        self.followers: List[int] = []  # 粉丝列表
        self.reputation_score = 0.0

    def follow_user(self, user_id: int) -> None:
        """关注用户"""
        if user_id not in self.following:
            self.following.append(user_id)

    def unfollow_user(self, user_id: int) -> None:
        """取消关注"""
        if user_id in self.following:
            self.following.remove(user_id)

    def add_follower(self, user_id: int) -> None:
        """添加粉丝"""
        if user_id not in self.followers:
            self.followers.append(user_id)

    def remove_follower(self, user_id: int) -> None:
        """移除粉丝"""
        if user_id in self.followers:
            self.followers.remove(user_id)

    def update_reputation(self, score: float) -> None:
        """更新声誉分数"""
        self.reputation_score = max(0, min(100, score))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user": self._user.to_dict(),
            "following_count": len(self.following),
            "followers_count": len(self.followers),
            "reputation_score": self.reputation_score,
        }
