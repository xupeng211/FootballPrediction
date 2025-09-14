"""
足球预测系统用户画像服务模块

提供用户画像生成和管理功能。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from src.models import User, UserProfile

from .base import BaseService


class UserProfileService(BaseService):
    """用户画像服务"""

    def __init__(self) -> None:
        super().__init__("UserProfileService")
        self._user_profiles: Dict[str, UserProfile] = {}

    async def initialize(self) -> bool:
        """初始化服务"""
        self.logger.info(f"正在初始化 {self.name}")
        # TODO: 加载用户数据、模型等
        return True

    async def shutdown(self) -> None:
        """关闭服务"""
        self.logger.info(f"正在关闭 {self.name}")
        self._user_profiles.clear()

    async def generate_profile(self, user: User) -> UserProfile:
        """生成用户画像"""
        self.logger.info(f"正在生成用户画像: {user.id}")

        # TODO: 实现实际的用户画像生成逻辑

        profile = UserProfile(
            user_id=user.id,
            display_name=user.username,
            email=user.profile.email,  # Assuming email is in the user's profile
            preferences={
                "interests": ["足球", "体育", "预测"],
                "content_type": "text",
                "language": "zh",
                "behavior_patterns": {"active_hours": [9, 10, 11, 14, 15, 16]},
            },
            created_at=datetime.now(),
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

    def create_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户画像 - 同步版本用于测试"""
        if not user_data or not user_data.get("user_id"):
            return {"status": "error", "message": "Empty or invalid user data"}

        from src.models import UserProfile

        user_id = user_data["user_id"]
        profile = UserProfile(
            user_id=user_id,
            display_name=user_data.get("name", "Anonymous"),
            email=user_data.get("email", ""),
            preferences={"interests": ["足球", "体育"], "language": "zh"},
            created_at=datetime.now(),
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
        # Convert UserProfile objects to dict for test compatibility
        return {
            user_id: profile.to_dict() if hasattr(profile, "to_dict") else profile
            for user_id, profile in self._user_profiles.items()
        }
