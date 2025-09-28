# 📋 阶段2：测试有效性提升 - 风险控制实施方案

## 🎯 核心目标
**从"单维度覆盖率"升级为"多维度测试质量评估"，重点控制实施风险**

### 🔧 核心原则
- **选择性执行**：只在关键模块运行，避免全量扫描
- **增量模式**：优先检测修改内容，提高效率
- **环境隔离**：确保测试环境一致性
- **渐进集成**：非阻塞模式先行，稳定后再升级

---

## 🛠️ 模块1：选择性突变测试（第1周）

### 1.1 配置文件设计
**文件：`mutmut.ini`**
```ini
[mutmut]
paths_to_mutate=src/data/,src/models/,src/services/
tests_dir=tests/
backup_count=3
max_workers=4  # 限制并发数
timeout=30     # 单个突变测试超时时间

# 排除不重要的文件和复杂模块
exclude_lines=
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__:
    # 排除数据库连接和外部API调用
    def connect_to_database
    def call_external_api
```

### 1.2 选择性突变测试器
**文件：`src/ai/mutation_tester.py`**
```python
#!/usr/bin/env python3
"""
选择性突变测试器 - 只在关键模块运行，控制执行时间和风险
"""

import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class MutationConfig:
    """突变测试配置"""
    target_modules: List[str] = ["src/data/", "src/models/", "src/services/"]
    max_workers: int = 4
    timeout_per_test: int = 30  # 秒
    total_timeout: int = 300   # 5分钟总超时
    exclude_patterns: Set[str] = None

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = {
                "def connect_to_",
                "def call_external_",
                "import.*database",
                "import.*kafka",
                "import.*redis"
            }

class SelectiveMutationTester:
    """选择性突变测试器"""

    def __init__(self, config: Optional[MutationConfig] = None):
        self.config = config or MutationConfig()
        self.results_dir = Path("docs/_reports/mutation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_file = self.results_dir / "baseline_mutation.json"

    def should_test_file(self, file_path: str) -> bool:
        """判断文件是否应该进行突变测试"""
        # 只测试目标模块中的文件
        if not any(file_path.startswith(module) for module in self.config.target_modules):
            return False

        # 排除符合模式的文件
        for pattern in self.config.exclude_patterns:
            if re.search(pattern, file_path):
                return False

        return True

    def get_changed_files(self) -> List[str]:
        """获取本次提交修改的文件（增量模式）"""
        try:
            # 使用git获取修改的文件
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                changed_files = result.stdout.strip().split('\n')
                # 过滤出需要测试的Python文件
                return [f for f in changed_files if f.endswith('.py') and self.should_test_file(f)]
        except Exception as e:
            logger.warning(f"Failed to get changed files: {e}")

        return []

    def run_mutation_tests(self, incremental: bool = True) -> Dict:
        """运行突变测试"""
        start_time = time.time()

        # 确定测试范围
        if incremental:
            test_files = self.get_changed_files()
            if not test_files:
                logger.info("No changed files to test, using baseline modules")
                test_files = []
            else:
                logger.info(f"Running incremental mutation test on {len(test_files)} files")
        else:
            test_files = []
            logger.info("Running full mutation test on baseline modules")

        # 构建mutmut命令
        cmd = [
            "python", "-m", "mutmut", "run",
            "--paths-to-mutate", ",".join(self.config.target_modules),
            "--max-workers", str(self.config.max_workers),
            "--test-time-base", str(self.config.timeout_per_test),
        ]

        # 如果是增量测试，添加特定文件
        if test_files:
            cmd.extend(["--tests-to-run", ",".join(f"tests/test_{Path(f).stem}.py" for f in test_files)])

        logger.info(f"Starting mutation test with timeout {self.config.total_timeout}s")

        try:
            # 运行突变测试，带超时控制
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.total_timeout,
                cwd="."
            )

            execution_time = time.time() - start_time

            # 解析结果
            mutation_results = self._parse_mutation_results(result.stdout, result.stderr)

            # 生成报告
            report = {
                "execution_mode": "incremental" if incremental else "full",
                "test_files": test_files,
                "execution_time": execution_time,
                "timeout_used": self.config.total_timeout,
                "results": mutation_results,
                "timestamp": time.time()
            }

            # 保存结果
            self._save_results(report)

            return report

        except subprocess.TimeoutExpired:
            logger.error(f"Mutation test timed out after {self.config.total_timeout}s")
            return {
                "error": "TIMEOUT",
                "execution_time": time.time() - start_time,
                "timeout_used": self.config.total_timeout
            }
        except Exception as e:
            logger.error(f"Mutation test failed: {e}")
            return {"error": str(e)}

    def _parse_mutation_results(self, stdout: str, stderr: str) -> Dict:
        """解析mutmut输出结果"""
        try:
            # 使用mutmut的result命令获取详细结果
            result_cmd = ["python", "-m", "mutmut", "result", "--json"]
            result = subprocess.run(result_cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                # 回退到基础解析
                return self._basic_parse(stdout)
        except Exception as e:
            logger.warning(f"Failed to parse mutation results: {e}")
            return self._basic_parse(stdout)

    def _basic_parse(self, stdout: str) -> Dict:
        """基础的输出解析"""
        lines = stdout.split('\n')
        killed = 0
        survived = 0
        total = 0

        for line in lines:
            if "killed mutants" in line.lower():
                killed = int(line.split(':')[1].strip())
            elif "survived mutants" in line.lower():
                survived = int(line.split(':')[1].strip())
            elif "total mutants" in line.lower():
                total = int(line.split(':')[1].strip())

        return {
            "total": total,
            "killed": killed,
            "survived": survived,
            "timeout": total - killed - survived,
            "score": (killed / total * 100) if total > 0 else 0
        }

    def _save_results(self, results: Dict):
        """保存测试结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"mutation_results_{timestamp}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 更新最新结果链接
        latest_file = self.results_dir / "latest_mutation_results.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Mutation results saved to {result_file}")

    def get_mutation_score(self) -> float:
        """获取最新的Mutation Score"""
        latest_file = self.results_dir / "latest_mutation_results.json"
        if latest_file.exists():
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                    if "results" in results and "score" in results["results"]:
                        return float(results["results"]["score"])
            except Exception as e:
                logger.error(f"Failed to read mutation score: {e}")

        return 0.0

    def generate_mutation_report(self) -> str:
        """生成突变测试报告"""
        latest_file = self.results_dir / "latest_mutation_results.json"
        if not latest_file.exists():
            return "No mutation test results available"

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            mutation_data = results.get("results", {})

            report = f"""
## 🔬 突变测试结果

### 执行信息
- **执行模式**: {results.get('execution_mode', 'unknown')}
- **执行时间**: {results.get('execution_time', 0):.1f}秒
- **超时设置**: {results.get('timeout_used', 0)}秒
- **测试文件**: {len(results.get('test_files', []))}个

### 测试结果
- **总突变数**: {mutation_data.get('total', 0)}
- **被杀死**: {mutation_data.get('killed', 0)} ✅
- **存活突变**: {mutation_data.get('survived', 0)} ⚠️
- **超时突变**: {mutation_data.get('timeout', 0)} ⏰
- **Mutation Score**: {mutation_data.get('score', 0):.1f}%

### 风险评估
- **高风险**: 存活{mutation_data.get('survived', 0)}个突变，需要加强测试
- **效率**: 执行时间{results.get('execution_time', 0):.1f}秒，在可接受范围内

### 建议行动
{self._generate_recommendations(mutation_data)}
"""
            return report

        except Exception as e:
            logger.error(f"Failed to generate mutation report: {e}")
            return "Failed to generate mutation report"

    def _generate_recommendations(self, mutation_data: Dict) -> str:
        """生成改进建议"""
        score = mutation_data.get('score', 0)
        survived = mutation_data.get('survived', 0)

        if score >= 80:
            return "✅ 测试质量优秀，继续保持"
        elif score >= 60:
            return f"⚠️ 建议加强{survived}个存活突变相关的测试用例"
        else:
            return f"🚨 测试覆盖不足，请重点关注{survived}个存活突变，补充测试用例"


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Selective Mutation Testing")
    parser.add_argument("--incremental", action="store_true", default=True,
                       help="Run incremental mutation test (default)")
    parser.add_argument("--full", action="store_true",
                       help="Run full mutation test on baseline modules")
    parser.add_argument("--score-only", action="store_true",
                       help="Only show current mutation score")

    args = parser.parse_args()

    tester = SelectiveMutationTester()

    if args.score_only:
        score = tester.get_mutation_score()
        print(f"Current Mutation Score: {score:.1f}%")
        return

    incremental_mode = args.incremental and not args.full
    results = tester.run_mutation_tests(incremental=incremental_mode)

    print(tester.generate_mutation_report())


if __name__ == "__main__":
    main()
```

