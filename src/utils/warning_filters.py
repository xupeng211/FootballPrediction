"""
警告过滤器设置
Warning Filters Setup
"""

import logging
import sys
import warnings

logger = logging.getLogger(__name__)


def setup_warning_filters():
    """设置警告过滤器"""
    try:
        # 忽略一些常见的警告
        warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow.*")
        warnings.filterwarnings(
            "ignore", category=DeprecationWarning, module="sklearn.*"
        )
        warnings.filterwarnings("ignore", category=FutureWarning, module="pandas.*")
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        # 如果设置失败,记录日志但不抛出异常
        logger.info(f"⚠️  警告过滤器设置失败: {e}")

    # 返回None以明确表示无返回值
    return None


# 只在非测试环境下自动设置
if "pytest" not in sys.modules:
    try:
        setup_warning_filters()
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        # 如果自动设置失败,不要影响应用启动
        logger.info(f"⚠️  警告过滤器自动设置失败: {e}")
