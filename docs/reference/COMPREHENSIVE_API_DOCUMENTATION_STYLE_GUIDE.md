# Comprehensive API Documentation Style Guide

## 1. General Principles

1. **Bilingual Documentation**: All public APIs and major components should have both Chinese and English documentation.
2. **Consistent Structure**: Follow a consistent structure for all docstrings and API documentation.
3. **Clear Examples**: Provide clear usage examples where appropriate.
4. **Type Annotations**: Use proper type annotations in Python code.

## 2. Docstring Format Standards

### 2.1 Module Docstrings

```python
"""
数据库连接管理模块 / Database Connection Management Module

提供同步和异步的PostgreSQL数据库连接、会话管理和生命周期控制。
支持多用户权限分离的数据库连接管理。

Provides synchronous and asynchronous PostgreSQL database connection, session management,
and lifecycle control. Supports multi-user permission-separated database connection management.

主要类 / Main Classes:
    DatabaseManager: 单例数据库连接管理器 / Singleton database connection manager
    MultiUserDatabaseManager: 多用户数据库连接管理器 / Multi-user database connection manager

主要方法 / Main Methods:
    DatabaseManager.initialize(): 初始化数据库连接 / Initialize database connection
    DatabaseManager.get_session(): 获取同步会话 / Get synchronous session
    DatabaseManager.get_async_session(): 获取异步会话 / Get asynchronous session

使用示例 / Usage Example:
    ```python
    from src.database.connection import DatabaseManager

    # 初始化数据库连接
    db_manager = DatabaseManager()
    db_manager.initialize()

    # 使用同步会话
    with db_manager.get_session() as session:
        # 执行数据库操作
        pass

    # 使用异步会话
    async with db_manager.get_async_session() as session:
        # 执行异步数据库操作
        pass
    ```

环境变量 / Environment Variables:
    DB_HOST: 数据库主机地址 / Database host address
    DB_PORT: 数据库端口 / Database port
    DB_NAME: 数据库名称 / Database name
    DB_USER: 数据库用户名 / Database username
    DB_PASSWORD: 数据库密码 / Database password

依赖 / Dependencies:
    - sqlalchemy: 数据库ORM框架 / Database ORM framework
    - psycopg2: PostgreSQL数据库适配器 / PostgreSQL database adapter
"""
```

### 2.2 Class Docstrings

```python
class DatabaseManager:
    """
    数据库连接管理器 / Database Connection Manager

    提供单例模式的数据库连接管理，支持同步和异步操作。
    实现连接池管理、会话管理和健康检查功能。

    Provides singleton database connection management with support for both
    synchronous and asynchronous operations. Implements connection pool management,
    session management, and health check functionality.

    Attributes:
        _instance (Optional[DatabaseManager]): 单例实例 / Singleton instance
        _sync_engine (Optional[Engine]): 同步数据库引擎 / Synchronous database engine
        _async_engine (Optional[AsyncEngine]): 异步数据库引擎 / Asynchronous database engine
        _session_factory (Optional[sessionmaker]): 同步会话工厂 / Synchronous session factory
        _async_session_factory (Optional[async_sessionmaker]): 异步会话工厂 / Asynchronous session factory
        _config (Optional[DatabaseConfig]): 数据库配置 / Database configuration

    Example:
        ```python
        from src.database.connection import DatabaseManager

        # 获取单例实例
        db_manager = DatabaseManager()
        db_manager.initialize()

        # 检查数据库健康状态
        is_healthy = db_manager.health_check()
        ```
    """
```

### 2.3 Method Docstrings

```python
    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """
        初始化数据库连接 / Initialize Database Connection

        根据提供的配置初始化同步和异步数据库引擎及会话工厂。
        如果未提供配置，则使用默认配置。

        Initialize synchronous and asynchronous database engines and session factories
        based on the provided configuration. If no configuration is provided,
        use the default configuration.

        Args:
            config (Optional[DatabaseConfig]): 数据库配置对象 / Database configuration object
                If None, uses default configuration from environment variables.
                Defaults to None.

        Raises:
            ValueError: 当配置参数无效时抛出 / Raised when configuration parameters are invalid
            RuntimeError: 当数据库连接初始化失败时抛出 / Raised when database connection initialization fails

        Example:
            ```python
            from src.database.connection import DatabaseManager, DatabaseConfig

            db_manager = DatabaseManager()

            # 使用默认配置
            db_manager.initialize()

            # 使用自定义配置
            config = DatabaseConfig(
                host="localhost",
                port=5432,
                database="football_prediction",
                user="football_user",
                password="football_password"
            )
            db_manager.initialize(config)
            ```

        Note:
            该方法应该在应用程序启动时调用一次。
            This method should be called once at application startup.
        """
```

