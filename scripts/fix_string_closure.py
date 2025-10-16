#!/usr/bin/env python3
"""
修复字符串闭合和括号匹配问题
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

def fix_string_closure(content: str) -> str:
    """修复未闭合的字符串"""
    lines = content.split('\n')

    for i, line in enumerate(lines):
        # 跳过注释和空行
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # 检查字典行，修复缺失的引号
        if '"' in line:
            # 查找字典键值对
            # 模式: "key": value,
            matches = re.finditer(r'"([^"]+)"\s*:\s*([^,}]+),?', line)
            for match in matches:
                key = match.group(1)
                value = match.group(2).strip()

                # 如果值没有闭合的引号
                if value.startswith('"') and not value.endswith('"'):
                    # 检查行尾是否有逗号
                    if line.endswith(','):
                        line = line[:-1] + '",'
                    else:
                        line = line + '"'
                elif value.startswith("'") and not value.endswith("'"):
                    if line.endswith(','):
                        line = line[:-1] + "',"
                    else:
                        line = line + "'"

        # 特殊处理：修复行尾的字典值
        if line.endswith('",') and line.count('"') % 2 == 1:
            # 奇数个引号，说明有未闭合的字符串
            line = line[:-2] + '",'
        elif line.endswith("',") and line.count("'") % 2 == 1:
            line = line[:-2] + "',"

        # 修复特定的模式错误
        # 1. 修复 f-string 结尾
        if 'f"' in line and line.endswith('"') and line.count('f"') > line.count('"') // 2:
            line += '"'
        elif "f'" in line and line.endswith("'") and line.count("f'") > line.count("'") // 2:
            line += "'"

        # 2. 修复字典中的字符串值
        if ': "' in line and not line.endswith('"') and not line.endswith('",'):
            # 检查是否需要添加引号
            if line.count('"') % 2 == 1:
                if line.endswith(','):
                    line = line[:-1] + '",'
                else:
                    line = line + '"'

        lines[i] = line

    return '\n'.join(lines)

def fix_bracket_mismatch(content: str) -> str:
    """修复括号不匹配"""
    # 修复函数参数中的括号
    # List[Dict[str, Any]) -> List[Dict[str, Any]]
    content = re.sub(r'List\[Dict\[str, Any\]\)', r'List[Dict[str, Any]]', content)
    content = re.sub(r'Optional\[List\[Dict\[str, Any\]\)\]', r'Optional[List[Dict[str, Any]]]', content)
    content = re.sub(r'Optional\[Dict\[str, Any\)\]', r'Optional[Dict[str, Any]]', content)

    # 修复函数参数列表
    content = re.sub(r'List\[Dict\[str, Any\]\s*->\s*None:', r'List[Dict[str, Any]]) -> None:', content)
    content = re.sub(r'Dict\[str, Any\]\s*->\s*None:', r'Dict[str, Any]]) -> None:', content)
    content = re.sub(r'Union\[.*?\]\s*->\s*None:', r'Union[.*?]]) -> None:', content)

    # 修复类型注解中的括号
    content = re.sub(r'(\w+):\s*(List\[Dict\[str, Any\])\s*->', r'\1: \2) ->', content)
    content = re.sub(r'(\w+):\s*(Optional\[Dict\[str, Any\])\s*->', r'\1: \2) ->', content)

    return content

def fix_specific_errors(content: str, file_path: str) -> str:
    """修复特定文件的错误"""
    # 修复字典初始化
    content = re.sub(r'{\s*"consistent":\s*True,\s*"issues":\s*\[,\s*"statistics":',
                    r'{"consistent": True,\n            "issues": [],\n            "statistics": {', content)

    # 修复统计信息中的错误
    content = re.sub(r'"total_records":\s*len\(df\),', r'"total_records": len(df),', content)
    content = re.sub(r'"total_columns":\s*len\(df\.columns\),', r'"total_columns": len(df.columns),', content)

    # 修复缓存配置
    content = re.sub(r'"match_processing":\s*3600,\s*#\s*1小时",',
                    r'"match_processing": 3600,  # 1小时', content)

    # 修复函数参数中的特殊错误
    if 'bulk_create' in file_path:
        content = re.sub(r'List\[Dict\[str, Any\)\s*->\s*List\[User\]:',
                        r'List[Dict[str, Any]]) -> List[User]:', content)

    # 修复 Union 类型错误
    content = re.sub(r'Union\[Dict\[str, Any\],\s*List\[Dict\[str, Any\],\s*pd\.DataFrame\]',
                    r'Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame]', content)

    return content

def main():
    """主函数"""
    print("开始修复字符串闭合和括号问题...")

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
            content = fix_string_closure(content)
            content = fix_bracket_mismatch(content)
            content = fix_specific_errors(content, file_path)

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
        print(f"\n仍有 {len(remaining_errors)} 个文件存在语法错误")
        print("\n这些文件需要手动修复。主要问题类型:")
        print("1. 未闭合的字符串字面量")
        print("2. 括号不匹配")
        print("3. 无效的语法（如前导零）")
        print("\n建议使用 IDE 或编辑器的语法高亮功能来定位和修复这些问题")
    else:
        print("\n✓ 所有文件的语法错误都已修复！")

if __name__ == "__main__":
    main()
