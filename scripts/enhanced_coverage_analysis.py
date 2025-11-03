#!/usr/bin/env python3
"""
增强的覆盖率分析工具 - M2-P1-05
Enhanced Coverage Analysis Tool

功能:
1. 完善的覆盖率分析功能
2. 测试执行时间监控
3. 报告生成和格式化
4. GitHub Actions集成支持
"""

import json
import subprocess
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import xml.etree.ElementTree as ET
import csv


@dataclass
class TestMetrics:
    """测试指标"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    coverage_percentage: float
    total_statements: int
    covered_statements: int
    missing_statements: int


@dataclass
class ModuleCoverage:
    """模块覆盖率信息"""
    module_name: str
    coverage_percentage: float
    statements: int
    covered: int
    missing: int
    execution_time: float = 0.0


@dataclass
class CoverageReport:
    """覆盖率报告"""
    timestamp: str
    test_metrics: TestMetrics
    module_coverage: List[ModuleCoverage]
    top_uncovered_files: List[Dict[str, Any]]
    recommendations: List[str]


class EnhancedCoverageAnalyzer:
    """增强的覆盖率分析器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.coverage_file = self.project_root / "coverage.xml"
        self.htmlcov_dir = self.project_root / "htmlcov"
        self.report_file = self.project_root / "coverage_report.json"
        self.trend_file = self.project_root / "coverage_trend.json"

    def run_tests_with_coverage(self, test_pattern: str = "tests/") -> Tuple[subprocess.CompletedProcess, float]:
        """运行测试并收集覆盖率数据"""
        print("🚀 开始运行测试并收集覆盖率数据...")

        start_time = time.time()

        try:
            # 运行pytest with coverage
            cmd = [
                "python", "-m", "pytest",
                test_pattern,
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--junitxml=test_results.xml",
                "--tb=short",
                "-v"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                cwd=self.project_root
            )

            execution_time = time.time() - start_time

            print(f"✅ 测试执行完成，耗时: {execution_time:.2f}秒")
            return result, execution_time

        except subprocess.TimeoutExpired:
            print("❌ 测试执行超时")
            return None, time.time() - start_time
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            return None, time.time() - start_time

    def parse_coverage_xml(self) -> Dict[str, Any]:
        """解析coverage.xml文件"""
        if not self.coverage_file.exists():
            print("❌ coverage.xml文件不存在")
            return {}

        try:
            tree = ET.parse(self.coverage_file)
            root = tree.getroot()

            # 获取总体覆盖率
            coverage_data = {}

            # 解析总体统计
            for coverage in root.findall(".//coverage"):
                line_rate = float(coverage.get("line-rate", 0))
                branch_rate = float(coverage.get("branch-rate", 0))

                coverage_data["line_coverage"] = line_rate * 100
                coverage_data["branch_coverage"] = branch_rate * 100

            # 解析各个包/模块
            packages = root.findall(".//package")
            modules = []

            for package in packages:
                package_name = package.get("name", "")
                for classes in package.findall("classes"):
                    for cls in classes.findall("class"):
                        module_name = cls.get("name", "")
                        if module_name.startswith("src."):
                            module_name = module_name[4:]  # 移除src.前缀

                            line_rate = float(cls.get("line-rate", 0))
                            lines = int(cls.get("lines", 0))
                            covered_lines = int(lines * line_rate)
                            missing_lines = lines - covered_lines

                            modules.append({
                                "module": module_name,
                                "coverage": line_rate * 100,
                                "statements": lines,
                                "covered": covered_lines,
                                "missing": missing_lines
                            })

            coverage_data["modules"] = modules
            return coverage_data

        except Exception as e:
            print(f"❌ 解析coverage.xml失败: {e}")
            return {}

    def parse_test_results(self) -> Dict[str, Any]:
        """解析test_results.xml文件"""
        test_results_file = self.project_root / "test_results.xml"
        if not test_results_file.exists():
            print("⚠️ test_results.xml文件不存在")
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

        try:
            tree = ET.parse(test_results_file)
            root = tree.getroot()

            testsuites = root.findall("testsuite")
            total_tests = 0
            total_failures = 0
            total_errors = 0
            total_skipped = 0
            total_time = 0.0

            for testsuite in testsuites:
                total_tests += int(testsuite.get("tests", 0))
                total_failures += int(testsuite.get("failures", 0))
                total_errors += int(testsuite.get("errors", 0))
                total_skipped += int(testsuite.get("skipped", 0))
                total_time += float(testsuite.get("time", 0))

            return {
                "total": total_tests,
                "passed": total_tests - total_failures - total_errors - total_skipped,
                "failed": total_failures + total_errors,
                "skipped": total_skipped,
                "time": total_time
            }

        except Exception as e:
            print(f"❌ 解析test_results.xml失败: {e}")
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

    def generate_recommendations(self, coverage_data: Dict[str, Any]) -> List[str]:
        """生成覆盖率改进建议"""
        recommendations = []

        if not coverage_data:
            return ["无法生成建议：缺少覆盖率数据"]

        total_coverage = coverage_data.get("line_coverage", 0)
        modules = coverage_data.get("modules", [])

        # 整体覆盖率建议
        if total_coverage < 30:
            recommendations.append("🎯 整体覆盖率较低，建议优先增加基础功能的单元测试")
        elif total_coverage < 50:
            recommendations.append("📈 覆盖率接近M2目标，继续增加边缘情况测试")
        else:
            recommendations.append("🎉 覆盖率良好，可以关注集成测试和性能测试")

        # 模块覆盖率建议
        low_coverage_modules = [m for m in modules if m["coverage"] < 20]
        if low_coverage_modules:
            recommendations.append(f"⚠️ 以下模块覆盖率过低，优先处理: {', '.join([m['module'] for m in low_coverage_modules[:3]])}")

        # 未覆盖语句最多的模块
        modules_by_missing = sorted(modules, key=lambda x: x["missing"], reverse=True)
        if modules_by_missing and modules_by_missing[0]["missing"] > 50:
            top_module = modules_by_missing[0]
            recommendations.append(f"🔍 {top_module['module']} 有 {top_module['missing']} 个未覆盖语句，建议重点测试")

        return recommendations

    def generate_report(self, test_result: subprocess.CompletedProcess, execution_time: float) -> CoverageReport:
        """生成覆盖率报告"""
        # 解析覆盖率数据
        coverage_data = self.parse_coverage_xml()

        # 解析测试结果
        test_data = self.parse_test_results()

        # 计算总体统计
        total_statements = sum(m.get("statements", 0) for m in coverage_data.get("modules", []))
        total_covered = sum(m.get("covered", 0) for m in coverage_data.get("modules", []))
        total_missing = total_statements - total_covered
        total_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0

        # 创建模块覆盖率列表
        module_coverage = []
        for module_data in coverage_data.get("modules", []):
            module_coverage.append(ModuleCoverage(
                module_name=module_data["module"],
                coverage_percentage=module_data["coverage"],
                statements=module_data["statements"],
                covered=module_data["covered"],
                missing=module_data["missing"]
            ))

        # 找出未覆盖率最高的文件
        top_uncovered = sorted(
            coverage_data.get("modules", []),
            key=lambda x: x["missing"],
            reverse=True
        )[:5]

        # 生成建议
        recommendations = self.generate_recommendations(coverage_data)

        # 创建测试指标
        test_metrics = TestMetrics(
            total_tests=test_data.get("total", 0),
            passed_tests=test_data.get("passed", 0),
            failed_tests=test_data.get("failed", 0),
            skipped_tests=test_data.get("skipped", 0),
            execution_time=execution_time,
            coverage_percentage=total_coverage,
            total_statements=total_statements,
            covered_statements=total_covered,
            missing_statements=total_missing
        )

        # 创建报告
        report = CoverageReport(
            timestamp=datetime.now().isoformat(),
            test_metrics=test_metrics,
            module_coverage=module_coverage,
            top_uncovered_files=top_uncovered,
            recommendations=recommendations
        )

        return report

    def save_report(self, report: CoverageReport):
        """保存报告到文件"""
        report_data = asdict(report)

        # 保存JSON格式报告
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"📊 覆盖率报告已保存到: {self.report_file}")

    def update_trend_data(self, report: CoverageReport):
        """更新覆盖率趋势数据"""
        trend_data = []

        # 读取现有趋势数据
        if self.trend_file.exists():
            try:
                with open(self.trend_file, 'r', encoding='utf-8') as f:
                    trend_data = json.load(f)
            except Exception as e:
                print(f"⚠️ 读取趋势数据失败: {e}")
                trend_data = []

        # 添加新的数据点
        new_point = {
            "timestamp": report.timestamp,
            "coverage": report.test_metrics.coverage_percentage,
            "tests": report.test_metrics.total_tests,
            "passed": report.test_metrics.passed_tests,
            "failed": report.test_metrics.failed_tests,
            "execution_time": report.test_metrics.execution_time
        }

        trend_data.append(new_point)

        # 只保留最近30次记录
        trend_data = trend_data[-30:]

        # 保存趋势数据
        with open(self.trend_file, 'w', encoding='utf-8') as f:
            json.dump(trend_data, f, indent=2, ensure_ascii=False)

        print(f"📈 覆盖率趋势数据已更新")

    def print_summary(self, report: CoverageReport):
        """打印覆盖率摘要"""
        print("\n" + "="*60)
        print("📊 测试覆盖率报告摘要")
        print("="*60)
        print(f"📅 时间: {report.timestamp[:19]}")
        print(f"🧪 测试总数: {report.test_metrics.total_tests}")
        print(f"✅ 通过: {report.test_metrics.passed_tests}")
        print(f"❌ 失败: {report.test_metrics.failed_tests}")
        print(f"⏭️  跳过: {report.test_metrics.skipped_tests}")
        print(f"⏱️  执行时间: {report.test_metrics.execution_time:.2f}秒")
        print(f"📈 总体覆盖率: {report.test_metrics.coverage_percentage:.1f}%")
        print(f"📝 总语句数: {report.test_metrics.total_statements}")
        print(f"✅ 已覆盖: {report.test_metrics.covered_statements}")
        print(f"❌ 未覆盖: {report.test_metrics.missing_statements}")

        if report.module_coverage:
            print(f"\n📋 模块覆盖率 (Top 10):")
            sorted_modules = sorted(report.module_coverage, key=lambda x: x.coverage_percentage, reverse=True)
            for module in sorted_modules[:10]:
                status = "✅" if module.coverage_percentage >= 50 else "⚠️" if module.coverage_percentage >= 20 else "❌"
                print(f"  {status} {module.module_name:<30} {module.coverage_percentage:>5.1f}% ({module.covered}/{module.statements})")

        if report.recommendations:
            print(f"\n💡 改进建议:")
            for rec in report.recommendations:
                print(f"  {rec}")

        print("="*60)

    def generate_github_actions_output(self, report: CoverageReport):
        """生成GitHub Actions输出格式"""
        print(f"::set-output name=coverage::{report.test_metrics.coverage_percentage:.1f}")
        print(f"::set-output name=tests_total::{report.test_metrics.total_tests}")
        print(f"::set-output name=tests_passed::{report.test_metrics.passed_tests}")
        print(f"::set-output name=tests_failed::{report.test_metrics.failed_tests}")
        print(f"::set-output name=execution_time::{report.test_metrics.execution_time:.2f}")

        # 生成markdown报告
        markdown_lines = [
            f"# 📊 测试覆盖率报告",
            f"**时间**: {report.timestamp[:19]}",
            f"",
            f"## 📈 总体统计",
            f"- **覆盖率**: {report.test_metrics.coverage_percentage:.1f}%",
            f"- **测试总数**: {report.test_metrics.total_tests}",
            f"- **通过**: {report.test_metrics.passed_tests}",
            f"- **失败**: {report.test_metrics.failed_tests}",
            f"- **执行时间**: {report.test_metrics.execution_time:.2f}秒",
            f"",
            f"## 📋 模块覆盖率"
        ]

        if report.module_coverage:
            sorted_modules = sorted(report.module_coverage, key=lambda x: x.coverage_percentage, reverse=True)
            for module in sorted_modules:
                markdown_lines.append(
                    f"- **{module.module_name}**: {module.coverage_percentage:.1f}% "
                    f"({module.covered}/{module.statements})"
                )

        if report.recommendations:
            markdown_lines.extend([
                f"",
                f"## 💡 改进建议"
            ])
            for rec in report.recommendations:
                markdown_lines.append(f"- {rec}")

        # 保存markdown报告
        markdown_report = "\n".join(markdown_lines)
        with open(self.project_root / "coverage_report.md", 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        print("📝 Markdown报告已生成: coverage_report.md")

    def analyze(self, test_pattern: str = "tests/", github_actions: bool = False) -> bool:
        """执行完整的覆盖率分析"""
        print("🚀 开始增强的覆盖率分析...")

        # 运行测试
        test_result, execution_time = self.run_tests_with_coverage(test_pattern)

        if test_result is None:
            print("❌ 测试执行失败")
            return False

        if test_result.returncode != 0:
            print(f"⚠️ 测试有失败，但继续分析覆盖率...")
            print(f"测试输出: {test_result.stderr}")

        # 生成报告
        report = self.generate_report(test_result, execution_time)

        # 保存报告
        self.save_report(report)

        # 更新趋势数据
        self.update_trend_data(report)

        # 打印摘要
        self.print_summary(report)

        # 生成GitHub Actions输出
        if github_actions:
            self.generate_github_actions_output(report)

        # 检查是否达到目标
        target_coverage = 50.0  # M2目标
        current_coverage = report.test_metrics.coverage_percentage

        if current_coverage >= target_coverage:
            print(f"🎉 恭喜！已达到M2目标覆盖率 {target_coverage}% (当前: {current_coverage:.1f}%)")
            return True
        else:
            remaining = target_coverage - current_coverage
            print(f"📈 距离M2目标还差 {remaining:.1f}% (当前: {current_coverage:.1f}%, 目标: {target_coverage}%)")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="增强的覆盖率分析工具")
    parser.add_argument("--test-pattern", default="tests/", help="测试模式 (默认: tests/)")
    parser.add_argument("--github-actions", action="store_true", help="GitHub Actions模式")
    parser.add_argument("--test", action="store_true", help="测试模式")

    args = parser.parse_args()

    if args.test:
        print("🧪 测试模式：验证工具链功能")
        # 创建一个临时测试文件来验证工具链
        test_project = Path(__file__).parent.parent
        analyzer = EnhancedCoverageAnalyzer(test_project)

        # 检查必要的文件
        if not (test_project / "pyproject.toml").exists():
            print("❌ pyproject.toml文件不存在")
            return False

        if not (test_project / "pytest.ini").exists():
            print("❌ pytest.ini文件不存在")
            return False

        print("✅ 项目配置文件检查通过")
        print("✅ 测试工具链验证完成")
        return True

    # 创建分析器
    analyzer = EnhancedCoverageAnalyzer()

    # 执行分析
    success = analyzer.analyze(args.test_pattern, args.github_actions)

    # 返回结果
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()