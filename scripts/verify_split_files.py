#!/usr/bin/env python3
"""
拆分文件验证脚本 - Issue #87
验证所有拆分后的模块是否可以正常导入
"""

import sys
import traceback
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, ".")


def test_module_import(module_name, description=""):
    """测试模块导入"""
    try:
        __import__(module_name)
        print(f"✅ {module_name} 导入成功 {description}")
        return True
    except Exception as e:
        print(f"❌ {module_name} 导入失败: {str(e)[:100]}")
        if "import" not in str(e):
            print(f"   详细错误: {traceback.format_exc().splitlines()[-1]}")
        return False


def main():
    """主验证函数"""
    print("🔍 Issue #87 拆分文件验证报告")
    print("=" * 50)

    # 测试拆分的主模块
    test_modules = [
        ("src.monitoring.anomaly_detector", "异常检测模块"),
        ("src.cache.decorators", "缓存装饰器模块"),
        ("src.domain.strategies.config", "策略配置模块"),
        ("src.facades.facades", "门面模式模块"),
        ("src.decorators.decorators", "装饰器模块"),
        ("src.domain.strategies.historical", "历史策略模块"),
        ("src.domain.strategies.ensemble", "集成策略模块"),
    ]

    success_count = 0
    total_count = len(test_modules)

    for module_name, description in test_modules:
        if test_module_import(module_name, description):
            success_count += 1

    print("\n" + "=" * 50)
    print(f"📊 验证结果: {success_count}/{total_count} 个模块导入成功")
    print(f"成功率: {(success_count/total_count)*100:.1f}%")

    if success_count == total_count:
        print("🎉 所有拆分模块验证通过！")
        return True
    else:
        print("⚠️ 部分模块需要进一步修复导入路径")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
