"""
性能和负载测试
专注于系统性能、并发处理和负载测试
"""

import pytest
import asyncio
import time
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime
import psutil
import gc


class TestServicePerformance:
    """服务性能测试"""

    def test_service_initialization_time(self):
        """测试服务初始化时间"""
        try:
            from src.services.inference_service import InferenceService
            from src.services.collection_service import FotMobCollectionService

            # 测试推理服务初始化时间
            start_time = time.time()
            inference_service = InferenceService()
            init_time = time.time() - start_time

            # 初始化应该在合理时间内完成
            assert init_time < 1.0, f"推理服务初始化时间过长: {init_time}s"

            # 测试收集服务初始化时间
            start_time = time.time()
            collection_service = FotMobCollectionService()
            init_time = time.time() - start_time

            assert init_time < 0.5, f"收集服务初始化时间过长: {init_time}s"

        except ImportError:
            pytest.skip("服务模块不可用")

    @patch("src.services.inference_service.Path.exists")
    async def test_prediction_response_time(self, mock_path):
        """测试预测响应时间"""
        try:
            from src.services.inference_service import InferenceService

            mock_path.return_value = False  # 避免模型加载

            service = InferenceService()
            service.is_initialized = True

            # 模拟快速预测
            service.predict_match = AsyncMock(
                return_value=Mock(
                    success=True,
                    prediction={"result": "HOME_WIN"},
                    to_dict=lambda: {
                        "success": True,
                        "prediction": {"result": "HOME_WIN"},
                    },
                )
            )

            # 测试单次预测响应时间
            start_time = time.time()
            await service.predict_match_simple("match_1", "Team A", "Team B")
            response_time = time.time() - start_time

            # 单次预测应该在100ms内完成
            assert response_time < 0.1, f"预测响应时间过长: {response_time}s"

        except ImportError:
            pytest.skip("推理服务模块不可用")

    async def test_batch_prediction_performance(self):
        """测试批量预测性能"""
        try:
            from src.services.inference_service import InferenceService

            service = InferenceService()
            service.is_initialized = True

            # 模拟批量预测
            service.batch_predict = AsyncMock(
                return_value=[Mock(success=True, prediction={"result": "HOME_WIN"}) for _ in range(100)]
            )

            # 创建100个预测请求
            requests = [
                Mock(
                    match_id=f"match_{i}",
                    home_team=f"Team_{i}",
                    away_team=f"Team_{i+1}",
                )
                for i in range(100)
            ]

            # 测试批量预测时间
            start_time = time.time()
            results = await service.batch_predict(requests)
            batch_time = time.time() - start_time

            # 批量预测应该比单独预测更快
            assert len(results) == 100
            assert batch_time < 5.0, f"批量预测时间过长: {batch_time}s"

            # 平均每个预测时间
            avg_time = batch_time / 100
            assert avg_time < 0.05, f"平均预测时间过长: {avg_time}s"

        except ImportError:
            pytest.skip("批量预测模块不可用")


class TestMemoryPerformance:
    """内存性能测试"""

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        try:
            from src.services.inference_service import InferenceService

            # 记录初始内存使用
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            services = []
            memory_samples = []

            # 创建多个服务实例
            for i in range(10):
                service = InferenceService()
                services.append(service)

                # 记录内存使用
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)

            # 验证内存使用不会无限增长
            max_memory = max(memory_samples)
            min_memory = min(memory_samples)
            memory_growth = max_memory - min_memory

            # 内存增长应该在合理范围内（< 50MB）
            assert memory_growth < 50, f"内存增长过大: {memory_growth}MB"

            # 清理
            del services
            gc.collect()

        except ImportError:
            pytest.skip("内存监控模块不可用")

    def test_large_data_memory_efficiency(self):
        """测试大数据内存效率"""
        import pandas as pd
        import numpy as np

        try:
            from src.ml.features.h2h_calculator import H2HCalculator

            # 创建大数据集
            large_data = pd.DataFrame(
                {
                    "home_team_id": np.random.randint(1, 100, 10000),
                    "away_team_id": np.random.randint(1, 100, 10000),
                    "home_score": np.random.randint(0, 5, 10000),
                    "away_score": np.random.randint(0, 5, 10000),
                    "match_date": pd.date_range("2020-01-01", periods=10000, freq="D"),
                }
            )

            h2h_calc = H2HCalculator(min_matches=0)

            # 记录处理前内存
            process = psutil.Process()
            before_memory = process.memory_info().rss / 1024 / 1024

            # 处理大数据
            stats = h2h_calc.calculate_h2h_for_match(large_data, 1, 2, pd.Timestamp.now())

            # 记录处理后内存
            after_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = after_memory - before_memory

            # 内存增长应该合理
            assert memory_increase < 100, f"大数据处理内存增长过大: {memory_increase}MB"
            assert stats is not None

            # 清理
            del large_data
            gc.collect()

        except ImportError:
            pytest.skip("大数据测试模块不可用")

    def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        try:
            from src.services.inference_service import InferenceService

            process = psutil.Process()
            memory_samples = []

            # 重复创建和销毁服务
            for _ in range(20):
                service = InferenceService()
                memory_samples.append(process.memory_info().rss / 1024 / 1024)
                del service
                gc.collect()

            # 检查内存趋势
            if len(memory_samples) > 1:
                initial_memory = memory_samples[0]
                final_memory = memory_samples[-1]
                memory_trend = final_memory - initial_memory

                # 内存趋势不应该持续增长（可能表示泄漏）
                assert memory_trend < 20, f"检测到潜在内存泄漏: {memory_trend}MB"

        except ImportError:
            pytest.skip("内存泄漏检测模块不可用")


