"""
JWT认证管理模块
JWT Authentication Manager Module

提供完整的JWT token管理、用户认证和授权功能
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
import redis.asyncio as redis
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Token数据模型"""

    user_id: int
    username: str
    email: str
    role: str
    token_type: str
    exp: datetime
    iat: datetime
    jti: str


@dataclass
class UserAuth:
    """用户认证数据"""

    id: int
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    role: str = "user"


class JWTAuthManager:
    """JWT认证管理器"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        redis_url: Optional[str] = None,
    ):
        """
        初始化JWT认证管理器

        Args:
            secret_key: JWT密钥
            algorithm: 加密算法
            access_token_expire_minutes: 访问令牌过期时间（分钟）
            refresh_token_expire_days: 刷新令牌过期时间（天）
            redis_url: Redis连接URL，用于token黑名单
        """
        self.secret_key = (
            secret_key or os.getenv("JWT_SECRET_KEY") or self._generate_secret_key()
        )
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

        # 密码加密上下文
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Redis连接（用于token黑名单）
        self.redis_client: Optional[redis.Redis] = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis连接失败，token黑名单功能不可用: {e}")

    def _generate_secret_key(self) -> str:
        """生成安全的JWT密钥"""
        return secrets.token_urlsafe(64)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建访问令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            JWT token字符串
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access",
                "jti": secrets.token_urlsafe(16),  # JWT ID，用于黑名单
            }
        )

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建刷新令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            JWT refresh token字符串
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh",
                "jti": secrets.token_urlsafe(16),
            }
        )

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    async def verify_token(self, token: str) -> TokenData:
        """
        验证JWT令牌

        Args:
            token: JWT令牌字符串

        Returns:
            TokenData对象

        Raises:
            ValueError: 令牌无效或过期
        """
        try:
            # 解码JWT
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 检查token是否在黑名单中
            if await self._is_token_blacklisted(payload.get("jti")):
                raise ValueError("Token has been revoked")

            # 提取用户信息
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid token: missing user ID")

            username = payload.get("username")
            email = payload.get("email")
            role = payload.get("role", "user")
            token_type = payload.get("type")
            exp = datetime.fromtimestamp(payload.get("exp"))
            iat = datetime.fromtimestamp(payload.get("iat"))
            jti = payload.get("jti")

            return TokenData(
                user_id=int(user_id),
                username=username,
                email=email,
                role=role,
                token_type=token_type,
                exp=exp,
                iat=iat,
                jti=jti,
            )

        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise ValueError("Invalid token")

    async def blacklist_token(self, jti: str, exp: datetime) -> None:
        """
        将token加入黑名单

        Args:
            jti: JWT ID
            exp: 过期时间
        """
        if not self.redis_client:
            logger.warning("Redis不可用，无法将token加入黑名单")
            return

        try:
            # 计算剩余过期时间
            ttl = int((exp - datetime.utcnow()).total_seconds())
            if ttl > 0:
                await self.redis_client.setex(f"blacklist:{jti}", ttl, "1")
                logger.info(f"Token {jti} 已加入黑名单")
        except Exception as e:
            logger.error(f"将token加入黑名单失败: {e}")

    async def _is_token_blacklisted(self, jti: Optional[str]) -> bool:
        """
        检查token是否在黑名单中

        Args:
            jti: JWT ID

        Returns:
            是否在黑名单中
        """
        if not self.redis_client or not jti:
            return False

        try:
            result = await self.redis_client.exists(f"blacklist:{jti}")
            return bool(result)
        except Exception as e:
            logger.error(f"检查token黑名单失败: {e}")
            return False

    def hash_password(self, password: str) -> str:
        """
        哈希密码

        Args:
            password: 明文密码

        Returns:
            哈希后的密码
        """
        # bcrypt限制密码长度为72字节
        if len(password.encode("utf-8")) > 72:
            password = password[:72]
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证密码

        Args:
            plain_password: 明文密码
            hashed_password: 哈希密码

        Returns:
            密码是否正确
        """
        # bcrypt限制密码长度为72字节
        if len(plain_password.encode("utf-8")) > 72:
            plain_password = plain_password[:72]
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_password_reset_token(self, email: str) -> str:
        """
        生成密码重置令牌

        Args:
            email: 用户邮箱

        Returns:
            密码重置令牌
        """
        delta = timedelta(hours=1)  # 1小时有效期
        to_encode = {"email": email, "type": "password_reset"}
        expire = datetime.utcnow() + delta

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "password_reset",
                "jti": secrets.token_urlsafe(16),
            }
        )

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def verify_password_reset_token(self, token: str) -> str:
        """
        验证密码重置令牌

        Args:
            token: 密码重置令牌

        Returns:
            用户邮箱

        Raises:
            ValueError: 令牌无效
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email: str = payload.get("email")
            token_type: str = payload.get("type")

            if token_type != "password_reset":
                raise ValueError("Invalid token type")

            if not email:
                raise ValueError("Invalid token: missing email")

            return email

        except jwt.ExpiredSignatureError:
            raise ValueError("Password reset token has expired")
        except jwt.JWTError:
            raise ValueError("Invalid password reset token")

    async def close(self) -> None:
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()

    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """
        验证密码强度

        Args:
            password: 密码

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        if len(password) < 8:
            errors.append("密码长度至少8位")

        if len(password) > 128:
            errors.append("密码长度不能超过128位")

        if not any(c.isupper() for c in password):
            errors.append("密码必须包含至少一个大写字母")

        if not any(c.islower() for c in password):
            errors.append("密码必须包含至少一个小写字母")

        if not any(c.isdigit() for c in password):
            errors.append("密码必须包含至少一个数字")

        # 检查特殊字符
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            errors.append("密码必须包含至少一个特殊字符")

        return len(errors) == 0, errors


# 全局JWT认证管理器实例
_jwt_auth_manager: Optional[JWTAuthManager] = None


def get_jwt_auth_manager() -> JWTAuthManager:
    """获取全局JWT认证管理器实例"""
    global _jwt_auth_manager
    if _jwt_auth_manager is None:
        _jwt_auth_manager = JWTAuthManager()
    return _jwt_auth_manager


def init_jwt_auth_manager(
    secret_key: Optional[str] = None,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7,
    redis_url: Optional[str] = None,
) -> JWTAuthManager:
    """
    初始化JWT认证管理器

    Args:
        secret_key: JWT密钥
        algorithm: 加密算法
        access_token_expire_minutes: 访问令牌过期时间
        refresh_token_expire_days: 刷新令牌过期时间
        redis_url: Redis连接URL

    Returns:
        JWT认证管理器实例
    """
    global _jwt_auth_manager
    _jwt_auth_manager = JWTAuthManager(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
        redis_url=redis_url,
    )
    return _jwt_auth_manager
