import uvicorn
from fastapi import FastAPI

"""
根目录下的简化 FastAPI 应用
Root Directory Simplified FastAPI Application
"""

# 常量定义
DEFAULT_PORT = 8000

# 创建简化的FastAPI应用
app = FastAPI(
    title="Football Prediction API",
    description="Advanced football match prediction system",
    version="2.0.0",
)


@app.get("/")
async def root():
    """根端点."""
    return {
        "message": "Football Prediction API",
        "version": "2.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """健康检查端点."""
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=DEFAULT_PORT,
        reload=True,
        log_level="info",
    )
