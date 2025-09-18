"""
支持流式处理的数据采集器

在基础采集器基础上添加Kafka流式处理能力，支持：
- 实时数据流发送
- 批量数据流处理
- Kafka集成
- 数据库和流式存储双写
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.streaming import FootballKafkaProducer, StreamConfig

from .base_collector import CollectionResult, DataCollector


class StreamingDataCollector(DataCollector):
    """
    支持流式处理的数据采集器

    继承自基础采集器，添加Kafka流式处理能力：
    - 数据采集后同时写入数据库和Kafka
    - 支持实时数据流
    - 提供批量流处理
    - 可配置的流式处理策略
    """

    def __init__(
        self,
        data_source: str = "default_source",
        max_retries: int = 3,
        retry_delay: int = 5,
        timeout: int = 30,
        enable_streaming: bool = True,
        stream_config: Optional[StreamConfig] = None
    ):
        """
        初始化流式采集器

        Args:
            data_source: 数据源标识
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 请求超时时间（秒）
            enable_streaming: 是否启用流式处理
            stream_config: 流配置，None表示使用默认配置
        """
        super().__init__(data_source, max_retries, retry_delay, timeout)
        self.logger = logging.getLogger(f"streaming_collector.{self.__class__.__name__}")

        self.enable_streaming = enable_streaming
        self.stream_config = stream_config or StreamConfig()
        self.kafka_producer = None

        # 如果启用流式处理，初始化Kafka生产者
        if self.enable_streaming:
            self._initialize_kafka_producer()

    def _initialize_kafka_producer(self) -> None:
        """初始化Kafka生产者"""
        try:
            self.kafka_producer = FootballKafkaProducer(self.stream_config)
            self.logger.info("Kafka生产者已初始化")
        except Exception as e:
            self.logger.error(f"初始化Kafka生产者失败: {e}")
            self.enable_streaming = False

    async def _send_to_stream(
        self,
        data_list: List[Dict[str, Any]],
        stream_type: str
    ) -> Dict[str, int]:
        """
        发送数据到Kafka流

        Args:
            data_list: 数据列表
            stream_type: 流类型 (match/odds/scores)

        Returns:
            发送统计信息
        """
        if not self.enable_streaming or not self.kafka_producer:
            return {"success": 0, "failed": 0}

        try:
            stats = await self.kafka_producer.send_batch(data_list, stream_type)
            self.logger.info(
                f"数据已发送到{stream_type}流 - "
                f"成功: {stats['success']}, 失败: {stats['failed']}"
            )
            return stats
        except Exception as e:
            self.logger.error(f"发送数据到流失败: {e}")
            return {"success": 0, "failed": len(data_list)}

    async def send_to_stream(self, data: List[Dict[str, Any]]) -> bool:
        """
        发送数据到流的公共接口

        Args:
            data: 要发送的数据列表

        Returns:
            bool: 发送是否成功
        """
        if not data:
            return True

        if not self.enable_streaming or not self.kafka_producer:
            return True

        try:
            # 根据数据内容推断流类型，默认使用 "data"
            stream_type = "data"
            if data and isinstance(data[0], dict):
                if any(key in data[0] for key in ['match_id', 'home_team', 'away_team']):
                    stream_type = "match"
                elif any(key in data[0] for key in ['odds', 'price', 'bookmaker']):
                    stream_type = "odds"
                elif any(key in data[0] for key in ['score', 'minute', 'live']):
                    stream_type = "scores"

            stats = await self._send_to_stream(data, stream_type)
            return stats["success"] > 0 or len(data) == 0
        except Exception as e:
            self.logger.error(f"发送数据到流失败: {e}")
            return False

    async def collect_fixtures_with_streaming(self, **kwargs) -> CollectionResult:
        """
        采集赛程数据并发送到流

        Returns:
            CollectionResult: 采集结果（包含流处理统计）
        """
        # 先执行基础采集
        # ⚠️ 修复：直接调用父类方法避免无限递归
        result = await super().collect_fixtures(**kwargs)

        # 如果采集成功且启用流式处理，发送到Kafka流
        if result and result.status == "success" and result.collected_data and self.enable_streaming:
            stream_stats = await self._send_to_stream(result.collected_data, "match")

            # 在采集结果中添加流处理统计
            if hasattr(result, 'stream_stats'):
                result.stream_stats = stream_stats
            else:
                # 如果没有stream_stats属性，添加到error_message中
                stream_info = f"流处理 - 成功: {stream_stats['success']}, 失败: {stream_stats['failed']}"
                if result.error_message:
                    result.error_message += f"; {stream_info}"
                else:
                    result.error_message = stream_info

        return result

    async def collect_odds_with_streaming(self, **kwargs) -> CollectionResult:
        """
        采集赔率数据并发送到流

        Returns:
            CollectionResult: 采集结果（包含流处理统计）
        """
        # 先执行基础采集
        result = await self.collect_odds(**kwargs)

        # 如果采集成功且启用流式处理，发送到Kafka流
        if result.status == "success" and result.collected_data and self.enable_streaming:
            stream_stats = await self._send_to_stream(result.collected_data, "odds")

            # 在采集结果中添加流处理统计
            if hasattr(result, 'stream_stats'):
                result.stream_stats = stream_stats
            else:
                stream_info = f"流处理 - 成功: {stream_stats['success']}, 失败: {stream_stats['failed']}"
                if result.error_message:
                    result.error_message += f"; {stream_info}"
                else:
                    result.error_message = stream_info

        return result

    async def collect_live_scores_with_streaming(self, **kwargs) -> CollectionResult:
        """
        采集实时比分数据并发送到流

        Returns:
            CollectionResult: 采集结果（包含流处理统计）
        """
        # 先执行基础采集
        result = await self.collect_live_scores(**kwargs)

        # 如果采集成功且启用流式处理，发送到Kafka流
        if result.status == "success" and result.collected_data and self.enable_streaming:
            stream_stats = await self._send_to_stream(result.collected_data, "scores")

            # 在采集结果中添加流处理统计
            if hasattr(result, 'stream_stats'):
                result.stream_stats = stream_stats
            else:
                stream_info = f"流处理 - 成功: {stream_stats['success']}, 失败: {stream_stats['failed']}"
                if result.error_message:
                    result.error_message += f"; {stream_info}"
                else:
                    result.error_message = stream_info

        return result

    async def batch_collect_and_stream(
        self,
        collection_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量采集并流处理

        Args:
            collection_configs: 采集配置列表，每个配置包含:
                - type: 采集类型 (fixtures/odds/scores)
                - kwargs: 采集参数

        Returns:
            批量处理结果统计
        """
        results = {
            "total_collections": len(collection_configs),
            "successful_collections": 0,
            "failed_collections": 0,
            "total_stream_success": 0,
            "total_stream_failed": 0,
            "collection_results": []
        }

        tasks = []
        for config in collection_configs:
            collection_type = config.get("type")
            collection_kwargs = config.get("kwargs", {})

            if collection_type == "fixtures":
                task = self.collect_fixtures_with_streaming(**collection_kwargs)
            elif collection_type == "odds":
                task = self.collect_odds_with_streaming(**collection_kwargs)
            elif collection_type == "scores":
                task = self.collect_live_scores_with_streaming(**collection_kwargs)
            else:
                self.logger.warning(f"未知的采集类型: {collection_type}")
                continue

            tasks.append((collection_type, task))

        # 并行执行所有采集任务
        task_results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )

        # 统计结果
        for i, (collection_type, result) in enumerate(zip([t[0] for t in tasks], task_results)):
            if isinstance(result, Exception):
                results["failed_collections"] += 1
                results["collection_results"].append({
                    "type": collection_type,
                    "status": "error",
                    "error": str(result)
                })
            else:
                if result.status == "success":
                    results["successful_collections"] += 1
                else:
                    results["failed_collections"] += 1

                # 提取流处理统计
                stream_stats = {"success": 0, "failed": 0}
                if result.error_message and "流处理" in result.error_message:
                    # 从error_message中解析流处理统计
                    try:
                        parts = result.error_message.split("流处理 - ")[1]
                        success_part = parts.split("成功: ")[1].split(",")[0]
                        failed_part = parts.split("失败: ")[1].split(";")[0] if ";" in parts else parts.split("失败: ")[1]
                        stream_stats["success"] = int(success_part)
                        stream_stats["failed"] = int(failed_part)
                    except (IndexError, ValueError):
                        pass

                results["total_stream_success"] += stream_stats["success"]
                results["total_stream_failed"] += stream_stats["failed"]

                results["collection_results"].append({
                    "type": collection_type,
                    "status": result.status,
                    "records_collected": result.records_collected,
                    "stream_stats": stream_stats
                })

        self.logger.info(
            f"批量采集完成 - 总计: {results['total_collections']}, "
            f"成功: {results['successful_collections']}, 失败: {results['failed_collections']}, "
            f"流成功: {results['total_stream_success']}, 流失败: {results['total_stream_failed']}"
        )

        return results

    def toggle_streaming(self, enable: bool) -> None:
        """
        切换流式处理开关

        Args:
            enable: 是否启用流式处理
        """
        if enable and not self.kafka_producer:
            self._initialize_kafka_producer()

        self.enable_streaming = enable and self.kafka_producer is not None
        self.logger.info(f"流式处理已{'启用' if self.enable_streaming else '禁用'}")

    def get_streaming_status(self) -> Dict[str, Any]:
        """
        获取流式处理状态

        Returns:
            流式处理状态信息
        """
        return {
            "streaming_enabled": self.enable_streaming,
            "kafka_producer_initialized": self.kafka_producer is not None,
            "stream_config": {
                "bootstrap_servers": self.stream_config.kafka_config.bootstrap_servers,
                "topics": list(self.stream_config.topics.keys())
            } if self.stream_config else None
        }

    def close(self) -> None:
        """关闭采集器和相关资源"""
        if self.kafka_producer:
            self.kafka_producer.close()
            self.kafka_producer = None

        self.logger.info("流式采集器已关闭")

    def __del__(self):
        """析构函数，确保资源清理"""
        self.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.close()

    # 实现抽象方法，但作为抽象类，具体实现需要在子类中提供
    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        """需要在具体子类中实现"""
        raise NotImplementedError("需要在具体采集器中实现")

    async def collect_odds(self, **kwargs) -> CollectionResult:
        """需要在具体子类中实现"""
        raise NotImplementedError("需要在具体采集器中实现")

    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        """需要在具体子类中实现"""
        raise NotImplementedError("需要在具体采集器中实现")
