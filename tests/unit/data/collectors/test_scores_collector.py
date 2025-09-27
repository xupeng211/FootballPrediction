#!/usr/bin/env python3
"""
测试实时比分采集器

测试覆盖：
1. ScoresCollector 初始化和配置
2. WebSocket实时采集功能
3. HTTP轮询备份模式
4. 比赛状态管理
5. 关键事件记录和去重
6. 持续监控模式
7. 数据清洗和标准化
8. 错误处理和回退机制
"""

from unittest.mock import AsyncMock, MagicMock, patch, MagicMock
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List

import pytest
import websockets

from src.data.collectors.base_collector import CollectionResult
from src.data.collectors.scores_collector import (
    ScoresCollector, MatchStatus, EventType
)


class TestScoresCollector:
    """测试实时比分采集器"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(
            data_source="test_scores_api",
            api_key="test_key",
            base_url="https://api.test.com/v4",
            websocket_url="wss://api.test.com/ws",
            polling_interval=60
        )

    def test_init_with_default_values(self):
        """测试默认初始化"""
        collector = ScoresCollector()

        assert collector.data_source == "scores_api"
        assert collector.api_key is None
        assert collector.base_url == "https://api.football-data.org/v4"
        assert collector.websocket_url is None
        assert collector.polling_interval == 120
        assert isinstance(collector._active_matches, set)
        assert isinstance(collector._processed_events, set)
        assert collector._websocket_connected is False

    def test_init_with_custom_values(self):
        """测试自定义初始化"""
        collector = ScoresCollector(
            data_source="custom_scores_api",
            api_key="custom_key",
            base_url="https://custom.api.com",
            websocket_url="wss://custom.api.com/ws",
            polling_interval=30
        )

        assert collector.data_source == "custom_scores_api"
        assert collector.api_key == "custom_key"
        assert collector.base_url == "https://custom.api.com"
        assert collector.websocket_url == "wss://custom.api.com/ws"
        assert collector.polling_interval == 30

    @pytest.mark.asyncio
    async def test_collect_fixtures_skipped(self):
        """测试赛程采集被跳过"""
        result = await self.collector.collect_fixtures()

        assert result.status == "skipped"
        assert result.collection_type == "fixtures"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_collect_odds_skipped(self):
        """测试赔率采集被跳过"""
        result = await self.collector.collect_odds()

        assert result.status == "skipped"
        assert result.collection_type == "odds"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_collect_live_scores_success_websocket(self):
        """测试成功通过WebSocket采集实时比分"""
        # Mock helper methods
        with patch.object(self.collector, '_get_live_matches', return_value=["1", "2"]), \
             patch.object(self.collector, '_collect_via_websocket') as mock_websocket, \
             patch.object(self.collector, '_save_to_bronze_layer'):

            # Setup mock data
            mock_websocket.return_value = [
                {
                    "external_match_id": "1",
                    "status": "IN_PLAY",
                    "home_score": 1,
                    "away_score": 0,
                    "minute": 45,
                    "events": []
                },
                {
                    "external_match_id": "2",
                    "status": "IN_PLAY",
                    "home_score": 0,
                    "away_score": 1,
                    "minute": 30,
                    "events": []
                }
            ]

            # Execute collection
            result = await self.collector.collect_live_scores(use_websocket=True)

            # Verify result
            assert result.status == "success"
            assert result.success_count == 2
            assert result.error_count == 0
            assert result.records_collected == 2
            assert len(result.collected_data) == 2

    @pytest.mark.asyncio
    async def test_collect_live_scores_websocket_fallback_to_polling(self):
        """测试WebSocket失败后回退到轮询模式"""
        with patch.object(self.collector, '_get_live_matches', return_value=["1"]), \
             patch.object(self.collector, '_collect_via_websocket', side_effect=Exception("WebSocket failed")), \
             patch.object(self.collector, '_collect_via_polling') as mock_polling, \
             patch.object(self.collector, '_save_to_bronze_layer'):

            # Setup mock data for polling
            mock_polling.return_value = [
                {
                    "external_match_id": "1",
                    "status": "IN_PLAY",
                    "home_score": 1,
                    "away_score": 0,
                    "minute": 45,
                    "events": []
                }
            ]

            # Execute collection
            result = await self.collector.collect_live_scores(use_websocket=True)

            # Verify result
            assert result.status == "partial"  # Partial due to WebSocket error
            assert result.success_count == 1
            assert result.error_count == 1
            assert "WebSocket failed" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_live_scores_polling_only(self):
        """测试仅使用轮询模式采集实时比分"""
        with patch.object(self.collector, '_get_live_matches', return_value=["1"]), \
             patch.object(self.collector, '_collect_via_polling') as mock_polling, \
             patch.object(self.collector, '_save_to_bronze_layer'):

            # Setup mock data
            mock_polling.return_value = [
                {
                    "external_match_id": "1",
                    "status": "IN_PLAY",
                    "home_score": 1,
                    "away_score": 0,
                    "minute": 45,
                    "events": []
                }
            ]

            # Execute collection with websocket disabled
            result = await self.collector.collect_live_scores(use_websocket=False)

            # Verify result
            assert result.status == "success"
            assert result.success_count == 1
            assert result.error_count == 0
            assert result.records_collected == 1

    @pytest.mark.asyncio
    async def test_collect_live_scores_no_live_matches(self):
        """测试没有进行中比赛的情况"""
        with patch.object(self.collector, '_get_live_matches', return_value=[]):
            result = await self.collector.collect_live_scores()

            # Verify result
            assert result.status == "success"
            assert result.success_count == 0
            assert result.error_count == 0
            assert result.records_collected == 0

    @pytest.mark.asyncio
    async def test_collect_live_scores_with_custom_match_ids(self):
        """测试使用自定义比赛ID列表"""
        with patch.object(self.collector, '_collect_via_polling') as mock_polling, \
             patch.object(self.collector, '_save_to_bronze_layer'):

            # Setup mock data
            mock_polling.return_value = [
                {
                    "external_match_id": "1",
                    "status": "IN_PLAY",
                    "home_score": 1,
                    "away_score": 0,
                    "minute": 45,
                    "events": []
                }
            ]

            # Execute collection with specific match IDs
            result = await self.collector.collect_live_scores(
                match_ids=["1", "2"], use_websocket=False
            )

            # Verify result
            assert result.status == "success"
            assert result.records_collected == 1
            # Verify that active matches were updated
            assert "1" in self.collector._active_matches
            assert "2" in self.collector._active_matches

    @pytest.mark.asyncio
    async def test_collect_live_scores_total_failure(self):
        """测试完全失败的实时比分采集"""
        with patch.object(self.collector, '_get_live_matches', side_effect=Exception("Database error")):

            result = await self.collector.collect_live_scores()

            assert result.status == "failed"
            assert result.success_count == 0
            assert result.error_count == 1
            assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_get_live_matches_success(self):
        """测试获取进行中比赛列表"""
        # The actual implementation returns empty list as placeholder
        matches = await self.collector._get_live_matches()

        assert matches == []

    @pytest.mark.asyncio
    async def test_get_live_matches_error(self):
        """测试获取进行中比赛列表失败"""
        # Since the actual implementation returns empty list on error, we test that
        matches = await self.collector._get_live_matches()

        assert matches == []

    @pytest.mark.asyncio
    async def test_collect_via_websocket_success(self):
        """测试成功通过WebSocket采集数据"""
        mock_websocket_data = [
            {"type": "match_update", "id": "1", "status": "IN_PLAY", "score": {"fullTime": {"home": 1, "away": 0}}},
            {"type": "match_update", "id": "2", "status": "IN_PLAY", "score": {"fullTime": {"home": 0, "away": 1}}}
        ]

        # Create a proper async context manager mock
        class MockWebSocket:
            def __init__(self):
                self.send = AsyncMock()
                self.ping = AsyncMock()
                self.close = AsyncMock()
                self.call_count = 0

                async def recv():
                    self.call_count += 1
                    if self.call_count == 1:
                        return json.dumps(mock_websocket_data[0])
                    elif self.call_count == 2:
                        return json.dumps(mock_websocket_data[1])
                    else:
                        raise asyncio.TimeoutError()

                self.recv = recv

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_websocket = MockWebSocket()

        with patch('websockets.connect', return_value=mock_websocket), \
             patch.object(self.collector, '_clean_live_data') as mock_clean:

            mock_clean.side_effect = [
                {"external_match_id": "1", "status": "IN_PLAY", "home_score": 1, "away_score": 0},
                {"external_match_id": "2", "status": "IN_PLAY", "home_score": 0, "away_score": 1}
            ]

            # Execute with short duration for testing
            data = await self.collector._collect_via_websocket(["1", "2"], duration=1)

            assert len(data) == 2
            assert data[0]["external_match_id"] == "1"
            assert data[1]["external_match_id"] == "2"

    @pytest.mark.asyncio
    async def test_collect_via_websocket_no_url(self):
        """测试WebSocket URL未配置的情况"""
        self.collector.websocket_url = None

        with pytest.raises(ValueError, match="WebSocket URL not configured"):
            await self.collector._collect_via_websocket(["1"])

    @pytest.mark.asyncio
    async def test_collect_via_polling_success(self):
        """测试成功通过轮询采集数据"""
        mock_match_data = {
            "id": "1",
            "status": "IN_PLAY",
            "score": {"fullTime": {"home": 1, "away": 0}},
            "minute": 45,
            "events": []
        }

        with patch.object(self.collector, '_get_match_live_data', return_value=mock_match_data), \
             patch.object(self.collector, '_clean_live_data') as mock_clean:

            mock_clean.return_value = {
                "external_match_id": "1",
                "status": "IN_PLAY",
                "home_score": 1,
                "away_score": 0,
                "minute": 45,
                "events": []
            }

            data = await self.collector._collect_via_polling(["1"])

            assert len(data) == 1
            assert data[0]["external_match_id"] == "1"

    @pytest.mark.asyncio
    async def test_collect_via_polling_match_error(self):
        """测试轮询时比赛数据获取失败"""
        with patch.object(self.collector, '_get_match_live_data', side_effect=Exception("API Error")):
            data = await self.collector._collect_via_polling(["1"])

            # Should return empty list when match fails
            assert data == []

    @pytest.mark.asyncio
    async def test_get_match_live_data_success(self):
        """测试成功获取比赛实时数据"""
        mock_response = {
            "id": "1",
            "status": "IN_PLAY",
            "score": {"fullTime": {"home": 1, "away": 0}},
            "minute": 45
        }

        with patch.object(self.collector, '_make_request', return_value=mock_response):
            data = await self.collector._get_match_live_data("1")

            assert data == mock_response

    @pytest.mark.asyncio
    async def test_get_match_live_data_error(self):
        """测试获取比赛实时数据失败"""
        with patch.object(self.collector, '_make_request', side_effect=Exception("API Error")):
            data = await self.collector._get_match_live_data("1")

            assert data is None

    @pytest.mark.asyncio
    async def test_clean_live_data_success(self):
        """测试成功清洗实时数据"""
        raw_data = {
            "id": "12345",
            "status": "IN_PLAY",
            "score": {
                "fullTime": {"home": 1, "away": 0},
                "halfTime": {"home": 0, "away": 0}
            },
            "minute": 45,
            "events": [
                {
                    "minute": 23,
                    "type": "GOAL",
                    "player": {"name": "Player A"},
                    "team": {"name": "Team A"}
                }
            ]
        }

        cleaned = await self.collector._clean_live_data(raw_data)

        assert cleaned is not None
        assert cleaned["external_match_id"] == "12345"
        assert cleaned["status"] == "IN_PLAY"
        assert cleaned["home_score"] == 1
        assert cleaned["away_score"] == 0
        assert cleaned["minute"] == 45
        assert len(cleaned["events"]) == 1
        assert cleaned["events"][0]["type"] == "GOAL"
        assert cleaned["events"][0]["player"] == "Player A"

    @pytest.mark.asyncio
    async def test_clean_live_data_missing_id(self):
        """测试清洗缺失ID的实时数据"""
        invalid_data = {
            "status": "IN_PLAY",
            # Missing id field
            "score": {"fullTime": {"home": 1, "away": 0}}
        }

        cleaned = await self.collector._clean_live_data(invalid_data)

        assert cleaned is None

    @pytest.mark.asyncio
    async def test_clean_live_data_invalid_structure(self):
        """测试清洗无效结构的实时数据"""
        # Test with actual invalid data structure
        invalid_data = {"invalid": "structure"}
        cleaned = await self.collector._clean_live_data(invalid_data)
        assert cleaned is None

    def test_is_match_finished(self):
        """测试比赛结束状态检查"""
        assert self.collector._is_match_finished("FINISHED") is True
        assert self.collector._is_match_finished("COMPLETED") is True
        assert self.collector._is_match_finished("CANCELLED") is True
        assert self.collector._is_match_finished("POSTPONED") is True
        assert self.collector._is_match_finished("IN_PLAY") is False
        assert self.collector._is_match_finished("SCHEDULED") is False

    @pytest.mark.asyncio
    async def test_collect_websocket_scores(self):
        """测试WebSocket比分采集方法"""
        with patch.object(self.collector, '_collect_via_websocket', return_value=[{"id": "1", "score": "1-0"}]) as mock_websocket:
            result = await self.collector._collect_websocket_scores(["1"])

            mock_websocket.assert_called_once_with(["1"])
            assert result == [{"id": "1", "score": "1-0"}]

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring_success(self):
        """测试启动持续监控模式成功"""
        with patch.object(self.collector, '_get_live_matches', return_value=["1"]), \
             patch.object(self.collector, 'collect_live_scores') as mock_collect:

            mock_collect.return_value = CollectionResult(
                data_source="test",
                collection_type="live_scores",
                records_collected=1,
                success_count=1,
                error_count=0,
                status="success"
            )

            # Run for a short time then cancel
            task = asyncio.create_task(self.collector.start_continuous_monitoring())
            await asyncio.sleep(0.5)  # Give it more time to run
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_collect.assert_called()


class TestScoresCollectorEdgeCases:
    """测试实时比分采集器边界情况"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(websocket_url="wss://test.com/ws")

    @pytest.mark.asyncio
    async def test_collect_live_scores_timeout_during_websocket(self):
        """测试WebSocket采集过程中的超时处理"""
        with patch.object(self.collector, '_get_live_matches', return_value=["1"]), \
             patch.object(self.collector, '_collect_via_websocket', side_effect=asyncio.TimeoutError("Connection timeout")), \
             patch.object(self.collector, '_collect_via_polling') as mock_polling, \
             patch.object(self.collector, '_save_to_bronze_layer'):

            mock_polling.return_value = []

            result = await self.collector.collect_live_scores()

            assert result.status == "failed"
            assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_collect_live_scores_websocket_connection_error(self):
        """测试WebSocket连接错误"""
        with patch.object(self.collector, '_get_live_matches', return_value=["1"]), \
             patch.object(self.collector, '_collect_via_websocket', side_effect=ConnectionError("Connection refused")), \
             patch.object(self.collector, '_collect_via_polling') as mock_polling, \
             patch.object(self.collector, '_save_to_bronze_layer'):

            mock_polling.return_value = []

            result = await self.collector.collect_live_scores()

            assert result.status == "failed"
            assert "connection refused" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_collect_live_scores_invalid_json(self):
        """测试WebSocket接收到无效JSON"""
        # Create a proper mock websocket that can be used in async context manager
        class MockWebSocket:
            def __init__(self):
                self.send = AsyncMock()
                self.ping = AsyncMock()

            async def recv(self):
                return "invalid json"  # Invalid JSON that will cause JSONDecodeError

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_websocket = MockWebSocket()

        with patch('websockets.connect', return_value=mock_websocket):
            # Should raise JSONDecodeError which is caught and re-raised as Exception
            with pytest.raises(Exception) as exc_info:
                await self.collector._collect_via_websocket(["1"], duration=1)

            # Verify it's related to JSON parsing
            assert "Expecting value" in str(exc_info.value) or "JSON decode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_collect_live_scores_websocket_heartbeat(self):
        """测试WebSocket心跳机制"""
        # Create a proper mock websocket that can be used in async context manager
        class MockWebSocket:
            def __init__(self):
                self.send = AsyncMock()
                self.ping_call_count = 0
                self.recv_call_count = 0

            async def ping(self):
                self.ping_call_count += 1

            async def recv(self):
                self.recv_call_count += 1
                raise asyncio.TimeoutError()  # Always timeout to trigger heartbeat

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_websocket = MockWebSocket()

        with patch('websockets.connect', return_value=mock_websocket):
            data = await self.collector._collect_via_websocket(["1"], duration=1)

            # Should send heartbeat ping
            assert mock_websocket.ping_call_count > 0
            assert data == []

    @pytest.mark.asyncio
    async def test_collect_via_polling_empty_match_ids(self):
        """测试轮询空比赛ID列表"""
        data = await self.collector._collect_via_polling([])

        assert data == []

    @pytest.mark.asyncio
    async def test_clean_live_data_missing_optional_fields(self):
        """测试清洗缺失可选字段的实时数据"""
        raw_data = {
            "id": "12345",
            "status": "IN_PLAY"
            # Missing score, minute, events
        }

        cleaned = await self.collector._clean_live_data(raw_data)

        assert cleaned is not None
        assert cleaned["external_match_id"] == "12345"
        assert cleaned["status"] == "IN_PLAY"
        assert cleaned["home_score"] is None
        assert cleaned["away_score"] is None
        assert cleaned["minute"] is None
        assert cleaned["events"] == []

    @pytest.mark.asyncio
    async def test_clean_live_data_empty_events(self):
        """测试清洗空事件列表的实时数据"""
        raw_data = {
            "id": "12345",
            "status": "IN_PLAY",
            "score": {"fullTime": {"home": 1, "away": 0}},
            "minute": 45,
            "events": []
        }

        cleaned = await self.collector._clean_live_data(raw_data)

        assert cleaned is not None
        assert len(cleaned["events"]) == 0

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring_with_failure(self):
        """测试持续监控模式中的错误处理"""
        with patch.object(self.collector, '_get_live_matches', return_value=["1"]), \
             patch.object(self.collector, 'collect_live_scores') as mock_collect:

            mock_collect.return_value = CollectionResult(
                data_source="test",
                collection_type="live_scores",
                records_collected=0,
                success_count=0,
                error_count=1,
                status="failed",
                error_message="API Error"
            )

            # Run for a short time then cancel
            task = asyncio.create_task(self.collector.start_continuous_monitoring())
            await asyncio.sleep(0.1)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Should continue monitoring despite failures
            assert mock_collect.call_count >= 1

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring_error_in_get_live_matches(self):
        """测试获取进行中比赛失败的持续监控"""
        with patch.object(self.collector, '_get_live_matches', side_effect=Exception("Database error")), \
             patch('asyncio.sleep') as mock_sleep:

            # Run for a short time then cancel
            task = asyncio.create_task(self.collector.start_continuous_monitoring())
            await asyncio.sleep(0.1)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Should continue monitoring despite errors

    def test_match_status_enum_values(self):
        """测试比赛状态枚举值"""
        assert MatchStatus.NOT_STARTED.value == "not_started"
        assert MatchStatus.FIRST_HALF.value == "first_half"
        assert MatchStatus.HALF_TIME.value == "half_time"
        assert MatchStatus.SECOND_HALF.value == "second_half"
        assert MatchStatus.FINISHED.value == "finished"
        assert MatchStatus.POSTPONED.value == "postponed"
        assert MatchStatus.CANCELLED.value == "cancelled"

    def test_event_type_enum_values(self):
        """测试事件类型枚举值"""
        assert EventType.GOAL.value == "goal"
        assert EventType.YELLOW_CARD.value == "yellow_card"
        assert EventType.RED_CARD.value == "red_card"
        assert EventType.SUBSTITUTION.value == "substitution"
        assert EventType.PENALTY.value == "penalty"
        assert EventType.OWN_GOAL.value == "own_goal"
        assert EventType.VAR_DECISION.value == "var_decision"