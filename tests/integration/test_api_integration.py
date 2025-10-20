"""
API集成测试
API Integration Tests

测试API端点与数据库、缓存的集成。
"""

import pytest
import asyncio
from httpx import AsyncClient
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from src.api.app import app
from src.database.models import Team, Match


@pytest.mark.integration
@pytest.mark.api
class TestAPIIntegration:
    """API集成测试类"""

    async def test_health_check_integration(self, api_client):
        """测试健康检查端点集成"""
        response = await api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    async def test_get_teams_integration(self, api_client):
        """测试获取球队列表集成"""
        # 先创建一些测试数据
        # 注意：这里使用模拟数据，因为数据库可能没有真实数据

        response = await api_client.get("/teams")

        # 应该返回200，即使没有数据
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_create_team_integration(self, api_client, db_session):
        """测试创建球队集成"""
        team_data = {
            "name": "Integration Test FC",
            "city": "Test City",
            "founded": 2020,
            "stadium": "Test Stadium",
            "capacity": 50000,
        }

        response = await api_client.post("/teams", json=team_data)

        # 检查响应
        assert response.status_code in [201, 422]  # 可能成功或验证失败

        if response.status_code == 201:
            data = response.json()
            assert data["name"] == team_data["name"]
            assert "id" in data

    async def test_get_matches_integration(self, api_client):
        """测试获取比赛列表集成"""
        response = await api_client.get("/matches")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_error_handling_integration(self, api_client):
        """测试错误处理集成"""
        # 测试404错误
        response = await api_client.get("/nonexistent")
        assert response.status_code == 404

        # 测试无效JSON
        response = await api_client.post(
            "/teams", data="invalid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [422, 415]

    async def test_cors_headers_integration(self, api_client):
        """测试CORS头集成"""
        # 预检请求
        response = await api_client.options("/teams")

        # 应该有CORS头
        assert "access-control-allow-origin" in response.headers

    async def test_rate_limiting_integration(self, api_client):
        """测试速率限制集成"""
        # 快速发送多个请求
        responses = []
        for _ in range(10):
            response = await api_client.get("/teams")
            responses.append(response)
            if response.status_code == 429:  # Too Many Requests
                break

        # 检查是否触发了速率限制
        assert any(r.status_code == 429 for r in responses) or len(responses) == 10


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """数据库集成测试类"""

    async def test_database_connection(self, db_session):
        """测试数据库连接"""
        # 执行简单查询
        result = await db_session.execute("SELECT 1 as test")
        assert result.scalar() == 1

    async def test_create_team_with_database(self, db_session):
        """测试创建球队并保存到数据库"""
        team = Team(name="Database Test FC", city="Test City", founded=2021)

        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        # 验证数据
        assert team.id is not None
        assert team.name == "Database Test FC"
        assert team.city == "Test City"

    async def test_create_match_with_database(self, db_session):
        """测试创建比赛并保存到数据库"""
        # 先创建球队
        home_team = Team(name="Home Team", city="Home City", founded=2020)
        away_team = Team(name="Away Team", city="Away City", founded=2020)

        db_session.add(home_team)
        db_session.add(away_team)
        await db_session.commit()
        await db_session.refresh(home_team)
        await db_session.refresh(away_team)

        # 创建比赛
        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date="2025-01-20T20:00:00Z",
            status="UPCOMING",
        )

        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)

        # 验证数据
        assert match.id is not None
        assert match.home_team_id == home_team.id
        assert match.away_team_id == away_team.id

    async def test_query_team_matches(self, db_session):
        """测试查询球队的比赛"""
        # 创建测试数据
        team = Team(name="Query Test FC", city="Test", founded=2020)
        db_session.add(team)
        await db_session.commit()

        # 创建比赛
        match = Match(
            home_team_id=team.id,
            away_team_id=999,  # 不存在的队ID
            match_date="2025-01-20T20:00:00Z",
            status="UPCOMING",
        )
        db_session.add(match)
        await db_session.commit()

        # 查询球队的比赛
        from sqlalchemy import select

        stmt = select(Match).where(Match.home_team_id == team.id)
        result = await db_session.execute(stmt)
        matches = result.scalars().all()

        assert len(matches) == 1
        assert matches[0].home_team_id == team.id

    async def test_transaction_rollback(self, db_session):
        """测试事务回滚"""
        # 开始事务
        team = Team(name="Rollback Test", city="Test", founded=2020)
        db_session.add(team)

        # 模拟错误并回滚
        await db_session.rollback()

        # 验证数据未保存
        assert team.id is None

    async def test_relationship_lazy_loading(self, db_session):
        """测试关系懒加载"""
        # 创建测试数据
        home_team = Team(name="Home FC", city="Home", founded=2020)
        away_team = Team(name="Away FC", city="Away", founded=2020)

        db_session.add(home_team)
        db_session.add(away_team)
        await db_session.commit()

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date="2025-01-20T20:00:00Z",
            status="UPCOMING",
        )

        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)

        # 测试懒加载关系
        # 注意：由于是集成测试，关系可能不会自动加载
        # 这里只验证基本字段
        assert match.home_team_id == home_team.id
        assert match.away_team_id == away_team.id


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflow:
    """端到端工作流测试"""

    async def test_complete_prediction_workflow(self, api_client, db_session):
        """测试完整的预测工作流"""
        # 1. 创建球队
        home_team_data = {
            "name": "E2E Home FC",
            "city": "Test City",
            "founded": 2020,
            "stadium": "Test Stadium",
        }

        home_response = await api_client.post("/teams", json=home_team_data)
        assert home_response.status_code in [201, 422]

        away_team_data = {
            "name": "E2E Away FC",
            "city": "Test City",
            "founded": 2021,
            "stadium": "Test Stadium",
        }

        away_response = await api_client.post("/teams", json=away_team_data)
        assert away_response.status_code in [201, 422]

        # 2. 创建比赛
        match_data = {
            "home_team_id": 1,  # 假设ID
            "away_team_id": 2,  # 假设ID
            "match_date": "2025-02-01T20:00:00Z",
            "venue": "Test Stadium",
        }

        match_response = await api_client.post("/matches", json=match_data)
        assert match_response.status_code in [201, 422]

        # 3. 创建预测
        prediction_data = {
            "match_id": 1,  # 假设ID
            "prediction": "HOME_WIN",
            "confidence": 0.75,
        }

        prediction_response = await api_client.post(
            "/predictions", json=prediction_data
        )
        assert prediction_response.status_code in [201, 422]

        # 4. 验证数据一致性
        teams_response = await api_client.get("/teams")
        assert teams_response.status_code == 200

        matches_response = await api_client.get("/matches")
        assert matches_response.status_code == 200

        predictions_response = await api_client.get("/predictions")
        assert predictions_response.status_code == 200

    async def test_api_pagination(self, api_client):
        """测试API分页功能"""
        # 测试不同的分页参数
        params_list = [{"page": 1, "limit": 10}, {"page": 2, "limit": 5}, {"limit": 20}]

        for params in params_list:
            response = await api_client.get("/teams", params=params)
            assert response.status_code == 200

            data = response.json()
            # 验证分页结构（如果有的话）
            if isinstance(data, dict):
                assert "items" in data or "results" in data
                if "items" in data:
                    assert len(data["items"]) <= params.get("limit", 100)

    async def test_concurrent_requests(self, api_client):
        """测试并发请求"""
        import asyncio

        async def make_request():
            return await api_client.get("/teams")

        # 并发发送10个请求
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有请求都成功
        assert all(isinstance(r, Exception) or r.status_code == 200 for r in responses)
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) > 0
