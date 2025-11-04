#!/usr/bin/env python3
"""
集成测试覆盖率改进器
Integrated Coverage Improver

结合质量保证机制和测试覆盖率提升，提供真实的改进方案
"""

import sys
import os
import json
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

class IntegratedCoverageImprover:
    """集成覆盖率改进器"""

    def __init__(self):
        self.project_root = project_root
        self.results_log = []

    def log(self, message: str, success: bool = None):
        """记录日志"""
        result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'message': message,
            'success': success
        }
        self.results_log.append(result)

        icon = "✅" if success is True else "❌" if success is False else "🔄"
        print(f"{icon} {message}")

def _check_current_state_handle_error():
            result = subprocess.run([
                sys.executable, '-m', 'compileall', '-q', 'src/'
            ], capture_output=True, text=True, cwd=self.project_root)


def _check_current_state_check_condition():
                self.log("src目录语法检查通过", True)
            else:
                error_count = len([line for line in result.stderr.split('\n') if line.strip()])
                self.log(f"src目录存在{error_count}个语法错误", False)

        except Exception as e:
            self.log(f"语法检查失败: {e}", False)

        # 2. 检查测试文件
        test_files = [
            'tests/realistic_first_tests.py',
            'tests/expand_successful_tests.py',
            'tests/apply_successful_strategy.py'
        ]

        total_tests = 0
        passed_tests = 0

def _check_current_state_handle_error():
                    result = subprocess.run([
                        sys.executable, str(self.project_root / test_file)
                    ], capture_output=True, text=True, cwd=self.project_root, timeout=60)


def _check_current_state_check_condition():
                                total = int(line.split(':')[-1].strip())
                                total_tests += total

                        self.log(f"{test_file} 运行成功", True)
                    else:
                        self.log(f"{test_file} 运行失败", False)

                except Exception as e:
                    self.log(f"{test_file} 执行异常: {e}", False)


def _check_current_state_check_condition():
            success_rate = (passed_tests / total_tests) * 100
            self.log(f"测试成功率: {success_rate:.1f}% ({passed_tests}/{total_tests})", True)
            estimated_coverage = success_rate * 0.3  # 保守估计
            self.log(f"估算覆盖率贡献: {estimated_coverage:.1f}%", True)
        else:
            self.log("没有成功运行的测试", False)

        # 3. 运行真实覆盖率测量

