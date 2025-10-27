# 特征实体测试
import pytest

from src.features.entities import FeatureEntity


@pytest.mark.unit
def test_feature_entity():
    entity = FeatureEntity(entity_id="test", entity_type="team")
    assert entity.entity_id == "test"
    assert entity.entity_type == "team"
