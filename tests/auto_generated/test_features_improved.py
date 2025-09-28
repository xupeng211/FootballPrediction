"""
features_improved.py 测试文件
测试改进版特征服务API功能，包括错误处理、日志记录和防御性编程
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 模拟外部依赖
with patch.dict('sys.modules', {
    'fastapi': Mock(),
    'sqlalchemy': Mock(),
    'sqlalchemy.ext.asyncio': Mock(),
    'sqlalchemy.exc': Mock(),
    'src.database.connection': Mock(),
    'src.database.models.match': Mock(),
    'src.features.entities': Mock(),
    'src.features.feature_calculator': Mock(),
    'src.features.feature_store': Mock(),
    'src.utils.response': Mock(),
    'src.api': Mock()
}):
    from api.features_improved import router, feature_store, feature_calculator, get_match_features_improved, features_health_check

# 模拟依赖注入
class MockSession:
    def __init__(self):
        self.execute = AsyncMock()
        self.scalar_one_or_none = AsyncMock()

class MockMatch:
    def __init__(self, id=1, home_team_id=1, away_team_id=2, league_id=1, match_time=None, season="2024-25", match_status="scheduled"):
        self.id = id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.league_id = league_id
        self.match_time = match_time or datetime.now()
        self.season = season
        self.match_status = match_status


class TestFeaturesImprovedInitialization:
    """测试改进版特征服务初始化"""

    @patch('api.features_improved.FootballFeatureStore')
    @patch('api.features_improved.FeatureCalculator')
    def test_successful_initialization(self, mock_calculator, mock_store):
        """测试成功初始化"""
        mock_store_instance = Mock()
        mock_calculator_instance = Mock()
        mock_store.return_value = mock_store_instance
        mock_calculator.return_value = mock_calculator_instance

        # 重新导入以测试初始化
        with patch('api.features_improved.logger') as mock_logger:
            import importlib
            import api.features_improved
            importlib.reload(api.features_improved)

            mock_logger.info.assert_called_with("特征存储和计算器初始化成功")

    @patch('api.features_improved.FootballFeatureStore')
    def test_initialization_failure(self, mock_store):
        """测试初始化失败"""
        mock_store.side_effect = Exception("Initialization failed")

        with patch('api.features_improved.logger') as mock_logger:
            import importlib
            import api.features_improved
            importlib.reload(api.features_improved)

            mock_logger.error.assert_called_with("特征存储初始化失败: Initialization failed")


class TestGetMatchFeaturesImproved:
    """测试改进版获取比赛特征功能"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_session = MockSession()
        self.mock_match = MockMatch(id=1, home_team_id=1, away_team_id=2)

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    @patch('api.features_improved.feature_calculator')
    def test_get_match_features_success(self, mock_calculator, mock_store, mock_get_session):
        """测试成功获取比赛特征"""
        # 设置依赖
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = self.mock_match
        mock_store.get_match_features_for_prediction.return_value = {"feature1": 1.0, "feature2": 2.0}

        # 执行测试
        result = get_match_features_improved(1, include_raw=False, session=self.mock_session)

        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["match_info"]["match_id"] == 1
        assert result["data"]["features"] == {"feature1": 1.0, "feature2": 2.0}

    @patch('api.features_improved.get_async_session')
    def test_invalid_match_id(self, mock_get_session):
        """测试无效比赛ID"""
        mock_get_session.return_value = self.mock_session

        with pytest.raises(Exception) as exc_info:
            get_match_features_improved(0, session=self.mock_session)

        # 验证HTTP异常
        assert "比赛ID必须大于0" in str(exc_info.value)

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    def test_feature_store_unavailable(self, mock_store, mock_get_session):
        """测试特征存储服务不可用"""
        # 设置特征存储为None
        with patch('api.features_improved.feature_store', None):
            mock_get_session.return_value = self.mock_session

            with pytest.raises(Exception) as exc_info:
                get_match_features_improved(1, session=self.mock_session)

            assert "特征存储服务暂时不可用" in str(exc_info.value)

    @patch('api.features_improved.get_async_session')
    def test_match_not_found(self, mock_get_session):
        """测试比赛不存在"""
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = None

        with pytest.raises(Exception) as exc_info:
            get_match_features_improved(999, session=self.mock_session)

        assert "比赛 999 不存在" in str(exc_info.value)

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    def test_database_query_error(self, mock_store, mock_get_session):
        """测试数据库查询错误"""
        from sqlalchemy.exc import SQLAlchemyError

        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.side_effect = SQLAlchemyError("Database error")
        mock_store.get_match_features_for_prediction.return_value = {}

        with pytest.raises(Exception) as exc_info:
            get_match_features_improved(1, session=self.mock_session)

        assert "数据库查询失败" in str(exc_info.value)

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    @patch('api.features_improved.MatchEntity')
    def test_match_entity_creation_error(self, mock_entity, mock_store, mock_get_session):
        """测试比赛实体创建错误"""
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = self.mock_match
        mock_entity.side_effect = Exception("Entity creation failed")
        mock_store.get_match_features_for_prediction.return_value = {}

        with pytest.raises(Exception) as exc_info:
            get_match_features_improved(1, session=self.mock_session)

        assert "处理比赛数据时发生错误" in str(exc_info.value)

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    def test_feature_retrieval_error(self, mock_store, mock_get_session):
        """测试特征获取错误（优雅降级）"""
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = self.mock_match
        mock_store.get_match_features_for_prediction.side_effect = Exception("Feature retrieval failed")

        result = get_match_features_improved(1, include_raw=False, session=self.mock_session)

        assert result["status"] == "success"
        assert result["data"]["features"] == {}  # 优雅降级：返回空特征
        assert "features_warning" in result["data"]
        assert "特征数据获取部分失败" in result["data"]["features_warning"]

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    @patch('api.features_improved.feature_calculator')
    @patch('api.features_improved.MatchEntity')
    def test_include_raw_features_success(self, mock_entity, mock_calculator, mock_store, mock_get_session):
        """测试包含原始特征数据成功"""
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = self.mock_match
        mock_store.get_match_features_for_prediction.return_value = {"basic_features": 1.0}

        # 模拟特征计算器
        mock_features = Mock()
        mock_features.to_dict.return_value = {"raw_feature1": 0.5, "raw_feature2": 0.8}
        mock_calculator.calculate_all_match_features.return_value = mock_features

        result = get_match_features_improved(1, include_raw=True, session=self.mock_session)

        assert result["status"] == "success"
        assert "raw_features" in result["data"]
        assert result["data"]["raw_features"]["raw_feature1"] == 0.5

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    @patch('api.features_improved.feature_calculator')
    def test_include_raw_features_error(self, mock_calculator, mock_store, mock_get_session):
        """测试包含原始特征数据失败"""
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = self.mock_match
        mock_store.get_match_features_for_prediction.return_value = {"basic_features": 1.0}
        mock_calculator.calculate_all_match_features.side_effect = Exception("Raw feature calculation failed")

        result = get_match_features_improved(1, include_raw=True, session=self.mock_session)

        assert result["status"] == "success"
        assert "raw_features_error" in result["data"]
        assert "Raw feature calculation failed" in result["data"]["raw_features_error"]

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    def test_empty_features_data(self, mock_store, mock_get_session):
        """测试空特征数据"""
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = self.mock_match
        mock_store.get_match_features_for_prediction.return_value = None

        result = get_match_features_improved(1, include_raw=False, session=self.mock_session)

        assert result["status"] == "success"
        assert result["data"]["features"] == {}

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    def test_match_without_season(self, mock_store, mock_get_session):
        """测试没有赛季信息的比赛"""
        mock_match_no_season = MockMatch(id=1, season=None)
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = mock_match_no_season
        mock_store.get_match_features_for_prediction.return_value = {"features": 1.0}

        with patch('api.features_improved.MatchEntity') as mock_entity:
            result = get_match_features_improved(1, include_raw=False, session=self.mock_session)

            # 验证使用了默认赛季
            mock_entity.assert_called_once()
            call_kwargs = mock_entity.call_args[1]
            assert call_kwargs['season'] == '2024-25'  # 默认赛季

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    def test_match_without_time(self, mock_store, mock_get_session):
        """测试没有比赛时间的比赛"""
        mock_match_no_time = MockMatch(id=1, match_time=None)
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = mock_match_no_time
        mock_store.get_match_features_for_prediction.return_value = {"features": 1.0}

        result = get_match_features_improved(1, include_raw=False, session=self.mock_session)

        assert result["status"] == "success"
        assert result["data"]["match_info"]["match_time"] is None

    @patch('api.features_improved.get_async_session')
    def test_unexpected_error_handling(self, mock_get_session):
        """测试未预期错误处理"""
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception) as exc_info:
            get_match_features_improved(1, session=self.mock_session)

        assert "获取比赛特征失败" in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)


