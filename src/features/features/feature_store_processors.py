"""
特征处理器
"""

# 导入
import os


# 常量
ENABLE_FEAST = os.getenv("ENABLE_FEAST", "true").lower() == "true"
HAS_FEAST = True
HAS_FEAST = False
INT64 = "INT64"


# 类定义
class _MockFeastResult:
    """轻量的Feast查询结果，仅实现 to_df 方法。"""

    pass  # TODO: 实现类逻辑


class MockEntity:
    pass  # TODO: 实现类逻辑


class MockFeatureView:
    pass  # TODO: 实现类逻辑


class MockField:
    pass  # TODO: 实现类逻辑


class MockFloat64:
    pass  # TODO: 实现类逻辑


class MockInt64:
    pass  # TODO: 实现类逻辑


class MockPostgreSQLSource:
    pass  # TODO: 实现类逻辑


class MockValueType:
    pass  # TODO: 实现类逻辑
