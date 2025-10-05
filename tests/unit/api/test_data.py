"""
数据API单元测试

测试数据访问相关的API端点：
- 比赛特征数据
- 球队统计数据
- 仪表板数据
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest


class TestGetMatchFeatures:
    """获取比赛特征数据API测试"""

    @pytest.mark.asyncio
    async def test_get_match_features_success(self, api_client_full, sample_match):
        """测试获取比赛特征成功"""
        mock_session = api_client_full.mock_session

        # 模拟比赛查询
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match

        # 模拟特征查询 - 返回空列表
        mock_features_result = MagicMock()
        mock_features_result.scalars.return_value.all.return_value = []

        # 模拟预测查询 - 返回None
        mock_prediction_result = MagicMock()
        mock_prediction_result.scalar_one_or_none.return_value = None

        # 模拟赔率查询 - 返回空列表
        mock_odds_result = MagicMock()
        mock_odds_result.scalars.return_value.all.return_value = []

        # 设置mock session的返回值
        mock_session.execute.side_effect = [
            mock_match_result,  # 第一次查询：match
            mock_features_result,  # 第二次查询：features
            mock_prediction_result,  # 第三次查询：prediction
            mock_odds_result,  # 第四次查询：odds
        ]

        # 发送请求
        response = api_client_full.get("/api/v1/data/matches/12345/features")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == 12345
        assert data["match_info"]["home_team_id"] == 10
        assert data["match_info"]["away_team_id"] == 20
        assert data["features"]["home_team"] is None
        assert data["features"]["away_team"] is None
        assert data["prediction"] is None
        assert data["odds"] == []

    @pytest.mark.asyncio
    async def test_get_match_features_with_data(self, api_client_full, sample_match):
        """测试获取比赛特征成功 - 包含数据"""
        mock_session = api_client_full.mock_session

        # 创建模拟特征
        mock_feature = MagicMock()
        mock_feature.team_type.value = "home"
        mock_feature.team_id = 10
        mock_feature.recent_5_wins = 3
        mock_feature.recent_5_draws = 1
        mock_feature.recent_5_losses = 1
        mock_feature.recent_5_goals_for = 8
        mock_feature.recent_5_goals_against = 4
        mock_feature.recent_5_win_rate.return_value = 0.6
        mock_feature.home_wins = 2
        mock_feature.home_draws = 1
        mock_feature.home_losses = 1
        mock_feature.away_wins = 1
        mock_feature.away_draws = 0
        mock_feature.away_losses = 2
        mock_feature.home_win_rate.return_value = 0.5
        mock_feature.away_win_rate.return_value = 0.33
        mock_feature.h2h_wins = 2
        mock_feature.h2h_draws = 1
        mock_feature.h2h_losses = 1
        mock_feature.h2h_goals_for = 5
        mock_feature.h2h_goals_against = 3
        mock_feature.h2h_win_rate.return_value = 0.5
        mock_feature.league_position = 3
        mock_feature.points = 25
        mock_feature.goal_difference = 8
        mock_feature.calculate_team_strength.return_value = 85.5

        # 创建模拟预测
        mock_prediction = MagicMock()
        mock_prediction.model_name = "test_model"
        mock_prediction.model_version = "1.0"
        mock_prediction.predicted_result.value = "home_win"
        mock_prediction.home_win_probability = Decimal("0.6")
        mock_prediction.draw_probability = Decimal("0.25")
        mock_prediction.away_win_probability = Decimal("0.15")
        mock_prediction.confidence_score = Decimal("0.75")
        mock_prediction.get_predicted_score.return_value = "2-1"
        mock_prediction.predicted_at = datetime.now()

        # 创建模拟赔率
        mock_odds = MagicMock()
        mock_odds.bookmaker = "TestBookmaker"
        mock_odds.market_type.value = "match_winner"
        mock_odds.home_odds = Decimal("2.5")
        mock_odds.draw_odds = Decimal("3.2")
        mock_odds.away_odds = Decimal("2.8")
        mock_odds.collected_at = datetime.now()

        # 设置mock返回值
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match

        mock_features_result = MagicMock()
        mock_features_result.scalars.return_value.all.return_value = [mock_feature]

        mock_prediction_result = MagicMock()
        mock_prediction_result.scalar_one_or_none.return_value = mock_prediction

        mock_odds_result = MagicMock()
        mock_odds_result.scalars.return_value.all.return_value = [mock_odds]

        mock_session.execute.side_effect = [
            mock_match_result,
            mock_features_result,
            mock_prediction_result,
            mock_odds_result,
        ]

        # 发送请求
        response = api_client_full.get("/api/v1/data/matches/12345/features")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == 12345
        assert data["features"]["home_team"]["team_id"] == 10
        assert data["features"]["home_team"]["recent_form"]["wins"] == 3
        assert data["features"]["home_team"]["team_strength"] == 85.5
        assert data["prediction"]["model_name"] == "test_model"
        assert data["prediction"]["probabilities"]["home_win"] == 0.6
        assert data["prediction"]["predicted_score"] == "2-1"
        assert len(data["odds"]) == 1
        assert data["odds"][0]["bookmaker"] == "TestBookmaker"
        assert data["odds"][0]["home_odds"] == 2.5

    @pytest.mark.asyncio
    async def test_get_match_features_not_found(self, api_client_full):
        """测试获取不存在比赛的特征"""
        mock_session = api_client_full.mock_session

        # 模拟比赛不存在
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_match_result

        # 发送请求
        response = api_client_full.get("/api/v1/data/matches/99999/features")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert "比赛不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_match_features_server_error(self, api_client_full, sample_match):
        """测试服务器错误"""
        mock_session = api_client_full.mock_session

        # 第一次查询成功，后续查询失败
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_match)),
            Exception("Database connection failed"),
        ]

        # 发送请求
        response = api_client_full.get("/api/v1/data/matches/12345/features")

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert "获取比赛特征失败" in data["message"]


class TestGetTeamStats:
    """获取球队统计数据API测试"""

    @pytest.mark.asyncio
    async def test_get_team_stats_success(self, api_client_full):
        """测试获取球队统计成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.name = "Test Team FC"

        # 创建模拟比赛（已结束）
        mock_matches = []
        # 比赛1: 球队10作为主队，2:1获胜
        match1 = MagicMock()
        match1.home_team_id = 10
        match1.away_team_id = 20
        match1.home_score = 2
        match1.away_score = 1
        match1.match_status = "finished"
        mock_matches.append(match1)

        # 比赛2: 球队10作为客队，1:2获胜
        match2 = MagicMock()
        match2.home_team_id = 30
        match2.away_team_id = 10
        match2.home_score = 1
        match2.away_score = 2
        match2.match_status = "finished"
        mock_matches.append(match2)

        # 比赛3: 球队10作为主队，3:1获胜
        match3 = MagicMock()
        match3.home_team_id = 10
        match3.away_team_id = 40
        match3.home_score = 3
        match3.away_score = 1
        match3.match_status = "finished"
        mock_matches.append(match3)

        # 比赛4: 球队10作为客队，0:2失败
        match4 = MagicMock()
        match4.home_team_id = 50
        match4.away_team_id = 10
        match4.home_score = 2
        match4.away_score = 0
        match4.match_status = "finished"
        mock_matches.append(match4)

        # 比赛5: 球队10作为主队，1:1平局
        match5 = MagicMock()
        match5.home_team_id = 10
        match5.away_team_id = 60
        match5.home_score = 1
        match5.away_score = 1
        match5.match_status = "finished"
        mock_matches.append(match5)

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team

        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = mock_matches

        mock_session.execute.side_effect = [mock_team_result, mock_matches_result]

        # 发送请求
        response = api_client_full.get("/api/v1/data/teams/10/stats")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == 10
        assert data["team_name"] == "Test Team FC"
        assert data["total_matches"] == 5
        assert data["wins"] == 3  # 3场胜利
        assert data["draws"] == 1  # 1场平局
        assert data["losses"] == 1  # 1场失败
        assert data["goals_for"] == 8  # 2+2+3+0+1 = 8
        assert data["goals_against"] == 6  # 1+1+1+2+1 = 6
        assert data["win_rate"] == 0.6  # 3/5 = 0.6
        assert data["goal_difference"] == 2  # 8-6 = 2
        assert data["points"] == 10  # 3*3 + 1*1 + 1*0 = 10

    @pytest.mark.asyncio
    async def test_get_team_stats_no_matches(self, api_client_full):
        """测试获取球队统计 - 无比赛记录"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.name = "Test Team FC"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team

        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_team_result, mock_matches_result]

        # 发送请求
        response = api_client_full.get("/api/v1/data/teams/10/stats")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == 10
        assert data["total_matches"] == 0
        assert data["wins"] == 0
        assert data["win_rate"] == 0.0
        assert data["goal_difference"] == 0
        assert data["points"] == 0

    @pytest.mark.asyncio
    async def test_get_team_stats_not_found(self, api_client_full):
        """测试获取不存在球队的统计"""
        mock_session = api_client_full.mock_session

        # 模拟球队不存在
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_team_result

        # 发送请求
        response = api_client_full.get("/api/v1/data/teams/99999/stats")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert "球队不存在" in data["message"]


class TestGetTeamRecentStats:
    """获取球队近期统计数据API测试"""

    @pytest.mark.asyncio
    async def test_get_team_recent_stats_success(self, api_client_full):
        """测试获取球队近期统计成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.team_name = "Test Team FC"

        # 创建模拟近期比赛
        match_time = datetime.now() - timedelta(days=10)
        mock_match = MagicMock()
        mock_match.id = 123
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.home_score = 2
        mock_match.away_score = 1
        mock_match.match_time = match_time
        mock_match.match_status = "finished"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team

        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [mock_match]

        mock_session.execute.side_effect = [mock_team_result, mock_matches_result]

        # 发送请求
        response = api_client_full.get("/api/v1/data/teams/10/recent_stats?days=30")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == 10
        assert data["team_name"] == "Test Team FC"
        assert data["period_days"] == 30
        assert data["total_matches"] == 1
        assert data["home_matches"] == 1
        assert data["wins"] == 1
        assert data["win_rate"] == 1.0
        assert data["clean_sheets"] == 0
        assert len(data["matches"]) == 1
        assert data["matches"][0]["match_id"] == 123
        assert data["matches"][0]["result"] == "win"
        assert data["matches"][0]["score"] == "2-1"

    @pytest.mark.asyncio
    async def test_get_team_recent_stats_custom_days(self, api_client_full):
        """测试获取球队近期统计 - 自定义天数"""
        mock_session = api_client_full.mock_session

        # 创建模拟球队
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.team_name = "Test Team FC"

        # 设置mock返回值
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = mock_team

        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_team_result, mock_matches_result]

        # 发送请求 - 7天
        response = api_client_full.get("/api/v1/data/teams/10/recent_stats?days=7")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7
        assert data["total_matches"] == 0

    @pytest.mark.asyncio
    async def test_get_team_recent_stats_invalid_days(self, api_client_full):
        """测试获取球队近期统计 - 无效天数"""
        # 发送请求 - 天数超过限制
        response = api_client_full.get("/api/v1/data/teams/10/recent_stats?days=400")

        # 验证响应 - FastAPI会自动验证参数
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_team_recent_stats_not_found(self, api_client_full):
        """测试获取不存在球队的近期统计"""
        mock_session = api_client_full.mock_session

        # 模拟球队不存在
        mock_team_result = MagicMock()
        mock_team_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_team_result

        # 发送请求
        response = api_client_full.get("/api/v1/data/teams/99999/recent_stats")

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert "球队不存在" in data["message"]


