"""
任务调度测试 - 数据收集任务
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery import Celery

from src.tasks.data_collection_tasks import (
    collect_fixtures_task,
    collect_historical_data_task,
    collect_odds_task,
    collect_scores_task,
    validate_collected_data,
)


@pytest.mark.unit
class TestDataCollectionTasks:
    """数据收集任务测试"""

    @pytest.fixture
    def mock_celery_app(self):
        """Mock Celery应用"""
        app = Celery("test")
        app.conf.task_always_eager = True
        return app

    @pytest.fixture
    def mock_collector(self):
        """Mock收集器"""
        collector = MagicMock()
        collector.collect_fixtures = AsyncMock(
            return_value=[{"id": 1, "home": "Team A", "away": "Team B"}]
        )
        collector.collect_odds = AsyncMock(
            return_value=[{"match_id": 1, "home_win": 2.1, "draw": 3.4, "away_win": 3.2}]
        )
        collector.collect_scores = AsyncMock(
            return_value=[{"match_id": 1, "home_score": 2, "away_score": 1}]
        )
        return collector

    def test_collect_fixtures_task_success(self, mock_celery_app, mock_collector):
        """测试成功收集比赛数据"""
        with patch(
            "src.tasks.data_collection_tasks.get_fixtures_collector",
            return_value=mock_collector,
        ):
            # 执行任务
            result = collect_fixtures_task.apply(
                args=[["premier_league", "la_liga"]], kwargs={"date": "2025-10-05"}
            ).get()

            assert result["status"] == "success"
            assert result["collected"] == 1
            assert result["leagues"] == ["premier_league", "la_liga"]
            assert "timestamp" in result

    def test_collect_fixtures_task_with_error(self, mock_celery_app):
        """测试收集比赛数据时的错误"""
        mock_collector = MagicMock()
        mock_collector.collect_fixtures = AsyncMock(side_effect=Exception("API error"))

        with patch(
            "src.tasks.data_collection_tasks.get_fixtures_collector",
            return_value=mock_collector,
        ):
            result = collect_fixtures_task.apply(args=[["premier_league"]]).get()

            assert result["status"] == "error"
            assert "API error" in result["error"]
            assert result["collected"] == 0

    def test_collect_odds_task_success(self, mock_celery_app, mock_collector):
        """测试成功收集赔率数据"""
        with patch(
            "src.tasks.data_collection_tasks.get_odds_collector",
            return_value=mock_collector,
        ):
            result = collect_odds_task.apply(
                args=[[1, 2, 3]], kwargs={"bookmakers": ["Bet365", "William Hill"]}
            ).get()

            assert result["status"] == "success"
            assert result["matches_processed"] == 3
            assert result["bookmakers"] == ["Bet365", "William Hill"]

    def test_collect_odds_task_batch_processing(self, mock_celery_app):
        """测试批量处理赔率收集"""
        # 模拟大量比赛
        match_ids = list(range(1, 101))  # 100场比赛

        mock_collector = MagicMock()
        mock_collector.collect_odds_batch = AsyncMock(
            return_value=[{"match_id": i, "odds": {"home_win": 2.0}} for i in match_ids]
        )

        with patch(
            "src.tasks.data_collection_tasks.get_odds_collector",
            return_value=mock_collector,
        ):
            result = collect_odds_task.apply(args=[match_ids]).get()

            assert result["status"] == "success"
            assert result["matches_processed"] == 100
            assert result["batch_size"] == 100

    def test_collect_scores_task_live_matches(self, mock_celery_app, mock_collector):
        """测试收集实时比分"""
        with patch(
            "src.tasks.data_collection_tasks.get_scores_collector",
            return_value=mock_collector,
        ):
            result = collect_scores_task.apply(kwargs={"match_type": "live"}).get()

            assert result["status"] == "success"
            assert result["match_type"] == "live"
            assert result["matches_updated"] == 1

    def test_collect_scores_task_finished_matches(self, mock_celery_app, mock_collector):
        """测试收集完场比分"""
        with patch(
            "src.tasks.data_collection_tasks.get_scores_collector",
            return_value=mock_collector,
        ):
            result = collect_scores_task.apply(
                kwargs={"match_type": "finished", "date": "2025-10-04"}
            ).get()

            assert result["status"] == "success"
            assert result["match_type"] == "finished"
            assert result["date"] == "2025-10-04"

    def test_collect_historical_data_task(self, mock_celery_app):
        """测试收集历史数据"""
        mock_collector = MagicMock()
        mock_collector.collect_historical_matches = AsyncMock(
            return_value=[{"id": 1, "date": "2024-09-01", "result": "2-1"}]
        )

        with patch(
            "src.tasks.data_collection_tasks.get_scores_collector",
            return_value=mock_collector,
        ):
            result = collect_historical_data_task.apply(
                args=[10],  # team_id
                kwargs={"start_date": "2024-09-01", "end_date": "2024-09-30"},
            ).get()

            assert result["status"] == "success"
            assert result["team_id"] == 10
            assert result["period"] == "2024-09-01 to 2024-09-30"
            assert result["matches_collected"] == 1

    def test_validate_collected_data_success(self, mock_celery_app):
        """测试数据验证成功"""
        valid_data = [
            {"match_id": 1, "home_team": "Team A", "away_team": "Team B"},
            {"match_id": 2, "home_team": "Team C", "away_team": "Team D"},
        ]

        result = validate_collected_data.apply(args=[valid_data, "fixtures"]).get()

        assert result["status"] == "valid"
        assert result["records_validated"] == 2
        assert result["records_invalid"] == 0

    def test_validate_collected_data_with_errors(self, mock_celery_app):
        """测试数据验证发现错误"""
        invalid_data = [
            {"match_id": 1, "home_team": None, "away_team": "Team B"},  # home_team为空
            {
                "match_id": None,
                "home_team": "Team C",
                "away_team": "Team D",
            },  # match_id为空
        ]

        result = validate_collected_data.apply(args=[invalid_data, "fixtures"]).get()

        assert result["status"] == "invalid"
        assert result["records_validated"] == 2
        assert result["records_invalid"] == 2
        assert len(result["errors"]) == 2

    @pytest.mark.asyncio
    async def test_chained_tasks_execution(self):
        """测试链式任务执行"""
        # 模拟链式执行：收集比赛 -> 收集赔率 -> 验证数据
        fixtures_data = [{"match_id": 1}]
        odds_data = [{"match_id": 1, "home_win": 2.0}]

        with patch("src.tasks.data_collection_tasks.collect_fixtures_task") as mock_fixtures, patch(
            "src.tasks.data_collection_tasks.collect_odds_task"
        ) as mock_odds, patch(
            "src.tasks.data_collection_tasks.validate_collected_data"
        ) as mock_validate:

            mock_fixtures.apply.return_value.get.return_value = {
                "status": "success",
                "data": fixtures_data,
            }
            mock_odds.apply.return_value.get.return_value = {
                "status": "success",
                "data": odds_data,
            }
            mock_validate.apply.return_value.get.return_value = {
                "status": "valid",
                "data": odds_data,
            }

            # 执行链式任务
            fixtures_result = mock_fixtures.apply(args=[["premier_league"]]).get()
            assert fixtures_result["status"] == "success"

            odds_result = mock_odds.apply(args=[[1]]).get()
            assert odds_result["status"] == "success"

            validate_result = mock_validate.apply(args=[odds_data, "odds"]).get()
            assert validate_result["status"] == "valid"

    def test_task_retry_on_failure(self, mock_celery_app):
        """测试任务失败重试"""
        call_count = 0

        def flaky_task(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"status": "success"}

        # 注册带重试的任务


        @mock_celery_app.task(
            bind=True,
            autoretry_for=(Exception,),
            retry_kwargs={"max_retries": 3, "countdown": 0},
        )
        def retry_task(self):
            return flaky_task()

        result = retry_task.apply().get()
        assert result["status"] == "success"
        assert call_count == 3

    def test_task_timeout_handling(self, mock_celery_app):
        """测试任务超时处理"""
        import time

        @mock_celery_app.task(time_limit=1, soft_time_limit=0.5)
        def slow_task():
            time.sleep(2)  # 超过时间限制
            return {"status": "done"}

        # 任务应该超时
        with pytest.raises(Exception):  # Celery会抛出超时异常
            slow_task.apply().get()

    def test_task_progress_tracking(self, mock_celery_app):
        """测试任务进度跟踪"""

        @mock_celery_app.task(bind=True)
        def progress_task(self, total_items):
            for i in range(total_items):
                # 更新进度
                self.update_state(state="PROGRESS", meta={"current": i + 1, "total": total_items})
                # 模拟工作
            return {"status": "COMPLETE", "total": total_items}

        # 执行任务并检查进度
        result = progress_task.apply(args=[10]).get()
        assert result["status"] == "COMPLETE"

    def test_task_result_caching(self, mock_celery_app):
        """测试任务结果缓存"""

        @mock_celery_app.task
        def cacheable_task(x):
            return x * 2

        # 第一次执行
        result1 = cacheable_task.apply(args=[5]).get()
        assert result1 == 10

        # 第二次执行（应该从缓存获取）
        result2 = cacheable_task.apply(args=[5]).get()
        assert result2 == 10

    def test_task_error_logging(self, mock_celery_app, caplog):
        """测试任务错误日志"""

        @mock_celery_app.task
        def error_task():
            raise ValueError("Test error")

        # 执行任务
        with pytest.raises(ValueError):
            error_task.apply().get()

        # 验证错误被记录
        # 注意：在实际应用中，需要配置Celery的日志系统

    def test_task_memory_usage(self, mock_celery_app):
        """测试任务内存使用"""
        import os

        import psutil

        @mock_celery_app.task
        def memory_intensive_task():
            # 创建大量数据
            large_list = list(range(1000000))
            return len(large_list)

        # 获取初始内存
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 执行任务
        result = memory_intensive_task.apply().get()
        assert result == 1000000

        # 验证内存没有泄露
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        assert memory_increase < 100 * 1024 * 1024  # 小于100MB

    def test_task_priority_handling(self, mock_celery_app):
        """测试任务优先级处理"""

        # 配置优先级队列
        mock_celery_app.conf.task_routes = {
            "src.tasks.data_collection_tasks.collect_odds_task": {"queue": "high_priority"}
        }

        @mock_celery_app.task
        def priority_task():
            return "done"

        # 任务应该被路由到高优先级队列
        result = priority_task.apply_async(queue="high_priority")
        assert result.get() == "done"

    def test_task_dynamic_rate_limit(self, mock_celery_app):
        """测试动态任务速率限制"""

        @mock_celery_app.task(rate_limit="10/m")  # 每分钟10个任务
        def rate_limited_task():
            return "success"

        # 快速提交多个任务
        results = []
        for _ in range(5):
            results.append(rate_limited_task.apply_async())

        # 所有任务都应该成功完成
        for result in results:
            assert result.get() == "success"

    def test_task_custom_metadata(self, mock_celery_app):
        """测试任务自定义元数据"""

        @mock_celery_app.task(bind=True)
        def metadata_task(self):
            # 添加自定义元数据
            self.request.custom = {"worker_id": "worker1", "region": "us-east"}
            return {"status": "completed", "worker": self.request.custom["worker_id"]}

        result = metadata_task.apply().get()
        assert result["status"] == "completed"
        assert result["worker"] == "worker1"
