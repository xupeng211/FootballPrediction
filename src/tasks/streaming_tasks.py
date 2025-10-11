"""
实时数据流任务

处理实时数据流，包括：
- WebSocket连接管理
- 实时数据处理
- 流数据持久化
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from celery import Task

from src.core.logging import get_logger
from src.tasks.celery_app import app
from src.tasks.error_handlers import TaskErrorLogger  # type: ignore

logger = get_logger(__name__)


class StreamingTask(Task):
    """
    流处理任务基类

    提供流处理任务的通用功能：
    - 异步任务执行
    - 错误处理和重试
    - 日志记录
    """

    def __init__(self):
        self.error_logger = TaskErrorLogger()
        self.logger = logging.getLogger(f"streaming_task.{self.__class__.__name__}")

    def run_async(self, coro):
        """运行异步协程"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)


@app.task(base=StreamingTask, bind=True)
def consume_kafka_streams_task(
    self,
    topics: Optional[List[str]] = None,
    batch_size: int = 100,
    timeout: float = 30.0,
):
    """
    消费Kafka流数据任务

    Args:
        topics: 要消费的Topic列表，None表示消费所有Topic
        batch_size: 批量消费大小
        timeout: 超时时间（秒）

    Returns:
        Dict: 消费统计结果
    """

    async def _consume_streams():
        try:
            consumer = FootballKafkaConsumer()

            # 订阅Topic
            if topics:
                consumer.subscribe_topics(topics)
            else:
                consumer.subscribe_all_topics()

            # 批量消费
            stats = await consumer.consume_batch(batch_size, timeout)

            self.logger.info(
                f"Kafka流消费完成 - 处理: {stats['processed']}, 失败: {stats['failed']}"
            )

            return {
                "task_id": self.request.id,
                "status": "success",
                "topics": topics or "all",
                "statistics": stats,
                "batch_size": batch_size,
                "timeout": timeout,
            }

        except Exception as e:
            error_msg = f"Kafka流消费失败: {e}"
            self.logger.error(error_msg)

            # 记录错误
            await self.error_logger.log_task_error(
                task_name="consume_kafka_streams_task",
                task_id=self.request.id,
                error=e,
                context={"topics": topics, "batch_size": batch_size},
                retry_count=self.request.retries,
            )

            return {
                "task_id": self.request.id,
                "status": "failed",
                "error": error_msg,
                "topics": topics or "all",
            }

        finally:
            # 清理资源
            if "consumer" in locals():
                consumer.stop_consuming()

    return self.run_async(_consume_streams())


@app.task(base=StreamingTask, bind=True)
def start_continuous_consumer_task(
    self, topics: Optional[List[str]] = None, consumer_group_id: Optional[str] = None
):
    """
    启动持续Kafka消费任务

    Args:
        topics: 要消费的Topic列表，None表示消费所有Topic
        consumer_group_id: 消费者组ID

    Returns:
        Dict: 任务状态
    """

    async def _start_continuous_consumer():
        try:
            consumer = FootballKafkaConsumer(consumer_group_id=consumer_group_id)

            # 订阅Topic
            if topics:
                consumer.subscribe_topics(topics)
            else:
                consumer.subscribe_all_topics()

            self.logger.info(f"启动持续Kafka消费 - Topics: {topics or 'all'}")

            # 启动持续消费（这将一直运行直到任务被取消）
            await consumer.start_consuming()

            return {
                "task_id": self.request.id,
                "status": "finished",
                "topics": topics or "all",
                "consumer_group_id": consumer_group_id,
            }

        except Exception as e:
            error_msg = f"持续Kafka消费失败: {e}"
            self.logger.error(error_msg)

            # 记录错误
            await self.error_logger.log_task_error(
                task_name="start_continuous_consumer_task",
                task_id=self.request.id,
                error=e,
                context={"topics": topics, "consumer_group_id": consumer_group_id},
                retry_count=self.request.retries,
            )

            return {
                "task_id": self.request.id,
                "status": "failed",
                "error": error_msg,
                "topics": topics or "all",
            }

        finally:
            # 清理资源
            if "consumer" in locals():
                consumer.stop_consuming()

    return self.run_async(_start_continuous_consumer())


@app.task(base=StreamingTask, bind=True)
def produce_to_kafka_stream_task(
    self,
    data_list: List[Dict[str, Any]],
    data_type: str,
    key_field: Optional[str] = None,
):
    """
    生产数据到Kafka流任务

    Args:
        data_list: 要发送的数据列表
        data_type: 数据类型 (match/odds/scores)
        key_field: 用作消息key的字段名

    Returns:
        Dict: 发送统计结果
    """

    async def _produce_to_stream():
        try:
            producer = FootballKafkaProducer()

            # 批量发送数据
            stats = await producer.send_batch(data_list, data_type)

            self.logger.info(
                f"数据已发送到Kafka流 - 类型: {data_type}, "
                f"成功: {stats['success']}, 失败: {stats['failed']}"
            )

            return {
                "task_id": self.request.id,
                "status": "success",
                "data_type": data_type,
                "total_records": len(data_list),
                "statistics": stats,
            }

        except Exception as e:
            error_msg = f"发送数据到Kafka流失败: {e}"
            self.logger.error(error_msg)

            # 记录错误
            await self.error_logger.log_task_error(
                task_name="produce_to_kafka_stream_task",
                task_id=self.request.id,
                error=e,
                context={"data_type": data_type, "record_count": len(data_list)},
                retry_count=self.request.retries,
            )

            return {
                "task_id": self.request.id,
                "status": "failed",
                "error": error_msg,
                "data_type": data_type,
                "total_records": len(data_list),
            }

        finally:
            # 清理资源
            if "producer" in locals():
                producer.close()

    return self.run_async(_produce_to_stream())


