"""
预测API测试
测试覆盖src/api/predictions.py中的所有路由
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from src.api.predictions import router


@pytest.mark.asyncio
class TestPredictions:
    """测试预测相关端点"""

    @patch('src.api.predictions.get_async_session')
    @patch('src.api.predictions.prediction_service')
    async def test_get_match_prediction_success(self, mock_service, mock_get_session):
        """测试获取比赛预测成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟比赛存在
        mock_match = MagicMock()
        mock_match.id = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_match

        # 模拟预测服务
        mock_service.predict.return_value = {
            "prediction": {
                "home_win_prob": 0.6,
                "draw_prob": 0.25,
                "away_win_prob": 0.15
            },
            "confidence": 0.85,
            "model_version": "v1.2.0"
        }

        from src.api.predictions import get_match_prediction
        result = await get_match_prediction(1)

        assert result is not None
        assert "data" in result
        assert result["success"] is True
        assert "prediction" in result["data"]

    @patch('src.api.predictions.get_async_session')
    async def test_get_match_prediction_not_found(self, mock_get_session):
        """测试获取不存在比赛的预测"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟比赛不存在
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        from src.api.predictions import get_match_prediction

        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction(99999)

        assert exc_info.value.status_code == 404

    @patch('src.api.predictions.prediction_service')
    async def test_batch_predict_success(self, mock_service):
        """测试批量预测成功"""
        mock_service.batch_predict.return_value = [
            {
                "match_id": 1,
                "prediction": {"home_win_prob": 0.6},
                "confidence": 0.85
            },
            {
                "match_id": 2,
                "prediction": {"home_win_prob": 0.4},
                "confidence": 0.78
            }
        ]

        from src.api.predictions import batch_predict
        result = await batch_predict(
            match_ids=[1, 2],
            model_version="v1.2.0"
        )

        assert result is not None
        assert "data" in result
        assert result["success"] is True
        assert len(result["data"]["predictions"]) == 2

    @patch('src.api.predictions.get_async_session')
    @patch('src.api.predictions.prediction_service')
    async def test_create_prediction_success(self, mock_service, mock_get_session):
        """测试创建预测成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟预测创建
        mock_service.create_prediction.return_value = {
            "id": 123,
            "match_id": 1,
            "prediction": {"home_win_prob": 0.6},
            "created_at": datetime.now()
        }

        from src.api.predictions import create_prediction
        result = await create_prediction(
            match_id=1,
            features={"team_form": 0.8},
            model_version="v1.2.0"
        )

        assert result is not None
        assert "data" in result
        assert result["success"] is True

    @patch('src.api.predictions.get_async_session')
    async def test_get_prediction_history(self, mock_get_session):
        """测试获取预测历史"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟历史记录
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            MagicMock(id=1, match_id=1, accuracy=0.85)
        ]

        from src.api.predictions import get_prediction_history
        result = await get_prediction_history(
            limit=10,
            offset=0,
            start_date=datetime.now().date()
        )

        assert result is not None
        assert "data" in result
        assert result["success"] is True


class TestRouterConfiguration:
    """测试路由配置"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/predictions"

    def test_router_tags(self):
        """测试路由标签"""
        assert router.tags == ["predictions"]

    def test_router_has_endpoints(self):
        """测试路由器有端点"""
        route_count = len(list(router.routes))
        assert route_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])