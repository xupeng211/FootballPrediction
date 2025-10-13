#!/usr/bin/env python3
"""
Kafka 测试主题初始化脚本
用于集成测试和 E2E 测试环境
"""

import os
import sys
import time
import logging
from typing import List

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from kafka import KafkaAdminClient, KafkaProducer
    from kafka.admin import NewTopic
    from kafka.errors import KafkaError
except ImportError:
    print("Warning: kafka-python not installed, skipping topic creation")
    sys.exit(0)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka 配置
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:9093')
TOPIC_PREFIX = os.getenv('KAFKA_TOPIC_PREFIX', 'test_')

# 测试主题列表
TEST_TOPICS = [
    'predictions',
    'matches',
    'audit_logs',
    'notifications',
    'analytics',
    'events',
    'errors',
    'dead_letter',
]

def create_topics(topics: List[str]) -> bool:
    """创建 Kafka 主题"""
    try:
        # 创建 Admin 客户端
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='test-topic-creator'
        )

        # 创建主题列表
        new_topics = []
        for topic in topics:
            full_topic_name = f"{TOPIC_PREFIX}{topic}"
            new_topics.append(NewTopic(
                name=full_topic_name,
                num_partitions=3,
                replication_factor=1
            ))
            logger.info(f"Preparing topic: {full_topic_name}")

        # 创建主题
        result = admin_client.create_topics(new_topics, validate_only=False)

        # 检查结果
        success_count = 0
        for topic_name, future in result.items():
            try:
                future.result()  # 等待创建完成
                logger.info(f"✅ Topic created: {topic_name}")
                success_count += 1
            except KafkaError as e:
                if e.error_name == 'TopicAlreadyExistsError':
                    logger.warning(f"⚠️ Topic already exists: {topic_name}")
                    success_count += 1
                else:
                    logger.error(f"❌ Failed to create topic {topic_name}: {e}")

        admin_client.close()
        return success_count == len(topics)

    except Exception as e:
        logger.error(f"Failed to connect to Kafka at {KAFKA_BROKER}: {e}")
        return False

def test_connection() -> bool:
    """测试 Kafka 连接"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            client_id='test-connection'
        )

        # 发送测试消息
        future = producer.send(
            f"{TOPIC_PREFIX}connection_test",
            value=b'{"test": "connection"}',
            key=b'test_key'
        )

        # 等待发送完成
        result = future.get(timeout=5)
        logger.info(f"✅ Kafka connection test successful: {result}")

        producer.close()
        return True

    except Exception as e:
        logger.error(f"❌ Kafka connection test failed: {e}")
        return False

def list_topics() -> List[str]:
    """列出所有现有主题"""
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='test-topic-lister'
        )

        topics = admin_client.list_topics()
        test_topics = [t for t in topics if t.startswith(TOPIC_PREFIX)]

        admin_client.close()
        return test_topics

    except Exception as e:
        logger.error(f"Failed to list topics: {e}")
        return []

def main():
    """主函数"""
    logger.info("Initializing Kafka test topics...")
    logger.info(f"Kafka broker: {KAFKA_BROKER}")
    logger.info(f"Topic prefix: {TOPIC_PREFIX}")

    # 等待 Kafka 启动
    logger.info("Waiting for Kafka to be ready...")
    for i in range(30):
        if test_connection():
            break
        logger.info(f"Waiting... ({i + 1}/30)")
        time.sleep(2)
    else:
        logger.error("Kafka is not ready after 60 seconds")
        sys.exit(1)

    # 创建主题
    full_topic_names = [f"{TOPIC_PREFIX}{topic}" for topic in TEST_TOPICS]
    success = create_topics(full_topic_names)

    if success:
        logger.info("✅ All test topics created successfully")

        # 列出所有测试主题
        existing_topics = list_topics()
        logger.info(f"Existing test topics: {existing_topics}")

        # 发送测试消息到每个主题
        logger.info("Sending test messages...")
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            client_id='test-message-sender'
        )

        for topic in TEST_TOPICS:
            full_topic = f"{TOPIC_PREFIX}{topic}"
            try:
                producer.send(
                    full_topic,
                    key=b'init_test',
                    value=f'{{"event": "topic_initialized", "topic": "{topic}", "timestamp": "{time.time()}"}}'.encode()
                )
                logger.info(f"✅ Test message sent to: {full_topic}")
            except Exception as e:
                logger.error(f"❌ Failed to send test message to {full_topic}: {e}")

        producer.flush()
        producer.close()

        logger.info("✅ Kafka test topics initialization completed")

    else:
        logger.error("❌ Failed to create some test topics")
        sys.exit(1)

if __name__ == "__main__":
    main()