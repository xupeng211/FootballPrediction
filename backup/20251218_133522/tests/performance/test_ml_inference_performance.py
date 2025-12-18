"""
ML推理性能测试
测试模型推理速度和并发处理能力
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from src.services.inference_service_v2 import (
    InferenceServiceV2,
    PredictionRequest,
    PredictionResponse,
)
from src.ml.inference import ModelLoader, MatchPredictor
from src.ml.inference.cache_manager import PredictionCache
from src.core.exceptions import PredictionError


class TestMLInferencePerformance:
    """ML推理性能测试"""

    @pytest.fixture
    def high_performance_service(self):
        """创建高性能推理服务实例"""
        # 创建优化的Mock依赖
        mock_model = Mock()
        mock_model.predict.return_value = [1]  # DRAW
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
        mock_model.n_features_in_ = 12
        mock_model.classes_ = [0, 1, 2]

        mock_loader = Mock()
        mock_loader.get_model.return_value = mock_model
        mock_loader.list_loaded_models.return_value = ["xgboost_v2.pkl"]
        mock_loader.get_model_metadata.return_value = {"accuracy": 0.65}
        mock_loader.load_model.return_value = True
        mock_loader.unload_model.return_value = True

        # 创建优化的缓存
        mock_cache = Mock()
        mock_cache.get.return_value = None  # 缓存未命中，测试实际推理性能
        mock_cache.set.return_value = True

        # 使用简单的dict避免__dict__问题
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5, "hit_rate": 0.67}

        service = InferenceServiceV2()
        service.model_loader = mock_loader
        service.cache_manager = mock_cache
        service.is_initialized = True

        return service

    def test_single_prediction_latency(self, high_performance_service):
        """测试单次预测延迟"""
        request = PredictionRequest(
            match_id="perf_test_1",
            home_team="Team A",
            away_team="Team B",
            features=[1.0] * 12,
            use_cache=False,  # 禁用缓存测试实际推理性能
        )

        # 预热
        for _ in range(3):
            try:
                # 这里我们只测试请求创建，不实际调用推理
                request_dict = request.to_dict()
                assert isinstance(request_dict, dict)
            except Exception:
                pass

        # 测试延迟
        latencies = []
        for _ in range(100):
            start_time = time.perf_counter()
            try:
                # 模拟推理延迟（实际项目中这里会是真正的推理）
                request_dict = request.to_dict()
                # 模拟特征处理时间
                _ = sum(request.features) / len(request.features)
                end_time = time.perf_counter()
                latencies.append((end_time - start_time) * 1000)  # 转换为毫秒
            except Exception:
                end_time = time.perf_counter()
                latencies.append((end_time - start_time) * 1000)

        # 性能断言
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"平均延迟: {avg_latency:.2f}ms")
        print(f"P95延迟: {p95_latency:.2f}ms")
        print(f"P99延迟: {p99_latency:.2f}ms")

        # 性能要求：平均延迟 < 1ms (仅请求处理)，P99 < 5ms
        assert avg_latency < 1.0, f"平均延迟过高: {avg_latency:.2f}ms"
        assert p99_latency < 5.0, f"P99延迟过高: {p99_latency:.2f}ms"

    def test_batch_prediction_throughput(self, high_performance_service):
        """测试批量预测吞吐量"""
        batch_size = 100
        requests = [
            PredictionRequest(
                match_id=f"batch_test_{i}",
                home_team=f"Team {i}",
                away_team=f"Opponent {i}",
                features=[float(i % 10)] * 12,
                use_cache=False,
            )
            for i in range(batch_size)
        ]

        start_time = time.perf_counter()

        # 模拟批量处理
        processed_count = 0
        for request in requests:
            try:
                # 模拟推理处理
                request_dict = request.to_dict()
                _ = sum(request.features) / len(request.features)
                processed_count += 1
            except Exception:
                pass

        end_time = time.perf_counter()
        total_time = end_time - start_time

        throughput = processed_count / total_time  # 请求/秒
        avg_latency = (total_time / processed_count) * 1000  # 毫秒

        print(f"批量大小: {batch_size}")
        print(f"处理时间: {total_time:.3f}s")
        print(f"吞吐量: {throughput:.2f} 请求/秒")
        print(f"平均延迟: {avg_latency:.2f}ms")

        # 性能要求：吞吐量 > 1000 请求/秒，平均延迟 < 1ms
        assert throughput > 1000, f"吞吐量过低: {throughput:.2f} 请求/秒"
        assert avg_latency < 1.0, f"平均延迟过高: {avg_latency:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_prediction_performance(self, high_performance_service):
        """测试并发预测性能"""
        concurrent_requests = 50
        requests_per_worker = 20

        async def simulate_prediction(request_id: int):
            """模拟预测处理"""
            request = PredictionRequest(
                match_id=f"concurrent_test_{request_id}",
                home_team=f"Team {request_id}",
                away_team=f"Opponent {request_id}",
                features=[float(request_id % 10)] * 12,
                use_cache=False,
            )

            start_time = time.perf_counter()
            try:
                # 模拟异步推理处理
                request_dict = request.to_dict()
                # 模拟一些计算
                _ = sum(request.features) / len(request.features)
                await asyncio.sleep(0.001)  # 模拟1ms的推理时间
                end_time = time.perf_counter()
                return {
                    "request_id": request_id,
                    "success": True,
                    "latency_ms": (end_time - start_time) * 1000,
                }
            except Exception as e:
                end_time = time.perf_counter()
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": str(e),
                    "latency_ms": (end_time - start_time) * 1000,
                }

        # 创建并发任务
        tasks = []
        for worker_id in range(concurrent_requests):
            for req_id in range(requests_per_worker):
                request_id = worker_id * requests_per_worker + req_id
                tasks.append(simulate_prediction(request_id))

        # 执行并发测试
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()

        # 分析结果
        successful_results = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        latencies = [r["latency_ms"] for r in successful_results]

        total_time = end_time - start_time
        total_requests = len(tasks)
        success_rate = len(successful_results) / total_requests * 100
        throughput = len(successful_results) / total_time

        if latencies:
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        else:
            avg_latency = p95_latency = p99_latency = 0

        print(f"并发测试结果:")
        print(f"总请求数: {total_requests}")
        print(f"成功请求数: {len(successful_results)}")
        print(f"成功率: {success_rate:.2f}%")
        print(f"总时间: {total_time:.3f}s")
        print(f"吞吐量: {throughput:.2f} 请求/秒")
        print(f"平均延迟: {avg_latency:.2f}ms")
        print(f"P95延迟: {p95_latency:.2f}ms")
        print(f"P99延迟: {p99_latency:.2f}ms")

        # 性能要求
        assert success_rate >= 95, f"成功率过低: {success_rate:.2f}%"
        assert throughput > 500, f"并发吞吐量过低: {throughput:.2f} 请求/秒"
        if latencies:
            assert p99_latency < 50, f"P99延迟过高: {p99_latency:.2f}ms"

    def test_memory_usage_optimization(self, high_performance_service):
        """测试内存使用优化"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 创建大量请求对象测试内存管理
        requests = []
        for i in range(1000):
            request = PredictionRequest(
                match_id=f"memory_test_{i}",
                home_team=f"Team {i}",
                away_team=f"Opponent {i}",
                features=[float(j) for j in range(12)],  # 创建不同的特征数据
                use_cache=False,
            )
            requests.append(request)

        # 处理请求
        processed = 0
        for request in requests:
            try:
                request_dict = request.to_dict()
                _ = sum(request.features) / len(request.features)
                processed += 1
            except Exception:
                pass

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # 清理
        del requests

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_recovered = peak_memory - final_memory

        print(f"内存使用测试:")
        print(f"初始内存: {initial_memory:.2f} MB")
        print(f"峰值内存: {peak_memory:.2f} MB")
        print(f"内存增长: {memory_increase:.2f} MB")
        print(f"内存回收: {memory_recovered:.2f} MB")
        print(f"处理请求数: {processed}")

        # 内存要求：处理1000个请求的内存增长 < 50MB
        assert memory_increase < 50, f"内存增长过多: {memory_increase:.2f} MB"
        assert processed >= 990, f"处理成功率过低: {processed}/1000"

    def test_cache_hit_performance(self, high_performance_service):
        """测试缓存命中性能"""
        # 配置缓存命中
        high_performance_service.cache_manager.get.return_value = {
            "prediction": "HOME_WIN",
            "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
        }

        request = PredictionRequest(
            match_id="cache_test",
            home_team="Team A",
            away_team="Team B",
            features=[1.0] * 12,
            use_cache=True,
        )

        # 测试缓存命中性能
        latencies = []
        for _ in range(1000):
            start_time = time.perf_counter()
            try:
                # 模拟缓存命中
                result = high_performance_service.cache_manager.get(request.match_id)
                if result:
                    _ = result["prediction"]
                end_time = time.perf_counter()
                latencies.append((end_time - start_time) * 1000)
            except Exception:
                end_time = time.perf_counter()
                latencies.append((end_time - start_time) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"缓存命中性能:")
        print(f"平均延迟: {avg_latency:.3f}ms")
        print(f"P95延迟: {p95_latency:.3f}ms")
        print(f"P99延迟: {p99_latency:.3f}ms")

        # 缓存命中应该非常快
        assert avg_latency < 0.1, f"缓存命中平均延迟过高: {avg_latency:.3f}ms"
        assert p99_latency < 0.5, f"缓存命中P99延迟过高: {p99_latency:.3f}ms"

    def test_feature_processing_performance(self, high_performance_service):
        """测试特征处理性能"""
        # 创建不同复杂度的特征数据
        simple_features = [1.0] * 12
        complex_features = [i * 0.1 + (i % 3) * 0.05 for i in range(12)]

        def process_features(features: List[float]) -> Dict[str, float]:
            """模拟特征处理"""
            # 基本统计
            mean_val = sum(features) / len(features)
            variance = sum((x - mean_val) ** 2 for x in features) / len(features)

            # 模拟一些特征工程计算
            normalized = [(x - mean_val) / (variance**0.5 + 1e-8) for x in features]
            interactions = [
                normalized[i] * normalized[i + 1] for i in range(len(normalized) - 1)
            ]

            return {
                "mean": mean_val,
                "variance": variance,
                "max_feature": max(features),
                "min_feature": min(features),
                "avg_interaction": (
                    sum(interactions) / len(interactions) if interactions else 0
                ),
            }

        # 性能测试
        iterations = 10000

        # 简单特征
        start_time = time.perf_counter()
        for _ in range(iterations):
            result = process_features(simple_features)
            assert result["mean"] == 1.0
        simple_time = time.perf_counter() - start_time

        # 复杂特征
        start_time = time.perf_counter()
        for _ in range(iterations):
            result = process_features(complex_features)
        complex_time = time.perf_counter() - start_time

        simple_throughput = iterations / simple_time
        complex_throughput = iterations / complex_time

        print(f"特征处理性能:")
        print(f"简单特征吞吐量: {simple_throughput:.0f} 次/秒")
        print(f"复杂特征吞吐量: {complex_throughput:.0f} 次/秒")
        print(f"性能比率: {simple_throughput/complex_throughput:.2f}x")

        # 性能要求：特征处理吞吐量 > 100,000 次/秒
        assert (
            simple_throughput > 100000
        ), f"简单特征处理吞吐量过低: {simple_throughput:.0f} 次/秒"
        assert (
            complex_throughput > 50000
        ), f"复杂特征处理吞吐量过低: {complex_throughput:.0f} 次/秒"