def _check_current_state_handle_error():
            result = subprocess.run([
                sys.executable, 'tests/real_coverage_measurement.py'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)


def _check_current_state_handle_error():
                            coverage = float(coverage_str)
                            self.log(f"真实覆盖率: {coverage:.1f}%", True)
                            return coverage

    def check_current_state(self):
        """检查当前状态"""
        self.log("🔍 检查当前项目状态...", None)

        # 1. 检查语法错误
        _check_current_state_handle_error()
            result = subprocess.run([
                sys.executable, '-m', 'compileall', '-q', 'src/'
            ], capture_output=True, text=True, cwd=self.project_root)

            _check_current_state_check_condition()
                self.log("src目录语法检查通过", True)
            else:
                error_count = len([line for line in result.stderr.split('\n') if line.strip()])
                self.log(f"src目录存在{error_count}个语法错误", False)

        except Exception as e:
            self.log(f"语法检查失败: {e}", False)

        # 2. 检查测试文件
        test_files = [
            'tests/realistic_first_tests.py',
            'tests/expand_successful_tests.py',
            'tests/apply_successful_strategy.py'
        ]

        total_tests = 0
        passed_tests = 0

        for test_file in test_files:
            if (self.project_root / test_file).exists():
                _check_current_state_handle_error()
                    result = subprocess.run([
                        sys.executable, str(self.project_root / test_file)
                    ], capture_output=True, text=True, cwd=self.project_root, timeout=60)

                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if '通过测试:' in line and ':' in line:
                                passed = int(line.split(':')[-1].strip())
                                passed_tests += passed
                            _check_current_state_check_condition()
                                total = int(line.split(':')[-1].strip())
                                total_tests += total

                        self.log(f"{test_file} 运行成功", True)
                    else:
                        self.log(f"{test_file} 运行失败", False)

                except Exception as e:
                    self.log(f"{test_file} 执行异常: {e}", False)

        _check_current_state_check_condition()
            success_rate = (passed_tests / total_tests) * 100
            self.log(f"测试成功率: {success_rate:.1f}% ({passed_tests}/{total_tests})", True)
            estimated_coverage = success_rate * 0.3  # 保守估计
            self.log(f"估算覆盖率贡献: {estimated_coverage:.1f}%", True)
        else:
            self.log("没有成功运行的测试", False)

        # 3. 运行真实覆盖率测量
        _check_current_state_handle_error()
            result = subprocess.run([
                sys.executable, 'tests/real_coverage_measurement.py'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if '综合覆盖率:' in line:
                        coverage_str = line.split(':')[-1].strip().rstrip('%')
                        _check_current_state_handle_error()
                            coverage = float(coverage_str)
                            self.log(f"真实覆盖率: {coverage:.1f}%", True)
                            return coverage
                        except ValueError:
                            pass
            else:
                self.log("真实覆盖率测量失败", False)

        except Exception as e:
            self.log(f"覆盖率测量异常: {e}", False)

        return 0.0

    def apply_quality_fixes(self):
        """应用质量修复"""
        self.log("🔧 应用质量修复...", None)

        # 尝试运行智能质量修复器
        try:
            result = subprocess.run([
                sys.executable, 'scripts/smart_quality_fixer.py', '--dry-run'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=120)

            if result.returncode == 0:
                self.log("智能质量修复器检查完成", True)
                # 检查输出中是否有修复建议
                if '发现' in result.stdout and '问题' in result.stdout:
                    self.log("质量修复器发现了一些问题", True)
                else:
                    self.log("质量修复器未发现明显问题", True)
            else:
                self.log("智能质量修复器执行失败", False)

        except Exception as e:
            self.log(f"质量修复器异常: {e}", False)

    def expand_test_coverage(self):
        """扩展测试覆盖率"""
        self.log("🧪 扩展测试覆盖率...", None)

        # 运行我们的覆盖率改进执行器
        try:
            result = subprocess.run([
                sys.executable, 'scripts/coverage_improvement_executor.py', '--phase', '1'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=120)

            if result.returncode == 0:
                self.log("Phase 1 执行完成", True)
                # 解析结果
                lines = result.stdout.split('\n')
                for line in lines:
                    if '当前真实覆盖率:' in line:
                        coverage_str = line.split(':')[-1].strip().rstrip('%')
                        try:
                            coverage = float(coverage_str)
                            self.log(f"Phase 1后覆盖率: {coverage:.1f}%", True)
                            return coverage
                        except ValueError:
                            pass
            else:
                self.log("Phase 1 执行失败", False)

        except Exception as e:
            self.log(f"Phase 1 执行异常: {e}", False)

        return None

    def generate_real_report(self, initial_coverage: float, final_coverage: float):
        """生成真实报告"""
        self.log("📊 生成真实改进报告...", None)

        report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'initial_coverage': initial_coverage,
            'final_coverage': final_coverage,
            'improvement': final_coverage - initial_coverage,
            'actions_taken': self.results_log,
            'summary': {
                'total_actions': len(self.results_log),
                'successful_actions': len([r for r in self.results_log if r.get('success') is True]),
    
    
                'failed_actions': len([r for r in self.results_log if r.get('success') is False])
            }
        }

        # 保存报告
        report_file = self.project_root / f'real_coverage_improvement_report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log(f"真实报告已保存: {report_file}", True)

        # 输出摘要
        summary = report['summary']
        print("\n📊 真实改进摘要:")
        print(f"   初始覆盖率: {initial_coverage:.1f}%")
        print(f"   最终覆盖率: {final_coverage:.1f}%")
        print(f"   改进幅度: {report['improvement']:+.1f}%")
        print(f"   总操作数: {summary['total_actions']}")
        print(f"   成功操作: {summary['successful_actions']}")
        print(f"   失败操作: {summary['failed_actions']}")

        if report['improvement'] > 0:
            print(f"   🎉 改进成功！覆盖率提升了 {report['improvement']:.1f}%")
        elif report['improvement'] == 0:
            print("   ➡️  覆盖率保持不变")
        else:
            print(f"   ⚠️  覆盖率下降了 {abs(report['improvement']):.1f}%")

        return report

    def run_integrated_improvement(self):
        """运行集成改进流程"""
        print("=" * 80)
        print("🎯 集成测试覆盖率改进流程")
        print("=" * 80)

        # 1. 检查当前状态
        initial_coverage = self.check_current_state()

        # 2. 应用质量修复
        self.apply_quality_fixes()

        # 3. 扩展测试覆盖率
        final_coverage = self.expand_test_coverage()

        # 如果没有获取到最终覆盖率，使用当前状态检查
        if final_coverage is None:
            final_coverage = self.check_current_state()

        # 4. 生成真实报告
        report = self.generate_real_report(initial_coverage, final_coverage)

        print("\n" + "=" * 80)
        print("🏁 集成改进流程完成")
        print("=" * 80)

        return report


def main():
    """主函数"""
    improver = IntegratedCoverageImprover()
    report = improver.run_integrated_improvement()

    return report


if __name__ == "__main__":
    main()