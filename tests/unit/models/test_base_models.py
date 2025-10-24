"""
基础模型测试
Base Models Tests

测试src/models/base_models.py中定义的基础模型功能。
Tests base model functionality defined in src/models/base_models.py.
"""

import pytest
import datetime
from typing import Any, Dict, List
from pydantic import ValidationError

# 导入要测试的模块
try:
    from src.models.base_models import (
        BaseModel,
        TimestampedModel,
        IdentifiableModel,
        StatusModel,
        MetadataModel,
        base_models,
    )
    BASE_MODELS_AVAILABLE = True
except ImportError:
    BASE_MODELS_AVAILABLE = False


@pytest.mark.skipif(not BASE_MODELS_AVAILABLE, reason="Base models module not available")
class TestBaseModel:
    """BaseModel测试"""

    def test_base_model_class_exists(self):
        """测试BaseModel类存在"""
        assert BaseModel is not None
        assert callable(BaseModel)

    def test_base_model_instantiation_empty(self):
        """测试空BaseModel实例化"""
        model = BaseModel()
        assert model.id is None
        assert model.created_at is None
        assert model.updated_at is None

    def test_base_model_instantiation_with_data(self):
        """测试带数据的BaseModel实例化"""
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        model = BaseModel(id=1, created_at=custom_time, updated_at=custom_time)
        assert model.id == 1
        assert model.created_at == custom_time
        assert model.updated_at == custom_time

    def test_base_model_with_optional_fields(self):
        """测试BaseModel可选字段"""
        # 测试只提供部分字段
        model = BaseModel(id=42)
        assert model.id == 42
        assert model.created_at is None
        assert model.updated_at is None

        # 修复：使用日期对象，Pydantic会自动转换为datetime
        custom_date = datetime.date(2023, 1, 1)
        model = BaseModel(created_at=custom_date)
        assert model.id is None
        # Pydantic自动将date转换为datetime
        assert model.created_at == datetime.datetime(2023, 1, 1, 0, 0, 0)
        assert model.updated_at is None

    def test_base_model_serialization(self):
        """测试BaseModel序列化"""
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        model = BaseModel(id=1, created_at=custom_time)
        data = model.model_dump()

        assert data["id"] == 1
        assert data["created_at"] == custom_time
        assert "updated_at" in data

    def test_base_model_deserialization(self):
        """测试BaseModel反序列化"""
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        data = {"id": 1, "created_at": custom_time, "updated_at": custom_time}
        model = BaseModel.model_validate(data)

        assert model.id == 1
        assert model.created_at == custom_time
        assert model.updated_at == custom_time

    def test_base_model_json_serialization(self):
        """测试BaseModel JSON序列化"""
        model = BaseModel(id=1)
        json_str = model.model_dump_json()

        assert "id" in json_str
        # 修复：JSON序列化可能不包含空格，检查更简单的模式
        assert '"id":1' in json_str or '"id": 1' in json_str

    def test_base_model_from_attributes(self):
        """测试BaseModel从属性创建"""
        # 创建一个字典，然后从属性创建模型
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        data = {"id": 123, "created_at": custom_time}
        model = BaseModel(**data)

        assert model.id == 123
        assert model.created_at == custom_time

    def test_base_model_config_from_attributes(self):
        """测试BaseModel配置"""
        # 验证from_attributes配置
        config = BaseModel.Config
        assert config.from_attributes is True

    def test_base_model_model_fields(self):
        """测试BaseModel模型字段"""
        fields = BaseModel.model_fields
        expected_fields = {"id", "created_at", "updated_at"}
        assert set(fields.keys()) == expected_fields


