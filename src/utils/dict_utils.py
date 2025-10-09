"""
足球预测系统字典处理工具模块

提供字典操作相关的工具函数。
"""

from typing import Any, Dict, List, cast


class DictUtils:
    """字典处理工具类"""

    @staticmethod
    def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典 - 递归合并嵌套字典，dict2的值会覆盖dict1中的同名键"""
        result = dict1.copy()
        for key, value in dict2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # 如果两边都是字典，则递归合并，保持嵌套结构
                result[key] = DictUtils.deep_merge(result[key], value)
            else:
                # 非字典值直接覆盖，确保最新值优先
                result[key] = value
        return result

    @staticmethod
    def flatten_dict(
        d: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, Any]:
        """扁平化嵌套字典 - 将多层嵌套结构转为单层，便于配置管理和数据传输"""
        items: List[tuple] = []
        for k, v in d.items():
            # 构建新的键名，使用分隔符连接层级关系
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                # 递归处理嵌套字典，保持层级关系的可追溯性
                items.extend(DictUtils.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def filter_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
        """过滤掉值为None的键值对"""
        return {k: v for k, v in d.items() if v is not None}
