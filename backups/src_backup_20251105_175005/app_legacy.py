"""
根目录下的简化 FastAPI 应用
Root Directory Simplified FastAPI Application
"""

from fastapi import FastAPI

# 创建简化的FastAPI应用
app = FastAPI(
    title="Football Prediction API",
    description="Advanced football match prediction system",
    version="2.0.0",
)


@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Football Prediction API",
        "version": "2.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,  # TODO: 将魔法数字 8000 提取为常量
        reload=True,
        log_level="info",
    )
