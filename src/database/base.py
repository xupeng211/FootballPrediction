"""
SQLAlchemy基础模型

提供所有数据模型的基础类，包含通用字段和方法。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy基础模型类"""


class TimestampMixin:
    """时间戳混入类，为模型添加创建时间和更新时间字段"""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

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

    所有业务模型都应该继承此类，自动包含：
    - 主键ID字段
    - 创建时间和更新时间字段
    - 常用的方法
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

    def to_dict(self, exclude_fields: Optional[set] = None) -> Dict[str, Any]:
        """
        将模型对象转换为字典

        Args:
            exclude_fields: 需要排除的字段集合

        Returns:
            Dict[str, Any]: 模型字典表示
        """
        if exclude_fields is None:
            exclude_fields = set()

        result: Dict[str, Any] = {}
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
    def from_dict(cls, data: Dict[str, Any]):
        """
        从字典创建模型实例

        Args:
            data: 包含模型数据的字典

        Returns:
            BaseModel: 模型实例
        """
        # 过滤掉不属于模型的字段
        valid_columns = {column.name for column in cls.__table__.columns}
        filtered_data = {key: value for key, value in data.items() if key in valid_columns}
        return cls(**filtered_data)

    def update_from_dict(self, data: Dict[str, Any], exclude_fields: Optional[set] = None) -> None:
        """
        从字典更新模型对象

        Args:
            data: 更新数据字典
            exclude_fields: 需要排除的字段集合
        """
        if exclude_fields is None:
            exclude_fields = {"id", "created_at"}  # 默认排除ID和创建时间

        valid_fields = {col.name for col in self.__table__.columns}

        for key, value in data.items():
            if key in valid_fields and key not in exclude_fields:
                setattr(self, key, value)

    def __repr__(self) -> str:
        """对象的字符串表示"""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)})>"


# 导出基础类，供其他模型使用
__all__ = ["Base", "BaseModel", "TimestampMixin"]
