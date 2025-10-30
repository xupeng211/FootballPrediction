"""
基本测试模板
Basic Test Template

针对模块: events.types
生成时间: 2025-10-30 21:30:40
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
except ImportError as e:
    pytest.skip(f"无法导入模块 {e}")


