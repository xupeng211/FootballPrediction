"""
Prometheus告警渠道

通过Prometheus指标记录告警信息。
"""





class PrometheusAlertChannel(BaseAlertChannel):
    """Prometheus告警渠道"""

    def __init__(
        self,
        metrics: Optional[PrometheusMetrics] = None,
        registry: Optional[CollectorRegistry] = None,
    ):
        """
        初始化Prometheus告警渠道

        Args:
            metrics: Prometheus指标管理器
            registry: Prometheus注册表
        """
        super().__init__(AlertChannel.PROMETHEUS)

        # 使用提供的指标管理器或创建新的
        self.metrics = metrics or PrometheusMetrics(registry or REGISTRY)

    async def send_alert(
        self, alert: Alert, rule_id: Optional[str] = None, **kwargs
    ) -> bool:
        """
        通过Prometheus记录告警

        Args:
            alert: 告警对象
            rule_id: 规则ID
            **kwargs: 其他参数

        Returns:
            是否记录成功
        """
        try:
            # 更新告警指标
            self.metrics.update_alert_metrics(alert, rule_id)

            self.logger.debug(
                f"已通过Prometheus记录告警: {alert.alert_id} - {alert.title}"
            )

            return True

        except Exception as e:
            self.logger.error(f"发送Prometheus告警失败: {e}", exc_info=True)
            return False

    async def test_connection(self) -> bool:
        """
        测试Prometheus连接

        Returns:
            是否正常
        """
        try:
            # 尝试访问注册表
            list(self.metrics.registry._collector_to_names)
            self.logger.info("Prometheus告警渠道测试成功")
            return True



        except Exception as e:
            self.logger.error(f"Prometheus告警渠道测试失败: {e}")
            return False