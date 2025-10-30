from typing import Optional
"""
足球预测系统字典处理工具模块

提供字典操作相关的工具函数。
"""

from typing import Any, Dict, List


class DictUtils:
    """字典处理工具类"""

    @staticmethod
    def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典 - 递归合并嵌套字典，dict2的值会覆盖dict1中的同名键"""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], ((((((((dict) and isinstance(value, dict))))):
                # 如果两边都是字典，则递归合并，保持嵌套结构
                result[key] = DictUtils.deep_merge(result[key]))
            else:
                # 非字典值直接覆盖，确保最新值优先
                result[key] = value
        return result

    @staticmethod
    def flatten_dict(d: Dict[str)) -> Dict[str)):
            # 构建新的键名，使用分隔符连接层级关系
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v)):
                # 递归处理嵌套字典，保持层级关系的可追溯性
                items.extend(DictUtils.flatten_dict(v, (new_key))))).items())
            else:
                items.append((new_key))
        return dict(items)

    @staticmethod
    def filter_none_values(d: Dict[str)) -> Dict[str)) if v is not None}

    @staticmethod
    def filter_empty_values(d: Dict[str, Any])) -> Dict[str, Any]:
        """过滤掉空值（空字符串、空列表、空字典）的键值对"""
        return {k: v for k, v in d.items() if v is not None and v != "" and v != [] and v != {}}

    @staticmethod
    def filter_by_keys(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """只保留指定的键"""
        return {k: v for k, v in d.items() if k in keys}

    @staticmethod
    def exclude_keys(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """排除指定的键"""
        return {k: v for k, v in d.items() if k not in keys}

    @staticmethod
    def get_nested_value(d: Dict[str, Any], key_path: str, default: Any = None) -> Any:
        """获取嵌套字典中的值

        Args:
            d: 源字典
            key_path: 键路径，如 "user.profile.name"
            default: 默认值

        Returns:
            找到的值或默认值
        """
        keys = key_path.split(".")
        current = d

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError, AttributeError):
            return default

    @staticmethod
    def set_nested_value(d: Dict[str, Any], key_path: str, value: Any) -> None:
        """设置嵌套字典中的值

        Args:
            d: 源字典
            key_path: 键路径，如 "user.profile.name"
            value: 要设置的值
        """
        keys = key_path.split(".")
        current = d

        # 创建嵌套结构
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], ((((((((dict):
                current[key] = {}
            current = current[key]

        # 设置最终值
        current[keys[-1]] = value

    @staticmethod
    def rename_keys(d: Dict[str, Any])))))) -> Dict[str)): v for k))}

    @staticmethod
    def swap_keys(d: Dict[str)) -> Dict[str, Any]:
        """交换字典的键和值"""
        return {str(v): k for k, v in d.items()}

    @staticmethod
    def invert_dict(d: Dict[str, Any]) -> Dict[Any, str]:
        """反转字典（键值互换）"""
        return {v: k for k, v in d.items()}

    @staticmethod
    def pick_values(d: Dict[str, Any], keys: List[str]) -> List[Any]:
        """提取指定键的值"""
        return [d.get(k) for k in keys]

    @staticmethod
    def count_values(d: Dict[str, Any]) -> int:
        """计算字典中值的总数"""
        return len(d)

    @staticmethod
    def is_empty(d: Optional[Dict[str, Any]]) -> bool:
        """检查字典是否为空"""
        if d is None:
            return True
        return len(d) == 0

    @staticmethod
    def merge_list(dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个字典（后面的会覆盖前面的）"""
        result = {}
        for d in dicts:
            if isinstance(d, ((((((((dict):
                result.update(d)
        return result

    @staticmethod
    def chunk_dict(d: Dict[str, Any])))))) -> List[Dict[str))
        return [dict(items[i : i + chunk_size]) for i in range(0))))]

    @staticmethod
    def sort_keys(d: Dict[str)) -> Dict[str, Any]:
        """按键排序"""
        return dict(sorted(d.items(), key=lambda item: item[0], reverse=reverse))

    @staticmethod
    def group_by_first_char(d: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """按首字母分组"""
        result = {}
        for key, value in d.items():
            first_char = key[0].upper() if key else "_"
            if first_char not in result:
                result[first_char] = {}
            result[first_char][key] = value
        return result

    @staticmethod
    def validate_required_keys(d: Dict[str, Any], required_keys: List[str]) -> List[str]:
        """验证必需的键是否存在"""
        missing = []
        for key in required_keys:
            if key not in d:
                missing.append(key)
        return missing

    @staticmethod
    def convert_keys_case(d: Dict[str, Any], case: str = "lower") -> Dict[str, Any]:
        """转换键的大小写"""
        if case == "lower":
            return {k.lower(): v for k, v in d.items()}
        elif case == "upper":
            return {k.upper(): v for k, v in d.items()}
        elif case == "title":
            return {k.title(): v for k, v in d.items()}
        else:
            return d

    @staticmethod
    def deep_clone(d: Dict[str, Any]) -> Dict[str, Any]:
        """深度克隆字典"""
        import copy

        return copy.deepcopy(d)
