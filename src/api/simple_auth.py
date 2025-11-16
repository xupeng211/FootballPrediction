from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

"""
简化的用户认证API

提供基本的用户认证功能,避免复杂依赖问题
"""

# 简化的依赖,避免复杂导入
# from src.database.connection import get_async_session

router = APIRouter(prefix="/auth", tags=["认证"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# 简化的用户数据结构
class SimpleUser(BaseModel):
    id: int
    username: str
    email: str
    password: str
    role: str
    is_active: bool = True
    created_at: datetime

    class Config:
        """Pydantic配置."""

        json_encoders = {datetime: lambda v: v.isoformat()}


# 简化的用户注册请求
class SimpleUserRegister(BaseModel):
    username: str
    email: str
    password: str


# 简化的令牌响应
class SimpleTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


# 简化的认证服务
class SimpleAuthService:
    """类文档字符串."""

    pass  # 添加pass语句

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        # 简化的用户存储（实际应用中应该使用数据库）
        self.users = {
            "admin": {
                "id": 1,
                "username": "admin",
                "password": "admin123",
                "email": "admin@example.com",
                "role": "admin",
            },
            "testuser": {
                "id": 2,
                "username": "testuser",
                "password": "test123",
                "email": "test@example.com",
                "role": "user",
            },
        }

    def verify_password(self, plain_password: str, stored_password: str) -> bool:
        """简单密码验证（实际应用中应该使用bcrypt）."""
        return plain_password == stored_password

    def authenticate_user(self, username: str, password: str) -> SimpleUser | None:
        """验证用户凭据."""
        user_data = self.users.get(username)
        if not user_data:
            return None

        if not self.verify_password(password, user_data["password"]):
            return None

        return SimpleUser(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            role=user_data["role"],
            created_at=datetime.utcnow(),
        )

    def create_user(self, username: str, email: str, password: str) -> SimpleUser:
        """创建新用户."""
        if username in self.users:
            raise ValueError("用户名已存在")

        # 简单的用户ID生成
        new_id = (
            max(user["id"] for user in self.users.values()) + 1 if self.users else 1
        )

        self.users[username] = {
            "id": new_id,
            "username": username,
            "password": password,
            "email": email,
            "role": "user",
        }

        return SimpleUser(
            id=new_id,
            username=username,
            email=email,
            password=password,
            role="user",
            created_at=datetime.utcnow(),
        )

    def store_user(self, user: SimpleUser) -> None:
        """存储用户对象."""
        self.users[user.username] = {
            "id": user.id,
            "username": user.username,
            "password": user.password,
            "email": user.email,
            "role": user.role,
        }

    def get_user(self, username: str) -> SimpleUser | None:
        """获取用户对象."""
        user_data = self.users.get(username)
        if not user_data:
            return None

        return SimpleUser(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            role=user_data["role"],
            created_at=datetime.utcnow(),
        )

    def generate_token(self, user: SimpleUser) -> str:
        """生成简单的访问令牌."""
        # 在实际应用中应该使用JWT或其他安全的令牌机制
        timestamp = datetime.utcnow().timestamp()
        token_data = f"{user.username}:{user.id}:{timestamp}"
        return f"Bearer {token_data}"

    def verify_token(self, token: str) -> SimpleUser | None:
        """验证访问令牌."""
        if not token.startswith("Bearer "):
            return None

        try:
            token_data = token[7:]  # 移除 "Bearer " 前缀
            parts = token_data.split(":")

            if len(parts) != 3:
                return None

            username, user_id_str, timestamp_str = parts

            # 简单的令牌过期检查（24小时）
            token_time = float(timestamp_str)
            if datetime.utcnow().timestamp() - token_time > 86400:  # 24小时
                return None

            user_data = self.users.get(username)
            if not user_data or str(user_data["id"]) != user_id_str:
                return None

            return SimpleUser(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                role=user_data["role"],
                created_at=datetime.utcnow(),
            )

        except (ValueError, IndexError):
            return None

    def get_user_by_username(self, username: str) -> SimpleUser | None:
        """根据用户名获取用户."""
        user_data = self.users.get(username)
        if not user_data:
            return None

        return SimpleUser(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            role=user_data["role"],
            created_at=datetime.utcnow(),
        )


# 全局认证服务实例
auth_service = SimpleAuthService()


# 依赖函数
async def get_current_user(token: str = Depends(oauth2_scheme)) -> SimpleUser:
    """获取当前用户（简化版本,不验证令牌）."""
    # 简化实现:从令牌中提取用户名
    # 实际应用中应该验证JWT令牌
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 简化实现:假设token格式为 "Bearer username"
    if token.startswith("Bearer "):
        username = token[7:]  # 移除 "Bearer " 前缀
    else:
        username = token

    user = auth_service.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# API端点
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: SimpleUserRegister):
    """用户注册."""
    try:
        user = auth_service.create_user(
            user_data.username, user_data.email, user_data.password
        )
        return {"message": "用户注册成功", "user": user.dict()}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e  # TODO: B904 exception chaining


@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录."""
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 简化的令牌（实际应用中应该使用JWT）
    access_token = f"Bearer {user.username}"
    expires_in = 3600  # 1小时

    return SimpleTokenResponse(
        access_token=access_token, token_type="bearer", expires_in=expires_in
    )


@router.get("/me")
async def get_current_user_info(current_user: SimpleUser = Depends(get_current_user)):
    """获取当前用户信息."""
    return {"user": current_user.dict(), "message": "用户信息获取成功"}


@router.post("/logout")
async def logout_user():
    """用户登出."""
    return {"message": "登出成功"}


# 导出router
__all__ = ["router"]
