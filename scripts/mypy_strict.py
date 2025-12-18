#!/usr/bin/env python3
"""
Mypy严格模式检查脚本
以正确的方式运行mypy严格模式检查
"""

import subprocess
import sys
from pathlib import Path

def run_mypy_strict():
    """运行mypy严格模式检查"""
    project_root = Path(__file__).parent.parent

    # 设置环境变量
    env = {
        "MYPYPATH": str(project_root),
        "PYTHONPATH": str(project_root)
    }

    # 构建mypy命令
    cmd = [
        sys.executable, "-m", "mypy",
        "--config-file", str(project_root / "pyproject.toml"),
        "src/ml",
        "src/services",
        "src/api",
        "src/database",
        "src/constants",
        "src/utils",
        "--show-error-codes",
        "--no-error-summary"
    ]

    try:
        # 运行mypy
        result = subprocess.run(
            cmd,
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        # 分析结果
        errors = []
        warnings = []
        notes = []

        for line in result.stdout.split('\n'):
            if line.strip():
                if 'error:' in line:
                    errors.append(line)
                elif 'warning:' in line:
                    warnings.append(line)
                elif 'note:' in line:
                    notes.append(line)

        # 打印结果
        print(f"🔍 Mypy严格模式检查结果")
        print(f"=" * 60)
        print(f"错误: {len(errors)}")
        print(f"警告: {len(warnings)}")
        print(f"说明: {len(notes)}")

        if errors:
            print(f"\n❌ 错误详情:")
            for error in errors:
                print(f"  {error}")

        if warnings:
            print(f"\n⚠️  警告详情:")
            for warning in warnings:
                print(f"  {warning}")

        # 返回退出码
        if errors:
            print(f"\n❌ Mypy检查失败，发现 {len(errors)} 个错误")
            return 1
        else:
            print(f"\n✅ Mypy检查通过！")
            return 0

    except subprocess.TimeoutExpired:
        print("❌ Mypy检查超时")
        return 1
    except Exception as e:
        print(f"❌ Mypy检查异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_mypy_strict())