#!/usr/bin/env python3
"""
终极项目清理脚本
清理所有大文件和无用目录，包括虚拟环境
"""

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

class UltimateCleaner:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.backup_dir = self.project_root / ".cleanup_backup"
        self.stats = {
            'venv_dirs': 0,
            'build_dirs': 0,
            'cache_dirs': 0,
            'log_files': 0,
            'large_files': 0,
            'size_mb': 0
        }
        self.errors = []
        self.dry_run = False

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        colors = {
            "INFO": "\033[0m",
            "WARN": "\033[0;33m",
            "ERROR": "\033[0;31m",
            "SUCCESS": "\033[0;32m",
            "HIGHLIGHT": "\033[1;34m"
        }
        color = colors.get(level, "\033[0m")
        print(f"{color}[{timestamp}] {level}: {message}\033[0m")

    def get_directory_size_mb(self, path: Path) -> float:
        """获取目录大小(MB)"""
        if not path.exists():
            return 0
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total += os.path.getsize(filepath)
        except (PermissionError, OSError):
            pass
        return total / (1024 * 1024)

    def clean_virtual_envs(self):
        """清理虚拟环境"""
        self.log("\n🐍 清理虚拟环境...", "HIGHLIGHT")

        # 识别虚拟环境目录
        venv_patterns = [
            "venv",
            ".venv",
            "venv_clean",
            "env",
            ".env",
            "ENV",
            ".virtualenv"
        ]

        for pattern in venv_patterns:
            venv_path = self.project_root / pattern
            if venv_path.exists() and venv_path.is_dir():
                # 检查是否是虚拟环境
                if (venv_path / "bin" / "activate").exists() or (venv_path / "Scripts" / "activate.bat").exists():
                    size_mb = self.get_directory_size_mb(venv_path)
                    self.log(f"  发现虚拟环境: {pattern}/ ({size_mb:.1f}MB)", "WARN")

                    if not self.dry_run:
                        # 保留一个（最新的或活跃的）
                        if pattern == ".venv":  # 假设.venv是当前使用的
                            self.log(f"  保留当前虚拟环境: {pattern}/", "INFO")
                        else:
                            # 备份重要配置
                            backup_path = self.backup_dir / "venvs" / pattern
                            backup_path.mkdir(parents=True, exist_ok=True)

                            # 备份requirements.txt（如果存在）
                            req_file = venv_path / "requirements.txt"
                            if req_file.exists():
                                shutil.copy2(req_file, backup_path / "requirements.txt")

                            # 删除虚拟环境
                            try:
                                shutil.rmtree(venv_path)
                                self.stats['venv_dirs'] += 1
                                self.stats['size_mb'] += size_mb
                                self.log(f"  删除虚拟环境: {pattern}/ (节省 {size_mb:.1f}MB)", "SUCCESS")
                            except Exception as e:
                                self.errors.append(f"删除虚拟环境失败 {pattern}: {e}")

    def clean_build_dirs(self):
        """清理构建目录"""
        self.log("\n🏗️ 清理构建目录...", "INFO")

        build_patterns = [
            "**/build",
            "**/dist",
            "**/*.egg-info",
            "**/.pytest_cache",
            "**/.mypy_cache",
            "**/.ruff_cache",
            "**/.coverage",
            "**/htmlcov",
            "**/.tox",
            "**/.nox"
        ]

        for pattern in build_patterns:
            for path in self.project_root.glob(pattern):
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    else:
                        size_mb = self.get_directory_size_mb(path)
                        if self.dry_run:
                            self.log(f"  [DRY] 将删除: {path.relative_to(self.project_root)} ({size_mb:.1f}MB)")
                        else:
                            try:
                                shutil.rmtree(path)
                                self.stats['build_dirs'] += 1
                                self.stats['size_mb'] += size_mb
                                self.log(f"  删除: {path.relative_to(self.project_root)} ({size_mb:.1f}MB)")
                            except Exception as e:
                                self.errors.append(f"删除构建目录失败 {path}: {e}")

    def clean_logs_and_temp(self):
        """清理日志和临时文件"""
        self.log("\n📝 清理日志和临时文件...", "INFO")

        # 清理日志
        log_patterns = [
            "**/*.log",
            "**/*.log.*",
            "logs/*.txt",
            ".logs/**/*"
        ]

        for pattern in log_patterns:
            for log_file in self.project_root.glob(pattern):
                if log_file.is_file():
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    if self.dry_run:
                        self.log(f"  [DRY] 将删除日志: {log_file.relative_to(self.project_root)} ({size_mb:.2f}MB)")
                    else:
                        try:
                            log_file.unlink()
                            self.stats['log_files'] += 1
                            self.stats['size_mb'] += size_mb
                            self.log(f"  删除日志: {log_file.relative_to(self.project_root)} ({size_mb:.2f}MB)")
                        except Exception as e:
                            self.errors.append(f"删除日志失败 {log_file}: {e}")

        # 清理其他临时文件
        temp_patterns = [
            "**/*.swp",
            "**/*.swo",
            "**/*.tmp",
            "**/*.temp",
            "**/.DS_Store",
            "**/Thumbs.db"
        ]

        for pattern in temp_patterns:
            for temp_file in self.project_root.glob(pattern):
                if temp_file.is_file():
                    try:
                        temp_file.unlink()
                        self.stats['large_files'] += 1
                        self.log(f"  删除临时文件: {temp_file.name}")
                    except Exception as e:
                        self.errors.append(f"删除临时文件失败 {temp_file}: {e}")

    def find_large_files(self, min_size_mb: int = 10):
        """查找大文件"""
        self.log(f"\n🔍 查找大于 {min_size_mb}MB 的文件...", "HIGHLIGHT")

        large_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 跳过某些目录
            dirs[:] = [d for d in dirs if d not in ['.git', 'venv', '.venv', 'venv_clean', 'node_modules']]

            for file in files:
                file_path = Path(root) / file
                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb > min_size_mb:
                        large_files.append((file_path, size_mb))
                except (PermissionError, OSError):
                    continue

        # 按大小排序
        large_files.sort(key=lambda x: x[1], reverse=True)

        # 显示前20个最大的文件
        for file_path, size_mb in large_files[:20]:
            rel_path = file_path.relative_to(self.project_root)
            self.log(f"  {rel_path} ({size_mb:.1f}MB)", "WARN")

        if len(large_files) > 20:
            self.log(f"  ... 还有 {len(large_files) - 20} 个大文件", "INFO")

        return large_files

    def clean_docker_resources(self):
        """清理Docker资源（可选）"""
        self.log("\n🐳 检查Docker资源...", "INFO")

        # 检查是否有Docker
        try:
            result = subprocess.run(
                ["docker", "system", "df"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log("  Docker系统信息:", "INFO")
                for line in result.stdout.split('\n')[:5]:
                    if line.strip():
                        self.log(f"    {line}", "INFO")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log("  Docker未安装或未运行", "INFO")

    def suggest_cleanup(self):
        """提供清理建议"""
        self.log("\n💡 清理建议:", "HIGHLIGHT")
        self.log("1. 虚拟环境占用大量空间，建议只保留当前使用的(.venv)", "INFO")
        self.log("2. 构建目录可以安全删除，需要时重新生成", "INFO")
        self.log("3. 日志文件定期清理，保留最近7天的即可", "INFO")
        self.log("4. 考虑添加到.gitignore以防止未来污染", "INFO")

    def run_cleanup(self):
        """执行终极清理"""
        self.log("=" * 80)
        self.log("开始终极项目清理...", "SUCCESS")
        self.log(f"项目根目录: {self.project_root}")
        self.log("=" * 80)

        if self.dry_run:
            self.log("⚠️ 试运行模式 - 不会实际删除文件", "WARN")

        # 1. 查找大文件
        large_files = self.find_large_files(10)

        # 2. 清理虚拟环境
        self.clean_virtual_envs()

        # 3. 清理构建目录
        self.clean_build_dirs()

        # 4. 清理日志和临时文件
        self.clean_logs_and_temp()

        # 5. Docker资源检查
        self.clean_docker_resources()

        # 6. 提供建议
        self.suggest_cleanup()

        # 生成报告
        self.log("\n" + "=" * 80)
        self.log("终极清理完成!", "SUCCESS")
        self.log(f"虚拟环境: {self.stats['venv_dirs']} 个")
        self.log(f"构建目录: {self.stats['build_dirs']} 个")
        self.log(f"日志文件: {self.stats['log_files']} 个")
        self.log(f"其他文件: {self.stats['large_files']} 个")
        self.log(f"节省空间: {self.stats['size_mb']:.1f} MB", "SUCCESS")

        if self.errors:
            self.log(f"\n错误数: {len(self.errors)}", "ERROR")
            for error in self.errors[:5]:
                self.log(f"  - {error}", "ERROR")

        self.log("=" * 80)

        # 保存清理报告
        if not self.dry_run:
            self.save_cleanup_report()

    def save_cleanup_report(self):
        """保存清理报告"""
        report_path = self.project_root / "docs" / "_reports"
        report_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"ultimate_cleanup_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 终极项目清理报告\n\n")
            f.write(f"**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**清理工具**: scripts/ultimate_cleanup.py\n\n")

            f.write("## 清理统计\n\n")
            f.write("| 项目 | 数量 | 说明 |\n")
            f.write("|------|------|------|\n")
            f.write(f"| 虚拟环境 | {self.stats['venv_dirs']} | 删除未使用的venv |\n")
            f.write(f"| 构建目录 | {self.stats['build_dirs']} | build/, dist/, .egg-info等 |\n")
            f.write(f"| 日志文件 | {self.stats['log_files']} | *.log文件 |\n")
            f.write(f"| 其他文件 | {self.stats['large_files']} | 临时文件等 |\n")
            f.write(f"| **总计节省** | **{self.stats['size_mb']:.1f} MB** | - |\n\n")

            f.write("## 建议\n\n")
            f.write("1. 定期运行 `python scripts/ultimate_cleanup.py` 清理项目\n")
            f.write("2. 只保留一个活跃的虚拟环境(.venv)\n")
            f.write("3. 将构建目录添加到.gitignore\n")
            f.write("4. 设置定时任务自动清理\n")

        self.log(f"\n📄 清理报告已保存: {report_file.relative_to(self.project_root)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("ULTIMATE_CLEANUP_DESCRIPTION_324"))
    parser.add_argument("--project-root", help = os.getenv("ULTIMATE_CLEANUP_HELP_325"), default=None)
    parser.add_argument("--dry-run", action = os.getenv("ULTIMATE_CLEANUP_ACTION_325"), help = os.getenv("ULTIMATE_CLEANUP_HELP_325"))

    args = parser.parse_args()

    cleaner = UltimateCleaner(args.project_root)
    cleaner.dry_run = args.dry_run

    cleaner.run_cleanup()