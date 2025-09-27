#!/usr/bin/env python3
"""
自动化文档清单生成脚本

该脚本遍历 docs/ 目录及其子目录，收集所有 .md 文件路径，
生成 docs/DOCS_AUTO_INDEX.md 文档清单。

使用方法:
    python scripts/generate_docs_index.py
"""

import os
from pathlib import Path
from typing import List


def collect_markdown_files(docs_dir: Path) -> List[Path]:
    """收集 docs 目录下所有 .md 文件，排除 README.md 和 DOCS_AUTO_INDEX.md"""
    markdown_files = []

    for file_path in docs_dir.rglob("*.md"):
        # 排除 README.md 文件和自己生成的文件
        if file_path.name not in ["README.md", "DOCS_AUTO_INDEX.md"]:
            markdown_files.append(file_path)

    # 按文件路径排序
    return sorted(markdown_files)


def generate_docs_index(docs_dir: Path, output_file: Path) -> None:
    """生成文档清单"""
    markdown_files = collect_markdown_files(docs_dir)

    # 生成文档内容
    content = """# 📑 自动化文档清单

该文件由脚本 `scripts/generate_docs_index.py` 自动生成，列出当前 `docs/` 目录下的所有 Markdown 文档，便于检查是否遗漏在总索引中。

## 文档列表
"""

    # 添加文件链接
    for file_path in markdown_files:
        # 计算相对路径（相对于docs目录）
        relative_path = file_path.relative_to(docs_dir)
        # 生成链接文本
        link_text = f"docs/{relative_path}"
        content += f"- [{link_text}]({relative_path})\n"

    # 添加统计信息
    content += f"\n---\n\n*总计文档数: {len(markdown_files)} 个*\n"
    content += f"*生成时间: {Path(__file__).stat().st_mtime}*\n"

    # 写入文件
    output_file.write_text(content, encoding='utf-8')
    print(f"✅ 已生成文档清单: {output_file}")
    print(f"📊 共找到 {len(markdown_files)} 个 Markdown 文档")


def main():
    """主函数"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / "docs"
    output_file = docs_dir / "DOCS_AUTO_INDEX.md"

    # 检查 docs 目录是否存在
    if not docs_dir.exists():
        print(f"❌ 错误: docs 目录不存在: {docs_dir}")
        return

    # 生成文档清单
    generate_docs_index(docs_dir, output_file)


if __name__ == "__main__":
    main()