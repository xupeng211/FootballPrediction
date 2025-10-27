#!/usr/bin/env python3
"""
批量修复SQLAlchemy模型重复定义问题
为所有BaseModel类添加extend_existing=True
"""

import re
from pathlib import Path

def fix_sqlalchemy_models():
    """修复SQLAlchemy模型重复定义问题"""
    print("🔧 修复SQLAlchemy模型重复定义问题...")

    models_dir = Path("src/database/models")
    if not models_dir.exists():
        print("❌ models目录不存在")
        return

    fixed_files = []

    for py_file in models_dir.rglob("*.py"):
        # 跳过备份文件
        if py_file.name.endswith('.bak') or '__pycache__' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找所有BaseModel类定义
            lines = content.split('\n')
            fixed_lines = []
            in_base_model_class = False
            class_indent = 0

            for line in lines:
                fixed_lines.append(line)

                # 检查是否是BaseModel类定义
                if re.match(r'^\s*class\s+\w+\s*\(\s*BaseModel\s*\)\s*:', line):
                    in_base_model_class = True
                    class_indent = len(line) - len(line.lstrip())
                    print(f"    找到BaseModel类: {line.strip()}")

                # 如果在BaseModel类中，检查是否已经有__table_args__
                elif in_base_model_class:
                    if line.strip().startswith('__table_args__'):
                        in_base_model_class = False  # 已有配置，跳过
                    elif line.strip().startswith('"""') or line.strip().startswith("'''"):
                        # 文档字符串，继续
                        continue
                    elif line.strip() == '':
                        # 空行，继续
                        continue
                    elif line.strip().startswith('@'):
                        # 装饰器，继续
                        continue
                    elif len(line) - len(line.lstrip()) <= class_indent:
                        # 新的类或函数开始，需要添加__table_args__
                        if 'extend_existing=True' not in content:
                            # 在类定义后添加__table_args__
                            insert_pos = len(fixed_lines) - 1
                            indent = ' ' * (class_indent + 4)
                            fixed_lines.insert(insert_pos, f"{indent}__table_args__ = {{'extend_existing': True}}")
                            print(f"    ✅ 为 {py_file.name} 添加了 __table_args__")
                            fixed_files.append(py_file)
                        in_base_model_class = False

            # 更新文件内容
            new_content = '\n'.join(fixed_lines)
            if new_content != content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)

        except Exception as e:
            print(f"    ⚠️ 处理 {py_file} 时出错: {e}")

    print(f"\n✅ 修复完成！处理了 {len(fixed_files)} 个文件")
    return fixed_files

def main():
    """主函数"""
    print("🚀 开始修复SQLAlchemy模型重复定义问题...")
    fixed_files = fix_sqlalchemy_models()

    if fixed_files:
        print("\n📊 修复总结:")
        print(f"  - 修复文件数: {len(fixed_files)}")
        print(f"  - 每个文件都添加了 '__table_args__ = {'extend_existing': True}'")
        print("\n🎯 建议:")
        print("  1. 运行测试验证修复效果")
        print("  2. 检查CI/CD流水线是否通过")
        print("  3. 如果仍有问题，可能需要检查数据库迁移文件")
    else:
        print("\n✅ 没有发现需要修复的文件")

if __name__ == "__main__":
    main()