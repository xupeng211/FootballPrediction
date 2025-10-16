#!/usr/bin/env python3
"""手动语法修复计划生成器"""

import os
import subprocess
import sys
from pathlib import Path

def get_syntax_errors():
    """获取所有语法错误"""
    error_files = []
    python_files = []

    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"检查 {len(python_files)} 个文件的语法错误...")

    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, file_path, 'exec')
        except SyntaxError as e:
            error_files.append({
                'file': file_path,
                'line': e.lineno,
                'msg': e.msg,
                'text': e.text if hasattr(e, 'text') else ''
            })
        except Exception as e:
            error_files.append({
                'file': file_path,
                'line': 0,
                'msg': str(e),
                'text': ''
            })

    return error_files

def categorize_errors(errors):
    """对错误进行分类"""
    categories = {
        'illegal_target': [],
        'unterminated_string': [],
        'invalid_syntax': [],
        'unmatched': [],
        'unexpected_indent': [],
        'others': []
    }

    for error in errors:
        msg = error['msg'].lower()
        if 'illegal target' in msg:
            categories['illegal_target'].append(error)
        elif 'unterminated string' in msg:
            categories['unterminated_string'].append(error)
        elif 'invalid syntax' in msg:
            categories['invalid_syntax'].append(error)
        elif 'unmatched' in msg or 'does not match' in msg:
            categories['unmatched'].append(error)
        elif 'unexpected indent' in msg:
            categories['unexpected_indent'].append(error)
        else:
            categories['others'].append(error)

    return categories

def generate_repair_plan():
    """生成修复计划"""
    print("生成手动语法修复计划...")
    print("=" * 60)

    # 获取所有错误
    errors = get_syntax_errors()
    print(f"\n发现 {len(errors)} 个语法错误文件")

    # 分类错误
    categories = categorize_errors(errors)

    print("\n错误分类:")
    for cat_name, cat_errors in categories.items():
        if cat_errors:
            print(f"  - {cat_name}: {len(cat_errors)} 个文件")

    # 生成修复脚本
    with open('manual_repair_script.py', 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""手动语法修复脚本\n')
        f.write('按照优先级修复语法错误\n"""\n\n')
        f.write('import os\n\n')
        f.write('# 错误修复计划\n')
        f.write('ERRORS_TO_FIX = [\n')

        # 按优先级添加错误（最简单的先修复）
        for error in categories['unterminated_string'][:10]:
            f.write(f'    ("{error["file"]}", {error["line"]}, "unterminated_string"),\n')

        for error in categories['illegal_target'][:10]:
            f.write(f'    ("{error["file"]}", {error["line"]}, "illegal_target"),\n')

        for error in categories['invalid_syntax'][:10]:
            f.write(f'    ("{error["file"]}", {error["line"]}, "invalid_syntax"),\n')

        f.write(']\n\n')

        # 生成修复函数
        f.write('def fix_unterminated_string(file_path, line_num):\n')
        f.write('    """修复未闭合的字符串"""\n')
        f.write('    with open(file_path, "r") as f:\n')
        f.write('        lines = f.readlines()\n')
        f.write('    \n')
        f.write('    if line_num <= len(lines):\n')
        f.write('        line = lines[line_num - 1]\n')
        f.write('        if line.count(\'"\') % 2 == 1:\n')
        f.write('            if line.rstrip().endswith(\',\'):\n')
        f.write('                lines[line_num - 1] = line[:-1] + \'",\\n\'\n')
        f.write('            else:\n')
        f.write('                lines[line_num - 1] = line + \'"\\n\'\n')
        f.write('            \n')
        f.write('            with open(file_path, "w") as f:\n')
        f.write('                f.writelines(lines)\n')
        f.write('            print(f"  ✓ 修复: {file_path}:{line_num}")\n')
        f.write('            return True\n')
        f.write('    return False\n\n')

        f.write('def fix_illegal_target(file_path, line_num):\n')
        f.write('    """修复类型注解错误"""\n')
        f.write('    with open(file_path, "r") as f:\n')
        f.write('        lines = f.readlines()\n')
        f.write('    \n')
        f.write('    if line_num <= len(lines):\n')
        f.write('        line = lines[line_num - 1]\n')
        f.write('        # 移除参数名中的引号\n')
        f.write('        import re\n')
        f.write('        fixed_line = re.sub(r\'"(\\w+)":\', r\'\\1:\', line)\n')
        f.write('        if fixed_line != line:\n')
        f.write('            lines[line_num - 1] = fixed_line\n')
        f.write('            with open(file_path, "w") as f:\n')
        f.write('                f.writelines(lines)\n')
        f.write('            print(f"  ✓ 修复: {file_path}:{line_num}")\n')
        f.write('            return True\n')
        f.write('    return False\n\n')

        f.write('def main():\n')
        f.write('    """主修复函数"""\n')
        f.write('    print("开始手动修复...")\n')
        f.write('    \n')
        f.write('    for file_path, line_num, error_type in ERRORS_TO_FIX:\n')
        f.write('        print(f"\\n处理: {file_path}")\n')
        f.write('        print(f"  第{line_num}行: {error_type}")\n')
        f.write('        \n')
        f.write('        if error_type == "unterminated_string":\n')
        f.write('            fix_unterminated_string(file_path, line_num)\n')
        f.write('        elif error_type == "illegal_target":\n')
        f.write('            fix_illegal_target(file_path, line_num)\n')
        f.write('        else:\n')
        f.write('            print(f"  跳过: 需要手动修复")\n')
        f.write('            print(f"  命令: vim {file_path} +{line_num}")\n\n')

        f.write('if __name__ == "__main__":\n')
        f.write('    main()\n')

    os.chmod('manual_repair_script.py', 0o755)

    # 生成详细报告
    with open('syntax_repair_plan.md', 'w') as f:
        f.write('# 语法修复计划\n\n')
        f.write(f'总错误数: {len(errors)}\n\n')

        f.write('## 错误分类\n\n')
        for cat_name, cat_errors in categories.items():
            if cat_errors:
                f.write(f'### {cat_name} ({len(cat_errors)} 个)\n\n')
                for error in cat_errors[:5]:  # 只显示前5个
                    f.write(f'- `{error["file"]}`:{error["line"]} - {error["msg"]}\n')
                if len(cat_errors) > 5:
                    f.write(f'  ... 还有 {len(cat_errors) - 5} 个\n')
                f.write('\n')

        f.write('## 修复优先级\n\n')
        f.write('1. **未闭合的字符串** - 最容易修复\n')
        f.write('2. **类型注解错误** - 移除多余的引号\n')
        f.write('3. **无效语法** - 需要具体分析\n')
        f.write('4. **括号不匹配** - 需要仔细检查\n')
        f.write('5. **缩进错误** - 调整缩进\n\n')

        f.write('## 快速修复命令\n\n')
        f.write('```bash\n')
        f.write('# 运行自动修复脚本\n')
        f.write('python manual_repair_script.py\n\n')
        f.write('# 或使用IDE逐个修复\n')
        for error in errors[:10]:
            f.write(f'# vim {error["file"]} +{error["line"]}\n')
        f.write('```\n')

    print("\n修复计划已生成:")
    print("  - manual_repair_script.py: 自动修复脚本")
    print("  - syntax_repair_plan.md: 详细修复计划")

if __name__ == "__main__":
    generate_repair_plan()