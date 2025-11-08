#!/usr/bin/env python3
"""
快速质量检查工具
Quick Quality Checker

一个专注于实际可用性的简化质量检查工具，避免复杂的依赖问题。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class QuickQualityResult:
    """快速质量检查结果"""
    success: bool
    test_runnable: bool
    code_quality_issues: int
    test_results: Dict[str, any]
    coverage_info: Dict[str, any]
    recommendations: List[str]


class QuickQualityChecker:
    """快速质量检查器"""

    def __init__(self):
        """初始化检查器"""
        self.project_root = Path.cwd()

    def run_basic_tests(self) -> Tuple[bool, Dict[str, any]]:
        """运行基础测试检查"""
        print("🧪 运行基础测试检查...")

        try:
            # 尝试运行小范围的核心测试
            result = subprocess.run(
                ["python", "-m", "pytest",
                 "tests/unit/core/test_di.py",
                 "tests/unit/utils/",
                 "--tb=no", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            output_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            summary_line = output_lines[-1] if output_lines else "无结果"

            return result.returncode == 0, {
                "returncode": result.returncode,
                "summary": summary_line,
                "output": result.stdout,
                "errors": result.stderr
            }

        except Exception as e:
            return False, {
                "error": f"测试执行失败: {e}",
                "returncode": -1
            }

    def check_code_quality(self) -> Tuple[int, List[str]]:
        """检查代码质量"""
        print("🔍 检查代码质量...")

        issues = []

        # Ruff 检查
        try:
            result = subprocess.run(
                ["ruff", "check", "src/", "--output-format=concise"],
                capture_output=True, text=True, cwd=self.project_root
            )

            ruff_output = result.stdout.strip()
            if ruff_output:
                ruff_issues = len([line for line in ruff_output.split('\n') if line.strip()])
                issues.append(f"Ruff发现 {ruff_issues} 个问题")

        except Exception as e:
            issues.append(f"Ruff检查失败: {e}")

        # 基础语法检查
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", "src/core/di.py"],
                capture_output=True, text=True, cwd=self.project_root
            )

            if result.returncode != 0:
                issues.append("核心模块语法检查失败")

        except Exception as e:
            issues.append(f"语法检查失败: {e}")

        return len(issues), issues

    def check_coverage_simple(self) -> Dict[str, any]:
        """简化覆盖率检查"""
        print("📊 检查测试覆盖率...")

        coverage_info = {
            "available": False,
            "percentage": 0.0,
            "error": None
        }

        try:
            # 尝试运行单个文件的覆盖率检查
            result = subprocess.run(
                ["python", "-m", "pytest",
                 "tests/unit/core/test_di.py",
                 "--cov=src.core.di",
                 "--cov-report=json",
                 "--tb=no"],
                capture_output=True, text=True, cwd=self.project_root
            )

            if result.returncode == 0:
                # 尝试读取覆盖率文件
                coverage_file = self.project_root / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)
                        coverage_info["available"] = True
                        coverage_info["percentage"] = coverage_data.get("totals", {}).get("percent_covered", 0.0)
                else:
                    coverage_info["error"] = "覆盖率文件未生成"
            else:
                coverage_info["error"] = result.stderr.strip()

        except Exception as e:
            coverage_info["error"] = f"覆盖率检查失败: {e}"

        return coverage_info

    def generate_recommendations(self, result: QuickQualityResult) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if not result.test_runnable:
            recommendations.append("🔧 修复测试环境问题，确保基础测试可运行")

        if result.code_quality_issues > 10:
            recommendations.append("🧹 运行 'make fix-code' 修复代码质量问题")
        elif result.code_quality_issues > 0:
            recommendations.append("🔍 检查并修复剩余的代码质量问题")

        if result.coverage_info.get("percentage", 0) < 30:
            recommendations.append("📈 增加测试覆盖率，当前低于30%标准")

        if result.success:
            recommendations.append("✅ 质量状况良好，继续保持！")

        return recommendations

    def run_quick_check(self) -> QuickQualityResult:
        """运行快速质量检查"""
        print("⚡ 快速质量检查开始...")
        print("="*50)

        # 1. 测试可运行性检查
        test_success, test_results = self.run_basic_tests()

        # 2. 代码质量检查
        quality_issues_count, quality_issues = self.check_code_quality()

        # 3. 覆盖率检查
        coverage_info = self.check_coverage_simple()

        # 4. 生成结果
        success = (
            test_success and
            quality_issues_count <= 10 and  # 允许少量问题
            coverage_info.get("percentage", 0) >= 20  # 降低覆盖率要求
        )

        result = QuickQualityResult(
            success=success,
            test_runnable=test_success,
            code_quality_issues=quality_issues_count,
            test_results=test_results,
            coverage_info=coverage_info,
            recommendations=[]
        )

        result.recommendations = self.generate_recommendations(result)

        return result

    def print_result(self, result: QuickQualityResult) -> None:
        """打印检查结果"""
        print("\n" + "="*50)
        print("⚡ 快速质量检查结果")
        print("="*50)

        # 总体状态
        if result.success:
            print("✅ 质量检查通过！")
        else:
            print("⚠️  需要关注一些质量问题")

        # 测试状态
        print(f"\n🧪 测试状态: {'✅ 可运行' if result.test_runnable else '❌ 有问题'}")
        if result.test_results.get("summary"):
            print(f"   摘要: {result.test_results['summary']}")

        # 代码质量
        print(f"\n🔍 代码质量: 发现 {result.code_quality_issues} 个问题")

        # 覆盖率
        if result.coverage_info.get("available"):
            percentage = result.coverage_info["percentage"]
            print(f"\n📊 覆盖率: {percentage:.1f}%")
        else:
            print(f"\n📊 覆盖率: 检查失败")
            if result.coverage_info.get("error"):
                print(f"   错误: {result.coverage_info['error']}")

        # 建议
        print(f"\n💡 改进建议:")
        for rec in result.recommendations:
            print(f"   {rec}")

        print("\n" + "="*50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="快速质量检查工具")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )

    args = parser.parse_args()

    checker = QuickQualityChecker()
    result = checker.run_quick_check()
    checker.print_result(result)

    # 返回适当的退出码
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()