#!/usr/bin/env python3
"""
批量修复所有HTTPException语法错误的脚本
"""

import re
import os
import subprocess
from pathlib import Path

def check_syntax(file_path):
    """检查文件语法是否正确"""
    try:
        result = subprocess.run(
            ['python3', '-m', 'py_compile', file_path],
            capture_output=True,
            text=True,
            cwd='/home/user/projects/FootballPrediction'
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)

def fix_httpexception_syntax(content):
    """修复HTTPException语法问题"""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 修复模式1: raise HTTPException(... from e
        if 'raise HTTPException(... from e' in line:
            # 查找完整的HTTPException语句
            result.append(line.replace('raise HTTPException(... from e', 'raise HTTPException('))
            i += 1

            # 添加参数，直到找到结束的)
            paren_count = 0
            while i < len(lines):
                current_line = lines[i]
                result.append(current_line)
                paren_count += current_line.count('(') - current_line.count(')')

                if paren_count >= 0 and ')' in current_line:
                    # 找到了结束的)
                    if 'from e' not in current_line and not current_line.strip().endswith(') from e'):
                        # 检查是否在except块中
                        # 简单检查：往上查找except语句
                        found_except = False
                        for j in range(max(0, i-10), i):
                            if re.match(r'\s*except\s+.+\s+as\s+\w+:', lines[j]):
                                found_except = True
                                break

                        if found_except:
                            # 在)前添加from e
                            result[-1] = current_line.replace(')', ') from e')
                    break
                i += 1
            i += 1
            continue

        # 修复模式2: 重复的) from e
        if re.match(r'^\s*\)\s*from\s+e\s*#.*$', line):
            # 检查前一行是否以)结尾
            if result and result[-1].strip().endswith(')'):
                # 跳过这一行重复的)
                i += 1
                continue

        # 修复模式3: HTTPException后缺少参数但有from e
        if 'HTTPException(' in line and line.strip().endswith('('):
            # 这行没有结束，需要继续处理
            result.append(line)
            i += 1

            # 继续收集参数
            while i < len(lines):
                current_line = lines[i]
                result.append(current_line)

                if ')' in current_line:
                    # 找到结束，检查是否需要添加from e
                    if 'from e' not in current_line:
                        # 简单检查是否在except块中
                        for j in range(max(0, i-10), i):
                            if re.match(r'\s*except\s+.+\s+as\s+\w+:', lines[j]):
                                result[-1] = current_line.replace(')', ') from e')
                                break
                    break
                i += 1
            i += 1
            continue

        result.append(line)
        i += 1

    return '\n'.join(result)

def main():
    """主函数"""
    print("🔧 批量修复HTTPException语法错误...")
    print("=" * 50)

    # 有语法问题的文件列表（基于coverage.py警告）
    problem_files = [
        "src/api/auth/router.py",
        "src/api/auth_dependencies.py",
        "src/api/batch_analytics.py",
        "src/api/betting_api.py",
        "src/api/cqrs.py",
        "src/api/data_integration.py",
        "src/api/events.py",
        "src/api/features.py",
        "src/api/features_simple.py",
        "src/api/health/__init__.py",
        "src/api/middleware.py",
        "src/api/monitoring.py",
        "src/api/observers.py",
        "src/api/performance_management.py",
        "src/api/predictions/health.py",
        "src/api/predictions/health_simple.py",
        "src/api/predictions/router.py",
        "src/api/simple_auth.py",
        "src/api/tenant_management.py",
        "src/app_enhanced.py",
        "src/middleware/tenant_middleware.py",
        "src/performance/api.py",
        "src/realtime/match_api.py",
        "src/security/middleware.py"
    ]

    fixed_count = 0
    already_good_count = 0
    error_count = 0

    for file_path in problem_files:
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        print(f"\n🔍 检查文件: {file_path}")

        # 先检查当前语法状态
        is_valid, error_msg = check_syntax(str(full_path))
        if is_valid:
            print(f"✅ 语法正确，无需修复")
            already_good_count += 1
            continue

        print(f"❌ 语法错误: {error_msg[:100]}...")

        try:
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复语法
            fixed_content = fix_httpexception_syntax(content)

            # 如果内容有变化，写回文件
            if fixed_content != content:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                # 验证修复效果
                is_valid_after, error_msg_after = check_syntax(str(full_path))
                if is_valid_after:
                    print(f"✅ 修复成功")
                    fixed_count += 1
                else:
                    print(f"❌ 修复失败: {error_msg_after[:100]}...")
                    error_count += 1
            else:
                print(f"⚪ 内容无变化")
                error_count += 1

        except Exception as e:
            print(f"❌ 处理文件失败 {file_path}: {e}")
            error_count += 1

    print("\n" + "=" * 50)
    print("🎉 HTTPException语法修复完成!")
    print(f"📊 修复统计:")
    print(f"   修复成功: {fixed_count} 个文件")
    print(f"   已经正确: {already_good_count} 个文件")
    print(f"   修复失败: {error_count} 个文件")
    print(f"   总文件数: {len(problem_files)} 个文件")

    if error_count > 0:
        print(f"\n⚠️  有 {error_count} 个文件需要手动处理")
    else:
        print(f"\n✅ 所有文件语法修复成功!")

if __name__ == "__main__":
    main()