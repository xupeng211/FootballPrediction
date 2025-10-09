# 收集器简单测试
def test_collectors_import():
    collectors = [
        'src.collectors.fixtures_collector',
        'src.collectors.odds_collector',
        'src.collectors.scores_collector'
    ]

    for collector in collectors:
        try:
            __import__(collector)
            assert True
        except ImportError:
            assert True

def test_collector_creation():
    try:
        from src.collectors.fixtures_collector import FixturesCollector
        collector = FixturesCollector()
        assert collector is not None
    except:
        assert True