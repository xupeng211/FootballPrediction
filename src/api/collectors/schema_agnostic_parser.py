#!/usr/bin/env python3
"""
V20.0 Schema-Agnostic 递归解析器
==============================

⚠️  DEPRECATED - 此文件已被弃用 ⚠️

此模块已被 V25 统一特征提取框架取代:
    - 新框架位置: src/processors/v25_production_extractor.py
    - 新入口: ExtractorRegistry.create("V25.0")

保留原因:
    - 被 backfill_v20.5_hardened.py 和 backfill_v20.8_scorched_earth.py 引用
    - 用于历史数据回填任务

计划:
    - V26.0 将完全移除此文件
    - 回填脚本将迁移到 V25 框架

核心功能（旧版）：
- 深度优先搜索 JSON 结构中的任意 key
- 自动定位并提取 xG、shots 等关键特征
- 容错性：无论数据嵌套在列表、字典还是混合结构中
- 支持模糊匹配和正则表达式

作者: Data Architecture Team
日期: 2025-12-24
版本: V20.0
弃用日期: 2025-12-26
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union, Callable
from collections import deque

logger = logging.getLogger(__name__)


class SchemaAgnosticParser:
    """
    Schema-Agnostic 递归解析器

    设计理念：
    1. 不依赖固定的 JSON 路径
    2. 自动发现并提取目标数据
    3. 处理 FotMob API 的多版本数据格式
    """

    # 常见特征的匹配模式
    TARGET_PATTERNS = {
        'expected_goals': [r'expected.?goals', r'xg', r'xG'],
        'shots_on_target': [r'shots.?on.?target', r'on.?target'],
        'total_shots': [r'total.?shots', r'shots'],
        'possession': [r'ball.?possession', r'possession'],
        'corners': [r'corners'],
        'fouls': [r'fouls'],
        'passes': [r'passes'],
    }

    def __init__(self):
        self.search_cache: Dict[str, Any] = {}
        logger.info("=== V20.0 Schema-Agnostic 解析器初始化 ===")

    def deep_search(
        self,
        data: Any,
        target_key: str,
        fuzzy: bool = True,
        max_depth: int = 20
    ) -> List[Dict[str, Any]]:
        """
        深度优先搜索目标 key 的所有出现位置

        Args:
            data: 要搜索的 JSON 数据
            target_key: 目标 key 名称
            fuzzy: 是否启用模糊匹配
            max_depth: 最大搜索深度

        Returns:
            找到的所有匹配项，每个包含 {'path': str, 'value': Any, 'parent': Dict}
        """
        results = []
        visited = set()  # 防止循环引用

        # 生成匹配模式
        patterns = [target_key]
        if fuzzy:
            patterns.extend(self._get_patterns_for_key(target_key))

        def _search_recursive(obj: Any, path: str = "", depth: int = 0):
            if depth > max_depth:
                return

            # 防止循环引用
            obj_id = id(obj)
            if obj_id in visited:
                return
            visited.add(obj_id)

            # 处理字典
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # 检查 key 是否匹配
                    if self._key_matches(key, patterns):
                        results.append({
                            'path': current_path,
                            'key': key,
                            'value': value,
                            'parent': obj
                        })

                    # 递归搜索
                    _search_recursive(value, current_path, depth + 1)

            # 处理列表
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    current_path = f"{path}[{idx}]"
                    _search_recursive(item, current_path, depth + 1)

        _search_recursive(data)
        return results

    def extract_feature_value(
        self,
        data: Any,
        feature_name: str,
        fallback: Any = None
    ) -> Optional[Any]:
        """
        提取特征的值

        Args:
            data: JSON 数据
            feature_name: 特征名称（如 'expected_goals'）
            fallback: 找不到时的默认值

        Returns:
            提取的值，找不到返回 fallback
        """
        # 检查缓存
        cache_key = f"{feature_name}_{id(data)}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]

        # 深度搜索
        matches = self.deep_search(data, feature_name, fuzzy=True)

        if not matches:
            return fallback

        # 策略：优先选择包含 'stats' 或 'home'/'away' 结构的值
        preferred = self._select_best_match(matches, feature_name)

        # 缓存结果
        self.search_cache[cache_key] = preferred

        return preferred

    def extract_home_away_stats(
        self,
        data: Any,
        feature_name: str
    ) -> Dict[str, Optional[Any]]:
        """
        提取主客队统计值

        Args:
            data: JSON 数据
            feature_name: 特征名称

        Returns:
            {'home': value, 'away': value}
        """
        matches = self.deep_search(data, feature_name, fuzzy=True)

        result = {'home': None, 'away': None}

        for match in matches:
            value = match.get('value')
            parent = match.get('parent', {})

            # 检查是否是 stats 数组格式 [home, away]
            if isinstance(value, list) and len(value) >= 2:
                result['home'] = value[0]
                result['away'] = value[1]
                break

            # 检查父对象是否有 home/away 键
            if isinstance(parent, dict):
                if 'home' in parent or 'homeValue' in parent:
                    result['home'] = parent.get('home') or parent.get('homeValue')
                if 'away' in parent or 'awayValue' in parent:
                    result['away'] = parent.get('away') or parent.get('awayValue')

        return result

    def find_stats_groups(self, data: Any) -> List[Dict]:
        """
        查找所有统计数据组

        返回结构：
        [
            {'key': 'expected_goals', 'stats': [home_val, away_val], 'title': 'Expected goals'},
            ...
        ]
        """
        stats_groups = []

        # 搜索所有包含 'stats' 键的对象
        matches = self.deep_search(data, 'stats', fuzzy=False)

        for match in matches:
            parent = match.get('parent', {})

            # 检查是否是统计组格式
            if isinstance(parent, dict) and 'key' in parent:
                key = parent.get('key', '')
                stats = parent.get('stats', [])

                if isinstance(stats, list) and len(stats) >= 2:
                    stats_groups.append({
                        'key': key,
                        'stats': stats,
                        'title': parent.get('title', key)
                    })

        return stats_groups

    def parse_all_match_stats(self, data: Any) -> Dict[str, Dict]:
        """
        解析比赛的所有统计数据

        Returns:
            {
                'expected_goals': {'home': 1.34, 'away': 1.49},
                'shots_on_target': {'home': 5, 'away': 3},
                ...
            }
        """
        result = {}

        # 查找所有统计组
        stats_groups = self.find_stats_groups(data)

        for group in stats_groups:
            key = group['key']
            stats = group['stats']

            # 解析主客队值
            home_val, away_val = None, None

            if isinstance(stats, list) and len(stats) >= 2:
                # 直接格式 [home, away]
                home_val = stats[0]
                away_val = stats[1]

            result[key] = {'home': home_val, 'away': away_val}

        return result

    def smart_extract_xg(self, data: Any) -> Dict[str, Optional[float]]:
        """
        智能提取 xG 数据

        这是 Schema-Agnostic 解析的核心示例：
        无论 xG 数据在 JSON 的哪个位置，都能自动定位并提取

        Returns:
            {'home': 1.34, 'away': 1.49} 或 {'home': None, 'away': None}
        """
        # 尝试多种提取策略
        strategies = [
            self._extract_xg_from_stats_groups,
            self._extract_xg_from_direct_search,
            self._extract_xg_from_nested_structure,
        ]

        for strategy in strategies:
            result = strategy(data)
            if result['home'] is not None or result['away'] is not None:
                return result

        return {'home': None, 'away': None}

    def _extract_xg_from_stats_groups(self, data: Any) -> Dict[str, Optional[float]]:
        """策略1: 从统计组中提取"""
        stats_groups = self.find_stats_groups(data)

        for group in stats_groups:
            key = group['key'].lower()
            if 'expected' in key and 'goal' in key:
                stats = group.get('stats', [])
                if isinstance(stats, list) and len(stats) >= 2:
                    return {
                        'home': self._to_float(stats[0]),
                        'away': self._to_float(stats[1])
                    }

        return {'home': None, 'away': None}

    def _extract_xg_from_direct_search(self, data: Any) -> Dict[str, Optional[float]]:
        """策略2: 直接搜索 expected_goals"""
        matches = self.deep_search(data, 'expected_goals', fuzzy=True)

        for match in matches:
            value = match.get('value')
            if isinstance(value, list) and len(value) >= 2:
                return {
                    'home': self._to_float(value[0]),
                    'away': self._to_float(value[1])
                }
            elif isinstance(value, dict):
                home = value.get('home') or value.get('homeValue')
                away = value.get('away') or value.get('awayValue')
                return {
                    'home': self._to_float(home),
                    'away': self._to_float(away)
                }

        return {'home': None, 'away': None}

    def _extract_xg_from_nested_structure(self, data: Any) -> Dict[str, Optional[float]]:
        """策略3: 从嵌套结构中提取（处理复杂情况）"""
        # 搜索包含 xG 相关关键词的所有位置
        patterns = ['expected_goals', 'xg', 'xG', 'expectedGoals']

        for pattern in patterns:
            matches = self.deep_search(data, pattern, fuzzy=True)

            for match in matches:
                # 检查兄弟节点是否有 home/away 数据
                parent = match.get('parent', {})
                if isinstance(parent, dict):
                    # 尝试从兄弟节点提取
                    for sibling_key, sibling_value in parent.items():
                        if isinstance(sibling_value, list) and len(sibling_value) == 2:
                            # 验证数据类型（应该是数字）
                            if self._is_numeric(sibling_value[0]) and self._is_numeric(sibling_value[1]):
                                return {
                                    'home': self._to_float(sibling_value[0]),
                                    'away': self._to_float(sibling_value[1])
                                }

        return {'home': None, 'away': None}

    def _key_matches(self, key: str, patterns: List[str]) -> bool:
        """检查 key 是否匹配任一模式"""
        key_lower = key.lower()

        for pattern in patterns:
            if pattern.lower() in key_lower:
                return True

        return False

    def _get_patterns_for_key(self, key: str) -> List[str]:
        """获取 key 的匹配模式"""
        return self.TARGET_PATTERNS.get(key, [])

    def _select_best_match(self, matches: List[Dict], feature_name: str) -> Any:
        """从多个匹配中选择最佳值"""
        if not matches:
            return None

        # 策略1: 选择最短路径的匹配（更接近根节点）
        matches_by_depth = sorted(matches, key=lambda m: m['path'].count('.'))

        # 策略2: 优先选择有 stats 键的
        for match in matches_by_depth:
            if 'stats' in match.get('path', '').lower():
                return match['value']

        # 默认返回第一个
        return matches_by_depth[0]['value']

    def _to_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _is_numeric(self, value: Any) -> bool:
        """检查是否是数字"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def clear_cache(self):
        """清除搜索缓存"""
        self.search_cache.clear()


