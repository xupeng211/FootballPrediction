"""
足球预测系统异常定义模块

定义系统中使用的所有自定义异常类。
"""


class FootballPredictionError(Exception):
    """足球预测系统基础异常类"""


class ConfigError(FootballPredictionError):
    """配置相关异常"""


class DataError(FootballPredictionError):
    """数据处理异常"""


class ModelError(FootballPredictionError):
    """模型相关异常"""


class PredictionError(FootballPredictionError):
    """预测相关异常"""


class CacheError(DataError):
    """缓存相关异常"""


class DatabaseError(DataError):
    """数据库相关异常"""


class ConsistencyError(DataError):
    """数据一致性异常"""


class ValidationError(FootballPredictionError):
    """数据验证异常"""


class DataQualityError(DataError):
    """数据质量异常"""


class PipelineError(FootballPredictionError):
    """数据管道异常"""


class ServiceLifecycleError(FootballPredictionError):
    """服务生命周期异常"""


class DependencyInjectionError(FootballPredictionError):
    """依赖注入异常"""


class LineageError(FootballPredictionError):
    """数据血缘追踪异常"""


class TrackingError(FootballPredictionError):
    """追踪相关异常"""


class BacktestError(FootballPredictionError):
    """回测相关异常"""


class DataProcessingError(DataError):
    """数据处理异常"""


class TaskExecutionError(FootballPredictionError):
    """任务执行异常"""


class TaskRetryError(FootballPredictionError):
    """任务重试异常"""


class AuthenticationError(FootballPredictionError):
    """认证异常"""


class AuthorizationError(FootballPredictionError):
    """授权异常"""


class RateLimitError(FootballPredictionError):
    """限流异常"""


class TimeoutError(FootballPredictionError):
    """超时异常"""