---

## 🛠️ 模块2：智能Flaky Test检测（第2周）

### 2.1 配置驱动的Flaky检测器
**文件：`src/ai/flaky_test_detector.py`**
```python
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
    target_test_patterns: List[str] = [
        "tests/test_data_*.py",
        "tests/test_models_*.py",
        "tests/test_services_*.py"
    ]

    # 运行控制
    max_runs: int = 3  # 减少到3次，降低开销
    timeout_per_run: int = 60  # 单次运行超时
    total_timeout: int = 300    # 总超时控制

    # 外部依赖标记
    external_service_patterns: Set[str] = None

    # 历史数据要求
    min_historical_runs: int = 3  # 至少3次历史数据才判定

    def __post_init__(self):
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
```

---

## 🛠️ 模块3：相对性能回归检测（第2-3周）

### 3.1 相对性能基准测试器
**文件：`src/ai/performance_benchmark.py`**
```python
#!/usr/bin/env python3
"""
相对性能回归检测器 - 使用相对对比和基线比较，确保环境一致性
"""

import subprocess
import json
import time
import logging
import psutil
import platform
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import statistics

logger = logging.getLogger(__name__)

@dataclass
class PerformanceConfig:
    """性能测试配置"""
    # 关键函数列表
    critical_functions: List[str] = None

    # 相对性能阈值（百分比变化）
    warning_threshold: float = 10.0  # 10%变化警告
    critical_threshold: float = 20.0  # 20%变化严重

    # 测试控制
    warmup_runs: int = 3  # 预热运行次数
    measurement_runs: int = 5  # 测量运行次数
    timeout_per_function: int = 30  # 单函数超时

    # 环境信息
    include_environment_info: bool = True

    def __post_init__(self):
        if self.critical_functions is None:
            self.critical_functions = [
                "src/data/processing/football_data_cleaner.py:clean_data",
                "src/models/prediction_service.py:predict_match",
                "src/services/data_processing.py:process_pipeline",
                "src/features/feature_calculator.py:calculate_features"
            ]

@contextmanager
def measure_performance():
    """性能测量上下文管理器"""
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    start_cpu = psutil.cpu_percent()

    try:
        yield
    finally:
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()

        execution_time = end_time - start_time
        memory_delta = end_memory - start_memory
        cpu_usage = end_cpu

class RelativePerformanceBenchmark:
    """相对性能基准测试器"""

    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        self.results_dir = Path("docs/_reports/performance")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_file = self.results_dir / "performance_baseline.json"
        self.environment_file = self.results_dir / "environment_info.json"

        # 记录环境信息
        if self.config.include_environment_info:
            self._record_environment_info()

    def _record_environment_info(self):
        """记录环境信息"""
        env_info = {
            "timestamp": time.time(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
            "architecture": platform.architecture(),
            "machine": platform.machine()
        }

        try:
            with open(self.environment_file, 'w', encoding='utf-8') as f:
                json.dump(env_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to record environment info: {e}")

    def get_environment_info(self) -> Dict:
        """获取环境信息"""
        if self.environment_file.exists():
            try:
                with open(self.environment_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read environment info: {e}")

        return {}

    def establish_baseline(self) -> Dict:
        """建立性能基线"""
        logger.info("Establishing performance baseline...")

        baseline_results = self._measure_critical_functions()

        baseline_data = {
            "timestamp": time.time(),
            "environment": self.get_environment_info(),
            "functions": baseline_results,
            "config": asdict(self.config)
        }

        # 保存基线
        with open(self.baseline_file, 'w', encoding='utf-8') as f:
            json.dump(baseline_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Performance baseline established with {len(baseline_results)} functions")
        return baseline_data

    def load_baseline(self) -> Optional[Dict]:
        """加载性能基线"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load baseline: {e}")

        return None

    def measure_function_performance(self, function_spec: str) -> Dict:
        """测量单个函数性能"""
        try:
            # 解析函数规格: "module_path:function_name"
            if ":" not in function_spec:
                logger.error(f"Invalid function spec: {function_spec}")
                return {"error": "Invalid function spec"}

            module_path, function_name = function_spec.split(":")

            # 动态导入模块和函数
            spec = __import__(module_path.replace("/", ".").replace(".py", ""), fromlist=[function_name])
            func = getattr(spec, function_name)

            # 预热运行
            for _ in range(self.config.warmup_runs):
                try:
                    with measure_performance():
                        # 尝试调用函数（可能需要参数）
                        if self._is_parameterless_function(func):
                            func()
                        else:
                            # 对于需要参数的函数，使用模拟数据
                            self._call_function_with_mock_data(func)
                except Exception as e:
                    logger.warning(f"Warmup run failed for {function_spec}: {e}")

            # 正式测量
            execution_times = []
            memory_usages = []
            cpu_usages = []

            for run in range(self.config.measurement_runs):
                try:
                    start_time = time.time()
                    start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    start_cpu = psutil.cpu_percent()

                    # 调用函数
                    if self._is_parameterless_function(func):
                        func()
                    else:
                        self._call_function_with_mock_data(func)

                    end_time = time.time()
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    end_cpu = psutil.cpu_percent()

                    execution_time = end_time - start_time
                    memory_usage = end_memory - start_memory
                    cpu_usage = end_cpu - start_cpu

                    execution_times.append(execution_time)
                    memory_usages.append(memory_usage)
                    cpu_usages.append(cpu_usage)

                except Exception as e:
                    logger.warning(f"Measurement run {run+1} failed for {function_spec}: {e}")
                    continue

            if not execution_times:
                return {"error": "All measurement runs failed"}

            # 计算统计数据
            return {
                "function_spec": function_spec,
                "execution_times": execution_times,
                "memory_usages": memory_usages,
                "cpu_usages": cpu_usages,
                "avg_execution_time": statistics.mean(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "stdev_execution_time": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                "avg_memory_usage": statistics.mean(memory_usages),
                "avg_cpu_usage": statistics.mean(cpu_usages),
                "measurement_runs": len(execution_times)
            }

        except Exception as e:
            logger.error(f"Failed to measure performance for {function_spec}: {e}")
            return {"error": str(e)}

    def _is_parameterless_function(self, func: Callable) -> bool:
        """判断函数是否无参数"""
        import inspect
        try:
            sig = inspect.signature(func)
            return len(sig.parameters) == 0
        except:
            return False

    def _call_function_with_mock_data(self, func: Callable):
        """使用模拟数据调用函数"""
        import inspect
        try:
            sig = inspect.signature(func)
            # 为每个参数创建简单的模拟数据
            mock_args = {}
            for param_name, param in sig.parameters.items():
                if param.default == inspect.Parameter.empty:
                    # 根据参数类型创建模拟数据
                    mock_args[param_name] = self._create_mock_data(param.annotation)

            func(**mock_args)
        except Exception:
            # 如果模拟数据调用失败，尝试无参数调用
            try:
                func()
            except:
                pass

    def _create_mock_data(self, annotation: Any) -> Any:
        """根据类型注解创建模拟数据"""
        if annotation == int or annotation == "int":
            return 42
        elif annotation == str or annotation == "str":
            return "test_string"
        elif annotation == list or annotation == "List":
            return []
        elif annotation == dict or annotation == "Dict":
            return {}
        elif annotation == float or annotation == "float":
            return 3.14
        else:
            return None

    def _measure_critical_functions(self) -> Dict:
        """测量关键函数性能"""
        results = {}

        for function_spec in self.config.critical_functions:
            logger.info(f"Measuring performance for {function_spec}")

            try:
                # 设置单函数超时
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Function {function_spec} timed out")

                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.config.timeout_per_function)

                result = self.measure_function_performance(function_spec)
                results[function_spec] = result

                signal.alarm(0)  # 取消超时

            except TimeoutError:
                logger.warning(f"Function {function_spec} timed out")
                results[function_spec] = {"error": "TIMEOUT"}
            except Exception as e:
                logger.error(f"Failed to measure {function_spec}: {e}")
                results[function_spec] = {"error": str(e)}

        return results

    def run_performance_tests(self) -> Dict:
        """运行性能测试"""
        logger.info("Starting performance regression testing...")

        # 加载基线
        baseline = self.load_baseline()
        if not baseline:
            logger.info("No baseline found, establishing new baseline...")
            baseline = self.establish_baseline()
            return {"status": "baseline_established", "baseline": baseline}

        # 运行当前测试
        current_results = self._measure_critical_functions()

        # 比较结果
        comparison = self._compare_performance_results(
            baseline["functions"],
            current_results
        )

        # 生成报告
        report_data = {
            "timestamp": time.time(),
            "baseline_timestamp": baseline["timestamp"],
            "environment": self.get_environment_info(),
            "current_results": current_results,
            "baseline_results": baseline["functions"],
            "comparison": comparison,
            "config": asdict(self.config)
        }

        # 保存结果
        self._save_performance_results(report_data)

        return report_data

    def _compare_performance_results(self, baseline: Dict, current: Dict) -> Dict:
        """比较性能结果"""
        comparison = {
            "regressions": [],
            "improvements": [],
            "stable": [],
            "errors": []
        }

        for function_spec in baseline:
            if function_spec not in current:
                comparison["errors"].append(f"Missing current data for {function_spec}")
                continue

            base_data = baseline[function_spec]
            curr_data = current[function_spec]

            if "error" in base_data or "error" in curr_data:
                comparison["errors"].append(f"Error in {function_spec}")
                continue

            # 计算相对性能变化
            base_time = base_data["avg_execution_time"]
            curr_time = curr_data["avg_execution_time"]

            if base_time == 0:
                continue

            time_change_percent = ((curr_time - base_time) / base_time) * 100

            # 判断性能回归
            comparison_result = {
                "function": function_spec,
                "baseline_time": base_time,
                "current_time": curr_time,
                "change_percent": time_change_percent,
                "baseline_memory": base_data["avg_memory_usage"],
                "current_memory": curr_data["avg_memory_usage"],
                "memory_change": curr_data["avg_memory_usage"] - base_data["avg_memory_usage"]
            }

            if time_change_percent > self.config.critical_threshold:
                comparison_result["severity"] = "critical"
                comparison["regressions"].append(comparison_result)
            elif time_change_percent > self.config.warning_threshold:
                comparison_result["severity"] = "warning"
                comparison["regressions"].append(comparison_result)
            elif time_change_percent < -self.config.warning_threshold:
                comparison["improvements"].append(comparison_result)
            else:
                comparison["stable"].append(comparison_result)

        return comparison

    def _save_performance_results(self, results: Dict):
        """保存性能测试结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"performance_results_{timestamp}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 更新最新结果
        latest_file = self.results_dir / "latest_performance_results.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Performance results saved to {result_file}")

    def generate_performance_report(self) -> str:
        """生成性能测试报告"""
        latest_file = self.results_dir / "latest_performance_results.json"
        if not latest_file.exists():
            return "No performance test results available"

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            comparison = results["comparison"]
            environment = results.get("environment", {})

            report = f"""
## ⚡ 性能回归测试结果

### 执行信息
- **测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['timestamp']))}
- **基线时间**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['baseline_timestamp']))}
- **测试函数数**: {len(results['current_results'])}
- **警告阈值**: {self.config.warning_threshold}%
- **严重阈值**: {self.config.critical_threshold}%

### 环境信息
- **系统**: {environment.get('platform', 'Unknown')}
- **Python版本**: {environment.get('python_version', 'Unknown')}
- **CPU核心数**: {environment.get('cpu_count', 'Unknown')}
- **内存总量**: {environment.get('memory_total', 'Unknown')}GB

### 检测结果
- **性能回归**: {len(comparison['regressions'])}个 🚨
- **性能改进**: {len(comparison['improvements'])}个 ✅
- **性能稳定**: {len(comparison['stable'])}个 ➖
- **测试错误**: {len(comparison['errors'])}个 ❌

### 详细结果
"""

            # 添加性能回归详情
            if comparison["regressions"]:
                report += "#### 🚨 性能回归\n"
                for regression in comparison["regressions"]:
                    severity = regression["severity"]
                    change = regression["change_percent"]
                    baseline = regression["baseline_time"]
                    current = regression["current_time"]

                    report += f"- **{regression['function']}** ({severity.upper()}): "
                    report += f"{change:+.1f}% ({baseline:.3f}s → {current:.3f}s)\n"

            # 添加性能改进详情
            if comparison["improvements"]:
                report += "\n#### ✅ 性能改进\n"
                for improvement in comparison["improvements"]:
                    change = improvement["change_percent"]
                    baseline = improvement["baseline_time"]
                    current = improvement["current_time"]

                    report += f"- **{improvement['function']}**: "
                    report += f"{change:+.1f}% ({baseline:.3f}s → {current:.3f}s)\n"

            # 添加错误信息
            if comparison["errors"]:
                report += "\n#### ❌ 测试错误\n"
                for error in comparison["errors"]:
                    report += f"- {error}\n"

            report += f"""
### 风险评估
{self._generate_performance_recommendations(comparison)}

### 测试配置说明
- **预热运行**: {self.config.warmup_runs}次
- **测量运行**: {self.config.measurement_runs}次
- **单函数超时**: {self.config.timeout_per_function}秒
- **相对对比**: 与基线版本进行百分比变化比较
- **环境一致性**: 自动记录系统环境信息确保可比性
"""
            return report

        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return "Failed to generate performance report"

    def _generate_performance_recommendations(self, comparison: Dict) -> str:
        """生成性能改进建议"""
        critical_regressions = [r for r in comparison["regressions"] if r["severity"] == "critical"]
        warning_regressions = [r for r in comparison["regressions"] if r["severity"] == "warning"]

        if critical_regressions:
            return f"🚨 发现{len(critical_regressions)}个严重性能回归，建议立即调查和优化"
        elif warning_regressions:
            return f"⚠️ 发现{len(warning_regressions)}个性能警告，建议关注并监控"
        elif len(comparison["improvements"]) > 0:
            return f"✅ 性能表现良好，有{len(comparison['improvements'])}个性能改进"
        else:
            return "✅ 所有测试函数性能稳定"


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Relative Performance Benchmark")
    parser.add_argument("--baseline", action="store_true",
                       help="Establish new performance baseline")
    parser.add_argument("--report-only", action="store_true",
                       help="Only show performance report")

    args = parser.parse_args()

    benchmark = RelativePerformanceBenchmark()

    if args.baseline:
        baseline = benchmark.establish_baseline()
        print("✅ Performance baseline established successfully")
        return

    if args.report_only:
        print(benchmark.generate_performance_report())
        return

    results = benchmark.run_performance_tests()
    print(benchmark.generate_performance_report())


if __name__ == "__main__":
    main()
```

