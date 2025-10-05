#!/usr/bin/env python3
"""
测试干净环境复现性
验证新的依赖可以在干净环境中正确安装
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path


def run_command(cmd, cwd=None, capture_output=True):
    """运行命令并返回结果"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=capture_output, text=True)
    return result


def test_clean_install():
    """测试干净环境安装"""
    print("🧪 Testing clean environment reproduction...\n")

    project_root = Path(__file__).parent.parent.parent
    requirements_dir = project_root / "requirements"

    # 创建临时虚拟环境
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = Path(temp_dir) / "test_venv"
        print(f"Creating temporary venv: {venv_path}")

        # 创建虚拟环境
        result = run_command([sys.executable, "-m", "venv", str(venv_path)])
        if result.returncode != 0:
            print(f"❌ Failed to create venv: {result.stderr}")
            return False

        # 确定虚拟环境中的python和pip路径
        if os.name == "nt":
            python_exe = venv_path / "Scripts" / "python.exe"
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:
            python_exe = venv_path / "bin" / "python"
            pip_exe = venv_path / "bin" / "pip"

        # 升级pip
        print("\n📦 Upgrading pip...")
        result = run_command([str(pip_exe), "install", "--upgrade", "pip"])
        if result.returncode != 0:
            print(f"❌ Failed to upgrade pip: {result.stderr}")
            return False

        # 安装基础依赖
        print("\n📦 Installing base dependencies...")
        result = run_command(
            [str(pip_exe), "install", "-r", str(requirements_dir / "base.lock")]
        )
        if result.returncode != 0:
            print(f"❌ Failed to install base dependencies: {result.stderr}")
            return False

        # 测试导入核心模块
        print("\n🧪 Testing core imports...")
        test_script = """
import sys
try:
    import fastapi
    print("✅ fastapi imported successfully")
except ImportError as e:
    print(f"❌ Failed to import fastapi: {e}")
    sys.exit(1)

try:
    import sqlalchemy
    print("✅ sqlalchemy imported successfully")
except ImportError as e:
    print(f"❌ Failed to import sqlalchemy: {e}")
    sys.exit(1)

try:
    import redis
    print("✅ redis imported successfully")
except ImportError as e:
    print(f"❌ Failed to import redis: {e}")
    sys.exit(1)

try:
    import pandas
    print("✅ pandas imported successfully")
except ImportError as e:
    print(f"❌ Failed to import pandas: {e}")
    sys.exit(1)

try:
    import mlflow
    print("✅ mlflow imported successfully")
except ImportError as e:
    print(f"❌ Failed to import mlflow: {e}")
    sys.exit(1)
"""

        result = run_command([str(python_exe), "-c", test_script])
        if result.returncode != 0:
            print("❌ Core import test failed")
            return False

        # 安装streaming依赖
        print("\n📦 Installing streaming dependencies...")
        result = run_command(
            [str(pip_exe), "install", "-r", str(requirements_dir / "streaming.lock")]
        )
        if result.returncode != 0:
            print(f"❌ Failed to install streaming dependencies: {result.stderr}")
            return False

        # 测试Kafka相关导入
        print("\n🧪 Testing Kafka imports...")
        kafka_test_script = """
import sys
try:
    import confluent_kafka
    print("✅ confluent_kafka imported successfully")
    print(f"   Version: {confluent_kafka.__version__}")
except ImportError as e:
    print(f"❌ Failed to import confluent_kafka: {e}")
    sys.exit(1)

try:
    import aiokafka
    print("✅ aiokafka imported successfully")
except ImportError as e:
    print(f"❌ Failed to import aiokafka: {e}")
    sys.exit(1)

try:
    import kafka
    print("✅ kafka_python imported successfully")
except ImportError as e:
    print(f"❌ Failed to import kafka_python: {e}")
    sys.exit(1)

print("\n✅ All streaming dependencies installed successfully!")
"""

        result = run_command([str(python_exe), "-c", kafka_test_script])
        if result.returncode != 0:
            print("❌ Kafka import test failed")
            return False

        # 验证版本一致性
        print("\n🔍 Verifying version consistency...")
        version_check = """
import pkg_resources
packages = ['confluent-kafka', 'aiokafka', 'kafka-python']
for pkg in packages:
    try:
        version = pkg_resources.get_distribution(pkg).version
        print(f"   {pkg}: {version}")
    except:
        print(f"   {pkg}: not found")
"""

        result = run_command([str(python_exe), "-c", version_check])
        print(result.stdout)

        print("\n✅ Clean environment reproduction test PASSED!")
        print("📦 All dependencies can be installed correctly in a clean environment.")
        return True


def test_dependency_conflicts():
    """测试依赖冲突"""
    print("\n🔍 Checking for dependency conflicts...")

    # 检查confluent-kafka的依赖
    conflicts = []

    # 检查是否有已知的冲突包
    known_conflicts = {
        "confluent-kafka": ["librdkafka", "confluent-kafka-python"],
        "aiokafka": ["kafka-python>=2.0.0"],  # aiokafka和kafka-python可以共存
    }

    project_root = Path(__file__).parent.parent.parent
    requirements_dir = project_root / "requirements"

    # 读取streaming.lock文件
    with open(requirements_dir / "streaming.lock", "r") as f:
        lock_content = f.read()

    for package, conflict_packages in known_conflicts.items():
        if package in lock_content:
            for conflict in conflict_packages:
                if conflict in lock_content and conflict != package:
                    conflicts.append(f"{package} conflicts with {conflict}")

    if conflicts:
        print("❌ Found potential conflicts:")
        for conflict in conflicts:
            print(f"   - {conflict}")
        return False
    else:
        print("✅ No dependency conflicts found")
        return True


def main():
    """主函数"""
    print("=" * 60)
    print("Clean Environment Reproduction Test")
    print("=" * 60)

    success = True

    # 测试依赖冲突
    if not test_dependency_conflicts():
        success = False

    # 测试干净环境安装
    if not test_clean_install():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ All tests PASSED! Dependencies are reproducible.")
        sys.exit(0)
    else:
        print("❌ Some tests FAILED! Please check dependencies.")
        sys.exit(1)


if __name__ == "__main__":
    main()
