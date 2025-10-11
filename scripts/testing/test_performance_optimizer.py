#!/usr/bin/env python3
"""
测试性能优化工具
分析和优化测试执行性能
"""

from typing import Dict, List
import sys
import time
import json
import subprocess
from pathlib import Path
from collections import defaultdict
import re

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestPerformanceAnalyzer:
    """测试性能分析器"""

    def __init__(self):
        self.results = {}
        self.slow_tests = []
        self.test_patterns = {}

    def run_tests_with_timing(self, test_path: str, pattern: str = None) -> Dict:
        """运行测试并记录时间"""
        cmd = [
            "python",
            "-m",
            "pytest",
            test_path,
            "--durations=0",
            "--tb=no",
            "-q",
            "--json-report",
            "--json-report-file=/tmp/test_results.json",
        ]

        if pattern:
            cmd.extend(["-k", pattern])

        start_time = time.time()
        result = subprocess.run(cmd, cwd=project_root, capture_output=True)
        end_time = time.time()

        duration = end_time - start_time

        # 解析结果
        try:
            with open("/tmp/test_results.json", "r") as f:
                json_data = json.load(f)
        except Exception:
            json_data = {"summary": {}, "tests": []}

        return {
            "duration": duration,
            "exit_code": result.returncode,
            "summary": json_data.get("summary", {}),
            "tests": json_data.get("tests", []),
        }

    def analyze_slow_tests(self, test_dir: str = "tests/unit") -> List[Dict]:
        """分析慢速测试"""
        print("🔍 Analyzing slow tests...")

        # 运行测试并获取耗时
        cmd = ["python", "-m", "pytest", test_dir, "--durations=20", "--tb=no", "-v"]

        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

        # 解析耗时信息
        slow_tests = []
        lines = result.stdout.split("\n")

        # 查找耗时列表
        in_duration_list = False
        for line in lines:
            if "slowest 20 test durations" in line.lower():
                in_duration_list = True
                continue

            if in_duration_list:
                # 匹配格式: duration (seconds) test_path::test_function
                match = re.match(r"\s*([\d.]+)\s+(.+?)\s+\[.*?\]", line)
                if match:
                    duration = float(match.group(1))
                    test_path = match.group(2)
                    slow_tests.append(
                        {
                            "duration": duration,
                            "path": test_path,
                            "category": self.categorize_test(test_path),
                        }
                    )
                elif line.strip() == "" and len(slow_tests) > 0:
                    break

        self.slow_tests = sorted(slow_tests, key=lambda x: x["duration"], reverse=True)
        return self.slow_tests

    def categorize_test(self, test_path: str) -> str:
        """分类测试"""
        if "api" in test_path:
            return "api"
        elif "database" in test_path:
            return "database"
        elif "cache" in test_path:
            return "cache"
        elif "services" in test_path:
            return "services"
        elif "models" in test_path:
            return "models"
        elif "collectors" in test_path:
            return "collectors"
        elif "tasks" in test_path:
            return "tasks"
        elif "streaming" in test_path:
            return "streaming"
        elif "monitoring" in test_path:
            return "monitoring"
        else:
            return "other"

    def generate_optimization_report(self) -> Dict:
        """生成优化报告"""
        report = {
            "slow_tests": self.slow_tests[:10],  # 前10个最慢的测试
            "categories": defaultdict(list),
            "recommendations": [],
        }

        # 按类别分组
        for test in self.slow_tests:
            report["categories"][test["category"]].append(test)

        # 生成建议
        total_slow_time = sum(t["duration"] for t in self.slow_tests)

        if total_slow_time > 60:
            report["recommendations"].append(
                {
                    "priority": "high",
                    "issue": "Total slow test time exceeds 60 seconds",
                    "suggestion": "Consider parallel test execution with pytest-xdist",
                }
            )

        # 检查特定类别的慢测试
        for category, tests in report["categories"].items():
            category_time = sum(t["duration"] for t in tests)
            if category_time > 30:
                report["recommendations"].append(
                    {
                        "priority": "medium",
                        "issue": f"{category.title()} tests are slow (total: {category_time:.1f}s)",
                        "suggestion": f"Review {category} tests for optimization opportunities",
                    }
                )

        # 检查是否有特别慢的单个测试
        very_slow = [t for t in self.slow_tests if t["duration"] > 5]
        if very_slow:
            report["recommendations"].append(
                {
                    "priority": "high",
                    "issue": f"{len(very_slow)} tests take more than 5 seconds",
                    "suggestion": "Consider mocking expensive operations or using fixtures",
                }
            )

        return report

    def optimize_test_order(self, test_files: List[str]) -> List[str]:
        """优化测试执行顺序"""
        print("📊 Optimizing test execution order...")

        # 收集测试运行时间数据
        test_times = {}
        for test_file in test_files:
            try:
                result = self.run_tests_with_timing(test_file)
                test_times[test_file] = result["duration"]
            except Exception as e:
                print(f"Warning: Could not run {test_file}: {e}")
                test_times[test_file] = 0

        # 按耗时排序（快的先执行）
        sorted_tests = sorted(test_times.items(), key=lambda x: x[1])
        return [test[0] for test in sorted_tests]

    def create_parallel_config(self, max_workers: int = None) -> Dict:
        """创建并行测试配置"""
        import multiprocessing

        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), 4)  # 限制最多4个并行

        return {
            "max_workers": max_workers,
            "cmd": f"pytest -n {max_workers} --dist=loadfile",
            "env_vars": {
                "PYTEST_XDIST_AUTO_NUM_WORKERS": str(max_workers),
                "PYTEST_XDIST_WORKER_COUNT": str(max_workers),
            },
        }

    def identify_test_dependencies(self) -> Dict[str, List[str]]:
        """识别测试之间的依赖关系"""
        print("🔗 Analyzing test dependencies...")

        dependencies = {}
        test_files = list(Path("tests/unit").rglob("test_*.py"))

        for test_file in test_files:
            file_path = str(test_file)
            deps = []

            # 读取文件内容查找import
            try:
                with open(test_file, "r") as f:
                    content = f.read()

                # 查找从其他测试模块导入
                import_pattern = r"from tests\..*?import"
                imports = re.findall(import_pattern, content)
                for imp in imports:
                    if "test_" in imp:
                        deps.append(imp)

            except Exception as e:
                print(f"Warning: Could not read {test_file}: {e}")

            if deps:
                dependencies[file_path] = deps

        return dependencies

    def suggest_fixtures(self) -> List[Dict]:
        """建议使用fixture来优化测试"""
        suggestions = []

        # 分析重复的Mock创建
        test_files = list(Path("tests/unit").rglob("test_*.py"))
        mock_patterns = defaultdict(int)

        for test_file in test_files:
            try:
                with open(test_file, "r") as f:
                    content = f.read()

                # 查找常见的Mock模式
                if "MagicMock()" in content:
                    mock_patterns["MagicMock"] += 1
                if "AsyncMock()" in content:
                    mock_patterns["AsyncMock"] += 1
                if "patch(" in content:
                    mock_patterns["patch"] += 1

            except Exception:
                pass

        # 生成建议
        for pattern, count in mock_patterns.items():
            if count > 10:
                suggestions.append(
                    {
                        "type": "fixture",
                        "pattern": pattern,
                        "usage_count": count,
                        "suggestion": f"Create a shared fixture for {pattern} to reduce duplication",
                    }
                )

        return suggestions


