#!/usr/bin/env python3
"""
Phase 3.2 - Core模块异常系统全面测试
异常处理comprehensive测试，基础设施快速覆盖
"""

import pytest
from src.core.exceptions import (
    FootballPredictionError, ConfigError, DataError, ModelError,
    PredictionError, CacheError, ServiceError, DatabaseError,
    ConsistencyError, ValidationError, DataQualityError, PipelineError,
    DomainError, BusinessRuleError, ServiceLifecycleError,
    DependencyInjectionError, LineageError, TrackingError, BacktestError,
    DataProcessingError, TaskExecutionError, TaskRetryError,
    AuthenticationError, AuthorizationError, RateLimitError, TimeoutError,
    AdapterError, StreamingError
)


class TestCoreExceptionsComprehensive:
    """Core异常系统全面测试类"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        exc = FootballPredictionError("基础测试异常")
        assert str(exc) == "基础测试异常"
        assert isinstance(exc, Exception)

    def test_base_exception_inheritance(self):
        """测试异常继承关系"""
        exc = FootballPredictionError("测试")
        assert isinstance(exc, Exception)
        assert isinstance(exc, FootballPredictionError)

    def test_config_error(self):
        """测试配置异常"""
        exc = ConfigError("配置文件不存在")
        assert str(exc) == "配置文件不存在"
        assert isinstance(exc, FootballPredictionError)
        assert isinstance(exc, ConfigError)

    def test_data_error_hierarchy(self):
        """测试数据异常层次结构"""
        # 基础数据异常
        data_exc = DataError("数据处理错误")
        assert isinstance(data_exc, FootballPredictionError)

        # 缓存异常继承自数据异常
        cache_exc = CacheError("缓存连接失败")
        assert isinstance(cache_exc, DataError)
        assert isinstance(cache_exc, FootballPredictionError)

        # 数据质量异常
        quality_exc = DataQualityError("数据质量不合格")
        assert isinstance(quality_exc, DataError)

        # 数据处理异常
        processing_exc = DataProcessingError("数据处理失败")
        assert isinstance(processing_exc, DataError)

    def test_model_error(self):
        """测试模型异常"""
        exc = ModelError("模型加载失败")
        assert str(exc) == "模型加载失败"
        assert isinstance(exc, FootballPredictionError)

    def test_prediction_error(self):
        """测试预测异常"""
        exc = PredictionError("预测计算失败")
        assert str(exc) == "预测计算失败"
        assert isinstance(exc, FootballPredictionError)

    def test_service_error_with_service_name(self):
        """测试服务异常带服务名"""
        exc = ServiceError("服务不可用", "prediction_service")
        assert exc.message == "服务不可用"
        assert exc.service_name == "prediction_service"
        assert str(exc) == "服务不可用"
        assert isinstance(exc, FootballPredictionError)

    def test_service_error_without_service_name(self):
        """测试服务异常不带服务名"""
        exc = ServiceError("通用服务错误")
        assert exc.message == "通用服务错误"
        assert exc.service_name is None
        assert isinstance(exc, FootballPredictionError)

    def test_database_error(self):
        """测试数据库异常"""
        exc = DatabaseError("数据库连接超时")
        assert str(exc) == "数据库连接超时"
        assert isinstance(exc, DataError)

    def test_consistency_error(self):
        """测试一致性异常"""
        exc = ConsistencyError("数据一致性检查失败")
        assert str(exc) == "数据一致性检查失败"
        assert isinstance(exc, DataError)

    def test_validation_error(self):
        """测试验证异常"""
        exc = ValidationError("输入数据验证失败")
        assert str(exc) == "输入数据验证失败"
        assert isinstance(exc, FootballPredictionError)

    def test_pipeline_error(self):
        """测试管道异常"""
        exc = PipelineError("数据管道执行失败")
        assert str(exc) == "数据管道执行失败"
        assert isinstance(exc, FootballPredictionError)

    def test_domain_error_hierarchy(self):
        """测试领域异常层次结构"""
        # 基础领域异常
        domain_exc = DomainError("领域逻辑错误")
        assert isinstance(domain_exc, FootballPredictionError)

        # 业务规则异常继承自领域异常
        business_exc = BusinessRuleError("违反业务规则")
        assert isinstance(business_exc, DomainError)
        assert isinstance(business_exc, FootballPredictionError)

    def test_service_lifecycle_error(self):
        """测试服务生命周期异常"""
        exc = ServiceLifecycleError("服务启动失败")
        assert str(exc) == "服务启动失败"
        assert isinstance(exc, FootballPredictionError)

    def test_dependency_injection_error(self):
        """测试依赖注入异常"""
        exc = DependencyInjectionError("依赖注入配置错误")
        assert str(exc) == "依赖注入配置错误"
        assert isinstance(exc, FootballPredictionError)

    def test_lineage_error(self):
        """测试数据血缘异常"""
        exc = LineageError("数据血缘追踪失败")
        assert str(exc) == "数据血缘追踪失败"
        assert isinstance(exc, FootballPredictionError)

    def test_tracking_error(self):
        """测试追踪异常"""
        exc = TrackingError("追踪信息丢失")
        assert str(exc) == "追踪信息丢失"
        assert isinstance(exc, FootballPredictionError)

    def test_backtest_error(self):
        """测试回测异常"""
        exc = BacktestError("回测数据不完整")
        assert str(exc) == "回测数据不完整"
        assert isinstance(exc, FootballPredictionError)

    def test_task_errors(self):
        """测试任务相关异常"""
        # 任务执行异常
        exec_exc = TaskExecutionError("任务执行超时")
        assert str(exec_exc) == "任务执行超时"
        assert isinstance(exec_exc, FootballPredictionError)

        # 任务重试异常
        retry_exc = TaskRetryError("任务重试次数耗尽")
        assert str(retry_exc) == "任务重试次数耗尽"
        assert isinstance(retry_exc, FootballPredictionError)

    def test_security_errors(self):
        """测试安全相关异常"""
        # 认证异常
        auth_exc = AuthenticationError("用户认证失败")
        assert str(auth_exc) == "用户认证失败"
        assert isinstance(auth_exc, FootballPredictionError)

        # 授权异常
        authz_exc = AuthorizationError("权限不足")
        assert str(authz_exc) == "权限不足"
        assert isinstance(authz_exc, FootballPredictionError)

    def test_system_errors(self):
        """测试系统相关异常"""
        # 限流异常
        rate_exc = RateLimitError("请求频率超限")
        assert str(rate_exc) == "请求频率超限"
        assert isinstance(rate_exc, FootballPredictionError)

        # 超时异常
        timeout_exc = TimeoutError("操作超时")
        assert str(timeout_exc) == "操作超时"
        assert isinstance(timeout_exc, FootballPredictionError)

    def test_integration_errors(self):
        """测试集成相关异常"""
        # 适配器异常
        adapter_exc = AdapterError("适配器初始化失败")
        assert str(adapter_exc) == "适配器初始化失败"
        assert isinstance(adapter_exc, FootballPredictionError)

        # 流处理异常
        streaming_exc = StreamingError("流数据处理失败")
        assert str(streaming_exc) == "流数据处理失败"
        assert isinstance(streaming_exc, FootballPredictionError)

    def test_exception_raising_and_catching(self):
        """测试异常抛出和捕获"""
        with pytest.raises(FootballPredictionError) as exc_info:
            raise FootballPredictionError("测试异常抛出")

        assert str(exc_info.value) == "测试异常抛出"

    def test_exception_inheritance_chain(self):
        """测试异常继承链"""
        exc = CacheError("缓存测试")

        # 验证完整的继承链
        assert isinstance(exc, CacheError)
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)
        assert isinstance(exc, Exception)

    def test_service_error_attributes(self):
        """测试服务异常属性"""
        message = "服务错误信息"
        service_name = "test_service"

        exc = ServiceError(message, service_name)

        assert hasattr(exc, 'message')
        assert hasattr(exc, 'service_name')
        assert exc.message == message
        assert exc.service_name == service_name

    def test_all_exceptions_importable(self):
        """测试所有异常都可以导入"""
        exceptions = [
            FootballPredictionError, ConfigError, DataError, ModelError,
            PredictionError, CacheError, ServiceError, DatabaseError,
            ConsistencyError, ValidationError, DataQualityError, PipelineError,
            DomainError, BusinessRuleError, ServiceLifecycleError,
            DependencyInjectionError, LineageError, TrackingError, BacktestError,
            DataProcessingError, TaskExecutionError, TaskRetryError,
            AuthenticationError, AuthorizationError, RateLimitError, TimeoutError,
            AdapterError, StreamingError
        ]

        for exc_class in exceptions:
            assert exc_class is not None, f"异常类 {exc_class.__name__} 导入失败"
            assert issubclass(exc_class, Exception), f"{exc_class.__name__} 不是Exception的子类"

    def test_exception_messages_with_unicode(self):
        """测试异常消息支持Unicode"""
        unicode_message = "测试异常消息包含中文 🚀 emoji"

        exc = FootballPredictionError(unicode_message)
        assert str(exc) == unicode_message

        # 测试各种异常类型的Unicode支持
        exc_types = [ConfigError, DataError, ValidationError, ServiceError]
        for exc_type in exc_types:
            if exc_type == ServiceError:
                exc = exc_type(unicode_message, "测试服务")
            else:
                exc = exc_type(unicode_message)
            assert unicode_message in str(exc)

def test_core_exceptions_comprehensive_suite():
    """Core异常系统综合测试套件"""
    # 快速验证核心异常功能
    assert FootballPredictionError("测试") is not None
    assert isinstance(ConfigError("配置错误"), FootballPredictionError)
    assert isinstance(DataError("数据错误"), FootballPredictionError)

    # 测试服务异常特殊功能
    service_exc = ServiceError("消息", "服务名")
    assert service_exc.service_name == "服务名"

    print("✅ Core异常系统综合测试套件通过")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])