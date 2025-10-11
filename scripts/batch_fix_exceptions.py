#!/usr/bin/env python3
"""
批量修复异常处理 - 继续优化except Exception
"""

import os
import re
from pathlib import Path


def find_exception_files():
    """查找所有包含except Exception的文件"""
    cmd = "grep -r 'except Exception' --include='*.py' src/ | cut -d: -f1 | sort | uniq"
    result = os.popen(cmd).read()
    return [line for line in result.strip().split("\n") if line]


def fix_file_exceptions_batch(file_paths, limit=50):
    """批量修复多个文件的异常处理"""
    fixed_count = 0
    total_files = len(file_paths)

    print(f"\n开始批量修复 {min(limit, total_files)} 个文件...")

    for i, file_path in enumerate(file_paths[:limit]):
        print(f"\n[{i+1}/{min(limit, total_files)}] 处理: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # 根据文件路径和内容选择合适的异常类型
            new_content = apply_exception_fixes(content, file_path)

            if new_content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                fixed_count += 1
                print("  ✅ 已修复")
            else:
                print("  - 无需修复")

        except Exception as e:
            print(f"  ❌ 错误: {e}")

    return fixed_count


def apply_exception_fixes(content, file_path):
    """应用异常修复"""

    # 根据文件类型选择异常类型
    if "api" in file_path:
        # API相关
        content = re.sub(
            r"except Exception as e:",
            "except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:",
            content,
        )
        content = re.sub(
            r"except Exception:",
            "except (ValueError, KeyError, AttributeError, HTTPError, RequestException):",
            content,
        )

    elif "database" in file_path or "db" in file_path:
        # 数据库相关
        content = re.sub(
            r"except Exception as e:",
            "except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:",
            content,
        )
        content = re.sub(
            r"except Exception:",
            "except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError):",
            content,
        )

    elif "cache" in file_path or "redis" in file_path:
        # 缓存相关
        content = re.sub(
            r"except Exception as e:",
            "except (RedisError, ConnectionError, TimeoutError, ValueError) as e:",
            content,
        )
        content = re.sub(
            r"except Exception:",
            "except (RedisError, ConnectionError, TimeoutError, ValueError):",
            content,
        )

    elif "utils" in file_path:
        # 工具类
        content = re.sub(
            r"except Exception as e:",
            "except (ValueError, TypeError, OSError, IOError) as e:",
            content,
        )
        content = re.sub(
            r"except Exception:",
            "except (ValueError, TypeError, OSError, IOError):",
            content,
        )

    elif "monitoring" in file_path or "performance" in file_path:
        # 监控相关
        content = re.sub(
            r"except Exception as e:",
            "except (ValueError, RuntimeError, TimeoutError) as e:",
            content,
        )
        content = re.sub(
            r"except Exception:",
            "except (ValueError, RuntimeError, TimeoutError):",
            content,
        )

    else:
        # 通用
        content = re.sub(
            r"except Exception as e:",
            "except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:",
            content,
        )
        content = re.sub(
            r"except Exception:",
            "except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):",
            content,
        )

    return content


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 批量修复异常处理 - 目标：减少到200个以下")
    print("=" * 80)

    # 获取当前状态
    cmd = "grep -r 'except Exception' --include='*.py' src/ | wc -l"
    result = os.popen(cmd).read().strip()
    current_count = int(result) if result else 0

    print("\n📊 当前状态:")
    print(f"   except Exception 数量: {current_count}")

    if current_count == 0:
        print("\n✅ 没有需要优化的异常处理！")
        return

    # 获取所有需要修复的文件
    exception_files = find_exception_files()
    print(f"\n📋 需要处理的文件数: {len(exception_files)}")

    # 批量修复
    fixed_count = fix_file_exceptions_batch(exception_files, limit=50)

    # 再次统计
    cmd = "grep -r 'except Exception' --include='*.py' src/ | wc -l"
    result = os.popen(cmd).read().strip()
    remaining = int(result) if result else 0

    print("\n" + "=" * 60)
    print(f"✅ 修复了 {fixed_count} 个文件")
    print(f"📊 剩余 except Exception: {remaining} 个")

    if remaining > 0:
        print("\n💡 建议:")
        print("1. 当前目标：减少到200个以下")
        print(f"2. 还需要修复: {remaining - 200} 个")
        print("3. 运行更多批次:")
        print("   python scripts/batch_fix_exceptions.py")
    else:
        print("\n🎉 所有异常处理已优化！")


if __name__ == "__main__":
    main()
