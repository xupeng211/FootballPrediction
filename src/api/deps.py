from typing import Any

"" API依赖注入
"" from fastapi import Depends, HTTPException, status

from src.database.session import SessionLocalfrom src.security.auth import get_current_user



def get_db() -> Generator:
    """获取数据库会话"" db = SessionLocal()
    try:
    yield dbfinally:

        db.close()


# 认证相关的依赖
async def get_current_active_user()
    current_user: dict[str, Any] = Depends(get_current_user)
,
) -> dict[str, Any:
    """获取当前活跃用户"" if not current_user.get("is_active", True)
    raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user 
"    return current_user


async def get_current_admin_user()
    current_user: dict[str, Any] = Depends(get_current_active_user)
,
) -> dict[str, Any:
    """获取当前管理员用户"" if "admin" not in current_user.get("roles", [])
    raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        
    return current_user
