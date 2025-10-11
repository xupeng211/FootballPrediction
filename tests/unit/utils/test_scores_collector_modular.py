"""
测试比分收集器的模块化拆分
Test modular split of scores collector
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.collectors.scores.data_sources import (
    BaseScoreSource,
    FootballAPISource,
    ApiSportsSource,
    ScoreSourceManager,
)
from src.collectors.scores.processor import ScoreDataProcessor
from src.collectors.scores.publisher import ScoreUpdatePublisher
from src.collectors.scores.collector import ScoresCollector
from src.collectors.scores.manager import ScoresCollectorManager


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_redis_manager():
    """模拟Redis管理器"""
    redis_manager = MagicMock()
    redis_manager.publish = AsyncMock()
    return redis_manager


@pytest.fixture
def mock_match():
    """模拟比赛对象"""
    match = MagicMock()
    match.id = 1
    match.home_score = 0
    match.away_score = 0
    match.home_half_score = 0
    match.away_half_score = 0
    match.match_status = "SCHEDULED"
    match.home_team = MagicMock()
    match.home_team.name = "Team A"
    match.away_team = MagicMock()
    match.away_team.name = "Team B"
    match.match_time = datetime.now()
    return match


class TestDataSources:
    """测试数据源模块"""

    def test_base_score_source_is_abstract(self):
        """测试基础数据源是抽象类"""
        with pytest.raises(TypeError):
            BaseScoreSource()

    @pytest.mark.asyncio
    async def test_football_api_source_transform(self):
        """测试Football API数据转换"""
        source = FootballAPISource()
        data = {
            "match": {
                "id": 123,
                "utcDate": "2024-01-01T15:00:00Z",
                "status": "IN_PLAY",
                "score": {
                    "fullTime": {"home": 2, "away": 1},
                    "halfTime": {"home": 1, "away": 0},
                },
            }
        }
        result = source.transform_data(data)
        assert result["match_id"] == 123
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["home_half_score"] == 1
        assert result["away_half_score"] == 0
        assert result["match_status"] == "IN_PLAY"

    @pytest.mark.asyncio
    async def test_api_sports_source_transform(self):
        """测试API-Sports数据转换"""
        source = ApiSportsSource()
        data = {
            "fixture": {
                "id": 456,
                "date": "2024-01-01T15:00:00Z",
                "status": {"long": "LIVE"},
            },
            "goals": {"home": 3, "away": 1},
            "score": {"halftime": {"home": 2, "away": 0}},
            "events": [{"type": "goal"}],
        }
        result = source.transform_data(data)
        assert result["match_id"] == 456
        assert result["home_score"] == 3
        assert result["away_score"] == 1
        assert result["home_half_score"] == 2
        assert result["away_half_score"] == 0
        assert result["match_status"] == "LIVE"
        assert len(result["events"]) == 1

    @pytest.mark.asyncio
    async def test_score_source_manager(self):
        """测试数据源管理器"""
        manager = ScoreSourceManager()
        # 测试获取数据源
        football_source = manager.get_source("football_api")
        assert isinstance(football_source, FootballAPISource)

        api_sports_source = manager.get_source("api_sports")
        assert isinstance(api_sports_source, ApiSportsSource)

        # 测试不存在的数据源
        assert manager.get_source("invalid") is None


class TestScoreDataProcessor:
    """测试比分数据处理器"""

    @pytest.mark.asyncio
    async def test_process_score_data_success(self, mock_db_session, mock_match):
        """测试成功处理比分数据"""
        mock_db_session.get.return_value = mock_match

        processor = ScoreDataProcessor(mock_db_session)
        score_data = {
            "home_score": 2,
            "away_score": 1,
            "match_status": "IN_PLAY",
            "match_time": "2024-01-01T15:00:00Z",
            "last_updated": "2024-01-01T15:30:00Z",
            "home_half_score": 1,
            "away_half_score": 0,
        }

        result = await processor.process_score_data(1, score_data)
        assert result is not None
        assert result["match_id"] == 1
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["match_status"] == "IN_PROGRESS"
        assert result["previous_status"] == "SCHEDULED"

    @pytest.mark.asyncio
    async def test_process_score_data_missing_match(self, mock_db_session):
        """测试处理不存在的比赛数据"""
        mock_db_session.get.return_value = None

        processor = ScoreDataProcessor(mock_db_session)
        score_data = {"home_score": 1, "away_score": 0, "match_status": "LIVE"}

        result = await processor.process_score_data(999, score_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_score_data_incomplete(self, mock_db_session, mock_match):
        """测试处理不完整的比分数据"""
        mock_db_session.get.return_value = mock_match

        processor = ScoreDataProcessor(mock_db_session)
        score_data = {"home_score": 1}  # 缺少必要字段

        result = await processor.process_score_data(1, score_data)
        assert result is None

    def test_validate_score_data(self):
        """测试验证比分数据"""
        processor = ScoreDataProcessor(MagicMock())

        # 有效数据
        valid_data = {"match_id": 1, "home_score": "2", "away_score": "1"}
        assert processor.validate_score_data(valid_data) is True

        # 无效数据（缺少字段）
        invalid_data = {"match_id": 1, "home_score": "2"}
        assert processor.validate_score_data(invalid_data) is False

        # 无效数据（非数字比分）
        invalid_score = {"match_id": 1, "home_score": "abc", "away_score": "1"}
        assert processor.validate_score_data(invalid_score) is False


class TestScoreUpdatePublisher:
    """测试比分更新发布器"""

    @pytest.mark.asyncio
    async def test_publish_score_update(self, mock_redis_manager):
        """测试发布比分更新"""
        publisher = ScoreUpdatePublisher(mock_redis_manager)
        score_data = {
            "match_id": 1,
            "home_score": 2,
            "away_score": 1,
            "match_status": "IN_PROGRESS",
            "previous_status": "SCHEDULED",
            "last_updated": datetime.now(),
        }

        await publisher.publish_score_update(score_data)

        # 验证发布调用
        assert mock_redis_manager.publish.call_count == 2
        calls = mock_redis_manager.publish.call_args_list

        # 验证特定频道发布
        assert calls[0][0][0] == "scores:match:1"
        assert calls[1][0][0] == "scores:global"

        # 验证消息内容
        message = json.loads(calls[0][0][1])
        assert message["type"] == "score_update"
        assert message["match_id"] == 1
        assert message["home_score"] == 2
        assert message["away_score"] == 1

    @pytest.mark.asyncio
    async def test_publish_match_event(self, mock_redis_manager):
        """测试发布比赛事件"""
        publisher = ScoreUpdatePublisher(mock_redis_manager)
        event_data = {"type": "goal", "minute": 25}

        await publisher.publish_match_event(1, event_data)

        # 验证发布调用
        mock_redis_manager.publish.assert_called_once()
        call_args = mock_redis_manager.publish.call_args

        assert call_args[0][0] == "scores:events:1"
        message = json.loads(call_args[0][1])
        assert message["type"] == "match_event"
        assert message["match_id"] == 1
        assert message["event"] == event_data

    @pytest.mark.asyncio
    async def test_publish_live_matches_list(self, mock_redis_manager):
        """测试发布实时比赛列表"""
        publisher = ScoreUpdatePublisher(mock_redis_manager)
        matches = [
            {"match_id": 1, "home_team": "A", "away_team": "B"},
            {"match_id": 2, "home_team": "C", "away_team": "D"},
        ]

        await publisher.publish_live_matches_list(matches)

        # 验证发布调用
        mock_redis_manager.publish.assert_called_once()
        call_args = mock_redis_manager.publish.call_args

        assert call_args[0][0] == "scores:live_matches"
        message = json.loads(call_args[0][1])
        assert message["type"] == "live_matches"
        assert message["count"] == 2
        assert len(message["matches"]) == 2


class TestScoresCollector:
    """测试比分收集器"""

    @pytest.mark.asyncio
    async def test_collector_initialization(self, mock_db_session, mock_redis_manager):
        """测试收集器初始化"""
        collector = ScoresCollector(
            db_session=mock_db_session,
            redis_manager=mock_redis_manager,
            api_key="test_key",
            websocket_url="ws://test.com",
            poll_interval=60,
        )

        assert collector.db_session == mock_db_session
        assert collector.redis_manager == mock_redis_manager
        assert collector.api_key == "test_key"
        assert collector.websocket_url == "ws://test.com"
        assert collector.poll_interval == 60
        assert collector.running is False
        assert isinstance(collector.source_manager, ScoreSourceManager)
        assert isinstance(collector.processor, ScoreDataProcessor)
        assert isinstance(collector.publisher, ScoreUpdatePublisher)

    @pytest.mark.asyncio
    async def test_collect_match_score_with_cache(
        self, mock_db_session, mock_redis_manager
    ):
        """测试从缓存收集比分"""
        collector = ScoresCollector(mock_db_session, mock_redis_manager)

        # 设置缓存
        cached_data = {"home_score": 1, "away_score": 0}
        collector.match_cache[1] = cached_data
        collector.last_update_cache[1] = datetime.now()

        result = await collector.collect_match_score(1)
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_collect_match_score_force_update(
        self, mock_db_session, mock_redis_manager
    ):
        """测试强制更新比分"""
        collector = ScoresCollector(mock_db_session, mock_redis_manager)

        # 模拟数据源返回
        test_data = {"home_score": 2, "away_score": 1, "match_status": "LIVE"}
        collector.source_manager.fetch_match_score = AsyncMock(return_value=test_data)

        # 模拟处理器返回
        processed_data = {
            "match_id": 1,
            "home_score": 2,
            "away_score": 1,
            "match_status": "IN_PROGRESS",
        }
        collector.processor.process_score_data = AsyncMock(return_value=processed_data)

        # 模拟保存和发布
        collector._save_score_data = AsyncMock()
        collector.publisher.publish_score_update = AsyncMock()

        result = await collector.collect_match_score(1, force=True)
        assert result == processed_data

    def test_get_stats(self, mock_db_session, mock_redis_manager):
        """测试获取统计信息"""
        collector = ScoresCollector(mock_db_session, mock_redis_manager)
        collector.stats = {
            "total_updates": 10,
            "successful_updates": 8,
            "failed_updates": 2,
            "average_processing_time": 0.5,
        }

        stats = collector.get_stats()
        assert stats["total_updates"] == 10
        assert stats["successful_updates"] == 8
        assert stats["failed_updates"] == 2
        assert stats["success_rate"] == 0.8
        assert stats["running"] is False


class TestScoresCollectorManager:
    """测试比分收集器管理器"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = ScoresCollectorManager()
        assert len(manager.collectors) == 0
        assert manager.global_stats["total_collectors"] == 0
        assert manager.global_stats["active_collectors"] == 0

    @pytest.mark.asyncio
    async def test_get_collector(self, mock_redis_manager):
        """测试获取收集器"""
        manager = ScoresCollectorManager()

        with patch("src.database.connection.DatabaseManager") as mock_db_manager:
            mock_db_manager.return_value.get_async_session.return_value = MagicMock()

            collector = await manager.get_collector(1)
            assert collector is not None
            assert 1 in manager.collectors
            assert manager.global_stats["total_collectors"] == 1

    @pytest.mark.asyncio
    async def test_start_all_collectors(self, mock_redis_manager):
        """测试启动所有收集器"""
        manager = ScoresCollectorManager()

        # 创建模拟收集器
        collector1 = AsyncMock()
        collector2 = AsyncMock()
        collector1.running = False
        collector2.running = False

        manager.collectors[1] = collector1
        manager.collectors[2] = collector2

        await manager.start_all()

        # 验证所有收集器都已启动
        collector1.start_collection.assert_called_once()
        collector2.start_collection.assert_called_once()
        assert manager.global_stats["active_collectors"] == 2

    @pytest.mark.asyncio
    async def test_stop_all_collectors(self, mock_redis_manager):
        """测试停止所有收集器"""
        manager = ScoresCollectorManager()
        manager.global_stats["active_collectors"] = 2

        # 创建模拟收集器
        collector1 = AsyncMock()
        collector2 = AsyncMock()
        collector1.running = True
        collector2.running = True

        manager.collectors[1] = collector1
        manager.collectors[2] = collector2

        await manager.stop_all()

        # 验证所有收集器都已停止
        collector1.stop_collection.assert_called_once()
        collector2.stop_collection.assert_called_once()
        assert manager.global_stats["active_collectors"] == 0

    def test_remove_collector(self, mock_redis_manager):
        """测试移除收集器"""
        manager = ScoresCollectorManager()
        manager.global_stats["total_collectors"] = 1

        # 创建模拟收集器
        collector = AsyncMock()
        collector.running = False

        manager.collectors[1] = collector

        manager.remove_collector(1)

        assert 1 not in manager.collectors
        assert manager.global_stats["total_collectors"] == 0

    def test_get_global_stats(self, mock_redis_manager):
        """测试获取全局统计"""
        manager = ScoresCollectorManager()

        # 创建模拟收集器
        collector1 = MagicMock()
        collector1.running = True
        collector1.stats = {
            "total_updates": 10,
            "successful_updates": 8,
            "failed_updates": 2,
            "average_processing_time": 0.5,
        }

        collector2 = MagicMock()
        collector2.running = False
        collector2.stats = {
            "total_updates": 5,
            "successful_updates": 4,
            "failed_updates": 1,
            "average_processing_time": 0.3,
        }

        manager.collectors[1] = collector1
        manager.collectors[2] = collector2

        stats = manager.get_global_stats()

        assert stats["total_collectors"] == 2
        assert stats["total_updates"] == 15
        assert stats["successful_updates"] == 12
        assert stats["failed_updates"] == 3
        assert stats["success_rate"] == 80.0
        assert "collectors" in stats

    @pytest.mark.asyncio
    async def test_health_check(self, mock_redis_manager):
        """测试健康检查"""
        manager = ScoresCollectorManager()

        # 创建模拟收集器
        collector1 = MagicMock()
        collector1.running = True
        collector1.get_stats.return_value = {"running": True}

        collector2 = MagicMock()
        collector2.running = False
        collector2.get_stats.return_value = {"running": False}

        manager.collectors[1] = collector1
        manager.collectors[2] = collector2

        health = await manager.health_check()

        assert health["status"] == "healthy"
        assert health["total_collectors"] == 2
        assert health["healthy_collectors"] == 1
        assert len(health["issues"]) == 1


def test_get_scores_manager():
    """测试获取全局管理器实例"""
    from src.collectors.scores.manager import get_scores_manager, _scores_manager

    # 重置全局变量
    import src.collectors.scores.manager as manager_module

    manager_module._scores_manager = None

    manager1 = get_scores_manager()
    manager2 = get_scores_manager()

    # 验证返回同一个实例
    assert manager1 is manager2
    assert isinstance(manager1, ScoresCollectorManager)
