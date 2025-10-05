"""
流数据处理器

整合Kafka Producer和Consumer功能，提供：
- 流式数据处理管理
- 生产者和消费者协调
- 数据流监控
- 批量处理能力
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .kafka_consumer import FootballKafkaConsumer
from .kafka_producer import FootballKafkaProducer
from .stream_config import StreamConfig


class StreamProcessor:
    """
    流数据处理器

    负责协调Kafka生产者和消费者，提供：
    - 统一的流数据处理接口
    - 生产者和消费者生命周期管理
    - 数据流监控和统计
    - 错误处理和恢复
    """

    def __init__(self, config: Optional[StreamConfig] = None):
        """
        初始化流处理器

        Args:
            config: 流配置，如果为None则使用默认配置
        """
        self.config = config or StreamConfig()
        self.producer: Optional[FootballKafkaProducer] = None
        self.consumer: Optional[FootballKafkaConsumer] = None
        self.logger = logging.getLogger(__name__)
        self.processing_stats: Dict[str, Any] = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "processing_errors": 0,
            "start_time": None,
        }

    def _initialize_producer(self) -> FootballKafkaProducer:
        """初始化生产者"""
        if not self.producer:
            self.producer = FootballKafkaProducer(self.config)
            self.logger.info("Kafka Producer已初始化")
        return self.producer

    def _initialize_consumer(
        self, consumer_group_id: Optional[str] = None
    ) -> FootballKafkaConsumer:
        """初始化消费者"""
        if not self.consumer:
            self.consumer = FootballKafkaConsumer(self.config, consumer_group_id)
            self.logger.info("Kafka Consumer已初始化")
        return self.consumer

    async def send_data_stream(
        self, data_list: List[Dict[str, Any]], data_type: str
    ) -> Dict[str, int]:
        """
        发送数据流

        Args:
            data_list: 数据列表
            data_type: 数据类型 (match/odds/scores)

        Returns:
            发送统计
        """
        producer = self._initialize_producer()

        # 批量发送
        stats = await producer.send_batch(data_list, data_type)

        # 更新统计
        self.processing_stats["messages_produced"] += stats["success"]
        self.processing_stats["processing_errors"] += stats["failed"]

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
        """
        消费数据流

        Args:
            topics: 要消费的Topic列表，None表示消费所有Topic
            batch_size: 批量消费大小
            timeout: 超时时间（秒）

        Returns:
            消费统计
        """
        consumer = self._initialize_consumer()

        # 订阅Topic
        if topics:
            consumer.subscribe_topics(topics)
        else:
            consumer.subscribe_all_topics()

        # 批量消费
        stats = await consumer.consume_batch(batch_size, timeout)

        # 更新统计
        self.processing_stats["messages_consumed"] += stats["processed"]
        self.processing_stats["processing_errors"] += stats["failed"]

        self.logger.info(
            f"数据流消费完成 - " f"处理: {stats['processed']}, 失败: {stats['failed']}"
        )

        return stats

    async def start_continuous_processing(self, topics: Optional[List[str]] = None) -> None:
        """
        启动持续流处理

        Args:
            topics: 要消费的Topic列表，None表示消费所有Topic
        """
        consumer = self._initialize_consumer()

        # 订阅Topic
        if topics:
            consumer.subscribe_topics(topics)
        else:
            consumer.subscribe_all_topics()

        # 记录开始时间
        self.processing_stats["start_time"] = datetime.now()

        # 开始持续消费
        self.logger.info("启动持续流处理...")
        await consumer.start_consuming()

    def stop(self) -> None:
        """停止流处理器"""
        self.stop_processing()

    def stop_processing(self) -> None:
        """停止流处理"""
        if self.consumer:
            self.consumer.stop_consuming()

        if self.producer:
            self.producer.close()

        self.logger.info("流处理已停止")

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息

        Returns:
            统计信息字典
        """
        stats = self.processing_stats.copy()

        if stats["start_time"]:
            elapsed = (datetime.now() - stats["start_time"]).total_seconds()
            stats["elapsed_seconds"] = elapsed
            stats["messages_per_second"] = (
                stats["messages_consumed"] + stats["messages_produced"]
            ) / max(elapsed, 1)

        return stats

    async def process_match_data_stream(
        self, match_data_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        处理比赛数据流

        Args:
            match_data_list: 比赛数据列表

        Returns:
            处理统计
        """
        return await self.send_data_stream(match_data_list, "match")

    async def process_odds_data_stream(
        self, odds_data_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        处理赔率数据流

        Args:
            odds_data_list: 赔率数据列表

        Returns:
            处理统计
        """
        return await self.send_data_stream(odds_data_list, "odds")

    async def process_scores_data_stream(
        self, scores_data_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        处理比分数据流

        Args:
            scores_data_list: 比分数据列表

        Returns:
            处理统计
        """
        return await self.send_data_stream(scores_data_list, "scores")

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态信息
        """
        health_status = {
            "producer_status": "unknown",
            "consumer_status": "unknown",
            "kafka_connection": False,
            "processing_stats": self.get_processing_stats(),
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # 检查生产者状态
            if self.producer and self.producer.producer:
                health_status["producer_status"] = "healthy"
            else:
                health_status["producer_status"] = "not_initialized"

            # 检查消费者状态
            if self.consumer and self.consumer.consumer:
                health_status["consumer_status"] = "healthy"
            else:
                health_status["consumer_status"] = "not_initialized"

            # 简单的Kafka连接检查
            if self.producer and self.producer.producer:
                # 尝试获取集群元数据
                metadata = self.producer.producer.list_topics(timeout=5)
                if metadata:
                    health_status["kafka_connection"] = True
                    health_status["available_topics"] = list(metadata.topics.keys())

        except Exception as e:
            health_status["error"] = str(e)
            self.logger.error(f"健康检查失败: {e}")

        return health_status

    def start(self) -> bool:
        """启动流处理器 - 简化版本用于测试"""
        try:
            self.processing_stats["start_time"] = datetime.now()
            self.logger.info("流处理器已启动")
            return True
        except Exception as e:
            self.logger.error(f"启动流处理器失败: {e}")
            return False

    async def send_data(self, data: Dict[str, Any], data_type: str = "match") -> bool:
        """发送单条数据 - 异步版本"""
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

    def consume_data(self, timeout: float = 5.0, max_messages: int = 10) -> Dict[str, int]:
        """消费数据 - 同步版本用于测试"""
        try:
            consumer = self._initialize_consumer()
            consumer.subscribe_all_topics()
            return asyncio.run(consumer.consume_batch(batch_size=max_messages, timeout=timeout))
        except Exception:
            return {"processed": 0, "failed": 1}

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.stop_processing()


class StreamProcessorManager:
    """
    流处理器管理器

    管理多个流处理器实例，提供：
    - 多流处理器协调
    - 负载均衡
    - 故障恢复
    """

    def __init__(self, config: Optional[StreamConfig] = None, num_processors: int = 1):
        """
        初始化管理器

        Args:
            config: 流配置
            num_processors: 处理器数量
        """
        self.config = config or StreamConfig()
        self.processors: List[StreamProcessor] = []
        self.logger = logging.getLogger(__name__)

        # 创建处理器实例
        for i in range(num_processors):
            processor = StreamProcessor(self.config)
            self.processors.append(processor)

        self.logger.info(f"创建了{num_processors}个流处理器")

    def start_all(self) -> bool:
        """启动所有处理器 - 简化版本用于测试"""
        try:
            for processor in self.processors:
                processor.start()
            self.logger.info("所有流处理器已启动")
            return True
        except Exception as e:
            self.logger.error(f"启动所有处理器失败: {e}")
            return False

    def stop_all(self) -> bool:
        """停止所有处理器 - 简化版本用于测试"""
        try:
            for processor in self.processors:
                processor.stop_processing()
            self.logger.info("所有流处理器已停止")
            return True
        except Exception as e:
            self.logger.error(f"停止所有处理器失败: {e}")
            return False

    async def start_all_processors(self, topics: Optional[List[str]] = None) -> None:
        """
        启动所有处理器

        Args:
            topics: 要处理的Topic列表
        """
        tasks = []
        for i, processor in enumerate(self.processors):
            # 使用不同的消费者组避免冲突
            consumer_group_id = f"football-prediction-consumers-{i}"
            if processor.consumer:
                processor.consumer._initialize_consumer(consumer_group_id)

            task = self._start_processor(processor, topics)
            tasks.append(task)

        self.logger.info(f"启动{len(self.processors)}个流处理器...")
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _start_processor(
        self, processor: StreamProcessor, topics: Optional[List[str]] = None
    ) -> None:
        """启动单个处理器"""
        await processor.start_continuous_processing(topics)

    def _stop_processor(self, processor: StreamProcessor) -> None:
        """停止单个处理器"""
        processor.stop_processing()

    def stop_all_processors(self) -> None:
        """停止所有处理器"""
        for processor in self.processors:
            self._stop_processor(processor)

        self.logger.info("所有流处理器已停止")

    async def get_aggregate_stats(self) -> Dict[str, Any]:
        """
        获取聚合统计信息

        Returns:
            聚合统计信息
        """
        aggregate_stats: Dict[str, Any] = {
            "total_processors": len(self.processors),
            "total_messages_produced": 0,
            "total_messages_consumed": 0,
            "total_processing_errors": 0,
            "processor_stats": [],
        }

        for i, processor in enumerate(self.processors):
            stats = processor.get_processing_stats()
            aggregate_stats["processor_stats"].append({"processor_id": i, **stats})

            aggregate_stats["total_messages_produced"] += stats.get("messages_produced", 0)
            aggregate_stats["total_messages_consumed"] += stats.get("messages_consumed", 0)
            aggregate_stats["total_processing_errors"] += stats.get("processing_errors", 0)

        return aggregate_stats

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.stop_all_processors()
