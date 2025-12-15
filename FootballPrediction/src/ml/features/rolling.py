"""
Rolling Window Features - 滚动窗口特征实现

Phase 2: AI Modeling - 滚动窗口特征

实现企业级的滚动窗口特征生成器，包含严格的防数据泄漏机制。
支持滚动平均、滚动求和、滚动标准差等多种统计特征。

设计重点：
1. 数据泄露防护: 严格的shift(1)操作
2. 时间序列安全: 正确的排序和分组逻辑
3. 性能优化: 向量化操作和内存管理
4. 类型安全: 完整的类型注解
"""

import logging
from typing import List, Optional, Dict, Any
import pandas as pd

from .base import BaseFeatureTransformer, DataLeakageError, FeatureEngineeringError

logger = logging.getLogger(__name__)


class RollingAverageTransformer(BaseFeatureTransformer):
    """
    滚动平均特征转换器。

    计算指定窗口大小的滚动平均值，严格防止数据泄露。
    支持多列、多窗口、多分组的复杂场景。

    防泄漏机制：
    - 自动应用shift(1)确保时间序列安全
    - 严格的数据排序和分组
    - 完整的输入验证

    使用示例:
        >>> transformer = RollingAverageTransformer(
        ...     windows=[3, 5, 10],
        ...     columns=['goals', 'shots'],
        ...     group_by=['team_id']
        ... )
        >>> features = transformer.fit_transform(match_data)
        >>> features.columns  # ['rolling_goals_3_mean', 'rolling_goals_5_mean', ...]
    """

    def __init__(
        self,
        windows=None,
        columns=None,
        column=None,
        window_size=None,
        group_by: Optional[List[str]] = None,
        date_column: str = 'match_date',
        min_periods: int = 1,
        output_prefix: str = 'rolling'
    ):
        """
        初始化滚动平均转换器。

        Args:
            windows: 窗口大小列表，如 [3, 5, 10]
            columns: 需要计算滚动平均的列名列表
            column: 单个列名（用于兼容测试用例）
            window_size: 单个窗口大小（用于兼容测试用例）
            group_by: 分组列名列表，默认使用['team_id']
            date_column: 日期列名，用于排序，默认为'match_date'
            min_periods: 最小周期数，默认为1
            output_prefix: 输出特征名称前缀

        Raises:
            ValueError: 当参数验证失败时
        """
        super().__init__(name="RollingAverageTransformer")

        # 兼容测试用例的参数格式
        if column is not None:
            self.columns = [column]
        elif columns is not None:
            self.columns = columns
        else:
            raise ValueError("必须指定columns或column参数")

        if window_size is not None:
            self.windows = [window_size]
        elif windows is not None:
            self.windows = windows
        else:
            raise ValueError("必须指定windows或window_size参数")

        # 参数验证
        if not self.windows or not all(isinstance(w, int) and w > 0 for w in self.windows):
            raise ValueError("windows必须为正整数列表")

        if not self.columns or not all(isinstance(c, str) and c for c in self.columns):
            raise ValueError("columns必须为非空字符串列表")
        self.group_by = group_by or ['team_id']
        self.date_column = date_column
        self.min_periods = min_periods
        self.output_prefix = output_prefix

        # 运行时状态
        self.feature_names_out_ = []

        logger.info(f"初始化滚动平均转换器: windows={windows}, columns={columns}")

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> 'RollingAverageTransformer':
        """
        适配转换器。

        对于滚动平均转换器，主要是验证输入数据的完整性。
        不需要存储全局统计信息，因此是无状态转换器。

        Args:
            X: 输入数据，必须包含所有必需列
            y: 目标变量（此处不使用）

        Returns:
            self: 返回自身以支持方法链
        """
        super().fit(X, y)

        # 验证数据完整性
        missing_required = [col for col in self.columns + [self.date_column] if col not in X.columns]
        if missing_required:
            raise ValueError(f"缺少必需列: {missing_required}")

        missing_groupby = [col for col in self.group_by if col not in X.columns]
        if missing_groupby:
            raise ValueError(f"缺少分组列: {missing_groupby}")

        # 生成特征名称
        self.feature_names_out_ = self._generate_feature_names()

        logger.info(f"滚动平均转换器适配完成，将生成 {len(self.feature_names_out_)} 个特征")
        return self

    def _transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        执行滚动平均转换。

        核心逻辑：
        1. 按分组列和日期列排序
        2. 分组计算滚动平均
        3. 应用shift(1)防止数据泄露

        Args:
            X: 输入数据

        Returns:
            包含滚动平均特征的DataFrame
        """
        # 验证输入
        missing_cols = [col for col in self.columns + [self.date_column] + self.group_by
                      if col not in X.columns]
        if missing_cols:
            raise ValueError(f"输入数据缺少列: {missing_cols}")

        # 复制数据以避免修改原数据
        df = X.copy()

        try:
            # 按分组列和日期列排序
            sort_cols = self.group_by + [self.date_column]
            df = df.sort_values(by=sort_cols)

            # 计算滚动平均特征
            for col in self.columns:
                for window in self.windows:
                    feature_name = self._create_feature_name(col, window)

                    # 核心防泄露逻辑：Group -> Rolling -> Mean -> Shift(1)
                    # shift(1) 确保当前行数据不包含在自身特征中
                    df[feature_name] = (
                        df.groupby(self.group_by)[col]
                        .transform(lambda x: x.rolling(window=window, min_periods=self.min_periods)
                        .mean()
                        .shift(1)  # 关键：防数据泄露
                        )
                    )

            return df

        except Exception as e:
            logger.error(f"滚动平均计算失败: {str(e)}")
            raise FeatureEngineeringError(f"滚动平均计算失败: {str(e)}") from e

    def _generate_feature_names(self, column: str = None, window: int = None) -> List[str]:
        """
        生成特征名称列表。

        Args:
            column: 列名（可选）
            window: 窗口大小（可选）

        Returns:
            特征名称列表
        """
        if column is not None and window is not None:
            return [f"{self.output_prefix}_{column}_{window}"]

        # 生成所有特征名称
        names = []
        for col in self.columns:
            for win in self.windows:
                names.append(f"{self.output_prefix}_{col}_{win}")

        return names

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        执行滚动平均转换。

        Args:
            X: 输入数据

        Returns:
            包含滚动平均特征的DataFrame
        """
        return self._transform(X)

    def _create_feature_name(self, column: str, window: int) -> str:
        """
        创建单个特征名称。

        Args:
            column: 列名
            window: 窗口大小

        Returns:
            格式化的特征名称
        """
        return f"{self.output_prefix}_{column}_{window}"


