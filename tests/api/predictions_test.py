"""
测试文件: src.api.predictions
使用"working test"方法生成
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def read_module_source():
    """读取模块源代码"""
    with open("src/api/predictions.py", 'r', encoding='utf-8') as f:
        return f.read()

# 获取模块源代码
MODULE_SOURCE = read_module_source()

