#!/usr/bin/env python3
"""
文档清理脚本
自动清理过期的报告、重复的文档和无用的任务文件
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta

class DocumentCleaner:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.docs_dir = self.project_root / "docs"
        self.archive_dir = self.docs_dir / "_archive"
        self.deleted_files = []
        self.archived_files = []
        self.errors = []

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def analyze_docs(self):
        """分析文档目录结构"""
        self.log("开始分析文档目录...")

        # 统计各类文件
        stats = {}
        for root, dirs, files in os.walk(self.docs_dir):
            for file in files:
                if file.endswith('.md'):
                    path = Path(root) / file
                    rel_path = path.relative_to(self.docs_dir)
                    category = str(rel_path).split('/')[0]
                    stats[category] = stats.get(category, 0) + 1

        self.log("\n📊 文档统计:")
        for category, count in sorted(stats.items()):
            self.log(f"  {category}: {count} 个文件")

        return stats

    def is_temporary_report(self, file_path: Path) -> bool:
        """判断是否是临时报告"""
        name_patterns = [
            "COVERAGE_BASELINE_*",
            "CLEANUP_UNIT_*",
            "BATCH*",
            "BUGFIX_TODO",
            "CI_*",
            "TEMP_*",
            "CLAUDE_*",
            "coverage_*.json",
            "ruff_*.json",
            "bandit*.json",
            "*_REPORT.json",
        ]

        file_name = file_path.name
        for pattern in name_patterns:
            if pattern.endswith('*'):
                if file_name.startswith(pattern[:-1]):
                    return True
            elif pattern.startswith('*'):
                if file_name.endswith(pattern[1:]):
                    return True
            elif file_name == pattern:
                return True

        return False

    def is_duplicate_coverage_report(self, file_path: Path) -> bool:
        """判断是否是重复的覆盖率报告"""
        name = file_path.name
        # 基线报告有很多重复的
        if "COVERAGE_BASELINE_P1_" in name:
            return True
        if name in ["COVERAGE_PROGRESS_NEW.md", "COVERAGE_PROGRESS.md"]:
            return True
        return False

    def is_old_report(self, file_path: Path, days: int = 30) -> bool:
        """判断是否是旧报告"""
        if not file_path.exists():
            return False

        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        cutoff_date = datetime.now() - timedelta(days=days)

        # 特别检查某些类型的报告
        if file_path.parent.name == "_reports":
            # 临时报告7天后就算旧
            if self.is_temporary_report(file_path):
                return mtime < (datetime.now() - timedelta(days=7))
            # 其他报告30天后算旧
            return mtime < cutoff_date

        return False

    def clean_reports(self):
        """清理 _reports 目录"""
        self.log("\n🗂️ 清理 _reports 目录...")

        reports_dir = self.docs_dir / "_reports"
        if not reports_dir.exists():
            return

        # 保留的重要文件
        keep_files = {
            "PRODUCTION_READINESS_REPORT.md",
            "MLFLOW_SECURITY_REPORT.md",
            "DEPENDENCY_VULNERABILITY_REPORT.md",
            "CONTINUOUS_IMPROVEMENT_REPORT.md",
        }

        for file_path in reports_dir.rglob("*"):
            if not file_path.is_file():
                continue

            rel_path = file_path.relative_to(self.docs_dir)

            # 跳过重要文件
            if file_path.name in keep_files:
                continue

            # 清理临时报告
            if self.is_temporary_report(file_path):
                self.archive_file(file_path, "临时报告")
            # 清理旧报告
            elif self.is_old_report(file_path, days=30):
                self.archive_file(file_path, "过期报告")

    def clean_tasks(self):
        """清理 _tasks 目录"""
        self.log("\n📋 清理 _tasks 目录...")

        tasks_dir = self.docs_dir / "_tasks"
        if not tasks_dir.exists():
            return

        # 检查任务文件是否已完成
        for file_path in tasks_dir.glob("*.md"):
            # 保留重要的任务文件
            if file_path.name in ["PRODUCTION_READINESS_BOARD.md"]:
                continue

            # 其他任务文件归档
            self.archive_file(file_path, "任务文件")

    def clean_duplicate_docs(self):
        """清理重复的文档"""
        self.log("\n🔄 清理重复文档...")

        # 处理重复的覆盖率进度报告
        coverage_reports = list(self.docs_dir.rglob("COVERAGE_PROGRESS*.md"))
        if len(coverage_reports) > 1:
            # 保留最新的一个
            coverage_reports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for file_path in coverage_reports[1:]:
                self.archive_file(file_path, "重复文档")

        # 处理重复的测试策略文档
        test_strategies = list(self.docs_dir.rglob("*TEST_STRATEGY*.md"))
        if len(test_strategies) > 1:
            test_strategies.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for file_path in test_strategies[1:]:
                self.archive_file(file_path, "重复文档")

    def archive_file(self, file_path: Path, reason: str):
        """归档文件"""
        try:
            # 创建归档目录
            archive_path = self.archive_dir / reason.replace(" ", "_")
            archive_path.mkdir(parents=True, exist_ok=True)

            # 计算相对路径
            rel_path = file_path.relative_to(self.docs_dir)
            target_path = archive_path / rel_path.name

            # 如果文件已存在，添加时间戳
            if target_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = target_path.stem
                suffix = target_path.suffix
                target_path = archive_path / f"{stem}_{timestamp}{suffix}"

            shutil.move(str(file_path), str(target_path))
            self.archived_files.append((str(rel_path), reason))
            self.log(f"  归档: {rel_path} ({reason})")

        except Exception as e:
            self.errors.append(f"归档失败 {file_path}: {e}")

    def organize_docs(self):
        """整理文档结构"""
        self.log("\n📚 整理文档结构...")

        # 创建标准的文档目录结构
        standard_dirs = {
            "api": self.docs_dir / "api",
            "architecture": self.docs_dir / "architecture",
            "ops": self.docs_dir / "ops",
            "reference": self.docs_dir / "reference",
            "guides": self.docs_dir / "guides",
        }

        for dir_name, dir_path in standard_dirs.items():
            if not dir_path.exists():
                dir_path.mkdir(exist_ok=True)
                self.log(f"  创建目录: {dir_name}/")

        # 移动散落的文档
        for file_path in self.docs_dir.glob("*.md"):
            if file_path.name in ["README.md", "INDEX.md", "CONTRIBUTING.md"]:
                continue

            # 根据文件名判断应该放在哪里
            name = file_path.name.lower()
            if "api" in name:
                target_dir = standard_dirs["api"]
            elif "architecture" in name or "arch" in name:
                target_dir = standard_dirs["architecture"]
            elif "deploy" in name or "ops" in name or "production" in name:
                target_dir = standard_dirs["ops"]
            elif "guide" in name or "tutorial" in name:
                target_dir = standard_dirs["guides"]
            else:
                continue

            if target_dir != file_path.parent:
                target_path = target_dir / file_path.name
                if not target_path.exists():
                    shutil.move(str(file_path), str(target_path))
                    self.log(f"  移动: {file_path.name} -> {dir_name}/")

    def create_docs_index(self):
        """创建文档索引"""
        self.log("\n📝 创建文档索引...")

        index_path = self.docs_dir / "INDEX.md"
        if index_path.exists():
            return

        content = """# 文档索引

