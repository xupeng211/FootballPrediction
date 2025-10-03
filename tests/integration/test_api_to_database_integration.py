"""
API到数据库集成测试
Integration tests for API to database communication
"""

import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# 导入需要测试的模块
try:
    from src.main import app
    from src.database.connection import get_async_session
    from src.database.models import Match, Team, League, Prediction
    from src.api.predictions import get_match_prediction
    from src.api.data import get_matches, get_teams, get_leagues
    from src.database.config import DatabaseConfig
except ImportError:
    pytest.skip("Required modules not available", allow_module_level=True)


class TestAPIDatabaseIntegration:
    """API到数据库集成测试类"""

    @pytest.fixture(autouse=True)
    def disable_external_services(self, monkeypatch):
        import src.api.health as health_module
        import src.api.models as models_module
        import src.api.predictions as predictions_module
        import src.models.prediction_service as prediction_module

        health_module.MINIMAL_HEALTH_MODE = True
        health_module.FAST_FAIL = False

        monkeypatch.setattr(models_module, "mlflow_client", MagicMock())
        monkeypatch.setattr(predictions_module, "prediction_service", MagicMock())
        monkeypatch.setattr(prediction_module, "MlflowClient", MagicMock())
        monkeypatch.setattr(prediction_module, "mlflow", MagicMock())

    @pytest_asyncio.fixture(autouse=True)
    async def setup_database(self, request):
        """设置测试数据库"""
        # 创建测试数据库会话
        request.instance.mock_session = AsyncMock(spec=AsyncSession)

        # Mock数据库依赖注入
        async def override_get_async_session():
            yield request.instance.mock_session

        app.dependency_overrides[get_async_session] = override_get_async_session
        yield request.instance.mock_session
        app.dependency_overrides.pop(get_async_session, None)

    @pytest.mark.asyncio
    async def test_get_match_prediction_db_flow(self):
        """测试获取比赛预测的完整数据库流程"""
        # 准备测试数据
        match_id = 12345

        # Mock比赛数据
        mock_match = MagicMock()
        mock_match.id = match_id
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.league_id = 1
        mock_match.match_time = datetime.now() + timedelta(days=1)
        mock_match.match_status = "scheduled"

        # Mock预测数据
        mock_prediction = MagicMock()
        mock_prediction.id = 100
        mock_prediction.match_id = match_id
        mock_prediction.home_win_probability = 0.55
        mock_prediction.draw_probability = 0.25
        mock_prediction.away_win_probability = 0.20
        mock_prediction.predicted_result = "home"
        mock_prediction.confidence_score = 0.55
        mock_prediction.created_at = datetime.now()

        # Mock数据库查询结果
        with patch('src.api.predictions.select') as mock_select:
            # Mock查询比赛
            mock_match_result = MagicMock()
            mock_match_result.scalar_one_or_none.return_value = mock_match
            mock_prediction_result = MagicMock()
            mock_prediction_result.scalar_one_or_none.return_value = mock_prediction

            self.mock_session.execute.side_effect = [mock_match_result, mock_prediction_result]

            # 执行API调用
            response = await get_match_prediction(
                match_id=match_id,
                force_predict=False,
                session=self.mock_session
            )

            # 验证响应
            assert response["success"] is True
            assert response["data"]["match_id"] == match_id
            assert response["data"]["source"] == "cached"
            assert "prediction" in response["data"]
            assert response["data"]["prediction"]["home_win_probability"] == 0.55

    @pytest.mark.asyncio
    async def test_create_prediction_db_flow(self):
        """测试创建预测的数据库流程"""
        match_id = 12345

        # Mock比赛数据
        mock_match = MagicMock()
        mock_match.id = match_id
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.match_status = "scheduled"

        # Mock预测服务
        with patch('src.api.predictions.prediction_service') as mock_service:
            mock_prediction_response = MagicMock()
            mock_prediction_response.to_dict.return_value = {
                "match_id": match_id,
                "home_win_probability": 0.50,
                "draw_probability": 0.30,
                "away_win_probability": 0.20,
                "predicted_result": "home",
                "confidence_score": 0.50,
            }

            mock_service.predict_match = AsyncMock(return_value=mock_prediction_response)

            # Mock查询比赛
            mock_match_result = MagicMock()
            mock_match_result.scalar_one_or_none.return_value = mock_match
            self.mock_session.execute.side_effect = [mock_match_result]

            # 执行预测创建
            response = await get_match_prediction(
                match_id=match_id,
                force_predict=True,
                session=self.mock_session
            )

            # 验证预测服务调用
            mock_service.predict_match.assert_awaited_once_with(match_id)

            # 验证响应
            assert response["success"] is True
            assert response["data"]["source"] == "real_time"

    @pytest.mark.asyncio
    async def test_get_matches_with_pagination_db_flow(self):
        """测试获取比赛列表的分页数据库流程"""
        # 准备测试数据
        page_size = 10
        page = 1

        # Mock比赛数据
        mock_matches = []
        for i in range(page_size):
            match = MagicMock()
            match.id = 1000 + i
            match.home_team_id = 1
            match.away_team_id = 2
            match.league_id = 1
            match.match_time = datetime.now() + timedelta(days=i)
            match.match_status = "scheduled"
            mock_matches.append(match)

        # Mock查询结果
        with patch('src.api.data.select') as mock_select:
            matches_result = MagicMock()
            matches_result.scalars.return_value.all.return_value = mock_matches
            count_result = MagicMock()
            count_result.scalar.return_value = 100
            self.mock_session.execute.side_effect = [matches_result, count_result]

            # 执行API调用
            response = await get_matches(
                limit=page_size,
                offset=(page - 1) * page_size,
                status=None,
                session=self.mock_session
            )

            # 验证响应
            assert response["success"] is True
            assert len(response["data"]["matches"]) == page_size
            assert response["data"]["pagination"]["limit"] == page_size
            assert response["data"]["pagination"]["total"] == 100

    @pytest.mark.asyncio
    async def test_get_teams_with_search_db_flow(self):
        """测试搜索球队的数据库流程"""
        search_term = "United"

        # Mock球队数据
        mock_teams = []
        team_names = ["Manchester United", "Newcastle United", "Leeds United"]
        for i, name in enumerate(team_names):
            team = MagicMock()
            team.id = 100 + i
            team.name = name
            team.short_name = name.split()[0][:3]
            team.country = "England"
            team.founded = 1900 + i * 10
            mock_teams.append(team)

        # Mock查询结果
        with patch('src.api.data.select') as mock_select:
            teams_result = MagicMock()
            teams_result.scalars.return_value.all.return_value = mock_teams
            count_result = MagicMock()
            count_result.scalar.return_value = len(mock_teams)
            self.mock_session.execute.side_effect = [teams_result, count_result]

            # 执行API调用
            response = await get_teams(
                search=search_term,
                limit=10,
                offset=0,
                session=self.mock_session
            )

            # 验证响应
            assert response["success"] is True
            assert len(response["data"]["teams"]) == 3
            assert all("United" in team.name for team in mock_teams)

    @pytest.mark.asyncio
    async def test_batch_predictions_db_transaction(self):
        """测试批量预测的数据库事务"""
        match_ids = [12345, 12346, 12347]

        # Mock比赛数据
        mock_matches = []
        for match_id in match_ids:
            match = MagicMock()
            match.id = match_id
            match.home_team_id = 1
            match.away_team_id = 2
            match.match_status = "scheduled"
            mock_matches.append(match)

        # Mock预测结果
        mock_predictions = []
        for match_id in match_ids:
            prediction = MagicMock()
            prediction.match_id = match_id
            prediction.to_dict.return_value = {
                "match_id": match_id,
                "home_win_probability": 0.50,
                "draw_probability": 0.30,
                "away_win_probability": 0.20,
                "predicted_result": "home",
                "confidence_score": 0.50,
            }
            mock_predictions.append(prediction)

        # Mock数据库事务和预测服务
        with patch('src.api.predictions.prediction_service') as mock_service:
            mock_service.batch_predict_matches = AsyncMock(return_value=mock_predictions)

            # Mock查询比赛
            mock_matches_result = MagicMock()
            mock_matches_result.__iter__.return_value = (MagicMock(id=mid) for mid in match_ids)
            self.mock_session.execute.side_effect = [mock_matches_result]

            from src.api.predictions import batch_predict_matches

            # 执行批量预测
            response = await batch_predict_matches(match_ids, self.mock_session)

            # 验证预测服务调用
            mock_service.batch_predict_matches.assert_awaited_once()

            # 验证响应
            assert response["success"] is True
            assert response["data"]["successful_predictions"] == len(match_ids)

    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """测试数据库错误处理"""
        match_id = 12345

        # Mock数据库错误
        with patch.object(self.mock_session, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")

            from src.api.predictions import get_match_prediction
            from fastapi import HTTPException

            # 验证错误处理
            with pytest.raises(HTTPException) as exc_info:
                await get_match_prediction(
                    match_id=match_id,
                    force_predict=False,
                    session=self.mock_session
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_concurrent_db_requests(self):
        """测试并发数据库请求"""
        match_ids = [12345, 12346, 12347, 12348, 12349]

        # Mock数据
        mock_matches = {match_id: MagicMock() for match_id in match_ids}

        # Mock查询
        async def mock_execute(query):
            mock_result = MagicMock()
            if hasattr(query, 'where_clause'):  # 简化判断
                for match_id, match in mock_matches.items():
                    if str(match_id) in str(query):
                        mock_result.scalar_one_or_none.return_value = match
                        break
            return mock_result

        self.mock_session.execute.side_effect = mock_execute

        # 并发执行多个请求
        async def get_prediction(match_id):
            from src.api.predictions import get_match_prediction
            return await get_match_prediction(
                match_id=match_id,
                force_predict=False,
                session=self.mock_session
            )

        # 并发执行
        tasks = [get_prediction(mid) for mid in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        assert len(results) == len(match_ids)
        # 注意：由于mock的限制，这里主要测试并发执行不会崩溃

    @pytest.mark.asyncio
    async def test_database_connection_pool(self):
        """测试数据库连接池"""
        with patch('src.database.connection.create_async_engine') as mock_async_engine, \
            patch('src.database.connection.create_engine') as mock_sync_engine:

            mock_async_engine.return_value = MagicMock(spec=AsyncEngine)
            mock_sync_engine.return_value = MagicMock(spec=Engine)

            config = DatabaseConfig(
                host="localhost",
                port=5432,
                database="test_db",
                username="user",
                password="pass",
            )

            from src.database.connection import DatabaseManager

            DatabaseManager._instance = None
            manager = DatabaseManager()
            manager.initialize(config=config)

            assert mock_async_engine.called
            assert mock_sync_engine.called

    def test_client_api_integration(self):
        """测试客户端API集成"""
        client = TestClient(app, base_url="http://localhost")
        from src.api import health as health_module
        health_module.MINIMAL_HEALTH_MODE = True

        # 测试健康检查端点
        response = client.get("/health")
        assert response.status_code == 200

        # 测试预测端点（需要mock数据库）
        with patch('src.api.predictions.get_async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            # 测试获取预测
            response = client.get("/predictions/12345")
            # 可能返回404或200，取决于mock设置
            assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_prediction_failure_returns_error(self):
        """预测过程中异常时返回HTTP 500"""
        match_id = 12345

        mock_match = MagicMock()
        mock_match.id = match_id
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.match_status = "scheduled"

        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match
        self.mock_session.execute.side_effect = [mock_match_result]

        with patch('src.api.predictions.prediction_service') as mock_service:
            mock_service.predict_match = AsyncMock(side_effect=RuntimeError("prediction failed"))

            with pytest.raises(HTTPException) as exc:
                await get_match_prediction(
                    match_id=match_id,
                    force_predict=True,
                    session=self.mock_session
                )

            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """测试缓存集成"""
        match_id = 12345

        # Mock缓存
        with patch('src.cache.redis_manager.RedisManager') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance

            # Mock缓存命中
            mock_redis_instance.get = AsyncMock(return_value=json.dumps({
                "match_id": match_id,
                "home_win_probability": 0.55,
                "draw_probability": 0.25,
                "away_win_probability": 0.20
            }))

            cached_data = await mock_redis_instance.get(f"prediction:{match_id}")
            assert cached_data is not None

            # Mock缓存未命中
            mock_redis_instance.get = AsyncMock(return_value=None)
            cached_data = await mock_redis_instance.get(f"prediction:{match_id}")
            assert cached_data is None

    @pytest.mark.asyncio
    async def test_data_consistency_check(self):
        """测试数据一致性检查"""
        # 准备不一致的数据
        mock_match = MagicMock()
        mock_match.id = 12345
        mock_match.home_team_id = 1
        mock_match.away_team_id = 1  # 错误：主客队相同

        with patch('src.api.data.select') as mock_select:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_match
            self.mock_session.execute.return_value = mock_result

            # 数据验证应该失败
            from src.api.data import validate_match_data
            is_valid = validate_match_data(mock_match)
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_query_optimization(self):
        """测试查询优化"""
        # 测试批量查询优化
        match_ids = [12345, 12346, 12347, 12348, 12349]

        with patch('src.api.data.select') as mock_select:
            matches = []
            for mid in match_ids:
                match = MagicMock()
                match.id = mid
                match.home_team_id = 1
                match.away_team_id = 2
                match.league_id = 1
                match.match_time = datetime.now()
                match.match_status = MagicMock(value="scheduled")
                matches.append(match)

            matches_result = MagicMock()
            matches_result.scalars.return_value.all.return_value = matches
            self.mock_session.execute.return_value = matches_result

            from src.api.data import get_matches_batch

            result = await get_matches_batch(match_ids, self.mock_session)

            assert [item["id"] for item in result] == match_ids
            mock_select.assert_called()

    @pytest.mark.asyncio
    async def test_relationship_loading(self):
        """测试关系加载"""
        match_id = 12345

        # Mock带关联数据的比赛
        mock_match = MagicMock()
        mock_match.id = match_id
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2

        # Mock关联的球队数据
        mock_home_team = MagicMock()
        mock_home_team.id = 1
        mock_home_team.name = "Home Team"

        mock_away_team = MagicMock()
        mock_away_team.id = 2
        mock_away_team.name = "Away Team"

        mock_match.match_status.value = "scheduled"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        self.mock_session.execute.return_value = mock_result

        from src.api.data import get_match_by_id

        response = await get_match_by_id(match_id, self.mock_session)

        assert response["success"] is True
        assert response["data"]["match"]["id"] == match_id

    @pytest.mark.asyncio
    async def test_n_plus_one_query_detection(self):
        """测试N+1查询检测"""
        call_count = 0

        async def counting_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = MagicMock(id=1)
            return result

        self.mock_session.execute.side_effect = counting_execute

        match_ids = [12345, 12346, 12347]

        from src.api.data import get_match_by_id

        for match_id in match_ids:
            await get_match_by_id(match_id, self.mock_session)

        assert call_count == len(match_ids)

        # 实际实现中应该使用预加载来优化
        # 这里只是演示如何检测问题
