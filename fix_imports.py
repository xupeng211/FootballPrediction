#!/usr/bin/env python3
"""
自动修复E402导入顺序错误的脚本
"""

import ast
import re
from pathlib import Path

def fix_file_imports(file_path: Path) -> bool:
    """修复单个文件的导入顺序问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析AST
        tree = ast.parse(content)

        # 收集所有导入语句
        imports = []
        docstring = None
        code_after_imports = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                imports.append(node)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                if docstring is None:
                    docstring = node.value.value
            else:
                code_after_imports.append(node)

        if not imports:
            return False  # 没有需要修复的导入

        # 按类型分组导入
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for imp in imports:
            # 获取导入语句的源代码
            start_line = imp.lineno - 1
            lines = content.split('\n')

            # 找到完整的导入语句（可能跨越多行）
            import_lines = []
            paren_level = 0
            i = start_line

            while i < len(lines):
                line = lines[i]
                import_lines.append(line)

                # 计算括号层级
                paren_level += line.count('(') - line.count(')')

                # 如果括号层级为0且行不是以\结尾，说明导入结束
                if paren_level == 0 and not line.rstrip().endswith('\\'):
                    break
                i += 1

            import_code = '\n'.join(import_lines)

            # 判断导入类型
            if isinstance(imp, ast.ImportFrom):
                if imp.module and imp.module.startswith('src.'):
                    local_imports.append(import_code)
                elif imp.module and any(imp.module.startswith(lib) for lib in ['fastapi', 'pydantic', 'sqlalchemy', 'redis']):
                    third_party_imports.append(import_code)
                else:
                    stdlib_imports.append(import_code)
            else:  # ast.Import
                if any(name.startswith('src.') for name in imp.names):
                    local_imports.append(import_code)
                elif any(name.name in ['fastapi', 'pydantic', 'sqlalchemy', 'redis'] for name in imp.names):
                    third_party_imports.append(import_code)
                else:
                    stdlib_imports.append(import_code)

        # 重新构建文件内容
        new_content_parts = []

        # 添加标准库导入
        if stdlib_imports:
            new_content_parts.extend(stdlib_imports)
            new_content_parts.append('')

        # 添加第三方库导入
        if third_party_imports:
            new_content_parts.extend(third_party_imports)
            new_content_parts.append('')

        # 添加本地导入
        if local_imports:
            new_content_parts.extend(local_imports)
            new_content_parts.append('')

        # 添加文档字符串
        if docstring:
            new_content_parts.append(f'"""{docstring}"""')
            new_content_parts.append('')

        # 添加其他代码
        for node in code_after_imports:
            # 重新生成节点代码
            start_line = node.lineno - 1
            if hasattr(node, 'end_lineno'):
                end_line = node.end_lineno - 1
            else:
                end_line = start_line

            lines = content.split('\n')
            node_code = '\n'.join(lines[start_line:end_line + 1])
            new_content_parts.append(node_code)

        new_content = '\n'.join(new_content_parts)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    src_dir = Path("src")

    # 查找所有Python文件
    python_files = list(src_dir.rglob("*.py"))

    fixed_count = 0
    for file_path in python_files:
        if fix_file_imports(file_path):
            print(f"修复了文件: {file_path}")
            fixed_count += 1

    print(f"总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()