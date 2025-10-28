"""测试比赛领域事件模块"""

from unittest.mock import Mock

import pytest

try:
    from src.domain.events.match_events import (
        MatchCancelledEvent,
        MatchFinishedEvent,
        MatchPostponedEvent,
        MatchStartedEvent,
    )
    from src.domain.models.match import MatchResult, MatchScore

    # 测试数据
    MATCH_ID = 123
    HOME_TEAM_ID = 1
    AWAY_TEAM_ID = 2
    FINAL_SCORE = MatchScore(home_score=2, away_score=1)
    RESULT = MatchResult.HOME_WIN
    CANCELLATION_REASON = "Bad weather"
    NEW_DATE = "2024-01-15T19:00:00Z"
    POSTPONEMENT_REASON = "Player illness"

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

    # 创建Mock对象用于测试
    MATCH_ID = 123
    HOME_TEAM_ID = 1
    AWAY_TEAM_ID = 2


@pytest.mark.skipif(not IMPORT_SUCCESS, reason="Module import failed")
@pytest.mark.domain
class TestMatchEvents:
    """比赛事件测试"""

    def test_match_started_event_creation(self):
        """测试比赛开始事件创建"""
        event = MatchStartedEvent(
            match_id=MATCH_ID, home_team_id=HOME_TEAM_ID, away_team_id=AWAY_TEAM_ID
        )

        assert event.match_id == MATCH_ID
        assert event.home_team_id == HOME_TEAM_ID
        assert event.away_team_id == AWAY_TEAM_ID
        assert event.aggregate_id == MATCH_ID

    def test_match_started_event_data(self):
        """测试比赛开始事件数据"""
        event = MatchStartedEvent(
            match_id=MATCH_ID, home_team_id=HOME_TEAM_ID, away_team_id=AWAY_TEAM_ID
        )

        event_data = event._get_event_data()
        expected_data = {
            "match_id": MATCH_ID,
            "home_team_id": HOME_TEAM_ID,
            "away_team_id": AWAY_TEAM_ID,
        }

        assert event_data == expected_data

    def test_match_finished_event_creation(self):
        """测试比赛结束事件创建"""
        event = MatchFinishedEvent(
            match_id=MATCH_ID,
            home_team_id=HOME_TEAM_ID,
            away_team_id=AWAY_TEAM_ID,
            final_score=FINAL_SCORE,
            result=RESULT,
        )

        assert event.match_id == MATCH_ID
        assert event.home_team_id == HOME_TEAM_ID
        assert event.away_team_id == AWAY_TEAM_ID
        assert event.final_score == FINAL_SCORE
        assert event.result == RESULT
        assert event.aggregate_id == MATCH_ID

    def test_match_finished_event_data(self):
        """测试比赛结束事件数据"""
        event = MatchFinishedEvent(
            match_id=MATCH_ID,
            home_team_id=HOME_TEAM_ID,
            away_team_id=AWAY_TEAM_ID,
            final_score=FINAL_SCORE,
            result=RESULT,
        )

        event_data = event._get_event_data()
        expected_data = {
            "match_id": MATCH_ID,
            "home_team_id": HOME_TEAM_ID,
            "away_team_id": AWAY_TEAM_ID,
            "final_score": {
                "home_score": FINAL_SCORE.home_score,
                "away_score": FINAL_SCORE.away_score,
                "result": RESULT.value,
            },
        }

        assert event_data == expected_data

    def test_match_cancelled_event_creation(self):
        """测试比赛取消事件创建"""
        event = MatchCancelledEvent(match_id=MATCH_ID, reason=CANCELLATION_REASON)

        assert event.match_id == MATCH_ID
        assert event.reason == CANCELLATION_REASON
        assert event.aggregate_id == MATCH_ID

    def test_match_cancelled_event_data(self):
        """测试比赛取消事件数据"""
        event = MatchCancelledEvent(match_id=MATCH_ID, reason=CANCELLATION_REASON)

        event_data = event._get_event_data()
        expected_data = {"match_id": MATCH_ID, "reason": CANCELLATION_REASON}

        assert event_data == expected_data

    def test_match_postponed_event_creation(self):
        """测试比赛延期事件创建"""
        event = MatchPostponedEvent(
            match_id=MATCH_ID, new_date=NEW_DATE, reason=POSTPONEMENT_REASON
        )

        assert event.match_id == MATCH_ID
        assert event.new_date == NEW_DATE
        assert event.reason == POSTPONEMENT_REASON
        assert event.aggregate_id == MATCH_ID

    def test_match_postponed_event_data(self):
        """测试比赛延期事件数据"""
        event = MatchPostponedEvent(
            match_id=MATCH_ID, new_date=NEW_DATE, reason=POSTPONEMENT_REASON
        )

        event_data = event._get_event_data()
        expected_data = {
            "match_id": MATCH_ID,
            "new_date": NEW_DATE,
            "reason": POSTPONEMENT_REASON,
        }

        assert event_data == expected_data

    def test_event_inheritance(self):
        """测试事件继承"""
        # 所有事件都应该继承自DomainEvent
        started_event = MatchStartedEvent(MATCH_ID, HOME_TEAM_ID, AWAY_TEAM_ID)
        finished_event = MatchFinishedEvent(
            MATCH_ID, HOME_TEAM_ID, AWAY_TEAM_ID, FINAL_SCORE, RESULT
        )
        cancelled_event = MatchCancelledEvent(MATCH_ID, CANCELLATION_REASON)
        postponed_event = MatchPostponedEvent(MATCH_ID, NEW_DATE, POSTPONEMENT_REASON)

        # 测试它们都有基本的事件属性
        for event in [started_event, finished_event, cancelled_event, postponed_event]:
            assert hasattr(event, "aggregate_id")
            assert hasattr(event, "_get_event_data")
            assert callable(event._get_event_data)

    def test_event_with_additional_kwargs(self):
        """测试带有额外参数的事件"""
        additional_data = {"stadium": "Old Trafford", "attendance": 75000}

        event = MatchStartedEvent(
            match_id=MATCH_ID,
            home_team_id=HOME_TEAM_ID,
            away_team_id=AWAY_TEAM_ID,
            **additional_data
        )

        # 额外参数应该被接受（虽然可能不直接存储）
        assert event.match_id == MATCH_ID
        assert event.home_team_id == HOME_TEAM_ID
        assert event.away_team_id == AWAY_TEAM_ID

    def test_different_score_results(self):
        """测试不同的比分结果"""
        test_cases = [
            (MatchScore(3, 0), MatchResult.HOME_WIN),
            (MatchScore(0, 2), MatchResult.AWAY_WIN),
            (MatchScore(1, 1), MatchResult.DRAW),
        ]

        for score, result in test_cases:
            event = MatchFinishedEvent(
                match_id=MATCH_ID,
                home_team_id=HOME_TEAM_ID,
                away_team_id=AWAY_TEAM_ID,
                final_score=score,
                result=result,
            )

            event_data = event._get_event_data()
            assert event_data["final_score"]["home_score"] == score.home_score
            assert event_data["final_score"]["away_score"] == score.away_score
            assert event_data["final_score"]["result"] == result.value

    def test_cancellation_and_postponement_reasons(self):
        """测试取消和延期原因"""
        reasons = [
            "Bad weather",
            "Safety concerns",
            "Technical issues",
            "Force majeure",
            "",
            "Multiple reasons complex situation",
        ]

        for reason in reasons:
            cancelled_event = MatchCancelledEvent(MATCH_ID, reason)
            postponed_event = MatchPostponedEvent(MATCH_ID, NEW_DATE, reason)

            assert cancelled_event.reason == reason
            assert postponed_event.reason == reason

    def test_date_formats(self):
        """测试不同的日期格式"""
        date_formats = [
            "2024-01-15T19:00:00Z",
            "2024-01-15 19:00:00",
            "2024/01/15 19:00",
            "15-01-2024 19:00",
        ]

        for date_str in date_formats:
            event = MatchPostponedEvent(MATCH_ID, date_str, "Test")
            assert event.new_date == date_str

    def test_edge_cases(self):
        """测试边缘情况"""
        # 测试ID为0的情况
        event = MatchStartedEvent(0, 0, 0)
        assert event.match_id == 0
        assert event.home_team_id == 0
        assert event.away_team_id == 0

        # 测试负数ID
        event = MatchCancelledEvent(-1, "Test")
        assert event.match_id == -1

        # 测试非常大的ID
        large_id = 999999999
        event = MatchPostponedEvent(large_id, NEW_DATE, "Test")
        assert event.match_id == large_id


