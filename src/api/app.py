"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .data_router import router as data_router
from .health import router as health_router
from .predictions import router as predictions_router
from .monitoring import router as monitoring_router

# 创建FastAPI应用实例
app = FastAPI()
    title="Football Prediction API",
    description="足球预测系统API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",


# 添加CORS中间件
app.add_middleware()
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],


# 添加Gzip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册路由
app.include_router(data_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")

# 根路径
@app.get("/")
async def root()
:
    return {"message": "Football Prediction API", "version": "1.0.0"}
