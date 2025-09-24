"""
Phase 4：API集成测试
目标：验证核心API在集成环境下的稳定性
重点：真实依赖交互、端到端测试、性能验证
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 导入应用和模型
from main import app
from src.core.config import get_settings
from src.database.models import League, Match, Prediction, Team


class TestAPIIntegrationBasic:
    """API基础集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    async def mock_database_session(self):
        """模拟数据库会话"""
        # 创建异步数据库引擎用于测试
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False, future=True
        )

        # 创建会话工厂
        async_session_factory = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试会话
        session = async_session_factory()

        yield session

        # 清理
        await session.close()
        await engine.dispose()

    def test_api_health_endpoint(self, client):
        """测试API健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

    def test_api_root_endpoint(self, client):
        """测试API根端点"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data

    def test_api_docs_accessible(self, client):
        """测试API文档可访问"""
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200


class TestDataAPIIntegration:
    """数据API集成测试"""

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "id": 1,
            "home_team_id": 10,
            "away_team_id": 20,
            "league_id": 1,
            "match_time": datetime.now().isoformat(),
            "season": "2024-25",
            "match_status": "scheduled",
        }

    @pytest.fixture
    def sample_team_data(self):
        """示例球队数据"""
        return {
            "id": 10,
            "name": "Test Team A",
            "country": "Test Country",
            "founded": 2020,
        }

    @pytest.mark.asyncio
    async def test_match_features_integration(self, client, sample_match_data):
        """测试比赛特征获取集成"""
        # 模拟数据库查询
        with patch("src.api.data.get_match_features") as mock_get_features:
            mock_get_features.return_value = {
                "match_id": 1,
                "match_info": sample_match_data,
                "features": {
                    "home_team": {"goals_scored": 2.5, "goals_conceded": 1.2},
                    "away_team": {"goals_scored": 1.8, "goals_conceded": 2.1},
                },
                "prediction": None,
                "odds": [],
            }

            response = client.get("/api/data/matches/1/features")
            assert response.status_code == 200

            data = response.json()
            assert "match_id" in data
            assert "match_info" in data
            assert "features" in data
            assert data["match_id"] == 1

    @pytest.mark.asyncio
    async def test_team_stats_integration(self, client, sample_team_data):
        """测试球队统计获取集成"""
        with patch("src.api.data.get_team_stats") as mock_get_stats:
            mock_get_stats.return_value = {
                "team_id": 10,
                "team_name": "Test Team A",
                "total_matches": 10,
                "wins": 6,
                "draws": 2,
                "losses": 2,
                "goals_for": 20,
                "goals_against": 12,
                "clean_sheets": 4,
                "win_rate": 0.6,
            }

            response = client.get("/api/data/teams/10/stats")
            assert response.status_code == 200

            data = response.json()
            assert "team_id" in data
            assert "team_name" in data
            assert "total_matches" in data
            assert data["team_id"] == 10

    @pytest.mark.asyncio
    async def test_dashboard_data_integration(self, client):
        """测试仪表板数据获取集成"""
        with patch("src.api.data.get_dashboard_data") as mock_get_dashboard:
            mock_get_dashboard.return_value = {
                "today_matches": {"count": 3, "matches": []},
                "predictions": {"count": 5, "accuracy": 0.75},
                "data_quality": {"overall_status": "healthy", "quality_score": 85.0},
                "system_health": {"database": "healthy", "redis": "healthy"},
            }

            response = client.get("/api/data/dashboard")
            assert response.status_code == 200

            data = response.json()
            assert "today_matches" in data
            assert "predictions" in data
            assert "data_quality" in data
            assert "system_health" in data


