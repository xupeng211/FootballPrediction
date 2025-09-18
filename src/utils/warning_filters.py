"""
警告过滤器模块

用于抑制第三方库产生的已知警告，特别是Marshmallow 4兼容性警告。
这些警告来自外部依赖库，不是我们的代码问题，但会干扰测试日志的清洁性。

使用方法：
    在应用启动时调用 setup_warning_filters() 函数
"""

import warnings


def setup_warning_filters() -> None:
    """
    设置项目级别的警告过滤器

    该函数应该在应用程序启动时调用，以确保：
    1. 抑制第三方库的已知兼容性警告
    2. 保持测试日志的清洁性
    3. 确保未来升级的兼容性
    """

    # 抑制 Marshmallow 4 兼容性警告 - 主要来自 Great Expectations
    try:
        import marshmallow.warnings

        warnings.filterwarnings(
            "ignore",
            category=marshmallow.warnings.ChangedInMarshmallow4Warning,
            message=r".*Number.*field should not be instantiated.*",
        )
        print("✅ Marshmallow 4 兼容性警告已抑制")
    except ImportError:
        # 如果无法导入 marshmallow.warnings，使用通用过滤器
        warnings.filterwarnings(
            "ignore", message=r".*Number.*field.*should.*not.*be.*instantiated.*"
        )
        print("⚠️  使用通用方式抑制 Marshmallow 警告")

    # 抑制其他已知的第三方库警告
    _setup_third_party_warning_filters()


def _setup_third_party_warning_filters() -> None:
    """设置第三方库的警告过滤器"""

    # Great Expectations 相关警告
    warnings.filterwarnings(
        "ignore", message=r".*great_expectations.*", category=DeprecationWarning
    )

    # SQLAlchemy 相关警告（如果需要）
    warnings.filterwarnings(
        "ignore", message=r".*sqlalchemy.*", category=DeprecationWarning
    )


def setup_test_warning_filters() -> None:
    """
    为测试环境设置特殊的警告过滤器

    测试环境可能需要更严格的警告控制，
    以确保测试输出的清洁性和一致性。
    """

    # 设置基础警告过滤器
    setup_warning_filters()

    # 测试专用的额外过滤器
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

    # 但保留 UserWarning，它们可能指示测试中的实际问题
    # warnings.filterwarnings("error", category=UserWarning)


def suppress_marshmallow_warnings(func=None):
    """
    装饰器：临时抑制 Marshmallow 警告

    用于特定函数或方法中临时抑制 Marshmallow 相关警告。

    使用示例：
        @suppress_marshmallow_warnings
        def some_function_using_great_expectations():
            # 这里的 Great Expectations 代码不会产生 Marshmallow 警告
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            with warnings.catch_warnings():
                try:
                    import marshmallow.warnings

                    warnings.filterwarnings(
                        "ignore",
                        category=marshmallow.warnings.ChangedInMarshmallow4Warning,
                    )
                except ImportError:
                    warnings.filterwarnings(
                        "ignore",
                        message=r".*Number.*field.*should.*not.*be.*instantiated.*",
                    )

                return func(*args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


# 自动设置警告过滤器（当模块被导入时）
def _auto_setup() -> None:
    """当模块导入时自动设置警告过滤器"""
    try:
        setup_warning_filters()
    except Exception as e:
        # 如果自动设置失败，不要影响应用启动
        print(f"⚠️  警告过滤器自动设置失败: {e}")


# 只在非测试环境下自动设置
import sys  # noqa: E402

if "pytest" not in sys.modules:
    _auto_setup()
