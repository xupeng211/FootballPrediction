from typing import Optional

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
                success_count += 1
            else:
                failed_modules.append((module_name, f"缺少 {expected_class}"))
        except ImportError as e:
            failed_modules.append((module_name, str(e)))
        except Exception as e:
            failed_modules.append((module_name, str(e)))

    if failed_modules:
        for _module, _error in failed_modules:
            pass

    return success_count == len(critical_modules)


def test_pytest_availability():
    """测试pytest是否可用"""

    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        return False


def test_basic_functionality():
    """测试基本功能"""

    try:
        # 测试一个简单的类实例化
        from src.monitoring.anomaly_detector import AnomalyDetector

        AnomalyDetector()

        # 测试一个简单的方法调用

        return True
    except Exception as e:
        return False


def main():
    """主函数"""

    # 1. 测试关键模块导入
    imports_ok = test_critical_imports()

    # 2. 测试pytest可用性
    pytest_ok = test_pytest_availability()

    # 3. 测试基本功能
    functionality_ok = test_basic_functionality()

    # 总结

    if imports_ok and pytest_ok and functionality_ok:
        return True
    else:
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