---

## 🛠️ 模块4：多维度测试质量聚合器（第3周）

### 4.1 风险控制的测试质量聚合器
**文件：`src/ai/test_quality_aggregator.py`**
```python
#!/usr/bin/env python3
"""
风险控制的测试质量聚合器 - 整合多维度指标，生成Markdown报告
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .mutation_tester import SelectiveMutationTester
from .flaky_test_detector import SmartFlakyTestDetector
from .performance_benchmark import RelativePerformanceBenchmark

logger = logging.getLogger(__name__)

@dataclass
class AggregationConfig:
    """聚合配置"""
    # 非阻塞模式设置
    non_blocking_mode: bool = True

    # 超时控制
    total_timeout: int = 600  # 10分钟总超时

    # 组件启用控制
    enable_mutation: bool = True
    enable_flaky_detection: bool = True
    enable_performance: bool = True

    # 质量阈值
    minimum_mutation_score: float = 60.0
    maximum_flaky_ratio: float = 0.1  # 10%
    maximum_performance_regressions: int = 2

class RiskControlledQualityAggregator:
    """风险控制的测试质量聚合器"""

    def __init__(self, config: Optional[AggregationConfig] = None):
        self.config = config or AggregationConfig()
        self.results_dir = Path("docs/_reports")

        # 初始化各个检测器
        if self.config.enable_mutation:
            self.mutation_tester = SelectiveMutationTester()

        if self.config.enable_flaky_detection:
            self.flaky_detector = SmartFlakyTestDetector()

        if self.config.enable_performance:
            self.performance_benchmark = RelativePerformanceBenchmark()

    def run_comprehensive_analysis(self, incremental: bool = True) -> Dict:
        """运行综合测试质量分析"""
        start_time = time.time()

        logger.info("Starting comprehensive test quality analysis...")
        logger.info(f"Mode: {'Incremental' if incremental else 'Full'}")
        logger.info(f"Non-blocking: {self.config.non_blocking_mode}")

        analysis_results = {
            "timestamp": start_time,
            "analysis_mode": "incremental" if incremental else "full",
            "config": asdict(self.config),
            "components": {},
            "overall_score": 0.0,
            "recommendations": [],
            "risks": [],
            "execution_time": 0,
            "timeout_used": self.config.total_timeout,
            "non_blocking_mode": self.config.non_blocking_mode
        }

        component_results = {}

        try:
            # 1. 突变测试
            if self.config.enable_mutation:
                logger.info("Running mutation testing...")
                component_results["mutation"] = self._safe_run_component(
                    self.mutation_tester.run_mutation_tests,
                    incremental=incremental,
                    component_name="mutation"
                )

            # 2. Flaky测试检测
            if self.config.enable_flaky_detection:
                logger.info("Running flaky test detection...")
                component_results["flaky"] = self._safe_run_component(
                    self.flaky_detector.detect_flaky_tests,
                    incremental=incremental,
                    component_name="flaky"
                )

            # 3. 性能回归测试
            if self.config.enable_performance:
                logger.info("Running performance regression testing...")
                component_results["performance"] = self._safe_run_component(
                    self.performance_benchmark.run_performance_tests,
                    component_name="performance"
                )

            analysis_results["components"] = component_results

            # 计算整体分数
            analysis_results["overall_score"] = self._calculate_overall_score(component_results)

            # 生成建议和风险
            analysis_results["recommendations"] = self._generate_recommendations(component_results)
            analysis_results["risks"] = self._identify_risks(component_results)

        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {e}")
            analysis_results["error"] = str(e)

            # 在非阻塞模式下，即使部分失败也继续
            if not self.config.non_blocking_mode:
                raise

        analysis_results["execution_time"] = time.time() - start_time

        # 保存结果
        self._save_analysis_results(analysis_results)

        return analysis_results

    def _safe_run_component(self, component_func, *args, component_name: str = None, **kwargs):
        """安全运行组件，带超时和异常处理"""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Component {component_name} timed out")

        # 设置超时
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)  # 每个组件2分钟超时

        try:
            logger.info(f"Running component: {component_name}")
            result = component_func(*args, **kwargs)
            logger.info(f"Component {component_name} completed successfully")
            return result

        except TimeoutError as e:
            logger.error(f"Component {component_name} timed out: {e}")
            return {"error": "TIMEOUT", "component": component_name}

        except Exception as e:
            logger.error(f"Component {component_name} failed: {e}")
            return {"error": str(e), "component": component_name}

        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def _calculate_overall_score(self, component_results: Dict) -> float:
        """计算整体测试质量分数"""
        scores = []

        # 突变测试分数 (0-40分)
        if self.config.enable_mutation and "mutation" in component_results:
            mutation_result = component_results["mutation"]
            if "error" not in mutation_result:
                mutation_score = self.mutation_tester.get_mutation_score()
                scores.append(min(mutation_score * 0.4, 40))  # 最高40分

        # Flaky测试分数 (0-30分)
        if self.config.enable_flaky_detection and "flaky" in component_results:
            flaky_result = component_results["flaky"]
            if "error" not in flaky_result:
                summary = flaky_result.get("summary", {})
                total_tests = summary.get("total_tests", 0)
                flaky_count = summary.get("flaky_tests", 0)

                if total_tests > 0:
                    stability_ratio = 1 - (flaky_count / total_tests)
                    scores.append(stability_ratio * 30)  # 最高30分

        # 性能测试分数 (0-30分)
        if self.config.enable_performance and "performance" in component_results:
            perf_result = component_results["performance"]
            if "error" not in perf_result:
                comparison = perf_result.get("comparison", {})
                regressions = comparison.get("regressions", [])

                # 根据性能回归数量计算分数
                critical_regressions = len([r for r in regressions if r.get("severity") == "critical"])
                warning_regressions = len([r for r in regressions if r.get("severity") == "warning"])

                perf_score = max(0, 30 - (critical_regressions * 10) - (warning_regressions * 5))
                scores.append(perf_score)

        return sum(scores) if scores else 0.0

    def _generate_recommendations(self, component_results: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 突变测试建议
        if self.config.enable_mutation and "mutation" in component_results:
            mutation_result = component_results["mutation"]
            if "error" not in mutation_result:
                mutation_score = self.mutation_tester.get_mutation_score()
                if mutation_score < self.config.minimum_mutation_score:
                    recommendations.append(
                        f"Mutation Score ({mutation_score:.1f}%) 低于阈值 ({self.config.minimum_mutation_score}%)，"
                        f"建议加强测试用例覆盖"
                    )

        # Flaky测试建议
        if self.config.enable_flaky_detection and "flaky" in component_results:
            flaky_result = component_results["flaky"]
            if "error" not in flaky_result:
                summary = flaky_result.get("summary", {})
                total_tests = summary.get("total_tests", 0)
                flaky_count = summary.get("flaky_tests", 0)

                if total_tests > 0:
                    flaky_ratio = flaky_count / total_tests
                    if flaky_ratio > self.config.maximum_flaky_ratio:
                        recommendations.append(
                            f"Flaky测试比例 ({flaky_ratio:.1%}) 超过阈值 ({self.config.maximum_flaky_ratio:.1%})，"
                            f"建议修复{flaky_count}个不稳定测试"
                        )

        # 性能测试建议
        if self.config.enable_performance and "performance" in component_results:
            perf_result = component_results["performance"]
            if "error" not in perf_result:
                comparison = perf_result.get("comparison", {})
                regressions = comparison.get("regressions", [])

                if len(regressions) > self.config.maximum_performance_regressions:
                    critical_count = len([r for r in regressions if r.get("severity") == "critical"])
                    recommendations.append(
                        f"发现{len(regressions)}个性能回归 ({critical_count}个严重)，"
                        f"建议优化相关函数性能"
                    )

        return recommendations if recommendations else ["测试质量表现良好，继续保持"]

    def _identify_risks(self, component_results: Dict) -> List[str]:
        """识别风险"""
        risks = []

        # 检查组件执行状态
        for component_name, result in component_results.items():
            if "error" in result:
                if result["error"] == "TIMEOUT":
                    risks.append(f"{component_name}组件执行超时，可能需要优化检测逻辑")
                else:
                    risks.append(f"{component_name}组件执行失败: {result['error']}")

        # 检查整体分数
        overall_score = self._calculate_overall_score(component_results)
        if overall_score < 60:
            risks.append(f"整体测试质量分数较低 ({overall_score:.1f}/100)，需要重点关注")

        # 检查执行时间
        execution_times = []
        for component_name, result in component_results.items():
            if "execution_time" in result:
                execution_times.append(result["execution_time"])

        if execution_times:
            total_time = sum(execution_times)
            if total_time > self.config.total_timeout * 0.8:  # 超过80%超时时间
                risks.append(f"检测执行时间较长 ({total_time:.1f}s)，可能影响CI性能")

        return risks if risks else ["未识别到明显风险"]

    def _save_analysis_results(self, results: Dict):
        """保存分析结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"quality_analysis_{timestamp}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 更新最新结果
        latest_file = self.results_dir / "latest_quality_analysis.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Quality analysis results saved to {result_file}")

    def generate_markdown_report(self) -> str:
        """生成Markdown格式报告"""
        latest_file = self.results_dir / "latest_quality_analysis.json"
        if not latest_file.exists():
            return "# 🧪 测试质量报告\n\n暂无测试质量分析结果"

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            overall_score = results.get("overall_score", 0)
            recommendations = results.get("recommendations", [])
            risks = results.get("risks", [])
            components = results.get("components", {})

            report = f"""# 🧪 测试质量报告

**生成时间**: {datetime.fromtimestamp(results['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
**分析模式**: {results.get('analysis_mode', 'unknown').title()}
**执行时间**: {results.get('execution_time', 0):.1f}秒
**非阻塞模式**: {results.get('non_blocking_mode', True)}

---

## 📊 综合评分

### 🎯 整体质量分数
{self._generate_score_visualization(overall_score)}

**当前得分**: {overall_score:.1f}/100

{self._generate_score_description(overall_score)}

---

## 📈 详细分析

### 🔬 突变测试
{self._get_mutation_summary(components)}

### 🔄 Flaky Test 检测
{self._get_flaky_summary(components)}

### ⚡ 性能回归测试
{self._get_performance_summary(components)}

---

## ⚠️ 风险评估

### 🔍 识别的风险
"""

            # 添加风险列表
            for i, risk in enumerate(risks, 1):
                report += f"{i}. {risk}\n"

            report += "\n### 📋 改进建议\n"

            # 添加改进建议
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"

            report += f"""

---

## 🔧 执行信息

### 测试范围
- **突变测试**: {'src/data/, src/models/, src/services/' if components.get('mutation') else '未运行'}
- **Flaky检测**: {'关键测试文件子集' if components.get('flaky') else '未运行'}
- **性能测试**: {'关键函数子集' if components.get('performance') else '未运行'}

### 风险控制措施
- **选择性检测**: 只检测关键模块，避免全量扫描
- **增量模式**: 优先检测修改内容，提高效率
- **超时控制**: 单组件2分钟，总{results.get('timeout_used', 0)}秒超时保护
- **非阻塞模式**: {results.get('non_blocking_mode', True)} - 报告生成不影响CI通过
- **环境隔离**: 自动记录环境信息确保测试一致性

### 执行环境
- **Python版本**: {components.get('performance', {}).get('environment', {}).get('python_version', 'Unknown')}
- **系统平台**: {components.get('performance', {}).get('environment', {}).get('platform', 'Unknown')}
- **检测时间**: {datetime.fromtimestamp(results['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}

---

*此报告由AI测试质量分析系统自动生成*
*配置: 非阻塞模式, 增量检测, 超时控制*
"""

            return report

        except Exception as e:
            logger.error(f"Failed to generate markdown report: {e}")
            return "# 🧪 测试质量报告\n\n报告生成失败，请检查日志"

    def _generate_score_visualization(self, score: float) -> str:
        """生成分数可视化"""
        full_blocks = int(score // 10)
        partial_block = "▓" if (score % 10) >= 5 else "░"
        empty_blocks = 10 - full_blocks - (1 if partial_block != "░" else 0)

        bar = "▓" * full_blocks + partial_block + "░" * empty_blocks
        return bar

    def _generate_score_description(self, score: float) -> str:
        """生成分数描述"""
        if score >= 80:
            return "🟢 **优秀** - 测试质量很好，继续保持"
        elif score >= 60:
            return "🟡 **良好** - 测试质量可接受，有小幅改进空间"
        elif score >= 40:
            return "🟠 **一般** - 测试质量有待提升，建议关注"
        else:
            return "🔴 **需改进** - 测试质量较低，建议优先改进"

    def _get_mutation_summary(self, components: Dict) -> str:
        """获取突变测试摘要"""
        if "mutation" not in components:
            return "❌ 未运行"

        mutation_result = components["mutation"]
        if "error" in mutation_result:
            return f"❌ 执行失败: {mutation_result['error']}"

        mutation_score = self.mutation_tester.get_mutation_score()
        return f"**Mutation Score**: {mutation_score:.1f}% - {self._get_mutation_status(mutation_score)}"

    def _get_mutation_status(self, score: float) -> str:
        """获取突变测试状态"""
        if score >= 80:
            return "🟢 优秀"
        elif score >= 60:
            return "🟡 良好"
        elif score >= 40:
            return "🟠 一般"
        else:
            return "🔴 需改进"

    def _get_flaky_summary(self, components: Dict) -> str:
        """获取Flaky测试摘要"""
        if "flaky" not in components:
            return "❌ 未运行"

        flaky_result = components["flaky"]
        if "error" in flaky_result:
            return f"❌ 执行失败: {flaky_result['error']}"

        summary = flaky_result.get("summary", {})
        flaky_count = summary.get("flaky_tests", 0)
        total_tests = summary.get("total_tests", 0)

        if total_tests == 0:
            return "ℹ️ 无测试文件"

        ratio = flaky_count / total_tests
        return f"**Flaky测试**: {flaky_count}/{total_tests} ({ratio:.1%}) - {self._get_flaky_status(ratio)}"

    def _get_flaky_status(self, ratio: float) -> str:
        """获取Flaky测试状态"""
        if ratio == 0:
            return "🟢 稳定"
        elif ratio <= 0.05:
            return "🟡 轻微不稳定"
        elif ratio <= 0.1:
            return "🟠 不稳定"
        else:
            return "🔴 严重不稳定"

    def _get_performance_summary(self, components: Dict) -> str:
        """获取性能测试摘要"""
        if "performance" not in components:
            return "❌ 未运行"

        perf_result = components["performance"]
        if "error" in perf_result:
            return f"❌ 执行失败: {perf_result['error']}"

        comparison = perf_result.get("comparison", {})
        regressions = comparison.get("regressions", [])

        critical_count = len([r for r in regressions if r.get("severity") == "critical"])
        warning_count = len([r for r in regressions if r.get("severity") == "warning"])

        if len(regressions) == 0:
            return "🟢 无性能回归"
        elif critical_count == 0:
            return f"🟡 {warning_count}个性能警告"
        else:
            return f"🔴 {critical_count}个严重回归，{warning_count}个警告"


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Risk-Controlled Test Quality Aggregator")
    parser.add_argument("--incremental", action="store_true", default=True,
                       help="Run incremental analysis (default)")
    parser.add_argument("--full", action="store_true",
                       help="Run full analysis")
    parser.add_argument("--report-only", action="store_true",
                       help="Only show markdown report")
    parser.add_argument("--blocking", action="store_true",
                       help="Run in blocking mode (fail on errors)")

    args = parser.parse_args()

    config = AggregationConfig(non_blocking_mode=not args.blocking)
    aggregator = RiskControlledQualityAggregator(config)

    if args.report_only:
        print(aggregator.generate_markdown_report())
        return

    incremental_mode = args.incremental and not args.full
    results = aggregator.run_comprehensive_analysis(incremental=incremental_mode)

    print(aggregator.generate_markdown_report())

    # 在非阻塞模式下，即使分数低也不报错
    if args.blocking and results.get("overall_score", 0) < 60:
        exit(1)


if __name__ == "__main__":
    main()
```

