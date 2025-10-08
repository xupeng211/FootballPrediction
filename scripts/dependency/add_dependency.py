#!/usr/bin/env python3
"""
安全添加依赖的工具
确保依赖被正确添加到对应的.in文件并生成lock文件
"""

import sys
import argparse
import subprocess
from pathlib import Path

# 定义依赖类别
CATEGORIES = {
    "core": "requirements/core.in",
    "api": "requirements/api.in",
    "ml": "requirements/ml.in",
    "dev": "requirements/dev.in",
    "base": "requirements/base.in",
}


def add_dependency(package: str, category: str = "api", version: str = None):
    """安全地添加依赖"""
    if category not in CATEGORIES:
        print(f"❌ 无效的类别: {category}")
        print(f"可用类别: {', '.join(CATEGORIES.keys())}")
        return False

    # 构建包字符串
    package_str = f"{package}{version if version else ''}"

    # 检查文件是否存在
    file_path = Path(CATEGORIES[category])
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False

    # 检查是否已存在
    existing_content = file_path.read_text()
    if package in existing_content:
        print(f"⚠️  依赖 {package} 已存在于 {file_path}")
        return False

    # 添加依赖
    with open(file_path, "a") as f:
        f.write(f"\n{package_str}\n")
    print(f"✅ 已添加 {package_str} 到 {file_path}")

    # 运行 make lock-deps
    print("🔒 正在锁定依赖...")
    try:
        result = subprocess.run(
            ["make", "lock-deps"], capture_output=True, text=True, cwd=Path.cwd()
        )
        if result.returncode == 0:
            print("✅ 依赖已成功锁定")
            return True
        else:
            print(f"❌ 锁定失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 运行make lock-deps失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="安全添加依赖")
    parser.add_argument("package", help="包名")
    parser.add_argument(
        "-c",
        "--category",
        choices=CATEGORIES.keys(),
        default="api",
        help="依赖类别 (默认: api)",
    )
    parser.add_argument("-v", "--version", help="版本号 (例如: ==1.0.0)")

    args = parser.parse_args()

    print(f"📦 添加依赖: {args.package}")
    print(f"📁 类别: {args.category}")
    if args.version:
        print(f"🏷️  版本: {args.version}")

    success = add_dependency(args.package, args.category, args.version)

    if success:
        print("\n✅ 完成! 请记得提交更新后的文件:")
        print(f"   - {CATEGORIES[args.category]}")
        print("   - requirements/*.lock")
    else:
        print("\n❌ 添加失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
