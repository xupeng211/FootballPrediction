#!/usr/bin/env python3
"""
服务性能测试
直接测试PostgreSQL、Redis、Kafka的性能
"""

import asyncio
import concurrent.futures
import json
import statistics

# 添加项目根目录到Python路径
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class ServicePerformanceTester:
    """服务性能测试器"""

    def __init__(self):
        self.results = {}

    def test_postgresql_performance(self, num_tests: int = 100) -> Dict[str, Any]:
        """测试PostgreSQL性能"""
        import psycopg2
        from psycopg2 import sql

        try:
            # 建立连接
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="football_prediction_test",
                user="postgres",
                password="postgres",
                connect_timeout=10,
            )

            times = []
            successful_queries = 0

            # 创建测试表
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS performance_test (
                        id SERIAL PRIMARY KEY,
                        test_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.commit()

            # 执行查询测试
            for i in range(num_tests):
                start_time = time.time()

                try:
                    with conn.cursor() as cursor:
                        # 插入测试
                        cursor.execute(
                            "INSERT INTO performance_test (test_data) VALUES (%s)",
                            (f"test_data_{i}",),
                        )

                        # 查询测试
                        cursor.execute("SELECT COUNT(*) FROM performance_test")
                        count = cursor.fetchone()[0]

                        conn.commit()

                        end_time = time.time()
                        times.append(end_time - start_time)
                        successful_queries += 1

                except Exception as e:
                    conn.rollback()
                    continue

            # 清理测试数据
            with conn.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS performance_test")
                conn.commit()

            conn.close()

            # 计算统计信息
            if times:
                return {
                    "service": "postgresql",
                    "total_tests": num_tests,
                    "successful_tests": successful_queries,
                    "success_rate": successful_queries / num_tests,
                    "avg_response_time": statistics.mean(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times),
                    "median_response_time": statistics.median(times),
                    "p95_response_time": (
                        statistics.quantiles(times, n=20)[18]
                        if len(times) > 20
                        else max(times)
                    ),
                    "throughput_qps": (
                        successful_queries / sum(times) if sum(times) > 0 else 0
                    ),
                }
            else:
                return {
                    "service": "postgresql",
                    "total_tests": num_tests,
                    "successful_tests": 0,
                    "success_rate": 0,
                    "error": "No successful queries",
                }

        except Exception as e:
            return {
                "service": "postgresql",
                "total_tests": num_tests,
                "successful_tests": 0,
                "success_rate": 0,
                "error": str(e),
            }

    def test_redis_performance(self, num_tests: int = 1000) -> Dict[str, Any]:
        """测试Redis性能"""
        import redis

        try:
            client = redis.Redis(
                host="localhost", port=6379, decode_responses=True, socket_timeout=5
            )

            times = []
            successful_ops = 0

            for i in range(num_tests):
                start_time = time.time()

                try:
                    # 写入测试
                    key = f"perf_test_{i}"
                    value = f"test_value_{i}"
                    client.set(key, value)

                    # 读取测试
                    retrieved_value = client.get(key)

                    # 删除测试
                    client.delete(key)

                    end_time = time.time()

                    if retrieved_value == value:
                        times.append(end_time - start_time)
                        successful_ops += 1

                except Exception:
                    continue

            # 计算统计信息
            if times:
                return {
                    "service": "redis",
                    "total_tests": num_tests,
                    "successful_tests": successful_ops,
                    "success_rate": successful_ops / num_tests,
                    "avg_response_time": statistics.mean(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times),
                    "median_response_time": statistics.median(times),
                    "p95_response_time": (
                        statistics.quantiles(times, n=20)[18]
                        if len(times) > 20
                        else max(times)
                    ),
                    "throughput_ops": (
                        successful_ops / sum(times) if sum(times) > 0 else 0
                    ),
                }
            else:
                return {
                    "service": "redis",
                    "total_tests": num_tests,
                    "successful_tests": 0,
                    "success_rate": 0,
                    "error": "No successful operations",
                }

        except Exception as e:
            return {
                "service": "redis",
                "total_tests": num_tests,
                "successful_tests": 0,
                "success_rate": 0,
                "error": str(e),
            }

    def test_kafka_performance(self, num_tests: int = 100) -> Dict[str, Any]:
        """测试Kafka性能"""
        import threading

        from kafka import KafkaConsumer, KafkaProducer
        from kafka.errors import KafkaError

        try:
            times = []
            successful_messages = 0

            # 创建生产者和消费者
            producer = KafkaProducer(
                bootstrap_servers=["localhost:9092"],
                value_serializer=lambda v: str(v).encode("utf-8"),
                request_timeout_ms=10000,
            )

            consumer = KafkaConsumer(
                "performance_test_topic",
                bootstrap_servers=["localhost:9092"],
                auto_offset_reset="earliest",
                consumer_timeout_ms=1000,
                value_deserializer=lambda m: m.decode("utf-8"),
            )

            def consume_messages():
                """消费消息的线程函数"""
                nonlocal successful_messages
                try:
                    for message in consumer:
                        if message.value.startswith("perf_test_"):
                            successful_messages += 1
                except Exception:
                    pass

            # 启动消费者线程
            consumer_thread = threading.Thread(target=consume_messages)
            consumer_thread.start()

            # 发送消息测试
            for i in range(num_tests):
                start_time = time.time()

                try:
                    future = producer.send(
                        "performance_test_topic", value=f"perf_test_{i}"
                    )
                    result = future.get(timeout=5)

                    end_time = time.time()
                    times.append(end_time - start_time)

                except Exception:
                    continue

            producer.close()
            consumer_thread.join(timeout=5)
            consumer.close()

            # 计算统计信息
            if times:
                return {
                    "service": "kafka",
                    "total_tests": num_tests,
                    "successful_tests": len(times),
                    "success_rate": len(times) / num_tests,
                    "avg_response_time": statistics.mean(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times),
                    "median_response_time": statistics.median(times),
                    "p95_response_time": (
                        statistics.quantiles(times, n=20)[18]
                        if len(times) > 20
                        else max(times)
                    ),
                    "throughput_msgps": (
                        len(times) / sum(times) if sum(times) > 0 else 0
                    ),
                    "consumer_success_rate": (
                        successful_messages / num_tests if num_tests > 0 else 0
                    ),
                }
            else:
                return {
                    "service": "kafka",
                    "total_tests": num_tests,
                    "successful_tests": 0,
                    "success_rate": 0,
                    "error": "No successful messages",
                }

        except Exception as e:
            return {
                "service": "kafka",
                "total_tests": num_tests,
                "successful_tests": 0,
                "success_rate": 0,
                "error": str(e),
            }

    def run_concurrent_performance_test(
        self, num_threads: int = 10, tests_per_thread: int = 10
    ):
        """运行并发性能测试"""
        print(f"🚀 Starting concurrent performance test with {num_threads} threads...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            # 提交Redis并发测试
            futures = []
            for i in range(num_threads):
                future = executor.submit(self.test_redis_performance, tests_per_thread)
                futures.append(future)

            # 收集结果
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    print(f"❌ Thread failed: {e}")

        # 汇总结果
        if results:
            total_tests = sum(r["total_tests"] for r in results)
            successful_tests = sum(r["successful_tests"] for r in results)
            all_times = []

            for r in results:
                if "avg_response_time" in r:
                    # 基于平均值模拟一些时间点
                    all_times.extend([r["avg_response_time"]] * r["successful_tests"])

            if all_times:
                return {
                    "test_type": "concurrent_redis",
                    "total_threads": num_threads,
                    "tests_per_thread": tests_per_thread,
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "success_rate": successful_tests / total_tests,
                    "avg_response_time": statistics.mean(all_times),
                    "min_response_time": min(all_times),
                    "max_response_time": max(all_times),
                    "throughput_ops": (
                        successful_tests / sum(all_times) if sum(all_times) > 0 else 0
                    ),
                }
            else:
                return {"error": "No successful operations in concurrent test"}
        else:
            return {"error": "No results from concurrent test"}

    def run_comprehensive_performance_test(self):
        """运行全面的性能测试"""
        print("🚀 Starting comprehensive performance tests...")

        # 单线程性能测试
        print("📊 Running single-threaded performance tests...")
        postgresql_result = self.test_postgresql_performance(50)
        redis_result = self.test_redis_performance(500)
        kafka_result = self.test_kafka_performance(50)

        # 并发性能测试
        print("📊 Running concurrent performance tests...")
        concurrent_result = self.run_concurrent_performance_test(5, 20)

        # 汇总结果
        self.results = {
            "single_threaded": {
                "postgresql": postgresql_result,
                "redis": redis_result,
                "kafka": kafka_result,
            },
            "concurrent": concurrent_result,
            "test_summary": {
                "total_tests_run": 3,
                "services_tested": ["postgresql", "redis", "kafka"],
                "concurrency_tested": True,
            },
        }

        return self.results

    def generate_performance_report(self):
        """生成性能测试报告"""
        print("\n" + "=" * 60)
        print("📊 Service Performance Test Report")
        print("=" * 60)

        # 单线程测试结果
        print("\n🔹 Single-threaded Performance:")
        for service, result in self.results.get("single_threaded", {}).items():
            print(f"\n   {service.upper()}:")
            if "error" in result:
                print(f"     ❌ Error: {result['error']}")
            else:
                print(f"     ✅ Success Rate: {result['success_rate']*100:.1f}%")
                print(
                    f"     ⏱️  Avg Response: {result['avg_response_time']*1000:.2f}ms"
                )
                print(f"     📊 P95 Response: {result['p95_response_time']*1000:.2f}ms")
                print(
                    f"     🚀 Throughput: {result.get('throughput_qps', result.get('throughput_ops', 0)):.1f} ops/sec"
                )

        # 并发测试结果
        concurrent_result = self.results.get("concurrent", {})
        if concurrent_result and "error" not in concurrent_result:
            print(
                f"\n🔹 Concurrent Performance ({concurrent_result['total_threads']} threads):"
            )
            print(f"     ✅ Success Rate: {concurrent_result['success_rate']*100:.1f}%")
            print(
                f"     ⏱️  Avg Response: {concurrent_result['avg_response_time']*1000:.2f}ms"
            )
            print(
                f"     🚀 Throughput: {concurrent_result['throughput_ops']:.1f} ops/sec"
            )

        # 保存报告
        report_path = Path("reports/service_performance_report.json")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 Detailed report saved to: {report_path}")

        # 性能评估
        self.evaluate_performance()

    def evaluate_performance(self):
        """评估性能结果"""
        print("\n🎯 Performance Evaluation:")

        single_threaded = self.results.get("single_threaded", {})
        concurrent = self.results.get("concurrent", {})

        # 评估标准
        criteria = {
            "postgresql": {
                "avg_response_ms": 50,
                "p95_response_ms": 100,
                "success_rate": 0.95,
            },
            "redis": {
                "avg_response_ms": 5,
                "p95_response_ms": 10,
                "success_rate": 0.99,
            },
            "kafka": {
                "avg_response_ms": 20,
                "p95_response_ms": 50,
                "success_rate": 0.95,
            },
        }

        passed_services = 0
        total_services = len(criteria)

        for service, standard in criteria.items():
            if service in single_threaded:
                result = single_threaded[service]
                if "error" not in result:
                    avg_ms = result["avg_response_time"] * 1000
                    p95_ms = result["p95_response_time"] * 1000
                    success_rate = result["success_rate"]

                    if (
                        avg_ms <= standard["avg_response_ms"]
                        and p95_ms <= standard["p95_response_ms"]
                        and success_rate >= standard["success_rate"]
                    ):
                        print(f"   ✅ {service.upper()}: PASSED")
                        passed_services += 1
                    else:
                        print(f"   ❌ {service.upper()}: FAILED")
                        if avg_ms > standard["avg_response_ms"]:
                            print(
                                f"      Avg response too high: {avg_ms:.1f}ms > {standard['avg_response_ms']}ms"
                            )
                        if p95_ms > standard["p95_response_ms"]:
                            print(
                                f"      P95 response too high: {p95_ms:.1f}ms > {standard['p95_response_ms']}ms"
                            )
                        if success_rate < standard["success_rate"]:
                            print(
                                f"      Success rate too low: {success_rate*100:.1f}% < {standard['success_rate']*100:.1f}%"
                            )
                else:
                    print(f"   ❌ {service.upper()}: ERROR - {result['error']}")

        print(
            f"\n📈 Overall Performance Score: {passed_services}/{total_services} services passed"
        )

        if passed_services == total_services:
            print("🎉 All services meet performance requirements!")
        elif passed_services >= total_services * 0.8:
            print(
                "⚠️  Most services meet performance requirements, but some need optimization"
            )
        else:
            print("🚨 Many services fail to meet performance requirements")


def main():
    """主函数"""
    tester = ServicePerformanceTester()

    try:
        # 运行性能测试
        results = tester.run_comprehensive_performance_test()

        # 生成报告
        tester.generate_performance_report()

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Performance test interrupted")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
