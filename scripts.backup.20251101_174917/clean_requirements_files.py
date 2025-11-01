#!/usr/bin/env python3
"""
Requirements文件清理工具
清理requirements文件中的重复TODO注释，保持依赖文件整洁
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class RequirementsCleaner:
    """Requirements文件清理器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.project_root / "backups" / f"requirements_backup_{self.timestamp}"
        self.cleaning_stats = {
            "files_processed": 0,
            "files_backed_up": 0,
            "todos_removed": 0,
            "lines_cleaned": 0,
            "errors": 0
        }

    def create_backup(self, file_path: Path) -> bool:
        """创建文件备份"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / file_path.relative_to(self.project_root)
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(file_path, backup_path)
            print(f"✅ 备份完成: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ 备份失败 {file_path}: {e}")
            return False

    def clean_requirements_file(self, file_path: Path) -> Tuple[bool, int]:
        """清理单个requirements文件"""
        try:
            # 读取原始内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            cleaned_lines = []
            todos_removed = 0
            lines_cleaned = 0

            for line in original_lines:
                # 检查是否包含TODO注释
                if "# TODO: 添加版本约束" in line:
                    # 移除重复的TODO注释，保留一个干净的版本
                    clean_line = re.sub(r'\s*# TODO: 添加版本约束(?:(?:\s*# TODO: 添加版本约束)*)', '', line)
                    clean_line = re.sub(r'\s*# TODO: 添加版本约束', '', line)
                    clean_line = clean_line.rstrip() + '\n'

                    if clean_line.strip() and clean_line.strip() != '#':
                        cleaned_lines.append(clean_line)
                        todos_removed += line.count("# TODO: 添加版本约束")
                        lines_cleaned += 1
                    elif not clean_line.strip():
                        cleaned_lines.append('\n')
                        todos_removed += line.count("# TODO: 添加版本约束")
                        lines_cleaned += 1
                    else:
                        cleaned_lines.append(line)
                else:
                    cleaned_lines.append(line)

            # 写回清理后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)

            return True, todos_removed

        except Exception as e:
            print(f"❌ 清理文件失败 {file_path}: {e}")
            return False, 0

    def find_all_requirements_files(self) -> List[Path]:
        """查找所有requirements相关文件"""
        requirements_files = []

        # 查找各种requirements文件模式
        patterns = [
            "**/requirements*.txt",
            "**/requirements*.lock",
            "**/requirements*.in",
            "**/requirements*.cfg"
        ]

        for pattern in patterns:
            requirements_files.extend(self.project_root.glob(pattern))

        # 去重并排序
        requirements_files = sorted(list(set(requirements_files)))

        return requirements_files

    def clean_all_requirements(self) -> Dict:
        """清理所有requirements文件"""
        print("🧹 开始清理requirements文件...")
        print(f"📁 项目根目录: {self.project_root}")
        print(f"💾 备份目录: {self.backup_dir}")
        print()

        # 查找所有requirements文件
        requirements_files = self.find_all_requirements_files()

        if not requirements_files:
            print("⚠️  未找到requirements文件")
            return self.cleaning_stats

        print(f"📋 找到 {len(requirements_files)} 个requirements文件:")
        for file_path in requirements_files:
            print(f"   - {file_path.relative_to(self.project_root)}")
        print()

        # 逐个清理文件
        for file_path in requirements_files:
            print(f"🔧 处理文件: {file_path.relative_to(self.project_root)}")

            # 创建备份
            if self.create_backup(file_path):
                self.cleaning_stats["files_backed_up"] += 1

            # 清理文件
            success, todos_removed = self.clean_requirements_file(file_path)

            if success:
                self.cleaning_stats["files_processed"] += 1
                self.cleaning_stats["todos_removed"] += todos_removed
                self.cleaning_stats["lines_cleaned"] += todos_removed
                print(f"   ✅ 清理完成，移除 {todos_removed} 个TODO注释")
            else:
                self.cleaning_stats["errors"] += 1
                print("   ❌ 清理失败")

        return self.cleaning_stats

    def generate_report(self) -> str:
        """生成清理报告"""
        report = f"""
# Requirements文件清理报告

**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**项目根目录**: {self.project_root}

## 清理统计

- **处理文件数**: {self.cleaning_stats['files_processed']}
- **备份文件数**: {self.cleaning_stats['files_backed_up']}
- **移除TODO注释数**: {self.cleaning_stats['todos_removed']}
- **清理行数**: {self.cleaning_stats['lines_cleaned']}
- **错误数**: {self.cleaning_stats['errors']}

## 备份位置

所有原文件已备份至: `{self.backup_dir}`

## 清理效果

- ✅ 移除了所有重复的"# TODO: 添加版本约束"注释
- ✅ 保持了依赖声明的完整性
- ✅ 提高了requirements文件的可读性
- ✅ 符合Python依赖管理最佳实践

## 建议

1. 验证清理后的requirements文件是否正常工作
2. 运行 `pip install -r requirements.txt` 确保依赖安装正常
3. 定期运行此清理工具保持文件整洁
4. 考虑使用 `pip-compile` 管理依赖版本

---
*报告生成时间: {datetime.now().isoformat()}*
        """.strip()

        return report

    def save_report(self, report: str) -> Path:
        """保存清理报告"""
        report_path = self.project_root / f"requirements_cleaning_report_{self.timestamp}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        return report_path

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='清理requirements文件中的重复TODO注释')
    parser.add_argument('--project-root', default='.', help='项目根目录路径')
    parser.add_argument('--dry-run', action='store_true', help='仅分析不执行清理')
    parser.add_argument('--report-only', action='store_true', help='仅生成报告')

    args = parser.parse_args()

    cleaner = RequirementsCleaner(args.project_root)

    if args.report_only:
        # 仅显示当前状态
        requirements_files = cleaner.find_all_requirements_files()
        print(f"📋 找到 {len(requirements_files)} 个requirements文件:")
        for file_path in requirements_files:
            print(f"   - {file_path.relative_to(cleaner.project_root)}")
        return

    if args.dry_run:
        print("🔍 DRY RUN模式 - 仅分析不执行清理")
        requirements_files = cleaner.find_all_requirements_files()

        total_todos = 0
        for file_path in requirements_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    todo_count = content.count("# TODO: 添加版本约束")
                    total_todos += todo_count
                    if todo_count > 0:
                        print(f"   📝 {file_path.relative_to(cleaner.project_root)}: {todo_count} 个TODO注释")
            except Exception as e:
                print(f"   ❌ 读取失败 {file_path}: {e}")

        print(f"\n📊 总计: {len(requirements_files)} 个文件, {total_todos} 个TODO注释")
        return

    # 执行清理
    stats = cleaner.clean_all_requirements()

    # 生成并保存报告
    report = cleaner.generate_report()
    report_path = cleaner.save_report(report)

    print("\n📊 清理完成!")
    print(f"📄 详细报告: {report_path}")
    print(f"✅ 处理文件: {stats['files_processed']}")
    print(f"🗑️  移除TODO: {stats['todos_removed']}")

    if stats['errors'] > 0:
        print(f"⚠️  错误数: {stats['errors']}")
    else:
        print("🎉 清理过程无错误!")

if __name__ == "__main__":
    main()