""""""""
预测 API 集成测试
测试预测 API 与数据库的交互
""""""""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestPredictionAPIIntegration:
    """预测 API 集成测试"""

    @pytest.mark.asyncio
    async def test_create_prediction(
        self, api_client: AsyncClient, db_session, sample_match_data, auth_headers: dict
    ):
        """测试创建预测"""
        # 准备请求数据
        request_data = {
            "match_id": sample_match_data["match"].id,
            "prediction": "HOME_WIN",
            "confidence": 0.85,
        }

        # 发送请求
        response = await api_client.post(
            "/api/v1/predictions", json=request_data, headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 201
        _data = response.json()
        assert data["match_id"] == request_data["match_id"]
        assert data["prediction"] == request_data["prediction"]
        assert data["confidence"] == request_data["confidence"]
        assert "id" in data
        assert "created_at" in data

        # 验证数据库中的数据
from src.database.models import Prediction

        _result = await db_session.get(Prediction, data["id"])
        assert result is not None
        assert result._prediction == request_data["prediction"]
        assert result.confidence == request_data["confidence"]

    @pytest.mark.asyncio
    async def test_get_prediction(
        self,
        api_client: AsyncClient,
        db_session,
        sample_prediction_data,
        auth_headers: dict,
    ):
        """测试获取单个预测"""
        _prediction = sample_prediction_data["prediction"]

        # 发送请求
        response = await api_client.get(
            f"/api/v1/predictions/{prediction.id}", headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert data["id"] == prediction.id
        assert data["prediction"] == prediction.prediction
        assert data["confidence"] == prediction.confidence

    @pytest.mark.asyncio
    async def test_list_user_predictions(
        self,
        api_client: AsyncClient,
        db_session,
        sample_prediction_data,
        auth_headers: dict,
    ):
        """测试获取用户预测列表"""
        _user = sample_prediction_data["user"]

        # 创建更多预测
from src.database.models import Prediction

        for i in range(5):
            pred = Prediction(
                user_id=user.id,
                match_id=sample_prediction_data["prediction"].match_id,
                _prediction="DRAW" if i % 2 == 0 else "AWAY_WIN",
                confidence=0.5 + (i * 0.1),
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(pred)
        await db_session.commit()

        # 发送请求
        response = await api_client.get(
            "/api/v1/predictions", params={"user_id": user.id}, headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "data" in data
        assert len(data["data"]) == 6  # 1个初始 + 5个新创建
        assert data["total"] == 6
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_update_prediction_status(
        self,
        api_client: AsyncClient,
        db_session,
        sample_prediction_data,
        auth_headers: dict,
    ):
        """测试更新预测状态"""
        _prediction = sample_prediction_data["prediction"]

        # 先更新比赛结果
from src.database.models import Match

        match = await db_session.get(Match, prediction.match_id)
        match.status = "COMPLETED"
        match.home_score = 2
        match.away_score = 1
        await db_session.commit()

        # 更新预测状态
        response = await api_client.patch(
            f"/api/v1/predictions/{prediction.id}/status",
            json={"status": "COMPLETED", "is_correct": True},
            headers=auth_headers,
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["is_correct"] is True

        # 验证数据库
        await db_session.refresh(prediction)
        assert prediction.status == "COMPLETED"
        assert prediction.is_correct is True

    @pytest.mark.asyncio
    async def test_prediction_validation(self, api_client: AsyncClient, auth_headers: dict):
        """测试预测数据验证"""
        # 无效的预测类型
        response = await api_client.post(
            "/api/v1/predictions",
            json={
                "match_id": 1,
                "prediction": "INVALID_PREDICTION",
                "confidence": 0.85,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

        # 无效的置信度
        response = await api_client.post(
            "/api/v1/predictions",
            json={
                "match_id": 1,
                "prediction": "HOME_WIN",
                "confidence": 1.5,  # 超出 0-1 范围
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

        # 缺少必需字段
        response = await api_client.post(
            "/api/v1/predictions",
            json={
                "prediction": "HOME_WIN"
                # 缺少 match_id 和 confidence
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_prediction_error(
        self, api_client: AsyncClient, sample_match_data, auth_headers: dict
    ):
        """测试重复预测错误"""
        request_data = {
            "match_id": sample_match_data["match"].id,
            "prediction": "HOME_WIN",
            "confidence": 0.85,
        }

        # 创建第一个预测
        response1 = await api_client.post(
            "/api/v1/predictions", json=request_data, headers=auth_headers
        )
        assert response1.status_code == 201

        # 尝试创建重复预测
        response2 = await api_client.post(
            "/api/v1/predictions", json=request_data, headers=auth_headers
        )
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, api_client: AsyncClient, sample_match_data):
        """测试未授权访问"""
        # 没有 token
        response = await api_client.post(
            "/api/v1/predictions",
            json={
                "match_id": sample_match_data["match"].id,
                "prediction": "HOME_WIN",
                "confidence": 0.85,
            },
        )
        assert response.status_code == 401

        # 无效的 token
        response = await api_client.post(
            "/api/v1/predictions",
            json={
                "match_id": sample_match_data["match"].id,
                "prediction": "HOME_WIN",
                "confidence": 0.85,
            },
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_prediction(
        self,
        api_client: AsyncClient,
        db_session,
        sample_prediction_data,
        auth_headers: dict,
    ):
        """测试删除预测"""
        _prediction = sample_prediction_data["prediction"]

        # 删除预测
        response = await api_client.delete(
            f"/api/v1/predictions/{prediction.id}", headers=auth_headers
        )
        assert response.status_code == 204

        # 验证已删除
from src.database.models import Prediction

        _result = await db_session.get(Prediction, prediction.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_prediction_statistics(
        self,
        api_client: AsyncClient,
        db_session,
        sample_prediction_data,
        auth_headers: dict,
    ):
        """测试预测统计"""
        _user = sample_prediction_data["user"]

        # 创建更多预测数据
from src.database.models import Match, Prediction

        predictions = []
        for i in range(10):
            # 创建比赛
            match = Match(
                home_team_id=1,
                away_team_id=2,
                match_date=datetime.now(timezone.utc),
                status="COMPLETED",
                home_score=i % 3,
                away_score=(i + 1) % 3,
                competition="Test League",
                season="2024/2025",
            )
            db_session.add(match)
            await db_session.commit()
            await db_session.refresh(match)

            # 创建预测
            pred = Prediction(
                user_id=user.id,
                match_id=match.id,
                _prediction="HOME_WIN" if i % 2 == 0 else "DRAW",
                confidence=0.5 + (i * 0.05),
                status="COMPLETED",
                is_correct=(i % 3 == 0),  # 每3个预测中1个正确
                created_at=datetime.now(timezone.utc),
            )
            predictions.append(pred)
            db_session.add(pred)

        await db_session.commit()

        # 获取统计
        response = await api_client.get(
            "/api/v1/predictions/statistics",
            params={"user_id": user.id},
            headers=auth_headers,
        )

        # 验证响应
        assert response.status_code == 200
        _stats = response.json()
        assert "total_predictions" in stats
        assert "correct_predictions" in stats
        assert "accuracy" in stats
        assert "total_predictions" == 11  # 1个初始 + 10个新创建
        assert "accuracy" in stats
        assert 0 <= stats["accuracy"] <= 1
