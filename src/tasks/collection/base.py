"""
数据采集任务基类
Base Data Collection Task

提供数据采集任务的基础功能。
"""

import asyncio
import logging
from typing import Any, Dict

from celery import Task

from ..celery_app import app
from ..error_logger import TaskErrorLogger

logger = logging.getLogger(__name__)


class DataCollectionTask(Task):
    """数据采集任务基类"""

    def __init__(self):
        super().__init__()
        self.error_logger = TaskErrorLogger()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理"""
        task_name = self.name.split(".")[-1] if self.name else "unknown_task"

        # 异步记录错误日志
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.error_logger.log_task_error(
                    task_name=task_name,
                    task_id=task_id,
                    error=exc,
                    context={"args": args, "kwargs": kwargs, "einfo": str(einfo)},
                    retry_count=self.request.retries if hasattr(self, "request") else 0,
                )
            )
        except Exception as log_error:
            logger.error(f"记录任务失败日志时出错: {str(log_error)}")

        logger.error(f"数据采集任务失败: {task_name} - {str(exc)}")

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的处理"""
        task_name = self.name.split(".")[-1] if self.name else "unknown_task"
        logger.info(f"数据采集任务成功: {task_name}")


class CollectionTaskMixin:
    """数据采集任务混入类，提供通用功能"""

    @staticmethod
    def handle_retry(self, task, exc, task_name: str):
        """处理任务重试逻辑"""
        from ..celery_app import TaskRetryConfig

        retry_config = TaskRetryConfig.get_retry_config(task_name)
        max_retries = retry_config["max_retries"]
        retry_delay = retry_config["retry_delay"]

        if task.request.retries < max_retries:
            logger.warning(
                f"{task_name}失败，将在{retry_delay}秒后重试 "
                f"(第{task.request.retries + 1}次): {str(exc)}"
            )
            raise task.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"{task_name}任务最终失败，已达最大重试次数: {str(exc)}")
            return False

        return True

    @staticmethod
    async def log_api_failure(task, task_name: str, api_endpoint: str, error: Exception):
        """记录API失败"""
        if hasattr(task, "error_logger"):
            await task.error_logger.log_api_failure(
                task_name=task_name,
                api_endpoint=api_endpoint,
                http_status=None,
                error_message=str(error),
                retry_count=task.request.retries if hasattr(task, "request") else 0,
            )

    @staticmethod
    def log_data_collection_error(task, data_source: str, collection_type: str, error: Exception, **context):
        """记录数据采集错误"""
        if hasattr(task, "error_logger"):
            asyncio.run(
                task.error_logger.log_data_collection_error(
                    data_source=data_source,
                    collection_type=collection_type,
                    error_message=str(error),
                    error_count=1,
                    context=context,
                )
            )