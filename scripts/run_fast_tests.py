#!/usr/bin/env python3
"""
快速测试运行脚本
实现分层测试策略，优化测试执行速度
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class FastTestRunner:
    """快速测试运行器"""

    def __init__(self):
        self.project_root = project_root
        self.results = {}

    def run_command(self, cmd, description, timeout=60):
        """运行命令并记录结果"""
        print(f"\n{'='*60}")
        print(f"🚀 {description}")
        print(f"{'='*60}")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )

            elapsed = time.time() - start_time

            # 解析输出
            if result.returncode == 0:
                print(f"✅ 成功！耗时: {elapsed:.2f}秒")

                # 提取测试统计
                output = result.stdout
                if "passed" in output:
                    for line in output.split('\n'):
                        if 'passed' in line and ('failed' in line or 'error' in line or 'skipped' in line):
                            print(f"📊 {line.strip()}")
                            break

                # 提取覆盖率
                if "TOTAL" in output:
                    for line in output.split('\n'):
                        if "TOTAL" in line and "%" in line:
                            print(f"🎯 覆盖率: {line.strip()}")
                            self.results['coverage'] = line.strip()
                            break

            else:
                print(f"❌ 失败！耗时: {elapsed:.2f}秒")
                if result.stderr:
                    print(f"错误信息: {result.stderr[:200]}...")

            self.results[description] = {
                'success': result.returncode == 0,
                'time': elapsed,
                'output': result.stdout[:500] if result.stdout else ''
            }

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"⏰ 超时！超过 {timeout} 秒")
            self.results[description] = {
                'success': False,
                'time': timeout,
                'output': 'TIMEOUT'
            }
            return False

        except Exception as e:
            print(f"❌ 异常: {e}")
            self.results[description] = {
                'success': False,
                'time': 0,
                'output': str(e)
            }
            return False

    def run_level_1_tests(self):
        """Level 1: 核心单元测试（< 30秒）"""
        print("\n🔍 Level 1: 运行核心单元测试")

        # 测试适配器模块
        cmd1 = "python -m pytest tests/unit/adapters/ -q --tb=no"
        self.run_command(cmd1, "适配器模块测试", timeout=30)

        # 测试核心工具
        cmd2 = "python -m pytest tests/unit/utils/test_class_methods.py tests/unit/utils/test_retry.py -q --tb=no"
        self.run_command(cmd2, "核心工具测试", timeout=30)

        # 测试基础服务
        cmd3 = "python -m pytest tests/unit/services/test_data_processing.py::TestDataProcessor::test_process_batch_data -q --tb=no"
        self.run_command(cmd3, "基础服务测试", timeout=30)

    def run_level_2_tests(self):
        """Level 2: 扩展单元测试（< 60秒）"""
        print("\n🔍 Level 2: 运行扩展单元测试")

        # 测试数据库模型
        cmd1 = "python -m pytest tests/unit/database/models/ -q --tb=no"
        self.run_command(cmd1, "数据库模型测试", timeout=60)

        # 测试API组件
        cmd2 = "python -m pytest tests/unit/api/test_health_check.py tests/unit/api/test_dependencies.py -q --tb=no"
        self.run_command(cmd2, "API组件测试", timeout=60)

        # 测试任务模块
        cmd3 = "python -m pytest tests/unit/tasks/test_error_logger.py -q --tb=no"
        self.run_command(cmd3, "任务模块测试", timeout=60)

    def run_level_3_tests(self):
        """Level 3: 集成测试（< 120秒）"""
        print("\n🔍 Level 3: 运行集成测试")

        # 测试完整的数据库模块
        cmd1 = "python -m pytest tests/unit/database/ -k 'not performance' -q --tb=no"
        self.run_command(cmd1, "数据库集成测试", timeout=120)

        # 测试缓存模块
        cmd2 = "python -m pytest tests/unit/cache/ -q --tb=no --ignore=tests/unit/cache/test_mock_redis.py"
        self.run_command(cmd2, "缓存模块测试", timeout=120)

    def run_coverage_check(self):
        """运行覆盖率检查"""
        print("\n📊 运行覆盖率检查")

        # 只对通过的测试运行覆盖率
        cmd = "python -m pytest tests/unit/adapters/ tests/unit/utils/test_class_methods.py tests/unit/utils/test_retry.py --cov=src --cov-report=term-missing --tb=no -q"
        self.run_command(cmd, "覆盖率检查", timeout=120)

    def run_all_levels(self, max_level=3):
        """运行所有级别的测试"""
        total_start = time.time()

        print(f"\n{'#'*60}")
        print("# 🚀 快速测试执行器")
        print("# 执行分层测试策略，优化速度")
        print(f"#{'#'*60}")

        if max_level >= 1:
            self.run_level_1_tests()

        if max_level >= 2:
            self.run_level_2_tests()

        if max_level >= 3:
            self.run_level_3_tests()

        # 运行覆盖率检查
        self.run_coverage_check()

        # 总结
        total_time = time.time() - total_start
        self.print_summary(total_time)

    def print_summary(self, total_time):
        """打印测试总结"""
        print(f"\n{'='*60}")
        print("📊 测试执行总结")
        print(f"{'='*60}")

        success_count = sum(1 for r in self.results.values() if r['success'])
        total_count = len(self.results)

        print(f"✅ 成功: {success_count}/{total_count}")
        print(f"⏱️  总耗时: {total_time:.2f}秒")

        if 'coverage' in self.results:
            print(f"🎯 覆盖率: {self.results['coverage']}")

        print("\n详细结果:")
        for desc, result in self.results.items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {desc}: {result['time']:.2f}秒")

        # 建议
        print("\n💡 建议:")
        if total_time > 300:
            print("- 考虑使用并行测试: pytest -n auto")
            print("- 考虑跳过慢速测试: pytest -m 'not slow'")
        if success_count < total_count:
            print("- 修复失败的测试以提升代码质量")
        if 'coverage' not in self.results:
            print("- 运行覆盖率检查以了解测试覆盖情况")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="快速测试运行器")
    parser.add_argument(
        "--level",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="测试级别 (1: 快速, 2: 中等, 3: 完整)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="只运行覆盖率检查"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="使用并行执行 (需要 pytest-xdist)"
    )

    args = parser.parse_args()

    runner = FastTestRunner()

    if args.coverage:
        runner.run_coverage_check()
    else:
        # 设置并行执行参数
        if args.parallel:
            os.environ['PYTEST_ADDOPTS'] = '-n auto'

        runner.run_all_levels(max_level=args.level)


if __name__ == "__main__":
    main()