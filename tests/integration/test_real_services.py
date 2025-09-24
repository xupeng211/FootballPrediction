#!/usr/bin/env python3
"""
真实的集成测试
直接测试Docker服务，不依赖FastAPI应用
"""

import asyncio
import sys
import time
from pathlib import Path

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestRealServicesIntegration:
    """真实服务集成测试"""

    def test_postgresql_real_connection(self):
        """测试真实PostgreSQL连接"""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="football_prediction_test",
                user="postgres",
                password="postgres",
                connect_timeout=10,
            )

            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                result = cursor.fetchone()
                print(f"PostgreSQL version: {result[0]}")

            conn.close()
            assert result is not None
            assert "PostgreSQL" in result[0]

        except Exception as e:
            pytest.fail(f"PostgreSQL connection failed: {e}")

    def test_redis_real_connection(self):
        """测试真实Redis连接"""
        import redis

        try:
            client = redis.Redis(
                host="localhost", port=6379, decode_responses=True, socket_timeout=5
            )

            # 测试连接
            result = client.ping()
            assert result is True

            # 测试写入和读取
            client.set("integration_test_key", "test_value")
            value = client.get("integration_test_key")
            client.delete("integration_test_key")

            assert value == "test_value"

        except Exception as e:
            pytest.fail(f"Redis connection failed: {e}")

    def test_kafka_real_connection(self):
        """测试真实Kafka连接"""
        from kafka import KafkaProducer
        from kafka.errors import KafkaError

        try:
            producer = KafkaProducer(
                bootstrap_servers=["localhost:9092"],
                value_serializer=lambda v: str(v).encode("utf-8"),
                request_timeout_ms=10000,
            )

            # 发送测试消息
            future = producer.send("test_integration_topic", value="test_message")
            result = future.get(timeout=10)

            producer.close()

            assert result.topic == "test_integration_topic"
            assert result.partition == 0
            assert result.offset >= 0

        except Exception as e:
            pytest.fail(f"Kafka connection failed: {e}")

    def test_service_connectivity_summary(self):
        """服务连接性汇总测试"""
        services = {
            "postgresql": self.test_postgresql_real_connection,
            "redis": self.test_redis_real_connection,
            "kafka": self.test_kafka_real_connection,
        }

        results = {}
        for service_name, test_func in services.items():
            try:
                test_func()
                results[service_name] = "healthy"
            except Exception as e:
                results[service_name] = f"unhealthy: {e}"

        healthy_count = sum(1 for status in results.values() if status == "healthy")
        total_count = len(results)

        print(f"\n📊 Service Connectivity Summary:")
        print(f"   Healthy: {healthy_count}/{total_count}")
        for service, status in results.items():
            icon = "✅" if status == "healthy" else "❌"
            print(f"   {icon} {service}: {status}")

        # 至少80%的服务必须健康
        success_rate = healthy_count / total_count
        assert success_rate >= 0.8, f"Only {success_rate*100:.1f}% services are healthy"


@pytest.mark.asyncio
async def test_async_services_check():
    """异步服务检查"""

    async def check_postgres():
        import psycopg2

        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="football_prediction_test",
                user="postgres",
                password="postgres",
                connect_timeout=5,
            )
            conn.close()
            return True
        except:
            return False

    async def check_redis():
        import redis

        try:
            client = redis.Redis(host="localhost", port=6379, socket_timeout=5)
            result = client.ping()
            return result
        except:
            return False

    # 并发检查所有服务
    start_time = time.time()
    tasks = [check_postgres(), check_redis()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()

    postgres_ok = results[0] is True
    redis_ok = results[1] is True

    assert postgres_ok, "PostgreSQL check failed"
    assert redis_ok, "Redis check failed"

    # 验证响应时间
    response_time = end_time - start_time
    assert response_time < 5.0, f"Service check took too long: {response_time:.2f}s"

    print(f"✅ Async services check completed in {response_time:.2f}s")


if __name__ == "__main__":
    # 简单的测试运行器
    test_instance = TestRealServicesIntegration()

    print("🚀 Starting real services integration tests...")

    try:
        test_instance.test_postgresql_real_connection()
        print("✅ PostgreSQL test passed")
    except Exception as e:
        print(f"❌ PostgreSQL test failed: {e}")

    try:
        test_instance.test_redis_real_connection()
        print("✅ Redis test passed")
    except Exception as e:
        print(f"❌ Redis test failed: {e}")

    try:
        test_instance.test_kafka_real_connection()
        print("✅ Kafka test passed")
    except Exception as e:
        print(f"❌ Kafka test failed: {e}")

    try:
        test_instance.test_service_connectivity_summary()
        print("✅ Service connectivity summary test passed")
    except Exception as e:
        print(f"❌ Service connectivity summary test failed: {e}")

    print("🎉 All integration tests completed!")
