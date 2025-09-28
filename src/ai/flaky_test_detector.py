#!/usr/bin/env python3
"""
智能Flaky Test检测器 - 基于历史数据和选择性检测，避免误报和性能开销
"""

import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

@dataclass
class FlakyDetectionConfig:
    """Flaky检测配置"""
    # 选择性检测：只检测关键测试文件
    target_test_patterns: List[str] = None

    # 运行控制
    max_runs: int = 3  # 减少到3次，降低开销
    timeout_per_run: int = 60  # 单次运行超时
    total_timeout: int = 300    # 总超时控制

    # 外部依赖标记
    external_service_patterns: Set[str] = None

    # 历史数据要求
    min_historical_runs: int = 3  # 至少3次历史数据才判定

    def __post_init__(self):
        if self.target_test_patterns is None:
            self.target_test_patterns = [
                "tests/test_data_*.py",
                "tests/test_models_*.py",
                "tests/test_services_*.py"
            ]
        if self.external_service_patterns is None:
            self.external_service_patterns = {
                "test_.*database.*",
                "test_.*kafka.*",
                "test_.*redis.*",
                "test_.*api.*",
                "test_.*external.*"
            }

class SmartFlakyTestDetector:
    """智能Flaky Test检测器"""

    def __init__(self, config: Optional[FlakyDetectionConfig] = None):
        self.config = config or FlakyDetectionConfig()
        self.results_dir = Path("docs/_reports/flaky")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.results_dir / "test_history.json"
        self.flaky_database = self.results_dir / "flaky_database.json"

    def load_test_history(self) -> Dict:
        """加载测试历史数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load test history: {e}")

        return {}

    def save_test_history(self, history: Dict):
        """保存测试历史数据"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save test history: {e}")

    def get_target_test_files(self) -> List[str]:
        """获取目标测试文件"""
        target_files = []

        # 使用glob匹配目标测试文件
        import glob
        for pattern in self.config.target_test_patterns:
            target_files.extend(glob.glob(pattern))

        # 去重并过滤存在的文件
        return list(set(f for f in target_files if Path(f).exists()))

    def is_external_service_test(self, test_file: str) -> bool:
        """判断是否为外部服务测试"""
        filename = Path(test_file).name.lower()
        for pattern in self.config.external_service_patterns:
            if re.match(pattern, filename):
                return True
        return False

    def run_test_multiple_times(self, test_path: str) -> Dict:
        """多次运行单个测试"""
        results = {
            "test_path": test_path,
            "runs": [],
            "passed": 0,
            "failed": 0,
            "execution_times": [],
            "is_flaky": False,
            "is_external_test": self.is_external_service_test(test_path)
        }

        logger.info(f"Running test {test_path} {self.config.max_runs} times...")

        for run in range(self.config.max_runs):
            try:
                start_time = time.time()

                # 运行单个测试文件
                result = subprocess.run(
                    ["python", "-m", "pytest", test_path, "--tb=short", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout_per_run,
                    cwd="."
                )

                execution_time = time.time() - start_time

                run_result = {
                    "run_number": run + 1,
                    "return_code": result.returncode,
                    "execution_time": execution_time,
                    "passed": result.returncode == 0,
                    "stdout": result.stdout[:1000],  # 截断长输出
                    "stderr": result.stderr[:1000]
                }

                results["runs"].append(run_result)
                results["execution_times"].append(execution_time)

                if result.returncode == 0:
                    results["passed"] += 1
                else:
                    results["failed"] += 1

            except subprocess.TimeoutExpired:
                logger.warning(f"Test {test_path} timed out on run {run + 1}")
                results["runs"].append({
                    "run_number": run + 1,
                    "error": "TIMEOUT",
                    "execution_time": self.config.timeout_per_run,
                    "passed": False
                })
                results["failed"] += 1
                results["execution_times"].append(self.config.timeout_per_run)

            except Exception as e:
                logger.error(f"Test {test_path} failed on run {run + 1}: {e}")
                results["runs"].append({
                    "run_number": run + 1,
                    "error": str(e),
                    "execution_time": 0,
                    "passed": False
                })
                results["failed"] += 1
                results["execution_times"].append(0)

        # 基于多次运行结果判断是否为flaky
        results["is_flaky"] = self._is_flaky_based_on_results(results)

        return results

    def _is_flaky_based_on_results(self, results: Dict) -> bool:
        """基于运行结果判断是否为flaky"""
        # 外部服务测试不计入主flaky指标
        if results.get("is_external_test", False):
            return False

        passed = results["passed"]
        failed = results["failed"]
        total_runs = len(results["runs"])

        # 如果有成功也有失败，则为flaky
        if passed > 0 and failed > 0:
            return True

        # 如果所有运行都失败，但执行时间差异很大，也可能是flaky
        if failed == total_runs and total_runs > 1:
            times = results["execution_times"]
            if max(times) > min(times) * 2:  # 执行时间差异超过2倍
                return True

        return False

    def detect_flaky_tests(self, incremental: bool = True) -> Dict:
        """检测Flaky测试"""
        start_time = time.time()

        # 获取目标测试文件
        target_files = self.get_target_test_files()

        # 加载历史数据
        history = self.load_test_history()

        # 执行检测
        flaky_results = []
        detection_summary = {
            "total_tests": len(target_files),
            "flaky_tests": 0,
            "external_tests": 0,
            "execution_time": 0,
            "detection_mode": "incremental" if incremental else "full"
        }

        for i, test_file in enumerate(target_files):
            logger.info(f"Processing test {i+1}/{len(target_files)}: {test_file}")

            # 检查超时
            if time.time() - start_time > self.config.total_timeout:
                logger.warning(f"Flaky detection timed out after {self.config.total_timeout}s")
                detection_summary["timeout"] = True
                break

            # 跳过外部服务测试（单独标记）
            if self.is_external_service_test(test_file):
                detection_summary["external_tests"] += 1
                continue

            # 运行多次检测
            test_results = self.run_test_multiple_times(test_file)

            # 更新历史数据
            if test_file not in history:
                history[test_file] = []
            history[test_file].append({
                "timestamp": time.time(),
                "results": test_results
            })

            # 如果是flaky且满足历史数据要求，则记录
            if test_results["is_flaky"]:
                historical_runs = len(history[test_file])
                if historical_runs >= self.config.min_historical_runs:
                    # 检查历史一致性
                    flaky_consistency = self._check_flaky_consistency(history[test_file])
                    if flaky_consistency >= 0.5:  # 50%以上的历史运行都是flaky
                        flaky_results.append(test_results)
                        detection_summary["flaky_tests"] += 1
                        logger.warning(f"Confirmed flaky test: {test_file}")
                else:
                    logger.info(f"Potential flaky test (needs more data): {test_file}")

        # 保存历史数据
        self.save_test_history(history)

        # 保存结果
        detection_summary["execution_time"] = time.time() - start_time
        final_results = {
            "summary": detection_summary,
            "flaky_tests": flaky_results,
            "timestamp": time.time()
        }

        self._save_flaky_results(final_results)

        return final_results

    def _check_flaky_consistency(self, history: List[Dict]) -> float:
        """检查flaky一致性"""
        if not history:
            return 0.0

        flaky_count = sum(1 for record in history if record["results"]["is_flaky"])
        return flaky_count / len(history)

    def _save_flaky_results(self, results: Dict):
        """保存flaky检测结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"flaky_results_{timestamp}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 更新最新结果
        latest_file = self.results_dir / "latest_flaky_results.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Flaky detection results saved to {result_file}")

    def generate_flaky_report(self) -> str:
        """生成Flaky测试报告"""
        latest_file = self.results_dir / "latest_flaky_results.json"
        if not latest_file.exists():
            return "No flaky test detection results available"

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            summary = results["summary"]

            report = f"""
## 🔄 Flaky Test 检测结果

### 执行信息
- **检测模式**: {summary.get('detection_mode', 'unknown')}
- **执行时间**: {summary.get('execution_time', 0):.1f}秒
- **总测试数**: {summary.get('total_tests', 0)}
- **超时设置**: {self.config.total_timeout}秒

### 检测结果
- **Flaky测试**: {summary.get('flaky_tests', 0)}个 ⚠️
- **外部服务测试**: {summary.get('external_tests', 0)}个 🔌
- **稳定测试**: {summary.get('total_tests', 0) - summary.get('flaky_tests', 0) - summary.get('external_tests', 0)}个 ✅

### 风险评估
- **检测覆盖率**: {(summary.get('total_tests', 0) / max(len(self.get_target_test_files()), 1) * 100):.1f}%
- **Flaky比例**: {(summary.get('flaky_tests', 0) / max(summary.get('total_tests', 0), 1) * 100):.1f}%
"""

            if summary.get('timeout', False):
                report += "- **执行超时**: 部分测试因超时未完成检测 ⏰\n"

            # 添加具体flaky测试信息
            if results.get("flaky_tests"):
                report += "\n### 🚨 具体Flaky测试\n"
                for flaky_test in results["flaky_tests"]:
                    test_path = flaky_test["test_path"]
                    failed_runs = flaky_test["failed"]
                    total_runs = len(flaky_test["runs"])
                    avg_time = sum(flaky_test["execution_times"]) / total_runs

                    report += f"- **{test_path}**: {failed_runs}/{total_runs}次失败，平均执行时间{avg_time:.1f}秒\n"

            report += f"""
### 改进建议
{self._generate_flaky_recommendations(summary)}

### 环境说明
- **检测配置**: {self.config.max_runs}次运行，要求{self.config.min_historical_runs}次历史数据
- **外部服务测试**: 已单独标记，不计入主要flaky指标
- **超时控制**: 单次{self.config.timeout_per_run}秒，总{self.config.total_timeout}秒
"""
            return report

        except Exception as e:
            logger.error(f"Failed to generate flaky report: {e}")
            return "Failed to generate flaky report"

    def _generate_flaky_recommendations(self, summary: Dict) -> str:
        """生成Flaky测试改进建议"""
        flaky_count = summary.get('flaky_tests', 0)
        total_tests = summary.get('total_tests', 0)

        if flaky_count == 0:
            return "✅ 未检测到Flaky测试，测试稳定性良好"
        elif flaky_count <= 2:
            return f"⚠️ 发现{flaky_count}个Flaky测试，建议优化测试逻辑，添加适当的等待或重试机制"
        else:
            return f"🚨 发现{flaky_count}个Flaky测试，占比{(flaky_count/total_tests*100):.1f}%，建议优先修复这些测试的不稳定性"


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Smart Flaky Test Detection")
    parser.add_argument("--incremental", action="store_true", default=True,
                       help="Run incremental flaky detection (default)")
    parser.add_argument("--full", action="store_true",
                       help="Run full flaky detection")
    parser.add_argument("--report-only", action="store_true",
                       help="Only show flaky test report")

    args = parser.parse_args()

    detector = SmartFlakyTestDetector()

    if args.report_only:
        print(detector.generate_flaky_report())
        return

    incremental_mode = args.incremental and not args.full
    results = detector.detect_flaky_tests(incremental=incremental_mode)

    print(detector.generate_flaky_report())


if __name__ == "__main__":
    main()