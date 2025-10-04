#!/usr/bin/env python3
"""
高级文档清理工具
深度清理docs目录中的所有无用文件
"""

import os
import re
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Set

class AdvancedDocumentCleaner:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.docs_dir = self.project_root / "docs"
        self.archive_dir = self.docs_dir / "_archive"
        self.stats = {
            'total_files': 0,
            'archived': 0,
            'deleted': 0,
            'duplicates': 0,
            'empty_dirs': 0,
            'size_saved_mb': 0
        }
        self.errors = []
        self.dry_run = False

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": "\033[0m",
            "WARN": "\033[0;33m",
            "ERROR": "\033[0;31m",
            "SUCCESS": "\033[0;32m",
            "HIGHLIGHT": "\033[1;34m"
        }
        color = colors.get(level, "\033[0m")
        print(f"{color}[{timestamp}] {level}: {message}\033[0m")

    def get_file_hash(self, file_path: Path) -> str:
        """获取文件哈希值用于查重"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""

    def is_likely_obsolete(self, file_path: Path) -> Tuple[bool, str]:
        """判断文件是否可能已过时"""
        name = file_path.name.lower()
        parent_dir = file_path.parent.name.lower()

        # 明显的过时文件模式
        obsolete_patterns = [
            # 临时文件
            r'^temp_.*',
            r'^tmp_.*',
            r'^.*_temp$',
            r'^.*_working$',
            r'^.*_draft$',

            # 备份文件
            r'^.*\.bak$',
            r'^.*\.backup$',
            r'^.*_backup\.',
            r'^.*_copy\.',

            # 旧版本标记
            r'^.*_v[0-9]+.*$',
            r'^.*_old$',
            r'^.*_deprecated$',
            r'^.*_legacy$',

            # 草稿和临时
            r'^draft_.*',
            r'^wip_.*',
            r'^work_in_progress.*',

            # AI生成的临时文件
            r'^claude_.*\.md\.bak$',
            r'^gpt_.*',
            r'^ai_.*_temp.*',

            # 测试文件
            r'^test_.*\.md$',
            r'^.*_test\.md$',

            # 多余的编号
            r'^.*_\d{8}_.*$',  # 日期编号
            r'^.*_\d{6}_.*$',  # 短日期编号
        ]

        for pattern in obsolete_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return True, f"匹配过时模式: {pattern}"

        # 特定目录的文件
        if parent_dir in ['_reports', '_tasks', '_archive']:
            # 检查修改时间
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                days_old = (datetime.now() - mtime).days

                # 临时报告7天后过时
                if any(temp in name for temp in ['temp', 'tmp', 'draft', 'wip']):
                    if days_old > 7:
                        return True, f"临时文件超过7天"

                # 普通报告30天后过时
                if days_old > 30:
                    return True, f"报告超过30天"
            except:
                pass

        # 内容检查 - 查找空文件或极少内容
        if file_path.suffix == '.md':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # 少于50字符的markdown文件可能没用
                    if len(content) < 50:
                        return True, "内容过少"
            except:
                pass

        return False, ""

    def find_duplicate_content(self) -> Dict[str, List[Path]]:
        """查找内容重复的文件"""
        self.log("\n🔍 查找重复内容...", "INFO")

        content_map = {}
        duplicates = {}

        for md_file in self.docs_dir.rglob("*.md"):
            if "_archive" in str(md_file):
                continue

            try:
                # 计算内容哈希
                content_hash = self.get_file_hash(md_file)
                if content_hash:
                    if content_hash not in content_map:
                        content_map[content_hash] = []
                    content_map[content_hash].append(md_file)
            except:
                pass

        # 找出重复的
        for hash_val, files in content_map.items():
            if len(files) > 1:
                duplicates[hash_val] = files
                self.log(f"\n  重复内容组 (哈希: {hash_val[:8]}...):")
                for f in files:
                    size = f.stat().st_size
                    self.log(f"    - {f.relative_to(self.docs_dir)} ({size} bytes)")

        return duplicates

    def find_similar_files(self) -> List[List[Path]]:
        """查找文件名相似的文件"""
        self.log("\n🔍 查找相似文件名...", "INFO")

        file_groups = {}

        for md_file in self.docs_dir.rglob("*.md"):
            if "_archive" in str(md_file):
                continue

            # 标准化文件名
            normalized = md_file.stem.lower()
            # 移除常见后缀
            normalized = re.sub(r'(_v\d+|_\d{8}|_old|_new|_backup|_draft|_copy|_temp|_working|_legacy|_deprecated)$', '', normalized)
            # 替换分隔符
            normalized = re.sub(r'[-_]+', '_', normalized)

            if normalized not in file_groups:
                file_groups[normalized] = []
            file_groups[normalized].append(md_file)

        # 找出相似的
        similar_groups = []
        for normalized, files in file_groups.items():
            if len(files) > 1:
                similar_groups.append(files)
                self.log(f"\n  相似文件组: {normalized}")
                for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    self.log(f"    - {f.name} ({mtime})")

        return similar_groups

    def find_orphaned_images(self) -> List[Path]:
        """查找未被引用的图片"""
        self.log("\n🖼️ 查找孤立图片...", "INFO")

        # 收集所有图片
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']
        all_images = []
        for ext in image_extensions:
            all_images.extend(self.docs_dir.rglob(f"*{ext}"))

        # 收集所有markdown内容
        referenced_images = set()
        for md_file in self.docs_dir.rglob("*.md"):
            if "_archive" not in str(md_file):
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 查找图片引用
                        for img in all_images:
                            if img.name in content:
                                referenced_images.add(img)
                except:
                    pass

        # 找出未引用的
        orphaned = [img for img in all_images if img not in referenced_images]

        for img in orphaned:
            size = img.stat().st_size
            self.log(f"  未引用: {img.relative_to(self.docs_dir)} ({size} bytes)")

        return orphaned

    def find_empty_files(self) -> List[Path]:
        """查找空文件"""
        self.log("\n📄 查找空文件...", "INFO")

        empty_files = []

        for file_path in self.docs_dir.rglob("*"):
            if not file_path.is_file() or "_archive" in str(file_path):
                continue

            try:
                if file_path.stat().st_size == 0:
                    empty_files.append(file_path)
                    self.log(f"  空文件: {file_path.relative_to(self.docs_dir)}")
                elif file_path.suffix == '.md':
                    # 检查markdown是否只有标题
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [l.strip() for l in f.readlines() if l.strip()]
                        if len(lines) <= 2:  # 只有标题或几乎空
                            empty_files.append(file_path)
                            self.log(f"  近空文件: {file_path.relative_to(self.docs_dir)}")
            except:
                pass

        return empty_files

    def find_large_obsolete_files(self, min_size_mb: float = 0.5) -> List[Tuple[Path, float, str]]:
        """查找大文件"""
        self.log(f"\n📦 查找大于 {min_size_mb}MB 的文件...", "INFO")

        large_files = []

        for file_path in self.docs_dir.rglob("*"):
            if not file_path.is_file() or "_archive" in str(file_path):
                continue

            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > min_size_mb:
                is_obsolete, reason = self.is_likely_obsolete(file_path)
                if is_obsolete:
                    large_files.append((file_path, size_mb, reason))
                    self.log(f"  {file_path.relative_to(self.docs_dir)}: {size_mb:.2f}MB ({reason})")

        return sorted(large_files, key=lambda x: x[1], reverse=True)

    def archive_file(self, file_path: Path, reason: str):
        """归档文件"""
        if self.dry_run:
            self.log(f"  [DRY] 将归档: {file_path.relative_to(self.docs_dir)} ({reason})")
            return

        try:
            # 创建归档目录
            archive_path = self.archive_dir / reason.replace(" ", "_").replace(":", "")
            archive_path.mkdir(parents=True, exist_ok=True)

            # 保留相对路径
            rel_path = file_path.relative_to(self.docs_dir)
            target_path = archive_path / rel_path.name

            # 避免覆盖
            counter = 1
            original_target = target_path
            while target_path.exists():
                stem = original_target.stem
                suffix = original_target.suffix
                target_path = archive_path / f"{stem}_{counter}{suffix}"
                counter += 1

            # 移动文件
            shutil.move(str(file_path), str(target_path))

            # 更新统计
            size_mb = file_path.stat().st_size / (1024 * 1024)
            self.stats['size_saved_mb'] += size_mb
            self.stats['archived'] += 1

            self.log(f"  归档: {rel_path} ({reason})")

        except Exception as e:
            self.errors.append(f"归档失败 {file_path}: {e}")

    def delete_file(self, file_path: Path, reason: str):
        """删除文件"""
        if self.dry_run:
            self.log(f"  [DRY] 将删除: {file_path.relative_to(self.docs_dir)} ({reason})")
            return

        try:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            file_path.unlink()
            self.stats['size_saved_mb'] += size_mb
            self.stats['deleted'] += 1
            self.log(f"  删除: {file_path.relative_to(self.docs_dir)} ({reason})")
        except Exception as e:
            self.errors.append(f"删除失败 {file_path}: {e}")

    def clean_obsolete_files(self):
        """清理过时文件"""
        self.log("\n🗑️ 清理过时文件...", "HIGHLIGHT")

        obsolete_count = 0
        for file_path in self.docs_dir.rglob("*"):
            if not file_path.is_file() or "_archive" in str(file_path):
                continue

            is_obsolete, reason = self.is_likely_obsolete(file_path)
            if is_obsolete:
                obsolete_count += 1
                self.archive_file(file_path, reason)

        self.log(f"  发现并处理 {obsolete_count} 个过时文件")

    def process_duplicates(self, duplicates: Dict[str, List[Path]]):
        """处理重复文件"""
        self.log("\n🔄 处理重复文件...", "HIGHLIGHT")

        for hash_val, files in duplicates.items():
            # 保留最新的，归档其他的
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            keep_file = files[0]

            for dup_file in files[1:]:
                self.archive_file(dup_file, f"重复文件 (保留: {keep_file.name})")
                self.stats['duplicates'] += 1

    def process_similar_files(self, similar_groups: List[List[Path]]):
        """处理相似文件"""
        self.log("\n📝 处理相似文件...", "HIGHLIGHT")

        for files in similar_groups:
            # 按修改时间排序，保留最新的
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            keep_file = files[0]

            for similar_file in files[1:]:
                # 检查是否是旧版本
                if any(old in similar_file.name.lower() for old in ['old', 'legacy', 'deprecated', 'backup']):
                    self.archive_file(similar_file, f"旧版本文件 (保留: {keep_file.name})")
                elif similar_file.stat().st_size < keep_file.stat().st_size * 0.5:
                    # 如果文件小很多，可能是未完成的版本
                    self.archive_file(similar_file, f"不完整版本 (保留: {keep_file.name})")

    def generate_cleanup_report(self):
        """生成详细的清理报告"""
        report_dir = self.docs_dir / "_reports"
        report_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"advanced_docs_cleanup_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 高级文档清理报告\n\n")
            f.write(f"**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**清理工具**: scripts/cleanup_docs_advanced.py\n\n")

            f.write("## 清理统计\n\n")
            f.write(f"- 扫描文件总数: {self.stats['total_files']}\n")
            f.write(f"- 归档文件数: {self.stats['archived']}\n")
            f.write(f"- 删除文件数: {self.stats['deleted']}\n")
            f.write(f"- 重复文件处理: {self.stats['duplicates']}\n")
            f.write(f"- 空目录删除: {self.stats['empty_dirs']}\n")
            f.write(f"- 节省空间: {self.stats['size_saved_mb']:.2f} MB\n\n")

            if self.errors:
                f.write("## 错误列表\n\n")
                for error in self.errors:
                    f.write(f"- {error}\n")
                f.write("\n")

            f.write("## 清理策略\n\n")
            f.write("1. **过时文件识别**: 基于文件名模式和时间戳\n")
            f.write("2. **内容去重**: 使用MD5哈希识别完全相同的文件\n")
            f.write("3. **相似文件合并**: 保留最新版本，归档旧版本\n")
            f.write("4. **孤立资源清理**: 删除未引用的图片和资源\n")
            f.write("5. **空文件清理**: 删除空文件和近空文档\n\n")

            f.write("## 建议\n\n")
            f.write("1. 定期运行清理（建议每月一次）\n")
            f.write("2. 使用版本控制管理重要文档变更\n")
            f.write("3. 避免创建临时文件，直接编辑最终版本\n")
            f.write("4. 建立文档命名规范，避免重复\n")
            f.write("5. 及时删除无用的草稿和备份\n")

        self.log(f"\n📄 详细报告已保存: {report_file.relative_to(self.docs_dir)}")

    def run_advanced_cleanup(self, dry_run: bool = False):
        """执行高级清理"""
        self.dry_run = dry_run
        self.log("=" * 70)
        self.log("开始高级文档清理...", "SUCCESS")
        self.log(f"文档目录: {self.docs_dir}")
        if dry_run:
            self.log("⚠️ 试运行模式 - 不会实际删除文件", "WARN")
        self.log("=" * 70)

        # 统计初始状态
        self.stats['total_files'] = len(list(self.docs_dir.rglob("*")))

        # 1. 查找和处理过时文件
        self.clean_obsolete_files()

        # 2. 查找重复内容
        duplicates = self.find_duplicate_content()
        if duplicates:
            self.process_duplicates(duplicates)

        # 3. 查找相似文件
        similar_files = self.find_similar_files()
        if similar_files:
            self.process_similar_files(similar_files)

        # 4. 查找孤立图片
        orphaned_images = self.find_orphaned_images()
        for img in orphaned_images:
            self.archive_file(img, "未引用的图片")

        # 5. 查找空文件
        empty_files = self.find_empty_files()
        for empty in empty_files:
            self.delete_file(empty, "空文件")

        # 6. 查找大文件
        large_files = self.find_large_obsolete_files()
        for large_file, size, reason in large_files:
            self.archive_file(large_file, f"大文件 {reason}")

        # 7. 清理空目录
        self.clean_empty_directories()

        # 生成报告
        self.generate_cleanup_report()

        # 输出总结
        self.log("\n" + "=" * 70)
        self.log("高级文档清理完成！", "SUCCESS")
        self.log(f"扫描文件: {self.stats['total_files']}")
        self.log(f"归档文件: {self.stats['archived']}")
        self.log(f"删除文件: {self.stats['deleted']}")
        self.log(f"处理重复: {self.stats['duplicates']}")
        self.log(f"节省空间: {self.stats['size_saved_mb']:.2f} MB")
        if self.errors:
            self.log(f"错误数: {len(self.errors)}", "WARN")
        self.log("=" * 70)

    def clean_empty_directories(self):
        """清理空目录"""
        self.log("\n🧹 清理空目录...", "INFO")

        # 从深层开始，逐级向上
        all_dirs = sorted(
            [d for d in self.docs_dir.rglob("*") if d.is_dir() and "_archive" not in str(d)],
            key=lambda x: len(x.parts),
            reverse=True
        )

        for dir_path in all_dirs:
            try:
                # 检查是否为空
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    self.stats['empty_dirs'] += 1
                    self.log(f"  删除空目录: {dir_path.relative_to(self.docs_dir)}")
            except OSError:
                # 目录不为空或权限问题
                pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="高级文档清理工具")
    parser.add_argument("--project-root", help="项目根目录", default=None)
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")
    parser.add_argument("--min-size-mb", type=float, default=0.5, help="大文件阈值(MB)")

    args = parser.parse_args()

    cleaner = AdvancedDocumentCleaner(args.project_root)
    cleaner.run_advanced_cleanup(dry_run=args.dry_run)