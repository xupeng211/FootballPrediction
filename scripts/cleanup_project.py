#!/usr/bin/env python3
"""
项目清理脚本
自动清理项目中的临时文件、缓存文件和过期文档
"""

import os
import shutil
import glob
import time
from pathlib import Path
from datetime import datetime, timedelta

class ProjectCleaner:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.cleaned_dirs = []
        self.cleaned_files = []
        self.errors = []

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def clean_python_cache(self):
        """清理Python缓存文件"""
        self.log("开始清理Python缓存文件...")

        # 清理__pycache__目录
        pycache_dirs = list(self.project_root.rglob("__pycache__"))
        for dir_path in pycache_dirs:
            try:
                shutil.rmtree(dir_path)
                self.cleaned_dirs.append(str(dir_path))
                self.log(f"删除目录: {dir_path.relative_to(self.project_root)}")
            except Exception as e:
                self.errors.append(f"删除目录失败 {dir_path}: {e}")

        # 清理.pyc文件
        pyc_files = list(self.project_root.rglob("*.pyc"))
        pyc_files.extend(self.project_root.rglob("*.pyo"))

        for file_path in pyc_files:
            try:
                file_path.unlink()
                self.cleaned_files.append(str(file_path))
                self.log(f"删除文件: {file_path.relative_to(self.project_root)}")
            except Exception as e:
                self.errors.append(f"删除文件失败 {file_path}: {e}")

        self.log(f"Python缓存清理完成，删除了{len(pycache_dirs)}个目录和{len(pyc_files)}个文件")

    def clean_backup_dirs(self):
        """清理备份目录"""
        self.log("开始清理备份目录...")

        backup_dirs = [
            self.project_root / ".cleanup_backup",
            self.project_root / ".bak",
            self.project_root / "backup",
        ]

        for backup_dir in backup_dirs:
            if backup_dir.exists():
                try:
                    size = self._get_dir_size(backup_dir)
                    shutil.rmtree(backup_dir)
                    self.cleaned_dirs.append(str(backup_dir))
                    self.log(f"删除备份目录: {backup_dir.name} ({size}MB)")
                except Exception as e:
                    self.errors.append(f"删除备份目录失败 {backup_dir}: {e}")

    def clean_temp_files(self):
        """清理临时文件"""
        self.log("开始清理临时文件...")

        # 清理临时测试文件
        temp_patterns = [
            "**/*_working.py",
            "**/*_fixed.py",
            "**/*_temp.py",
            "**/*_backup.py",
            "**/TEMP_*",
            "**/temp_*",
            "**/*.tmp",
            "**/*.swp",
            "**/*.swo",
            "**/.DS_Store",
            "**/Thumbs.db"
        ]

        for pattern in temp_patterns:
            files = list(self.project_root.glob(pattern))
            for file_path in files:
                # 跳过.git和重要的临时文件
                if ".git" in str(file_path):
                    continue
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    else:
                        shutil.rmtree(file_path)
                    self.cleaned_files.append(str(file_path))
                    self.log(f"删除临时文件: {file_path.relative_to(self.project_root)}")
                except Exception as e:
                    self.errors.append(f"删除临时文件失败 {file_path}: {e}")

    def clean_old_logs(self, days: int = 30):
        """清理旧日志文件"""
        self.log(f"开始清理{days}天前的日志文件...")

        cutoff_date = datetime.now() - timedelta(days=days)
        log_dirs = [
            self.project_root / "logs",
            self.project_root / ".logs",
        ]

        cleaned_count = 0
        for log_dir in log_dirs:
            if not log_dir.exists():
                continue

            for log_file in log_dir.rglob("*.log"):
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        log_file.unlink()
                        cleaned_count += 1
                        self.log(f"删除旧日志: {log_file.relative_to(self.project_root)}")
                except Exception as e:
                    self.errors.append(f"删除日志失败 {log_file}: {e}")

        if cleaned_count > 0:
            self.log(f"清理了{cleaned_count}个旧日志文件")

    def archive_old_reports(self, days: int = 90):
        """归档旧报告文件"""
        self.log(f"开始归档{days}天前的报告文件...")

        cutoff_date = datetime.now() - timedelta(days=days)
        reports_dir = self.project_root / "docs" / "_reports"
        archive_dir = self.project_root / "docs" / "_archive"

        if not reports_dir.exists():
            return

        archive_dir.mkdir(exist_ok=True)

        archived_count = 0
        for report_file in reports_dir.rglob("*"):
            if not report_file.is_file():
                continue

            try:
                mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                if mtime < cutoff_date:
                    # 创建相对路径的归档目录
                    rel_path = report_file.relative_to(reports_dir)
                    archive_path = archive_dir / rel_path
                    archive_path.parent.mkdir(parents=True, exist_ok=True)

                    shutil.move(str(report_file), str(archive_path))
                    archived_count += 1
                    self.log(f"归档报告: {report_file.name}")
            except Exception as e:
                self.errors.append(f"归档报告失败 {report_file}: {e}")

        if archived_count > 0:
            self.log(f"归档了{archived_count}个旧报告文件")

    def organize_root_directory(self):
        """整理根目录"""
        self.log("开始整理根目录...")

        # 创建临时目录
        temp_dir = self.project_root / "_temp_organize"
        temp_dir.mkdir(exist_ok=True)

        # 需要移动的文件模式
        move_patterns = {
            "scripts": ["*.py", "*.sh", "*.bat"],
            "config": ["*.ini", "*.cfg", "*.conf", "*.yaml", "*.yml"],
            "docs": ["*.md", "*.txt", "*.rst"],
        }

        for dir_name, patterns in move_patterns.items():
            target_dir = self.project_root / dir_name
            target_dir.mkdir(exist_ok=True)

            for pattern in patterns:
                files = list((self.project_root).glob(pattern))
                for file_path in files:
                    # 跳过重要文件
                    if file_path.name in ["README.md", "LICENSE", "Makefile", "requirements.txt"]:
                        continue
                    if file_path.parent == self.project_root and file_path.is_file():
                        try:
                            target_path = target_dir / file_path.name
                            if not target_path.exists():
                                shutil.move(str(file_path), str(target_path))
                                self.log(f"移动文件: {file_path.name} -> {dir_name}/")
                        except Exception as e:
                            self.errors.append(f"移动文件失败 {file_path}: {e}")

        # 清理空的临时目录
        if temp_dir.exists() and not any(temp_dir.iterdir()):
            temp_dir.rmdir()

    def update_gitignore(self):
        """更新.gitignore文件"""
        self.log("更新.gitignore文件...")

        gitignore_path = self.project_root / ".gitignore"
        additions = [
            "",
            "# 自动添加的清理规则",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            ".cleanup_backup/",
            "logs/*.log",
            "*.tmp",
            "*.bak",
            "*_working.py",
            "*_fixed.py",
            "*_temp.py",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# 缓存目录",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            ".coverage",
            "htmlcov/",
            "",
            "# 临时报告",
            "TEMP_*.md",
            "CLAUDE_*.md.bak",
            "*_ANALYSIS.md",
            "*_SUMMARY.md",
        ]

        try:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                for line in additions:
                    f.write(line + "\n")
            self.log(".gitignore文件已更新")
        except Exception as e:
            self.errors.append(f"更新.gitignore失败: {e}")

    def _get_dir_size(self, path: Path) -> float:
        """获取目录大小(MB)"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return round(total_size / (1024 * 1024), 2)

    def run_cleanup(self):
        """执行完整的清理流程"""
        start_time = time.time()
        self.log("=" * 50)
        self.log("开始项目清理...")
        self.log(f"项目根目录: {self.project_root}")
        self.log("=" * 50)

        # 执行清理步骤
        self.clean_python_cache()
        self.clean_backup_dirs()
        self.clean_temp_files()
        self.clean_old_logs()
        self.archive_old_reports()
        self.organize_root_directory()
        self.update_gitignore()

        # 生成清理报告
        elapsed_time = time.time() - start_time
        self.log("=" * 50)
        self.log("清理完成!")
        self.log(f"耗时: {elapsed_time:.2f}秒")
        self.log(f"删除目录数: {len(self.cleaned_dirs)}")
        self.log(f"删除文件数: {len(self.cleaned_files)}")
        if self.errors:
            self.log(f"错误数: {len(self.errors)}")
            for error in self.errors[:5]:  # 只显示前5个错误
                self.log(f"  - {error}", "ERROR")
        self.log("=" * 50)

        # 保存清理报告
        self.save_cleanup_report(elapsed_time)

    def save_cleanup_report(self, elapsed_time: float):
        """保存清理报告"""
        report_path = self.project_root / "docs" / "_reports"
        report_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"cleanup_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 项目清理报告\n\n")
            f.write(f"**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**耗时**: {elapsed_time:.2f}秒\n\n")
            f.write("## 清理统计\n\n")
            f.write(f"- 删除目录数: {len(self.cleaned_dirs)}\n")
            f.write(f"- 删除文件数: {len(self.cleaned_files)}\n")
            f.write(f"- 错误数: {len(self.errors)}\n\n")

            if self.cleaned_dirs:
                f.write("## 删除的目录\n\n")
                for dir_path in self.cleaned_dirs[:20]:  # 只显示前20个
                    f.write(f"- {dir_path}\n")
                if len(self.cleaned_dirs) > 20:
                    f.write(f"- ... 还有{len(self.cleaned_dirs) - 20}个目录\n")
                f.write("\n")

            if self.errors:
                f.write("## 错误列表\n\n")
                for error in self.errors:
                    f.write(f"- {error}\n")
                f.write("\n")

        self.log(f"清理报告已保存: {report_file.relative_to(self.project_root)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("CLEANUP_PROJECT_DESCRIPTION_332"))
    parser.add_argument("--project-root", help = os.getenv("CLEANUP_PROJECT_HELP_333"), default=None)
    parser.add_argument("--logs-days", type=int, default=30, help = os.getenv("CLEANUP_PROJECT_HELP_333"))
    parser.add_argument("--reports-days", type=int, default=90, help = os.getenv("CLEANUP_PROJECT_HELP_334"))

    args = parser.parse_args()

    cleaner = ProjectCleaner(args.project_root)
    cleaner.logs_days = args.logs_days
    cleaner.reports_days = args.reports_days
    cleaner.run_cleanup()