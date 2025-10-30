#!/usr/bin/env python3
""""
实时质量监控面板API
Real-time Quality Monitoring Dashboard API

提供实时质量数据,WebSocket连接和RESTful API接口
""""

import asyncio
import json
from pathlib import Path

import uvicorn
FastAPI,
WebSocket,
    WebSocketDisconnect,
    HTTPException,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.core.logging_system import get_logger
from scripts.quality_guardian import QualityGuardian
from scripts.improvement_monitor import ImprovementMonitor

logger = get_logger(__name__)

app = FastAPI(
    title="质量监控面板API", description="实时质量监控和改进分析系统", version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
quality_guardian = QualityGuardian()
improvement_monitor = ImprovementMonitor()
connected_clients: List[WebSocket] = []
latest_quality_data: Dict[str, Any] = {}


class QualityMetrics(BaseModel):
    """质量指标数据模型"""

    timestamp: datetime
    overall_score: float
    coverage_percentage: float
    code_quality_score: float
    security_score: float
    ruff_errors: int
    mypy_errors: int
    file_count: int
    tests_run: int
    tests_passed: int


class TrendData(BaseModel):
    """趋势数据模型"""

    timestamp: datetime
    metric_name: str
    value: float
    change_percentage: float


class AlertData(BaseModel):
    """告警数据模型"""

    timestamp: datetime
    level: str  # info, warning, error, critical
    message: str
    source: str
    details: Dict[str, Any]


def setup_static_files():
    """设置静态文件服务"""
    frontend_path = Path(__file__).parent / "frontend" / "build"
    if frontend_path.exists():
        app.mount(
            "/static", StaticFiles(directory=frontend_path / "static"), name="static"
        )
        app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("质量监控面板API启动")
    # 启动后台数据收集任务
    asyncio.create_task(collect_quality_data())


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("质量监控面板API关闭")


async def collect_quality_data():
    """后台任务:定期收集质量数据"""
    while True:
        try:
            # 收集质量数据
            quality_data = await get_current_quality_metrics()
            global latest_quality_data
            latest_quality_data = quality_data

            # 向所有连接的客户端广播数据
            await broadcast_quality_update(quality_data)

            # 等待30秒
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"收集质量数据时发生错误: {e}")
            await asyncio.sleep(30)


async def get_current_quality_metrics() -> Dict[str, Any]:
    """获取当前质量指标"""
    try:
        # 运行质量检查
        quality_report = quality_guardian.run_quality_check()

        # 获取改进监控数据
        improvement_data = improvement_monitor.get_current_status()

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_score": quality_report.get("overall_score", 0.0),
            "coverage_percentage": quality_report.get("coverage_percentage", 0.0),
            "code_quality_score": quality_report.get("code_quality_score", 0.0),
            "security_score": quality_report.get("security_score", 0.0),
            "ruff_errors": quality_report.get("ruff_errors", 0),
            "mypy_errors": quality_report.get("mypy_errors", 0),
            "file_count": quality_report.get("file_count", 0),
            "tests_run": improvement_data.get("total_tests", 0),
            "tests_passed": improvement_data.get("passed_tests", 0),
            "improvement_cycles": improvement_data.get("total_cycles", 0),
            "success_rate": improvement_data.get("success_rate", 0.0),
        }

    except Exception as e:
        logger.error(f"获取质量指标时发生错误: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_score": 0.0,
            "coverage_percentage": 0.0,
            "code_quality_score": 0.0,
            "security_score": 0.0,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "file_count": 0,
            "tests_run": 0,
            "tests_passed": 0,
            "improvement_cycles": 0,
            "success_rate": 0.0,
        }


async def broadcast_quality_update(data: Dict[str, Any]):
    """向所有WebSocket连接广播质量更新"""
    if not connected_clients:
        return

    message = json.dumps(data)
    disconnected_clients = []

    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception as e:
            logger.warning(f"向客户端发送数据失败: {e}")
            disconnected_clients.append(client)

    # 移除断开的连接
    for client in disconnected_clients:
        if client in connected_clients:
            connected_clients.remove(client)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点,用于实时数据推送"""
    await websocket.accept()
    connected_clients.append(websocket)

    logger.info(f"新的WebSocket连接: {len(connected_clients)} 个活跃连接")

    try:
        # 发送当前数据
        if latest_quality_data:
            await websocket.send_text(json.dumps(latest_quality_data))

        # 保持连接
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info(f"WebSocket连接断开: {len(connected_clients)} 个活跃连接")


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "connected_clients": len(connected_clients),
        "latest_data": bool(latest_quality_data),
    }


@app.get("/api/quality/metrics", response_model=QualityMetrics)
async def get_quality_metrics():
    """获取当前质量指标"""
    if not latest_quality_data:
        # 如果没有数据,立即获取
        metrics = await get_current_quality_metrics()
        return QualityMetrics(**metrics)

    return QualityMetrics(**latest_quality_data)


@app.get("/api/quality/trends")
async def get_quality_trends(hours: int = 24):
    """获取质量趋势数据"""
    # TODO: 实现趋势数据收集
    # 这里应该从数据库或历史数据中获取趋势信息
    return {
        "time_range_hours": hours,
        "data_points": [],
        "trends": {
            "overall_score": "stable",
            "coverage": "improving",
            "code_quality": "stable",
        },
    }


@app.get("/api/quality/alerts")
async def get_quality_alerts(limit: int = 10):
    """获取质量告警信息"""
    # TODO: 实现告警系统
    alerts = []

    # 基于当前数据生成告警
    if latest_quality_data:
        overall_score = latest_quality_data.get("overall_score", 0)
        if overall_score < 8.0:
            alerts.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "warning",
                    "message": f"质量分数较低: {overall_score:.2f}",
                    "source": "quality_monitor",
                    "details": {"score": overall_score},
                }
            )

    return {"alerts": alerts[:limit], "total": len(alerts)}


@app.post("/api/quality/trigger-check")
async def trigger_quality_check(background_tasks: BackgroundTasks):
    """手动触发质量检查"""
    background_tasks.add_task(run_quality_check_and_broadcast)

    return {"message": "质量检查已启动", "timestamp": datetime.now().isoformat()}


async def run_quality_check_and_broadcast():
    """运行质量检查并广播结果"""
    try:
        # 运行质量检查
        quality_data = await get_current_quality_metrics()
        latest_quality_data.update(quality_data)

        # 广播结果
        await broadcast_quality_update(quality_data)

        logger.info("手动质量检查完成并广播")

    except Exception as e:
        logger.error(f"手动质量检查失败: {e}")


@app.get("/api/system/status")
async def get_system_status():
    """获取系统状态"""
    return {
        "timestamp": datetime.now().isoformat(),
        "services": {
            "quality_guardian": "running",
            "improvement_monitor": "running",
            "websocket_server": "running",
            "continuous_improvement": "running",
        },
        "connected_clients": len(connected_clients),
        "latest_update": (
            latest_quality_data.get("timestamp") if latest_quality_data else None
        ),
    }


if __name__ == "__main__":
    logger.info("启动质量监控面板API服务...")

    # 设置静态文件
    try:
        setup_static_files()
    except Exception as e:
        logger.warning(f"静态文件设置失败: {e}")

    # 启动服务器
    uvicorn.run(
        "quality_dashboard_api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
