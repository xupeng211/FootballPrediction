#!/usr/bin/env python3
"""
HTTPException语法修复工具
专门修复Issue #352中描述的HTTPException结构问题
"""

import re
from pathlib import Path

def fix_http_exception_syntax(content: str) -> str:
    """修复HTTPException语法错误"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 检测HTTPException结束后的多余异常链片段
        if (line.strip().startswith(') from e') and
            i > 0 and
            'raise HTTPException' in lines[i-1:i+1]):
            # 这是多余的片段，跳过
            print(f"  🔧 修复多余异常链: {line.strip()}")
            i += 1
            continue

        # 检测分离的HTTPException参数
        if (re.match(r'^\s+\)\s*$', line) and
            i > 0 and
            'raise HTTPException(' in '\n'.join(lines[max(0, i-5):i])):
            # 找到可能的分离参数
            print(f"  🔧 检测到HTTPException分离结构在第{i+1}行")

            # 向前查找raise语句
            raise_line_idx = -1
            for j in range(i-1, max(-1, i-10), -1):
                if 'raise HTTPException(' in lines[j]:
                    raise_line_idx = j
                    break

            if raise_line_idx >= 0:
                # 收集分离的参数
                param_lines = []
                k = i + 1
                while k < len(lines) and re.match(r'^\s+[a-zA-Z_].*=', lines[k]):
                    param_lines.append(lines[k].strip())
                    k += 1

                if param_lines:
                    # 重新构建HTTPException
                    params_str = ',\n        '.join(param_lines)
                    fixed_lines[raise_line_idx] = (
                        fixed_lines[raise_line_idx].rstrip() +
                        f'\n        {params_str}\n    )'
                    )

                    # 跳过原始分离的参数
                    print(f"  🔧 重新构建HTTPException参数: {len(param_lines)}个参数")
                    i = k
                    continue

        fixed_lines.append(line)
        i += 1

    return '\n'.join(fixed_lines)

def fix_exception_chaining(content: str) -> str:
    """修复异常链问题，添加from e"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        fixed_lines.append(line)

        # 检测需要添加异常链的地方
        if (line.strip().startswith('raise HTTPException(') and
            'from e' not in line):
            # 查找对应的except块
            # 这是一个简化版本，实际需要更复杂的上下文分析
            pass

    return '\n'.join(fixed_lines)

def main():
    """主修复函数"""
    print("🔧 开始修复HTTPException语法错误...")

    # 需要修复的文件列表
    files_to_fix = [
        "src/api/betting_api.py",
        "src/api/features.py",
        "src/api/features_simple.py",
        "src/api/middleware.py",
        "src/api/performance_management.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py",
        "src/api/realtime_streaming.py",
        "src/api/tenant_management.py"
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            print(f"  ⚠️  文件不存在: {file_path}")
            continue

        print(f"\n📝 处理文件: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 应用修复
            fixed_content = fix_http_exception_syntax(original_content)

            # 检查是否有变化
            if fixed_content != original_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"  ✅ 已修复: {file_path}")
                fixed_count += 1
            else:
                print(f"  ℹ️  无需修复: {file_path}")

        except Exception as e:
            print(f"  ❌ 修复失败 {file_path}: {e}")

    print(f"\n🎉 修复完成! 共修复 {fixed_count} 个文件")

    # 验证修复结果
    print("\n🔍 验证修复结果...")
    import subprocess
    import sys

    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists():
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', str(path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"  ✅ 语法验证通过: {file_path}")
                else:
                    print(f"  ❌ 语法验证失败: {file_path}")
                    print(f"     错误: {result.stderr}")
            except Exception as e:
                print(f"  ⚠️  验证异常 {file_path}: {e}")

if __name__ == "__main__":
    main()