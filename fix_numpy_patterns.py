#!/usr/bin/env python3
"""
批量修复测试中的numpy随机数问题
"""
import re

def fix_numpy_random_patterns(file_path):
    """修复文件中的numpy随机数模式"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 统计替换次数
    replacements = 0

    # 模式1: np.random.normal(mean, std, size)
    pattern1 = r'np\.random\.normal\(([^,]+),\s*([^,]+),\s*([^)]+)\)'

    def replace_normal(match):
        nonlocal replacements
        mean = match.group(1).strip()
        std = match.group(2).strip()
        size = match.group(3).strip()

        # 生成类似的确定数据
        if size.isdigit():
            size_int = int(size)
            if mean.replace('.', '').isdigit() and std.replace('.', '').isdigit():
                # 数值参数，生成线性分布
                replacements += 1
                return f"[{mean} + {std} * (i - {size_int}//2) / 20 for i in range({size_int})]"

        return match.group(0)

    content = re.sub(pattern1, replace_normal, content)

    # 模式2: np.random.rand(...)
    pattern2 = r'np\.random\.rand\(([^)]+)\)'

    def replace_rand(match):
        nonlocal replacements
        args = match.group(1).strip()

        if args.isdigit():
            size = int(args)
            replacements += 1
            if size == 1:
                return "0.5"
            elif size == 2:
                return "[0.5, 0.5]"
            else:
                return f"[i/{size} for i in range({size})]"

        return match.group(0)

    content = re.sub(pattern2, replace_rand, content)

    if replacements > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {replacements} numpy patterns in {file_path}")
        return True
    else:
        print(f"No numpy patterns found in {file_path}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        fix_numpy_random_patterns(file_path)
    else:
        print("Usage: python fix_numpy.py <file_path>")