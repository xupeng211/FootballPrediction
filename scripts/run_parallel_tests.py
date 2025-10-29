#!/usr/bin/env python3
"""
并行测试运行脚本
使用 pytest-xdist 实现并行测试执行
"""

import os
import sys
import subprocess
import time
import multiprocessing
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_cpu_count():
    """获取可用的CPU核心数"""
    cpu_count = multiprocessing.cpu_count()
    # 保留一个核心给系统
    return max(1, cpu_count - 1)


def run_parallel_tests(test_path="tests/unit", workers=None, coverage=False):
    """运行并行测试"""

    # 默认使用 CPU 核心数
    if workers is None:
        workers = get_cpu_count()
        print(f"🔍 自动检测到 {workers} 个CPU核心")

    print(f"\n{'='*60}")
    print("🚀 并行测试执行器")
    print(f"📊 使用 {workers} 个并行进程")
    print(f"{'='*60}")

    # 构建命令
    cmd = [
        "python",
        "-m",
        "pytest",
        test_path,
        "-n",
        str(workers),
        "--dist=loadscope",  # 按测试类/模块分配
        "--tb=short",
        "-q",
    ]

    # 添加覆盖率
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-branch"])

    # 设置环境变量优化
    env = os.environ.copy()
    env.update(
        {
            "PYTEST_XDIST_AUTO_NUM_WORKERS": str(workers),
            "PYTEST_XDIST_DISABLE_RSYNC": "1",
            "PYTHONPATH": str(project_root),
        }
    )

    # 执行测试
    start_time = time.time()
    try:
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=project_root,
            env=env,
            text=True,
            timeout=300,  # 5分钟超时
        )

        elapsed = time.time() - start_time
        print(f"\n⏱️  测试完成，耗时: {elapsed:.2f}秒")

        # 解析结果
        output = result.stdout + result.stderr

        # 查找测试统计
        for line in output.split("\n"):
            if "passed" in line and ("failed" in line or "error" in line):
                print(f"📊 {line.strip()}")
                break

        # 查找覆盖率
        if coverage:
            for line in output.split("\n"):
                if "TOTAL" in line and "%" in line:
                    print(f"🎯 {line.strip()}")
                    break

        # 性能分析
        print("\n📈 性能分析:")
        print(f"  并行进程数: {workers}")
        print(f"  总耗时: {elapsed:.2f}秒")
        print(f"  平均每进程: {elapsed/workers:.2f}秒")

        # 估算加速比
        if hasattr(result, "returncode") and result.returncode == 0:
            print("  ✅ 所有测试通过")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("\n⏰ 测试超时（超过5分钟）")
        print("建议：")
        print("  1. 减少并行进程数: --workers 2")
        print("  2. 运行特定测试模块")
        print("  3. 使用 --maxfail 限制失败数量")
        return False

    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        return False

    except Exception as e:
        print(f"\n❌ 执行错误: {e}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="并行测试运行器")
    parser.add_argument("--workers", type=int, help="并行进程数（默认：CPU核心数-1）")
    parser.add_argument("--path", default="tests/unit", help="测试路径（默认：tests/unit）")
    parser.add_argument("--coverage", action="store_true", help="运行覆盖率测试")
    parser.add_argument("--fast", action="store_true", help="快速模式（只运行单元测试）")

    args = parser.parse_args()

    # 快速模式
    if args.fast:
        args.path = "tests/unit/adapters tests/unit/utils tests/unit/services"

    # 检查 pytest-xdist
    try:
        import xdist
    except ImportError:
        print("❌ 缺少 pytest-xdist 插件")
        print("请安装: pip install pytest-xdist")
        sys.exit(1)

    # 运行测试
    success = run_parallel_tests(test_path=args.path, workers=args.workers, coverage=args.coverage)

    if success:
        print("\n✅ 并行测试执行成功！")
        sys.exit(0)
    else:
        print("\n❌ 并行测试执行失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