class TestFeaturesAPIIntegration:
    """特征API集成测试"""

    @pytest.mark.asyncio
    async def test_match_features_improved_integration(self, client):
        """测试改进版比赛特征获取集成"""
        with patch(
            "src.api.features_improved.get_match_features_improved"
        ) as mock_get_features:
            mock_get_features.return_value = {
                "success": True,
                "data": {
                    "match_info": {
                        "match_id": 1,
                        "home_team_id": 10,
                        "away_team_id": 20,
                    },
                    "features": {
                        "home_recent_form": [1, 1, 0, 1, 0],
                        "away_recent_form": [0, 1, 0, 0, 1],
                        "home_goals_avg": 2.1,
                        "away_goals_avg": 1.3,
                    },
                },
                "message": "Features retrieved successfully",
            }

            response = client.get("/api/features/improved/matches/1")
            assert response.status_code == 200

            data = response.json()
            assert "success" in data
            assert "data" in data
            assert "message" in data
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_features_health_check_integration(self, client):
        """测试特征服务健康检查集成"""
        with patch(
            "src.api.features_improved.features_health_check"
        ) as mock_health_check:
            mock_health_check.return_value = {
                "status": "healthy",
                "components": {
                    "feature_store": True,
                    "feature_calculator": True,
                    "feature_store_connection": True,
                },
                "timestamp": datetime.now().isoformat(),
            }

            response = client.get("/api/features/health")
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert "components" in data
            assert data["status"] == "healthy"


class TestPredictionAPIIntegration:
    """预测API集成测试"""

    @pytest.mark.asyncio
    async def test_match_prediction_integration(self, client):
        """测试比赛预测获取集成"""
        with patch("src.api.predictions.get_match_prediction") as mock_get_prediction:
            mock_get_prediction.return_value = {
                "success": True,
                "data": {
                    "match_id": 1,
                    "prediction": {
                        "home_win_prob": 0.45,
                        "draw_prob": 0.25,
                        "away_win_prob": 0.30,
                        "confidence": 0.75,
                        "model_version": "xgboost_v2.1",
                    },
                    "features_used": ["home_form", "away_form", "head_to_head"],
                    "prediction_time": datetime.now().isoformat(),
                },
                "message": "Prediction generated successfully",
            }

            response = client.get("/api/predictions/matches/1")
            assert response.status_code == 200

            data = response.json()
            assert "success" in data
            assert "data" in data
            assert "message" in data
            assert data["success"] is True

            prediction_data = data["data"]["prediction"]
            assert "home_win_prob" in prediction_data
            assert "draw_prob" in prediction_data
            assert "away_win_prob" in prediction_data
            assert (
                abs(
                    sum(
                        [
                            prediction_data["home_win_prob"],
                            prediction_data["draw_prob"],
                            prediction_data["away_win_prob"],
                        ]
                    )
                    - 1.0
                )
                < 0.01
            )

    @pytest.mark.asyncio
    async def test_batch_prediction_integration(self, client):
        """测试批量预测集成"""
        match_ids = [1, 2, 3]

        with patch("src.api.predictions.get_batch_predictions") as mock_get_batch:
            mock_get_batch.return_value = {
                "success": True,
                "data": {
                    "predictions": [
                        {
                            "match_id": 1,
                            "prediction": {
                                "home_win_prob": 0.45,
                                "draw_prob": 0.25,
                                "away_win_prob": 0.30,
                            },
                        },
                        {
                            "match_id": 2,
                            "prediction": {
                                "home_win_prob": 0.60,
                                "draw_prob": 0.20,
                                "away_win_prob": 0.20,
                            },
                        },
                        {
                            "match_id": 3,
                            "prediction": {
                                "home_win_prob": 0.35,
                                "draw_prob": 0.30,
                                "away_win_prob": 0.35,
                            },
                        },
                    ],
                    "total_processed": 3,
                    "processing_time": 0.45,
                },
                "message": "Batch prediction completed",
            }

            response = client.post(
                "/api/predictions/batch", json={"match_ids": match_ids}
            )
            assert response.status_code == 200

            data = response.json()
            assert "success" in data
            assert "data" in data
            assert data["success"] is True

            predictions = data["data"]["predictions"]
            assert len(predictions) == 3
            assert all("match_id" in pred for pred in predictions)


