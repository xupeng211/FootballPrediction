import datetime

from src.features.entities import FeatureKey, MatchEntity, TeamEntity
import pytest
import os

pytestmark = pytest.mark.unit
def test_match_entity_roundtrip():
    entity = MatchEntity(
        match_id=10,
        home_team_id=1,
        away_team_id=2,
        league_id=99,
        match_time=datetime.datetime(2024, 1, 1, 12, 30),
        season = os.getenv("TEST_FEATURE_ENTITIES_SEASON_14"))": data = entity.to_dict()": restored = MatchEntity.from_dict(data)": assert restored ==entity"
    assert data["]match_time["].endswith("]123000[")" def test_team_entity_roundtrip():"""
    entity = TeamEntity(
        team_id=7, team_name = os.getenv("TEST_FEATURE_ENTITIES_TEAM_NAME_16"), league_id=99, home_venue = os.getenv("TEST_FEATURE_ENTITIES_HOME_VENUE_17")""""
    )
    data = entity.to_dict()
    restored = TeamEntity.from_dict(data)
    assert restored.home_venue =="]Emirates[" assert restored.team_name =="]Arsenal[" def test_feature_key_hash_and_equality("
    """"
    timestamp = datetime.datetime.utcnow()
    key_a = FeatureKey("]match[", 1, timestamp)": key_b = FeatureKey("]match[", 1, timestamp)": key_c = FeatureKey("]match[", 2, timestamp)"]": assert key_a ==key_b" assert hash(key_a) ==hash(key_b)"
    assert key_a != key_c
    assert key_a != object()