"""
装饰器模式API端点
Decorator Pattern API Endpoints

提供装饰器模式的HTTP接口实现。
Provides HTTP interface implementation for decorator pattern.
"""

from typing import Any

from src.core.config import Config

# mypy: ignore-errors
# 类型检查已忽略 - 这些文件包含复杂的动态类型逻辑