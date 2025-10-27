# 数据收集器简单测试
import pytest

from src.collectors.fixtures_collector import FixturesCollector
from src.collectors.odds_collector import OddsCollector
from src.collectors.scores_collector import ScoresCollector


@pytest.mark.unit
def test_collector_instances():
    fixtures = FixturesCollector()
    odds = OddsCollector()
    scores = ScoresCollector()

    assert fixtures is not None
    assert odds is not None
    assert scores is not None


def test_collector_configs():
    fixtures = FixturesCollector()
    assert hasattr(fixtures, "config")
    assert hasattr(fixtures, "logger")
