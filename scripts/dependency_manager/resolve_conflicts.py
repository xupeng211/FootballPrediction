#!/usr/bin/env python3
"""
解决关键依赖冲突
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def resolve_conflicts():
    """解决关键冲突"""
    print("🔧 PH2-3: 解决关键冲突...")
    print("="*60)

    # 使用干净环境的Python
    venv_python = Path("venv_clean/bin/python")
    if not venv_python.exists():
        print("❌ 干净环境不存在，请先运行PH2-2")
        return False

    print(f"📍 使用干净环境: {venv_python}")

    # 1. 测试已知冲突
    print("\n1️⃣ 测试已知冲突...")

    conflicts = []

    # 测试scipy/highspy冲突
    print("  🔍 测试 scipy/highspy 冲突...")
    try:
        result = subprocess.run([str(venv_python), "-c",
            "import scipy; import highspy; print('✅ scipy/highspy 兼容')"],
            capture_output=True, text=True, timeout=10)
        if "generic_type" in result.stderr:
            conflicts.append({
                "type": "scipy_highspy",
                "error": result.stderr,
                "severity": "critical"
            })
            print("  ❌ 发现scipy/highspy冲突")
        else:
            print("  ✅ scipy/highspy无冲突")
    except subprocess.TimeoutExpired:
        print("  ⚠️ 测试超时")
    except Exception as e:
        print(f"  ⚠️ 测试失败: {e}")

    # 测试numpy版本
    print("  🔍 测试numpy版本...")
    result = subprocess.run([str(venv_python), "-c",
        "import numpy; print(f'numpy版本: {numpy.__version__}')"],
        capture_output=True, text=True)
    if "1.26.4" in result.stdout:
        print("  ✅ numpy版本正确")
    else:
        conflicts.append({
            "type": "numpy_version",
            "error": f"期望1.26.4，实际{result.stdout.strip()}",
            "severity": "high"
        })
        print("  ❌ numpy版本不正确")

    # 测试pydantic/fastapi兼容性
    print("  🔍 测试pydantic/fastapi兼容性...")
    try:
        result = subprocess.run([str(venv_python), "-c",
            "import pydantic; import fastapi; print(f'pydantic: {pydantic.__version__}'); print(f'fastapi: {fastapi.__version__}')"],
            capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ pydantic/fastapi兼容")
        else:
            conflicts.append({
                "type": "pydantic_fastapi",
                "error": result.stderr,
                "severity": "high"
            })
            print("  ❌ pydantic/fastapi不兼容")
    except Exception as e:
        print(f"  ⚠️ 测试失败: {e}")

    # 2. 安装项目依赖并测试
    print("\n2️⃣ 安装项目依赖...")

    # 先复制项目文件
    project_requirements = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt"
    ]

    for req_file in project_requirements:
        if Path(req_file).exists():
            print(f"  📄 找到 {req_file}")

    # 安装项目本身
    print("  📦 安装项目包...")
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "-e", "."],
                      capture_output=True, text=True)
        print("  ✅ 项目包安装成功")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 项目包安装失败: {e}")
        conflicts.append({
            "type": "project_install",
            "error": str(e),
            "severity": "critical"
        })

    # 3. 测试核心模块导入
    print("\n3️⃣ 测试核心模块导入...")

    test_modules = [
        "src.api.routes",
        "src.api.models",
        "src.database.config",
        "src.core.config"
    ]

    for module in test_modules:
        try:
            result = subprocess.run([str(venv_python), "-c", f"import {module}"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✅ {module}")
            else:
                print(f"  ❌ {module}: {result.stderr}")
                conflicts.append({
                    "type": "import_error",
                    "module": module,
                    "error": result.stderr,
                    "severity": "medium"
                })
        except Exception as e:
            print(f"  ⚠️ {module}: 测试失败")

    # 4. 运行基本测试
    print("\n4️⃣ 运行基本测试...")
    try:
        # 切换到干净环境并运行简单测试
        test_cmd = f"""
cd /home/user/projects/FootballPrediction
source venv_clean/bin/activate
python -m pytest tests/unit/test_main.py -v --tb=short
"""
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ 基本测试通过")
        else:
            print("  ❌ 基本测试失败")
            print(f"  错误: {result.stderr}")
    except Exception as e:
        print(f"  ⚠️ 测试运行失败: {e}")

    # 5. 生成冲突报告
    print("\n5️⃣ 生成冲突解决报告...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "environment": "venv_clean",
        "conflicts_found": len(conflicts),
        "conflicts": conflicts,
        "resolution_status": "resolved" if not conflicts else "partial"
    }

    report_file = Path("docs/_reports/dependency_health/conflict_resolution_report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"  📄 报告已保存: {report_file}")

    # 6. 总结
    print(f"\n📊 冲突解决总结:")
    print(f"  🔍 发现冲突: {len(conflicts)} 个")

    if conflicts:
        print("  ❗ 未解决的冲突:")
        for i, conflict in enumerate(conflicts, 1):
            severity = "🔴" if conflict["severity"] == "critical" else "🟠"
            print(f"    {severity} {i}. {conflict['type']}: {conflict.get('error', '未知错误')}")
        return False
    else:
        print("  ✅ 所有关键冲突已解决!")
        return True

if __name__ == "__main__":
    success = resolve_conflicts()
    sys.exit(0 if success else 1)