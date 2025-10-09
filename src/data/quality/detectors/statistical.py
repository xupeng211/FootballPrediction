"""


"""






    """统计学异常检测器"""

        """

        """

        """


        """




















        """


        """















        """


        """














from .metrics import (

统计学异常检测器
Statistical Anomaly Detector
实现基于统计学的异常检测方法，包括：
- 3σ规则检测
- 分布偏移检测（Kolmogorov-Smirnov检验）
- 四分位距(IQR)异常值检测
    anomalies_detected_total,
    data_drift_score,
    anomaly_detection_duration_seconds,
)
# 忽略sklearn警告
warnings.filterwarnings("ignore", category=UserWarning)
class StatisticalAnomalyDetector:
    def __init__(self, sigma_threshold: float = 3.0):
        初始化统计学异常检测器
        Args:
            sigma_threshold: 3σ规则的阈值，默认为3.0
        self.sigma_threshold = sigma_threshold
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")
    def detect_outliers_3sigma(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> AnomalyDetectionResult:
        使用3σ规则检测异常值
        Args:
            data: 待检测的数据序列
            table_name: 表名
            column_name: 列名
        Returns:
            AnomalyDetectionResult: 异常检测结果
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
        使用Kolmogorov-Smirnov检验检测分布偏移
        Args:
            baseline_data: 基准数据
            current_data: 当前数据
            table_name: 表名
            column_name: 列名
            significance_level: 显著性水平，默认0.05
        Returns:
            AnomalyDetectionResult: 异常检测结果
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
        使用四分位距(IQR)方法检测异常值
        Args:
            data: 待检测的数据序列
            table_name: 表名
            column_name: 列名
            iqr_multiplier: IQR倍数，默认1.5
        Returns:
            AnomalyDetectionResult: 异常检测结果
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