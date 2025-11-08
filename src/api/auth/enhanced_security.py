"""
企业级API安全系统
Enhanced API Security System

提供完整的JWT认证、权限控制、速率限制等企业级安全功能。
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, validator

# ============================================================================
# 配置和常量
# ============================================================================

# JWT配置 - 在生产环境中应该从环境变量读取
JWT_SECRET_KEY = secrets.token_urlsafe(32)  # 生产环境应该使用固定密钥
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# 速率限制配置
RATE_LIMIT_REQUESTS = 100  # 每小时请求数
RATE_LIMIT_WINDOW = 3600  # 时间窗口（秒）


# 权限级别
class Permission:
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    PREDICT = "predict"


# ============================================================================
# 数据模型
# ============================================================================


class UserCredentials(BaseModel):
    """用户凭据模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")

    @validator("password")
    def validate_password(self, v):
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        return v


class TokenResponse(BaseModel):
    """令牌响应模型"""

    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    scope: str = Field(default="read write", description="权限范围")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(..., description="刷新令牌")


class UserInfo(BaseModel):
    """用户信息模型"""

    id: int
    username: str
    email: str | None = None
    is_active: bool = True
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    last_login: datetime | None = None


# ============================================================================
# 密码处理
# ============================================================================


class PasswordManager:
    """密码管理器"""

    @staticmethod
    def hash_password(password: str) -> str:
        """加密密码"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False


# ============================================================================
# JWT令牌管理
# ============================================================================


class TokenManager:
    """JWT令牌管理器"""

    @staticmethod
    def create_access_token(
        data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "access"})

        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(
        data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "refresh"})

        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # 检查令牌类型
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌类型"
                )

            # 检查过期时间
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp, UTC) < datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已过期"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已过期"
            ) from None
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌"
            ) from None


# ============================================================================
# 模拟用户存储（生产环境应使用数据库）
# ============================================================================


class MockUserStore:
    """模拟用户存储"""

    def __init__(self):
        # 初始化一些测试用户
        self.users = {
            "admin": {
                "id": 1,
                "username": "admin",
                "password_hash": PasswordManager.hash_password("Admin123!"),
                "email": "admin@example.com",
                "is_active": True,
                "permissions": [
                    Permission.READ,
                    Permission.WRITE,
                    Permission.ADMIN,
                    Permission.PREDICT,
                ],
                "created_at": datetime.now(UTC),
                "last_login": None,
            },
            "user": {
                "id": 2,
                "username": "user",
                "password_hash": PasswordManager.hash_password("User123!"),
                "email": "user@example.com",
                "is_active": True,
                "permissions": [Permission.READ, Permission.PREDICT],
                "created_at": datetime.now(UTC),
                "last_login": None,
            },
        }

        # 存储刷新令牌
        self.refresh_tokens = {}

    def get_user(self, username: str) -> dict[str, Any] | None:
        """获取用户信息"""
        return self.users.get(username)

    def verify_user(self, username: str, password: str) -> dict[str, Any] | None:
        """验证用户凭据"""
        user = self.get_user(username)
        if user and PasswordManager.verify_password(password, user["password_hash"]):
            return user
        return None

    def update_last_login(self, username: str) -> None:
        """更新最后登录时间"""
        if username in self.users:
            self.users[username]["last_login"] = datetime.now(UTC)

    def store_refresh_token(self, token: str, user_id: int) -> None:
        """存储刷新令牌"""
        self.refresh_tokens[token] = {
            "user_id": user_id,
            "created_at": datetime.now(UTC),
        }

    def verify_refresh_token(self, token: str) -> int | None:
        """验证刷新令牌"""
        token_data = self.refresh_tokens.get(token)
        if token_data:
            return token_data["user_id"]
        return None

    def revoke_refresh_token(self, token: str) -> None:
        """撤销刷新令牌"""
        self.refresh_tokens.pop(token, None)


# 全局用户存储实例
user_store = MockUserStore()

# ============================================================================
# 安全依赖
# ============================================================================


class EnhancedSecurity(HTTPBearer):
    """增强的安全认证"""

    def __init__(self, required_permissions: list[str] | None = None):
        super().__init__(auto_error=True)
        self.required_permissions = required_permissions or []

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    ) -> UserInfo:
        """验证认证和权限"""

        # 验证令牌
        try:
            payload = TokenManager.verify_token(credentials.credentials, "access")
        except HTTPException:
            raise

        # 获取用户信息
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌中缺少用户信息"
            )

        user_data = user_store.get_user(username)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在"
            )

        if not user_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已被禁用"
            )

        # 检查权限
        user_permissions = set(user_data.get("permissions", []))
        required_permissions = set(self.required_permissions)

        if required_permissions and not required_permissions.issubset(user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="权限不足"
            )

        return UserInfo(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data.get("email"),
            is_active=user_data["is_active"],
            permissions=user_data.get("permissions", []),
            created_at=user_data["created_at"],
            last_login=user_data.get("last_login"),
        )


# ============================================================================
# 速率限制
# ============================================================================


class RateLimiter:
    """速率限制器"""

    def __init__(self):
        self.requests = {}

    def is_allowed(
        self,
        key: str,
        limit: int = RATE_LIMIT_REQUESTS,
        window: int = RATE_LIMIT_WINDOW,
    ) -> bool:
        """检查是否允许请求"""
        now = datetime.now(UTC)

        if key not in self.requests:
            self.requests[key] = []

        # 清理过期请求
        self.requests[key] = [
            req_time
            for req_time in self.requests[key]
            if (now - req_time).total_seconds() < window
        ]

        # 检查是否超过限制
        if len(self.requests[key]) >= limit:
            return False

        # 记录当前请求
        self.requests[key].append(now)
        return True


# 全局速率限制器实例
rate_limiter = RateLimiter()

# ============================================================================
# 辅助函数
# ============================================================================


def create_user_tokens(username: str) -> TokenResponse:
    """为用户创建令牌"""
    user = user_store.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 创建访问令牌
    access_data = {
        "sub": user["username"],
        "user_id": user["id"],
        "permissions": user["permissions"],
    }
    access_token = TokenManager.create_access_token(access_data)

    # 创建刷新令牌
    refresh_data = {"sub": user["username"], "user_id": user["id"]}
    refresh_token = TokenManager.create_refresh_token(refresh_data)

    # 存储刷新令牌
    user_store.store_refresh_token(refresh_token, user["id"])

    # 更新最后登录时间
    user_store.update_last_login(username)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        scope=" ".join(user["permissions"]),
    )


def get_client_identifier(request: Request) -> str:
    """获取客户端标识符"""
    # 优先使用用户ID，然后使用IP地址
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # 使用IP地址和User-Agent的组合
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    user_agent = request.headers.get("User-Agent", "")

    # 使用哈希来保护隐私
    identifier = hashlib.md5(f"{ip}:{user_agent}".encode()).hexdigest()
    return f"ip:{identifier}"
