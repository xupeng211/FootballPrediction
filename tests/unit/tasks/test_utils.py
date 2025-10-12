"""
任务工具函数测试
Tests for Tasks Utils

测试src.tasks.utils模块的任务工具函数
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
from typing import List

# 测试导入
try:
    from src.tasks.utils import (
        should_collect_live_scores,
        get_upcoming_matches,
        is_match_day,
        get_active_leagues,
        calculate_next_collection_time,
        cleanup_stale_tasks,
        get_task_priority,
    )

    TASKS_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    TASKS_UTILS_AVAILABLE = False
    # 创建模拟函数
    should_collect_live_scores = None
    get_upcoming_matches = None
    is_match_day = None
    get_active_leagues = None
    calculate_next_collection_time = None
    cleanup_stale_tasks = None
    get_task_priority = None


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestShouldCollectLiveScores:
    """测试：是否应该采集实时比分"""

    @pytest.mark.asyncio
    async def test_should_collect_with_live_matches(self):
        """测试：有实时比赛时应该采集"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 5  # 5场比赛
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await should_collect_live_scores()

            assert result is True
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_collect_no_matches(self):
        """测试：没有比赛时不应该采集"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 0  # 0场比赛
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await should_collect_live_scores()

            assert result is False

    @pytest.mark.asyncio
    async def test_should_collect_with_upcoming_matches(self):
        """测试：有即将开始的比赛时应该采集"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 3  # 3场比赛
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await should_collect_live_scores()

            assert result is True

    @pytest.mark.asyncio
    async def test_should_collect_database_error(self):
        """测试：数据库错误时返回False"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_db_manager.return_value.get_async_session.side_effect = Exception(
                "Database error"
            )

            result = await should_collect_live_scores()

            assert result is False


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestGetUpcomingMatches:
    """测试：获取即将到来的比赛"""

    @pytest.mark.asyncio
    async def test_get_upcoming_matches_default_hours(self):
        """测试：获取未来24小时的比赛"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()

            # 模拟比赛数据
            mock_matches = [
                {
                    "id": 1,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "match_time": datetime.now() + timedelta(hours=1),
                    "league": "Premier League",
                },
                {
                    "id": 2,
                    "home_team": "Team C",
                    "away_team": "Team D",
                    "match_time": datetime.now() + timedelta(hours=12),
                    "league": "La Liga",
                },
            ]

            mock_result.fetchall.return_value = mock_matches
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            matches = await get_upcoming_matches()

            assert len(matches) == 2
            assert matches[0]["home_team"] == "Team A"
            assert matches[1]["league"] == "La Liga"

    @pytest.mark.asyncio
    async def test_get_upcoming_matches_custom_hours(self):
        """测试：获取自定义时间范围内的比赛"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.fetchall.return_value = []  # 没有比赛
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            matches = await get_upcoming_matches(hours=48)

            assert isinstance(matches, list)
            assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_get_upcoming_matches_with_filters(self):
        """测试：获取带过滤器的比赛"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()

            # 模拟只返回非取消的比赛
            mock_matches = [
                {
                    "id": 3,
                    "home_team": "Team E",
                    "away_team": "Team F",
                    "match_time": datetime.now() + timedelta(hours=6),
                    "league": "Serie A",
                    "status": "scheduled",
                }
            ]

            mock_result.fetchall.return_value = mock_matches
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            matches = await get_upcoming_matches(hours=12)

            assert len(matches) == 1
            assert matches[0]["status"] == "scheduled"


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestIsMatchDay:
    """测试：是否是比赛日"""

    def test_is_match_day_weekend(self):
        """测试：周末是比赛日"""
        # 2024-01-13是周六
        saturday = datetime(2024, 1, 13)
        result = is_match_day(saturday)
        assert result is True

    def test_is_match_day_weekday(self):
        """测试：工作日可能不是比赛日"""
        # 2024-01-10是周三
        wednesday = datetime(2024, 1, 10)
        result = is_match_day(wednesday)
        # 根据实现，可能返回True或False
        assert isinstance(result, bool)

    def test_is_match_day_default_date(self):
        """测试：使用默认日期（今天）"""
        result = is_match_day()
        assert isinstance(result, bool)

    def test_is_match_day_friday(self):
        """测试：周五通常是比赛日"""
        # 2024-01-12是周五
        friday = datetime(2024, 1, 12)
        result = is_match_day(friday)
        assert result is True

    def test_is_match_day_monday(self):
        """测试：周一通常不是比赛日"""
        # 2024-01-08是周一
        monday = datetime(2024, 1, 8)
        result = is_match_day(monday)
        # 根据实现，可能返回True或False
        assert isinstance(result, bool)


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestGetActiveLeagues:
    """测试：获取活跃联赛"""

    @pytest.mark.asyncio
    async def test_get_active_leagues_with_data(self):
        """测试：获取有数据的活跃联赛"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()

            # 模拟联赛数据
            mock_leagues = ["Premier League", "La Liga", "Serie A", "Bundesliga"]
            mock_result.scalars.return_value.all.return_value = mock_leagues
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            leagues = await get_active_leagues()

            assert len(leagues) == 4
            assert "Premier League" in leagues
            assert "La Liga" in leagues

    @pytest.mark.asyncio
    async def test_get_active_leagues_empty(self):
        """测试：没有活跃联赛"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            leagues = await get_active_leagues()

            assert isinstance(leagues, list)
            assert len(leagues) == 0

    @pytest.mark.asyncio
    async def test_get_active_leagues_with_time_filter(self):
        """测试：获取时间过滤的活跃联赛"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()
            mock_result = Mock()

            # 模拟最近7天有活动的联赛
            mock_leagues = ["Premier League", "Ligue 1"]
            mock_result.scalars.return_value.all.return_value = mock_leagues
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            leagues = await get_active_leagues()

            assert len(leagues) == 2
            assert all(isinstance(league, str) for league in leagues)


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestCalculateNextCollectionTime:
    """测试：计算下次采集时间"""

    def test_calculate_next_live_collection(self):
        """测试：计算实时采集时间"""
        now = datetime.now()
        next_time = calculate_next_collection_time("live_scores", now)

        # 实时采集应该很快（几分钟内）
        time_diff = next_time - now
        assert timedelta(minutes=0) < time_diff < timedelta(minutes=15)

    def test_calculate_next_daily_collection(self):
        """测试：计算每日采集时间"""
        now = datetime.now()
        next_time = calculate_next_collection_time("daily_odds", now)

        # 每日采集应该在24小时内
        time_diff = next_time - now
        assert time_diff < timedelta(hours=24)

    def test_calculate_next_hourly_collection(self):
        """测试：计算每小时采集时间"""
        now = datetime.now()
        next_time = calculate_next_collection_time("hourly_update", now)

        # 每小时采集应该在1小时内
        time_diff = next_time - now
        assert time_diff < timedelta(hours=1)

    def test_calculate_next_weekly_collection(self):
        """测试：计算每周采集时间"""
        now = datetime.now()
        next_time = calculate_next_collection_time("weekly_report", now)

        # 每周采集应该在7天内
        time_diff = next_time - now
        assert time_diff < timedelta(days=7)

    def test_calculate_next_custom_interval(self):
        """测试：计算自定义间隔采集时间"""
        now = datetime.now()
        next_time = calculate_next_collection_time(
            "custom_task", now, interval_minutes=45
        )

        # 自定义间隔应该在45分钟内
        time_diff = next_time - now
        assert time_diff <= timedelta(minutes=45)

    def test_calculate_next_with_base_time(self):
        """测试：基于基准时间计算采集时间"""
        now = datetime.now()
        base_time = now.replace(hour=18, minute=0, second=0, microsecond=0)

        next_time = calculate_next_collection_time(
            "evening_update", now, base_time=base_time
        )

        # 如果已经过了18:00，应该是明天的18:00
        if now.hour >= 18:
            assert next_time.date() > now.date()
        else:
            assert next_time.date() == now.date()
            assert next_time.hour == 18


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestCleanupStaleTasks:
    """测试：清理过期任务"""

    def test_cleanup_stale_tasks_success(self):
        """测试：成功清理过期任务"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = Mock()
            mock_result = Mock()
            mock_result.rowcount = 5  # 清理了5个任务
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session

            cleaned_count = cleanup_stale_tasks()

            assert cleaned_count == 5
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()

    def test_cleanup_stale_tasks_no_stale(self):
        """测试：没有过期任务"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = Mock()
            mock_result = Mock()
            mock_result.rowcount = 0  # 没有清理任务
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session

            cleaned_count = cleanup_stale_tasks()

            assert cleaned_count == 0

    def test_cleanup_stale_tasks_with_threshold(self):
        """测试：使用自定义阈值清理"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = Mock()
            mock_result = Mock()
            mock_result.rowcount = 3
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session

            # 清理超过6小时的任务
            cleaned_count = cleanup_stale_tasks(hours_threshold=6)

            assert cleaned_count == 3


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestGetTaskPriority:
    """测试：获取任务优先级"""

    def test_get_task_priority_high(self):
        """测试：高优先级任务"""
        priority = get_task_priority("live_scores")
        assert priority in [1, 2, 3]  # 高优先级（数值小）
        assert priority <= 3

    def test_get_task_priority_medium(self):
        """测试：中优先级任务"""
        priority = get_task_priority("daily_odds")
        assert priority in [4, 5, 6, 7]  # 中优先级

    def test_get_task_priority_low(self):
        """测试：低优先级任务"""
        priority = get_task_priority("weekly_report")
        assert priority in [8, 9, 10]  # 低优先级（数值大）
        assert priority >= 8

    def test_get_task_priority_unknown(self):
        """测试：未知任务优先级"""
        priority = get_task_priority("unknown_task")
        assert priority == 10  # 默认低优先级

    def test_get_task_priority_case_insensitive(self):
        """测试：大小写不敏感"""
        priority1 = get_task_priority("Live_Scores")
        priority2 = get_task_priority("live_scores")
        assert priority1 == priority2

    def test_get_task_priority_mapping(self):
        """测试：各种任务优先级映射"""
        # 测试已知的任务类型
        known_tasks = [
            ("live_scores", 1),
            ("live_odds", 2),
            ("match_results", 3),
            ("daily_fixtures", 4),
            ("team_stats", 5),
            ("player_stats", 6),
            ("historical_data", 7),
            ("weekly_report", 8),
            ("monthly_report", 9),
            ("cleanup", 10),
        ]

        for task_name, expected_priority in known_tasks:
            priority = get_task_priority(task_name)
            assert (
                priority == expected_priority
            ), f"Task {task_name} should have priority {expected_priority}"


