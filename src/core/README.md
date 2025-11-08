# Core Components - 核心组件

## 🎯 概述

核心组件层(Core Components)是足球预测系统的基础设施层，提供了系统运行所需的核心服务和工具。包括依赖注入、配置管理、日志系统、异常处理、事件应用初始化等关键功能。

## 🏗️ 架构设计

### 核心设计原则
- **依赖注入**: 轻量级DI容器实现组件解耦
- **配置驱动**: 统一的配置管理机制
- **结构化日志**: 分级分类的日志系统
- **异常统一**: 标准化的异常处理体系
- **事件驱动**: 基础事件应用框架

## 📁 目录结构

```
src/core/
├── __init__.py              # 核心模块初始化
├── config.py                # 配置管理系统
├── di.py                    # 依赖注入容器
├── exceptions.py            # 异常定义
├── logging.py               # 统一日志接口
├── logger.py                # 日志实现
├── logger_simple.py         # 简化日志器
├── logging_system.py        # 日志系统
├── error_handler.py         # 错误处理器
├── path_manager.py          # 路径管理
├── constants.py             # 常量定义
├── event_application.py     # 事件应用初始化
├── service_lifecycle.py     # 服务生命周期管理
├── di_setup.py              # DI容器设置
├── config_di.py             # 配置与DI集成
├── dependencies.py          # 依赖定义
├── auto_binding.py          # 自动绑定
└── prediction_engine.py     # 预测引擎
```

## 🎯 核心组件详解

### 1. 依赖注入容器 (Dependency Injection)

#### DIContainer 轻量级实现
```python
from src.core.di import DIContainer, ServiceCollection, ServiceLifetime

# 创建服务集合
services = ServiceCollection()

# 注册服务
services.add_singleton(DatabaseManager)
services.add_scoped(PredictionService)
services.add_transient(CacheService)

# 构建容器
container = services.build_container()

# 解析服务
db_manager = container.resolve(DatabaseManager)
prediction_service = container.resolve(PredictionService)
```

#### 服务生命周期管理
```python
# 单例模式 - 整个容器生命周期内只创建一次
services.add_singleton(ConfigService)

# 作用域模式 - 每个作用域内创建一次
services.add_scoped(UserContext)

# 瞬时模式 - 每次请求都创建新实例
services.add_transient(Validator)
```

#### 作用域管理
```python
# 创建作用域
with container.create_scope("request_scope") as scope:
    # 在作用域内解析服务
    user_context = container.resolve(UserContext)
    # 作用域结束时自动清理资源
```

### 2. 配置管理系统 (Configuration Management)

#### Settings 配置类
```python
from src.core.config import Settings, get_settings

# 获取配置实例
settings = get_settings()

# 访问配置
database_url = settings.database_url
redis_url = settings.redis_url
api_host = settings.api_host
log_level = settings.log_level
```

#### 环境变量支持
```python
# 支持从环境变量自动加载配置
# DATABASE_URL=postgresql://user:pass@localhost/db
# REDIS_URL=redis://localhost:6379/0
# LOG_LEVEL=DEBUG
# API_HOST=0.0.0.0
```

#### Pydantic 配置验证
```python
from pydantic import Field
from src.core.config import Settings

class CustomSettings(Settings):
    custom_field: str = Field(default="default_value", description="自定义字段")
    max_connections: int = Field(default=10, ge=1, le=100)

    class Config:
        env_file = ".env"
        case_sensitive = False
```

### 3. 日志系统 (Logging System)

#### 统一日志接口
```python
from src.core.logging import get_logger, LogLevel, LogCategory

# 获取日志器
logger = get_logger("my_module", "INFO")

# 记录日志
logger.info("操作成功")
logger.error("操作失败", user_id=123, action="create")
logger.warning("警告信息")
logger.debug("调试信息")
```

#### 结构化日志
```python
from src.core.logging import StructuredLogger

# 创建结构化日志器
structured_logger = StructuredLogger("prediction_service", LogCategory["PREDICTION"])

# 带上下文的日志记录
structured_logger.info("预测完成",
                      prediction_id=123,
                      confidence=0.85,
                      duration=1.23)
```

#### 性能日志
```python
from src.core.logging import log_performance, log_async_performance

# 记录性能
log_performance("data_processing", 2.34, records=1000)
log_async_performance("api_call", 0.56, endpoint="/predictions")
```

#### 审计日志
```python
from src.core.logging import log_audit

# 记录审计事件
log_audit("CREATE_PREDICTION", "user_123", "prediction_456",
          ip_address="192.168.1.1",
          user_agent="Mozilla/5.0...")
```

### 4. 异常处理系统 (Exception Handling)

