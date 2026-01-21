"""
推理性能测试
测试ML推理组件的性能指标和响应时间
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from src.ml.inference.cache_manager import PredictionCache
from src.ml.inference.model_loader import ModelLoader
from src.ml.inference.predictor import MatchPredictor, PredictionError


class TestMatchPredictorPerformance:
    """MatchPredictor性能测试"""

    @pytest.fixture
    def mock_predictor(self):
        """创建Mock预测器用于性能测试"""
        # Mock模型
        mock_model = Mock()
        mock_model.predict.return_value = [1]  # Draw
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
        mock_model.n_features_in_ = 3
        mock_model.classes_ = [0, 1, 2]

        # Mock加载器
        mock_loader = Mock()
        mock_loader.get_model.return_value = mock_model

        # Mock元数据
        mock_metadata = Mock()
        mock_metadata.feature_names = ["feature1", "feature2", "feature3"]
        mock_loader.get_model_metadata.return_value = mock_metadata

        # Mock缓存
        mock_cache = Mock()
        mock_cache.get.return_value = None  # 缓存未命中

        predictor = MatchPredictor(
            model_loader=mock_loader,
            cache_manager=mock_cache,
            default_model_name="test_model",
        )

        return predictor

    def test_single_prediction_latency(self, mock_predictor):
        """测试单次预测延迟"""
        features = [1.0, 2.0, 3.0]

        # 测量多次预测的延迟
        latencies = []
        for _ in range(10):
            start_time = time.perf_counter()
            result = mock_predictor.predict(features)
            end_time = time.perf_counter()

            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            # 验证结果正确性
            assert result is not None
            assert "predicted_class" in result

        # 性能断言
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"平均延迟: {avg_latency:.2f}ms")
        print(f"最大延迟: {max_latency:.2f}ms")

        # 单次预测应在10ms内完成
        assert avg_latency < 10.0, f"平均预测延迟过高: {avg_latency:.2f}ms"
        assert max_latency < 50.0, f"最大预测延迟过高: {max_latency:.2f}ms"

    def test_batch_prediction_throughput(self, mock_predictor):
        """测试批量预测吞吐量"""
        batch_size = 100
        features = [1.0, 2.0, 3.0]

        start_time = time.perf_counter()

        # 执行批量预测
        results = []
        for _ in range(batch_size):
            result = mock_predictor.predict(features)
            results.append(result)

        end_time = time.perf_counter()
        duration = end_time - start_time

        # 计算吞吐量
        throughput = batch_size / duration  # 预测/秒

        print(f"批量预测吞吐量: {throughput:.1f} 预测/秒")
        print(f"总耗时: {duration:.2f}秒")

        # 验证结果
        assert len(results) == batch_size
        for result in results:
            assert result is not None

        # 吞吐量应至少为100预测/秒
        assert throughput >= 100, f"吞吐量过低: {throughput:.1f} 预测/秒"

    def test_concurrent_predictions(self, mock_predictor):
        """测试并发预测性能"""

        async def async_predict(features: List[float]) -> Dict[str, Any]:
            """异步包装预测函数"""
            return mock_predictor.predict(features)

        async def concurrent_test():
            """并发测试"""
            features = [1.0, 2.0, 3.0]
            concurrent_count = 10

            start_time = time.perf_counter()

            # 创建并发任务
            tasks = [async_predict(features) for _ in range(concurrent_count)]

            # 等待所有任务完成
            results = await asyncio.gather(*tasks)

            end_time = time.perf_counter()
            duration = end_time - start_time

            # 验证结果
            assert len(results) == concurrent_count
            for result in results:
                assert result is not None

            print(f"并发预测耗时: {duration:.3f}秒")
            print(f"并发数量: {concurrent_count}")

            return duration

        # 运行并发测试
        duration = asyncio.run(concurrent_test())

        # 并发预测应该比串行快
        assert duration < 1.0, f"并发预测耗时过长: {duration:.3f}秒"

    def test_memory_usage_stability(self, mock_predictor):
        """测试内存使用稳定性"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 执行大量预测
        for i in range(1000):
            features = [1.0, i % 10, (i + 1) % 10]
            mock_predictor.predict(features)

            # 每100次检查一次内存
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory

                print(f"第{i}次预测，内存增长: {memory_increase:.2f}MB")

                # 内存增长不应超过50MB
                assert memory_increase < 50, f"内存增长过多: {memory_increase:.2f}MB"

        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory

        print(f"总内存增长: {total_memory_increase:.2f}MB")

        # 总内存增长应控制在合理范围
        assert total_memory_increase < 100, f"总内存增长过多: {total_memory_increase:.2f}MB"


class TestCachePerformance:
    """缓存性能测试"""

    def test_cache_hit_performance(self):
        """测试缓存命中性能"""
        cache = PredictionCache(default_ttl=3600)
        features = {"feature1": 1.0, "feature2": 2.0}
        result = {"prediction": 0.8}

        # 预填充缓存
        cache.set(features, "test_model", result)

        # 测量缓存读取性能
        cache_times = []
        for _ in range(1000):
            start_time = time.perf_counter()
            cached_result = cache.get(features, "test_model")
            end_time = time.perf_counter()

            cache_times.append((end_time - start_time) * 1000000)  # 微秒

        avg_cache_time = sum(cache_times) / len(cache_times)

        print(f"平均缓存访问时间: {avg_cache_time:.2f}μs")
        print(f"最大缓存访问时间: {max(cache_times):.2f}μs")

        # 缓存访问应该很快
        assert avg_cache_time < 100, f"缓存访问过慢: {avg_cache_time:.2f}μs"
        assert max(cache_times) < 1000, f"缓存访问最大时间过长: {max(cache_times):.2f}μs"

    def test_cache_write_performance(self):
        """测试缓存写入性能"""
        cache = PredictionCache(default_ttl=3600)

        write_times = []
        for i in range(1000):
            features = {"feature1": i, "feature2": i + 1}
            result = {"prediction": 0.8 + i * 0.001}

            start_time = time.perf_counter()
            cache.set(features, "test_model", result)
            end_time = time.perf_counter()

            write_times.append((end_time - start_time) * 1000000)  # 微秒

        avg_write_time = sum(write_times) / len(write_times)

        print(f"平均缓存写入时间: {avg_write_time:.2f}μs")
        print(f"最大缓存写入时间: {max(write_times):.2f}μs")

        # 缓存写入应该很快
        assert avg_write_time < 200, f"缓存写入过慢: {avg_write_time:.2f}μs"


class TestModelLoadingPerformance:
    """模型加载性能测试"""

    def test_model_loading_time(self):
        """测试模型加载时间"""
        with patch("src.ml.inference.model_loader.joblib.load") as mock_joblib:
            # Mock模型加载耗时
            def mock_load_delay(*args, **kwargs):
                time.sleep(0.01)  # 模拟10ms加载时间
                mock_model = Mock()
                mock_model.n_features_in_ = 10
                mock_model.classes_ = [0, 1, 2]
                return mock_model

            mock_joblib.side_effect = mock_load_delay

            with patch("os.path.exists", return_value=True):
                loader = ModelLoader("/mock/path")

                start_time = time.perf_counter()
                model = loader.load_model("test", "/mock/model.pkl")
                end_time = time.perf_counter()

                load_time = (end_time - start_time) * 1000

                print(f"模型加载时间: {load_time:.2f}ms")

                # 模型加载应该在合理时间内完成
                assert load_time < 100, f"模型加载过慢: {load_time:.2f}ms"
                assert model is not None


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s"])
