from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

"""
SQLAlchemy基础模型和数据库连接

提供所有数据模型的基础类,包含通用字段和方法，以及数据库连接函数。
"""


class Base(DeclarativeBase):
    """SQLAlchemy基础模型类"""


class TimestampMixin:
    """类文档字符串"""

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
    """
    基础模型类

    所有业务模型都应该继承此类,自动包含:
    - 主键ID字段
    - 创建时间和更新时间字段
    - 常用的方法
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

    def to_dict(self, exclude_fields: set | None = None) -> dict[str, Any]:
        """
        将模型对象转换为字典

        Args:
            exclude_fields: 需要排除的字段集合

        Returns:
            Dict[str, Any]: 模型字典表示
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
        """从字典创建模型实例

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
        """
        从字典更新模型对象

        Args:
            data: 更新数据字典
            exclude_fields: 需要排除的字段集合
        """
        exclude_fields = exclude_fields or set()

        {column.name for column in self.__table__.columns}
        for key, value in data.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        """对象的字符串表示"""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)})>"


DATABASE_URL = "sqlite:///./football_prediction.db"
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./football_prediction.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """
    获取同步数据库会话
    Get synchronous database session

    用于FastAPI的依赖注入。
    Used for FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话
    Get asynchronous database session

    用于异步操作的依赖注入。
    Used for async operation dependency injection.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


__all__ = ["Base", "BaseModel", "TimestampMixin"]
