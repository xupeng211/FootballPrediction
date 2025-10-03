import os
"""数据库基础模型测试"""

import pytest
from datetime import datetime
from unittest.mock import Mock
from sqlalchemy import Column, String, Integer

from src.database.base import Base, BaseModel, TimestampMixin


class TestBase:
    """测试SQLAlchemy基础类"""

    def test_base_creation(self):
        """测试基础类创建"""
        # Base应该可以正常创建
        assert Base is not None
        # 验证它是一个DeclarativeBase
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)


class TestTimestampMixin:
    """测试时间戳混入类"""

    def test_timestamp_mixin_columns(self):
        """测试时间戳混入类的列"""
        # 创建一个使用TimestampMixin的测试类
        class TestModel(Base, TimestampMixin):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___30")
            id = Column(Integer, primary_key=True)

        # 验证时间戳列存在
        columns = TestModel.__table__.columns
        assert "created_at" in columns
        assert "updated_at" in columns

        # 验证列属性
        created_at = columns["created_at"]
        updated_at = columns["updated_at"]

        assert created_at.nullable is False
        assert updated_at.nullable is False
        assert created_at.comment == "创建时间"
        assert updated_at.comment == "更新时间"


class TestBaseModel:
    """测试基础模型类"""

    def test_base_model_is_abstract(self):
        """测试BaseModel是抽象类"""
        assert BaseModel.__abstract__ is True

    def test_base_model_inherits(self):
        """测试BaseModel的继承关系"""
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(BaseModel, Base)
        assert hasattr(BaseModel, 'created_at')
        assert hasattr(BaseModel, 'updated_at')
        assert hasattr(BaseModel, 'id')

    def test_concrete_model_creation(self):
        """测试创建具体模型"""
        # 创建一个具体的测试模型
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___66")
            name = Column(String(50))
            value = Column(Integer)

        # 验证模型属性
        assert TestModel.__table__ is not None
        assert "id" in TestModel.__table__.columns
        assert "created_at" in TestModel.__table__.columns
        assert "updated_at" in TestModel.__table__.columns
        assert "name" in TestModel.__table__.columns
        assert "value" in TestModel.__table__.columns

    def test_to_dict_basic(self):
        """测试基本字典转换"""
        # 创建一个具体的测试模型
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___82")
            name = Column(String(50))
            value = Column(Integer)

        # 创建实例
        test_time = datetime(2025, 1, 15, 10, 30, 0)
        model = TestModel(
            id=1,
            name="Test",
            value=100,
            created_at=test_time,
            updated_at=test_time
        )

        # 转换为字典
        result = model.to_dict()

        # 验证结果
        assert result["id"] == 1
        assert result["name"] == "Test"
        assert result["value"] == 100
        assert result["created_at"] == test_time.isoformat()
        assert result["updated_at"] == test_time.isoformat()

    def test_to_dict_with_exclude_fields(self):
        """测试排除字段的字典转换"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___108")
            name = Column(String(50))
            secret = Column(String(100))

        model = TestModel(
            id=1,
            name="Test",
            secret = os.getenv("TEST_BASE_SECRET_114"),
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        # 排除secret字段
        result = model.to_dict(exclude_fields={"secret"})

        assert "secret" not in result
        assert result["name"] == "Test"
        assert result["id"] == 1

    def test_to_dict_datetime_conversion(self):
        """测试datetime转换"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___129")
            name = Column(String(50))

        test_time = datetime(2025, 1, 15, 10, 30, 45, 123456)
        model = TestModel(
            id=1,
            name="Test",
            created_at=test_time,
            updated_at=test_time
        )

        result = model.to_dict()

        # datetime应该被转换为ISO格式字符串
        assert result["created_at"] == test_time.isoformat()
        assert result["updated_at"] == test_time.isoformat()

    def test_to_dict_with_none_values(self):
        """测试处理None值"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___149")
            name = Column(String(50))
            optional_field = Column(String(50))

        model = TestModel(
            id=1,
            name="Test",
            optional_field=None,
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        result = model.to_dict()

        assert result["optional_field"] is None

    def test_from_dict(self):
        """测试从字典创建模型"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___166")
            name = Column(String(50))
            value = Column(Integer)

        data = {
            "name": "From Dict",
            "value": 200,
            "created_at": datetime(2025, 1, 15, 10, 30, 0).isoformat(),
            "updated_at": datetime(2025, 1, 15, 10, 30, 0).isoformat()
        }

        model = TestModel.from_dict(data)

        # 注意：from_dict方法应该过滤掉不存在的字段
        # datetime字段会被作为字符串处理，需要模型层面转换
        assert model.name == "From Dict"
        assert model.value == 200

    def test_from_dict_partial_data(self):
        """测试从部分数据创建模型"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___186")
            name = Column(String(50))
            value = Column(Integer)

        data = {"name": "Partial"}

        model = TestModel.from_dict(data)

        assert model.name == "Partial"
        # 没有提供的字段应该使用默认值或None

    def test_update_from_dict(self):
        """测试从字典更新模型"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___200")
            name = Column(String(50))
            value = Column(Integer)

        model = TestModel(
            id=1,
            name = os.getenv("TEST_BASE_NAME_206"),
            value=100,
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        update_data = {"name": "Updated", "value": 200}
        model.update_from_dict(update_data)

        assert model.name == "Updated"
        assert model.value == 200
        # ID不应该被更新
        assert model.id == 1

    def test_update_from_dict_with_exclude_fields(self):
        """测试更新时排除字段"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___221")
            name = Column(String(50))
            value = Column(Integer)

        model = TestModel(
            id=1,
            name = os.getenv("TEST_BASE_NAME_206"),
            value=100,
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        update_data = {"name": "Updated", "id": 999}
        model.update_from_dict(update_data, exclude_fields={"id"})

        assert model.name == "Updated"
        # ID应该保持不变
        assert model.id == 1

    def test_update_from_dict_default_excludes(self):
        """测试默认排除字段"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___242")
            name = Column(String(50))

        model = TestModel(
            id=1,
            name = os.getenv("TEST_BASE_NAME_206"),
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        update_data = {"id": 999, "created_at": datetime(2026, 1, 1, 0, 0, 0)}
        model.update_from_dict(update_data)

        # ID和created_at应该保持不变（默认排除）
        assert model.id == 1
        assert model.created_at == datetime(2025, 1, 15, 10, 30, 0)

    def test_update_from_dict_invalid_fields(self):
        """测试更新无效字段"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___262")
            name = Column(String(50))

        model = TestModel(
            id=1,
            name = os.getenv("TEST_BASE_NAME_206"),
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        # 无效字段应该被忽略
        update_data = {"name": "Updated", "invalid_field": "value"}
        model.update_from_dict(update_data)

        assert model.name == "Updated"
        # 不应该有invalid_field属性
        assert not hasattr(model, 'invalid_field')

    def test_repr(self):
        """测试字符串表示"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___282")
            name = Column(String(50))

        model = TestModel(id=1, name="Test")

        repr_str = repr(model)
        assert "TestModel" in repr_str
        assert "id=1" in repr_str

    def test_repr_without_id(self):
        """测试没有ID时的字符串表示"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___292")
            name = Column(String(50))

        model = TestModel(name="Test")

        repr_str = repr(model)
        assert "TestModel" in repr_str
        assert "id=None" in repr_str


class TestBaseModelEdgeCases:
    """测试BaseModel的边界情况"""

    def test_to_dict_all_fields_excluded(self):
        """测试排除所有字段"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___305")
            name = Column(String(50))

        model = TestModel(
            id=1,
            name="Test",
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        # 排除所有字段
        result = model.to_dict(exclude_fields={"id", "name", "created_at", "updated_at"})

        # 结果应该是空字典
        assert result == {}

    def test_from_dict_empty_dict(self):
        """测试从空字典创建"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___326")
            name = Column(String(50))

        model = TestModel.from_dict({})

        assert model is not None
        # 所有字段应该是默认值或None

    def test_update_from_dict_empty_dict(self):
        """测试用空字典更新"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___336")
            name = Column(String(50))

        original_name = os.getenv("TEST_BASE_ORIGINAL_NAME_339")
        model = TestModel(
            id=1,
            name=original_name,
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        model.update_from_dict({})

        # 什么都不应该改变
        assert model.name == original_name

    def test_to_dict_with_special_characters(self):
        """测试处理特殊字符"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___353")
            text = Column(String(100))

        special_text = os.getenv("TEST_BASE_SPECIAL_TEXT_356")
        model = TestModel(
            id=1,
            text=special_text,
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            updated_at=datetime(2025, 1, 15, 10, 30, 0)
        )

        result = model.to_dict()

        assert result["text"] == special_text

    def test_datetime_microseconds(self):
        """测试datetime微秒精度"""
        class TestModel(BaseModel):
            __tablename__ = os.getenv("TEST_BASE___TABLENAME___370")
            name = Column(String(50))

        precise_time = datetime(2025, 1, 15, 10, 30, 45, 123456)
        model = TestModel(
            id=1,
            name="Test",
            created_at=precise_time,
            updated_at=precise_time
        )

        result = model.to_dict()

        # 微秒应该被保留
        assert "123456" in result["created_at"]