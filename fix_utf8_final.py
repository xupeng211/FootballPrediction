#!/usr/bin/env python3
"""
最终版UTF-8编码修复脚本
"""

import os
import re
import glob


def fix_file(filepath):
    """修复单个文件的UTF-8编码问题"""
    print(f"正在修复: {filepath}")

    try:
        # 以二进制模式读取
        with open(filepath, "rb") as f:
            raw_data = f.read()

        # 移除UTF-8 BOM（如果有）
        if raw_data.startswith(b"\xef\xbb\xbf"):
            raw_data = raw_data[3:]

        # 清理无效的UTF-8序列
        # 特别是EF BF BD（替换字符）
        cleaned_data = raw_data.replace(b"\xef\xbf\xbd", b"")

        # 尝试解码
        text = cleaned_data.decode("utf-8", errors="replace")

        # 额外清理：移除其他无效控制字符（保留换行、制表符等）
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # 确保文件以换行符结尾
        if not text.endswith("\n"):
            text += "\n"

        # 写回文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"✅ 成功修复: {filepath}")
        return True

    except Exception as e:
        print(f"❌ 修复失败 {filepath}: {e}")
        return False


def main():
    """主函数"""
    # 需要修复的文件模式
    patterns = [
        "src/monitoring/alerts/channels/*.py",
        "src/monitoring/alerts/channels/**/*.py",
    ]

    # 收集所有需要修复的文件
    files_to_fix = []
    for pattern in patterns:
        files_to_fix.extend(glob.glob(pattern, recursive=True))

    # 去重
    files_to_fix = list(set(files_to_fix))

    print(f"找到 {len(files_to_fix)} 个需要检查的文件")

    success_count = 0
    for filepath in files_to_fix:
        if fix_file(filepath):
            success_count += 1

    print(f"\n修复完成: {success_count}/{len(files_to_fix)} 个文件")

    # 验证修复结果
    print("\n验证修复结果:")
    for filepath in files_to_fix[:5]:  # 只检查前5个
        os.system(f'file "{filepath}"')


if __name__ == "__main__":
    main()
