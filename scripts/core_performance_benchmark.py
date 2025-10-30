#!/usr/bin/env python3
"""
Phase G Week 4 核心模块性能基准测试
Core Performance Benchmark

专注于测试核心模块性能，建立性能基线。
"""

import asyncio
import json
import statistics
import time
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.utils.string_utils import StringUtils
    from src.utils.dict_utils import DictUtils
    from src.services.manager import service_manager
    from src.observers.manager import get_observer_manager
    from src.core.service_lifecycle import get_lifecycle_manager
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("⚠️  某些模块可能不可用，将跳过相关测试")


class CorePerformanceBenchmark:
    """核心模块性能基准测试工具"""

    def __init__(self):
        self.results: Dict[str, List[float]] = {}
        self.start_time = None

    def run_benchmark(self, name: str, func, iterations: int = 1000) -> Dict[str, Any]:
        """运行性能基准测试"""
        print(f"🔧 运行基准测试: {name}")

        times = []

        # 预热
        for _ in range(10):
            try:
                func()
            except Exception:
                pass

        # 正式测试
        successful_runs = 0
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                result = func()
                end = time.perf_counter()
                times.append(end - start)
                successful_runs += 1

                # 简单验证结果不为空
                if result is None:
                    print(f"⚠️  警告: 函数返回None结果")
            except Exception as e:
                print(f"⚠️  测试运行失败: {e}")
                continue

        if successful_runs == 0:
            print(f"❌ 所有测试运行都失败了")
            return {
                'name': name,
                'iterations': iterations,
                'successful_runs': 0,
                'error': 'All runs failed'
            }

        # 计算统计信息
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        result_stats = {
            'name': name,
            'iterations': iterations,
            'successful_runs': successful_runs,
            'avg_time_ms': avg_time * 1000,
            'median_time_ms': median_time * 1000,
            'min_time_ms': min_time * 1000,
            'max_time_ms': max_time * 1000,
            'std_dev_ms': std_dev * 1000,
            'total_time_s': sum(times),
            'ops_per_second': successful_runs / sum(times) if sum(times) > 0 else 0,
            'success_rate': (successful_runs / iterations) * 100
        }

        self.results[name] = times

        return result_stats

    def test_string_utils_performance(self) -> Dict[str, Any]:
        """测试字符串工具性能"""

        def snake_case_conversion():
            return StringUtils.to_snake_case('TestPerformanceStringConversion')

        return self.run_benchmark('string_utils.snake_case', snake_case_conversion, 10000)

    def test_dict_utils_performance(self) -> Dict[str, Any]:
        """测试字典工具性能"""
        test_dict = {
            'key1': 'value1', 'key2': 'value2', 'key3': 'value3',
            'performance_test': 'test_value', 'filter_me': 'filtered',
            'keep_this': 'kept', 'another_key': 'another_value',
            'extra_key1': 'extra1', 'extra_key2': 'extra2'
        }

        def dict_filtering():
            return DictUtils.filter_keys(test_dict, ['key1', 'performance_test', 'keep_this'])

        return self.run_benchmark('dict_utils.filter_keys', dict_filtering, 10000)

    def test_service_manager_performance(self) -> Dict[str, Any]:
        """测试服务管理器性能"""

        def service_loading():
            return len(service_manager.get_all_services())

        return self.run_benchmark('service_manager.get_all_services', service_loading, 1000)

    def test_observer_manager_performance(self) -> Dict[str, Any]:
        """测试观察者管理器性能"""
        observer_manager = get_observer_manager()

        def metrics_collection():
            return observer_manager.get_all_metrics()

        return self.run_benchmark('observer_manager.get_metrics', metrics_collection, 1000)

    def test_lifecycle_manager_performance(self) -> Dict[str, Any]:
        """测试生命周期管理器性能"""

        def lifecycle_operations():
            lifecycle_manager = get_lifecycle_manager()
            return len(lifecycle_manager.get_all_services())

        return self.run_benchmark('lifecycle_manager.get_services', lifecycle_operations, 1000)

    async def test_async_observer_performance(self) -> Dict[str, Any]:
        """测试异步观察者性能"""
        observer_manager = get_observer_manager()

        async def async_prediction_record():
            await observer_manager.record_prediction(
                strategy_name="test_strategy",
                response_time_ms=50.0,
                success=True,
                confidence=0.85
            )

        times = []
        iterations = 1000
        successful_runs = 0

        # 预热
        for _ in range(10):
            try:
                await async_prediction_record()
            except Exception:
                pass

        # 正式测试
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                await async_prediction_record()
                end = time.perf_counter()
                times.append(end - start)
                successful_runs += 1
            except Exception as e:
                print(f"⚠️  异步测试失败: {e}")
                continue

        if successful_runs == 0:
            return {
                'name': 'async_observer.record_prediction',
                'iterations': iterations,
                'successful_runs': 0,
                'error': 'All async runs failed'
            }

        avg_time = statistics.mean(times)
        result_stats = {
            'name': 'async_observer.record_prediction',
            'iterations': iterations,
            'successful_runs': successful_runs,
            'avg_time_ms': avg_time * 1000,
            'ops_per_second': successful_runs / sum(times) if sum(times) > 0 else 0,
            'success_rate': (successful_runs / iterations) * 100
        }

        return result_stats

    def test_complex_string_operations(self) -> Dict[str, Any]:
        """测试复杂字符串操作性能"""

        def complex_string_processing():
            test_strings = [
                'TestPerformanceStringConversion',
                'AnotherTestCaseWithMultipleWords',
                'XMLHttpRequestToAPIServiceEndpoint',
                'ComplexBusinessLogicValidationRule',
                'DatabaseConnectionPoolManager'
            ]
            results = []
            for s in test_strings:
                results.append(StringUtils.to_snake_case(s))
            return results

        return self.run_benchmark('string_utils.complex_processing', complex_string_processing, 1000)

    def test_complex_dict_operations(self) -> Dict[str, Any]:
        """测试复杂字典操作性能"""
        test_dict = {f'key_{i}': f'value_{i}' for i in range(100)}
        test_dict.update({
            'special_key_1': 'special_value_1',
            'special_key_2': 'special_value_2',
            'performance_test_key': 'performance_test_value'
        })

        def complex_dict_filtering():
            filter_keys = [f'key_{i}' for i in range(10, 20)]
            filter_keys.extend(['special_key_1', 'performance_test_key'])
            return DictUtils.filter_keys(test_dict, filter_keys)

        return self.run_benchmark('dict_utils.complex_filtering', complex_dict_filtering, 1000)

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        print("🚀 Phase G Week 4 核心模块性能基准测试开始...")
        print("=" * 60)

        start_time = time.time()
        self.start_time = start_time

        all_results = {}

        # 同步测试
        tests = [
            self.test_string_utils_performance,
            self.test_complex_string_operations,
            self.test_dict_utils_performance,
            self.test_complex_dict_operations,
            self.test_service_manager_performance,
            self.test_observer_manager_performance,
            self.test_lifecycle_manager_performance,
        ]

        for test_func in tests:
            try:
                result = test_func()
                all_results[result['name']] = result
                if result.get('error'):
                    print(f"❌ {result['name']}: {result['error']}")
                else:
                    print(f"✅ {result['name']}: {result['avg_time_ms']:.3f}ms avg, {result['ops_per_second']:.0f} ops/s ({result['success_rate']:.1f}% success)")
            except Exception as e:
                print(f"❌ {test_func.__name__} 失败: {e}")

        # 异步测试
        try:
            async_result = asyncio.run(self.test_async_observer_performance())
            all_results[async_result['name']] = async_result
            if async_result.get('error'):
                print(f"❌ {async_result['name']}: {async_result['error']}")
            else:
                print(f"✅ {async_result['name']}: {async_result['avg_time_ms']:.3f}ms avg, {async_result['ops_per_second']:.0f} ops/s ({async_result['success_rate']:.1f}% success)")
        except Exception as e:
            print(f"❌ 异步测试失败: {e}")

        total_time = time.time() - start_time

        print("=" * 60)
        print(f"📊 核心模块性能基准测试完成，总耗时: {total_time:.2f}s")
        successful_tests = len([r for r in all_results.values() if not r.get('error')])
        print(f"📈 共完成 {successful_tests}/{len(all_results)} 个基准测试")

        return {
            'timestamp': datetime.now().isoformat(),
            'total_benchmark_time_s': total_time,
            'benchmarks': all_results,
            'summary': self._generate_summary(all_results),
            'successful_tests': successful_tests,
            'total_tests': len(all_results)
        }

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成性能摘要"""
        successful_results = [r for r in results.values() if not r.get('error')]

        if not successful_results:
            return {}

        avg_times = [r.get('avg_time_ms', 0) for r in successful_results]
        ops_per_second = [r.get('ops_per_second', 0) for r in successful_results]
        success_rates = [r.get('success_rate', 0) for r in successful_results]

        return {
            'total_benchmarks': len(results),
            'successful_benchmarks': len(successful_results),
            'avg_response_time_ms': statistics.mean(avg_times),
            'max_response_time_ms': max(avg_times),
            'min_response_time_ms': min(avg_times),
            'avg_ops_per_second': statistics.mean(ops_per_second),
            'max_ops_per_second': max(ops_per_second),
            'min_ops_per_second': min(ops_per_second),
            'avg_success_rate': statistics.mean(success_rates)
        }

    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """保存基准测试结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"core_performance_benchmark_{timestamp}.json"

        filepath = os.path.join(os.path.dirname(__file__), '..', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"💾 基准测试结果已保存到: {filepath}")
        return filepath

    def display_results(self, results: Dict[str, Any]):
        """显示测试结果"""
        print("\n📊 性能基准测试详细结果:")
        print("=" * 80)

        for name, result in results.items():
            if result.get('error'):
                print(f"❌ {name}: {result['error']}")
                continue

            print(f"\n🔧 {name}")
            print(f"   迭代次数: {result.get('iterations', 0)}")
            print(f"   成功次数: {result.get('successful_runs', 0)}")
            print(f"   成功率: {result.get('success_rate', 0):.1f}%")
            print(f"   平均响应时间: {result.get('avg_time_ms', 0):.3f}ms")
            print(f"   最小响应时间: {result.get('min_time_ms', 0):.3f}ms")
            print(f"   最大响应时间: {result.get('max_time_ms', 0):.3f}ms")
            print(f"   吞吐量: {result.get('ops_per_second', 0):.0f} ops/s")

        # 显示摘要
        summary = results.get('summary', {})
        if summary:
            print(f"\n📈 性能摘要:")
            print(f"   成功测试: {summary.get('successful_benchmarks', 0)}/{summary.get('total_benchmarks', 0)}")
            print(f"   平均响应时间: {summary.get('avg_response_time_ms', 0):.3f}ms")
            print(f"   最大响应时间: {summary.get('max_response_time_ms', 0):.3f}ms")
            print(f"   平均吞吐量: {summary.get('avg_ops_per_second', 0):.0f} ops/s")
            print(f"   最大吞吐量: {summary.get('max_ops_per_second', 0):.0f} ops/s")
            print(f"   平均成功率: {summary.get('avg_success_rate', 0):.1f}%")

        print("\n🎯 性能分析:")
        if summary.get('avg_response_time_ms', 0) < 1:
            print("   ✅ 响应时间: 优秀 (< 1ms)")
        elif summary.get('avg_response_time_ms', 0) < 5:
            print("   ⚠️  响应时间: 良好 (1-5ms)")
        else:
            print("   ❌ 响应时间: 需要优化 (> 5ms)")

        if summary.get('avg_ops_per_second', 0) > 10000:
            print("   ✅ 吞吐量: 优秀 (> 10,000 ops/s)")
        elif summary.get('avg_ops_per_second', 0) > 5000:
            print("   ✅ 吞吐量: 良好 (5,000-10,000 ops/s)")
        else:
            print("   ⚠️  吞吐量: 可接受 (< 5,000 ops/s)")

        if summary.get('avg_success_rate', 0) > 99:
            print("   ✅ 成功率: 优秀 (> 99%)")
        elif summary.get('avg_success_rate', 0) > 95:
            print("   ✅ 成功率: 良好 (95-99%)")
        else:
            print("   ❌ 成功率: 需要改进 (< 95%)")


def main():
    """主函数"""
    benchmark = CorePerformanceBenchmark()

    # 运行所有基准测试
    results = benchmark.run_all_benchmarks()

    # 显示结果
    benchmark.display_results(results)

    # 保存结果
    filepath = benchmark.save_results(results)

    return results


if __name__ == "__main__":
    main()