#!/usr/bin/env python3
"""
创建版本兼容性矩阵
"""

import json
import subprocess
import sys
from pathlib import Path
from packaging import version

def create_compatibility_matrix():
    """创建兼容性矩阵"""
    print("🔍 分析版本兼容性矩阵...")
    print("="*60)

    # 关键包及其兼容性要求
    key_packages = {
        "scipy": {
            "min_version": "1.9.0",
            "max_version": None,
            "compatible_with": ["numpy", "sklearn", "pandas"],
            "conflicts": ["highspy < 1.6.0"]
        },
        "numpy": {
            "min_version": "1.20.0",
            "max_version": "2.0.0",
            "compatible_with": ["scipy", "pandas", "sklearn"],
            "notes": "某些包可能还不支持numpy 2.x"
        },
        "pydantic": {
            "min_version": "2.0.0",
            "max_version": None,
            "compatible_with": ["fastapi >= 0.100.0"],
            "conflicts": ["pydantic < 2.0", "fastapi < 0.68.0"]
        },
        "fastapi": {
            "min_version": "0.100.0",
            "max_version": None,
            "compatible_with": ["pydantic >= 2.0"],
            "notes": "0.100+ 推荐使用 pydantic 2.x"
        },
        "sklearn": {
            "min_version": "1.0.0",
            "max_version": None,
            "compatible_with": ["numpy", "scipy"],
            "notes": "需要scipy用于算法实现"
        },
        "tensorflow": {
            "min_version": "2.8.0",
            "max_version": None,
            "compatible_with": ["numpy < 2.0.0"],
            "notes": "TensorFlow 2.x 可能不支持 numpy 2.x"
        },
        "torch": {
            "min_version": "1.12.0",
            "max_version": None,
            "compatible_with": ["numpy"],
            "notes": "PyTorch 通常与最新numpy兼容"
        }
    }

    # 获取当前安装的版本
    print("\n📦 获取当前版本...")
    current_versions = {}

    result = subprocess.run([sys.executable, "-m", "pip", "list"],
                          capture_output=True, text=True)

    for line in result.stdout.split('\n'):
        if line and ' ' in line and not line.startswith('Package'):
            parts = line.split()
            if len(parts) >= 2:
                package_name = parts[0].lower()
                current_versions[package_name] = parts[1]

    # 分析兼容性
    print("\n🔍 兼容性分析:")
    compatibility_matrix = {}

    for pkg_name, pkg_info in key_packages.items():
        pkg_name_lower = pkg_name.lower()
        current_version = current_versions.get(pkg_name_lower)

        analysis = {
            "package": pkg_name,
            "current_version": current_version,
            "recommended_min": pkg_info["min_version"],
            "recommended_max": pkg_info["max_version"],
            "status": "unknown",
            "issues": [],
            "recommendations": []
        }

        if current_version:
            # 检查最小版本
            if version.parse(current_version) < version.parse(pkg_info["min_version"]):
                analysis["status"] = "outdated"
                analysis["issues"].append(f"版本过低，需要 >= {pkg_info['min_version']}")
                analysis["recommendations"].append(f"升级到 {pkg_info['min_version']} 或更高")
            else:
                analysis["status"] = "compatible"

            # 检查最大版本
            if pkg_info["max_version"] and version.parse(current_version) >= version.parse(pkg_info["max_version"]):
                if analysis["status"] == "compatible":
                    analysis["status"] = "warning"
                analysis["issues"].append(f"版本可能过高，建议 < {pkg_info['max_version']}")

            # 特殊检查
            if pkg_name == "numpy" and version.parse(current_version) >= version.parse("2.0.0"):
                if "tensorflow" in current_versions:
                    analysis["status"] = "warning"
                    analysis["issues"].append("numpy 2.x可能与TensorFlow不兼容")

            if pkg_name == "pydantic":
                if version.parse(current_version) >= version.parse("2.0.0"):
                    if "fastapi" in current_versions:
                        fastapi_ver = current_versions.get("fastapi")
                        if fastapi_ver and version.parse(fastapi_ver) < version.parse("0.100.0"):
                            analysis["status"] = "warning"
                            analysis["issues"].append("pydantic 2.x需要FastAPI >= 0.100.0")
        else:
            analysis["status"] = "not_installed"
            analysis["issues"].append("包未安装")

        compatibility_matrix[pkg_name] = analysis

        # 打印分析结果
        status_icon = {
            "compatible": "✅",
            "outdated": "⬇️",
            "warning": "⚠️",
            "conflict": "❌",
            "not_installed": "➖",
            "unknown": "❓"
        }.get(analysis["status"], "❓")

        print(f"  {status_icon} {pkg_name}: {current_version or '未安装'}")
        if analysis["issues"]:
            for issue in analysis["issues"]:
                print(f"    - {issue}")

    # 生成推荐组合
    print("\n💡 推荐版本组合:")
    recommendations = {
        "stable": {
            "description": "稳定组合（推荐）",
            "versions": {
                "numpy": "1.26.4",
                "scipy": "1.11.4",
                "pandas": "2.1.4",
                "sklearn": "1.3.2",
                "pydantic": "2.5.0",
                "fastapi": "0.104.1"
            }
        },
        "latest": {
            "description": "最新版（可能有风险）",
            "versions": {
                "numpy": "1.26.4",
                "scipy": "1.11.4",
                "pandas": "2.1.4",
                "sklearn": "1.3.2",
                "pydantic": "2.11.9",
                "fastapi": "0.116.1"
            }
        },
        "minimal": {
            "description": "最小依赖（减少冲突）",
            "versions": {
                "numpy": "1.24.4",
                "scipy": "1.10.1",
                "pydantic": "2.0.3",
                "fastapi": "0.100.1"
            }
        }
    }

    for profile, info in recommendations.items():
        print(f"\n  🎯 {profile}: {info['description']}")
        for pkg, ver in info['versions'].items():
            print(f"    - {pkg}=={ver}")

    # 保存矩阵
    matrix_data = {
        "current_versions": current_versions,
        "compatibility_matrix": compatibility_matrix,
        "recommendations": recommendations,
        "generated_at": str(Path().resolve())
    }

    output_file = Path("docs/_reports/dependency_health/compatibility_matrix.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(matrix_data, f, indent=2)

    print(f"\n📄 兼容性矩阵已保存: {output_file}")

    return matrix_data

if __name__ == "__main__":
    matrix = create_compatibility_matrix()