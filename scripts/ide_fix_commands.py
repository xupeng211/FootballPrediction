#!/usr/bin/env python3
"""IDE修复命令生成器
使用方法: python -c "import ide_fix_commands; ide_fix_commands.run()"
"""

import subprocess
import sys

ERRORS = [
    ("src/adapters/factory_simple.py", 93, 5, "invalid syntax (<unknown>, line 93)"),
    ("src/adapters/factory.py", 30, 5, "illegal target for annotation (<unknown>, line 30)"),
    ("src/adapters/registry.py", 261, 5, "illegal target for annotation (<unknown>, line 261)"),
    ("src/adapters/football.py", 37, 5, "illegal target for annotation (<unknown>, line 37)"),
    ("src/config/openapi_config.py", 473, 21, "closing parenthesis '}' does not match opening parenthesis '[' on line 454 (<unknown>, line 473)"),
    ("src/api/schemas.py", 16, 5, "illegal target for annotation (<unknown>, line 16)"),
    ("src/api/cqrs.py", 25, 5, "illegal target for annotation (<unknown>, line 25)"),
    ("src/api/buggy_api.py", 11, 5, "invalid syntax (<unknown>, line 11)"),
    ("src/api/dependencies.py", 37, 5, "invalid syntax (<unknown>, line 37)"),
    ("src/api/data_router.py", 33, 5, "illegal target for annotation (<unknown>, line 33)"),
    ("src/api/features.py", 26, 4, "unexpected indent (<unknown>, line 26)"),
    ("src/api/facades.py", 20, 4, "unexpected indent (<unknown>, line 20)"),
    ("src/api/deps.py", 25, 5, "invalid syntax (<unknown>, line 25)"),
    ("src/api/app.py", 33, 4, "unexpected indent (<unknown>, line 33)"),
    ("src/api/decorators.py", 61, 5, "invalid syntax (<unknown>, line 61)"),
    ("src/api/observers.py", 25, 5, "illegal target for annotation (<unknown>, line 25)"),
    ("src/api/repositories.py", 34, 5, "invalid syntax (<unknown>, line 34)"),
    ("src/api/events.py", 64, 5, "invalid syntax (<unknown>, line 64)"),
    ("src/api/adapters.py", 116, 5, "invalid syntax (<unknown>, line 116)"),
    ("src/api/monitoring.py", 51, 5, "illegal target for annotation (<unknown>, line 51)"),
    ("src/api/auth.py", 27, 5, "invalid syntax (<unknown>, line 27)"),
    ("src/api/predictions/models.py", 12, 5, "illegal target for annotation (<unknown>, line 12)"),
    ("src/api/predictions/router.py", 32, 5, "illegal target for annotation (<unknown>, line 32)"),
    ("src/api/data/__init__.py", 24, 5, "expected an indented block after class definition on line 23 (<unknown>, line 24)"),
    ("src/api/data/models/odds_models.py", 13, 5, "illegal target for annotation (<unknown>, line 13)"),
    ("src/api/data/models/match_models.py", 14, 5, "illegal target for annotation (<unknown>, line 14)"),
    ("src/api/data/models/__init__.py", 21, 5, "expected an indented block after class definition on line 20 (<unknown>, line 21)"),
    ("src/api/data/models/league_models.py", 14, 5, "illegal target for annotation (<unknown>, line 14)"),
    ("src/api/data/models/team_models.py", 13, 5, "illegal target for annotation (<unknown>, line 13)"),
    ("src/utils/validators.py", 29, 5, "invalid syntax (<unknown>, line 29)"),
    ("src/utils/response.py", 17, 5, "illegal target for annotation (<unknown>, line 17)"),
    ("src/utils/dict_utils.py", 61, 5, "invalid syntax (<unknown>, line 61)"),
    ("src/utils/time_utils.py", 35, 5, "invalid syntax (<unknown>, line 35)"),
    ("src/utils/data_validator.py", 38, 5, "invalid syntax (<unknown>, line 38)"),
    ("src/utils/file_utils.py", 43, 5, "invalid syntax (<unknown>, line 43)"),
    ("src/utils/redis_cache.py", 19, 5, "invalid syntax (<unknown>, line 19)"),
    ("src/utils/_retry/__init__.py", 21, 5, "invalid syntax (<unknown>, line 21)"),
    ("src/repositories/base.py", 26, 5, "illegal target for annotation (<unknown>, line 26)"),
    ("src/repositories/prediction.py", 134, 15, "unmatched ')' (<unknown>, line 134)"),
    ("src/repositories/user.py", 281, 73, "closing parenthesis ')' does not match opening parenthesis '[' on line 272 (<unknown>, line 281)"),
    ("src/repositories/provider.py", 53, 5, "invalid syntax (<unknown>, line 53)"),
    ("src/repositories/di.py", 29, 5, "invalid syntax (<unknown>, line 29)"),
    ("src/repositories/match.py", 144, 80, "closing parenthesis '}' does not match opening parenthesis '[' (<unknown>, line 144)"),
    ("src/stubs/mocks/feast.py", 112, 5, "closing parenthesis ')' does not match opening parenthesis '[' on line 111 (<unknown>, line 112)"),
    ("src/stubs/mocks/confluent_kafka.py", 21, 5, "closing parenthesis ')' does not match opening parenthesis '[' on line 20 (<unknown>, line 21)"),
    ("src/facades/base.py", 82, 5, "closing parenthesis ')' does not match opening parenthesis '[' on line 81 (<unknown>, line 82)"),
    ("src/facades/facades.py", 52, 5, "closing parenthesis ')' does not match opening parenthesis '[' on line 51 (<unknown>, line 52)"),
    ("src/facades/factory.py", 4, 8, "invalid syntax (<unknown>, line 4)"),
    ("src/patterns/decorator.py", 87, 5, "closing parenthesis ')' does not match opening parenthesis '[' on line 86 (<unknown>, line 87)"),
    ("src/patterns/facade.py", 223, 5, "closing parenthesis ')' does not match opening parenthesis '[' on line 222 (<unknown>, line 223)"),
]

def open_in_editor(file_path, line):
    """在编辑器中打开文件到指定行"""
    editors = [
        ["code", "--goto", f"{file_path}:{line}"],  # VS Code
        ["vim", f"+{line}", file_path],           # Vim
        ["nano", f"+{line}", file_path],         # Nano
    ]

    for editor_cmd in editors:
        try:
            subprocess.run(editor_cmd, check=True)
            print(f"Opened {file_path} at line {line}")
            return
        except:
            continue
    print(f"Could not open {file_path} in any editor")

def run():
    """运行修复命令"""
    print("IDE修复助手")
    print("=" * 50)

    for file_path, line, col, msg in ERRORS:
        print(f"\n文件: {file_path}")
        print(f"错误: 第{line}行第{col}列 - {msg}")
        print("修复建议:")

        # 读取错误行
        with open(file_path, 'r') as f:
            lines = f.readlines()

        if line <= len(lines):
            error_line = lines[line - 1].strip()
            print(f"  当前行: {error_line}")

            # 生成修复建议
            if "illegal target" in msg:
                print("  建议: 移除参数名周围的引号")
                print("  示例: \"param\" -> param")
            elif "unterminated string" in msg:
                print("  建议: 添加闭合的引号")
                print("  示例: \"value -> \"value\"")
            elif "invalid syntax" in msg:
                print("  建议: 检查语法，可能需要添加引号或逗号")

            print(f"\n是否在编辑器中打开? (y/n)")
            # input()  # 取消注释以启用交互
            # open_in_editor(file_path, line)

if __name__ == "__main__":
    run()
