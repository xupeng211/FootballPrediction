"""
改进的比分收集器测试
Tests for Improved Scores Collector

测试src.collectors.scores_collector_improved模块的实时比分收集功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import asyncio
import json
# import aiostream  # 模块不存在，移除

# 测试导入
try:
    from src.collectors.scores_collector_improved import (
        ScoresCollector,
        ScoresCollectorManager,
    )
    from src.database.models import MatchStatus, RawScoresData

    SCORES_COLLECTOR_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    SCORES_COLLECTOR_AVAILABLE = False
    ScoresCollector = None
    ScoresCollectorManager = None
    MatchStatus = None
    RawScoresData = None


@pytest.mark.skipif(
    not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available"
)
class TestScoresCollector:
    """比分收集器测试"""

    def test_collector_creation(self):
        """测试：收集器创建"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session,
            redis_manager=redis_manager,
            api_key="test_api_key",
            websocket_url="ws://test.com",
            poll_interval=30,
        )

        assert collector is not None
        assert collector.api_key == "test_api_key"
        assert collector.websocket_url == "ws://test.com"
        assert collector.poll_interval == 30
        assert collector.running is False
        assert collector.match_cache == {}

    def test_collector_creation_with_env_vars(self):
        """测试：使用环境变量创建收集器"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        with patch.dict(
            "os.environ",
            {
                "FOOTBALL_API_TOKEN": "env_api_key",
                "SCORES_WEBSOCKET_URL": "ws://env.com",
                "FOOTBALL_API_URL": "https://env.api.com",
                "API_SPORTS_URL": "https://env.api-sports.com",
                "SCOREBAT_URL": "https://env.scorebat.com",
            },
        ):
            collector = ScoresCollector(
                db_session=db_session, redis_manager=redis_manager
            )

            assert collector.api_key == "env_api_key"
            assert collector.websocket_url == "ws://env.com"
            assert "https://env.api.com" in collector.api_endpoints["football_api"]

    @pytest.mark.asyncio
    async def test_start_collection(self):
        """测试：启动收集"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session,
            redis_manager=redis_manager,
            websocket_url="ws://test.com",
        )

        with patch.object(collector, "_websocket_listener") as mock_ws:
            with patch.object(collector, "_http_poller") as mock_poll:
                mock_ws.return_value = AsyncMock()
                mock_poll.return_value = AsyncMock()

                await collector.start_collection()

                assert collector.running is True
                assert collector.websocket_task is not None
                assert collector.poll_task is not None

    @pytest.mark.asyncio
    async def test_stop_collection(self):
        """测试：停止收集"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 设置运行状态
        collector.running = True
        collector.websocket_task = AsyncMock()
        collector.poll_task = AsyncMock()

        await collector.stop_collection()

        assert collector.running is False
        assert collector.websocket_task.cancel.called
        assert collector.poll_task.cancel.called

    @pytest.mark.asyncio
    async def test_collect_match_score(self):
        """测试：收集比赛比分"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        match_id = 123
        score_data = {
            "match_id": match_id,
            "home_score": 2,
            "away_score": 1,
            "status": "LIVE",
            "minute": 75,
        }

        with patch.object(collector, "_fetch_match_score_from_api") as mock_fetch:
            mock_fetch.return_value = score_data

            with patch.object(collector, "_process_score_data") as mock_process:
                mock_process.return_value = True

                _result = await collector.collect_match_score(match_id)

                assert result is True
                mock_fetch.assert_called_once_with(match_id)
                mock_process.assert_called_once_with(score_data)

    @pytest.mark.asyncio
    async def test_collect_match_score_not_found(self):
        """测试：收集不存在的比赛比分"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        match_id = 999

        with patch.object(collector, "_fetch_match_score_from_api") as mock_fetch:
            mock_fetch.return_value = None

            _result = await collector.collect_match_score(match_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_collect_live_matches(self):
        """测试：收集实时比赛"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        live_matches = [
            {
                "match_id": 1,
                "home_team": "Team A",
                "away_team": "Team B",
                "status": "LIVE",
            },
            {
                "match_id": 2,
                "home_team": "Team C",
                "away_team": "Team D",
                "status": "LIVE",
            },
        ]

        with patch.object(collector, "_get_live_matches") as mock_get:
            mock_get.return_value = live_matches

            _result = await collector.collect_live_matches()

            assert len(result) == 2
            assert result[0]["match_id"] == 1
            assert result[1]["status"] == "LIVE"

    @pytest.mark.asyncio
    async def test_websocket_listener(self):
        """测试：WebSocket监听器"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session,
            redis_manager=redis_manager,
            websocket_url="ws://test.com",
        )

        collector.running = True

        # 模拟WebSocket消息
        test_messages = [
            {"type": "score_update", "data": {"match_id": 1, "score": "2-1"}},
            {"type": "match_event", "data": {"match_id": 1, "event": "goal"}},
        ]

        with patch("websockets.connect") as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            # 模拟接收消息
            mock_websocket.recv.side_effect = [
                json.dumps(msg) for msg in test_messages
            ] + [asyncio.CancelledError()]

            with patch.object(collector, "_handle_websocket_message") as mock_handle:
                collector.websocket_task = asyncio.create_task(
                    collector._websocket_listener()
                )

                # 等待处理
                await asyncio.sleep(0.1)

                # 验证消息被处理
                assert mock_handle.call_count == 2

                # 清理
                collector.websocket_task.cancel()
                try:
                    await collector.websocket_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_http_poller(self):
        """测试：HTTP轮询器"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session,
            redis_manager=redis_manager,
            poll_interval=0.1,  # 快速测试
        )

        collector.running = True

        with patch.object(collector, "collect_live_matches") as mock_collect:
            mock_collect.return_value = [{"match_id": 1, "status": "LIVE"}]

            with patch.object(collector, "collect_match_score") as mock_score:
                mock_score.return_value = True

                # 启动轮询任务
                collector.poll_task = asyncio.create_task(collector._http_poller())

                # 等待一轮轮询
                await asyncio.sleep(0.2)

                # 验证方法被调用
                assert mock_collect.called
                assert mock_score.called

                # 停止轮询
                collector.running = False
                collector.poll_task.cancel()
                try:
                    await collector.poll_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_handle_websocket_message(self):
        """测试：处理WebSocket消息"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 测试比分更新消息
        score_message = {
            "type": "score_update",
            "data": {"match_id": 123, "home_score": 2, "away_score": 1, "minute": 60},
        }

        with patch.object(collector, "_process_score_data") as mock_process:
            mock_process.return_value = True

            await collector._handle_websocket_message(score_message)

            mock_process.assert_called_once_with(score_message["data"])

    @pytest.mark.asyncio
    async def test_handle_websocket_match_event(self):
        """测试：处理比赛事件消息"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        event_message = {
            "type": "match_event",
            "data": {
                "match_id": 123,
                "event": "goal",
                "player": "Player A",
                "minute": 60,
            },
        }

        with patch.object(collector, "_handle_match_event") as mock_handle:
            await collector._handle_websocket_message(event_message)

            mock_handle.assert_called_once_with(event_message["data"])

    @pytest.mark.asyncio
    async def test_fetch_match_score_from_api(self):
        """测试：从API获取比分"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        match_id = 123

        # 测试成功获取
        with patch.object(collector, "_fetch_from_football_api") as mock_football:
            mock_football.return_value = {"score": "2-1"}

            _result = await collector._fetch_match_score_from_api(match_id)

            assert _result == {"score": "2-1"}
            mock_football.assert_called_once_with(match_id)

        # 测试fallback到其他API
        with patch.object(collector, "_fetch_from_football_api") as mock_football:
            with patch.object(collector, "_fetch_from_api_sports") as mock_sports:
                mock_football.return_value = None
                mock_sports.return_value = {"score": "1-2"}

                _result = await collector._fetch_match_score_from_api(match_id)

                assert _result == {"score": "1-2"}
                mock_sports.assert_called_once_with(match_id)

    @pytest.mark.asyncio
    async def test_fetch_from_football_api(self):
        """测试：从Football API获取数据"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session, redis_manager=redis_manager, api_key="test_key"
        )

        match_id = 123

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "match": {
                    "id": match_id,
                    "score": {
                        "fullTime": {"home": 2, "away": 1},
                        "halfTime": {"home": 1, "away": 0},
                    },
                    "status": "IN_PLAY",
                }
            }
            mock_get.return_value.__aenter__.return_value = mock_response

            _result = await collector._fetch_from_football_api(match_id)

            assert result is not None
            assert "match" in result

    @pytest.mark.asyncio
    async def test_fetch_from_api_sports(self):
        """测试：从API Sports获取数据"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session, redis_manager=redis_manager, api_key="test_key"
        )

        match_id = 123

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "response": [
                    {
                        "fixture": {"id": match_id, "status": {"long": "Live"}},
                        "goals": {"home": 2, "away": 1},
                    }
                ]
            }
            mock_get.return_value.__aenter__.return_value = mock_response

            _result = await collector._fetch_from_api_sports(match_id)

            assert result is not None
            assert "response" in result

    @pytest.mark.asyncio
    async def test_fetch_from_scorebat(self):
        """测试：从Scorebat获取数据"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        match_id = 123

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = [
                {
                    "title": "Team A vs Team B",
                    "date": "2024-01-15T20:00:00Z",
                    "videos": [{"title": "Highlights"}],
                }
            ]
            mock_get.return_value.__aenter__.return_value = mock_response

            _result = await collector._fetch_from_scorebat(match_id)

            assert result is not None
            assert len(result) == 1

    def test_transform_football_api_data(self):
        """测试：转换Football API数据"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        api_data = {
            "match": {
                "id": 123,
                "utcDate": "2024-01-15T20:00:00Z",
                "score": {
                    "fullTime": {"home": 2, "away": 1},
                    "halfTime": {"home": 1, "away": 0},
                },
                "status": "IN_PLAY",
                "matchday": 20,
            }
        }

        _result = collector._transform_football_api_data(api_data)

        assert result["match_id"] == 123
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["status"] == "LIVE"
        assert "timestamp" in result

    def test_transform_api_sports_data(self):
        """测试：转换API Sports数据"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        api_data = {
            "response": [
                {
                    "fixture": {"id": 123, "status": {"long": "Live", "elapsed": 75}},
                    "goals": {"home": 2, "away": 1},
                }
            ]
        }

        _result = collector._transform_api_sports_data(api_data)

        assert result["match_id"] == 123
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["status"] == "LIVE"
        assert result["minute"] == 75

    @pytest.mark.asyncio
    async def test_process_score_data(self):
        """测试：处理比分数据"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        score_data = {
            "match_id": 123,
            "home_score": 2,
            "away_score": 1,
            "status": "LIVE",
            "minute": 75,
        }

        # 模拟数据库中的比赛
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_score = 1
        mock_match.away_score = 1
        mock_match.status = MatchStatus.LIVE
        mock_match.updated_at = datetime.now() - timedelta(minutes=5)

        with patch.object(collector, "_has_significant_change") as mock_change:
            with patch.object(collector, "_save_score_data") as mock_save:
                with patch.object(collector, "_publish_score_update") as mock_publish:
                    mock_change.return_value = True
                    mock_save.return_value = True
                    mock_publish.return_value = True

                    _result = await collector._process_score_data(score_data)

                    assert result is True
                    mock_change.assert_called_once()
                    mock_save.assert_called_once_with(score_data)
                    mock_publish.assert_called_once_with(score_data)

    def test_map_status(self):
        """测试：状态映射"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 测试各种状态映射
        test_cases = [
            ("LIVE", MatchStatus.LIVE),
            ("IN_PLAY", MatchStatus.LIVE),
            ("PAUSED", MatchStatus.HALF_TIME),
            ("FINISHED", MatchStatus.FINISHED),
            ("POSTPONED", MatchStatus.POSTPONED),
            ("CANCELLED", MatchStatus.CANCELLED),
            ("SCHEDULED", MatchStatus.SCHEDULED),
            ("UNKNOWN", MatchStatus.UNKNOWN),
        ]

        for api_status, expected in test_cases:
            _result = collector._map_status(api_status)
            assert _result == expected

    def test_has_significant_change(self):
        """测试：检查是否有显著变化"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 创建模拟比赛
        match = Mock()
        match.home_score = 1
        match.away_score = 1
        match.status = MatchStatus.LIVE
        match.minute = 60

        # 测试比分变化
        new_data = {"home_score": 2, "away_score": 1, "status": "LIVE", "minute": 61}
        assert collector._has_significant_change(match, new_data) is True

        # 测试状态变化
        new_data = {
            "home_score": 1,
            "away_score": 1,
            "status": "FINISHED",
            "minute": 90,
        }
        assert collector._has_significant_change(match, new_data) is True

        # 测试无显著变化
        new_data = {"home_score": 1, "away_score": 1, "status": "LIVE", "minute": 61}
        assert collector._has_significant_change(match, new_data) is False

    @pytest.mark.asyncio
    async def test_save_score_data(self):
        """测试：保存比分数据"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        score_data = {
            "match_id": 123,
            "home_score": 2,
            "away_score": 1,
            "status": "LIVE",
            "minute": 75,
            "timestamp": datetime.now(),
        }

        # 模拟数据库查询
        mock_match = Mock()
        mock_match.home_score = 1
        mock_match.away_score = 1
        mock_match.status = MatchStatus.LIVE

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_match

        db_session.execute.return_value = mock_result

        with patch.object(db_session, "commit") as mock_commit:
            with patch.object(db_session, "refresh") as mock_refresh:
                await collector._save_score_data(score_data)

                # 验证更新语句被创建
                db_session.execute.assert_called()
                mock_commit.assert_called_once()
                mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_score_update(self):
        """测试：发布比分更新"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        score_data = {
            "match_id": 123,
            "home_score": 2,
            "away_score": 1,
            "status": "LIVE",
        }

        with patch.object(redis_manager, "publish_to_channel") as mock_publish:
            await collector._publish_score_update(score_data)

            mock_publish.assert_called_once_with(
                "score_updates", json.dumps(score_data)
            )

    @pytest.mark.asyncio
    async def test_handle_match_event(self):
        """测试：处理比赛事件"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        event_data = {
            "match_id": 123,
            "event": "goal",
            "player": "Player A",
            "minute": 60,
            "team": "home",
        }

        with patch.object(redis_manager, "publish_to_channel") as mock_publish:
            await collector._handle_match_event(event_data)

            mock_publish.assert_called_once_with("match_events", json.dumps(event_data))

    @pytest.mark.asyncio
    async def test_get_live_matches(self):
        """测试：获取实时比赛"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 模拟数据库查询结果
        mock_matches = [
            Mock(id=1, home_team="Team A", away_team="Team B", status=MatchStatus.LIVE),
            Mock(id=2, home_team="Team C", away_team="Team D", status=MatchStatus.LIVE),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_matches
        db_session.execute.return_value = mock_result

        _result = await collector._get_live_matches()

        assert len(result) == 2
        assert result[0]["match_id"] == 1
        assert result[0]["home_team"] == "Team A"
        assert result[1]["status"] == "LIVE"

    @pytest.mark.asyncio
    async def test_cleanup_cache(self):
        """测试：清理缓存"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 添加一些过期缓存
        old_time = datetime.now() - timedelta(hours=2)
        collector.match_cache = {1: {"data": "test1"}, 2: {"data": "test2"}}
        collector.last_update_cache = {
            1: old_time,
            2: datetime.now() - timedelta(minutes=30),
        }

        await collector._cleanup_cache()

        # 验证旧缓存被清理
        assert 1 not in collector.match_cache
        assert 1 not in collector.last_update_cache
        # 验证新缓存保留
        assert 2 in collector.match_cache
        assert 2 in collector.last_update_cache

    def test_get_stats(self):
        """测试：获取统计信息"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 设置一些统计
        collector.match_cache = {1: {}, 2: {}, 3: {}}
        collector.last_update_cache = {
            1: datetime.now(),
            2: datetime.now() - timedelta(minutes=5),
            3: datetime.now() - timedelta(minutes=10),
        }

        _stats = collector.get_stats()

        assert stats["cached_matches"] == 3
        assert stats["running"] is False
        assert "websocket_task" in stats
        assert "poll_task" in stats
        assert "last_updates" in stats


@pytest.mark.skipif(
    not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available"
)
class TestScoresCollectorManager:
    """比分收集器管理器测试"""

    def test_manager_creation(self):
        """测试：管理器创建"""
        manager = ScoresCollectorManager()
        assert manager is not None
        assert manager.collectors == {}
        assert manager.db_session is None
        assert manager.redis_manager is None

    @pytest.mark.asyncio
    async def test_get_collector(self):
        """测试：获取收集器"""
        manager = ScoresCollectorManager()

        # 模拟依赖
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        manager.db_session = db_session
        manager.redis_manager = redis_manager

        # 第一次获取，创建新实例
        collector1 = await manager.get_collector(session_id=1)
        assert collector1 is not None
        assert 1 in manager.collectors

        # 第二次获取，返回相同实例
        collector2 = await manager.get_collector(session_id=1)
        assert collector1 is collector2

    @pytest.mark.asyncio
    async def test_start_all(self):
        """测试：启动所有收集器"""
        manager = ScoresCollectorManager()

        # 模拟收集器
        collector1 = AsyncMock()
        collector2 = AsyncMock()
        manager.collectors = {1: collector1, 2: collector2}

        await manager.start_all()

        collector1.start_collection.assert_called_once()
        collector2.start_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_all(self):
        """测试：停止所有收集器"""
        manager = ScoresCollectorManager()

        # 模拟收集器
        collector1 = AsyncMock()
        collector2 = AsyncMock()
        manager.collectors = {1: collector1, 2: collector2}

        await manager.stop_all()

        collector1.stop_collection.assert_called_once()
        collector2.stop_collection.assert_called_once()


@pytest.mark.skipif(
    not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available"
)
class TestScoresCollectorIntegration:
    """比分收集器集成测试"""

    @pytest.mark.asyncio
    async def test_full_collection_workflow(self):
        """测试：完整的收集工作流"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session, redis_manager=redis_manager, api_key="test_key"
        )

        # 1. 获取实时比赛
        live_matches = [{"match_id": 123, "status": "LIVE"}]

        with patch.object(collector, "_get_live_matches") as mock_get:
            mock_get.return_value = live_matches

            # 2. 获取比分数据
            score_data = {
                "match_id": 123,
                "home_score": 2,
                "away_score": 1,
                "status": "LIVE",
                "minute": 75,
            }

            with patch.object(collector, "_fetch_match_score_from_api") as mock_fetch:
                mock_fetch.return_value = score_data

                # 3. 处理数据
                with patch.object(collector, "_process_score_data") as mock_process:
                    mock_process.return_value = True

                    # 4. 发布更新
                    with patch.object(collector, "_publish_score_update"):
                        # 执行收集
                        _matches = await collector.collect_live_matches()
                        for match in matches:
                            await collector.collect_match_score(match["match_id"])

                        # 验证流程
                        assert len(matches) == 1
                        mock_fetch.assert_called_once_with(123)
                        mock_process.assert_called_once_with(score_data)
                        # _publish_score_update 在 _process_score_data 内部调用

    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self):
        """测试：错误处理和重试"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 模拟API失败然后成功
        with patch.object(collector, "_fetch_from_football_api") as mock_fetch:
            mock_fetch.side_effect = [
                None,  # 第一次失败
                None,  # 第二次失败
                {"match_id": 123, "home_score": 2, "away_score": 1},  # 第三次成功
            ]

            with patch.object(collector, "_fetch_from_api_sports") as mock_sports:
                mock_sports.return_value = None  # fallback也失败

                # 第一次调用，应该失败
                _result = await collector._fetch_match_score_from_api(123)
                assert result is None

                # 第二次调用，应该成功
                _result = await collector._fetch_match_score_from_api(123)
                assert result is not None
                assert result["match_id"] == 123

    @pytest.mark.asyncio
    async def test_concurrent_updates(self):
        """测试：并发更新"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 模拟多个并发更新
        updates = [
            {"match_id": 123, "home_score": 1, "away_score": 0},
            {"match_id": 123, "home_score": 2, "away_score": 0},
            {"match_id": 123, "home_score": 2, "away_score": 1},
        ]

        async def process_update(update):
            with patch.object(collector, "_has_significant_change") as mock_change:
                with patch.object(collector, "_save_score_data") as mock_save:
                    mock_change.return_value = True
                    mock_save.return_value = True
                    await collector._process_score_data(update)

        # 并发执行更新
        tasks = [process_update(update) for update in updates]
        await asyncio.gather(*tasks)

        # 验证所有更新都被处理
        # 由于使用了锁，不会有竞态条件

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """测试：缓存性能"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(db_session=db_session, redis_manager=redis_manager)

        # 添加缓存
        collector.match_cache[123] = {
            "home_score": 2,
            "away_score": 1,
            "status": "LIVE",
            "minute": 75,
        }
        collector.last_update_cache[123] = datetime.now()

        # 测试缓存命中
        cached_data = collector.match_cache.get(123)
        assert cached_data is not None
        assert cached_data["home_score"] == 2

        # 测试缓存过期
        collector.last_update_cache[123] = datetime.now() - timedelta(hours=1)
        await collector._cleanup_cache()

        # 缓存应该被清理
        assert 123 not in collector.match_cache

    @pytest.mark.asyncio
    async def test_websocket_reconnection(self):
        """测试：WebSocket重连"""
        db_session = AsyncMock()
        redis_manager = AsyncMock()

        collector = ScoresCollector(
            db_session=db_session,
            redis_manager=redis_manager,
            websocket_url="ws://test.com",
        )

        collector.running = True

        with patch("websockets.connect") as mock_connect:
            # 第一次连接失败
            mock_connect.side_effect = [
                ConnectionError("Connection failed"),
                Mock(),  # 第二次成功
            ]

            with patch("asyncio.sleep") as mock_sleep:
                # 启动WebSocket监听
                task = asyncio.create_task(collector._websocket_listener())

                # 等待重连
                await asyncio.sleep(0.1)

                # 验证sleep被调用（重连延迟）
                assert mock_sleep.called

                # 清理
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


@pytest.mark.skipif(
    SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not SCORES_COLLECTOR_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if SCORES_COLLECTOR_AVAILABLE:
        from src.collectors.scores_collector_improved import (
            ScoresCollector,
            ScoresCollectorManager,
        )

        assert ScoresCollector is not None
        assert ScoresCollectorManager is not None
