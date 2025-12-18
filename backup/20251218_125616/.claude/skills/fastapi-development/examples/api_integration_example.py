"""
FastAPI系统集成示例
将 fastapi-development Skill 应用于现有的足球预测系统
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import time
import uuid
from typing import Optional
import logging

# 导入现有系统组件
try:
    from src.api.schemas import PredictionRequest, PredictionResponse
    from src.services.inference_service_v2 import InferenceServiceV2
    from src.database.connection import get_connection
except ImportError:
    print("⚠️  无法导入现有系统组件，使用模拟组件")
    # 创建模拟组件用于演示
    class MockService:
        async def predict_match(self, home: str, away: str):
            await asyncio.sleep(0.05)  # 模拟推理时间
            return {"prediction": "HOME", "confidence": 0.75, "probabilities": {"HOME": 0.65, "DRAW": 0.22, "AWAY": 0.13}}

    class PredictionRequest:
        def __init__(self, home_team: str, away_team: str):
            self.home_team = home_team
            self.away_team = away_team

    InferenceServiceV2 = MockService

# 导入我们的性能优化组件
from ..scripts.api_performance_optimizer import (
    APIPerformanceOptimizer, APICacheManager, PerformanceMetrics
)
from ..templates.performance_middleware import MiddlewareConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedFootballAPI:
    """增强的足球预测API"""

    def __init__(self):
        self.app = FastAPI(
            title="Enhanced Football Prediction API",
            description="高性能足球赛果预测API v2.0",
            version="2.0.0"
        )

        # 初始化性能优化器
        self.optimizer = APIPerformanceOptimizer()
        self.cache_manager = APICacheManager()
        self.inference_service = InferenceServiceV2()

        # 设置应用
        self._setup_middleware()
        self._setup_routes()
        self._setup_exception_handlers()

    async def initialize(self):
        """初始化API服务"""
        await self.optimizer.initialize()
        await self.optimizer.start_background_tasks()
        print("🚀 增强足球预测API初始化完成")

    def _setup_middleware(self):
        """设置中间件"""
        # 1. CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境中应该限制具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 2. 性能监控中间件
        MiddlewareConfig.setup_middleware(self.app)

        # 3. 自定义性能中间件
        @self.app.middleware("http")
        async def add_process_time_header(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time

            # 记录性能指标
            self.optimizer.record_request(PerformanceMetrics(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration=process_time,
                timestamp=time.time(),
                request_id=getattr(request.state, 'request_id', str(uuid.uuid4()))
            ))

            # 添加性能头
            response.headers["X-Process-Time"] = str(process_time)
            if process_time > 0.1:  # 如果响应时间超过100ms
                response.headers["X-Performance-Warning"] = "slow-response"

            return response

    def _setup_routes(self):
        """设置路由"""

        @self.app.get("/health", tags=["Health"])
        async def health_check():
            """健康检查端点 - 增强版"""
            health = await self.optimizer.health_check()
            return health

        @self.app.get("/metrics", tags=["Monitoring"])
        async def get_metrics():
            """获取性能指标"""
            performance_summary = self.optimizer.get_performance_summary()
            cache_stats = self.cache_manager.get_cache_stats()

            return {
                "performance": performance_summary,
                "cache": cache_stats,
                "timestamp": time.time()
            }

        @self.app.post("/api/predict", response_model=dict, tags=["Prediction"])
        async def predict_match(
            request: dict,
            background_tasks: BackgroundTasks
        ):
            """预测端点 - 高性能版本"""
            start_time = time.time()

            try:
                # 生成请求ID
                request_id = str(uuid.uuid4())

                # 提取参数
                home_team = request.get('home_team')
                away_team = request.get('away_team')

                if not home_team or not away_team:
                    raise HTTPException(
                        status_code=400,
                        detail="home_team and away_team are required"
                    )

                # 生成缓存键
                cache_key = f"predict:{home_team}:{away_team}"

                # 尝试从缓存获取
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result:
                    cached_result['cached'] = True
                    cached_result['request_id'] = request_id
                    cached_result['cache_hit'] = True

                    # 后台任务：记录缓存命中
                    background_tasks.add_task(
                        self._log_prediction, request_id, home_team, away_team, "cache_hit"
                    )

                    duration = time.time() - start_time
                    logger.info(f"缓存命中预测: {home_team} vs {away_team} - {duration:.3f}s")
                    return cached_result

                # 执行预测（使用优化后的服务）
                prediction_result = await self._run_prediction_with_optimization(
                    home_team, away_team
                )

                # 构建响应
                response = {
                    "request_id": request_id,
                    "match": {
                        "home_team": home_team,
                        "away_team": away_team
                    },
                    "prediction": prediction_result.get("prediction"),
                    "confidence": prediction_result.get("confidence"),
                    "probabilities": prediction_result.get("probabilities", {}),
                    "cached": False,
                    "cache_hit": False,
                    "processing_time": time.time() - start_time,
                    "timestamp": time.time()
                }

                # 缓存结果（30分钟）
                await self.cache_manager.set(cache_key, response, expire=1800)

                # 后台任务：记录预测日志
                background_tasks.add_task(
                    self._log_prediction, request_id, home_team, away_team, "new_prediction"
                )

                return response

            except Exception as e:
                logger.error(f"预测错误: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Prediction failed")

        @self.app.post("/api/predict/batch", tags=["Prediction"])
        async def batch_predict(request: dict, background_tasks: BackgroundTasks):
            """批量预测端点 - 优化版本"""
            matches = request.get('matches', [])
            if not matches:
                raise HTTPException(status_code=400, detail="No matches provided")

            batch_id = str(uuid.uuid4())
            start_time = time.time()

            try:
                # 使用优化器的批量处理
                results = await self.optimizer.batch_optimize(matches, batch_size=20)

                response = {
                    "batch_id": batch_id,
                    "total_matches": len(matches),
                    "successful_predictions": len(results),
                    "processing_time": time.time() - start_time,
                    "predictions": results,
                    "timestamp": time.time()
                }

                # 后台任务：记录批量预测日志
                background_tasks.add_task(
                    self._log_batch_prediction, batch_id, len(matches), len(results)
                )

                return response

            except Exception as e:
                logger.error(f"批量预测错误: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Batch prediction failed")

        @self.app.get("/api/cache/stats", tags=["Cache"])
        async def get_cache_stats():
            """获取缓存统计"""
            return self.cache_manager.get_cache_stats()

        @self.app.post("/api/cache/clear", tags=["Cache"])
        async def clear_cache():
            """清理缓存"""
            self.cache_manager.clear_local_cache()
            return {"message": "Local cache cleared", "timestamp": time.time()}

        @self.app.get("/api/performance/summary", tags=["Monitoring"])
        async def get_performance_summary():
            """获取性能摘要"""
            return self.optimizer.get_performance_summary()

        # 原有端点的增强版本
        @self.app.get("/api/monitoring", tags=["Monitoring"])
        async def enhanced_monitoring():
            """增强的监控端点"""
            performance = self.optimizer.get_performance_summary()
            cache = self.cache_manager.get_cache_stats()
            health = await self.optimizer.health_check()

            return {
                "status": "operational",
                "performance": performance,
                "cache": cache,
                "health": health,
                "version": "2.0.0-enhanced",
                "timestamp": time.time()
            }

    def _setup_exception_handlers(self):
        """设置异常处理器"""

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            request_id = getattr(request.state, 'request_id', 'unknown')
            logger.error(
                f"HTTP {exc.status_code}: {exc.detail}",
                extra={"request_id": request_id, "path": str(request.url.path)}
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            request_id = getattr(request.state, 'request_id', 'unknown')
            logger.error(
                f"未处理异常: {str(exc)}",
                exc_info=True,
                extra={"request_id": request_id}
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )

    async def _run_prediction_with_optimization(self, home_team: str, away_team: str):
        """运行优化的预测"""
        # 使用推理服务
        if hasattr(self.inference_service, 'predict_match'):
            result = await self.inference_service.predict_match(home_team, away_team)
        else:
            # 模拟预测逻辑
            await asyncio.sleep(0.05)  # 模拟推理时间
            result = {
                "prediction": "HOME",
                "confidence": 0.75,
                "probabilities": {"HOME": 0.65, "DRAW": 0.22, "AWAY": 0.13}
            }

        return result

    async def _log_prediction(self, request_id: str, home_team: str, away_team: str, result_type: str):
        """记录预测日志（后台任务）"""
        # 这里可以实现日志记录到数据库或文件
        logger.info(f"预测记录: {request_id} - {home_team} vs {away_team} - {result_type}")

    async def _log_batch_prediction(self, batch_id: str, total: int, successful: int):
        """记录批量预测日志（后台任务）"""
        logger.info(f"批量预测记录: {batch_id} - {successful}/{total} 成功")


# 创建应用实例
enhanced_api = EnhancedFootballAPI()
app = enhanced_api.app


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("🏈 启动增强足球预测API...")
    await enhanced_api.initialize()
    print("✅ API服务已就绪")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("🛑 关闭增强足球预测API...")


# 健康检查端点（用于Kubernetes等）
@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "Enhanced Football Prediction API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "predict": "/api/predict",
            "batch_predict": "/api/predict/batch",
            "metrics": "/metrics",
            "monitoring": "/api/monitoring",
            "docs": "/docs"
        }
    }


def create_app():
    """应用工厂函数"""
    return app


if __name__ == "__main__":
    import uvicorn

    # 运行开发服务器
    uvicorn.run(
        "api_integration_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )