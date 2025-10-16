#!/usr/bin/env python3
"""
修复 Ruff 错误 - Phase 2: 处理复杂错误
包括 E731 (lambda 赋值)、E714/E721 (类型比较)等
"""

import ast
import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"📝 命令: {' '.join(cmd)}")
    print('='*60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 成功")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ 失败: {e.stderr[:500]}")
        return False, e.stderr

def fix_e731_errors():
    """修复 E731: Do not assign a lambda expression, use a `def`"""
    print("\n🎯 修复 E731: lambda 赋值改为 def")

    files_to_fix = []
    for root, dirs, files in os.walk(["src", "tests"]):
        # 跳过 .venv, __pycache__ 等
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))

    fixed_count = 0

    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            lines = content.split('\n')

            # 解析 AST 来找到 lambda 赋值
            try:
                tree = ast.parse(content)
                lambda_assigns = find_lambda_assignments(tree)
            except:
                lambda_assigns = []

            # 修复每个 lambda 赋值
            for assign_info in sorted(lambda_assigns, key=lambda x: x['line'], reverse=True):
                line_num = assign_info['line'] - 1  # 转换为0基索引
                if line_num < len(lines):
                    line = lines[line_num]

                    # 提取变量名
                    var_match = re.match(r'(\s*)(\w+)\s*=\s*lambda', line)
                    if var_match:
                        indent = var_match.group(1)
                        var_name = var_match.group(2)

                        # 生成函数定义
                        func_name = var_name
                        if not func_name.startswith('_'):
                            func_name = f"_{func_name}"  # 如果不是私有，添加下划线

                        # 创建 def 替换
                        def_line = f"{indent}def {func_name}{assign_info['args']}:"
                        return_line = f"{indent}    return {assign_info['body']}"

                        # 替换原行
                        lines[line_num] = def_line
                        lines.insert(line_num + 1, return_line)

                        # 更新后续使用
                        for i, other_line in enumerate(lines):
                            if i != line_num and i != line_num + 1:
                                # 替换变量使用
                                lines[i] = re.sub(rf'\b{re.escape(var_name)}\b', func_name, lines[i])

                        fixed_count += 1
                        print(f"  修复: {file_path}:{line_num+1} - lambda {var_name} -> def {func_name}")

            # 如果内容有变化，写回文件
            if '\n'.join(lines) != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))

        except Exception as e:
            print(f"⚠️ 修复文件 {file_path} 时出错: {e}")

    print(f"✅ 修复了 {fixed_count} 个 lambda 赋值")

def find_lambda_assignments(tree: ast.AST) -> List[dict]:
    """查找 AST 中的 lambda 赋值"""
    assignments = []

    class LambdaVisitor(ast.NodeVisitor):
        def visit_Assign(self, node):
            if isinstance(node.value, ast.Lambda):
                # 提取参数
                args = []
                for arg in node.value.args.args:
                    args.append(arg.arg)

                # 提取函数体
                body = ast.unparse(node.value.body) if hasattr(ast, 'unparse') else str(node.value.body)

                assignments.append({
                    'line': node.lineno,
                    'args': f"({', '.join(args)})",
                    'body': body
                })

            self.generic_visit(node)

    LambdaVisitor().visit(tree)
    return assignments

def fix_e714_e721_errors():
    """修复 E714/E721: 类型比较错误"""
    print("\n🎯 修复 E714/E721: 类型比较错误")

    patterns = [
        # E714: Test for object identity should be `is not`
        (r'(\w+)\s+is\s+not\s+(\d+)', r'\1 != \2'),
        (r'(\w+)\s+is\s+not\s+"([^"]*)"', r'\1 != "\2"'),
        (r'(\w+)\s+is\s+not\s+\'([^\']*)\'', r"\1 != '\2'"),

        # E721: Use `is` and `is not` for type comparisons
        (r'type\((\w+)\)\s*==\s*(\w+)', r'\1.__class__ is \2'),
        (r'type\((\w+)\)\s*!=\s*(\w+)', r'\1.__class__ is not \2'),
    ]

    files_to_fix = []
    for root, dirs, files in os.walk(["src", "tests"]):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))

    fixed_count = 0
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用修复模式
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1

        except Exception as e:
            print(f"⚠️ 修复文件 {file_path} 时出错: {e}")

    print(f"✅ 修复了 {fixed_count} 个文件的类型比较错误")

def fix_e722_bare_except():
    """修复 E722: 裸露 except"""
    print("\n🎯 修复 E722: 裸露 except -> except Exception")

    files_to_fix = []
    for root, dirs, files in os.walk(["src", "tests"]):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))

    fixed_count = 0
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 修复裸露 except
            # 简单情况：独立一行的 except:
            content = re.sub(r'^(\s*)except:\s*$', r'\1except Exception:', content, flags=re.MULTILINE)

            # 复杂情况：try...except 在同一行
            content = re.sub(r'except:\s*#', 'except Exception:  #', content)

            # 避免已经有的 except Exception 重复
            content = re.sub(r'except Exception:\s*Exception:', 'except Exception:', content)

            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1

        except Exception as e:
            print(f"⚠️ 修复文件 {file_path} 时出错: {e}")

    print(f"✅ 修复了 {fixed_count} 个文件的裸露 except")

def run_final_ruff_fix():
    """运行 ruff 自动修复剩余可修复的错误"""
    print("\n🎯 运行 ruff 自动修复剩余错误")

    cmd = ["ruff", "check", "--fix", "src/", "tests/"]
    success, output = run_command(cmd, "ruff 自动修复")

    if success:
        print("✅ ruff 自动修复完成")
    else:
        print("⚠️ ruff 自动修复遇到问题")

def main():
    """主函数"""
    print("🚀 开始 Phase 2: 修复复杂 Ruff 错误")
    print("="*60)

    # 1. 修复 E731 (lambda 赋值)
    fix_e731_errors()

    # 2. 修复 E714/E721 (类型比较)
    fix_e714_e721_errors()

    # 3. 修复 E722 (裸露 except)
    fix_e722_bare_except()

    # 4. 运行 ruff 自动修复
    run_final_ruff_fix()

    print("\n" + "="*60)
    print("✅ Phase 2 修复完成！")
    print("\n📋 后续步骤：")
    print("1. 运行 'ruff check src/ tests/' 查看剩余错误")
    print("2. 手动修复无法自动处理的错误")
    print("3. 运行 'make lint' 验证所有错误已修复")

if __name__ == "__main__":
    main()