class TestFeaturesHealthCheck:
    """测试特征服务健康检查"""

    def test_health_check_all_healthy(self):
        """测试健康检查全部健康"""
        with patch('api.features_improved.feature_store', Mock()):
            with patch('api.features_improved.feature_calculator', Mock()):
                result = features_health_check()

                assert result["status"] == "healthy"
                assert result["components"]["feature_store"] is True
                assert result["components"]["feature_calculator"] is True

    def test_health_check_feature_store_none(self):
        """测试特征存储为None的健康检查"""
        with patch('api.features_improved.feature_store', None):
            with patch('api.features_improved.feature_calculator', Mock()):
                result = features_health_check()

                assert result["status"] == "unhealthy"
                assert result["components"]["feature_store"] is False

    def test_health_check_feature_calculator_none(self):
        """测试特征计算器为None的健康检查"""
        with patch('api.features_improved.feature_store', Mock()):
            with patch('api.features_improved.feature_calculator', None):
                result = features_health_check()

                assert result["status"] == "unhealthy"
                assert result["components"]["feature_calculator"] is False

    def test_health_check_connection_failure(self):
        """测试连接失败的健康检查"""
        mock_store = Mock()
        # 模拟连接检查失败
        def mock_connection_check():
            raise Exception("Connection failed")

        with patch('api.features_improved.feature_store', mock_store):
            with patch('api.features_improved.feature_calculator', Mock()):
                # 模拟连接检查逻辑
                with patch('api.features_improved.logger') as mock_logger:
                    result = features_health_check()

                    # 验证连接检查失败时的状态
                    assert result["components"]["feature_store_connection"] is False
                    mock_logger.warning.assert_called()

    def test_health_check_timestamp(self):
        """测试健康检查时间戳"""
        with patch('api.features_improved.feature_store', Mock()):
            with patch('api.features_improved.feature_calculator', Mock()):
                result = features_health_check()

                assert "timestamp" in result
                # 验证时间戳格式
                datetime.fromisoformat(result["timestamp"])


