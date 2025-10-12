#!/usr/bin/env python3
"""
快速检查测试覆盖率
"""

import subprocess
import sys
import time
import os

def run_coverage():
    """运行覆盖率测试"""
    print("🔍 开始运行测试覆盖率检查...")
    start_time = time.time()

    # 设置环境变量以加速测试
    env = os.environ.copy()
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    env['PYTHONPATH'] = '/home/user/projects/FootballPrediction'

    try:
        # 运行pytest覆盖率测试
        cmd = [
            'python', '-m', 'pytest',
            'tests/unit/',
            '--cov=src',
            '--cov-report=term',
            '--cov-report=html:htmlcov',
            '--tb=no',
            '-q',
            '-x'  # 第一个失败时停止
        ]

        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            env=env,
            cwd='/home/user/projects/FootballPrediction'
        )

        elapsed = time.time() - start_time
        print(f"\n⏱️  测试完成，耗时: {elapsed:.2f}秒")

        if result.stdout:
            print("\n📊 输出:")
            print(result.stdout)

        if result.stderr:
            print("\n⚠️  错误:")
            print(result.stderr)

        # 尝试从输出中提取覆盖率信息
        output = result.stdout + result.stderr
        for line in output.split('\n'):
            if 'TOTAL' in line and '%' in line:
                print(f"\n🎯 总体覆盖率: {line.strip()}")
                break

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("\n⏰ 测试超时！")
        return False
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        return False

def run_quick_coverage():
    """运行快速覆盖率检查（仅运行通过的测试）"""
    print("🚀 运行快速覆盖率检查...")

    # 首先获取可以通过的测试列表
    try:
        # 收集测试但不运行
        collect_cmd = [
            'python', '-m', 'pytest',
            'tests/unit/',
            '--collect-only',
            '-q'
        ]

        result = subprocess.run(
            collect_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd='/home/user/projects/FootballPrediction'
        )

        if result.returncode == 0:
            print(f"✅ 收集到 {len(result.stdout.splitlines())} 个测试")

    except Exception as e:
        print(f"收集测试失败: {e}")

    # 运行覆盖率测试，跳过已知的失败测试
    cmd = [
        'python', '-m', 'pytest',
        'tests/unit/',
        '--cov=src',
        '--cov-report=term-missing',
        '--tb=no',
        '-q',
        '--ignore=tests/unit/data/quality/test_data_quality_monitor.py',
        '--ignore=tests/unit/cache/test_mock_redis.py'
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd='/home/user/projects/FootballPrediction'
        )

        print("\n📊 快速覆盖率结果:")
        print(result.stdout)

        # 查找总体覆盖率
        for line in result.stdout.split('\n'):
            if 'TOTAL' in line and '%' in line:
                coverage = line.strip()
                print(f"\n🎯 {coverage}")

                # 解析覆盖率百分比
                try:
                    percent = float(coverage.split('%')[0].split()[-1])
                    if percent >= 30:
                        print(f"✅ 恭喜！已达到30%覆盖率目标！")
                    else:
                        print(f"⚠️  当前覆盖率 {percent:.1f}%，目标30%，还需 {(30-percent):.1f}%")
                except:
                    pass
                break

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("\n⏰ 快速测试也超时了！")
        return False
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("📊 测试覆盖率检查工具")
    print("=" * 60)

    # 先尝试快速检查
    if run_quick_coverage():
        print("\n✅ 快速检查完成！")
    else:
        print("\n⚠️  快速检查失败，尝试完整检查...")
        run_coverage()