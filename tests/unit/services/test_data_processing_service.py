"""数据处理服务测试"""

from datetime import datetime
from unittest.mock import Mock

import pandas as pd
import pytest

from src.services.data_processing import DataProcessingService


class TestDataProcessingService:
    """数据处理服务测试"""

    @pytest.fixture
    def mock_repository(self):
        """模拟数据仓库"""
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存"""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository, mock_cache):
        """创建数据处理服务"""
        return DataProcessingService(repository=mock_repository, cache=mock_cache)

    def test_process_match_data(self, service, mock_repository):
        """测试处理比赛数据"""
        # 准备测试数据
        raw_data = {
            "match_id": 1,
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2024-01-01",
            "score": "2-1",
        }

        # 设置模拟返回
        mock_repository.save_processed_data.return_value = True

        # 调用方法
        result = service.process_match(raw_data)

        # 验证
        assert result is True
        mock_repository.save_processed_data.assert_called_once()

    def test_clean_player_data(self, service):
        """测试清理球员数据"""
        # 准备脏数据
        dirty_data = {
            "name": "John Doe ",
            "age": " 25",
            "position": "  MIDFIELDER  ",
            "salary": "50000.00",
        }

        # 调用方法
        cleaned_data = service.clean_player_data(dirty_data)

        # 验证
        assert cleaned_data["name"] == "John Doe"
        assert cleaned_data["age"] == 25
        assert cleaned_data["position"] == "MIDFIELDER"
        assert cleaned_data["salary"] == 50000.0

    def test_validate_match_data(self, service):
        """测试验证比赛数据"""
        # 有效数据
        valid_data = {
            "match_id": 1,
            "home_team_id": 1,
            "away_team_id": 2,
            "date": datetime(2024, 1, 1),
            "league": "Premier League",
        }
        assert service.validate_match_data(valid_data) is True

        # 无效数据（缺少字段）
        invalid_data = {"match_id": 1, "home_team_id": 1}
        assert service.validate_match_data(invalid_data) is False

    def test_aggregate_team_stats(self, service, mock_repository):
        """测试聚合球队统计"""
        # 设置模拟返回
        mock_repository.get_team_matches.return_value = [
            {"team_id": 1, "goals_scored": 2, "goals_conceded": 1},
            {"team_id": 1, "goals_scored": 3, "goals_conceded": 2},
            {"team_id": 1, "goals_scored": 1, "goals_conceded": 1},
        ]

        # 调用方法
        stats = service.aggregate_team_stats(1)

        # 验证
        assert stats["total_goals_scored"] == 6
        assert stats["total_goals_conceded"] == 4
        assert stats["matches_played"] == 3
        assert stats["average_goals_scored"] == 2.0

    def test_transform_data_format(self, service):
        """测试转换数据格式"""
        # 准备测试数据
        data_list = [
            {"match_id": 1, "team": "A", "score": 2},
            {"match_id": 1, "team": "B", "score": 1},
        ]

        # 调用方法
        transformed = service.transform_to_match_format(data_list)

        # 验证
        assert transformed["match_id"] == 1
        assert transformed["home_score"] == 2
        assert transformed["away_score"] == 1

    def test_handle_missing_data(self, service):
        """测试处理缺失数据"""
        # 准备带缺失值的数据
        data = pd.DataFrame(
            {"id": [1, 2, 3], "name": ["Team A", None, "Team C"], "score": [2, None, 1]}
        )

        # 调用方法
        cleaned_data = service.handle_missing_data(data)

        # 验证
        assert None not in cleaned_data["name"].values
        assert None not in cleaned_data["score"].values

    def test_calculate_derived_features(self, service):
        """测试计算衍生特征"""
        # 准备基础数据
        base_data = {
            "home_goals": 2,
            "away_goals": 1,
            "home_shots": 10,
            "away_shots": 5,
        }

        # 调用方法
        features = service.calculate_features(base_data)

        # 验证
        assert features["goal_difference"] == 1
        assert features["total_goals"] == 3
        assert features["home_shot_accuracy"] == 0.2  # 2/10
        assert features["away_shot_accuracy"] == 0.2  # 1/5

    def test_batch_process_matches(self, service, mock_repository):
        """测试批量处理比赛"""
        # 准备测试数据
        matches = [
            {"id": 1, "home": "A", "away": "B"},
            {"id": 2, "home": "C", "away": "D"},
        ]

        # 设置模拟返回
        mock_repository.batch_save.return_value = True

        # 调用方法
        result = service.batch_process_matches(matches)

        # 验证
        assert result is True
        mock_repository.batch_save.assert_called_once()

    def test_data_quality_check(self, service):
        """测试数据质量检查"""
        # 准备测试数据
        data = {
            "total_records": 1000,
            "null_values": 50,
            "duplicates": 10,
            "invalid_dates": 5,
        }

        # 调用方法
        quality_score = service.calculate_quality_score(data)

        # 验证
        assert 0 <= quality_score <= 1
        assert quality_score > 0.9  # 期望较高的质量分数

    def test_cache_processed_data(self, service, mock_cache):
        """测试缓存处理后的数据"""
        # 准备测试数据
        data = {"match_id": 1, "processed": True}
        cache_key = "match_1"

        # 调用方法
        service.cache_data(cache_key, data, ttl=3600)

        # 验证
        mock_cache.set.assert_called_once_with(cache_key, data, ex=3600)

    def test_get_cached_data(self, service, mock_cache):
        """测试获取缓存数据"""
        # 设置模拟返回
        cached_data = {"match_id": 1, "processed": True}
        mock_cache.get.return_value = cached_data

        # 调用方法
        result = service.get_cached_data("match_1")

        # 验证
        assert result == cached_data
        mock_cache.get.assert_called_once_with("match_1")
