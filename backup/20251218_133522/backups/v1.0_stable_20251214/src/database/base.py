"""SQLAlchemy基础模型和数据库连接.

提供所有数据模型的基础类,包含通用字段和方法，以及数据库连接函数。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy基础模型类."""


class TimestampMixin:
    """类文档字符串."""

    pass  # 添加pass语句
    """时间戳混入类,为模型添加创建时间和更新时间字段"""

    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )


class BaseModel(Base, TimestampMixin):
    """基础模型类.

    所有业务模型都应该继承此类,自动包含:
    - 主键ID字段
    - 创建时间和更新时间字段
    - 常用的方法
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

    def to_dict(self, exclude_fields: set | None = None) -> dict[str, Any]:
        """将模型对象转换为字典.

        Args:
            exclude_fields: 需要排除的字段集合

        Returns:
            dict[str, Any]: 模型字典表示
        """
        if exclude_fields is None:
            exclude_fields = set()

        result: dict[str, Any] = {}
        for column in self.__table__.columns:
            column_name = column.name
            if column_name not in exclude_fields:
                value = getattr(self, column_name)
                if isinstance(value, datetime):
                    # 将datetime转换为ISO格式字符串
                    result[column_name] = value.isoformat()
                else:
                    result[column_name] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """从字典创建模型实例.

        Args:
            data: 包含模型数据的字典

        Returns:
            BaseModel: 模型实例
        """
        # 过滤掉不属于模型的字段
        valid_columns = {column.name for column in cls.__table__.columns}
        filtered_data = {
            key: value for key, value in data.items() if key in valid_columns
        }
        return cls(**filtered_data)

    def update_from_dict(
        self, data: dict[str, Any], exclude_fields: set[str] | None = None
    ) -> None:
        """从字典更新模型对象.

        Args:
            data: 更新数据字典
            exclude_fields: 需要排除的字段集合
        """
        exclude_fields = exclude_fields or set()

        {column.name for column in self.__table__.columns}
        for key, value in data.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        """对象的字符串表示."""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)})>"


# ============================================================================
# ⚠️ 过时的数据库配置 - 已迁移到 async_manager.py
# ⚠️ DEPRECATED DATABASE CONFIG - Moved to async_manager.py
# ============================================================================

"""
⚠️ 警告：以下代码已弃用！

旧的连接配置已经移动到 src/database/async_manager.py。
请使用新的统一接口：

    from src.database.async_manager import initialize_database, get_async_db_session

旧的代码（已弃用）:

    # 同步数据库引擎和会话
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 异步数据库引擎和会话
    async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    def get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

新的代码:

    from src.database.async_manager import initialize_database, get_async_db_session

    # 1. 应用启动时初始化
    initialize_database()

    # 2. 在路由中使用（自动依赖注入）
    @app.get("/matches/")
    async def get_matches(session: AsyncSession = Depends(get_async_db_session)):
        result = await session.execute(select(Match))
        return result.scalars().all()

    # 3. 在脚本中使用（上下文管理器）
    async def my_script():
        async with get_async_db_session() as session:
            result = await session.execute(select(Match))
            return result.scalars().all()
"""


def get_db():
    """⚠️ DEPRECATED: 使用 src.database.async_manager.get_async_db_session"""
    import warnings

    warnings.warn(
        "get_db() 已弃用，请使用 src.database.async_manager.get_async_db_session",
        DeprecationWarning,
        stacklevel=2,
    )
    from .async_manager import get_async_db_session

    # 直接返回新的实现
    return get_async_db_session()


async def get_async_db():
    """⚠️ DEPRECATED: 使用 src.database.async_manager.get_async_db_session"""
    import warnings

    warnings.warn(
        "get_async_db() 已弃用，请使用 src.database.async_manager.get_async_db_session",
        DeprecationWarning,
        stacklevel=2,
    )
    from .async_manager import get_async_db_session

    async for session in get_async_db_session():
        yield session


class DatabaseManager:
    """数据库管理器 - 为测试提供mock接口."""

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化数据库管理器."""
        self.config = config or {}
        self._connection = None
        self._initialized = False  # 向后兼容的初始化状态

    def initialize(self) -> None:
        """初始化数据库管理器（向后兼容方法）."""
        self._initialized = True

    async def check_connection(self) -> dict[str, Any]:
        """检查数据库连接."""
        return {
            "status": "healthy",
            "response_time_ms": 12,
            "pool_size": 10,
            "active_connections": 3,
        }

    def get_connection_status(self) -> dict[str, Any]:
        """获取连接状态."""
        return {
            "status": "healthy",
            "response_time_ms": 5,
        }

    async def connect(self) -> None:
        """建立连接."""
        pass

    async def disconnect(self) -> None:
        """断开连接."""
        pass


# ============================================================================
# 导出列表
# Export list
# ============================================================================

__all__ = [
    # 基础模型类（保留，继续使用）
    "Base",
    "BaseModel",
    "TimestampMixin",
    # 旧的依赖注入函数（已弃用，保留向后兼容）
    "get_db",  # ⚠️ DEPRECATED
    "get_async_db",  # ⚠️ DEPRECATED
    # 测试用数据库管理器（保留）
    "DatabaseManager",
]

# ============================================================================
# 使用说明
# Usage Guide
# ============================================================================

"""
📚 新代码应该从哪里导入？

1. 模型和基础类:
   from src.database.base import Base, BaseModel, TimestampMixin

2. 数据库会话管理（推荐）:
   from src.database.async_manager import (
       initialize_database,
       get_async_db_session,
       get_db_session,
   )

3. 依赖注入（FastAPI）:
   from src.database.async_manager import get_async_db_session
   from fastapi import Depends

   @app.get("/")
   async def handler(session: AsyncSession = Depends(get_async_db_session)):
       pass

4. 脚本和爬虫:
   from src.database.async_manager import get_db_session

   async def my_script():
       async with get_db_session() as session:
           # 使用 session 执行查询
           pass

⚠️ 注意: get_db() 和 get_async_db() 已弃用，请迁移到新接口。
"""

# ============================================================================
# 向后兼容的别名
# Backward Compatibility Aliases
# ============================================================================

# AsyncSessionLocal 别名（向后兼容）
try:
    from .async_manager import get_database_manager

    # 创建一个虚拟的 AsyncSessionLocal 类以保持向后兼容
    class AsyncSessionLocal:
        """
        ⚠️ DEPRECATED: 使用 src.database.async_manager.get_db_session

        为向后兼容而保留的 AsyncSessionLocal 类
        """

        pass

    # 将其添加到模块命名空间（但不推荐使用）
    import sys

    current_module = sys.modules[__name__]
    current_module.AsyncSessionLocal = AsyncSessionLocal

except ImportError:
    pass
