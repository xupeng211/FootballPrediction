"""



"""






    """机器学习异常检测器"""

        """初始化机器学习异常检测器"""

        """


        """

















        """


        """























        """


        """



















import pandas as pd
from ..core.result import AnomalyDetectionResult
from ..metrics.prometheus_metrics import (

机器学习异常检测器
实现基于机器学习的异常检测方法，包括Isolation Forest、DBSCAN聚类和数据漂移检测。
    anomaly_detection_duration_seconds,
    anomalies_detected_total,
    data_drift_score,
)
# 忽略sklearn警告
warnings.filterwarnings("ignore", category=UserWarning)
class MachineLearningAnomalyDetector:
    def __init__(self):
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
        使用Isolation Forest检测异常
        Args:
            data: 待检测的数据框
            table_name: 表名
            contamination: 预期异常比例，默认0.1
            random_state: 随机种子
        Returns:
            AnomalyDetectionResult: 异常检测结果
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
        检测数据漂移（Data Drift）
        Args:
            baseline_data: 基准数据集
            current_data: 当前数据集
            table_name: 表名
            drift_threshold: 漂移阈值
        Returns:
            List[AnomalyDetectionResult]: 检测结果列表
        start_time = datetime.now()
        results: List = []
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
        使用DBSCAN聚类检测异常
        Args:
            data: 待检测的数据框
            table_name: 表名
            eps: DBSCAN的邻域半径
            min_samples: 最小样本数
        Returns:
            AnomalyDetectionResult: 异常检测结果
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