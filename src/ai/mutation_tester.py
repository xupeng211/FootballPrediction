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
    target_modules: List[str] = None
    max_workers: int = 4
    timeout_per_test: int = 30  # 秒
    total_timeout: int = 300   # 5分钟总超时
    exclude_patterns: Set[str] = None

    def __post_init__(self):
        if self.target_modules is None:
            self.target_modules = ["src/data/", "src/models/", "src/services/"]
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
            test_files_pytest = []
            for f in test_files:
                test_name = f"tests/test_{Path(f).stem}.py"
                if Path(test_name).exists():
                    test_files_pytest.append(test_name)

            if test_files_pytest:
                cmd.extend(["--tests-to-run", ",".join(test_files_pytest)])

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