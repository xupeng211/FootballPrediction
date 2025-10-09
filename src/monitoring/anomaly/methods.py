"""
异常检测方法
Anomaly Detection Methods

实现各种异常检测算法。
"""




logger = logging.getLogger(__name__)


class BaseDetector:
    """检测器基类"""

    def __init__(self, name: str):
        """初始化检测器"""
        self.name = name

    def _calculate_severity(self, anomaly_score: float) -> AnomalySeverity:
        """
        计算异常严重程度

        Args:
            anomaly_score: 异常得分（0-1）

        Returns:
            AnomalySeverity: 严重程度
        """
        if anomaly_score >= 0.2:
            return AnomalySeverity.CRITICAL
        elif anomaly_score >= 0.1:
            return AnomalySeverity.HIGH
        elif anomaly_score >= 0.05:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW


class ThreeSigmaDetector(BaseDetector):
    """3σ规则异常检测器"""

    def __init__(self):
        super().__init__("3sigma")

    def detect(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        3σ规则异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            mean = data.mean()
            std = data.std()

            if std == 0:
                return []  # 无变化数据不检测异常

            # 3σ异常阈值
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std

            # 检测异常值
            outliers = data[(data < lower_bound) | (data > upper_bound)]

            if len(outliers) > 0:
                # 计算异常得分
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.OUTLIER,
                        severity=severity,
                        anomalous_values=outliers.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="3sigma",
                        description=f"发现 {len(outliers)} 个3σ规则异常值，超出范围 [{lower_bound:.2f}, {upper_bound:.2f}]",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"3σ规则检测失败 {table_name}.{column_name}: {e}")
            return []


class IQRDetector(BaseDetector):
    """IQR方法异常检测器"""

    def __init__(self):
        super().__init__("iqr")

    def detect(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        IQR方法异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1

            if IQR == 0:
                return []  # IQR为0时不检测异常

            # IQR异常阈值
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # 检测异常值
            outliers = data[(data < lower_bound) | (data > upper_bound)]

            if len(outliers) > 0:
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.OUTLIER,
                        severity=severity,
                        anomalous_values=outliers.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="iqr",
                        description=f"发现 {len(outliers)} 个IQR方法异常值，超出范围 [{lower_bound:.2f}, {upper_bound:.2f}]",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"IQR方法检测失败 {table_name}.{column_name}: {e}")
            return []


class ZScoreDetector(BaseDetector):
    """Z-score异常检测器"""

    def __init__(self, threshold: float = 3.0):
        super().__init__("z_score")
        self.threshold = threshold

    def detect(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        Z-score异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            mean = data.mean()
            std = data.std()

            if std == 0:
                return []

            # 计算Z-score
            z_scores = np.abs((data - mean) / std)

            # 检测异常值
            outliers = data[z_scores > self.threshold]
            outlier_scores = z_scores[z_scores > self.threshold]

            if len(outliers) > 0:
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.OUTLIER,
                        severity=severity,
                        anomalous_values=outliers.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="z_score",
                        description=f"发现 {len(outliers)} 个Z-score异常值，最大Z-score: {outlier_scores.max():.2f}",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"Z-score检测失败 {table_name}.{column_name}: {e}")
            return []


class RangeDetector(BaseDetector):
    """范围检查异常检测器"""

    def __init__(self, thresholds: dict):
        super().__init__("range_check")
        self.thresholds = thresholds

    def detect(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        范围检查异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            # 获取列的阈值
            column_thresholds = self.thresholds.get(str(column_name), {})

            if not column_thresholds:
                return []

            min_val = column_thresholds.get("min")
            max_val = column_thresholds.get("max")

            outliers = []

            if min_val is not None:
                outliers.extend(data[data < min_val].tolist())

            if max_val is not None:
                outliers.extend(data[data > max_val].tolist())

            if len(outliers) > 0:
                anomaly_score = len(outliers) / len(data)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.VALUE_RANGE,
                        severity=severity,
                        anomalous_values=outliers,
                        anomaly_score=anomaly_score,
                        detection_method="range_check",
                        description=f"发现 {len(outliers)} 个范围异常值，预期范围: [{min_val}, {max_val}]",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"范围检查失败 {table_name}.{column_name}: {e}")
            return []


class FrequencyDetector(BaseDetector):
    """频率分布异常检测器"""

    def __init__(self):
        super().__init__("frequency")

    def detect(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        频率分布异常检测

        Args:
            data: 数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            # 计算值频率
            value_counts = data.value_counts()
            total_count = len(data)

            # 检测频率异常（出现次数过少或过多）
            expected_freq = total_count / len(value_counts)  # 平均频率

            anomalous_values = []
            for value, count in value_counts.items():
                # 频率异常：大于平均频率的5倍或小于平均频率的1/10
                if count > expected_freq * 5 or count < expected_freq * 0.1:
                    anomalous_values.append(value)

            if len(anomalous_values) > 0:
                anomaly_score = len(anomalous_values) / len(value_counts)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.FREQUENCY,
                        severity=severity,
                        anomalous_values=anomalous_values,
                        anomaly_score=anomaly_score,
                        detection_method="frequency",
                        description=f"发现 {len(anomalous_values)} 个频率异常值，预期频率: {expected_freq:.1f}",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"频率检测失败 {table_name}.{column_name}: {e}")
            return []


class TimeGapDetector(BaseDetector):
    """时间间隔异常检测器"""

    def __init__(self):
        super().__init__("time_gap")

    def detect(
        self, data: pd.Series, table_name: str, column_name: str
    ) -> List[AnomalyResult]:
        """
        时间间隔异常检测

        Args:
            data: 时间数据序列
            table_name: 表名
            column_name: 列名

        Returns:
            List[AnomalyResult]: 异常结果
        """
        try:
            # 转换为时间戳并排序
            time_data = pd.to_datetime(data).sort_values()

            if len(time_data) < 2:



                return []

            # 计算时间间隔
            time_diffs = time_data.diff().dt.total_seconds().dropna()

            # 使用IQR方法检测时间间隔异常
            Q1 = time_diffs.quantile(0.25)
            Q3 = time_diffs.quantile(0.75)
            IQR = Q3 - Q1

            if IQR == 0:
                return []

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # 检测异常时间间隔
            anomalous_gaps = time_diffs[
                (time_diffs < lower_bound) | (time_diffs > upper_bound)
            ]

            if len(anomalous_gaps) > 0:
                anomaly_score = len(anomalous_gaps) / len(time_diffs)
                severity = self._calculate_severity(anomaly_score)

                return [
                    AnomalyResult(
                        table_name=table_name,
                        column_name=column_name,
                        anomaly_type=AnomalyType.PATTERN_BREAK,
                        severity=severity,
                        anomalous_values=anomalous_gaps.tolist(),
                        anomaly_score=anomaly_score,
                        detection_method="time_gap",
                        description=f"发现 {len(anomalous_gaps)} 个时间间隔异常，正常范围: {lower_bound:.0f}-{upper_bound:.0f}秒",
                    )
                ]

            return []

        except Exception as e:
            logger.error(f"时间间隔检测失败 {table_name}.{column_name}: {e}")
            return []