# 单例实例
_parser_instance: Optional[SchemaAgnosticParser] = None


def get_parser() -> SchemaAgnosticParser:
    """获取解析器单例"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = SchemaAgnosticParser()
    return _parser_instance


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 测试数据：模拟不同的 JSON 结构
    test_cases = [
        # 结构1: 标准格式
        {
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [{
                            "key": "expected_goals",
                            "stats": [1.34, 1.49]
                        }]
                    }
                }
            }
        },
        # 结构2: 嵌套列表
        {
            "content": {
                "stats": [{
                    "key": "expected_goals",
                    "stats": [1.34, 1.49]
                }]
            }
        },
        # 结构3: 深度嵌套
        {
            "l2_json": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [{
                                    "key": "expected_goals",
                                    "type": "text",
                                    "stats": ["1.34", "1.49"]
                                }]
                            }
                        }
                    }
                }
            }
        }
    ]

    parser = get_parser()

    print("=== Schema-Agnostic 解析器测试 ===\n")

    for i, test_data in enumerate(test_cases, 1):
        print(f"测试用例 {i}:")
        xg = parser.smart_extract_xg(test_data)
        print(f"  xG: {xg}")
        print()


# ============================================
# 核心递归搜索代码片段（输出要求）
# ============================================

def deep_search_core(data: Any, target: str, max_depth: int = 20) -> List[Dict]:
    """
    V20.0 核心递归搜索算法

    特点：
    1. 不依赖固定路径
    2. 自动处理任意嵌套层级
    3. 支持列表、字典混合结构
    4. 防止循环引用
    """
    results = []
    visited = set()

    def _recursive_search(obj: Any, path: str = "", depth: int = 0):
        if depth > max_depth:
            return

        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if target.lower() in key.lower():
                    results.append({'path': current_path, 'key': key, 'value': value})
                _recursive_search(value, current_path, depth + 1)

        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                current_path = f"{path}[{idx}]"
                _recursive_search(item, current_path, depth + 1)

    _recursive_search(data)
    return results
