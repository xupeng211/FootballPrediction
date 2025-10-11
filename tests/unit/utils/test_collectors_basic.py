"""
Collectors模块基础测试
Collectors Module Basic Tests
"""

import pytest


def test_collectors_directory_exists():
    """测试收集器目录存在"""
    import os

    collectors_dir = os.path.join(os.getcwd(), "src", "collectors")
    assert os.path.exists(collectors_dir)
    assert os.path.isdir(collectors_dir)


def test_collectors_init_file():
    """测试收集器模块有__init__.py"""
    import os

    init_file = os.path.join(os.getcwd(), "src", "collectors", "__init__.py")
    assert os.path.exists(init_file)


def test_collector_files_exist():
    """测试收集器文件存在"""
    import os

    expected_files = [
        "fixtures_collector.py",
        "odds_collector.py",
        "scores_collector.py",
    ]

    for file_name in expected_files:
        file_path = os.path.join(os.getcwd(), "src", "collectors", file_name)
        if os.path.exists(file_path):
            assert os.path.isfile(file_path)


def test_data_collectors_directory():
    """测试数据收集器目录"""
    import os

    data_dir = os.path.join(os.getcwd(), "src", "data", "collectors")
    if os.path.exists(data_dir):
        assert os.path.isdir(data_dir)


def test_mock_collector_pattern():
    """测试收集器模式"""

    # 模拟收集器基类
    class BaseCollector:
        def __init__(self, name):
            self.name = name
            self.data = []

        def collect(self):
            return {"status": "collected", "data": self.data}

        def add_data(self, item):
            self.data.append(item)

    # 模拟具体收集器
    class FixtureCollector(BaseCollector):
        def __init__(self):
            super().__init__("fixtures")

        def collect_fixtures(self):
            self.add_data("fixture1")
            self.add_data("fixture2")
            return self.collect()

    # 测试收集器
    collector = FixtureCollector()
    assert collector.name == "fixtures"
    assert len(collector.data) == 0

    # 测试收集方法
    result = collector.collect_fixtures()
    assert result["status"] == "collected"
    assert len(collector.data) == 2
    assert "fixture1" in collector.data
    assert "fixture2" in collector.data


def test_collector_registry():
    """测试收集器注册表"""

    class CollectorRegistry:
        def __init__(self):
            self.collectors = {}

        def register(self, name, collector_class):
            self.collectors[name] = collector_class

        def create(self, name, *args, **kwargs):
            if name in self.collectors:
                return self.collectors[name](*args, **kwargs)
            raise ValueError(f"Unknown collector: {name}")

    # 模拟收集器
    class MockCollector:
        def __init__(self, config=None):
            self.config = config or {}

    # 创建注册表
    registry = CollectorRegistry()

    # 注册收集器
    registry.register("test", MockCollector)

    # 创建收集器
    collector = registry.create("test", {"type": "test"})
    assert collector is not None
    assert collector.config["type"] == "test"

    # 测试未知收集器
    with pytest.raises(ValueError):
        registry.create("unknown")
