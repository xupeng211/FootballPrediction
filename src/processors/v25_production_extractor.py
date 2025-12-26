#!/usr/bin/env python3
"""
V25.1 万能自适应特征提取器
==========================

架构级改进：从硬编码映射转向全量自适应吞噬

设计原则:
    - 零硬编码：自动发现并提取所有数值型特征
    - 递归打平：处理任意深度的嵌套 JSON 结构
    - 动态类型发现：自动转换 int/float/百分比/布尔值
    - 特征对齐：NaN 填充确保特征矩阵一致性
    - 命名规范：路径式命名保证唯一性和可读性

核心能力:
    - 递归打平算法：将嵌套 JSON 转换为扁平特征
    - 全量吞噬：提取 JSON 中所有数值因子
    - 零数据损耗：无论联赛/赛季，最大化特征利用

Author: Architecture Team
Version: V25.1 (Adaptive Universal Extractor)
Date: 2025-12-26
"""

import re
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

import numpy as np
import structlog

from src.processors.base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ValidationConfig,
    register_extractor,
)
from src.processors.exceptions import (
    DataParsingError,
    SchemaMismatchError,
    InsufficientFeaturesError,
    MissingRequiredKeyError,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# 全局特征注册表（用于跨比赛特征对齐）
# ============================================================================

# 全局特征集合：记录所有已见过的特征键
_GLOBAL_FEATURE_KEYS: Set[str] = set()
_GLOBAL_FEATURE_LOCK = False


def get_global_feature_keys() -> Set[str]:
    """获取全局特征键集合"""
    return _GLOBAL_FEATURE_KEYS.copy()


def register_feature_keys(keys: Set[str]) -> None:
    """注册新的特征键到全局集合"""
    global _GLOBAL_FEATURE_KEYS
    _GLOBAL_FEATURE_KEYS.update(keys)


# ============================================================================
# 辅助函数：递归打平与类型转换
# ============================================================================

def _parse_value(value: Any) -> Optional[float]:
    """
    智能解析值，支持多种类型转换

    处理:
    - int/float: 直接返回
    - 百分比字符串: "61%" -> 0.61, "61" -> 61.0
    - 带括号的百分比: "61 (79%)" -> 61.0
    - 布尔值: True -> 1.0, False -> 0.0
    - None/空字符串: -> None

    Args:
        value: 输入值

    Returns:
        转换后的浮点数或 None
    """
    if value is None or value == "" or value == "-":
        return None

    # 布尔值转换
    if isinstance(value, bool):
        return 1.0 if value else 0.0

    # 数字类型直接返回
    if isinstance(value, (int, float)):
        # 检查 NaN
        if isinstance(value, float) and value != value:
            return None
        return float(value)

    if not isinstance(value, str):
        return None

    # 字符串处理
    value = value.strip()

    # 处理百分比: "61%" -> 0.61 (如果值较小，可能是百分比)
    # 或者 "61" 直接保留原值
    # 策略：如果字符串包含 %，先去掉 % 然后按数值处理
    if "%" in value:
        # 提取数字部分
        num_part = value.replace("%", "").strip()
        try:
            num = float(num_part)
            # 如果数字在 0-100 之间，可能是百分比，转换为 0-1
            if 0 <= num <= 100:
                return num / 100.0
            return num
        except ValueError:
            pass

    # 处理 "1.34 (79%)" 格式
    if "(" in value:
        value = value.split("(")[0].strip()

    # 移除所有非数字字符（保留小数点和负号）
    cleaned = re.sub(r'[^\d.\-]', '', value)

    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _sanitize_key(key: str) -> str:
    """
    清理键名，确保是合法的特征名

    - 转换为小写
    - 移除特殊字符
    - 替换空格和连字符为下划线

    Args:
        key: 原始键名

    Returns:
        清理后的键名
    """
    # 转小写
    key = key.lower()
    # 移除特殊字符，只保留字母、数字、下划线、点
    key = re.sub(r'[^\w.]', '_', key)
    # 多个连续下划线替换为单个
    key = re.sub(r'_+', '_', key)
    # 去除首尾下划线
    key = key.strip('_')
    return key


def _fully_flatten(
    data: Any,
    prefix: str = "",
    max_depth: int = 20,
    current_depth: int = 0
) -> Dict[str, Any]:
    """
    递归打平嵌套结构（核心算法）

    将任意深度的嵌套 JSON 转换为单层字典。
    键名采用路径模式，如：content_stats_Periods_All_stats_0_BallPossesion

    Args:
        data: 输入数据（dict, list, 或基本类型）
        prefix: 当前路径前缀
        max_depth: 最大递归深度（防止循环引用）
        current_depth: 当前递归深度

    Returns:
        打平后的字典 {key: parsed_value}
    """
    if current_depth > max_depth:
        logger.warning(f"递归深度超过 {max_depth}，停止打平: {prefix}")
        return {}

    result = {}

    # 处理字典
    if isinstance(data, dict):
        for key, value in data.items():
            # 清理键名
            safe_key = _sanitize_key(str(key))
            # 构造新前缀
            new_prefix = f"{prefix}_{safe_key}" if prefix else safe_key

            # 递归处理
            if isinstance(value, (dict, list)):
                result.update(_fully_flatten(value, new_prefix, max_depth, current_depth + 1))
            else:
                parsed = _parse_value(value)
                if parsed is not None:
                    result[new_prefix] = parsed
                else:
                    # 对于无法解析的字符串，尝试保留
                    if isinstance(value, str) and value:
                        result[new_prefix] = value

    # 处理列表
    elif isinstance(data, list):
        if not data:
            return result

        # 检查列表元素类型
        first_type = type(data[0]) if data else None

        if all(isinstance(x, (int, float)) for x in data):
            # 纯数值列表，计算统计特征
            result[f"{prefix}_mean"] = float(np.mean(data))
            result[f"{prefix}_std"] = float(np.std(data))
            result[f"{prefix}_min"] = float(min(data))
            result[f"{prefix}_max"] = float(max(data))
            result[f"{prefix}_sum"] = float(sum(data))
            result[f"{prefix}_len"] = len(data)
            # 同时保存每个元素
            for i, item in enumerate(data):
                result[f"{prefix}_{i}"] = float(item)

        elif all(isinstance(x, str) for x in data):
            # 纯字符串列表，保存长度和第一个元素
            result[f"{prefix}_len"] = len(data)
            result[f"{prefix}_first"] = data[0] if data else ""

        elif all(isinstance(x, dict) for x in data):
            # 字典列表，递归处理每个元素（使用索引）
            for i, item in enumerate(data):
                new_prefix = f"{prefix}_{i}"
                result.update(_fully_flatten(item, new_prefix, max_depth, current_depth + 1))

        else:
            # 混合类型列表，简单索引
            for i, item in enumerate(data):
                new_prefix = f"{prefix}_{i}"
                if isinstance(item, (dict, list)):
                    result.update(_fully_flatten(item, new_prefix, max_depth, current_depth + 1))
                else:
                    parsed = _parse_value(item)
                    if parsed is not None:
                        result[new_prefix] = parsed

    else:
        # 基本类型
        parsed = _parse_value(data)
        if parsed is not None:
            result[prefix] = parsed

    return result


def align_features(
    features: Dict[str, Any],
    reference_keys: Set[str]
) -> Dict[str, Any]:
    """
    特征对齐：填充缺失的特征键

    确保所有比赛的特征键一致，缺失的键填充 0 或 NaN。

    Args:
        features: 当前提取的特征
        reference_keys: 参考键集合（全局所有已见过的特征）

    Returns:
        对齐后的特征字典
    """
    aligned = features.copy()

    for key in reference_keys:
        if key not in aligned:
            # 数值特征填充 0，字符串特征填充空字符串
            aligned[key] = 0.0

    return aligned


# ============================================================================
# V25.1 自适应提取器
# ============================================================================


@dataclass
class V25ExtractionMetrics:
    """V25.1 提取器执行指标"""
    total_features: int = 0
    numeric_features: int = 0
    string_features: int = 0
    nan_count: int = 0
    flatten_depth: int = 0


class V25ProductionExtractor(BaseExtractor):
    """
    V25.1 万能自适应特征提取器

    架构级改进：从硬编码映射转向全量自适应吞噬

    核心能力:
        1. 递归打平：自动处理任意深度嵌套的 JSON 结构
        2. 全量吞噬：提取所有数值型因子，零数据损耗
        3. 动态类型发现：智能转换 int/float/百分比/布尔值
        4. 特征对齐：全局注册表确保跨比赛特征一致性
        5. 鲁棒性优先：容错设计，部分缺失不影响整体提取

    提取策略:
        - 路径式命名：content_stats_Periods_All_stats_0_key
        - 百分比归一化：自动将 "61%" 转换为 0.61
        - 列表统计：纯数值列表自动计算 mean/std/min/max
        - NaN 对齐：自动填充缺失特征为 0
    """

    # 版本标识
    VERSION = "V25.1"

    # 验证配置（降低最小特征要求，因为现在提取更多特征）
    DEFAULT_CONFIG = ValidationConfig(
        min_features=50,      # 降低到 50，允许部分特征缺失
        max_features=20000,   # 提高上限以支持全量提取
        allow_partial=True,
    )

    def __init__(self, validation_config: Optional[ValidationConfig] = None):
        """初始化 V25.1 提取器"""
        super().__init__(validation_config or self.DEFAULT_CONFIG)
        self._metrics = V25ExtractionMetrics()

    @property
    def version(self) -> str:
        """返回版本号"""
        return self.VERSION

    def pre_process(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """预处理原始数据 - 处理 l2_json 嵌套结构"""
        self._logger.debug("开始预处理", version=self.version)

        if not raw_data:
            raise DataParsingError(
                "原始数据为空",
                raw_data_type=type(raw_data).__name__,
            )

        # 处理 l2_json 嵌套
        if "l2_json" in raw_data:
            self._logger.debug("检测到 l2_json 嵌套结构，进行扁平化")
            raw_data = self._flatten_l2_json(raw_data)

        return raw_data

    def _flatten_l2_json(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """扁平化 l2_json 嵌套结构"""
        l2_content = raw_data.get("l2_json")

        if isinstance(l2_content, str):
            try:
                import json
                l2_content = json.loads(l2_content)
            except json.JSONDecodeError as e:
                raise DataParsingError(
                    "l2_json 字符串解析失败",
                    parse_error=str(e),
                )

        if isinstance(l2_content, dict):
            # 合并到主数据
            merged = {**raw_data, **l2_content}
            merged.pop("l2_json", None)
            return merged

        return raw_data

    def extract(self, raw_data: Dict[str, Any]) -> ExtractionResult:
        """
        全量自适应特征提取（核心方法）

        策略：
        1. 递归打平整个 JSON 结构
        2. 自动类型转换和值提取
        3. 全局特征对齐（填充缺失特征）
        4. 动态计算统计特征
        """
        self._logger.info("开始全量特征提取", version=self.version)

        self._metrics = V25ExtractionMetrics()
        features: Dict[str, Any] = {}
        warnings: List[str] = []
        errors: List[str] = []

        try:
            # Step 1: 递归打平整个 JSON
            self._logger.info("步骤 1/4: 递归打平 JSON 结构")
            flattened = _fully_flatten(raw_data, max_depth=25)
            self._metrics.flatten_depth = max(
                len(k.split('_')) for k in flattened.keys()
            ) if flattened else 0

            # Step 2: 分类特征并注册到全局表
            self._logger.info("步骤 2/4: 特征分类与对齐")
            numeric_features = {}
            string_features = {}

            for key, value in flattened.items():
                # 跳过元数据键
                if key.startswith('_'):
                    continue

                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric_features[key] = float(value)
                elif isinstance(value, str):
                    string_features[key] = value
                # 布尔值已在 _parse_value 中转换为 1.0/0.0

            self._metrics.numeric_features = len(numeric_features)
            self._metrics.string_features = len(string_features)

            # Step 3: 全局特征对齐（填充缺失特征）
            global _GLOBAL_FEATURE_KEYS
            reference_keys = get_global_feature_keys()

            if reference_keys:
                # 填充缺失的特征
                for key in reference_keys:
                    if key not in numeric_features:
                        numeric_features[key] = 0.0

            # 注册当前特征到全局表
            register_feature_keys(set(numeric_features.keys()))

            # Step 4: 合并特征
            features.update(numeric_features)
            features.update(string_features)

            # 添加元数据
            features["_meta"] = {
                "extraction_version": self.version,
                "extraction_timestamp": self._get_timestamp(),
                "feature_count": len(features),
                "numeric_count": len(numeric_features),
                "string_count": len(string_features),
                "flatten_depth": self._metrics.flatten_depth,
                "global_registry_size": len(get_global_feature_keys()),
            }

            self._metrics.total_features = len(features)

            # 确定状态
            if self._metrics.total_features >= 100:
                status = ExtractionStatus.SUCCESS
            elif self._metrics.total_features >= 20:
                status = ExtractionStatus.PARTIAL
            else:
                status = ExtractionStatus.FAILED

            self._logger.info(
                "特征提取完成",
                total_features=self._metrics.total_features,
                numeric_features=self._metrics.numeric_features,
                string_features=self._metrics.string_features,
                flatten_depth=self._metrics.flatten_depth,
                global_registry_size=len(get_global_feature_keys()),
                status=status.value,
            )

            return ExtractionResult(
                status=status,
                features=features,
                warnings=warnings,
                errors=errors,
            )

        except Exception as e:
            self._logger.error("特征提取异常", error=str(e), error_type=type(e).__name__)
            raise DataParsingError(
                f"{self.version} 特征提取失败: {e}",
                parse_error=str(e),
            ) from e

    def validate(self, features: Dict[str, Any]) -> bool:
        """
        验证提取的特征

        V25.1 采用宽松验证策略：
        - 只要求特征数量 >= min_features
        - 不强制要求特定键存在
        - 允许部分特征缺失
        """
        feature_count = len(features)

        self._logger.debug(
            "开始验证特征",
            feature_count=feature_count,
            min_required=self._validation_config.min_features,
        )

        # 只检查特征维度下限
        if feature_count < self._validation_config.min_features:
            raise InsufficientFeaturesError(
                f"特征维度不足: {feature_count} < {self._validation_config.min_features}",
                actual_count=feature_count,
                min_required=self._validation_config.min_features,
            )

        # 检查最大限制（警告）
        if (
            self._validation_config.max_features is not None
            and feature_count > self._validation_config.max_features
        ):
            self._logger.warning(
                "特征维度超过上限",
                feature_count=feature_count,
                max_allowed=self._validation_config.max_features,
            )

        self._logger.debug("特征验证通过", feature_count=feature_count)
        return True

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 注册提取器（使用 V25.1 版本号）
register_extractor(V25ProductionExtractor)
