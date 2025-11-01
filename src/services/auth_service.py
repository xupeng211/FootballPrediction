"""
用户认证服务

提供用户注册,登录,JWT令牌管理等认证相关功能
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User, UserRole
from src.repositories.auth_user import AuthUserRepository


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """类文档字符串"""

    pass  # 添加pass语句
    """用户认证服务"""

    def __init__(self, db: AsyncSession):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.db = db
        self.user_repo = AuthUserRepository(db)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(
        self, token: str, token_type: str = "access"
    ) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError:
            return None

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """注册新用户"""
        # 检查用户名是否已存在
        existing_user = await self.user_repo.get_by_username(username)
        if existing_user:
            raise ValueError("用户名已存在")

        # 检查邮箱是否已存在
        existing_email = await self.user_repo.get_by_email(email)
        if existing_email:
            raise ValueError("邮箱已存在")

        # 创建新用户
        password_hash = self.get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role=role.value,
            is_active=True,
            is_verified=False,  # 需要邮箱验证
        )

        # 设置默认偏好
        user.preferences = {
            "favorite_teams": [],
            "favorite_leagues": [],
            "notification_enabled": True,
            "email_notifications": True,
            "language": "zh-CN",
            "timezone": "UTC+8",
            "odds_format": "decimal",
        }

        # 设置默认统计
        user.statistics = {
            "total_predictions": 0,
            "correct_predictions": 0,
            "total_profit_loss": 0.0,
            "best_streak": 0,
            "current_streak": 0,
            "average_odds": 0.0,
            "average_confidence": 0.0,
        }

        created_user = await self.user_repo.create(user)
        return created_user

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户凭据"""
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        # 更新最后登录时间
        user.update_last_login()
        await self.user_repo.update(user)

        return user

    async def login_user(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """用户登录,返回令牌信息"""
        user = await self.authenticate_user(username, password)
        if not user:
            return None

        # 创建访问令牌和刷新令牌
        access_token_data = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
            "email": user.email,
        }
        refresh_token_data = {
            "sub": user.username,
            "user_id": user.id,
        }

        access_token = self.create_access_token(access_token_data)
        refresh_token = self.create_refresh_token(refresh_token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user.to_dict(),
        }

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """使用刷新令牌获取新的访问令牌"""
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return None

        username = payload.get("sub")
        user = await self.user_repo.get_by_username(username)
        if not user or not user.is_active:
            return None

        # 创建新的访问令牌
        access_token_data = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
            "email": user.email,
        }
        return self.create_access_token(access_token_data)

    async def get_current_user(self, token: str) -> Optional[User]:
        """从令牌获取当前用户"""
        payload = self.verify_token(token, "access")
        if not payload:
            return None

        username = payload.get("sub")
        if not username:
            return None

        user = await self.user_repo.get_by_username(username)
        if not user or not user.is_active:
            return None

        return user

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> bool:
        """修改密码"""
        if not self.verify_password(current_password, user.password_hash):
            return False

        user.password_hash = self.get_password_hash(new_password)
        await self.user_repo.update(user)
        return True

    async def reset_password_request(self, email: str) -> Optional[str]:
        """请求密码重置"""
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None

        # 生成重置令牌（有效期1小时）
        reset_token_data = {
            "sub": user.username,
            "user_id": user.id,
            "type": "password_reset",
        }
        reset_token = self.create_access_token(reset_token_data, timedelta(hours=1))
        return reset_token

    async def reset_password(self, reset_token: str, new_password: str) -> bool:
        """重置密码"""
        payload = self.verify_token(reset_token, "access")
        if not payload or payload.get("type") != "password_reset":
            return False

        username = payload.get("sub")
        user = await self.user_repo.get_by_username(username)
        if not user:
            return False

        user.password_hash = self.get_password_hash(new_password)
        await self.user_repo.update(user)
        return True

    async def verify_email(self, verification_token: str) -> bool:
        """验证邮箱"""
        payload = self.verify_token(verification_token, "access")
        if not payload or payload.get("type") != "email_verification":
            return False

        username = payload.get("sub")
        user = await self.user_repo.get_by_username(username)
        if not user:
            return False

        user.is_verified = True
        await self.user_repo.update(user)
        return True

    def create_email_verification_token(self, user: User) -> str:
        """创建邮箱验证令牌"""
        verification_data = {
            "sub": user.username,
            "user_id": user.id,
            "type": "email_verification",
        }
        return self.create_access_token(verification_data, timedelta(hours=24))
