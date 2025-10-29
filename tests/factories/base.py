"""
基础测试工厂类
提供所有工厂的基类和通用功能
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseFactory(ABC):
    """基础工厂抽象类"""

    @classmethod
    @abstractmethod
    def create(cls, **kwargs) -> Any:
        """创建实例的抽象方法"""
        pass

    @classmethod
    @abstractmethod
    def create_batch(cls, count: int, **kwargs) -> List[Any]:
        """批量创建实例的抽象方法"""
        pass

    @classmethod
    def get_default_data(cls) -> Dict[str, Any]:
        """获取默认数据"""
        return {}

    @classmethod
    def generate_id(cls) -> int:
        """生成ID"""
        return uuid.uuid4().int

    @classmethod
    def generate_timestamp(cls) -> datetime:
        """生成时间戳"""
        return datetime.now(timezone.utc)


class DataFactoryMixin:
    """数据工厂混入类"""

    @classmethod
    def create_with_relations(cls, **kwargs):
        """创建带关联关系的实例"""
        return cls.create(**kwargs)

    @classmethod
    def create_test_data(cls, count: int = 1, **kwargs):
        """创建测试数据"""
        if count == 1:
            return cls.create(**kwargs)
        return cls.create_batch(count, **kwargs)


class ValidationMixin:
    """验证混入类"""

    @classmethod
    def validate_data(cls, data: Dict[str, Any]) -> bool:
        """验证数据有效性"""
        return True

    @classmethod
    def sanitize_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理数据"""
        return data.copy()


class TimestampMixin:
    """时间戳混入类"""

    @classmethod
    def with_timestamps(cls, **kwargs):
        """添加时间戳字段"""
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        return kwargs
