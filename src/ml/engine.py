#!/usr/bin/env python3
"""
V26.8 ML Engine - 向后兼容接口
================================

此文件提供向后兼容的导入层。
所有实现已拆分至：
- src/ml/training/v17_engine.py (V17MLEngine 训练引擎)
- src/ml/inference/model_dispatcher.py (Predictor + ModelDispatcher 推理引擎)

[Genesis.GoldenLayout] 重构完成
"""

import sys
import warnings

from src.ml.inference.model_dispatcher import ModelDispatcher, Predictor

# 导入新拆分的组件
from src.ml.training.v17_engine import V17MLEngine

# 导入旧的 main 函数用于测试
from src.ml.training.v17_engine import main as _v17_main

# 保留旧版 Predictor 别名（向后兼容）
V26Predictor = Predictor
V26ModelDispatcher = ModelDispatcher

# 向后兼容性导出
__all__ = [
    "ModelDispatcher",
    "Predictor",
    "V17MLEngine",
    "V26ModelDispatcher",
    "V26Predictor",
    "main",
]

# 弃用警告
warnings.warn(
    "直接导入 from src.ml.engine 已弃用。请使用新路径:"
    "- from src.ml.training import V17MLEngine"
    "- from src.ml.inference import ModelDispatcher, Predictor",
    DeprecationWarning,
    stacklevel=2
)


def main():
    """主函数 - 保留用于测试"""
    return _v17_main()


if __name__ == "__main__":
    sys.exit(main())
