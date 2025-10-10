"""
用户领域模型

封装用户相关的业务逻辑和规则。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .prediction import Prediction, PredictionType, PredictionStatus, PredictionMetrics


class UserStatus(Enum):
    """用户状态枚举"""

    ACTIVE = "active"  # 活跃
    INACTIVE = "inactive"  # 不活跃
    SUSPENDED = "suspended"  # 暂停
    BANNED = "banned"  # 禁用


class UserRole(Enum):
    """用户角色枚举"""

    USER = "user"  # 普通用户
    PREMIUM = "premium"  # 高级用户
    ADMIN = "admin"  # 管理员
    MODERATOR = "moderator"  # 版主


class UserLevel(Enum):
    """用户等级枚举"""

    BEGINNER = (1, "新手", 0, 99)
    BRONZE = (2, "青铜", 100, 299)
    SILVER = (3, "白银", 300, 699)
    GOLD = (4, "黄金", 700, 1499)
    PLATINUM = (5, "铂金", 1500, 2999)
    DIAMOND = (6, "钻石", 3000, 9999)
    MASTER = (7, "大师", 10000, float("inf"))

    def __init__(self, level: int, title: str, min_points: int, max_points: float):
        self.level = level
        self.title = title
        self.min_points = min_points
        self.max_points = max_points

    @classmethod
    def from_points(cls, points: int) -> "UserLevel":
        """从积分获取等级"""
        for level in reversed(cls):
            if points >= level.min_points:
                return level
        return cls.BEGINNER


@dataclass
class UserPreferences:
    """用户偏好设置"""

    timezone: str = "UTC"
    language: str = "zh-CN"
    email_notifications: bool = True
    push_notifications: bool = True
    prediction_reminders: bool = True
    odds_format: str = "decimal"  # decimal, fractional, american
    preferred_leagues: List[int] = field(default_factory=list)
    favorite_teams: List[int] = field(default_factory=list)


@dataclass
class UserStatistics:
    """用户统计数据"""

    total_predictions: int = 0
    correct_predictions: int = 0
    incorrect_predictions: int = 0
    void_predictions: int = 0
    pending_predictions: int = 0
    accuracy_rate: float = 0.0
    best_streak: int = 0
    current_streak: int = 0
    points: int = 0
    rank: int = 0

    def update_accuracy(self):
        """更新准确率"""
        completed = self.correct_predictions + self.incorrect_predictions
        self.accuracy_rate = (
            self.correct_predictions / completed if completed > 0 else 0.0
        )

    def get_level(self) -> UserLevel:
        """获取用户等级"""
        return UserLevel.from_points(self.points)


@dataclass
class UserActivity:
    """用户活动记录"""

    activity_type: str
    description: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class UserProfile:
    """用户档案

    管理用户的个人信息、偏好设置和统计数据。
    """

    def __init__(
        self,
        id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
        location: Optional[str] = None,
        website: Optional[str] = None,
        birth_date: Optional[datetime] = None,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.display_name = display_name or username
        self.avatar_url = avatar_url
        self.bio = bio
        self.location = location
        self.website = website
        self.birth_date = birth_date

        # 偏好设置
        self.preferences = UserPreferences()

        # 统计数据
        self.statistics = UserStatistics()

        # 活动记录
        self.activities: List[UserActivity] = []

        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    # ==================== 预测管理 ====================

    def add_prediction(self, prediction: Prediction) -> bool:
        """添加预测记录"""
        # 更新统计
        self.statistics.total_predictions += 1
        self.statistics.pending_predictions += 1

        # 添加活动记录
        activity = UserActivity(
            activity_type="prediction",
            description=f"对比赛 {prediction.match.id} 进行预测",
            timestamp=datetime.now(),
            metadata={
                "prediction_id": prediction.id,
                "type": prediction.prediction_type.value,
                "result": prediction.predicted_result,
                "confidence": prediction.confidence,
            },
        )
        self.activities.append(activity)
        self.updated_at = datetime.now()

        return True

    def settle_prediction(self, prediction: Prediction) -> bool:
        """结算预测"""
        if prediction.status not in [
            PredictionStatus.CORRECT,
            PredictionStatus.INCORRECT,
            PredictionStatus.VOID,
        ]:
            return False

        # 更新统计
        self.statistics.pending_predictions = max(
            0, self.statistics.pending_predictions - 1
        )

        if prediction.status == PredictionStatus.CORRECT:
            self.statistics.correct_predictions += 1
            # 增加积分
            points_earned = self._calculate_points(prediction)
            self.statistics.points += points_earned
            self.statistics.current_streak += 1
            self.statistics.best_streak = max(
                self.statistics.best_streak, self.statistics.current_streak
            )

            # 记录活动
            activity = UserActivity(
                activity_type="prediction_correct",
                description=f"预测正确，获得 {points_earned} 积分",
                timestamp=datetime.now(),
                metadata={
                    "prediction_id": prediction.id,
                    "points_earned": points_earned,
                    "current_streak": self.statistics.current_streak,
                },
            )
        elif prediction.status == PredictionStatus.INCORRECT:
            self.statistics.incorrect_predictions += 1
            self.statistics.current_streak = 0

            # 记录活动
            activity = UserActivity(
                activity_type="prediction_incorrect",
                description="预测错误",
                timestamp=datetime.now(),
                metadata={"prediction_id": prediction.id, "current_streak": 0},
            )
        else:  # VOID
            self.statistics.void_predictions += 1
            activity = UserActivity(
                activity_type="prediction_void",
                description="预测无效",
                timestamp=datetime.now(),
                metadata={"prediction_id": prediction.id},
            )

        self.activities.append(activity)
        self.statistics.update_accuracy()
        self.updated_at = datetime.now()

        return True

    def _calculate_points(self, prediction: Prediction) -> int:
        """计算预测应得积分"""
        base_points = 10

        # 根据置信度调整
        confidence_bonus = int(prediction.confidence * 10)

        # 根据预测类型调整
        type_bonus = {
            PredictionType.MATCH_RESULT: 0,
            PredictionType.OVER_UNDER: 5,
            PredictionType.BOTH_TEAMS_SCORE: 5,
            PredictionType.CORRECT_SCORE: 20,
            PredictionType.FIRST_GOAL_SCORER: 15,
            PredictionType.HANDICAP: 10,
        }

        total_points = (
            base_points
            + confidence_bonus
            + type_bonus.get(prediction.prediction_type, 0)
        )

        # 如果是高价值投注，额外奖励
        if prediction.is_value_bet():
            total_points = int(total_points * 1.5)

        return total_points

    # ==================== 活动管理 ====================

    def get_recent_activities(self, limit: int = 10) -> List[UserActivity]:
        """获取最近活动"""
        return sorted(self.activities, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_prediction_trend(self, days: int = 30) -> Dict[str, int]:
        """获取预测趋势"""
        since = datetime.now() - timedelta(days=days)
        recent_activities = [
            a
            for a in self.activities
            if a.timestamp > since and a.activity_type.startswith("prediction")
        ]

        trend = {"correct": 0, "incorrect": 0, "void": 0, "total": 0}

        for activity in recent_activities:
            if activity.activity_type == "prediction_correct":
                trend["correct"] += 1
            elif activity.activity_type == "prediction_incorrect":
                trend["incorrect"] += 1
            elif activity.activity_type == "prediction_void":
                trend["void"] += 1
            trend["total"] += 1

        return trend

    def get_favorite_leagues(self, limit: int = 5) -> List[Tuple[int, int]]:
        """获取最常预测的联赛"""
        league_counts = {}
        for activity in self.activities:
            if activity.activity_type == "prediction":
                league_id = activity.metadata.get("league_id")
                if league_id:
                    league_counts[league_id] = league_counts.get(league_id, 0) + 1

        # 按次数排序
        sorted_leagues = sorted(league_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_leagues[:limit]

    # ==================== 偏好管理 ====================

    def update_preferences(self, **kwargs) -> bool:
        """更新偏好设置"""
        updated = False
        for key, value in kwargs.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)
                updated = True

        if updated:
            self.updated_at = datetime.now()

        return updated

    def add_favorite_team(self, team_id: int) -> bool:
        """添加喜欢的球队"""
        if team_id not in self.preferences.favorite_teams:
            self.preferences.favorite_teams.append(team_id)
            self.updated_at = datetime.now()
            return True
        return False

    def remove_favorite_team(self, team_id: int) -> bool:
        """移除喜欢的球队"""
        if team_id in self.preferences.favorite_teams:
            self.preferences.favorite_teams.remove(team_id)
            self.updated_at = datetime.now()
            return True
        return False

    # ==================== 成就系统 ====================

    def get_achievements(self) -> List[Dict[str, Any]]:
        """获取成就列表"""
        achievements = []

        # 准确率成就
        if self.statistics.accuracy_rate >= 0.5:
            achievements.append(
                {
                    "id": "accuracy_50",
                    "name": "预言家",
                    "description": "预测准确率达到50%",
                    "icon": "🔮",
                    "unlocked_at": None,  # 需要记录解锁时间
                }
            )

        # 连胜成就
        if self.statistics.best_streak >= 5:
            achievements.append(
                {
                    "id": "streak_5",
                    "name": "连胜达人",
                    "description": "连续预测正确5次",
                    "icon": "🔥",
                    "unlocked_at": None,
                }
            )

        # 预测数量成就
        if self.statistics.total_predictions >= 100:
            achievements.append(
                {
                    "id": "predictions_100",
                    "name": "活跃预测者",
                    "description": "完成100次预测",
                    "icon": "📊",
                    "unlocked_at": None,
                }
            )

        return achievements

    def get_next_level_progress(self) -> Dict[str, Any]:
        """获取下一等级进度"""
        current_level = self.statistics.get_level()
        next_level = (
            UserLevel(current_level.level + 1)
            if current_level.level < UserLevel.MASTER.level
            else UserLevel.MASTER
        )

        if current_level.level >= UserLevel.MASTER.level:
            return {
                "current_level": current_level,
                "next_level": None,
                "current_points": self.statistics.points,
                "points_needed": 0,
                "progress": 1.0,
            }

        points_needed = next_level.min_points - self.statistics.points
        level_range = next_level.min_points - current_level.min_points
        progress = 1.0 - (points_needed / level_range)

        return {
            "current_level": current_level,
            "next_level": next_level,
            "current_points": self.statistics.points,
            "points_needed": max(0, points_needed),
            "progress": max(0, min(1.0, progress)),
        }

    # ==================== 导出和序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "location": self.location,
            "website": self.website,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "preferences": {
                "timezone": self.preferences.timezone,
                "language": self.preferences.language,
                "email_notifications": self.preferences.email_notifications,
                "push_notifications": self.preferences.push_notifications,
                "prediction_reminders": self.preferences.prediction_reminders,
                "odds_format": self.preferences.odds_format,
                "preferred_leagues": self.preferences.preferred_leagues,
                "favorite_teams": self.preferences.favorite_teams,
            },
            "statistics": {
                "total_predictions": self.statistics.total_predictions,
                "correct_predictions": self.statistics.correct_predictions,
                "incorrect_predictions": self.statistics.incorrect_predictions,
                "void_predictions": self.statistics.void_predictions,
                "pending_predictions": self.statistics.pending_predictions,
                "accuracy_rate": self.statistics.accuracy_rate,
                "best_streak": self.statistics.best_streak,
                "current_streak": self.statistics.current_streak,
                "points": self.statistics.points,
                "rank": self.statistics.rank,
                "level": self.statistics.get_level().title,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """从字典创建实例"""
        profile = cls(
            id=data.get("id"),
            username=data.get("username"),
            email=data.get("email"),
            display_name=data.get("display_name"),
            avatar_url=data.get("avatar_url"),
            bio=data.get("bio"),
            location=data.get("location"),
            website=data.get("website"),
            birth_date=datetime.fromisoformat(data["birth_date"])
            if data.get("birth_date")
            else None,
        )

        # 恢复偏好设置
        if "preferences" in data:
            prefs = data["preferences"]
            profile.preferences.timezone = prefs.get("timezone", "UTC")
            profile.preferences.language = prefs.get("language", "zh-CN")
            profile.preferences.email_notifications = prefs.get(
                "email_notifications", True
            )
            profile.preferences.push_notifications = prefs.get(
                "push_notifications", True
            )
            profile.preferences.prediction_reminders = prefs.get(
                "prediction_reminders", True
            )
            profile.preferences.odds_format = prefs.get("odds_format", "decimal")
            profile.preferences.preferred_leagues = prefs.get("preferred_leagues", [])
            profile.preferences.favorite_teams = prefs.get("favorite_teams", [])

        # 恢复统计数据
        if "statistics" in data:
            stats = data["statistics"]
            profile.statistics.total_predictions = stats.get("total_predictions", 0)
            profile.statistics.correct_predictions = stats.get("correct_predictions", 0)
            profile.statistics.incorrect_predictions = stats.get(
                "incorrect_predictions", 0
            )
            profile.statistics.void_predictions = stats.get("void_predictions", 0)
            profile.statistics.pending_predictions = stats.get("pending_predictions", 0)
            profile.statistics.accuracy_rate = stats.get("accuracy_rate", 0.0)
            profile.statistics.best_streak = stats.get("best_streak", 0)
            profile.statistics.current_streak = stats.get("current_streak", 0)
            profile.statistics.points = stats.get("points", 0)
            profile.statistics.rank = stats.get("rank", 0)

        return profile

    # ==================== 比较和哈希 ====================

    def __eq__(self, other) -> bool:
        """比较两个用户档案是否相同"""
        if not isinstance(other, UserProfile):
            return False
        return (
            self.id == other.id
            if self.id and other.id
            else self.username == other.username
        )

    def __hash__(self) -> int:
        """生成哈希值"""
        if self.id:
            return hash(self.id)
        return hash(self.username or self.email)

    def __str__(self) -> str:
        """字符串表示"""
        return self.display_name or self.username or f"User {self.id}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"UserProfile(id={self.id}, username='{self.username}', "
            f"display_name='{self.display_name}', level={self.statistics.get_level().title})"
        )
