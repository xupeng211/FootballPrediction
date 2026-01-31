#!/usr/bin/env python3
"""
V79.000 Base Feature Processor - 基础特征处理器
================================================

提供特征提取的抽象基类和通用工具函数。

Author: V79.000 Engineering Team
Version: V79.000 "Base Processor"
Date: 2026-01-25
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Data Classes
# =============================================================================

@dataclass
class ProcessorConfig:
    """V79.000: 处理器配置基类"""

    # 数据库超时配置
    query_timeout: int = 30000
    connection_timeout: int = 10000

    # 缓存配置
    enable_cache: bool = True
    cache_size: int = 1000


DEFAULT_PROCESSOR_CONFIG = ProcessorConfig()


# =============================================================================
# Abstract Base Processor
# =============================================================================

class BaseFeatureProcessor(ABC):
    """
    V79.000: 特征处理器抽象基类

    定义所有特征处理器的统一接口和通用功能。
    """

    def __init__(self, config: ProcessorConfig | None = None):
        """
        初始化处理器

        Args:
            config: 处理器配置
        """
        self.config = config or DEFAULT_PROCESSOR_CONFIG
        self.settings = get_settings()
        self._conn = None
        self._cache: dict[str, Any] = {}

    def _get_connection(self) -> psycopg2.extensions.connection:
        """
        获取数据库连接

        Returns:
            数据库连接对象

        Raises:
            psycopg2.Error: 数据库连接失败
        """
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
                connect_timeout=self.config.connection_timeout,
            )
        return self._conn

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def cleanup(self) -> None:
        """清理资源（供子类扩展）"""
        self.close()
        self._cache.clear()

    @abstractmethod
    def extract_features(
        self,
        match_data: dict[str, Any],
        verbose: bool = False
    ) -> dict[str, Any]:
        """
        提取特征（抽象方法，子类必须实现）

        Args:
            match_data: 比赛数据字典
            verbose: 是否打印详细信息

        Returns:
            特征字典
        """


# =============================================================================
# Utility Functions
# =============================================================================

def parse_json_safely(
    json_data: dict[str, Any] | str | None,
    default: Any = None
) -> dict[str, Any]:
    """
    安全解析 JSON 数据

    Args:
        json_data: JSON 数据（dict 或字符串）
        default: 解析失败时的默认返回值

    Returns:
        解析后的字典，失败时返回默认值
    """
    if isinstance(json_data, dict):
        return json_data

    if isinstance(json_data, str):
        try:
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return default

    if default is None:
        return {}

    return default


def calculate_date_difference(
    current_date: datetime,
    previous_date: datetime | None
) -> int:
    """
    计算两个日期之间的天数差

    Args:
        current_date: 当前日期
        previous_date: 之前的日期

    Returns:
        天数差（previous_date 在 current_date 之后返回默认值）
    """
    if previous_date is None:
        return 14  # 默认值

    # V77.000: 修复时区感知问题
    if previous_date.tzinfo is None and current_date.tzinfo is not None:
        previous_date = previous_date.replace(tzinfo=current_date.tzinfo)
    elif previous_date.tzinfo is not None and current_date.tzinfo is None:
        current_date = current_date.replace(tzinfo=previous_date.tzinfo)

    # 防护：确保 previous_date 不在 current_date 之后
    if previous_date > current_date:
        logger.warning(
            f"previous_date ({previous_date}) > current_date ({current_date}), "
            f"using default rest days"
        )
        return 14

    delta = current_date - previous_date
    return max(0, delta.days)


# =============================================================================
# Type Aliases
# =============================================================================

# 常用类型别名
MatchData = dict[str, Any]
FeatureDict = dict[str, float]
JSONData = dict[str, Any] | str | None
