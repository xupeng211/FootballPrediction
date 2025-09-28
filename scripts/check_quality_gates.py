#!/usr/bin/env python3
"""
质量门禁检查器 - 验证项目是否达到预定义的质量标准
用于CI/CD流水线中的质量门禁检查
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List


class QualityGateChecker:
    """质量门禁检查器"""

    def __init__(self):
        # 质量门禁阈值配置
        self.gates = {
            'coverage_development': {
                'minimum': 20.0,
                'description': '开发环境测试覆盖率',
                'critical': True
            },
            'coverage_production': {
                'minimum': 80.0,
                'description': '生产环境测试覆盖率',
                'critical': False  # 生产环境要求更严格，但开发阶段不阻止
            },
            'quality_score': {
                'minimum': 40.0,
                'description': '综合质量分数',
                'critical': True
            },
            'auto_generated_tests': {
                'minimum': 20,
                'description': '自动生成测试文件数量',
                'critical': True
            },
            'flaky_test_ratio': {
                'maximum': 10.0,  # 最大值
                'description': 'Flaky测试比例',
                'critical': False
            },
            'mutation_score': {
                'minimum': 30.0,
                'description': 'Mutation测试分数',
                'critical': False
            }
        }

    def load_quality_snapshot(self, snapshot_path: str) -> Dict[str, Any]:
        """加载质量快照数据"""
        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 质量快照文件未找到: {snapshot_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ 质量快照文件格式错误: {e}")
            sys.exit(1)

    def extract_metrics(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        """从快照中提取质量指标"""
        metrics = {}

        # 提取覆盖率
        coverage_data = snapshot.get('coverage', {})
        if coverage_data:
            metrics['coverage_development'] = coverage_data.get('coverage_percent', 0.0)
            metrics['coverage_production'] = coverage_data.get('coverage_percent', 0.0)

        # 提取质量分数
        summary_data = snapshot.get('summary', {})
        if summary_data:
            metrics['quality_score'] = summary_data.get('overall_score', 0.0)

        # 提取测试统计
        auto_tests_data = snapshot.get('auto_tests', {})
        if auto_tests_data:
            metrics['auto_generated_tests'] = auto_tests_data.get('auto_tests_added', 0)

        # 提取测试稳定性
        flaky_data = snapshot.get('flaky', {})
        if flaky_data:
            metrics['flaky_test_ratio'] = flaky_data.get('flaky_rate', 0.0)

        # 提取mutation测试分数
        mutation_data = snapshot.get('mutation', {})
        if mutation_data:
            metrics['mutation_score'] = mutation_data.get('mutation_score', 0.0)

        return metrics

    def check_gate(self, gate_name: str, gate_config: Dict[str, Any], value: float) -> Dict[str, Any]:
        """检查单个质量门禁"""
        result = {
            'name': gate_name,
            'description': gate_config['description'],
            'value': value,
            'threshold': gate_config.get('minimum', gate_config.get('maximum')),
            'passed': False,
            'critical': gate_config.get('critical', False),
            'message': ''
        }

        if 'minimum' in gate_config:
            result['passed'] = value >= gate_config['minimum']
            result['message'] = f"{value:.1f} >= {gate_config['minimum']:.1f}"
        elif 'maximum' in gate_config:
            result['passed'] = value <= gate_config['maximum']
            result['message'] = f"{value:.1f} <= {gate_config['maximum']:.1f}"

        return result

    def check_all_gates(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """检查所有质量门禁"""
        results = []

        for gate_name, gate_config in self.gates.items():
            if gate_name in metrics:
                value = metrics[gate_name]
                result = self.check_gate(gate_name, gate_config, value)
                results.append(result)
            else:
                # 指标不存在，创建失败结果
                results.append({
                    'name': gate_name,
                    'description': gate_config['description'],
                    'value': 0.0,
                    'threshold': gate_config.get('minimum', gate_config.get('maximum')),
                    'passed': False,
                    'critical': gate_config.get('critical', False),
                    'message': '指标数据缺失'
                })

        return results

    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """生成质量门禁检查报告"""
        report_lines = []
        report_lines.append("🎯 质量门禁检查报告")
        report_lines.append("=" * 50)
        report_lines.append("")

        # 统计结果
        total_gates = len(results)
        passed_gates = sum(1 for r in results if r['passed'])
        critical_failed = sum(1 for r in results if not r['passed'] and r['critical'])

        # 总体状态
        if critical_failed == 0:
            overall_status = "✅ 通过"
            status_emoji = "🟢"
        elif critical_failed <= 2:
            overall_status = "⚠️ 有条件通过"
            status_emoji = "🟡"
        else:
            overall_status = "❌ 失败"
            status_emoji = "🔴"

        report_lines.append(f"总体状态: {status_emoji} {overall_status}")
        report_lines.append(f"通过门禁: {passed_gates}/{total_gates}")
        report_lines.append(f"关键失败: {critical_failed}")
        report_lines.append("")

        # 详细结果
        report_lines.append("📊 详细检查结果:")
        report_lines.append("-" * 50)

        for result in results:
            status_icon = "✅" if result['passed'] else "❌"
            critical_flag = " [关键]" if result['critical'] else ""

            report_lines.append(
                f"{status_icon} {result['description']}{critical_flag}"
            )
            report_lines.append(f"   当前值: {result['value']:.1f}")
            report_lines.append(f"   阈值: {result['threshold']:.1f}")
            report_lines.append(f"   结果: {result['message']}")
            report_lines.append("")

        # 建议和改进措施
        failed_gates = [r for r in results if not r['passed']]
        if failed_gates:
            report_lines.append("💡 改进建议:")
            report_lines.append("-" * 30)

            for gate in failed_gates:
                if gate['name'] == 'coverage_development':
                    report_lines.append("- 运行 `make coverage` 查看详细覆盖率报告")
                    report_lines.append("- 重点关注低覆盖率模块的测试补充")
                elif gate['name'] == 'quality_score':
                    report_lines.append("- 检查代码质量工具输出 (flake8, mypy, black)")
                    report_lines.append("- 运行 `make quality` 进行全面质量检查")
                elif gate['name'] == 'auto_generated_tests':
                    report_lines.append("- 运行 `python scripts/generate_tests.py` 生成更多测试")
                    report_lines.append("- 检查测试生成配置和覆盖率分析")
                elif gate['name'] == 'flaky_test_ratio':
                    report_lines.append("- 分析和修复不稳定的测试用例")
                    report_lines.append("- 检查测试中的时间依赖和外部依赖")

            report_lines.append("")

        # 总结
        if critical_failed == 0:
            report_lines.append("🎉 所有质量门禁均已通过！项目质量符合要求。")
        elif critical_failed <= 2:
            report_lines.append("⚠️  少量质量门禁未通过，但可以继续开发。建议尽快修复。")
        else:
            report_lines.append("🚨 多个关键质量门禁未通过，建议优先处理质量问题后再继续开发。")

        return "\n".join(report_lines)

    def save_report(self, report: str, output_path: str) -> None:
        """保存检查报告到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📋 质量门禁报告已保存: {output_path}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")

    def check_and_exit(self, snapshot_path: str, output_dir: str = None) -> None:
        """执行质量门禁检查并根据结果退出"""
        # 加载数据
        snapshot = self.load_quality_snapshot(snapshot_path)
        metrics = self.extract_metrics(snapshot)

        # 检查门禁
        results = self.check_all_gates(metrics)

        # 生成报告
        report = self.generate_report(results)

        # 输出报告
        print(report)

        # 保存报告
        if output_dir:
            output_path = Path(output_dir) / "quality_gates_report.md"
            self.save_report(report, output_path)

        # 根据关键失败数量决定退出码
        critical_failed = sum(1 for r in results if not r['passed'] and r['critical'])

        if critical_failed > 2:
            print("\n🚨 质量门禁检查失败 - 退出码 1")
            sys.exit(1)
        elif critical_failed > 0:
            print("\n⚠️  质量门禁有条件通过 - 退出码 0")
            sys.exit(0)
        else:
            print("\n✅ 质量门禁检查通过 - 退出码 0")
            sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='检查项目质量门禁')
    parser.add_argument('snapshot_path', help='质量快照文件路径')
    parser.add_argument('--output-dir', '-o',
                       help='报告输出目录')
    parser.add_argument('--gates', '-g', action='store_true',
                       help='显示所有质量门禁配置')

    args = parser.parse_args()

    checker = QualityGateChecker()

    if args.gates:
        print("🎯 当前配置的质量门禁:")
        print("-" * 50)
        for name, config in checker.gates.items():
            critical = " [关键]" if config['critical'] else ""
            threshold = config.get('minimum', config.get('maximum'))
            threshold_type = "最小值" if 'minimum' in config else "最大值"
            print(f"{name}: {config['description']}{critical}")
            print(f"   {threshold_type}: {threshold}")
            print()
        return

    checker.check_and_exit(args.snapshot_path, args.output_dir)


if __name__ == "__main__":
    main()