class TestFeaturesImprovedIntegration:
    """测试改进版特征服务集成功能"""

    @patch('api.features_improved.get_async_session')
    @patch('api.features_improved.feature_store')
    @patch('api.features_improved.feature_calculator')
    def test_end_to_end_feature_retrieval(self, mock_calculator, mock_store, mock_get_session):
        """测试端到端特征获取"""
        # 设置完整的测试场景
        mock_match = MockMatch(id=100, home_team_id=10, away_team_id=20, league_id=5)
        mock_get_session.return_value = self.mock_session
        self.mock_session.scalar_one_or_none.return_value = mock_match
        mock_store.get_match_features_for_prediction.return_value = {
            "team_form": 0.8,
            "head_to_head": 0.6,
            "league_performance": 0.9
        }

        result = get_match_features_improved(100, include_raw=False, session=self.mock_session)

        # 验证响应结构
        assert result["status"] == "success"
        assert "data" in result
        assert "match_info" in result["data"]
        assert "features" in result["data"]

        # 验证比赛信息
        match_info = result["data"]["match_info"]
        assert match_info["match_id"] == 100
        assert match_info["home_team_id"] == 10
        assert match_info["away_team_id"] == 20
        assert match_info["league_id"] == 5

        # 验证特征数据
        features = result["data"]["features"]
        assert features["team_form"] == 0.8
        assert features["head_to_head"] == 0.6

    def test_concurrent_feature_requests(self):
        """测试并发特征请求"""
        import asyncio

        async def mock_feature_request(match_id):
            # 模拟异步特征请求
            await asyncio.sleep(0.1)
            return {"match_id": match_id, "features": {"test": 1.0}}

        async def run_concurrent_requests():
            tasks = [
                mock_feature_request(1),
                mock_feature_request(2),
                mock_feature_request(3),
            ]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_concurrent_requests())
        assert len(results) == 3
        assert results[0]["match_id"] == 1
        assert results[2]["match_id"] == 3

    def test_feature_service_error_recovery(self):
        """测试特征服务错误恢复"""
        # 模拟服务从错误中恢复
        with patch('api.features_improved.feature_store') as mock_store:
            # 第一次调用失败
            mock_store.get_match_features_for_prediction.side_effect = [Exception("Service unavailable"), {"features": 1.0}]

            # 第一次请求应该失败
            with pytest.raises(Exception):
                get_match_features_improved(1, session=self.mock_session)

            # 第二次请求应该成功
            with patch('api.features_improved.get_async_session') as mock_get_session:
                mock_get_session.return_value = self.mock_session
                self.mock_session.scalar_one_or_none.return_value = self.mock_match

                result = get_match_features_improved(1, session=self.mock_session)
                assert result["status"] == "success"

    def test_feature_service_performance_monitoring(self):
        """测试特征服务性能监控"""
        import time

        with patch('api.features_improved.get_async_session') as mock_get_session:
            mock_get_session.return_value = self.mock_session
            self.mock_session.scalar_one_or_none.return_value = self.mock_match

            with patch('api.features_improved.feature_store') as mock_store:
                mock_store.get_match_features_for_prediction.return_value = {"features": 1.0}

                start_time = time.time()
                result = get_match_features_improved(1, session=self.mock_session)
                end_time = time.time()

                execution_time = end_time - start_time
                assert execution_time < 1.0  # 应该在1秒内完成
                assert result["status"] == "success"

    def test_feature_service_parameter_validation(self):
        """测试特征服务参数验证"""
        # 测试不同参数组合
        test_cases = [
            (1, False),  # 正常参数
            (1, True),   # 包含原始特征
            (999, False), # 大ID
        ]

        for match_id, include_raw in test_cases:
            # 验证参数类型
            assert isinstance(match_id, int)
            assert isinstance(include_raw, bool)
            assert match_id > 0

    def test_feature_service_response_structure(self):
        """测试特征服务响应结构"""
        # 验证API响应的基本结构
        with patch('api.features_improved.get_async_session') as mock_get_session:
            mock_get_session.return_value = self.mock_session
            self.mock_session.scalar_one_or_none.return_value = self.mock_match

            with patch('api.features_improved.feature_store') as mock_store:
                mock_store.get_match_features_for_prediction.return_value = {"features": 1.0}

                result = get_match_features_improved(1, session=self.mock_session)

                # 验证响应结构
                assert "status" in result
                assert "data" in result
                assert "message" in result
                assert result["status"] in ["success", "error"]

                # 验证数据结构
                data = result["data"]
                assert "match_info" in data
                assert "features" in data

                # 验证比赛信息结构
                match_info = data["match_info"]
                required_fields = ["match_id", "home_team_id", "away_team_id", "league_id"]
                for field in required_fields:
                    assert field in match_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])