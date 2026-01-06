#!/usr/bin/env python3
"""
V26.2 生产级"零缺陷"收割流水线 (Phase 1.3 优化版)
===================================================

V26.2 → V26.1 核心改进 (Phase 1.3 优化)：
    - max_features: 8000 → 6000 (减少 25% 维度)
    - sparsity_threshold: 0.95 → 0.90 (更激进剪枝)
    - 核心特征白名单: 保护滚动特征、赛前特征
    - 目标内存占用减少 40%

V26.1 → V26.0 核心改进：
    - 集成稀疏度过滤器: 自动剔除全零/低方差特征
    - 维度硬限制: 强制控制在 8000 维以内
    - 动态剪枝: 每处理 100 场触发一次特征剪枝
    - 内存安全: 确保 Bulk Insert 不再 OOM

V26.0 排序稳定性保证：
    - 字典列表先按 name/key/id 排序
    - 使用排序后的索引作为特征名后缀
    - 确保不同比赛的特征列（如 shot_1, shot_2）逻辑含义一致

设计原则:
    - 零硬编码：自动发现并提取所有数值型特征
    - 递归打平：处理任意深度的嵌套 JSON 结构
    - 动态类型发现：自动转换 int/float/百分比/布尔值
    - 特征对齐：NaN 填充确保特征矩阵一致性
    - 命名规范：路径式命名保证唯一性和可读性
    - 排序稳定：跨比赛特征语义一致性

Author: Architecture Team
Version: V26.2 (Phase 1.3 Optimization)
Date: 2025-12-28
"""

from dataclasses import dataclass
import re
from typing import Any

import numpy as np
import structlog

from src.processors.base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ValidationConfig,
    register_extractor,
)
from src.processors.exceptions import DataParsingError, InsufficientFeaturesError

logger = structlog.get_logger(__name__)


# ============================================================================
# 全局特征注册表（用于跨比赛特征对齐）
# ============================================================================

# 全局特征集合：记录所有已见过的特征键
_GLOBAL_FEATURE_KEYS: set[str] = set()
_GLOBAL_FEATURE_LOCK = False


def get_global_feature_keys() -> set[str]:
    """获取全局特征键集合"""
    return _GLOBAL_FEATURE_KEYS.copy()


def register_feature_keys(keys: set[str]) -> None:
    """注册新的特征键到全局集合"""
    global _GLOBAL_FEATURE_KEYS
    _GLOBAL_FEATURE_KEYS.update(keys)


# ============================================================================
# V26.0 最小黑名单 (只过滤明显噪音)
# ============================================================================

# V26.0: 最小黑名单 - 只过滤纯文本噪音，保留坐标和结构化数据
FEATURE_BLACKLIST = {
    # 只过滤纯文本噪音
    "commentary",
    "description",
    "headline",
    "summary",
    "template",
    "labeltemplate",
    "defaulttext",
    "textlabelid",
    "texttemplateid",
    "pollname",
    # V26.0: 保留坐标特征 (x, y, shotmap, position, location 等)
    # V26.0: 保留 id, url, image 等作为可能的特征
    # 让模型决定哪些特征有用
}

# 白名单前缀：保留的核心数据路径
FEATURE_WHITELIST_PREFIX = {
    # V25.2: 顶层容器（必须允许进入以访问嵌套数据）
    "content",
    "general",  # FotMob JSON 顶层键
    # 技术统计
    "stats",
    "stat",
    "xg",
    "xa",
    "possession",
    "pass",
    "shot",
    # 战术指标
    "tactical",
    "formation",
    "lineup",
    "player",
    "team",
    # 赔率数据
    "odds",
    "bet",
    "price",
    # 比赛信息
    "match",
    "score",
    "winner",
    "status",
    # 其他核心数据
    "h2h",
    "table",
    "momentum",
    "playerstats",
}


def _should_skip_path(path: str) -> bool:
    """
    V26.0 路径过滤 - 最小过滤策略

    只过滤明显的噪音关键词，保留大部分数据。
    """
    path_lower = path.lower()

    # 只检查明显的噪音关键词
    for blacklist_key in FEATURE_BLACKLIST:
        if blacklist_key in path_lower:
            return True

    return False