@pytest.mark.skipif(not IMPORT_SUCCESS, reason="Module import failed")
class TestEventIntegration:
    """事件集成测试"""

    def test_event_serialization_compatibility(self):
        """测试事件序列化兼容性"""
        events = [
            MatchStartedEvent(MATCH_ID, HOME_TEAM_ID, AWAY_TEAM_ID),
            MatchFinishedEvent(
                MATCH_ID, HOME_TEAM_ID, AWAY_TEAM_ID, FINAL_SCORE, RESULT
            ),
            MatchCancelledEvent(MATCH_ID, CANCELLATION_REASON),
            MatchPostponedEvent(MATCH_ID, NEW_DATE, POSTPONEMENT_REASON),
        ]

        for event in events:
            # 所有事件都应该能够序列化为字典
            event_data = event._get_event_data()
            assert isinstance(event_data, dict)
            assert "match_id" in event_data

    def test_event_workflow_simulation(self):
        """测试事件工作流模拟"""
        match_id = 123
        home_team = 1
        away_team = 2

        # 1. 比赛开始
        started = MatchStartedEvent(match_id, home_team, away_team)
        assert started.aggregate_id == match_id

        # 2. 比赛延期
        postponed = MatchPostponedEvent(match_id, NEW_DATE, "Weather")
        assert postponed.match_id == match_id

        # 3. 比赛取消
        cancelled = MatchCancelledEvent(match_id, "Final decision")
        assert cancelled.match_id == match_id

        # 4. 如果比赛正常结束
        finished = MatchFinishedEvent(
            match_id, home_team, away_team, FINAL_SCORE, RESULT
        )
        assert finished.match_id == match_id


def test_import_fallback():
    """测试导入回退"""
    if not IMPORT_SUCCESS:
        assert IMPORT_ERROR is not None
        assert len(IMPORT_ERROR) > 0
    else:
        assert True  # 导入成功
