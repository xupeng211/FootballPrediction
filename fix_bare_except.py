#!/usr/bin/env python3
"""
修复 bare except 错误（E722）
将 except: 改为 except Exception:
"""

import os
import re
import subprocess
from pathlib import Path


def fix_bare_excepts(filepath):
    """修复单个文件的 bare except"""
    print(f"处理: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复 bare except
        # 使用正则表达式匹配各种情况
        patterns = [
            # 简单的 except:
            (r"\bexcept:\s*\n", r"except Exception:\n"),
            # except: 后面有注释
            (r"\bexcept:\s*#", r"except Exception: #"),
            # except: 后面有代码
            (r"\bexcept:\s*(\w)", r"except Exception:\n\1"),
            # 带缩进的 except:
            (r"(\s+)except:\s*\n", r"\1except Exception:\n"),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        # 特殊处理：在行尾的 except:
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped == "except:":
                # 保持原有缩进
                indent = line[: len(line) - len(stripped)]
                new_line = f"{indent}except Exception:"
                new_lines.append(new_line)
            elif stripped.endswith("except:"):
                # 例如：try: ... except:
                line = line.replace("except:", "except Exception:")
                new_lines.append(line)
            else:
                new_lines.append(line)

        content = "\n".join(new_lines)

        # 写回文件
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print("  ✅ 已修复")
            return True
        else:
            print("  - 无需修复")
            return False

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def main():
    """主函数"""
    # 获取所有有 E722 错误的文件
    result = subprocess.run(
        ["ruff", "check", "--select=E722", "--output-format=concise"],
        capture_output=True,
        text=True,
    )

    files = set()
    for line in result.stdout.split("\n"):
        if line:
            filepath = line.split(":")[0]
            if os.path.exists(filepath):
                files.add(filepath)

    print(f"找到 {len(files)} 个需要修复的文件")
    print("=" * 60)

    fixed_count = 0
    for filepath in sorted(files):
        if fix_bare_excepts(filepath):
            fixed_count += 1

    print("=" * 60)
    print(f"✅ 修复了 {fixed_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果...")
    result = subprocess.run(
        ["ruff", "check", "--select=E722"], capture_output=True, text=True
    )

    remaining = len(result.stdout.split("\n")) if result.stdout.strip() else 0
    print(f"剩余 {remaining} 个 E722 错误")

    if remaining > 0:
        print("\n前 10 个错误:")
        for line in result.stdout.split("\n")[:10]:
            if line:
                print(f"  {line}")


if __name__ == "__main__":
    main()