def _should_skip_value(key: str, value: Any) -> bool:
    """
    V26.0 值级别检查 - 最小过滤

    只过滤明显的文本噪音，保留所有数值和结构化数据。
    """
    if value is None:
        return False

    key_lower = key.lower()

    # 只检查 V26.0 的最小黑名单
    for blacklist_key in FEATURE_BLACKLIST:
        if blacklist_key in key_lower:
            return True

    # 检查值是否为长文本噪音
    if isinstance(value, str):
        val_lower = value.lower()
        # 长文本描述（超过 100 字符）
        if len(value) > 100:
            if " " in val_lower and ("." in val_lower or "," in val_lower):
                return True

    return False


# ============================================================================
# 辅助函数：递归打平与类型转换
# ============================================================================


def _parse_value(value: Any) -> float | None:
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
    cleaned = re.sub(r"[^\d.\-]", "", value)

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
    key = re.sub(r"[^\w.]", "_", key)
    # 多个连续下划线替换为单个
    key = re.sub(r"_+", "_", key)
    # 去除首尾下划线
    key = key.strip("_")
    return key


def _extract_semantic_key(item: dict[str, Any]) -> str | None:
    """
    从字典中提取语义化键名

    优先级: type > name > key > id > title

    Args:
        item: 字典项

    Returns:
        语义化键名，如果找不到则返回 None
    """
    # 优先级顺序
    priority_keys = ["type", "name", "key", "id", "title", "label"]

    for key in priority_keys:
        if key in item:
            value = item[key]
            if isinstance(value, str) and value:
                # 清理并返回
                return _sanitize_key(value)
            if isinstance(value, (int, float)):
                # 对于数字类型，只在 type 字段时使用
                if key == "type":
                    return f"type_{int(value)}"

    return None


