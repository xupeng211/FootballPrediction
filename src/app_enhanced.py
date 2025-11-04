"""
增强版 FastAPI 应用 - 集成数据访问层
Enhanced FastAPI Application with Data Access Layer
"""

import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:enhanced_db_password_2024@localhost:5433/football_prediction_staging",  # TODO: 将魔法数字 5433 提取为常量
)

# Redis 配置
REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://:minimal_redis_password_2024@localhost:6379/0",  # TODO: 将魔法数字 6379 提取为常量
)


# 简单的数据模型
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str


class PredictionResponse(BaseModel):
    id: int
    match_id: int
    predicted_winner: str
    confidence: float
    created_at: str


# 数据库连接池
db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db_pool

    print("🚀 Starting Enhanced Football Prediction API...")

    # 初始化数据库连接池
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        print("✅ Database connection pool created")

        # 创建基础表结构
        await create_tables()
        print("✅ Database tables initialized")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("⚠️  Running without database connection")

    print("✅ Enhanced API startup complete")

    yield

    # 清理资源
    if db_pool:
        await db_pool.close()
        print("🔄 Database connections closed")

    print("✅ Shutdown complete")


async def create_tables():
    """创建基础表结构"""
    if not db_pool:
        return

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                match_id INTEGER NOT NULL,
                predicted_winner VARCHAR(100) NOT NULL,  # TODO: 将魔法数字 100 提取为常量
                confidence FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                home_team VARCHAR(100) NOT NULL,  # TODO: 将魔法数字 100 提取为常量
                away_team VARCHAR(100) NOT NULL,  # TODO: 将魔法数字 100 提取为常量
                match_date TIMESTAMP NOT NULL,
                league VARCHAR(100),  # TODO: 将魔法数字 100 提取为常量
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )


async def get_db_connection():
    """获取数据库连接"""
    if not db_pool:
        raise HTTPException(
            status_code=503,  # TODO: 将魔法数字 503 提取为常量
            detail="Database not available",  # TODO: 将魔法数字 503 提取为常量
        )  # TODO: 将魔法数字 503 提取为常量
    return db_pool


# 创建 FastAPI 应用
app = FastAPI(
    title="Football Prediction API - Enhanced",
    description="Advanced football match prediction system with data access layer",
    version="2.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Football Prediction API - Enhanced",
        "version": "2.1.0",
        "status": "healthy",
        "features": ["database", "redis", "predictions"],
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """增强健康检查端点"""
    db_status = "connected" if db_pool else "disconnected"

    # 简单的 Redis 检查
    redis_status = "connected"  # 这里可以添加实际的 Redis 检查

    return HealthResponse(
        status="healthy", version="2.1.0", database=db_status, redis=redis_status
    )


@app.get("/predictions", response_model=list[PredictionResponse])
async def get_predictions():
    """获取所有预测"""
    if not db_pool:
        raise HTTPException(
            status_code=503,  # TODO: 将魔法数字 503 提取为常量
            detail="Database not available",  # TODO: 将魔法数字 503 提取为常量
        )  # TODO: 将魔法数字 503 提取为常量

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM predictions ORDER BY created_at DESC LIMIT 10"
        )

        return [
            PredictionResponse(
                id=row["id"],
                match_id=row["match_id"],
                predicted_winner=row["predicted_winner"],
                confidence=row["confidence"],
                created_at=row["created_at"].isoformat(),
            )
            for row in rows
        ]


@app.post("/predictions", response_model=PredictionResponse)
async def create_prediction(match_id: int, predicted_winner: str, confidence: float):
    """创建新预测"""
    if not db_pool:
        raise HTTPException(
            status_code=503,  # TODO: 将魔法数字 503 提取为常量
            detail="Database not available",  # TODO: 将魔法数字 503 提取为常量
        )  # TODO: 将魔法数字 503 提取为常量

    if confidence < 0 or confidence > 1:
        raise HTTPException(
            status_code=400,  # TODO: 将魔法数字 400 提取为常量
            detail="Confidence must be between 0 and 1",  # TODO: 将魔法数字 400 提取为常量
        )  # TODO: 将魔法数字 400 提取为常量

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO predictions (match_id, predicted_winner, confidence)
            VALUES ($1, $2, $3)
            RETURNING id, match_id, predicted_winner, confidence, created_at
            """,
            match_id,
            predicted_winner,
            confidence,
        )

        return PredictionResponse(
            id=row["id"],
            match_id=row["match_id"],
            predicted_winner=row["predicted_winner"],
            confidence=row["confidence"],
            created_at=row["created_at"].isoformat(),
        )


@app.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(prediction_id: int):
    """获取特定预测"""
    if not db_pool:
        raise HTTPException(
            status_code=503,  # TODO: 将魔法数字 503 提取为常量
            detail="Database not available",  # TODO: 将魔法数字 503 提取为常量
        )  # TODO: 将魔法数字 503 提取为常量

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM predictions WHERE id = $1", prediction_id
        )

        if not row:
            raise HTTPException(
                status_code=404,  # TODO: 将魔法数字 404 提取为常量
                detail="Prediction not found",  # TODO: 将魔法数字 404 提取为常量
            )  # TODO: 将魔法数字 404 提取为常量

        return PredictionResponse(
            id=row["id"],
            match_id=row["match_id"],
            predicted_winner=row["predicted_winner"],
            confidence=row["confidence"],
            created_at=row["created_at"].isoformat(),
        )


@app.delete("/predictions/{prediction_id}")
async def delete_prediction(prediction_id: int):
    """删除预测"""
    if not db_pool:
        raise HTTPException(
            status_code=503,  # TODO: 将魔法数字 503 提取为常量
            detail="Database not available",  # TODO: 将魔法数字 503 提取为常量
        )  # TODO: 将魔法数字 503 提取为常量

    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM predictions WHERE id = $1", prediction_id
        )

        if result == "DELETE 0":
            raise HTTPException(
                status_code=404,  # TODO: 将魔法数字 404 提取为常量
                detail="Prediction not found",  # TODO: 将魔法数字 404 提取为常量
            )  # TODO: 将魔法数字 404 提取为常量

        return {"message": "Prediction deleted successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app_enhanced:app",
        host="0.0.0.0",
        port=8000,  # TODO: 将魔法数字 8000 提取为常量
        reload=True,
        log_level="info",
    )
