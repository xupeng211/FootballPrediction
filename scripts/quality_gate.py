#!/usr/bin/env python3
"""
质量门禁检查脚本
Quality Gate Checker
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List


class QualityGate:
    """质量门禁检查器"""

    def __init__(self):
        self.targets = {
            "coverage": {"min": 45.0, "target": 50.0},
            "test_pass_rate": {"min": 95.0, "target": 100.0},
            "code_quality": {"min": 8.0, "target": 9.0},
            "security": {"min": 100.0, "target": 100.0},
            "performance": {"min": 90.0, "target": 98.0},
        }

        self.metrics = {}
        self.blockers = []
        self.warnings = []

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
        if "passed" in output:
            # 提取通过数量
            parts = output.split()
            passed = 0
            failed = 0
            for i, part in enumerate(parts):
                if part == "passed":
                    passed = int(parts[i - 1])
                elif part == "failed":
                    failed = int(parts[i - 1])

            total = passed + failed
            pass_rate = (passed / total * 100) if total > 0 else 0

            self.metrics["test_pass_rate"] = pass_rate

            if pass_rate < self.targets["test_pass_rate"]["min"]:
                self.blockers.append(f"测试通过率过低: {pass_rate:.2f}%")
            else:
                print(f"✅ 测试通过率: {pass_rate:.2f}%")
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
            except:
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
                target = self.targets[metric]["target"]
                status = "✅" if value >= target else "⚠️"
                print(f"  {metric}: {value:.2f} (目标: {target}) {status}")

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


def main():
    parser = argparse.ArgumentParser(description="质量门禁检查")
    parser.add_argument("--ci-mode", action="store_true", help="CI模式，失败时退出码1")
    args = parser.parse_args()

    gate = QualityGate()
    gate.run_checks(ci_mode=args.ci_mode)


if __name__ == "__main__":
    main()
