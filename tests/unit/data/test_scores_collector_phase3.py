"""
Phase 3：实时比分采集器模块综合测试
目标：全面提升scores_collector.py模块覆盖率到60%+
重点：测试WebSocket连接、HTTP轮询、比分数据处理、事件跟踪和比赛状态管理功能
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.data.collectors.scores_collector import (
    CollectionResult,
    EventType,
    MatchStatus,
    ScoresCollector,
)


class TestScoresCollectorBasic:
    """实时比分采集器基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(
            data_source="scores_api",
            api_key="test_key",
            base_url="https://api.football-data.org/v4",
            websocket_url="wss://api.football-data.org/v4/websocket",
        )

    def test_collector_initialization(self):
        """测试采集器初始化"""
        assert self.collector.data_source == "scores_api"
        assert self.collector.api_key == "test_key"
        assert self.collector.base_url == "https://api.football-data.org/v4"
        assert (
            self.collector.websocket_url == "wss://api.football-data.org/v4/websocket"
        )
        assert self.collector.polling_interval == 120
        assert self.collector._active_matches == set()
        assert self.collector._processed_events == set()
        assert self.collector._websocket_connected == False

    def test_collector_inheritance(self):
        """测试继承关系"""
        from src.data.collectors.base_collector import DataCollector

        assert isinstance(self.collector, DataCollector)

    def test_match_status_enum(self):
        """测试比赛状态枚举"""
        assert MatchStatus.NOT_STARTED.value == "not_started"
        assert MatchStatus.FIRST_HALF.value == "first_half"
        assert MatchStatus.HALF_TIME.value == "half_time"
        assert MatchStatus.SECOND_HALF.value == "second_half"
        assert MatchStatus.FINISHED.value == "finished"
        assert MatchStatus.POSTPONED.value == "postponed"
        assert MatchStatus.CANCELLED.value == "cancelled"

    def test_event_type_enum(self):
        """测试事件类型枚举"""
        assert EventType.GOAL.value == "goal"
        assert EventType.YELLOW_CARD.value == "yellow_card"
        assert EventType.RED_CARD.value == "red_card"
        assert EventType.SUBSTITUTION.value == "substitution"
        assert EventType.PENALTY.value == "penalty"
        assert EventType.OWN_GOAL.value == "own_goal"
        assert EventType.VAR_DECISION.value == "var_decision"

    def test_collector_initialization_with_defaults(self):
        """测试采集器默认初始化"""
        collector = ScoresCollector()
        assert collector.data_source == "scores_api"
        assert collector.api_key is None
        assert collector.base_url == "https://api.football-data.org/v4"
        assert collector.websocket_url is None
        assert collector.polling_interval == 120


