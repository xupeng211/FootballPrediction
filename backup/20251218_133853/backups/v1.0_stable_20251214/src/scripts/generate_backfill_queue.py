#!/usr/bin/env python3
"""
L2 回填队列生成器 - ETL Pipeline Extract Phase
Generate Backfill Queue for L2 Data Collection

基于 ETL (Extract-Transform-Load) 模式的高性能数据库导出工具。
专门用于从 PostgreSQL 数据库中筛选已结束且详情缺失的比赛，
为 L2 回填脚本提供标准化的输入队列。

Architecture:
    Extract: 从数据库筛选比赛 (PostgreSQL + Async SQLAlchemy)
    Transform: 数据清洗和标准化
    Load: 导出为 CSV 文件

使用示例:
    python src/scripts/generate_backfill_queue.py

输出文件:
    data/l2_backfill_queue.csv (标准格式，包含 match_id 列表)

Author: Database Expert
Version: 2.0 (ETL Optimized)
"""

import sys
import csv
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 项目模块导入
from src.database.async_manager import initialize_database, fetch_all
from sqlalchemy import text
from tqdm import tqdm

# 尝试导入 tqdm，如果没有则使用简单进度条
try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    logging.warning("tqdm not installed, using simple progress indicator")

# 配置专业日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/backfill_queue_generation.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class BackfillConfig:
    """回填配置参数"""

    output_dir: str = "data"
    output_filename: str = "l2_backfill_queue.csv"
    batch_size: int = 1000  # 批量处理大小，优化内存使用
    show_progress: bool = True
    dry_run: bool = False  # 仅查询，不导出文件

    # 比赛状态配置 (基于 FotMob API 实际状态)
    finished_statuses = [
        "FT",
        "AET",
        "PEN",
        "finished",
    ]  # Full Time, After Extra Time, Penalties

    # 数据完整度配置
    incomplete_completeness = [
        "NULL",
        "partial",
        "basic",
        "detailed",
    ]  # 需要回填的完整度状态


