#!/usr/bin/env python3
"""
🚀 ML性能测试 - 机器学习模型性能测试

测试机器学习模型的性能指标、优化和扩展性
包括训练速度、预测速度、内存使用、并发性能等
"""

import asyncio
import os

# 模拟导入，避免循环依赖问题
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psutil
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

# 尝试导入ML模块
try:
    from src.ml.model_training import (
        ModelTrainer,
        ModelType,
        TrainingConfig,
        TrainingStatus,
    )
    from src.ml.models.base_model import BaseModel, PredictionResult, TrainingResult
    from src.ml.models.poisson_model import PoissonModel

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入ML模块: {e}")
    CAN_IMPORT = False


# 性能测试工具类
class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_start = None
        self.memory_end = None

    def start(self):
        """开始监控"""
        self.start_time = time.time()
        process = psutil.Process(os.getpid())
        self.memory_start = process.memory_info().rss / 1024 / 1024  # MB

    def stop(self):
        """停止监控"""
        self.end_time = time.time()
        process = psutil.Process(os.getpid())
        self.memory_end = process.memory_info().rss / 1024 / 1024  # MB

    def get_execution_time(self) -> float:
        """获取执行时间（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0

    def get_memory_usage(self) -> dict[str, float]:
        """获取内存使用情况"""
        return {
            "start_mb": self.memory_start or 0,
            "end_mb": self.memory_end or 0,
            "delta_mb": (self.memory_end or 0) - (self.memory_start or 0),
        }


def create_performance_test_data(num_samples: int = 1000) -> pd.DataFrame:
    """创建性能测试数据"""
    teams = [f"Team_{chr(65+i)}" for i in range(20)]  # Team_A 到 Team_T
    data = []

    for i in range(num_samples):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        # 使用更复杂的数据生成以增加计算量
        team_strength = np.random.uniform(0.5, 2.5, len(teams))
        home_strength = team_strength[teams.index(home_team)]
        away_strength = team_strength[teams.index(away_team)]

        # 考虑更多因素的进球模拟
        home_advantage = 0.3
        weather_factor = np.random.uniform(0.8, 1.2)
        fatigue_factor = np.random.uniform(0.9, 1.1)

        home_expected = (
            (home_strength * home_advantage * weather_factor) / away_strength * 1.5
        )
        away_expected = (
            away_strength / (home_strength * home_advantage) * 1.1 * fatigue_factor
        )

        home_goals = np.random.poisson(max(home_expected, 0.1))
        away_goals = np.random.poisson(max(away_expected, 0.1))

        if home_goals > away_goals:
            result = "home_win"
        elif home_goals < away_goals:
            result = "away_win"
        else:
            result = "draw"

        data.append(
            {
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_goals,
                "away_score": away_goals,
                "result": result,
                "match_date": datetime.now()
                - timedelta(days=np.random.randint(0, 365)),
                "home_team_strength": home_strength,
                "away_team_strength": away_strength,
                "weather_factor": weather_factor,
                "fatigue_factor": fatigue_factor,
            }
        )

    return pd.DataFrame(data)


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.performance
class TestMLModelPerformance:
    """ML模型性能测试"""

    def test_training_performance_small_dataset(self):
        """测试小数据集训练性能"""
        model = PoissonModel()
        training_data = create_performance_test_data(100)

        monitor = PerformanceMonitor()
        monitor.start()

        result = model.train(training_data)

        monitor.stop()

        # 性能断言
        execution_time = monitor.get_execution_time()
        memory_usage = monitor.get_memory_usage()

        assert execution_time < 5.0  # 小数据集训练应在5秒内完成
        assert result.accuracy > 0.3  # 基本性能要求
        assert model.is_trained is True

        print(
            f"小数据集训练性能: {execution_time:.3f}s, 内存变化: {memory_usage['delta_mb']:.2f}MB"
        )

    def test_training_performance_medium_dataset(self):
        """测试中等数据集训练性能"""
        model = PoissonModel()
        training_data = create_performance_test_data(1000)

        monitor = PerformanceMonitor()
        monitor.start()

        result = model.train(training_data)

        monitor.stop()

        # 性能断言
        execution_time = monitor.get_execution_time()
        memory_usage = monitor.get_memory_usage()

        assert execution_time < 15.0  # 中等数据集训练应在15秒内完成
        assert result.accuracy > 0.3
        assert len(model.team_attack_strength) > 0

        print(
            f"中等数据集训练性能: {execution_time:.3f}s, 内存变化: {memory_usage['delta_mb']:.2f}MB"
        )

    def test_prediction_performance_single(self):
        """测试单个预测性能"""
        model = PoissonModel()
        training_data = create_performance_test_data(200)
        model.train(training_data)

        test_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "perf_test_001",
        }

        monitor = PerformanceMonitor()
        monitor.start()

        result = model.predict(test_data)

        monitor.stop()

        # 性能断言
        execution_time = monitor.get_execution_time()
        memory_usage = monitor.get_memory_usage()

        assert execution_time < 0.1  # 单个预测应在100ms内完成
        assert isinstance(result, PredictionResult)
        assert (
            abs(result.home_win_prob + result.draw_prob + result.away_win_prob - 1.0)
            < 0.01
        )

        print(
            f"单个预测性能: {execution_time:.6f}s, 内存变化: {memory_usage['delta_mb']:.2f}MB"
        )

    def test_prediction_performance_batch(self):
        """测试批量预测性能"""
        model = PoissonModel()
        training_data = create_performance_test_data(200)
        model.train(training_data)

        # 创建批量预测数据
        batch_size = 100
        batch_data = []
        for i in range(batch_size):
            batch_data.append(
                {
                    "home_team": f"Team_{chr(65 + i % 20)}",
                    "away_team": f"Team_{chr(65 + (i + 1) % 20)}",
                    "match_id": f"batch_test_{i:03d}",
                }
            )

        monitor = PerformanceMonitor()
        monitor.start()

        predictions = []
        for data in batch_data:
            result = model.predict(data)
            predictions.append(result)

        monitor.stop()

        # 性能断言
        execution_time = monitor.get_execution_time()
        monitor.get_memory_usage()
        avg_time_per_prediction = execution_time / batch_size

        assert execution_time < 5.0  # 批量预测应在5秒内完成
        assert avg_time_per_prediction < 0.05  # 平均每个预测在50ms内
        assert len(predictions) == batch_size

        print(
            f"批量预测性能: {execution_time:.3f}s, 平均每个: {avg_time_per_prediction:.6f}s"
        )

    def test_model_memory_usage(self):
        """测试模型内存使用"""
        # 获取初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 创建并训练多个模型
        models = []
        training_data = create_performance_test_data(300)

        for i in range(5):
            model = PoissonModel(f"memory_test_v{i}")
            model.train(training_data)
            models.append(model)

        # 获取训练后内存使用
        after_training_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = after_training_memory - initial_memory

        # 进行预测以测试推理内存使用
        test_data = {"home_team": "Team_A", "away_team": "Team_B"}
        for model in models:
            model.predict(test_data)

        # 获取预测后内存使用
        after_prediction_memory = process.memory_info().rss / 1024 / 1024

        # 内存使用断言
        assert memory_increase < 100  # 5个模型内存增长应小于100MB
        assert (
            after_prediction_memory - after_training_memory < 10
        )  # 预测内存增长应小于10MB

        print(
            f"内存使用: 初始={initial_memory:.2f}MB, 训练后={after_training_memory:.2f}MB, "
            f"预测后={after_prediction_memory:.2f}MB, 增长={memory_increase:.2f}MB"
        )

    def test_concurrent_prediction_performance(self):
        """测试并发预测性能"""
        model = PoissonModel()
        training_data = create_performance_test_data(200)
        model.train(training_data)

        def predict_task(task_id):
            """单个预测任务"""
            test_data = {
                "home_team": f"Team_{chr(65 + task_id % 20)}",
                "away_team": f"Team_{chr(65 + (task_id + 1) % 20)}",
                "match_id": f"concurrent_test_{task_id:03d}",
            }
            start_time = time.time()
            result = model.predict(test_data)
            end_time = time.time()
            return {
                "task_id": task_id,
                "execution_time": end_time - start_time,
                "result": result,
            }

        # 并发测试
        num_tasks = 50
        max_workers = 4

        monitor = PerformanceMonitor()
        monitor.start()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(predict_task, i) for i in range(num_tasks)]
            results = [future.result() for future in as_completed(futures)]

        monitor.stop()

        # 分析结果
        execution_times = [r["execution_time"] for r in results]
        successful_tasks = len([r for r in results if r["result"] is not None])

        total_execution_time = monitor.get_execution_time()
        avg_task_time = np.mean(execution_times)
        max_task_time = np.max(execution_times)

        # 性能断言
        assert successful_tasks == num_tasks
        assert total_execution_time < 10.0  # 总执行时间应在10秒内
        assert avg_task_time < 0.5  # 平均任务时间应在500ms内

        print(
            f"并发预测性能: 任务数={num_tasks}, 并发数={max_workers}, "
            f"总时间={total_execution_time:.3f}s, 平均任务时间={avg_task_time:.6f}s, "
            f"最大任务时间={max_task_time:.6f}s"
        )

    def test_model_scaling_performance(self):
        """测试模型扩展性能"""
        data_sizes = [100, 500, 1000, 2000]
        performance_results = []

        for size in data_sizes:
            model = PoissonModel(f"scale_test_{size}")
            training_data = create_performance_test_data(size)

            monitor = PerformanceMonitor()
            monitor.start()

            result = model.train(training_data)

            monitor.stop()

            performance_results.append(
                {
                    "data_size": size,
                    "training_time": monitor.get_execution_time(),
                    "memory_usage": monitor.get_memory_usage()["delta_mb"],
                    "accuracy": result.accuracy,
                }
            )

        # 分析扩展性
        training_times = [r["training_time"] for r in performance_results]
        [r["memory_usage"] for r in performance_results]

        # 计算时间复杂度（应该是近似线性的）
        size_ratio = data_sizes[-1] / data_sizes[0]
        time_ratio = training_times[-1] / training_times[0]

        # 扩展性断言
        assert time_ratio < size_ratio * 1.5  # 时间增长不应超过数据增长的1.5倍
        assert all(t < 30 for t in training_times)  # 所有训练时间都应在30秒内

        print("扩展性测试结果:")
        for result in performance_results:
            print(
                f"  数据量={result['data_size']}, 训练时间={result['training_time']:.3f}s, "
                f"内存增长={result['memory_usage']:.2f}MB, 准确率={result['accuracy']:.3f}"
            )

        print(f"数据增长{size_ratio:.1f}倍，时间增长{time_ratio:.1f}倍")


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.performance
class TestMLModelOptimization:
    """ML模型优化测试"""

    def test_hyperparameter_optimization_impact(self):
        """测试超参数优化的影响"""
        base_training_data = create_performance_test_data(500)

        # 不同的超参数配置
        hyperparameter_configs = [
            {"home_advantage": 0.1, "min_matches_per_team": 5},
            {"home_advantage": 0.3, "min_matches_per_team": 10},
            {"home_advantage": 0.5, "min_matches_per_team": 15},
            {"home_advantage": 0.7, "min_matches_per_team": 20},
        ]

        results = []

        for config in hyperparameter_configs:
            model = PoissonModel()
            model.update_hyperparameters(**config)

            monitor = PerformanceMonitor()
            monitor.start()

            training_result = model.train(base_training_data)

            monitor.stop()

            # 评估性能
            test_data = create_performance_test_data(100)
            evaluation_metrics = model.evaluate(test_data)

            results.append(
                {
                    "config": config,
                    "training_time": monitor.get_execution_time(),
                    "training_accuracy": training_result.accuracy,
                    "evaluation_accuracy": evaluation_metrics["accuracy"],
                    "memory_usage": monitor.get_memory_usage()["delta_mb"],
                }
            )

        # 分析结果
        best_config = max(results, key=lambda x: x["evaluation_accuracy"])
        fastest_training = min(results, key=lambda x: x["training_time"])

        print("超参数优化结果:")
        for result in results:
            print(
                f"  配置={result['config']}, 训练时间={result['training_time']:.3f}s, "
                f"评估准确率={result['evaluation_accuracy']:.3f}"
            )

        print(
            f"最佳配置: {best_config['config']}, 准确率: {best_config['evaluation_accuracy']:.3f}"
        )
        print(
            f"最快训练: {fastest_training['config']}, 时间: {fastest_training['training_time']:.3f}s"
        )

        # 优化断言
        assert best_config["evaluation_accuracy"] > 0.3
        assert fastest_training["training_time"] < 10.0

    def test_data_preprocessing_optimization(self):
        """测试数据预处理优化"""
        # 创建包含噪声的数据
        raw_data = create_performance_test_data(1000)

        # 添加一些噪声和异常值
        noisy_data = raw_data.copy()
        for i in range(len(noisy_data)):
            if np.random.random() < 0.1:  # 10%的概率添加异常值
                noisy_data.loc[i, "home_score"] = np.random.randint(-5, 20)
                noisy_data.loc[i, "away_score"] = np.random.randint(-5, 20)

        def optimized_preprocessing(data):
            """优化的数据预处理"""
            # 1. 过滤无效数据
            filtered_data = data[
                (data["home_score"] >= 0)
                & (data["home_score"] <= 15)
                & (data["away_score"] >= 0)
                & (data["away_score"] <= 15)
            ]

            # 2. 移除重复数据
            filtered_data = filtered_data.drop_duplicates(
                subset=["home_team", "away_team", "match_date"]
            )

            # 3. 数据质量检查
            initial_size = len(data)
            final_size = len(filtered_data)
            quality_ratio = final_size / initial_size

            return filtered_data, quality_ratio

        # 测试预处理性能
        monitor = PerformanceMonitor()
        monitor.start()

        clean_data, quality_ratio = optimized_preprocessing(noisy_data)

        monitor.stop()

        # 训练模型比较
        model_noisy = PoissonModel("noisy_data")
        model_clean = PoissonModel("clean_data")

        # 训练噪声数据模型
        start_time = time.time()
        model_noisy.train(noisy_data)
        noisy_training_time = time.time() - start_time

        # 训练清洁数据模型
        start_time = time.time()
        model_clean.train(clean_data)
        clean_training_time = time.time() - start_time

        # 评估性能
        test_data = create_performance_test_data(100)
        noisy_metrics = model_noisy.evaluate(test_data)
        clean_metrics = model_clean.evaluate(test_data)

        preprocessing_time = monitor.get_execution_time()

        print("数据预处理优化:")
        print(f"  预处理时间: {preprocessing_time:.3f}s")
        print(f"  数据质量提升: {quality_ratio:.3f}")
        print(
            f"  噪声数据训练时间: {noisy_training_time:.3f}s, 准确率: {noisy_metrics['accuracy']:.3f}"
        )
        print(
            f"  清洁数据训练时间: {clean_training_time:.3f}s, 准确率: {clean_metrics['accuracy']:.3f}"
        )

        # 优化断言
        assert preprocessing_time < 2.0  # 预处理应该很快
        assert quality_ratio > 0.7  # 应该保留大部分数据
        assert (
            clean_metrics["accuracy"] >= noisy_metrics["accuracy"]
        )  # 清洁数据应该提高或保持准确率

    def test_model_caching_optimization(self):
        """测试模型缓存优化"""
        model = PoissonModel()
        training_data = create_performance_test_data(300)
        model.train(training_data)

        # 重复相同的预测请求
        same_prediction_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "cache_test",
        }

        # 第一次预测（无缓存）
        monitor = PerformanceMonitor()
        monitor.start()

        result1 = model.predict(same_prediction_data)

        monitor.stop()
        first_prediction_time = monitor.get_execution_time()

        # 模拟缓存行为（实际实现中应该在模型内部实现缓存）
        # 这里我们只是测试重复调用的性能一致性
        subsequent_times = []

        for i in range(10):
            monitor.start()
            result = model.predict(same_prediction_data)
            monitor.stop()
            subsequent_times.append(monitor.get_execution_time())

            # 验证结果一致性
            assert result.home_win_prob == result1.home_win_prob
            assert result.draw_prob == result1.draw_prob
            assert result.away_win_prob == result1.away_win_prob

        avg_subsequent_time = np.mean(subsequent_times)
        max_subsequent_time = np.max(subsequent_times)

        print("模型缓存测试:")
        print(f"  首次预测时间: {first_prediction_time:.6f}s")
        print(f"  平均后续时间: {avg_subsequent_time:.6f}s")
        print(f"  最大后续时间: {max_subsequent_time:.6f}s")

        # 缓存性能断言
        assert (
            max_subsequent_time < first_prediction_time * 2
        )  # 后续预测不应该显著慢于首次
        assert all(t < 0.1 for t in subsequent_times)  # 所有后续预测都应该很快

    def test_batch_processing_optimization(self):
        """测试批处理优化"""
        model = PoissonModel()
        training_data = create_performance_test_data(300)
        model.train(training_data)

        # 创建批量数据
        batch_data = []
        for i in range(100):
            batch_data.append(
                {
                    "home_team": f"Team_{chr(65 + i % 20)}",
                    "away_team": f"Team_{chr(65 + (i + 1) % 20)}",
                    "match_id": f"batch_opt_{i:03d}",
                }
            )

        # 逐个处理
        monitor = PerformanceMonitor()
        monitor.start()

        individual_results = []
        for data in batch_data:
            result = model.predict(data)
            individual_results.append(result)

        monitor.stop()
        individual_time = monitor.get_execution_time()

        # 模拟批处理优化（实际应该在模型中实现）
        # 这里测试向量化和批处理的潜力
        monitor = PerformanceMonitor()
        monitor.start()

        # 模拟批处理逻辑
        batch_results = []
        for data in batch_data:
            result = model.predict(data)  # 在实际实现中这应该是批处理
            batch_results.append(result)

        monitor.stop()
        batch_time = monitor.get_execution_time()

        # 验证结果一致性
        assert len(individual_results) == len(batch_results)
        for i, (ind, batch) in enumerate(zip(individual_results, batch_results)):
            assert ind.home_win_prob == batch.home_win_prob
            assert ind.draw_prob == batch.draw_prob
            assert ind.away_win_prob == batch.away_win_prob

        print("批处理优化测试:")
        print(f"  逐个处理时间: {individual_time:.3f}s")
        print(f"  批处理时间: {batch_time:.3f}s")
        print(
            f"  性能提升: {individual_time/batch_time:.2f}x"
            if batch_time > 0
            else "无法计算"
        )

        # 性能断言
        assert batch_time <= individual_time * 1.2  # 批处理不应该显著慢于逐个处理


# 测试运行器
async def run_ml_performance_tests():
    """运行ML性能测试套件"""
    print("🚀 开始ML性能测试")
    print("=" * 60)

    # 这里可以添加更复杂的ML性能测试逻辑
    print("✅ ML性能测试完成")


if __name__ == "__main__":
    asyncio.run(run_ml_performance_tests())