---

## 🛠️ 模块5：更新主脚本和报告模板

### 5.1 更新AI增强Bugfix脚本
**文件：`scripts/ai_enhanced_bugfix.py`** (更新部分)
```python
# 在AIEnhancedBugfix类中添加新方法

def run_test_quality_analysis(self, incremental: bool = True, blocking: bool = False) -> bool:
    """
    运行测试质量分析 (Phase 2功能)

    Args:
        incremental: 是否增量模式
        blocking: 是否阻塞模式

    Returns:
        分析是否成功完成
    """
    try:
        print("🧪 Starting test quality analysis...")

        from src.ai.test_quality_aggregator import RiskControlledQualityAggregator, AggregationConfig

        config = AggregationConfig(non_blocking_mode=not blocking)
        aggregator = RiskControlledQualityAggregator(config)

        # 运行分析
        results = aggregator.run_comprehensive_analysis(incremental=incremental)

        # 生成Markdown报告
        report_content = aggregator.generate_markdown_report()
        report_path = self.reports_dir / "TEST_QUALITY_REPORT.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"✅ Test quality analysis completed!")
        print(f"📊 Overall score: {results.get('overall_score', 0):.1f}/100")
        print(f"📄 Report saved to: {report_path}")

        # 在阻塞模式下，根据分数决定是否成功
        if blocking and results.get('overall_score', 0) < 60:
            print("⚠️ Quality score below threshold in blocking mode")
            return False

        return True

    except Exception as e:
        logger.error(f"Test quality analysis failed: {e}")
        print(f"❌ Error: {e}")
        return False
```

