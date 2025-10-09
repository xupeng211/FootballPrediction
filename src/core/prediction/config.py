"""
预测引擎配置
Prediction Engine Configuration

管理预测引擎的配置参数。
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PredictionConfig:
    """预测引擎配置类"""

    # MLflow配置
    mlflow_tracking_uri: str

    # 并发控制
    max_concurrent_predictions: int

    # 超时设置
    prediction_timeout: float

    # 缓存配置
    cache_warmup_enabled: bool
    cache_ttl_predictions: int
    cache_ttl_features: int
    cache_ttl_odds: int

    # 性能阈值
    performance_warning_threshold: float
    performance_error_threshold: float

    @classmethod
    def from_env(cls) -> "PredictionConfig":
        """从环境变量创建配置"""
        return cls(
            mlflow_tracking_uri=os.getenv(
                "MLFLOW_TRACKING_URI", "http://localhost:5002"
            ),
            max_concurrent_predictions=int(
                os.getenv("MAX_CONCURRENT_PREDICTIONS", "10")
            ),
            prediction_timeout=float(
                os.getenv("PREDICTION_TIMEOUT", "30.0")
            ),
            cache_warmup_enabled=(
                os.getenv("CACHE_WARMUP_ENABLED", "true").lower() == "true"
            ),
            cache_ttl_predictions=int(
                os.getenv("CACHE_TTL_PREDICTIONS", "3600")
            ),
            cache_ttl_features=int(
                os.getenv("CACHE_TTL_FEATURES", "1800")
            ),
            cache_ttl_odds=int(
                os.getenv("CACHE_TTL_ODDS", "300")
            ),
            performance_warning_threshold=float(
                os.getenv("PERFORMANCE_WARNING_THRESHOLD", "5.0")
            ),
            performance_error_threshold=float(
                os.getenv("PERFORMANCE_ERROR_THRESHOLD", "10.0")
            ),
        )

    @classmethod
    def create(
        cls,
        mlflow_tracking_uri: Optional[str] = None,
        max_concurrent_predictions: Optional[int] = None,
        prediction_timeout: Optional[float] = None,
        cache_warmup_enabled: Optional[bool] = None,
    ) -> "PredictionConfig":
        """创建配置实例"""
        config = cls.from_env()

        if mlflow_tracking_uri:
            config.mlflow_tracking_uri = mlflow_tracking_uri
        if max_concurrent_predictions:
            config.max_concurrent_predictions = max_concurrent_predictions
        if prediction_timeout:
            config.prediction_timeout = prediction_timeout
        if cache_warmup_enabled is not None:
            config.cache_warmup_enabled = cache_warmup_enabled

        return config