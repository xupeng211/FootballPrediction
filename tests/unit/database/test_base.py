"""
数据库基础模型测试
Tests for Database Base Models

测试src.database.base模块的功能
"""

import pytest
from datetime import datetime
from sqlalchemy import Column, String, Integer

from src.database.base import Base, TimestampMixin, BaseModel


@pytest.mark.unit
@pytest.mark.database

class TestTimestampMixin:
    """时间戳混入测试"""

    def test_timestamp_mixin_attributes(self):
        """测试：时间戳混入属性"""

        # 创建一个使用TimestampMixin的临时模型
        class TestModel(Base, TimestampMixin):
            __tablename__ = "test_timestamp"

            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # 检查字段是否存在
        assert hasattr(TestModel, "created_at")
        assert hasattr(TestModel, "updated_at")

        # 创建实例
        TestModel(name="test")

        # 检查列定义
        columns = TestModel.__table__.columns
        assert "created_at" in columns
        assert "updated_at" in columns

        # 检查列的默认值设置
        assert columns["created_at"].default is not None
        assert columns["updated_at"].default is not None
        assert columns["updated_at"].onupdate is not None


class TestBaseModel:
    """基础模型测试"""

    def test_base_model_attributes(self):
        """测试：基础模型属性"""

        # 创建一个继承BaseModel的测试模型
        class TestModel(BaseModel):
            __tablename__ = "test_base_model"

            name = Column(String(50), nullable=False)
            description = Column(String(200))

        # 检查字段
        assert hasattr(TestModel, "id")
        assert hasattr(TestModel, "created_at")
        assert hasattr(TestModel, "updated_at")

        # 检查表名
        assert TestModel.__tablename__ == "test_base_model"

        # 检查是否是抽象类
        assert TestModel.__abstract__ is True

    def test_base_model_to_dict(self):
        """测试：基础模型转字典"""

        class TestModel(BaseModel):
            __tablename__ = "test_to_dict"

            name = Column(String(50), nullable=False)
            description = Column(String(200))

        # 创建实例
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        instance = TestModel(
            id=1,
            name="Test Item",
            description="Test Description",
            created_at=test_time,
            updated_at=test_time,
        )

        # 转换为字典
        _result = instance.to_dict()

        # 验证结果
        assert _result["id"] == 1
        assert _result["name"] == "Test Item"
        assert _result["description"] == "Test Description"
        assert _result["created_at"] == "2023-01-01T12:00:00"
        assert _result["updated_at"] == "2023-01-01T12:00:00"

    def test_base_model_to_dict_exclude_fields(self):
        """测试：基础模型转字典（排除字段）"""

        class TestModel(BaseModel):
            __tablename__ = "test_to_dict_exclude"

            name = Column(String(50))
            secret = Column(String(100))

        instance = TestModel(
            id=1,
            name="Test",
            secret="Secret Value",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 排除敏感字段
        _result = instance.to_dict(exclude_fields={"secret"})

        assert "id" in result
        assert "name" in result
        assert "secret" not in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_base_model_from_dict(self):
        """测试：从字典创建基础模型"""

        class TestModel(BaseModel):
            __tablename__ = "test_from_dict"

            name = Column(String(50))
            description = Column(String(200))

        # 准备数据
        _data = {
            "name": "Test Item",
            "description": "Test Description",
            "invalid_field": "should be ignored",
            "id": 999,  # 应该被忽略，因为是自动生成的
        }

        # 从字典创建实例
        instance = TestModel.from_dict(data)

        # 验证
        assert instance.name == "Test Item"
        assert instance.description == "Test Description"
        # id会被设置，因为是从字典传入的
        assert instance.id == 999

    def test_base_model_update_from_dict(self):
        """测试：从字典更新基础模型"""

        class TestModel(BaseModel):
            __tablename__ = "test_update_dict"

            name = Column(String(50))
            description = Column(String(200))

        # 创建实例
        instance = TestModel(name="Original Name", description="Original Description")

        # 更新数据
        update_data = {
            "name": "Updated Name",
            "description": "Updated Description",
            "invalid_field": "should be ignored",
        }

        # 更新
        instance.update_from_dict(update_data)

        # 验证更新
        assert instance.name == "Updated Name"
        assert instance.description == "Updated Description"

    def test_base_model_update_from_dict_exclude_fields(self):
        """测试：从字典更新基础模型（排除字段）"""

        class TestModel(BaseModel):
            __tablename__ = "test_update_exclude"

            name = Column(String(50))
            description = Column(String(200))
            status = Column(String(20))

        instance = TestModel(name="Original", description="Original", status="active")

        # 更新但排除status字段
        instance.update_from_dict(
            {
                "name": "New Name",
                "description": "New Description",
                "status": "inactive",  # 应该被忽略
            },
            exclude_fields={"status"},
        )

        # 验证
        assert instance.name == "New Name"
        assert instance.description == "New Description"
        assert instance.status == "active"  # 未被更新

    def test_base_model_inheritance(self):
        """测试：基础模型继承"""

        # 测试单继承关系
        class TestModel(BaseModel):
            __tablename__ = "test_inheritance"

            name = Column(String(50))

        # 检查继承关系
        assert issubclass(TestModel, BaseModel)
        assert issubclass(TestModel, Base)
        assert issubclass(TimestampMixin, object)

        # 创建实例
        test_instance = TestModel(name="Test")

        # 检查字段
        assert test_instance.name == "Test"
        assert test_instance.id is None
        # 检查时间戳列定义
        columns = TestModel.__table__.columns
        assert "created_at" in columns
        assert "updated_at" in columns
        assert columns["created_at"].default is not None
        assert columns["updated_at"].default is not None

    def test_base_model_with_none_values(self):
        """测试：基础模型处理None值"""

        class TestModel(BaseModel):
            __tablename__ = "test_none_values"

            name = Column(String(50))
            optional_field = Column(String(100))

        # 创建包含None的实例
        instance = TestModel(name="Test", optional_field=None)

        # 转换为字典
        _result = instance.to_dict()

        # None值应该被保留
        assert _result["name"] == "Test"
        assert _result["optional_field"] is None

    def test_base_model_table_info(self):
        """测试：基础模型表信息"""

        class TestModel(BaseModel):
            __tablename__ = "test_table_info"

            __table_args__ = {"comment": "Test table for unit testing"}

            name = Column(String(50), comment="Name field")

        # 检查表信息
        assert TestModel.__tablename__ == "test_table_info"
        assert hasattr(TestModel, "__table__")

        # 检查列信息
        columns = TestModel.__table__.columns
        assert "id" in columns
        assert "name" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
