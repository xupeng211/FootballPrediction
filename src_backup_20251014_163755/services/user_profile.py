"""
足球预测系统用户画像服务模块

提供用户画像生成和管理功能。
"""

from typing import List
from datetime import datetime
from .base_unified import SimpleService


# 简化的UserProfile类定义
class UserProfile:
    def __init__(
        self, user_id: str, display_name: str, email: str, preferences: Dict[str, Any]
    ):
        self.user_id = user_id
        self.display_name = display_name
        self.email = email
        self.preferences = preferences

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "email": self.email,
            "preferences": self.preferences,
        }


# 简化的User类定义
class User:
    def __init__(self, id: str, username: str) -> None:
        self.id = id
        self.username = username


class UserProfileService(SimpleService):
    """用户画像服务"""

    def __init__(self) -> None:
        super().__init__("UserProfileService")
        self._user_profiles: Dict[str, UserProfile] = {}}

    async def _on_initialize(self) -> bool:
        """初始化服务"""
        self.logger.info(f"正在初始化 {self.name}")
        # 加载用户数据、模型等
        # 在实际生产环境中，这里会从数据库加载用户数据
        try:
            # 这里可以加载用户数据
            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"初始化失败: {e}")
            return False

    async def _on_shutdown(self) -> None:
        """关闭服务"""
        self.logger.info(f"正在关闭 {self.name}")
        self._user_profiles.clear()

    async def _get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "description": "User profile service for managing user preferences and behavior",
            "version": "1.0.0",
            "profiles_count": len(self._user_profiles),
        }

    async def generate_profile(self, user: User) -> UserProfile:
        """生成用户画像"""
        self.logger.info(f"正在生成用户画像: {user.id}")
        # 实现用户画像生成逻辑
        # 基于用户行为和偏好生成画像
        interests = self._analyze_user_interests(user)
        behavior_patterns = self._analyze_behavior_patterns(user)
        content_preferences = self._analyze_content_preferences(user)
        profile = UserProfile(
            user_id=user.id,
            display_name=getattr(user, "display_name", user.username),
            email=(
                getattr(user.profile, "email", "") if hasattr(user, "profile") else ""
            ),
            preferences={
                "interests": interests,
                "content_type": content_preferences.get(str("preferred_type"), "text"),
                "language": content_preferences.get(str("language"), "zh"),
                "behavior_patterns": behavior_patterns,
                "notification_settings": self._get_notification_settings(user),
                "created_at": datetime.now(),
            },
        )
        self._user_profiles[user.id] = profile
        return profile

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        return self._user_profiles.get(user_id)

    async def update_profile(
        self, user_id: str, updates: Dict[str, Any]
    ) -> Optional[UserProfile]:
        """更新用户画像"""
        profile = await self.get_profile(user_id)
        if not profile:
            return None
        # 更新画像数据
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
            else:
                # Assume other keys are part of preferences
                profile.preferences[key] = value
        return profile

    def _analyze_user_interests(self, user: User) -> List[str]:
        """分析用户兴趣"""
        # 在实际系统中，这里会基于用户行为分析兴趣
        # 现在提供默认的兴趣列表
        default_interests = ["足球", "体育", "预测"]
        # 可以根据用户属性调整兴趣
        if hasattr(user, "profile") and hasattr(user.profile, "favorite_teams"):
            if user.profile.favorite_teams and isinstance(
                user.profile.favorite_teams, (list, tuple)
            ):
                default_interests.extend(user.profile.favorite_teams)
        return list(set(default_interests))  # 去重

    def _analyze_behavior_patterns(self, user: User) -> Dict[str, Any]:
        """分析用户行为模式"""
        # 在实际系统中，这里会基于用户日志分析行为模式
        return {
            "active_hours": [9, 10, 11, 14, 15, 16, 20, 21],  # 默认活跃时间
            "login_frequency": "daily",
            "content_consumption_rate": "medium",
            "prediction_activity": "regular",
        }

    def _analyze_content_preferences(self, user: User) -> Dict[str, Any]:
        """分析内容偏好"""
        return {
            "preferred_type": "text",
            "language": "zh",
            "content_length": "medium",
            "preferred_leagues": ["PL", "PD", "SA"],  # 英超、西甲、意甲
        }

    def _get_notification_settings(self, user: User) -> Dict[str, Any]:
        """获取通知设置"""
        return {
            "email_notifications": True,
            "push_notifications": True,
            "match_reminders": True,
            "prediction_updates": True,
        }

    def create_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户画像 - 同步版本用于测试"""
        if not user_data or not user_data.get("user_id"):
            return {"status": "error", "message": "Empty or invalid user data"}

        user_id = user_data["user_id"]
        interests = user_data.get(str("interests"), ["足球", "体育"])
        preferences = {
            "interests": interests,
            "language": user_data.get(str("language"), "zh"),
            "content_type": user_data.get(str("content_type"), "text"),
            "behavior_patterns": {"active_hours": [9, 10, 11, 14, 15, 16]},
        }
        profile = UserProfile(
            user_id=user_id,
            display_name=user_data.get(str("name"), "Anonymous"),
            email=user_data.get(str("email"), ""),
            preferences={
                **preferences,
                "created_at": datetime.now(),
            },
        )
        self._user_profiles[user_id] = profile
        return {"status": "created", "profile": profile.to_dict()}

    def delete_profile(self, user_id: str) -> Dict[str, Any]:
        """删除用户画像"""
        if user_id in self._user_profiles:
            del self._user_profiles[user_id]
            return {"status": "deleted"}
        return {"status": "not_found"}

    @property
    def _profiles(self) -> Dict[str, Any]:
        """兼容测试代码的属性"""
        # Convert UserProfile objects to Dict[str, Any] for test compatibility
        return {
            user_id: profile.to_dict() if hasattr(profile, "to_dict") else profile
            for user_id, profile in self._user_profiles.items()
        }