#### 异常层次结构
```python
from src.core.exceptions import (
    FootballPredictionError,
    ConfigError,
    DataError,
    PredictionError,
    ValidationError,
    ServiceError,
    DatabaseError
)

# 使用异常层次
try:
    # 业务逻辑
    pass
except ValidationError as e:
    logger.error(f"验证失败: {e.message}")
except DataError as e:
    logger.error(f"数据错误: {e.message}")
except FootballPredictionError as e:
    logger.error(f"系统错误: {e.message}")
```

#### 自定义异常
```python
from src.core.exceptions import PredictionError

class CustomPredictionError(PredictionError):
    """自定义预测异常"""

    def __init__(self, message: str, prediction_id: int = None, **kwargs):
        super().__init__(message, prediction_id=prediction_id, **kwargs)

# 使用自定义异常
raise CustomPredictionError(
    message="预测模型不可用",
    prediction_id=123,
    model_name="neural_network_v2"
)
```

### 5. 事件应用初始化 (Event Application)

#### 事件系统初始化
```python
from src.core.event_application import initialize_event_system, get_event_bus

# 初始化事件系统
await initialize_event_system()

# 获取事件总线
event_bus = get_event_bus()

# 发布事件
from src.events.domain.prediction_events import PredictionCreatedEvent
event = PredictionCreatedEvent(prediction_id=123, match_id=456)
await event_bus.publish(event)
```

## 🔄 业务流程

### 依赖注入流程
```mermaid
sequenceDiagram
    participant Client
    participant Container
    participant Service
    participant Dependency

    Client->>Container: resolve(ServiceType)
    Container->>Container: check_service_registered()
    Container->>Container: analyze_dependencies()
    Container->>Dependency: resolve(DependencyType)
    Dependency-->>Container: dependency_instance
    Container->>Service: create_service(dependency_instance)
    Service-->>Container: service_instance
    Container-->>Client: service_instance
```

### 配置加载流程
```mermaid
sequenceDiagram
    participant Application
    participant Settings
    participant Environment
    participant ConfigFile

    Application->>Settings: get_settings()
    Settings->>Environment: load_environment_variables()
    Settings->>ConfigFile: load_config_file()
    Settings->>Settings: validate_configuration()
    Settings-->>Application: settings_instance
```

## 📋 使用指南

### 基础依赖注入使用
```python
# 1. 定义服务接口
class IDataService:
    async def get_data(self) -> dict:
        pass

# 2. 实现服务
class DataService(IDataService):
    def __init__(self, config: ConfigService):
        self.config = config

    async def get_data(self) -> dict:
        return {"source": "database", "status": "active"}

# 3. 配置容器
services = ServiceCollection()
services.add_singleton(ConfigService)
services.add_transient(IDataService, DataService)
container = services.build_container()

# 4. 使用服务
data_service = container.resolve(IDataService)
data = await data_service.get_data()
```

### 配置管理最佳实践
```python
# 创建自定义配置类
class DatabaseConfig:
    def __init__(self, settings: Settings):
        self.url = settings.database_url
        self.pool_size = getattr(settings, 'db_pool_size', 10)
        self.timeout = getattr(settings, 'db_timeout', 30)

# 在服务中使用
class DatabaseService:
    def __init__(self, db_config: DatabaseConfig):
        self.config = db_config
        self.connection = None

    async def connect(self):
        self.connection = await create_async_engine(
            self.config.url,
            pool_size=self.config.pool_size,
            connect_timeout=self.config.timeout
        )
```

### 日志使用规范
```python
# 1. 模块级日志器
logger = get_logger(__name__)

# 2. 结构化日志
def process_prediction(prediction_data: dict):
    start_time = time.time()

    try:
        logger.info("开始处理预测",
                   prediction_id=prediction_data.get('id'),
                   match_id=prediction_data.get('match_id'))

        result = await prediction_engine.process(prediction_data)

        duration = time.time() - start_time
        logger.info("预测处理完成",
                   prediction_id=prediction_data.get('id'),
                   result=result,
                   duration=duration)

        return result

    except Exception as e:
        logger.error("预测处理失败",
                    prediction_id=prediction_data.get('id'),
                    error=str(e),
                    error_type=type(e).__name__)
        raise
```

### 异常处理策略
```python
# 1. 业务异常
class InsufficientDataError(DataError):
    def __init__(self, required_fields: list, available_fields: list):
        super().__init__(
            f"数据不足，需要字段: {required_fields}，可用字段: {available_fields}",
            required_fields=required_fields,
            available_fields=available_fields
        )

# 2. 异常处理装饰器
def handle_service_errors(service_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ServiceError:
                raise  # 重新抛出服务异常
            except Exception as e:
                logger.error(f"{service_name}服务异常: {e}")
                raise ServiceError(f"{service_name}服务异常", service_name=service_name)
        return wrapper
    return decorator

# 3. 使用装饰器
@handle_service_errors("prediction")
async def create_prediction(data: dict) -> Prediction:
    # 预测创建逻辑
    pass
```

