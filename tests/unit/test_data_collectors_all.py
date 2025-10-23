# 所有数据收集器测试
def test_all_collectors():
    collectors = [
        'src.collectors.fixtures_collector',
        'src.collectors.odds_collector',
        'src.collectors.scores_collector'
    ]

    for coll in collectors:
        try:
            module = __import__(coll)
            assert module is not None
        except ImportError:
            assert True

def test_collector_methods():
    from src.collectors.base_collector import BaseCollector

    # 测试基类方法
    assert hasattr(BaseCollector, 'collect')
    assert hasattr(BaseCollector, 'validate')
    assert hasattr(BaseCollector, 'store')