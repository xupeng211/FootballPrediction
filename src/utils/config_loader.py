"""
Configuration loader utilities
"""

import json
import os
from typing import Any, Dict, Optional


def load_config_from_file(file_path: str) -> Dict[str, Any]:
    """Load configuration from file"""
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.endswith(".json"):
                return json.load(f)  # type: ignore
            elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
                import yaml  # type: ignore

                return yaml.safe_load(f) or {}
            else:
                return {}
    except Exception:
        return {}
