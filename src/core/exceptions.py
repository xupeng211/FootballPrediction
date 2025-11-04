"""
足球预测系统异常定义模块

定义系统中使用的所有自定义异常类.
"""


class FootballPredictionError(Exception):
    """足球预测系统基础异常类"""

    def __init__(self, message: str, **kwargs):
        """
        初始化异常

        Args:
            message: 异常消息
            **kwargs: 额外的异常属性（如code, details等）
        """
        super().__init__(message)
        self.message = message

        # 将关键字参数设置为属性
        for key, value in kwargs.items():
            setattr(self, key, value)


# 别名，保持向后兼容
FootballPredictionException = FootballPredictionError


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


class ServiceError(FootballPredictionError):
    """服务错误"""

    def __init__(self, message: str, service_name: str = None):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.message = message
        self.service_name = service_name
        super().__init__(message)


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


class DomainError(FootballPredictionError):
    """领域层异常"""

    pass


class BusinessRuleError(DomainError):
    """业务规则异常"""

    pass


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


class AdapterError(FootballPredictionError):
    """适配器相关异常"""


class StreamingError(FootballPredictionError):
    """流式处理相关异常"""


# 添加别名以兼容测试文件
DataValidationError = ValidationError
ConfigurationError = ConfigError
ServiceUnavailableError = ServiceError
