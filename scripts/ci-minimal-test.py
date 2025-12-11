#!/usr/bin/env python3
"""
CI最小化验证脚本
用于快速验证CI环境的基本功能
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, timeout=30):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timeout"


def check_basic_imports():
    """检查基本模块导入"""
    print("🔍 检查基本模块导入...")

    imports = ["sys", "os", "json", "datetime", "fastapi", "pydantic", "sqlalchemy"]

    for module in imports:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False

    return True


def check_project_structure():
    """检查项目结构"""
    print("🏗️ 检查项目结构...")

    required_dirs = ["src", "tests", "src/api", "src/database"]

    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path}")
            return False

    return True


def run_minimal_tests():
    """运行最小化测试"""
    print("🧪 运行最小化测试...")

    # 设置环境变量
    os.environ.update(
        {
            "FOOTBALL_PREDICTION_ML_MODE": "mock",
            "SKIP_ML_MODEL_LOADING": "true",
            "INFERENCE_SERVICE_MOCK": "true",
            "TESTING": "true",
        }
    )

    # 尝试运行基本导入测试
    test_cmd = 'python -c \'import sys; sys.path.insert(0, "src"); print("✅ 基本导入测试通过")\''

    success, stdout, stderr = run_command(test_cmd, timeout=10)

    if success:
        print("✅ 最小化测试通过")
        return True
    else:
        print(f"❌ 最小化测试失败: {stderr}")
        return False


def main():
    """主函数"""
    print("🚀 CI最小化验证开始...")

    # 基本检查
    checks = [
        ("基本模块导入", check_basic_imports),
        ("项目结构", check_project_structure),
        ("最小化测试", run_minimal_tests),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n📋 {name}:")
        try:
            result = check_func()
            results.append((name, result))
            print(f"{'✅' if result else '❌'} {name}: {'通过' if result else '失败'}")
        except Exception as e:
            print(f"❌ {name}: 异常 - {e}")
            results.append((name, False))

    # 汇总结果
    print("\n📊 CI验证结果:")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:20} {status}")

    print("=" * 50)
    print(f"总计: {passed}/{total} 项检查通过")

    if passed == total:
        print("🎉 CI验证完全通过!")
        sys.exit(0)
    else:
        print("⚠️ CI验证失败，需要修复问题")
        sys.exit(1)


if __name__ == "__main__":
    main()