### 2.4 Data Class Docstrings

```python
@dataclass
class DataFreshnessResult:
    """
    数据新鲜度检查结果 / Data Freshness Check Result

    存储单个表的数据新鲜度检查结果，包括时间戳、记录数和新鲜度状态。
    Stores data freshness check results for a single table, including timestamps,
    record counts, and freshness status.

    Attributes:
        table_name (str): 表名 / Table name
        last_update_time (Optional[datetime]): 最后更新时间 / Last update time
        records_count (int): 记录数量 / Number of records
        freshness_hours (float): 数据新鲜度（小时） / Data freshness in hours
        is_fresh (bool): 是否新鲜 / Whether data is fresh
        threshold_hours (float): 新鲜度阈值（小时） / Freshness threshold in hours

    Example:
        ```python
        from src.monitoring.quality_monitor import DataFreshnessResult
        from datetime import datetime

        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=datetime.now(),
            records_count=1000,
            freshness_hours=2.5,
            is_fresh=True,
            threshold_hours=24.0
        )

        print(f"表 {result.table_name} 数据新鲜度: {result.freshness_hours} 小时")
        ```
    """
```

### 2.5 Enum Docstrings

```python
class DatabaseRole(str, Enum):
    """
    数据库用户角色枚举 / Database User Role Enumeration

    定义数据库用户的三种角色，用于权限分离。
    Defines three roles for database users for permission separation.

    Roles:
        READER: 只读用户（分析、前端） / Read-only user (analytics, frontend)
        WRITER: 读写用户（数据采集） / Read-write user (data collection)
        ADMIN: 管理员用户（运维、迁移） / Administrator user (operations, migration)

    Example:
        ```python
        from src.database.connection import DatabaseRole

        # 使用枚举值
        role = DatabaseRole.READER
        print(role.value)  # 输出: reader
        ```

    Note:
        基于DATA_DESIGN.md第5.3节权限控制设计。
        Based on DATA_DESIGN.md Section 5.3 Permission Control Design.
    """

    READER = "reader"  # 只读用户（分析、前端） / Read-only user (analytics, frontend)
    WRITER = "writer"  # 读写用户（数据采集） / Read-write user (data collection)
    ADMIN = "admin"  # 管理员用户（运维、迁移） / Administrator user (operations, migration)
```

## 3. API Documentation Standards

### 3.1 FastAPI Endpoint Documentation

```python
@router.get(
    "/health",
    summary="检查服务健康状态 / Check Service Health",
    description="检查API服务和依赖组件的健康状态 / Check health status of API service and dependent components",
    responses={
        200: {
            "description": "服务健康 / Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "components": {
                            "database": "healthy",
                            "redis": "healthy",
                            "mlflow": "healthy"
                        },
                        "timestamp": "2025-09-15T10:30:00Z"
                    }
                }
            }
        },
        503: {
            "description": "服务不健康 / Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "components": {
                            "database": "unhealthy",
                            "redis": "healthy",
                            "mlflow": "healthy"
                        },
                        "timestamp": "2025-09-15T10:30:00Z",
                        "errors": {
                            "database": "Connection timeout"
                        }
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """
    检查服务健康状态 / Check Service Health

    执行全面的健康检查，包括数据库、Redis缓存和MLflow服务的连接状态。
    Perform comprehensive health check including database, Redis cache,
    and MLflow service connection status.

    Returns:
        Dict[str, Any]: 健康检查结果 / Health check results
            - status (str): 服务整体状态 ('healthy' or 'unhealthy') / Overall service status
            - components (Dict[str, str]): 各组件状态 / Component statuses
            - timestamp (str): 检查时间戳 / Check timestamp
            - errors (Optional[Dict[str, str]]): 错误信息（如果有） / Error messages if any

    Example:
        ```python
        import requests

        response = requests.get("http://localhost:8000/health")
        health_data = response.json()

        if health_data["status"] == "healthy":
            print("所有服务组件正常运行")
        else:
            print("以下组件存在问题:")
            for component, status in health_data["components"].items():
                if status != "healthy":
                    print(f"  {component}: {health_data['errors'].get(component, 'Unknown error')}")
        ```

    Note:
        该端点用于监控系统和服务发现。
        This endpoint is used for monitoring systems and service discovery.
    """
```

