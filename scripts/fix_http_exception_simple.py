#!/usr/bin/env python3
"""
简单HTTPException语法修复脚本
Simple HTTPException Syntax Fix Script

使用sed命令和简单模式匹配修复HTTPException语法错误。
"""

import os
import subprocess


def run_sed_command(pattern, file_path):
    """运行sed命令"""
    try:
        cmd = ['sed', '-i', pattern, file_path]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def fix_http_exception_file(file_path):
    """修复单个HTTPException文件"""

    if not os.path.exists(file_path):
        return False

    changes_made = False

    # 修复模式1: 删除空的HTTPException括号行
    patterns_to_fix = [
        # 删除空行后的单独括号行
        (r'/^\s*$/N; /^\s*\n\s*)$/d', "删除空行后的单独括号"),

        # 删除文件末尾的多余异常链
        (r's/\s*\)\s*from\s*e\s*#.*TODO.*exception.*chaining.*$//g', "删除末尾异常链"),

        # 合并分离的HTTPException参数
        (r'/raise HTTPException(/,/^)/ { /^)$/d; }', "删除单独的右括号行"),

        # 清理多余的空行
        (r'/^$/N;/^\n$/d', "删除连续空行"),
    ]

    for pattern, _description in patterns_to_fix:
        try:
            # 备份原文件
            backup_file = file_path + '.backup'
            if not os.path.exists(backup_file):
                os.system(f'cp "{file_path}" "{backup_file}"')

            # 运行sed命令
            if run_sed_command(pattern, file_path):
                changes_made = True
        except Exception:
            pass

    return changes_made

def manual_fix_file(file_path):
    """手动修复特定文件的HTTPException问题"""

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 手动修复特定模式
        lines = content.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检查是否是HTTPException开始
            if 'raise HTTPException(' in line:
                # 收集后续行直到找到正确的结构
                exception_lines = [line]
                i += 1

                # 跳过空行和单独的括号行
                while i < len(lines):
                    current_line = lines[i].strip()
                    if current_line == ')' and (i == 0 or not lines[i-1].strip().startswith('status_code')):
                        # 跳过单独的右括号行
                        i += 1
                        continue
                    elif current_line.startswith('status_code') or current_line.startswith('detail') or current_line.startswith('content'):
                        # 这是参数行，添加到异常
                        exception_lines.append(lines[i])
                        i += 1
                    elif current_line == ')' and (i > 0 and ('status_code' in lines[i-1] or 'detail' in lines[i-1])):
                        # 正确的结束括号
                        exception_lines.append(lines[i])
                        i += 1
                        break
                    else:
                        break

                # 重新构造HTTPException
                if len(exception_lines) > 1:
                    # 重新格式化异常
                    fixed_exception = "raise HTTPException(\n"
                    for param_line in exception_lines[1:]:
                        if param_line.strip() != ')':
                            fixed_exception += f"    {param_line}\n"
                    fixed_exception += ")"
                    fixed_lines.append(fixed_exception)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
                i += 1

        # 写回修复后的内容
        fixed_content = '\n'.join(fixed_lines)
        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        else:
            return False

    except Exception:
        return False

def main():
    """主函数"""

    # Issue #352中指定的10个API文件
    api_files = [
        "src/api/betting_api.py",
        "src/api/features.py",
        "src/api/features_simple.py",
        "src/api/middleware.py",
        "src/api/performance_management.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py",
        "src/api/realtime_streaming.py",
        "src/api/tenant_management.py",
        "src/api/routes/user_management.py"
    ]


    fixed_count = 0
    manual_fixed_count = 0

    for file_path in api_files:
        if os.path.exists(file_path):

            # 首先尝试sed修复
            if fix_http_exception_file(file_path):
                fixed_count += 1

            # 然后尝试手动修复
            if manual_fix_file(file_path):
                manual_fixed_count += 1

        else:
            pass




if __name__ == "__main__":
    main()
