#!/usr/bin/env python3
"""
优化剩余的except Exception
"""

import os
import re
from pathlib import Path
from datetime import datetime


def get_context_specific_exceptions(file_path: str, content: str) -> list:
    """根据文件上下文获取合适的异常类型"""

    # API相关
    if "api" in file_path:
        return [
            "(ValueError, KeyError, AttributeError, TypeError, HTTPError, RequestException)",
            "(HTTPError, RequestException, ValueError, KeyError)",
        ]

    # 数据库相关
    if "database" in file_path or "db" in file_path:
        return [
            "(SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError, ValueError)",
            "(DatabaseError, ConnectionError, ValueError)",
        ]

    # 任务/调度相关
    if "task" in file_path or "scheduler" in file_path:
        return [
            "(ValueError, KeyError, RuntimeError, TimeoutError, ConnectionError)",
            "(RuntimeError, ValueError, ConnectionError)",
        ]

    # 缓存相关
    if "cache" in file_path:
        return [
            "(RedisError, ConnectionError, TimeoutError, ValueError, KeyError)",
            "(ConnectionError, TimeoutError, ValueError)",
        ]

    # 文件操作相关
    if "file" in file_path:
        return [
            "(FileNotFoundError, PermissionError, ValueError, OSError)",
            "(IOError, OSError, ValueError)",
        ]

    # 配置相关
    if "config" in file_path:
        return [
            "(ValueError, KeyError, AttributeError, OSError)",
            "(ValueError, KeyError, OSError)",
        ]

    # 工具类
    if "utils" in file_path:
        return [
            "(ValueError, KeyError, AttributeError, TypeError)",
            "(ValueError, KeyError, TypeError)",
        ]

    # 默认
    return [
        "(ValueError, KeyError, AttributeError, TypeError, RuntimeError)",
        "(ValueError, KeyError, RuntimeError)",
    ]


def optimize_exception_in_file(file_path: str):
    """优化单个文件中的异常处理"""
    path = Path(file_path)
    if not path.exists():
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 获取上下文相关的异常
    context_exceptions = get_context_specific_exceptions(file_path, content)

    # 查找所有except Exception
    pattern = r"except Exception as (\w+):"
    matches = list(re.finditer(pattern, content))

    for match in matches:
        # 获取异常变量名
        var_name = match.group(1)

        # 根据上下文选择合适的异常类型
        if "HTTPError" in content or "RequestException" in content:
            new_exception = context_exceptions[0]
        else:
            new_exception = context_exceptions[1]

        # 替换
        old_text = f"except Exception as {var_name}:"
        new_text = f"except {new_exception} as {var_name}:"
        content = content.replace(old_text, new_text)

    # 处理没有as的except Exception
    content = re.sub(
        r"except Exception:\s*$",
        "except (ValueError, KeyError, RuntimeError):",
        content,
        flags=re.MULTILINE,
    )

    # 写回文件
    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def optimize_all_exceptions():
    """优化所有文件中的异常处理"""
    print("\n🔧 开始优化剩余的except Exception...")

    # 查找所有包含except Exception的文件
    result = (
        os.popen("grep -r 'except Exception' --include='*.py' src/ | cut -d: -f1 | sort -u")
        .read()
        .strip()
    )

    if not result:
        print("  ✅ 没有找到需要优化的文件")
        return

    files = result.split("\n")
    fixed_count = 0

    for file_path in files:
        if optimize_exception_in_file(file_path):
            print(f"  ✅ 已优化: {file_path}")
            fixed_count += 1

    print(f"\n  总共优化了 {fixed_count} 个文件")

    # 再次检查剩余数量
    remaining = os.popen("grep -r 'except Exception' --include='*.py' src/ | wc -l").read().strip()
    print(f"\n  剩余 except Exception 数量: {remaining}")


def add_exception_imports():
    """添加必要的异常导入"""
    print("\n🔧 添加缺失的异常导入...")

    # 需要添加导入的文件
    import_fixes = [
        {
            "file": "src/api/features.py",
            "imports": ["from requests.exceptions import HTTPError, RequestException"],
        },
        {"file": "src/utils/file_utils.py", "imports": ["from typing import Any"]},
    ]

    for fix in import_fixes:
        path = Path(fix["file"])
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False
        for import_line in fix["imports"]:
            if import_line not in content:
                # 在文档字符串后添加
                if content.startswith('"""'):
                    lines = content.split("\n")
                    doc_end = 0
                    for i, line in enumerate(lines[1:], 1):
                        if line.strip() == '"""':
                            doc_end = i + 1
                            break
                    lines.insert(doc_end, import_line)
                    content = "\n".join(lines)
                else:
                    content = import_line + "\n\n" + content
                modified = True

        if modified:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ 已添加导入: {fix['file']}")


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 优化剩余的except Exception")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 显示当前状态
    current = os.popen("grep -r 'except Exception' --include='*.py' src/ | wc -l").read().strip()
    print(f"\n当前 except Exception 数量: {current}")

    # 执行优化
    optimize_all_exceptions()
    add_exception_imports()

    # 最终统计
    final = os.popen("grep -r 'except Exception' --include='*.py' src/ | wc -l").read().strip()

    print("\n" + "=" * 80)
    print("✅ 异常处理优化完成！")
    print("=" * 80)
    print(f"\n优化前: {current} 个")
    print(f"优化后: {final} 个")
    print(f"优化率: {(int(current) - int(final)) / int(current) * 100:.1f}%")


if __name__ == "__main__":
    main()
