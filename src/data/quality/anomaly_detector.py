"""
高级数据质量异常检测模块

实现基于统计学和机器学习的数据异常检测功能，用于足球预测系统的数据质量监控。

支持的检测方法：
1. 统计学方法：
   - 3σ规则检测
   - 分布偏移检测（Kolmogorov-Smirnov检验）
   - 四分位距(IQR)异常值检测

2. 机器学习方法：
   - Isolation Forest 异常检测
   - 数据漂移检测（Data Drift）
   - 聚类异常检测

集成 Prometheus 监控指标，支持实时异常告警。

基于 DATA_DESIGN.md 中的数据治理与质量控制架构设计。
"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from prometheus_client import Counter, Gauge, Histogram
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from src.database.connection import DatabaseManager

# 忽略sklearn警告
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)


# =============================================================================
# Prometheus 监控指标 - 使用延迟初始化避免重复注册
# =============================================================================


def _get_or_create_metric(metric_class, name: str, description: str, labels: list):
    """
    安全地获取或创建Prometheus指标，避免重复注册错误

    Args:
        metric_class: 指标类型 (Counter, Gauge, Histogram)
        name: 指标名称
        description: 指标描述
        labels: 标签列表

    Returns:
        Prometheus指标实例
    """
    from prometheus_client import REGISTRY

    # 尝试从已注册的指标中查找
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, "_name") and collector._name == name:
            return collector

    # 如果不存在，创建新指标
    try:
        return metric_class(name, description, labels)
    except ValueError as e:
        # 如果仍然失败，记录警告并返回一个虚拟指标
        logger.warning(f"无法创建Prometheus指标 {name}: {e}")

        # 返回一个虚拟对象，避免代码崩溃
        class DummyMetric:
            def labels(self, *args, **kwargs):
                return self

            def inc(self, *args, **kwargs):
                pass

            def set(self, *args, **kwargs):
                pass

            def observe(self, *args, **kwargs):
                pass

        return DummyMetric()


# 异常检测总计指标
anomalies_detected_total = _get_or_create_metric(
    Counter,
    "football_data_anomalies_detected_total",
    "Total number of data anomalies detected",
    ["table_name", "anomaly_type", "detection_method", "severity"],
)

# 数据漂移评分指标
data_drift_score = _get_or_create_metric(
    Gauge,
    "football_data_drift_score",
    "Data drift score indicating distribution changes",
    ["table_name", "feature_name"],
)

# 异常检测执行时间
anomaly_detection_duration_seconds = _get_or_create_metric(
    Histogram,
    "football_data_anomaly_detection_duration_seconds",
    "Time taken to complete anomaly detection",
    ["table_name", "detection_method"],
)

# 异常检测覆盖率
anomaly_detection_coverage = _get_or_create_metric(
    Gauge,
    "football_data_anomaly_detection_coverage",
    "Percentage of data covered by anomaly detection",
    ["table_name"],
)


class AnomalyDetectionResult:
    """异常检测结果类"""

    def __init__(
        self,
        table_name: str,
        detection_method: str,
        anomaly_type: str,
        severity: str = "medium",
    ):
        """
        初始化异常检测结果

        Args:
            table_name: 表名
            detection_method: 检测方法
            anomaly_type: 异常类型
            severity: 严重程度 (low, medium, high, critical)
        """
        self.table_name = table_name
        self.detection_method = detection_method
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.timestamp = datetime.now()
        self.anomalous_records: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

    def add_anomalous_record(self, record: Dict[str, Any]) -> None:
        """添加异常记录"""
        self.anomalous_records.append(record)

    def set_statistics(self, stats: Dict[str, Any]) -> None:
        """设置统计信息"""
        self.statistics = stats

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """设置元数据"""
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "detection_method": self.detection_method,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "anomalous_records_count": len(self.anomalous_records),
            "anomalous_records": self.anomalous_records,
            "statistics": self.statistics,
            "metadata": self.metadata,
        }


class StatisticalAnomalyDetector:
    """统计学异常检测器"""

    def __init__(self, sigma_threshold: float = 3.0):
        """
        初始化统计学异常检测器

        Args:
            sigma_threshold: 3σ规则的阈值，默认为3.0
        """
        self.sigma_threshold = sigma_threshold
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

    def detect_outliers_3sigma(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> AnomalyDetectionResult:
        """
        使用3σ规则检测异常值

        Args:
            data: 待检测的数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            AnomalyDetectionResult: 异常检测结果
        """
        start_time = datetime.now()

        try:
            # 处理NaN值和空数据
            if data.empty:
                raise ValueError("输入数据为空")

            # 删除NaN值进行计算
            clean_data = data.dropna()
            if clean_data.empty:
                raise ValueError("删除NaN后数据为空")

            # 计算均值和标准差
            mean = clean_data.mean()
            std = clean_data.std()

            # 处理标准差为0的情况（所有值相同）
            if std == 0 or np.isnan(std):
                # 所有值相同，没有异常值
                result = AnomalyDetectionResult(
                    table_name=table_name,
                    detection_method="3sigma",
                    anomaly_type="statistical_outlier",
                    severity="low",
                )
                result.set_statistics(
                    {
                        "total_records": len(clean_data),
                        "outliers_count": 0,
                        "outlier_rate": 0.0,
                        "mean": float(mean),
                        "std": 0.0,
                        "sigma_threshold": self.sigma_threshold,
                    }
                )
                return result

            # 计算异常值阈值
            lower_bound = mean - self.sigma_threshold * std
            upper_bound = mean + self.sigma_threshold * std

            # 对于极大值和非负数据，使用对数变换
            is_positive_data = (clean_data >= 0).all()
            data_range_ratio = clean_data.max() / (clean_data.min() + 1e-10)

            if is_positive_data and data_range_ratio > 1000:
                # 使用对数变换来处理极端范围的数据
                log_data = np.log1p(clean_data)
                log_mean = log_data.mean()
                log_std = log_data.std()

                if log_std > 1e-9:  # 确保对数变换后有标准差
                    log_lower_bound = log_mean - self.sigma_threshold * log_std
                    log_upper_bound = log_mean + self.sigma_threshold * log_std

                    # 检测对数变换后的异常值
                    outliers_mask = (log_data < log_lower_bound) | (
                        log_data > log_upper_bound
                    )
                    outliers = clean_data[outliers_mask]
                else:
                    outliers = pd.Series(dtype=clean_data.dtype)
            else:
                # 正常检测流程
                lower_bound = mean - self.sigma_threshold * std
                upper_bound = mean + self.sigma_threshold * std
                outliers_mask = (clean_data < lower_bound) | (clean_data > upper_bound)
                outliers = clean_data[outliers_mask]

            # 检测异常值（基于原始数据索引，但只对非NaN值进行检测）
            outliers_mask = (clean_data < lower_bound) | (clean_data > upper_bound)
            outliers = clean_data[outliers_mask]

            # 创建检测结果
            result = AnomalyDetectionResult(
                table_name=table_name,
                detection_method="3sigma",
                anomaly_type="statistical_outlier",
                severity="medium" if len(outliers) < len(clean_data) * 0.05 else "high",
            )

            # 添加异常记录
            for idx, value in outliers.items():
                # 处理极大值情况，避免计算错误
                try:
                    z_score = float((value - mean) / std)
                    # 限制z_score的范围，避免极端值
                    z_score = max(-100, min(100, z_score))
                except (OverflowError, ValueError):
                    z_score = 100 if value > mean else -100

                result.add_anomalous_record(
                    {
                        "index": int(idx),
                        "column": column_name,
                        "value": float(value),
                        "z_score": z_score,
                        "threshold_exceeded": (
                            "lower" if value < lower_bound else "upper"
                        ),
                    }
                )

            # 设置统计信息
            result.set_statistics(
                {
                    "total_records": len(clean_data),  # 使用清理后的数据计数
                    "outliers_count": len(outliers),
                    "outlier_rate": (
                        len(outliers) / len(clean_data) if len(clean_data) > 0 else 0.0
                    ),
                    "mean": float(mean),
                    "std": float(std),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound),
                    "sigma_threshold": self.sigma_threshold,
                }
            )

            # 记录Prometheus指标
            anomalies_detected_total.labels(
                table_name=table_name,
                anomaly_type="statistical_outlier",
                detection_method="3sigma",
                severity=result.severity,
            ).inc(len(outliers))

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="3sigma"
            ).observe(duration)

            self.logger.info(
                f"3σ异常检测完成: {table_name}.{column_name}, "
                f"发现 {len(outliers)} 个异常值 (共 {len(data)} 条记录)"
            )

            return result

        except Exception as e:
            self.logger.error(f"3σ异常检测失败: {e}")
            raise

    def detect_distribution_shift(
        self,
        baseline_data: pd.Series,
        current_data: pd.Series,
        table_name: str,
        column_name: str,
        significance_level: float = 0.05,
    ) -> AnomalyDetectionResult:
        """
        使用Kolmogorov-Smirnov检验检测分布偏移

        Args:
            baseline_data: 基准数据
            current_data: 当前数据
            table_name: 表名
            column_name: 列名
            significance_level: 显著性水平，默认0.05

        Returns:
            AnomalyDetectionResult: 异常检测结果
        """
        start_time = datetime.now()

        try:
            # 执行KS检验
            ks_statistic, p_value = stats.ks_2samp(baseline_data, current_data)

            # 判断是否存在分布偏移
            distribution_shifted = p_value < significance_level

            # 确定严重程度
            if p_value < 0.001:
                severity = "critical"
            elif p_value < 0.01:
                severity = "high"
            elif p_value < 0.05:
                severity = "medium"
            else:
                severity = "low"

            # 创建检测结果
            result = AnomalyDetectionResult(
                table_name=table_name,
                detection_method="ks_test",
                anomaly_type="distribution_shift",
                severity=severity if distribution_shifted else "low",
            )

            # 计算分布统计信息
            baseline_stats = {
                "mean": float(baseline_data.mean()),
                "std": float(baseline_data.std()),
                "median": float(baseline_data.median()),
                "min": float(baseline_data.min()),
                "max": float(baseline_data.max()),
            }

            current_stats = {
                "mean": float(current_data.mean()),
                "std": float(current_data.std()),
                "median": float(current_data.median()),
                "min": float(current_data.min()),
                "max": float(current_data.max()),
            }

            # 设置统计信息 - 确保布尔值正确转换
            result.set_statistics(
                {
                    "ks_statistic": float(ks_statistic),
                    "p_value": float(p_value),
                    "significance_level": significance_level,
                    "distribution_shifted": bool(distribution_shifted),  # 确保是布尔值
                    "baseline_size": len(baseline_data),
                    "current_size": len(current_data),
                    "baseline_stats": baseline_stats,
                    "current_stats": current_stats,
                    "mean_difference": float(
                        current_stats["mean"] - baseline_stats["mean"]
                    ),
                    "std_difference": float(
                        current_stats["std"] - baseline_stats["std"]
                    ),
                }
            )

            # 如果检测到分布偏移，添加详细信息
            if distribution_shifted:
                result.add_anomalous_record(
                    {
                        "column": column_name,
                        "ks_statistic": float(ks_statistic),
                        "p_value": float(p_value),
                        "baseline_period": "historical",
                        "current_period": "recent",
                        "shift_type": "distribution_change",
                    }
                )

            # 记录数据漂移评分
            drift_score = min(1.0, ks_statistic * 2)  # 归一化到0-1
            data_drift_score.labels(
                table_name=table_name, feature_name=column_name
            ).set(drift_score)

            # 记录Prometheus指标
            if distribution_shifted:
                anomalies_detected_total.labels(
                    table_name=table_name,
                    anomaly_type="distribution_shift",
                    detection_method="ks_test",
                    severity=severity,
                ).inc()

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="ks_test"
            ).observe(duration)

            self.logger.info(
                f"分布偏移检测完成: {table_name}.{column_name}, "
                f"KS统计量={ks_statistic:.4f}, p值={p_value:.4f}, "
                f"偏移={'是' if distribution_shifted else '否'}"
            )

            return result

        except Exception as e:
            self.logger.error(f"分布偏移检测失败: {e}")
            raise

    def detect_outliers_iqr(
        self,
        data: pd.Series,
        table_name: str,
        column_name: str,
        iqr_multiplier: float = 1.5,
    ) -> AnomalyDetectionResult:
        """
        使用四分位距(IQR)方法检测异常值

        Args:
            data: 待检测的数据序列
            table_name: 表名
            column_name: 列名
            iqr_multiplier: IQR倍数，默认1.5

        Returns:
            AnomalyDetectionResult: 异常检测结果
        """
        start_time = datetime.now()

        try:
            # 计算四分位数
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1

            # 计算异常值阈值
            lower_bound = Q1 - iqr_multiplier * IQR
            upper_bound = Q3 + iqr_multiplier * IQR

            # 检测异常值
            outliers_mask = (data < lower_bound) | (data > upper_bound)
            outliers = data[outliers_mask]

            # 创建检测结果
            result = AnomalyDetectionResult(
                table_name=table_name,
                detection_method="iqr",
                anomaly_type="statistical_outlier",
                severity="medium" if len(outliers) < len(data) * 0.05 else "high",
            )

            # 添加异常记录
            for idx, value in outliers.items():
                result.add_anomalous_record(
                    {
                        "index": int(idx),
                        "column": column_name,
                        "value": float(value),
                        "iqr_distance": float(
                            max(lower_bound - value, value - upper_bound) / IQR
                        ),
                        "threshold_exceeded": (
                            "lower" if value < lower_bound else "upper"
                        ),
                    }
                )

            # 设置统计信息
            result.set_statistics(
                {
                    "total_records": len(data),
                    "outliers_count": len(outliers),
                    "outlier_rate": len(outliers) / len(data),
                    "Q1": float(Q1),
                    "Q3": float(Q3),
                    "IQR": float(IQR),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound),
                    "iqr_multiplier": iqr_multiplier,
                }
            )

            # 记录Prometheus指标
            anomalies_detected_total.labels(
                table_name=table_name,
                anomaly_type="statistical_outlier",
                detection_method="iqr",
                severity=result.severity,
            ).inc(len(outliers))

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="iqr"
            ).observe(duration)

            self.logger.info(
                f"IQR异常检测完成: {table_name}.{column_name}, "
                f"发现 {len(outliers)} 个异常值"
            )

            return result

        except Exception as e:
            self.logger.error(f"IQR异常检测失败: {e}")
            raise


class MachineLearningAnomalyDetector:
    """机器学习异常检测器"""

    def __init__(self):
        """初始化机器学习异常检测器"""
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")
        self.scaler = StandardScaler()
        self.isolation_forest = None
        self.dbscan = None

    def detect_anomalies_isolation_forest(
        self,
        data: pd.DataFrame,
        table_name: str,
        contamination: float = 0.1,
        random_state: int = 42,
    ) -> AnomalyDetectionResult:
        """
        使用Isolation Forest检测异常

        Args:
            data: 待检测的数据框
            table_name: 表名
            contamination: 预期异常比例，默认0.1
            random_state: 随机种子

        Returns:
            AnomalyDetectionResult: 异常检测结果
        """
        start_time = datetime.now()

        try:
            # 数据预处理
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) == 0:
                raise ValueError("没有可用的数值列进行异常检测")

            X = data[numeric_columns].fillna(data[numeric_columns].mean())
            X_scaled = self.scaler.fit_transform(X)

            # 训练Isolation Forest模型
            self.isolation_forest = IsolationForest(
                contamination=contamination, random_state=random_state, n_estimators=100
            )

            # 预测异常
            anomaly_labels = self.isolation_forest.fit_predict(X_scaled)
            anomaly_scores = self.isolation_forest.decision_function(X_scaled)

            # 获取异常记录
            anomalous_indices = np.where(anomaly_labels == -1)[0]

            # 确定严重程度
            anomaly_rate = len(anomalous_indices) / len(data)
            if anomaly_rate > 0.2:
                severity = "critical"
            elif anomaly_rate > 0.1:
                severity = "high"
            elif anomaly_rate > 0.05:
                severity = "medium"
            else:
                severity = "low"

            # 创建检测结果
            result = AnomalyDetectionResult(
                table_name=table_name,
                detection_method="isolation_forest",
                anomaly_type="ml_anomaly",
                severity=severity,
            )

            # 添加异常记录
            for idx in anomalous_indices:
                anomaly_record = {
                    "index": int(idx),
                    "anomaly_score": float(anomaly_scores[idx]),
                    "features": {},
                }

                # 添加特征值
                for col in numeric_columns:
                    anomaly_record["features"][col] = float(data.iloc[idx][col])

                result.add_anomalous_record(anomaly_record)

            # 设置统计信息
            result.set_statistics(
                {
                    "total_records": len(data),
                    "anomalies_count": len(anomalous_indices),
                    "anomaly_rate": anomaly_rate,
                    "contamination_param": contamination,
                    "features_used": list(numeric_columns),
                    "mean_anomaly_score": (
                        float(np.mean(anomaly_scores[anomalous_indices]))
                        if len(anomalous_indices) > 0
                        else 0.0
                    ),
                    "min_anomaly_score": float(np.min(anomaly_scores)),
                    "max_anomaly_score": float(np.max(anomaly_scores)),
                }
            )

            # 记录Prometheus指标
            anomalies_detected_total.labels(
                table_name=table_name,
                anomaly_type="ml_anomaly",
                detection_method="isolation_forest",
                severity=severity,
            ).inc(len(anomalous_indices))

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="isolation_forest"
            ).observe(duration)

            self.logger.info(
                f"Isolation Forest异常检测完成: {table_name}, "
                f"发现 {len(anomalous_indices)} 个异常 (异常率: {anomaly_rate:.2%})"
            )

            return result

        except Exception as e:
            self.logger.error(f"Isolation Forest异常检测失败: {e}")
            raise

    def detect_data_drift(
        self,
        baseline_data: pd.DataFrame,
        current_data: pd.DataFrame,
        table_name: str,
        drift_threshold: float = 0.1,
    ) -> List[AnomalyDetectionResult]:
        """
        检测数据漂移（Data Drift）

        Args:
            baseline_data: 基准数据集
            current_data: 当前数据集
            table_name: 表名
            drift_threshold: 漂移阈值

        Returns:
            List[AnomalyDetectionResult]: 检测结果列表
        """
        start_time = datetime.now()
        results = []

        try:
            # 获取数值列
            numeric_columns = baseline_data.select_dtypes(include=[np.number]).columns
            common_columns = list(set(numeric_columns) & set(current_data.columns))

            if len(common_columns) == 0:
                self.logger.warning(f"没有可比较的数值列: {table_name}")
                return results

            for column in common_columns:
                try:
                    # 获取列数据
                    baseline_col = baseline_data[column].dropna()
                    current_col = current_data[column].dropna()

                    if len(baseline_col) == 0 or len(current_col) == 0:
                        continue

                    # 计算统计差异
                    baseline_mean = baseline_col.mean()
                    current_mean = current_col.mean()
                    baseline_std = baseline_col.std()
                    current_std = current_col.std()

                    # 计算漂移评分
                    mean_drift = abs(current_mean - baseline_mean) / max(
                        abs(baseline_mean), 1e-8
                    )
                    std_drift = abs(current_std - baseline_std) / max(
                        baseline_std, 1e-8
                    )

                    # 综合漂移评分
                    drift_score = (mean_drift + std_drift) / 2

                    # 执行KS检验
                    ks_stat, p_value = stats.ks_2samp(baseline_col, current_col)

                    # 判断是否存在显著漂移
                    has_drift = (drift_score > drift_threshold) or (p_value < 0.05)

                    if has_drift:
                        # 确定严重程度
                        if drift_score > 0.5 or p_value < 0.001:
                            severity = "critical"
                        elif drift_score > 0.3 or p_value < 0.01:
                            severity = "high"
                        elif drift_score > 0.1 or p_value < 0.05:
                            severity = "medium"
                        else:
                            severity = "low"

                        # 创建检测结果
                        result = AnomalyDetectionResult(
                            table_name=table_name,
                            detection_method="data_drift",
                            anomaly_type="feature_drift",
                            severity=severity,
                        )

                        # 添加漂移记录
                        result.add_anomalous_record(
                            {
                                "column": column,
                                "drift_score": float(drift_score),
                                "mean_drift": float(mean_drift),
                                "std_drift": float(std_drift),
                                "ks_statistic": float(ks_stat),
                                "p_value": float(p_value),
                                "baseline_mean": float(baseline_mean),
                                "current_mean": float(current_mean),
                                "baseline_std": float(baseline_std),
                                "current_std": float(current_std),
                            }
                        )

                        # 设置统计信息
                        result.set_statistics(
                            {
                                "column": column,
                                "drift_score": float(drift_score),
                                "threshold": drift_threshold,
                                "baseline_size": len(baseline_col),
                                "current_size": len(current_col),
                                "mean_change_pct": float(mean_drift * 100),
                                "std_change_pct": float(std_drift * 100),
                                "ks_statistic": float(ks_stat),
                                "p_value": float(p_value),
                            }
                        )

                        results.append(result)

                        # 记录数据漂移评分
                        data_drift_score.labels(
                            table_name=table_name, feature_name=column
                        ).set(drift_score)

                        # 记录Prometheus指标
                        anomalies_detected_total.labels(
                            table_name=table_name,
                            anomaly_type="feature_drift",
                            detection_method="data_drift",
                            severity=severity,
                        ).inc()

                    else:
                        # 记录正常的漂移评分
                        data_drift_score.labels(
                            table_name=table_name, feature_name=column
                        ).set(drift_score)

                except Exception as col_error:
                    self.logger.warning(f"列 {column} 的漂移检测失败: {col_error}")
                    continue

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="data_drift"
            ).observe(duration)

            self.logger.info(
                f"数据漂移检测完成: {table_name}, "
                f"检测了 {len(common_columns)} 个特征, "
                f"发现 {len(results)} 个漂移特征"
            )

            return results

        except Exception as e:
            self.logger.error(f"数据漂移检测失败: {e}")
            raise

    def detect_anomalies_clustering(
        self,
        data: pd.DataFrame,
        table_name: str,
        eps: float = 0.5,
        min_samples: int = 5,
    ) -> AnomalyDetectionResult:
        """
        使用DBSCAN聚类检测异常

        Args:
            data: 待检测的数据框
            table_name: 表名
            eps: DBSCAN的邻域半径
            min_samples: 最小样本数

        Returns:
            AnomalyDetectionResult: 异常检测结果
        """
        start_time = datetime.now()

        try:
            # 数据预处理
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) == 0:
                raise ValueError("没有可用的数值列进行聚类异常检测")

            X = data[numeric_columns].fillna(data[numeric_columns].mean())
            X_scaled = self.scaler.fit_transform(X)

            # 执行DBSCAN聚类
            self.dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            cluster_labels = self.dbscan.fit_predict(X_scaled)

            # 噪声点（标签为-1）被认为是异常
            anomalous_indices = np.where(cluster_labels == -1)[0]

            # 确定严重程度
            anomaly_rate = len(anomalous_indices) / len(data)
            if anomaly_rate > 0.3:
                severity = "critical"
            elif anomaly_rate > 0.2:
                severity = "high"
            elif anomaly_rate > 0.1:
                severity = "medium"
            else:
                severity = "low"

            # 创建检测结果
            result = AnomalyDetectionResult(
                table_name=table_name,
                detection_method="dbscan_clustering",
                anomaly_type="clustering_outlier",
                severity=severity,
            )

            # 添加异常记录
            for idx in anomalous_indices:
                anomaly_record = {
                    "index": int(idx),
                    "cluster_label": int(cluster_labels[idx]),
                    "features": {},
                }

                # 添加特征值
                for col in numeric_columns:
                    anomaly_record["features"][col] = float(data.iloc[idx][col])

                result.add_anomalous_record(anomaly_record)

            # 计算聚类统计
            unique_clusters = np.unique(cluster_labels[cluster_labels != -1])

            # 设置统计信息
            result.set_statistics(
                {
                    "total_records": len(data),
                    "anomalies_count": len(anomalous_indices),
                    "anomaly_rate": anomaly_rate,
                    "num_clusters": len(unique_clusters),
                    "eps": eps,
                    "min_samples": min_samples,
                    "features_used": list(numeric_columns),
                    "largest_cluster_size": (
                        int(np.max(np.bincount(cluster_labels[cluster_labels != -1])))
                        if len(unique_clusters) > 0
                        else 0
                    ),
                }
            )

            # 记录Prometheus指标
            anomalies_detected_total.labels(
                table_name=table_name,
                anomaly_type="clustering_outlier",
                detection_method="dbscan_clustering",
                severity=severity,
            ).inc(len(anomalous_indices))

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="dbscan_clustering"
            ).observe(duration)

            self.logger.info(
                f"DBSCAN聚类异常检测完成: {table_name}, "
                f"发现 {len(anomalous_indices)} 个异常 (异常率: {anomaly_rate:.2%}), "
                f"共 {len(unique_clusters)} 个聚类"
            )

            return result

        except Exception as e:
            self.logger.error(f"DBSCAN聚类异常检测失败: {e}")
            raise


class AdvancedAnomalyDetector:
    """高级异常检测器 - 整合统计学和机器学习方法"""

    def __init__(self):
        """初始化高级异常检测器"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 初始化子检测器
        self.statistical_detector = StatisticalAnomalyDetector()
        self.ml_detector = MachineLearningAnomalyDetector()

        # 检测配置
        self.detection_config = {
            "matches": {
                "enabled_methods": ["3sigma", "iqr", "isolation_forest", "data_drift"],
                "key_columns": ["home_score", "away_score", "match_time"],
                "drift_baseline_days": 30,
            },
            "odds": {
                "enabled_methods": [
                    "3sigma",
                    "iqr",
                    "isolation_forest",
                    "distribution_shift",
                ],
                "key_columns": ["home_odds", "draw_odds", "away_odds"],
                "drift_baseline_days": 7,
            },
            "predictions": {
                "enabled_methods": ["3sigma", "clustering", "data_drift"],
                "key_columns": [
                    "home_win_probability",
                    "draw_probability",
                    "away_win_probability",
                ],
                "drift_baseline_days": 14,
            },
        }

    async def run_comprehensive_detection(
        self, table_name: str, time_window_hours: int = 24
    ) -> List[AnomalyDetectionResult]:
        """
        运行综合异常检测

        Args:
            table_name: 表名
            time_window_hours: 检测时间窗口（小时）

        Returns:
            List[AnomalyDetectionResult]: 异常检测结果列表
        """
        start_time = datetime.now()
        results = []

        try:
            self.logger.info(f"开始对表 {table_name} 进行综合异常检测")

            # 获取表配置
            if table_name not in self.detection_config:
                self.logger.warning(f"表 {table_name} 没有配置异常检测规则")
                return results

            config = self.detection_config[table_name]

            # 获取数据
            current_data = await self._get_table_data(table_name, time_window_hours)
            if current_data.empty:
                self.logger.warning(f"表 {table_name} 没有数据")
                return results

            # 更新覆盖率指标
            total_records = await self._get_total_records(table_name)
            coverage = len(current_data) / max(total_records, 1)
            anomaly_detection_coverage.labels(table_name=table_name).set(coverage)

            # 执行各种检测方法
            for method in config["enabled_methods"]:
                try:
                    if method == "3sigma":
                        results.extend(
                            await self._run_3sigma_detection(
                                table_name, current_data, config
                            )
                        )

                    elif method == "iqr":
                        results.extend(
                            await self._run_iqr_detection(
                                table_name, current_data, config
                            )
                        )

                    elif method == "isolation_forest":
                        if len(current_data) >= 10:  # 需要足够的数据
                            result = self.ml_detector.detect_anomalies_isolation_forest(
                                current_data, table_name
                            )
                            results.append(result)

                    elif method == "clustering":
                        if len(current_data) >= 20:  # 需要更多数据进行聚类
                            result = self.ml_detector.detect_anomalies_clustering(
                                current_data, table_name
                            )
                            results.append(result)

                    elif method == "data_drift":
                        drift_results = await self._run_data_drift_detection(
                            table_name, current_data, config
                        )
                        results.extend(drift_results)

                    elif method == "distribution_shift":
                        shift_results = await self._run_distribution_shift_detection(
                            table_name, current_data, config
                        )
                        results.extend(shift_results)

                except Exception as method_error:
                    self.logger.error(f"检测方法 {method} 执行失败: {method_error}")
                    continue

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            anomaly_detection_duration_seconds.labels(
                table_name=table_name, detection_method="comprehensive"
            ).observe(duration)

            self.logger.info(
                f"表 {table_name} 综合异常检测完成, "
                f"执行了 {len(config['enabled_methods'])} 种方法, "
                f"发现 {len(results)} 个异常结果, "
                f"耗时 {duration:.2f} 秒"
            )

            return results

        except Exception as e:
            self.logger.error(f"综合异常检测失败: {e}")
            raise

    async def _get_table_data(
        self, table_name: str, time_window_hours: int
    ) -> pd.DataFrame:
        """获取表数据"""
        try:
            # 检查数据库管理器是否已初始化
            if not self.db_manager or not hasattr(self.db_manager, "get_async_session"):
                self.logger.error("数据库连接未初始化，请先调用 initialize()")
                return pd.DataFrame()

            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

            async with self.db_manager.get_async_session() as session:
                if table_name == "matches":
                    query = text(
                        """
                        SELECT home_score, away_score, home_ht_score, away_ht_score,
                               minute, match_time, created_at, updated_at
                        FROM matches
                        WHERE updated_at >= :cutoff_time
                        ORDER BY updated_at DESC
                        LIMIT 1000
                    """
                    )
                elif table_name == "odds":
                    query = text(
                        """
                        SELECT home_odds, draw_odds, away_odds, over_odds, under_odds,
                               collected_at, created_at
                        FROM odds
                        WHERE collected_at >= :cutoff_time
                        ORDER BY collected_at DESC
                        LIMIT 1000
                    """
                    )
                elif table_name == "predictions":
                    query = text(
                        """
                        SELECT home_win_probability, draw_probability, away_win_probability,
                               confidence_score, created_at
                        FROM predictions
                        WHERE created_at >= :cutoff_time
                        ORDER BY created_at DESC
                        LIMIT 1000
                    """
                    )
                else:
                    return pd.DataFrame()

                result = await session.execute(query, {"cutoff_time": cutoff_time})
                rows = result.fetchall()

                if rows:
                    columns = result.keys()
                    return pd.DataFrame(rows, columns=columns)
                else:
                    return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取表 {table_name} 数据失败: {e}")
            return pd.DataFrame()

    async def _get_total_records(self, table_name: str) -> int:
        """获取表总记录数"""
        try:
            # 检查数据库管理器是否已初始化
            if not self.db_manager or not hasattr(self.db_manager, "get_async_session"):
                self.logger.error("数据库连接未初始化，请先调用 initialize()")
                return 0

            async with self.db_manager.get_async_session() as session:
                # Use whitelist validation to prevent SQL injection
                allowed_tables = ["matches", "odds", "predictions"]
                if table_name not in allowed_tables:
                    return 0

                # Use table mapping for safe query construction
                table_queries = {
                    "matches": text("SELECT COUNT(*) FROM matches"),
                    "odds": text("SELECT COUNT(*) FROM odds"),
                    "predictions": text("SELECT COUNT(*) FROM predictions"),
                }

                query = table_queries[table_name]
                result = await session.execute(query)
                count = result.scalar()
                return int(count) if count is not None else 0
        except Exception as e:
            self.logger.error(f"获取表 {table_name} 记录数失败: {e}")
            return 0

    async def _run_3sigma_detection(
        self, table_name: str, data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行3σ检测"""
        results = []
        for column in config["key_columns"]:
            if column in data.columns and data[column].dtype in ["int64", "float64"]:
                try:
                    result = self.statistical_detector.detect_outliers_3sigma(
                        data[column].dropna(), table_name, column
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"列 {column} 的3σ检测失败: {e}")
        return results

    async def _run_iqr_detection(
        self, table_name: str, data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行IQR检测"""
        results = []
        for column in config["key_columns"]:
            if column in data.columns and data[column].dtype in ["int64", "float64"]:
                try:
                    result = self.statistical_detector.detect_outliers_iqr(
                        data[column].dropna(), table_name, column
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"列 {column} 的IQR检测失败: {e}")
        return results

    async def _run_data_drift_detection(
        self, table_name: str, current_data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行数据漂移检测"""
        try:
            # 获取基准数据
            baseline_days = config.get(str("drift_baseline_days"), 30)
            baseline_data = await self._get_baseline_data(table_name, baseline_days)

            if baseline_data.empty:
                self.logger.warning(f"表 {table_name} 没有足够的基准数据进行漂移检测")
                return []

            return self.ml_detector.detect_data_drift(
                baseline_data, current_data, table_name
            )

        except Exception as e:
            self.logger.error(f"数据漂移检测失败: {e}")
            return []

    async def _run_distribution_shift_detection(
        self, table_name: str, current_data: pd.DataFrame, config: Dict[str, Any]
    ) -> List[AnomalyDetectionResult]:
        """运行分布偏移检测"""
        results = []
        try:
            # 获取基准数据
            baseline_days = config.get(str("drift_baseline_days"), 30)
            baseline_data = await self._get_baseline_data(table_name, baseline_days)

            if baseline_data.empty:
                return results

            for column in config["key_columns"]:
                if column in current_data.columns and column in baseline_data.columns:
                    if current_data[column].dtype in [
                        "int64",
                        "float64",
                    ] and baseline_data[column].dtype in ["int64", "float64"]:
                        try:
                            result = (
                                self.statistical_detector.detect_distribution_shift(
                                    baseline_data[column].dropna(),
                                    current_data[column].dropna(),
                                    table_name,
                                    column,
                                )
                            )
                            results.append(result)
                        except Exception as e:
                            self.logger.warning(f"列 {column} 的分布偏移检测失败: {e}")

            return results

        except Exception as e:
            self.logger.error(f"分布偏移检测失败: {e}")
            return []

    async def _get_baseline_data(
        self, table_name: str, baseline_days: int
    ) -> pd.DataFrame:
        """获取基准数据"""
        try:
            start_time = datetime.now() - timedelta(days=baseline_days + 7)
            end_time = datetime.now() - timedelta(days=7)

            async with self.db_manager.get_async_session() as session:
                if table_name == "matches":
                    query = """
                        SELECT home_score, away_score, home_ht_score, away_ht_score,
                               minute, match_time
                        FROM matches
                        WHERE updated_at BETWEEN %s AND %s
                        ORDER BY updated_at
                        LIMIT 2000
                    """
                elif table_name == "odds":
                    query = """
                        SELECT home_odds, draw_odds, away_odds, over_odds, under_odds
                        FROM odds
                        WHERE collected_at BETWEEN %s AND %s
                        ORDER BY collected_at
                        LIMIT 2000
                    """
                elif table_name == "predictions":
                    query = """
                        SELECT home_win_probability, draw_probability, away_win_probability,
                               confidence_score
                        FROM predictions
                        WHERE created_at BETWEEN %s AND %s
                        ORDER BY created_at
                        LIMIT 2000
                    """
                else:
                    return pd.DataFrame()

                result = await session.execute(query, (start_time, end_time))
                rows = result.fetchall()

                if rows:
                    columns = result.keys()
                    return pd.DataFrame(rows, columns=columns)
                else:
                    return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取基准数据失败: {e}")
            return pd.DataFrame()

    async def get_anomaly_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取异常检测摘要

        Args:
            hours: 时间窗口（小时）

        Returns:
            Dict[str, Any]: 异常检测摘要
        """
        try:
            # 运行各表的异常检测
            all_results = {}
            for table_name in self.detection_config.keys():
                results = await self.run_comprehensive_detection(table_name, hours)
                all_results[table_name] = results

            # 生成摘要
            summary = {
                "detection_period": {
                    "hours": hours,
                    "start_time": (datetime.now() - timedelta(hours=hours)).isoformat(),
                    "end_time": datetime.now().isoformat(),
                },
                "tables_analyzed": list(self.detection_config.keys()),
                "total_anomalies": sum(
                    len(results) for results in all_results.values()
                ),
                "anomalies_by_table": {},
                "anomalies_by_severity": {
                    "low": 0,
                    "medium": 0,
                    "high": 0,
                    "critical": 0,
                },
                "anomalies_by_method": {},
                "anomalies_by_type": {},
            }

            # 统计各表异常
            for table_name, results in all_results.items():
                table_summary = {
                    "total_anomalies": len(results),
                    "methods_used": list(set(r.detection_method for r in results)),
                    "severity_breakdown": {
                        "low": 0,
                        "medium": 0,
                        "high": 0,
                        "critical": 0,
                    },
                    "anomaly_types": list(set(r.anomaly_type for r in results)),
                }

                for result in results:
                    # 按严重程度统计
                    severity = result.severity
                    table_summary["severity_breakdown"][severity] += 1
                    summary["anomalies_by_severity"][severity] += 1

                    # 按方法统计
                    method = result.detection_method
                    if method not in summary["anomalies_by_method"]:
                        summary["anomalies_by_method"][method] = 0
                    summary["anomalies_by_method"][method] += 1

                    # 按类型统计
                    anomaly_type = result.anomaly_type
                    if anomaly_type not in summary["anomalies_by_type"]:
                        summary["anomalies_by_type"][anomaly_type] = 0
                    summary["anomalies_by_type"][anomaly_type] += 1

                summary["anomalies_by_table"][table_name] = table_summary

            return summary

        except Exception as e:
            self.logger.error(f"生成异常检测摘要失败: {e}")
            raise
