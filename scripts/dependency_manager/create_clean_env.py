#!/usr/bin/env python3
"""
创建干净的虚拟环境
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def create_clean_environment():
    """创建干净的虚拟环境"""
    print("🌟 PH2-2: 创建干净虚拟环境...")
    print("="*60)

    # 虚拟环境配置
    venv_name = "venv_clean"
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    # 推荐的稳定版本（来自兼容性矩阵分析）
    stable_versions = {
        "numpy": "1.26.4",
        "scipy": "1.11.4",
        "pandas": "2.1.4",
        "scikit-learn": "1.3.2",
        "pydantic": "2.5.0",
        "fastapi": "0.104.1",
        "uvicorn": "0.24.0",
        "sqlalchemy": "2.0.23",
        "alembic": "1.12.1",
        "pytest": "7.4.3",
        "python-dotenv": "1.0.0",
        "httpx": "0.25.2",
        "redis": "5.0.1"
    }

    print(f"📦 Python版本: {python_version}")
    print(f"📁 虚拟环境名: {venv_name}")
    print(f"\n🎯 将安装稳定版本:")
    for pkg, ver in stable_versions.items():
        print(f"  - {pkg}=={ver}")

    # 1. 删除旧环境（如果存在）
    print("\n1️⃣ 清理旧环境...")
    venv_path = Path(venv_name)
    if venv_path.exists():
        print(f"  🗑️ 删除现有环境: {venv_name}")
        subprocess.run(["rm", "-rf", str(venv_path)], check=True)

    # 2. 创建新虚拟环境
    print("\n2️⃣ 创建虚拟环境...")
    try:
        subprocess.run([sys.executable, "-m", "venv", venv_name], check=True)
        print(f"  ✅ 虚拟环境创建成功: {venv_name}")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 创建失败: {e}")
        return None

    # 3. 获取虚拟环境的Python和pip路径
    if sys.platform == "win32":
        python_venv = venv_path / "Scripts" / "python.exe"
        pip_venv = venv_path / "Scripts" / "pip.exe"
        activate_script = venv_path / "Scripts" / "activate"
    else:
        python_venv = venv_path / "bin" / "python"
        pip_venv = venv_path / "bin" / "pip"
        activate_script = venv_path / "bin" / "activate"

    print(f"  📍 Python路径: {python_venv}")
    print(f"  📍 pip路径: {pip_venv}")

    # 4. 升级pip
    print("\n3️⃣ 升级pip...")
    subprocess.run([str(python_venv), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    print("  ✅ pip已升级")

    # 5. 安装核心包（分批安装以避免冲突）
    print("\n4️⃣ 安装核心依赖包...")

    # 第一批：基础包
    batch1 = ["numpy==1.26.4", "pandas==2.1.4"]
    print("  📦 安装第一批: numpy, pandas")
    subprocess.run([str(pip_venv), "install"] + batch1, check=True)
    print("  ✅ 第一批安装完成")

    # 第二批：科学计算
    batch2 = ["scipy==1.11.4", "scikit-learn==1.3.2"]
    print("  📦 安装第二批: scipy, scikit-learn")
    subprocess.run([str(pip_venv), "install"] + batch2, check=True)
    print("  ✅ 第二批安装完成")

    # 第三批：Web框架
    batch3 = ["pydantic==2.5.0", "fastapi==0.104.1", "uvicorn==0.24.0"]
    print("  📦 安装第三批: pydantic, fastapi, uvicorn")
    subprocess.run([str(pip_venv), "install"] + batch3, check=True)
    print("  ✅ 第三批安装完成")

    # 第四批：数据库和其他
    batch4 = ["sqlalchemy==2.0.23", "alembic==1.12.1", "python-dotenv==1.0.0",
              "httpx==0.25.2", "redis==5.0.1"]
    print("  📦 安装第四批: sqlalchemy, alembic等")
    subprocess.run([str(pip_venv), "install"] + batch4, check=True)
    print("  ✅ 第四批安装完成")

    # 第五批：开发工具
    batch5 = ["pytest==7.4.3", "pytest-asyncio==0.21.1", "pytest-cov==4.1.0"]
    print("  📦 安装第五批: pytest等开发工具")
    subprocess.run([str(pip_venv), "install"] + batch5, check=True)
    print("  ✅ 第五批安装完成")

    # 6. 生成requirements文件
    print("\n5️⃣ 生成requirements文件...")
    result = subprocess.run([str(pip_venv), "freeze"], capture_output=True, text=True)
    requirements_clean = Path("requirements-clean.txt")
    with open(requirements_clean, 'w') as f:
        f.write(result.stdout)
    print(f"  ✅ requirements-clean.txt已生成")

    # 7. 保存环境信息
    print("\n6️⃣ 保存环境信息...")
    env_info = {
        "created_at": datetime.now().isoformat(),
        "python_version": python_version,
        "venv_name": venv_name,
        "venv_path": str(venv_path.absolute()),
        "activate_script": str(activate_script),
        "packages_installed": stable_versions,
        "total_packages": len([line for line in result.stdout.split('\n') if line.strip()])
    }

    env_file = venv_path / "environment_info.json"
    with open(env_file, 'w') as f:
        json.dump(env_info, f, indent=2, default=str)
    print(f"  ✅ 环境信息已保存: {env_file}")

    # 8. 创建激活脚本
    print("\n7️⃣ 创建便捷脚本...")
    activate_sh = Path("activate_clean_env.sh")
    with open(activate_sh, 'w') as f:
        f.write(f"""#!/bin/bash
# 激活干净环境脚本
echo "🌟 激活干净虚拟环境: {venv_name}"
source {activate_script}
echo "✅ 环境已激活！"
echo "Python: $(which python)"
echo "pip: $(which pip)"
""")
    subprocess.run(["chmod", "+x", str(activate_sh)])
    print(f"  ✅ 激活脚本: {activate_sh}")

    # 9. 测试环境
    print("\n8️⃣ 测试环境...")
    test_script = venv_path / "test_imports.py"
    with open(test_script, 'w') as f:
        f.write("""
import sys
print(f"Python: {sys.version}")

# 测试核心包
packages = ["numpy", "pandas", "scipy", "sklearn", "pydantic", "fastapi"]
for pkg in packages:
    try:
        __import__(pkg)
        print(f"✅ {pkg}: 导入成功")
    except ImportError as e:
        print(f"❌ {pkg}: 导入失败 - {e}")
""")

    result = subprocess.run([str(python_venv), str(test_script)], capture_output=True, text=True)
    print("  📋 测试结果:")
    print(result.stdout)

    print(f"\n🎉 干净环境创建完成！")
    print(f"\n📋 使用方法:")
    print(f"  1. 激活环境: source {activate_script}")
    print(f"  2. 或使用: bash {activate_sh}")
    print(f"  3. 安装项目包: pip install -e .")
    print(f"  4. 运行测试: pytest")

    return venv_path

if __name__ == "__main__":
    venv_path = create_clean_environment()