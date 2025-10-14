from typing import Any, Dict, List, Optional, Union
"""
足球预测系统字典处理工具模块

提供字典操作相关的工具函数。
"""



class DictUtils:
    """字典处理工具类"""

    @staticmethod
    def get_nested(data: Dict[str, Any], path: str, default: Any = None) -> Any:
        """获取嵌套字典的值

        Args:
            data: 源字典
            path: 嵌套路径，使用点分隔，如 'a.b.c'
            default: 默认值，当路径不存在时返回

        Returns:
            找到的值或默认值
        """
        keys = path.split('.')
        current = data

        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except (TypeError, AttributeError):
            return default

    @staticmethod
    def set_nested(data: Dict[str, Any], path: str, value: Any) -> None:
        """设置嵌套字典的值

        Args:
            data: 目标字典
            path: 嵌套路径，使用点分隔，如 'a.b.c'
            value: 要设置的值
        """
        keys = path.split('.')
        current = data

        # 遍历到倒数第二级
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # 设置最后一级的值
        current[keys[-1]] = value

    @staticmethod
    def merge(dict1: Dict[str, Any], dict2: Dict[str, Any], deep: bool = False) -> Dict[str, Any]:
        """合并两个字典

        Args:
            dict1: 第一个字典
            dict2: 第二个字典
            deep: 是否深度合并

        Returns:
            合并后的字典
        """
        if deep:
            return DictUtils.deep_merge(dict1, dict2)
        else:
            result = dict1.copy()
            result.update(dict2)
            return result

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
    def flatten(
        d: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, Any]:
        """扁平化嵌套字典 - 将多层嵌套结构转为单层，便于配置管理和数据传输"""
        items: List[tuple] = []
        for k, v in d.items():
            # 构建新的键名，使用分隔符连接层级关系
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                # 递归处理嵌套字典，保持层级关系的可追溯性
                items.extend(DictUtils.flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def flatten_dict(
        d: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, Any]:
        """扁平化嵌套字典的别名方法"""
        return DictUtils.flatten(d, parent_key, sep)

    @staticmethod
    def filter_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
        """过滤掉值为None的键值对"""
        return {k: v for k, v in d.items() if v is not None}

    @staticmethod
    def pick(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """从字典中选择指定的键"""
        return {k: d[k] for k in keys if k in d}

    @staticmethod
    def omit(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """从字典中移除指定的键"""
        return {k: v for k, v in d.items() if k not in keys}

    @staticmethod
    def rename_keys(d: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """重命名字典的键"""
        return {mapping.get(k, k): v for k, v in d.items()}

    @staticmethod
    def filter_by_value(d: Dict[str, Any], predicate) -> Dict[str, Any]:
        """根据值过滤字典"""
        return {k: v for k, v in d.items() if predicate(v)}

    @staticmethod
    def filter_by_key(d: Dict[str, Any], predicate) -> Dict[str, Any]:
        """根据键过滤字典"""
        return {k: v for k, v in d.items() if predicate(k)}

    @staticmethod
    def invert(d: Dict[str, Any]) -> Dict[Any, str]:
        """反转字典（值作为键，键作为值）"""
        result = {}
        for k, v in d.items():
            if v in result:
                # 如果值重复，转换为列表
                if not isinstance(result[v], list):
                    result[v] = [result[v]]
                result[v].append(k)
            else:
                result[v] = k
        return result

    @staticmethod
    def group_by_key(d: Dict[str, Any], key_func) -> Dict[Any, List[Any]]:
        """根据键的某个属性分组"""
        result = {}
        for k, v in d.items():
            group_key = key_func(k)
            if group_key not in result:
                result[group_key] = []
            result[group_key].append(v)
        return result

    @staticmethod
    def deep_copy(d: Dict[str, Any]) -> Dict[str, Any]:
        """深度复制字典"""
        import copy
        return copy.deepcopy(d)

    @staticmethod
    def get_path(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
        """通过路径列表获取值"""
        current = d
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @staticmethod
    def set_path(d: Dict[str, Any], path: List[str], value: Any) -> None:
        """通过路径列表设置值"""
        current = d
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
