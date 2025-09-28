#!/usr/bin/env python3
"""
相对性能基准测试器 - 只在关键函数运行，控制执行时间和风险
"""

import subprocess
import json
import time
import logging
import psutil
import platform
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
import statistics
import re

logger = logging.getLogger(__name__)

@dataclass
class PerformanceBenchmarkConfig:
    """性能基准测试配置"""
    # 选择性测试：只测试关键函数
    target_functions: List[str] = None

    # 性能阈值控制（百分比变化）
    warning_threshold: float = 10.0  # 10%变化警告
    critical_threshold: float = 20.0  # 20%变化严重

    # 执行控制
    max_runs: int = 5  # 减少运行次数
    warmup_runs: int = 2  # 预热运行
    timeout_per_function: int = 30  # 单个函数超时
    total_timeout: int = 180  # 总超时控制

    # 环境信息收集
    collect_env_info: bool = True

    # 内存控制
    max_memory_mb: int = 512  # 最大内存使用

    def __post_init__(self):
        if self.target_functions is None:
            self.target_functions = [
                "src.models.prediction_service.predict_match",
                "src.data.collectors.scores_collector.collect_data",
                "src.features.feature_calculator.calculate_features",
                "src.services.data_processing.process_batch"
            ]

class RelativePerformanceBenchmark:
    """相对性能基准测试器"""

    def __init__(self, config: Optional[PerformanceBenchmarkConfig] = None):
        self.config = config or PerformanceBenchmarkConfig()
        self.results_dir = Path("docs/_reports/performance")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_file = self.results_dir / "performance_baselines.json"
        self.env_info_file = self.results_dir / "environment_info.json"

    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        env_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }

        # 获取git commit信息
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                env_info["git_commit"] = result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get git commit: {e}")

        return env_info

    def save_environment_info(self, env_info: Dict[str, Any]):
        """保存环境信息"""
        with open(self.env_info_file, 'w', encoding='utf-8') as f:
            json.dump(env_info, f, indent=2, ensure_ascii=False)
        logger.info(f"Environment info saved to {self.env_info_file}")

    def load_baselines(self) -> Dict:
        """加载历史基准数据"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load baselines: {e}")

        return {}

    def save_baselines(self, baselines: Dict):
        """保存基准数据"""
        with open(self.baseline_file, 'w', encoding='utf-8') as f:
            json.dump(baselines, f, indent=2, ensure_ascii=False)
        logger.info(f"Performance baselines saved to {self.baseline_file}")

    def create_test_script(self, function_name: str) -> str:
        """创建性能测试脚本"""
        script = f'''
import time
import psutil
import sys
import os

# 添加项目路径
sys.path.insert(0, os.getcwd())

def benchmark_function():
    """基准测试函数"""
    try:
        # 导入并运行目标函数
        module_path, func_name = "{function_name}".rsplit(".", 1)
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)

        # 创建简单的测试数据
        if "predict_match" in func_name:
            test_data = {{"home_team": "Team A", "away_team": "Team B", "league": "Test League"}}
            result = func(**test_data)
        elif "collect_data" in func_name:
            result = func()
        elif "calculate_features" in func_name:
            result = func({{"match_data": []}})
        elif "process_batch" in func_name:
            result = func([])
        else:
            result = func()

        return {{"success": True, "result": str(result)[:100]}}
    except Exception as e:
        return {{"success": False, "error": str(e)}}

if __name__ == "__main__":
    # 运行基准测试
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024

    result = benchmark_function()

    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss / 1024 / 1024

    # 输出结果
    print(json.dumps({{
        "execution_time": end_time - start_time,
        "memory_usage": end_memory - start_memory,
        "result": result
    }}, ensure_ascii=False))
'''
        return script

    def run_function_benchmark(self, function_name: str) -> Dict:
        """运行单个函数的基准测试"""
        results = {
            "function": function_name,
            "runs": [],
            "execution_times": [],
            "memory_usages": [],
            "successful_runs": 0,
            "failed_runs": 0,
            "avg_execution_time": 0,
            "std_execution_time": 0,
            "avg_memory_usage": 0,
            "performance_grade": "unknown"
        }

        logger.info(f"Benchmarking function {function_name}...")

        # 预热运行
        for i in range(self.config.warmup_runs):
            try:
                self._run_single_benchmark(function_name)
            except Exception as e:
                logger.warning(f"Warmup run {i+1} failed: {e}")

        # 正式运行
        for run in range(self.config.max_runs):
            try:
                start_time = time.time()

                # 检查内存使用
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                if current_memory > self.config.max_memory_mb:
                    logger.warning(f"Memory limit exceeded: {current_memory}MB > {self.config.max_memory_mb}MB")
                    break

                # 运行基准测试
                benchmark_result = self._run_single_benchmark(function_name)

                execution_time = time.time() - start_time

                run_data = {
                    "run_number": run + 1,
                    "execution_time": execution_time,
                    "memory_usage": benchmark_result.get("memory_usage", 0),
                    "success": benchmark_result.get("result", {}).get("success", False),
                    "result": benchmark_result.get("result", {})
                }

                results["runs"].append(run_data)
                results["execution_times"].append(execution_time)
                results["memory_usages"].append(benchmark_result.get("memory_usage", 0))

                if run_data["success"]:
                    results["successful_runs"] += 1
                else:
                    results["failed_runs"] += 1

                # 检查超时
                if execution_time > self.config.timeout_per_function:
                    logger.warning(f"Function {function_name} timed out on run {run + 1}")
                    break

            except Exception as e:
                logger.error(f"Function {function_name} failed on run {run + 1}: {e}")
                results["failed_runs"] += 1

        # 计算统计数据
        if results["execution_times"]:
            results["avg_execution_time"] = statistics.mean(results["execution_times"])
            results["std_execution_time"] = statistics.stdev(results["execution_times"]) if len(results["execution_times"]) > 1 else 0

        if results["memory_usages"]:
            results["avg_memory_usage"] = statistics.mean(results["memory_usages"])

        # 评估性能等级
        results["performance_grade"] = self._evaluate_performance_grade(results)

        return results

    def _run_single_benchmark(self, function_name: str) -> Dict:
        """运行单次基准测试"""
        # 创建临时测试脚本
        script_content = self.create_test_script(function_name)
        script_path = "/tmp/benchmark_script.py"

        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            # 运行测试脚本
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_per_function,
                cwd="."
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Script failed: {result.stderr}")
                return {"error": result.stderr, "memory_usage": 0}

        except subprocess.TimeoutExpired:
            logger.error(f"Benchmark script timed out for {function_name}")
            return {"error": "TIMEOUT", "memory_usage": 0}
        except Exception as e:
            logger.error(f"Benchmark script failed for {function_name}: {e}")
            return {"error": str(e), "memory_usage": 0}
        finally:
            # 清理临时文件
            try:
                Path(script_path).unlink()
            except:
                pass

    def _evaluate_performance_grade(self, results: Dict) -> str:
        """评估性能等级"""
        if results["failed_runs"] > 0:
            return "failed"

        if results["successful_runs"] < self.config.max_runs * 0.8:
            return "unstable"

        # 基于执行时间变异性评估
        cv = results["std_execution_time"] / results["avg_execution_time"] if results["avg_execution_time"] > 0 else 1

        if cv < 0.1:  # 变异系数小于10%
            return "excellent"
        elif cv < 0.2:  # 变异系数小于20%
            return "good"
        elif cv < 0.3:  # 变异系数小于30%
            return "fair"
        else:
            return "poor"

    def compare_with_baseline(self, current_results: Dict, baseline_data: Dict) -> Dict:
        """与基准数据对比"""
        comparison = {
            "function": current_results["function"],
            "current_performance": current_results,
            "baseline_performance": baseline_data.get(current_results["function"], {}),
            "changes": {},
            "alerts": []
        }

        baseline = baseline_data.get(current_results["function"], {})

        if baseline:
            # 执行时间对比
            current_time = current_results.get("avg_execution_time", 0)
            baseline_time = baseline.get("avg_execution_time", 0)

            if baseline_time > 0:
                time_change_pct = ((current_time - baseline_time) / baseline_time) * 100
                comparison["changes"]["execution_time_change_pct"] = time_change_pct

                # 生成警告
                if abs(time_change_pct) > self.config.critical_threshold:
                    comparison["alerts"].append({
                        "type": "critical",
                        "metric": "execution_time",
                        "change_pct": time_change_pct,
                        "message": f"执行时间变化{time_change_pct:.1f}%，超过{self.config.critical_threshold}%阈值"
                    })
                elif abs(time_change_pct) > self.config.warning_threshold:
                    comparison["alerts"].append({
                        "type": "warning",
                        "metric": "execution_time",
                        "change_pct": time_change_pct,
                        "message": f"执行时间变化{time_change_pct:.1f}%，超过{self.config.warning_threshold}%阈值"
                    })

            # 内存使用对比
            current_memory = current_results.get("avg_memory_usage", 0)
            baseline_memory = baseline.get("avg_memory_usage", 0)

            if baseline_memory > 0:
                memory_change_pct = ((current_memory - baseline_memory) / baseline_memory) * 100
                comparison["changes"]["memory_usage_change_pct"] = memory_change_pct

                if abs(memory_change_pct) > self.config.critical_threshold:
                    comparison["alerts"].append({
                        "type": "critical",
                        "metric": "memory_usage",
                        "change_pct": memory_change_pct,
                        "message": f"内存使用变化{memory_change_pct:.1f}%，超过{self.config.critical_threshold}%阈值"
                    })
                elif abs(memory_change_pct) > self.config.warning_threshold:
                    comparison["alerts"].append({
                        "type": "warning",
                        "metric": "memory_usage",
                        "change_pct": memory_change_pct,
                        "message": f"内存使用变化{memory_change_pct:.1f}%，超过{self.config.warning_threshold}%阈值"
                    })

        return comparison

    def run_performance_benchmarks(self, update_baselines: bool = False) -> Dict:
        """运行性能基准测试"""
        start_time = time.time()

        # 收集环境信息
        env_info = self.get_environment_info()
        if self.config.collect_env_info:
            self.save_environment_info(env_info)

        # 加载基准数据
        baseline_data = self.load_baselines()

        # 执行基准测试
        benchmark_results = []
        comparisons = []

        summary = {
            "total_functions": len(self.config.target_functions),
            "successful_functions": 0,
            "failed_functions": 0,
            "execution_time": 0,
            "environment": env_info,
            "alerts": []
        }

        for i, function_name in enumerate(self.config.target_functions):
            logger.info(f"Processing function {i+1}/{len(self.config.target_functions)}: {function_name}")

            # 检查总超时
            if time.time() - start_time > self.config.total_timeout:
                logger.warning(f"Performance benchmark timed out after {self.config.total_timeout}s")
                summary["timeout"] = True
                break

            try:
                # 运行基准测试
                result = self.run_function_benchmark(function_name)
                benchmark_results.append(result)

                # 与基准对比
                comparison = self.compare_with_baseline(result, baseline_data)
                comparisons.append(comparison)

                # 收集警告
                summary["alerts"].extend(comparison["alerts"])

                if result["performance_grade"] != "failed":
                    summary["successful_functions"] += 1
                else:
                    summary["failed_functions"] += 1

            except Exception as e:
                logger.error(f"Failed to benchmark {function_name}: {e}")
                summary["failed_functions"] += 1

        # 更新基准数据
        if update_baselines:
            new_baselines = {}
            for result in benchmark_results:
                if result["performance_grade"] != "failed":
                    new_baselines[result["function"]] = {
                        "avg_execution_time": result["avg_execution_time"],
                        "std_execution_time": result["std_execution_time"],
                        "avg_memory_usage": result["avg_memory_usage"],
                        "performance_grade": result["performance_grade"],
                        "timestamp": time.time()
                    }

            # 合并新旧基准数据
            baseline_data.update(new_baselines)
            self.save_baselines(baseline_data)

        # 生成最终报告
        summary["execution_time"] = time.time() - start_time
        final_report = {
            "summary": summary,
            "benchmark_results": benchmark_results,
            "comparisons": comparisons,
            "timestamp": time.time()
        }

        self._save_results(final_report)

        return final_report

    def _save_results(self, results: Dict):
        """保存测试结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"performance_results_{timestamp}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 更新最新结果
        latest_file = self.results_dir / "latest_performance_results.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Performance benchmark results saved to {result_file}")

    def generate_performance_report(self) -> str:
        """生成性能报告"""
        latest_file = self.results_dir / "latest_performance_results.json"
        if not latest_file.exists():
            return "No performance benchmark results available"

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            summary = results["summary"]
            env_info = summary.get("environment", {})

            report = f"""
## ⚡ 性能基准测试结果

### 环境信息
- **系统**: {env_info.get('platform', 'Unknown')}
- **Python版本**: {env_info.get('python_version', 'Unknown')}
- **CPU核心数**: {env_info.get('cpu_count', 'Unknown')}
- **内存总量**: {env_info.get('memory_total_gb', 'Unknown')}GB
- **Git提交**: {env_info.get('git_commit', 'Unknown')}

### 执行信息
- **总函数数**: {summary.get('total_functions', 0)}
- **成功函数**: {summary.get('successful_functions', 0)} ✅
- **失败函数**: {summary.get('failed_functions', 0)} ❌
- **执行时间**: {summary.get('execution_time', 0):.1f}秒
- **超时设置**: {self.config.total_timeout}秒

### 性能警报
- **总警报数**: {len(summary.get('alerts', []))}
- **严重警报**: {len([a for a in summary.get('alerts', []) if a.get('type') == 'critical'])} 🚨
- **警告警报**: {len([a for a in summary.get('alerts', []) if a.get('type') == 'warning'])} ⚠️
"""

            # 添加具体警报信息
            if summary.get('alerts'):
                report += "\n### 🚨 具体警报\n"
                for alert in summary['alerts'][:5]:  # 只显示前5个
                    report += f"- **{alert.get('metric', 'Unknown')}**: {alert.get('message', 'No message')}\n"

            # 添加性能概览
            if results.get('benchmark_results'):
                report += "\n### 📊 性能概览\n"
                for result in results['benchmark_results'][:3]:  # 只显示前3个
                    func_name = result['function'].split('.')[-1]
                    avg_time = result.get('avg_execution_time', 0)
                    grade = result.get('performance_grade', 'unknown')
                    report += f"- **{func_name}**: {avg_time:.3f}s ({grade})\n"

            report += f"""
### 配置信息
- **运行次数**: {self.config.max_runs}次（预热{self.config.warmup_runs}次）
- **警告阈值**: {self.config.warning_threshold}%变化
- **严重阈值**: {self.config.critical_threshold}%变化
- **内存限制**: {self.config.max_memory_mb}MB
"""

            return report

        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return "Failed to generate performance report"


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Relative Performance Benchmark")
    parser.add_argument("--update-baselines", action="store_true",
                       help="Update baseline performance data")
    parser.add_argument("--report-only", action="store_true",
                       help="Only show performance report")

    args = parser.parse_args()

    benchmark = RelativePerformanceBenchmark()

    if args.report_only:
        print(benchmark.generate_performance_report())
        return

    results = benchmark.run_performance_benchmarks(update_baselines=args.update_baselines)
    print(benchmark.generate_performance_report())


if __name__ == "__main__":
    main()