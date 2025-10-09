"""

"""




    """业务指标收集器

    """

        """

        """



        """

        """







        """

        """





        """

        """



        """

        """




        """

        """


        """

        """




业务指标收集器 / Business Metrics Collector
收集和管理业务相关的指标，如预测数量、准确率等。
class BusinessMetricsCollector:
    负责收集与业务逻辑相关的各项指标。
    def __init__(self, prometheus_manager: PrometheusMetricsManager, aggregator):
        初始化业务指标收集器
        Args:
            prometheus_manager: Prometheus指标管理器
            aggregator: 指标聚合器
        self.prometheus = prometheus_manager
        self.aggregator = aggregator
        # 业务计数器
        self.predictions_total = 0
        self.predictions_correct = 0
        self.predictions_verified = 0
        self.model_loads = 0
        # 按模型统计
        self.model_stats: Dict[str, Dict[str, Any]] = {}
    def record_prediction(
        self,
        model_version: str,
        predicted_result: str,
        confidence: float,
        duration: float,
        success: bool = True,
    ):
        记录预测指标
        Args:
            model_version: 模型版本
            predicted_result: 预测结果
            confidence: 置信度
            duration: 预测耗时
            success: 是否成功
        # 更新计数
        self.predictions_total += 1
        # 更新模型统计
        if model_version not in self.model_stats:
            self.model_stats[model_version] = {
                "predictions": 0,
                "total_duration": 0.0,
                "last_prediction": None,
            }
        self.model_stats[model_version]["predictions"] += 1
        self.model_stats[model_version]["total_duration"] += duration
        self.model_stats[model_version]["last_prediction"] = datetime.now()
        # 更新Prometheus指标
        self.prometheus.increment_counter(
            "prediction_counter",
            labels={"model_version": model_version, "result": predicted_result}
        )
        self.prometheus.observe_histogram(
            "request_duration",
            duration,
            labels={"endpoint": "/predict", "method": "POST"}
        )
        # 记录到聚合器
        metric = MetricPoint(
            name="prediction_duration",
            value=duration,
            labels={"model_version": model_version},
            unit="seconds",
        )
        self.aggregator.add_metric(metric)
        # 记录置信度
        confidence_metric = MetricPoint(
            name="prediction_confidence",
            value=confidence,
            labels={"model_version": model_version, "result": predicted_result},
            unit="ratio",
        )
        self.aggregator.add_metric(confidence_metric)
    def record_prediction_verification(
        self, model_version: str, is_correct: bool, time_window: str = "1h"
    ):
        记录预测验证指标
        Args:
            model_version: 模型版本
            is_correct: 是否正确
            time_window: 时间窗口
        self.predictions_verified += 1
        if is_correct:
            self.predictions_correct += 1
        # 计算准确率
        if self.predictions_verified > 0:
            accuracy = self.predictions_correct / self.predictions_verified
            # 更新Prometheus
            self.prometheus.set_gauge(
                "prediction_accuracy",
                accuracy,
                labels={"model_version": model_version, "time_window": time_window}
            )
            # 记录到聚合器
            metric = MetricPoint(
                name="prediction_accuracy",
                value=accuracy,
                labels={"model_version": model_version, "window": time_window},
                unit="ratio",
            )
            self.aggregator.add_metric(metric)
            # 更新模型统计
            if model_version in self.model_stats:
                self.model_stats[model_version]["accuracy"] = accuracy
    def record_model_load(
        self, model_name: str, model_version: str, success: bool, load_time: float
    ):
        记录模型加载指标
        Args:
            model_name: 模型名称
            model_version: 模型版本
            success: 是否成功
            load_time: 加载耗时
        status = "success" if success else "failed"
        self.model_loads += 1
        # 更新Prometheus
        self.prometheus.increment_counter(
            "model_load_counter",
            labels={"model_name": model_name, "status": status}
        )
        # 记录到聚合器
        metric = MetricPoint(
            name="model_load_time",
            value=load_time,
            labels={
                "model_name": model_name,
                "model_version": model_version,
                "status": status,
            },
            unit="seconds",
        )
        self.aggregator.add_metric(metric)
    def record_data_collection(
        self, source: str, data_type: str, records: int, success: bool, duration: float
    ):
        记录数据收集指标
        Args:
            source: 数据源
            data_type: 数据类型
            records: 记录数
            success: 是否成功
            duration: 耗时
        status = "success" if success else "failed"
        # 更新Prometheus
        self.prometheus.increment_counter(
            "data_collection_counter",
            labels={"source": source, "status": status}
        )
        # 记录吞吐量
        if duration > 0 and success:
            throughput = records / duration
            metric = MetricPoint(
                name="data_collection_throughput",
                value=throughput,
                labels={"source": source, "data_type": data_type},
                unit="records/sec",
            )
            self.aggregator.add_metric(metric)
        # 记录数据量
        metric = MetricPoint(
            name="data_collection_volume",
            value=records,
            labels={"source": source, "data_type": data_type, "status": status},
            unit="records",
        )
        self.aggregator.add_metric(metric)
    def record_value_bet(
        self, bookmaker: str, confidence_level: str, expected_value: float
    ):
        记录价值投注指标
        Args:
            bookmaker: 博彩公司
            confidence_level: 置信度级别
            expected_value: 期望值
        # 更新Prometheus
        self.prometheus.increment_counter(
            "value_bets_counter",
            labels={"confidence_level": confidence_level}
        )
        # 记录到聚合器
        metric = MetricPoint(
            name="value_bet_ev",
            value=expected_value,
            labels={"bookmaker": bookmaker, "confidence_level": confidence_level},
            unit="ratio",
        )
        self.aggregator.add_metric(metric)
    def get_business_summary(self) -> Dict[str, Any]:
        获取业务指标摘要
        Returns:
            业务指标摘要字典
        summary = {
            "predictions": {
                "total": self.predictions_total,
                "correct": self.predictions_correct, Any
                "verified": self.predictions_verified,
                "accuracy": (
                    self.predictions_correct / self.predictions_verified
                    if self.predictions_verified > 0
                    else 0
                ),
            },
            "models": {
                "total_loads": self.model_loads,
                "active_models": len(self.model_stats),
                "model_details": self.model_stats,
            },
            "last_updated": datetime.now().isoformat(),
        }
        # 添加每个模型的平均延迟
        for model_version, stats in self.model_stats.items():
            if stats["predictions"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["predictions"]
            else:
                stats["avg_duration"] = 0
        return summary