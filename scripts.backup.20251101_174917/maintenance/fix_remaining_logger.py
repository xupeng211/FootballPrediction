#!/usr/bin/env python3
"""
修复剩余的 logger 未定义错误
"""

import re
from pathlib import Path


def fix_logger_in_class(file_path: Path, class_name: str) -> bool:
    """在特定类的 __init__ 方法中添加 logger"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 查找类的 __init__ 方法
    class_pattern = (
        rf"(class {class_name}[^:]*:.*?)(def __init__\(self[^)]*\):\s*\n(.*?)(?=def|class|$))"
    )
    match = re.search(class_pattern, content, re.DOTALL)

    if match:
        # 检查是否已经有 logger
        if "self.logger = logging.getLogger" in match.group(3):
            return False

        # 在 __init__ 方法中添加 logger
        init_content = match.group(3)

        # 找到合适的插入位置（在其他属性定义之后）
        lines = init_content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith("#"):
                insert_idx = i + 1

        # 插入 logger 定义
        indent = "        "  # 8 spaces
        lines.insert(insert_idx, f"{indent}self.logger = logging.getLogger(__name__)")

        # 重新构建内容
        new_init = "\n".join(lines)
        content = content.replace(match.group(0), match.group(1) + match.group(2) + "\n" + new_init)

        # 确保有 logging 导入
        if "import logging" not in content:
            lines = content.split("\n")
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_idx = i + 1
                elif line.strip() == "" and import_idx > 0:
                    break
            lines.insert(import_idx, "import logging")
            content = "\n".join(lines)

        # 写回文件
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    return False


def main():
    """主函数"""
    # 需要修复的文件和类名
    fixes = [
        ("src/domain/strategies/ml_model.py", "MLModelStrategy"),
        ("src/features/feature_store.py", None),  # 模块级别的 logger
    ]

    print("🔧 修复剩余的 logger 错误\n")

    fixed_count = 0
    for file_path, class_name in fixes:
        path = Path(file_path)
        if path.exists():
            print(f"📝 修复文件: {file_path}")
            if class_name:
                if fix_logger_in_class(path, class_name):
                    print(f"   ✅ 已修复 {class_name} 类")
                    fixed_count += 1
                else:
                    print("   ⚪ 无需修复")
            else:
                # 模块级别的 logger
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                if "logger." in content and "logger = logging.getLogger" not in content:
                    # 添加模块级别的 logger
                    lines = content.split("\n")
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if (
                            line.startswith("def ")
                            or line.startswith("async def ")
                            or line.startswith("class ")
                        ):
                            insert_idx = i
                            break

                    if insert_idx > 0:
                        lines.insert(insert_idx, "\nlogger = logging.getLogger(__name__)\n")
                        content = "\n".join(lines)

                        # 确保有 logging 导入
                        if "import logging" not in content:
                            import_idx = 0
                            for i, line in enumerate(lines):
                                if line.startswith("import ") or line.startswith("from "):
                                    import_idx = i + 1
                                elif line.strip() == "" and import_idx > 0:
                                    break
                            lines.insert(import_idx, "import logging")
                            content = "\n".join(lines)

                        with open(path, "w", encoding="utf-8") as f:
                            f.write(content)

                        print("   ✅ 已修复模块级 logger")
                        fixed_count += 1
                    else:
                        print("   ⚪ 无需修复")
                else:
                    print("   ⚪ 无需修复")
        else:
            print(f"   ❌ 文件不存在: {file_path}")

    print(f"\n✅ 完成！共修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