class TestAPIIntegrationPerformance:
    """API性能集成测试"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, client):
        """测试并发请求性能"""
        import concurrent.futures
        import threading

        def make_request():
            start_time = time.time()
            try:
                response = client.get("/health")
                return time.time() - start_time, response.status_code
            except Exception as e:
                return time.time() - start_time, str(e)

        # 模拟并发请求
        num_requests = 50
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in futures]

        # 分析结果
        response_times = [result[0] for result in results if isinstance(result[1], int)]
        successful_requests = [
            result
            for result in results
            if isinstance(result[1], int) and result[1] == 200
        ]

        # 断言性能指标
        assert len(successful_requests) >= num_requests * 0.95  # 95%以上请求成功
        assert len(response_times) > 0

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Max response time: {max_response_time:.3f}s")
        print(f"Success rate: {len(successful_requests)/num_requests*100:.1f}%")

        # 性能断言（可以根据实际情况调整）
        assert avg_response_time < 1.0  # 平均响应时间小于1秒
        assert max_response_time < 3.0  # 最大响应时间小于3秒

    @pytest.mark.asyncio
    async def test_api_error_handling_performance(self, client):
        """测试API错误处理性能"""
        start_time = time.time()

        # 测试各种错误场景
        error_scenarios = [
            ("/api/data/matches/99999/features", 404),  # 不存在的比赛
            ("/api/data/teams/99999/stats", 404),  # 不存在的球队
            ("/api/predictions/matches/0", 400),  # 无效的比赛ID
        ]

        for endpoint, expected_status in error_scenarios:
            response = client.get(endpoint)
            assert response.status_code == expected_status

        total_time = time.time() - start_time
        print(
            f"Error handling performance: {total_time:.3f}s for {len(error_scenarios)} requests"
        )

        # 错误处理也应该在合理时间内完成
        assert total_time < 2.0


class TestAPIIntegrationSecurity:
    """API安全集成测试"""

    def test_sql_injection_protection(self, client):
        """测试SQL注入防护"""
        malicious_ids = [
            "1' OR '1'='1",
            "1; DROP TABLE matches; --",
            "1 UNION SELECT username, password FROM users",
            "1' AND SLEEP(10)--",
        ]

        for malicious_id in malicious_ids:
            response = client.get(f"/api/data/matches/{malicious_id}/features")
            # 应该返回400或404，而不是500
            assert response.status_code in [400, 404, 422]

    def test_rate_limiting_simulation(self, client):
        """模拟速率限制测试"""
        # 快速发送多个请求
        responses = []
        for i in range(20):
            response = client.get("/health")
            responses.append(response.status_code)

        # 大部分请求应该成功
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 15  # 至少75%的请求成功

    def test_cors_headers(self, client):
        """测试CORS头部"""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        # 检查CORS头部
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers


@pytest.mark.asyncio
async def test_full_integration_workflow():
    """完整的集成测试工作流"""
    client = TestClient(app)

    # 1. 健康检查
    health_response = client.get("/health")
    assert health_response.status_code == 200

    # 2. 获取比赛特征
    with patch("src.api.data.get_match_features") as mock_features:
        mock_features.return_value = {
            "match_id": 1,
            "match_info": {"id": 1, "home_team_id": 10, "away_team_id": 20},
            "features": {"home_goals_avg": 2.1, "away_goals_avg": 1.3},
            "prediction": None,
            "odds": [],
        }

        features_response = client.get("/api/data/matches/1/features")
        assert features_response.status_code == 200

    # 3. 获取预测
    with patch("src.api.predictions.get_match_prediction") as mock_prediction:
        mock_prediction.return_value = {
            "success": True,
            "data": {
                "match_id": 1,
                "prediction": {
                    "home_win_prob": 0.45,
                    "draw_prob": 0.25,
                    "away_win_prob": 0.30,
                },
            },
            "message": "Success",
        }

        prediction_response = client.get("/api/predictions/matches/1")
        assert prediction_response.status_code == 200

    # 4. 获取仪表板数据
    with patch("src.api.data.get_dashboard_data") as mock_dashboard:
        mock_dashboard.return_value = {
            "today_matches": {"count": 0, "matches": []},
            "predictions": {"count": 0, "accuracy": 0.0},
            "data_quality": {"overall_status": "healthy", "quality_score": 85.0},
            "system_health": {"database": "healthy", "redis": "healthy"},
        }

        dashboard_response = client.get("/api/data/dashboard")
        assert dashboard_response.status_code == 200

    print("✅ Full integration workflow completed successfully")
