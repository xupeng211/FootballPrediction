#!/usr/bin/env python3
"""
备份当前Python环境
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def backup_environment():
    """备份当前环境"""
    print("📦 PH2-1: 备份当前环境...")
    print("="*60)

    # 创建备份目录
    backup_dir = Path("environment_backup")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)

    print(f"📁 备份目录: {backup_path}")

    # 1. 备份已安装的包列表
    print("\n1️⃣ 备份包列表...")

    # 完整列表
    result = subprocess.run([sys.executable, "-m", "pip", "list"],
                          capture_output=True, text=True)
    full_list = backup_path / "pip_list_full.txt"
    with open(full_list, 'w') as f:
        f.write(result.stdout)
    print(f"  ✅ 完整包列表: {full_list}")

    # requirements格式
    result = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                          capture_output=True, text=True)
    requirements = backup_path / "requirements.txt"
    with open(requirements, 'w') as f:
        f.write(result.stdout)
    print(f"  ✅ requirements.txt: {requirements}")

    # 仅项目相关包
    project_deps = backup_path / "project_dependencies.txt"
    result = subprocess.run([sys.executable, "-m", "pipdeptree"],
                          capture_output=True, text=True)
    with open(project_deps, 'w') as f:
        f.write(result.stdout)
    print(f"  ✅ 依赖树: {project_deps}")

    # 2. 备份关键配置文件
    print("\n2️⃣ 备份配置文件...")

    config_files = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-minimal.txt",
        "requirements.lock",
        ".env.production",
        "Pipfile",
        "setup.cfg"
    ]

    config_backup = backup_path / "configs"
    config_backup.mkdir(exist_ok=True)

    for config_file in config_files:
        src = Path(config_file)
        if src.exists():
            dst = config_backup / config_file
            subprocess.run(["cp", str(src), str(dst)], check=True)
            print(f"  ✅ {config_file}")

    # 3. 备份虚拟环境信息
    print("\n3️⃣ 备份环境信息...")

    env_info = {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": sys.platform,
        "timestamp": timestamp,
        "backup_path": str(backup_path),
        "pip_version": subprocess.run([sys.executable, "-m", "pip", "--version"],
                                   capture_output=True, text=True).stdout.strip()
    }

    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and
        sys.base_prefix != sys.prefix):
        env_info["virtual_env"] = True
        env_info["venv_path"] = sys.prefix
    else:
        env_info["virtual_env"] = False
        env_info["venv_path"] = None

    env_file = backup_path / "environment_info.json"
    with open(env_file, 'w') as f:
        json.dump(env_info, f, indent=2, default=str)
    print(f"  ✅ 环境信息: {env_file}")

    # 4. 创建恢复脚本
    print("\n4️⃣ 创建恢复脚本...")

    restore_script = backup_path / "restore_environment.sh"
    restore_content = f"""#!/bin/bash
# 环境恢复脚本 - 备份时间: {timestamp}

echo "🔄 恢复Python环境..."
echo "备份时间: {timestamp}"
echo "备份路径: {backup_path}"

# 1. 创建虚拟环境（如果需要）
if [ "$1" = "--venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv_backup
    source venv_backup/bin/activate
fi

# 2. 升级pip
python -m pip install --upgrade pip

# 3. 安装包
echo "📦 安装备份的包..."
python -m pip install -r requirements.txt

echo "✅ 环境恢复完成！"
echo "如需激活虚拟环境，请运行: source venv_backup/bin/activate"
"""

    with open(restore_script, 'w') as f:
        f.write(restore_content)

    # 设置执行权限
    subprocess.run(["chmod", "+x", str(restore_script)])
    print(f"  ✅ 恢复脚本: {restore_script}")

    # 5. 生成备份报告
    print("\n5️⃣ 生成备份报告...")

    report = {
        "backup_timestamp": timestamp,
        "backup_path": str(backup_path),
        "total_packages": len(result.stdout.split('\n')) if result.stdout else 0,
        "python_version": sys.version,
        "is_virtual_env": env_info["virtual_env"],
        "files_backed_up": [
            str(full_list),
            str(requirements),
            str(project_deps),
            str(env_file),
            str(restore_script)
        ]
    }

    report_file = backup_path / "backup_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  ✅ 备份报告: {report_file}")

    # 6. 创建最新备份的符号链接
    latest = backup_dir / "latest"
    if latest.exists():
        latest.unlink()
    latest.symlink_to(backup_path)

    print(f"\n🎉 环境备份完成！")
    print(f"📂 备份位置: {backup_path}")
    print(f"🔗 最新备份: {latest}")
    print(f"\n📋 恢复步骤:")
    print(f"  1. cd {backup_path}")
    print(f"  2. bash restore_environment.sh")
    print(f"  3. (可选) bash restore_environment.sh --venv")

    return backup_path

if __name__ == "__main__":
    backup_path = backup_environment()