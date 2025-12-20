#!/usr/bin/env python3
"""
核心模块覆盖率提升测试
专注于提升特征提取器、主引擎和API客户端的测试覆盖率
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# 导入核心模块
from src.data_access.processors.advanced_feature_extractor import AdvancedFeatureExtractor
from src.api.fotmob_client import FotMobAPIClient, CircuitBreaker, CircuitState
from src.core.main_engine_v5 import MainEngineV5
from src.schemas.match_features import MatchFeatures
from src.config_unified import get_settings


class TestFeatureExtractorCoverage:
    """特征提取器覆盖率提升测试"""

    @pytest.fixture
    def extractor(self):
        """创建特征提取器实例"""
        return AdvancedFeatureExtractor()

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            'content': {
                'stats': {
                    'Periods': {
                        'All': {
                            'stats': [{
                                'key': 'top_stats',
                                'stats': [
                                    {'key': 'expected_goals', 'stats': [1.5, 0.8]},
                                    {'key': 'BallPossesion', 'stats': [55, 45]},
                                    {'key': 'CornerKicks', 'stats': [7, 3]},
                                    {'key': 'YellowCards', 'stats': [2, 4]},
                                    {'key': 'Shots', 'stats': [12, 15]}
                                ]
                            }]
                        }
                    }
                }
            },
            'general': {
                'homeTeam': {'name': 'Manchester United'},
                'awayTeam': {'name': 'Liverpool'}
            }
        }

    def test_extractor_initialization(self, extractor):
        """测试提取器初始化"""
        assert extractor is not None
        assert hasattr(extractor, 'extract_complete_features')

    def test_complete_feature_extraction(self, extractor, sample_match_data):
        """测试完整特征提取"""
        features = extractor.extract_complete_features(sample_match_data, 'test_match')

        # 验证核心特征
        assert features.home_xg == 1.5
        assert features.away_xg == 0.8
        assert features.home_possession == 55.0
        assert features.away_possession == 45.0
        assert features.home_corners == 7
        assert features.away_corners == 3
        assert features.home_yellow_cards == 2
        assert features.away_yellow_cards == 4
        assert features.home_shots_total == 12
        assert features.away_shots_total == 15

    def test_extract_xg_features(self, extractor, sample_match_data):
        """测试XG特征提取"""
        xg_features = extractor._extract_xg_features(sample_match_data)
        assert xg_features['home_xg'] == 1.5
        assert xg_features['away_xg'] == 0.8
        assert xg_features['xg_difference'] == 0.7
        assert xg_features['total_xg'] == 2.3

    def test_extract_possession_features(self, extractor, sample_match_data):
        """测试控球率特征提取"""
        possession_features = extractor._extract_possession_features(sample_match_data)
        assert possession_features['home_possession'] == 55.0
        assert possession_features['away_possession'] == 45.0
        assert possession_features['possession_difference'] == 10.0

    def test_extract_corners_features(self, extractor, sample_match_data):
        """测试角球特征提取"""
        corners_features = extractor._extract_corners_features(sample_match_data)
        assert corners_features['home_corners'] == 7
        assert corners_features['away_corners'] == 3
        assert corners_features['corners_difference'] == 4

    def test_extract_cards_features(self, extractor, sample_match_data):
        """测试牌数特征提取"""
        cards_features = extractor._extract_cards_features(sample_match_data)
        assert cards_features['home_yellow_cards'] == 2
        assert cards_features['away_yellow_cards'] == 4

    def test_extract_shots_features(self, extractor, sample_match_data):
        """测试射门特征提取"""
        shots_features = extractor._extract_shots_features(sample_match_data)
        assert shots_features['home_shots_total'] == 12
        assert shots_features['away_shots_total'] == 15

    def test_empty_data_handling(self, extractor):
        """测试空数据处理"""
        empty_data = {'content': {'stats': {}}, 'general': {}}
        features = extractor.extract_complete_features(empty_data, 'empty_test')

        # 验证默认值处理
        assert features.home_xg == 0.0
        assert features.away_xg == 0.0
        assert features.home_possession == 0.0
        assert features.away_possession == 0.0

    def test_malformed_data_handling(self, extractor):
        """测试异常数据处理"""
        malformed_data = {'invalid': 'data'}

        with pytest.raises(Exception):
            extractor.extract_complete_features(malformed_data, 'malformed_test')


class TestFotMobClientCoverage:
    """FotMob客户端覆盖率提升测试"""

    @pytest.fixture
    def client(self):
        """创建API客户端实例"""
        return FotMobAPIClient(timeout=5, max_retries=2)

    def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert client.base_url == "https://www.fotmob.com/api"
        assert client.timeout.total == 5
        assert client.max_retries == 2
        assert client.circuit_breaker is not None

    def test_circuit_breaker_initialization(self, client):
        """测试熔断器初始化"""
        cb = client.circuit_breaker
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.state == CircuitState.CLOSED
        assert cb.call_allowed() == True

    def test_circuit_breaker_success_flow(self, client):
        """测试熔断器成功流程"""
        cb = client.circuit_breaker

        # 记录成功
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_failure_flow(self, client):
        """测试熔断器失败流程"""
        cb = client.circuit_breaker

        # 记录失败
        for i in range(5):
            cb.record_failure(Exception(f"Test error {i}"))

        assert cb.failure_count == 5
        assert cb.state == CircuitState.OPEN
        assert cb.call_allowed() == False

    def test_circuit_breaker_recovery_flow(self, client):
        """测试熔断器恢复流程"""
        cb = client.circuit_breaker

        # 触发熔断
        for i in range(5):
            cb.record_failure(Exception(f"Test error {i}"))

        assert cb.state == CircuitState.OPEN

        # 模拟时间恢复（手动设置为HALF_OPEN）
        cb.state = CircuitState.HALF_OPEN
        assert cb.call_allowed() == True

        # 记录成功应该恢复到CLOSED
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_match_data_method(self, client):
        """测试获取比赛数据方法"""
        # Mock响应数据
        mock_data = {'test': 'data'}

        with patch.object(client, 'get_match_details', return_value=mock_data):
            result = await client.get_match_data('test_match')
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_multiple_matches_method(self, client):
        """测试批量获取比赛数据方法"""
        # Mock响应数据
        mock_data = [{'match': 'data1'}, {'match': 'data2'}]

        with patch.object(client, 'get_match_details', side_effect=mock_data):
            results = await client.get_multiple_matches(['match1', 'match2'])
            assert len(results) == 2
            assert results[0] == mock_data[0]
            assert results[1] == mock_data[1]


class TestMainEngineCoverage:
    """主引擎覆盖率提升测试"""

    @pytest.fixture
    def engine(self):
        """创建主引擎实例"""
        # 使用测试模式初始化
        return MainEngineV5(test_mode=True)

    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine is not None
        assert hasattr(engine, 'collect_match_data')
        assert hasattr(engine, 'process_predictions')

    @patch('src.core.main_engine_v5.get_settings')
    def test_database_connection_config(self, mock_settings):
        """测试数据库连接配置"""
        # Mock配置
        mock_settings.return_value.database.host = 'localhost'
        mock_settings.return_value.database.port = 5432
        mock_settings.return_value.database.name = 'test_db'
        mock_settings.return_value.database.user = 'test_user'
        mock_settings.return_value.database.password.get_secret_value.return_value = 'test_pass'

        # 这里只测试配置获取，不测试实际连接
        settings = get_settings()
        assert settings.database.host == 'localhost'

    def test_data_validation_schema(self):
        """测试数据验证模式"""
        # 创建有效的特征数据
        valid_data = {
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_xg': 1.5,
            'away_xg': 0.8,
            'home_possession': 55.0,
            'away_possession': 45.0,
            'home_corners': 7,
            'away_corners': 3,
            'home_yellow_cards': 2,
            'away_yellow_cards': 4,
            'home_shots_total': 12,
            'away_shots_total': 15
        }

        # 验证可以创建MatchFeatures对象
        features = MatchFeatures(**valid_data)
        assert features.home_team == 'Team A'
        assert features.home_xg == 1.5
        assert features.home_possession == 55.0

    def test_settings_initialization(self):
        """测试配置系统初始化"""
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, 'database')
        assert hasattr(settings, 'model')
        assert hasattr(settings, 'logging')


class TestSystemIntegrationCoverage:
    """系统集成覆盖率提升测试"""

    def test_end_to_end_feature_pipeline(self):
        """测试端到端特征处理流水线"""
        # 创建测试数据
        test_data = {
            'content': {
                'stats': {
                    'Periods': {
                        'All': {
                            'stats': [{
                                'key': 'top_stats',
                                'stats': [
                                    {'key': 'expected_goals', 'stats': [2.1, 0.9]},
                                    {'key': 'BallPossesion', 'stats': [60, 40]},
                                    {'key': 'CornerKicks', 'stats': [8, 2]},
                                    {'key': 'YellowCards', 'stats': [1, 3]},
                                    {'key': 'Shots', 'stats': [15, 10]}
                                ]
                            }]
                        }
                    }
                }
            },
            'general': {
                'homeTeam': {'name': 'Arsenal'},
                'awayTeam': {'name': 'Chelsea'}
            }
        }

        # 提取特征
        extractor = AdvancedFeatureExtractor()
        features = extractor.extract_complete_features(test_data, 'pipeline_test')

        # 验证流水线完整性
        assert features.home_xg == 2.1
        assert features.away_xg == 0.9
        assert features.home_possession == 60.0
        assert features.away_possession == 40.0
        assert features.home_corners == 8
        assert features.away_corners == 2
        assert features.home_yellow_cards == 1
        assert features.away_yellow_cards == 3
        assert features.home_shots_total == 15
        assert features.away_shots_total == 10

        # 验证计算特征
        assert features.xg_difference == 1.2
        assert features.total_xg == 3.0
        assert features.possession_difference == 20.0
        assert features.corners_difference == 6
        assert features.shots_difference == 5

    def test_api_client_with_circuit_breaker_integration(self):
        """测试API客户端与熔断器集成"""
        client = FotMobAPIClient(failure_threshold=3, recovery_timeout=30)

        # 验证熔断器配置
        assert client.circuit_breaker.failure_threshold == 3
        assert client.circuit_breaker.recovery_timeout == 30

        # 测试熔断器状态
        assert client.circuit_breaker.call_allowed() == True
        assert client.circuit_breaker.state == CircuitState.CLOSED