class RollingSumTransformer(BaseFeatureTransformer):
    """
    滚动求和特征转换器。

    计算指定窗口大小的滚动求和，严格防止数据泄露。
    适用于累积统计场景，如累积进球、累积黄牌等。

    防泄漏机制与RollingAverageTransformer相同。
    """

    def __init__(
        self,
        windows=None,
        columns=None,
        column=None,
        window_size=None,
        group_by: Optional[List[str]] = None,
        date_column: str = 'match_date',
        min_periods: int = 1,
        output_prefix: str = 'rolling'
    ):
        """
        初始化滚动求和转换器。

        Args:
            windows: 窗口大小列表，如 [3, 5, 10]
            columns: 需要计算滚动求和的列名列表
            column: 单个列名（用于兼容测试用例）
            window_size: 单个窗口大小（用于兼容测试用例）
            group_by: 分组列名列表，默认使用['team_id']
            date_column: 日期列名，用于排序，默认为'match_date'
            min_periods: 最小周期数，默认为1
            output_prefix: 输出特征名称前缀

        Raises:
            ValueError: 当参数验证失败时
        """
        super().__init__(name="RollingSumTransformer")

        # 兼容测试用例的参数格式
        if column is not None:
            self.columns = [column]
        elif columns is not None:
            self.columns = columns
        else:
            raise ValueError("必须指定columns或column参数")

        if window_size is not None:
            self.windows = [window_size]
        elif windows is not None:
            self.windows = windows
        else:
            raise ValueError("必须指定windows或window_size参数")

        # 参数验证
        if not self.windows or not all(isinstance(w, int) and w > 0 for w in self.windows):
            raise ValueError("windows必须为正整数列表")

        if not self.columns or not all(isinstance(c, str) and c for c in self.columns):
            raise ValueError("columns必须为非空字符串列表")
        self.group_by = group_by or ['team_id']
        self.date_column = date_column
        self.min_periods = min_periods
        self.output_prefix = output_prefix

        # 运行时状态
        self.feature_names_out_ = []

        logger.info(f"初始化滚动求和转换器: windows={windows}, columns={columns}")

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> 'RollingSumTransformer':
        """
        适配转换器。
        """
        super().fit(X, y)

        # 验证数据完整性
        missing_required = [col for col in self.columns + [self.date_column] if col not in X.columns]
        if missing_required:
            raise ValueError(f"缺少必需列: {missing_required}")

        missing_groupby = [col for col in self.group_by if col not in X.columns]
        if missing_groupby:
            raise ValueError(f"缺少分组列: {missing_groupby}")

        # 生成特征名称
        self.feature_names_out_ = self._generate_feature_names()

        logger.info(f"滚动求和转换器适配完成，将生成 {len(self.feature_names_out_)} 个特征")
        return self

    def _transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        执行滚动求和转换。

        核心逻辑与RollingAverageTransformer相同，但使用sum()替代mean()。

        Args:
            X: 输入数据

        Returns:
            包含滚动求和特征的DataFrame
        """
        # 验证输入
        missing_cols = [col for col in self.columns + [self.date_column] + self.group_by
                      if col not in X.columns]
        if missing_cols:
            raise ValueError(f"输入数据缺少列: {missing_cols}")

        # 复制数据
        df = X.copy()

        try:
            # 按分组列和日期列排序
            sort_cols = self.group_by + [self.date_column]
            df = df.sort_values(by=sort_cols)

            # 计算滚动求和特征
            for col in self.columns:
                for window in self.windows:
                    feature_name = f"{self.output_prefix}_{col}_{window}_sum"

                    # 核心防泄露逻辑：Group -> Rolling -> Sum -> Shift(1)
                    df[feature_name] = (
                        df.groupby(self.group_by)[col]
                        .transform(lambda x: x.rolling(window=window, min_periods=self.min_periods)
                        .sum()
                        .shift(1)  # 关键：防数据泄露
                        )
                    )

            return df

        except Exception as e:
            logger.error(f"滚动求和计算失败: {str(e)}")
            raise FeatureEngineeringError(f"滚动求和计算失败: {str(e)}") from e

    def _generate_feature_names(self, column: str = None, window: int = None) -> List[str]:
        """
        生成特征名称列表。
        """
        if column is not None and window is not None:
            return [f"{self.output_prefix}_{column}_{window}_sum"]

        names = []
        for col in self.columns:
            for win in self.windows:
                names.append(f"{self.output_prefix}_{col}_{win}_sum")

        return names

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        执行滚动求和转换。

        Args:
            X: 输入数据

        Returns:
            包含滚动求和特征的DataFrame
        """
        return self._transform(X)


