import asyncio
import os
import time
import pytest
import psutil
from unittest.mock import AsyncMock
from src.core.prediction_engine import PredictionEngine
from src.models.prediction_service import PredictionResult

"""
预测性能基准测试
Performance Benchmarks for Prediction

测试预测引擎的性能指标。
Test performance metrics of prediction engine.
"""


@pytest.mark.performance
class TestPredictionBenchmarks:
    """预测性能基准测试"""

    @pytest.mark.asyncio
    async def test_single_prediction_latency(self, prediction_engine):
        """测试单次预测延迟"""
        match_id = 12345

        # 模拟快速预测
        prediction_engine.prediction_service.predict_match = AsyncMock(
            return_value=PredictionResult(
                match_id=match_id,
                model_version="1.0.0",
                predicted_result="home",
                confidence_score=0.65,
            )
        )
        prediction_engine._get_match_info = AsyncMock(return_value={"id": match_id})

        # 测试多次预测延迟
        latencies = []
        for _ in range(100):
            start_time = time.perf_counter()
            await prediction_engine.predict_match(match_id)
            latency = (time.perf_counter() - start_time) * 1000  # ms
            latencies.append(latency)

        # 计算统计
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[94]  # 95th percentile
        p99_latency = sorted(latencies)[98]  # 99th percentile

        print("\n单次预测延迟统计:")
        print(f"  平均: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")

        # 性能断言
        assert avg_latency < 100, f"平均延迟过高: {avg_latency:.2f}ms"
        assert p95_latency < 200, f"P95延迟过高: {p95_latency:.2f}ms"
        assert p99_latency < 500, f"P99延迟过高: {p99_latency:.2f}ms"

    @pytest.mark.asyncio
    async def test_batch_prediction_throughput(self, prediction_engine):
        """测试批量预测吞吐量"""
        # 准备测试数据
        batch_sizes = [10, 50, 100, 500, 1000]
        throughputs = []

        for batch_size in batch_sizes:
            match_ids = list(range(10000, 10000 + batch_size))

            # 模拟预测
            prediction_engine.predict_match = AsyncMock(
                side_effect=lambda mid: {
                    "match_id": mid,
                    "prediction": "home" if mid % 2 == 0 else "away",
                }
            )

            # 执行批量预测
            start_time = time.perf_counter()
            results = await prediction_engine.batch_predict(match_ids)
            duration = time.perf_counter() - start_time

            # 计算吞吐量
            throughput = len(results) / duration
            throughputs.append((batch_size, throughput))

            print(f"\n批量大小: {batch_size}")
            print(f"  吞吐量: {throughput:.2f} predictions/sec")
            print(f"  平均延迟: {duration / batch_size * 1000:.2f}ms/prediction")

            # 性能断言
            assert throughput > 100, f"吞吐量过低: {throughput:.2f} predictions/sec"

        # 分析吞吐量趋势
        print("\n吞吐量趋势:")
        for batch_size, throughput in throughputs:
            print(f"  {batch_size:4d}: {throughput:8.2f} predictions/sec")

    @pytest.mark.asyncio
    async def test_concurrent_prediction_scalability(self, prediction_engine):
        """测试并发预测可扩展性"""
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}

        for concurrency in concurrency_levels:
            # 模拟预测（带少量延迟）
            async def mock_predict(mid):
                await asyncio.sleep(0.01)  # 10ms模拟处理时间
                return {"match_id": mid, "prediction": "home"}

            prediction_engine.predict_match = AsyncMock(side_effect=mock_predict)

            # 准备任务
            match_ids = list(range(20000, 20100))
            semaphore = asyncio.Semaphore(concurrency)

            async def predict_with_semaphore(mid):
                async with semaphore:
                    return await prediction_engine.predict_match(mid)

            # 执行并发预测
            start_time = time.perf_counter()
            tasks = [predict_with_semaphore(mid) for mid in match_ids]
            predictions = await asyncio.gather(*tasks)
            duration = time.perf_counter() - start_time

            # 计算指标
            throughput = len(predictions) / duration
            efficiency = throughput / concurrency if concurrency > 0 else 0
            results[concurrency] = {
                "throughput": throughput,
                "duration": duration,
                "efficiency": efficiency,
            }

            print(f"\n并发级别: {concurrency}")
            print(f"  吞吐量: {throughput:.2f} predictions/sec")
            print(f"  效率: {efficiency:.2f} predictions/sec per worker")
            print(f"  总时间: {duration:.2f}s")

        # 分析可扩展性
        print("\n可扩展性分析:")
        max_throughput = max(r["throughput"] for r in results.values())
        optimal_concurrency = max(
            results.keys(), key=lambda k: results[k]["efficiency"]
        )
        print(f"  最大吞吐量: {max_throughput:.2f} predictions/sec")
        print(f"  最优并发级别: {optimal_concurrency}")

    @pytest.mark.asyncio
    async def test_cache_performance(self, prediction_engine):
        """测试缓存性能"""
        match_id = 12345
        prediction_data = {
            "match_id": match_id,
            "prediction": "home",
            "confidence": 0.65,
        }

        # 测试缓存未命中
        prediction_engine.prediction_service.predict_match = AsyncMock(
            return_value=prediction_data
        )
        prediction_engine._get_match_info = AsyncMock(return_value={"id": match_id})

        # 第一次预测（缓存未命中）
        start_time = time.perf_counter()
        await prediction_engine.predict_match(match_id)
        cache_miss_time = (time.perf_counter() - start_time) * 1000

        # 第二次预测（缓存命中）
        start_time = time.perf_counter()
        await prediction_engine.predict_match(match_id)
        cache_hit_time = (time.perf_counter() - start_time) * 1000

        # 计算缓存效果
        speedup = (
            cache_miss_time / cache_hit_time if cache_hit_time > 0 else float("inf")
        )

        print("\n缓存性能:")
        print(f"  缓存未命中: {cache_miss_time:.2f}ms")
        print(f"  缓存命中: {cache_hit_time:.2f}ms")
        print(f"  加速比: {speedup:.2f}x")

        # 性能断言
        assert speedup > 10, f"缓存效果不明显: {speedup:.2f}x"
        assert cache_hit_time < 1, f"缓存访问过慢: {cache_hit_time:.2f}ms"

    @pytest.mark.asyncio
    async def test_memory_usage(self, prediction_engine):
        """测试内存使用"""

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 预测大量比赛
        for batch in range(10):
            match_ids = list(range(30000 + batch * 100, 30000 + (batch + 1) * 100))

            prediction_engine.predict_match = AsyncMock(
                side_effect=lambda mid: {
                    "match_id": mid,
                    "prediction": "home",
                    "features": {f"feature_{i}": i for i in range(100)},  # 大量特征数据
                }
            )

            await prediction_engine.batch_predict(match_ids)

            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory

            print(f"\n批次 {batch + 1}:")
            print(f"  当前内存: {current_memory:.1f}MB")
            print(f"  内存增长: {memory_increase:.1f}MB")

        # 最终内存检查
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory

        print("\n内存使用总结:")
        print(f"  初始内存: {initial_memory:.1f}MB")
        print(f"  最终内存: {final_memory:.1f}MB")
        print(f"  总增长: {total_increase:.1f}MB")

        # 内存断言（1000个预测不应超过100MB增长）
        assert total_increase < 100, f"内存使用过多: {total_increase:.1f}MB"

    @pytest.mark.asyncio
    async def test_prediction_accuracy_under_load(self, prediction_engine):
        """测试负载下的预测准确性"""
        # 准备测试数据
        total_predictions = 0

        # 模拟预测服务（有时会失败）
        async def mock_predict_with_error(mid):
            if mid % 20 == 0:  # 5%失败率
                raise Exception("Random error")
            return PredictionResult(
                match_id=mid,
                model_version="1.0.0",
                predicted_result="home" if mid % 3 == 0 else "away",
                confidence_score=0.6 + (mid % 5) * 0.05,
            )

        prediction_engine.prediction_service.predict_match = AsyncMock(
            side_effect=mock_predict_with_error
        )
        prediction_engine._get_match_info = AsyncMock(return_value={"id": 1})

        # 执行大量预测
        match_ids = list(range(40000, 40500))
        results = []

        for match_id in match_ids:
            try:
                _result = await prediction_engine.predict_match(match_id)
                results.append(result)
                total_predictions += 1
            except Exception:
                continue

        # 计算成功率
        success_rate = len(results) / len(match_ids)
        avg_confidence = (
            sum(r.get("confidence", 0) for r in results) / len(results)
            if results
            else 0
        )

        print("\n负载测试结果:")
        print(f"  成功率: {success_rate:.2%}")
        print(f"  平均置信度: {avg_confidence:.3f}")
        print(f"  成功预测数: {len(results)}")
        print(f"  失败预测数: {len(match_ids) - len(results)}")

        # 性能断言
        assert success_rate > 0.9, f"成功率过低: {success_rate:.2%}"
        assert avg_confidence > 0.5, f"平均置信度过低: {avg_confidence:.3f}"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_performance(self, prediction_engine):
        """测试持续性能"""
        duration_minutes = 1  # 运行1分钟
        target_rate = 50  # 目标50 predictions/sec

        prediction_engine.predict_match = AsyncMock(
            side_effect=lambda mid: {
                "match_id": mid,
                "prediction": "home",
            }
        )

        start_time = time.time()
        end_time = start_time + duration_minutes * 60
        predictions = []
        errors = 0

        match_id = 50000
        while time.time() < end_time:
            try:
                _result = await prediction_engine.predict_match(match_id)
                predictions.append(result)
                match_id += 1

                # 控制速率
                await asyncio.sleep(1 / target_rate)
            except Exception:
                errors += 1
                await asyncio.sleep(0.1)  # 错误后短暂等待

        actual_duration = time.time() - start_time
        actual_rate = len(predictions) / actual_duration

        print(f"\n持续性能测试 ({duration_minutes}分钟):")
        print(f"  实际速率: {actual_rate:.2f} predictions/sec")
        print(f"  目标速率: {target_rate} predictions/sec")
        print(f"  总预测数: {len(predictions)}")
        print(f"  错误数: {errors}")
        print(f"  成功率: {len(predictions) / (len(predictions) + errors):.2%}")

        # 性能断言
        assert actual_rate > target_rate * 0.9, (
            f"持续性能不足: {actual_rate:.2f} < {target_rate * 0.9}"
        )
        assert errors / (len(predictions) + errors) < 0.05, (
            f"错误率过高: {errors / (len(predictions) + errors):.2%}"
        )


@pytest.fixture
async def prediction_engine():
    """创建预测引擎"""
    engine = PredictionEngine()
    yield engine
    await engine.close()
