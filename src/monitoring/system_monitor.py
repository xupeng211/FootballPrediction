"""
系统监控模块

提供全面的系统监控功能，包括：
- 应用性能监控
- 数据库连接监控
- 缓存监控
- API性能监控
- 资源使用监控
- 业务指标监控
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram
from sqlalchemy import text

from src.cache.redis_manager import get_redis_manager
from src.database.connection import get_async_session, DatabaseManager

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    系统监控器

    提供全面的系统性能和健康状态监控
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        初始化系统监控器

        Args:
            registry: Prometheus注册表实例
        """
        self.registry = registry or REGISTRY
        self.start_time = time.time()

        # 初始化Prometheus指标
        self._initialize_metrics()

        # 监控状态
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

    def _initialize_metrics(self):
        """初始化所有Prometheus指标"""

        # 系统资源指标
        self.system_cpu_percent = self._create_gauge(
            "system_cpu_percent", "System CPU usage percentage"
        )
        self.system_memory_percent = self._create_gauge(
            "system_memory_percent", "System memory usage percentage"
        )
        self.system_disk_percent = self._create_gauge(
            "system_disk_percent", "System disk usage percentage"
        )
        self.process_memory_bytes = self._create_gauge(
            "process_memory_bytes", "Process memory usage in bytes"
        )
        self.process_cpu_percent = self._create_gauge(
            "process_cpu_percent", "Process CPU usage percentage"
        )

        # 应用指标
        self.app_uptime_seconds = self._create_gauge(
            "app_uptime_seconds", "Application uptime in seconds"
        )
        self.app_requests_total = self._create_counter(
            "app_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status_code"],
        )
        self.app_request_duration_seconds = self._create_histogram(
            "app_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
        )

        # 数据库指标
        self.db_connections_active = self._create_gauge(
            "db_connections_active", "Number of active database connections"
        )
        self.db_connections_total = self._create_gauge(
            "db_connections_total", "Total number of database connections"
        )
        self.db_query_duration_seconds = self._create_histogram(
            "db_query_duration_seconds",
            "Database query duration in seconds",
            ["operation", "table"],
        )
        self.db_slow_queries_total = self._create_counter(
            "db_slow_queries_total",
            "Total number of slow database queries",
            ["operation", "table"],
        )

        # 缓存指标
        self.cache_operations_total = self._create_counter(
            "cache_operations_total",
            "Total number of cache operations",
            ["operation", "cache_type", "result"],
        )
        self.cache_hit_ratio = self._create_gauge(
            "cache_hit_ratio", "Cache hit ratio", ["cache_type"]
        )
        self.cache_size_bytes = self._create_gauge(
            "cache_size_bytes", "Cache size in bytes", ["cache_type"]
        )

        # 业务指标
        self.business_predictions_total = self._create_counter(
            "business_predictions_total",
            "Total number of predictions made",
            ["model_version", "league"],
        )
        self.business_prediction_accuracy = self._create_gauge(
            "business_prediction_accuracy",
            "Prediction accuracy rate",
            ["model_version", "time_period"],
        )
        self.business_data_collection_jobs_total = self._create_counter(
            "business_data_collection_jobs_total",
            "Total number of data collection jobs",
            ["data_source", "status"],
        )

        # ML模型指标
        self.ml_model_inference_duration_seconds = self._create_histogram(
            "ml_model_inference_duration_seconds",
            "ML model inference duration in seconds",
            ["model_name", "model_version"],
        )
        self.ml_model_training_duration_seconds = self._create_histogram(
            "ml_model_training_duration_seconds",
            "ML model training duration in seconds",
            ["model_name", "model_version"],
        )
        self.ml_model_accuracy = self._create_gauge(
            "ml_model_accuracy",
            "ML model accuracy score",
            ["model_name", "model_version", "metric_type"],
        )

    def _create_counter(
        self, name: str, description: str, labels: List[str] = None
    ) -> Counter:
        """创建Counter指标"""
        try:
            return Counter(name, description, labels or [], registry=self.registry)
        except ValueError:
            from unittest.mock import Mock

            mock = Mock()
            mock.inc = Mock()
            mock.labels = Mock(return_value=mock)
            return mock

    def _create_gauge(
        self, name: str, description: str, labels: List[str] = None
    ) -> Gauge:
        """创建Gauge指标"""
        try:
            return Gauge(name, description, labels or [], registry=self.registry)
        except ValueError:
            from unittest.mock import Mock

            mock = Mock()
            mock.set = Mock()
            mock.inc = Mock()
            mock.dec = Mock()
            mock.labels = Mock(return_value=mock)
            return mock

    def _create_histogram(
        self, name: str, description: str, labels: List[str] = None
    ) -> Histogram:
        """创建Histogram指标"""
        try:
            return Histogram(name, description, labels or [], registry=self.registry)
        except ValueError:
            from unittest.mock import Mock

            mock = Mock()
            mock.observe = Mock()
            mock.labels = Mock(return_value=mock)
            return mock

    async def start_monitoring(self, interval: int = 30):
        """
        启动系统监控

        Args:
            interval: 监控数据收集间隔（秒）
        """
        if self.is_monitoring:
            logger.warning("系统监控已经在运行中")
            return

        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info(f"系统监控已启动，监控间隔: {interval}秒")

    async def stop_monitoring(self):
        """停止系统监控"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("系统监控已停止")

    async def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self.is_monitoring:
            try:
                await self._collect_system_metrics()
                await self._collect_database_metrics()
                await self._collect_cache_metrics()
                await self._collect_application_metrics()

                # 等待下一次收集
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控数据收集失败: {e}")
                await asyncio.sleep(interval)

    async def _collect_system_metrics(self):
        """收集系统资源指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu_percent.set(cpu_percent)

            # 内存使用率
            memory = psutil.virtual_memory()
            self.system_memory_percent.set(memory.percent)

            # 磁盘使用率
            disk = psutil.disk_usage("/")
            self.system_disk_percent.set(disk.percent)

            # 进程资源使用
            process = psutil.Process()
            self.process_memory_bytes.set(process.memory_info().rss)
            self.process_cpu_percent.set(process.cpu_percent())

            # 应用运行时间
            uptime = time.time() - self.start_time
            self.app_uptime_seconds.set(uptime)

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")

    async def _collect_database_metrics(self):
        """收集数据库指标"""
        try:
            db_manager = DatabaseManager()

            # 获取连接池状态
            if db_manager._sync_engine:
                pool = db_manager._sync_engine.pool
                if pool:
                    self.db_connections_active.set(pool.checkedout())
                    self.db_connections_total.set(pool.size())

            # 查询数据库统计信息
            async with get_async_session() as session:
                try:
                    # 检查数据库连接状态
                    result = await session.execute(text("SELECT 1"))
                    connection_status = 1 if result.scalar() == 1 else 0

                    # 记录连接状态（这里可以根据需要扩展）
                    if connection_status == 0:
                        logger.warning("数据库连接状态异常")

                except Exception as e:
                    logger.error(f"数据库健康检查失败: {e}")

        except Exception as e:
            logger.error(f"收集数据库指标失败: {e}")

    async def _collect_cache_metrics(self):
        """收集缓存指标"""
        try:
            redis_manager = get_redis_manager()

            # 尝试获取Redis信息
            try:
                info = redis_manager.get_info()
                if info:
                    # Redis连接数
                    if "connected_clients" in info:
                        # 这里可以添加Redis连接数监控
                        pass

                    # Redis内存使用
                    if "used_memory" in info:
                        self.cache_size_bytes.labels(cache_type="redis").set(
                            info["used_memory"]
                        )

            except Exception:
                # Redis连接失败，记录异常但不中断监控
                pass

        except Exception as e:
            logger.error(f"收集缓存指标失败: {e}")

    async def _collect_application_metrics(self):
        """收集应用指标"""
        try:
            # 这里可以添加应用特定的指标收集逻辑
            # 比如活跃用户数、当前处理的请求数等
            pass

        except Exception as e:
            logger.error(f"收集应用指标失败: {e}")

    # 便捷方法
    def record_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """记录HTTP请求"""
        self.app_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        self.app_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

    def record_database_query(
        self, operation: str, table: str, duration: float, is_slow: bool = False
    ):
        """记录数据库查询"""
        self.db_query_duration_seconds.labels(operation=operation, table=table).observe(
            duration
        )

        if is_slow:
            self.db_slow_queries_total.labels(operation=operation, table=table).inc()

    def record_cache_operation(self, operation: str, cache_type: str, result: str):
        """记录缓存操作"""
        self.cache_operations_total.labels(
            operation=operation, cache_type=cache_type, result=result
        ).inc()

    def record_prediction(self, model_version: str, league: str):
        """记录预测操作"""
        self.business_predictions_total.labels(
            model_version=model_version, league=league
        ).inc()

    def record_model_inference(
        self, model_name: str, model_version: str, duration: float
    ):
        """记录模型推理"""
        self.ml_model_inference_duration_seconds.labels(
            model_name=model_name, model_version=model_version
        ).observe(duration)

    async def get_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "version": "1.0.0",
            "components": {},
            "metrics": {},
            "checks": {},
        }

        # 执行所有健康检查
        checks = [
            self._check_database(),
            self._check_redis(),
            self._check_system_resources(),
            self._check_application_health(),
            self._check_external_services(),
            self._check_data_pipeline(),
        ]

        results = await asyncio.gather(*checks, return_exceptions=True)

        unhealthy_count = 0
        warning_count = 0

        for i, result in enumerate(results):
            check_name = [
                "database",
                "redis",
                "system_resources",
                "application",
                "external_services",
                "data_pipeline",
            ][i]

            if isinstance(result, Exception):
                health_status["components"][check_name] = {
                    "status": "error",
                    "error": str(result),
                }
                unhealthy_count += 1
            else:
                health_status["components"][check_name] = result
                if result["status"] == "unhealthy":
                    unhealthy_count += 1
                elif result["status"] == "warning":
                    warning_count += 1

        # 确定整体状态
        if unhealthy_count > 0:
            health_status["status"] = "unhealthy"
        elif warning_count > 0:
            health_status["status"] = "degraded"
        else:
            health_status["status"] = "healthy"

        # 添加汇总指标
        health_status["metrics"] = {
            "total_components": len(checks),
            "unhealthy_components": unhealthy_count,
            "warning_components": warning_count,
            "healthy_components": len(checks) - unhealthy_count - warning_count,
        }

        return health_status

    async def _check_database(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            start_time = time.time()
            async with get_async_session() as session:
                # 基础连接测试
                result = await session.execute(text("SELECT 1"))
                basic_health = result.scalar() == 1

                # 查询性能测试
                perf_start = time.time()
                await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables")
                )
                query_time = time.time() - perf_start

                # 连接池状态
                db_manager = DatabaseManager()
                pool_status = {}
                if db_manager._sync_engine and db_manager._sync_engine.pool:
                    pool = db_manager._sync_engine.pool
                    pool_status = {
                        "size": pool.size(),
                        "checked_in": pool.checkedin(),
                        "checked_out": pool.checkedout(),
                        "overflow": pool.overflow(),
                        "invalidated": pool.invalidated(),
                    }

                response_time = time.time() - start_time

                status = "healthy"
                if not basic_health:
                    status = "unhealthy"
                elif query_time > 2.0:  # 查询超过2秒
                    status = "warning"
                elif response_time > 3.0:  # 总响应超过3秒
                    status = "warning"

                return {
                    "status": status,
                    "response_time": response_time,
                    "query_time": query_time,
                    "basic_health": basic_health,
                    "pool_status": pool_status,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _check_redis(self) -> Dict[str, Any]:
        """检查Redis健康状态"""
        try:
            start_time = time.time()
            redis_manager = get_redis_manager()

            # 基础ping测试
            redis_manager.ping()

            # 获取Redis信息
            info = redis_manager.get_info()

            # 测试读写性能
            test_key = "health_check_test"
            write_start = time.time()
            redis_manager.set(test_key, "test", ex=1)
            write_time = time.time() - write_start

            read_start = time.time()
            redis_manager.get(test_key)
            read_time = time.time() - read_start

            response_time = time.time() - start_time

            status = "healthy"
            if not info:
                status = "unhealthy"
            elif write_time > 0.1 or read_time > 0.1:  # 读写超过100ms
                status = "warning"
            elif response_time > 0.5:  # 总响应超过500ms
                status = "warning"

            return {
                "status": status,
                "response_time": response_time,
                "write_time": write_time,
                "read_time": read_time,
                "connected_clients": info.get(str("connected_clients"), 0)
                if info
                else 0,
                "used_memory": info.get(str("used_memory"), 0) if info else 0,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源健康状态"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu_percent = psutil.cpu_percent(interval=1)

            # 检查进程状态
            process = psutil.Process()
            process_memory = process.memory_info().rss
            process_cpu = process.cpu_percent()

            status = "healthy"
            warnings = []

            if memory.percent > 90:
                warnings.append(f"内存使用率过高: {memory.percent:.1f}%")
                status = "warning"
            elif memory.percent > 95:
                status = "unhealthy"

            if disk.percent > 90:
                warnings.append(f"磁盘使用率过高: {disk.percent:.1f}%")
                status = "warning"
            elif disk.percent > 95:
                status = "unhealthy"

            if cpu_percent > 80:
                warnings.append(f"CPU使用率过高: {cpu_percent:.1f}%")
                status = "warning"
            elif cpu_percent > 90:
                status = "unhealthy"

            if process_memory > 2 * 1024 * 1024 * 1024:  # 进程内存超过2GB
                warnings.append(
                    f"进程内存使用过高: {process_memory / 1024 / 1024:.1f}MB"
                )
                status = "warning"

            return {
                "status": status,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "cpu_percent": cpu_percent,
                "process_memory_mb": process_memory / 1024 / 1024,
                "process_cpu_percent": process_cpu,
                "warnings": warnings,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"系统资源健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _check_application_health(self) -> Dict[str, Any]:
        """检查应用程序健康状态"""
        try:
            status = "healthy"
            warnings = []

            # 检查最近的错误日志
            from src.database.connection import get_async_session
            from sqlalchemy import text

            async with get_async_session() as session:
                # 检查最近1小时的错误数量
                one_hour_ago = datetime.now() - timedelta(hours=1)
                result = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) as error_count
                    FROM error_logs
                    WHERE created_at >= :time_limit
                    """
                    ),
                    {"time_limit": one_hour_ago},
                )
                recent_errors = result.scalar()

                if recent_errors > 100:
                    warnings.append(f"最近1小时错误过多: {recent_errors}")
                    status = "warning"
                elif recent_errors > 500:
                    status = "unhealthy"

                # 检查任务失败率
                result = await session.execute(
                    text(
                        """
                    SELECT
                        COUNT(*) as total_tasks,
                        COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_tasks
                    FROM error_logs
                    WHERE created_at >= :time_limit
                    """
                    ),
                    {"time_limit": one_hour_ago},
                )
                task_stats = result.fetchone()

                if task_stats and task_stats.total_tasks > 0:
                    failure_rate = task_stats.failed_tasks / task_stats.total_tasks
                    if failure_rate > 0.1:  # 失败率超过10%
                        warnings.append(f"任务失败率过高: {failure_rate:.1%}")
                        status = "warning"
                    elif failure_rate > 0.2:  # 失败率超过20%
                        status = "unhealthy"

            return {
                "status": status,
                "recent_errors": recent_errors,
                "failure_rate": failure_rate if task_stats else 0,
                "warnings": warnings,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"应用程序健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _check_external_services(self) -> Dict[str, Any]:
        """检查外部服务健康状态"""
        try:
            status = "healthy"
            services_status = {}

            # 检查MLflow服务
            try:
                import mlflow

                # 尝试连接MLflow tracking server
                mlflow_client = mlflow.tracking.MlflowClient()
                mlflow_client.search_experiments(max_results=1)
                services_status["mlflow"] = {"status": "healthy"}
            except Exception as e:
                services_status["mlflow"] = {"status": "unhealthy", "error": str(e)}
                status = "warning"

            # 检查Kafka服务（如果配置）
            try:
                from src.streaming.kafka_producer import get_kafka_producer

                get_kafka_producer()
                # 简单的健康检查
                services_status["kafka"] = {"status": "healthy"}
            except Exception as e:
                services_status["kafka"] = {"status": "unhealthy", "error": str(e)}
                # Kafka不是关键服务，只设置为warning
                if status == "healthy":
                    status = "warning"

            return {
                "status": status,
                "services": services_status,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"外部服务健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _check_data_pipeline(self) -> Dict[str, Any]:
        """检查数据管道健康状态"""
        try:
            status = "healthy"
            warnings = []

            from src.database.connection import get_async_session
            from sqlalchemy import text

            async with get_async_session() as session:
                # 检查数据新鲜度
                result = await session.execute(
                    text(
                        """
                    SELECT
                        MAX(created_at) as latest_data_time,
                        COUNT(*) as total_records
                    FROM matches
                    """
                    )
                )
                match_stats = result.fetchone()

                if match_stats and match_stats.latest_data_time:
                    time_diff = datetime.now() - match_stats.latest_data_time
                    hours_diff = time_diff.total_seconds() / 3600

                    if hours_diff > 48:  # 数据超过48小时未更新
                        warnings.append(f"比赛数据过旧: {hours_diff:.1f}小时未更新")
                        status = "warning"
                    elif hours_diff > 72:  # 数据超过72小时未更新
                        status = "unhealthy"

                # 检查数据处理积压
                result = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) as backlog_count
                    FROM raw_matches
                    WHERE processed = false
                    """
                    )
                )
                backlog = result.scalar()

                if backlog > 1000:
                    warnings.append(f"数据处理积压过多: {backlog}条记录")
                    status = "warning"
                elif backlog > 5000:
                    status = "unhealthy"

            return {
                "status": status,
                "latest_data_time": (
                    match_stats.latest_data_time.isoformat()
                    if match_stats and match_stats.latest_data_time
                    else None
                ),
                "total_records": match_stats.total_records if match_stats else 0,
                "backlog_count": backlog,
                "warnings": warnings,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"数据管道健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# 全局监控器实例
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器实例"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


# 便捷函数
def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录HTTP请求的便捷函数"""
    monitor = get_system_monitor()
    monitor.record_request(method, endpoint, status_code, duration)


def record_db_query(operation: str, table: str, duration: float, is_slow: bool = False):
    """记录数据库查询的便捷函数"""
    monitor = get_system_monitor()
    monitor.record_database_query(operation, table, duration, is_slow)


def record_cache_op(operation: str, cache_type: str, result: str):
    """记录缓存操作的便捷函数"""
    monitor = get_system_monitor()
    monitor.record_cache_operation(operation, cache_type, result)


def record_prediction(model_version: str, league: str):
    """记录预测操作的便捷函数"""
    monitor = get_system_monitor()
    monitor.record_prediction(model_version, league)


async def start_system_monitoring(interval: int = 30):
    """启动系统监控的便捷函数"""
    monitor = get_system_monitor()
    await monitor.start_monitoring(interval)


async def stop_system_monitoring():
    """停止系统监控的便捷函数"""
    monitor = get_system_monitor()
    await monitor.stop_monitoring()
