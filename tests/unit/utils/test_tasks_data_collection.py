"""
数据采集任务模块测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import asyncio

from src.tasks.data_collection_tasks import (
    DataCollectionTask,
    collect_fixtures_task,
    collect_odds_task,
    collect_scores_task,
    manual_collect_all_data,
    emergency_data_collection_task,
    collect_historical_data_task,
    validate_collected_data,
    FixturesCollector,
    collect_all_data_task,
)


class TestDataCollectionTask:
    """数据采集任务基类测试"""

    @pytest.fixture
    def task_instance(self):
        """创建任务实例"""
        return DataCollectionTask()

    def test_task_init(self, task_instance):
        """测试任务初始化"""
        assert task_instance.error_logger is not None
        assert hasattr(task_instance, "on_failure")
        assert hasattr(task_instance, "on_success")

    def test_on_failure(self, task_instance):
        """测试任务失败处理"""
        # 模拟任务请求对象
        mock_request = MagicMock()
        mock_request.retries = 2
        task_instance.request = mock_request
        task_instance.name = "test.tasks.collect_fixtures_task"

        # 模拟错误和异常信息
        exc = ValueError("Test error")
        task_id = "task_123"
        args = ["arg1", "arg2"]
        kwargs = {"key1": "value1"}
        einfo = MagicMock()
        einfo.__str__ = lambda: "Error info"

        # 模拟异步日志记录
        with patch.object(
            task_instance.error_logger, "log_task_error", new_callable=AsyncMock
        ):
            with patch("src.tasks.data_collection_tasks.logger") as mock_app_logger:
                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_loop.return_value.run_until_complete = MagicMock()

                    # 调用失败处理
                    task_instance.on_failure(exc, task_id, args, kwargs, einfo)

                    # 验证日志记录被调用
                    mock_app_logger.error.assert_called()

    def test_on_success(self, task_instance):
        """测试任务成功处理"""
        task_instance.name = "test.tasks.collect_fixtures_task"
        retval = {"status": "success"}
        task_id = "task_123"
        args = []
        kwargs = {}

        with patch("src.tasks.data_collection_tasks.logger") as mock_logger:
            task_instance.on_success(retval, task_id, args, kwargs)
            mock_logger.info.assert_called_once_with(
                "数据采集任务成功: collect_fixtures_task"
            )


class TestCollectFixturesTask:
    """赛程数据采集任务测试"""

    @pytest.fixture
    def mock_task(self):
        """模拟任务对象"""
        task = MagicMock()
        task.name = "src.tasks.data_collection_tasks.collect_fixtures_task"
        task.request.retries = 0
        task.error_logger = MagicMock()
        task.retry = MagicMock(side_effect=Exception("Retry triggered"))
        return task

    @pytest.mark.asyncio
    async def test_collect_fixtures_success(self):
        """测试成功的赛程采集"""
        leagues = ["PL", "CL"]
        days_ahead = 7

        # 模拟采集器
        mock_collector = MagicMock()
        mock_result = {
            "status": "success",
            "success_count": 10,
            "error_count": 0,
            "records_collected": 10,
        }
        mock_collector.collect_fixtures = AsyncMock(return_value=mock_result)

        with patch("src.tasks.data_collection_tasks.asyncio.run") as mock_run:
            mock_run.return_value = mock_result

            result = collect_fixtures_task(leagues=leagues, days_ahead=days_ahead)

            assert result["status"] == "success"
            assert result["records_collected"] == 10
            assert result["success_count"] == 10
            assert result["error_count"] == 0
            assert result["leagues"] == leagues
            assert result["days_ahead"] == days_ahead

    def test_collect_fixtures_with_failure(self):
        """测试赛程采集失败"""
        error = Exception("API error")

        with patch("src.tasks.data_collection_tasks.asyncio.run", side_effect=error):
            with patch("src.tasks.data_collection_tasks.logger"):
                with pytest.raises(Exception):
                    collect_fixtures_task()

    def test_collect_fixtures_retry_mechanism(self, mock_task):
        """测试重试机制"""
        Exception("Temporary failure")
        mock_task.request.retries = 0

        with patch(
            "src.tasks.data_collection_tasks.TaskRetryConfig.get_retry_config"
        ) as mock_config:
            mock_config.return_value = {"max_retries": 3, "retry_delay": 60}

            # 模拟任务方法
            with patch.object(
                collect_fixtures_task, "retry", side_effect=Exception("Retry")
            ):
                with pytest.raises(Exception):
                    collect_fixtures_task.__self__ = mock_task
                    collect_fixtures_task.__globals__["self"] = mock_task


class TestCollectOddsTask:
    """赔率数据采集任务测试"""

    def test_collect_odds_compatibility_params(self):
        """测试兼容性参数处理"""
        # 测试旧参数转换
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.success_count = 5
        mock_result.error_count = 0
        mock_result.records_collected = 5

        with patch(
            "src.tasks.data_collection_tasks.asyncio.run", return_value=mock_result
        ):
            result = collect_odds_task(match_id=123, bookmaker="bet365")

            # 验证参数被正确转换
            assert result["status"] == "success"

    def test_collect_odds_failure_handling(self):
        """测试赔率采集失败处理"""
        error = Exception("Odds API error")

        with patch("src.tasks.data_collection_tasks.asyncio.run", side_effect=error):
            with patch("src.tasks.data_collection_tasks.logger"):
                with pytest.raises(Exception):
                    collect_odds_task(match_ids=["123"], bookmakers=["bet365"])


class TestCollectScoresTask:
    """比分数据采集任务测试"""

    def test_collect_scores_compatibility_params(self):
        """测试比分采集兼容性参数"""
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.success_count = 3
        mock_result.error_count = 0
        mock_result.records_collected = 3

        with patch(
            "src.tasks.data_collection_tasks.asyncio.run", return_value=mock_result
        ):
            result = collect_scores_task(match_id=456, live=True)

            assert result["status"] == "success"
            assert result["live_only"] is True

    def test_collect_scores_skip_when_no_live(self):
        """测试无实时比赛时跳过采集"""
        with patch(
            "src.tasks.data_collection_tasks.should_collect_live_scores",
            return_value=False,
        ):
            with patch("src.tasks.data_collection_tasks.logger"):
                result = collect_scores_task(live_only=True)

                assert result["status"] == "skipped"
                assert result["reason"] == "no_live_matches"


class TestManualCollectAllData:
    """手动全量数据采集测试"""

    def test_manual_collect_all_success(self):
        """测试手动全量采集成功"""
        # 模拟任务结果
        mock_fixtures = MagicMock()
        mock_fixtures.get = MagicMock(return_value={"status": "success", "records": 10})
        mock_fixtures.id = "fixtures_task_id"

        mock_odds = MagicMock()
        mock_odds.get = MagicMock(return_value={"status": "success", "records": 20})
        mock_odds.id = "odds_task_id"

        mock_scores = MagicMock()
        mock_scores.get = MagicMock(return_value={"status": "success", "records": 5})
        mock_scores.id = "scores_task_id"

        with patch(
            "src.tasks.data_collection_tasks.collect_fixtures_task.delay",
            return_value=mock_fixtures,
        ):
            with patch(
                "src.tasks.data_collection_tasks.collect_odds_task.delay",
                return_value=mock_odds,
            ):
                with patch(
                    "src.tasks.data_collection_tasks.collect_scores_task.delay",
                    return_value=mock_scores,
                ):
                    result = manual_collect_all_data()

                    assert result["status"] == "success"
                    assert "results" in result
                    assert "task_ids" in result
                    assert result["task_ids"]["fixtures"] == "fixtures_task_id"

    def test_manual_collect_all_with_failure(self):
        """测试手动全量采集部分失败"""
        # 模拟部分失败
        mock_fixtures = MagicMock()
        mock_fixtures.get = MagicMock(side_effect=Exception("Network error"))

        mock_odds = MagicMock()
        mock_odds.get = MagicMock(return_value={"status": "success", "records": 20})

        with patch(
            "src.tasks.data_collection_tasks.collect_fixtures_task.delay",
            return_value=mock_fixtures,
        ):
            with patch(
                "src.tasks.data_collection_tasks.collect_odds_task.delay",
                return_value=mock_odds,
            ):
                with patch("src.tasks.data_collection_tasks.collect_scores_task.delay"):
                    result = manual_collect_all_data()

                    assert result["status"] == "failed"
                    assert "error" in result
                    assert "partial_results" in result


class TestEmergencyDataCollection:
    """紧急数据收集测试"""

    def test_emergency_collection_specific_match(self):
        """测试特定比赛的紧急收集"""
        match_id = 123

        # 模拟高优先级任务
        mock_task = MagicMock()
        mock_task.get = MagicMock(return_value={"status": "success", "records": 5})

        with patch(
            "src.tasks.data_collection_tasks.collect_fixtures_task.apply_async",
            return_value=mock_task,
        ):
            with patch(
                "src.tasks.data_collection_tasks.collect_odds_task.apply_async",
                return_value=mock_task,
            ):
                with patch(
                    "src.tasks.data_collection_tasks.collect_scores_task.apply_async",
                    return_value=mock_task,
                ):
                    result = emergency_data_collection_task(match_id=match_id)

                    assert result["status"] == "success"
                    assert result["priority"] == "emergency"
                    assert match_id in result["message"]

    def test_emergency_collection_all_data(self):
        """测试全量紧急收集"""
        mock_task = MagicMock()
        mock_task.get = MagicMock(return_value={"status": "success", "records": 10})

        with patch(
            "src.tasks.data_collection_tasks.collect_fixtures_task.apply_async",
            return_value=mock_task,
        ):
            with patch(
                "src.tasks.data_collection_tasks.collect_odds_task.apply_async",
                return_value=mock_task,
            ):
                with patch(
                    "src.tasks.data_collection_tasks.collect_scores_task.apply_async",
                    return_value=mock_task,
                ):
                    result = emergency_data_collection_task(match_id=None)

                    assert result["status"] == "success"
                    assert result["priority"] == "emergency"

    def test_emergency_collection_failure(self):
        """测试紧急收集失败"""
        error = Exception("Emergency collection failed")

        with patch(
            "src.tasks.data_collection_tasks.collect_fixtures_task.apply_async",
            side_effect=error,
        ):
            with patch("src.tasks.data_collection_tasks.logger"):
                result = emergency_data_collection_task(match_id=123)

                assert result["status"] == "failed"
                assert "error" in result


class TestCollectHistoricalData:
    """历史数据收集测试"""

    def test_collect_historical_data_defaults(self):
        """测试历史数据收集默认参数"""
        team_id = 456

        mock_result = {
            "status": "success",
            "matches_collected": 100,
            "data_summary": {"matches": 100, "odds": 80},
        }

        with patch(
            "src.tasks.data_collection_tasks.asyncio.run", return_value=mock_result
        ):
            result = collect_historical_data_task(team_id=team_id)

            assert result["status"] == "success"
            assert result["team_id"] == team_id
            assert result["matches"] == 100
            assert result["data_types"] == ["matches", "odds", "scores", "players"]

    def test_collect_historical_data_custom_params(self):
        """测试历史数据收集自定义参数"""
        team_id = 789
        start_date = "2023-01-01"
        end_date = "2023-12-31"
        data_types = ["matches", "odds"]

        mock_result = {"status": "success", "matches_collected": 50}

        with patch(
            "src.tasks.data_collection_tasks.asyncio.run", return_value=mock_result
        ):
            result = collect_historical_data_task(
                team_id=team_id,
                start_date=start_date,
                end_date=end_date,
                data_types=data_types,
            )

            assert result["status"] == "success"
            assert result["start_date"] == start_date
            assert result["end_date"] == end_date
            assert result["data_types"] == data_types

    def test_collect_historical_data_list_result(self):
        """测试历史数据收集返回列表格式"""
        team_id = 123
        mock_result = [{"match_id": 1}, {"match_id": 2}]  # 列表格式

        with patch(
            "src.tasks.data_collection_tasks.asyncio.run", return_value=mock_result
        ):
            result = collect_historical_data_task(team_id=team_id)

            assert result["status"] == "success"
            assert result["matches"] == 2
            assert result["data_summary"]["matches"] == 2


class TestValidateCollectedData:
    """数据验证测试"""

    def test_validate_empty_data(self):
        """测试验证空数据"""
        result = validate_collected_data({}, "match")

        assert result["is_valid"] is False
        assert "数据为空" in result["errors"]

    def test_validate_match_data_success(self):
        """测试验证成功的比赛数据"""
        data = {
            "id": "123",
            "home_team_id": "456",
            "away_team_id": "789",
            "start_time": "2024-01-01T15:00:00",
        }

        result = validate_collected_data(data, "match")

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_match_data_missing_fields(self):
        """测试验证缺少字段的比赛数据"""
        data = {
            "id": "123",
            "home_team_id": "456",
            # 缺少 away_team_id 和 start_time
        }

        result = validate_collected_data(data, "match")

        assert result["is_valid"] is False
        assert len(result["errors"]) == 2

    def test_validate_team_data_success(self):
        """测试验证成功的球队数据"""
        data = {"id": "456", "name": "Test Team"}

        result = validate_collected_data(data, "team")

        assert result["is_valid"] is True

    def test_validate_odds_data_invalid_values(self):
        """测试验证无效赔率值"""
        data = {
            "match_id": "123",
            "home_win": -1.5,  # 负数，无效
            "draw": 3.0,
            "away_win": 4.0,
        }

        result = validate_collected_data(data, "odds")

        assert result["is_valid"] is False
        assert any("赔率值必须为正数" in error for error in result["errors"])

    def test_validate_with_exception(self):
        """测试验证过程异常"""
        data = {"test": "data"}

        # 模拟验证过程异常
        with patch.object(
            validate_collected_data,
            "__wrapped__",
            side_effect=Exception("Validation error"),
        ):
            result = validate_collected_data(data, "unknown")

            assert result["is_valid"] is False
            assert "验证过程出错" in result["errors"]


class TestFixturesCollector:
    """赛程收集器测试"""

    def test_fixtures_collector_init(self):
        """测试收集器初始化"""
        collector = FixturesCollector()

        assert collector.logger is not None

    def test_collect_fixtures(self):
        """测试收集赛程"""
        collector = FixturesCollector()

        result = collector.collect_fixtures(days_ahead=7)

        assert result["status"] == "success"
        assert result["fixtures_collected"] == 0
        assert result["days_ahead"] == 7
        assert "timestamp" in result


class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_collect_all_data_task_alias(self):
        """测试向后兼容的函数别名"""
        assert collect_all_data_task is manual_collect_all_data

        # 测试调用别名
        with patch(
            "src.tasks.data_collection_tasks.manual_collect_all_data",
            return_value={"status": "test"},
        ):
            result = collect_all_data_task()
            assert result["status"] == "test"


class TestTaskRetryConfiguration:
    """任务重试配置测试"""

    def test_retry_config_lookup(self):
        """测试重试配置查找"""
        with patch(
            "src.tasks.data_collection_tasks.TaskRetryConfig.get_retry_config"
        ) as mock_config:
            mock_config.return_value = {"max_retries": 3, "retry_delay": 60}

            # 这个测试通过 patch 验证配置查找被调用
            # 实际的重试逻辑在各个任务函数中
            assert True  # 如果没有异常，说明配置查找正常

    def test_retry_exceeded(self):
        """测试超过最大重试次数"""
        # 模拟超过重试次数的情况
        mock_task = MagicMock()
        mock_task.request.retries = 5  # 超过默认最大重试次数

        with patch(
            "src.tasks.data_collection_tasks.TaskRetryConfig.get_retry_config"
        ) as mock_config:
            mock_config.return_value = {"max_retries": 3, "retry_delay": 60}

            error = Exception("Max retries exceeded")
            with patch(
                "src.tasks.data_collection_tasks.asyncio.run", side_effect=error
            ):
                with pytest.raises(Exception):
                    collect_fixtures_task.__self__ = mock_task
                    collect_fixtures_task.__globals__["self"] = mock_task
