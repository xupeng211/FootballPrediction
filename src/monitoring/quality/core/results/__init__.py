"""src.monitoring.quality.core.results 模块 - 桩实现"

临时创建的桩模块,用于解决导入错误.
"""

# 桩实现


class DataCompletenessResult:
    """数据完整性结果桩实现"""

    def __init__(self, is_complete: bool = True, message: str = "数据完整性检查通过"):
        self.is_complete = is_complete
        self.message = message


class DataFreshnessResult:
    """数据新鲜度结果桩实现"""

    def __init__(self, is_fresh: bool = True, message: str = "数据新鲜度检查通过"):
        self.is_fresh = is_fresh
        self.message = message