@pytest.mark.skipif(not BASE_MODELS_AVAILABLE, reason="Base models module not available")
class TestTimestampedModel:
    """TimestampedModel测试"""

    def test_timestamped_model_class_exists(self):
        """测试TimestampedModel类存在"""
        assert TimestampedModel is not None
        assert callable(TimestampedModel)

    def test_timestamped_model_instantiation(self):
        """测试TimestampedModel实例化"""
        model = TimestampedModel()

        assert isinstance(model.created_at, datetime.datetime)
        assert isinstance(model.updated_at, datetime.datetime)
        assert model.created_at is not None
        assert model.updated_at is not None

    def test_timestamped_model_default_values(self):
        """测试TimestampedModel默认值"""
        model1 = TimestampedModel()
        model2 = TimestampedModel()

        # 每次实例化都应该生成新的时间戳
        assert model1.created_at <= model2.created_at
        assert model1.updated_at <= model2.updated_at

    def test_timestamped_model_custom_timestamps(self):
        """测试TimestampedModel自定义时间戳"""
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        model = TimestampedModel(
            created_at=custom_time,
            updated_at=custom_time
        )

        assert model.created_at == custom_time
        assert model.updated_at == custom_time

    def test_timestamped_model_inheritance(self):
        """测试TimestampedModel继承关系"""
        # 验证TimestampedModel继承自BaseModel
        assert issubclass(TimestampedModel, BaseModel)

        # 测试继承的属性
        model = TimestampedModel(id=1)
        assert model.id == 1  # 来自BaseModel
        assert isinstance(model.created_at, datetime.datetime)

    def test_timestamped_model_serialization(self):
        """测试TimestampedModel序列化"""
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        model = TimestampedModel(
            id=1,
            created_at=custom_time,
            updated_at=custom_time
        )

        data = model.model_dump()
        assert data["id"] == 1
        assert "created_at" in data
        assert "updated_at" in data

    def test_timestamped_model_json_serialization(self):
        """测试TimestampedModel JSON序列化"""
        model = TimestampedModel()
        json_str = model.model_dump_json()

        assert "created_at" in json_str
        assert "updated_at" in json_str


@pytest.mark.skipif(not BASE_MODELS_AVAILABLE, reason="Base models module not available")
class TestIdentifiableModel:
    """IdentifiableModel测试"""

    def test_identifiable_model_class_exists(self):
        """测试IdentifiableModel类存在"""
        assert IdentifiableModel is not None
        assert callable(IdentifiableModel)

    def test_identifiable_model_instantiation(self):
        """测试IdentifiableModel实例化"""
        model = IdentifiableModel(id=1, name="Test Model")

        assert model.id == 1
        assert model.name == "Test Model"
        assert model.description is None

    def test_identifiable_model_with_description(self):
        """测试IdentifiableModel带描述"""
        model = IdentifiableModel(
            id=42,
            name="Test Model",
            description="This is a test model"
        )

        assert model.id == 42
        assert model.name == "Test Model"
        assert model.description == "This is a test model"

    def test_identifiable_model_required_fields(self):
        """测试IdentifiableModel必需字段"""
        # id和name是必需的
        with pytest.raises(ValidationError):
            IdentifiableModel(id=1)  # 缺少name

        with pytest.raises(ValidationError):
            IdentifiableModel(name="Test")  # 缺少id

    def test_identifiable_model_field_types(self):
        """测试IdentifiableModel字段类型"""
        model = IdentifiableModel(id=1, name="Test")

        assert isinstance(model.id, int)
        assert isinstance(model.name, str)
        assert model.description is None or isinstance(model.description, str)

    def test_identifiable_model_inheritance(self):
        """测试IdentifiableModel继承关系"""
        # 验证IdentifiableModel继承自BaseModel
        assert issubclass(IdentifiableModel, BaseModel)

        # 测试继承的属性
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        model = IdentifiableModel(
            id=1,
            name="Test",
            created_at=custom_time
        )

        assert model.id == 1
        assert model.created_at == custom_time

    def test_identifiable_model_serialization(self):
        """测试IdentifiableModel序列化"""
        model = IdentifiableModel(
            id=123,
            name="Test Model",
            description="Test Description"
        )

        data = model.model_dump()
        assert data["id"] == 123
        assert data["name"] == "Test Model"
        assert data["description"] == "Test Description"

    def test_identifiable_model_json_serialization(self):
        """测试IdentifiableModel JSON序列化"""
        model = IdentifiableModel(id=1, name="Test")
        json_str = model.model_dump_json()

        assert "id" in json_str
        assert "name" in json_str


