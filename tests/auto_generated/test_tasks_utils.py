"""
Auto-generated tests for src.tasks.utils module
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.tasks.utils import (
    should_collect_live_scores,
    get_upcoming_matches,
    is_match_day,
    get_active_leagues,
    calculate_next_collection_time,
    cleanup_stale_tasks,
    get_task_priority,
)


class TestShouldCollectLiveScores:
    """测试实时比分采集判断"""

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_should_collect_live_scores_with_matches(self, mock_db_manager):
        """测试有比赛时应该采集实时比分"""
        # 模拟数据库查询返回有比赛
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2  # 2场比赛
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        result = await should_collect_live_scores()

        assert result is True

        # 验证SQL查询
        call_args = mock_session.execute.call_args[0][0]
        assert "SELECT COUNT(*) as match_count" in str(call_args)
        assert "matches" in str(call_args)

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_should_collect_live_scores_no_matches(self, mock_db_manager):
        """测试无比赛时不应该采集实时比分"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0  # 无比赛
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        result = await should_collect_live_scores()

        assert result is False

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_should_collect_live_scores_with_exception(self, mock_db_manager):
        """测试数据库异常时的处理"""
        mock_db_manager.return_value.get_async_session.side_effect = Exception("Database connection failed")

        result = await should_collect_live_scores()

        assert result is False  # 异常时返回False

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_should_collect_live_scores_time_range(self, mock_db_manager):
        """测试时间范围计算"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        with patch('src.tasks.utils.datetime') as mock_datetime:
            mock_now = datetime(2025, 9, 28, 15, 30, 0)
            mock_datetime.now.return_value = mock_now

            await should_collect_live_scores()

            # 验证时间参数
            call_kwargs = mock_session.execute.call_args[1]
            start_time = call_kwargs["start_time"]
            end_time = call_kwargs["end_time"]

            expected_start = mock_now - timedelta(hours=2)
            expected_end = mock_now + timedelta(hours=2)

            assert start_time == expected_start
            assert end_time == expected_end


class TestGetUpcomingMatches:
    """测试获取即将到来的比赛"""

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_get_upcoming_matches_basic(self, mock_db_manager):
        """测试基本获取即将到来的比赛"""
        # 模拟数据库返回
        mock_session = AsyncMock()
        mock_result = MagicMock()

            # 模拟查询结果
        mock_rows = [
            MagicMock(
                id=1001,
                home_team_id=1,
                away_team_id=2,
                league_id=10,
                match_time=datetime(2025, 9, 28, 16, 0, 0),
                match_status="scheduled"
            ),
            MagicMock(
                id=1002,
                home_team_id=3,
                away_team_id=4,
                league_id=10,
                match_time=datetime(2025, 9, 28, 18, 30, 0),
                match_status="scheduled"
            )
        ]
        mock_result.__iter__ = lambda: iter(mock_rows)
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        result = await get_upcoming_matches(hours=24)

        # 验证结果
        assert len(result) == 2
        assert result[0]["id"] == 1001
        assert result[0]["home_team_id"] == 1
        assert result[0]["match_time"] == "2025-09-28T16:00:00"
        assert result[0]["match_status"] == "scheduled"

        assert result[1]["id"] == 1002
        assert result[1]["away_team_id"] == 4

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_get_upcoming_matches_custom_hours(self, mock_db_manager):
        """测试自定义时间范围"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = lambda: iter([])
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        with patch('src.tasks.utils.datetime') as mock_datetime:
            mock_now = datetime(2025, 9, 28, 15, 30, 0)
            mock_datetime.now.return_value = mock_now

            await get_upcoming_matches(hours=12)

            # 验证时间参数
            call_kwargs = mock_session.execute.call_args[1]
            end_time = call_kwargs["end_time"]
            expected_end = mock_now + timedelta(hours=12)
            assert end_time == expected_end

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_get_upcoming_matches_with_exception(self, mock_db_manager):
        """测试异常处理"""
        mock_db_manager.return_value.get_async_session.side_effect = Exception("Query failed")

        result = await get_upcoming_matches()

        assert result == []  # 异常时返回空列表


