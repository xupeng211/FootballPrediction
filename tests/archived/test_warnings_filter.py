"""
import warnings
from warnings import Warning

测试警告过滤器
"""

import warnings
import os
import sys


def configure_test_warnings():
    """配置测试期间的警告过滤器"""

    # 过滤 MonkeyPatchWarning (来自 locust/gevent)
    warnings.filterwarnings(
        "ignore",
        category=MonkeyPatchWarning,
        message=".*Monkey-patching ssl after ssl has already been imported.*",
    )

    # 过滤 DeprecationWarning
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*直接从 error_handler 导入已弃用.*",
    )

    # 过滤 RuntimeWarning 来自 optional.py
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        message=".*导入.*时发生意外错误.*",
        module=r"src\.dependencies\.optional",
    )

    # 设置环境变量
    os.environ["GEVENT_SUPPRESS_RAGWARN"] = "1"

    # 在 Python 3.7+ 上过滤 ssl 警告
    if sys.version_info >= (3, 7):
        warnings.filterwarnings(
            "ignore", category=ResourceWarning, message=".*unclosed.*"
        )


# 在导入时自动配置
configure_test_warnings()
