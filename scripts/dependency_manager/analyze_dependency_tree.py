#!/usr/bin/env python3
"""
分析依赖树
"""

import json
import sys
from pathlib import Path

def analyze_dependency_tree():
    """分析依赖树"""
    tree_file = Path("docs/_reports/dependency_health/dependency_tree_tree.json")

    if not tree_file.exists():
        print("❌ 依赖树文件不存在，请先运行: pipdeptree --json-tree")
        return

    with open(tree_file) as f:
        tree = json.load(f)

    print("\n🌳 依赖树分析")
    print("="*60)

    # 分析深度
    def get_depth(pkg, current_depth=0):
        if not pkg.get('dependencies'):
            return current_depth
        return max(get_depth(dep, current_depth + 1) for dep in pkg['dependencies'])

    max_depth = 0
    total_packages = 0

    for pkg in tree:
        depth = get_depth(pkg)
        max_depth = max(max_depth, depth)
        total_packages += 1

    print(f"📊 统计信息:")
    print(f"  总包数: {total_packages}")
    print(f"  最大深度: {max_depth}")

    # 查找关键包
    key_packages = ['scipy', 'highspy', 'sklearn', 'numpy', 'fastapi', 'pydantic']
    print(f"\n🔑 关键包分析:")

    def find_package(tree, name):
        for pkg in tree:
            if pkg['package']['key'].lower() == name.lower():
                return pkg
        return None

    for pkg_name in key_packages:
        pkg = find_package(tree, pkg_name)
        if pkg:
            version = pkg['package'].get('installed_version', 'Unknown')
            deps = len(pkg.get('dependencies', []))
            print(f"  ✅ {pkg_name}: {version} (依赖数: {deps})")
        else:
            print(f"  ❌ {pkg_name}: 未找到")

    # 查找冲突
    print(f"\n⚠️ 潜在冲突:")
    scipy = find_package(tree, 'scipy')
    highspy = find_package(tree, 'highspy')

    if scipy and highspy:
        print(f"  🔴 scipy/highspy 冲突")
        print(f"     - scipy: {scipy['package'].get('installed_version', 'Unknown')}")
        print(f"     - highspy: {highspy['package'].get('installed_version', 'Unknown')}")

    # 保存简化报告
    report = {
        "total_packages": total_packages,
        "max_depth": max_depth,
        "key_packages": {},
        "conflicts": []
    }

    for pkg_name in key_packages:
        pkg = find_package(tree, pkg_name)
        if pkg:
            report["key_packages"][pkg_name] = {
                "version": pkg['package'].get('installed_version', 'Unknown'),
                "dependencies_count": len(pkg.get('dependencies', []))
            }

    if scipy and highspy:
        report["conflicts"].append({
            "packages": ["scipy", "highspy"],
            "type": "version_conflict"
        })

    report_file = Path("docs/_reports/dependency_health/dependency_tree_analysis.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 分析报告已保存: {report_file}")

if __name__ == "__main__":
    analyze_dependency_tree()