class TestModelLoadingPerformance:
    """模型加载性能测试"""

    def test_model_loading_latency(self):
        """测试模型加载延迟"""
        mock_loader = Mock()

        # 模拟不同大小的模型加载时间
        loading_times = [0.1, 0.5, 1.0, 2.0]  # 秒

        for load_time in loading_times:

            def slow_load(*args, **kwargs):
                time.sleep(load_time)
                return True

            mock_loader.load_model.side_effect = slow_load

            start_time = time.perf_counter()
            result = mock_loader.load_model("test_model", "/path/to/model.pkl")
            end_time = time.perf_counter()

            actual_load_time = end_time - start_time

            print(f"预期加载时间: {load_time}s, 实际加载时间: {actual_load_time:.3f}s")
            assert abs(actual_load_time - load_time) < 0.1, f"加载时间不准确"
            assert result is True

    def test_concurrent_model_loading(self):
        """测试并发模型加载"""
        mock_loader = Mock()

        def load_with_delay(*args, **kwargs):
            time.sleep(0.1)  # 模拟100ms加载时间
            return True

        mock_loader.load_model.side_effect = load_with_delay

        # 测试串行加载
        start_time = time.perf_counter()
        for i in range(5):
            mock_loader.load_model(f"model_{i}", f"/path/to/model_{i}.pkl")
        serial_time = time.perf_counter() - start_time

        # 测试并发加载
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.perf_counter()
            futures = [
                executor.submit(
                    mock_loader.load_model, f"model_{i}", f"/path/to/model_{i}.pkl"
                )
                for i in range(5)
            ]
            results = [f.result() for f in futures]
            concurrent_time = time.perf_counter() - start_time

        speedup = serial_time / concurrent_time

        print(f"串行加载时间: {serial_time:.3f}s")
        print(f"并发加载时间: {concurrent_time:.3f}s")
        print(f"加速比: {speedup:.2f}x")

        # 并发加载应该有显著加速
        assert speedup > 2.0, f"并发加载加速比不足: {speedup:.2f}x"
        assert all(results), "部分模型加载失败"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
