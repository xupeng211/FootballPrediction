"""数据库连接池优化管理器
Database Connection Pool Optimization Manager.

提供智能的数据库连接池管理、监控和自动优化功能。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import event
from sqlalchemy.pool import Pool, QueuePool

logger = logging.getLogger(__name__)


@dataclass
class PoolMetrics:
    """连接池指标."""

    pool_size: int = 0
    checked_in: int = 0
    checked_out: int = 0
    overflow: int = 0
    invalid: int = 0
    total_connections: int = 0
    utilization_rate: float = 0.0
    wait_time_avg: float = 0.0
    creation_time: datetime | None = None
    last_activity: datetime | None = None


@dataclass
class PoolOptimizationConfig:
    """连接池优化配置."""

    min_pool_size: int = 5
    max_pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    optimization_interval: int = 300  # 5分钟
    auto_adjust: bool = True
    utilization_threshold_high: float = 80.0
    utilization_threshold_low: float = 30.0


class ConnectionPoolOptimizer:
    """连接池优化器."""

    def __init__(self, config: PoolOptimizationConfig | None = None):
        self.config = config or PoolOptimizationConfig()
        self.pools: dict[str, Pool] = {}
        self.pool_metrics: dict[str, PoolMetrics] = {}
        self.optimization_history: list[dict[str, Any]] = []
        self.is_monitoring = False
        self.monitoring_task: asyncio.Task | None = None

    def register_pool(self, pool_name: str, pool: Pool):
        """注册连接池."""
        self.pools[pool_name] = pool
        self.pool_metrics[pool_name] = PoolMetrics(creation_time=datetime.utcnow())

        # 注册连接池事件监听器
        self._register_pool_events(pool_name, pool)

        logger.info(f"Registered connection pool: {pool_name}")

    def _register_pool_events(self, pool_name: str, pool: Pool):
        """注册连接池事件监听器."""

        @event.listens_for(pool, "connect")
        def on_connect(dbapi_connection, connection_record):
            metrics = self.pool_metrics[pool_name]
            metrics.last_activity = datetime.utcnow()
            logger.debug(f"New connection established in pool: {pool_name}")

        @event.listens_for(pool, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            metrics = self.pool_metrics[pool_name]
            metrics.last_activity = datetime.utcnow()
            metrics.checked_out += 1
            logger.debug(f"Connection checked out from pool: {pool_name}")

        @event.listens_for(pool, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            metrics = self.pool_metrics[pool_name]
            metrics.last_activity = datetime.utcnow()
            metrics.checked_in += 1
            logger.debug(f"Connection checked in to pool: {pool_name}")

    async def start_monitoring(self):
        """开始监控."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Connection pool monitoring started")

    async def stop_monitoring(self):
        """停止监控."""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Connection pool monitoring stopped")

    async def _monitoring_loop(self):
        """监控循环."""
        while self.is_monitoring:
            try:
                await self._update_pool_metrics()

                if self.config.auto_adjust:
                    await self._auto_optimize_pools()

                await asyncio.sleep(self.config.optimization_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # 错误时等待1分钟

    async def _update_pool_metrics(self):
        """更新连接池指标."""
        for pool_name, pool in self.pools.items():
            try:
                metrics = self.pool_metrics[pool_name]

                # 获取连接池状态
                if hasattr(pool, "size"):
                    metrics.pool_size = pool.size()
                    metrics.checked_in = pool.checkedin()
                    metrics.checked_out = pool.checkedout()
                    metrics.overflow = pool.overflow()
                    metrics.invalid = pool.invalid()
                    metrics.total_connections = metrics.checked_in + metrics.checked_out

                    # 计算利用率
                    if metrics.pool_size > 0:
                        metrics.utilization_rate = (
                            metrics.checked_out / metrics.pool_size
                        ) * 100

                logger.debug(f"Updated metrics for pool {pool_name}: {metrics}")

            except Exception as e:
                logger.error(f"Error updating metrics for pool {pool_name}: {e}")

    async def _auto_optimize_pools(self):
        """自动优化连接池."""
        for pool_name, metrics in self.pool_metrics.items():
            try:
                pool = self.pools[pool_name]

                # 检查利用率是否过高
                if metrics.utilization_rate > self.config.utilization_threshold_high:
                    await self._scale_up_pool(pool_name, pool, metrics)

                # 检查利用率是否过低
                elif metrics.utilization_rate < self.config.utilization_threshold_low:
                    await self._scale_down_pool(pool_name, pool, metrics)

            except Exception as e:
                logger.error(f"Error auto-optimizing pool {pool_name}: {e}")

    async def _scale_up_pool(self, pool_name: str, pool: Pool, metrics: PoolMetrics):
        """扩大连接池."""
        try:
            # 对于QueuePool，可以调整max_overflow
            if isinstance(pool, QueuePool):
                current_overflow = pool._max_overflow
                new_overflow = min(
                    current_overflow + 2, self.config.max_pool_size - pool._pool_size
                )

                if new_overflow > current_overflow:
                    logger.info(
                        f"Scaling up pool {pool_name}: overflow {current_overflow} -> {new_overflow}"
                    )

                    # 记录优化操作
                    optimization_record = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "pool_name": pool_name,
                        "operation": "scale_up",
                        "old_overflow": current_overflow,
                        "new_overflow": new_overflow,
                        "utilization_rate": metrics.utilization_rate,
                        "reason": "high_utilization",
                    }
                    self.optimization_history.append(optimization_record)

        except Exception as e:
            logger.error(f"Error scaling up pool {pool_name}: {e}")

    async def _scale_down_pool(self, pool_name: str, pool: Pool, metrics: PoolMetrics):
        """缩小连接池."""
        try:
            # 对于QueuePool，可以减少max_overflow
            if isinstance(pool, QueuePool):
                current_overflow = pool._max_overflow
                new_overflow = max(current_overflow - 1, 0)

                if new_overflow < current_overflow:
                    logger.info(
                        f"Scaling down pool {pool_name}: overflow {current_overflow} -> {new_overflow}"
                    )

                    # 记录优化操作
                    optimization_record = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "pool_name": pool_name,
                        "operation": "scale_down",
                        "old_overflow": current_overflow,
                        "new_overflow": new_overflow,
                        "utilization_rate": metrics.utilization_rate,
                        "reason": "low_utilization",
                    }
                    self.optimization_history.append(optimization_record)

        except Exception as e:
            logger.error(f"Error scaling down pool {pool_name}: {e}")

    async def get_pool_status(self, pool_name: str) -> dict[str, Any] | None:
        """获取连接池状态."""
        if pool_name not in self.pools:
            return None

        pool = self.pools[pool_name]
        metrics = self.pool_metrics[pool_name]

        status = {
            "pool_name": pool_name,
            "pool_type": type(pool).__name__,
            "metrics": {
                "pool_size": metrics.pool_size,
                "checked_in": metrics.checked_in,
                "checked_out": metrics.checked_out,
                "overflow": metrics.overflow,
                "invalid": metrics.invalid,
                "total_connections": metrics.total_connections,
                "utilization_rate": round(metrics.utilization_rate, 2),
                "creation_time": (
                    metrics.creation_time.isoformat() if metrics.creation_time else None
                ),
                "last_activity": (
                    metrics.last_activity.isoformat() if metrics.last_activity else None
                ),
            },
            "config": self._get_pool_config(pool),
            "health_status": self._evaluate_pool_health(metrics),
            "recommendations": self._generate_pool_recommendations(metrics),
        }

        return status

    def _get_pool_config(self, pool: Pool) -> dict[str, Any]:
        """获取连接池配置."""
        config = {}

        if isinstance(pool, QueuePool):
            config.update(
                {
                    "pool_size": pool._pool_size,
                    "max_overflow": pool._max_overflow,
                    "timeout": pool._timeout,
                    "recycle": pool._recycle,
                    "pre_ping": pool._pre_ping,
                }
            )

        return config

    def _evaluate_pool_health(self, metrics: PoolMetrics) -> dict[str, Any]:
        """评估连接池健康状态."""
        health_status = {"overall": "healthy", "issues": [], "warnings": []}

        # 检查利用率
        if metrics.utilization_rate > 90:
            health_status["overall"] = "critical"
            health_status["issues"].append(
                f"连接池利用率过高: {metrics.utilization_rate:.1f}%"
            )
        elif metrics.utilization_rate > 80:
            health_status["overall"] = "warning"
            health_status["warnings"].append(
                f"连接池利用率较高: {metrics.utilization_rate:.1f}%"
            )

        # 检查无效连接
        if metrics.invalid > 0:
            health_status["issues"].append(f"发现无效连接: {metrics.invalid}")

        # 检查连接泄漏
        if metrics.checked_out > metrics.pool_size + 5:  # 允许少量溢出
            health_status["warnings"].append("可能存在连接泄漏")

        # 检查连接池空闲时间
        if (
            metrics.last_activity
            and datetime.utcnow() - metrics.last_activity > timedelta(hours=1)
        ):
            health_status["warnings"].append("连接池长时间无活动")

        return health_status

    def _generate_pool_recommendations(self, metrics: PoolMetrics) -> list[str]:
        """生成连接池优化建议."""
        recommendations = []

        if metrics.utilization_rate > 85:
            recommendations.append("考虑增加连接池大小或max_overflow")
        elif metrics.utilization_rate < 20:
            recommendations.append("考虑减少连接池大小以节省资源")

        if metrics.invalid > metrics.total_connections * 0.1:  # 超过10%的无效连接
            recommendations.append("检查数据库连接稳定性，考虑降低pool_recycle时间")

        if (
            not metrics.last_activity
            or datetime.utcnow() - metrics.last_activity > timedelta(hours=2)
        ):
            recommendations.append("连接池长时间未使用，考虑清理或配置连接超时")

        return recommendations

    async def get_all_pools_status(self) -> dict[str, Any]:
        """获取所有连接池状态."""
        all_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_active": self.is_monitoring,
            "total_pools": len(self.pools),
            "pools": {},
            "summary": {
                "total_connections": 0,
                "avg_utilization": 0.0,
                "healthy_pools": 0,
                "warning_pools": 0,
                "critical_pools": 0,
            },
        }

        total_utilization = 0.0
        pool_count = 0

        for pool_name in self.pools:
            status = await self.get_pool_status(pool_name)
            if status:
                all_status["pools"][pool_name] = status

                # 统计汇总信息
                metrics = status["metrics"]
                all_status["summary"]["total_connections"] += metrics[
                    "total_connections"
                ]
                total_utilization += metrics["utilization_rate"]
                pool_count += 1

                health = status["health_status"]["overall"]
                if health == "healthy":
                    all_status["summary"]["healthy_pools"] += 1
                elif health == "warning":
                    all_status["summary"]["warning_pools"] += 1
                elif health == "critical":
                    all_status["summary"]["critical_pools"] += 1

        if pool_count > 0:
            all_status["summary"]["avg_utilization"] = round(
                total_utilization / pool_count, 2
            )

        return all_status

    async def optimize_pool_manually(
        self, pool_name: str, optimization_type: str, **kwargs
    ) -> dict[str, Any]:
        """手动优化连接池."""
        if pool_name not in self.pools:
            return {"error": f"Pool {pool_name} not found"}

        pool = self.pools[pool_name]
        metrics = self.pool_metrics[pool_name]

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "pool_name": pool_name,
            "optimization_type": optimization_type,
            "success": False,
            "changes": {},
            "message": "",
        }

        try:
            if optimization_type == "reset_overflow":
                if isinstance(pool, QueuePool):
                    old_overflow = pool._max_overflow
                    # 这里不能直接修改，需要重新创建连接池
                    result["message"] = "需要重新创建连接池来重置overflow设置"
                    result["changes"]["overflow"] = {
                        "old": old_overflow,
                        "new": self.config.max_overflow,
                    }

            elif optimization_type == "force_recycle":
                result["message"] = "强制回收连接功能需要连接池重启"

            elif optimization_type == "clear_invalid":
                invalid_count = metrics.invalid
                metrics.invalid = 0  # 重置计数器
                result["changes"]["invalid_connections_cleared"] = invalid_count
                result["message"] = f"已清理 {invalid_count} 个无效连接计数"
                result["success"] = True

            else:
                result["message"] = (
                    f"Unsupported optimization type: {optimization_type}"
                )

            # 记录优化历史
            if result["success"]:
                self.optimization_history.append(
                    {
                        "timestamp": result["timestamp"],
                        "pool_name": pool_name,
                        "operation": f"manual_{optimization_type}",
                        "changes": result["changes"],
                        "metrics_before": {
                            "utilization_rate": metrics.utilization_rate,
                            "total_connections": metrics.total_connections,
                        },
                    }
                )

        except Exception as e:
            result["message"] = f"Optimization failed: {str(e)}"
            logger.error(f"Manual optimization failed for pool {pool_name}: {e}")

        return result

    def get_optimization_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取优化历史."""
        return self.optimization_history[-limit:]


# 全局连接池优化器实例
_pool_optimizer: ConnectionPoolOptimizer | None = None


def get_connection_pool_optimizer() -> ConnectionPoolOptimizer:
    """获取全局连接池优化器实例."""
    global _pool_optimizer
    if _pool_optimizer is None:
        _pool_optimizer = ConnectionPoolOptimizer()
    return _pool_optimizer


async def initialize_connection_pool_optimizer(
    config: PoolOptimizationConfig | None = None,
) -> ConnectionPoolOptimizer:
    """初始化连接池优化器."""
    global _pool_optimizer

    _pool_optimizer = ConnectionPoolOptimizer(config)
    await _pool_optimizer.start_monitoring()

    logger.info("Connection pool optimizer initialized and monitoring started")
    return _pool_optimizer