@app.task(base=StreamingTask, bind=True)
def stream_health_check_task(self):
    """
    流处理健康检查任务

    Returns:
        Dict: 健康检查结果
    """

    async def _stream_health_check():
        try:
            processor = StreamProcessor()
            health_status = await processor.health_check()

            self.logger.info(f"流处理健康检查完成: {health_status}")

            return {
                "task_id": self.request.id,
                "status": "success",
                "health_status": health_status,
                "timestamp": health_status.get("timestamp"),
            }

        except Exception as e:
            error_msg = f"流处理健康检查失败: {e}"
            self.logger.error(error_msg)

            # 记录错误
            await self.error_logger.log_task_error(
                task_name="stream_health_check_task",
                task_id=self.request.id,
                error=e,
                context={},
                retry_count=self.request.retries,
            )

            return {"task_id": self.request.id, "status": "failed", "error": error_msg}

        finally:
            # 清理资源
            if "processor" in locals():
                processor.stop_processing()

    return self.run_async(_stream_health_check())


@app.task(base=StreamingTask, bind=True)
def stream_data_processing_task(
    self,
    topics: Optional[List[str]] = None,
    processing_duration: int = 300,  # 5分钟
):
    """
    流数据处理任务

    Args:
        topics: 要处理的Topic列表
        processing_duration: 处理持续时间（秒）

    Returns:
        Dict: 处理统计结果
    """

    async def _stream_data_processing():
        try:
            processor = StreamProcessor()

            # 启动定时流处理
            processing_task = asyncio.create_task(
                processor.start_continuous_processing(topics)
            )

            # 等待指定时间后停止
            await asyncio.sleep(processing_duration)
            processor.stop_processing()

            # 等待处理任务完成
            try:
                await asyncio.wait_for(processing_task, timeout=10.0)
            except asyncio.TimeoutError:
                processing_task.cancel()

            # 获取处理统计
            stats = processor.get_processing_stats()

            self.logger.info(f"流数据处理完成: {stats}")

            return {
                "task_id": self.request.id,
                "status": "success",
                "topics": topics or "all",
                "processing_duration": processing_duration,
                "statistics": stats,
            }

        except Exception as e:
            error_msg = f"流数据处理失败: {e}"
            self.logger.error(error_msg)

            # 记录错误
            await self.error_logger.log_task_error(
                task_name="stream_data_processing_task",
                task_id=self.request.id,
                error=e,
                context={"topics": topics, "duration": processing_duration},
                retry_count=self.request.retries,
            )

            return {
                "task_id": self.request.id,
                "status": "failed",
                "error": error_msg,
                "topics": topics or "all",
            }

        finally:
            # 清理资源
            if "processor" in locals():
                processor.stop_processing()

    return self.run_async(_stream_data_processing())


@app.task(base=StreamingTask, bind=True)
def kafka_topic_management_task(self, action: str, topic_name: Optional[str] = None):
    """
    Kafka Topic管理任务

    Args:
        action: 操作类型 (create/list/delete)
        topic_name: Topic名称（create/delete时需要）

    Returns:
        Dict: 操作结果
    """

    async def _kafka_topic_management():
        try:
            config = StreamConfig()

            if action == "list":
                # 列出所有配置的Topic
                topics = config.get_all_topics()

                self.logger.info(f"Kafka Topic列表: {topics}")

                return {
                    "task_id": self.request.id,
                    "status": "success",
                    "action": action,
                    "topics": topics,
                }

            elif action == "create" and topic_name:
                # 检查Topic是否已在配置中
                if config.is_valid_topic(topic_name):
                    topic_config = config.get_topic_config(topic_name)

                    self.logger.info(f"Topic {topic_name} 配置已存在: {topic_config}")

                    return {
                        "task_id": self.request.id,
                        "status": "success",
                        "action": action,
                        "topic_name": topic_name,
                        "message": "Topic配置已存在",
                    }
                else:
                    return {
                        "task_id": self.request.id,
                        "status": "failed",
                        "action": action,
                        "topic_name": topic_name,
                        "error": "Topic不在配置中",
                    }

            else:
                return {
                    "task_id": self.request.id,
                    "status": "failed",
                    "action": action,
                    "error": "不支持的操作或缺少参数",
                }

        except Exception as e:
            error_msg = f"Kafka Topic管理失败: {e}"
            self.logger.error(error_msg)

            # 记录错误
            await self.error_logger.log_task_error(
                task_name="kafka_topic_management_task",
                task_id=self.request.id,
                error=e,
                context={"action": action, "topic_name": topic_name},
                retry_count=self.request.retries,
            )

            return {
                "task_id": self.request.id,
                "status": "failed",
                "error": error_msg,
                "action": action,
            }

    return self.run_async(_kafka_topic_management())