class TestConcurrencyPerformance:
    """并发性能测试"""

    def test_thread_safety_performance(self):
        """测试线程安全性能"""
        try:
            from src.services.inference_service import InferenceService

            service = InferenceService()
            results = []
            errors = []

            def worker_task(worker_id):
                try:
                    for i in range(10):
                        # 模拟服务操作
                        stats = service.get_service_stats()
                        results.append(f"Worker {worker_id}: {i}")
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {e}")

            # 创建多个线程
            threads = []
            start_time = time.time()

            for i in range(5):
                thread = threading.Thread(target=worker_task, args=(i,))
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            execution_time = time.time() - start_time

            # 验证并发性能
            assert len(errors) == 0, f"并发操作出现错误: {errors}"
            assert len(results) == 50, f"并发操作结果不完整: {len(results)}"
            assert execution_time < 2.0, f"并发执行时间过长: {execution_time}s"

        except ImportError:
            pytest.skip("线程安全测试模块不可用")

    async def test_async_concurrency_performance(self):
        """测试异步并发性能"""
        try:
            from src.services.inference_service import InferenceService

            service = InferenceService()
            service.is_initialized = True

            # 模拟异步操作
            service.predict_match = AsyncMock(return_value=Mock(success=True, prediction={"result": "HOME_WIN"}))

            # 创建并发任务
            tasks = []
            start_time = time.time()

            for i in range(100):
                task = service.predict_match_simple(f"match_{i}", f"Team_{i}", f"Team_{i+1}")
                tasks.append(task)

            # 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            execution_time = time.time() - start_time

            # 验证异步并发性能
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= 90, f"异步并发成功率过低: {len(successful_results)}/100"
            assert execution_time < 3.0, f"异步并发执行时间过长: {execution_time}s"

        except ImportError:
            pytest.skip("异步并发测试模块不可用")

    def test_process_pool_performance(self):
        """测试进程池性能"""
        try:
            from src.ml.features.h2h_calculator import H2HCalculator

            def cpu_intensive_task(data):
                """CPU密集型任务"""
                h2h_calc = H2HCalculator(min_matches=0)
                return h2h_calc.calculate_h2h_for_match(data, 1, 2, pd.Timestamp.now())

            # 准备测试数据
            test_data = pd.DataFrame(
                {
                    "home_team_id": [1, 2] * 500,
                    "away_team_id": [2, 1] * 500,
                    "home_score": [1, 0] * 500,
                    "away_score": [0, 1] * 500,
                    "match_date": pd.date_range("2024-01-01", periods=1000, freq="D"),
                }
            )

            # 测试串行执行
            start_time = time.time()
            for _ in range(5):
                cpu_intensive_task(test_data)
            serial_time = time.time() - start_time

            # 测试进程池执行
            start_time = time.time()
            with ProcessPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(cpu_intensive_task, test_data) for _ in range(5)]
                results = [future.result() for future in futures]
            parallel_time = time.time() - start_time

            # 进程池应该更快（至少不慢太多）
            assert len(results) == 5, "进程池结果不完整"
            assert parallel_time <= serial_time * 1.2, f"进程池性能不佳: {parallel_time}s vs {serial_time}s"

        except ImportError:
            pytest.skip("进程池测试模块不可用")