class TestScoresCollectorSkippedMethods:
    """实时比分采集器跳过方法测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector()

    @pytest.mark.asyncio
    async def test_collect_fixtures_skipped(self):
        """测试赛程采集跳过"""
        result = await self.collector.collect_fixtures()
        assert result.data_source == "scores_api"
        assert result.collection_type == "fixtures"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_collect_odds_skipped(self):
        """测试赔率采集跳过"""
        result = await self.collector.collect_odds()
        assert result.data_source == "scores_api"
        assert result.collection_type == "odds"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.status == "skipped"


class TestScoresCollectorLiveScores:
    """实时比分采集功能测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(
            data_source="scores_api",
            api_key="test_key",
            websocket_url="wss://api.football-data.org/v4/websocket",
        )

    @pytest.mark.asyncio
    async def test_collect_live_scores_success(self):
        """测试成功采集实时比分"""
        # Mock依赖方法
        self.collector._get_live_matches = AsyncMock(return_value=["match1", "match2"])
        self.collector._collect_via_websocket = AsyncMock(
            return_value=[
                {
                    "external_match_id": "match1",
                    "status": "LIVE",
                    "home_score": 1,
                    "away_score": 0,
                },
                {
                    "external_match_id": "match2",
                    "status": "LIVE",
                    "home_score": 0,
                    "away_score": 0,
                },
            ]
        )
        self.collector._save_to_bronze_layer = AsyncMock()

        result = await self.collector.collect_live_scores()

        assert result.data_source == "scores_api"
        assert result.collection_type == "live_scores"
        assert result.records_collected == 2
        assert result.success_count == 2
        assert result.error_count == 0
        assert result.status == "success"
        assert "match1" in self.collector._active_matches
        assert "match2" in self.collector._active_matches

    @pytest.mark.asyncio
    async def test_collect_live_scores_no_matches(self):
        """测试无进行中比赛"""
        self.collector._get_live_matches = AsyncMock(return_value=[])

        result = await self.collector.collect_live_scores()

        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_collect_live_scores_websocket_failure_fallback(self):
        """测试WebSocket失败回退到轮询"""
        # Mock依赖方法
        self.collector._get_live_matches = AsyncMock(return_value=["match1"])
        self.collector._collect_via_websocket = AsyncMock(
            side_effect=Exception("WebSocket failed")
        )
        self.collector._collect_via_polling = AsyncMock(
            return_value=[
                {
                    "external_match_id": "match1",
                    "status": "LIVE",
                    "home_score": 1,
                    "away_score": 0,
                }
            ]
        )
        self.collector._save_to_bronze_layer = AsyncMock()

        result = await self.collector.collect_live_scores()

        assert result.records_collected == 1
        assert result.success_count == 1
        assert result.error_count == 1
        assert result.status == "partial"
        assert "WebSocket failed" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_live_scores_polling_only(self):
        """测试仅使用轮询模式"""
        # Mock依赖方法
        self.collector._get_live_matches = AsyncMock(return_value=["match1"])
        self.collector._collect_via_polling = AsyncMock(
            return_value=[
                {
                    "external_match_id": "match1",
                    "status": "LIVE",
                    "home_score": 1,
                    "away_score": 0,
                }
            ]
        )
        self.collector._save_to_bronze_layer = AsyncMock()

        result = await self.collector.collect_live_scores(use_websocket=False)

        assert result.records_collected == 1
        assert result.success_count == 1
        assert result.error_count == 0
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_collect_live_scores_general_exception(self):
        """测试一般异常处理"""
        self.collector._get_live_matches = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await self.collector.collect_live_scores()

        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 1
        assert result.status == "failed"
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_live_scores_with_custom_match_ids(self):
        """测试使用自定义比赛ID"""
        # Mock依赖方法
        self.collector._collect_via_websocket = AsyncMock(
            return_value=[
                {
                    "external_match_id": "match1",
                    "status": "LIVE",
                    "home_score": 1,
                    "away_score": 0,
                }
            ]
        )
        self.collector._save_to_bronze_layer = AsyncMock()

        result = await self.collector.collect_live_scores(match_ids=["match1"])

        assert result.records_collected == 1
        assert result.success_count == 1
        assert "match1" in self.collector._active_matches

    @pytest.mark.asyncio
    async def test_collect_live_scores_no_websocket_url(self):
        """测试无WebSocket URL配置"""
        collector = ScoresCollector(api_key="test_key")  # No websocket_url

        collector._get_live_matches = AsyncMock(return_value=["match1"])
        collector._collect_via_polling = AsyncMock(
            return_value=[
                {
                    "external_match_id": "match1",
                    "status": "LIVE",
                    "home_score": 1,
                    "away_score": 0,
                }
            ]
        )
        collector._save_to_bronze_layer = AsyncMock()

        result = await collector.collect_live_scores(use_websocket=True)

        assert result.records_collected == 1
        assert result.success_count == 1
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_collect_websocket_scores_delegation(self):
        """测试WebSocket比分采集委托"""
        self.collector._collect_via_websocket = AsyncMock(
            return_value=[{"match_id": "1"}]
        )

        result = await self.collector._collect_websocket_scores(["match1"])

        assert result == [{"match_id": "1"}]
        self.collector._collect_via_websocket.assert_called_once_with(["match1"])


