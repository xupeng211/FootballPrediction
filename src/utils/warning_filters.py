"""
警告过滤器设置
Warning Filters Setup
"""

import warnings
import sys

def setup_warning_filters():
    """设置警告过滤器"""
    # 忽略一些常见的警告
    warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="sklearn.*")
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas.*")
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

# 只在非测试环境下自动设置
if "pytest" not in sys.modules:
    try:
        setup_warning_filters()
    except Exception as e:
        # 如果自动设置失败，不要影响应用启动
        print(f"⚠️  警告过滤器自动设置失败: {e}")
