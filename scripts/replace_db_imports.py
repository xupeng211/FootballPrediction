#!/usr/bin/env python3
"""
数据库导入替换脚本
Database Import Replacement Script

自动将旧的数据库连接导入替换为新的异步接口
支持安全、渐进式的迁移策略

使用方法:
python scripts/replace_db_imports.py [--dry-run] [--backup]

选项:
--dry-run: 预览模式，不实际修改文件
--backup: 修改前创建备份文件
--file: 指定要处理的文件（可选，默认处理报告中的所有文件）
"""

import os
import sys
import re
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("patches/import_replacement.log"),
    ],
)
logger = logging.getLogger(__name__)


class DatabaseImportReplacer:
    """数据库导入替换器"""

    def __init__(self, backup: bool = True):
        self.backup = backup
        self.processed_files = []
        self.failed_files = []
        self.replacements = {
            # 旧导入模式 -> 新导入模式
            "from src.database.connection import get_async_session": "from src.database.async_manager import get_db_session",
            "from src.database.connection import DatabaseManager": "from src.database.async_manager import AsyncDatabaseManager",
            "from src.database.connection import DatabaseManager, get_async_session": "from src.database.async_manager import AsyncDatabaseManager, get_db_session",
            "from ..database.connection import get_session": "from src.database.async_manager import get_db_session",
            # 兼容性替换（临时）
            "DatabaseManager()": "DatabaseCompatManager()",
            "get_session()": "get_db_session()",
            # 特殊的CQRS模式
            "from ..database.connection_mod import get_session": "from src.database.async_manager import get_db_session",
        }

    def analyze_file(self, file_path: Path) -> dict[str, any]:
        """
        分析文件，确定替换策略

        Args:
            file_path: 文件路径

        Returns:
            分析结果字典
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"error": str(e), "needs_replacement": False}

        # 检查是否需要替换
        has_old_imports = any(
            pattern in content for pattern in self.replacements.keys()
        )
        is_async = "async def" in content

        # 检查函数签名
        sync_functions = re.findall(r"def\s+(\w+)\s*\(", content)
        async_functions = re.findall(r"async def\s+(\w+)\s*\(", content)

        return {
            "needs_replacement": has_old_imports,
            "is_async": is_async,
            "sync_functions": sync_functions,
            "async_functions": async_functions,
            "content": content,
        }

    def generate_replacement_strategy(self, analysis: dict[str, any]) -> str:
        """
        根据文件分析结果生成替换策略

        Args:
            analysis: 文件分析结果

        Returns:
            策略描述字符串
        """
        if not analysis["needs_replacement"]:
            return "无需替换"

        if analysis["is_async"]:
            return "异步文件 - 直接替换为异步接口"

        if analysis["sync_functions"] and not analysis["async_functions"]:
            return "同步文件 - 使用兼容适配器"

        if analysis["sync_functions"] and analysis["async_functions"]:
            return "混合文件 - 优先使用异步接口，同步部分用适配器"

        return "默认策略 - 使用兼容适配器"

    def apply_replacements(
        self, file_path: Path, analysis: dict[str, any], dry_run: bool = False
    ) -> bool:
        """
        应用导入替换

        Args:
            file_path: 文件路径
            analysis: 文件分析结果
            dry_run: 是否为预览模式

        Returns:
            替换是否成功
        """
        content = analysis["content"]
        original_content = content

        try:
            # 根据策略选择替换方式
            strategy = self.generate_replacement_strategy(analysis)
            logger.info(f"📁 {file_path} - {strategy}")

            if "异步文件" in strategy or "混合文件" in strategy:
                # 异步文件 - 直接替换
                for old_pattern, new_pattern in self.replacements.items():
                    if old_pattern in content:
                        content = content.replace(old_pattern, new_pattern)
                        logger.info(
                            f"  ✅ 替换: {old_pattern[:50]}... -> {new_pattern[:50]}..."
                        )

            elif "同步文件" in strategy:
                # 同步文件 - 使用兼容适配器
                if "from src.database.connection import" in content:
                    # 替换导入语句
                    content = re.sub(
                        r"from src\.database\.connection import ([^\\n]+)",
                        r"from src.database.compat import DatabaseCompatManager, fetch_all_sync, fetch_one_sync, execute_sync",
                        content,
                    )
                    logger.info("  🔄 同步适配器: 导入已替换")

                # 替换DatabaseManager实例化
                content = re.sub(
                    r"DatabaseManager\(\)", r"DatabaseCompatManager()", content
                )

            # 通用替换
            content = re.sub(r"get_session\(\)", r"get_db_session()", content)

            # 如果有变化，写入文件
            if content != original_content:
                if not dry_run:
                    if self.backup:
                        backup_path = file_path.with_suffix(
                            file_path.suffix + ".backup"
                        )
                        shutil.copy2(file_path, backup_path)
                        logger.info(f"  💾 备份: {backup_path}")

                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    logger.info("  ✅ 文件已更新")
                else:
                    logger.info("  🔍 预览模式: 将更新此文件")

                return True
            else:
                logger.info("  ℹ️  无需更改")
                return False

        except Exception as e:
            logger.error(f"  ❌ 处理失败: {e}")
            self.failed_files.append((str(file_path), str(e)))
            return False

    def process_files(
        self, file_list: list[Path], dry_run: bool = False
    ) -> dict[str, int]:
        """
        批量处理文件

        Args:
            file_list: 文件路径列表
            dry_run: 是否为预览模式

        Returns:
            处理结果统计
        """
        stats = {
            "total": len(file_list),
            "processed": 0,
            "needs_replacement": 0,
            "failed": 0,
            "skipped": 0,
        }

        logger.info(f"🚀 开始处理 {len(file_list)} 个文件 (预览模式: {dry_run})")

        for file_path in file_list:
            logger.info(f"\n{'='*60}")

            try:
                # 分析文件
                analysis = self.analyze_file(file_path)

                if "error" in analysis:
                    logger.error(f"❌ 分析失败: {analysis['error']}")
                    stats["failed"] += 1
                    continue

                if not analysis["needs_replacement"]:
                    logger.info("ℹ️  跳过: 无需替换")
                    stats["skipped"] += 1
                    continue

                stats["needs_replacement"] += 1

                # 应用替换
                if self.apply_replacements(file_path, analysis, dry_run):
                    stats["processed"] += 1
                    self.processed_files.append(str(file_path))

            except Exception as e:
                logger.error(f"❌ 处理 {file_path} 时出错: {e}")
                stats["failed"] += 1
                self.failed_files.append((str(file_path), str(e)))

        return stats

    def generate_summary_report(self, stats: dict[str, int]) -> str:
        """
        生成处理摘要报告

        Args:
            stats: 处理统计

        Returns:
            报告字符串
        """
        report = f"""
