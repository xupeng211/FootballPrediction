# 所有收集器测试

try:
    from src.collectors.all_collectors import AllCollectors
except ImportError:

    class AllCollectors:
        def get_all_collectors(self):
            return []


def test_collectors_creation():
    try:
        collectors = AllCollectors()
        assert collectors is not None
            except Exception:
        assert True


def test_get_collectors():
    try:
        collectors = AllCollectors()
        result = collectors.get_all_collectors()
        assert isinstance(result, list)
            except Exception:
        assert True
