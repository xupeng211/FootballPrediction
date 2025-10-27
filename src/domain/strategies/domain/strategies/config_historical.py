"""
历史数据策略
"""

# 导入
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

# 常量
YAML = "yaml"
JSON = "json"


# 类定义
class HistoricalConfig:
    """历史数据策略配置"""

    pass  # TODO: 实现类逻辑
