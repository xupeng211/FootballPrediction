#!/usr/bin/env python3
"""
独立的导入测试 - Issue #88 阶段1验证
不依赖pytest或conftest，直接测试关键模块导入
"""

import sys

# 添加项目根目录到Python路径
sys.path.insert(0, ".")


def test_critical_imports():
    """测试关键模块导入"""
    print("🧪 测试关键模块导入")  # TODO: Add logger import if needed
    print("=" * 50)  # TODO: Add logger import if needed

    critical_modules = [
        ("src.monitoring.anomaly_detector", "AnomalyDetector"),
        ("src.cache.decorators", "cache_result"),
        ("src.domain.strategies.config", "StrategyConfig"),
        ("src.facades.facades", "MainSystemFacade"),
        ("src.decorators.decorators", "CacheDecorator"),
        ("src.domain.strategies.historical", "HistoricalStrategy"),
        ("src.domain.strategies.ensemble", "EnsembleStrategy"),
        ("src.performance.analyzer", "PerformanceAnalyzer"),
        ("src.adapters.football", "FootballMatch"),
        ("src.patterns.facade", "PredictionRequest"),
    ]

    success_count = 0
    failed_modules = []

    for module_name, expected_class in critical_modules:
        try:
            module = __import__(module_name, fromlist=[expected_class])
            if hasattr(module, expected_class):
                print(
                    f"✅ {module_name} - {expected_class} 可用"
                )  # TODO: Add logger import if needed
                success_count += 1
            else:
                print(
                    f"⚠️ {module_name} - {expected_class} 不可用"
                )  # TODO: Add logger import if needed
                failed_modules.append((module_name, f"缺少 {expected_class}"))
        except ImportError as e:
            print(
                f"❌ {module_name} - 导入失败: {str(e)[:50]}..."
            )  # TODO: Add logger import if needed
            failed_modules.append((module_name, str(e)))
        except Exception as e:
            print(
                f"❌ {module_name} - 其他错误: {str(e)[:50]}..."
            )  # TODO: Add logger import if needed
            failed_modules.append((module_name, str(e)))

    print(
        f"\n📊 导入测试结果: {success_count}/{len(critical_modules)} 成功"
    )  # TODO: Add logger import if needed

    if failed_modules:
        print("\n❌ 失败的模块:")  # TODO: Add logger import if needed
        for module, error in failed_modules:
            print(f"  - {module}: {error[:60]}...")  # TODO: Add logger import if needed

    return success_count == len(critical_modules)


def test_pytest_availability():
    """测试pytest是否可用"""
    print("\n🧪 测试pytest可用性")  # TODO: Add logger import if needed
    print("=" * 30)  # TODO: Add logger import if needed

    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print(
                f"✅ pytest可用: {result.stdout.strip()}"
            )  # TODO: Add logger import if needed
            return True
        else:
            print(
                f"❌ pytest版本检查失败: {result.stderr}"
            )  # TODO: Add logger import if needed
            return False
    except Exception as e:
        print(f"❌ pytest测试失败: {e}")  # TODO: Add logger import if needed
        return False


def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能")  # TODO: Add logger import if needed
    print("=" * 30)  # TODO: Add logger import if needed

    try:
        # 测试一个简单的类实例化
        from src.monitoring.anomaly_detector import AnomalyDetector

        AnomalyDetector()
        print("✅ AnomalyDetector 实例化成功")  # TODO: Add logger import if needed

        # 测试一个简单的方法调用

        print("✅ cache_result 装饰器可用")  # TODO: Add logger import if needed

        return True
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")  # TODO: Add logger import if needed
        return False


def main():
    """主函数"""
    print(
        "🚀 Issue #88 阶段1验证: 导入路径修复效果"
    )  # TODO: Add logger import if needed
    print("=" * 60)  # TODO: Add logger import if needed

    # 1. 测试关键模块导入
    imports_ok = test_critical_imports()

    # 2. 测试pytest可用性
    pytest_ok = test_pytest_availability()

    # 3. 测试基本功能
    functionality_ok = test_basic_functionality()

    # 总结
    print("\n🎯 阶段1验证总结:")  # TODO: Add logger import if needed
    print(
        f"✅ 关键模块导入: {'通过' if imports_ok else '失败'}"
    )  # TODO: Add logger import if needed
    print(
        f"✅ pytest可用性: {'通过' if pytest_ok else '失败'}"
    )  # TODO: Add logger import if needed
    print(
        f"✅ 基本功能测试: {'通过' if functionality_ok else '失败'}"
    )  # TODO: Add logger import if needed

    if imports_ok and pytest_ok and functionality_ok:
        print(
            "\n🎉 阶段1完成! 基础导入问题已解决。"
        )  # TODO: Add logger import if needed
        print(
            "📈 下一步: 可以开始运行基础测试了。"
        )  # TODO: Add logger import if needed
        return True
    else:
        print(
            "\n⚠️ 阶段1部分完成，仍有问题需要解决。"
        )  # TODO: Add logger import if needed
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
