"""
            import asyncio

            from src.monitoring.alert_manager import AlertManager
        from ..celery_config import TaskRetryConfig

基础任务类
Base Task Classes

提供所有调度任务的基类，包含失败处理和告警功能。
"""



logger = logging.getLogger(__name__)


class BaseDataTask(Task):
    """数据任务基类

    提供统一的任务失败处理、告警通知和成功记录功能。
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理

        Args:
            exc: 异常对象
            task_id: 任务ID
            args: 任务位置参数
            kwargs: 任务关键字参数
            einfo: 异常信息
        """
        logger.error(f"Task {self.name} failed: {exc}")
        # 发送告警通知
        self._send_alert_notification(
            task_name=self.name,
            error=str(exc),
            task_id=task_id,
            args=args,
            kwargs=kwargs,
        )

    def _send_alert_notification(self, task_name: str, error: str, task_id: str,
                                args: tuple, kwargs: dict) -> None:
        """发送告警通知

        Args:
            task_name: 任务名称
            error: 错误信息
            task_id: 任务ID
            args: 任务参数
            kwargs: 任务关键字参数
        """
        try:


            async def _send_alert():
                alert_manager = AlertManager()

                # 创建告警消息
                alert_message = {
                    "title": f"任务失败告警: {task_name}",
                    "description": f"任务 {task_name} 执行失败",
                    "error": error,
                    "task_id": task_id,
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "severity": "high",
                    "timestamp": datetime.now().isoformat(),
                    "source": "celery_task",
                }

                # 发送告警
                result = await alert_manager.send_alert(alert_message)
                if result.get("status") == "success":
                    logger.info(f"告警通知发送成功: {task_name}")
                else:
                    logger.error(f"告警通知发送失败: {result.get('error')}")

            # 运行异步告警发送
            asyncio.run(_send_alert())

        except Exception as e:
            logger.error(f"发送告警通知时出错: {str(e)}")

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的处理

        Args:
            retval: 返回值
            task_id: 任务ID
            args: 任务参数
            kwargs: 任务关键字参数
        """
        logger.info(f"Task {self.name} completed successfully")

    def get_retry_config(self, task_name: str) -> Dict[str, Any]:
        """获取任务的重试配置

        Args:
            task_name: 任务名称

        Returns:
            重试配置字典
        """

        return TaskRetryConfig.RETRY_CONFIGS.get(
            task_name,
            {


                "max_retries": TaskRetryConfig.MAX_RETRIES,
                "retry_delay": TaskRetryConfig.DEFAULT_RETRY_DELAY,
            }
        )