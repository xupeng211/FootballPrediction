#!/usr/bin/env python3
"""
FootballPrediction 项目清理脚本
================================

Phase 1: 移动冗余文件到 archive/
Phase 2: 合并重复目录

执行前请确保：
1. 已提交所有 Git 更改
2. 已关闭正在运行的服务
3. 备份重要数据（如需要）

作者：Claude Code
日期：2024-12-29
版本：1.0
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


class ProjectCleaner:
    """项目清理器"""

    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.archive_root = self.project_root / "archive"
        self.moved_files = []
        self.merged_dirs = []
        self.errors = []

        # 创建归档时间戳目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.cleaning_archive = self.archive_root / f"cleanup_{timestamp}"
        if not self.dry_run:
            self.cleaning_archive.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        prefix = "[DRY RUN]" if self.dry_run else "[EXECUTE]"
        print(f"{prefix} [{level}] {message}")

    def move_file(self, src: Path, dst_rel: str) -> bool:
        """移动单个文件"""
        if not src.exists():
            self.log(f"文件不存在，跳过: {src}", "WARN")
            return False

        dst = self.cleaning_archive / dst_rel / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            if not self.dry_run:
                shutil.move(str(src), str(dst))
            self.moved_files.append({
                "src": str(src.relative_to(self.project_root)),
                "dst": str(dst.relative_to(self.project_root)),
                "size": src.stat().st_size if src.exists() else 0
            })
            self.log(f"移动: {src.name} -> {dst_rel}/")
            return True
        except Exception as e:
            self.errors.append(f"移动失败: {src} -> {dst}: {e}")
            self.log(f"移动失败: {e}", "ERROR")
            return False

    def merge_directory(self, src: Path, dst: Path) -> bool:
        """合并目录（将 src 目录内容移动到 dst）"""
        if not src.exists():
            self.log(f"目录不存在，跳过: {src}", "WARN")
            return False

        if not dst.exists():
            self.log(f"目标目录不存在，先创建: {dst}", "WARN")
            if not self.dry_run:
                dst.mkdir(parents=True, exist_ok=True)

        moved_count = 0
        for item in src.iterdir():
            if item.name.startswith("."):
                continue

            dst_path = dst / item.name
            if dst_path.exists():
                self.log(f"目标已存在，跳过: {dst_path}", "WARN")
                continue

            try:
                if not self.dry_run:
                    shutil.move(str(item), str(dst_path))
                moved_count += 1
            except Exception as e:
                self.errors.append(f"合并失败: {item} -> {dst_path}: {e}")
                self.log(f"合并失败: {e}", "ERROR")

        if moved_count > 0:
            self.merged_dirs.append({
                "src": str(src.relative_to(self.project_root)),
                "dst": str(dst.relative_to(self.project_root)),
                "files_count": moved_count
            })
            self.log(f"合并: {src.name} -> {dst.name} ({moved_count} 个文件)")

        # 删除空目录
        if not self.dry_run and src.exists() and not list(src.iterdir()):
            src.rmdir()
            self.log(f"删除空目录: {src}")

        return moved_count > 0

    def phase1_cleanup_redundant_files(self):
        """Phase 1: 清理冗余文件"""
        self.log("=" * 60)
        self.log("Phase 1: 清理冗余文件")
        self.log("=" * 60)

        # 1. 根目录冗余文件
        root_junk_files = [
            "cat",
            "cli.py",
            "diagnose_sample.json",
            "Makefile.backup",
            "CODE_FREEZE_NOTICE.md",
            "COMMIT_MESSAGE.md",
            "DEPLOYMENT_HEALTH_SNAPSHOT.md",
            "MANIFEST.md",
        ]

        for filename in root_junk_files:
            filepath = self.project_root / filename
            if filepath.exists():
                self.move_file(filepath, "root_cleanup")

        # 2. frontend/ 目录
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            dst = self.cleaning_archive / "frontend_archive"
            if not self.dry_run:
                shutil.move(str(frontend_dir), str(dst))
            self.moved_files.append({
                "src": "frontend/",
                "dst": f"{self.cleaning_archive.relative_to(self.project_root)}/frontend_archive/",
                "size": sum(f.stat().st_size for f in frontend_dir.rglob("*") if f.is_file())
            })
            self.log(f"移动目录: frontend/ -> archive/")

        # 3. src/ 下的版本化文件
        versioned_files = [
            "src/ops/data_pipeline_v25.py",
            "src/ops/holographic_harvester_v34.py",
            "src/modeling/trainer_v2.py",
        ]

        for filepath_str in versioned_files:
            filepath = self.project_root / filepath_str
            if filepath.exists():
                self.move_file(filepath, "src_versions")

        # 4. database/ (根目录)
        database_dir = self.project_root / "database"
        if database_dir.exists():
            dst = self.cleaning_archive / "database_root"
            if not self.dry_run:
                shutil.move(str(database_dir), str(dst))
            self.moved_files.append({
                "src": "database/",
                "dst": f"{self.cleaning_archive.relative_to(self.project_root)}/database_root/",
                "size": 0  # 目录大小不统计
            })
            self.log(f"移动目录: database/ -> archive/ (将使用 src/database/)")

    def phase2_merge_directories(self):
        """Phase 2: 合并重复目录"""
        self.log("=" * 60)
        self.log("Phase 2: 合并重复目录")
        self.log("=" * 60)

        # 1. 合并 configs/ -> config/
        configs_dir = self.project_root / "configs"
        config_dir = self.project_root / "config"

        if configs_dir.exists() and config_dir.exists():
            self.merge_directory(configs_dir, config_dir)

        # 2. 合并 src/modeling/ -> src/ml/
        modeling_dir = self.project_root / "src" / "modeling"
        ml_dir = self.project_root / "src" / "ml"

        if modeling_dir.exists() and ml_dir.exists():
            self.merge_directory(modeling_dir, ml_dir)

        # 3. 合并 src/models/ -> src/ml/ (如果还存在)
        models_dir = self.project_root / "src" / "models"
        if models_dir.exists() and ml_dir.exists():
            self.merge_directory(models_dir, ml_dir)

    def generate_manifest(self):
        """生成移动清单"""
        manifest = {
            "cleanup_timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "moved_files": self.moved_files,
            "merged_dirs": self.merged_dirs,
            "errors": self.errors,
            "summary": {
                "total_files_moved": len(self.moved_files),
                "total_dirs_merged": len(self.merged_dirs),
                "total_errors": len(self.errors)
            }
        }

        manifest_path = self.cleaning_archive / "manifest.json"
        if not self.dry_run:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)

        self.log(f"清单已生成: {manifest_path.relative_to(self.project_root)}")
        return manifest

    def print_summary(self, manifest: Dict):
        """打印总结"""
        print("\n" + "=" * 60)
        print("清理总结")
        print("=" * 60)
        print(f"移动文件数: {manifest['summary']['total_files_moved']}")
        print(f"合并目录数: {manifest['summary']['total_dirs_merged']}")
        print(f"错误数: {manifest['summary']['total_errors']}")

        if self.errors:
            print("\n错误详情:")
            for error in self.errors:
                print(f"  - {error}")

        if self.dry_run:
            print("\n⚠️  这是 DRY RUN 模式，没有实际执行任何操作")
            print("   如果确认无误，请运行:")
            print("   python scripts/cleanup_project.py --execute")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FootballPrediction 项目清理脚本")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行操作（默认为 dry-run 模式）"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="项目根目录（默认自动检测）"
    )

    args = parser.parse_args()

    # 确认项目根目录
    project_root = args.project_root
    if not (project_root / "CLAUDE.md").exists():
        print(f"错误: 无法找到 CLAUDE.md，请确认项目根目录: {project_root}")
        return 1

    print(f"项目根目录: {project_root}")

    # 创建清理器
    cleaner = ProjectCleaner(project_root, dry_run=not args.execute)

    # 执行清理
    cleaner.phase1_cleanup_redundant_files()
    cleaner.phase2_merge_directories()

    # 生成清单
    manifest = cleaner.generate_manifest()
    cleaner.print_summary(manifest)

    return 0


if __name__ == "__main__":
    exit(main())
