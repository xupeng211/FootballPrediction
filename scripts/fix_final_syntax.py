#!/usr/bin/env python3
"""
最终语法修复脚本 - 修复所有剩余语法错误
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

def fix_all_errors(content: str, file_path: str) -> str:
    """修复所有语法错误"""
    fixes = 0
    original = content

    # 1. 修复中文标点为英文标点（仅在非字符串部分）
    chinese_to_english = {
        '（': '(',
        '）': ')',
        '，': ',',
        '。': '.',
        '：': ':',
        '；': ';',
        '！': '!',
        '？': '?',
        '【': '[',
        '】': ']',
        '｛': '{',
        '｝': '}',
        '、': ',',
    }

    # 逐行处理，跳过注释和字符串
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 跳过注释行
        if line.strip().startswith('#'):
            continue

        # 跳过文档字符串
        if '"""' in line or "'''" in line:
            # 简单判断是否在文档字符串中
            if line.count('"""') == 1 or line.count("'''") == 1:
                continue

        # 替换中文标点
        for chinese, english in chinese_to_english.items():
            if chinese in line:
                line = line.replace(chinese, english)
                fixes += 1

        lines[i] = line

    content = '\n'.join(lines)

    # 2. 修复类型注解错误
    content = re.sub(r'Optional\[Dict\[str, Any\]\]\s*=\s*None',
                    r'Optional[Dict[str, Any]] = None', content)
    content = re.sub(r'Optional\[List\[str\]\]\s*=\s*None',
                    r'Optional[List[str]] = None', content)
    content = re.sub(r'Optional\[List\[Dict\[str, Any\]\]\]\s*=\s*None',
                    r'Optional[List[Dict[str, Any]]] = None', content)

    # 3. 修复函数参数中的类型注解
    content = re.sub(r'(\w+):\s*Optional\[Dict\[str, Any\]\s*\]\s*=\s*None',
                    r'\1: Optional[Dict[str, Any]] = None', content)
    content = re.sub(r'(\w+):\s*Optional\[List\[str\]\s*\]\s*=\s*None',
                    r'\1: Optional[List[str]] = None', content)

    # 4. 修复字典初始化错误
    content = re.sub(r'{\s*"errors":\s*\[\],\s*"warnings":\s*\[\]\}',
                    r'{"errors": [], "warnings": []}', content)
    content = re.sub(r'{\s*"errors":\s*\[\],\s*"warnings":\s*\[\}',
                    r'{"errors": [], "warnings": []}', content)
    content = re.sub(r'{\s*"errors":\s*\[,\s*"warnings":\s*\[\}',
                    r'{"errors": [], "warnings": []}', content)

    # 5. 修复列表初始化
    content = re.sub(r'List\[Any\]\s*=\s*\{\[\]', r'List[Any] = []', content)
    content = re.sub(r'List\[Any\]\s*=\s*\{\}', r'List[Any] = []', content)
    content = re.sub(r'List\[Any\]\s*=\s*{\[\]', r'List[Any] = []', content)

    # 6. 修复 f-string 引号问题
    content = re.sub(r'f"([^"]*?)\'([^"]*?)"', r'f"\1\2"', content)
    content = re.sub(r"f'([^']*?)\"([^']*?)'", r"f'\1\2'", content)

    # 7. 修复函数定义中的参数错误
    # 修复 Union 类型
    content = re.sub(r'Union\[Dict\[str, Any\],\s*List\[Dict\[str, Any\],\s*pd\.DataFrame\]',
                    r'Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame]', content)

    # 8. 修复函数参数缺少的括号
    content = re.sub(r'raw_data:\s*Union\[Dict\[str, Any\],\s*List\[Dict\[str, Any\]\]\s*=\s*None',
                    r'raw_data: Union[Dict[str, Any], List[Dict[str, Any]]] = None', content)

    # 9. 修复函数返回类型注解
    content = re.sub(r'\)\s*-\s*>\s*Dict\[str, Any\]:', r') -> Dict[str, Any]:', content)
    content = re.sub(r'\)\s*-\s*>\s*Optional\[Dict\[str, Any\]\]:', r') -> Optional[Dict[str, Any]]:', content)

    # 10. 修复未闭合的字符串
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 修复行尾未闭合的字符串
        if line.count('"') % 2 == 1 and not line.strip().endswith('"'):
            line += '"'
            fixes += 1
        elif line.count("'") % 2 == 1 and not line.strip().endswith("'"):
            line += "'"
            fixes += 1
        lines[i] = line
    content = '\n'.join(lines)

    # 11. 特定文件的修复
    if 'data_validator.py' in file_path:
        # 修复验证规则中的错误
        content = re.sub(r'"required_fields":\s*\[\s*"([^"]+)"\s*,\s*\n\s*"([^"]+)"',
                        r'"required_fields": [\n            "\1",\n            "\2"', content)
        content = re.sub(r'"errors":\s*\[\s*"([^"]+)"\s*,',
                        r'"errors": ["\1"],', content)

    elif 'processing_cache.py' in file_path:
        # 修复缓存配置中的错误
        content = re.sub(r'"match_processing":\s*3600,\s*#\s*1小时"',
                        r'"match_processing": 3600,  # 1小时', content)
        content = re.sub(r'"hits":\s*0,',
                        r'"hits": 0,', content)

    elif 'match_processor.py' in file_path:
        # 修复处理器中的错误
        content = re.sub(r'cleaned_data\s*=\s*await',
                        r'cleaned_data = await', content)
        content = re.sub(r'standardized_data\s*=\s*await',
                        r'standardized_data = await', content)

    # 12. 修复字典值中的引号错误
    content = re.sub(r':\s*"([^"]*?)\s*,\s*\n', r': "\1",\n        ', content)

    # 13. 修复类属性定义中的错误
    content = re.sub(r'self\.(\w+)\s*=\s*{\s*',
                    r'self.\1 = {\n            ', content)

    # 14. 修复多行字符串中的引号
    content = re.sub(r'"""\s*\n\s*"([^"]+)"\s*\n\s*"""',
                    r'"""\n            \1\n        """', content)

    return content