@pytest.mark.skipif(not BASE_MODELS_AVAILABLE, reason="Base models module not available")
class TestStatusModel:
    """StatusModel测试"""

    def test_status_model_class_exists(self):
        """测试StatusModel类存在"""
        assert StatusModel is not None
        assert callable(StatusModel)

    def test_status_model_instantiation(self):
        """测试StatusModel实例化"""
        model = StatusModel()

        assert model.status == "active"
        assert model.is_enabled is True

    def test_status_model_custom_values(self):
        """测试StatusModel自定义值"""
        model = StatusModel(status="inactive", is_enabled=False)

        assert model.status == "inactive"
        assert model.is_enabled is False

    def test_status_model_only_status(self):
        """测试StatusModel只设置status"""
        model = StatusModel(status="pending")

        assert model.status == "pending"
        assert model.is_enabled is True  # 默认值

    def test_status_model_only_is_enabled(self):
        """测试StatusModel只设置is_enabled"""
        model = StatusModel(is_enabled=False)

        assert model.status == "active"  # 默认值
        assert model.is_enabled is False

    def test_status_model_field_types(self):
        """测试StatusModel字段类型"""
        model = StatusModel()

        assert isinstance(model.status, str)
        assert isinstance(model.is_enabled, bool)

    def test_status_model_inheritance(self):
        """测试StatusModel继承关系"""
        assert issubclass(StatusModel, BaseModel)

        # 测试继承的属性
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        model = StatusModel(
            id=1,
            status="active",
            created_at=custom_time
        )

        assert model.id == 1
        assert model.status == "active"
        assert model.created_at == custom_time

    def test_status_model_serialization(self):
        """测试StatusModel序列化"""
        model = StatusModel(
            id=1,
            status="archived",
            is_enabled=False
        )

        data = model.model_dump()
        assert data["id"] == 1
        assert data["status"] == "archived"
        assert data["is_enabled"] is False

    def test_status_model_json_serialization(self):
        """测试StatusModel JSON序列化"""
        model = StatusModel()
        json_str = model.model_dump_json()

        assert "status" in json_str
        assert "is_enabled" in json_str


@pytest.mark.skipif(not BASE_MODELS_AVAILABLE, reason="Base models module not available")
class TestMetadataModel:
    """MetadataModel测试"""

    def test_metadata_model_class_exists(self):
        """测试MetadataModel类存在"""
        assert MetadataModel is not None
        assert callable(MetadataModel)

    def test_metadata_model_instantiation(self):
        """测试MetadataModel实例化"""
        model = MetadataModel()

        assert model.metadata == {}
        assert model.tags == []

    def test_metadata_model_with_data(self):
        """测试MetadataModel带数据实例化"""
        metadata = {"key1": "value1", "key2": 42}
        tags = ["tag1", "tag2", "tag3"]

        model = MetadataModel(metadata=metadata, tags=tags)

        assert model.metadata == metadata
        assert model.tags == tags

    def test_metadata_model_only_metadata(self):
        """测试MetadataModel只设置metadata"""
        metadata = {"version": "1.0", "author": "test"}
        model = MetadataModel(metadata=metadata)

        assert model.metadata == metadata
        assert model.tags == []  # 默认值

    def test_metadata_model_only_tags(self):
        """测试MetadataModel只设置tags"""
        tags = ["production", "api"]
        model = MetadataModel(tags=tags)

        assert model.metadata == {}  # 默认值
        assert model.tags == tags

    def test_metadata_model_field_types(self):
        """测试MetadataModel字段类型"""
        model = MetadataModel()

        assert isinstance(model.metadata, dict)
        assert isinstance(model.tags, list)

    def test_metadata_model_complex_data(self):
        """测试MetadataModel复杂数据"""
        complex_metadata = {
            "config": {
                "debug": True,
                "timeout": 30,
                "servers": ["server1", "server2"]
            },
            "metrics": {
                "enabled": True,
                "interval": 60
            }
        }
        tags = ["web", "api", "monitoring"]

        model = MetadataModel(metadata=complex_metadata, tags=tags)

        assert model.metadata == complex_metadata
        assert model.tags == tags

    def test_metadata_model_inheritance(self):
        """测试MetadataModel继承关系"""
        assert issubclass(MetadataModel, BaseModel)

        # 测试继承的属性
        custom_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        model = MetadataModel(
            id=1,
            metadata={"test": "value"},
            tags=["test"],
            created_at=custom_time
        )

        assert model.id == 1
        assert model.metadata == {"test": "value"}
        assert model.tags == ["test"]
        assert model.created_at == custom_time

    def test_metadata_model_serialization(self):
        """测试MetadataModel序列化"""
        model = MetadataModel(
            id=1,
            metadata={"key": "value"},
            tags=["tag1", "tag2"]
        )

        data = model.model_dump()
        assert data["id"] == 1
        assert data["metadata"] == {"key": "value"}
        assert data["tags"] == ["tag1", "tag2"]

    def test_metadata_model_json_serialization(self):
        """测试MetadataModel JSON序列化"""
        model = MetadataModel()
        json_str = model.model_dump_json()

        assert "metadata" in json_str
        assert "tags" in json_str