### 3.2 FastAPI Path and Query Parameters

```python
@router.get(
    "/predictions/{match_id}",
    summary="获取比赛预测结果 / Get Match Prediction",
    description="获取指定比赛的预测结果，如果不存在则实时生成 / Get prediction result for specified match, generate in real-time if not exists"
)
async def get_match_prediction(
    match_id: int = Path(
        ...,
        description="比赛唯一标识符 / Unique match identifier",
        ge=1,
        example=12345
    ),
    force_predict: bool = Query(
        default=False,
        description="是否强制重新预测 / Whether to force re-prediction"
    ),
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    获取指定比赛的预测结果 / Get Prediction for Specified Match

    该端点首先检查数据库中是否存在该比赛的缓存预测结果。
    如果存在且未设置force_predict参数，则直接返回缓存结果。
    否则，实时生成新的预测结果并存储到数据库。

    This endpoint first checks if there's a cached prediction result for the match in the database.
    If it exists and force_predict is not set, it returns the cached result directly.
    Otherwise, it generates a new prediction in real-time and stores it in the database.

    Args:
        match_id (int): 比赛唯一标识符，必须大于0 / Unique match identifier, must be greater than 0
            Constraints:
                - Minimum value: 1
                - Example: 12345
        force_predict (bool): 是否强制重新预测，默认为False / Whether to force re-prediction, defaults to False
            If True, generates a new prediction even if cached result exists.
        session (AsyncSession): 数据库会话，由依赖注入提供 / Database session, provided by dependency injection

    Returns:
        Dict[str, Any]: API响应字典 / API response dictionary
            - success (bool): 请求是否成功 / Whether request was successful
            - data (Dict): 预测数据 / Prediction data
                - match_id (int): 比赛ID / Match ID
                - match_info (Dict): 比赛信息 / Match information
                - prediction (Dict): 预测结果 / Prediction result

    Raises:
        HTTPException:
            - 404: 当比赛不存在时 / When match does not exist
            - 500: 当预测过程发生错误时 / When prediction process fails

    Example:
        ```python
        import requests

        # 获取比赛预测
        response = requests.get("http://localhost:8000/api/v1/predictions/12345")
        if response.status_code == 200:
            data = response.json()
            prediction = data["data"]["prediction"]
            print(f"预测结果: {prediction['predicted_result']}")
            print(f"置信度: {prediction['confidence_score']:.2f}")

        # 强制重新预测
        response = requests.get("http://localhost:8000/api/v1/predictions/12345?force_predict=true")
        ```

    Note:
        预测结果会自动缓存到数据库以提高性能。
        Prediction results are automatically cached in the database to improve performance.
    """
```

## 4. Documentation Best Practices

### 4.1 Consistency Guidelines

1. **Language Pairing**: Always provide both Chinese and English documentation
2. **Structure Consistency**: Follow the same structure for all docstrings
3. **Terminology Consistency**: Use consistent terminology throughout the codebase
4. **Formatting Consistency**: Maintain consistent formatting and indentation

### 4.2 Content Guidelines

1. **Clarity**: Write clear, concise descriptions
2. **Completeness**: Include all relevant information
3. **Accuracy**: Ensure technical details are accurate
4. **Examples**: Provide practical usage examples
5. **Context**: Explain the purpose and context of components

### 4.3 Maintenance Guidelines

1. **Update with Code**: Update documentation when modifying code
2. **Review Regularly**: Periodically review documentation for accuracy
3. **Version Control**: Keep documentation in version control with code
4. **Automated Checks**: Use tools to check documentation quality

## 5. Documentation Tools and Automation

### 5.1 Sphinx Configuration

```python
# docs/conf.py
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

# 支持Google和NumPy风格的docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
```

### 5.2 Automated Documentation Generation

```bash
# Makefile
.PHONY: docs
docs:
	sphinx-apidoc -o docs/api src/
	cd docs && make html
	@echo "Documentation generated in docs/_build/html/"
```

## 6. Documentation Review Process

1. **Peer Review**: Have team members review documentation
2. **Technical Accuracy**: Verify technical details are correct
3. **Language Quality**: Check for grammar and clarity
4. **Completeness**: Ensure all public APIs are documented
5. **Consistency**: Verify consistent style and formatting
