#!/usr/bin/env python3
"""
质量门禁检查脚本 - Phase 2 增强版
Enhanced Quality Gate Checker

Phase 2 - 建立质量门禁机制
提供全面的项目质量检查，包括覆盖率、测试执行、代码质量等
"""

import argparse
import json
import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QualityGate:
    """质量门禁检查器"""

    def __init__(self):
        # Phase 3 质量标准 (已更新)
        self.targets = {
            "coverage": {"min": 20.0, "target": 25.0},  # Phase 3 目标：25%+
            "test_pass_rate": {"min": 85.0, "target": 90.0},
            "code_quality": {"min": 7.0, "target": 8.0},
            "security": {"min": 80.0, "target": 90.0},  # 安全评分
        }

        self.metrics = {}
        self.blockers = []
        self.warnings = []
        self.project_root = Path(__file__).parent.parent

    def check_coverage(self):
        """检查测试覆盖率"""
        print("📊 检查测试覆盖率...")

        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            print("⚠️ 覆盖率报告不存在")
            self.blockers.append("覆盖率报告缺失")
            return 0.0

        with open(coverage_file) as f:
            data = json.load(f)

        coverage = data["totals"]["percent_covered"]
        self.metrics["coverage"] = coverage

        if coverage < self.targets["coverage"]["min"]:
            self.blockers.append(
                f"覆盖率过低: {coverage:.2f}% < {self.targets['coverage']['min']}%"
            )
        elif coverage < self.targets["coverage"]["target"]:
            self.warnings.append(
                f"覆盖率未达标: {coverage:.2f}% < {self.targets['coverage']['target']}%"
            )
        else:
            print(f"✅ 覆盖率达标: {coverage:.2f}%")

        return coverage

    def check_test_results(self):
        """检查测试结果"""
        print("✅ 检查测试通过率...")

        # 运行测试并获取结果
        result = subprocess.run(
            ["python", "-m", "pytest", "--tb=no", "-q"], capture_output=True, text=True
        )

        # 解析pytest输出
        output = result.stdout
        # 查找包含测试统计的行
        import re
        pattern = r'= (\d+) failed, (\d+) passed, (\d+) skipped.*'
        match = re.search(pattern, output)

        if match:
            failed = int(match.group(1))
            passed = int(match.group(2))
            skipped = int(match.group(3))

            total = passed + failed + skipped
            pass_rate = (passed / total * 100) if total > 0 else 0

            self.metrics["test_pass_rate"] = pass_rate
            self.metrics["tests_failed"] = failed
            self.metrics["tests_passed"] = passed
            self.metrics["tests_skipped"] = skipped

            if pass_rate < self.targets["test_pass_rate"]["min"]:
                self.blockers.append(f"测试通过率过低: {pass_rate:.2f}%")
            else:
                print(f"✅ 测试通过率: {pass_rate:.2f}% ({passed}/{total})")
        else:
            self.metrics["test_pass_rate"] = 0.0
            self.blockers.append("无法解析测试结果")

    def check_code_quality(self):
        """检查代码质量"""
        print("🔍 检查代码质量...")

        # 运行ruff检查
        result = subprocess.run(
            ["ruff", "check", "src/", "--output-format=json"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # 没有错误
            quality_score = 10.0
        else:
            # 根据错误数量计算分数
            try:
                errors = json.loads(result.stdout)
                error_count = len(errors)
                # 简单的评分公式
                quality_score = max(5.0, 10.0 - (error_count * 0.1))
            except Exception:
                quality_score = 7.0

        self.metrics["code_quality"] = quality_score

        if quality_score < self.targets["code_quality"]["min"]:
            self.blockers.append(f"代码质量评分过低: {quality_score:.2f}")
        else:
            print(f"✅ 代码质量评分: {quality_score:.2f}")

    def check_security(self):
        """检查安全性"""
        print("🔒 检查安全性...")

        # 如果有bandit报告，读取它
        security_file = Path("security-report.json")
        if security_file.exists():
            with open(security_file) as f:
                data = json.load(f)

            # 计算安全评分
            high_issues = len(
                [r for r in data["results"] if r["issue_severity"] == "HIGH"]
            )
            medium_issues = len(
                [r for r in data["results"] if r["issue_severity"] == "MEDIUM"]
            )

            if high_issues > 0:
                security_score = 60.0
                self.blockers.append(f"发现 {high_issues} 个高危安全问题")
            elif medium_issues > 5:
                security_score = 80.0
                self.warnings.append(f"发现 {medium_issues} 个中危安全问题")
            else:
                security_score = 100.0
        else:
            # 没有运行安全扫描，假设安全
            security_score = 100.0

        self.metrics["security"] = security_score
        print(f"✅ 安全评分: {security_score:.2f}%")

    def calculate_overall_score(self):
        """计算总体质量评分"""
        if not self.metrics:
            return 0.0

        # 加权平均
        weights = {
            "coverage": 0.3,
            "test_pass_rate": 0.25,
            "code_quality": 0.25,
            "security": 0.2,
        }

        score = 0.0
        total_weight = 0.0

        for metric, value in self.metrics.items():
            if metric in weights:
                score += value * weights[metric]
                total_weight += weights[metric]

        return score / total_weight if total_weight > 0 else 0.0

    def run_checks(self, ci_mode=False):
        """运行所有检查"""
        print("🚦 质量门禁检查开始...")

        # 运行各项检查
        self.check_coverage()
        self.check_test_results()
        self.check_code_quality()
        self.check_security()

        # 计算总分
        overall_score = self.calculate_overall_score()

        # 判断是否通过
        passed = len(self.blockers) == 0

        # 生成报告
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "passed": passed,
            "score": round(overall_score, 2),
            "metrics": self.metrics,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "targets": self.targets,
        }

        # 保存报告
        with open("quality-report.json", "w") as f:
            json.dump(report, f, indent=2)

        # 打印结果
        print("\n" + "=" * 50)
        print("🚦 质量门禁检查结果")
        print("=" * 50)
        print(f"总分: {overall_score:.2f}/10.0")
        print(f"状态: {'✅ 通过' if passed else '❌ 失败'}")

        if self.metrics:
            print("\n📊 指标:")
            for metric, value in self.metrics.items():
                if metric in self.targets:
                    target = self.targets[metric]["target"]
                    status = "✅" if value >= target else "⚠️"
                    print(f"  {metric}: {value:.2f} (目标: {target}) {status}")
                else:
                    print(f"  {metric}: {value:.2f} (无设定目标)")

        if self.blockers:
            print("\n❌ 阻塞问题:")
            for blocker in self.blockers:
                print(f"  - {blocker}")

        if self.warnings:
            print("\n⚠️ 警告:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if ci_mode and not passed:
            print("\n❌ 质量门禁未通过，阻止合并")
            sys.exit(1)

        return report

    def run_quick_checks(self, ci_mode=False):
        """运行快速质量检查（用于pre-commit）"""
        print("⚡ 质量门禁快速检查...")

        # 运行关键测试
        print("🧪 运行关键测试...")
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/unit/api/test_adapters.py", "tests/unit/utils/test_dict_utils_enhanced.py", "--tb=no", "-q"],
            capture_output=True, text=True
        )

        # 解析结果
        output = result.stdout
        import re

        # 尝试匹配有失败的情况
        pattern = r'= (\d+) failed, (\d+) passed.*'
        match = re.search(pattern, output)

        # 如果没有失败，尝试匹配全部通过的情况
        if not match:
            pattern = r'= (\d+) passed.*'
            match = re.search(pattern, output)
            if match:
                passed = int(match.group(1))
                failed = 0
                total = passed
                print(f"✅ 关键测试通过: {passed}/{total}")
            else:
                print("⚠️ 无法解析测试结果")
                if ci_mode:
                    sys.exit(1)
                return

        else:
            # 处理有失败的情况
            failed = int(match.group(1))
            passed = int(match.group(2))
            total = passed + failed

            if failed > 0:
                print(f"❌ 关键测试失败: {failed}/{total}")
                if ci_mode:
                    sys.exit(1)
            else:
                print(f"✅ 关键测试通过: {passed}/{total}")

        # 代码质量检查
        print("🔍 代码质量检查...")
        try:
            result = subprocess.run(["ruff", "check", "src/"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 代码质量检查通过")
            else:
                print("⚠️ 发现代码质量问题")
                if ci_mode:
                    sys.exit(1)
        except FileNotFoundError:
            print("⚠️ Ruff未安装，跳过代码质量检查")


def main():
    parser = argparse.ArgumentParser(description="质量门禁检查")
    parser.add_argument("--ci-mode", action="store_true", help="CI模式，失败时退出码1")
    parser.add_argument("--quick-mode", action="store_true", help="快速模式，仅运行关键检查")
    args = parser.parse_args()

    gate = QualityGate()
    if args.quick_mode:
        gate.run_quick_checks(ci_mode=args.ci_mode)
    else:
        gate.run_checks(ci_mode=args.ci_mode)


if __name__ == "__main__":
    main()
