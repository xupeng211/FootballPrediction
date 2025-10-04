"""预测API集成测试

使用真实的 FastAPI 路由和内存 SQLite 数据库，验证预测接口在无外部依赖
（Feast/Redis/MLflow）情况下的核心流程。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Dict

import importlib

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import (
    League,
    Match,
    MatchStatus,
    PredictedResult,
    Predictions,
    Team,
)


@pytest_asyncio.fixture(scope="session")
async def test_db() -> AsyncGenerator[AsyncEngine, None]:
    """为集成测试提供内存 SQLite 引擎并初始化模式。"""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # 初始化数据库模式
    from src.database.models import Base  # 延迟导入避免循环

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_db: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """基于测试引擎创建独立的 AsyncSession。"""

    async_session = sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def predictions_app(
    test_db: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[FastAPI, None]:
    """构建仅包含预测路由的 FastAPI 应用并覆盖依赖。"""

    # 禁用队列依赖，确保预测服务以Mock实现运行
    monkeypatch.setenv("ENABLE_FEAST", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")
    monkeypatch.setenv("MINIMAL_API_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "test")

    # 重新加载预测路由依赖以应用最新环境变量
    import src.api.predictions as predictions_module

    predictions_module = importlib.reload(predictions_module)

    app = FastAPI()
    app.include_router(predictions_module.router, prefix="/api/v1")

    async_session_factory = sessionmaker(
        test_db, class_=AsyncSession, expire_on_commit=False
    )

    from src.database.connection import get_async_session

    async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def integration_client(
    predictions_app: FastAPI,
) -> AsyncGenerator[AsyncClient, None]:
    """创建用于集成测试的 AsyncClient。"""

    transport = ASGITransport(app=predictions_app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def cached_prediction(db_session: AsyncSession) -> Dict[str, int]:
    """预置一场比赛及其缓存预测，返回相关ID。"""

    league = League(league_name="Integration League", country="Testland")
    db_session.add(league)
    await db_session.flush()

    home_team = Team(team_name="Integration FC", league_id=league.id)
    away_team = Team(team_name="Example United", league_id=league.id)
    db_session.add_all([home_team, away_team])
    await db_session.flush()

    match = Match(
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        league_id=league.id,
        season="2024-25",
        match_time=datetime.utcnow() + timedelta(days=2),
        match_status=MatchStatus.SCHEDULED,
    )
    db_session.add(match)
    await db_session.flush()

    prediction = Predictions(
        match_id=match.id,
        model_name="baseline_model",
        model_version="1.0",
        predicted_result=PredictedResult.HOME_WIN,
        home_win_probability=Decimal("0.6500"),
        draw_probability=Decimal("0.2000"),
        away_win_probability=Decimal("0.1500"),
        confidence_score=Decimal("0.6500"),
        predicted_home_score=Decimal("2.0"),
        predicted_away_score=Decimal("1.0"),
        predicted_at=datetime.utcnow(),
        features_used={"form_index": 0.72},
        prediction_metadata={"source": "integration"},
    )
    db_session.add(prediction)
    await db_session.commit()

    return {"match_id": match.id, "prediction_id": prediction.id}


@pytest.mark.asyncio
async def test_get_match_prediction_returns_cached(
    integration_client: AsyncClient, cached_prediction: Dict[str, int]
) -> None:
    """验证存在缓存预测时，API返回缓存结果。"""

    match_id = cached_prediction["match_id"]

    response = await integration_client.get(f"/api/v1/predictions/{match_id}")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["match_id"] == match_id
    assert data["source"] == "cached"
    assert data["prediction"]["model_version"] == "1.0"
    assert data["prediction"]["model_name"] == "baseline_model"


@pytest.mark.asyncio
async def test_prediction_history_returns_records(
    integration_client: AsyncClient, cached_prediction: Dict[str, int]
) -> None:
    """验证历史预测接口返回插入的预测记录。"""

    match_id = cached_prediction["match_id"]

    response = await integration_client.get(
        f"/api/v1/predictions/history/{match_id}?limit=5"
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["match_id"] == match_id
    assert data["total_predictions"] == 1
    assert data["predictions"][0]["model_version"] == "1.0"

    # 不存在的比赛返回404
    missing_response = await integration_client.get(
        "/api/v1/predictions/history/999999"
    )
    assert missing_response.status_code == 404
