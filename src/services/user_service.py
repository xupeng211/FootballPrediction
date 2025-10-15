from typing import Any, Dict, List, Optional, Union

"""
用户服务层
"""

from datetime import datetime

from sqlalchemy.orm import Session

from src.database.models.user import User
from src.domain.user import UserCreate, UserUpdate
from src.security.auth import AuthManager, get_auth_manager


class UserService:
    """用户服务类"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth = get_auth_manager()

    def get(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()  # type: ignore

    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()  # type: ignore

    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()  # type: ignore

    def create(self, user_data: UserCreate) -> User:
        """创建新用户"""
        # 密码哈希
        hashed_password = self.auth.get_password_hash(user_data.password)

        # 创建用户对象
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=hashed_password,
            is_active=True,
            is_verified=False,
            roles="user",  # 默认角色
        )

        # 保存到数据库
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        db_user = self.get(user_id)
        if not db_user:
            return None

        # 更新字段
        user_data.Dict[str, Any](exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def update_password(self, user_id: int, new_password: str) -> bool:
        """更新用户密码"""
        db_user = self.get(user_id)
        if not db_user:
            return False

        # 更新密码哈希
        db_user.password_hash = self.auth.get_password_hash(new_password)
        self.db.commit()

        return True

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户登录"""
        # 通过用户名或邮箱查找用户
        user = self.get_by_username(username)
        if not user:
            user = self.get_by_email(username)

        if not user:
            return None

        # 验证密码
        if not self.auth.verify_password(password, user.password_hash):
            return None

        return user

    def update_last_login(self, user_id: int) -> bool:
        """更新最后登录时间"""
        db_user = self.get(user_id)
        if not db_user:
            return False

        db_user.touch_login()
        self.db.commit()

        return True

    def activate_user(self, user_id: int) -> bool:
        """激活用户"""
        db_user = self.get(user_id)
        if not db_user:
            return False

        db_user.is_verified = True
        db_user.is_active = True
        self.db.commit()

        return True

    def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        db_user = self.get(user_id)
        if not db_user:
            return False

        db_user.is_active = False
        self.db.commit()

        return True

    def add_role(self, user_id: int, role: str) -> bool:
        """添加用户角色"""
        db_user = self.get(user_id)
        if not db_user:
            return False

        db_user.add_role(role)
        self.db.commit()

        return True

    def remove_role(self, user_id: int, role: str) -> bool:
        """移除用户角色"""
        db_user = self.get(user_id)
        if not db_user:
            return False

        db_user.remove_role(role)
        self.db.commit()

        return True

    def delete(self, user_id: int) -> bool:
        """删除用户"""
        db_user = self.get(user_id)
        if not db_user:
            return False

        self.db.delete(db_user)
        self.db.commit()

        return True
