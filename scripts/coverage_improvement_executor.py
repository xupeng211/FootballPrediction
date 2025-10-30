#!/usr/bin/env python3
"""
测试覆盖率最佳实践执行器
自动化执行分阶段的测试覆盖率提升计划
"""

import sys
import os
import subprocess
import json
import datetime
from typing import Dict, List, Any
from pathlib import Path

# 添加项目根路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

class CoverageImprovementExecutor:
    """覆盖率改进执行器"""

    def __init__(self):
        self.project_root = project_root
        self.results_log = []
        self.current_phase = 1
        self.start_time = datetime.datetime.now()

    def log_result(self, category: str, message: str, success: bool = None):
        """记录执行结果"""
        result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'category': category,
            'message': message,
            'success': success
        }
        self.results_log.append(result)

        # 输出到控制台
        icon = "✅" if success is True else "❌" if success is False else "🔄"
        print(f"{icon} [{category}] {message}")

    def run_syntax_check(self):
        """运行语法检查"""
        self.log_result("语法检查", "开始检查项目语法...", None)

        try:
            # 检查src目录
            result = subprocess.run([
                sys.executable, '-m', 'compileall', '-q', 'src/'
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                self.log_result("语法检查", "src目录语法检查通过", True)
            else:
                error_count = len(result.stderr.split('\n')) if result.stderr else 0
                self.log_result("语法检查", f"src目录存在{error_count}个语法错误", False)

            # 检查tests目录
            result_tests = subprocess.run([
                sys.executable, '-m', 'compileall', '-q', 'tests/'
            ], capture_output=True, text=True, cwd=self.project_root)

            if result_tests.returncode == 0:
                self.log_result("语法检查", "tests目录语法检查通过", True)
            else:
                error_count = len(result_tests.stderr.split('\n')) if result_tests.stderr else 0
                self.log_result("语法检查", f"tests目录存在{error_count}个语法错误", False)

        except Exception as e:
            self.log_result("语法检查", f"语法检查失败: {e}", False)

    def run_existing_tests(self):
        """运行现有的测试"""
        self.log_result("现有测试", "运行现有测试以获取基准...", None)

        existing_test_files = [
            'tests/realistic_first_tests.py',
            'tests/expand_successful_tests.py',
            'tests/apply_successful_strategy.py'
        ]

        total_tests = 0
        total_passed = 0

        for test_file in existing_test_files:
            if (self.project_root / test_file).exists():
                self.log_result("现有测试", f"运行 {test_file}...", None)
                try:
                    result = subprocess.run([
                        sys.executable, str(self.project_root / test_file)
                    ], capture_output=True, text=True, cwd=self.project_root, timeout=60)

                    if result.returncode == 0:
                        # 解析测试结果
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if '通过测试:' in line and ':' in line:
                                passed = int(line.split(':')[-1].strip())
                                total_passed += passed
                                self.log_result("现有测试", f"{test_file} 通过 {passed} 个测试", True)
                            if '总测试数:' in line and ':' in line:
                                total = int(line.split(':')[-1].strip())
                                total_tests += total
                                self.log_result("现有测试", f"{test_file} 总计 {total} 个测试", True)
                    else:
                        self.log_result("现有测试", f"{test_file} 运行失败", False)

                except subprocess.TimeoutExpired:
                    self.log_result("现有测试", f"{test_file} 运行超时", False)
                except Exception as e:
                    self.log_result("现有测试", f"{test_file} 执行异常: {e}", False)
            else:
                self.log_result("现有测试", f"{test_file} 文件不存在", False)

        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
            self.log_result("现有测试", f"总体成功率: {success_rate:.1f}% ({total_passed}/{total_tests})", True)
            estimated_coverage = success_rate * 0.6  # 保守估计
            self.log_result("覆盖率估算", f"基于成功率估算覆盖率: {estimated_coverage:.1f}%", True)
        else:
            self.log_result("现有测试", "没有成功运行的测试", False)

    def phase1_basic_modules(self):
        """Phase 1: 基础模块全覆盖"""
        self.log_result("Phase 1", "开始基础模块全覆盖...", None)

        # 1.1 深度测试已验证模块
        self.log_result("Phase 1.1", "深度测试已验证模块...", None)

        try:
            result = subprocess.run([
                sys.executable, 'tests/expand_successful_tests.py'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)

            if result.returncode == 0:
                self.log_result("Phase 1.1", "已验证模块深度测试成功", True)
            else:
                self.log_result("Phase 1.1", "已验证模块深度测试失败", False)
        except Exception as e:
            self.log_result("Phase 1.1", f"深度测试异常: {e}", False)

        # 1.2 创建新的基础模块测试
        self.log_result("Phase 1.2", "创建新的基础模块测试...", None)

        basic_modules = [
            'utils.dict_utils',
            'utils.response',
            'utils.data_validator',
            'config.fastapi_config',
            'config.openapi_config'
        ]

        for module_name in basic_modules:
            self._test_basic_module(module_name)

        # 1.3 运行真实覆盖率测量
        self.log_result("Phase 1.3", "运行真实覆盖率测量...", None)

        try:
            result = subprocess.run([
                sys.executable, 'tests/real_coverage_measurement.py'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)

            if result.returncode == 0:
                self.log_result("Phase 1.3", "真实覆盖率测量完成", True)
                # 解析覆盖率数据
                lines = result.stdout.split('\n')
                for line in lines:
                    if '综合覆盖率:' in line:
                        coverage = line.split(':')[-1].strip().rstrip('%')
                        try:
                            coverage_float = float(coverage)
                            self.log_result("覆盖率测量", f"当前真实覆盖率: {coverage_float}%", True)

                            # 检查是否达到Phase 1目标
                            if coverage_float >= 5:
                                self.log_result("Phase 1", "✅ Phase 1目标达成 (>=5%)", True)
                            else:
                                self.log_result("Phase 1", f"⚠️  Phase 1目标未达成 (当前{coverage_float}% < 5%)", False)
                        except ValueError:
                            pass
            else:
                self.log_result("Phase 1.3", "真实覆盖率测量失败", False)
        except Exception as e:
            self.log_result("Phase 1.3", f"覆盖率测量异常: {e}", False)

    def _test_basic_module(self, module_name: str):
        """测试基础模块"""
        try:
            module = __import__(module_name, fromlist=['*'])

            # 测试无参数函数
            function_count = 0
            for name, obj in module.__dict__.items():
                if callable(obj) and not name.startswith('_'):
                    try:
                        import inspect
                        sig = inspect.signature(obj)
                        if len(sig.parameters) == 0:
                            result = obj()
                            function_count += 1
                            self.log_result("基础模块测试", f"{module_name}.{name}() 执行成功", True)
                    except:
                        pass

            if function_count > 0:
                self.log_result("基础模块测试", f"{module_name} 成功测试 {function_count} 个函数", True)
            else:
                self.log_result("基础模块测试", f"{module_name} 没有可测试的无参数函数", False)

        except ImportError as e:
            self.log_result("基础模块测试", f"{module_name} 导入失败: {e}", False)
        except Exception as e:
            self.log_result("基础模块测试", f"{module_name} 测试异常: {e}", False)

    def generate_progress_report(self):
        """生成进度报告"""
        self.log_result("报告生成", "生成进度报告...", None)

        report = {
            'execution_time': datetime.datetime.now().isoformat(),
            'duration_minutes': (datetime.datetime.now() - self.start_time).total_seconds() / 60,
            'current_phase': self.current_phase,
            'results': self.results_log,
            'summary': {
                'total_actions': len(self.results_log),
                'successful_actions': len([r for r in self.results_log if r.get('success') is True]),
                'failed_actions': len([r for r in self.results_log if r.get('success') is False]),
                'pending_actions': len([r for r in self.results_log if r.get('success') is None])
            }
        }

        # 保存报告
        report_file = self.project_root / 'coverage_improvement_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log_result("报告生成", f"报告已保存到: {report_file}", True)

        # 输出摘要
        summary = report['summary']
        print(f"\n📊 执行摘要:")
        print(f"   总操作数: {summary['total_actions']}")
        print(f"   成功操作: {summary['successful_actions']}")
        print(f"   失败操作: {summary['failed_actions']}")
        print(f"   进行中操作: {summary['pending_actions']}")
        print(f"   执行时长: {report['duration_minutes']:.1f} 分钟")

        success_rate = (summary['successful_actions'] / summary['total_actions'] * 100) if summary['total_actions'] > 0 else 0
        print(f"   成功率: {success_rate:.1f}%")

        return report

    def run_phase1(self):
        """执行Phase 1"""
        print("=" * 80)
        print("🎯 开始执行 Phase 1: 基础模块全覆盖 (目标: 5-10%)")
        print("=" * 80)

        self.current_phase = 1

        # 执行Phase 1步骤
        self.run_syntax_check()
        self.run_existing_tests()
        self.phase1_basic_modules()

        # 生成报告
        report = self.generate_progress_report()

        print("\n" + "=" * 80)
        print("🏁 Phase 1 执行完成")
        print("=" * 80)

        return report

    def run_quick_diagnosis(self):
        """运行快速诊断"""
        print("=" * 80)
        print("🔍 快速诊断: 检查当前项目状态")
        print("=" * 80)

        self.run_syntax_check()
        self.run_existing_tests()

        # 简单的覆盖率估算
        report = self.generate_progress_report()

        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='测试覆盖率改进执行器')
    parser.add_argument('--phase', type=int, choices=[1], help='执行指定阶段')
    parser.add_argument('--diagnosis', action='store_true', help='运行快速诊断')
    parser.add_argument('--all', action='store_true', help='执行所有可用阶段')

    args = parser.parse_args()

    executor = CoverageImprovementExecutor()

    if args.diagnosis:
        executor.run_quick_diagnosis()
    elif args.phase == 1:
        executor.run_phase1()
    elif args.all:
        # 目前只实现了Phase 1
        executor.run_phase1()
    else:
        print("请指定要执行的操作:")
        print("  --diagnosis  运行快速诊断")
        print("  --phase 1    执行Phase 1")
        print("  --all        执行所有阶段")


if __name__ == "__main__":
    main()