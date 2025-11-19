from typing import Optional

"""增强版 FastAPI 应用
Enhanced FastAPI Application.

提供基础的应用结构,包含数据库连接和基本的预测功能.
Provides basic application structure with database connection and basic prediction functionality.
"""

import os
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost/football_db"
)

# 全局数据库连接池
db_pool = None


async def init_db_pool():
    """启动时初始化数据库连接."""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
    except Exception:
        raise


async def close_db_pool():
    """关闭时清理连接池."""
    global db_pool
    if db_pool:
        await db_pool.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    # 启动时初始化
    await init_db_pool()
    yield
    # 关闭时清理
    await close_db_pool()


# 创建 FastAPI 应用
app = FastAPI(
    title="足球预测系统 - 增强版",
    description="基于机器学习的足球比赛结果预测系统",
    version="1.0.0",
    lifespan=lifespan,
)


# 数据模型
class PredictionRequest(BaseModel):
    """预测请求模型."""

    match_id: str
    home_team: str
    away_team: str
    confidence: float | None = None

    def __post_init__(self):
        # 验证confidence范围
        if self.confidence is not None and not (0 <= self.confidence <= 1):
            raise HTTPException(status_code=400, detail="confidence必须在0-1之间")


class PredictionResponse(BaseModel):
    """预测响应模型."""

    match_id: str
    prediction: str
    confidence: float
    created_at: str


# 路由端点
@app.get("/")
async def root():
    """根端点."""
    return {"message": "足球预测系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查."""
    return {"status": "healthy", "database": "connected" if db_pool else "disconnected"}


@app.get("/db")
async def get_db_connection():
    """获取数据库连接."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="数据库连接未初始化")

    async with db_pool.acquire() as connection:
        result = await connection.fetchval("SELECT 1")
        return {"db_status": "connected", "test_result": result}


@app.get("/predictions", response_model=list[PredictionResponse])
async def get_predictions():
    """获取所有预测."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="数据库连接未初始化")

    try:
        async with db_pool.acquire():
            # 模拟查询预测数据
            predictions = [
                {
                    "match_id": "match_001",
                    "prediction": "home_win",
                    "confidence": 0.75,
                    "created_at": "2025-11-09T10:00:00Z",
                }
            ]
            return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}") from e


@app.post("/predictions", response_model=PredictionResponse)
async def create_prediction(request: PredictionRequest):
    """创建新预测."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="数据库连接未初始化")

    try:
        async with db_pool.acquire():
            # 模拟保存预测数据
            response = PredictionResponse(
                match_id=request.match_id,
                prediction="home_win",  # 简化逻辑
                confidence=request.confidence or 0.5,
                created_at="2025-11-09T10:00:00Z",
            )
            return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}") from e


if __name__ == "__main__":
    uvicorn.run(
        "src.app_enhanced:app", host="0.0.0.0", port=8001, reload=True, log_level="info"
    )