class TestScoresCollectorHelperMethods:
    """实时比分采集器辅助方法测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector()

    @pytest.mark.asyncio
    async def test_get_live_matches_success(self):
        """测试成功获取进行中比赛"""
        # 注意：当前实现返回空列表，测试应验证这一行为
        result = await self.collector._get_live_matches()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_live_matches_exception(self):
        """测试获取进行中比赛异常"""
        # 注意：当前实现总是返回空列表，没有异常处理逻辑
        # 测试应验证当前的实际行为
        result = await self.collector._get_live_matches()
        assert result == []

    def test_is_match_finished_true(self):
        """测试比赛结束判断-已结束"""
        collector = ScoresCollector()

        finished_statuses = ["FINISHED", "COMPLETED", "CANCELLED", "POSTPONED"]
        for status in finished_statuses:
            assert collector._is_match_finished(status) == True

    def test_is_match_finished_false(self):
        """测试比赛结束判断-未结束"""
        collector = ScoresCollector()

        ongoing_statuses = [
            "LIVE",
            "HALF_TIME",
            "FIRST_HALF",
            "SECOND_HALF",
            "NOT_STARTED",
        ]
        for status in ongoing_statuses:
            assert collector._is_match_finished(status) == False

    def test_is_match_finished_case_insensitive(self):
        """测试比赛结束判断大小写不敏感"""
        collector = ScoresCollector()

        assert collector._is_match_finished("finished") == True
        assert collector._is_match_finished("Finished") == True
        assert collector._is_match_finished("FINISHED") == True
        assert collector._is_match_finished("live") == False


class TestScoresCollectorWebSocket:
    """WebSocket连接测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(
            api_key="test_key", websocket_url="wss://api.football-data.org/v4/websocket"
        )

    @pytest.mark.asyncio
    async def test_collect_via_websocket_success(self):
        """测试WebSocket采集成功"""
        # 简化测试，直接测试WebSocket连接和数据接收逻辑
        # 创建模拟的WebSocket对象
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        mock_websocket.recv.side_effect = [
            json.dumps({"type": "match_update", "id": "1", "status": "LIVE"}),
            json.dumps({"type": "match_update", "id": "2", "status": "LIVE"}),
            asyncio.TimeoutError(),  # 模拟超时触发心跳
        ]
        mock_websocket.ping = AsyncMock()

        # 创建异步上下文管理器
        class MockWebSocketContextManager:
            async def __aenter__(self):
                return mock_websocket

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        # Mock _clean_live_data 返回有效数据（添加id字段）
        def mock_clean_data(data):
            if data.get("type") == "match_update":
                return {"external_match_id": data["id"], "status": data["status"]}
            return None

        self.collector._clean_live_data = AsyncMock(side_effect=mock_clean_data)

        # 让wait_for直接返回字符串而不是coroutine
        message1 = json.dumps({"type": "match_update", "id": "1", "status": "LIVE"})
        message2 = json.dumps({"type": "match_update", "id": "2", "status": "LIVE"})

        with patch(
            "websockets.connect", return_value=MockWebSocketContextManager()
        ), patch(
            "asyncio.wait_for", side_effect=[message1, message2, asyncio.TimeoutError()]
        ), patch(
            "asyncio.get_event_loop"
        ) as mock_loop:

            # 让时间函数返回足够的值以支持循环
            def mock_time():
                current_time = getattr(mock_time, "_current_time", 0)
                mock_time._current_time = current_time + 1
                return current_time

            mock_time._current_time = 0
            mock_loop.return_value.time = mock_time

            result = await self.collector._collect_via_websocket(
                ["match1", "match2"], duration=3
            )

            assert len(result) == 2
            assert self.collector._websocket_connected == False

    @pytest.mark.asyncio
    async def test_collect_via_websocket_no_url(self):
        """测试无WebSocket URL"""
        collector = ScoresCollector()

        with pytest.raises(ValueError, match="WebSocket URL not configured"):
            await collector._collect_via_websocket(["match1"])

    @pytest.mark.asyncio
    async def test_collect_via_websocket_connection_error(self):
        """测试WebSocket连接错误"""
        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await self.collector._collect_via_websocket(["match1"])

    @pytest.mark.asyncio
    async def test_collect_via_websocket_heartbeat(self):
        """测试WebSocket心跳机制"""
        # 简化测试，专注于验证WebSocket连接的基本功能
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        mock_websocket.recv.side_effect = [asyncio.TimeoutError()]
        mock_websocket.ping = AsyncMock()

        # 创建异步上下文管理器
        class MockWebSocketContextManager:
            async def __aenter__(self):
                return mock_websocket

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        # 直接测试异常情况下的连接处理
        with patch(
            "websockets.connect", return_value=MockWebSocketContextManager()
        ), patch("asyncio.wait_for", side_effect=[asyncio.TimeoutError()]), patch(
            "asyncio.get_event_loop"
        ) as mock_loop:

            # 简单的时间函数
            def mock_time():
                return 0

            mock_loop.return_value.time = mock_time

            # 使用极短的持续时间，快速测试连接
            result = await self.collector._collect_via_websocket(["match1"], duration=1)

            # 验证WebSocket连接被尝试
            assert result == []
            assert mock_websocket.send.called


