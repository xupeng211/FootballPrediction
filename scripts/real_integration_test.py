#!/usr/bin/env python3
"""
简化的集成测试脚本
使用真实依赖进行测试
"""

import asyncio
import sys
import time
import logging
from typing import Dict, List, Optional
import subprocess
import requests
import psycopg2
import redis
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealIntegrationTester:
    """真实集成测试器"""

    def __init__(self):
        self.services_status = {}
        self.start_time = time.time()

    def test_postgresql_connection(self) -> bool:
        """测试PostgreSQL连接"""
        try:
            # 使用测试环境配置
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="football_prediction_test",
                user="postgres",
                password="postgres",
                connect_timeout=10
            )

            # 执行简单查询
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                result = cursor.fetchone()
                logger.info(f"PostgreSQL version: {result[0]}")

            conn.close()

            self.services_status['postgresql'] = {
                'status': 'healthy',
                'response_time': time.time() - self.start_time,
                'details': f"Connected to PostgreSQL: {result[0]}"
            }

            logger.info("✅ PostgreSQL connection successful")
            return True

        except Exception as e:
            self.services_status['postgresql'] = {
                'status': 'unhealthy',
                'error': str(e),
                'response_time': time.time() - self.start_time
            }
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return False

    def test_redis_connection(self) -> bool:
        """测试Redis连接"""
        try:
            # 连接到Redis
            client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True,
                socket_timeout=5
            )

            # 测试连接
            result = client.ping()

            # 测试写入和读取
            client.set('integration_test_key', 'test_value')
            value = client.get('integration_test_key')
            client.delete('integration_test_key')

            if value == 'test_value':
                self.services_status['redis'] = {
                    'status': 'healthy',
                    'response_time': time.time() - self.start_time,
                    'details': "Redis ping and read/write successful"
                }

                logger.info("✅ Redis connection successful")
                return True
            else:
                raise Exception("Redis read/write test failed")

        except Exception as e:
            self.services_status['redis'] = {
                'status': 'unhealthy',
                'error': str(e),
                'response_time': time.time() - self.start_time
            }
            logger.error(f"❌ Redis connection failed: {e}")
            return False

    def test_kafka_connection(self) -> bool:
        """测试Kafka连接"""
        try:
            from kafka import KafkaProducer
            from kafka.errors import KafkaError

            # 创建Kafka生产者
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9092'],
                value_serializer=lambda v: str(v).encode('utf-8'),
                request_timeout_ms=10000
            )

            # 发送测试消息
            future = producer.send('integration_test_topic', value='test_message')
            result = future.get(timeout=10)

            producer.close()

            self.services_status['kafka'] = {
                'status': 'healthy',
                'response_time': time.time() - self.start_time,
                'details': f"Message sent to topic {result.topic}, partition {result.partition}, offset {result.offset}"
            }

            logger.info("✅ Kafka connection successful")
            return True

        except Exception as e:
            self.services_status['kafka'] = {
                'status': 'unhealthy',
                'error': str(e),
                'response_time': time.time() - self.start_time
            }
            logger.error(f"❌ Kafka connection failed: {e}")
            return False

    def run_integration_tests(self) -> Dict[str, bool]:
        """运行所有集成测试"""
        logger.info("🚀 Starting real integration tests...")

        tests = {
            'postgresql': self.test_postgresql_connection(),
            'redis': self.test_redis_connection(),
            'kafka': self.test_kafka_connection()
        }

        return tests

    def print_status_report(self):
        """打印状态报告"""
        logger.info("\n" + "="*60)
        logger.info("📊 Real Integration Test Results")
        logger.info("="*60)

        for service, status_info in self.services_status.items():
            status = status_info.get('status', 'unknown')
            response_time = status_info.get('response_time', 0)

            if status == 'healthy':
                details = status_info.get('details', '')
                logger.info(f"✅ {service.upper():<10}: Healthy ({response_time:.2f}s) - {details}")
            else:
                error = status_info.get('error', 'Unknown error')
                logger.error(f"❌ {service.upper():<10}: Unhealthy - {error}")

        # 计算健康服务数量
        healthy_count = sum(1 for info in self.services_status.values()
                          if info.get('status') == 'healthy')
        total_count = len(self.services_status)

        logger.info(f"\n📈 Integration Test Results: {healthy_count}/{total_count} services healthy")

        if healthy_count == total_count:
            logger.info("🎉 All services are healthy!")
        elif healthy_count >= total_count * 0.8:  # 80%以上服务健康
            logger.info("⚠️  Most services are healthy, but some issues detected")
        else:
            logger.error("🚨 Critical service issues detected")

    def get_test_summary(self) -> Dict:
        """获取测试摘要"""
        healthy_count = sum(1 for info in self.services_status.values()
                          if info.get('status') == 'healthy')
        total_count = len(self.services_status)

        return {
            'total_services': total_count,
            'healthy_services': healthy_count,
            'success_rate': healthy_count / total_count if total_count > 0 else 0,
            'services_status': self.services_status
        }


def main():
    """主函数"""
    tester = RealIntegrationTester()

    # 运行集成测试
    tests = tester.run_integration_tests()

    # 打印状态报告
    tester.print_status_report()

    # 获取测试摘要
    summary = tester.get_test_summary()

    logger.info(f"\n📋 Test Summary:")
    logger.info(f"   Total Services: {summary['total_services']}")
    logger.info(f"   Healthy Services: {summary['healthy_services']}")
    logger.info(f"   Success Rate: {summary['success_rate']*100:.1f}%")

    # 判断是否成功
    if summary['success_rate'] >= 0.8:  # 80%以上服务健康
        logger.info("✅ Integration tests passed!")
        return 0
    else:
        logger.error("❌ Integration tests failed!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Integration test interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)