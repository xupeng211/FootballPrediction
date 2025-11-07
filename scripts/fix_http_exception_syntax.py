#!/usr/bin/env python3
"""
修复被sed命令破坏的HTTPException语法
"""

from pathlib import Path


def fix_http_exception_syntax(content):
    """修复HTTPException语法错误"""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 检测破坏的raise语句
        if 'raise HTTPException(... from e' in line:
            # 找到完整的raise语句块
            indent = len(line) - len(line.lstrip())
            result.append(line.replace('raise HTTPException(... from e', 'raise HTTPException('))
            i += 1

            # 添加参数行，直到找到结束的)
            while i < len(lines):
                current_line = lines[i]
                if ')' in current_line and 'from e' in current_line:
                    # 修复这一行：移除重复的 from e
                    result.append(current_line.replace(') from e  #', ')  #').replace(') from e', ')'))
                    i += 1
                    break
                else:
                    result.append(current_line)
                    i += 1

            # 添加from e子句
            result.append(' ' * indent + ') from e  # TODO: B904 exception chaining')
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)

def main():
    """主函数"""
    print("🔧 修复HTTPException语法错误...")

    fixed_files = 0
    for py_file in Path("src").rglob("*.py"):
        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            # 检查是否有语法错误
            if 'raise HTTPException(... from e' in content:
                fixed_content = fix_http_exception_syntax(content)

                if content != fixed_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    print(f"✅ 修复了: {py_file}")
                    fixed_files += 1
        except Exception as e:
            print(f"❌ 处理文件失败 {py_file}: {e}")

    print(f"🎉 总共修复了 {fixed_files} 个文件")

if __name__ == "__main__":
    main()
