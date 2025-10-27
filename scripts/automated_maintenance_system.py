#!/usr/bin/env python3
"""
自动化维护系统 - 路径A阶段3
建立项目长期维护自动化机制
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

class AutomatedMaintenanceSystem:
    def __init__(self):
        self.maintenance_log = []
        self.system_status = {
            'health_checks': {},
            'quality_metrics': {},
            'maintenance_actions': [],
            'last_run': None
        }

    def run_health_checks(self):
        """运行健康检查"""
        print("🏥 运行系统健康检查...")
        print("=" * 50)

        health_results = {}

        # 检查1: 核心测试
        try:
            result = subprocess.run(
                ["pytest", "test_basic_pytest.py", "-q"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                health_results['core_tests'] = {'status': '✅ 通过', 'details': '基础功能测试正常'}
            else:
                health_results['core_tests'] = {'status': '❌ 失败', 'details': result.stderr[:100]}
        except Exception as e:
            health_results['core_tests'] = {'status': '💥 异常', 'details': str(e)}

        # 检查2: 代码质量
        try:
            result = subprocess.run(
                ["ruff", "check", "src/", "--statistics"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                health_results['code_quality'] = {'status': '✅ 优秀', 'details': '零代码质量问题'}
            else:
                lines = result.stdout.split('\n')
                errors = 0
                for line in lines:
                    if 'Found' in line and 'errors' in line:
                        errors = int(line.split('errors')[0].split()[-1])
                        break
                health_results['code_quality'] = {'status': '⚠️ 需要改进', 'details': f'{errors}个质量问题'}
        except Exception as e:
            health_results['code_quality'] = {'status': '💥 异常', 'details': str(e)}

        # 检查3: 文件完整性
        try:
            required_files = [
                'src/database/repositories/team_repository.py',
                'tests/conftest.py',
                'test_basic_pytest.py'
            ]
            missing_files = [f for f in required_files if not Path(f).exists()]

            if not missing_files:
                health_results['file_integrity'] = {'status': '✅ 完整', 'details': '所有必需文件存在'}
            else:
                health_results['file_integrity'] = {'status': '❌ 缺失', 'details': f'缺失: {missing_files}'}
        except Exception as e:
            health_results['file_integrity'] = {'status': '💥 异常', 'details': str(e)}

        # 显示结果
        for check, result in health_results.items():
            print(f"  {check}: {result['status']} - {result['details']}")

        self.system_status['health_checks'] = health_results
        return health_results

    def collect_quality_metrics(self):
        """收集质量指标"""
        print("\n📊 收集质量指标...")
        print("=" * 50)

        metrics = {}

        # 指标1: 测试覆盖率
        try:
            result = subprocess.run(
                ["pytest", "test_basic_pytest.py", "--cov=src", "--cov-report=json:maintenance_coverage.json", "--quiet"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and Path("maintenance_coverage.json").exists():
                with open("maintenance_coverage.json", 'r') as f:
                    coverage_data = json.load(f)

                total_coverage = coverage_data['totals']['percent_covered']
                metrics['coverage'] = {
                    'total_coverage': total_coverage,
                    'target_met': total_coverage >= 15.0,
                    'trend': 'stable'  # 可以与历史数据比较
                }
                print(f"  📈 覆盖率: {total_coverage:.2f}% (目标: 15%)")
            else:
                metrics['coverage'] = {'total_coverage': 0, 'target_met': False, 'trend': 'unknown'}
                print("  📈 覆盖率: 无法获取")
        except Exception as e:
            metrics['coverage'] = {'total_coverage': 0, 'target_met': False, 'trend': 'error'}
            print(f"  📈 覆盖率错误: {e}")

        # 指标2: 文件统计
        try:
            # 统计源码文件
            src_files = list(Path("src").rglob("*.py"))
            test_files = list(Path("tests").rglob("*.py"))

            metrics['file_stats'] = {
                'source_files': len(src_files),
                'test_files': len(test_files),
                'test_to_source_ratio': len(test_files) / len(src_files) if src_files else 0
            }
            print(f"  📁 源码文件: {len(src_files)} 个")
            print(f"  📁 测试文件: {len(test_files)} 个")
            print(f"  📊 测试/源码比: {metrics['file_stats']['test_to_source_ratio']:.2f}")
        except Exception as e:
            metrics['file_stats'] = {'error': str(e)}
            print(f"  📁 文件统计错误: {e}")

        # 指标3: 项目活跃度
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--since='1 week ago'"],
                capture_output=True,
                text=True,
                timeout=30
            )

            commits = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            metrics['project_activity'] = {
                'commits_last_week': commits,
                'activity_level': 'high' if commits >= 5 else 'medium' if commits >= 2 else 'low'
            }
            print(f"  🚀 最近一周提交: {commits} 次")
            print(f"  📊 活跃度: {metrics['project_activity']['activity_level']}")
        except Exception as e:
            metrics['project_activity'] = {'error': str(e)}
            print(f"  🚀 活跃度检查错误: {e}")

        self.system_status['quality_metrics'] = metrics
        return metrics

    def run_maintenance_actions(self):
        """运行维护操作"""
        print("\n🔧 执行维护操作...")
        print("=" * 50)

        actions_performed = []

        # 操作1: 清理临时文件
        try:
            temp_files_to_clean = [
                "maintenance_coverage.json",
                "coverage_validation.json",
                ".coverage",
                "__pycache__"
            ]

            cleaned_count = 0
            for temp_file in temp_files_to_clean:
                if Path(temp_file).exists():
                    if Path(temp_file).is_file():
                        Path(temp_file).unlink()
                    else:
                        import shutil
                        shutil.rmtree(temp_file, ignore_errors=True)
                    cleaned_count += 1

            actions_performed.append(f"清理临时文件: {cleaned_count}个")
            print(f"  🧹 清理临时文件: {cleaned_count} 个")
        except Exception as e:
            actions_performed.append(f"清理临时文件失败: {e}")
            print(f"  ❌ 清理临时文件失败: {e}")

        # 操作2: 更新维护日志
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'health_status': self.system_status.get('health_checks', {}),
                'quality_metrics': self.system_status.get('quality_metrics', {}),
                'actions_performed': actions_performed
            }

            log_file = Path("maintenance_logs/maintenance_log.json")
            log_file.parent.mkdir(exist_ok=True)

            # 读取现有日志
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(log_entry)

            # 保留最近30条日志
            if len(logs) > 30:
                logs = logs[-30:]

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

            actions_performed.append("更新维护日志")
            print(f"  📝 更新维护日志: 保存到 {log_file}")
        except Exception as e:
            actions_performed.append(f"更新维护日志失败: {e}")
            print(f"  ❌ 更新维护日志失败: {e}")

        # 操作3: 生成质量报告
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'system_status': self.system_status,
                'recommendations': self._generate_recommendations()
            }

            report_file = Path("reports/latest_quality_report.json")
            report_file.parent.mkdir(exist_ok=True)

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            actions_performed.append("生成质量报告")
            print(f"  📊 生成质量报告: 保存到 {report_file}")
        except Exception as e:
            actions_performed.append(f"生成质量报告失败: {e}")
            print(f"  ❌ 生成质量报告失败: {e}")

        self.system_status['maintenance_actions'] = actions_performed
        self.system_status['last_run'] = datetime.now().isoformat()
        return actions_performed

    def _generate_recommendations(self):
        """生成改进建议"""
        recommendations = []

        health = self.system_status.get('health_checks', {})
        metrics = self.system_status.get('quality_metrics', {})

        # 基于健康检查的建议
        if health.get('core_tests', {}).get('status') != '✅ 通过':
            recommendations.append({
                'priority': 'high',
                'category': 'testing',
                'description': '修复基础测试失败问题',
                'action': '检查测试环境和依赖'
            })

        if health.get('code_quality', {}).get('status') != '✅ 优秀':
            recommendations.append({
                'priority': 'medium',
                'category': 'quality',
                'description': '改进代码质量问题',
                'action': '运行 ruff check --fix'
            })

        # 基于质量指标的建议
        if metrics.get('coverage', {}).get('target_met') is False:
            recommendations.append({
                'priority': 'medium',
                'category': 'coverage',
                'description': '提升测试覆盖率到15%以上',
                'action': '添加更多测试用例'
            })

        if metrics.get('file_stats', {}).get('test_to_source_ratio', 0) < 0.1:
            recommendations.append({
                'priority': 'low',
                'category': 'testing',
                'description': '增加测试文件数量',
                'action': '为关键模块创建测试'
            })

        if not recommendations:
            recommendations.append({
                'priority': 'info',
                'category': 'general',
                'description': '系统状态良好',
                'action': '继续保持当前质量标准'
            })

        return recommendations

    def generate_maintenance_report(self):
        """生成维护报告"""
        print("\n📋 生成维护报告...")
        print("=" * 50)

        report = {
            'report_time': datetime.now().isoformat(),
            'system_status': self.system_status,
            'summary': {
                'overall_health': self._calculate_overall_health(),
                'total_actions': len(self.system_status.get('maintenance_actions', [])),
                'next_maintenance': self._schedule_next_maintenance()
            }
        }

        # 保存报告
        report_file = Path(f"maintenance_reports/maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ 维护报告已保存: {report_file}")

        # 显示简要总结
        print("\n📊 维护总结:")
        print(f"  整体健康状态: {report['summary']['overall_health']}")
        print(f"  执行操作数: {report['summary']['total_actions']}")
        print(f"  下次维护: {report['summary']['next_maintenance']}")

        return report

    def _calculate_overall_health(self):
        """计算整体健康状态"""
        health = self.system_status.get('health_checks', {})

        scores = {
            '✅ 通过': 100,
            '✅ 优秀': 100,
            '✅ 完整': 100,
            '⚠️ 需要改进': 70,
            '⚠️ 需要关注': 70,
            '❌ 失败': 0,
            '❌ 缺失': 0,
            '💥 异常': 0
        }

        total_score = 0
        count = 0

        for check, result in health.items():
            if 'status' in result:
                score = scores.get(result['status'], 50)
                total_score += score
                count += 1

        if count > 0:
            average = total_score / count
            if average >= 90:
                return '🏆 优秀'
            elif average >= 70:
                return '✅ 良好'
            elif average >= 50:
                return '⚠️ 需要关注'
            else:
                return '❌ 需要修复'

        return '❓ 未知'

    def _schedule_next_maintenance(self):
        """安排下次维护时间"""
        # 基于当前系统状态安排下次维护
        health = self.system_status.get('health_checks', {})

        # 如果有问题，建议尽快维护
        for check, result in health.items():
            if result.get('status') in ['❌ 失败', '❌ 缺失', '💥 异常']:
                return '立即 (24小时内)'

        # 如果有改进项，建议一周内
        metrics = self.system_status.get('quality_metrics', {})
        if not metrics.get('coverage', {}).get('target_met', True):
            return '一周内'

        # 状态良好，建议定期维护
        return '一周后'

    def run_automated_maintenance(self):
        """运行自动化维护"""
        print("🤖 开始自动化维护系统...")
        print("=" * 60)

        start_time = time.time()

        # 执行维护流程
        self.run_health_checks()
        self.collect_quality_metrics()
        self.run_maintenance_actions()

        # 生成报告
        report = self.generate_maintenance_report()

        duration = time.time() - start_time

        print("\n🎉 自动化维护完成!")
        print(f"⏱️  总用时: {duration:.2f}秒")
        print(f"📊 系统状态: {report['summary']['overall_health']}")
        print(f"🔧 执行操作: {report['summary']['total_actions']} 个")
        print(f"📅 下次维护: {report['summary']['next_maintenance']}")

        return report

def main():
    """主函数"""
    maintainer = AutomatedMaintenanceSystem()
    return maintainer.run_automated_maintenance()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)