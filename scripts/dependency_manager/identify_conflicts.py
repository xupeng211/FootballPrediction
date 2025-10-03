#!/usr/bin/env python3
"""
识别依赖冲突源头
"""

import subprocess
import sys
import re
from pathlib import Path

def identify_conflicts():
    """识别冲突源头"""
    print("🔍 识别依赖冲突源头...")
    print("="*60)

    conflicts = []

    # 1. 检查scipy/highspy冲突
    print("\n1️⃣ 检查 scipy/highspy 冲突...")
    try:
        result = subprocess.run([sys.executable, "-c",
            "import scipy; import highspy; print('No conflict')"],
            capture_output=True, text=True, timeout=5)
        if "generic_type" in result.stderr:
            conflicts.append({
                "type": "scipy_highspy",
                "packages": ["scipy", "highspy"],
                "error": result.stderr,
                "severity": "critical"
            })
            print("  🔴 发现 scipy/highspy 类型注册冲突")
    except Exception as e:
        print(f"  ⚠️ 检查失败: {e}")

    # 2. 检查pydantic版本冲突
    print("\n2️⃣ 检查 pydantic 版本要求...")
    result = subprocess.run([sys.executable, "-m", "pip", "show", "pydantic"],
                          capture_output=True, text=True)
    if "Version:" in result.stdout:
        version = re.search(r"Version: (.+)", result.stdout).group(1)
        print(f"  📦 pydantic 当前版本: {version}")

    # 检查哪些包要求特定pydantic版本
    result = subprocess.run([sys.executable, "-m", "pip", "list"],
                          capture_output=True, text=True)
    installed_packages = {}
    for line in result.stdout.split('\n'):
        if line and ' ' in line and not line.startswith('Package'):
            parts = line.split()
            if len(parts) >= 2:
                installed_packages[parts[0].lower()] = parts[1]

    # 查找依赖pydantic的包
    pydantic_dependents = []
    result = subprocess.run([sys.executable, "-m", "pipdeptree", "-p", "pydantic"],
                          capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if '==' in line and 'pydantic' not in line:
            pkg = line.split('==')[0].strip()
            if pkg in installed_packages:
                pydantic_dependents.append(pkg)

    print(f"  🔗 依赖 pydantic 的包: {len(pydantic_dependents)} 个")
    for pkg in pydantic_dependents[:5]:
        print(f"    - {pkg}")

    # 3. 检查numpy版本要求
    print("\n3️⃣ 检查 numpy 版本要求...")
    if "numpy" in installed_packages:
        numpy_version = installed_packages["numpy"]
        print(f"  📦 numpy 当前版本: {numpy_version}")

    # 4. 测试项目模块导入
    print("\n4️⃣ 测试项目模块导入...")
    test_modules = [
        "sklearn",
        "tensorflow",
        "torch"
    ]

    for module in test_modules:
        try:
            __import__(module)
            print(f"  ✅ {module} - 导入成功")
        except ImportError as e:
            if "generic_type" in str(e):
                conflicts.append({
                    "type": "import_conflict",
                    "module": module,
                    "error": str(e),
                    "severity": "high"
                })
                print(f"  ❌ {module} - 冲突错误")
            else:
                print(f"  ⚪ {module} - 未安装或未导入")

    # 5. 生成冲突报告
    print("\n📋 冲突总结:")
    if conflicts:
        for conflict in conflicts:
            severity_icon = "🔴" if conflict["severity"] == "critical" else "🟠"
            print(f"  {severity_icon} {conflict['type']}: {conflict.get('packages', conflict.get('module', 'Unknown'))}")
    else:
        print("  ✅ 未发现明显冲突")

    # 保存冲突报告
    report = {
        "conflicts": conflicts,
        "analysis": {
            "installed_packages": installed_packages,
            "pydantic_dependents": pydantic_dependents,
            "numpy_version": installed_packages.get("numpy"),
            "pydantic_version": installed_packages.get("pydantic")
        }
    }

    output_file = Path("docs/_reports/dependency_health/conflict_analysis.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        import json
        json.dump(report, f, indent=2)

    print(f"\n📄 冲突分析报告已保存: {output_file}")

    return conflicts

if __name__ == "__main__":
    conflicts = identify_conflicts()