class TestGetDashboardData:
    """获取仪表板数据API测试"""

    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self, api_client_full):
        """测试获取仪表板数据成功"""
        mock_session = api_client_full.mock_session

        # 创建模拟今日比赛
        mock_match = MagicMock()
        mock_match.id = 123
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.league_id = 1
        mock_match.match_time = datetime.now()
        mock_match.match_status.value = "scheduled"

        # 创建模拟预测
        mock_prediction = MagicMock()
        mock_prediction.match_id = 123
        mock_prediction.model_name = "test_model"
        mock_prediction.predicted_result.value = "home_win"
        mock_prediction.confidence_score = Decimal("0.75")
        mock_prediction.predicted_at = datetime.now()

        # 设置mock返回值
        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = [mock_match]

        mock_predictions_result = MagicMock()
        mock_predictions_result.scalars.return_value.all.return_value = [mock_prediction]

        mock_db_result = MagicMock()
        mock_db_result.scalar.return_value = 1

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_matches_result,  # 查询今日比赛
            mock_predictions_result,  # 查询最新预测
            mock_db_result,  # 系统健康检查
            mock_logs_result,  # 查询采集日志
        ]

        # 发送请求（DataQualityMonitor已经在conftest.py中被mock了）
        response = api_client_full.get("/api/v1/data/dashboard/data")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "generated_at" in data
        assert data["today_matches"]["count"] == 1
        assert len(data["today_matches"]["matches"]) == 1
        assert data["predictions"]["count"] == 1
        assert len(data["predictions"]["latest"]) == 1
        assert data["data_quality"]["overall_status"] == "healthy"
        assert data["data_quality"]["quality_score"] == 95
        assert "system_health" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_data_no_data(self, api_client_full):
        """测试获取仪表板数据 - 无数据"""
        mock_session = api_client_full.mock_session

        # 设置mock返回值 - 空数据
        mock_matches_result = MagicMock()
        mock_matches_result.scalars.return_value.all.return_value = []

        mock_predictions_result = MagicMock()
        mock_predictions_result.scalars.return_value.all.return_value = []

        mock_db_result = MagicMock()
        mock_db_result.scalar.return_value = 1

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_matches_result,
            mock_predictions_result,
            mock_db_result,
            mock_logs_result,
        ]

        # 发送请求（DataQualityMonitor已经在conftest.py中被mock了）
        response = api_client_full.get("/api/v1/data/dashboard/data")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["today_matches"]["count"] == 0
        assert data["predictions"]["count"] == 0
        assert data["data_quality"]["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_dashboard_data_error(self, api_client_full):
        """测试获取仪表板数据错误"""
        mock_session = api_client_full.mock_session

        # 模拟数据库错误
        mock_session.execute.side_effect = Exception("Database error")

        # 发送请求（DataQualityMonitor已经在conftest.py中被mock了）
        response = api_client_full.get("/api/v1/data/dashboard/data")

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert "获取仪表板数据失败" in data["message"]


class TestSystemHealth:
    """系统健康状态测试"""

    @pytest.mark.asyncio
    async def test_system_health_healthy(self, api_client_full):
        """测试系统健康状态 - 健康"""
        mock_session = api_client_full.mock_session

        # 模拟数据库健康
        mock_db_result = MagicMock()
        mock_db_result.scalar.return_value = 1

        # 模拟采集日志健康
        mock_log = MagicMock()
        mock_log.created_at = datetime.now()
        mock_log.status = "success"

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = [mock_log]

        mock_session.execute.side_effect = [mock_db_result, mock_logs_result]

        # 直接调用函数
        from src.api.data import get_system_health

        health = await get_system_health(mock_session)

        # 验证结果
        assert health["database"] == "healthy"
        assert health["data_collection"] == "healthy"
        assert "last_collection" in health
        assert health["recent_failures"] == 0

    @pytest.mark.asyncio
    async def test_system_health_unhealthy(self, api_client_full):
        """测试系统健康状态 - 不健康"""
        mock_session = api_client_full.mock_session

        # 模拟数据库不健康
        mock_session.execute.side_effect = Exception("Connection failed")

        # 直接调用函数
        from src.api.data import get_system_health

        health = await get_system_health(mock_session)

        # 验证结果
        assert health["database"] == "unknown"
        assert "error" in health

    @pytest.mark.asyncio
    async def test_system_health_warning(self, api_client_full):
        """测试系统健康状态 - 警告"""
        mock_session = api_client_full.mock_session

        # 模拟数据库健康
        mock_db_result = MagicMock()
        mock_db_result.scalar.return_value = 1

        # 模拟部分采集失败
        success_log = MagicMock()
        success_log.status = "success"
        success_log.created_at = datetime.now()

        failed_log = MagicMock()
        failed_log.status = "failed"
        failed_log.created_at = datetime.now()

        mock_logs_result = MagicMock()
        mock_logs_result.scalars.return_value.all.return_value = [
            success_log,
            failed_log,
        ]

        mock_session.execute.side_effect = [mock_db_result, mock_logs_result]

        # 直接调用函数
        from src.api.data import get_system_health

        health = await get_system_health(mock_session)

        # 验证结果
        assert health["database"] == "healthy"
        assert health["data_collection"] == "warning"
        assert health["recent_failures"] == 1
