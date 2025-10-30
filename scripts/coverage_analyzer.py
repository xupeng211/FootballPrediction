#!/usr/bin/env python3
"""
覆盖率精细化分析和优化工具
Phase E: 优化提升阶段 - 专门的覆盖率分析工具
"""

import subprocess
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse


class CoverageAnalyzer:
    """覆盖率分析器"""

    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.coverage_file = self.project_root / ".coverage_report.json"

    def analyze_phase_e_tests(self):
        """分析Phase E测试覆盖率"""
        print("🔍 Phase E 测试覆盖率分析")
        print("=" * 50)

        # 定义Phase E测试文件
        phase_e_tests = [
            "tests/unit/domain/test_advanced_business_logic.py",
            "tests/unit/edge_cases/test_boundary_and_exception_handling.py",
            "tests/unit/performance/test_advanced_performance.py"
        ]

        total_test_cases = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0

        for test_file in phase_e_tests:
            if not self.project_root.joinpath(test_file).exists():
                print(f"❌ 测试文件不存在: {test_file}")
                continue

            print(f"\n📊 分析测试文件: {test_file}")

            # 运行测试并收集统计信息
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    test_file, "--tb=short", "-v"
                ], capture_output=True, text=True, cwd=self.project_root)

                # 解析测试结果
                output = result.stdout
                test_stats = self._parse_test_output(output)

                total_test_cases += test_stats.get("total", 0)
                total_passed += test_stats.get("passed", 0)
                total_failed += test_stats.get("failed", 0)
                total_skipped += test_stats.get("skipped", 0)

                print(f"  ✅ 通过: {test_stats.get('passed', 0)}")
                print(f"  ❌ 失败: {test_stats.get('failed', 0)}")
                print(f"  ⏭️  跳过: {test_stats.get('skipped', 0)}")
                print(f"  📊 总计: {test_stats.get('total', 0)}")

                # 显示最慢的测试
                slow_tests = self._extract_slow_tests(output)
                if slow_tests:
                    print("  🐌 最慢的测试:")
                    for test, duration in slow_tests[:3]:
                        print(f"    - {test}: {duration:.2f}s")

            except Exception as e:
                print(f"  ❌ 分析失败: {e}")

        # 汇总统计
        print("\n📈 Phase E 测试汇总统计:")
        print(f"  🧪 总测试用例: {total_test_cases}")
        print(f"  ✅ 通过: {total_passed} ({total_passed/total_test_cases*100:.1f}%)" if total_test_cases > 0 else "  ✅ 通过: 0")
        print(f"  ❌ 失败: {total_failed} ({total_failed/total_test_cases*100:.1f}%)" if total_test_cases > 0 else "  ❌ 失败: 0")
        print(f"  ⏭️  跳过: {total_skipped} ({total_skipped/total_test_cases*100:.1f}%)" if total_test_cases > 0 else "  ⏭️  跳过: 0")

        success_rate = total_passed / total_test_cases if total_test_cases > 0 else 0
        print(f"  🎯 成功率: {success_rate:.1%}")

        return {
            "total_tests": total_test_cases,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "success_rate": success_rate
        }

    def _parse_test_output(self, output):
        """解析pytest输出"""
        # 尝试从输出中提取测试统计信息
        lines = output.split('\n')

        total = 0
        passed = 0
        failed = 0
        skipped = 0

        for line in lines:
            # 查找包含测试统计的行
            if "passed" in line and ("failed" in line or "error" in line):
                # 示例: "19 passed, 15 skipped, 5 failed in 40.70s"
                parts = line.split()

                for i, part in enumerate(parts):
                    if part.isdigit() and i + 1 < len(parts):
                        if parts[i+1] == "passed":
                            passed = int(part)
                        elif parts[i+1] == "failed":
                            failed = int(part)
                        elif parts[i+1] == "skipped":
                            skipped = int(part)
                        elif parts[i+1] == "error":
                            failed += int(part)

                total = passed + failed + skipped
                break

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped
        }

    def _extract_slow_tests(self, output):
        """提取最慢的测试"""
        slow_tests = []

        # 查找 "slowest 10 durations" 部分
        if "slowest" in output and "durations" in output:
            lines = output.split('\n')
            slow_section = False

            for line in lines:
                if "slowest" in line and "durations" in line:
                    slow_section = True
                    continue

                if slow_section:
                    if line.strip() == "":
                        break

                    # 解析慢测试行: "0.76s call     tests/..."
                    match = re.match(r'([\d.]+)s\s+call\s+(.+)', line.strip())
                    if match:
                        duration = float(match.group(1))
                        test_name = match.group(2)
                        slow_tests.append((test_name, duration))

        return slow_tests

    def analyze_coverage_by_module(self):
        """按模块分析覆盖率"""
        print("\n🔍 按模块覆盖率分析")
        print("=" * 50)

        # 定义要分析的关键模块
        key_modules = [
            "src/domain",
            "src/api",
            "src/cache",
            "src/database",
            "src/utils",
            "src/services"
        ]

        module_coverage = {}

        for module in key_modules:
            module_path = self.project_root / module
            if not module_path.exists():
                print(f"❌ 模块不存在: {module}")
                continue

            print(f"\n📊 分析模块: {module}")

            try:
                # 尝试获取该模块的覆盖率
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    f"--cov={module}",
                    "--cov-report=term-missing",
                    "--tb=short",
                    "-q",
                    f"tests/unit/{module.split('/')[-1]}/"
                ], capture_output=True, text=True, cwd=self.project_root)

                # 解析覆盖率结果
                coverage_percent = self._extract_coverage_percent(result.stdout)
                module_coverage[module] = coverage_percent

                print(f"  📈 覆盖率: {coverage_percent:.1f}%")

                # 提取未覆盖的文件
                uncovered_files = self._extract_uncovered_files(result.stdout)
                if uncovered_files:
                    print(f"  📋 未覆盖文件 ({len(uncovered_files)}):")
                    for file in uncovered_files[:3]:  # 只显示前3个
                        print(f"    - {file}")

            except Exception as e:
                print(f"  ❌ 分析失败: {e}")
                module_coverage[module] = 0

        return module_coverage

    def _extract_coverage_percent(self, output):
        """提取覆盖率百分比"""
        # 查找类似 "TOTAL      100  50  50%" 的行
        lines = output.split('\n')

        for line in lines:
            if "TOTAL" in line and "%" in line:
                parts = line.split()
                for part in parts:
                    if part.endswith('%'):
                        try:
                            return float(part.rstrip('%'))
                        except ValueError:
                            continue

        return 0

    def _extract_uncovered_files(self, output):
        """提取未覆盖的文件"""
        uncovered_files = []
        lines = output.split('\n')

        for line in lines:
            # 查找未覆盖的文件行 (通常有 "missing" 字段)
            if "missing" in line and "src/" in line:
                parts = line.split()
                if parts and "src/" in parts[0]:
                    uncovered_files.append(parts[0])

        return uncovered_files

    def generate_optimization_recommendations(self, test_stats, module_coverage):
        """生成优化建议"""
        print("\n💡 覆盖率优化建议")
        print("=" * 50)

        recommendations = []

        # 基于测试统计的建议
        if test_stats["success_rate"] < 0.8:
            recommendations.append({
                "priority": "HIGH",
                "area": "测试稳定性",
                "suggestion": f"测试成功率仅{test_stats['success_rate']:.1%}，建议修复失败的测试用例"
            })

        if test_stats["failed"] > 0:
            recommendations.append({
                "priority": "HIGH",
                "area": "测试修复",
                "suggestion": f"有{test_stats['failed']}个失败测试，优先修复这些测试以提升覆盖率"
            })

        if test_stats["skipped"] > test_stats["passed"]:
            recommendations.append({
                "priority": "MEDIUM",
                "area": "依赖管理",
                "suggestion": f"跳过的测试({test_stats['skipped']})多于通过的测试，检查模块依赖和环境配置"
            })

        # 基于模块覆盖率的建议
        low_coverage_modules = [(mod, cov) for mod, cov in module_coverage.items() if cov < 10]
        if low_coverage_modules:
            recommendations.append({
                "priority": "HIGH",
                "area": "模块覆盖",
                "suggestion": f"以下模块覆盖率过低: {', '.join([f'{m}({c:.1f}%)' for m, c in low_coverage_modules])}，需要重点补充测试"
            })

        # 基于Phase E特性的建议
        phase_e_coverage_suggestions = [
            {
                "priority": "MEDIUM",
                "area": "边界条件测试",
                "suggestion": "增加更多极值和边界条件测试，确保系统在各种极端情况下的稳定性"
            },
            {
                "priority": "MEDIUM",
                "area": "异常处理测试",
                "suggestion": "补充异常处理和错误恢复场景的测试，提升系统的健壮性"
            },
            {
                "priority": "LOW",
                "area": "性能测试",
                "suggestion": "添加更多性能基准测试，监控系统在不同负载下的表现"
            }
        ]

        recommendations.extend(phase_e_coverage_suggestions)

        # 显示建议
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {
                "HIGH": "🔴",
                "MEDIUM": "🟡",
                "LOW": "🟢"
            }

            print(f"\n{i}. {priority_emoji.get(rec['priority'], '⚪')} {rec['area']}")
            print(f"   💡 {rec['suggestion']}")

        return recommendations

    def create_coverage_report(self):
        """创建完整的覆盖率报告"""
        print("📋 生成Phase E覆盖率报告")
        print("=" * 60)

        # 分析测试统计
        test_stats = self.analyze_phase_e_tests()

        # 分析模块覆盖率
        module_coverage = self.analyze_coverage_by_module()

        # 生成优化建议
        recommendations = self.generate_optimization_recommendations(test_stats, module_coverage)

        # 创建报告文件
        report = {
            "timestamp": datetime.now().isoformat(),
            "phase": "E - 优化提升阶段",
            "test_statistics": test_stats,
            "module_coverage": module_coverage,
            "recommendations": recommendations,
            "summary": {
                "total_test_files": 3,
                "total_test_cases": test_stats.get("total_tests", 0),
                "success_rate": test_stats.get("success_rate", 0),
                "average_module_coverage": sum(module_coverage.values()) / len(module_coverage) if module_coverage else 0,
                "recommendations_count": len(recommendations)
            }
        }

        # 保存报告
        report_file = self.project_root / "phase_e_coverage_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 报告已保存到: {report_file}")

        # 显示总结
        summary = report["summary"]
        print("\n🎯 Phase E 总结:")
        print(f"  📊 总测试用例: {summary['total_test_cases']}")
        print(f"  📈 测试成功率: {summary['success_rate']:.1%}")
        print(f"  📋 平均模块覆盖率: {summary['average_module_coverage']:.1f}%")
        print(f"  💡 优化建议数: {summary['recommendations_count']}")

        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Phase E 覆盖率精细化分析")
    parser.add_argument("--report-only", action="store_true", help="仅生成报告")

    args = parser.parse_args()

    analyzer = CoverageAnalyzer()

    print("🚀 启动Phase E覆盖率精细化分析...")

    # 创建完整报告
    analyzer.create_coverage_report()

    if not args.report_only:
        # 显示额外分析
        print("\n🔧 下一步行动建议:")
        print("1. 修复失败的测试用例")
        print("2. 补充低覆盖率模块的测试")
        print("3. 添加更多边界条件和异常处理测试")
        print("4. 集成性能和并发测试")
        print("5. 更新GitHub Issues同步进展")

    print("\n✅ Phase E覆盖率分析完成")


if __name__ == "__main__":
    main()