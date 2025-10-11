#!/usr/bin/env python3
"""
优化异常处理 - 将except Exception替换为更具体的异常
"""

import os
import re


def analyze_exceptions_in_file(file_path):
    """分析文件中的异常处理"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找except Exception模式
    pattern = r"except(\s+Exception(\s+as\s+(\w+))?)"
    matches = list(re.finditer(pattern, content))

    if not matches:
        return []

    results = []
    for match in matches:
        line_num = content[: match.start()].count("\n") + 1
        except_text = match.group(0)
        results.append({"line": line_num, "text": except_text, "full_match": match})

    return results


def suggest_specific_exception(file_path, line_num, context):
    """根据上下文建议具体的异常类型"""
    # 简单的异常类型映射
    suggestions = {
        "import": "ImportError",
        "open(": "FileNotFoundError, OSError",
        "json.": "JSONDecodeError",
        "dict": "KeyError, ValueError",
        "list": "IndexError, ValueError",
        "int(": "ValueError, TypeError",
        "float(": "ValueError, TypeError",
        "connect": "ConnectionError",
        "request": "RequestException",
        "sql": "SQLAlchemyError",
        "database": "DatabaseError",
        "cache": "CacheError",
        "redis": "RedisError",
        "api": "APIError",
        "http": "HTTPError",
        "url": "URLError",
        "parse": "ParseError",
        "validate": "ValidationError",
        "auth": "AuthenticationError",
        "permission": "PermissionError",
        "timeout": "TimeoutError",
        "network": "NetworkError",
        "async": "AsyncError",
    }

    # 读取上下文
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 获取异常前后的代码
    start = max(0, line_num - 5)
    end = min(len(lines), line_num + 5)
    context_code = "".join(lines[start:end]).lower()

    # 根据上下文建议异常类型
    for keyword, exception in suggestions.items():
        if keyword in context_code:
            return exception

    # 默认建议
    return "ValueError, TypeError, AttributeError"


def fix_exceptions_in_file(file_path, dry_run=True):
    """修复文件中的异常处理"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = analyze_exceptions_in_file(file_path)
    if not matches:
        return 0

    print(f"\n处理文件: {file_path}")
    print(f"  发现 {len(matches)} 个宽泛异常处理")

    fixed_count = 0
    lines = content.split("\n")

    # 从后往前处理，避免行号变化
    for match_info in reversed(matches):
        line_idx = match_info["line"] - 1
        if line_idx < len(lines):
            original_line = lines[line_idx]

            # 获取建议的异常类型
            context_lines = lines[max(0, line_idx - 3) : line_idx + 3]
            context = "\n".join(context_lines)
            suggested = suggest_specific_exception(file_path, line_idx, context)

            # 替换except Exception
            new_line = original_line.replace(
                "except Exception", f"except ({suggested})"
            )

            if dry_run:
                print(f"  行 {line_idx+1}: {original_line.strip()}")
                print(f"  建议: {new_line.strip()}")
            else:
                lines[line_idx] = new_line
                fixed_count += 1
                print(f"  ✅ 修复行 {line_idx+1}")

    if not dry_run and fixed_count > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    return fixed_count


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 优化异常处理 - 第二阶段代码质量改进")
    print("=" * 80)

    # 统计当前状态
    cmd = "grep -r 'except Exception' --include='*.py' src/ | wc -l"
    result = os.popen(cmd).read().strip()
    current_count = int(result) if result else 0

    print("\n📊 当前状态:")
    print(f"   except Exception 数量: {current_count}")

    if current_count == 0:
        print("\n✅ 没有需要优化的异常处理！")
        return

    # 查找需要处理的文件
    cmd = "grep -r 'except Exception' --include='*.py' src/ | cut -d: -f1 | sort | uniq"
    result = os.popen(cmd).read()
    files = result.strip().split("\n") if result.strip() else []

    print(f"\n📋 需要处理的文件数: {len(files)}")

    # 处理前10个文件作为示例
    print("\n🔍 分析前10个文件的异常处理:")
    print("-" * 60)

    dry_run = True  # 先只分析，不修改

    for i, file_path in enumerate(files[:10]):
        fix_exceptions_in_file(file_path, dry_run=dry_run)

    print("\n" + "-" * 60)
    print("\n💡 建议:")
    print("1. 根据上下文选择合适的异常类型")
    print("2. 避免捕获过于宽泛的Exception")
    print("3. 使用多个except子句处理不同类型的异常")
    print("4. 考虑使用finally块进行清理")
    print("\n运行 'python scripts/optimize_exceptions.py --fix' 来实际修改文件")


if __name__ == "__main__":
    import sys

    if "--fix" in sys.argv:
        # 实际修复模式
        dry_run = False
        print("⚠️ 警告: 将要修改文件！")
        # 这里可以添加实际的修复逻辑
    else:
        # 分析模式
        main()
