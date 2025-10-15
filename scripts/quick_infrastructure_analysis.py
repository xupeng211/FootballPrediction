#!/usr/bin/env python3
"""
快速基础设施问题分析
"""

import os
import subprocess
from pathlib import Path

def main():
    print("=" * 80)
    print("           足球预测系统基础设施问题快速分析")
    print("=" * 80)
    
    print("\n🔍 1. 语法错误（最严重）:")
    # 检查几个已知有问题的文件
    problem_files = [
        "src/adapters/registry_simple.py",
        "src/adapters/factory_simple.py", 
        "src/adapters/factory.py",
        "src/adapters/football.py",
        "src/api/schemas.py",
        "src/api/performance.py",
        "src/api/facades.py",
        "src/api/app.py",
        "src/api/observers.py"
    ]
    
    syntax_errors = 0
    for file_path in problem_files:
        if Path(file_path).exists():
            try:
                subprocess.run(
                    ["python", "-m", "py_compile", file_path],
                    capture_output=True,
                    check=True
                )
            except subprocess.CalledProcessError:
                print(f"  ❌ {file_path}")
                syntax_errors += 1
    
    print(f"\n发现 {syntax_errors} 个语法错误")
    
    print("\n🔍 2. 测试收集错误:")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", "tests/"],
            capture_output=True,
            text=True,
            timeout=20
        )
        output = result.stderr
        if "errors" in output:
            error_count = output.split("errors")[0].split()[-1]
            print(f"  ❌ {error_count} 个测试收集错误")
        else:
            print("  ✅ 测试收集正常")
    except:
        print("  ⚠️ 无法检查测试收集")
    
    print("\n🔍 3. 备份文件问题:")
    backup_dirs = list(Path('.').glob('src_backup_*'))
    if backup_dirs:
        print(f"  ❌ 发现 {len(backup_dirs)} 个备份目录")
        for d in backup_dirs[:3]:
            print(f"     - {d}")
    else:
        print("  ✅ 无备份目录")
    
    print("\n🔍 4. 配置文件检查:")
    config_files = {
        'pytest.ini': '测试配置',
        'mypy.ini': '类型检查配置',
        'pyproject.toml': '项目配置',
        '.env.example': '环境变量示例'
    }
    
    for file, desc in config_files.items():
        if Path(file).exists():
            print(f"  ✅ {file} ({desc})")
        else:
            print(f"  ❌ {file} ({desc})")
    
    print("\n🔍 5. Python文件统计:")
    src_files = list(Path('src').rglob('*.py'))
    test_files = list(Path('tests').rglob('*.py'))
    
    print(f"  📁 src/: {len(src_files)} 个Python文件")
    print(f"  📁 tests/: {len(test_files)} 个Python文件")
    
    # 检查__init__.py
    missing_inits = 0
    for dir_path in Path('src').rglob('*/'):
        if not (dir_path / '__init__.py').exists() and dir_path != Path('src'):
            missing_inits += 1
    
    if missing_inits > 0:
        print(f"  ❌ {missing_inits} 个目录缺少__init__.py")
    else:
        print("  ✅ 所有目录都有__init__.py")
    
    print("\n" + "=" * 80)
    print("                    问题优先级总结")
    print("=" * 80)
    
    print("\n🚨 立即修复（阻塞性）:")
    print("  1. 语法错误 - 使用 fix_syntax_errors.py 脚本")
    print("  2. 测试收集错误 - 修复导入和缺失方法")
    
    print("\n⚡ 高优先级:")
    print("  1. 删除备份目录")
    print("  2. 补充__init__.py文件")
    
    print("\n📈 中优先级:")
    print("  1. 完善配置文件")
    print("  2. 增加测试覆盖率")

if __name__ == "__main__":
    main()