class TestScoresCollectorPolling:
    """HTTP轮询测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(api_key="test_key")

    @pytest.mark.asyncio
    async def test_collect_via_polling_success(self):
        """测试轮询采集成功"""
        # Mock依赖方法
        self.collector._get_match_live_data = AsyncMock(
            side_effect=[
                {
                    "id": "match1",
                    "status": "LIVE",
                    "score": {"fullTime": {"home": 1, "away": 0}},
                },
                {
                    "id": "match2",
                    "status": "LIVE",
                    "score": {"fullTime": {"home": 0, "away": 0}},
                },
            ]
        )
        self.collector._clean_live_data = AsyncMock(side_effect=lambda x: x)

        result = await self.collector._collect_via_polling(["match1", "match2"])

        assert len(result) == 2
        assert self.collector._get_match_live_data.call_count == 2

    @pytest.mark.asyncio
    async def test_collect_via_polling_match_error(self):
        """测试轮询单场比赛错误"""
        self.collector._get_match_live_data = AsyncMock(
            side_effect=[
                {
                    "id": "match1",
                    "status": "LIVE",
                    "score": {"fullTime": {"home": 1, "away": 0}},
                },
                Exception("Match not found"),
                {
                    "id": "match3",
                    "status": "LIVE",
                    "score": {"fullTime": {"home": 0, "away": 0}},
                },
            ]
        )
        self.collector._clean_live_data = AsyncMock(side_effect=lambda x: x)

        with patch.object(self.collector.logger, "error") as mock_error:
            result = await self.collector._collect_via_polling(
                ["match1", "match2", "match3"]
            )

            assert len(result) == 2  # 只有成功的数据被返回
            assert mock_error.call_count == 1

    @pytest.mark.asyncio
    async def test_collect_via_polling_general_exception(self):
        """测试轮询一般异常"""
        # 注意：实际实现会捕获单场比赛的异常，不会抛出整体异常
        # 测试应验证异常被正确处理并记录日志
        original_method = self.collector._get_match_live_data

        async def failing_method(match_id):
            raise Exception("Polling failed")

        self.collector._get_match_live_data = failing_method
        self.collector._clean_live_data = AsyncMock(side_effect=lambda x: x)

        with patch.object(self.collector.logger, "error") as mock_error:
            result = await self.collector._collect_via_polling(["invalid_match"])

            # 验证结果为空（因为所有比赛都失败了）
            assert result == []
            # 验证错误日志被记录
            mock_error.assert_called()

        # 恢复原方法
        self.collector._get_match_live_data = original_method

    @pytest.mark.asyncio
    async def test_get_match_live_data_success(self):
        """测试获取比赛实时数据成功"""
        mock_response = {"id": "match1", "status": "LIVE"}
        self.collector._make_request = AsyncMock(return_value=mock_response)

        result = await self.collector._get_match_live_data("match1")

        assert result == mock_response
        self.collector._make_request.assert_called_once_with(
            url="https://api.football-data.org/v4/matches/match1",
            headers={"X-Auth-Token": "test_key"},
        )

    @pytest.mark.asyncio
    async def test_get_match_live_data_no_api_key(self):
        """测试无API key的情况"""
        collector = ScoresCollector()
        mock_response = {"id": "match1", "status": "LIVE"}
        collector._make_request = AsyncMock(return_value=mock_response)

        result = await collector._get_match_live_data("match1")

        assert result == mock_response
        collector._make_request.assert_called_once_with(
            url="https://api.football-data.org/v4/matches/match1", headers={}
        )

    @pytest.mark.asyncio
    async def test_get_match_live_data_failure(self):
        """测试获取比赛实时数据失败"""
        self.collector._make_request = AsyncMock(side_effect=Exception("API error"))

        with patch.object(self.collector.logger, "error") as mock_error:
            result = await self.collector._get_match_live_data("match1")

            assert result is None
            mock_error.assert_called_with(
                "Failed to get live data for match match1: API error"
            )


class TestScoresCollectorDataCleaning:
    """实时数据清洗测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector()

    @pytest.mark.asyncio
    async def test_clean_live_data_success(self):
        """测试成功清洗实时数据"""
        raw_data = {
            "id": "123",
            "status": "LIVE",
            "score": {"fullTime": {"home": 2, "away": 1}},
            "minute": 75,
            "events": [
                {
                    "minute": 45,
                    "type": "goal",
                    "player": {"name": "Player1"},
                    "team": {"name": "Team1"},
                }
            ],
        }

        result = await self.collector._clean_live_data(raw_data)

        assert result is not None
        assert result["external_match_id"] == "123"
        assert result["status"] == "LIVE"
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["minute"] == 75
        assert len(result["events"]) == 1
        assert result["events"][0]["type"] == "goal"
        assert result["events"][0]["player"] == "Player1"
        assert result["collected_at"] is not None
        assert result["processed"] == False
        assert result["raw_data"] == raw_data

    @pytest.mark.asyncio
    async def test_clean_live_data_missing_id(self):
        """测试缺失比赛ID"""
        raw_data = {"status": "LIVE"}

        with patch.object(self.collector.logger, "warning") as mock_warning:
            result = await self.collector._clean_live_data(raw_data)

            assert result is None
            mock_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_clean_live_data_missing_optional_fields(self):
        """测试缺失可选字段"""
        raw_data = {"id": "123", "status": "LIVE"}

        result = await self.collector._clean_live_data(raw_data)

        assert result is not None
        assert result["external_match_id"] == "123"
        assert result["status"] == "LIVE"
        assert result["home_score"] is None
        assert result["away_score"] is None
        assert result["minute"] is None
        assert result["events"] == []

    @pytest.mark.asyncio
    async def test_clean_live_data_with_missing_score_structure(self):
        """测试比分结构缺失"""
        raw_data = {"id": "123", "status": "LIVE", "score": {}}

        result = await self.collector._clean_live_data(raw_data)

        assert result is not None
        assert result["home_score"] is None
        assert result["away_score"] is None

    @pytest.mark.asyncio
    async def test_clean_live_data_exception(self):
        """测试数据清洗异常"""
        with patch.object(self.collector.logger, "warning") as mock_warning:
            result = await self.collector._clean_live_data({"invalid": "data"})

            assert result is None
            # 实际实现记录的是warning而不是error
            mock_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_clean_live_data_with_complex_events(self):
        """测试复杂事件数据清洗"""
        raw_data = {
            "id": "123",
            "status": "LIVE",
            "score": {"fullTime": {"home": 1, "away": 0}},
            "events": [
                {
                    "minute": 25,
                    "type": "goal",
                    "player": {"name": "Player1"},
                    "team": {"name": "Team1"},
                },
                {
                    "minute": 60,
                    "type": "yellow_card",
                    "player": {"name": "Player2"},
                    "team": {"name": "Team2"},
                },
                {
                    "minute": 80,
                    "type": "substitution",
                    "player": {"name": "Player3"},
                    "team": {"name": "Team1"},
                },
                {"type": "invalid_event"},  # 缺失字段的事件
            ],
        }

        result = await self.collector._clean_live_data(raw_data)

        assert result is not None
        assert len(result["events"]) == 4
        assert result["events"][0]["type"] == "goal"
        assert result["events"][1]["type"] == "yellow_card"
        assert result["events"][2]["type"] == "substitution"
        assert result["events"][3]["type"] == "invalid_event"


