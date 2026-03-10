#!/usr/bin/env python3
"""
TITAN 模型加载器
================

V4.46.8 重构：从 predict_pipeline.py 剥离的模型加载逻辑。

专职负责 TITAN 模型的加载、验证和预测。

@module src.ml.inference.titan_loader
@version V4.46.8
@updated 2026-03-11
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from src.constants.model_config import (
    MODEL_DIR,
    TITAN_COMBAT_FEATURES,
    DEFAULT_VALUES,
)

logger = logging.getLogger(__name__)


class TitanModelLoader:
    """
    TITAN 模型加载器

    专职负责 TITAN 模型的加载、验证和预测。

    使用示例:
        >>> loader = TitanModelLoader()
        >>> if loader.load():
        ...     away_prob, draw_prob, home_prob = loader.predict(features)
    """

    def __init__(self, model_dir: Optional[Path] = None):
        """
        初始化加载器

        Args:
            model_dir: 模型目录路径，默认使用 MODEL_DIR
        """
        self._model_dir = model_dir or MODEL_DIR
        self._model = None
        self._scaler = None

    @property
    def is_loaded(self) -> bool:
        """模型是否已加载"""
        return self._model is not None

    @property
    def has_scaler(self) -> bool:
        """是否有缩放器"""
        return self._scaler is not None

    def load(self) -> bool:
        """
        加载模型和缩放器

        尝试加载以下模型文件 (按优先级):
        1. titan_v4466_real_combat.joblib
        2. titan_v4466_combat_final.joblib

        Returns:
            加载成功返回 True
        """
        model_path = self._model_dir / "titan_v4466_real_combat.joblib"
        scaler_path = self._model_dir / "titan_v4466_real_combat_scaler.joblib"

        # 尝试备用模型
        if not model_path.exists():
            for m, s in [
                ("titan_v4466_combat_final.joblib", "titan_v4466_combat_final_scaler.joblib"),
            ]:
                if (self._model_dir / m).exists():
                    model_path = self._model_dir / m
                    scaler_path = self._model_dir / s
                    break

        if not model_path.exists():
            logger.warning("未找到可用模型")
            return False

        try:
            self._model = joblib.load(str(model_path))
            if scaler_path.exists():
                self._scaler = joblib.load(str(scaler_path))
            logger.info(f"模型加载成功: {model_path.name}")
            return True
        except Exception as e:
            logger.warning(f"模型加载失败: {e}")
            return False

    def predict(self, features: Dict[str, float]) -> Tuple[float, float, float]:
        """
        执行预测

        Args:
            features: 特征字典

        Returns:
            (away_prob, draw_prob, home_prob) 概率元组

        Raises:
            RuntimeError: 模型未加载
        """
        if not self.is_loaded:
            raise RuntimeError("模型未加载")

        # 构建特征 DataFrame
        X_df = pd.DataFrame(
            [[features.get(name, DEFAULT_VALUES.get(name, 0.0)) for name in TITAN_COMBAT_FEATURES]],
            columns=TITAN_COMBAT_FEATURES,
        )

        # 应用缩放器 (如果有)
        if self.has_scaler:
            X = self._scaler.transform(X_df)
        else:
            X = X_df.values

        # 执行预测
        probs = self._model.predict_proba(X)[0]
        return probs[0], probs[1], probs[2]

    def get_model_info(self) -> Dict[str, any]:
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "is_loaded": self.is_loaded,
            "has_scaler": self.has_scaler,
            "model_type": type(self._model).__name__ if self._model else None,
            "feature_count": len(TITAN_COMBAT_FEATURES),
            "features": TITAN_COMBAT_FEATURES,
        }


def get_titan_model(model_dir: Optional[Path] = None) -> TitanModelLoader:
    """
    获取 TITAN 模型加载器实例

    Args:
        model_dir: 模型目录路径

    Returns:
        已加载的 TitanModelLoader 实例
    """
    loader = TitanModelLoader(model_dir)
    loader.load()
    return loader


__all__ = ["TitanModelLoader", "get_titan_model"]