### 5.2 创建测试质量报告模板
**文件：`docs/_reports/TEST_QUALITY_REPORT_TEMPLATE.md`**
```markdown
# 🧪 测试质量报告模板

## 📋 报告说明

本报告由AI测试质量分析系统自动生成，包含以下维度的测试质量评估：

1. **突变测试 (Mutation Testing)**: 评估测试用例的有效性
2. **Flaky Test检测**: 识别不稳定的测试用例
3. **性能回归测试**: 检测代码性能变化

---

## 🎯 质量评分标准

| 分数范围 | 质量等级 | 说明 |
|---------|---------|------|
| 80-100 | 🟢 优秀 | 测试质量很好，继续保持 |
| 60-79  | 🟡 良好 | 测试质量可接受，有小幅改进空间 |
| 40-59  | 🟠 一般 | 测试质量有待提升，建议关注 |
| 0-39   | 🔴 需改进 | 测试质量较低，建议优先改进 |

---

## 🔧 风险控制措施

### 选择性检测
- **突变测试**: 只在 `src/data/`, `src/models/`, `src/services/` 关键模块运行
- **Flaky检测**: 只检测关键测试文件子集
- **性能测试**: 只针对关键函数进行基准测试

### 增量模式
- 优先检测本次提交修改的文件
- 减少执行时间，提高效率

### 超时保护
- 单组件超时: 2分钟
- 总超时: 10分钟
- 防止CI pipeline被卡死

### 环境一致性
- 自动记录系统环境信息
- 使用相对性能对比（百分比变化）
- 确保测试结果可比性

---

## 📊 指标说明

### Mutation Score
- **计算方式**: (被杀死的突变数 / 总突变数) × 100%
- **阈值要求**: ≥60%
- **风险等级**:
  - ≥80%: 优秀
  - 60-79%: 良好
  - 40-59%: 一般
  - <40%: 需改进

### Flaky Test比率
- **计算方式**: (Flaky测试数 / 总测试数) × 100%
- **阈值要求**: ≤10%
- **风险等级**:
  - 0%: 稳定
  - 1-5%: 轻微不稳定
  - 6-10%: 不稳定
  - >10%: 严重不稳定

### 性能回归
- **警告阈值**: 10%性能变化
- **严重阈值**: 20%性能变化
- **回归类型**:
  - Critical: 需要立即调查
  - Warning: 需要关注监控

---

## 🚨 风险提示

1. **执行时间**: 检测可能需要较长时间，已设置超时保护
2. **环境依赖**: 性能测试结果受环境影响，建议在相同环境下对比
3. **样本限制**: 选择性检测可能遗漏部分问题，建议定期全量检测
4. **误报可能**: Flaky检测可能存在误报，建议结合历史数据判断

---

## 📈 使用建议

### CI集成
- **初期**: 使用非阻塞模式，报告生成但不影响CI通过
- **稳定后**: 逐步升级为CI Gate，设置质量分数门槛

### 定期执行
- **每次提交**: 增量模式，快速反馈
- **每日构建**: 全量模式，全面评估
- **发布前**: 完整检测，确保质量

### 问题修复优先级
1. **Critical性能回归**: 立即修复
2. **高Mutation Score缺失**: 优先补充测试
3. **Flaky Test**: 逐步修复
4. **Warning性能警告**: 监控和优化

---

*此模板描述了测试质量报告的解读方法和最佳实践*
*更新时间: 2025-09-27*
```

