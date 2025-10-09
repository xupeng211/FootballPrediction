"""
"""




    """

    """

        """

        """



        """启动所有处理器 - 简化版本用于测试"""

        """停止所有处理器 - 简化版本用于测试"""

        """

        """



        """启动单个处理器"""

        """停止单个处理器"""

        """停止所有处理器"""


        """

        """


        """

        """







        """


        """

        """异步上下文管理器入口"""

        """异步上下文管理器出口"""



from typing import List
import asyncio
import logging
from ..stream_config import StreamConfig
from .processor import StreamProcessor
from .statistics import ProcessingStatistics

流处理器管理器
Stream Processor Manager
class StreamProcessorManager:
    流处理器管理器
    管理多个流处理器实例，提供：
    - 多流处理器协调
    - 负载均衡
    - 故障恢复
    def __init__(self, config: Optional[StreamConfig] = None, num_processors: int = 1):
        初始化管理器
        Args:
            config: 流配置
            num_processors: 处理器数量
        self.config = config or StreamConfig()
        self.processors: List[StreamProcessor] = []
        self.logger = logging.getLogger(__name__)
        self.statistics = ProcessingStatistics()
        # 创建处理器实例
        for i in range(num_processors):
            processor = StreamProcessor(self.config)
            self.processors.append(processor)
        self.logger.info(f"创建了{num_processors}个流处理器")
    def start_all(self) -> bool:
        try:
            for processor in self.processors:
                processor.start()
            self.logger.info("所有流处理器已启动")
            return True
        except Exception as e:
            self.logger.error(f"启动所有处理器失败: {e}")
            return False
    def stop_all(self) -> bool:
        try:
            for processor in self.processors:
                processor.stop_processing()
            self.logger.info("所有流处理器已停止")
            return True
        except Exception as e:
            self.logger.error(f"停止所有处理器失败: {e}")
            return False
    async def start_all_processors(self, topics: Optional[List[str]] = None) -> None:
        启动所有处理器
        Args:
            topics: 要处理的Topic列表
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
        await processor.start_continuous_processing(topics)
    def _stop_processor(self, processor: StreamProcessor) -> None:
        processor.stop_processing()
    def stop_all_processors(self) -> None:
        for processor in self.processors:
            self._stop_processor(processor)
        self.logger.info("所有流处理器已停止")
    async def get_aggregate_stats(self) -> Dict[str, Any]:
        获取聚合统计信息
        Returns:
            聚合统计信息
        stats_list = []
        for processor in self.processors:
            stats = processor.get_processing_stats()
            stats_list.append(stats)
        return self.statistics.aggregate_stats(stats_list)
    async def health_check_all(self) -> Dict[str, Any]:
        检查所有处理器的健康状态
        Returns:
            所有处理器的健康状态信息
        health_status = {
            "total_processors": len(self.processors),
            "healthy_processors": 0,
            "unhealthy_processors": 0,
            "processor_health": [],
            "overall_status": "unknown",
        }
        healthy_count = 0
        for i, processor in enumerate(self.processors):
            processor_health = await processor.health_check()
            processor_health["processor_id"] = i
            health_status["processor_health"].append(processor_health)
            if processor_health.get("overall_status") == "healthy":
                healthy_count += 1
        health_status["healthy_processors"] = healthy_count
        health_status["unhealthy_processors"] = len(self.processors) - healthy_count
        # 判断整体状态
        if healthy_count == len(self.processors):
            health_status["overall_status"] = "healthy"
        elif healthy_count > 0:
            health_status["overall_status"] = "degraded"
        else:
            health_status["overall_status"] = "unhealthy"
        return health_status
    def restart_processor(self, processor_id: int) -> bool:
        重启指定的处理器
        Args:
            processor_id: 处理器ID
        Returns:
            是否重启成功
        if 0 <= processor_id < len(self.processors):
            try:
                processor = self.processors[processor_id]
                processor.stop_processing()
                processor.start()
                self.logger.info(f"处理器 {processor_id} 重启成功")
                return True
            except Exception as e:
                self.logger.error(f"重启处理器 {processor_id} 失败: {e}")
                return False
        return False
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop_all_processors()