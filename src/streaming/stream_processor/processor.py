"""
"""




    """

    """

        """

        """

        """初始化生产者"""

        """初始化消费者"""

        """


        """





        """


        """






        """

        """




        """停止流处理器"""

        """停止流处理"""



        """

        """

        """


        """

        """


        """

        """


        """

        """

        """

        """启动流处理器 - 简化版本用于测试"""

        """发送单条数据 - 异步版本"""

        """消费数据 - 同步版本用于测试"""

        """异步上下文管理器入口"""

        """异步上下文管理器出口"""



from typing import Optional
import asyncio
import logging
from ..kafka_consumer import FootballKafkaConsumer
from ..kafka_producer import FootballKafkaProducer
from ..stream_config import StreamConfig
from .health import HealthChecker
from .statistics import ProcessingStatistics

流数据处理器
Stream Data Processor
class StreamProcessor:
    流数据处理器
    负责协调Kafka生产者和消费者，提供：
    - 统一的流数据处理接口
    - 生产者和消费者生命周期管理
    - 数据流监控和统计
    - 错误处理和恢复
    def __init__(self, config: Optional[StreamConfig] = None):
        初始化流处理器
        Args:
            config: 流配置，如果为None则使用默认配置
        self.config = config or StreamConfig()
        self.producer: Optional[FootballKafkaProducer] = None
        self.consumer: Optional[FootballKafkaConsumer] = None
        self.logger = logging.getLogger(__name__)
        self.statistics = ProcessingStatistics()
        self.health_checker = HealthChecker()
    def _initialize_producer(self) -> FootballKafkaProducer:
        if not self.producer:
            self.producer = FootballKafkaProducer(self.config)
            self.logger.info("Kafka Producer已初始化")
        return self.producer
    def _initialize_consumer(
        self, consumer_group_id: Optional[str] = None
    ) -> FootballKafkaConsumer:
        if not self.consumer:
            self.consumer = FootballKafkaConsumer(self.config, consumer_group_id)
            self.logger.info("Kafka Consumer已初始化")
        return self.consumer
    async def send_data_stream(
        self, data_list: List[Dict[str, Any]], data_type: str
    ) -> Dict[str, int]:
        发送数据流
        Args:
            data_list: 数据列表
            data_type: 数据类型 (match/odds/scores)
        Returns:
            发送统计
        producer = self._initialize_producer()
        # 批量发送
        stats = await producer.send_batch(data_list, data_type)
        # 更新统计
        self.statistics.record_message_produced(stats["success"])
        self.statistics.record_error(stats["failed"])
        self.logger.info(
            f"数据流发送完成 - 类型: {data_type}, "
            f"成功: {stats['success']}, 失败: {stats['failed']}"
        )
        return stats
    async def consume_data_stream(
        self,
        topics: Optional[List[str]] = None,
        batch_size: int = 100,
        timeout: float = 30.0,
    ) -> Dict[str, int]:
        消费数据流
        Args:
            topics: 要消费的Topic列表，None表示消费所有Topic
            batch_size: 批量消费大小
            timeout: 超时时间（秒）
        Returns:
            消费统计
        consumer = self._initialize_consumer()
        # 订阅Topic
        if topics:
            consumer.subscribe_topics(topics)
        else:
            consumer.subscribe_all_topics()
        # 批量消费
        stats = await consumer.consume_batch(batch_size, timeout)
        # 更新统计
        self.statistics.record_message_consumed(stats["processed"])
        self.statistics.record_error(stats["failed"])
        self.logger.info(
            f"数据流消费完成 - "
            f"处理: {stats['processed']}, 失败: {stats['failed']}"
        )
        return stats
    async def start_continuous_processing(
        self, topics: Optional[List[str]] = None
    ) -> None:
        启动持续流处理
        Args:
            topics: 要消费的Topic列表，None表示消费所有Topic
        consumer = self._initialize_consumer()
        # 订阅Topic
        if topics:
            consumer.subscribe_topics(topics)
        else:
            consumer.subscribe_all_topics()
        # 记录开始时间
        self.statistics.start_timing()
        # 开始持续消费
        self.logger.info("启动持续流处理...")
        await consumer.start_consuming()
    def stop(self) -> None:
        self.stop_processing()
    def stop_processing(self) -> None:
        if self.consumer:
            self.consumer.stop_consuming()
        if self.producer:
            self.producer.close()
        self.logger.info("流处理已停止")
    def get_processing_stats(self) -> Dict[str, Any]:
        获取处理统计信息
        Returns:
            统计信息字典
        return self.statistics.get_stats()
    async def process_match_data_stream(
        self, match_data_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        处理比赛数据流
        Args:
            match_data_list: 比赛数据列表
        Returns:
            处理统计
        return await self.send_data_stream(match_data_list, "match")
    async def process_odds_data_stream(
        self, odds_data_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        处理赔率数据流
        Args:
            odds_data_list: 赔率数据列表
        Returns:
            处理统计
        return await self.send_data_stream(odds_data_list, "odds")
    async def process_scores_data_stream(
        self, scores_data_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        处理比分数据流
        Args:
            scores_data_list: 比分数据列表
        Returns:
            处理统计
        return await self.send_data_stream(scores_data_list, "scores")
    async def health_check(self) -> Dict[str, Any]:
        健康检查
        Returns:
            健康状态信息
        return await self.health_checker.check_health(
            producer=self.producer,
            consumer=self.consumer,
            processing_stats=self.get_processing_stats(),
        )
    def start(self) -> bool:
        try:
            self.statistics.start_timing()
            self.logger.info("流处理器已启动")
            return True
        except Exception as e:
            self.logger.error(f"启动流处理器失败: {e}")
            return False
    async def send_data(self, data: Dict[str, Any], data_type: str = "match") -> bool:
        try:
            producer = self._initialize_producer()
            if data_type == "match":
                return await producer.send_match_data(data)
            elif data_type == "odds":
                return await producer.send_odds_data(data)
            elif data_type == "scores":
                return await producer.send_scores_data(data)
            return False
        except Exception:
            return False
    def consume_data(
        self, timeout: float = 5.0, max_messages: int = 10
    ) -> Dict[str, int]:
        try:
            consumer = self._initialize_consumer()
            consumer.subscribe_all_topics()
            return asyncio.run(
                consumer.consume_batch(batch_size=max_messages, timeout=timeout)
            )
        except Exception:
            return {"processed": 0, "failed": 1}
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop_processing()