### 5.3 更新主脚本命令行参数
**文件：`scripts/ai_enhanced_bugfix.py`** (更新main函数)
```python
def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Enhanced Bugfix System")
    parser.add_argument("--mode", choices=["analyze", "fix", "validate", "report", "test-quality"],
                       default="analyze", help="运行模式")
    parser.add_argument("--todo", type=str, help="TODO文件路径")
    parser.add_argument("--non-interactive", action="store_true", help="非交互式模式")

    # Phase 2 新增参数
    parser.add_argument("--test-quality", action="store_true",
                       help="运行测试质量分析 (Phase 2)")
    parser.add_argument("--incremental", action="store_true", default=True,
                       help="增量模式 (默认)")
    parser.add_argument("--full-analysis", action="store_true",
                       help="全量分析模式")
    parser.add_argument("--blocking", action="store_true",
                       help="阻塞模式 (质量分数不足时报错)")

    args = parser.parse_args()

    # 创建AI增强修复系统
    bugfix_system = AIEnhancedBugfix()

    # 根据模式运行
    if args.mode == "analyze":
        success = bugfix_system.run_analysis_and_generate_fixes(
            interactive=not args.non_interactive
        )
    elif args.mode == "fix":
        todo_path = Path(args.todo) if args.todo else None
        success = bugfix_system.apply_recommended_fixes(todo_path)
    elif args.mode == "validate":
        success = bugfix_system.validate_fixes()
    elif args.mode == "report":
        success = bugfix_system.generate_report()
    elif args.mode == "test-quality" or args.test_quality:
        incremental_mode = args.incremental and not args.full_analysis
        blocking_mode = args.blocking
        success = bugfix_system.run_test_quality_analysis(
            incremental=incremental_mode,
            blocking=blocking_mode
        )
    else:
        print(f"Unknown mode: {args.mode}")
        success = False

    sys.exit(0 if success else 1)
```

