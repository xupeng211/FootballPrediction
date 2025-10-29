#!/usr/bin/env python3
"""
质量守护检查器
Quality Guardian Checker

确保代码质量基线不被破坏，防止覆盖率回退
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


class QualityGuardian:
    """质量守护检查器"""

    def __init__(self, baseline_file: str = "config/quality_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.baseline = self._load_baseline()
        self.current_metrics = {}

    def _load_baseline(self) -> Dict:
        """加载质量基线"""
        try:
            with open(self.baseline_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 质量基线文件不存在: {self.baseline_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ 质量基线文件格式错误: {e}")
            sys.exit(1)

    def _run_command(self, command: List[str]) -> str:
        """执行命令并返回输出"""
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            return result.stdout
        except subprocess.TimeoutExpired:
            print(f"❌ 命令执行超时: {' '.join(command)}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 命令执行失败: {e}")
            sys.exit(1)

    def _parse_coverage_output(self, coverage_output: str) -> Dict:
        """解析覆盖率输出"""
        metrics = {}
        lines = coverage_output.split("\n")

        # 查找覆盖率报告部分
        coverage_section = False
        for line in lines:
            if "coverage: platform linux" in line:
                coverage_section = True
                continue

            if not coverage_section:
                continue

            # 解析TOTAL行
            if "TOTAL" in line:
                parts = line.split()
                # 查找包含百分比的最后一个字段
                for part in reversed(parts):
                    if part.endswith("%"):
                        try:
                            coverage = float(part.rstrip("%"))
                            metrics["total_coverage"] = coverage
                            break
                        except ValueError:
                            continue
                break

        # 解析模块覆盖率 - 查找所有包含src的行
        domain_coverage = None
        utils_coverage = None

        for line in lines:
            if "src/domain/" in line and "%" in line:
                parts = line.split()
                for part in reversed(parts):
                    if part.endswith("%"):
                        try:
                            domain_coverage = float(part.rstrip("%"))
                            break
                        except ValueError:
                            continue

            if "src/utils/" in line and "%" in line:
                parts = line.split()
                for part in reversed(parts):
                    if part.endswith("%"):
                        try:
                            utils_coverage = float(part.rstrip("%"))
                            break
                        except ValueError:
                            continue

        if domain_coverage is not None:
            metrics["domain_coverage"] = domain_coverage
        if utils_coverage is not None:
            metrics["utils_coverage"] = utils_coverage

        return metrics

    def _check_test_results(self, test_output: str) -> Dict:
        """检查测试结果"""
        metrics = {}
        lines = test_output.split("\n")

        for line in lines:
            # 查找包含测试结果的行
            if "=" in line and "passed" in line:
                # 解析类似 "============= 264 passed in 0.70s =============" 的输出
                if "passed" in line and ("failed" in line or "passed" in line):
                    # 提取passed数量
                    import re

                    match = re.search(r"(\d+)\s+passed", line)
                    if match:
                        passed = int(match.group(1))

                        # 查找failed数量
                        failed = 0
                        failed_match = re.search(r"(\d+)\s+failed", line)
                        if failed_match:
                            failed = int(failed_match.group(1))

                        total = passed + failed
                        if total > 0:
                            metrics["total_tests"] = total
                            metrics["passed_tests"] = passed
                            metrics["pass_rate"] = (passed / total) * 100
                            break

        return metrics

    def run_quality_checks(self) -> bool:
        """运行质量检查"""
        print("🛡️ 质量守护检查开始...")
        print(f"📊 基线覆盖率: {self.baseline['baseline']['total_coverage']:.2f}%")
        print(f"🎯 最低要求: {self.baseline['quality_gates']['minimum_total_coverage']:.2f}%")

        # 运行测试和覆盖率检查
        print("\n🧪 运行测试套件...")
        test_command = [
            "python",
            "-m",
            "pytest",
            "-v",
            "test_domain_league_comprehensive.py",
            "test_domain_match_comprehensive.py",
            "test_domain_prediction_comprehensive.py",
            "test_domain_team_comprehensive.py",
            "tests/unit/utils/test_crypto_utils.py",
            "tests/unit/utils/test_date_utils.py",
            "tests/unit/utils/test_file_utils.py",
            "tests/unit/utils/test_i18n.py",
            "tests/unit/utils/test_warning_filters.py",
            "--cov=src",
            "--cov-report=term-missing",
            "--tb=short",
        ]

        output = self._run_command(test_command)

        # 调试：保存输出到文件
        with open("debug_output.log", "w", encoding="utf-8") as f:
            f.write(output)
        print("📝 测试输出已保存到 debug_output.log")

        # 解析结果
        self.current_metrics.update(self._parse_coverage_output(output))
        self.current_metrics.update(self._check_test_results(output))

        # 调试：显示解析结果
        print(f"🔍 解析到的指标: {self.current_metrics}")

        # 质量门禁检查
        return self._check_quality_gates()

    def _check_quality_gates(self) -> bool:
        """检查质量门禁"""
        print("\n🚪 质量门禁检查:")

        gates = self.baseline["quality_gates"]
        all_passed = True

        # 检查总覆盖率
        total_cov = self.current_metrics.get("total_coverage", 0)
        min_total = gates["minimum_total_coverage"]

        if total_cov >= min_total:
            print(f"✅ 总覆盖率: {total_cov:.2f}% >= {min_total:.2f}%")
        else:
            print(f"❌ 总覆盖率: {total_cov:.2f}% < {min_total:.2f}%")
            all_passed = False

        # 检查测试通过率
        pass_rate = self.current_metrics.get("pass_rate", 0)
        min_pass_rate = gates["minimum_pass_rate"]

        if pass_rate >= min_pass_rate:
            print(f"✅ 测试通过率: {pass_rate:.1f}% >= {min_pass_rate:.1f}%")
        else:
            print(f"❌ 测试通过率: {pass_rate:.1f}% < {min_pass_rate:.1f}%")
            all_passed = False

        # 检查覆盖率回退
        baseline_cov = self.baseline["baseline"]["total_coverage"]
        max_regression = gates["maximum_regression"]

        regression = baseline_cov - total_cov
        if regression <= max_regression:
            print(f"✅ 覆盖率回退: {regression:.2f}% <= {max_regression:.2f}%")
        else:
            print(f"❌ 覆盖率回退: {regression:.2f}% > {max_regression:.2f}%")
            all_passed = False

        return all_passed

    def generate_report(self) -> str:
        """生成质量报告"""
        report = []
        report.append("📊 质量检查报告")
        report.append("=" * 50)
        report.append(f"📈 当前覆盖率: {self.current_metrics.get('total_coverage', 0):.2f}%")
        report.append(f"🎯 基线覆盖率: {self.baseline['baseline']['total_coverage']:.2f}%")
        report.append(f"📝 测试数量: {self.current_metrics.get('total_tests', 0)}")
        report.append(f"✅ 通过率: {self.current_metrics.get('pass_rate', 0):.1f}%")

        return "\n".join(report)


def main():
    """主函数"""
    guardian = QualityGuardian()

    try:
        quality_passed = guardian.run_quality_checks()

        print("\n" + "=" * 50)
        print(guardian.generate_report())

        if quality_passed:
            print("\n🎉 质量检查通过！代码质量达标。")
            sys.exit(0)
        else:
            print("\n❌ 质量检查失败！请修复问题后重试。")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 质量检查被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 质量检查出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