class RollingStdTransformer(BaseFeatureTransformer):
    """
    滚动标准差特征转换器。

    计算滚动窗口标准差，用于识别数据波动性。
    帮用于波动性分析和风险管理。
    """

    def __init__(
        self,
        windows=None,
        columns=None,
        column=None,
        window_size=None,
        group_by: Optional[List[str]] = None,
        date_column: str = 'match_date',
        min_periods: int = 2,  # 标准差需要更多数据点
        output_prefix: str = 'rolling'
    ):
        """
        初始化滚动标准差转换器。
        """
        super().__init__(name="RollingStdTransformer")

        # 兼容测试用例的参数格式
        if column is not None:
            self.columns = [column]
        elif columns is not None:
            self.columns = columns
        else:
            raise ValueError("必须指定columns或column参数")

        if window_size is not None:
            self.windows = [window_size]
        elif windows is not None:
            self.windows = windows
        else:
            raise ValueError("必须指定windows或window_size参数")

        # 参数验证
        if not self.windows or not all(isinstance(w, int) and w > 0 for w in self.windows):
            raise ValueError("windows必须为正整数列表")

        if not self.columns or not all(isinstance(c, str) and c for c in self.columns):
            raise ValueError("columns必须为非空字符串列表")
        self.group_by = group_by or ['team_id']
        self.date_column = date_column
        self.min_periods = min_periods
        self.output_prefix = output_prefix

        self.feature_names_out_ = []

        logger.info(f"初始化滚动标准差转换器: windows={windows}, columns={columns}")

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> 'RollingStdTransformer':
        """
        适配转换器。
        """
        super().fit(X, y)

        missing_required = [col for col in self.columns + [self.date_column] if col not in X.columns]
        if missing_required:
            raise ValueError(f"缺少必需列: {missing_required}")

        missing_groupby = [col for col in self.group_by if col not in X.columns]
        if missing_groupby:
            raise ValueError(f"缺少分组列: {missing_groupby}")

        self.feature_names_out_ = self._generate_feature_names()
        return self

    def _transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        执行滚动标准差转换。
        """
        missing_cols = [col for col in self.columns + [self.date_column] + self.group_by
                      if col not in X.columns]
        if missing_cols:
            raise ValueError(f"输入数据缺少列: {missing_cols}")

        df = X.copy()

        try:
            sort_cols = self.group_by + [self.date_column]
            df = df.sort_values(by=sort_cols)

            for col in self.columns:
                for window in self.windows:
                    feature_name = f"{self.output_prefix}_{col}_{window}_std"
                    df[feature_name] = (
                        df.groupby(self.group_by)[col]
                        .transform(lambda x: x.rolling(window=window, min_periods=self.min_periods)
                        .std()
                        .shift(1)
                        )
                    )

            return df

        except Exception as e:
            logger.error(f"滚动标准差计算失败: {str(e)}")
            raise FeatureEngineeringError(f"滚动标准差计算失败: {str(e)}") from e

    def _generate_feature_names(self, column: str = None, window: int = None) -> List[str]:
        """
        生成特征名称列表。
        """
        if column is not None and window is not None:
            return [f"{self.output_prefix}_{column}_{window}_std"]

        names = []
        for col in self.columns:
            for win in self.windows:
                names.append(f"{self.output_prefix}_{col}_{win}_std")

        return names

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        执行滚动标准差转换。

        Args:
            X: 输入数据

        Returns:
            包含滚动标准差特征的DataFrame
        """
        return self._transform(X)