📊 数据库导入替换处理报告
{'='*50}

📈 处理统计:
- 总文件数: {stats['total']}
- 需要替换: {stats['needs_replacement']}
- 成功处理: {stats['processed']}
- 跳过文件: {stats['skipped']}
- 失败文件: {stats['failed']}

✅ 成功处理的文件:
{chr(10).join(f"  • {f}" for f in self.processed_files[:10])}
{f"  ... 还有 {len(self.processed_files) - 10} 个文件" if len(self.processed_files) > 10 else ""}

❌ 失败的文件:
{chr(10).join(f"  • {f}: {e}" for f, e in self.failed_files[:5])}
{f"  ... 还有 {len(self.failed_files) - 5} 个文件" if len(self.failed_files) > 5 else ""}

💡 下一步操作:
1. 检查成功处理的文件，确认替换正确
2. 手动修复失败的文件
3. 运行测试验证功能正常
4. 提交更改到版本控制
        """
        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库导入替换脚本")
    parser.add_argument(
        "--dry-run", action="store_true", help="预览模式，不实际修改文件"
    )
    parser.add_argument("--no-backup", action="store_true", help="不创建备份文件")
    parser.add_argument("--file", type=str, help="指定要处理的文件")
    parser.add_argument(
        "--limit", type=int, default=3, help="限制处理的文件数量（用于测试）"
    )

    args = parser.parse_args()

    # 确保工作目录正确
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    logger.info(f"🏠 工作目录: {project_root}")

    # 读取需要处理的文件列表
    usage_report = project_root / "reports" / "old_db_usage.txt"

    if args.file:
        # 处理单个文件
        file_paths = [Path(args.file)]
    else:
        # 从报告文件读取
        if not usage_report.exists():
            logger.error(f"❌ 报告文件不存在: {usage_report}")
            sys.exit(1)

        # 解析报告文件，提取文件路径
        file_paths = set()
        with open(usage_report, encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    file_path = line.split(":")[0]
                    # 只处理.py文件且排除测试文件（第一步）
                    if file_path.endswith(".py") and not any(
                        x in file_path for x in ["test_", "/tests/"]
                    ):
                        file_paths.add(Path(file_path))

        file_paths = list(file_paths)

        # 限制处理数量（用于测试）
        if args.limit:
            file_paths = file_paths[: args.limit]
            logger.info(f"⚠️  限制处理数量为: {args.limit}")

    logger.info(f"📋 将处理 {len(file_paths)} 个文件")

    # 创建替换器
    replacer = DatabaseImportReplacer(backup=not args.no_backup)

    # 处理文件
    stats = replacer.process_files(file_paths, dry_run=args.dry_run)

    # 生成报告
    report = replacer.generate_summary_report(stats)

    # 保存报告
    report_file = (
        Path("patches")
        / f"replacement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    # 输出报告
    print(report)

    logger.info(f"📄 详细报告已保存到: {report_file}")

    # 返回状态码
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    from datetime import datetime

    main()