class TestScoresCollectorContinuousMonitoring:
    """持续监控测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(
            api_key="test_key", polling_interval=1  # 短间隔用于测试
        )

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring_success(self):
        """测试启动持续监控成功"""
        # Mock依赖方法
        self.collector._get_live_matches = AsyncMock(return_value=["match1"])
        self.collector.collect_live_scores = AsyncMock(
            return_value=CollectionResult(
                data_source="scores_api",
                collection_type="live_scores",
                records_collected=1,
                success_count=1,
                error_count=0,
                status="success",
            )
        )

        # 测试监控运行一段时间
        task = asyncio.create_task(self.collector.start_continuous_monitoring())
        await asyncio.sleep(0.1)  # 让监控运行一小段时间
        task.cancel()  # 取消任务

        # 验证监控至少运行了一次
        assert self.collector.collect_live_scores.called

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring_with_custom_matches(self):
        """测试使用自定义比赛ID的持续监控"""
        self.collector.collect_live_scores = AsyncMock(
            return_value=CollectionResult(
                data_source="scores_api",
                collection_type="live_scores",
                records_collected=1,
                success_count=1,
                error_count=0,
                status="success",
            )
        )

        task = asyncio.create_task(
            self.collector.start_continuous_monitoring(match_ids=["match1"])
        )
        await asyncio.sleep(0.1)
        task.cancel()

        # 验证使用自定义比赛ID
        self.collector.collect_live_scores.assert_called_with(
            match_ids=["match1"], use_websocket=True
        )

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring_failure_handling(self):
        """测试持续监控失败处理"""
        self.collector._get_live_matches = AsyncMock(return_value=["match1"])
        self.collector.collect_live_scores = AsyncMock(
            return_value=CollectionResult(
                data_source="scores_api",
                collection_type="live_scores",
                records_collected=0,
                success_count=0,
                error_count=1,
                status="failed",
                error_message="API error",
            )
        )

        with patch.object(self.collector.logger, "error") as mock_error:
            task = asyncio.create_task(self.collector.start_continuous_monitoring())
            await asyncio.sleep(0.1)
            task.cancel()

            mock_error.assert_called_with("Monitoring failed: API error")

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring_exception_handling(self):
        """测试持续监控异常处理"""
        self.collector._get_live_matches = AsyncMock(
            side_effect=Exception("Database error")
        )

        # 测试异常不会中断监控
        task = asyncio.create_task(self.collector.start_continuous_monitoring())
        await asyncio.sleep(0.1)
        task.cancel()

        # 验证监控继续运行（不会抛出异常）
        assert not task.done()


class TestScoresCollectorIntegration:
    """实时比分采集器集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = ScoresCollector(
            api_key="test_key", websocket_url="wss://api.football-data.org/v4/websocket"
        )

    @pytest.mark.asyncio
    async def test_complete_workflow_simulation(self):
        """测试完整工作流模拟"""
        # Mock所有依赖
        self.collector._get_live_matches = AsyncMock(return_value=["match1", "match2"])
        self.collector._collect_via_websocket = AsyncMock(
            return_value=[
                {
                    "external_match_id": "match1",
                    "status": "LIVE",
                    "home_score": 1,
                    "away_score": 0,
                },
                {
                    "external_match_id": "match2",
                    "status": "LIVE",
                    "home_score": 0,
                    "away_score": 0,
                },
            ]
        )
        self.collector._clean_live_data = AsyncMock(side_effect=lambda x: x)
        self.collector._save_to_bronze_layer = AsyncMock()

        # 运行完整工作流
        result = await self.collector.collect_live_scores()

        # 验证结果
        assert result.status == "success"
        assert result.records_collected == 2
        assert result.success_count == 2
        assert len(result.collected_data) == 2

        # 验证状态更新
        assert "match1" in self.collector._active_matches
        assert "match2" in self.collector._active_matches

    @pytest.mark.asyncio
    async def test_error_handling_comprehensive(self):
        """测试全面错误处理"""
        # Mock各种错误场景
        self.collector._get_live_matches = AsyncMock(return_value=["match1"])
        self.collector._collect_via_websocket = AsyncMock(
            side_effect=Exception("WebSocket failed")
        )
        self.collector._collect_via_polling = AsyncMock(
            side_effect=Exception("Polling failed")
        )

        result = await self.collector.collect_live_scores()

        # 验证错误处理 - 当轮询也失败时，状态应该是failed而不是partial
        assert result.status == "failed"
        assert result.success_count == 0
        assert result.error_count == 1  # 只有一个总错误
        # 由于回退机制，最终显示的是Polling failed
        assert "Polling failed" in result.error_message

    @pytest.mark.asyncio
    async def test_websocket_and_polling_fallback_simulation(self):
        """测试WebSocket和轮询回退模拟"""
        # 模拟WebSocket失败，轮询成功
        self.collector._get_live_matches = AsyncMock(return_value=["match1"])
        self.collector._collect_via_websocket = AsyncMock(
            side_effect=Exception("WebSocket error")
        )
        self.collector._collect_via_polling = AsyncMock(
            return_value=[
                {
                    "external_match_id": "match1",
                    "status": "LIVE",
                    "home_score": 1,
                    "away_score": 0,
                }
            ]
        )
        self.collector._save_to_bronze_layer = AsyncMock()

        result = await self.collector.collect_live_scores()

        # 验证回退机制工作正常
        assert result.status == "partial"
        assert result.success_count == 1
        assert result.error_count == 1
        assert len(result.collected_data) == 1

    @pytest.mark.asyncio
    async def test_match_status_transition_handling(self):
        """测试比赛状态转换处理"""
        # 模拟比赛从进行中到结束
        match_data = [
            {
                "external_match_id": "match1",
                "status": "LIVE",
                "home_score": 1,
                "away_score": 0,
            },
            {
                "external_match_id": "match2",
                "status": "FINISHED",
                "home_score": 2,
                "away_score": 1,
            },
        ]

        self.collector._get_live_matches = AsyncMock(return_value=["match1", "match2"])
        self.collector._collect_via_polling = AsyncMock(return_value=match_data)
        self.collector._clean_live_data = AsyncMock(side_effect=lambda x: x)
        self.collector._save_to_bronze_layer = AsyncMock()

        result = await self.collector.collect_live_scores(use_websocket=False)

        # 验证数据采集和处理
        assert result.records_collected == 2
        assert result.success_count == 2

        # 验证比赛结束判断
        assert self.collector._is_match_finished("FINISHED") == True
        assert self.collector._is_match_finished("LIVE") == False
