from typing import Set
from typing import Dict
from typing import List
#!/usr/bin/env python3
"""
实时质量监控WebSocket服务器
Real-time Quality Monitoring WebSocket Server

提供实时质量指标推送、告警广播和客户端连接管理
"""

import asyncio
import json
from datetime import datetime

import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.core.logging_system import get_logger
from src.metrics.advanced_analyzer import AdvancedMetricsAnalyzer
from src.quality_gates.gate_system import QualityGateSystem

logger = get_logger(__name__)


class QualityMonitorServer:
    """实时质量监控服务器"""

    def __init__(self):
        self.app = FastAPI(
            title="实时质量监控服务",
            description="Real-time Quality Monitoring WebSocket Server",
            version="1.0.0",
        )

        # 配置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应该限制具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 连接管理
        self.active_connections: Set[WebSocket] = set()

        # 数据存储
        self.redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

        # 分析器
        self.metrics_analyzer = AdvancedMetricsAnalyzer()
        self.quality_gate_system = QualityGateSystem()

        # 配置路由
        self._setup_routes()

        # 后台任务
        self.background_task = None

        self.logger = get_logger(self.__class__.__name__)

    def _setup_routes(self):
        """设置路由"""

        @self.app.websocket("/ws/quality")
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_websocket_connection(websocket)

        @self.app.get("/api/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @self.app.get("/api/current-metrics")
        async def get_current_metrics():
            """获取当前质量指标"""
            try:
                metrics = await self.collect_quality_metrics()
                return metrics
            except Exception as e:
                self.logger.error(f"获取当前指标失败: {e}")
                return {"error": str(e)}

        @self.app.get("/api/alerts")
        async def get_active_alerts():
            """获取活跃告警"""
            try:
                alerts = await self.get_active_alerts()
                return {"alerts": alerts}
            except Exception as e:
                self.logger.error(f"获取告警失败: {e}")
                return {"alerts": []}

    async def handle_websocket_connection(self, websocket: WebSocket):
        """处理WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)

        client_id = f"client_{len(self.active_connections)}"
        self.logger.info(f"新客户端连接: {client_id}, 总连接数: {len(self.active_connections)}")

        try:
            # 发送初始数据
            initial_metrics = await self.collect_quality_metrics()
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "initial_data",
                        "data": initial_metrics,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

            # 保持连接并处理客户端消息
            while True:
                data = await websocket.receive_text()
                await self.handle_client_message(websocket, data)

        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
            self.logger.info(
                f"客户端断开连接: {client_id}, 剩余连接数: {len(self.active_connections)}"
            )
        except Exception as e:
            self.logger.error(f"WebSocket连接错误: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def handle_client_message(self, websocket: WebSocket, data: str):
        """处理客户端消息"""
        try:
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "request_metrics":
                metrics = await self.collect_quality_metrics()
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "metrics_update",
                            "data": metrics,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )
            elif message_type == "ping":
                await websocket.send_text(
                    json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()})
                )

        except json.JSONDecodeError:
            self.logger.warning(f"收到无效JSON消息: {data}")
        except Exception as e:
            self.logger.error(f"处理客户端消息失败: {e}")

    async def collect_quality_metrics(self) -> Dict:
        """收集质量指标"""
        try:
            # 获取基础质量指标
            current_time = datetime.now()

            # 运行质量门禁检查
            quality_results = self.quality_gate_system.run_all_checks()

            # 收集实时指标
            metrics = {
                "timestamp": current_time.isoformat(),
                "overall_score": quality_results.get("average_score", 0),
                "overall_status": quality_results.get("overall_status", "UNKNOWN"),
                "gates_checked": quality_results.get("gates_checked", 0),
                "summary": quality_results.get("summary", {}),
                "detailed_results": quality_results.get("results", []),
                # 实时性能指标
                "performance": {
                    "response_time_ms": 150,  # 模拟响应时间
                    "cpu_usage": 45.2,  # 模拟CPU使用率
                    "memory_usage": 68.5,  # 模拟内存使用率
                    "active_connections": len(self.active_connections),
                },
                # 趋势数据 (从Redis获取历史数据)
                "trends": await self.get_trend_data(),
                # 告警信息
                "alerts": await self.get_active_alerts(),
                # 系统健康状态
                "system_health": {
                    "server_status": "healthy",
                    "database_status": "healthy",
                    "redis_status": ("healthy" if self.redis_client.ping() else "unhealthy"),
                },
            }

            # 缓存到Redis
            self.redis_client.setex(
                f"quality_metrics_{current_time.strftime('%Y%m%d_%H%M')}",
                3600,  # 1小时过期
                json.dumps(metrics),
            )

            return metrics

        except Exception as e:
            self.logger.error(f"收集质量指标失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "overall_score": 0,
                "overall_status": "ERROR",
            }

    async def get_trend_data(self, hours: int = 24) -> Dict:
        """获取趋势数据"""
        try:
            # 从Redis获取历史数据
            trend_data = []
            current_time = datetime.now()

            for i in range(hours * 12):  # 每5分钟一个数据点
                timestamp = current_time.replace(
                    minute=(current_time.minute - i * 5) % 60,
                    hour=current_time.hour - (i * 5) // 60,
                )
                key = f"quality_metrics_{timestamp.strftime('%Y%m%d_%H%M')}"
                data = self.redis_client.get(key)

                if data:
                    metrics = json.loads(data)
                    trend_data.append(
                        {
                            "timestamp": timestamp.isoformat(),
                            "score": metrics.get("overall_score", 0),
                            "status": metrics.get("overall_status", "UNKNOWN"),
                        }
                    )

            return {
                "data_points": len(trend_data),
                "trend": trend_data[:100],  # 最多返回100个数据点
            }

        except Exception as e:
            self.logger.error(f"获取趋势数据失败: {e}")
            return {"data_points": 0, "trend": []}

    async def get_active_alerts(self) -> List[Dict]:
        """获取活跃告警"""
        try:
            alerts = []

            # 从Redis获取告警
            alert_keys = self.redis_client.keys("alert:*")
            for key in alert_keys:
                alert_data = self.redis_client.get(key)
                if alert_data:
                    alerts.append(json.loads(alert_data))

            # 检查实时告警条件
            current_metrics = await self.collect_quality_metrics()

            # 质量分数告警
            if current_metrics.get("overall_score", 0) < 8.0:
                alerts.append(
                    {
                        "id": "quality_score_low",
                        "type": "quality",
                        "severity": "warning",
                        "title": "质量分数偏低",
                        "message": f"当前质量分数: {current_metrics.get('overall_score', 0):.2f}",
                        "timestamp": datetime.now().isoformat(),
                        "active": True,
                    }
                )

            # 系统健康告警
            system_health = current_metrics.get("system_health", {})
            if system_health.get("redis_status") != "healthy":
                alerts.append(
                    {
                        "id": "redis_unhealthy",
                        "type": "system",
                        "severity": "error",
                        "title": "Redis连接异常",
                        "message": "Redis缓存服务连接失败",
                        "timestamp": datetime.now().isoformat(),
                        "active": True,
                    }
                )

            return alerts

        except Exception as e:
            self.logger.error(f"获取活跃告警失败: {e}")
            return []

    async def broadcast_quality_update(self, data: Dict):
        """广播质量更新给所有连接的客户端"""
        if not self.active_connections:
            return

        message = json.dumps(
            {
                "type": "quality_update",
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 并发发送给所有客户端
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.warning(f"发送消息失败: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def start_background_monitoring(self):
        """启动后台监控任务"""
        while True:
            try:
                # 收集最新指标
                metrics = await self.collect_quality_metrics()

                # 广播给所有客户端
                await self.broadcast_quality_update(metrics)

                # 检查告警条件
                await self.check_alert_conditions(metrics)

                # 等待5分钟后再次检查
                await asyncio.sleep(300)  # 5分钟

            except Exception as e:
                self.logger.error(f"后台监控任务失败: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试

    async def check_alert_conditions(self, metrics: Dict):
        """检查告警条件"""
        try:
            alerts = []

            # 质量分数告警
            score = metrics.get("overall_score", 0)
            if score < 7.0:
                alerts.append(
                    {
                        "id": f"quality_critical_{datetime.now().strftime('%Y%m%d%H%M')}",
                        "type": "quality",
                        "severity": "critical",
                        "title": "质量分数严重偏低",
                        "message": f"质量分数 {score:.2f} 低于临界值 7.0",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            elif score < 8.0:
                alerts.append(
                    {
                        "id": f"quality_warning_{datetime.now().strftime('%Y%m%d%H%M')}",
                        "type": "quality",
                        "severity": "warning",
                        "title": "质量分数偏低",
                        "message": f"质量分数 {score:.2f} 低于目标值 8.0",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 连接数告警
            active_connections = len(self.active_connections)
            if active_connections > 50:
                alerts.append(
                    {
                        "id": f"connections_high_{datetime.now().strftime('%Y%m%d%H%M')}",
                        "type": "system",
                        "severity": "warning",
                        "title": "连接数过高",
                        "message": f"活跃连接数 {active_connections} 超过阈值 50",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 保存告警到Redis
            for alert in alerts:
                self.redis_client.setex(
                    f"alert:{alert['id']}", 3600, json.dumps(alert)  # 1小时过期
                )

            # 如果有新告警，立即广播
            if alerts:
                await self.broadcast_quality_update({"type": "new_alerts", "alerts": alerts})

        except Exception as e:
            self.logger.error(f"检查告警条件失败: {e}")

    async def start_server(self):
        """启动服务器和后台任务"""
        self.logger.info("启动实时质量监控服务器...")

        # 启动后台监控任务
        self.background_task = asyncio.create_task(self.start_background_monitoring())

        self.logger.info("实时质量监控服务器启动完成")

    def stop_server(self):
        """停止服务器"""
        if self.background_task:
            self.background_task.cancel()

        # 关闭所有WebSocket连接
        for connection in self.active_connections.copy():
            try:
                asyncio.create_task(connection.close())
            except Exception:
                pass

        self.active_connections.clear()
        self.logger.info("实时质量监控服务器已停止")


# 创建全局服务器实例
monitor_server = QualityMonitorServer()

# FastAPI应用实例
app = monitor_server.app


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    await monitor_server.start_server()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    monitor_server.stop_server()


if __name__ == "__main__":
    import uvicorn

    print("🚀 启动实时质量监控服务器...")
    print("📡 WebSocket服务: ws://localhost:8001/ws/quality")
    print("📊 API文档: http://localhost:8001/docs")
    print("❤️  健康检查: http://localhost:8001/api/health")

    uvicorn.run(
        "src.realtime.quality_monitor_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
