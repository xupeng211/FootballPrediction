"""
健康检查
Health Check
"""




class HealthChecker:
    """
    流处理器健康检查器

    检查流处理器的健康状态，包括生产者、消费者和Kafka连接状态。
    """

    def __init__(self):
        """初始化健康检查器"""
        pass

    async def check_health(
        self,
        producer: Optional[FootballKafkaProducer] = None,
        consumer: Optional[FootballKafkaConsumer] = None,
        processing_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行健康检查

        Args:
            producer: Kafka生产者实例
            consumer: Kafka消费者实例
            processing_stats: 处理统计信息

        Returns:
            健康状态信息
        """
        health_status = {
            "producer_status": "unknown",
            "consumer_status": "unknown",
            "kafka_connection": False,
            "processing_stats": processing_stats or {},
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unhealthy",
        }

        healthy_components = []

        try:
            # 检查生产者状态
            if producer and producer.producer:
                health_status["producer_status"] = "healthy"
                healthy_components.append("producer")
            else:
                health_status["producer_status"] = "not_initialized"

            # 检查消费者状态
            if consumer and consumer.consumer:
                health_status["consumer_status"] = "healthy"
                healthy_components.append("consumer")
            else:
                health_status["consumer_status"] = "not_initialized"

            # 简单的Kafka连接检查
            if producer and producer.producer:
                # 尝试获取集群元数据
                metadata = producer.producer.list_topics(timeout=5)
                if metadata:
                    health_status["kafka_connection"] = True
                    healthy_components.append("kafka_connection")
                    health_status["available_topics"] = list(metadata.topics.keys())

            # 判断整体健康状态
            if len(healthy_components) >= 2:  # 至少两个组件健康
                health_status["overall_status"] = "healthy"
            elif len(healthy_components) >= 1:
                health_status["overall_status"] = "degraded"

        except Exception as e:
            health_status["error"] = str(e)
            health_status["overall_status"] = "unhealthy"

        return health_status

    def is_healthy(self, health_status: Dict[str, Any]) -> bool:
        """
        判断是否健康

        Args:
            health_status: 健康状态信息

        Returns:
            是否健康
        """
        return health_status.get("overall_status") == "healthy"

    def get_available_topics(self, health_status: Dict[str, Any]) -> list:
        """
        获取可用的Topic列表

        Args:
            health_status: 健康状态信息

        Returns:
            Topic列表
        """
        return health_status.get("available_topics", [])
from datetime import datetime


