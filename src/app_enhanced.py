"""
增强版 FastAPI 应用 - 集成数据访问层
Enhanced FastAPI Application with Data Access Layer
"""

import os
from contextlib import asynccontextmanager
from typing import List

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:enhanced_db_password_2024@localhost:5433/football_prediction_staging",
)

# 全局数据库连接池
db_pool = None


class PredictionResponse(BaseModel):
    """预测响应模型"""
    id: int
    match_id: int
    home_team: str
    away_team: str
    prediction: str
    confidence: float
    created_at: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库连接
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        print("✅ 数据库连接池初始化成功")
        yield
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        yield
    finally:
        # 关闭时清理连接池
        if db_pool:
            await db_pool.close()
            print("✅ 数据库连接池已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Football Prediction API - Enhanced",
    description="增强版足球预测API，集成数据访问层",
    version="2.0.0",
    lifespan=lifespan,
)


async def get_db_connection():
    """获取数据库连接"""
    if not db_pool:
        raise HTTPException(
            status_code=503,
            detail="Database not available",
        )
    return db_pool


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "database": "connected" if db_pool else "disconnected"}


@app.get("/predictions", response_model=List[PredictionResponse])
async def get_predictions():
    """获取所有预测"""
    pool = await get_db_connection()

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, match_id, home_team, away_team, prediction, confidence, created_at
                FROM predictions
                ORDER BY created_at DESC
                LIMIT 10
                """
            )

            return [
                PredictionResponse(
                    id=row["id"],
                    match_id=row["match_id"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    prediction=row["prediction"],
                    confidence=row["confidence"],
                    created_at=str(row["created_at"])
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch predictions: {str(e)}"
        )


@app.post("/predictions", response_model=PredictionResponse)
async def create_prediction(
    match_id: int,
    home_team: str,
    away_team: str,
    prediction: str,
    confidence: float
):
    """创建新预测"""
    # 验证confidence范围
    if confidence < 0 or confidence > 1:
        raise HTTPException(
            status_code=400,
            detail="Confidence must be between 0 and 1"
        )

    pool = await get_db_connection()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO predictions (match_id, home_team, away_team, prediction, confidence)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, match_id, home_team, away_team, prediction, confidence, created_at
                """,
                match_id, home_team, away_team, prediction, confidence
            )

            return PredictionResponse(
                id=row["id"],
                match_id=row["match_id"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                prediction=row["prediction"],
                confidence=row["confidence"],
                created_at=str(row["created_at"])
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create prediction: {str(e)}"
        )


@app.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(prediction_id: int):
    """获取单个预测"""
    pool = await get_db_connection()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, match_id, home_team, away_team, prediction, confidence, created_at
                FROM predictions
                WHERE id = $1
                """,
                prediction_id
            )

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Prediction not found"
                )

            return PredictionResponse(
                id=row["id"],
                match_id=row["match_id"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                prediction=row["prediction"],
                confidence=row["confidence"],
                created_at=str(row["created_at"])
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch prediction: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)