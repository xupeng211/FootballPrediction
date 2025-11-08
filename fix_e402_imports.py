#!/usr/bin/env python3
"""
修复E402 import顺序错误
Fix E402 import order errors
"""

import re
from pathlib import Path

def fix_e402_imports(file_path: Path) -> bool:
    """修复单个文件的E402错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        if len(lines) < 20:  # 跳过太短的文件
            return False

        # 找到导入语句和文档字符串
        imports = []
        docstring = []
        other_lines = []
        after_imports = []
        in_docstring = False
        docstring_ended = False

        for i, line in enumerate(lines):
            # 处理文档字符串
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                if not in_docstring:
                    in_docstring = True
                    docstring.append(line)
                elif line.strip().endswith('"""') or line.strip().endswith("'''"):
                    in_docstring = False
                    docstring.append(line)
                    docstring_ended = True
                else:
                    docstring.append(line)
                continue

            if in_docstring:
                docstring.append(line)
                continue

            # 收集导入语句（在文档字符串之后）
            if docstring_ended or not docstring:
                if (line.strip().startswith('import ') or
                    line.strip().startswith('from ') or
                    line.strip() == '' or
                    line.strip().startswith('#')):

                    # 检查是否是真正的导入行（不是空行或注释）
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        imports.append(line)
                    elif not line.strip() and imports:  # 导入之间的空行
                        imports.append(line)
                    elif not line.strip() and not imports and not docstring_ended:
                        # 文档字符串后的空行，忽略
                        continue
                    else:
                        # 注释行或其他行
                        if not imports:
                            other_lines.append(line)
                        else:
                            after_imports.append(line)
                else:
                    if imports:
                        after_imports.append(line)
                    else:
                        other_lines.append(line)
            else:
                other_lines.append(line)

        # 如果没有找到导入错误，返回False
        if not imports or not after_imports:
            return False

        # 重新组织内容
        new_lines = []

        # 添加原始的from typing import
        typing_import = None
        for line in other_lines[:5]:  # 检查前几行
            if line.strip().startswith('from typing import'):
                typing_import = line
                other_lines.remove(line)
                break

        if typing_import:
            new_lines.append(typing_import)
            new_lines.append('')

        # 添加文档字符串（如果有）
        if docstring:
            new_lines.extend(docstring)
            new_lines.append('')

        # 添加其他非导入行（如果有）
        if other_lines:
            for line in other_lines:
                if line.strip() and not (line.strip().startswith('from typing import') or
                                       line.strip().startswith('"""') or
                                       line.strip().startswith("'''")):
                    new_lines.append(line)

        # 添加导入语句
        new_lines.extend(imports)
        new_lines.append('')

        # 添加剩余的代码
        if after_imports:
            new_lines.extend(after_imports)

        # 写回文件
        new_content = '\n'.join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"修复文件 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    base_path = Path("src")

    # 需要修复的文件列表（从ruff输出中提取）
    files_to_fix = [
        "cache/redis_manager.py",
        "database/models/data_collection_log.py",
        "domain/events/match_events.py",
        "facades/subsystems/database.py",
        "quality_gates/gate_system.py",
        "realtime/match_api.py",
        "scheduler/celery_config.py",
        "services/database/database_service.py",
        "utils/_retry/__init__.py"
    ]

    fixed_count = 0

    for file_path_str in files_to_fix:
        file_path = base_path / file_path_str
        if file_path.exists():
            print(f"正在修复: {file_path}")
            if fix_e402_imports(file_path):
                print(f"✓ 修复了: {file_path}")
                fixed_count += 1
            else:
                print(f"- 无需修复或修复失败: {file_path}")
        else:
            print(f"文件不存在: {file_path}")

    print(f"\n总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()