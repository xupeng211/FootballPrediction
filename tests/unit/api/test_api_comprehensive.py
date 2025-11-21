#!/usr/bin/env python3
"""
综合API接口测试
Comprehensive API Endpoint Testing

测试 src/api/ 目录下的核心端点，包括：
- 数据管理API端点测试
- 预测API端点测试
- 健康检查API测试
- CORS和错误处理测试

创建时间: 2025-11-22
基于: QA架构师API测试覆盖率提升建议
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入测试目标
try:
    from src.main import app
    from src.api.data_management import router as data_router
    from src.api.predictions.router import router as predictions_router
    from src.api.health import router as health_router
    from src.database.connection import get_async_session
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import API modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture
def mock_async_session():
    """模拟数据库会话"""
    session = Mock(spec=AsyncSession)
    return session


@pytest.fixture
def test_client(mock_async_session):
    """创建测试客户端，使用Mock数据库会话"""
    # 使用依赖注入覆盖，避免真实数据库连接
    app.dependency_overrides[get_async_session] = lambda: mock_async_session
    client = TestClient(app)
    yield client
    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "id": "pred_12345",
        "match_id": 1001,
        "home_team_id": 1,
        "away_team_id": 2,
        "home_score": 2,
        "away_score": 1,
        "confidence": 0.85,
        "ev": 0.15,
        "kelly_fraction": 0.05,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


@pytest.fixture
def sample_matches_data():
    """示例比赛数据"""
    return {
        "matches": [
            {
                "id": 1001,
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_name": "Team A",
                "away_team_name": "Team B",
                "match_date": datetime.now().isoformat(),
                "status": "SCHEDULED"
            },
            {
                "id": 1002,
                "home_team_id": 3,
                "away_team_id": 4,
                "home_team_name": "Team C",
                "away_team_name": "Team D",
                "match_date": datetime.now().isoformat(),
                "status": "FINISHED"
            }
        ],
        "total": 2,
        "limit": 20,
        "offset": 0
    }


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="API modules not available")
class TestAPIComprehensive:
    """综合API测试类"""

    @pytest.mark.unit
    def test_cors_headers_present(self, test_client):
        """测试CORS头是否正确设置"""
        # 发送OPTIONS请求检查CORS
        response = test_client.options("/api/v1/matches")

        # 验证CORS相关头部
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]

        for header in cors_headers:
            # 检查头部存在（不区分大小写）
            assert any(h.lower() == header.lower() for h in response.headers.keys())

    @pytest.mark.unit
    def test_api_v1_matches_get_success(self, test_client, mock_async_session, sample_matches_data):
        """测试GET /api/v1/matches 成功场景"""
        # Mock数据库查询返回
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            Mock(id=1001, home_team_id=1, away_team_id=2,
                 home_team_name="Team A", away_team_name="Team B",
                 match_date=datetime.now(), status="SCHEDULED"),
            Mock(id=1002, home_team_id=3, away_team_id=4,
                 home_team_name="Team C", away_team_name="Team D",
                 match_date=datetime.now(), status="FINISHED")
        ]
        mock_result.scalars.return_value.__len__ = Mock(return_value=2)
        mock_async_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/matches")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["matches"]) == 2
        assert data["total"] >= 2

    @pytest.mark.unit
    def test_api_v1_matches_pagination(self, test_client, mock_async_session):
        """测试分页参数"""
        # Mock数据库查询
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.__len__ = Mock(return_value=0)
        mock_async_session.execute.return_value = mock_result

        # 测试limit和offset参数
        response = test_client.get("/api/v1/matches?limit=10&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20

    @pytest.mark.unit
    def test_api_v1_matches_empty_data(self, test_client, mock_async_session):
        """测试空数据返回"""
        # Mock空数据返回
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.__len__ = Mock(return_value=0)
        mock_async_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/matches")

        assert response.status_code == 200
        data = response.json()
        assert data["matches"] == []
        assert data["total"] == 0

    @pytest.mark.unit
    def test_api_v1_matches_database_failure(self, test_client, mock_async_session):
        """测试数据库连接失败"""
        # Mock数据库异常
        mock_async_session.execute.side_effect = Exception("Database connection failed")

        response = test_client.get("/api/v1/matches")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]

    @pytest.mark.unit
    def test_api_v1_matches_invalid_pagination(self, test_client):
        """测试无效分页参数"""
        # 测试超出范围的limit
        response = test_client.get("/api/v1/matches?limit=101")
        assert response.status_code == 422  # Validation Error

        # 测试负数offset
        response = test_client.get("/api/v1/matches?offset=-1")
        assert response.status_code == 422

    @pytest.mark.unit
    def test_api_v1_predictions_by_id_success(self, test_client, mock_async_session, sample_prediction_data):
        """测试GET /api/v1/predictions/{id} 成功场景"""
        # Mock数据库查询返回预测数据
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Mock(**sample_prediction_data)
        mock_async_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/predictions/pred_12345")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "pred_12345"
        assert data["match_id"] == 1001
        assert data["confidence"] == 0.85
        assert "ev" in data

    @pytest.mark.unit
    def test_api_v1_predictions_by_id_not_found(self, test_client, mock_async_session):
        """测试预测ID不存在"""
        # Mock返回None（未找到）
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/predictions/nonexistent_id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_api_v1_predictions_by_id_service_degradation(self, test_client, mock_async_session):
        """测试服务降级模式"""
        # Mock数据库异常，触发服务降级
        mock_async_session.execute.side_effect = Exception("Service temporarily unavailable")

        response = test_client.get("/api/v1/predictions/pred_12345")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]

    @pytest.mark.unit
    def test_api_v1_predictions_by_id_invalid_id(self, test_client):
        """测试无效的预测ID格式"""
        # 测试空ID
        response = test_client.get("/api/v1/predictions/")
        assert response.status_code == 404  # Not Found

        # 测试空字符串ID
        response = test_client.get("/api/v1/predictions/ ")
        assert response.status_code == 422  # Validation Error

    @pytest.mark.unit
    def test_api_health_inference_success(self, test_client):
        """测试健康检查推理服务"""
        response = test_client.get("/api/v1/health/inference")

        assert response.status_code == 200
        data = response.json()

        # 验证必需字段
        required_fields = ["status", "model_loaded", "model_version", "feature_count"]
        for field in required_fields:
            assert field in data

        # 验证字段类型
        assert isinstance(data["status"], str)
        assert isinstance(data["model_loaded"], bool)
        assert isinstance(data["feature_count"], int)

    @pytest.mark.unit
    def test_api_health_inference_detailed(self, test_client):
        """测试健康检查详细信息"""
        response = test_client.get("/api/v1/health/inference?detailed=true")

        assert response.status_code == 200
        data = response.json()

        # 详细模式应该包含更多信息
        if "model_metadata" in data:
            assert isinstance(data["model_metadata"], dict)

    @pytest.mark.unit
    def test_api_v1_root_endpoint(self, test_client):
        """测试API根端点"""
        response = test_client.get("/api/v1/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "title" in data  # 根据实际实现调整

    @pytest.mark.unit
    def test_api_error_handling_404(self, test_client):
        """测试404错误处理"""
        response = test_client.get("/api/v1/nonexistent_endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_api_error_handling_method_not_allowed(self, test_client):
        """测试方法不允许错误"""
        response = test_client.delete("/api/v1/matches")

        assert response.status_code == 405  # Method Not Allowed

    @pytest.mark.unit
    def test_api_content_type_json(self, test_client):
        """测试JSON内容类型"""
        response = test_client.get("/api/v1/matches", headers={"Accept": "application/json"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.unit
    def test_api_response_time_performance(self, test_client, mock_async_session):
        """测试API响应时间性能"""
        # Mock快速返回
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.__len__ = Mock(return_value=0)
        mock_async_session.execute.return_value = mock_result

        import time
        start_time = time.time()

        response = test_client.get("/api/v1/matches")

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        # API响应时间应该小于1秒（包括Mock开销）
        assert response_time < 1.0

    @pytest.mark.unit
    def test_api_request_id_header(self, test_client):
        """测试请求ID头部"""
        response = test_client.get("/api/v1/health/inference")

        assert response.status_code == 200
        # 检查是否有请求追踪相关的头部（根据实际实现调整）
        if "x-request-id" in response.headers:
            assert response.headers["x-request-id"]

    @pytest.mark.unit
    def test_api_validation_error_format(self, test_client):
        """测试验证错误格式"""
        response = test_client.get("/api/v1/matches?limit=invalid")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        # FastAPI的验证错误通常包含具体字段信息
        if isinstance(data["detail"], list):
            # FastAPI详细错误格式
            assert len(data["detail"]) > 0
        elif isinstance(data["detail"], dict):
            # 自定义错误格式
            pass

    @pytest.mark.unit
    def test_api_concurrent_requests(self, test_client, mock_async_session):
        """测试并发请求处理"""
        import concurrent.futures
        import threading

        # Mock数据库返回
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.__len__ = Mock(return_value=0)
        mock_async_session.execute.return_value = mock_result

        def make_request():
            return test_client.get("/api/v1/matches")

        # 并发发送5个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "matches" in data

    @pytest.mark.unit
    def test_api_large_response_handling(self, test_client, mock_async_session):
        """测试大响应处理"""
        # Mock返回大量数据
        large_data_list = [
            Mock(id=i, home_team_id=i%10+1, away_team_id=(i+1)%10+1,
                 home_team_name=f"Team {i%10+1}", away_team_name=f"Team {(i+1)%10+1}",
                 match_date=datetime.now(), status="SCHEDULED")
            for i in range(100)  # 模拟100条记录
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = large_data_list
        mock_result.scalars.return_value.__len__ = Mock(return_value=100)
        mock_async_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/matches?limit=100")

        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) == 100
        assert data["total"] >= 100


if __name__ == "__main__":
    # 简单的测试运行验证
    print("Running comprehensive API tests...")
    print("This test suite validates API endpoints, error handling, and performance.")
    print("To run with pytest: pytest tests/unit/api/test_api_comprehensive.py -v")