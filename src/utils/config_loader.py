"""
Configuration loader utilities
"""

import json
import os
from typing import Any, Dict


def load_config_from_file(file_path: str) -> Dict[str, Any]:
    """Load configuration from file"""
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.endswith(".json"):
                return json.load(f)
            elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
                import yaml

                return yaml.safe_load(f) or {}
            else:
                return {}
    except (ValueError, KeyError, RuntimeError, ImportError):
        return {}
    except Exception as e:
        # 捕获YAML解析错误和其他可能的异常
        return {}