class BackfillQueueGenerator:
    """
    高性能 L2 回填队列生成器

    专门设计用于处理大规模比赛数据的 ETL 提取工具。
    采用异步数据库操作和批量处理优化，确保在大数据量场景下的稳定性能。
    """

    def __init__(self, config: BackfillConfig):
        """
        初始化生成器

        Args:
            config: 回填配置参数
        """
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.output_file = self.output_dir / config.output_filename

        # 统计信息
        self.stats = {
            "total_queried": 0,
            "valid_matches": 0,
            "by_season": {},
            "by_completeness": {},
            "by_status": {},
            "exported": 0,
        }

        logger.info("🔧 初始化回填队列生成器")
        logger.info(f"   输出文件: {self.output_file}")
        logger.info(f"   批量大小: {config.batch_size}")
        logger.info(f"   已结束状态: {config.finished_statuses}")
        logger.info(f"   不完整状态: {config.incomplete_completeness}")

    async def _initialize_database(self) -> None:
        """初始化数据库连接"""
        try:
            logger.info("🔌 初始化数据库连接...")
            initialize_database()
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def _build_sql_query(self) -> text:
        """
        构建优化的 SQL 查询

        Returns:
            SQLAlchemy Text 对象
        """
        # 构建状态条件
        status_conditions = ", ".join(
            [f"'{status}'" for status in self.config.finished_statuses]
        )

        # 构建完整度条件
        completeness_conditions = []
        if "NULL" in self.config.incomplete_completeness:
            completeness_conditions.append("data_completeness IS NULL")

        for completeness in self.config.incomplete_completeness:
            if completeness != "NULL":
                completeness_conditions.append(f"data_completeness = '{completeness}'")

        completeness_clause = " OR ".join(completeness_conditions)

        # 构建完整查询语句
        query = f"""
            SELECT
                fotmob_id as match_id,
                status,
                data_completeness,
                match_date,
                home_team_name,
                away_team_name,
                season,
                league_id,
                created_at,
                updated_at
            FROM matches
            WHERE fotmob_id IS NOT NULL
              AND status IN ({status_conditions})
              AND ({completeness_clause})
            ORDER BY match_date DESC, fotmob_id DESC
        """

        logger.info(
            f"📋 构建查询: 已结束状态 {len(self.config.finished_statuses)} 个，不完整状态 {len(self.config.incomplete_completeness)} 个"
        )
        return text(query)

    async def extract_pending_matches(self) -> List[Dict[str, Any]]:
        """
        提取需要 L2 回填的比赛数据 (ETL Extract Phase)

        Returns:
            待回填的比赛数据列表
        """
        logger.info("🔍 开始提取需要 L2 回填的比赛...")

        query = self._build_sql_query()

        try:
            # 执行查询
            matches = await fetch_all(query)
            self.stats["total_queried"] = len(matches)

            logger.info(f"📊 查询结果: 共 {len(matches)} 场比赛")

            # 数据验证和统计
            valid_matches = []
            for match in matches:
                # 基本数据验证
                if not match.get("match_id"):
                    logger.warning("⚠️ 跳过无效比赛记录: 缺少 match_id")
                    continue

                # 统计信息更新
                season = match.get("season", "Unknown")
                self.stats["by_season"][season] = (
                    self.stats["by_season"].get(season, 0) + 1
                )

                completeness = match.get("data_completeness", "NULL")
                self.stats["by_completeness"][completeness] = (
                    self.stats["by_completeness"].get(completeness, 0) + 1
                )

                status = match.get("status", "Unknown")
                self.stats["by_status"][status] = (
                    self.stats["by_status"].get(status, 0) + 1
                )

                valid_matches.append(match)

            self.stats["valid_matches"] = len(valid_matches)
            logger.info(f"✅ 有效比赛数据: {len(valid_matches)} 场")

            return valid_matches

        except Exception as e:
            logger.error(f"❌ 数据提取失败: {e}", exc_info=True)
            raise

    def _prepare_csv_data(self, matches: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        数据转换和标准化 (ETL Transform Phase)

        Args:
            matches: 原始比赛数据

        Returns:
            标准化的 CSV 数据
        """
        logger.info("🔄 开始数据转换和标准化...")

        csv_data = []
        for match in matches:
            csv_row = {
                "match_id": str(match["match_id"]),  # 确保 match_id 为字符串
                "status": match.get("status", ""),
                "data_completeness": match.get("data_completeness", "NULL"),
                "match_date": self._format_datetime(match.get("match_date")),
                "home_team": match.get("home_team_name", ""),
                "away_team": match.get("away_team_name", ""),
                "season": match.get("season", ""),
                "league_id": str(match.get("league_id", "")),
                "created_at": self._format_datetime(match.get("created_at")),
                "updated_at": self._format_datetime(match.get("updated_at")),
            }
            csv_data.append(csv_row)

        logger.info(f"✅ 数据转换完成: {len(csv_data)} 条记录")
        return csv_data

    def _format_datetime(self, dt_obj: Optional[datetime]) -> str:
        """格式化日期时间对象"""
        if dt_obj is None:
            return ""
        if isinstance(dt_obj, str):
            return dt_obj
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")

    def _write_csv_file(self, csv_data: List[Dict[str, str]]) -> None:
        """
        写入 CSV 文件 (ETL Load Phase)

        Args:
            csv_data: 标准化的 CSV 数据
        """
        if not csv_data:
            logger.warning("⚠️ 没有数据需要导出")
            return

        if self.config.dry_run:
            logger.info(
                f"🔍 DRY RUN: 将导出 {len(csv_data)} 条记录到 {self.output_file}"
            )
            return

        logger.info(f"💾 开始导出 {len(csv_data)} 条记录到 {self.output_file}")

        try:
            # 创建进度条
            if self.config.show_progress and HAS_TQDM:
                pbar = tqdm(total=len(csv_data), desc="导出进度", unit="records")
            else:
                pbar = None
                logger.info("📝 写入 CSV 文件...")

            with open(self.output_file, "w", newline="", encoding="utf-8") as csvfile:
                # CSV 字段定义
                fieldnames = [
                    "match_id",
                    "status",
                    "data_completeness",
                    "match_date",
                    "home_team",
                    "away_team",
                    "season",
                    "league_id",
                    "created_at",
                    "updated_at",
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # 批量写入以提高性能
                for i in range(0, len(csv_data), self.config.batch_size):
                    batch = csv_data[i : i + self.config.batch_size]
                    writer.writerows(batch)

                    if pbar:
                        pbar.update(len(batch))
                    else:
                        # 简单进度显示
                        progress = min(i + self.config.batch_size, len(csv_data))
                        percentage = (progress / len(csv_data)) * 100
                        logger.info(
                            f"   进度: {progress}/{len(csv_data)} ({percentage:.1f}%)"
                        )

            if pbar:
                pbar.close()

            self.stats["exported"] = len(csv_data)
            logger.info(f"✅ CSV 导出完成: {self.output_file}")

            # 文件大小信息
            file_size = self.output_file.stat().st_size
            logger.info(f"📁 文件大小: {file_size / 1024:.1f} KB")

        except Exception as e:
            logger.error(f"❌ CSV 导出失败: {e}", exc_info=True)
            raise

    def _print_detailed_summary(self) -> None:
        """打印详细的统计摘要"""
        print("\n" + "=" * 80)
        print("🎯 L2 回填队列生成完成 - ETL Pipeline Summary")
        print("=" * 80)

        # 基本统计
        print("📊 数据提取统计:")
        print(f"   数据库查询总数: {self.stats['total_queried']}")
        print(f"   有效比赛数量: {self.stats['valid_matches']}")
        print(f"   成功导出记录: {self.stats['exported']}")
        print(f"   输出文件路径: {self.output_file}")
        print()

        # 按赛季分布
        if self.stats["by_season"]:
            print("📅 按赛季分布:")
            for season, count in sorted(self.stats["by_season"].items(), reverse=True):
                percentage = (count / self.stats["valid_matches"]) * 100
                print(f"   {season:>12}: {count:>4} 场 ({percentage:>5.1f}%)")
            print()

        # 按数据完整度分布
        if self.stats["by_completeness"]:
            print("📈 按数据完整度分布:")
            for completeness, count in sorted(
                self.stats["by_completeness"].items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / self.stats["valid_matches"]) * 100
                print(f"   {completeness:>12}: {count:>4} 场 ({percentage:>5.1f}%)")
            print()

        # 按比赛状态分布
        if self.stats["by_status"]:
            print("🏁 按比赛状态分布:")
            for status, count in sorted(
                self.stats["by_status"].items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / self.stats["valid_matches"]) * 100
                print(f"   {status:>12}: {count:>4} 场 ({percentage:>5.1f}%)")
            print()

        print("🚀 使用建议:")
        print(
            f"   python src/scripts/backfill_l2_matches.py --input {self.output_file}"
        )
        print("=" * 80)

    async def run(self) -> None:
        """
        运行完整的 ETL 流程
        """
        start_time = datetime.now()
        logger.info("🚀 开始 L2 回填队列生成 ETL 流程...")

        try:
            # 1. 初始化数据库连接
            await self._initialize_database()

            # 2. Extract: 从数据库提取数据
            matches = await self.extract_pending_matches()

            if not matches:
                logger.info("✅ 所有比赛都已完成 L2 数据采集，无需回填")
                return

            # 3. Transform: 数据转换和标准化
            csv_data = self._prepare_csv_data(matches)

            # 4. Load: 导出到 CSV 文件
            self._write_csv_file(csv_data)

            # 5. 生成详细摘要
            self._print_detailed_summary()

            # 计算执行时间
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.info(f"🎉 L2 回填队列生成完成！耗时: {execution_time:.2f} 秒")

        except Exception as e:
            logger.error(f"❌ L2 回填队列生成失败: {e}", exc_info=True)
            sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="L2 回填队列生成器 - ETL Pipeline Extract Phase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                                    # 使用默认配置
  %(prog)s --output-dir custom_data           # 自定义输出目录
  %(prog)s --batch-size 500                   # 设置批量大小
  %(prog)s --dry-run                          # 仅查询，不导出文件
  %(prog)s --no-progress                      # 禁用进度显示
        """,
    )

    parser.add_argument(
        "--output-dir", "-o", default="data", help="输出目录路径 (默认: data)"
    )

    parser.add_argument(
        "--output-filename",
        "-f",
        default="l2_backfill_queue.csv",
        help="输出文件名 (默认: l2_backfill_queue.csv)",
    )

    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=1000,
        help="批量处理大小，优化内存使用 (默认: 1000)",
    )

    parser.add_argument(
        "--dry-run", "-d", action="store_true", help="仅查询统计，不导出文件"
    )

    parser.add_argument(
        "--no-progress", "-np", action="store_true", help="禁用进度显示"
    )

    return parser.parse_args()


async def main():
    """主函数"""
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)

    # 解析命令行参数
    args = parse_arguments()

    # 构建配置
    config = BackfillConfig(
        output_dir=args.output_dir,
        output_filename=args.output_filename,
        batch_size=args.batch_size,
        show_progress=not args.no_progress,
        dry_run=args.dry_run,
    )

    # 创建生成器并运行
    generator = BackfillQueueGenerator(config)
    await generator.run()


if __name__ == "__main__":
    # 运行 ETL 流程
    asyncio.run(main())
