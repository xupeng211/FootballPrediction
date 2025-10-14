"""
JWT认证和RBAC权限控制模块
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any,  Dict[str, Any],  Any, List[Any], Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


class TokenType:
    """Token类型常量"""

    ACCESS = "access"
    REFRESH = "refresh"


class Role:
    """角色常量"""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    MODERATOR = "moderator"


class Permission:
    """权限常量"""

    # 预测相关
    CREATE_PREDICTION = "create_prediction"
    READ_PREDICTION = "read_prediction"
    UPDATE_PREDICTION = "update_prediction"
    DELETE_PREDICTION = "delete_prediction"

    # 用户相关
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"

    # 比赛相关
    READ_MATCH = "read_match"
    UPDATE_MATCH = "update_match"
    DELETE_MATCH = "delete_match"

    # 系统相关
    READ_SYSTEM = "read_system"
    UPDATE_SYSTEM = "update_system"
    MANAGE_USERS = "manage_users"


# 角色权限映射
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.CREATE_PREDICTION,
        Permission.READ_PREDICTION,
        Permission.UPDATE_PREDICTION,
        Permission.DELETE_PREDICTION,
        Permission.READ_USER,
        Permission.UPDATE_USER,
        Permission.DELETE_USER,
        Permission.READ_MATCH,
        Permission.UPDATE_MATCH,
        Permission.DELETE_MATCH,
        Permission.READ_SYSTEM,
        Permission.UPDATE_SYSTEM,
        Permission.MANAGE_USERS,
    ],
    Role.MODERATOR: [
        Permission.CREATE_PREDICTION,
        Permission.READ_PREDICTION,
        Permission.UPDATE_PREDICTION,
        Permission.DELETE_PREDICTION,
        Permission.READ_USER,
        Permission.UPDATE_USER,
        Permission.READ_MATCH,
        Permission.UPDATE_MATCH,
        Permission.READ_SYSTEM,
    ],
    Role.USER: [
        Permission.CREATE_PREDICTION,
        Permission.READ_PREDICTION,
        Permission.UPDATE_PREDICTION,
        Permission.DELETE_PREDICTION,
        Permission.READ_USER,
        Permission.UPDATE_USER,
        Permission.READ_MATCH,
    ],
    Role.VIEWER: [
        Permission.READ_PREDICTION,
        Permission.READ_MATCH,
        Permission.READ_SYSTEM,
    ],
}


class AuthManager:
    """认证管理器"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
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
                "type": TokenType.ACCESS,
                "iat": datetime.utcnow(),
            }
        )

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update(
            {
                "exp": expire,
                "type": TokenType.REFRESH,
                "iat": datetime.utcnow(),
            }
        )

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(
        self, token: str, token_type: str = TokenType.ACCESS
    ) -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 检查token类型
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )

            # 检查过期时间
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                )

            return payload

        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    def refresh_access_token(self, refresh_token: str) -> str:
        """使用刷新令牌获取新的访问令牌"""
        payload = self.verify_token(refresh_token, TokenType.REFRESH)

        # 移除敏感信息，创建新的访问令牌
        user_data = {
            "sub": payload.get("sub"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
        }

        return self.create_access_token(user_data)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)


# 全局认证管理器实例
auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """获取认证管理器实例"""
    global auth_manager
    if auth_manager is None:
        from src.security.secret_manager import get_secret_manager

        secret_manager = get_secret_manager()
        secret_key = secret_manager.get_jwt_secret()

        auth_manager = AuthManager(secret_key=secret_key)

    return auth_manager


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """获取当前用户"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth = get_auth_manager()
    payload = auth.verify_token(credentials.credentials)

    # 获取用户信息
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return {
        "user_id": user_id,
        "roles": payload.get("roles", []),
        "permissions": payload.get("permissions", []),
        "token_type": payload.get("type"),
    }


def require_permissions(required_permissions: Union[str, List[str]):
    """权限装饰器工厂"""
    if isinstance(required_permissions, str):
        required_permissions = [required_permissions]

    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = current_user.get("permissions", [])
        user_roles = current_user.get("roles", [])

        # 检查用户是否有所有必需的权限
        for permission in required_permissions:
            if permission not in user_permissions:
                # 检查用户角色是否有该权限
                has_permission = False
                for role in user_roles:
                    role_perms = ROLE_PERMISSIONS.get(role, [])
                    if permission in role_perms:
                        has_permission = True
                        break

                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission} required",
                    )

        return current_user

    return permission_checker


def require_roles(required_roles: Union[str, List[str]):
    """角色装饰器工厂"""
    if isinstance(required_roles, str):
        required_roles = [required_roles]

    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])

        # 检查用户是否有任一必需的角色
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}",
            )

        return current_user

    return role_checker


def get_user_permissions(roles: List[str]) -> List[str]:
    """获取用户所有权限"""
    permissions = set()
    for role in roles:
        role_perms = ROLE_PERMISSIONS.get(role, [])
        permissions.update(role_perms)

    return list(permissions)


# 常用的权限依赖
RequireAdmin = require_roles(Role.ADMIN)
RequireUser = require_roles([Role.USER, Role.MODERATOR, Role.ADMIN])
RequireModerator = require_roles([Role.MODERATOR, Role.ADMIN])
RequireViewer = require_roles([Role.VIEWER, Role.USER, Role.MODERATOR, Role.ADMIN])
