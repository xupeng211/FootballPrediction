#!/usr/bin/env python3
"""
简单测试服务器
Simple Test Server for Performance Testing

Phase G Week 5 Day 2 - 轻量级测试服务器
"""

import asyncio
import json
import time
import random
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="性能测试服务器", version="1.0.0")

# 模拟数据存储
mock_teams = ["Team A", "Team B", "Team C", "Team D", "Team E"]
mock_matches = []
mock_predictions = []

# 生成一些模拟比赛数据
for i in range(10):
    home_team = random.choice(mock_teams)
    away_team = random.choice([t for t in mock_teams if t != home_team])
    mock_matches.append({
        "id": i + 1,
        "home_team": home_team,
        "away_team": away_team,
        "date": f"2024-01-{i+1:02d}",
        "competition": "Test League",
        "status": "upcoming"
    })

class PredictionRequest(BaseModel):
    home_team: str
    away_team: str
    match_date: str
    competition: str

@app.get("/")
async def root():
    """根端点"""
    start_time = time.time()

    # 模拟一些处理时间
    await asyncio.sleep(0.01 + random.random() * 0.05)

    response_time = time.time() - start_time
    return JSONResponse({
        "message": "足球预测系统运行正常",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": round(response_time * 1000, 2)
    })

@app.get("/health")
async def health_check():
    """健康检查端点"""
    start_time = time.time()

    # 模拟健康检查逻辑
    await asyncio.sleep(0.005)

    response_time = time.time() - start_time
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "ok",
            "redis": "ok",
            "services": "ok"
        },
        "response_time_ms": round(response_time * 1000, 2)
    })

@app.get("/api/health")
async def api_health():
    """API健康检查"""
    return await health_check()

@app.get("/api/v1/teams")
async def get_teams():
    """获取球队列表"""
    start_time = time.time()

    # 模拟数据库查询
    await asyncio.sleep(0.02 + random.random() * 0.03)

    response_time = time.time() - start_time
    return JSONResponse({
        "teams": [{"id": i+1, "name": team} for i, team in enumerate(mock_teams)],
        "count": len(mock_teams),
        "response_time_ms": round(response_time * 1000, 2)
    })

@app.get("/api/v1/matches")
async def get_matches():
    """获取比赛列表"""
    start_time = time.time()

    # 模拟数据库查询
    await asyncio.sleep(0.03 + random.random() * 0.05)

    response_time = time.time() - start_time
    return JSONResponse({
        "matches": mock_matches,
        "count": len(mock_matches),
        "response_time_ms": round(response_time * 1000, 2)
    })

@app.post("/api/v1/predictions/simple")
async def create_prediction(request: PredictionRequest):
    """创建简单预测"""
    start_time = time.time()

    # 模拟预测算法处理
    await asyncio.sleep(0.05 + random.random() * 0.1)

    # 生成模拟预测结果
    prediction = {
        "id": len(mock_predictions) + 1,
        "home_team": request.home_team,
        "away_team": request.away_team,
        "match_date": request.match_date,
        "competition": request.competition,
        "prediction": random.choice(["home_win", "draw", "away_win"]),
        "confidence": round(random.uniform(0.6, 0.95), 2),
        "home_win_probability": round(random.uniform(0.2, 0.7), 2),
        "draw_probability": round(random.uniform(0.1, 0.4), 2),
        "away_win_probability": round(random.uniform(0.1, 0.6), 2),
        "created_at": datetime.now().isoformat()
    }

    mock_predictions.append(prediction)
    response_time = time.time() - start_time

    return JSONResponse({
        "prediction": prediction,
        "response_time_ms": round(response_time * 1000, 2),
        "processing_time_ms": round(response_time * 1000, 2)
    })

@app.get("/api/v1/user/profile")
async def get_user_profile():
    """获取用户档案"""
    start_time = time.time()

    # 模拟用户数据查询
    await asyncio.sleep(0.02 + random.random() * 0.03)

    response_time = time.time() - start_time
    return JSONResponse({
        "user_id": random.randint(1000, 9999),
        "username": f"test_user_{random.randint(1, 100)}",
        "email": f"test{random.randint(1, 100)}@example.com",
        "predictions_count": len(mock_predictions),
        "success_rate": round(random.uniform(0.6, 0.85), 2),
        "response_time_ms": round(response_time * 1000, 2)
    })

@app.get("/metrics")
async def get_metrics():
    """获取系统指标"""
    return JSONResponse({
        "system": {
            "cpu_usage": round(random.uniform(20, 80), 1),
            "memory_usage": round(random.uniform(30, 70), 1),
            "active_connections": random.randint(10, 100)
        },
        "api": {
            "total_requests": random.randint(1000, 10000),
            "error_rate": round(random.uniform(0, 2), 2),
            "avg_response_time": round(random.uniform(50, 150), 1)
        },
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    print("🚀 启动性能测试服务器...")
    print("📊 服务器地址: http://localhost:8000")
    print("🔗 健康检查: http://localhost:8000/health")
    print("⚡ 支持的端点:")
    print("   GET  /")
    print("   GET  /health")
    print("   GET  /api/health")
    print("   GET  /api/v1/teams")
    print("   GET  /api/v1/matches")
    print("   POST /api/v1/predictions/simple")
    print("   GET  /api/v1/user/profile")
    print("   GET  /metrics")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )