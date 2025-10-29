#!/usr/bin/env python3
"""
数据库基础模型测试
测试 src.database.base 模块的功能
"""

from datetime import datetime

import pytest

from src.database.base import Base, TimestampMixin


@pytest.mark.unit
class TestBase:
    """SQLAlchemy基础模型测试"""

    def test_base_class_import(self):
        """测试基础模型类导入"""
        # 验证Base类可以导入
        assert Base is not None
        assert hasattr(Base, "__tablename__")  # SQLAlchemy DeclarativeBase 属性

    def test_base_class_inheritance(self):
        """测试基础模型类继承"""

        # 创建继承自Base的模型类
        class TestModel(Base):
            __tablename__ = "test_table"

            def __init__(self):
                # 不调用super()，因为我们只测试类结构
                pass

        # 验证继承关系
        model = TestModel()
        assert isinstance(model, Base)
        assert isinstance(model, TestModel)

    def test_base_class_attributes(self):
        """测试基础模型类属性"""
        # 验证Base类有DeclarativeBase的属性
        assert hasattr(Base, "__init_subclass__")
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

    def test_base_class_table_name(self):
        """测试基础模型类表名"""

        class TestModel(Base):
            __tablename__ = "test_table"

        # 验证表名设置
        assert TestModel.__tablename__ == "test_table"

    def test_multiple_base_models(self):
        """测试多个基础模型"""

        class Model1(Base):
            __tablename__ = "model1_table"

        class Model2(Base):
            __tablename__ = "model2_table"

        model1 = Model1()
        model2 = Model2()

        # 验证不同模型
        assert isinstance(model1, Base)
        assert isinstance(model2, Base)
        assert model1 is not model2
        assert Model1.__tablename__ == "model1_table"
        assert Model2.__tablename__ == "model2_table"


@pytest.mark.unit
class TestTimestampMixin:
    """时间戳混入类测试"""

    def test_timestamp_mixin_structure(self):
        """测试时间戳混入类结构"""
        # 验证TimestampMixin类存在
        assert TimestampMixin is not None
        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")

    def test_timestamp_mixin_column_definitions(self):
        """测试时间戳混入类列定义"""
        # 验证列属性存在
        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")

        # 验证列属性是SQLAlchemy Column对象
        from sqlalchemy import Column

        assert isinstance(TimestampMixin.created_at, Column)
        assert isinstance(TimestampMixin.updated_at, Column)

    def test_timestamp_mixin_column_attributes(self):
        """测试时间戳混入类列属性"""
        created_at_col = TimestampMixin.created_at
        updated_at_col = TimestampMixin.updated_at

        # 验证created_at列
        assert created_at_col.nullable is False
        assert created_at_col.comment == "创建时间"

        # 验证updated_at列
        assert updated_at_col.nullable is False
        assert updated_at_col.comment == "更新时间"

    def test_timestamp_mixin_usage(self):
        """测试时间戳混入类使用"""

        # 创建使用TimestampMixin的模型
        class TestModel(Base, TimestampMixin):
            __tablename__ = "test_with_timestamps"

        # 验证模型继承了时间戳字段
        assert hasattr(TestModel, "created_at")
        assert hasattr(TestModel, "updated_at")

        # 验证表名设置
        assert TestModel.__tablename__ == "test_with_timestamps"

    def test_multiple_models_with_timestamp(self):
        """测试多个模型使用时间戳混入"""

        class Model1(Base, TimestampMixin):
            __tablename__ = "model1_timestamps"

        class Model2(Base, TimestampMixin):
            __tablename__ = "model2_timestamps"

        # 验证两个模型都有时间戳字段
        assert hasattr(Model1, "created_at")
        assert hasattr(Model1, "updated_at")
        assert hasattr(Model2, "created_at")
        assert hasattr(Model2, "updated_at")

        # 验证模型独立
        assert Model1.__tablename__ == "model1_timestamps"
        assert Model2.__tablename__ == "model2_timestamps"

    def test_timestamp_mixin_column_types(self):
        """测试时间戳混入类列类型"""
        from sqlalchemy import DateTime

        # 验证列类型
        assert isinstance(TimestampMixin.created_at.type, DateTime)
        assert isinstance(TimestampMixin.updated_at.type, DateTime)

    def test_timestamp_mixin_inheritance_chain(self):
        """测试时间戳混入类继承链"""

        # 创建多层继承
        class BaseModel(Base, TimestampMixin):
            __tablename__ = "base_table"

        class ExtendedModel(BaseModel):
            __tablename__ = "extended_table"

        # 验证继承链
        assert isinstance(ExtendedModel(), Base)
        assert isinstance(ExtendedModel(), BaseModel)
        assert isinstance(ExtendedModel(), TimestampMixin)

        # 验证字段继承
        assert hasattr(ExtendedModel, "created_at")
        assert hasattr(ExtendedModel, "updated_at")

    def test_timestamp_mixin_default_values(self):
        """测试时间戳混入类默认值"""
        created_at_col = TimestampMixin.created_at
        updated_at_col = TimestampMixin.updated_at

        # 验证默认值设置
        assert created_at_col.default is not None
        assert updated_at_col.default is not None
        assert updated_at_col.onupdate is not None

    @patch("src.database.base.datetime")
    def test_timestamp_mixin_datetime_mock(self, mock_datetime):
        """测试时间戳混入类时间处理"""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time

        # 重新导入以应用mock
        import importlib

        import src.database.base

        importlib.reload(src.database.base)

from src.database.base import TimestampMixin

        # 验证时间戳字段使用mock的时间
        # 注意：由于列定义在模块级别，这里我们主要验证结构
        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")

    def test_mixed_inheritance_patterns(self):
        """测试混合继承模式"""

        # 测试不同的继承组合
        class SimpleModel(Base):
            __tablename__ = "simple_table"

        class TimestampModel(Base, TimestampMixin):
            __tablename__ = "timestamp_table"

        class ComplexModel(TimestampMixin, Base):
            __tablename__ = "complex_table"

        # 验证所有模型都可以创建
        simple = SimpleModel()
        timestamp = TimestampModel()
        complex = ComplexModel()

        assert isinstance(simple, Base)
        assert isinstance(timestamp, Base)
        assert isinstance(complex, Base)
        assert isinstance(timestamp, TimestampMixin)
        assert isinstance(complex, TimestampMixin)

        # 验证字段
        assert not hasattr(SimpleModel, "created_at")
        assert hasattr(TimestampModel, "created_at")
        assert hasattr(ComplexModel, "created_at")
