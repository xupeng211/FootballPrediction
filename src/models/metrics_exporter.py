







        """初始化Prometheus指标"""


































模型指标导出器
提供Prometheus指标导出功能,监控模型性能和预测质量
logger = logging.getLogger(__name__)
class ModelMetricsExporter:
    模型指标导出器
    提供模型性能监控指标导出,包括:
    - 预测数量统计
    - 预测准确率监控
    - 置信度分布
    - 响应时间监控
    def __init__(self, registry=None):
        # 使用自定义registry避免重复注册错误
        if registry is None:
            # 在测试环境中创建新的registry,避免重复注册
            self.registry = CollectorRegistry()
        else:
            self.registry = registry
        # 预测指标
        self.predictions_total = Counter(
            "football_predictions_total",
            "Total number of predictions made",
            ["model_name", "model_version", "predicted_result"],
            registry=self.registry,
        )
        # 预测准确率
        self.prediction_accuracy = Gauge(
            "football_prediction_accuracy",
            "Model prediction accuracy",
            ["model_name", "model_version", "time_window"],
            registry=self.registry,
        )
        # 预测置信度分布
        self.prediction_confidence = Histogram(
            "football_prediction_confidence_score",
            "Distribution of prediction confidence scores",
            ["model_name", "model_version"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry,
        )
        # 模型响应时间
        self.prediction_duration = Histogram(
            "football_model_prediction_duration_seconds",
            "Time spent making predictions",
            ["model_name", "model_version"],
            registry=self.registry,
        )
        # 模型覆盖率
        self.model_coverage_rate = Gauge(
            "football_model_coverage_rate",
            "Percentage of matches with predictions",
            ["model_name", "model_version"],
            registry=self.registry,
        )
        # 每日预测数量
        self.daily_predictions_count = Counter(
            "football_daily_predictions_count",
            "Number of predictions per day",
            ["model_name", "date"],
            registry=self.registry,
        )
        # 模型加载时间
        self.model_load_duration = Histogram(
            "football_model_load_duration_seconds",
            "Time spent loading models",
            ["model_name", "model_version"],
            registry=self.registry,
        )
        # 预测错误数量
        self.prediction_errors_total = Counter(
            "football_prediction_errors_total",
            "Total number of prediction errors",
            ["model_name", "model_version", "error_type"],
            registry=self.registry,
        )
    def export_prediction_metrics(self, result: Any) -> None:
        导出预测指标
        Args:
            result: PredictionResult对象
        try:
            # 预测总数
            self.predictions_total.labels(
                model_name=result.model_name,
                model_version=result.model_version,
                predicted_result=result.predicted_result,
            ).inc()
            # 预测置信度
            self.prediction_confidence.labels(
                model_name=result.model_name, model_version=result.model_version
            ).observe(result.confidence_score)
            # 每日预测数量
            today = datetime.now().strftime("%Y-%m-%d")
            self.daily_predictions_count.labels(
                model_name=result.model_name, date=today
            ).inc()
            logger.debug(
                f"已导出预测指标:match_id={result.match_id}, result={result.predicted_result}"
            )
        except Exception as e:
            logger.error(f"导出预测指标失败: {e}")
    def export_accuracy_metrics(
        self,
        model_name: str,
        model_version: str,
        accuracy: float,
        time_window: str = "7d",
    ) -> None:
        导出准确率指标
        Args:
            model_name: 模型名称
            model_version: 模型版本
            accuracy: 准确率 (0-1)
            time_window: 时间窗口
        try:
            self.prediction_accuracy.labels(
                model_name=model_name,
                model_version=model_version,
                time_window=time_window,
            ).set(accuracy)
            logger.debug(
                f"已导出准确率指标:{model_name} v{model_version} = {accuracy:.3f}"
            )
        except Exception as e:
            logger.error(f"导出准确率指标失败: {e}")
    def export_duration_metrics(
        self, model_name: str, model_version: str, duration: float
    ) -> None:
        导出响应时间指标
        Args:
            model_name: 模型名称
            model_version: 模型版本
            duration: 持续时间(秒)
        try:
            self.prediction_duration.labels(
                model_name=model_name, model_version=model_version
            ).observe(duration)
        except Exception as e:
            logger.error(f"导出响应时间指标失败: {e}")
    def export_coverage_metrics(
        self, model_name: str, model_version: str, coverage_rate: float
    ) -> None:
        导出模型覆盖率指标
        Args:
            model_name: 模型名称
            model_version: 模型版本
            coverage_rate: 覆盖率 (0-1)
        try:
            self.model_coverage_rate.labels(
                model_name=model_name, model_version=model_version
            ).set(coverage_rate)
        except Exception as e:
            logger.error(f"导出覆盖率指标失败: {e}")
    def export_error_metrics(
        self, model_name: str, model_version: str, error_type: str
    ) -> None:
        导出错误指标
        Args:
            model_name: 模型名称
            model_version: 模型版本
            error_type: 错误类型
        try:
            self.prediction_errors_total.labels(
                model_name=model_name,
                model_version=model_version,
                error_type=error_type,
            ).inc()
        except Exception as e:
            logger.error(f"导出错误指标失败: {e}")
    def export_model_load_duration(
        self, model_name: str, model_version: str, duration: float
    ) -> None:
        导出模型加载时间指标
        Args:
            model_name: 模型名称
            model_version: 模型版本
            duration: 加载时间(秒)
        try:
            self.model_load_duration.labels(
                model_name=model_name, model_version=model_version
            ).observe(duration)
        except Exception as e:
            logger.error(f"导出模型加载时间指标失败: {e}")
    def get_metrics_summary(self) -> Dict[str, Any]:
        获取指标摘要
        Returns:
            指标摘要字典
        try:
            return {
                "predictions_total": "预测总数统计",
                "prediction_accuracy": "预测准确率监控", Dict, cast
                "prediction_confidence": "预测置信度分布",
                "prediction_duration": "预测响应时间",
                "model_coverage_rate": "模型覆盖率",
                "daily_predictions_count": "每日预测数量",
                "model_load_duration": "模型加载时间",
                "prediction_errors_total": "预测错误统计",
            }
        except Exception as e:
            logger.error(f"获取指标摘要失败: {e}")
            return {}