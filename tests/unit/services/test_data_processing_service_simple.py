from typing import Optional

"""数据处理服务测试 - 简化版本"""

from unittest.mock import Mock

import pytest

from src.services.data_processing import DataProcessingService


class TestDataProcessingServiceSimple:
    """数据处理服务测试 - 简化版本"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def service(self, mock_session):
        """创建数据处理服务"""
        return DataProcessingService(session=mock_session)

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.session is not None
        assert service.initialized is False
        assert len(service.processors) == 4
        assert "match" in service.processors
        assert "odds" in service.processors
        assert "scores" in service.processors
        assert "features" in service.processors

    @pytest.mark.asyncio
    async def test_process_match_data(self, service):
        """测试处理比赛数据"""
        # 准备测试数据
        raw_data = {
            "match_id": 1,
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
        }

        # 处理数据
        processed = await service.processors["match"].process(raw_data)

        # 验证结果
        assert processed["match_id"] == 1
        assert processed["type"] == "match"
        assert "processed_at" in processed
        assert processed["home_team"] == "Team A"

    @pytest.mark.asyncio
    async def test_process_odds_data(self, service):
        """测试处理赔率数据"""
        # 准备测试数据
        raw_data = {"match_id": 1, "home_win": 2.5, "draw": 3.2, "away_win": 2.8}

        # 处理数据
        processed = await service.processors["odds"].process(raw_data)

        # 验证结果
        assert processed["match_id"] == 1
        assert processed["type"] == "odds"
        assert "processed_at" in processed
        assert processed["home_win"] == 2.5

    @pytest.mark.asyncio
    async def test_process_scores_data(self, service):
        """测试处理比分数据"""
        # 准备测试数据
        raw_data = {"match_id": 1, "minute": 45, "scorer": "Player A", "team": "Team A"}

        # 处理数据
        processed = await service.processors["scores"].process(raw_data)

        # 验证结果
        assert processed["match_id"] == 1
        assert processed["type"] == "scores"
        assert "processed_at" in processed
        assert processed["scorer"] == "Player A"

    @pytest.mark.asyncio
    async def test_multiple_data_types(self, service):
        """测试处理多种数据类型"""
        match_data = {"match_id": 1, "home": "Team A"}
        odds_data = {"match_id": 1, "home_win": 2.5}
        scores_data = {"match_id": 1, "minute": 45}

        # 处理不同类型的数据
        processed_match = await service.processors["match"].process(match_data)
        processed_odds = await service.processors["odds"].process(odds_data)
        processed_scores = await service.processors["scores"].process(scores_data)

        # 验证处理结果
        assert processed_match["type"] == "match"
        assert processed_odds["type"] == "odds"
        assert processed_scores["type"] == "scores"

    def test_service_session_usage(self, service):
        """测试服务会话使用"""
        # 模拟会话操作
        service.session.query.return_value = ["match1", "match2"]

        # 测试会话调用
        results = service.session.query()

        # 验证
        assert results == ["match1", "match2"]
        service.session.query.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])