def main():
    """主函数"""
    print("开始最终语法修复...")

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
    total_fixes = 0

    for file_path in error_files:
        print(f"\n处理: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            content = original_content
            content = fix_all_errors(content, file_path)

            # 如果有修复，保存文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ 文件已修复")
                fixed_count += 1

                # 验证修复是否成功
                if check_syntax(file_path):
                    print(f"  ✓ 语法错误已修复")
                else:
                    print(f"  ✗ 仍有语法错误")
                    # 尝试显示具体错误
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        print(f"    错误位置: 第{e.lineno}行")
                        print(f"    错误信息: {e.msg}")
                        lines = content.split('\n')
                        if 0 <= e.lineno - 1 < len(lines):
                            print(f"    错误行: {lines[e.lineno - 1][:100]}")
            else:
                print(f"  - 未找到需要修复的内容")

        except Exception as e:
            print(f"  ✗ 处理失败: {e}")

    print(f"\n修复完成！")
    print(f"- 处理文件: {len(error_files)}")
    print(f"- 成功修复: {fixed_count}")

    # 再次检查
    remaining_errors = []
    for file_path in python_files:
        if not check_syntax(file_path):
            remaining_errors.append(file_path)

    if remaining_errors:
        print(f"\n仍有 {len(remaining_errors)} 个文件存在语法错误:")
        for file_path in remaining_errors[:10]:
            print(f"  - {file_path}")
        if len(remaining_errors) > 10:
            print(f"  ... 还有 {len(remaining_errors) - 10} 个文件")

        # 提供手动修复建议
        print("\n手动修复建议:")
        print("1. 检查文件中的中文标点符号，替换为英文标点")
        print("2. 确保所有字符串都正确闭合")
        print("3. 检查括号是否匹配")
        print("4. 检查类型注解的语法")
    else:
        print("\n✓ 所有文件的语法错误都已修复！")
        print(f"\n语法修复统计:")
        print(f"- 总文件数: {len(python_files)}")
        print(f"- 成功修复: {fixed_count}")
        print(f"- 成功率: {(len(python_files) - len(remaining_errors)) / len(python_files) * 100:.1f}%")

if __name__ == "__main__":
    main()