class TestOptimizer:
    """测试优化器"""

    def __init__(self):
        self.analyzer = TestPerformanceAnalyzer()

    def run_optimization(self, test_dir: str = "tests/unit"):
        """运行完整的优化流程"""
        print("🚀 Starting test performance optimization...\n")

        # 1. 分析慢测试
        slow_tests = self.analyzer.analyze_slow_tests(test_dir)
        print(f"\n✅ Found {len(slow_tests)} slow tests")

        # 2. 生成报告
        report = self.analyzer.generate_optimization_report()
        print("\n📋 Optimization Report:")
        print("=" * 50)

        if report["slow_tests"]:
            print("\n🐌 Top 10 Slowest Tests:")
            for i, test in enumerate(report["slow_tests"][:10], 1):
                print(f"  {i}. {test['path']}: {test['duration']:.2f}s")

        if report["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in report["recommendations"]:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                print(f"  {priority_emoji.get(rec['priority'], '⚪')} {rec['issue']}")
                print(f"     → {rec['suggestion']}")

        # 3. 建议fixture优化
        fixture_suggestions = self.analyzer.suggest_fixtures()
        if fixture_suggestions:
            print("\n🔧 Fixture Optimization Suggestions:")
            for sug in fixture_suggestions[:5]:
                print(f"  • {sug['suggestion']} (used {sug['usage_count']} times)")

        # 4. 创建并行配置
        parallel_config = self.analyzer.create_parallel_config()
        print("\n⚡ Parallel Configuration:")
        print(f"  • Max workers: {parallel_config['max_workers']}")
        print(f"  • Command: {parallel_config['cmd']}")

        # 5. 保存优化配置
        self.save_optimization_config(report, parallel_config)

        print("\n✅ Optimization analysis complete!")
        print("📄 Saved configuration to scripts/testing/test_optimization_config.json")

    def save_optimization_config(self, report: Dict, parallel_config: Dict):
        """保存优化配置"""
        config = {
            "timestamp": time.time(),
            "slow_tests": report["slow_tests"],
            "recommendations": report["recommendations"],
            "parallel_config": parallel_config,
            "optimization_applied": False,
        }

        config_path = (
            project_root / "scripts" / "testing" / "test_optimization_config.json"
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    def apply_optimizations(self):
        """应用优化建议"""
        config_path = (
            project_root / "scripts" / "testing" / "test_optimization_config.json"
        )

        if not config_path.exists():
            print("❌ No optimization configuration found. Run analysis first.")
            return

        with open(config_path, "r") as f:
            config = json.load(f)

        if config["optimization_applied"]:
            print("✅ Optimizations already applied")
            return

        print("🔧 Applying optimizations...")

        # 创建优化的pytest配置
        pytest_ini_path = project_root / "pytest.optimized.ini"
        with open(pytest_ini_path, "w") as f:
            f.write(
                """[tool:pytest]
# Optimized pytest configuration
addopts =
    --strict-markers
    --strict-config
    --tb=short
    --durations=10
    --maxfail=10
    -ra

# Parallel execution
# Use: pytest -n auto --dist=loadfile

# Test patterns
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    slow: marks tests as slow (deselect with -m "not slow")
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    smoke: marks tests as smoke tests
    regression: marks tests as regression tests

# Minimum version
minversion = 6.0

# Logging
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(name)s: %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# Warnings
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
"""
            )

        # 创建运行脚本
        run_script = project_root / "scripts" / "testing" / "run_optimized_tests.py"
        with open(run_script, "w") as f:
            f.write(
                '''#!/usr/bin/env python3
"""Optimized test runner"""


def run_tests():
    """Run tests with optimizations"""

    # Parallel execution
    cmd = [
        "python", "-m", "pytest",
        "-n", "auto",
        "--dist=loadfile",
        "--maxfail=10",
        "tests/unit/",
        "-m", "not slow"
    ]

    cmd = ["python", "-m", "pytest"]
    print("Running: " + " ".join(cmd))
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    sys.exit(run_tests())
'''
            )

        run_script.chmod(0o755)

        # 标记优化已应用
        config["optimization_applied"] = True
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        print("✅ Optimizations applied successfully!")
        print(f"📄 Created optimized pytest config: {pytest_ini_path}")
        print(f"📄 Created optimized test runner: {run_script}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test Performance Optimizer")
    parser.add_argument(
        "action", choices=["analyze", "apply", "run"], help="Action to perform"
    )
    parser.add_argument(
        "--test-dir", default="tests/unit", help="Test directory to analyze"
    )

    args = parser.parse_args()

    optimizer = TestOptimizer()

    if args.action == "analyze":
        optimizer.run_optimization(args.test_dir)
    elif args.action == "apply":
        optimizer.apply_optimizations()
    elif args.action == "run":
        # 运行优化后的测试
        config_path = project_root / "scripts" / "testing" / "run_optimized_tests.py"
        if config_path.exists():
            subprocess.run([sys.executable, str(config_path)])
        else:
            print("❌ Optimized test runner not found. Run 'apply' first.")


if __name__ == "__main__":
    main()
