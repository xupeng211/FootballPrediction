#!/usr/bin/env python3
"""
核心功能稳定性验证工具 - 路径A阶段1
验证Issue #88成果后的系统稳定性
"""

import subprocess
import sys
import os
import time
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.insert(0, '.')

class CoreStabilityValidator:
    def __init__(self):
        self.results = {
            'tests': {'status': 'pending', 'details': {}},
            'code_quality': {'status': 'pending', 'details': {}},
            'coverage': {'status': 'pending', 'details': {}},
            'core_functionality': {'status': 'pending', 'details': {}},
            'overall_status': 'pending'
        }

    def run_test_validation(self):
        """验证测试状态"""
        print("🧪 验证测试状态...")
        print("=" * 40)

        try:
            # 运行核心测试套件
            test_files = [
                'test_basic_pytest.py',
                'test_core_config_enhanced.py',
                'test_models_prediction_fixed.py',
                'test_api_routers_enhanced.py',
                'test_database_models_fixed.py'
            ]

            start_time = time.time()
            result = subprocess.run(
                ["pytest"] + test_files + ["-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120
            )
            duration = time.time() - start_time

            if result.returncode == 0:
                # 解析测试结果
                lines = result.stdout.split('\n')
                passed = 0
                failed = 0
                total = 0

                for line in lines:
                    if 'passed' in line and 'failed' in line:
                        # 提取测试统计
                        parts = line.split()
                        for part in parts:
                            if 'passed' in part:
                                try:
                                    passed = int(part.split('passed')[0])
                                except (ValueError, IndexError):
                                    passed = 0
                            elif 'failed' in part:
                                try:
                                    failed = int(part.split('failed')[0])
                                except (ValueError, IndexError):
                                    failed = 0
                        total = passed + failed
                        break

                # 如果解析失败，使用另一种方法
                if total == 0:
                    # 查找包含数字的行
                    for line in lines:
                        if '=' in line and 'passed' in line:
                            try:
                                # 类似 "37 passed, 2 failed in 0.82s"
                                if 'passed' in line:
                                    passed = int(line.split('passed')[0].split()[-1])
                                if 'failed' in line:
                                    failed = int(line.split('failed')[0].split()[-1])
                                total = passed + failed
                                break
                            except (ValueError, IndexError):
                                continue

                self.results['tests'] = {
                    'status': '✅ 通过',
                    'details': {
                        'total_tests': total,
                        'passed': passed,
                        'failed': failed,
                        'duration': f"{duration:.2f}s",
                        'pass_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%"
                    }
                }
                print(f"✅ 测试验证通过: {passed}/{total} ({(passed/total*100):.1f}%)")
                print(f"⏱️  执行时间: {duration:.2f}秒")
            else:
                self.results['tests'] = {
                    'status': '❌ 失败',
                    'details': {
                        'error': result.stderr[:500],
                        'exit_code': result.returncode
                    }
                }
                print(f"❌ 测试验证失败")

        except subprocess.TimeoutExpired:
            self.results['tests'] = {
                'status': '⏰ 超时',
                'details': {'error': '测试执行超时 (120秒)'}
            }
            print(f"⏰ 测试执行超时")

        except Exception as e:
            self.results['tests'] = {
                'status': '💥 异常',
                'details': {'error': str(e)}
            }
            print(f"💥 测试验证异常: {e}")

    def run_code_quality_validation(self):
        """验证代码质量"""
        print("\n🔍 验证代码质量...")
        print("=" * 40)

        try:
            # 检查Ruff
            result = subprocess.run(
                ["ruff", "check", "src/", "--statistics"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.results['code_quality'] = {
                    'status': '✅ 优秀',
                    'details': {
                        'ruff_errors': 0,
                        'status': '零错误'
                    }
                }
                print("✅ Ruff检查通过: 零错误")
            else:
                # 解析错误统计
                lines = result.stdout.split('\n')
                errors = 0
                for line in lines:
                    if 'Found' in line and 'errors' in line:
                        errors = int(line.split('errors')[0].split()[-1])
                        break

                self.results['code_quality'] = {
                    'status': '⚠️ 需要改进',
                    'details': {
                        'ruff_errors': errors,
                        'status': f'{errors}个错误'
                    }
                }
                print(f"⚠️ 发现 {errors} 个代码质量问题")

        except Exception as e:
            self.results['code_quality'] = {
                'status': '💥 异常',
                'details': {'error': str(e)}
            }
            print(f"💥 代码质量检查异常: {e}")

    def run_coverage_validation(self):
        """验证覆盖率稳定性"""
        print("\n📊 验证覆盖率...")
        print("=" * 40)

        try:
            result = subprocess.run(
                ["pytest"] + [
                    'test_basic_pytest.py',
                    'test_core_config_enhanced.py',
                    'test_models_prediction_fixed.py',
                    'test_api_routers_enhanced.py',
                    'test_database_models_fixed.py'
                ] + ["--cov=src", "--cov-report=json:coverage_validation.json", "--quiet"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and Path("coverage_validation.json").exists():
                with open("coverage_validation.json", 'r') as f:
                    coverage_data = json.load(f)

                total_coverage = coverage_data['totals']['percent_covered']

                self.results['coverage'] = {
                    'status': '✅ 稳定',
                    'details': {
                        'total_coverage': f"{total_coverage:.2f}%",
                        'target_met': total_coverage >= 15.0,
                        'lines_covered': coverage_data['totals']['covered_lines'],
                        'lines_total': coverage_data['totals']['num_statements']
                    }
                }

                print(f"✅ 覆盖率稳定: {total_coverage:.2f}%")
                print(f"📈 目标达成: {'是' if total_coverage >= 15.0 else '否'} (目标: 15%)")

                # 清理临时文件
                Path("coverage_validation.json").unlink(missing_ok=True)
            else:
                self.results['coverage'] = {
                    'status': '❌ 失败',
                    'details': {'error': '覆盖率报告生成失败'}
                }
                print("❌ 覆盖率验证失败")

        except Exception as e:
            self.results['coverage'] = {
                'status': '💥 异常',
                'details': {'error': str(e)}
            }
            print(f"💥 覆盖率验证异常: {e}")

    def run_core_functionality_validation(self):
        """验证核心功能可用性"""
        print("\n⚙️ 验证核心功能...")
        print("=" * 40)

        functionality_tests = []

        # 测试1: 基础模块导入
        try:
            from src.core.config import Config
            from src.models.prediction import PredictionResult
            from src.database.repositories.team_repository import TeamRepository
            functionality_tests.append(('模块导入', '✅ 通过'))
        except Exception as e:
            functionality_tests.append(('模块导入', f'❌ 失败: {e}'))

        # 测试2: 基础实例化
        try:
            config = Config()
            functionality_tests.append(('实例化', '✅ 通过'))
        except NameError:
            # 如果Config未定义，先导入
            try:
                from src.core.config import Config
                config = Config()
                functionality_tests.append(('实例化', '✅ 通过'))
            except Exception as e:
                functionality_tests.append(('实例化', f'❌ 失败: {e}'))
        except Exception as e:
            functionality_tests.append(('实例化', f'❌ 失败: {e}'))

        # 测试3: 测试环境
        try:
            import tests.conftest
            functionality_tests.append(('测试环境', '✅ 通过'))
        except Exception as e:
            functionality_tests.append(('测试环境', f'❌ 失败: {e}'))

        # 测试4: 文件完整性
        try:
            required_files = [
                'src/database/repositories/team_repository.py',
                'tests/conftest.py',
                'test_basic_pytest.py'
            ]
            missing_files = [f for f in required_files if not Path(f).exists()]

            if not missing_files:
                functionality_tests.append(('文件完整性', '✅ 通过'))
            else:
                functionality_tests.append(('文件完整性', f'❌ 缺失: {missing_files}'))
        except Exception as e:
            functionality_tests.append(('文件完整性', f'❌ 失败: {e}'))

        # 计算成功率
        total_tests = len(functionality_tests)
        passed_tests = len([t for t in functionality_tests if '✅' in t[1]])
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        self.results['core_functionality'] = {
            'status': '✅ 稳定' if success_rate >= 75 else '⚠️ 需要关注' if success_rate >= 50 else '❌ 不稳定',
            'details': {
                'total_checks': total_tests,
                'passed_checks': passed_tests,
                'success_rate': f"{success_rate:.1f}%",
                'tests': functionality_tests
            }
        }

        print(f"核心功能验证: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        for test_name, result in functionality_tests:
            print(f"  {test_name}: {result}")

    def calculate_overall_status(self):
        """计算总体状态"""
        print("\n🎯 计算总体状态...")
        print("=" * 40)

        status_scores = {
            '✅ 通过': 100,
            '✅ 优秀': 100,
            '✅ 稳定': 100,
            '⚠️ 需要改进': 70,
            '⚠️ 需要关注': 70,
            '❌ 失败': 0,
            '❌ 不稳定': 0,
            '💥 异常': 0,
            '⏰ 超时': 50
        }

        total_score = 0
        categories = 0

        for category, result in self.results.items():
            if category == 'overall_status':
                continue

            if 'status' in result:
                score = status_scores.get(result['status'], 0)
                total_score += score
                categories += 1
                print(f"  {category}: {result['status']} ({score}分)")

        if categories > 0:
            average_score = total_score / categories

            if average_score >= 90:
                overall_status = '🏆 优秀'
                recommendation = '系统状态优秀，可以继续推进后续工作'
            elif average_score >= 70:
                overall_status = '✅ 良好'
                recommendation = '系统状态良好，建议关注改进项'
            elif average_score >= 50:
                overall_status = '⚠️ 需要关注'
                recommendation = '系统需要改进，建议优先解决关键问题'
            else:
                overall_status = '❌ 需要修复'
                recommendation = '系统存在问题，需要立即修复'
        else:
            overall_status = '❓ 未知'
            recommendation = '无法确定系统状态'

        self.results['overall_status'] = {
            'status': overall_status,
            'score': f"{average_score:.1f}%" if categories > 0 else "N/A",
            'recommendation': recommendation,
            'categories_evaluated': categories
        }

        print(f"\n🏆 总体状态: {overall_status} ({average_score:.1f}%)")
        print(f"💡 建议: {recommendation}")

    def generate_validation_report(self):
        """生成验证报告"""
        print("\n📋 生成验证报告...")
        print("=" * 50)

        report = {
            'validation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'validator_version': '1.0.0',
            'results': self.results
        }

        # 保存报告
        report_file = Path('validation_report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ 验证报告已保存: {report_file}")

        return report

    def run_full_validation(self):
        """运行完整验证流程"""
        print("🚀 开始核心功能稳定性验证")
        print("=" * 60)

        start_time = time.time()

        # 执行所有验证
        self.run_test_validation()
        self.run_code_quality_validation()
        self.run_coverage_validation()
        self.run_core_functionality_validation()
        self.calculate_overall_status()

        duration = time.time() - start_time

        # 生成报告
        report = self.generate_validation_report()

        print(f"\n🎉 验证完成!")
        print(f"⏱️  总用时: {duration:.2f}秒")
        print(f"📊 总体状态: {self.results['overall_status']['status']}")
        print(f"💡 建议: {self.results['overall_status']['recommendation']}")

        return report

def main():
    """主函数"""
    validator = CoreStabilityValidator()
    return validator.run_full_validation()

if __name__ == "__main__":
    main()