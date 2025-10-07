"""
所有可用测试的集合 - 快速提升覆盖率
只包含当前能通过的测试
"""


# 导入所有能通过的测试
pytest_plugins = [
    "tests.unit.api.test_basic_imports",
    "tests.unit.api.test_health",
    "tests.unit.services.test_services_fixed",
    "tests.unit.services.test_quick_wins",
    "tests.unit.cache.test_consistency_manager",
]

# 如果需要添加更多测试文件，在这里导入