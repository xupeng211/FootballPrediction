#!/usr/bin/env python3
"""
快速修复脚本
直接处理具体文件的语法错误
"""

import os
from pathlib import Path


def fix_file(file_path: str):
    """修复单个文件的常见语法错误"""
    path = Path(file_path)

    if not path.exists():
        print(f"文件不存在: {file_path}")
        return False

    try:
        # 读取文件
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复常见的语法错误
        # 1. 修复 __all__ = [) 的问题
        content = content.replace("__all__ = [)", "__all__ = [")

        # 2. 修复字典的括号问题
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # 查找类似 {"key": value,) 的模式
            if ")," in line and i > 0:
                # 检查是否在字典或列表中
                prev_line = lines[i - 1]
                if "{" in prev_line or "[" in prev_line:
                    # 移除多余的逗号
                    line = line.replace("),", ")")
                    lines[i] = line

        content = "\n".join(lines)

        # 3. 修复 @abstractmethodasync 的问题
        content = content.replace("@abstractmethodasync", "@abstractmethod\nasync")

        # 4. 修复 except 后面缺少冒号
        import re

        content = re.sub(r"except\s*\([^)]+\)\s*([^\n:])", r"except (\1):\n    \2", content)
        content = re.sub(r"except\s*([^\n:])", r"except Exception:\n    \1", content)

        # 5. 修复文档字符串
        content = content.replace('"""适配器状态枚举"" ACTIVE', '"""适配器状态枚举"""\n    ACTIVE')
        content = content.replace(
            '"""被适配者接口"" @abstractmethod',
            '"""被适配者接口"""\n    @abstractmethod',
        )
        content = content.replace(
            '"""目标接口"" @abstractmethod', '"""目标接口"""\n    @abstractmethod'
        )

        # 6. 修复缺少冒号的函数定义
        content = re.sub(r"(def\s+\w+\([^)]*\))([^\n:])", r"\1:\2", content)

        # 7. 修复 try/finally 缺少冒号
        content = re.sub(r"(try|finally)([^\n:])", r"\1:\2", content)

        # 8. 修复 return 语句中的字典括号
        content = re.sub(r"return\s*\{([^}]+),\s*\)", r"return {\1}", content)

        # 保存修复后的内容
        if content != original:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")
            return True
        else:
            print(f"ℹ️ 无需修复: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False


# 需要修复的关键文件列表
critical_files = [
    "src/adapters/base.py",
    "src/adapters/__init__.py",
    "src/services/__init__.py",
    "src/domain/models/__init__.py",
    "src/api/events.py",
    "src/api/dependencies.py",
]

print("🔧 开始快速修复关键文件...")
fixed_count = 0

for file_path in critical_files:
    if fix_file(file_path):
        fixed_count += 1

print(f"\n✅ 完成！修复了 {fixed_count} 个文件")
