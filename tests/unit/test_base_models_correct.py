#!/usr/bin/env python3
"""
基础模型测试
测试 src.models.base_models 模块的功能
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.models.base_models import (
    FootballBaseModel,
    IdentifiableModel,
    MetadataModel,
    StatusModel,
    TimestampedModel,
)


@pytest.mark.unit
class TestFootballBaseModel:
    """足球基础模型测试"""

    def test_football_base_model_creation_empty(self):
        """测试空参数创建足球基础模型"""
        model = FootballBaseModel()

        # 验证默认值
        assert model.id is None
        assert model.created_at is None
        assert model.updated_at is None

    def test_football_base_model_creation_with_data(self):
        """测试带数据创建足球基础模型"""
        now = datetime.now()
        model = FootballBaseModel(id=123, created_at=now, updated_at=now)

        assert model.id == 123
        assert model.created_at == now
        assert model.updated_at == now

    def test_football_base_model_partial_data(self):
        """测试部分数据创建足球基础模型"""
        model = FootballBaseModel(id=456)

        assert model.id == 456
        assert model.created_at is None
        assert model.updated_at is None

    def test_football_base_model_dict_conversion(self):
        """测试足球基础模型字典转换"""
        now = datetime.now()
        model = FootballBaseModel(id=789, created_at=now, updated_at=now)

        result = model.model_dump()

        expected = {"id": 789, "created_at": now, "updated_at": now}
        assert result == expected

    def test_football_base_model_json_serialization(self):
        """测试足球基础模型JSON序列化"""
        model = FootballBaseModel(id=999)

        json_str = model.model_dump_json()
        assert "id" in json_str
        assert "999" in json_str


@pytest.mark.unit
class TestTimestampedModel:
    """时间戳模型测试"""

    @patch("src.models.base_models.datetime")
    def test_timestamped_model_creation(self, mock_datetime):
        """测试时间戳模型创建"""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time

        model = TimestampedModel()

        assert model.created_at == fixed_time
        assert model.updated_at == fixed_time
        assert model.created_at == model.updated_at

    def test_timestamped_model_custom_timestamps(self):
        """测试自定义时间戳的时间戳模型"""
        created = datetime(2024, 1, 1, 10, 0, 0)
        updated = datetime(2024, 1, 1, 12, 0, 0)

        model = TimestampedModel(created_at=created, updated_at=updated)

        assert model.created_at == created
        assert model.updated_at == updated
        assert model.created_at != model.updated_at

    def test_timestamped_model_validation(self):
        """测试时间戳模型验证"""
        # 测试有效的时间戳
        valid_time = datetime.now()
        model = TimestampedModel(created_at=valid_time, updated_at=valid_time)

        assert model.created_at == valid_time
        assert model.updated_at == valid_time


@pytest.mark.unit
class TestIdentifiableModel:
    """可识别模型测试"""

    def test_identifiable_model_creation_minimal(self):
        """测试最小参数创建可识别模型"""
        model = IdentifiableModel(id=1, name="Test Model")

        assert model.id == 1
        assert model.name == "Test Model"
        assert model.description is None

    def test_identifiable_model_creation_full(self):
        """测试完整参数创建可识别模型"""
        model = IdentifiableModel(
            id=999, name="Full Model", description="This is a full model description"
        )

        assert model.id == 999
        assert model.name == "Full Model"
        assert model.description == "This is a full model description"

    def test_identifiable_model_validation(self):
        """测试可识别模型验证"""
        # 测试必需字段
        model = IdentifiableModel(id=123, name="Required Name")

        assert model.id == 123
        assert model.name == "Required Name"

    def test_identifiable_model_types(self):
        """测试可识别模型类型"""
        model = IdentifiableModel(id=42, name="Type Test", description=123)

        assert isinstance(model.id, int)
        assert isinstance(model.name, str)
        # description可以是各种类型，这里测试数字
        assert model.description == 123


@pytest.mark.unit
class TestStatusModel:
    """状态模型测试"""

    def test_status_model_creation_default(self):
        """测试默认状态创建状态模型"""
        model = StatusModel()

        assert model.status == "active"
        assert model.is_enabled is True

    def test_status_model_creation_custom(self):
        """测试自定义状态创建状态模型"""
        model = StatusModel(status="inactive", is_enabled=False)

        assert model.status == "inactive"
        assert model.is_enabled is False

    def test_status_model_different_statuses(self):
        """测试不同状态的状态模型"""
        statuses = ["active", "inactive", "pending", "suspended", "deleted"]

        for status in statuses:
            model = StatusModel(status=status)
            assert model.status == status
            assert model.is_enabled is True  # 默认值

    def test_status_model_boolean_values(self):
        """测试布尔值的状态模型"""
        # 测试不同的enabled状态
        enabled_model = StatusModel(is_enabled=True)
        disabled_model = StatusModel(is_enabled=False)

        assert enabled_model.is_enabled is True
        assert disabled_model.is_enabled is False
        assert enabled_model.status == "active"  # 默认值
        assert disabled_model.status == "active"  # 默认值


@pytest.mark.unit
class TestMetadataModel:
    """元数据模型测试"""

    def test_metadata_model_creation_default(self):
        """测试默认元数据创建元数据模型"""
        model = MetadataModel()

        assert model.metadata == {}
        assert model.tags == []

    def test_metadata_model_creation_with_data(self):
        """测试带数据创建元数据模型"""
        metadata_data = {"key1": "value1", "key2": 42}
        tags_list = ["tag1", "tag2", "tag3"]

        model = MetadataModel(metadata=metadata_data, tags=tags_list)

        assert model.metadata == metadata_data
        assert model.tags == tags_list

    def test_metadata_model_empty_collections(self):
        """测试空集合的元数据模型"""
        model = MetadataModel(metadata={}, tags=[])

        assert model.metadata == {}
        assert model.tags == []

    def test_metadata_model_complex_data(self):
        """测试复杂数据的元数据模型"""
        complex_metadata = {
            "config": {
                "setting1": True,
                "setting2": "value",
                "nested": {"deep": "value"},
            },
            "numbers": [1, 2, 3, 4, 5],
        }
        complex_tags = ["system:core", "user-generated", "production"]

        model = MetadataModel(metadata=complex_metadata, tags=complex_tags)

        assert model.metadata == complex_metadata
        assert model.tags == complex_tags
        assert model.metadata["config"]["nested"]["deep"] == "value"
        assert 3 in model.metadata["numbers"]

    def test_metadata_model_mutation(self):
        """测试元数据模型修改"""
        model = MetadataModel()

        # 添加元数据
        model.metadata["new_key"] = "new_value"
        model.tags.append("new_tag")

        assert model.metadata["new_key"] == "new_value"
        assert "new_tag" in model.tags
        assert len(model.tags) == 1

    def test_metadata_model_type_validation(self):
        """测试元数据模型类型验证"""
        # metadata应该是字典
        model = MetadataModel(metadata={"key": "value"})
        assert isinstance(model.metadata, dict)

        # tags应该是列表
        model = MetadataModel(tags=["tag1", "tag2"])
        assert isinstance(model.tags, list)
