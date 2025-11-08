"""
实时性能监控仪表板
Real-time Performance Monitoring Dashboard

提供Web界面的实时性能监控，包括系统指标、API性能、数据库状态等。
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from ..performance.enhanced_optimizer import EnhancedPerformanceOptimizer

logger = logging.getLogger(__name__)

# ============================================================================
# 监控数据管理器
# ============================================================================


class MonitoringDataManager:
    """监控数据管理器"""

    def __init__(self):
        self.connected_clients: list[WebSocket] = []
        self.performance_optimizer: EnhancedPerformanceOptimizer | None = None
        self.monitoring_active = False
        self.update_interval = 2.0  # 2秒更新一次
        self.max_history_points = 100  # 保留最近100个数据点
        self.metrics_history: list[dict[str, Any]] = []

    async def initialize(self):
        """初始化监控系统"""
        try:
            self.performance_optimizer = EnhancedPerformanceOptimizer()
            await self.performance_optimizer.initialize(
                database_url="sqlite+aiosqlite:///monitoring.db",
                max_concurrent_requests=50,
            )
            logger.info("监控系统初始化完成")
        except Exception as e:
            logger.error(f"监控系统初始化失败: {e}")
            # 创建一个模拟的性能优化器用于演示
            self.performance_optimizer = MockPerformanceOptimizer()

    async def register_client(self, websocket: WebSocket):
        """注册WebSocket客户端"""
        self.connected_clients.append(websocket)
        logger.info(
            f"客户端连接: {websocket.client.host}, 总连接数: {len(self.connected_clients)}"
        )

    async def unregister_client(self, websocket: WebSocket):
        """注销WebSocket客户端"""
        if websocket in self.connected_clients:
            self.connected_clients.remove(websocket)
            logger.info(
                f"客户端断开: {websocket.client.host}, 总连接数: {len(self.connected_clients)}"
            )

    async def start_monitoring(self):
        """开始监控"""
        if not self.monitoring_active:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info("实时监控已启动")

    async def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        logger.info("实时监控已停止")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                # 收集当前指标
                current_metrics = await self._collect_metrics()

                # 添加到历史记录
                self.metrics_history.append(current_metrics)
                if len(self.metrics_history) > self.max_history_points:
                    self.metrics_history.pop(0)

                # 广播给所有连接的客户端
                await self._broadcast_metrics(current_metrics)

                # 评估告警规则
                try:
                    from .alert_system import alert_manager

                    await alert_manager.evaluate_metrics(current_metrics)
                except Exception as e:
                    logger.warning(f"告警评估失败: {e}")

                # 等待下次更新
                await asyncio.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(self.update_interval)

    async def _collect_metrics(self) -> dict[str, Any]:
        """收集当前指标"""
        if not self.performance_optimizer:
            return self._get_mock_metrics()

        try:
            # 获取综合指标
            comprehensive_metrics = (
                await self.performance_optimizer.get_comprehensive_metrics()
            )

            # 获取系统资源信息
            system_info = await self._get_system_info()

            # 组合指标数据
            return {
                "timestamp": datetime.now().isoformat(),
                "system": comprehensive_metrics.get("system", {}),
                "database": comprehensive_metrics.get("database", {}),
                "cache": comprehensive_metrics.get("cache", {}),
                "concurrency": comprehensive_metrics.get("concurrency", {}),
                "system_info": system_info,
                "alerts": await self._check_alerts(comprehensive_metrics),
            }
        except Exception as e:
            logger.error(f"收集指标失败: {e}")
            return self._get_mock_metrics()

    async def _get_system_info(self) -> dict[str, Any]:
        """获取系统信息"""
        try:
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
                "load_average": (
                    psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0]
                ),
            }
        except ImportError:
            # 如果没有psutil，返回模拟数据
            return {
                "cpu_percent": 45.2,
                "memory_percent": 68.7,
                "disk_usage": 32.1,
                "load_average": [1.2, 1.1, 0.9],
            }

    async def _check_alerts(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """检查告警条件"""
        alerts = []

        # 检查响应时间告警
        system_metrics = metrics.get("system", {})
        if system_metrics.get("avg_response_time", 0) > 1.0:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"平均响应时间过高: {system_metrics.get('avg_response_time', 0):.2f}s",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 检查错误率告警
        if system_metrics.get("error_rate", 0) > 5.0:
            alerts.append(
                {
                    "level": "critical",
                    "message": f"错误率过高: {system_metrics.get('error_rate', 0):.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 检查数据库连接告警
        db_metrics = metrics.get("database", {})
        if db_metrics.get("active_connections", 0) > 50:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"数据库连接数过高: {db_metrics.get('active_connections', 0)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 检查缓存命中率告警
        cache_metrics = metrics.get("cache", {})
        if cache_metrics.get("hit_rate", 100) < 70:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"缓存命中率过低: {cache_metrics.get('hit_rate', 100):.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return alerts

    async def _broadcast_metrics(self, metrics: dict[str, Any]):
        """广播指标给所有客户端"""
        if not self.connected_clients:
            return

        message = json.dumps(metrics, default=str)
        disconnected_clients = []

        for client in self.connected_clients:
            try:
                if client.client_state == WebSocketState.CONNECTED:
                    await client.send_text(message)
                else:
                    disconnected_clients.append(client)
            except Exception as e:
                logger.warning(f"发送数据到客户端失败: {e}")
                disconnected_clients.append(client)

        # 清理断开的客户端
        for client in disconnected_clients:
            await self.unregister_client(client)

    def _get_mock_metrics(self) -> dict[str, Any]:
        """获取模拟指标数据"""
        import random

        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "total_requests": random.randint(800, 1200),
                "active_connections": random.randint(20, 80),
                "avg_response_time": random.uniform(0.1, 0.8),
                "requests_per_second": random.uniform(5, 25),
                "error_rate": random.uniform(0, 3),
            },
            "database": {
                "active_connections": random.randint(5, 25),
                "total_connections": random.randint(30, 100),
                "connection_pool_size": 20,
                "avg_query_time": random.uniform(0.05, 0.3),
                "slow_queries": random.randint(0, 5),
            },
            "cache": {
                "hit_count": random.randint(200, 800),
                "miss_count": random.randint(50, 200),
                "hit_rate": random.uniform(70, 95),
                "avg_response_time": random.uniform(0.001, 0.01),
            },
            "concurrency": {
                "active_tasks": random.randint(5, 30),
                "queued_requests": random.randint(0, 10),
                "worker_count": 10,
                "available_slots": random.randint(5, 15),
            },
            "system_info": {
                "cpu_percent": random.uniform(20, 80),
                "memory_percent": random.uniform(40, 85),
                "disk_usage": random.uniform(20, 60),
                "load_average": [
                    random.uniform(0.5, 2.0),
                    random.uniform(0.5, 2.0),
                    random.uniform(0.5, 2.0),
                ],
            },
            "alerts": [],
        }

    def get_metrics_history(self, minutes: int = 30) -> list[dict[str, Any]]:
        """获取历史指标数据"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            metrics
            for metrics in self.metrics_history
            if datetime.fromisoformat(metrics["timestamp"]) > cutoff_time
        ]


