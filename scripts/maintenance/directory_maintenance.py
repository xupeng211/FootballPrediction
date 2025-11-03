#!/usr/bin/env python3
"""
目录维护自动化脚本
Directory Maintenance Automation Script

用于自动化维护FootballPrediction项目的目录结构
包含清理、检查、归档、监控等功能

使用方法:
    python3 scripts/maintenance/directory_maintenance.py [选项]

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

class DirectoryMaintenance:
    """目录维护主类"""

    def __init__(self, project_root: Optional[Path] = None):
        """初始化维护工具"""
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.docs_dir = self.project_root / "docs"
        self.scripts_dir = self.project_root / "scripts"
        self.config_dir = self.project_root / "config"

        # 维护配置
        self.temp_extensions = ['.tmp', '.bak', '.log', '.swp', '.swo']
        self.cache_dirs = ['__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache']
        self.legacy_patterns = [
            'quality_report_*.json',
            'coverage_*.json',
            'improvement-report-*.md',
            'ci_coverage_report_*.json'
        ]

        # 健康指标阈值
        self.max_root_files = 400
        self.max_empty_dirs = 5
        self.archive_days = 30

    def clean_temp_files(self) -> int:
        """清理临时文件"""
        cleaned_count = 0
        total_size_freed = 0

        print("🧹 开始清理临时文件...")

        for ext in self.temp_extensions:
            for file_path in self.project_root.rglob(f"*{ext}"):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_count += 1
                    total_size_freed += file_size

        # 清理Python缓存文件
        cache_files = list(self.project_root.rglob("*.pyc")) + \
                     list(self.project_root.rglob("*.pyo")) + \
                     list(self.project_root.rglob("*.pyd"))

        for file_path in cache_files:
            if file_path.is_file():
                file_size = file_path.stat().st_size
                file_path.unlink()
                cleaned_count += 1
                total_size_freed += file_size

        size_mb = round(total_size_freed / (1024 * 1024), 2)
        print(f"✅ 清理了 {cleaned_count} 个临时文件，释放 {size_mb} MB 空间")
        return cleaned_count

    def clean_cache_dirs(self) -> int:
        """清理缓存目录"""
        cleaned_count = 0

        print("🗂️  开始清理缓存目录...")

        for cache_dir in self.cache_dirs:
            for dir_path in self.project_root.rglob(cache_dir):
                if dir_path.is_dir():
                    try:
                        shutil.rmtree(dir_path)
                        cleaned_count += 1
                    except OSError as e:
                        print(f"⚠️  无法删除目录 {dir_path}: {e}")

        print(f"✅ 清理了 {cleaned_count} 个缓存目录")
        return cleaned_count

    def check_misplaced_files(self) -> List[Path]:
        """检查错误放置的文件"""
        misplaced_files = []

        print("🔍 开始检查错误放置的文件...")

        # 检查根目录下的Python文件
        for file_path in self.project_root.glob("*.py"):
            if file_path.name != "manage.py":  # 排除管理脚本
                misplaced_files.append(file_path)

        # 检查根目录下的配置文件
        config_patterns = ["*.ini", "*.toml", "*.yml", "*.yaml"]
        for pattern in config_patterns:
            for file_path in self.project_root.glob(pattern):
                # 保留一些特殊文件
                if file_path.name not in ["alembic.ini"]:  # 保留符号链接
                    misplaced_files.append(file_path)

        # 检查根目录下的大量JSON报告文件
        json_reports = list(self.project_root.glob("quality_report_*.json")) + \
                      list(self.project_root.glob("coverage_*.json"))
        misplaced_files.extend(json_reports)

        # 检查根目录下的临时目录
        temp_dirs = [".pytest_cache", "__pycache__", ".ruff_cache", ".mypy_cache"]
        for temp_dir in temp_dirs:
            dir_path = self.project_root / temp_dir
            if dir_path.exists():
                misplaced_files.append(dir_path)

        if misplaced_files:
            print(f"⚠️  发现 {len(misplaced_files)} 个可能错误放置的文件/目录:")
            for item in misplaced_files[:10]:  # 只显示前10个
                item_type = "目录" if item.is_dir() else "文件"
                print(f"   - {item_type}: {item}")
            if len(misplaced_files) > 10:
                print(f"   - ... 还有 {len(misplaced_files) - 10} 个")
        else:
            print("✅ 未发现明显错误放置的文件")

        return misplaced_files

    def find_empty_dirs(self) -> List[Path]:
        """查找空目录"""
        empty_dirs = []

        print("📁 开始查找空目录...")

        for dir_path in self.project_root.rglob("*"):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                # 排除一些特殊目录
                if not any(parent.name in ['.git', '.venv', 'node_modules'] for parent in dir_path.parents):
                    empty_dirs.append(dir_path)

        if empty_dirs:
            print(f"⚠️  发现 {len(empty_dirs)} 个空目录:")
            for dir_path in empty_dirs[:10]:  # 只显示前10个
                print(f"   - {dir_path}")
            if len(empty_dirs) > 10:
                print(f"   - ... 还有 {len(empty_dirs) - 10} 个")
        else:
            print("✅ 未发现空目录")

        return empty_dirs

    def check_naming_conventions(self) -> Dict[str, List[str]]:
        """检查命名规范"""
        violations = {
            "snake_case_files": [],
            "kebab_case_dirs": [],
            "other_issues": []
        }

        print("📝 开始检查命名规范...")

        # 检查目录命名 (应该是kebab-case)
        for dir_path in self.project_root.rglob("*"):
            if dir_path.is_dir() and dir_path.parent == self.project_root:
                dir_name = dir_path.name
                if '_' in dir_name and not dir_name.startswith('.'):
                    violations["kebab_case_dirs"].append(dir_name)

        # 检查Python文件命名 (应该是snake_case)
        for file_path in self.project_root.rglob("*.py"):
            file_name = file_path.stem
            if '-' in file_name or ' ' in file_name:
                violations["snake_case_files"].append(str(file_path))

        # 统计违规数量
        total_violations = sum(len(items) for items in violations.values())
        if total_violations > 0:
            print(f"⚠️  发现 {total_violations} 个命名规范问题:")
            for violation_type, items in violations.items():
                if items:
                    print(f"   - {violation_type}: {len(items)} 个")
                    for item in items[:3]:  # 只显示前3个
                        print(f"     * {item}")
                    if len(items) > 3:
                        print(f"     * ... 还有 {len(items) - 3} 个")
        else:
            print("✅ 命名规范检查通过")

        return violations

    def archive_old_reports(self, days_old: int = None) -> int:
        """归档旧报告"""
        days_old = days_old or self.archive_days
        cutoff_date = datetime.now() - timedelta(days=days_old)
        archived_count = 0

        print(f"📦 开始归档 {days_old} 天前的报告...")

        # 确保归档目录存在
        archive_dir = self.docs_dir / "reports" / "legacy"
        archive_dir.mkdir(parents=True, exist_ok=True)

        # 归档旧的JSON报告
        for pattern in self.legacy_patterns:
            for report_path in self.project_root.glob(pattern):
                if report_path.is_file():
                    try:
                        # 从文件名解析日期
                        file_date_str = self._extract_date_from_filename(report_path.name)
                        if file_date_str:
                            file_date = datetime.strptime(file_date_str, "%Y%m%d_%H%M%S")
                            if file_date < cutoff_date:
                                archive_path = archive_dir / report_path.name
                                if not archive_path.exists():
                                    shutil.move(str(report_path), str(archive_path))
                                    archived_count += 1
                    except (ValueError, IndexError):
                        # 如果无法解析日期，也归档
                        if report_path.stat().st_mtime < cutoff_date.timestamp():
                            archive_path = archive_dir / report_path.name
                            if not archive_path.exists():
                                shutil.move(str(report_path), str(archive_path))
                                archived_count += 1

        print(f"✅ 归档了 {archived_count} 个旧报告")
        return archived_count

    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """从文件名中提取日期时间字符串"""
        # 尝试匹配不同的日期格式
        import re

        # 格式1: quality_report_20251103_094000.json
        match = re.search(r'(\d{8}_\d{6})', filename)
        if match:
            return match.group(1)

        # 格式2: improvement-report-20251029-132325.md
        match = re.search(r'(\d{8}-\d{6})', filename)
        if match:
            return match.group(1).replace('-', '_')

        return None

    def generate_health_report(self) -> Dict[str, Any]:
        """生成目录健康报告"""
        print("📊 生成目录健康报告...")

        # 基本统计
        root_files = list(self.project_root.iterdir())
        root_file_count = len(root_files)

        # 计算各类文件数量
        python_files = list(self.project_root.rglob("*.py"))
        markdown_files = list(self.project_root.rglob("*.md"))
        json_files = list(self.project_root.rglob("*.json"))

        # 计算目录数量
        all_dirs = [d for d in self.project_root.rglob("*") if d.is_dir()]

        # 计算项目大小
        total_size = 0
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size

        # 检查健康指标
        health_score = 100
        issues = []

        if root_file_count > self.max_root_files:
            health_score -= 20
            issues.append(f"根目录文件过多 ({root_file_count} > {self.max_root_files})")

        empty_dirs = self.find_empty_dirs()
        if len(empty_dirs) > self.max_empty_dirs:
            health_score -= 10
            issues.append(f"空目录过多 ({len(empty_dirs)} > {self.max_empty_dirs})")

        naming_violations = self.check_naming_conventions()
        total_violations = sum(len(items) for items in naming_violations.values())
        if total_violations > 10:
            health_score -= 15
            issues.append(f"命名规范问题过多 ({total_violations} 个)")

        report = {
            "timestamp": datetime.now().isoformat(),
            "health_score": max(0, health_score),
            "statistics": {
                "root_files": root_file_count,
                "python_files": len(python_files),
                "markdown_files": len(markdown_files),
                "json_files": len(json_files),
                "total_dirs": len(all_dirs),
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            },
            "issues": issues,
            "misplaced_files": len(self.check_misplaced_files()),
            "empty_dirs": len(empty_dirs),
            "naming_violations": total_violations
        }

        return report

    def save_health_report(self, report: Dict[str, Any]) -> Path:
        """保存健康报告"""
        reports_dir = self.docs_dir / "reports" / "health"
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"health_report_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"💾 健康报告已保存: {report_file}")
        return report_file

    def auto_fix_issues(self, dry_run: bool = True) -> Dict[str, int]:
        """自动修复常见问题"""
        fixes = {
            "removed_empty_dirs": 0,
            "moved_misplaced_files": 0,
            "archived_old_reports": 0,
            "cleaned_temp_files": 0,
            "cleaned_cache_dirs": 0
        }

        print(f"🔧 开始{'模拟' if dry_run else '实际'}修复...")

        # 1. 清理临时文件
        if not dry_run:
            fixes["cleaned_temp_files"] = self.clean_temp_files()
            fixes["cleaned_cache_dirs"] = self.clean_cache_dirs()

        # 2. 归档旧报告
        if not dry_run:
            fixes["archived_old_reports"] = self.archive_old_reports()

        # 3. 删除空目录
        empty_dirs = self.find_empty_dirs()
        if not dry_run:
            for dir_path in empty_dirs:
                try:
                    dir_path.rmdir()
                    fixes["removed_empty_dirs"] += 1
                except OSError:
                    pass
        else:
            fixes["removed_empty_dirs"] = len(empty_dirs)

        # 4. 移动错误放置的文件
        misplaced_files = self.check_misplaced_files()
        if not dry_run:
            # 创建合适的目录
            (self.scripts_dir / "temp").mkdir(exist_ok=True)
            (self.docs_dir / "reports" / "temp").mkdir(exist_ok=True)

            for file_path in misplaced_files:
                if file_path.is_file():
                    if file_path.suffix == '.py':
                        dest = self.scripts_dir / "temp" / file_path.name
                    elif file_path.suffix in ['.json', '.md']:
                        dest = self.docs_dir / "reports" / "temp" / file_path.name
                    else:
                        continue

                    if not dest.exists():
                        shutil.move(str(file_path), str(dest))
                        fixes["moved_misplaced_files"] += 1
        else:
            fixes["moved_misplaced_files"] = len(misplaced_files)

        print(f"✅ {'模拟' if dry_run else '实际'}修复完成:")
        for fix_type, count in fixes.items():
            if count > 0:
                print(f"   - {fix_type}: {count}")

        return fixes

    def run_maintenance(self,
                       clean_temp: bool = True,
                       clean_cache: bool = True,
                       archive_reports: bool = True,
                       generate_report: bool = True,
                       auto_fix: bool = False,
                       dry_run: bool = False) -> Dict[str, Any]:
        """运行完整的维护流程"""
        print("🚀 开始目录维护流程...")
        print(f"📁 项目根目录: {self.project_root}")
        print(f"🎯 模式: {'模拟运行' if dry_run else '实际执行'}")
        print("-" * 50)

        results = {
            "start_time": datetime.now().isoformat(),
            "actions": [],
            "issues_found": {},
            "fixes_applied": {},
            "health_report": None
        }

        try:
            # 1. 清理临时文件
            if clean_temp:
                if dry_run:
                    print("🧹 [模拟] 清理临时文件...")
                    results["actions"].append("temp_files_cleaned_simulated")
                else:
                    temp_count = self.clean_temp_files()
                    results["fixes_applied"]["temp_files_cleaned"] = temp_count
                    results["actions"].append("temp_files_cleaned")

            # 2. 清理缓存目录
            if clean_cache:
                if dry_run:
                    print("🗂️  [模拟] 清理缓存目录...")
                    results["actions"].append("cache_dirs_cleaned_simulated")
                else:
                    cache_count = self.clean_cache_dirs()
                    results["fixes_applied"]["cache_dirs_cleaned"] = cache_count
                    results["actions"].append("cache_dirs_cleaned")

            # 3. 检查问题
            misplaced_files = self.check_misplaced_files()
            empty_dirs = self.find_empty_dirs()
            naming_violations = self.check_naming_conventions()

            results["issues_found"] = {
                "misplaced_files": len(misplaced_files),
                "empty_dirs": len(empty_dirs),
                "naming_violations": sum(len(items) for items in naming_violations.values())
            }

            # 4. 归档旧报告
            if archive_reports:
                if dry_run:
                    print("📦 [模拟] 归档旧报告...")
                    results["actions"].append("reports_archived_simulated")
                else:
                    archive_count = self.archive_old_reports()
                    results["fixes_applied"]["reports_archived"] = archive_count
                    results["actions"].append("reports_archived")

            # 5. 自动修复
            if auto_fix:
                fixes = self.auto_fix_issues(dry_run=dry_run)
                if dry_run:
                    results["issues_found"]["potential_fixes"] = fixes
                else:
                    results["fixes_applied"].update(fixes)
                results["actions"].append("auto_fix_applied")

            # 6. 生成健康报告
            if generate_report:
                health_report = self.generate_health_report()
                results["health_report"] = health_report

                if not dry_run:
                    report_file = self.save_health_report(health_report)
                    results["health_report_file"] = str(report_file)
                else:
                    results["actions"].append("health_report_generated_simulated")

            results["end_time"] = datetime.now().isoformat()
            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            print(f"❌ 维护过程中出现错误: {e}")

        # 打印总结
        print("-" * 50)
        if results["success"]:
            print("✅ 目录维护流程完成!")
            print(f"📊 健康评分: {results['health_report']['health_score'] if results.get('health_report') else 'N/A'}")
            print(f"📁 根目录文件数: {results['health_report']['statistics']['root_files'] if results.get('health_report') else 'N/A'}")
        else:
            print("❌ 目录维护流程失败!")

        return results

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FootballPrediction 项目目录维护工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python3 scripts/maintenance/directory_maintenance.py                    # 完整维护
  python3 scripts/maintenance/directory_maintenance.py --check-only        # 仅检查
  python3 scripts/maintenance/directory_maintenance.py --dry-run          # 模拟运行
  python3 scripts/maintenance/directory_maintenance.py --auto-fix         # 自动修复
  python3 scripts/maintenance/directory_maintenance.py --clean-only       # 仅清理
        """
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径 (默认: 自动检测)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不实际修改文件"
    )

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅检查问题，不执行修复"
    )

    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="仅执行清理操作"
    )

    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="自动修复发现的问题"
    )

    parser.add_argument(
        "--no-temp",
        action="store_true",
        help="不清理临时文件"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="不清理缓存目录"
    )

    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="不归档旧报告"
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="不生成健康报告"
    )

    parser.add_argument(
        "--archive-days",
        type=int,
        default=30,
        help="归档多少天前的报告 (默认: 30)"
    )

    args = parser.parse_args()

    # 创建维护工具实例
    maintenance = DirectoryMaintenance(args.project_root)

    # 设置归档天数
    if args.archive_days:
        maintenance.archive_days = args.archive_days

    # 确定运行模式
    if args.check_only:
        print("🔍 仅检查模式...")
        # 只执行检查，不执行任何修改操作
        misplaced_files = maintenance.check_misplaced_files()
        empty_dirs = maintenance.find_empty_dirs()
        naming_violations = maintenance.check_naming_conventions()
        health_report = maintenance.generate_health_report()

        print(f"\n📊 检查完成，健康评分: {health_report['health_score']}")
        if health_report['issues']:
            print("⚠️  发现的问题:")
            for issue in health_report['issues']:
                print(f"   - {issue}")

    elif args.clean_only:
        print("🧹 仅清理模式...")
        results = maintenance.run_maintenance(
            clean_temp=not args.no_temp,
            clean_cache=not args.no_cache,
            archive_reports=not args.no_archive,
            generate_report=not args.no_report,
            auto_fix=False,
            dry_run=args.dry_run
        )

    else:
        # 完整维护流程
        results = maintenance.run_maintenance(
            clean_temp=not args.no_temp,
            clean_cache=not args.no_cache,
            archive_reports=not args.no_archive,
            generate_report=not args.no_report,
            auto_fix=args.auto_fix,
            dry_run=args.dry_run
        )

        # 保存维护结果
        if not args.dry_run and results.get("success"):
            maintenance_log_dir = maintenance.project_root / "logs" / "maintenance"
            maintenance_log_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = maintenance_log_dir / f"maintenance_log_{timestamp}.json"

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

            print(f"📝 维护日志已保存: {log_file}")

if __name__ == "__main__":
    main()