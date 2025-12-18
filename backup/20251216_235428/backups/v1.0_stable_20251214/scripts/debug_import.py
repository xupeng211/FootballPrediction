"""
导入自测脚本
验证循环引用问题是否已解决
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试关键导入"""
    imports_to_test = [
        # 基础导入
        ("src.database.models", "Base, League, Team, Match"),

        # 工具导入
        ("src.utils.normalizer", "TeamNameStandardizer, LeagueNameStandardizer"),

        # 仓库导入（关键测试）
        ("src.database.repositories", "TeamRepository, LeagueRepository, MatchRepository"),

        # 单独测试每个仓库类
        ("src.database.repositories", "TeamRepository"),
        ("src.database.repositories", "LeagueRepository"),
        ("src.database.repositories", "MatchRepository"),
    ]

    success_count = 0
    total_count = len(imports_to_test)

    for module_name, import_names in imports_to_test:
        try:
            exec(f"from {module_name} import {import_names}")
            print(f"✅ Import Success: from {module_name} import {import_names}")
            success_count += 1
        except ImportError as e:
            print(f"❌ Import Failed: from {module_name} import {import_names}")
            print(f"   Error: {str(e)}")
        except Exception as e:
            print(f"⚠️  Unexpected Error: from {module_name} import {import_names}")
            print(f"   Error: {str(e)}")

    print(f"\n📊 Import Test Results: {success_count}/{total_count} successful")

    if success_count == total_count:
        print("🎉 All imports successful! Circular import issue resolved.")
        return True
    else:
        print("⚠️  Some imports failed. Circular import issue still exists.")
        return False

def test_basic_functionality():
    """测试基本功能是否正常"""
    try:
        from src.database.repositories import TeamRepository, LeagueRepository, MatchRepository
        from src.utils.normalizer import TeamNameStandardizer

        # 测试标准化器
        standardizer = TeamNameStandardizer()
        result = standardizer.normalize_team_name("Man Utd")
        print(f"✅ Normalizer Test: 'Man Utd' → '{result}'")

        # 测试仓库类实例化（不连接数据库）
        print("✅ Repository Classes imported successfully")
        print(f"   - TeamRepository: {TeamRepository}")
        print(f"   - LeagueRepository: {LeagueRepository}")
        print(f"   - MatchRepository: {MatchRepository}")

        return True

    except Exception as e:
        print(f"❌ Functionality Test Failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Import Debug Tests...")
    print("=" * 60)

    # 测试导入
    imports_ok = test_imports()

    print("\n" + "=" * 60)

    # 测试基本功能
    if imports_ok:
        print("🔧 Testing Basic Functionality...")
        functionality_ok = test_basic_functionality()

        if functionality_ok:
            print("\n🎉 All tests passed! System ready for use.")
            sys.exit(0)
        else:
            print("\n⚠️  Imports ok but functionality issues.")
            sys.exit(1)
    else:
        print("\n❌ Import issues detected. Please fix circular imports.")
        sys.exit(1)