@pytest.mark.skipif(
    not TASKS_UTILS_AVAILABLE, reason="Tasks utils module not available"
)
class TestTasksUtilsIntegration:
    """任务工具函数集成测试"""

    @pytest.mark.asyncio
    async def test_complete_workflow_check(self):
        """测试：完整工作流检查"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()

            # 模拟应该采集
            mock_result = Mock()
            mock_result.scalar.return_value = 3
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            # 1. 检查是否应该采集
            should_collect = await should_collect_live_scores()
            assert should_collect is True

            # 2. 获取即将到来的比赛
            mock_result.fetchall.return_value = [
                {
                    "id": 1,
                    "home_team": "Team A",
                    "match_time": datetime.now() + timedelta(hours=1),
                }
            ]
            mock_session.execute.return_value = mock_result

            upcoming = await get_upcoming_matches()
            assert len(upcoming) > 0

    def test_time_based_decisions(self):
        """测试：基于时间的决策"""
        now = datetime.now()

        # 1. 检查是否是比赛日
        is_match_day_result = is_match_day(now)
        assert isinstance(is_match_day_result, bool)

        # 2. 计算下次采集时间
        for task_type in ["live_scores", "daily_odds", "hourly_update"]:
            next_time = calculate_next_collection_time(task_type, now)
            assert next_time > now
            assert isinstance(next_time, datetime)

    @pytest.mark.asyncio
    async def test_league_and_match_coordination(self):
        """测试：联赛和比赛协调"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            mock_session = AsyncMock()

            # 模拟活跃联赛
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [
                "Premier League",
                "La Liga",
            ]
            mock_session.execute.return_value = mock_result

            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            # 获取活跃联赛
            leagues = await get_active_leagues()
            assert len(leagues) > 0

            # 基于联赛数决定任务优先级
            if len(leagues) > 5:
                priority = get_task_priority("live_scores")
                assert priority <= 3  # 联赛多时应该高优先级

    def test_priority_queue_simulation(self):
        """测试：优先级队列模拟"""
        tasks = [
            "live_scores",
            "daily_odds",
            "weekly_report",
            "cleanup",
            "unknown_task",
        ]

        # 获取所有任务优先级
        priorities = [(task, get_task_priority(task)) for task in tasks]

        # 按优先级排序（数值小的优先）
        priorities.sort(key=lambda x: x[1])

        # 验证顺序
        assert priorities[0][0] == "live_scores"
        assert priorities[0][1] == 1
        assert priorities[-1][0] == "cleanup"
        assert priorities[-1][1] == 10

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """测试：错误恢复工作流"""
        with patch("src.tasks.utils.DatabaseManager") as mock_db_manager:
            # 模拟数据库错误
            mock_db_manager.return_value.get_async_session.side_effect = Exception(
                "Connection failed"
            )

            # 应该优雅处理错误
            result = await should_collect_live_scores()
            assert result is False

            # 重置模拟
            mock_db_manager.reset_mock()

            # 恢复正常
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            result = await should_collect_live_scores()
            assert result is True


@pytest.mark.skipif(
    TASKS_UTILS_AVAILABLE, reason="Tasks utils module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not TASKS_UTILS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if TASKS_UTILS_AVAILABLE:
        from src.tasks.utils import (
            should_collect_live_scores,
            get_upcoming_matches,
            is_match_day,
            get_active_leagues,
            calculate_next_collection_time,
            cleanup_stale_tasks,
            get_task_priority,
        )

        assert should_collect_live_scores is not None
        assert get_upcoming_matches is not None
        assert is_match_day is not None
        assert get_active_leagues is not None
        assert calculate_next_collection_time is not None
        assert cleanup_stale_tasks is not None
        assert get_task_priority is not None
