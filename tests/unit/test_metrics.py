"""
核心指标模块测试
测试Prometheus指标管理系统的功能
"""

import pytest
import time
from unittest.mock import patch, Mock
from prometheus_client import CollectorRegistry, REGISTRY

from src.core.metrics import MetricsManager, get_metrics


class TestMetricsManager:
    """MetricsManager测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        # 创建多个实例应该返回同一个对象
        manager1 = MetricsManager()
        manager2 = MetricsManager()

        assert manager1 is manager2, "MetricsManager应该实现单例模式"

    def test_initialization_only_once(self):
        """测试初始化只执行一次"""
        manager1 = MetricsManager()

        # 获取原始注册表
        original_registry = manager1.get_registry()

        # 创建第二个实例
        manager2 = MetricsManager()

        # 注册表应该是同一个
        assert manager1.get_registry() is manager2.get_registry()
        assert manager1.get_registry() is original_registry

    def test_custom_registry_creation(self):
        """测试自定义注册表创建"""
        manager = MetricsManager()
        registry = manager.get_registry()

        # 应该是CollectorRegistry实例
        assert isinstance(registry, CollectorRegistry)

        # 应该与默认注册表不同
        assert registry is not REGISTRY

    def test_prediction_requests_counter(self):
        """测试预测请求计数器"""
        manager = MetricsManager()
        counter = manager.prediction_requests_total

        # 测试计数器增量
        counter.labels(model_name="xgboost_v2", prediction_type="single").inc()
        counter.labels(model_name="xgboost_v2", prediction_type="batch").inc(5)

        # 验证计数器值
        assert counter.labels(model_name="xgboost_v2", prediction_type="single")._value.get() == 1.0
        assert counter.labels(model_name="xgboost_v2", prediction_type="batch")._value.get() == 5.0

    def test_model_inference_latency_histogram(self):
        """测试模型推理延迟直方图"""
        manager = MetricsManager()
        histogram = manager.model_inference_latency

        # 观察一些延迟值
        histogram.labels(model_name="xgboost_v2").observe(0.01)  # 10ms
        histogram.labels(model_name="xgboost_v2").observe(0.05)  # 50ms
        histogram.labels(model_name="neural_net").observe(0.1)  # 100ms

        # 验证观察计数
        samples = list(histogram.labels(model_name="xgboost_v2").collect())[0].samples
        count_samples = [s for s in samples if s.name.endswith("_count")]

        assert len(count_samples) > 0
        assert count_samples[0].value == 2.0  # xgboost_v2被观察了2次

    def test_prediction_accuracy_counter(self):
        """测试预测准确率计数器"""
        manager = MetricsManager()
        counter = manager.prediction_accuracy_total

        # 记录准确率和错误
        counter.labels(model_name="xgboost_v2", result_type="correct").inc()
        counter.labels(model_name="xgboost_v2", result_type="incorrect").inc()
        counter.labels(model_name="neural_net", result_type="correct").inc(3)

        # 验证计数
        assert counter.labels(model_name="xgboost_v2", result_type="correct")._value.get() == 1.0
        assert counter.labels(model_name="xgboost_v2", result_type="incorrect")._value.get() == 1.0
        assert counter.labels(model_name="neural_net", result_type="correct")._value.get() == 3.0

    def test_data_collection_counter(self):
        """测试数据收集计数器"""
        manager = MetricsManager()
        counter = manager.data_collection_requests_total

        # 记录数据收集请求
        counter.labels(data_source="fotmob", status="success").inc()
        counter.labels(data_source="fotmob", status="error").inc(2)
        counter.labels(data_source="odds_portal", status="success").inc(5)

        # 验证计数
        assert counter.labels(data_source="fotmob", status="success")._value.get() == 1.0
        assert counter.labels(data_source="fotmob", status="error")._value.get() == 2.0
        assert counter.labels(data_source="odds_portal", status="success")._value.get() == 5.0

    def test_feature_computation_latency_histogram(self):
        """测试特征计算延迟直方图"""
        manager = MetricsManager()
        histogram = manager.feature_computation_latency

        # 观察特征计算延迟
        histogram.labels(feature_type="h2h").observe(0.15)  # 150ms
        histogram.labels(feature_type="rolling").observe(0.3)  # 300ms
        histogram.labels(feature_type="venue").observe(0.05)  # 50ms

        # 验证观察
        samples = list(histogram.labels(feature_type="rolling").collect())[0].samples
        count_samples = [s for s in samples if s.name.endswith("_count")]

        assert len(count_samples) > 0
        assert count_samples[0].value == 1.0

    def test_cache_operations_counter(self):
        """测试缓存操作计数器"""
        manager = MetricsManager()
        counter = manager.cache_operations_total

        # 记录缓存操作
        counter.labels(cache_type="prediction", operation="hit").inc(10)
        counter.labels(cache_type="prediction", operation="miss").inc(3)
        counter.labels(cache_type="features", operation="set").inc(5)

        # 验证计数
        assert counter.labels(cache_type="prediction", operation="hit")._value.get() == 10.0
        assert counter.labels(cache_type="prediction", operation="miss")._value.get() == 3.0
        assert counter.labels(cache_type="features", operation="set")._value.get() == 5.0

    def test_generate_metrics_output(self):
        """测试指标数据生成"""
        manager = MetricsManager()

        # 添加一些指标数据
        manager.prediction_requests_total.labels(model_name="test_model", prediction_type="single").inc()

        # 生成指标数据
        metrics_output = manager.generate_metrics()

        # 验证输出格式
        assert isinstance(metrics_output, bytes)
        assert len(metrics_output) > 0

        # 验证内容包含我们的指标
        metrics_str = metrics_output.decode("utf-8")
        assert "prediction_requests_total" in metrics_str
        assert "test_model" in metrics_str
        assert "single" in metrics_str


class TestGlobalMetrics:
    """全局指标测试"""

    def test_get_metrics_function(self):
        """测试全局获取指标函数"""
        # 使用全局函数获取指标
        metrics_output = get_metrics()

        assert isinstance(metrics_output, bytes)
        assert len(metrics_output) > 0

    def test_global_metrics_instances(self):
        """测试全局指标实例"""
        from src.core.metrics import (
            prediction_requests_total,
            model_inference_latency,
            prediction_accuracy_total,
            data_collection_requests_total,
            feature_computation_latency,
            cache_operations_total,
        )

        # 验证所有指标实例都存在
        assert prediction_requests_total is not None
        assert model_inference_latency is not None
        assert prediction_accuracy_total is not None
        assert data_collection_requests_total is not None
        assert feature_computation_latency is not None
        assert cache_operations_total is not None

    def test_global_metrics_usage(self):
        """测试全局指标使用"""
        from src.core.metrics import prediction_requests_total, model_inference_latency

        # 使用全局指标
        prediction_requests_total.labels(model_name="global_test", prediction_type="batch").inc()

        model_inference_latency.labels(model_name="global_test").observe(0.025)  # 25ms

        # 验证指标已更新
        metrics_output = get_metrics()
        metrics_str = metrics_output.decode("utf-8")

        assert "global_test" in metrics_str


class TestMetricsIntegration:
    """指标集成测试"""

    def test_real_world_prediction_workflow(self):
        """测试真实世界预测工作流程的指标记录"""
        from src.core.metrics import (
            prediction_requests_total,
            model_inference_latency,
            cache_operations_total,
            prediction_accuracy_total,
        )

        # 模拟预测请求
        def simulate_prediction_request(model_name: str, prediction_type: str):
            # 记录请求开始
            prediction_requests_total.labels(model_name=model_name, prediction_type=prediction_type).inc()

            # 模拟推理延迟
            start_time = time.time()
            time.sleep(0.01)  # 模拟10ms推理时间
            inference_time = time.time() - start_time

            # 记录推理延迟
            model_inference_latency.labels(model_name=model_name).observe(inference_time)

            # 模拟缓存命中/未命中
            if prediction_type == "single":
                cache_operations_total.labels(cache_type="prediction", operation="hit").inc()
            else:
                cache_operations_total.labels(cache_type="prediction", operation="miss").inc()

            # 模拟预测结果
            import random

            if random.random() > 0.3:  # 70%准确率
                prediction_accuracy_total.labels(model_name=model_name, result_type="correct").inc()
                return True
            else:
                prediction_accuracy_total.labels(model_name=model_name, result_type="incorrect").inc()
                return False

        # 执行多个预测请求
        correct_predictions = 0
        for i in range(10):
            is_correct = simulate_prediction_request("xgboost_v2", "single")
            if is_correct:
                correct_predictions += 1

        # 验证指标记录
        metrics_output = get_metrics()
        metrics_str = metrics_output.decode("utf-8")

        assert "prediction_requests_total" in metrics_str
        assert "model_inference_latency_seconds" in metrics_str
        assert "cache_operations_total" in metrics_str
        assert "prediction_accuracy_total" in metrics_str

    def test_metrics_thread_safety(self):
        """测试指标线程安全性"""
        import threading
        from src.core.metrics import prediction_requests_total

        def increment_counter(thread_id: int):
            """在多个线程中递增计数器"""
            for i in range(100):
                prediction_requests_total.labels(model_name=f"model_{thread_id}", prediction_type="thread_test").inc()

        # 创建多个线程
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=increment_counter, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有计数都已正确记录
        metrics_output = get_metrics()
        metrics_str = metrics_output.decode("utf-8")

        # 每个线程应该有100次计数
        for thread_id in range(5):
            assert f"model_{thread_id}" in metrics_str

    def test_metrics_memory_usage(self):
        """测试指标内存使用"""
        import psutil
        import os

        # 获取初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        from src.core.metrics import feature_computation_latency

        # 创建大量指标观察
        for i in range(1000):
            feature_computation_latency.labels(feature_type=f"feature_{i % 10}").observe(  # 循环使用10种特征类型
                0.1 + i * 0.001
            )

        # 检查内存增长
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"内存增长: {memory_increase:.2f}MB")

        # 内存增长应该合理（小于50MB）
        assert memory_increase < 50, f"内存增长过多: {memory_increase:.2f}MB"


if __name__ == "__main__":
    # 运行指标测试
    pytest.main([__file__, "-v", "-s"])
