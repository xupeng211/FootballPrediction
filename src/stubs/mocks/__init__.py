from typing import Any, Dict, List, Optional, Union
"""
Mock模块用于测试
为缺失的外部依赖提供mock实现
"""

from . import confluent_kafka
from . import feast

__all__ = ["confluent_kafka", "feast"]