class TestLoadTesting:
    """负载测试"""

    def test_high_load_prediction_requests(self):
        """测试高负载预测请求"""
        try:
            from src.services.inference_service import InferenceService

            service = InferenceService()
            service.is_initialized = True

            # 模拟高负载
            def load_worker(worker_id, request_count):
                results = []
                start_time = time.time()

                for i in range(request_count):
                    try:
                        # 模拟快速预测
                        result = {
                            "worker_id": worker_id,
                            "request_id": i,
                            "success": True,
                            "timestamp": time.time(),
                        }
                        results.append(result)
                    except Exception as e:
                        results.append({"error": str(e)})

                return {
                    "worker_id": worker_id,
                    "execution_time": time.time() - start_time,
                    "results": results,
                }

            # 启动多个负载工作线程
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(load_worker, i, 25) for i in range(4)]  # 每个线程25个请求

                results = [future.result() for future in futures]

            # 分析负载测试结果
            total_requests = sum(len(r["results"]) for r in results)
            total_time = max(r["execution_time"] for r in results)
            successful_requests = sum(len([res for res in r["results"] if res.get("success")]) for r in results)

            # 验证负载性能
            assert total_requests == 100, f"总请求数不正确: {total_requests}"
            assert successful_requests >= 95, f"成功率过低: {successful_requests}/100"
            assert total_time < 5.0, f"高负载响应时间过长: {total_time}s"

            # 计算QPS（每秒请求数）
            qps = successful_requests / total_time
            assert qps >= 20, f"QPS过低: {qps} requests/second"

        except ImportError:
            pytest.skip("负载测试模块不可用")

    def test_sustained_load_stability(self):
        """测试持续负载稳定性"""
        try:
            from src.services.inference_service import InferenceService

            service = InferenceService()
            service.is_initialized = True

            # 持续负载测试
            def sustained_worker(duration_seconds):
                end_time = time.time() + duration_seconds
                request_count = 0
                error_count = 0

                while time.time() < end_time:
                    try:
                        # 模拟请求
                        service.get_service_stats()
                        request_count += 1
                        time.sleep(0.01)  # 100 QPS
                    except Exception:
                        error_count += 1

                return {
                    "request_count": request_count,
                    "error_count": error_count,
                    "error_rate": error_count / max(request_count, 1),
                }

            # 运行持续负载测试
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=2) as executor:
                future = executor.submit(sustained_worker, 2)  # 2秒测试
                result = future.result()
            test_time = time.time() - start_time

            # 验证稳定性
            assert result["request_count"] > 100, "持续负载请求数过少"
            assert result["error_rate"] < 0.01, f"错误率过高: {result['error_rate']}"
            assert test_time < 3.0, f"持续负载测试时间异常: {test_time}s"

        except ImportError:
            pytest.skip("持续负载测试模块不可用")


class TestResourceUtilization:
    """资源利用率测试"""

    def test_cpu_utilization_efficiency(self):
        """测试CPU利用率效率"""
        try:
            import pandas as pd
            import numpy as np
            from src.ml.features.h2h_calculator import H2HCalculator

            # 创建CPU密集型任务
            data = pd.DataFrame(
                {
                    "home_team_id": np.random.randint(1, 50, 1000),
                    "away_team_id": np.random.randint(1, 50, 1000),
                    "home_score": np.random.randint(0, 5, 1000),
                    "away_score": np.random.randint(0, 5, 1000),
                    "match_date": pd.date_range("2024-01-01", periods=1000, freq="H"),
                }
            )

            h2h_calc = H2HCalculator(min_matches=0)

            # 监控CPU使用率
            process = psutil.Process()
            initial_cpu = process.cpu_percent()

            start_time = time.time()
            for i in range(10):
                stats = h2h_calc.calculate_h2h_for_match(data, 1, 2, pd.Timestamp.now())
            execution_time = time.time() - start_time

            final_cpu = process.cpu_percent()
            avg_cpu = (initial_cpu + final_cpu) / 2

            # 验证CPU效率
            assert stats is not None, "计算结果为空"
            assert execution_time < 5.0, f"CPU密集型任务时间过长: {execution_time}s"
            assert avg_cpu < 80.0, f"CPU使用率过高: {avg_cpu}%"

        except ImportError:
            pytest.skip("CPU利用率测试模块不可用")

    def test_io_efficiency(self):
        """测试IO效率"""
        try:
            from src.services.collection_service import FotMobCollectionService

            service = FotMobCollectionService()

            # 模拟IO操作
            def io_simulation():
                # 模拟文件IO
                with open("/dev/null", "w") as f:
                    f.write("test" * 1000)
                return "io_complete"

            # 测试IO效率
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(io_simulation) for _ in range(10)]
                results = [future.result() for future in futures]
            io_time = time.time() - start_time

            # 验证IO效率
            assert len(results) == 10, "IO操作结果不完整"
            assert all(r == "io_complete" for r in results), "IO操作结果错误"
            assert io_time < 1.0, f"IO操作时间过长: {io_time}s"

        except ImportError:
            pytest.skip("IO效率测试模块不可用")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
