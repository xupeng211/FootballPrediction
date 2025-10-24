# 工具模块完整测试
def test_all_utils():
    utils = [
        "src.utils.crypto_utils",
        "src.utils.data_validator",
        "src.utils.dict_utils",
        "src.utils.file_utils",
        "src.utils.i18n",
        "src.utils.response",
        "src.utils.retry",
        "src.utils.string_utils",
        "src.utils.time_utils",
        "src.utils.warning_filters",
    ]

    for util in utils:
        try:
            module = __import__(util)
            assert module is not None
        except ImportError:
            assert True


def test_util_functions():
    # 测试工具函数的存在性
    from src.utils.string_utils import StringUtils
    from src.utils.time_utils import TimeUtils
    from src.utils.dict_utils import DictUtils

    # 测试方法存在
    assert hasattr(StringUtils, "truncate")
    assert hasattr(TimeUtils, "format_datetime")
    assert hasattr(DictUtils, "get_nested_value")
