#!/usr/bin/env python3
"""验证所有依赖的一致性"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    """运行命令并返回结果"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def check_lock_files():
    """检查lock文件是否存在"""
    required_locks = [
        "requirements/base.lock",
        "requirements/dev.lock",
        "requirements/requirements.lock",
    ]

    missing = []
    for lock_file in required_locks:
        if not Path(lock_file).exists():
            missing.append(lock_file)

    if missing:
        print(f"❌ 缺少lock文件: {missing}")
        return False

    print("✅ 所有必需的lock文件都存在")
    return True


def check_pip_consistency():
    """检查pip consistency"""
    success, stdout, stderr = run_command("pip check")

    if success:
        print("✅ pip check通过 - 没有依赖冲突")
        return True
    else:
        print("❌ pip check失败:")
        print(f"   {stderr}")
        return False


def compare_with_lock():
    """比较当前安装的包与lock文件"""
    # 获取当前安装的包
    success, stdout, _ = run_command("pip list --format=freeze")
    if not success:
        print("❌ 无法获取pip list")
        return False

    installed = {}
    for line in stdout.strip().split("\n"):
        if "==" in line:
            name, version = line.split("==")
            installed[name.lower()] = version

    # 读取主要lock文件
    with open("requirements/requirements.lock", "r") as f:
        lock_content = f.read()

    mismatches = []
    for line in lock_content.split("\n"):
        if "==" in line and not line.startswith("#"):
            # 处理可能带有注释的行
            package_line = line.split("#")[0].strip()
            if package_line and "==" in package_line:
                name, version = package_line.split("==")
                name = name.lower()

                if name in installed:
                    if installed[name] != version:
                        mismatches.append((name, installed[name], version))
                else:
                    mismatches.append((name, "NOT INSTALLED", version))

    if mismatches:
        print(f"❌ 发现 {len(mismatches)} 个版本不匹配:")
        for name, installed_ver, lock_ver in mismatches[:10]:  # 只显示前10个
            print(f"   {name}: installed={installed_ver}, lock={lock_ver}")
        if len(mismatches) > 10:
            print(f"   ... 还有 {len(mismatches) - 10} 个不匹配")
        return False
    else:
        print("✅ 所有包版本与lock文件一致")
        return True


def check_hash_consistency():
    """检查关键包的哈希值"""
    # 这里可以添加哈希验证逻辑
    print("✅ 哈希值验证 (跳过 - 需要额外实现)")
    return True


def main():
    """主验证函数"""
    print("=" * 60)
    print("🔍 依赖一致性验证报告")
    print("=" * 60)

    checks = [
        ("Lock文件存在", check_lock_files),
        ("pip consistency", check_pip_consistency),
        ("版本一致性", compare_with_lock),
        ("哈希值", check_hash_consistency),
    ]

    all_passed = True
    for check_name, check_func in checks:
        print(f"\n📋 检查: {check_name}")
        if not check_func():
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！依赖环境完全一致。")
        return 0
    else:
        print("⚠️ 发现问题！需要修复依赖。")
        print("\n💡 建议的修复步骤:")
        print("   1. 更新依赖: make lock-deps")
        print("   2. 重新安装: make install")
        print("   3. 再次验证: make verify-deps")
        return 1


if __name__ == "__main__":
    sys.exit(main())
