"""
预测服务配置

定义预测服务的配置参数和重试配置
"""



# MLflow重试配置 / MLflow retry configuration
# Import moved to top

try:

    MLFLOW_RETRY_CONFIG = RetryConfig(
        max_attempts=int(os.getenv("MLFLOW_RETRY_MAX_ATTEMPTS", "3")),
        base_delay=float(os.getenv("MLFLOW_RETRY_BASE_DELAY", "2.0")),
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=(MlflowException, ConnectionError, TimeoutError),
    )
except ImportError:
    # MLflow未安装时的默认配置
    MLFLOW_RETRY_CONFIG = RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=(ConnectionError, TimeoutError),
    )


class PredictionConfig:
    """
    预测服务配置类

    封装所有预测服务相关的配置参数
    """

    def __init__(self):
        # MLflow配置
        self.mlflow_tracking_uri = os.getenv(


            "MLFLOW_TRACKING_URI",
            "http://localhost:5002"
        )

        # 缓存TTL配置
        model_cache_ttl_hours = int(os.getenv("MODEL_CACHE_TTL_HOURS", "1"))
        self.model_cache_ttl = timedelta(hours=model_cache_ttl_hours)

        prediction_cache_ttl_minutes = int(
            os.getenv("PREDICTION_CACHE_TTL_MINUTES", "30")
        )
        self.prediction_cache_ttl = timedelta(minutes=prediction_cache_ttl_minutes)

        # 缓存大小配置
        self.model_cache_max_size = 10
        self.prediction_cache_max_size = 1000

        # 特征配置
        self.feature_order = [
            "home_recent_wins",
            "home_recent_goals_for",
            "home_recent_goals_against",
            "away_recent_wins",
            "away_recent_goals_for",
            "away_recent_goals_against",
            "h2h_home_advantage",
            "home_implied_probability",
            "draw_implied_probability",
            "away_implied_probability",
        ]

        # 默认模型名称
        self.default_model_name = "football_baseline_model"

        # 统计查询默认天数
        self.default_stats_days = 30