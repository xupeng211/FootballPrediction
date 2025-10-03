#!/usr/bin/env python3
"""
深度项目清理脚本
清理所有临时文件、缓存、报告和无用数据
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta

class DeepCleaner:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.archive_dir = self.project_root / ".cleanup_archive"
        self.stats = {
            'temp_files': 0,
            'cache_dirs': 0,
            'reports': 0,
            'logs': 0,
            'misc': 0
        }
        self.errors = []
        self.dry_run = False

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = {
            "INFO": "\033[0m",
            "WARN": "\033[0;33m",
            "ERROR": "\033[0;31m",
            "SUCCESS": "\033[0;32m"
        }.get(level, "\033[0m")
        print(f"{color}[{timestamp}] {level}: {message}\033[0m")

    def get_file_size_mb(self, path: Path) -> float:
        """获取文件大小(MB)"""
        if path.is_file():
            return path.stat().st_size / (1024 * 1024)
        elif path.is_dir():
            total = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total += os.path.getsize(filepath)
            return total / (1024 * 1024)
        return 0

    def clean_temp_files(self):
        """清理临时文件"""
        self.log("\n🗑️ 清理临时文件...", "INFO")

        patterns = [
            "**/*.tmp",
            "**/*_temp*",
            "**/*_backup*",
            "**/*_working*",
            "**/*.bak",
            "**/*.swp",
            "**/*.swo",
            "**/TEMP_*",
            "**/CLAUDE_*.md.bak",
            "**/*.orig",
            "**/*.rej"
        ]

        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                # 跳过重要目录
                if ".git" in str(file_path):
                    continue

                try:
                    size = self.get_file_size_mb(file_path)
                    if self.dry_run:
                        self.log(f"  [DRY] 将删除: {file_path.relative_to(self.project_root)} ({size:.2f}MB)")
                    else:
                        if file_path.is_file():
                            file_path.unlink()
                        else:
                            shutil.rmtree(file_path)
                        self.stats['temp_files'] += 1
                        self.log(f"  删除: {file_path.relative_to(self.project_root)} ({size:.2f}MB)")
                except Exception as e:
                    self.errors.append(f"删除失败 {file_path}: {e}")

    def clean_cache_dirs(self):
        """清理缓存目录"""
        self.log("\n🧹 清理缓存目录...", "INFO")

        cache_dirs = [
            self.project_root / ".pytest_cache",
            self.project_root / ".mypy_cache",
            self.project_root / ".ruff_cache",
            self.project_root / ".coverage",
            self.project_root / "htmlcov",
            self.project_root / ".tox",
            self.project_root / ".nox",
            self.project_root / "build",
            self.project_root / "dist",
        ]

        # 查找所有 __pycache__ 目录
        cache_dirs.extend(self.project_root.rglob("__pycache__"))

        for cache_dir in cache_dirs:
            if cache_dir.exists():
                try:
                    size = self.get_file_size_mb(cache_dir)
                    if self.dry_run:
                        self.log(f"  [DRY] 将删除: {cache_dir.relative_to(self.project_root)} ({size:.2f}MB)")
                    else:
                        shutil.rmtree(cache_dir)
                        self.stats['cache_dirs'] += 1
                        self.log(f"  删除: {cache_dir.relative_to(self.project_root)} ({size:.2f}MB)")
                except Exception as e:
                    self.errors.append(f"删除缓存失败 {cache_dir}: {e}")

    def clean_reports_and_data(self):
        """清理报告和数据文件"""
        self.log("\n📊 清理报告和数据文件...", "INFO")

        # 根目录的报告文件
        report_files = [
            "coverage.json",
            "audit-report.json",
            "cache_coverage_report.json",
            "dependency_task_board.json",
            "vulnerabilities.csv",
            "vulnerabilities.json",
            "test_results.json",
            "ruff_report.json",
            "bandit_report.json",
            "complexity_report.json",
            "performance_report.json",
        ]

        for report_file in report_files:
            file_path = self.project_root / report_file
            if file_path.exists():
                try:
                    size = self.get_file_size_mb(file_path)
                    if self.dry_run:
                        self.log(f"  [DRY] 将归档: {file_path.name} ({size:.2f}MB)")
                    else:
                        self.archive_file(file_path, "reports")
                        self.stats['reports'] += 1
                        self.log(f"  归档: {file_path.name} ({size:.2f}MB)")
                except Exception as e:
                    self.errors.append(f"归档失败 {file_path}: {e}")

    def clean_logs(self):
        """清理日志文件"""
        self.log("\n📝 清理日志文件...", "INFO")

        # 查找所有日志文件
        log_patterns = [
            "**/*.log",
            "**/*.log.*",
            "logs/*.json",
            ".logs/**/*",
        ]

        for pattern in log_patterns:
            for log_file in self.project_root.glob(pattern):
                if log_file.is_file():
                    try:
                        # 检查是否是30天前的
                        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if datetime.now() - mtime > timedelta(days=30):
                            size = self.get_file_size_mb(log_file)
                            if self.dry_run:
                                self.log(f"  [DRY] 将删除: {log_file.relative_to(self.project_root)} ({size:.2f}MB)")
                            else:
                                log_file.unlink()
                                self.stats['logs'] += 1
                                self.log(f"  删除: {log_file.relative_to(self.project_root)} ({size:.2f}MB)")
                    except Exception as e:
                        self.errors.append(f"删除日志失败 {log_file}: {e}")

    def clean_misc_files(self):
        """清理其他杂项文件"""
        self.log("\n🧹 清理杂项文件...", "INFO")

        misc_files = [
            ".DS_Store",
            "Thumbs.db",
            "desktop.ini",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".coverage.*",
            "*.egg-info",
        ]

        for pattern in misc_files:
            for file_path in self.project_root.glob(pattern):
                if ".git" in str(file_path):
                    continue

                try:
                    if file_path.is_file():
                        size = self.get_file_size_mb(file_path)
                        if self.dry_run:
                            self.log(f"  [DRY] 将删除: {file_path.relative_to(self.project_root)} ({size:.2f}MB)")
                        else:
                            file_path.unlink()
                            self.stats['misc'] += 1
                            self.log(f"  删除: {file_path.relative_to(self.project_root)} ({size:.2f}MB)")
                except Exception as e:
                    self.errors.append(f"删除文件失败 {file_path}: {e}")

    def archive_file(self, file_path: Path, category: str):
        """归档文件"""
        archive_path = self.archive_dir / category
        archive_path.mkdir(parents=True, exist_ok=True)

        # 保留相对路径结构
        target_path = archive_path / file_path.name

        # 避免覆盖
        counter = 1
        original_target = target_path
        while target_path.exists():
            stem = original_target.stem
            suffix = original_target.suffix
            target_path = archive_path / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.move(str(file_path), str(target_path))

    def update_gitignore(self):
        """更新 .gitignore"""
        self.log("\n📝 更新 .gitignore...", "INFO")

        gitignore_path = self.project_root / ".gitignore"

        # 检查是否已有这些规则
        rules_to_add = [
            "",
            "# 深度清理规则",
            "*.tmp",
            "*_temp*",
            "*_backup*",
            "*_working*",
            "*.bak",
            "*.swp",
            "*.swo",
            "TEMP_*",
            "CLAUDE_*.md.bak",
            "*.orig",
            "*.rej",
            "",
            "# 报告文件",
            "coverage.json",
            "audit-report.json",
            "*_report.json",
            "vulnerabilities.csv",
            "vulnerabilities.json",
            "",
            "# 缓存目录",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            ".coverage",
            "htmlcov/",
            ".tox/",
            ".nox/",
            "",
            "# 构建目录",
            "build/",
            "dist/",
            "*.egg-info/",
        ]

        if not gitignore_path.exists():
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("\n".join(rules_to_add))
            self.log("  创建新的 .gitignore")
        else:
            # 读取现有内容
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing = f.read().splitlines()

            # 添加新规则
            new_rules = []
            for rule in rules_to_add:
                if rule and rule not in existing:
                    new_rules.append(rule)

            if new_rules:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    for rule in new_rules:
                        f.write(rule + "\n")
                self.log(f"  添加了 {len(new_rules)} 条新规则")

    def run_cleanup(self):
        """执行完整清理"""
        self.log("=" * 70)
        self.log("开始深度项目清理...", "SUCCESS")
        self.log(f"项目根目录: {self.project_root}")
        self.log("=" * 70)

        if self.dry_run:
            self.log("⚠️ 试运行模式 - 不会实际删除文件", "WARN")

        # 计算开始时的大小
        start_size = self.get_directory_size(self.project_root)

        # 执行清理
        self.clean_temp_files()
        self.clean_cache_dirs()
        self.clean_reports_and_data()
        self.clean_logs()
        self.clean_misc_files()
        self.update_gitignore()

        # 计算节省的空间
        if not self.dry_run:
            end_size = self.get_directory_size(self.project_root)
            saved_space = start_size - end_size
        else:
            saved_space = 0

        # 生成报告
        self.log("\n" + "=" * 70)
        self.log("深度清理完成!", "SUCCESS")
        self.log(f"临时文件: {self.stats['temp_files']} 个")
        self.log(f"缓存目录: {self.stats['cache_dirs']} 个")
        self.log(f"报告文件: {self.stats['reports']} 个")
        self.log(f"日志文件: {self.stats['logs']} 个")
        self.log(f"杂项文件: {self.stats['misc']} 个")
        self.log(f"总计: {sum(self.stats.values())} 个文件/目录")

        if saved_space > 0:
            self.log(f"节省空间: {saved_space:.2f} MB", "SUCCESS")

        if self.errors:
            self.log(f"\n错误数: {len(self.errors)}", "ERROR")
            for error in self.errors[:5]:
                self.log(f"  - {error}", "ERROR")

        self.log("=" * 70)

        # 保存清理报告
        if not self.dry_run:
            self.save_cleanup_report(saved_space)

    def get_directory_size(self, path: Path) -> float:
        """获取目录大小(MB)"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total += os.path.getsize(filepath)
        return total / (1024 * 1024)

    def save_cleanup_report(self, saved_space_mb: float):
        """保存清理报告"""
        report_path = self.project_root / "docs" / "_reports"
        report_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"deep_cleanup_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 深度项目清理报告\n\n")
            f.write(f"**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**清理工具**: scripts/deep_cleanup.py\n\n")

            f.write("## 清理统计\n\n")
            f.write("| 类别 | 数量 |\n")
            f.write("|------|------|\n")
            f.write(f"| 临时文件 | {self.stats['temp_files']} |\n")
            f.write(f"| 缓存目录 | {self.stats['cache_dirs']} |\n")
            f.write(f"| 报告文件 | {self.stats['reports']} |\n")
            f.write(f"| 日志文件 | {self.stats['logs']} |\n")
            f.write(f"| 杂项文件 | {self.stats['misc']} |\n")
            f.write(f"| **总计** | **{sum(self.stats.values())}** |\n\n")

            f.write(f"## 空间优化\n\n")
            f.write(f"- 节省空间: {saved_space_mb:.2f} MB\n")
            f.write(f"- 归档位置: `.cleanup_archive/`\n\n")

            if self.errors:
                f.write("## 错误列表\n\n")
                for error in self.errors:
                    f.write(f"- {error}\n")
                f.write("\n")

            f.write("## 建议\n\n")
            f.write("1. 定期运行 `python scripts/deep_cleanup.py` 清理项目\n")
            f.write("2. 使用 `python scripts/deep_cleanup.py --dry-run` 预览将要删除的文件\n")
            f.write("3. 检查 `.cleanup_archive/` 目录确认归档内容\n")

        self.log(f"\n📄 清理报告已保存: {report_file.relative_to(self.project_root)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("DEEP_CLEANUP_DESCRIPTION_405"))
    parser.add_argument("--project-root", help = os.getenv("DEEP_CLEANUP_HELP_406"), default=None)
    parser.add_argument("--dry-run", action = os.getenv("DEEP_CLEANUP_ACTION_406"), help = os.getenv("DEEP_CLEANUP_HELP_406"))

    args = parser.parse_args()

    cleaner = DeepCleaner(args.project_root)
    cleaner.dry_run = args.dry_run

    cleaner.run_cleanup()