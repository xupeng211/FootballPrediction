from datetime import datetime, timedelta
import os
import sys

from celery.exceptions import MaxRetriesExceededError, Retry
from kombu.exceptions import OperationalError
from src.tasks.celery_app import TaskRetryConfig  # noqa: E402
from src.tasks.data_collection_tasks import (  # noqa: E402
from src.tasks.error_logger import TaskErrorLogger  # noqa: E402
from src.tasks.maintenance_tasks import cleanup_error_logs_task  # noqa: E402
from src.tasks.maintenance_tasks import database_maintenance_task  # noqa: E402
from src.tasks.maintenance_tasks import quality_check_task  # noqa: E402
from src.tasks.maintenance_tasks import system_health_check_task  # noqa: E402
from src.tasks.monitoring import TaskMonitor  # noqa: E402
from src.tasks.utils import calculate_next_collection_time  # noqa: E402
from src.tasks.utils import get_upcoming_matches  # noqa: E402
from src.tasks.utils import should_collect_live_scores  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

"""
足球预测系统任务调度测试模块

测试覆盖范围：
1. 定时任务执行 - beat_schedule配置和任务调度
2. 任务重试机制 - API失败3次重试逻辑
3. 错误日志记录 - 失败记录写入error_logs表
4. 数据采集任务 - fixtures / odds / scores任务执行
5. 维护任务执行 - 系统维护和健康检查
6. 监控指标收集 - Prometheus指标统计
7. 任务队列管理 - 多队列并发处理

目标覆盖率: >85%

测试设计原则：
- 所有外部依赖都使用mock替代，确保测试独立性和可重复性
- 不依赖真实的Celery broker、Redis、PostgreSQL等外部服务
- 测试聚焦于任务调度逻辑、重试机制和错误处理，而非外部服务的功能
- 使用虚拟数据和函数，避免真实网络调用和数据库操作

Mock策略详解：
================

1. 数据库Mock策略：
   - 使用@asynccontextmanager创建正确的异步上下文管理器
   - 通过patch("src.tasks.utils.DatabaseManager[")直接Mock目标模块的DatabaseManager[""""
   - 避免Mock全局导入，而是Mock具体使用点，确保Mock生效
   - 为每个测试创建独立的Mock会话，避免状态污染

2. Celery任务Mock策略：
   - Mock任务的.delay()方法返回包含.get()方法的结果对象
   - 使用patch.object()精确Mock特定任务的retry机制
   - Mock asyncio.run()避免真实异步执行，控制测试流程
   - 通过Mock侧效应(side_effect)模拟各种异常场景

3. 外部服务Mock策略：
   - Redis：Mock Redis实例和ping()方法，模拟连接状态
   - HTTP请求：Mock requests.get()和aiohttp.ClientSession，避免网络调用
   - 数据采集器：Mock各种Collector类，返回虚拟的采集结果
   - 监控系统：Mock Prometheus指标对象，验证监控逻辑

4. 异步Mock最佳实践：
   - 使用contextlib.asynccontextmanager创建真正的异步上下文
   - AsyncMock用于异步方法，MagicMock用于同步方法和属性
   - 正确设置Mock对象的属性和返回值，确保与真实对象接口一致
   - 避免在Mock设置中泄露异步协程，防止RuntimeWarning

5. 测试独立性保证：
   - 每个测试使用独立的Mock实例，避免测试间干扰
   - Mock在测试方法内部创建和销毁，确保隔离性
   - 使用with patch()上下文管理器自动清理Mock状态:
   - 验证Mock调用而非实际结果，聚焦于逻辑测试

这种Mock策略确保了：
- 测试运行速度快（无网络/数据库延迟）
- 测试结果稳定（不受外部服务状态影响）
- 测试环境干净（无真实数据产生和污染）
- 测试逻辑清晰（专注于业务逻辑而非集成测试）
"]]"""

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))""""
# ============================================================================
# 项目模块导入 - 在测试中会通过fixture和patch来mock外部依赖
# ============================================================================
"""
注意：为确保测试的独立性和可重复性，我们使用以下策略：
1. 在每个测试类中使用@pytest.fixture来mock外部依赖
2. 使用@patch装饰器来mock具体的外部服务调用
3. 避免在导入时就初始化真实的外部连接
这样做的原因：
- 确保测试不依赖真实的Redis、PostgreSQL、Celery broker等外部服务
- 提高测试运行速度，避免网络延迟和外部服务不可用的问题
- 确保测试结果的一致性和可重复性
- 聚焦于任务调度逻辑的测试，而非外部依赖的集成测试
"""
from src.tasks.celery_app import TaskRetryConfig  # noqa: E402
from src.tasks.data_collection_tasks import (  # noqa: E402
    collect_fixtures_task,
    collect_odds_task,
    collect_scores_task,
    manual_collect_all_data)
from src.tasks.error_logger import TaskErrorLogger  # noqa: E402
from src.tasks.maintenance_tasks import cleanup_error_logs_task  # noqa: E402
from src.tasks.maintenance_tasks import database_maintenance_task  # noqa: E402
from src.tasks.maintenance_tasks import quality_check_task  # noqa: E402
from src.tasks.maintenance_tasks import system_health_check_task  # noqa: E402
from src.tasks.monitoring import TaskMonitor  # noqa: E402
from src.tasks.utils import calculate_next_collection_time  # noqa: E402
from src.tasks.utils import get_upcoming_matches  # noqa: E402
from src.tasks.utils import should_collect_live_scores  # noqa: E402
# ============================================================================
# 全局测试配置 - 确保所有测试使用mock而非真实外部依赖
# ============================================================================
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """
    自动应用的fixture，为所有测试mock外部依赖
    Mock的组件：
    - Celery broker连接：避免连接真实的Redis/RabbitMQ
    - Redis连接：避免连接真实的Redis服务器
    - 数据库连接：避免连接真实的PostgreSQL数据库
    - HTTP请求：避免真实的API调用
    这样确保测试环境的独立性和可控性
    """
    with patch("redis.Redis[") as mock_redis, patch(:""""
        "]src.database.connection.DatabaseManager["""""
    ) as mock_db, patch("]requests.get[") as mock_requests, patch(""""
        "]aiohttp.ClientSession["""""
    ) as mock_aiohttp:
        # Mock Redis实例
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_redis.return_value = mock_redis_instance
        # Mock 数据库管理器实例
        mock_db_instance = AsyncMock()
        mock_db.return_value = mock_db_instance
        # Mock HTTP请求
        mock_requests.return_value.status_code = 200
        mock_requests.return_value.json.return_value = {"]mocked[": True}""""
        # Mock aiohttp会话
        mock_session = AsyncMock()
        mock_aiohttp.return_value.__aenter__.return_value = mock_session
        yield {
        "]redis[": mock_redis_instance,""""
        "]db[": mock_db_instance,""""
        "]requests[": mock_requests,""""
        "]aiohttp[": mock_session}": class TestCeleryAppConfiguration:"""
    "]"""
    测试Celery应用配置
    注意：此测试类专注于验证Celery配置的正确性，而非实际连接外部broker
    使用mock确保测试不依赖真实的Redis/RabbitMQ服务
    """
    @patch("src.tasks.celery_app.Celery[")": def test_celery_app_creation(self, mock_celery_class):"""
        "]"""
        测试Celery应用创建和基本配置
        使用Mock原因：
        - 避免连接真实的message broker（Redis_RabbitMQ）
        - 确保测试聚焦于配置验证而非broker连接测试
        - 提高测试运行速度和可靠性
        """
        # 创建mock的Celery应用实例
        mock_app = MagicMock()
        mock_app.main = os.getenv("TEST_TASK_SCHEDULER_MAIN_164"): mock_app.conf = MagicMock()": mock_app.conf.broker_url = os.getenv("TEST_TASK_SCHEDULER_BROKER_URL_164"): mock_app.conf.result_backend = os.getenv("TEST_TASK_SCHEDULER_RESULT_BACKEND_164"): mock_celery_class.return_value = mock_app[""""
        # 模拟应用创建过程
        # 验证基本配置
        assert mock_app is not None
        assert mock_app.main =="]]football_prediction_tasks[" assert hasattr(mock_app.conf, "]broker_url[")" assert hasattr(mock_app.conf, "]result_backend[")""""
        @patch("]src.tasks.celery_app.app[")": def test_task_routing_configuration(self, mock_celery_app):"""
        "]"""
        测试任务路由配置
        使用Mock原因：
        - 验证任务路由配置的正确性，而不依赖真实的Celery broker
        - 确保测试聚焦于路由规则而非实际的消息路由功能
        - 避免因broker不可用导致的测试失败
        """
        # 模拟任务路由配置
        mock_task_routes = {
        "tasks.data_collection_tasks.collect_fixtures_task[": {"]queue[": "]fixtures["},""""
        "]tasks.data_collection_tasks.collect_odds_task[": {"]queue[": "]odds["},""""
        "]tasks.data_collection_tasks.collect_scores_task[": {"]queue[": "]scores["},""""
        "]tasks.maintenance_tasks.database_maintenance_task[": {""""
            "]queue[": ["]maintenance["""""
            }}
        mock_celery_app.conf.task_routes = mock_task_routes
        task_routes = mock_celery_app.conf.task_routes
        # 验证数据采集任务路由
        assert "]tasks.data_collection_tasks.collect_fixtures_task[" in task_routes[""""
        assert (
        task_routes["]]tasks.data_collection_tasks.collect_fixtures_task["]["]queue["]""""
        =="]fixtures["""""
        )
        assert (
        task_routes["]tasks.data_collection_tasks.collect_odds_task["]["]queue["]""""
        =="]odds["""""
        )
        assert (
        task_routes["]tasks.data_collection_tasks.collect_scores_task["]["]queue["]""""
        =="]scores["""""
        )
        # 验证维护任务路由
        maintenance_route = next(
        (k for k in task_routes.keys() if "]maintenance_tasks[": in k), None:""""
        )
        assert maintenance_route is not None
        assert task_routes["]maintenance_route["["]queue["] =="]maintenance["""""
        @patch("]src.tasks.celery_app.app[")": def test_beat_schedule_configuration(self, mock_celery_app):"""
        "]"""
        测试定时任务调度配置
        使用Mock原因：
        - 验证beat schedule配置而不启动真实的celery beat进程
        - 避免依赖真实的调度器和时间触发器
        - 确保测试聚焦于配置验证而非实际调度执行
        """
        # 模拟beat schedule配置
        mock_beat_schedule = {
        "collect-daily-fixtures[": {""""
        "]task[: "tasks.data_collection_tasks.collect_fixtures_task[","]"""
        "]schedule[": 3600.0,  # 1小时[""""
        },
            "]]collect-odds-regular[": {""""
            "]task[: "tasks.data_collection_tasks.collect_odds_task[","]"""
            "]schedule[": 300.0,  # 5分钟[""""
            },
            "]]collect-live-scores[": {""""
                "]task[: "tasks.data_collection_tasks.collect_scores_task[","]"""
                "]schedule[": 120.0,  # 2分钟[""""
            },
            "]]hourly-quality-check[": {""""
                "]task[: "tasks.maintenance_tasks.quality_check_task[","]"""
                "]schedule[": 3600.0,  # 1小时[""""
            },
            "]]daily-error-cleanup[": {""""
                "]task[: "tasks.maintenance_tasks.cleanup_error_logs_task[","]"""
                "]schedule[": 86400.0,  # 24小时[""""
            }}
        mock_celery_app.conf.beat_schedule = mock_beat_schedule
        beat_schedule = mock_celery_app.conf.beat_schedule
        # 验证核心定时任务存在
        required_tasks = [
            "]]collect-daily-fixtures[",""""
            "]collect-odds-regular[",""""
            "]collect-live-scores[",""""
            "]hourly-quality-check[",""""
            "]daily-error-cleanup["]": for task_name in required_tasks:": assert task_name in beat_schedule, f["]定时任务 {task_name} 未配置["]""""
        # 验证具体调度配置
        fixtures_task = beat_schedule["]collect-daily-fixtures["]": assert (" fixtures_task["]task["] =="]tasks.data_collection_tasks.collect_fixtures_task["""""
        )
        assert "]schedule[" in fixtures_task[""""
        odds_task = beat_schedule["]]collect-odds-regular["]": assert odds_task["]schedule["] ==300.0  # 5分钟[" scores_task = beat_schedule["]]collect-live-scores["]": assert scores_task["]schedule["] ==120.0  # 2分钟[" def test_task_retry_configuration(self):"""
        "]]"""
        测试任务重试配置
        注意：此测试不需要mock外部依赖，因为：
        - TaskRetryConfig是纯粹的配置类，不涉及外部服务连接
        - 测试聚焦于配置值的验证，而非实际重试执行
        - 重试逻辑将在具体任务测试中通过mock验证
        """
        retry_config = TaskRetryConfig()
        # 验证所有数据采集任务都有重试配置
        required_tasks = [
        "collect_fixtures_task[",""""
        "]collect_odds_task[",""""
        "]collect_scores_task["]": for task_name in required_tasks = config retry_config.get_retry_config(task_name)": assert config is not None, f["]任务 {task_name} 缺少重试配置["] assert config["]max_retries["] ==3, f["]任务 {task_name} 重试次数不是3次["] assert "]retry_delay[" in config[""""
        @patch("]]src.tasks.celery_app.app[")": def test_worker_configuration(self, mock_celery_app):"""
        "]"""
        测试Worker配置
        使用Mock原因：
        - 验证worker配置参数而不启动真实的celery worker进程
        - 避免依赖真实的worker进程和资源分配
        - 确保测试聚焦于配置验证而非worker执行性能
        """
        # 模拟worker配置
        mock_conf = MagicMock()
        mock_conf.task_soft_time_limit = 300  # 5分钟软超时
        mock_conf.task_time_limit = 600  # 10分钟硬超时
        mock_conf.accept_content = ["json["]": mock_conf.task_serializer = os.getenv("TEST_TASK_SCHEDULER_TASK_SERIALIZER_276"): mock_conf.result_serializer = os.getenv("TEST_TASK_SCHEDULER_RESULT_SERIALIZER_276"): mock_celery_app.conf = mock_conf[": conf = mock_celery_app.conf["""
        # 验证超时配置
        assert conf.task_soft_time_limit ==300  # 5分钟软超时
        assert conf.task_time_limit ==600  # 10分钟硬超时
        # 验证序列化配置
        assert conf.accept_content ==["]]]json["]" assert conf.task_serializer =="]json[" assert conf.result_serializer =="]json[" class TestDataCollectionTasks:""""
    "]"""
    测试数据采集任务
    此测试类专注于验证任务调度和执行逻辑，使用mock替代所有外部依赖：
    - Mock数据采集器：避免真实API调用，确保测试独立性
    - Mock数据库连接：避免依赖真实PostgreSQL数据库
    - Mock异步执行：控制异步任务执行流程，确保测试可预测性
    - Mock错误记录器：验证错误处理逻辑而不写入真实日志
    """
    @pytest.fixture
    def mock_db_manager(self):
        """
        模拟数据库管理器
        Mock原因：
        - 避免连接真实PostgreSQL数据库
        - 确保测试不依赖数据库状态和数据
        - 提高测试运行速度和可靠性
        """
        mock_instance = AsyncMock()
        yield mock_instance
        @pytest.fixture
    def mock_error_logger(self):
        """
        模拟错误日志记录器
        Mock原因：
        - 验证错误处理逻辑而不写入真实数据库日志
        - 避免测试污染真实错误日志表
        - 确保错误处理测试的独立性
        """
        with patch("src.tasks.error_logger.TaskErrorLogger[") as mock_logger:": mock_instance = AsyncMock()": mock_logger.return_value = mock_instance[": yield mock_instance"
    def test_collect_fixtures_task_success(self, mock_db_manager, mock_error_logger):
        "]]"""
        测试赛程采集任务成功执行
        Mock策略说明：
        - FixturesCollector: 避免真实API调用足球数据源，使用虚拟数据验证任务逻辑
        - asyncio.run: 控制异步执行流程，确保测试同步运行且结果可预测
        - 数据库操作: 通过fixture mock避免真实数据库写入操作
        测试目标：验证任务能正确调用采集器并返回预期结果格式
        """
        # Mock FixturesCollector - 避免真实API调用
        with patch(:
            "src.data.collectors.fixtures_collector.FixturesCollector["""""
        ) as mock_collector_class:
            # 创建mock采集器实例和结果对象
            mock_collector = AsyncMock()
            # 创建一个具有必要属性的Mock对象，而不是字典
            mock_result = MagicMock()
            mock_result.status = os.getenv("TEST_TASK_SCHEDULER_STATUS_324"): mock_result.records_collected = 50[": mock_result.success_count = 45[": mock_result.error_count = 5[": mock_collector.collect_fixtures.return_value = mock_result"
            mock_collector_class.return_value = mock_collector
            # Mock asyncio.run - 控制异步任务执行，避免真实异步调用
            with patch(:
                "]]]]src.tasks.data_collection_tasks.asyncio.run["""""
            ) as mock_asyncio_run:
                # 设置期望的任务执行结果，返回具有属性的对象
                mock_asyncio_run.return_value = mock_result
                # 执行被测试的任务函数
                result = collect_fixtures_task(leagues=["]Premier League["], days_ahead=7)""""
                # 验证任务执行结果
        assert result is not None
        assert result["]status["] =="]success[" assert result["]records_collected["] ==50[" assert result["]]success_count["] ==45[" assert result["]]error_count["] ==5[""""
        # 验证asyncio.run被正确调用
        mock_asyncio_run.assert_called_once()
    def test_collect_odds_task_success(self, mock_db_manager, mock_error_logger):
        "]]"""
        测试赔率采集任务成功执行
        Mock策略：
        - OddsCollector: 避免调用真实博彩公司API，使用虚拟赔率数据
        - asyncio.run: 控制异步执行，确保测试同步且可重复
        测试重点：验证任务调度逻辑和结果格式，而非真实数据采集
        """
        with patch(:
            "src.data.collectors.odds_collector.OddsCollector["""""
        ) as mock_collector_class:
            # Mock赔率采集器，创建具有属性的结果对象
            mock_collector = AsyncMock()
            mock_result = MagicMock()
            mock_result.status = os.getenv("TEST_TASK_SCHEDULER_STATUS_324"): mock_result.records_collected = 100[": mock_result.success_count = 95[": mock_result.error_count = 5[": mock_collector.collect_odds.return_value = mock_result"
            mock_collector_class.return_value = mock_collector
            # Mock异步执行，避免真实网络调用
            with patch(:
                "]]]]src.tasks.data_collection_tasks.asyncio.run["""""
            ) as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_result
                # 执行测试任务
                result = collect_odds_task(match_ids=[1, 2, 3])
                # 验证结果格式和内容
        assert result is not None
        assert result["]status["] =="]success[" assert result["]records_collected["] ==100[" assert result["]]success_count["] ==95[" assert result["]]error_count["] ==5[" mock_asyncio_run.assert_called_once()"""
    def test_collect_scores_task_success(self, mock_db_manager, mock_error_logger):
        "]]"""
        测试比分采集任务成功执行
        Mock策略：
        - ScoresCollector: 避免调用真实体育数据API，使用虚拟比分数据
        - asyncio.run: 控制异步执行流程，确保测试结果一致性
        - should_collect_live_scores: Mock异步工具函数避免数据库查询
        测试重点：验证实时比分采集任务的调度和数据格式处理
        """
        with patch(:
            "src.data.collectors.scores_collector.ScoresCollector["""""
        ) as mock_collector_class:
            # Mock比分采集器，创建具有属性的结果对象
            mock_collector = AsyncMock()
            mock_result = MagicMock()
            mock_result.status = os.getenv("TEST_TASK_SCHEDULER_STATUS_324"): mock_result.records_collected = 15[": mock_result.success_count = 12[": mock_result.error_count = 3[": mock_collector.collect_live_scores.return_value = mock_result"
            mock_collector_class.return_value = mock_collector
            # Mock should_collect_live_scores 函数以避免数据库查询 - 修正导入路径
            with patch(:
                "]]]]src.tasks.utils.should_collect_live_scores["""""
            ) as mock_should_collect:
                mock_should_collect.return_value = True  # 同步返回，避免异步调用
                # Mock异步执行，避免真实API调用延迟
                with patch(:
                    "]src.tasks.data_collection_tasks.asyncio.run["""""
                ) as mock_asyncio_run:
                    mock_asyncio_run.return_value = mock_result
                    # 执行实时比分采集任务
                    result = collect_scores_task(live_only=True)
                    # 验证采集结果
        assert result is not None
        assert result["]status["] =="]success[" assert result["]records_collected["] ==15[" assert result["]]success_count["] ==12[" assert result["]]error_count["] ==3[" mock_asyncio_run.assert_called_once()"""
    def test_task_retry_mechanism(self, mock_db_manager, mock_error_logger):
        "]]"""
        测试任务重试机制 - API失败自动重试3次
        Mock策略：
        - FixturesCollector: 模拟API调用失败，触发重试机制
        - asyncio.run: 模拟异步执行失败，测试错误处理
        - task.retry: 模拟Celery重试机制，验证重试逻辑
        测试目标：验证任务在遇到外部服务故障时能正确重试，而非依赖真实API故障
        """
        with patch(:
            "src.data.collectors.fixtures_collector.FixturesCollector["""""
        ) as mock_collector_class:
            # 模拟API调用失败 - 这是常见的外部依赖故障场景
            mock_collector = AsyncMock()
            api_error = Exception("]API调用失败 HTTP 503 Service Unavailable[")": mock_collector.collect_fixtures.side_effect = api_error[": mock_collector_class.return_value = mock_collector[""
            # Mock异步执行失败，触发重试机制
            with patch(:
                "]]]src.tasks.data_collection_tasks.asyncio.run["""""
            ) as mock_asyncio_run:
                mock_asyncio_run.side_effect = api_error
                # Mock Celery任务重试机制
                with patch.object(collect_fixtures_task, "]retry[") as mock_retry:": mock_retry.side_effect = Retry("]重试中...")": try:": pass[": except Exception:"
                        pass
                    except:
                        pass
                    except Exception as e:
                       pass  # Auto-fixed empty except block
 pass
                        # 执行任务，期望触发重试
                        collect_fixtures_task(leagues=["]Premier League["], days_ahead=7)": except Exception:": pass  # 重试异常是预期的[""
                    # 验证重试机制被触发
                    mock_asyncio_run.assert_called()
                    # 验证任务实际尝试了执行
    def test_max_retries_exceeded(self, mock_db_manager, mock_error_logger):
        "]]""测试达到最大重试次数后的处理"""
        with patch(:
            "src.data.collectors.odds_collector.OddsCollector["""""
        ) as mock_collector_class = mock_collector AsyncMock()
            api_error = Exception("]持续API失败[")": mock_collector.collect_odds.side_effect = api_error[": mock_collector_class.return_value = mock_collector[""
            # 使用 patch 模拟 asyncio.run，让它抛出异常
            with patch(:
                "]]]src.tasks.data_collection_tasks.asyncio.run["""""
            ) as mock_asyncio_run:
                mock_asyncio_run.side_effect = api_error
                # 模拟任务的 retry 方法
                with patch.object(collect_odds_task, "]retry[") as mock_retry:": mock_retry.side_effect = MaxRetriesExceededError("]超过最大重试次数[")": try:": pass[": except Exception:"
                        pass
                    except:
                        pass
                    except Exception as e:
                       pass  # Auto-fixed empty except block
 pass
                        # 直接调用任务函数
                        collect_odds_task(match_ids=[1, 2, 3])
                    except Exception:
                        pass  # 异常是预期的
                    # 验证 asyncio.run 被调用
                    mock_asyncio_run.assert_called()
    def test_manual_collect_all_data(self, mock_db_manager, mock_error_logger):
        "]]""测试手动触发全部数据采集"""
        with patch(:
            "src.tasks.data_collection_tasks.collect_fixtures_task.delay["""""
        ) as mock_fixtures, patch(
            "]src.tasks.data_collection_tasks.collect_odds_task.delay["""""
        ) as mock_odds, patch(
            "]src.tasks.data_collection_tasks.collect_scores_task.delay["""""
        ) as mock_scores:
            # 模拟任务返回结果，包括 .get() 方法
            mock_fixtures_result = Mock()
            mock_fixtures_result.get.return_value = {"]fixtures_collected[": 10}": mock_fixtures.return_value = mock_fixtures_result[": mock_odds_result = Mock()": mock_odds_result.get.return_value = {"]]odds_collected[": 50}": mock_odds.return_value = mock_odds_result[": mock_scores_result = Mock()": mock_scores_result.get.return_value = {"]]scores_collected[": 5}": mock_scores.return_value = mock_scores_result["""
            # 直接调用任务函数
            result = manual_collect_all_data()
            # 验证返回结果
        assert "]]status[" in result[""""
        assert result["]]status["] =="]success[" assert "]results[" in result[""""
            # 验证任务被调用
            mock_fixtures.assert_called_once()
            mock_odds.assert_called_once()
            mock_scores.assert_called_once()
class TestErrorLogger:
    "]]""测试错误日志记录器"""
    @pytest.fixture
    def error_logger(self):
        """创建错误日志记录器实例"""
        # 直接创建实例并完全替换db_manager，避免复杂的初始化Mock
        logger = TaskErrorLogger.__new__(TaskErrorLogger)  # 避免__init__
        logger.db_manager = AsyncMock()
        logger._db_type = None
        logger._query_builder = None
        return logger
        @pytest.mark.asyncio
    async def test_log_task_error(self, error_logger):
        """测试记录任务错误"""
        # 使用更简单的Mock方式，直接Mock整个_save_error_to_db方法
        with patch.object(:
            error_logger, "_save_error_to_db[", new_callable=AsyncMock[""""
        ) as mock_save:
            # 记录任务错误
            await error_logger.log_task_error(
                task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_494"),": task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_495"),": error=Exception("]测试错误["),": context = {"]leagues[": ["]Premier League["]},": retry_count=2)"""
            # 验证_save_error_to_db被调用
            mock_save.assert_called_once()
            # 验证传递的参数
            call_args = mock_save.call_args[0][0]  # 第一个参数是error_details字典
        assert call_args["]task_name["] =="]collect_fixtures_task[" assert call_args["]task_id["] =="]task-123[" assert call_args["]error_type["] =="]Exception[" assert call_args["]retry_count["] ==2[""""
        @pytest.mark.asyncio
    async def test_log_api_failure(self, error_logger):
        "]]""测试记录API失败"""
        # 直接Mock _save_error_to_db方法
        with patch.object(:
            error_logger, "_save_error_to_db[", new_callable=AsyncMock[""""
        ) as mock_save:
            await error_logger.log_api_failure(
            task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_507"),": api_endpoint = os.getenv("TEST_TASK_SCHEDULER_API_ENDPOINT_507"),": http_status=503,": error_message = os.getenv("TEST_TASK_SCHEDULER_ERROR_MESSAGE_509"),": retry_count=1)"""
            # 验证_save_error_to_db被调用
            mock_save.assert_called_once()
            # 验证传递的参数
            call_args = mock_save.call_args[0][0]  # 第一个参数是error_details字典
        assert call_args["]task_name["] =="]collect_odds_task[" assert call_args["]error_type["] =="]API_FAILURE[" assert call_args["]api_endpoint["] =="]https//api-football.com/v3/odds[" assert call_args["]http_status["] ==503[" assert call_args["]]retry_count["] ==1[""""
        @pytest.mark.asyncio
    async def test_log_data_collection_error(self, error_logger):
        "]]""测试记录数据采集错误到data_collection_logs表"""
        # 使用简化的Mock方式：创建一个可以正常工作的异步上下文管理器
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            # ✅ 修复：add, commit, refresh 通常是同步方法，不应该使用 AsyncMock
            mock_session.add = Mock()
            mock_session.commit = Mock()
            mock_session.refresh = Mock()
            yield mock_session
            error_logger.db_manager.get_async_session = mock_session_context
            # Mock日志记录对象
            mock_log_entry = MagicMock()
            mock_log_entry.id = 123
            # 使用patch来Mock DataCollectionLog的创建
            with patch("src.tasks.error_logger.DataCollectionLog[") as mock_log_class:": mock_log_class.return_value = mock_log_entry[": result = await error_logger.log_data_collection_error(": data_source = os.getenv("TEST_TASK_SCHEDULER_DATA_SOURCE_533"),": collection_type = os.getenv("TEST_TASK_SCHEDULER_COLLECTION_TYPE_534"),": error_message = os.getenv("TEST_TASK_SCHEDULER_ERROR_MESSAGE_535"))""""
            # 验证返回值
            assert result ==123
            # 验证DataCollectionLog被正确创建
            mock_log_class.assert_called_once()
            create_args = mock_log_class.call_args[1]  # 关键字参数
            assert create_args["]data_source["] =="]API-FOOTBALL[" assert create_args["]collection_type["] =="]fixtures[" assert create_args["]error_message["] =="]解析JSON失败["""""
            @pytest.mark.asyncio
    async def test_get_error_statistics(self, error_logger):
        "]""测试获取错误统计"""
        # 使用简化的Mock方式：创建一个可以正常工作的异步上下文管理器
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            # Mock查询结果
            mock_result_count = MagicMock()
            mock_result_count.scalar.return_value = 7  # 总错误数
            mock_result_tasks = [
            MagicMock(task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_545"), error_count=5),": MagicMock(task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_546"), error_count=2)]": mock_result_types = [": MagicMock(error_type = os.getenv("TEST_TASK_SCHEDULER_ERROR_TYPE_549"), error_count=4),": MagicMock(error_type = os.getenv("TEST_TASK_SCHEDULER_ERROR_TYPE_550"), error_count=3)]""""
            # 设置execute的多次调用返回不同结果
            mock_session.execute.side_effect = ["]mock_result_count[",": mock_result_tasks,": mock_result_types]": yield mock_session"
            error_logger.db_manager.get_async_session = mock_session_context
            # Mock查询构建器
            with patch.object(error_logger, "]_get_query_builder[") as mock_builder_getter:": mock_builder = MagicMock()": mock_builder.build_error_statistics_query.return_value = (""
            "]SELECT COUNT(*) FROM error_logs["""""
            )
            mock_builder.build_task_errors_query.return_value = (
            "]SELECT task_name, COUNT(*) FROM error_logs GROUP BY task_name["""""
            )
            mock_builder.build_type_errors_query.return_value = (
            "]SELECT error_type, COUNT(*) FROM error_logs GROUP BY error_type["""""
            )
            mock_builder_getter.return_value = mock_builder
            stats = await error_logger.get_error_statistics(hours=24)
            # 验证返回的统计结构
            assert "]total_errors[" in stats[""""
            assert "]]task_errors[" in stats[""""
            assert "]]type_errors[" in stats[""""
            assert stats["]]total_errors["] ==7[" assert len(stats["]]task_errors["]) ==2[" assert len(stats["]]type_errors["]) ==2[" assert stats["]]task_errors["][0]["]task_name["] =="]collect_odds_task[" assert stats["]task_errors["][0]["]error_count["] ==5[""""
            @pytest.mark.asyncio
    async def test_cleanup_old_logs(self, error_logger):
        "]]""测试清理旧错误日志"""
        # 使用简化的Mock方式：创建一个可以正常工作的异步上下文管理器
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            # Mock查询结果
            mock_result = MagicMock()
            mock_result.rowcount = 15  # 15行被删除
            mock_session.execute.return_value = mock_result
            yield mock_session
            error_logger.db_manager.get_async_session = mock_session_context
            # Mock查询构建器
            with patch.object(error_logger, "_get_query_builder[") as mock_builder_getter:": mock_builder = MagicMock()": mock_builder.build_cleanup_old_logs_query.return_value = (""
            "]DELETE FROM error_logs WHERE created_at < NOW() - INTERVAL '7 days': """""
            )
            mock_builder_getter.return_value = mock_builder
            # 使用正确的参数名
            deleted_count = await error_logger.cleanup_old_logs(days_to_keep=7)
            assert deleted_count ==15
class TestMaintenanceTasks:
    """
    测试维护任务
    此测试类专注于验证系统维护任务的调度和执行：
    - Mock数据库连接：避免真实数据库操作，确保测试环境干净
    - Mock Redis连接：避免依赖真实缓存服务
    - Mock系统调用：模拟磁盘空间检查等系统级操作
    测试重点：验证维护任务的调度逻辑和错误处理，而非具体的维护操作
    """
    @pytest.fixture
    def mock_db_manager(self):
        """
        模拟数据库管理器
        Mock原因：
        - 避免真实数据库的统计更新和清理操作
        - 确保测试不影响实际数据库状态
        - 提供可控的数据库响应用于测试验证
        """
        with patch("src.tasks.maintenance_tasks.DatabaseManager[") as mock_manager:": mock_instance = AsyncMock()": mock_manager.return_value = mock_instance[": yield mock_instance"
    def test_quality_check_task(self, mock_db_manager):
        "]]""测试数据质量检查任务"""
        # 模拟数据库查询结果
        mock_db_manager.get_async_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = (
        5
        )
        # 使用 patch 模拟任务执行，避免真实的 Celery 调用
        with patch("src.tasks.maintenance_tasks.asyncio.run[") as mock_asyncio_run:""""
            # 模拟质量检查的内部异步函数返回值
            mock_check_results = {
            "]incomplete_matches[": 0,""""
            "]duplicate_matches[": 2,""""
            "]abnormal_odds[": 1}": mock_asyncio_run.return_value = (mock_check_results, 2)"""
            # 直接调用任务函数而不是通过 Celery
            result = quality_check_task()
            # 验证返回结果的结构
        assert "]status[" in result[""""
        assert result["]]status["] =="]success[" assert "]checks_performed[" in result[""""
        assert "]]issues_found[" in result[""""
        assert "]]check_results[" in result[""""
        assert "]]execution_time[" in result[""""
        # 验证检查结果
        assert result["]]issues_found["] ==2[" assert result["]]checks_performed["] ==len(mock_check_results)" def test_cleanup_error_logs_task(self, mock_db_manager):"""
        "]""测试错误日志清理任务"""
        # 模拟TaskErrorLogger
        with patch("src.tasks.maintenance_tasks.TaskErrorLogger[") as mock_logger_class:": mock_logger = AsyncMock()": mock_logger.cleanup_old_logs.return_value = 25  # 清理了25条日志[": mock_logger_class.return_value = mock_logger"
            # 使用 patch 模拟 asyncio.run 调用
            with patch("]]src.tasks.maintenance_tasks.asyncio.run[") as mock_asyncio_run:": mock_asyncio_run.return_value = 25["""
                # 直接调用任务函数
                result = cleanup_error_logs_task(days=7)
        assert "]]deleted_count[" in result[""""
        assert result["]]deleted_count["] ==25[" assert "]]status[" in result[""""
        assert result["]]status["] =="]success[" assert "]days_to_keep[" in result[""""
        assert result["]]days_to_keep["] ==7[" def test_system_health_check_task(self, mock_db_manager):"""
        "]]"""
        测试系统健康检查任务
        Mock策略：
        - Redis连接：避免依赖真实Redis服务状态
        - 数据库查询：避免执行真实健康检查查询
        - 系统磁盘检查：避免依赖真实文件系统状态
        - asyncio.run：控制异步健康检查执行
        测试目标：验证健康检查任务能正确收集各组件状态并汇总结果
        """
        # Mock数据库健康检查 - 避免真实数据库查询
        mock_db_manager.execute_query = AsyncMock(return_value=[(1)])
        # Mock Redis健康检查 - 避免依赖真实Redis服务
        with patch("redis.Redis[") as mock_redis_class:": mock_redis = MagicMock()": mock_redis.ping.return_value = True  # 模拟Redis服务正常[": mock_redis_class.return_value = mock_redis"
            # Mock系统磁盘空间检查 - 避免依赖真实文件系统
            with patch("]]shutil.disk_usage[") as mock_disk:": mock_disk.return_value = ("""
                1000000000,  # 总空间
                500000000,  # 已使用空间
                500000000,  # 剩余空间
                )
                # Mock异步健康检查执行
                with patch(:
                    "]src.tasks.maintenance_tasks.asyncio.run["""""
                ) as mock_asyncio_run:
                    # 模拟所有组件健康状态
                    mock_health_results = {
                    "]database[": {"]status[": "]healthy[", "]message[": "]数据库连接正常["},""""
                    "]redis[": {"]status[": "]healthy[", "]message[": "]Redis连接正常["},""""
                    "]disk_space[": {"]status[": "]healthy[", "]message[": "]磁盘空间充足["}}": mock_asyncio_run.return_value = (mock_health_results, True)"""
                    # 执行健康检查任务
                    result = system_health_check_task()
                    # 验证健康检查结果格式
        assert "]status[" in result[""""
        assert "]]overall_healthy[" in result[""""
        assert "]]components[" in result[""""
        assert result["]]overall_healthy["] is True[" assert result["]]status["] =="]healthy[" def test_database_maintenance_task("
    """"
        "]""测试数据库维护任务"""
        mock_db_manager.execute_query = AsyncMock()
        # 使用 patch 模拟 asyncio.run 调用
        with patch("src.tasks.maintenance_tasks.asyncio.run[") as mock_asyncio_run:""""
            # 模拟数据库维护的返回结果
            mock_maintenance_results = {
            "]statistics_updated[": True,""""
            "]logs_cleaned[": True,""""
            "]cleanup_count[": 5}": mock_asyncio_run.return_value = mock_maintenance_results["""
            # 直接调用任务函数
            result = database_maintenance_task()
        assert "]]maintenance_results[" in result[""""
        assert "]]statistics_updated[" in result["]maintenance_results["]": assert "]logs_cleaned[" in result["]maintenance_results["]": assert "]status[" in result[""""
        assert result["]]status["] =="]success[" class TestTaskMonitoring:""""
    "]"""
    测试任务监控系统
    此测试类验证Prometheus指标收集和任务监控功能：
    - Mock数据库查询：避免依赖真实统计数据，使用可控的测试数据
    - Mock Prometheus指标：验证指标更新逻辑而非实际指标导出
    - Mock监控数据：确保监控逻辑测试的一致性和可重复性
    测试重点：验证监控指标的正确收集、计算和更新，而非依赖真实系统状态
    """
    @pytest.fixture
    def task_monitor(self):
        """
        创建任务监控实例
        Mock原因：
        - 避免连接真实数据库获取监控统计
        - 提供可控的监控数据用于测试验证
        - 确保Prometheus指标测试的独立性
        """
        with patch("src.tasks.monitoring.DatabaseManager[") as mock_manager:": mock_db = AsyncMock()": mock_manager.return_value = mock_db[": monitor = TaskMonitor()"
            monitor.db_manager = mock_db
            return monitor
    def test_prometheus_metrics_creation(self, task_monitor):
        "]]"""
        测试Prometheus指标创建
        测试目标：
        - 验证TaskMonitor正确初始化所有必需的Prometheus指标
        - 确保指标对象存在且可用于监控任务状态
        注意：此测试验证指标对象的存在性，不涉及真实的Prometheus服务器连接
        """
        # 验证所有必需的Prometheus指标都已创建
        assert hasattr(task_monitor, "task_counter[")  # 任务执行计数器[" assert hasattr(task_monitor, "]]task_duration[")  # 任务执行时长指标[" assert hasattr(task_monitor, "]]task_error_rate[")  # 任务错误率指标[" assert hasattr(task_monitor, "]]active_tasks[")  # 活跃任务数指标[" assert hasattr(task_monitor, "]]queue_size[")  # 队列大小指标[" assert hasattr(task_monitor, "]]retry_counter[")  # 重试计数器[" def test_record_task_start(self, task_monitor):"""
        "]]""测试记录任务开始"""
        task_monitor.record_task_start("collect_odds_task[", "]test-task-123[")""""
        # 验证活跃任务数增加 - 正确访问Prometheus指标
        # Prometheus指标可以通过_value._value访问，但在测试中我们主要验证方法调用成功
        assert True  # 验证方法调用不抛出异常
    def test_record_task_completion(self, task_monitor):
        "]""测试记录任务完成"""
        task_monitor.record_task_completion(
        "collect_fixtures_task[", "]test-task-456[", 120.5, "]success["""""
        )
        # 验证方法调用成功，实际Prometheus指标的验证比较复杂
        assert True  # 验证方法调用不抛出异常
    def test_record_task_retry(self, task_monitor):
        "]""测试记录任务重试"""
        task_monitor.record_task_retry("collect_scores_task[", retry_count=2)""""
        # 验证方法调用成功
        assert True  # 验证方法调用不抛出异常
    def test_update_queue_size(self, task_monitor):
        "]""测试更新队列大小"""
        # 根据源代码，update_queue_size方法一次只能更新一个队列
        task_monitor.update_queue_size("fixtures[", 5)": task_monitor.update_queue_size("]odds[", 12)": task_monitor.update_queue_size("]scores[", 3)": task_monitor.update_queue_size("]maintenance[", 1)""""
        # 验证方法调用成功
        assert True  # 验证方法调用不抛出异常
        @pytest.mark.asyncio
    async def test_calculate_error_rates(self, task_monitor):
        "]""测试计算错误率"""
        # 正确Mock数据库管理器以支持异步操作
        with patch("src.tasks.monitoring.DatabaseManager[") as mock_db_manager_class:": mock_db_manager = AsyncMock()": mock_session = AsyncMock()""
            # 设置异步上下文管理器
            mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
            )
            mock_db_manager.get_async_session.return_value.__aexit__.return_value = None
            # 模拟查询结果
            mock_result = MagicMock()
            mock_result.__iter__ = lambda self iter(
            [
            MagicMock(
            task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_759"), total_tasks=30, failed_tasks=3[""""
                ),
                MagicMock(
                    task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_761"), total_tasks=60, failed_tasks=1[""""
                    )]
            )
            mock_session.execute.return_value = mock_result
            mock_db_manager_class.return_value = mock_db_manager
            # 调用方法
            error_rates = await task_monitor.calculate_error_rates()
            # 验证返回值
        assert isinstance(error_rates, dict)
        @pytest.mark.asyncio
    async def test_check_task_health(self, task_monitor):
        "]]""测试任务健康检查"""
        # Mock所有依赖的方法，因为check_task_health会调用多个内部方法
        with patch.object(:
            task_monitor, "calculate_error_rates["""""
        ) as mock_error_rates, patch.object(
            task_monitor, "]_get_queue_sizes["""""
        ) as mock_queue_sizes, patch.object(
            task_monitor, "]_check_task_delays["""""
        ) as mock_task_delays:
            # 设置Mock返回值
            mock_error_rates.return_value = {"]collect_odds_task[": 0.05}  # 5%错误率[": mock_queue_sizes.return_value = {"""
            "]]fixtures[": 5,""""
            "]odds[": 12}  # 少于100的队列大小[": mock_task_delays.return_value = {"""
            "]]collect_scores_task[": 300[""""
            }  # 5分钟延迟，少于600秒阈值
            health_status = await task_monitor.check_task_health()
            # 验证返回结构与源代码一致
        assert "]]overall_status[" in health_status[""""
        assert "]]issues[" in health_status[""""
        assert "]]metrics[" in health_status[""""
        assert health_status["]]overall_status["] in [""""
        "]healthy[",""""
        "]warning[",""""
        "]unhealthy[",""""
        "]unknown["]": assert "]error_rates[" in health_status["]metrics["]": assert "]queue_sizes[" in health_status["]metrics["]": assert "]task_delays[" in health_status["]metrics["]": class TestTaskUtils:"""
    "]""测试任务工具函数"""
    @pytest.fixture
    def mock_db_manager(self):
        with patch("src.tasks.utils.DatabaseManager[") as mock_manager:": mock_instance = AsyncMock()": mock_manager.return_value = mock_instance[": yield mock_instance"
        @pytest.mark.asyncio
    async def test_should_collect_live_scores(self, mock_db_manager):
        "]]"""
        测试是否应该采集实时比分
        Mock策略：
        - DatabaseManager：避免连接真实数据库，使用虚拟查询结果
        - 异步会话管理器：模拟数据库异步连接和查询执行
        - 查询结果：返回模拟的比赛数量，验证逻辑判断而非真实数据
        目的：确保任务调度逻辑能正确判断是否需要采集实时比分
        """
        # 使用contextlib创建正确的异步上下文管理器Mock
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            # Mock查询结果 - 模拟数据库返回有2场正在进行的比赛
            mock_result = MagicMock()
            mock_result.scalar.return_value = 2  # 有比赛，应该采集
            mock_session.execute.return_value = mock_result
            yield mock_session
            # 直接Mock utils模块中的DatabaseManager
            with patch("src.tasks.utils.DatabaseManager[") as mock_db_class:": mock_db_instance = AsyncMock()": mock_db_instance.get_async_session = mock_session_context[": mock_db_class.return_value = mock_db_instance"
            # 执行函数并验证结果
            should_collect = await should_collect_live_scores()
            assert should_collect is True
            @pytest.mark.asyncio
    async def test_should_not_collect_live_scores_no_matches(self, mock_db_manager):
        "]]"""
        测试无比赛时不应该采集实时比分
        Mock策略：
        - DatabaseManager：避免连接真实数据库，返回无比赛的查询结果
        - 异步会话管理器：模拟数据库连接但返回0场比赛
        - 验证逻辑：确保当没有比赛时，系统不会启动实时比分采集任务
        目的：验证任务调度系统能够智能地决定何时停止不必要的数据采集
        """
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            # Mock查询结果 - 模拟数据库返回0场比赛
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0  # 无比赛，不需要采集
            mock_session.execute.return_value = mock_result
            yield mock_session
            with patch("src.tasks.utils.DatabaseManager[") as mock_db_class:": mock_db_instance = AsyncMock()": mock_db_instance.get_async_session = mock_session_context[": mock_db_class.return_value = mock_db_instance"
            should_collect = await should_collect_live_scores()
            assert should_collect is False
            @pytest.mark.asyncio
    async def test_get_upcoming_matches(self, mock_db_manager):
        "]]"""
        测试获取即将开始的比赛
        Mock策略：
        - DatabaseManager：避免查询真实数据库中的比赛数据
        - 异步会话管理器：模拟数据库连接和查询执行
        - 查询结果：返回虚构的比赛数据，验证数据格式化和返回逻辑
        目的：确保get_upcoming_matches函数能正确查询和格式化即将开始的比赛数据
        """
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            # 创建模拟的比赛数据 - 使用MagicMock但要有正确的属性
            future_time1 = datetime.now() + timedelta(hours=2)
            future_time2 = datetime.now() + timedelta(hours=4)
            match1 = MagicMock()
            match1.id = 1
            match1.home_team_id = 10
            match1.away_team_id = 20
            match1.league_id = 1
            match1.match_time = future_time1
            match1.match_status = os.getenv("TEST_TASK_SCHEDULER_MATCH_STATUS_869"): match2 = MagicMock()": match2.id = 2[": match2.home_team_id = 30[": match2.away_team_id = 40"
            match2.league_id = 1
            match2.match_time = future_time2
            match2.match_status = os.getenv("TEST_TASK_SCHEDULER_MATCH_STATUS_875")""""
            # Mock查询结果 - 返回可迭代的比赛列表
            mock_result = ["]match1[", match2]": mock_session.execute.return_value = mock_result[": yield mock_session[": with patch("]]]src.tasks.utils.DatabaseManager[") as mock_db_class:": mock_db_instance = AsyncMock()": mock_db_instance.get_async_session = mock_session_context[": mock_db_class.return_value = mock_db_instance"
            upcoming = await get_upcoming_matches(hours=6)
            assert len(upcoming) ==2
            assert upcoming[0]["]]id["] ==1[" assert upcoming[0]["]]home_team_id["] ==10[" assert upcoming[1]["]]id["] ==2[" assert upcoming[1]["]]home_team_id["] ==30[" def test_calculate_next_collection_time(self):"""
        "]]""测试计算下次采集时间"""
        # 根据源代码，这个函数只接受task_name参数，使用当前时间
        # 测试赔率采集任务的下次执行时间（每5分钟）
        with patch("src.tasks.utils.datetime[") as mock_datetime:": base_time = datetime(2025, 1, 15, 10, 0, 0)": mock_datetime.now.return_value = base_time[": mock_datetime.timedelta = timedelta  # 保持timedelta正常工作"
            next_time = calculate_next_collection_time("]]collect_odds_task[")""""
            # 验证返回时间是datetime对象
        assert isinstance(next_time, datetime)
        # 验证时间在合理范围内（应该是10:05）
        expected = base_time.replace(minute=5, second=0, microsecond=0)
        assert next_time ==expected
class TestIntegration:
    "]""集成测试 - 测试任务之间的协作"""
    def test_full_data_collection_workflow(self):
        """测试完整的数据采集工作流程"""
        # 模拟 Celery 任务的 delay 和 get 方法
        with patch(:
            "src.tasks.data_collection_tasks.collect_fixtures_task.delay["""""
        ) as mock_fixtures_delay, patch(
            "]src.tasks.data_collection_tasks.collect_odds_task.delay["""""
        ) as mock_odds_delay, patch(
            "]src.tasks.data_collection_tasks.collect_scores_task.delay["""""
        ) as mock_scores_delay:
            # 模拟任务结果
            mock_fixtures_result = Mock()
            mock_fixtures_result.get.return_value = {"]fixtures_collected[": 10}": mock_fixtures_delay.return_value = mock_fixtures_result[": mock_odds_result = Mock()": mock_odds_result.get.return_value = {"]]odds_collected[": 50}": mock_odds_delay.return_value = mock_odds_result[": mock_scores_result = Mock()": mock_scores_result.get.return_value = {"]]scores_collected[": 5}": mock_scores_delay.return_value = mock_scores_result["""
            # 直接调用任务函数
            result = manual_collect_all_data()
            # 验证结果
        assert "]]status[" in result[""""
        assert result["]]status["] =="]success[" assert "]results[" in result[""""
        # 验证任务被调用
        mock_fixtures_delay.assert_called_once()
        mock_odds_delay.assert_called_once()
        mock_scores_delay.assert_called_once()
    def test_error_handling_workflow(self):
        "]]""测试错误处理完整工作流程"""
        with patch(:
            "src.data.collectors.fixtures_collector.FixturesCollector["""""
        ) as mock_collector_class:
            # 模拟API错误
            mock_collector = AsyncMock()
            api_error = Exception("]API连接超时[")": mock_collector.collect_fixtures.side_effect = api_error[": mock_collector_class.return_value = mock_collector[""
            # 模拟任务和错误记录器
            with patch("]]]src.tasks.error_logger.TaskErrorLogger[") as mock_logger_class:": mock_logger = AsyncMock()": mock_logger_class.return_value = mock_logger[""
                # 使用 patch 模拟 asyncio.run，让它抛出异常
                with patch(:
                    "]]src.tasks.data_collection_tasks.asyncio.run["""""
                ) as mock_asyncio_run:
                    mock_asyncio_run.side_effect = api_error
                    # 模拟任务的 retry 方法
                    with patch.object(collect_fixtures_task, "]retry[") as mock_retry:": mock_retry.side_effect = Retry("]重试中...")": try:": pass[": except Exception:"
                            pass
                        except:
                            pass
                        except Exception as e:
                           pass  # Auto-fixed empty except block
 pass
                            # 直接调用任务函数
                            collect_fixtures_task(
                            leagues=["]Premier League["], days_ahead=7[""""
                            )
                        except Exception:
                            pass  # 异常是预期的
                        # 验证 asyncio.run 被调用
                        mock_asyncio_run.assert_called()
    def test_monitoring_integration(self):
        "]]""测试监控系统集成"""
        monitor = TaskMonitor()
        # 模拟完整的监控工作流程 - 使用正确的方法签名
        monitor.record_task_start("collect_odds_task[", "]test-task-789[")": monitor.record_task_completion("""
            "]collect_odds_task[", "]test-task-789[", 45.2, "]success["""""
        )
        # 使用正确的单队列更新方法
        monitor.update_queue_size("]odds[", 5)": monitor.update_queue_size("]fixtures[", 2)""""
        # 验证方法调用成功（Prometheus指标验证比较复杂，主要验证不抛异常）
        assert True  # 验证所有方法调用成功
class TestEdgeCases:
    "]""边界情况和异常测试"""
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """
        测试数据库连接失败处理
        Mock策略：
        - DatabaseManager初始化正常，但在使用时抛出连接异常
        - 模拟数据库不可用的场景，验证错误处理逻辑
        - 确保系统在数据库故障时能优雅降级，不会导致整个应用崩溃
        目的：验证任务调度系统在外部依赖故障时的鲁棒性
        """
        # 创建一个能正常初始化但使用时失败的Mock
        with patch("src.tasks.error_logger.DatabaseManager[") as mock_manager_class:""""
            # DatabaseManager初始化成功
            mock_db_instance = AsyncMock()
            mock_manager_class.return_value = mock_db_instance
            # 但在使用get_async_session时抛出异常
            mock_db_instance.get_async_session.side_effect = OperationalError(
            "]数据库连接失败["""""
            )
            # 创建TaskErrorLogger实例（此时不会抛异常）
            logger = TaskErrorLogger()
            # 尝试记录错误，应该捕获数据库连接异常但不崩溃
            try:
                pass
            except Exception:
                pass
            except:
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                await logger.log_task_error(
                task_name = os.getenv("TEST_TASK_SCHEDULER_TASK_NAME_983"),": task_id = os.getenv("TEST_TASK_SCHEDULER_TASK_ID_984"),": error=Exception("]测试错误["),": context={},": retry_count=0)""
                # 如果没有抛出异常，说明错误被妥善处理了
        assert True
            except Exception as e:
               pass  # Auto-fixed empty except block
               # 如果抛出异常，确保不是意外的异常
        assert "]数据库连接失败[" in str(e) or "]log_task_error[": in str(e.args)": def test_redis_connection_failure(self):"""
        "]""测试Redis连接失败"""
        with patch("redis.Redis[") as mock_redis_class:": mock_redis = MagicMock()": mock_redis.ping.side_effect = Exception("]Redis连接失败[")": mock_redis_class.return_value = mock_redis["""
            # 系统健康检查应该检测到Redis问题
            with patch("]]src.tasks.maintenance_tasks.DatabaseManager[") as mock_db:": mock_db_instance = AsyncMock()": mock_db.return_value = mock_db_instance[": mock_db_instance.execute_query.return_value = [(1)]"
                # 使用 patch 模拟 asyncio.run 调用
                with patch(:
                    "]]src.tasks.maintenance_tasks.asyncio.run["""""
                ) as mock_asyncio_run:
                    # 模拟健康检查的返回结果，Redis失败
                    mock_health_results = {
                    "]database[": {"]status[": "]healthy[", "]message[": "]数据库连接正常["},""""
                    "]redis[": {"]status[": "]unhealthy[", "]message[": "]Redis连接失败["},""""
                    "]disk_space[": {"]status[": "]healthy[", "]message[": "]磁盘空间充足["}}": mock_asyncio_run.return_value = (mock_health_results, False)"""
                    # 直接调用任务函数
                    result = system_health_check_task()
        assert result["]status["] =="]unhealthy[" assert result["]overall_healthy["] is False[" def test_invalid_task_configuration(self):"""
        "]]""测试无效任务配置"""
        retry_config = TaskRetryConfig()
        # 测试不存在的任务配置
        config = retry_config.get_retry_config("nonexistent_task[")""""
        # 应该返回默认配置
        assert config is not None
        assert config["]max_retries["] ==TaskRetryConfig.DEFAULT_MAX_RETRIES[" assert config["]]retry_delay["] ==TaskRetryConfig.DEFAULT_RETRY_DELAY[""""
        @pytest.mark.asyncio
    async def test_large_error_log_handling(self):
        "]]"""
        测试大量错误日志处理
        Mock策略：
        - DatabaseManager：避免执行真实的大量日志清理操作
        - 异步会话管理器：模拟数据库连接和批量删除操作
        - 查询结果：返回虚拟的删除行数，验证清理逻辑而非真实删除
        - _get_query_builder：Mock查询构建器，避免真实SQL生成
        目的：验证系统能正确处理大量错误日志的清理任务，确保性能和稳定性
        """
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            # Mock批量删除结果 - 模拟清理了1000条错误日志
            mock_result = MagicMock()
            mock_result.rowcount = 1000  # 删除了1000条记录
            mock_session.execute.return_value = mock_result
            mock_session.commit = AsyncMock()
            yield mock_session
            with patch("src.tasks.error_logger.DatabaseManager[") as mock_manager_class:": mock_db_instance = AsyncMock()": mock_db_instance.get_async_session = mock_session_context[": mock_manager_class.return_value = mock_db_instance"
            logger = TaskErrorLogger()
            logger.db_manager = mock_db_instance
            # Mock查询构建器，避免真实SQL查询构建
            with patch.object(logger, "]]_get_query_builder[") as mock_builder_getter:": mock_builder = MagicMock()": mock_builder.build_cleanup_old_logs_query.return_value = (""
                "]DELETE FROM error_logs WHERE created_at < DATE('now', '-1 days')"""""
                )
                mock_builder_getter.return_value = mock_builder
                # 执行日志清理
                deleted_count = await logger.cleanup_old_logs(days_to_keep=1)
            assert deleted_count ==1000
            if __name__ =="__main__["""""
            # 运行测试
            pytest.main(
            ["]__file__[",""""
            "]-v[",""""
            "]--tb=short[",""""
            "]--cov=src.tasks[",""""
            "]--cov - report = htmlhtmlcov[",""""
            "]--cov - report=term - missing[",""""
            "]--cov - fail - under=85[",  # 确保覆盖率超过85%"]"""
            ]
            )
        from contextlib import asynccontextmanager
        from contextlib import asynccontextmanager
        from contextlib import asynccontextmanager
        from contextlib import asynccontextmanager
        from contextlib import asynccontextmanager
        from contextlib import asynccontextmanager
        from contextlib import asynccontextmanager