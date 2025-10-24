#!/usr/bin/env python3
"""
数据库迁移系统验证脚本
用于验证所有迁移文件的导入和执行状态
"""

import os
import sys
import importlib
import subprocess
from pathlib import Path

def run_command(cmd, description=""):
    """运行命令并返回结果"""
    print(f"🔧 {description}")
    print(f"   执行: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", str(e)

def check_migration_imports():
    """检查所有迁移文件的导入"""
    print("📋 检查迁移文件导入")

    # 添加src目录到Python路径
    sys.path.insert(0, 'src')

    migration_dir = Path('src/database/migrations/versions')
    if not migration_dir.exists():
        print("   ❌ 迁移目录不存在")
        return False

    error_files = []
    total_files = 0

    for py_file in migration_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue

        total_files += 1
        module_name = py_file.stem

        try:
            # 尝试导入模块
            importlib.import_module(f'database.migrations.versions.{module_name}')
            print(f"   ✅ {module_name}")
        except Exception as e:
            print(f"   ❌ {module_name}: {e}")
            error_files.append((module_name, str(e)))

    print(f"\n📊 导入检查结果: {total_files - len(error_files)}/{total_files} 个文件导入成功")

    if error_files:
        print("\n❌ 导入失败的文件:")
        for filename, error in error_files:
            print(f"   - {filename}: {error}")
        return False

    return True

def check_alembic_status():
    """检查Alembic状态"""
    print("\n🔧 检查Alembic状态")

    # 检查当前版本
    success, stdout, stderr = run_command(
        "python -m alembic current",
        "检查当前数据库版本"
    )

    if success:
        print("   ✅ Alembic连接正常")
        if "test" in stdout:
            print("   ✅ 数据库版本: test (最新)")
        else:
            print(f"   📋 数据库版本: {stdout.strip()}")
    else:
        print(f"   ❌ Alembic状态检查失败: {stderr}")
        return False

    # 检查迁移历史
    success, stdout, stderr = run_command(
        "python -m alembic history",
        "检查迁移历史"
    )

    if success:
        migration_lines = [line for line in stdout.strip().split('\n') if line.strip()]
        print(f"   ✅ 迁移历史完整 ({len(migration_lines)} 个记录)")
    else:
        print(f"   ❌ 迁移历史检查失败: {stderr}")
        return False

    return True

def test_migration_execution():
    """测试迁移执行"""
    print("\n🔨 测试迁移执行")

    # 使用make命令测试迁移
    success, stdout, stderr = run_command(
        "make db-migrate",
        "执行数据库迁移"
    )

    if success:
        print("   ✅ 数据库迁移执行成功")
        if "Database migrations completed" in stdout:
            print("   ✅ 迁移完成确认")
        return True
    else:
        print(f"   ❌ 数据库迁移失败: {stderr}")
        return False

def check_migration_syntax():
    """检查迁移文件语法"""
    print("\n🔍 检查迁移文件语法")

    migration_dir = Path('src/database/migrations/versions')
    syntax_errors = []

    for py_file in migration_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue

        try:
            # 编译检查语法
            with open(py_file, 'r', encoding='utf-8') as f:
                compile(f.read(), str(py_file), 'exec')
            print(f"   ✅ {py_file.name}")
        except SyntaxError as e:
            print(f"   ❌ {py_file.name}: 语法错误 - {e}")
            syntax_errors.append((py_file.name, str(e)))
        except Exception as e:
            print(f"   ⚠️  {py_file.name}: 其他错误 - {e}")

    if syntax_errors:
        print(f"\n❌ 发现 {len(syntax_errors)} 个语法错误")
        return False

    print("   ✅ 所有迁移文件语法正确")
    return True

def check_database_connection():
    """检查数据库连接"""
    print("\n🔗 检查数据库连接")

    success, stdout, stderr = run_command(
        "python -c \"import sqlite3; conn = sqlite3.connect('football_prediction.db'); print('数据库连接成功'); conn.close()\"",
        "测试SQLite数据库连接"
    )

    if success:
        print("   ✅ 数据库连接正常")
        return True
    else:
        print(f"   ❌ 数据库连接失败: {stderr}")
        return False

def main():
    """主函数"""
    print("📚 数据库迁移系统验证")
    print("=" * 50)

    checks = [
        ("数据库连接检查", check_database_connection),
        ("迁移文件语法检查", check_migration_syntax),
        ("迁移文件导入检查", check_migration_imports),
        ("Alembic状态检查", check_alembic_status),
        ("迁移执行测试", test_migration_execution),
    ]

    results = []

    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}")
        print("-" * 30)

        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            results.append((check_name, False))

    # 生成报告
    print("\n" + "=" * 50)
    print("📊 验证结果汇总")
    print("=" * 50)

    passed = 0
    total = len(results)

    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {check_name}")
        if result:
            passed += 1

    print(f"\n📈 总体结果: {passed}/{total} 项检查通过")

    if passed == total:
        print("🎉 数据库迁移系统验证成功！")
        print("✅ 所有迁移文件都能正常导入和执行")
        print("✅ 数据库迁移系统工作正常")
        return 0
    else:
        print("⚠️  存在失败项目，请检查并修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())