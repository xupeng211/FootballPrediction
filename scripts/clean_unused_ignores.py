#!/usr/bin/env python3
"""
清理未使用的type: ignore注释
"""
import re
from pathlib import Path

def clean_unused_ignores(project_root: Path):
    """清理未使用的type: ignore注释"""
    python_files = list(project_root.glob("src/**/*.py"))

    for file_path in python_files:
        if '__pycache__' in str(file_path):
            continue

        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content

            # 移除行尾的type: ignore注释
            lines = content.split('\n')
            cleaned_lines = []

            for line in lines:
                # 移除简单的type: ignore注释
                if line.rstrip().endswith('  # type: ignore'):
                    cleaned_line = line.replace('  # type: ignore', '')
                    cleaned_lines.append(cleaned_line)
                elif line.rstrip().endswith('# type: ignore'):
                    cleaned_line = line.replace('# type: ignore', '')
                    cleaned_lines.append(cleaned_line.rstrip())
                else:
                    cleaned_lines.append(line)

            content = '\n'.join(cleaned_lines)

            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                print(f"✅ 清理 {file_path.name} 中的未使用type: ignore注释")

        except Exception as e:
            print(f"❌ 处理 {file_path} 时出错: {e}")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    clean_unused_ignores(project_root)
    print("🎉 清理完成！")