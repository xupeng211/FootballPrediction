"""足球预测系统字典处理工具模块.

提供字典操作相关的工具函数.
"""

from typing import Any


class DictUtils:
    """字典处理工具类."""

    @staticmethod
    def deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
        """深度合并字典 - 递归合并嵌套字典,dict2的值会覆盖dict1中的同名键."""
        result = dict1.copy()
        for key, value in dict2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # 如果两边都是字典，则递归合并,保持嵌套结构
                result[key] = DictUtils.deep_merge(result[key], value)
            else:
                # 非字典值直接覆盖,确保最新值优先
                result[key] = value
        return result

    @staticmethod
    def flatten_dict(
        d: dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> dict[str, Any]:
        # 构建新的键名,使用分隔符连接层级关系
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                # 递归处理嵌套字典,保持层级关系的可追溯性
                items.extend(DictUtils.flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def filter_none_values(d: dict[str, Any]) -> dict[str, Any]:
        """过滤掉None值的键值对."""
        return {k: v for k, v in d.items() if v is not None}

    @staticmethod
    def filter_empty_values(d: dict[str, Any]) -> dict[str, Any]:
        """过滤掉空值（空字符串,空列表,空字典）的键值对."""
        return {
            k: v
            for k, v in d.items()
            if v is not None and v != "" and v != [] and v != {}
        }

    @staticmethod
    def filter_by_keys(d: dict[str, Any], keys: list[str]) -> dict[str, Any]:
        """只保留指定的键."""
        return {k: v for k, v in d.items() if k in keys}

    @staticmethod
    def exclude_keys(d: dict[str, Any], keys: list[str]) -> dict[str, Any]:
        """排除指定的键."""
        return {k: v for k, v in d.items() if k not in keys}

    @staticmethod
    def get_nested_value(
        d: dict[str, Any], key_path: str | list[str], default: Any = None
    ) -> Any:
        """获取嵌套字典中的值.

        Args:
            d: 源字典
            key_path: 键路径,如 "user.profile.name" 或 ["user", "profile", "name"]
            default: 默认值

        Returns:
            找到的值或默认值
        """
        if isinstance(key_path, str):
            keys = key_path.split(".")
        elif isinstance(key_path, list):
            keys = key_path
        else:
            return default

        current = d

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError, AttributeError):
            return default

    @staticmethod
    def set_nested_value(
        d: dict[str, Any], key_path: str | list[str], value: Any
    ) -> None:
        """设置嵌套字典中的值.

        Args:
            d: 源字典
            key_path: 键路径,如 "user.profile.name" 或 ["user", "profile", "name"]
            value: 要设置的值
        """
        if isinstance(key_path, str):
            keys = key_path.split(".")
        elif isinstance(key_path, list):
            keys = key_path
        else:
            return

        current = d

        # 创建嵌套结构
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # 设置最终值
        current[keys[-1]] = value

    @staticmethod
    def rename_keys(d: dict[str, Any], key_map: dict[str, str]) -> dict[str, Any]:
        """重命名字典的键."""
        return {key_map.get(k, k): v for k, v in d.items()}

    @staticmethod
    def swap_keys(d: dict[str, Any]) -> dict[str, Any]:
        """交换字典的键和值."""
        return {str(v): k for k, v in d.items()}

    @staticmethod
    def invert_dict(d: dict[str, Any]) -> dict[Any, str]:
        """反转字典（键值互换）."""
        return {v: k for k, v in d.items()}

    @staticmethod
    def pick_values(d: dict[str, Any], keys: list[str]) -> list[Any]:
        """提取指定键的值."""
        return [d.get(k) for k in keys]

    @staticmethod
    def count_values(d: dict[str, Any]) -> int:
        """计算字典中值的总数."""
        return len(d)

    @staticmethod
    def is_empty(d: dict[str, Any] | None) -> bool:
        """检查字典是否为空."""
        if d is None:
            return True
        return len(d) == 0

    @staticmethod
    def merge_list(dicts: list[dict[str, Any]]) -> dict[str, Any]:
        """合并多个字典（后面的会覆盖前面的）."""
        result = {}
        for d in dicts:
            if isinstance(d, dict):
                result.update(d)
        return result

    @staticmethod
    def chunk_dict(d: dict[str, Any], chunk_size: int) -> list[dict[str, Any]]:
        items = list(d.items())
        return [
            dict(items[i : i + chunk_size]) for i in range(0, len(items), chunk_size)
        ]

    @staticmethod
    def sort_keys(d: dict[str, Any], reverse: bool = False) -> dict[str, Any]:
        """按键排序."""
        return dict(sorted(d.items(), key=lambda item: item[0], reverse=reverse))

    @staticmethod
    def group_by_first_char(d: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """按首字母分组."""
        result = {}
        for key, value in d.items():
            first_char = key[0].upper() if key else "_"
            if first_char not in result:
                result[first_char] = {}
            result[first_char][key] = value
        return result

    @staticmethod
    def validate_required_keys(
        d: dict[str, Any], required_keys: list[str]
    ) -> list[str]:
        """验证必需的键是否存在."""
        missing = []
        for key in required_keys:
            if key not in d:
                missing.append(key)
        return missing

    @staticmethod
    def convert_keys_case(d: dict[str, Any], case: str = "lower") -> dict[str, Any]:
        """转换键的大小写（递归处理嵌套字典）."""

        def _convert(obj, case):
            if isinstance(obj, dict):
                if case == "lower":
                    return {k.lower(): _convert(v, case) for k, v in obj.items()}
                elif case == "upper":
                    return {k.upper(): _convert(v, case) for k, v in obj.items()}
                elif case == "title":
                    return {k.title(): _convert(v, case) for k, v in obj.items()}
                else:
                    return obj
            elif isinstance(obj, list):
                return [_convert(item, case) for item in obj]
            else:
                return obj

        return _convert(d, case)

    @staticmethod
    def deep_clone(d: dict[str, Any]) -> dict[str, Any]:
        """深度克隆字典."""
        import copy

        return copy.deepcopy(d)

    @staticmethod
    def merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
        """浅度合并字典 - dict2的值会覆盖dict1中的同名键."""
        result = dict1.copy()
        result.update(dict2)
        return result

    @staticmethod
    def get(d: dict[str, Any], key: str, default: Any = None) -> Any:
        """获取字典值，支持默认值."""
        return d.get(key, default)

    @staticmethod
    def has_key(d: dict[str, Any], key: str) -> bool:
        """检查字典是否包含指定键."""
        return key in d

    @staticmethod
    def filter_keys(d: dict[str, Any], filter_func) -> dict[str, Any]:
        """根据过滤函数筛选键值对."""
        return {k: v for k, v in d.items() if filter_func(k)}


# 顶级函数，用于直接导入
def deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """深度合并字典 - 递归合并嵌套字典,dict2的值会覆盖dict1中的同名键."""
    return DictUtils.deep_merge(dict1, dict2)


def merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """浅度合并字典 - dict2的值会覆盖dict1中的同名键."""
    return DictUtils.merge(dict1, dict2)


def deep_clone(d: dict[str, Any]) -> dict[str, Any]:
    """深度克隆字典."""
    return DictUtils.deep_clone(d)


def get(d: dict[str, Any], key: str, default: Any = None) -> Any:
    """获取字典值，支持默认值."""
    return DictUtils.get(d, key, default)


def has_key(d: dict[str, Any], key: str) -> bool:
    """检查字典是否包含指定键."""
    return DictUtils.has_key(d, key)


def get_nested_value(
    d: dict[str, Any], key_path: str | list[str], default: Any = None
) -> Any:
    """获取嵌套字典中的值."""
    if isinstance(key_path, str):
        keys = key_path.split(".")
    elif isinstance(key_path, list):
        keys = key_path
    else:
        return default

    current = d
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def set_nested_value(
    d: dict[str, Any], key_path: str | list[str], value: Any
) -> dict[str, Any]:
    """设置嵌套字典中的值."""
    if isinstance(key_path, str):
        keys = key_path.split(".")
    elif isinstance(key_path, list):
        keys = key_path
    else:
        return d

    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return d


def flatten_dict(d: dict[str, Any], separator: str = ".") -> dict[str, Any]:
    """扁平化嵌套字典."""

    def _flatten(obj, parent_key="", sep="."):
        items = []
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
            if isinstance(v, dict):
                items.extend(_flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    return _flatten(d, sep=separator)


def filter_dict(
    d: dict[str, Any], keys: list[str] = None, predicate=None
) -> dict[str, Any]:
    """过滤字典，只保留指定的键或满足条件的键值对."""
    if predicate is not None:
        # 使用谓词函数过滤
        return {k: v for k, v in d.items() if predicate(k, v)}
    elif keys is not None:
        # 按键过滤
        return {key: d[key] for key in keys if key in d}
    else:
        return {}


def rename_keys(d: dict[str, Any], key_map: dict[str, str]) -> dict[str, Any]:
    """重命名字典中的键."""
    result = {}
    for key, value in d.items():
        new_key = key_map.get(key, key)
        result[new_key] = value
    return result
