#!/usr/bin/env python3
"""
集成测试环境设置和验证脚本
用于Phase 4集成测试的前置环境检查
"""

import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
import redis
import requests

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cache.redis_manager import RedisManager
from core.config import get_settings
from database.config import DatabaseConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegrationTestEnvironment:
    """集成测试环境管理器"""

    def __init__(self):
        self.settings = get_settings()
        self.services_status = {}
        self.start_time = time.time()

    async def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            config = DatabaseConfig()

            # 尝试连接PostgreSQL
            conn = psycopg2.connect(
                host=config.host or "localhost",
                port=config.port or 5432,
                database=config.database or "football_prediction_integration_test",
                user=config.username or "football_user",
                password=config.password or "football_integration_pass",
                connect_timeout=5,
            )

            # 执行简单查询验证连接
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            conn.close()

            self.services_status["database"] = {
                "status": "healthy",
                "response_time": time.time() - self.start_time,
                "details": f"Connected to PostgreSQL at {config.host}:{config.port}",
            }

            logger.info("✅ Database connection successful")
            return True

        except Exception as e:
            self.services_status["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Database connection failed: {e}")
            return False

    async def check_redis_connection(self) -> bool:
        """检查Redis连接"""
        try:
            redis_manager = RedisManager()
            client = redis_manager.get_client()

            # 测试连接
            result = client.ping()

            self.services_status["redis"] = {
                "status": "healthy" if result else "unhealthy",
                "response_time": time.time() - self.start_time,
                "details": "Redis ping successful",
            }

            logger.info("✅ Redis connection successful")
            return result

        except Exception as e:
            self.services_status["redis"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Redis connection failed: {e}")
            return False

    async def check_kafka_connection(self) -> bool:
        """检查Kafka连接（使用kafka-python库）"""
        try:
            from kafka import KafkaProducer
            from kafka.errors import KafkaError

            # 尝试创建Kafka生产者
            producer = KafkaProducer(
                bootstrap_servers=["localhost:9092"],
                value_serializer=lambda v: str(v).encode("utf-8"),
                request_timeout_ms=5000,
            )

            # 发送测试消息
            future = producer.send("integration_test_topic", value="test_message")
            result = future.get(timeout=5)

            producer.close()

            self.services_status["kafka"] = {
                "status": "healthy",
                "response_time": time.time() - self.start_time,
                "details": f"Message sent to topic {result.topic}, partition {result.partition}",
            }

            logger.info("✅ Kafka connection successful")
            return True

        except Exception as e:
            self.services_status["kafka"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Kafka connection failed: {e}")
            return False

    async def check_feast_connection(self) -> bool:
        """检查Feast特征存储连接"""
        try:
            from feast import FeatureStore

            # 尝试初始化Feast存储
            store = FeatureStore(repo_path="/tmp/feast_integration_test")

            # 测试获取特征定义
            features = store.list_features()

            self.services_status["feast"] = {
                "status": "healthy",
                "response_time": time.time() - self.start_time,
                "details": f"Connected to Feast, found {len(features)} features",
            }

            logger.info("✅ Feast connection successful")
            return True

        except Exception as e:
            self.services_status["feast"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ Feast connection failed: {e}")
            return False

    async def check_fastapi_service(self) -> bool:
        """检查FastAPI服务是否运行"""
        try:
            # 尝试访问健康检查端点
            response = requests.get("http://localhost:8000/health", timeout=5)

            if response.status_code == 200:
                health_data = response.json()
                self.services_status["fastapi"] = {
                    "status": "healthy",
                    "response_time": time.time() - self.start_time,
                    "details": health_data,
                }
                logger.info("✅ FastAPI service healthy")
                return True
            else:
                raise Exception(f"HTTP {response.status_code}")

        except Exception as e:
            self.services_status["fastapi"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - self.start_time,
            }
            logger.error(f"❌ FastAPI service check failed: {e}")
            return False

    async def run_all_checks(self) -> Dict[str, bool]:
        """运行所有服务检查"""
        logger.info("🚀 Starting integration test environment checks...")

        checks = {
            "database": await self.check_database_connection(),
            "redis": await self.check_redis_connection(),
            "kafka": await self.check_kafka_connection(),
            "feast": await self.check_feast_connection(),
            "fastapi": await self.check_fastapi_service(),
        }

        return checks

    def print_status_report(self):
        """打印状态报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 Integration Test Environment Status Report")
        logger.info("=" * 60)

        for service, status_info in self.services_status.items():
            status = status_info.get("status", "unknown")
            response_time = status_info.get("response_time", 0)

            if status == "healthy":
                logger.info(f"✅ {service.upper():<10}: Healthy ({response_time:.2f}s)")
            else:
                error = status_info.get("error", "Unknown error")
                logger.error(f"❌ {service.upper():<10}: Unhealthy - {error}")

        # 计算健康服务数量
        healthy_count = sum(
            1
            for info in self.services_status.values()
            if info.get("status") == "healthy"
        )
        total_count = len(self.services_status)

        logger.info(
            f"\n📈 Overall Health: {healthy_count}/{total_count} services healthy"
        )

        if healthy_count == total_count:
            logger.info("🎉 All services are healthy!")
        elif healthy_count >= total_count * 0.8:  # 80%以上服务健康
            logger.info("⚠️  Most services are healthy, but some issues detected")
        else:
            logger.error("🚨 Critical service issues detected")

    def is_ready_for_integration_tests(
        self, required_services: List[str] = None
    ) -> bool:
        """检查是否准备好进行集成测试"""
        if required_services is None:
            required_services = ["database", "redis"]  # 基础必需服务

        healthy_required = [
            service
            for service in required_services
            if self.services_status.get(service, {}).get("status") == "healthy"
        ]

        return len(healthy_required) == len(required_services)


async def main():
    """主函数"""
    env_checker = IntegrationTestEnvironment()

    # 运行所有检查
    checks = await env_checker.run_all_checks()

    # 打印状态报告
    env_checker.print_status_report()

    # 检查是否准备好进行集成测试
    if env_checker.is_ready_for_integration_tests(["database", "redis"]):
        logger.info("✅ Environment is ready for integration tests")
        return 0
    else:
        logger.error("❌ Environment is not ready for integration tests")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Integration test setup interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
