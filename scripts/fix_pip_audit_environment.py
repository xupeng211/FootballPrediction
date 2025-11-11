#!/usr/bin/env python3
"""
智能pip-audit环境修复工具
Intelligent pip-audit Environment Fix Tool

修复pip-audit检测系统Python而非虚拟环境的问题
"""

import os
import subprocess
from pathlib import Path


def find_venv_python():
    """查找虚拟环境Python路径"""
    current_dir = Path.cwd()

    # 检查常见的虚拟环境目录
    venv_dirs = [
        ".venv",
        "venv",
        "env",
        ".env",
        "virtualenv"
    ]

    for venv_dir in venv_dirs:
        venv_path = current_dir / venv_dir
        if venv_path.exists():
            python_path = venv_path / "bin" / "python3"
            if python_path.exists():
                return str(python_path)

    return None

def fix_pip_audit_environment():
    """修复pip-audit环境检测问题"""

    # 查找虚拟环境Python
    venv_python = find_venv_python()

    if venv_python:

        # 设置环境变量
        os.environ['PIPAPI_PYTHON_LOCATION'] = venv_python

        # 重新运行pip-audit
        try:
            result = subprocess.run(
                ['pip-audit'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                pass
            else:
                pass

        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
    else:
        pass

def create_environment_fix_script():
    """创建环境修复脚本"""
    script_content = '''#!/bin/bash
# pip-audit环境修复脚本
# pip-audit Environment Fix Script

echo "🔧 修复pip-audit环境检测问题..."

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 检测到虚拟环境: $VIRTUAL_ENV"

    # 设置pip-audit环境变量
    export PIPAPI_PYTHON_LOCATION="$VIRTUAL_ENV/bin/python"
    echo "✅ 设置 PIPAPI_PYTHON_LOCATION=$PIPAPI_PYTHON_LOCATION"

    # 运行pip-audit
    echo "\n🔍 运行pip-audit..."
    pip-audit
else
    echo "❌ 未检测到虚拟环境"
    echo "💡 请先激活虚拟环境:"
    echo "   source .venv/bin/activate"
    echo "   然后重新运行此脚本"
fi
'''

    script_path = Path("scripts/fix_pip_audit_environment.sh")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    # 设置执行权限
    os.chmod(script_path, 0o755)

def main():
    """主函数"""

    # 方法1: 直接修复
    fix_pip_audit_environment()

    # 方法2: 创建修复脚本
    create_environment_fix_script()


if __name__ == "__main__":
    main()
