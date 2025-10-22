#!/usr/bin/env python3
"""
覆盖率质量门禁
Coverage Quality Gate

检查代码覆盖率是否达到预设标准，如果未达到则阻止构建。
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Tuple


class CoverageQualityGate:
    """覆盖率质量门禁检查器"""

    def __init__(self):
        self.thresholds = {
            "overall": 75.0,      # 总体覆盖率阈值
            "critical": 80.0,     # 关键模块覆盖率阈值
            "minimum": 60.0,      # 最低覆盖率阈值
        }

        # 关键模块列表
        self.critical_modules = [
            "src/api/predictions/router.py",
            "src/api/health/__init__.py",
            "src/core/di_setup.py",
            "src/services/prediction.py",
            "src/database/repositories/match_repository.py",
            "src/database/repositories/prediction_repository.py",
        ]

        # 忽略的模块（新开发或测试中的模块）
        self.ignored_modules = [
            "src/monitoring/",
            "src/lineage/",
            "src/data/collectors/streaming_collector.py",
        ]

    def run_coverage_analysis(self) -> Dict:
        """运行覆盖率分析"""
        try:
            # 运行pytest生成覆盖率报告
            cmd = [
                "python", "-m", "pytest",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term-missing",
                "--quiet",
                "tests/unit/api/test_predictions_router_new.py",
                "tests/unit/api/test_health_router_new.py",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )

            # 检查是否有错误输出，但不阻止继续执行
            if result.returncode != 0:
                print(f"⚠️  测试执行有失败项，但继续分析覆盖率")
                print(f"stderr: {result.stderr[:200]}...")  # 只显示前200个字符

            # 读取覆盖率报告
            coverage_file = Path("coverage.json")
            if not coverage_file.exists():
                print("❌ 覆盖率报告文件不存在")
                return None

            with open(coverage_file, 'r') as f:
                return json.load(f)

        except Exception as e:
            print(f"❌ 运行覆盖率分析时出错: {e}")
            return None

    def extract_module_coverage(self, coverage_data: Dict) -> List[Dict]:
        """提取模块覆盖率信息"""
        modules = []

        if 'files' in coverage_data:
            for file_path, file_data in coverage_data['files'].items():
                if any(ignore in file_path for ignore in self.ignored_modules):
                    continue

                modules.append({
                    'path': file_path,
                    'statements': file_data['summary']['num_statements'],
                    'missing': file_data['summary']['missing_lines'],
                    'covered': file_data['summary']['covered_lines'],
                    'coverage': file_data['summary']['percent_covered'],
                    'is_critical': file_path in self.critical_modules,
                })

        return modules

    def check_quality_gate(self, coverage_data: Dict) -> Tuple[bool, List[str]]:
        """检查质量门禁"""
        violations = []

        # 检查总体覆盖率
        overall_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
        if overall_coverage < self.thresholds['overall']:
            violations.append(
                f"总体覆盖率 {overall_coverage:.1f}% 低于阈值 {self.thresholds['overall']}%"
            )

        # 检查各模块覆盖率
        modules = self.extract_module_coverage(coverage_data)

        for module in modules:
            threshold = (
                self.thresholds['critical'] if module['is_critical']
                else self.thresholds['minimum']
            )

            if module['coverage'] < threshold:
                violation_type = "关键模块" if module['is_critical'] else "普通模块"
                violations.append(
                    f"{violation_type} {module['path']} 覆盖率 {module['coverage']:.1f}% 低于阈值 {threshold}%"
                )

        # 检查零覆盖率模块
        zero_coverage_modules = [
            m['path'] for m in modules if m['coverage'] == 0 and m['statements'] > 0
        ]

        if zero_coverage_modules:
            violations.append(f"发现 {len(zero_coverage_modules)} 个零覆盖率模块: {', '.join(zero_coverage_modules[:3])}")

        return len(violations) == 0, violations

    def generate_report(self, coverage_data: Dict, violations: List[str]) -> str:
        """生成覆盖率报告"""
        overall_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
        total_statements = coverage_data.get('totals', {}).get('num_statements', 0)
        total_missing = coverage_data.get('totals', {}).get('missing_lines', 0)

        modules = self.extract_module_coverage(coverage_data)
        critical_modules = [m for m in modules if m['is_critical']]

        report = f"""
📊 覆盖率质量门禁报告
{'='*50}

🎯 总体覆盖率: {overall_coverage:.1f}%
📝 总代码行数: {total_statements}
❌ 未覆盖行数: {total_missing}
📋 测试模块数: {len(modules)}
🔥 关键模块数: {len(critical_modules)}

📈 关键模块覆盖率:
"""

        for module in critical_modules:
            status = "✅" if module['coverage'] >= self.thresholds['critical'] else "❌"
            report += f"  {status} {module['path']}: {module['coverage']:.1f}%\n"

        report += f"\n⚠️  质量门禁违规 ({len(violations)}项):\n"
        if violations:
            for violation in violations:
                report += f"  ❌ {violation}\n"
        else:
            report += "  ✅ 无违规项\n"

        # 推荐改进措施
        if violations:
            report += f"\n💡 改进建议:\n"

            zero_coverage = len([m for m in modules if m['coverage'] == 0])
            if zero_coverage > 0:
                report += f"  🔧 优先为 {zero_coverage} 个零覆盖率模块添加基础测试\n"

            low_coverage = len([m for m in modules if 0 < m['coverage'] < self.thresholds['minimum']])
            if low_coverage > 0:
                report += f"  📈 提升 {low_coverage} 个低覆盖率模块的测试覆盖\n"

        return report

    def check_and_report(self, verbose: bool = True) -> bool:
        """执行质量门禁检查并生成报告"""
        print("🚀 开始覆盖率质量门禁检查...")

        # 运行覆盖率分析
        coverage_data = self.run_coverage_analysis()
        if coverage_data is None:
            print("❌ 无法获取覆盖率数据")
            return False

        # 检查质量门禁
        passed, violations = self.check_quality_gate(coverage_data)

        # 生成报告
        report = self.generate_report(coverage_data, violations)

        if verbose:
            print(report)

        # 保存报告到文件
        report_file = Path("reports/quality/coverage_gate_report.md")
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 详细报告已保存到: {report_file}")

        if passed:
            print("✅ 覆盖率质量门禁通过!")
            return True
        else:
            print("❌ 覆盖率质量门禁失败!")
            print("请提升测试覆盖率后重新运行检查。")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="覆盖率质量门禁检查")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="显示详细报告"
    )
    parser.add_argument(
        "--overall-threshold",
        type=float,
        default=75.0,
        help="总体覆盖率阈值 (默认: 75.0)"
    )
    parser.add_argument(
        "--critical-threshold",
        type=float,
        default=80.0,
        help="关键模块覆盖率阈值 (默认: 80.0)"
    )
    parser.add_argument(
        "--minimum-threshold",
        type=float,
        default=60.0,
        help="最低覆盖率阈值 (默认: 60.0)"
    )

    args = parser.parse_args()

    # 创建质量门禁检查器
    gate = CoverageQualityGate()

    # 更新阈值
    gate.thresholds['overall'] = args.overall_threshold
    gate.thresholds['critical'] = args.critical_threshold
    gate.thresholds['minimum'] = args.minimum_threshold

    # 执行检查
    passed = gate.check_and_report(verbose=args.verbose)

    # 设置退出码
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()