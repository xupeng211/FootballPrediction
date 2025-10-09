"""



"""





    """数据任务基类"""

        """任务失败时的处理"""

        """发送告警通知"""







        """任务成功时的处理"""

        """准备标准化的任务结果"""


            import asyncio
            from src.monitoring.alert_manager import AlertManager

基础任务类
提供所有调度任务的通用基类和功能。
logger = logging.getLogger(__name__)
class BaseDataTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {self.name} failed: {exc}")
        # 发送告警通知
        self._send_alert_notification(
            task_name=self.name,
            error=str(exc),
            task_id=task_id,
            args=args,
            kwargs=kwargs,
        )
    def _send_alert_notification(self, task_name, error, task_id, args, kwargs):
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
        logger.info(f"Task {self.name} completed successfully")
    def _prepare_result(self, status: str, **kwargs) -> Dict[str, Any]:
        result = {
            "status": status,
            "execution_time": datetime.now().isoformat(),
            **kwargs
            "execution_time": datetime.now().isoformat(),)
        return result