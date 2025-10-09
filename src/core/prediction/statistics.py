"""
预测统计信息
Prediction Statistics

管理预测引擎的性能统计。
"""



@dataclass
class PredictionStatistics:
    """预测统计信息类"""

    total_predictions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    prediction_errors: int = 0
    avg_prediction_time: float = 0.0
    total_prediction_time: float = 0.0
    last_prediction_time: Optional[float] = None
    min_prediction_time: float = float("inf")
    max_prediction_time: float = 0.0

    # 额外统计信息
    batch_predictions: int = 0
    concurrent_predictions: int = 0
    cache_warmups: int = 0

    # 错误统计
    timeout_errors: int = 0
    data_errors: int = 0
    model_errors: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.total_predictions == 0:
            return 0.0
        return (self.prediction_errors / self.total_predictions) * 100

    @property
    def predictions_per_second(self) -> float:
        """每秒预测数"""
        if self.total_prediction_time == 0:
            return 0.0
        return self.total_predictions / self.total_prediction_time

    def record_prediction(self, prediction_time: float):
        """记录一次预测"""
        self.total_predictions += 1
        self.total_prediction_time += prediction_time
        self.last_prediction_time = time.time()
        self.min_prediction_time = min(self.min_prediction_time, prediction_time)
        self.max_prediction_time = max(self.max_prediction_time, prediction_time)

        # 更新平均预测时间
        self.avg_prediction_time = self.total_prediction_time / self.total_predictions

    def record_cache_hit(self):
        """记录缓存命中"""
        self.cache_hits += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.cache_misses += 1

    def record_error(self, error_type: str = "unknown"):
        """记录错误"""
        self.prediction_errors += 1
        if error_type == "timeout":
            self.timeout_errors += 1
        elif error_type == "data":
            self.data_errors += 1
        elif error_type == "model":
            self.model_errors += 1

    def record_batch_prediction(self, count: int):
        """记录批量预测"""
        self.batch_predictions += count
        self.total_predictions += count

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "total_predictions": float(self.total_predictions),
            "cache_hits": float(self.cache_hits),
            "cache_misses": float(self.cache_misses),
            "prediction_errors": float(self.prediction_errors),
            "avg_prediction_time": self.avg_prediction_time,
            "cache_hit_rate": self.cache_hit_rate,
            "error_rate": self.error_rate,
            "predictions_per_second": self.predictions_per_second,
            "min_prediction_time": self.min_prediction_time
            if self.min_prediction_time != float("inf")
            else 0.0,
            "max_prediction_time": self.max_prediction_time,
            "batch_predictions": float(self.batch_predictions),
            "concurrent_predictions": float(self.concurrent_predictions),
            "cache_warmups": float(self.cache_warmups),
            "timeout_errors": float(self.timeout_errors),
            "data_errors": float(self.data_errors),
            "model_errors": float(self.model_errors),
        }

    def reset(self):
        """重置统计信息"""
        self.total_predictions = 0
        self.cache_hits = 0
            "model_errors": float(self.model_errors),)

        self.prediction_errors = 0
        self.avg_prediction_time = 0.0
        self.total_prediction_time = 0.0
        self.last_prediction_time = None
        self.min_prediction_time = float("inf")
        self.max_prediction_time = 0.0
        self.batch_predictions = 0
        self.concurrent_predictions = 0
        self.cache_warmups = 0
        self.timeout_errors = 0
        self.data_errors = 0
        self.model_errors = 0