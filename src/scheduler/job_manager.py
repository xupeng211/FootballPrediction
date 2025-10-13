"""
作业管理器

负责管理和执行具体的作业任务，提供超时控制、资源管理、
状态监控等功能。支持同步和异步任务执行。

基于 DATA_DESIGN.md 第3节调度策略设计。
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class JobExecutionResult:
    """作业执行结果类"""

    def __init__(
        self,
        job_id: str,
        success: bool,
        start_time: datetime,
        end_time: datetime,
        result: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        memory_usage: float = 0.0,
        cpu_usage: float = 0.0,
    ):
        """
        初始化执行结果

        Args:
            job_id: 作业ID
            success: 是否执行成功
            start_time: 开始时间
            end_time: 结束时间
            result: 执行结果
            error: 错误信息
            execution_time: 执行时间（秒）
            memory_usage: 内存使用量（MB）
            cpu_usage: CPU使用率（%）
        """
        self.job_id = job_id
        self.success = success
        self.start_time = start_time
        self.end_time = end_time
        self._result = result
        self.error = error
        self.execution_time = execution_time
        self.memory_usage = memory_usage
        self.cpu_usage = cpu_usage

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "job_id": self.job_id,
            "success": self.success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "execution_time": self.execution_time,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "error": self.error,
            "result": str(self.result) if self.result is not None else None,
        }


class ResourceMonitor:
    """资源监控器"""

    def __init__(self):
        """初始化资源监控器"""
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.resource_stats: Dict[str, List[float]] = {
            "memory": [],
            "cpu": [],
        }

    def start_monitoring(self, job_id: str) -> None:
        """
        开始监控资源使用情况

        Args:
            job_id: 作业ID
        """
        if self.monitoring:
            return

        self.monitoring = True
        self.resource_stats = {"memory": [], "cpu": []}

        def _monitor():
            """监控线程"""
            import psutil

            process = psutil.Process()
            while self.monitoring:
                try:
                    # 获取内存使用情况（MB）
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    self.resource_stats["memory"].append(memory_mb)

                    # 获取CPU使用率
                    cpu_percent = process.cpu_percent()
                    self.resource_stats["cpu"].append(cpu_percent)

                    time.sleep(1)  # 每秒采样一次

                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    logger.warning(f"资源监控异常: {e}")
                    break

        self.monitor_thread = threading.Thread(
            target=_monitor, name=f"ResourceMonitor-{job_id}"
        )
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> Tuple[float, float]:
        """
        停止监控并返回统计结果

        Returns:
            Tuple[float, float]: (平均内存使用量MB, 平均CPU使用率%)
        """
        self.monitoring = False

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

        # 计算平均值
        avg_memory = (
            sum(self.resource_stats["memory"]) / len(self.resource_stats["memory"])
            if self.resource_stats["memory"]
            else 0.0
        )
        avg_cpu = (
            sum(self.resource_stats["cpu"]) / len(self.resource_stats["cpu"])
            if self.resource_stats["cpu"]
            else 0.0
        )

        return avg_memory, avg_cpu


class JobManager:
    """
    作业管理器主类

    负责管理和执行具体的作业任务，提供以下功能：
    - 任务执行和超时控制
    - 资源使用监控
    - 执行状态跟踪
    - 异步和同步任务支持
    - 执行结果记录
    """

    def __init__(self, max_workers: int = 5):
        """
        初始化作业管理器

        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_jobs: Dict[str, threading.Thread] = {}
        self.execution_history: List[JobExecutionResult] = []
        self.db_manager = DatabaseManager()

        # 性能统计
        self.total_jobs_executed = 0
        self.successful_jobs = 0
        self.failed_jobs = 0

        logger.info(f"作业管理器初始化完成，最大工作线程数: {max_workers}")

    def execute_job(
        self,
        task_id: str,
        task_function: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        timeout: int = 300,
    ) -> bool:
        """
        执行作业任务

        Args:
            task_id: 任务ID
            task_function: 要执行的任务函数
            args: 任务函数参数
            kwargs: 任务函数关键字参数
            timeout: 超时时间（秒）

        Returns:
            bool: 执行是否成功
        """
        if task_id in self.running_jobs:
            logger.warning(f"作业 {task_id} 正在执行中，跳过")
            return False

        start_time = datetime.now()
        resource_monitor = ResourceMonitor()
        kwargs = kwargs or {}

        logger.info(f"开始执行作业: {task_id}, 超时: {timeout}秒")

        try:
            # 开始资源监控
            resource_monitor.start_monitoring(task_id)

            # 判断是否为异步函数
            if asyncio.iscoroutinefunction(task_function):
                _result = self._execute_async_job(task_function, args, kwargs, timeout)
            else:
                _result = self._execute_sync_job(task_function, args, kwargs, timeout)

            # 停止资源监控
            avg_memory, avg_cpu = resource_monitor.stop_monitoring()

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # 记录执行结果
            execution_result = JobExecutionResult(
                job_id=task_id,
                success=True,
                start_time=start_time,
                end_time=end_time,
                _result =result,
                execution_time=execution_time,
                memory_usage=avg_memory,
                cpu_usage=avg_cpu,
            )

            self._record_execution_result(execution_result)
            self.successful_jobs += 1

            logger.info(f"作业执行成功: {task_id}, 耗时: {execution_time:.2f}秒")
            return True

        except TimeoutError:
            error_msg = f"作业超时: {task_id}, 超时时间: {timeout}秒"
            logger.error(error_msg)
            self._handle_job_failure(task_id, start_time, resource_monitor, error_msg)
            return False

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            error_msg = f"作业执行异常: {task_id} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._handle_job_failure(task_id, start_time, resource_monitor, error_msg)
            return False

        finally:
            # 清理运行记录
            if task_id in self.running_jobs:
                del self.running_jobs[task_id]

            self.total_jobs_executed += 1

    def _execute_sync_job(
        self,
        task_function: Callable,
        args: tuple,
        kwargs: Dict[str, Any],
        timeout: int,
    ) -> Any:
        """
        执行同步作业

        Args:
            task_function: 任务函数
            args: 参数
            kwargs: 关键字参数
            timeout: 超时时间

        Returns:
            Any: 执行结果
        """
        future = self.executor.submit(task_function, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            future.cancel()
            raise e

    def _execute_async_job(
        self,
        task_function: Callable,
        args: tuple,
        kwargs: Dict[str, Any],
        timeout: int,
    ) -> Any:
        """
        执行异步作业

        Args:
            task_function: 异步任务函数
            args: 参数
            kwargs: 关键字参数
            timeout: 超时时间

        Returns:
            Any: 执行结果
        """

        # 在新的事件循环中执行异步任务
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    asyncio.wait_for(task_function(*args, **kwargs), timeout=timeout)
                )
            finally:
                loop.close()

        future = self.executor.submit(run_async)
        return future.result(timeout=timeout + 10)  # 额外10秒缓冲

    def _handle_job_failure(
        self,
        task_id: str,
        start_time: datetime,
        resource_monitor: ResourceMonitor,
        error_msg: str,
    ) -> None:
        """
        处理作业失败

        Args:
            task_id: 任务ID
            start_time: 开始时间
            resource_monitor: 资源监控器
            error_msg: 错误信息
        """
        # 停止资源监控
        avg_memory, avg_cpu = resource_monitor.stop_monitoring()

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # 记录失败结果
        execution_result = JobExecutionResult(
            job_id=task_id,
            success=False,
            start_time=start_time,
            end_time=end_time,
            error=error_msg,
            execution_time=execution_time,
            memory_usage=avg_memory,
            cpu_usage=avg_cpu,
        )

        self._record_execution_result(execution_result)
        self.failed_jobs += 1

    def _record_execution_result(self, result: JobExecutionResult) -> None:
        """
        记录执行结果

        Args:
            result: 执行结果
        """
        # 添加到历史记录
        self.execution_history.append(result)

        # 保留最近100条记录
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

        # 记录到数据库（异步执行，避免阻塞）
        threading.Thread(
            target=self._save_execution_result_to_db,
            args=(result,),
            daemon=True,
        ).start()

    def _save_execution_result_to_db(self, result: JobExecutionResult) -> None:
        """
        保存执行结果到数据库

        Args:
            result: 执行结果
        """
        try:
            # 这里可以扩展保存到数据库的逻辑
            # 当前仅记录日志
            logger.debug(f"执行结果已记录: {result.job_id}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"保存执行结果到数据库失败: {e}")

    def kill_job(self, task_id: str) -> bool:
        """
        强制终止正在运行的作业

        Args:
            task_id: 任务ID

        Returns:
            bool: 终止是否成功
        """
        if task_id not in self.running_jobs:
            logger.warning(f"作业不存在或未运行: {task_id}")
            return False

        try:
            # 注意：Python线程无法直接强制终止
            # 这里只是从记录中移除，实际的线程可能仍在运行
            del self.running_jobs[task_id]

            logger.info(f"作业已标记终止: {task_id}")
            return True

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"终止作业失败: {task_id} - {e}")
            return False

    def get_running_jobs(self) -> List[str]:
        """
        获取正在运行的作业列表

        Returns:
            List[str]: 正在运行的作业ID列表
        """
        return list(self.running_jobs.keys())

    def get_job_statistics(self) -> Dict[str, Any]:
        """
        获取作业执行统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        success_rate = (
            (self.successful_jobs / self.total_jobs_executed * 100)
            if self.total_jobs_executed > 0
            else 0
        )

        recent_executions = (
            self.execution_history[-10:] if self.execution_history else []
        )
        avg_execution_time = (
            sum(r.execution_time for r in recent_executions) / len(recent_executions)
            if recent_executions
            else 0
        )

        return {
            "total_jobs_executed": self.total_jobs_executed,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "success_rate": round(success_rate, 2),
            "running_jobs_count": len(self.running_jobs),
            "running_jobs": list(self.running_jobs.keys()),
            "avg_execution_time": round(avg_execution_time, 2),
            "max_workers": self.max_workers,
            "executor_stats": {
                "active_threads": self.executor._threads,
                "pending_tasks": self.executor._work_queue.qsize(),
            },
        }

    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取执行历史记录

        Args:
            limit: 返回记录数量限制

        Returns:
            List[Dict[str, Any]]: 执行历史记录
        """
        recent_history = (
            self.execution_history[-limit:] if self.execution_history else []
        )
        return [result.to_dict() for result in reversed(recent_history)]

    def cleanup_resources(self) -> None:
        """清理资源"""
        try:
            # 等待所有任务完成
            self.executor.shutdown(wait=True)

            # 清理执行历史
            self.execution_history.clear()
            self.running_jobs.clear()

            logger.info("作业管理器资源清理完成")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"作业管理器资源清理失败: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup_resources()