## 🔧 设计模式应用

### 1. 单例模式 (Singleton Pattern)
- **DIContainer**: 全局容器实例管理
- **Config**: 配置管理器单例
- **LoggerManager**: 日志管理器单例

### 2. 工厂模式 (Factory Pattern)
- **ServiceCollection**: 服务工厂注册
- **Logger**: 日志器工厂创建
- **Settings**: 配置实例工厂

### 3. 依赖注入模式 (Dependency Injection)
- **DIContainer**: 依赖注入容器实现
- **ServiceLifetime**: 生命周期管理
- **Constructor Injection**: 构造函数注入

### 4. 观察者模式 (Observer Pattern)
- **Event Bus**: 事件总线实现
- **Logging**: 日志观察者
- **Configuration**: 配置变更监听

### 5. 策略模式 (Strategy Pattern)
- **Logger**: 不同日志输出策略
- **Config**: 不同配置源策略
- **ErrorHandler**: 不同错误处理策略

## 🧪 测试策略

### 单元测试
```python
import pytest
from unittest.mock import Mock, patch
from src.core.di import DIContainer, ServiceLifetime

def test_dependency_injection():
    """测试依赖注入"""
    # 准备
    container = DIContainer()

    # 注册服务
    container.register_singleton(ServiceInterface, ServiceImplementation)

    # 执行
    service = container.resolve(ServiceInterface)

    # 验证
    assert isinstance(service, ServiceImplementation)

def test_service_lifetime():
    """测试服务生命周期"""
    container = DIContainer()

    # 单例测试
    container.register_singleton(TestService)
    service1 = container.resolve(TestService)
    service2 = container.resolve(TestService)
    assert service1 is service2

    # 瞬时测试
    container.register_transient(TestService)
    service3 = container.resolve(TestService)
    service4 = container.resolve(TestService)
    assert service3 is not service4

@patch('src.core.config.os.getenv')
def test_config_from_environment(mock_getenv):
    """测试从环境变量加载配置"""
    mock_getenv.return_value = "test_value"

    settings = Settings()
    assert settings.database_url == "test_value"
```

### 集成测试
```python
@pytest.mark.asyncio
async def test_core_integration():
    """测试核心组件集成"""
    # 设置容器
    services = ServiceCollection()
    services.add_singleton(ConfigService)
    services.add_transient(LoggerService)
    services.add_scoped(PredictionService)

    container = services.build_container()

    # 测试依赖链
    prediction_service = container.resolve(PredictionService)
    assert prediction_service.config is not None
    assert prediction_service.logger is not None

    # 测试作用域
    with container.create_scope():
        service1 = container.resolve(PredictionService)
        service2 = container.resolve(PredictionService)
        assert service1 is service2
```

## 📈 性能优化

### 1. 依赖注入优化
- **缓存单例**: 单例服务实例缓存
- **延迟加载**: 按需创建服务实例
- **循环依赖检测**: 避免无限递归

### 2. 配置优化
- **缓存配置**: 避免重复读取配置文件
- **环境变量缓存**: 缓存环境变量读取
- **配置验证**: 启动时验证配置完整性

### 3. 日志优化
- **异步日志**: 非阻塞日志写入
- **批量写入**: 批量日志输出
- **日志级别过滤**: 减少不必要的日志处理

### 4. 内存管理
- **作用域清理**: 及时清理作用域资源
- **弱引用**: 避免循环引用导致的内存泄漏
- **定期清理**: 定期清理缓存和临时对象

## 🔮 扩展指南

### 添加新的核心服务
1. 创建服务接口和实现
2. 在DI容器中注册服务
3. 定义适当的服务生命周期
4. 编写单元测试和集成测试

### 扩展配置系统
1. 在Settings类中添加新字段
2. 添加相应的环境变量映射
3. 实现配置验证逻辑
4. 更新配置文档

### 增强日志系统
1. 创建新的日志器类型
2. 定义日志格式和输出
3. 添加日志过滤和处理逻辑
4. 集成监控和告警系统

### 自定义异常类型
1. 继承适当的基类异常
2. 定义异常特有的属性
3. 实现异常处理逻辑
4. 添加异常文档和测试

## 📚 相关文档

- [领域层架构指南](../domain/README.md)
- [CQRS模式实现指南](../cqrs/README.md)
- [事件驱动架构说明](../events/README.md)
- [API设计原则](../api/README.md)
- [测试最佳实践](../../docs/testing/TESTING_GUIDE.md)

---

*最后更新: 2025-11-07*
*维护者: Core Team*