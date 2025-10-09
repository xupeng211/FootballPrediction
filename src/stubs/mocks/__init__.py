"""
Mock模块用于测试
为缺失的外部依赖提供mock实现
"""

from typing import cast, Any, Optional, Union

from . import confluent_kafka
from . import feast

__all__ = ["confluent_kafka", "feast"]
