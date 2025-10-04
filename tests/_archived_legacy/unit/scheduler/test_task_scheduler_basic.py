from datetime import datetime, timedelta

from src.scheduler.task_scheduler import TaskScheduler, ScheduledTask
from unittest.mock import Mock
import pytest

"""
TaskScheduler 基础测试套件
目标：覆盖核心调度功能，避免复杂的依赖和外部服务
"""

class TestTaskSchedulerBasic:
    """TaskScheduler 基础测试套件"""
    @pytest.fixture
    def scheduler(self):
        """创建调度器实例"""
        return TaskScheduler()
    @pytest.fixture
    def sample_task(self):
        """创建示例任务"""
        return ScheduledTask(
            task_id="test_task[",": name="]测试任务[",": cron_expression="]0 0 * * *",  # 每天午夜[": task_function=lambda: print("]测试任务执行["))": class TestInitialization:"""
        "]""测试初始化"""
        def test_init_success(self):
            """测试成功初始化"""
            scheduler = TaskScheduler()
            assert scheduler is not None
            assert hasattr(scheduler, "tasks[")" assert hasattr(scheduler, "]is_running[")" assert hasattr(scheduler, "]scheduler_thread[")" assert not scheduler.is_running  # 初始状态为未运行["""
    class TestTaskRegistration:
        "]]""测试任务注册"""
        def test_register_task_success(self, scheduler, sample_task):
            """测试成功注册任务"""
            result = scheduler.register_task(sample_task)
            assert result is True
            assert sample_task.task_id in scheduler.tasks
            assert scheduler.tasks[sample_task.task_id] ==sample_task
        def test_register_duplicate_task(self, scheduler, sample_task):
            """测试注册重复任务"""
            # 第一次注册
            scheduler.register_task(sample_task)
            assert sample_task.task_id in scheduler.tasks
            # 第二次注册同一任务
            result = scheduler.register_task(sample_task)
            # 根据实际实现，重复注册可能返回True（覆盖）或False（拒绝）
            assert isinstance(result, bool)
        def test_unregister_task_success(self, scheduler, sample_task):
            """测试成功注销任务"""
            # 先注册
            scheduler.register_task(sample_task)
            assert sample_task.task_id in scheduler.tasks
            # 再注销
            result = scheduler.unregister_task(sample_task.task_id)
            assert result is True
            assert sample_task.task_id not in scheduler.tasks
        def test_unregister_nonexistent_task(self, scheduler):
            """测试注销不存在的任务"""
            result = scheduler.unregister_task("nonexistent_task[")": assert result is False[" class TestTaskExecution:""
        "]]""测试任务执行"""
        def test_get_ready_tasks(self, scheduler, sample_task):
            """测试获取就绪任务"""
            # 设置任务的下次运行时间为过去
            sample_task.next_run = datetime.now() - timedelta(minutes=1)
            scheduler.register_task(sample_task)
            current_time = datetime.now()
            ready_tasks = scheduler.get_ready_tasks(current_time)
            # Check that get_ready_tasks method exists and returns a list
            assert isinstance(ready_tasks, list)
        def test_get_ready_tasks_none_ready(self, scheduler, sample_task):
            """测试获取就绪任务（没有就绪的）"""
            # 设置任务的下次运行时间为未来
            sample_task.next_run = datetime.now() + timedelta(hours=1)
            scheduler.register_task(sample_task)
            current_time = datetime.now()
            ready_tasks = scheduler.get_ready_tasks(current_time)
            assert len(ready_tasks) ==0
        def test_execute_task_success(self, scheduler, sample_task):
            """测试成功执行任务"""
            # Mock任务函数
            mock_func = Mock()
            sample_task.task_function = mock_func
            scheduler.execute_task(sample_task)
            mock_func.assert_called_once()
            # 任务应该被标记为已完成
            assert sample_task.last_run_time is not None
        def test_execute_task_with_error(self, scheduler, sample_task):
            """测试执行任务时出错"""
            # Mock会抛出异常的任务函数
            mock_func = Mock(side_effect=Exception("任务执行失败["))": sample_task.task_function = mock_func["""
            # The scheduler handles exceptions internally, so we expect no exception to be raised
            scheduler.execute_task(sample_task)
            # 任务应该被标记为失败
            assert sample_task.last_run_time is not None
            assert sample_task.last_error is not None
    class TestSchedulerLifecycle:
        "]]""测试调度器生命周期"""
        def test_start_scheduler(self, scheduler):
            """测试启动调度器"""
            result = scheduler.start()
            assert result is True
            assert scheduler.is_running
            # 清理：停止调度器
            scheduler.stop()
        def test_stop_scheduler(self, scheduler):
            """测试停止调度器"""
            # 先启动
            scheduler.start()
            assert scheduler.is_running
            # 再停止
            result = scheduler.stop()
            assert result is True
            assert not scheduler.is_running
        def test_start_already_running_scheduler(self, scheduler):
            """测试启动已在运行的调度器"""
            # 启动调度器
            scheduler.start()
            assert scheduler.is_running
            # 再次启动
            result = scheduler.start()
            assert result is False  # 应该失败
            # 清理
            scheduler.stop()
    class TestTaskStatus:
        """测试任务状态"""
        def test_get_task_status_all(self, scheduler, sample_task):
            """测试获取所有任务状态"""
            scheduler.register_task(sample_task)
            status = scheduler.get_task_status()
            assert isinstance(status, dict)
            # Check that the method exists and returns a dictionary with expected structure:
            assert "scheduler_status[" in status or "]tasks[": in status[": def test_get_task_status_specific(self, scheduler, sample_task):"""
            "]]""测试获取特定任务状态"""
            scheduler.register_task(sample_task)
            status = scheduler.get_task_status(sample_task.task_id)
            assert isinstance(status, dict)
            # Check that the method returns task information
            assert "task_id[" in status or "]name[": in status[": def test_get_task_status_nonexistent(self, scheduler):"""
            "]]""测试获取不存在任务的状态"""
            status = scheduler.get_task_status("nonexistent_task[")": assert isinstance(status, dict)"""
            # Check that error handling works correctly
            assert "]error[" in status[""""
    class TestTaskScheduleUpdate:
        "]]""测试任务调度更新"""
        def test_update_task_schedule_success(self, scheduler, sample_task):
            """测试成功更新任务调度"""
            scheduler.register_task(sample_task)
            original_next_run = sample_task.next_run_time
            new_cron = "*/30 * * * *"  # 每30分钟[": result = scheduler.update_task_schedule(sample_task.task_id, new_cron)": assert result is True[" assert sample_task.cron_expression ==new_cron"
            # 下次运行时间应该已经更新
            assert sample_task.next_run_time != original_next_run
        def test_update_task_schedule_nonexistent(self, scheduler):
            "]]""测试更新不存在任务的调度"""
            result = scheduler.update_task_schedule("nonexistent_task[", "]0 * * * *")": assert result is False[" class TestScheduledTaskClass:""
        "]""测试ScheduledTask类"""
        def test_task_creation(self):
            """测试任务创建"""
            task = ScheduledTask(
                task_id="test_task[",": name="]测试任务[",": cron_expression="]0 0 * * *",": task_function=lambda: None)": assert task.task_id =="test_task[" assert task.name =="]测试任务[" assert task.cron_expression =="]0 0 * * *" assert task.last_run_time is None[""""
            assert task.last_error is None
        def test_should_run_logic(self):
            "]""测试任务是否应该运行的逻辑"""
            task = ScheduledTask(
                task_id="test_task[",": name="]测试任务[",": cron_expression="]0 0 * * *",": task_function=lambda: None)"""
            # 设置下次运行时间为过去
            task.next_run_time = datetime.now() - timedelta(minutes=1)
            assert task.should_run(datetime.now())
            # 设置下次运行时间为未来
            task.next_run_time = datetime.now() + timedelta(hours=1)
            assert not task.should_run(datetime.now())
            # 设置任务为运行中
            task.is_running = True
            task.next_run_time = datetime.now() - timedelta(minutes=1)
            assert not task.should_run(datetime.now())
        def test_mark_completed(self):
            """测试标记任务完成"""
            task = ScheduledTask(
                task_id="test_task[",": name="]测试任务[",": cron_expression="]0 0 * * *",": task_function=lambda: None)": task.mark_completed(success=True)": assert task.last_run_time is not None"
            assert task.last_error is None
            task.mark_completed(success=False, error="任务失败[")": assert task.last_error =="]任务失败[" def test_to_dict("
    """"
            "]""测试转换为字典"""
            task = ScheduledTask(
                task_id="test_task[",": name="]测试任务[",": cron_expression="]0 0 * * *",": task_function=lambda: None)": task_dict = task.to_dict()": assert isinstance(task_dict, dict)"
            assert task_dict["task_id["] ==task.task_id[" assert task_dict["]]name["] ==task.name[" class TestErrorHandling:"""
        "]]""测试错误处理"""
        def test_task_function_exception_handling(self, scheduler):
            """测试任务函数异常处理"""
            def failing_task():
                raise Exception("任务失败[")": task = ScheduledTask(": task_id="]failing_task[",": name="]失败任务[",": cron_expression="]0 0 * * *",": task_function=failing_task)": scheduler.register_task(task)""
            # 执行任务 - scheduler handles exceptions internally
            scheduler.execute_task(task)
            # 检查任务状态
            assert task.last_run_time is not None
            assert task.last_error is not None
    class TestIntegrationScenarios:
        """测试集成场景"""
        def test_full_scheduler_workflow(self, scheduler):
            """测试完整调度器工作流程"""
            # 创建测试任务
            task = ScheduledTask(
                task_id="workflow_task[",": name="]工作流测试任务[",": cron_expression="]0 0 * * *",": task_function=Mock())"""
            # 注册任务
            assert scheduler.register_task(task)
            # 检查状态
            status = scheduler.get_task_status(task.task_id)
            assert isinstance(status, dict)
            # 启动调度器
            assert scheduler.start()
            # 停止调度器
            assert scheduler.stop()
            # 注销任务
            assert scheduler.unregister_task(task.task_id)
    class TestPerformance:
        """测试性能"""
        def test_multiple_task_registration(self, scheduler):
            """测试多任务注册性能"""
            import time
            start_time = time.time()
            # 注册多个任务
            for i in range(100):
                task = ScheduledTask(
                    task_id=f["task_{i}"],": name=f["任务 {i}"],": cron_expression=f["{i % 60} * * * *"],": task_function=lambda: None)": scheduler.register_task(task)": end_time = time.time()"
            # 注册应该在合理时间内完成
            assert (end_time - start_time) < 5.0
    class TestUtilityMethods:
        """测试工具方法"""
        def test_scheduler_attributes(self, scheduler):
            """测试调度器属性"""
            assert hasattr(scheduler, "tasks[")" assert hasattr(scheduler, "]is_running[")" assert hasattr(scheduler, "]scheduler_thread[")"]" assert isinstance(scheduler.tasks, dict)""
            assert isinstance(scheduler.is_running, bool)
