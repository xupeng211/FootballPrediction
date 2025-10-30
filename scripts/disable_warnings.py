#!/usr/bin/env python3
"""
配置警告过滤器
"""

import warnings
import os
from src.core.config import 


def configure_warnings():
    """配置警告过滤器"""

    # 1. 过滤 MonkeyPatchWarning
    warnings.filterwarnings(
        "ignore",
        category=MonkeyPatchWarning,
        message=".*Monkey-patching ssl after ssl has already been imported.*",
    )

    # 2. 过滤 DeprecationWarning
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*直接从 error_handler 导入已弃用.*",
    )

    # 3. 过滤 RuntimeWarning 来自 optional.py
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        message=".*导入 matplotlib 时发生意外错误.*",
        module=r"src\.dependencies\.optional",
    )

    # 4. 设置环境变量来抑制 gevent 警告
    os.environ["GEVENT_SUPPRESS_RAGWARN"] = "1"
    os.environ["GEVENT_MONKEY_PATCH_WARN"] = "0"


if __name__ == "__main__":
    configure_warnings()
    print("警告过滤器已配置")