def _fully_flatten(
    data: Any,
    prefix: str = "",
    max_depth: int = 25,  # V26.0: 提高到 25
    current_depth: int = 0,
    list_limit: int = 50,  # V26.0: 提高到 50
) -> dict[str, Any]:
    """
    V26.0 递归打平算法（生产级稳定性版）

    核心改进：
        - max_depth: 15 → 25
        - list_limit: 15 → 50 (对 lineup, shots, events 全量展开)
        - 最小黑名单过滤
        - V26.0 排序稳定性修复：使用排序后的索引作为特征名后缀

    Args:
        data: 输入数据（dict, list, 或基本类型）
        prefix: 当前路径前缀
        max_depth: 最大递归深度
        current_depth: 当前递归深度
        list_limit: 列表展开限制

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
            safe_key = _sanitize_key(str(key))
            new_prefix = f"{prefix}_{safe_key}" if prefix else safe_key

            # V26.0: 路径级别过滤
            if _should_skip_path(new_prefix):
                continue

            # V26.0: 值级别过滤
            if _should_skip_value(safe_key, value):
                continue

            # 递归处理
            if isinstance(value, (dict, list)):
                result.update(_fully_flatten(value, new_prefix, max_depth, current_depth + 1, list_limit))
            else:
                parsed = _parse_value(value)
                if parsed is not None:
                    result[new_prefix] = parsed

    # 处理列表
    elif isinstance(data, list):
        if not data:
            return result

        # V26.0: 动态列表限制
        if any(
            kw in prefix.lower()
            for kw in [
                "lineup",
                "playerstats",
                "substitutions",
                "shots",
                "matches",
                "momentum",
                "events",
                "topplayers",
                "stats",
                "period",
            ]
        ):
            limit = min(list_limit, len(data))
        else:
            limit = min(30, len(data))  # 提高默认限制

        data = data[:limit]

        # 纯数值列表
        if all(isinstance(x, (int, float)) for x in data):
            result[f"{prefix}_mean"] = float(np.mean(data))
            result[f"{prefix}_std"] = float(np.std(data))
            result[f"{prefix}_min"] = float(min(data))
            result[f"{prefix}_max"] = float(max(data))
            result[f"{prefix}_sum"] = float(sum(data))
            result[f"{prefix}_len"] = len(data)

        # 纯字符串列表
        elif all(isinstance(x, str) for x in data):
            result[f"{prefix}_len"] = len(data)

        # 字典列表 - V26.0 排序稳定性修复
        elif all(isinstance(x, dict) for x in data):
            # V26.0: 排序稳定性 - 按 name/key/id 排序
            def _sort_key(item: dict) -> tuple:
                """排序键函数，确保跨比赛特征对齐"""
                for key in ["name", "key", "id", "type"]:
                    if key in item:
                        val = item[key]
                        if isinstance(val, str):
                            return (0, val.lower())
                        if isinstance(val, (int, float)):
                            return (1, val)
                return (2, "")

            sorted_data = sorted(data, key=_sort_key)

            # V26.0: 排序稳定性修复 - 使用排序后的索引 i 作为特征名后缀
            used_keys = {}
            for i, item in enumerate(sorted_data):
                semantic_key = _extract_semantic_key(item)

                if semantic_key:
                    base_key = semantic_key
                    if base_key in used_keys:
                        suffix = used_keys[base_key]
                        unique_key = f"{base_key}_{suffix}"
                        used_keys[base_key] = suffix + 1
                    else:
                        unique_key = base_key
                        used_keys[base_key] = 1
                    new_prefix = f"{prefix}_{unique_key}"
                else:
                    # V26.0 修复：使用排序后的索引 i（而非原始索引）
                    # 这样确保不同比赛的特征列逻辑含义一致
                    new_prefix = f"{prefix}_{i}"

                result.update(_fully_flatten(item, new_prefix, max_depth, current_depth + 1, list_limit))

        else:
            # 混合类型列表
            used_keys = {}
            dict_items = []
            other_items = []

            for i, item in enumerate(data):
                if isinstance(item, dict):
                    dict_items.append((i, item))
                else:
                    other_items.append((i, item))

            # 对字典元素排序
            def _sort_key(item: dict) -> tuple:
                for key in ["name", "key", "id", "type"]:
                    if key in item:
                        val = item[key]
                        if isinstance(val, str):
                            return (0, val.lower())
                        if isinstance(val, (int, float)):
                            return (1, val)
                return (2, "")

            dict_items.sort(key=lambda x: _sort_key(x[1]))

            # V26.0: 排序稳定性修复 - 处理字典元素（使用排序后的索引）
            for sorted_idx, (original_i, item) in enumerate(dict_items):
                semantic_key = _extract_semantic_key(item)

                if semantic_key:
                    base_key = semantic_key
                    if base_key in used_keys:
                        suffix = used_keys[base_key]
                        unique_key = f"{base_key}_{suffix}"
                        used_keys[base_key] = suffix + 1
                    else:
                        unique_key = base_key
                        used_keys[base_key] = 1
                    new_prefix = f"{prefix}_{unique_key}"
                else:
                    # V26.0 修复：使用排序后的索引
                    new_prefix = f"{prefix}_{sorted_idx}"

                result.update(_fully_flatten(item, new_prefix, max_depth, current_depth + 1, list_limit))

            # 处理非字典元素
            for i, item in other_items:
                if isinstance(item, list):
                    new_prefix = f"{prefix}_{i}"
                    result.update(_fully_flatten(item, new_prefix, max_depth, current_depth + 1, list_limit))
                else:
                    parsed = _parse_value(item)
                    if parsed is not None:
                        new_prefix = f"{prefix}_{i}"
                        result[new_prefix] = parsed

    else:
        # 基本类型
        parsed = _parse_value(data)
        if parsed is not None:
            result[prefix] = parsed

    return result


def align_features(features: dict[str, Any], reference_keys: set[str]) -> dict[str, Any]:
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
# V26.0 生产级自适应提取器
# ============================================================================


@dataclass
class V26ExtractionMetrics:
    """V26.0 提取器执行指标"""

    total_features: int = 0
    numeric_features: int = 0
    string_features: int = 0
    nan_count: int = 0
    flatten_depth: int = 0


class V25ProductionExtractor(BaseExtractor):
    """
    V26.2 生产级"零缺陷"收割流水线 (Phase 1.3 优化版)

    V26.2 → V26.1 核心改进：
        - max_features: 8000 → 6000 (减少 25% 维度)
        - sparsity_threshold: 0.95 → 0.90 (更激进剪枝)
        - 核心特征白名单: 保护滚动特征、赛前特征
        - 目标内存占用减少 40%

    核心能力:
        1. 递归打平：自动处理任意深度嵌套的 JSON 结构
        2. 最小过滤：保留坐标等结构化数据
        3. 动态类型发现：智能转换 int/float/百分比/布尔值
        4. 特征对齐：全局注册表确保跨比赛特征一致性
        5. 稀疏度过滤：自动剔除低价值特征（V26.2 优化）
        6. 排序稳定：确保不同比赛的特征列逻辑含义一致
        7. 核心特征保护：白名单机制保护高价值特征（V26.2 新增）
    """

    # 版本标识
    VERSION = "V26.2"

    # 验证配置（V26.0 调整）
    DEFAULT_CONFIG = ValidationConfig(
        min_features=1000,  # V26.0: 提高下限
        max_features=15000,  # V26.0: 提高上限
        allow_partial=True,
    )

    def __init__(self, validation_config: ValidationConfig | None = None):
        """初始化 V26.0 提取器"""
        super().__init__(validation_config or self.DEFAULT_CONFIG)
        self._metrics = V26ExtractionMetrics()

    @property
    def version(self) -> str:
        """返回版本号"""
        return self.VERSION

    def pre_process(self, raw_data: dict[str, Any]) -> dict[str, Any]:
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

    def _flatten_l2_json(self, raw_data: dict[str, Any]) -> dict[str, Any]:
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

    def extract(self, raw_data: dict[str, Any]) -> ExtractionResult:
        """
        V26.0 全量自适应特征提取（核心方法）

        策略：
        1. 递归打平整个 JSON 结构（V26.0: 更高深度和列表限制）
        2. 自动类型转换和值提取
        3. 全局特征对齐（填充缺失特征）
        4. 动态计算统计特征
        """
        self._logger.info("开始全量特征提取", version=self.version)

        self._metrics = V26ExtractionMetrics()
        features: dict[str, Any] = {}
        warnings: list[str] = []
        errors: list[str] = []

        try:
            # Step 1: 递归打平整个 JSON (V26.0: 使用更高参数)
            self._logger.info("步骤 1/4: 递归打平 JSON 结构")
            flattened = _fully_flatten(raw_data, max_depth=25, list_limit=50)
            self._metrics.flatten_depth = max(len(k.split("_")) for k in flattened.keys()) if flattened else 0

            # Step 2: 分类特征并注册到全局表
            self._logger.info("步骤 2/4: 特征分类与对齐")
            numeric_features = {}
            string_features = {}

            for key, value in flattened.items():
                # 跳过元数据键
                if key.startswith("_"):
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

            # Step 4.5: V26.1 特征剪枝（控制维度）
            from src.processors.v26_sparsity_filter import apply_sparsity_filter

            features_before_prune = len(features)
            features = apply_sparsity_filter(features)
            features_after_prune = len(features)

            # 添加元数据
            features["_meta"] = {
                "extraction_version": self.version,
                "extraction_timestamp": self._get_timestamp(),
                "feature_count": len(features),
                "features_before_prune": features_before_prune,
                "features_after_prune": features_after_prune,
                "pruned_count": features_before_prune - features_after_prune,
                "numeric_count": len(numeric_features),
                "string_count": len(string_features),
                "flatten_depth": self._metrics.flatten_depth,
                "global_registry_size": len(get_global_feature_keys()),
            }

            self._metrics.total_features = len(features)

            # V26.0: 调整状态判断阈值
            if self._metrics.total_features >= 3000:
                status = ExtractionStatus.SUCCESS
            elif self._metrics.total_features >= 1000:
                status = ExtractionStatus.PARTIAL
            else:
                status = ExtractionStatus.FAILED

            self._logger.info(
                "特征提取完成",
                total_features=self._metrics.total_features,
                features_before_prune=features_before_prune,
                features_after_prune=features_after_prune,
                pruned_count=features_before_prune - features_after_prune,
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

    def validate(self, features: dict[str, Any]) -> bool:
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
        if self._validation_config.max_features is not None and feature_count > self._validation_config.max_features:
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
