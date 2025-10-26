#!/usr/bin/env python3
"""修复config.py文件的语法错误"""

import re


def fix_config_py():
    file_path = "src/database/config.py"

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 修复函数定义
    content = re.sub(
        r"def __init__\(self,\) ->  :\s*\n\s*self,",
        "def __init__(\n        self,",
        content,
    )

    # 修复参数列表末尾
    content = re.sub(
        r"echo_pool: bool = False\s+self\.database",
        "echo_pool: bool = False,\n    ):\n        self.database",
        content,
    )

    # 修复password字段
    content = re.sub(
        r"self\.pass\n:\n:\npassword = password or",
        "self.password = password or",
        content,
    )

    # 修复方法内的password引用
    content = re.sub(r"pass:\n:\n:\nword", "password", content)

    # 修复if语句
    content = re.sub(r"if:self\.", "if self.", content)
    content = re.sub(r'else:"', 'else ""', content)

    # 修复return语句
    content = re.sub(r"return  \(\s*\n", "return (\n            ", content)
    content = re.sub(r"\s*\)\s*\n", ")", content)

    # 修复函数调用参数
    content = re.sub(
        r"DatabaseConfig\(\)\s*\n\s*database=",
        "DatabaseConfig(\n        database=",
        content,
    )

    # 修复password参数
    content = re.sub(r"pass:\n:\n:\nword=os\.getenv", "password=os.getenv", content)

    # 修复参数列表的括号匹配
    content = re.sub(
        r'port=int\(os\.getenv\([^)]+\), "0"\) or None,\s*pool_size=',
        'port=int(os.getenv(f"{prefix}DATABASE_PORT", "0")) or None,\n        pool_size=',
        content,
    )

    # 修复其他参数
    content = re.sub(
        r'pool_size=int\(os\.getenv\([^)]+\), "5"\),\s*max_overflow=',
        'pool_size=int(os.getenv(f"{prefix}DB_POOL_SIZE", "5")),\n        max_overflow=',
        content,
    )

    content = re.sub(
        r'max_overflow=int\(os\.getenv\([^)]+\), "10"\),\s*echo=',
        'max_overflow=int(os.getenv(f"{prefix}DB_MAX_OVERFLOW", "10")),\n        echo=',
        content,
    )

    # 修复if env
    content = re.sub(r"if:env is None:", "if env is None:", content)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 修复了 {file_path}")
    else:
        print(f"⚪ 文件 {file_path} 无需修复")


if __name__ == "__main__":
    fix_config_py()
