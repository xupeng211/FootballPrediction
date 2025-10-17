#!/usr/bin/env python3
"""
只检查项目核心文件的损坏情况
"""

import ast
from pathlib import Path

def check_core_files():
    """检查核心项目文件"""
    core_files = [
        # 核心模块
        'src/main.py',
        'src/api/app.py',
        'src/api/__init__.py',
        'src/core/__init__.py',
        'src/core/prediction_engine.py',
        'src/core/config.py',

        # 数据库
        'src/database/__init__.py',
        'src/database/models/__init__.py',
        'src/database/models/match.py',
        'src/database/models/team.py',
        'src/database/session.py',

        # 工具类
        'src/utils/__init__.py',
        'src/utils/string_utils.py',
        'src/utils/helpers.py',
        'src/utils/crypto_utils.py',

        # 测试配置
        'tests/conftest.py',
        'tests/__init__.py',

        # 配置文件
        'pytest.ini',
        'pyproject.toml',
        'requirements/requirements.lock',
    ]

    print("核心文件损坏情况检查")
    print("=" * 60)

    good_files = []
    bad_files = []

    for file_path in core_files:
        path = Path(file_path)
        if not path.exists():
            print(f"❌ {file_path} - 文件不存在")
            continue

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否是Python文件
            if file_path.endswith('.py'):
                ast.parse(content)
                print(f"✅ {file_path} - 语法正确")
                good_files.append(file_path)
            else:
                print(f"✅ {file_path} - 配置文件")
                good_files.append(file_path)

        except SyntaxError as e:
            print(f"❌ {file_path} - 语法错误: {e}")
            bad_files.append((file_path, str(e)))
        except Exception as e:
            print(f"❌ {file_path} - 其他错误: {e}")
            bad_files.append((file_path, str(e)))

    print("\n" + "=" * 60)
    print(f"核心文件统计:")
    print(f"• 正常文件: {len(good_files)}")
    print(f"• 损坏文件: {len(bad_files)}")

    if bad_files:
        print("\n需要修复的关键文件:")
        for file_path, error in bad_files:
            if any(keyword in file_path for keyword in ['main.py', 'app.py', 'conftest.py', 'string_utils.py']):
                print(f"🔥 {file_path} - {error[:60]}...")

    return len(bad_files)

if __name__ == '__main__':
    exit(check_core_files())