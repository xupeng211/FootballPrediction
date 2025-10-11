#!/usr/bin/env python3
"""
简单测试审计服务模块
Simple Test Audit Service Module
"""

import sys

sys.path.insert(0, "/home/user/projects/FootballPrediction")


def test_basic_imports():
    """测试基础导入"""
    print("🔍 测试基础导入...")

    try:
        # 测试基础模块
        from src.services.audit.advanced.context import AuditContext
        from src.services.audit.advanced.sanitizer import DataSanitizer

        print("✅ 基础模块导入成功")

        # 测试功能
        _ = AuditContext(user_id="test_user")
        sanitizer = DataSanitizer()
        test_data = {"test": "value"}
        _ = sanitizer.sanitize_data(test_data)
        print("✅ 基础功能正常")

        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_directory_structure():
    """测试目录结构"""
    print("\n📁 测试目录结构...")

    import os

    required_dirs = [
        "/home/user/projects/FootballPrediction/src/services/audit/advanced",
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/analyzers",
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/loggers",
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/reporters",
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/decorators",
    ]

    all_exist = True
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ {os.path.basename(dir_path)} 目录存在")
        else:
            print(f"❌ {os.path.basename(dir_path)} 目录不存在")
            all_exist = False

    return all_exist


def test_file_count():
    """测试文件数量"""
    print("\n📄 测试文件创建...")

    import glob

    # 计算主要文件
    main_files = glob.glob(
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/*.py"
    )
    analyzer_files = glob.glob(
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/analyzers/*.py"
    )
    logger_files = glob.glob(
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/loggers/*.py"
    )
    reporter_files = glob.glob(
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/reporters/*.py"
    )
    decorator_files = glob.glob(
        "/home/user/projects/FootballPrediction/src/services/audit/advanced/decorators/*.py"
    )

    print(f"✅ 主文件: {len(main_files)} 个")
    print(f"✅ 分析器文件: {len(analyzer_files)} 个")
    print(f"✅ 日志器文件: {len(logger_files)} 个")
    print(f"✅ 报告器文件: {len(reporter_files)} 个")
    print(f"✅ 装饰器文件: {len(decorator_files)} 个")

    total_files = (
        len(main_files)
        + len(analyzer_files)
        + len(logger_files)
        + len(reporter_files)
        + len(decorator_files)
    )
    print(f"✅ 总计: {total_files} 个Python文件")

    return total_files >= 15  # 至少应该有15个文件


def main():
    """主测试函数"""
    print("🚀 简单审计服务模块测试\n")

    tests = [
        test_directory_structure,
        test_file_count,
        test_basic_imports,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📋 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 基础测试通过！拆分基本成功！")
        return True
    else:
        print("⚠️ 部分测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
