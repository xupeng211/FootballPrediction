"""
Kafka流高级封装
"""



logger = logging.getLogger(__name__)


class KafkaStream:
    """Kafka流（高级封装）"""

    def __init__(
        self,
        stream_id: str,
        source_topic: str,
        sink_topic: Optional[str] = None,
        config: Optional[StreamConfig] = None,
    ):
        """
        初始化Kafka流

        Args:
            stream_id: 流ID
            source_topic: 源主题
            sink_topic: 目标主题
            config: 流配置
        """
        self.stream_id = stream_id
        self.source_topic = source_topic
        self.sink_topic = sink_topic
        self.config = config or StreamConfig()
        self.processors: List[StreamProcessor] = []

    def add_processor(
        self,
        processor_func: Callable,
        output_topic: Optional[str] = None,
    ) -> "KafkaStream":
        """
        添加处理器

         Args:
             processor_func: 处理函数
             output_topic: 输出主题

         Returns:
             KafkaStream: 返回自身以支持链式调用
        """
        processor = StreamProcessor(
            input_topics=self.source_topic,
            output_topic=output_topic or self.sink_topic,
            processor_func=processor_func,
            config=self.config,
        )
        self.processors.append(processor)
        return self

    async def start(self) -> None:
        """启动流"""
        logger.info(f"启动Kafka流: {self.stream_id}")
        tasks = []
        for processor in self.processors:
            tasks.append(processor.start())
        await asyncio.gather(*tasks)

    def stop(self) -> None:
        """停止流"""
        logger.info(f"停止Kafka流: {self.stream_id}")
        for processor in self.processors:
            processor.stop()

    def close(self) -> None:
        """关闭流"""
        self.stop()
        for processor in self.processors:
            processor.close()

    def health_check(self) -> bool:
        """健康检查"""
        return all(p.health_check() for p in self.processors)


async def ensure_topics_exist(config: Optional[StreamConfig] = None) -> None:
    """
    确保默认主题存在

    Args:
        config: 流配置
    """
    try:
        manager = KafkaTopicManager(config)
        for topic_name, topic_config in DEFAULT_TOPICS.items():
            manager.create_topic(
                topic_name=topic_name,
                num_partitions=topic_config["partitions"], List, Optional


                replication_factor=topic_config["replication_factor"],
                config=topic_config["config"],
            )
        manager.close()
    except Exception as e:
        logger.error(f"确保主题存在失败: {e}")