class TestIsMatchDay:
    """测试比赛日检查"""

    def test_is_match_day_weekend(self):
        """测试周末是比赛日"""
        # 周六 (weekday=5)
        saturday = datetime(2025, 9, 27)  # 2025-09-27 是周六
        assert is_match_day(saturday) is True

        # 周日 (weekday=6)
        sunday = datetime(2025, 9, 28)  # 2025-09-28 是周日
        assert is_match_day(sunday) is True

    def test_is_match_day_weekday(self):
        """测试工作日不是比赛日"""
        # 周一 (weekday=0)
        monday = datetime(2025, 9, 29)  # 2025-09-29 是周一
        assert is_match_day(monday) is False

        # 周三 (weekday=2)
        wednesday = datetime(2025, 10, 1)  # 2025-10-01 是周三
        assert is_match_day(wednesday) is False

    def test_is_match_day_default_today(self):
        """测试默认使用今天"""
        with patch('src.tasks.utils.datetime') as mock_datetime:
            mock_today = datetime(2025, 9, 27)  # 周六
            mock_datetime.now.return_value = mock_today

            result = is_match_day()
            assert result is True


class TestGetActiveLeagues:
    """测试获取活跃联赛"""

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_get_active_leagues_basic(self, mock_db_manager):
        """测试基本获取活跃联赛"""
        mock_session = AsyncMock()
        mock_result = MagicMock()

            # 模拟查询结果
        mock_rows = [
            MagicMock(name="Premier League"),
            MagicMock(name="La Liga"),
            MagicMock(name="Serie A")
        ]
        mock_result.__iter__ = lambda: iter(mock_rows)
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        result = await get_active_leagues()

        assert len(result) == 3
        assert "Premier League" in result
        assert "La Liga" in result
        assert "Serie A" in result

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_get_active_leagues_with_exception(self, mock_db_manager):
        """测试异常处理"""
        mock_db_manager.return_value.get_async_session.side_effect = Exception("Database error")

        result = await get_active_leagues()

        # 异常时返回默认联赛列表
        assert len(result) == 4
        assert "Premier League" in result
        assert "La Liga" in result
        assert "Serie A" in result
        assert "Bundesliga" in result


class TestCalculateNextCollectionTime:
    """测试计算下次采集时间"""

    @patch('src.tasks.utils.datetime')
    def test_calculate_next_collection_time_fixtures_task(self, mock_datetime):
        """测试赛程采集任务时间计算"""
        # 模拟当前时间 2025-09-28 15:30:00 (周日)
        current_time = datetime(2025, 9, 28, 15, 30, 0)
        mock_datetime.now.return_value = current_time

        result = calculate_next_collection_time("collect_fixtures_task")

        # 应该是第二天凌晨2点
        expected = datetime(2025, 9, 29, 2, 0, 0)
        assert result == expected

    @patch('src.tasks.utils.datetime')
    def test_calculate_next_collection_time_fixtures_before_2am(self, mock_datetime):
        """测试赛程采集任务在凌晨2点前"""
        # 模拟当前时间 2025-09-28 01:30:00 (凌晨1:30)
        current_time = datetime(2025, 9, 28, 1, 30, 0)
        mock_datetime.now.return_value = current_time

        result = calculate_next_collection_time("collect_fixtures_task")

        # 应该是当天凌晨2点
        expected = datetime(2025, 9, 28, 2, 0, 0)
        assert result == expected

    @patch('src.tasks.utils.datetime')
    def test_calculate_next_collection_time_odds_task(self, mock_datetime):
        """测试赔率采集任务时间计算"""
        # 模拟当前时间 2025-09-28 15:32:00
        current_time = datetime(2025, 9, 28, 15, 32, 0)
        mock_datetime.now.return_value = current_time

        result = calculate_next_collection_time("collect_odds_task")

        # 应该是下一个5分钟整点: 15:35:00
        expected = datetime(2025, 9, 28, 15, 35, 0)
        assert result == expected

    @patch('src.tasks.utils.datetime')
    def test_calculate_next_collection_time_odds_task_hour_boundary(self, mock_datetime):
        """测试赔率采集任务跨小时边界"""
        # 模拟当前时间 2025-09-28 15:58:00
        current_time = datetime(2025, 9, 28, 15, 58, 0)
        mock_datetime.now.return_value = current_time

        result = calculate_next_collection_time("collect_odds_task")

        # 应该是下一个5分钟整点: 16:00:00
        expected = datetime(2025, 9, 28, 16, 0, 0)
        assert result == expected

    @patch('src.tasks.utils.datetime')
    def test_calculate_next_collection_time_scores_task(self, mock_datetime):
        """测试比分采集任务时间计算"""
        # 模拟当前时间 2025-09-28 15:31:00
        current_time = datetime(2025, 9, 28, 15, 31, 0)
        mock_datetime.now.return_value = current_time

        result = calculate_next_collection_time("collect_scores_task")

        # 应该是下一个2分钟整点: 15:32:00
        expected = datetime(2025, 9, 28, 15, 32, 0)
        assert result == expected

    @patch('src.tasks.utils.datetime')
    def test_calculate_next_collection_time_unknown_task(self, mock_datetime):
        """测试未知任务类型"""
        current_time = datetime(2025, 9, 28, 15, 30, 0)
        mock_datetime.now.return_value = current_time

        result = calculate_next_collection_time("unknown_task")

        # 应该是1小时后
        expected = datetime(2025, 9, 28, 16, 30, 0)
        assert result == expected


