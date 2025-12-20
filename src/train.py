#!/usr/bin/env python3
"""
Football Prediction Training Entry Point
足球预测模型训练入口

Usage:
    python -m src.train
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.trainer_v1 import main

if __name__ == "__main__":
    main()