#!/usr/bin/env python3
"""
系统性诊断测试问题
"""
import subprocess
import time
import os
from pathlib import Path

def run_command(cmd, timeout=30):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd="/home/user/projects/FootballPrediction"
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def diagnose_tests():
    """诊断测试问题"""
    print("=== 测试问题诊断 ===\n")

    # 1. 检查测试环境
    print("1. 检查Python环境...")
    ret, out, err = run_command("python --version")
    print(f"   Python版本: {out.strip()}")
    print(f"   当前工作目录: {os.getcwd()}")
    print(f"   虚拟环境: {os.getenv('VIRTUAL_ENV', 'None')}\n")

    # 2. 找出最慢的测试文件
    print("2. 查找最慢的测试文件...")
    test_dir = Path("tests/unit")
    test_files = list(test_dir.glob("*.py"))

    slow_files = []
    for test_file in test_files[:10]:  # 测试前10个文件
        print(f"   测试 {test_file.name}...")
        start = time.time()
        ret, out, err = run_command(f"python -m pytest {test_file} --tb=no -q --maxfail=1", timeout=15)
        elapsed = time.time() - start

        if elapsed > 5 or ret != 0:
            slow_files.append((test_file.name, elapsed, ret))
            status = "超时" if elapsed > 15 else ("失败" if ret != 0 else "通过")
            print(f"     状态: {status}, 耗时: {elapsed:.1f}秒")
        else:
            print(f"     状态: 通过, 耗时: {elapsed:.1f}秒")

    # 3. 分析具体的错误
    print(f"\n3. 问题文件分析:")
    for filename, elapsed, ret in sorted(slow_files, key=lambda x: x[1], reverse=True)[:5]:
        print(f"\n   文件: {filename}")
        if ret != 0:
            ret, out, err = run_command(f"python -m pytest tests/unit/{filename} --tb=short -v --maxfail=1", timeout=15)
            if "FAILED" in out:
                lines = out.split("\n")
                for i, line in enumerate(lines):
                    if "FAILED" in line and "ERROR" not in line:
                        print(f"     错误: {line}")
                        if i+1 < len(lines) and lines[i+1].strip():
                            print(f"     详情: {lines[i+1]}")
                        break

    # 4. 检查是否有导入问题
    print(f"\n4. 检查导入问题...")
    problematic_imports = [
        "src.models",
        "src.database",
        "src.cache.redis_manager",
        "src.tasks",
        "src.lineage"
    ]

    for imp in problematic_imports:
        print(f"   测试导入 {imp}...")
        start = time.time()
        ret, out, err = run_command(f'python -c "import {imp}"', timeout=10)
        elapsed = time.time() - start
        if ret != 0 or elapsed > 2:
            print(f"     问题: {'失败' if ret != 0 else '过慢'}, 耗时: {elapsed:.1f}秒")
            if err:
                print(f"     错误: {err.strip().split(chr(10))[0]}")
        else:
            print(f"     正常, 耗时: {elapsed:.2f}秒")

if __name__ == "__main__":
    diagnose_tests()