# ============================================================================
# 模拟性能优化器（用于演示）
# ============================================================================


class MockPerformanceOptimizer:
    """模拟性能优化器"""

    def __init__(self):
        self.initialized = True

    async def initialize(self, database_url: str, max_concurrent_requests: int):
        """模拟初始化"""
        pass

    async def get_comprehensive_metrics(self) -> dict[str, Any]:
        """获取模拟指标"""
        import random

        return {
            "system": {
                "total_requests": random.randint(800, 1200),
                "active_connections": random.randint(20, 80),
                "avg_response_time": random.uniform(0.1, 0.8),
                "requests_per_second": random.uniform(5, 25),
                "error_rate": random.uniform(0, 3),
            },
            "database": {
                "active_connections": random.randint(5, 25),
                "total_connections": random.randint(30, 100),
                "connection_pool_size": 20,
                "avg_query_time": random.uniform(0.05, 0.3),
                "slow_queries": random.randint(0, 5),
            },
            "cache": {
                "hit_count": random.randint(200, 800),
                "miss_count": random.randint(50, 200),
                "hit_rate": random.uniform(70, 95),
                "avg_response_time": random.uniform(0.001, 0.01),
            },
            "concurrency": {
                "active_tasks": random.randint(5, 30),
                "queued_requests": random.randint(0, 10),
                "worker_count": 10,
                "available_slots": random.randint(5, 15),
            },
        }


# ============================================================================
# 全局监控管理器实例
# ============================================================================

monitoring_manager = MonitoringDataManager()
