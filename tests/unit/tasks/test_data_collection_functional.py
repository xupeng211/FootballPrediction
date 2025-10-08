"""
data_collection_tasks功能测试
测试数据收集任务的实际业务逻辑
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.mark.unit
class TestDataCollectionTasksFunctional:
    """数据收集任务功能测试"""

    @pytest.fixture
    def mock_collector(self):
        """创建模拟的数据收集器"""
        collector = MagicMock()
        collector.collect_data = AsyncMock()
        collector.validate_data = MagicMock()
        return collector

    @pytest.fixture
    def mock_storage(self):
        """创建模拟的数据存储"""
        storage = MagicMock()
        storage.save_data = AsyncMock()
        storage.check_existing = AsyncMock()
        return storage

    def test_collect_fixtures_task_validation(self):
        """测试收集赛程任务的数据验证"""
        try:
            from src.tasks.data_collection_tasks import collect_fixtures_task

            # 测试无效参数
            with pytest.raises(ValueError) as exc_info:
                asyncio.run(collect_fixtures_task(league_id=-1))
            assert "league_id" in str(exc_info.value).lower()

            with pytest.raises(ValueError) as exc_info:
                asyncio.run(collect_fixtures_task(league_id=0))
            assert "league_id" in str(exc_info.value).lower()

        except ImportError:
            pytest.skip("Data collection tasks not available")

    @pytest.mark.asyncio
    async def test_collect_fixtures_task_success(self, mock_collector, mock_storage):
        """测试成功收集赛程数据"""
        try:
            from src.tasks.data_collection_tasks import collect_fixtures_task

            # 设置mock返回值
            mock_storage.check_existing.return_value = False
            mock_collector.collect_data.return_value = [
                {
                    "id": 1,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "date": "2024-01-01",
                },
                {
                    "id": 2,
                    "home_team": "Team C",
                    "away_team": "Team D",
                    "date": "2024-01-02",
                },
            ]
            mock_collector.validate_data.return_value = True
            mock_storage.save_data.return_value = True

            with patch(
                "src.tasks.data_collection_tasks.FixturesCollector",
                return_value=mock_collector,
            ), patch(
                "src.tasks.data_collection_tasks.DataLakeStorage",
                return_value=mock_storage,
            ):
                result = await collect_fixtures_task(league_id=39)

                assert result["success"] is True
                assert result["collected"] == 2
                assert "league_id" in result
                assert result["league_id"] == 39

        except ImportError:
            pytest.skip("Data collection tasks not available")

    @pytest.mark.asyncio
    async def test_collect_scores_task_with_date_range(
        self, mock_collector, mock_storage
    ):
        """测试按日期范围收集比分数据"""
        try:
            from src.tasks.data_collection_tasks import collect_scores_task

            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 1, 7)

            # 设置mock
            mock_collector.collect_data.return_value = [
                {
                    "match_id": 1,
                    "home_score": 2,
                    "away_score": 1,
                    "status": "completed",
                },
                {
                    "match_id": 2,
                    "home_score": 0,
                    "away_score": 0,
                    "status": "completed",
                },
            ]
            mock_storage.save_data.return_value = True

            with patch(
                "src.tasks.data_collection_tasks.ScoresCollector",
                return_value=mock_collector,
            ), patch(
                "src.tasks.data_collection_tasks.DataLakeStorage",
                return_value=mock_storage,
            ):
                result = await collect_scores_task(
                    start_date=start_date, end_date=end_date
                )

                assert result["success"] is True
                assert result["collected"] == 2
                assert "date_range" in result

        except ImportError:
            pytest.skip("Data collection tasks not available")

    @pytest.mark.asyncio
    async def test_collect_odds_task_error_handling(self, mock_collector, mock_storage):
        """测试收集赔率数据的错误处理"""
        try:
            from src.tasks.data_collection_tasks import collect_odds_task

            # 设置mock抛出异常
            mock_collector.collect_data.side_effect = Exception(
                "API rate limit exceeded"
            )

            with patch(
                "src.tasks.data_collection_tasks.OddsCollector",
                return_value=mock_collector,
            ):
                result = await collect_odds_task(bookmaker="bet365")

                assert result["success"] is False
                assert "error" in result
                assert "rate limit" in result["error"].lower()

        except ImportError:
            pytest.skip("Data collection tasks not available")

    def test_validate_collection_parameters(self):
        """测试收集参数验证函数"""
        try:
            from src.tasks.data_collection_tasks import validate_collection_params

            # 测试有效参数
            assert validate_collection_params(league_id=39) is True
            assert (
                validate_collection_params(
                    start_date=datetime.now(),
                    end_date=datetime.now() + timedelta(days=1),
                )
                is True
            )

            # 测试无效参数
            with pytest.raises(ValueError):
                validate_collection_params(league_id=-1)

            with pytest.raises(ValueError):
                validate_collection_params(
                    start_date=datetime.now(),
                    end_date=datetime.now() - timedelta(days=1),  # 结束日期早于开始日期
                )

        except ImportError:
            pytest.skip("Data collection tasks not available")

    @pytest.mark.asyncio
    async def test_batch_collection_task(self, mock_collector, mock_storage):
        """测试批量数据收集任务"""
        try:
            from src.tasks.data_collection_tasks import batch_collect_task

            tasks = [
                {"type": "fixtures", "league_id": 39},
                {"type": "scores", "date": "2024-01-01"},
                {"type": "odds", "bookmaker": "bet365"},
            ]

            # 设置mock
            mock_collector.collect_data.return_value = [{"id": 1, "data": "test"}]
            mock_storage.save_data.return_value = True

            with patch(
                "src.tasks.data_collection_tasks.get_collector",
                return_value=mock_collector,
            ), patch(
                "src.tasks.data_collection_tasks.DataLakeStorage",
                return_value=mock_storage,
            ):
                result = await batch_collect_task(tasks)

                assert result["success"] is True
                assert result["total_tasks"] == 3
                assert result["completed"] == 3
                assert len(result["results"]) == 3

        except ImportError:
            pytest.skip("Data collection tasks not available")

    @pytest.mark.asyncio
    async def test_data_deduplication(self, mock_storage):
        """测试数据去重功能"""
        try:
            from src.tasks.data_collection_tasks import deduplicate_data

            # 设置mock - 返回已存在的数据
            mock_storage.check_existing.return_value = True

            existing_data = [
                {"id": 1, "match_id": 100, "data": "existing"},
                {"id": 2, "match_id": 101, "data": "existing"},
                {"id": 3, "match_id": 102, "data": "new"},  # 新数据
            ]

            new_data = [
                {"id": 1, "match_id": 100, "data": "updated"},
                {"id": 3, "match_id": 102, "data": "new"},
                {"id": 4, "match_id": 103, "data": "new"},
            ]

            with patch(
                "src.tasks.data_collection_tasks.DataLakeStorage",
                return_value=mock_storage,
            ):
                result = await deduplicate_data(existing_data, new_data, "match_id")

                # 应该只保留新数据或更新的数据
                assert len(result) == 2  # ID 3和4是新的
                assert any(d["match_id"] == 103 for d in result)
                assert any(d["match_id"] == 102 for d in result)

        except ImportError:
            pytest.skip("Data collection tasks not available")

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, mock_collector):
        """测试重试机制"""
        try:
            from src.tasks.data_collection_tasks import collect_with_retry

            # 前两次失败，第三次成功
            call_count = 0

            async def failing_collect():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Temporary failure")
                return [{"id": 1, "data": "success"}]

            mock_collector.collect_data = failing_collect

            result = await collect_with_retry(mock_collector, max_retries=3)

            assert result["success"] is True
            assert call_count == 3  # 应该重试了2次

        except ImportError:
            pytest.skip("Data collection tasks not available")

    @pytest.mark.asyncio
    async def test_data_quality_check(self):
        """测试数据质量检查"""
        try:
            from src.tasks.data_collection_tasks import validate_data_quality

            # 测试有效数据
            valid_data = [
                {
                    "match_id": 1,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "score": "2-1",
                },
                {
                    "match_id": 2,
                    "home_team": "Team C",
                    "away_team": "Team D",
                    "score": "0-0",
                },
            ]

            result = await validate_data_quality(valid_data, data_type="match")
            assert result["valid"] is True
            assert result["errors"] == []

            # 测试无效数据
            invalid_data = [
                {"match_id": None, "home_team": "", "away_team": None},  # 缺少必要字段
                {"match_id": 2, "home_team": "Team C"},  # 缺少away_team
            ]

            result = await validate_data_quality(invalid_data, data_type="match")
            assert result["valid"] is False
            assert len(result["errors"]) > 0

        except ImportError:
            pytest.skip("Data collection tasks not available")

    def test_task_scheduling_config(self):
        """测试任务调度配置"""
        try:
            from src.tasks.data_collection_tasks import TASK_SCHEDULES

            # 检查配置存在
            assert isinstance(TASK_SCHEDULES, dict)
            assert "fixtures" in TASK_SCHEDULES
            assert "scores" in TASK_SCHEDULES
            assert "odds" in TASK_SCHEDULES

            # 检查调度配置格式
            for task_name, config in TASK_SCHEDULES.items():
                assert "schedule" in config
                assert "enabled" in config
                assert isinstance(config["enabled"], bool)

        except ImportError:
            pytest.skip("Task schedules not available")

    @pytest.mark.asyncio
    async def test_task_monitoring_metrics(self):
        """测试任务监控指标"""
        try:
            from src.tasks.data_collection_tasks import TaskMetrics, update_metrics

            metrics = TaskMetrics()

            # 更新指标
            update_metrics(metrics, "fixtures", success=True, duration=5.2)
            update_metrics(metrics, "fixtures", success=False, duration=1.1)
            update_metrics(metrics, "scores", success=True, duration=3.8)

            # 验证指标
            assert metrics.total_tasks == 3
            assert metrics.successful_tasks == 2
            assert metrics.failed_tasks == 1
            assert metrics.average_duration > 0

            # 获取特定任务的指标
            fixtures_metrics = metrics.get_task_metrics("fixtures")
            assert fixtures_metrics["total"] == 2
            assert fixtures_metrics["success_rate"] == 0.5

        except ImportError:
            pytest.skip("Task metrics not available")

    @pytest.mark.asyncio
    async def test_concurrent_collection_limits(self, mock_collector, mock_storage):
        """测试并发收集限制"""
        try:
            from src.tasks.data_collection_tasks import concurrent_collect_with_limit

            # 创建多个任务
            tasks = [{"type": "fixtures", "league_id": i} for i in range(10)]

            # 设置mock
            mock_collector.collect_data.return_value = [{"id": i, "data": "test"}]
            mock_storage.save_data.return_value = True

            with patch(
                "src.tasks.data_collection_tasks.get_collector",
                return_value=mock_collector,
            ), patch(
                "src.tasks.data_collection_tasks.DataLakeStorage",
                return_value=mock_storage,
            ):
                # 限制并发数为3
                result = await concurrent_collect_with_limit(tasks, max_concurrent=3)

                assert result["success"] is True
                assert result["total"] == 10
                assert result["completed"] == 10

        except ImportError:
            pytest.skip("Concurrent collection not available")
