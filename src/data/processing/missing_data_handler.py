"""
高级缺失数据处理器

提供专业的缺失数据分析、检测和处理功能，包括：
- 缺失数据模式分析
- 多种缺失值处理策略
- 缺失机制检测
- 智能插补方法
"""

import logging
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MissingDataHandler:
    """高级缺失数据处理器"""

    def __init__(self):
        self.missing_patterns = {}
        self.imputation_history = {}

    def analyze_missing_patterns(self, data: pd.DataFrame) -> dict[str, Any]:
        """分析缺失数据模式

        Args:
            data: 要分析的数据

        Returns:
            Dict: 缺失模式分析结果
        """
        analysis = {
            "total_missing": data.isnull().sum().sum(),
            "missing_by_column": {},
            "missing_patterns": {},
            "missing_mechanism": self._detect_missing_mechanism(data),
            "missing_correlation": self._analyze_missing_correlation(data),
        }

        for column in data.columns:
            missing_count = data[column].isnull().sum()
            if missing_count > 0:
                analysis["missing_by_column"][column] = {
                    "count": missing_count,
                    "percentage": missing_count / len(data) * 100,
                    "type": self._classify_missing_type(data[column]),
                }

        # 识别缺失模式
        missing_matrix = data.isnull()
        pattern_counts = missing_matrix.value_counts().head(10)
        analysis["missing_patterns"] = {
            str(pattern): count for pattern, count in pattern_counts.items()
        }

        self.missing_patterns = analysis
        return analysis

    def _classify_missing_type(self, series: pd.Series) -> str:
        """分类缺失值类型"""
        missing_ratio = series.isnull().sum() / len(series)

        if missing_ratio < 0.05:
            return "sporadic"
        elif missing_ratio < 0.20:
            return "moderate"
        elif missing_ratio < 0.50:
            return "substantial"
        else:
            return "extensive"

    def _detect_missing_mechanism(self, data: pd.DataFrame) -> str:
        """检测缺失机制（简化版）"""
        total_cells = data.shape[0] * data.shape[1]
        missing_cells = data.isnull().sum().sum()
        missing_ratio = missing_cells / total_cells

        if missing_ratio < 0.10:
            return "likely_mcar"
        elif missing_ratio < 0.30:
            return "likely_mar"
        else:
            return "likely_mnar"

    def _analyze_missing_correlation(self, data: pd.DataFrame) -> dict[str, Any]:
        """分析缺失值之间的相关性"""
        missing_indicators = data.isnull().astype(int)
        correlation_matrix = missing_indicators.corr()

        # 找出高度相关的缺失模式
        high_corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i + 1, len(correlation_matrix.columns)):
                corr_val = correlation_matrix.iloc[i, j]
                if abs(corr_val) > 0.5:
                    high_corr_pairs.append(
                        {
                            "column1": correlation_matrix.columns[i],
                            "column2": correlation_matrix.columns[j],
                            "correlation": corr_val,
                        }
                    )

        return {
            "correlation_matrix": correlation_matrix.to_dict(),
            "high_correlations": high_corr_pairs,
        }

    def impute_missing_data(
        self, data: pd.DataFrame, strategy: str = "adaptive"
    ) -> pd.DataFrame:
        """缺失数据插补

        Args:
            data: 包含缺失值的数据
            strategy: 插补策略

        Returns:
            pd.DataFrame: 插补后的数据
        """
        logger.info(f"开始使用 {strategy} 策略进行缺失值插补")

        imputed_data = data.copy()
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        categorical_columns = data.select_dtypes(include=["object"]).columns

        if strategy == "adaptive":
            numeric_strategy = self._select_optimal_strategy(data, numeric_columns)
            categorical_strategy = "mode"
        else:
            numeric_strategy = strategy
            categorical_strategy = "mode"

        # 处理数值型数据
        if len(numeric_columns) > 0:
            imputed_data[numeric_columns] = self._impute_numeric(
                data[numeric_columns], numeric_strategy
            )

        # 处理分类型数据
        if len(categorical_columns) > 0:
            imputed_data[categorical_columns] = self._impute_categorical(
                data[categorical_columns], categorical_strategy
            )

        # 记录插补历史
        self.imputation_history[len(self.imputation_history)] = {
            "strategy": strategy,
            "numeric_strategy": numeric_strategy,
            "timestamp": pd.Timestamp.now().isoformat(),
            "original_missing": data.isnull().sum().sum(),
            "remaining_missing": imputed_data.isnull().sum().sum(),
        }

        logger.info(f"缺失值插补完成，剩余缺失值: {imputed_data.isnull().sum().sum()}")
        return imputed_data

    def _select_optimal_strategy(self, data: pd.DataFrame, columns: list[str]) -> str:
        """选择最优插补策略"""
        total_missing = data[columns].isnull().sum().sum()
        total_cells = len(data) * len(columns)
        missing_ratio = total_missing / total_cells

        if missing_ratio < 0.05:
            return "mean"
        elif missing_ratio < 0.20:
            return "median"
        else:
            return "mode"

    def _impute_numeric(self, data: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """数值型数据插补"""
        imputed_data = data.copy()

        if strategy == "mean":
            imputed_data = imputed_data.fillna(imputed_data.mean())
        elif strategy == "median":
            imputed_data = imputed_data.fillna(imputed_data.median())
        elif strategy == "mode":
            for column in imputed_data.columns:
                mode_value = imputed_data[column].mode()
                if not mode_value.empty:
                    imputed_data[column].fillna(mode_value[0], inplace=True)
                else:
                    imputed_data[column].fillna(0, inplace=True)
        elif strategy == "forward_fill":
            imputed_data = imputed_data.fillna(method="ffill")
            imputed_data = imputed_data.fillna(method="bfill")  # 处理开头的NaN
        elif strategy == "backward_fill":
            imputed_data = imputed_data.fillna(method="bfill")
            imputed_data = imputed_data.fillna(method="ffill")  # 处理结尾的NaN
        elif strategy == "interpolate":
            for column in imputed_data.columns:
                imputed_data[column] = imputed_data[column].interpolate()
        elif strategy == "zero":
            imputed_data = imputed_data.fillna(0)

        return imputed_data

    def _impute_categorical(self, data: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """分类型数据插补"""
        imputed_data = data.copy()

        if strategy == "mode":
            for column in imputed_data.columns:
                mode_value = imputed_data[column].mode()
                if not mode_value.empty:
                    imputed_data[column].fillna(mode_value[0], inplace=True)
                else:
                    imputed_data[column].fillna("Unknown", inplace=True)
        elif strategy == "forward_fill":
            imputed_data = imputed_data.fillna(method="ffill")
            imputed_data = imputed_data.fillna(method="bfill")
        elif strategy == "backward_fill":
            imputed_data = imputed_data.fillna(method="bfill")
            imputed_data = imputed_data.fillna(method="ffill")
        elif strategy == "unknown":
            imputed_data = imputed_data.fillna("Unknown")

        return imputed_data

    def handle_columns_with_excessive_missing(
        self, data: pd.DataFrame, threshold: float = 0.5
    ) -> pd.DataFrame:
        """处理缺失值过多的列

        Args:
            data: 数据
            threshold: 缺失值比例阈值

        Returns:
            pd.DataFrame: 处理后的数据
        """
        columns_to_drop = []
        columns_to_keep = []

        for column in data.columns:
            missing_ratio = data[column].isnull().sum() / len(data)
            if missing_ratio > threshold:
                columns_to_drop.append(column)
            else:
                columns_to_keep.append(column)

        if columns_to_drop:
            logger.warning(f"删除缺失值过多的列: {columns_to_drop} (阈值: {threshold})")
            data = data.drop(columns=columns_to_drop)

        return data

    def validate_imputation_quality(
        self, original_data: pd.DataFrame, imputed_data: pd.DataFrame
    ) -> dict[str, Any]:
        """验证插补质量

        Args:
            original_data: 原始数据（包含缺失值）
            imputed_data: 插补后的数据

        Returns:
            Dict: 插补质量评估结果
        """
        validation = {
            "original_missing_count": original_data.isnull().sum().sum(),
            "remaining_missing_count": imputed_data.isnull().sum().sum(),
            "imputation_success_rate": 0.0,
            "column_validation": {},
        }

        total_original_missing = validation["original_missing_count"]
        total_remaining_missing = validation["remaining_missing_count"]

        if total_original_missing > 0:
            validation["imputation_success_rate"] = (
                (total_original_missing - total_remaining_missing)
                / total_original_missing
            ) * 100

        # 按列验证
        for column in original_data.columns:
            if original_data[column].isnull().any():
                col_validation = {
                    "original_missing": original_data[column].isnull().sum(),
                    "remaining_missing": imputed_data[column].isnull().sum(),
                    "imputed_successfully": not imputed_data[column].isnull().any(),
                }
                validation["column_validation"][column] = col_validation

        return validation

    def get_missing_data_report(self) -> dict[str, Any]:
        """获取缺失数据处理报告"""
        return {
            "latest_patterns": self.missing_patterns,
            "imputation_history": self.imputation_history,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[str]:
        """生成缺失数据处理建议"""
        recommendations = []

        if not self.missing_patterns:
            return ["还没有进行缺失数据分析"]

        missing_ratio = self.missing_patterns["total_missing"] / (
            sum(
                len(pattern.split())
                for pattern in self.missing_patterns.get("missing_patterns", {}).keys()
            )
            if self.missing_patterns.get("missing_patterns")
            else 1
        )

        if missing_ratio > 0.3:
            recommendations.append("数据缺失率较高，建议检查数据收集过程")

        if self.missing_patterns.get("missing_mechanism") == "likely_mnar":
            recommendations.append("可能存在非随机缺失，建议深入调查缺失原因")

        extensive_missing = [
            col
            for col, info in self.missing_patterns.get("missing_by_column", {}).items()
            if info["percentage"] > 50
        ]

        if extensive_missing:
            recommendations.append(f"以下列缺失率过高，考虑删除: {extensive_missing}")

        return recommendations


# 便捷函数
def handle_missing_data(
    data: pd.DataFrame, strategy: str = "adaptive", drop_threshold: float = 0.5
) -> pd.DataFrame:
    """
    便捷的缺失数据处理函数

    Args:
        data: 包含缺失值的数据
        strategy: 插补策略
        drop_threshold: 删除列的阈值

    Returns:
        pd.DataFrame: 处理后的数据
    """
    handler = MissingDataHandler()

    # 分析缺失模式
    handler.analyze_missing_patterns(data)

    # 处理缺失值过多的列
    data = handler.handle_columns_with_excessive_missing(data, drop_threshold)

    # 插补缺失值
    imputed_data = handler.impute_missing_data(data, strategy)

    return imputed_data