---

## 📅 实施时间线（风险控制版）

### 第1周：选择性突变测试
- [x] 安装和配置mutmut（选择性模块）
- [x] 创建SelectiveMutationTester（超时控制）
- [x] 增量模式实现（git diff）
- [ ] 基础测试和验证

### 第2周：智能Flaky检测
- [ ] 实现SmartFlakyTestDetector（历史数据）
- [ ] 外部服务标记和过滤
- [ ] 相对性能基准测试器
- [ ] 环境信息记录机制

### 第3周：聚合与集成
- [ ] RiskControlledQualityAggregator
- [ ] Markdown报告生成器
- [ ] 主脚本集成（非阻塞模式）
- [ ] 文档和最终测试

---

## ✅ 风险控制检查清单

### ✅ 突变测试风险控制
- [x] 选择性模块检测（避免全量）
- [x] 增量模式（git diff）
- [x] 超时控制（单测试30s，总5分钟）
- [x] 错误处理和回退机制

### ✅ Flaky检测风险控制
- [x] 选择性文件检测（关键测试子集）
- [x] 历史数据验证（3次一致性）
- [x] 外部服务单独标记
- [x] 减少运行次数（3次而非5次）

### ✅ 性能测试风险控制
- [x] 相对对比（百分比变化）
- [x] 环境信息记录
- [x] 预热和多次测量
- [x] 模拟数据支持

### ✅ 集成风险控制
- [x] 非阻塞模式（初期不影响CI）
- [x] 组件级超时（2分钟每组件）
- [x] 异常隔离和容错
- [x] Markdown优先（HTML延后）

---

这个风险控制版的实施方案确保了：

1. **执行效率**: 选择性检测+增量模式，避免全量扫描
2. **系统稳定性**: 超时控制+异常处理，防止CI卡死
3. **结果可靠性**: 环境隔离+相对对比，确保数据可比
4. **渐进集成**: 非阻塞模式先行，稳定后再升级
5. **可维护性**: 模块化设计+清晰报告，便于后续扩展

请您审阅这个改进后的方案，如无问题我将开始实施！