#!/usr/bin/env python3
"""
清理文件末尾的多余括号和引号
"""

import os
import re
import ast
from pathlib import Path

def check_syntax(file_path: str) -> bool:
    """检查文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError:
        return False
    except Exception:
        return False

def clean_file_ending(content: str) -> str:
    """清理文件末尾的多余字符"""
    # 移除文件末尾多余的括号、引号等
    patterns = [
        r'[\]}]+$',  # 文件末尾多余的 ] 和 }
        r'"}]+$',   # 文件末尾多余的 " 和 }
        r"'\]}+$",  # 文件末尾多余的 ' 和 }
        r'"]+$',    # 文件末尾多余的 " 和 ]
        r"']+$",    # 文件末尾多余的 ' 和 ]
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content)

    # 确保文件以换行符结尾
    if content and not content.endswith('\n'):
        content += '\n'

    return content

def fix_specific_patterns(content: str) -> str:
    """修复特定的模式错误"""
    # 修复末尾多余的逗号和引号组合
    content = re.sub(r'",$', '"', content)
    content = re.sub(r"',$", "'", content)

    # 修复字典中的错误模式
    content = re.sub(r':\s*\[\s*,\s*$', ': [],', content)
    content = re.sub(r':\s{\s*,\s*$', ': {},', content)

    # 修复函数参数中的错误
    content = re.sub(r'List\[Dict\[str, Any\]\s*->\s*List\[User\]:',
                    r'List[Dict[str, Any]]) -> List[User]:', content)
    content = re.sub(r'List\[Dict\[str, Any\]\s*->\s*List\[Match\]:',
                    r'List[Dict[str, Any]]) -> List[Match]:', content)
    content = re.sub(r'List\[Dict\[str, Any\]\s*->\s*List\[Prediction\]:',
                    r'List[Dict[str, Any]]) -> List[Prediction]:', content)

    # 修复返回类型注解
    content = re.sub(r'->\s*Dict\[str, Any\s*$', '-> Dict[str, Any]:', content)

    # 修复特定的字符串错误
    content = re.sub(r'(\w+)\]$', r'\1]', content)

    return content

def main():
    """主函数"""
    print("开始清理文件末尾的多余字符...")

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    # 检查哪些文件有语法错误
    error_files = []
    for file_path in python_files:
        if not check_syntax(file_path):
            error_files.append(file_path)

    print(f"\n发现 {len(error_files)} 个文件有语法错误")

    if not error_files:
        print("所有文件语法都正确！")
        return

    # 修复每个文件
    fixed_count = 0

    for file_path in error_files:
        print(f"\n处理: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            content = original_content

            # 应用修复
            content = clean_file_ending(content)
            content = fix_specific_patterns(content)

            # 如果有修复，保存文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ 文件已清理")
                fixed_count += 1

                # 验证修复是否成功
                if check_syntax(file_path):
                    print(f"  ✓ 语法错误已修复")
                else:
                    print(f"  ✗ 仍有语法错误")
                    # 显示第一个错误
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        print(f"    错误位置: 第{e.lineno}行")
                        print(f"    错误信息: {e.msg}")
            else:
                print(f"  - 未找到需要清理的内容")

        except Exception as e:
            print(f"  ✗ 处理失败: {e}")

    print(f"\n清理完成！")
    print(f"- 处理文件: {len(error_files)}")
    print(f"- 成功修复: {fixed_count}")

    # 再次检查
    remaining_errors = []
    for file_path in python_files:
        if not check_syntax(file_path):
            remaining_errors.append(file_path)

    if remaining_errors:
        print(f"\n仍有 {len(remaining_errors)} 个文件存在语法错误")
        print("\n建议:")
        print("1. 使用IDE的语法检查功能定位具体错误")
        print("2. 检查未闭合的字符串、括号不匹配等问题")
        print("3. 运行 python -m py_compile <文件名> 查看具体错误")
    else:
        print("\n✓ 所有文件的语法错误都已修复！")

if __name__ == "__main__":
    main()
