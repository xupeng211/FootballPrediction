"""Configuration loader utilities."""

import json
import os
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


def load_config_from_file(file_path: str) -> dict[str, Any]:
    """Load configuration from file."""
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            if file_path.endswith(".json"):
                result = json.load(f)
                # 如果解析结果是null、true、false、数字等非对象类型，返回空字典
                if result is None or isinstance(
                    result, bool | int | float | str | list
                ):
                    return {}
                return result
            elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
                if yaml is None:
                    raise ImportError("yaml library not available")
                return yaml.safe_load(f) or {}
            else:
                return {}
    except (ValueError, KeyError, RuntimeError, ImportError, json.JSONDecodeError):
        return {}
    except Exception:
        # 捕获YAML解析错误和其他可能的异常
        return {}
