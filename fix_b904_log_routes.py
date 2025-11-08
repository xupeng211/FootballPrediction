#!/usr/bin/env python3
"""
专门修复log_routes.py中B904异常处理错误的脚本
"""

import re

def fix_log_routes_b904():
    """修复log_routes.py中的B904错误"""

    file_path = 'src/monitoring/log_routes.py'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 匹配模式：except Exception as e: 后面跟着logger.error然后raise HTTPException
    # 使用正则表达式进行替换
    pattern = r'(\s+except Exception as e:\s*\n\s+logger\.error\(f"[^"]*\{e\}"\)\s*\n(\s+raise HTTPException\([^)]+\))\s*$'

    def replacement_func(match):
        except_block = match.group(1)
        raise_block = match.group(2)
        # 检查raise语句是否已经有from
        if ' from ' not in raise_block:
            return f"{except_block}\n{raise_block.rstrip()} from e"
        return match.group(0)

    # 应用替换
    content = re.sub(pattern, replacement_func, content, flags=re.MULTILINE)

    # 如果内容有变化，写回文件
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    return False

if __name__ == "__main__":
    print("正在修复src/monitoring/log_routes.py中的B904错误...")
    if fix_log_routes_b904():
        print("✓ B904错误修复成功")
    else:
        print("✗ 没有找到需要修复的B904错误或修复失败")