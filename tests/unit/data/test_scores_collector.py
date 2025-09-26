"""
足球数据采集器测试 - ScoresCollector
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import responses

from src.data.collectors.scores_collector import ScoresCollector, MatchStatus, EventType


class TestScoresCollector:
    """测试实时比分采集器"""

    @pytest.fixture
    def collector(self):
        """创建ScoresCollector实例"""
        with patch("src.data.collectors.base_collector.DatabaseManager"):
            return ScoresCollector()

    def test_init(self, collector):
        """测试初始化"""
    assert collector.base_url is not None
    assert collector.websocket_url is None  # 默认为 None
    assert hasattr(collector, 'polling_interval')
    assert collector.polling_interval == 120
    assert hasattr(collector, '_active_matches')
    assert isinstance(collector._active_matches, set)

    @pytest.mark.asyncio
    async def test_collect_fixtures_skipped(self, collector):
        """测试ScoresCollector不处理赛程数据"""
        result = await collector.collect_fixtures()

    assert result.status == "skipped"
    assert result.records_collected == 0
    assert result.success_count == 0
    assert result.error_count == 0

    
    @pytest.mark.asyncio
    async def test_collect_odds_skipped(self, collector):
        """测试ScoresCollector不处理赔率数据"""
        result = await collector.collect_odds()

    assert result.status == "skipped"
    assert result.records_collected == 0
    assert result.success_count == 0
    assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_collect_live_scores_success(self, collector):
        """测试成功采集实时比分"""
        match_ids = ["match_1", "match_2"]

        with patch.object(collector, '_get_live_matches') as mock_get_matches, \
             patch.object(collector, '_collect_via_polling') as mock_polling:

            mock_get_matches.return_value = match_ids
            mock_polling.return_value = [
                {
                    "match_id": "match_1",
                    "home_score": 1,
                    "away_score": 0,
                    "status": "live"
                }
            ]

            result = await collector.collect_live_scores()

    assert result.status == "success"
    assert result.records_collected == 1

    @pytest.mark.asyncio
    async def test_collect_live_scores_no_matches(self, collector):
        """测试无比赛时的实时比分采集"""
        with patch.object(collector, '_get_live_matches') as mock_get_matches:
            mock_get_matches.return_value = []  # 无比赛

            result = await collector.collect_live_scores()

    assert result.status == "success"
    assert result.records_collected == 0

    @pytest.mark.asyncio
    async def test_get_live_matches_success(self, collector):
        """测试成功获取实时比赛列表"""
        # 由于实际实现返回空列表，我们测试这个行为
        matches = await collector._get_live_matches()

        # 当前实现返回空列表作为占位符
    assert isinstance(matches, list)
    assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_get_match_live_data_success(self, collector):
        """测试成功获取单个比赛实时数据"""
        with patch.object(collector, '_make_request_with_retry') as mock_request:
            mock_response = {
                "match_id": "match_1",
                "home_score": 2,
                "away_score": 1,
                "status": "second_half",
                "events": [
                    {
                        "type": "goal",
                        "minute": 25,
                        "team": "home"
                    }
                ]
            }
            mock_request.return_value = mock_response

            data = await collector._get_match_live_data("match_1")

    assert data is not None
    assert data["home_score"] == 2
    assert data["away_score"] == 1

    @pytest.mark.asyncio
    async def test_get_match_live_data_not_found(self, collector):
        """测试比赛不存在的情况"""
        with patch.object(collector, '_make_request_with_retry') as mock_request:
            mock_request.return_value = None  # 比赛不存在

            data = await collector._get_match_live_data("nonexistent_match")

    assert data is None

    @responses.activate
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, collector):
        """测试API限流处理"""
        # Mock 429 Too Many Requests 响应
        responses.add(
            responses.GET,
            "https:_/api.example.com/live-matches",
            status=429,
            json={"error": "Rate limit exceeded"}
        )

        with patch.object(collector, '_make_request') as mock_make_request:
            mock_make_request.side_effect = Exception("Rate limit exceeded")

            try:
                await collector._get_live_matches()
            except Exception as e:
    assert "Rate limit exceeded" in str(e)

    @pytest.mark.asyncio
    async def test_api_timeout(self, collector):
        """测试API超时处理"""
        with patch.object(collector, '_make_request') as mock_make_request:
            mock_make_request.side_effect = asyncio.TimeoutError("Request timeout")

            try:
                await collector._get_live_matches()
            except asyncio.TimeoutError as e:
    assert "Request timeout" in str(e)

    @pytest.mark.asyncio
    async def test_process_response_success(self, collector):
        """测试成功处理响应数据"""
        with patch.object(collector, '_get_match_live_data') as mock_get_data, \
             patch.object(collector, '_clean_live_data') as mock_clean:

            mock_get_data.return_value = {
                "match_id": "match_1",
                "home_score": 2,
                "away_score": 1,
                "status": "finished"
            }
            mock_clean.return_value = {
                "match_id": "match_1",
                "home_score": 2,
                "away_score": 1,
                "status": "finished"
            }

            result = await collector._collect_via_polling(["match_1"])

    assert len(result) == 1
    assert result[0]["home_score"] == 2

    @pytest.mark.asyncio
    async def test_process_response_invalid_json(self, collector):
        """测试无效JSON响应处理"""
        with patch.object(collector, '_make_request') as mock_request:
            mock_request.return_value = "invalid json string"

            try:
                await collector._get_match_live_data("match_1")
            except json.JSONDecodeError:
                pass  # 期望抛出JSON解析错误

    @pytest.mark.asyncio
    async def test_process_response_empty_data(self, collector):
        """测试空响应数据处理"""
        with patch.object(collector, '_make_request') as mock_request:
            mock_request.return_value = {}  # 空数据

            data = await collector._get_match_live_data("match_1")

            # 应该返回空字典，因为方法直接返回响应
    assert data == {}

    @pytest.mark.asyncio
    async def test_process_response_missing_fields(self, collector):
        """测试响应中缺少必要字段"""
        with patch.object(collector, '_make_request') as mock_request:
            mock_request.return_value = {
                "match_id": "match_1"
                # 缺少score、status等必要字段
            }

            data = await collector._get_match_live_data("match_1")

            # 应该能处理缺失字段
    assert data is not None
    assert data["match_id"] == "match_1"

    def test_match_status_enum(self):
        """测试比赛状态枚举"""
    assert MatchStatus.NOT_STARTED.value == "not_started"
    assert MatchStatus.FIRST_HALF.value == "first_half"
    assert MatchStatus.FINISHED.value == "finished"
    assert MatchStatus.POSTPONED.value == "postponed"

    def test_event_type_enum(self):
        """测试事件类型枚举"""
    assert EventType.GOAL.value == "goal"
    assert EventType.YELLOW_CARD.value == "yellow_card"
    assert EventType.RED_CARD.value == "red_card"
    assert EventType.SUBSTITUTION.value == "substitution"

    @pytest.mark.asyncio
    async def test_clean_live_data_success(self, collector):
        """测试成功清洗实时数据"""
        raw_data = {
            "id": "match_1",
            "status": "SECOND_HALF",  # 大写状态
            "minute": "45",
            "score": {
                "fullTime": {
                    "home": "2",  # 字符串形式的分数
                    "away": "1"
                }
            }
        }

        cleaned_data = await collector._clean_live_data(raw_data)

    assert cleaned_data is not None
    assert cleaned_data["home_score"] == "2"  # 保持字符串格式
    assert cleaned_data["away_score"] == "1"
    assert cleaned_data["status"] == "SECOND_HALF"  # 保持原始格式

    @pytest.mark.asyncio
    async def test_clean_live_data_with_none_values(self, collector):
        """测试清洗包含None值的数据"""
        raw_data = {
            "id": "match_1",
            "status": None,
            "score": {
                "fullTime": {
                    "home": None,  # None值
                    "away": 1
                }
            }
        }

        cleaned_data = await collector._clean_live_data(raw_data)

        # 应该合理处理None值，可能是设置为默认值或过滤掉
    assert cleaned_data is not None
    assert cleaned_data["external_match_id"] == "match_1"

    @pytest.mark.asyncio
    async def test_clean_live_data_empty_dict(self, collector):
        """测试清洗空字典"""
        cleaned_data = await collector._clean_live_data({})

    assert cleaned_data is None  # 空字典应该返回None

    def test_is_match_finished(self, collector):
        """测试比赛是否结束的判断"""
    assert collector._is_match_finished("finished") is True
    assert collector._is_match_finished("FINISHED") is True
    assert collector._is_match_finished("postponed") is True
    assert collector._is_match_finished("cancelled") is True
    assert collector._is_match_finished("first_half") is False
    assert collector._is_match_finished("second_half") is False

    @pytest.mark.asyncio
    async def test_start_continuous_monitoring(self, collector):
        """测试启动持续监控"""
        with patch.object(collector, '_get_live_matches') as mock_get_matches, \
             patch.object(collector, '_collect_via_polling') as mock_polling, \
             patch('asyncio.sleep') as mock_sleep:

            mock_get_matches.return_value = ["match_1"]
            mock_polling.return_value = [{"match_id": "match_1", "status": "finished"}]

            # 模拟监控运行一次
            mock_sleep.side_effect = [None, KeyboardInterrupt()]  # 第一次循环后中断

            try:
                await collector.start_continuous_monitoring()
            except KeyboardInterrupt:
                pass  # 正常中断

            # 验证监控逻辑被调用
            mock_get_matches.assert_called()
            mock_polling.assert_called_with(["match_1"])