@pytest.mark.skipif(not BASE_MODELS_AVAILABLE, reason="Base models module not available")
class TestBaseModelsNamespace:
    """base_models命名空间测试"""

    def test_base_models_namespace_exists(self):
        """测试base_models命名空间存在"""
        assert base_models is not None

    def test_base_models_namespace_content(self):
        """测试base_models命名空间内容"""
        # 验证所有模型都在命名空间中
        assert hasattr(base_models, "BaseModel")
        assert hasattr(base_models, "TimestampedModel")
        assert hasattr(base_models, "IdentifiableModel")
        assert hasattr(base_models, "StatusModel")
        assert hasattr(base_models, "MetadataModel")

    def test_base_models_namespace_access(self):
        """测试base_models命名空间访问"""
        # 验证可以通过命名空间访问所有模型
        assert base_models.BaseModel is BaseModel
        assert base_models.TimestampedModel is TimestampedModel
        assert base_models.IdentifiableModel is IdentifiableModel
        assert base_models.StatusModel is StatusModel
        assert base_models.MetadataModel is MetadataModel

    def test_base_models_namespace_instantiation(self):
        """测试通过命名空间实例化模型"""
        # 通过命名空间创建模型实例
        model1 = base_models.BaseModel(id=1)
        model2 = base_models.IdentifiableModel(id=1, name="Test")
        model3 = base_models.StatusModel(status="active")

        assert model1.id == 1
        assert model2.id == 1 and model2.name == "Test"
        assert model3.status == "active"

    def test_all_models_inherit_base_model(self):
        """测试所有模型都继承自BaseModel"""
        models = [
            TimestampedModel,
            IdentifiableModel,
            StatusModel,
            MetadataModel
        ]

        for model_class in models:
            assert issubclass(model_class, BaseModel), f"{model_class.__name__} should inherit from BaseModel"


@pytest.mark.skipif(not BASE_MODELS_AVAILABLE, reason="Base models module not available")
class TestBaseModelsIntegration:
    """基础模型集成测试"""

    def test_combined_model_inheritance(self):
        """测试组合模型继承"""
        # 创建一个组合多个基础模型的类
        class CombinedModel(TimestampedModel, IdentifiableModel, StatusModel, MetadataModel):
            pass

        model = CombinedModel(
            id=1,
            name="Combined Model",
            metadata={"type": "test"},
            tags=["test"]
        )

        # 验证所有属性都存在
        assert model.id == 1
        assert model.name == "Combined Model"
        assert model.status == "active"  # StatusModel默认值
        assert model.metadata == {"type": "test"}
        assert model.tags == ["test"]
        assert isinstance(model.created_at, datetime.datetime)
        assert isinstance(model.updated_at, datetime.datetime)

    def test_model_workflow(self):
        """测试完整的工作流"""
        # 1. 创建一个组合所有基础模型的类用于工作流测试
        class WorkflowModel(TimestampedModel, IdentifiableModel, StatusModel, MetadataModel):
            """工作流测试用的组合模型"""
            pass

        model_data = {
            "id": 42,  # 直接在数据中设置ID
            "name": "Test Entity",
            "description": "A test entity for validation",
            "status": "processing",
            "is_enabled": True,
            "metadata": {
                "source": "test",
                "version": "1.0",
                "environment": "development"
            },
            "tags": ["test", "validation", "demo"]
        }

        model = WorkflowModel(**model_data)

        # 2. 验证模型创建成功
        assert model.id == 42
        assert model.name == "Test Entity"
        assert model.status == "processing"
        assert model.is_enabled is True
        assert len(model.tags) == 3
        assert model.metadata["version"] == "1.0"
        assert isinstance(model.created_at, datetime.datetime)

        # 3. 序列化和反序列化
        serialized = model.model_dump()
        deserialized = WorkflowModel.model_validate(serialized)

        assert deserialized.id == 42
        assert deserialized.name == "Test Entity"

        # 4. 更新状态
        model.status = "completed"
        model.is_enabled = False
        model.tags.append("done")

        assert model.status == "completed"
        assert model.is_enabled is False
        assert "done" in model.tags

    def test_edge_cases_validation(self):
        """测试边界情况验证"""
        # 测试空字符串
        model = IdentifiableModel(id=1, name="")
        assert model.name == ""

        # 测试空列表和字典
        model = MetadataModel(metadata={}, tags=[])
        assert model.metadata == {}
        assert model.tags == []

        # 测试布尔值边界
        model = StatusModel(is_enabled=False)
        assert model.is_enabled is False
        model.is_enabled = True
        assert model.is_enabled is True

    def test_model_consistency(self):
        """测试模型一致性"""
        # 创建多个相同类型的模型
        models = [
            BaseModel() for _ in range(5)
        ]

        # 验证它们都有相同的结构
        for model in models:
            assert hasattr(model, 'id')
            assert hasattr(model, 'created_at')
            assert hasattr(model, 'updated_at')

        # 验证每个实例都是独立的
        models[0].id = 1
        models[1].id = 2

        assert models[0].id != models[1].id