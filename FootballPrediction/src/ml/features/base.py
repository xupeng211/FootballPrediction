"""
Base Feature Transformer - 特征工程抽象基类

Phase 2: AI Modeling - 特征工程架构核心

遵循Scikit-Learn Transformer接口规范，提供标准化的特征生成框架。
支持严格的类型安全、数据验证和错误处理。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class BaseFeatureTransformer(ABC):
    """
    所有特征生成器的抽象基类。

    遵循Scikit-Learn Transformer接口规范，确保与标准ML管道兼容。
    提供类型安全、数据验证和错误处理机制。

    设计原则：
    1. Scikit-Learn兼容性: 实现fit/transform接口
    2. 类型安全: 严格类型注解
    3. 数据完整性: 输入输出验证
    4. 防数据泄露: 时间序列安全处理
    5. 可扩展性: 支持自定义特征逻辑
    """

    def __init__(
        self,
        name: str,
        required_columns: Optional[List[str]] = None,
        output_suffix: str = "_feature"
    ):
        """
        初始化特征转换器。

        Args:
            name: 特征转换器名称，用于日志和调试
            required_columns: 必需的输入列列表
            output_suffix: 输出特征列的后缀

        Raises:
            ValueError: 当参数验证失败时
        """
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")

        self.name = name
        self.required_columns = required_columns or []
        self.output_suffix = output_suffix

        # 运行时状态
        self.is_fitted_ = False
        self.feature_names_out_ = []

        logger.info(f"初始化特征转换器: {self.name}")

    @abstractmethod
    def fit(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None
    ) -> 'BaseFeatureTransformer':
        """
        适配转换器（如果需要统计全局信息）。

        对于有状态转换器，计算全局统计信息（如均值、方差等）。
        对于无状态转换器，仅验证输入并返回self。

        Args:
            X: 输入数据，必需列必须存在
            y: 目标变量（可选，某些特征可能需要）

        Returns:
            self: 返回自身以支持方法链

        Raises:
            ValueError: 当输入验证失败时
            TypeError: 当输入类型错误时
        """
        self._validate_input(X)
        self._fit(X, y)
        self.is_fitted_ = True

        logger.info(f"特征转换器 {self.name} 适配完成")
        return self

    @abstractmethod
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        执行特征转换。

        必须返回包含新特征的DataFrame，且行数与输入保持一致。
        确保防止数据泄露，特别是对于时间序列数据。

        Args:
            X: 输入数据，必需列必须存在

        Returns:
            包含新特征的DataFrame

        Raises:
            ValueError: 当输入验证失败时
            RuntimeError: 当转换器未适配时
        """
        if not self.is_fitted_:
            raise RuntimeError(f"特征转换器 {self.name} 尚未适配，请先调用fit方法")

        self._validate_input(X)
        result = self._transform(X)
        self._validate_output(result, len(X))

        return result

    def fit_transform(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        适配并转换数据的便捷方法。

        Args:
            X: 输入数据
            y: 目标变量（可选）

        Returns:
            转换后的数据
        """
        return self.fit(X, y).transform(X)

    def get_feature_names_out(self) -> List[str]:
        """
        获取输出特征名称。

        Returns:
            输出特征名称列表
        """
        if not self.is_fitted_:
            raise RuntimeError(f"特征转换器 {self.name} 尚未适配")
        return self.feature_names_out_.copy()

    def _validate_input(self, X: pd.DataFrame) -> None:
        """
        验证输入数据。

        Args:
            X: 输入数据

        Raises:
            TypeError: 当输入不是DataFrame时
            ValueError: 当必需列缺失时
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"输入必须是pd.DataFrame，得到 {type(X)}")

        missing_columns = [col for col in self.required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(
                f"输入数据缺少必需列: {missing_columns}. "
                f"可用列: {list(X.columns)}"
            )

    def _validate_output(self, result: pd.DataFrame, expected_rows: int) -> None:
        """
        验证输出数据。

        Args:
            result: 输出结果
            expected_rows: 期望的行数

        Raises:
            ValueError: 当输出验证失败时
        """
        if not isinstance(result, pd.DataFrame):
            raise TypeError(f"输出必须是pd.DataFrame，得到 {type(result)}")

        if len(result) != expected_rows:
            raise ValueError(
                f"输出行数 ({len(result)}) 与输入行数 ({expected_rows}) 不匹配"
            )

    def _fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> None:
        """
        实际的适配逻辑，由子类重写。

        Args:
            X: 输入数据
            y: 目标变量
        """
        pass  # 默认无状态适配

    @abstractmethod
    def _transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        实际的转换逻辑，由子类重写。

        Args:
            X: 输入数据

        Returns:
            转换后的数据
        """
        pass

    def _create_feature_name(self, base_name: str, **kwargs) -> str:
        """
        创建特征名称。

        Args:
            base_name: 基础名称
            **kwargs: 额外参数（如窗口大小等）

        Returns:
            格式化的特征名称
        """
        params_str = "_".join(f"{k}_{v}" for k, v in sorted(kwargs.items()) if v is not None)
        if params_str:
            return f"{base_name}{self.output_suffix}_{params_str}"
        return f"{base_name}{self.output_suffix}"

    def __repr__(self) -> str:
        """字符串表示。"""
        return f"{self.__class__.__name__}(name='{self.name}', fitted={self.is_fitted_})"

    def __str__(self) -> str:
        """用户友好的字符串表示。"""
        return self.__repr__()


class FeatureEngineeringError(Exception):
    """特征工程专用异常类。"""
    pass


class DataLeakageError(FeatureEngineeringError):
    """数据泄露专用异常类。"""
    pass