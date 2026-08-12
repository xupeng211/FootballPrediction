"""Deprecated compatibility imports for the canonical inference dispatcher.

The historical v17 training engine is not present in this repository and is
not recreated here. Existing imports of ``ModelDispatcher`` and ``Predictor``
are delegated to their canonical inference owner.

lifecycle: compatibility
component: legacy ML import facade
"""

import warnings

from src.ml.inference.model_dispatcher import ModelDispatcher, Predictor

# 保留历史别名，但不创建新的实现或训练入口。
V26Predictor = Predictor
V26ModelDispatcher = ModelDispatcher

__all__ = [
    "ModelDispatcher",
    "Predictor",
    "V26ModelDispatcher",
    "V26Predictor",
]

warnings.warn(
    "直接导入 from src.ml.engine 已弃用，请使用 "
    "from src.ml.inference import ModelDispatcher, Predictor",
    DeprecationWarning,
    stacklevel=2,
)