class TestCleanupStaleTasks:
    """测试清理过期任务"""

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_cleanup_stale_tasks_success(self, mock_db_manager):
        """测试成功清理过期任务"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5  # 清理了5条记录
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        result = await cleanup_stale_tasks()

        assert result == 5
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

        # 验证SQL查询
        call_args = mock_session.execute.call_args[0][0]
        assert "DELETE FROM error_logs" in str(call_args)
        assert "7 days" in str(call_args)

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_cleanup_stale_tasks_no_rowcount(self, mock_db_manager):
        """测试没有rowcount属性的情况"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        # 模拟没有rowcount属性
        del mock_result.rowcount
        mock_session.execute.return_value = mock_result

        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

        result = await cleanup_stale_tasks()

        assert result == 0

    @pytest.mark.asyncio
    @patch('src.tasks.utils.DatabaseManager')
    async def test_cleanup_stale_tasks_with_exception(self, mock_db_manager):
        """测试异常处理"""
        mock_db_manager.return_value.get_async_session.side_effect = Exception("Cleanup failed")

        result = await cleanup_stale_tasks()

        assert result == 0  # 异常时返回0


class TestGetTaskPriority:
    """测试获取任务优先级"""

    def test_get_task_priority_scores_task(self):
        """测试比分采集任务优先级"""
        priority = get_task_priority("collect_scores_task")
        assert priority == 1  # 最高优先级

    def test_get_task_priority_odds_task(self):
        """测试赔率采集任务优先级"""
        priority = get_task_priority("collect_odds_task")
        assert priority == 2  # 中等优先级

    def test_get_task_priority_fixtures_task(self):
        """测试赛程采集任务优先级"""
        priority = get_task_priority("collect_fixtures_task")
        assert priority == 3  # 较低优先级

    def test_get_task_priority_unknown_task(self):
        """测试未知任务优先级"""
        priority = get_task_priority("unknown_task")
        assert priority == 5  # 默认优先级

    @pytest.mark.parametrize("task_name,expected_priority", [
        ("collect_scores_task", 1),
        ("collect_odds_task", 2),
        ("collect_fixtures_task", 3),
        ("unknown_task", 5),
        ("another_unknown_task", 5),
    ])
    def test_get_task_priority_parametrized(self, task_name, expected_priority):
        """参数化测试任务优先级"""
        priority = get_task_priority(task_name)
        assert priority == expected_priority


@pytest.fixture
def mock_database_session():
    """模拟数据库会话fixture"""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_upcoming_match_data():
    """示例即将到来比赛数据fixture"""
    return [
        {
            "id": 1001,
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 10,
            "match_time": "2025-09-28T16:00:00",
            "match_status": "scheduled"
        },
        {
            "id": 1002,
            "home_team_id": 3,
            "away_team_id": 4,
            "league_id": 10,
            "match_time": "2025-09-28T18:30:00",
            "match_status": "scheduled"
        }
    ]


@pytest.fixture
def sample_active_leagues():
    """示例活跃联赛fixture"""
    return ["Premier League", "La Liga", "Serie A", "Bundesliga"]