## 📚 核心文档

### 快速开始
- [CLAUDE.md](../CLAUDE.md) - AI开发指南
- [快速参考](../CLAUDE_QUICK_REFERENCE.md)
- [故障排除](../CLAUDE_TROUBLESHOOTING.md)

### API文档
- [API参考](reference/API_REFERENCE.md)
- [数据库架构](reference/DATABASE_SCHEMA.md)
- [开发指南](reference/DEVELOPMENT_GUIDE.md)

### 架构设计
- [系统架构](architecture/)
- [生产环境架构](architecture/PRODUCTION_ARCHITECTURE.md)

### 运维手册
- [部署指南](ops/)
- [监控指南](ops/monitoring/)
- [安全配置](ops/security/)

### 测试文档
- [测试策略](testing/)
- [覆盖率报告](testing/COVERAGE_PROGRESS.md)

### 项目管理
- [工作流指南](ai/CLAUDE_WORKFLOW_GUIDE.md)
- [AI开发规则](AI_DEVELOPMENT_DOCUMENTATION_RULES.md)

## 📊 报告归档

过期报告已归档到 [_archive/](./_archive/) 目录。

## 🔗 相关链接

- GitHub仓库
- CI/CD流水线
- 监控仪表板
"""

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.log(f"  创建文档索引: INDEX.md")

    def run_cleanup(self):
        """执行完整的清理流程"""
        self.log("=" * 60)
        self.log("开始文档清理...")
        self.log(f"项目根目录: {self.project_root}")
        self.log("=" * 60)

        # 分析当前状态
        self.analyze_docs()

        # 执行清理
        self.clean_reports()
        self.clean_tasks()
        self.clean_duplicate_docs()
        self.organize_docs()
        self.create_docs_index()

        # 生成清理报告
        self.log("\n" + "=" * 60)
        self.log("文档清理完成!")
        self.log(f"归档文件数: {len(self.archived_files)}")
        self.log(f"删除文件数: {len(self.deleted_files)}")
        if self.errors:
            self.log(f"错误数: {len(self.errors)}")

        # 保存清理报告
        self.save_cleanup_report()

        self.log("=" * 60)

    def save_cleanup_report(self):
        """保存清理报告"""
        report_path = self.docs_dir / "_reports"
        report_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"docs_cleanup_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 文档清理报告\n\n")
            f.write(f"**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 清理统计\n\n")
            f.write(f"- 归档文件数: {len(self.archived_files)}\n")
            f.write(f"- 删除文件数: {len(self.deleted_files)}\n")
            f.write(f"- 错误数: {len(self.errors)}\n\n")

            if self.archived_files:
                f.write("## 归档的文件\n\n")
                for file_path, reason in self.archived_files:
                    f.write(f"- `{file_path}` ({reason})\n")
                f.write("\n")

            if self.errors:
                f.write("## 错误列表\n\n")
                for error in self.errors:
                    f.write(f"- {error}\n")
                f.write("\n")

        self.log(f"\n📄 清理报告已保存: {report_file.relative_to(self.project_root)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("CLEANUP_DOCS_DESCRIPTION_358"))
    parser.add_argument("--project-root", help = os.getenv("CLEANUP_DOCS_HELP_359"), default=None)
    parser.add_argument("--dry-run", action = os.getenv("CLEANUP_DOCS_ACTION_359"), help = os.getenv("CLEANUP_DOCS_HELP_359"))

    args = parser.parse_args()

    cleaner = DocumentCleaner(args.project_root)
    cleaner.dry_run = args.dry_run

    if args.dry_run:
        cleaner.log("⚠️ 试运行模式 - 不会实际删除文件")

    cleaner.run_cleanup()