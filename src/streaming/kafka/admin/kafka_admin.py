"""
Kafka管理器
"""


# Import moved to top



try: NewTopic
    KAFKA_ADMIN_AVAILABLE = True
except ImportError:
    KAFKA_ADMIN_AVAILABLE = False
    AdminClient = None
    NewTopic = None


logger = logging.getLogger(__name__)
_settings = get_settings()


class KafkaAdmin:
    """Kafka管理器"""

    def __init__(self, bootstrap_servers: Optional[str] = None):
        if not KAFKA_ADMIN_AVAILABLE:
            raise ImportError("confluent_kafka is required for KafkaAdmin")

        self.bootstrap_servers = bootstrap_servers or getattr(_settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.admin_client = AdminClient({"bootstrap.servers": self.bootstrap_servers})

    async def create_topics(self, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建主题"""
        try:
            new_topics = [
                NewTopic(
                    topic["name"],
                    num_partitions=topic.get("num_partitions", 3),
                    replication_factor=topic.get("replication_factor", 1),
                )
                for topic in topics
            ]

            result = self.admin_client.create_topics(new_topics)

            # 等待创建完成
            for topic_name, future in result.items():
                try:
                    future.result(timeout=10)
                    logger.info(f"主题 {topic_name} 创建成功")
                except Exception as e:
                    logger.error(f"主题 {topic_name} 创建失败: {e}")

            return {"status": "success", "created_topics": [t["name"] for t in topics]}
        except Exception as e:
            logger.error(f"创建Kafka主题失败: {e}")
            return {"status": "error", "error": str(e)}

    async def delete_topics(self, topic_names: List[str]) -> Dict[str, Any]:
        """删除主题"""
        try:
            result = self.admin_client.delete_topics(topic_names)



            # 等待删除完成
            for topic_name, future in result.items():
                try:
                    future.result(timeout=10)
                    logger.info(f"主题 {topic_name} 删除成功")
                except Exception as e:
                    logger.error(f"主题 {topic_name} 删除失败: {e}")

            return {"status": "success", "deleted_topics": topic_names}
        except Exception as e:
            logger.error(f"删除Kafka主题失败: {e}")
            return {"status": "error", "error": str(e)}