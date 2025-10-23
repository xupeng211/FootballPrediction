# 特征实体测试
from src.features.entities import FeatureEntity

def test_feature_entity():
    entity = FeatureEntity(entity_id="test", entity_type="team")
    assert entity.entity_id == "test"
    assert entity.entity_type == "team"