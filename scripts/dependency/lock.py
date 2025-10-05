#!/usr/bin/env python3
"""
依赖锁定工具
确保所有依赖都有固定版本
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def freeze_dependencies():
    """冻结当前虚拟环境中的所有依赖"""
    print("🔒 正在冻结依赖...")

    # 获取所有已安装的包
    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"❌ 冻结依赖失败: {result.stderr}")
        return False

    # 写入锁文件
    lock_file = Path("requirements.lock.txt")
    header = f"""# 锁定依赖 - 自动生成
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 虚拟环境: .venv
# Python版本: {sys.version}
#
# 生成命令: pip freeze > requirements.lock.txt
# 警告: 不要手动编辑此文件
#
"""

    with open(lock_file, "w") as f:
        f.write(header)
        f.write(result.stdout)

    print(f"✅ 依赖已锁定到 {lock_file}")
    print(f"📦 总计 {len(result.stdout.splitlines())} 个包")
    return True


def verify_lock():
    """验证锁文件是否与当前环境一致"""
    print("🔍 验证依赖一致性...")

    lock_file = Path("requirements.lock.txt")
    if not lock_file.exists():
        print("❌ 锁文件不存在")
        return False

    # 读取锁文件
    with open(lock_file, "r") as f:
        lines = f.readlines()

    # 提取包名和版本
    locked_packages = {}
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        if "==" in line:
            name, version = line.strip().split("==", 1)
            locked_packages[name.lower()] = version

    # 获取当前安装的包
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        text=True,
    )

    current_packages = {}
    for line in result.stdout.splitlines():
        if "==" in line:
            name, version = line.strip().split("==", 1)
            current_packages[name.lower()] = version

    # 比较差异
    mismatches = []
    for name, version in current_packages.items():
        if name in locked_packages:
            if locked_packages[name] != version:
                mismatches.append(
                    f"{name}: 锁定={locked_packages[name]}, 当前={version}"
                )
        else:
            mismatches.append(f"{name}: 未锁定")

    if mismatches:
        print("❌ 发现不一致:")
        for mismatch in mismatches[:10]:  # 只显示前10个
            print(f"  - {mismatch}")
        if len(mismatches) > 10:
            print(f"  ... 还有 {len(mismatches) - 10} 个不一致")
        return False
    else:
        print("✅ 所有依赖一致")
        return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="依赖管理工具")
    parser.add_argument("action", choices=["lock", "verify", "freeze"], help="操作类型")

    args = parser.parse_args()

    if args.action in ["lock", "freeze"]:
        freeze_dependencies()
    elif args.action == "verify":
        verify_lock()


if __name__ == "__main__":
    main()
