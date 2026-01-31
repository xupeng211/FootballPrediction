#!/usr/bin/env python3
"""
V34.0 Greedy Extraction Engine - 贪婪无差别采矿引擎
==================================================
"Data is Asset" - 提取 JSON 中的每一个数字和分类特征
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class GreedyMiner:
    """
    V34.0 贪婪采矿引擎 - 无差别特征提取

    核心原则:
    1. 遍历 JSON 中的每一个节点
    2. 只要是数字 (int/float) → 提取为特征
    3. 只要是可映射的字符串 → 提取为分类特征
    4. 冗余保证 → 现在不用，未来可能有用
    5. 结构化存储 → 按类别组织到嵌套 JSONB
    """

    def __init__(self):
        """初始化贪婪采矿引擎"""
        self.extraction_version = "V34.0"
        self.extraction_stats = {
            "total_nodes_visited": 0,
            "numeric_features": 0,
            "categorical_features": 0,
            "array_features": 0,
            "nested_objects": 0,
        }

    def extract_all_features(self, json_data: dict, match_id: int | None = None) -> dict[str, Any]:
        """
        无差别提取所有特征

        Args:
            json_data: FotMob L2 JSON 数据
            match_id: 比赛 ID (可选)

        Returns:
            全息特征字典
        """
        # 重置统计
        self.extraction_stats = {
            "total_nodes_visited": 0,
            "numeric_features": 0,
            "categorical_features": 0,
            "array_features": 0,
            "nested_objects": 0,
        }

        # 处理嵌套的 l2_json 结构
        actual_data = json_data.get("l2_json", json_data)
        if isinstance(actual_data, str):
            actual_data = json.loads(actual_data)

        # 初始化全息特征结构
        holographic_features = {
            "raw_stats": {},  # 原始统计数字
            "spatial_data": {},  # 坐标/位置数据
            "time_series": {},  # 时序数据
            "contextual": {},  # 上下文信息 (裁判/天气/等)
            "player_stats": {},  # 球员统计
            "team_stats": {},  # 球队统计
            "shotmap_data": {},  # 射门图数据
            "momentum_data": {},  # 动量数据
            "auto_extracted": {},  # 自动提取的特征
        }

        # 开始贪婪遍历
        self._greedy_traverse(actual_data, holographic_features, path_prefix="")

        # 添加元数据
        holographic_features["_meta"] = {
            "match_id": match_id,
            "extraction_version": self.extraction_version,
            "extraction_timestamp": datetime.now().isoformat(),
            "total_features": sum(self.extraction_stats[k] for k in self.extraction_stats if "features" in k),
        }

        return holographic_features

    def _greedy_traverse(self, obj: Any, features: dict, path_prefix: str, depth: int = 0) -> None:
        """
        贪婪遍历 JSON 对象并提取所有值

        Args:
            obj: 当前节点对象
            features: 特征存储字典
            path_prefix: 当前路径前缀
            depth: 当前深度
        """
        if depth > 20:  # 防止过深递归
            return

        self.extraction_stats["total_nodes_visited"] += 1

        if isinstance(obj, dict):
            self.extraction_stats["nested_objects"] += 1

            for key, value in obj.items():
                current_path = f"{path_prefix}.{key}" if path_prefix else key
                safe_key = self._sanitize_key(key)
                safe_path = self._sanitize_key(current_path)

                # 根据值的类型进行不同处理
                if isinstance(value, (int, float)):
                    # 数字特征 → 提取
                    self._extract_numeric_feature(value, safe_path, safe_key, features)
                elif isinstance(value, str):
                    # 字符串特征 → 提取为分类
                    self._extract_string_feature(value, safe_path, safe_key, features)
                elif isinstance(value, list):
                    # 数组/列表 → 提取统计特征
                    self._extract_array_feature(value, safe_path, safe_key, features)
                elif isinstance(value, dict):
                    # 嵌套对象 → 递归遍历
                    self._greedy_traverse(value, features, current_path, depth + 1)
                elif value is None or isinstance(value, bool):
                    # None/Bool → 跳过
                    pass

        elif isinstance(obj, list):
            self.extraction_stats["array_features"] += 1
            # 列表也需要遍历内部元素
            for i, item in enumerate(obj[:100]):  # 限制前100个元素
                current_path = f"{path_prefix}[{i}]" if path_prefix else f"root[{i}]"
                self._greedy_traverse(item, features, current_path, depth + 1)

    def _extract_numeric_feature(self, value: float, path: str, key: str, features: dict) -> None:
        """提取数字特征"""
        # 确保 value 是 Python 原生类型（避免 numpy 类型导致 JSON 序列化失败）
        if hasattr(value, "item"):  # numpy scalar
            value = value.item()
        value = float(value) if not isinstance(value, bool) else value

        self.extraction_stats["numeric_features"] += 1

        # 根据路径判断应该存入哪个分类
        category = self._classify_feature_path(path)

        # 存储到对应分类
        if category == "spatial":
            features["spatial_data"][key] = value
        elif category == "time_series":
            features["time_series"][key] = value
        elif category == "contextual":
            features["contextual"][key] = value
        elif "player" in path.lower() or path.startswith("content.playerStats"):
            features["player_stats"][key] = value
        elif "team" in path.lower():
            features["team_stats"][key] = value
        elif "shot" in path.lower() or path.startswith("content.shotmap"):
            features["shotmap_data"][key] = value
        elif "momentum" in path.lower():
            features["momentum_data"][key] = value
        else:
            features["raw_stats"][key] = value

        # 同时也存入 auto_extracted (扁平化)
        features["auto_extracted"][path] = value

    def _extract_string_feature(self, value: str, path: str, key: str, features: dict) -> None:
        """提取字符串特征"""
        # 只有特定类型的字符串才提取
        extractable_patterns = [
            "name",
            "team",
            "player",
            "referee",
            "stadium",
            "venue",
            "league",
            "season",
            "competition",
            "country",
        ]

        if any(pattern in path.lower() or pattern in value.lower() for pattern in extractable_patterns):
            features["contextual"][key] = value
            features["auto_extracted"][path] = value
            self.extraction_stats["categorical_features"] += 1

    def _extract_array_feature(self, value: list, path: str, key: str, features: dict) -> None:
        """提取数组特征"""
        if not value:
            return

        # 提取数组统计信息（确保 JSON 可序列化）
        def make_json_serializable(obj):
            """将对象转换为 JSON 可序列化类型"""
            if hasattr(obj, "item"):  # numpy scalar
                return float(obj.item())
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            if isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [make_json_serializable(v) for v in obj]
            return obj

        stats = {
            "count": len(value),
            "first": make_json_serializable(value[0]) if value else None,
            "last": make_json_serializable(value[-1]) if value else None,
        }

        # 如果数组包含数字，计算统计量
        numeric_values = [v for v in value if isinstance(v, (int, float))]
        if numeric_values:
            stats.update(
                {
                    "sum": float(sum(numeric_values)),
                    "mean": float(np.mean(numeric_values)),
                    "std": float(np.std(numeric_values)),
                    "min": float(np.min(numeric_values)),
                    "max": float(np.max(numeric_values)),
                }
            )

        # 存储统计信息
        stats_key = f"{key}_array_stats"
        features["auto_extracted"][stats_key] = stats

    def _classify_feature_path(self, path: str) -> str:
        """
        根据路径分类特征

        Returns:
            分类名称: spatial, time_series, contextual, raw_stats
        """
        path_lower = path.lower()

        # 空间/坐标类特征
        if any(kw in path_lower for kw in ["x", "y", "coordinate", "position", "location"]):
            return "spatial"

        # 时序类特征
        if any(kw in path_lower for kw in ["minute", "time", "momentum", "period", "trend"]):
            return "time_series"

        # 上下文类特征
        if any(kw in path_lower for kw in ["weather", "referee", "venue", "league", "season", "team"]):
            return "contextual"

        # 默认归类
        return "raw_stats"

    def _sanitize_key(self, key: str) -> str:
        """
        清理键名，确保可以作为字典键

        Args:
            key: 原始键名

        Returns:
            安全的键名
        """
        # 替换特殊字符
        replacements = {
            ".": "_",
            "-": "_",
            " ": "_",
            "/": "_",
            "[": "_",
            "]": "_",
            "(": "_",
            ")": "_",
        }

        safe_key = key
        for old, new in replacements.items():
            safe_key = safe_key.replace(old, new)

        # 移除非字母数字下划线的字符
        safe_key = "".join(c if c.isalnum() or c == "_" else "" for c in safe_key)

        # 确保不以数字开头
        if safe_key and safe_key[0].isdigit():
            safe_key = f"_{safe_key}"

        return safe_key or "unknown"

    def get_extraction_hash(self, json_data: dict) -> str:
        """
        计算数据开采逻辑的哈希指纹

        Args:
            json_data: JSON 数据

        Returns:
            哈希值 (SHA256 的前16位)
        """
        # 使用版本号 + 关键键的集合生成哈希
        key_set = sorted(self._get_all_keys(json_data))
        hash_input = f"{self.extraction_version}:{json.dumps(key_set, sort_keys=True)}"

        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _get_all_keys(self, obj: Any, keys: set | None = None) -> set:
        """递归获取所有键"""
        if keys is None:
            keys = set()

        if isinstance(obj, dict):
            for key, value in obj.items():
                keys.add(key)
                self._get_all_keys(value, keys)
        elif isinstance(obj, list):
            for item in obj:
                self._get_all_keys(item, keys)

        return keys

    def get_extraction_stats(self) -> dict[str, int]:
        """获取开采统计信息"""
        return self.extraction_stats.copy()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("V34.0 Greedy Extraction Engine Ready")
    print("全息开采模式已就绪")
