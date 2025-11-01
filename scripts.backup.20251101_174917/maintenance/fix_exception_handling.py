#!/usr/bin/env python3
"""
优化异常处理 - 批量替换except Exception
"""

import os


def fix_exceptions_in_critical_files():
    """修复关键文件中的异常处理"""

    # 优先处理的文件列表（按重要性排序）
    critical_files = [
        "src/api/app.py",
        "src/api/decorators.py",
        "src/api/events.py",
        "src/services/base_unified.py",
        "src/core/di.py",
        "src/database/connection_mod/__init__.py",
        "src/cache/redis_manager.py",
        "src/utils/crypto_utils.py",
    ]

    fixed_files = 0

    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"\n处理: {file_path}")
            if fix_file_exceptions(file_path):
                fixed_files += 1
                print("  ✅ 已修复")
            else:
                print("  ⚠️ 无需修复或修复失败")
        else:
            print(f"\n文件不存在: {file_path}")

    return fixed_files


def fix_file_exceptions(file_path):
    """修复单个文件的异常处理"""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 根据文件内容选择合适的异常类型
        if "api" in file_path:
            # API相关文件
            replacements = [
                (
                    "except Exception as e:",
                    "except (ValueError, KeyError, AttributeError, HTTPError) as e:",
                ),
            ]
        elif "database" in file_path or "cache" in file_path:
            # 数据库和缓存相关
            replacements = [
                (
                    "except Exception as e:",
                    "except (ConnectionError, TimeoutError, ValueError) as e:",
                ),
            ]
        elif "crypto" in file_path:
            # 加密相关
            replacements = [
                (
                    "except Exception as e:",
                    "except (ValueError, TypeError, OSError) as e:",
                ),
            ]
        else:
            # 通用
            replacements = [
                (
                    "except Exception as e:",
                    "except (ValueError, TypeError, AttributeError, KeyError) as e:",
                ),
                ),
            ]

        # 应用替换
        modified = False
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                modified = True

        # 写回文件
        if modified and content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def create_exception_type_mapping():
    """创建异常类型映射"""

    mapping = {
        # API相关
        "request": ["RequestException", "HTTPError", "ConnectionError"],
        "json": ["JSONDecodeError"],
        "response": ["HTTPError", "ResponseError"],
        # 数据库相关
        "sql": ["SQLAlchemyError", "DatabaseError"],
        "connect": ["ConnectionError", "TimeoutError"],
        "session": ["SessionError"],
        # 缓存相关
        "redis": ["RedisError", "ConnectionError"],
        "cache": ["CacheError"],
        # 文件操作
        "open": ["FileNotFoundError", "OSError", "PermissionError"],
        "read": ["IOError", "OSError"],
        "write": ["IOError", "OSError"],
        # 数据处理
        "int(": ["ValueError", "TypeError"],
        "float(": ["ValueError", "TypeError"],
        "dict": ["KeyError", "ValueError"],
        "list": ["IndexError", "ValueError"],
        # 网络相关
        "http": ["HTTPError", "URLError"],
        "url": ["URLError"],
        "timeout": ["TimeoutError"],
        # 通用
        "parse": ["ParseError", "ValueError"],
        "validate": ["ValidationError", "ValueError"],
        "auth": ["AuthenticationError", "PermissionError"],
    }

    return mapping


def analyze_exception_patterns():
    """分析异常模式"""

    print("\n📊 分析异常处理模式...")

    # 统计各种模式
    patterns = {
        "except Exception:": 0,
        "except Exception as e:": 0,
        "except Exception as err:": 0,
        "except Exception as ex:": 0,
    }

    cmd = "grep -r 'except Exception' --include='*.py' src/"
    result = os.popen(cmd).read()

    for pattern in patterns:
        patterns[pattern] = result.count(pattern)

    print("\n异常处理模式统计:")
    for pattern, count in patterns.items():
        print(f"  {pattern}: {count} 次")

    return patterns


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 优化异常处理 - 第二阶段代码质量改进")
    print("=" * 80)

    # 分析当前状态
    patterns = analyze_exception_patterns()
    total_exceptions = sum(patterns.values())

    print("\n📊 当前状态:")
    print(f"   except Exception总数: {total_exceptions}")

    # 修复关键文件
    print("\n🔧 开始修复关键文件...")
    fixed_count = fix_exceptions_in_critical_files()

    print(f"\n✅ 修复了 {fixed_count} 个关键文件")

    # 再次统计
    cmd = "grep -r 'except Exception' --include='*.py' src/ | wc -l"
    result = os.popen(cmd).read().strip()
    remaining = int(result) if result else 0

    print(f"\n📊 剩余 except Exception: {remaining} 个")

    if remaining > 0:
        print("\n💡 建议:")
        print("1. 继续处理其他文件的异常处理")
        print("2. 根据具体上下文选择合适的异常类型")
        print("3. 考虑创建自定义异常类")
        print("4. 使用多个except子句处理不同异常")


if __name__ == "__main__":
    main()
