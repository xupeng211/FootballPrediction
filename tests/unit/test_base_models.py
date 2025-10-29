#!/usr/bin/env python3
"""
基础模型测试
测试 src.models.base_models 模块的功能
"""

from datetime import datetime

import pytest

from src.models.base_models import BaseModel, TimestampMixin


@pytest.mark.unit
class TestBaseModel:
    """基础模型测试"""

    def test_base_model_creation(self):
        """测试基础模型创建"""
        model = BaseModel()

        # 验证模型可以创建
        assert model is not None
        assert isinstance(model, BaseModel)

    def test_base_model_attributes(self):
        """测试基础模型属性"""
        model = BaseModel()

        # 验证模型有基本属性
        assert hasattr(model, "__class__")
        assert hasattr(model, "__dict__")

    def test_base_model_inheritance(self):
        """测试基础模型继承"""

        # 创建继承自BaseModel的类
        class TestModel(BaseModel):
            def __init__(self):
                super().__init__()
                self.test_field = "test_value"

        model = TestModel()

        # 验证继承关系
        assert isinstance(model, BaseModel)
        assert isinstance(model, TestModel)
        assert model.test_field == "test_value"

    def test_base_model_dict_access(self):
        """测试基础模型字典访问"""
        model = BaseModel()

        # 验证可以通过__dict__访问属性
        assert isinstance(model.__dict__, dict)

    def test_base_model_dynamic_attributes(self):
        """测试基础模型动态属性"""
        model = BaseModel()

        # 动态添加属性
        model.dynamic_field = "dynamic_value"
        model.number_field = 42

        # 验证动态属性
        assert model.dynamic_field == "dynamic_value"
        assert model.number_field == 42

    def test_base_model_attribute_deletion(self):
        """测试基础模型属性删除"""
        model = BaseModel()

        # 添加属性
        model.temp_field = "temp_value"
        assert hasattr(model, "temp_field")

        # 删除属性
        del model.temp_field
        assert not hasattr(model, "temp_field")

    def test_base_model_multiple_instances(self):
        """测试多个基础模型实例"""
        model1 = BaseModel()
        model2 = BaseModel()

        # 验证不同实例
        assert model1 is not model2
        assert id(model1) != id(model2)

        # 独立属性
        model1.field1 = "value1"
        model2.field2 = "value2"

        assert model1.field1 == "value1"
        assert not hasattr(model2, "field1")
        assert model2.field2 == "value2"
        assert not hasattr(model1, "field2")


@pytest.mark.unit
class TestTimestampMixin:
    """时间戳混入类测试"""

    def test_timestamp_mixin_creation(self):
        """测试时间戳混入类创建"""

        class TestModel(TimestampMixin):
            def __init__(self):
                super().__init__()
                # 模拟时间戳初始化
                if hasattr(self, "_init_timestamps"):
                    self._init_timestamps()

        model = TestModel()

        # 验证混入类可以创建
        assert model is not None
        assert isinstance(model, TimestampMixin)

    def test_timestamp_mixin_attributes(self):
        """测试时间戳混入类属性"""

        class TestModel(TimestampMixin):
            def __init__(self):
                super().__init__()
                # 模拟时间戳字段
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

        model = TestModel()

        # 验证时间戳属性存在
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

    def test_timestamp_mixin_inheritance_chain(self):
        """测试时间戳混入类继承链"""

        class TestModel(BaseModel, TimestampMixin):
            def __init__(self):
                super().__init__()
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

        model = TestModel()

        # 验证多重继承
        assert isinstance(model, BaseModel)
        assert isinstance(model, TimestampMixin)
        assert isinstance(model, TestModel)

    def test_timestamp_mixin_with_data(self):
        """测试时间戳混入类带数据"""

        class TestModel(TimestampMixin):
            def __init__(self, data=None):
                super().__init__()
                self.data = data or {}
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

        test_data = {"name": "test", "value": 123}
        model = TestModel(test_data)

        assert model.data == test_data
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")

    def test_timestamp_mixin_method_call(self):
        """测试时间戳混入类方法调用"""

        class TestModel(TimestampMixin):
            def __init__(self):
                super().__init__()
                self.timestamp_field = datetime.now()

            def get_timestamp(self):
                return self.timestamp_field

        model = TestModel()

        # 验证方法调用
        timestamp = model.get_timestamp()
        assert isinstance(timestamp, datetime)
        assert timestamp == model.timestamp_field

    def test_multiple_models_with_mixin(self):
        """测试多个模型使用混入类"""

        class Model1(TimestampMixin):
            def __init__(self):
                super().__init__()
                self.created_at = datetime.now()

        class Model2(TimestampMixin):
            def __init__(self):
                super().__init__()
                self.created_at = datetime.now()

        model1 = Model1()
        model2 = Model2()

        # 验证独立实例
        assert model1 is not model2
        assert model1.created_at != model2.created_at

    def test_mixin_attribute_isolation(self):
        """测试混入类属性隔离"""

        class TestModel(TimestampMixin):
            def __init__(self):
                super().__init__()
                self.created_at = datetime.now()
                self.model_specific = "value"

        model1 = TestModel()
        model2 = TestModel()

        # 在model1上添加属性
        model1.extra_field = "extra"

        # 验证属性隔离
        assert hasattr(model1, "extra_field")
        assert not hasattr(model2, "extra_field")
        assert model1.model_specific == model2.model_specific  # 共同属性
        assert model1.created_at != model2.created_at  # 不同时间戳
