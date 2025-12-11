#!/usr/bin/env python3
"""
数据库数据诊断脚本
Database Data Inspection Script

用于诊断 matches 表中 status 和 data_completeness 字段的实际分布情况。
帮助调试 generate_backfill_queue.py 筛选条件不匹配的问题。

使用示例:
    python src/scripts/inspect_db_data.py

输出:
    - status 字段分布统计
    - data_completeness 字段分布统计
    - 随机采样数据展示
    - 可视化图表（如果 matplotlib 可用）
"""

import os
import sys
import asyncio
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 项目模块导入
from src.database.async_manager import initialize_database, fetch_all
from sqlalchemy import text

# 尝试导入可选依赖
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class InspectionConfig:
    """诊断配置参数"""
    sample_size: int = 10  # 采样数量
    show_all_fields: bool = False  # 是否显示所有字段
    output_charts: bool = True  # 是否输出图表
    output_dir: str = "data"  # 输出目录


class DatabaseInspector:
    """数据库诊断工具"""

    def __init__(self, config: InspectionConfig):
        """
        初始化诊断工具

        Args:
            config: 诊断配置参数
        """
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"🔍 初始化数据库诊断工具")
        logger.info(f"   采样数量: {config.sample_size}")
        logger.info(f"   输出目录: {self.output_dir}")

    async def initialize_database(self) -> None:
        """初始化数据库连接"""
        try:
            logger.info("🔌 初始化数据库连接...")
            initialize_database()
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    async def get_status_distribution(self) -> List[Dict[str, Any]]:
        """
        获取 status 字段分布统计

        Returns:
            status 分布统计结果
        """
        logger.info("📊 分析 status 字段分布...")

        query = text("""
            SELECT
                status,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches), 2) as percentage
            FROM matches
            GROUP BY status
            ORDER BY count DESC
        """)

        try:
            results = await fetch_all(query)
            logger.info(f"✅ 找到 {len(results)} 种不同的 status 值")
            return results
        except Exception as e:
            logger.error(f"❌ 查询 status 分布失败: {e}")
            raise

    async def get_data_completeness_distribution(self) -> List[Dict[str, Any]]:
        """
        获取 data_completeness 字段分布统计

        Returns:
            data_completeness 分布统计结果
        """
        logger.info("📈 分析 data_completeness 字段分布...")

        query = text("""
            SELECT
                COALESCE(data_completeness, 'NULL') as data_completeness,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches), 2) as percentage
            FROM matches
            GROUP BY data_completeness
            ORDER BY count DESC
        """)

        try:
            results = await fetch_all(query)
            logger.info(f"✅ 找到 {len(results)} 种不同的 data_completeness 值")
            return results
        except Exception as e:
            logger.error(f"❌ 查询 data_completeness 分布失败: {e}")
            raise

    async def get_fotmob_id_stats(self) -> Dict[str, Any]:
        """
        获取 fotmob_id 字段统计信息

        Returns:
            fotmob_id 统计信息
        """
        logger.info("🆔 分析 fotmob_id 字段...")

        query = text("""
            SELECT
                COUNT(*) as total_matches,
                COUNT(fotmob_id) as matches_with_fotmob_id,
                COUNT(*) - COUNT(fotmob_id) as matches_without_fotmob_id,
                ROUND(COUNT(fotmob_id) * 100.0 / COUNT(*), 2) as fotmob_id_coverage
            FROM matches
        """)

        try:
            result = await fetch_all(query)
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"❌ 查询 fotmob_id 统计失败: {e}")
            raise

    async def get_sample_records(self) -> List[Dict[str, Any]]:
        """
        获取随机采样记录

        Returns:
            随机采样的比赛记录
        """
        logger.info(f"🎲 随机采样 {self.config.sample_size} 条记录...")

        # 首先获取总记录数
        count_query = text("SELECT COUNT(*) as total FROM matches WHERE fotmob_id IS NOT NULL")
        count_result = await fetch_all(count_query)
        total_records = count_result[0]['total']

        if total_records == 0:
            logger.warning("⚠️ 数据库中没有 fotmob_id 不为空的记录")
            return []

        logger.info(f"📊 总共有 {total_records} 条有 fotmob_id 的记录")

        # 随机选择一些记录（使用 TABLESAMPLE 或者 OFFSET）
        if total_records <= self.config.sample_size:
            # 如果记录数很少，直接获取所有记录
            query = text("""
                SELECT
                    id,
                    fotmob_id,
                    status,
                    data_completeness,
                    match_date,
                    home_team_name,
                    away_team_name,
                    season,
                    created_at,
                    updated_at
                FROM matches
                WHERE fotmob_id IS NOT NULL
                ORDER BY RANDOM()
            """)
        else:
            # 如果记录数很多，使用随机采样
            query = text(f"""
                SELECT
                    id,
                    fotmob_id,
                    status,
                    data_completeness,
                    match_date,
                    home_team_name,
                    away_team_name,
                    season,
                    created_at,
                    updated_at
                FROM matches
                WHERE fotmob_id IS NOT NULL
                ORDER BY RANDOM()
                LIMIT {self.config.sample_size}
            """)

        try:
            results = await fetch_all(query)
            logger.info(f"✅ 获取到 {len(results)} 条采样记录")
            return results
        except Exception as e:
            logger.error(f"❌ 获取采样记录失败: {e}")
            raise

    async def get_potential_backfill_candidates(self) -> Dict[str, Any]:
        """
        获取潜在回填候选统计

        Returns:
            潜在回填候选的统计信息
        """
        logger.info("🎯 分析潜在回填候选...")

        # 尝试不同的状态组合
        queries = {
            "finished_matches": text("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE fotmob_id IS NOT NULL
                  AND status IN ('FT', 'AET', 'PEN', 'finished')
            """),
            "incomplete_data": text("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE fotmob_id IS NOT NULL
                  AND (data_completeness IS NULL
                       OR data_completeness = 'partial'
                       OR data_completeness = 'basic')
            """),
            "combined_candidates": text("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE fotmob_id IS NOT NULL
                  AND status IN ('FT', 'AET', 'PEN', 'finished')
                  AND (data_completeness IS NULL
                       OR data_completeness = 'partial'
                       OR data_completeness = 'basic')
            """),
            "all_statuses": text("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE fotmob_id IS NOT NULL
            """)
        }

        results = {}
        for name, query in queries.items():
            try:
                result = await fetch_all(query)
                results[name] = result[0]['count']
            except Exception as e:
                logger.error(f"❌ 查询 {name} 失败: {e}")
                results[name] = 0

        return results

    def print_distributions(self, status_dist: List[Dict], completeness_dist: List[Dict]) -> None:
        """打印分布统计"""
        print("\n" + "="*80)
        print("📊 字段分布统计")
        print("="*80)

        # Status 分布
        print(f"\n🏁 Status 字段分布 (共 {len(status_dist)} 种状态):")
        print("-" * 60)
        print(f"{'Status':<15} {'Count':<10} {'Percentage':<12}")
        print("-" * 60)
        for item in status_dist:
            print(f"{item['status']:<15} {item['count']:<10} {item['percentage']:<12}%")

        # Data Completeness 分布
        print(f"\n📈 Data Completeness 字段分布 (共 {len(completeness_dist)} 种状态):")
        print("-" * 60)
        print(f"{'Completeness':<15} {'Count':<10} {'Percentage':<12}")
        print("-" * 60)
        for item in completeness_dist:
            print(f"{item['data_completeness']:<15} {item['count']:<10} {item['percentage']:<12}%")

    def print_sample_records(self, samples: List[Dict]) -> None:
        """打印采样记录"""
        print("\n" + "="*80)
        print(f"🎲 随机采样记录 ({len(samples)} 条)")
        print("="*80)

        if not samples:
            print("⚠️ 没有采样记录可显示")
            return

        for i, record in enumerate(samples, 1):
            print(f"\n📝 记录 {i}:")
            print(f"   ID: {record.get('id', 'N/A')}")
            print(f"   FotMob ID: {record.get('fotmob_id', 'N/A')}")
            print(f"   Status: {record.get('status', 'N/A')}")
            print(f"   Data Completeness: {record.get('data_completeness', 'N/A')}")
            print(f"   Match Date: {record.get('match_date', 'N/A')}")
            print(f"   Teams: {record.get('home_team_name', 'N/A')} vs {record.get('away_team_name', 'N/A')}")
            print(f"   Season: {record.get('season', 'N/A')}")

            if self.config.show_all_fields:
                print("   所有字段:")
                for key, value in record.items():
                    print(f"     {key}: {value}")

    def print_candidate_analysis(self, candidates: Dict[str, Any]) -> None:
        """打印回填候选分析"""
        print("\n" + "="*80)
        print("🎯 潜在回填候选分析")
        print("="*80)

        print(f"\n📊 回填候选统计:")
        print(f"   已结束比赛 (FT/AET/PEN/finished): {candidates.get('finished_matches', 0)}")
        print(f"   数据不完整 (NULL/partial/basic): {candidates.get('incomplete_data', 0)}")
        print(f"   组合候选 (已结束 + 数据不完整): {candidates.get('combined_candidates', 0)}")
        print(f"   所有有 fotmob_id 的比赛: {candidates.get('all_statuses', 0)}")

        # 计算覆盖率
        all_matches = candidates.get('all_statuses', 0)
        if all_matches > 0:
            candidate_percentage = (candidates.get('combined_candidates', 0) / all_matches) * 100
            finished_percentage = (candidates.get('finished_matches', 0) / all_matches) * 100
            incomplete_percentage = (candidates.get('incomplete_data', 0) / all_matches) * 100

            print(f"\n📈 覆盖率分析:")
            print(f"   已结束比赛占比: {finished_percentage:.2f}%")
            print(f"   数据不完整占比: {incomplete_percentage:.2f}%")
            print(f"   回填候选占比: {candidate_percentage:.2f}%")

    def create_visualization(self, status_dist: List[Dict], completeness_dist: List[Dict]) -> None:
        """创建可视化图表"""
        if not HAS_VISUALIZATION or not self.config.output_charts:
            return

        try:
            logger.info("📊 生成可视化图表...")

            # 创建图表
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Database Data Distribution Analysis', fontsize=16)

            # Status 分布饼图
            status_labels = [item['status'] for item in status_dist]
            status_counts = [item['count'] for item in status_dist]
            ax1.pie(status_counts, labels=status_labels, autopct='%1.1f%%')
            ax1.set_title('Status Distribution')

            # Status 分布柱状图
            ax2.bar(status_labels, status_counts)
            ax2.set_title('Status Distribution (Bar)')
            ax2.set_xlabel('Status')
            ax2.set_ylabel('Count')
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')

            # Data Completeness 分布饼图
            completeness_labels = [item['data_completeness'] for item in completeness_dist]
            completeness_counts = [item['count'] for item in completeness_dist]
            ax3.pie(completeness_counts, labels=completeness_labels, autopct='%1.1f%%')
            ax3.set_title('Data Completeness Distribution')

            # Data Completeness 分布柱状图
            ax4.bar(completeness_labels, completeness_counts)
            ax4.set_title('Data Completeness Distribution (Bar)')
            ax4.set_xlabel('Data Completeness')
            ax4.set_ylabel('Count')
            plt.setp(ax4.get_xticklabels(), rotation=45, ha='right')

            # 调整布局并保存
            plt.tight_layout()
            output_file = self.output_dir / "database_distribution_analysis.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"✅ 图表已保存到: {output_file}")
            print(f"\n📊 可视化图表已保存到: {output_file}")

        except Exception as e:
            logger.error(f"❌ 生成图表失败: {e}")

    async def run(self) -> None:
        """运行完整的诊断流程"""
        logger.info("🚀 开始数据库诊断...")

        try:
            # 1. 初始化数据库连接
            await self.initialize_database()

            # 2. 获取数据分布统计
            logger.info("📊 获取数据分布统计...")
            status_dist = await self.get_status_distribution()
            completeness_dist = await self.get_data_completeness_distribution()
            fotmob_stats = await self.get_fotmob_id_stats()

            # 3. 获取采样记录
            samples = await self.get_sample_records()

            # 4. 获取回填候选分析
            candidates = await self.get_potential_backfill_candidates()

            # 5. 打印结果
            print(f"\n🔌 FotMob ID 覆盖率统计:")
            print(f"   总比赛数: {fotmob_stats.get('total_matches', 0)}")
            print(f"   有 FotMob ID 的比赛: {fotmob_stats.get('matches_with_fotmob_id', 0)}")
            print(f"   无 FotMob ID 的比赛: {fotmob_stats.get('matches_without_fotmob_id', 0)}")
            print(f"   覆盖率: {fotmob_stats.get('fotmob_id_coverage', 0)}%")

            self.print_distributions(status_dist, completeness_dist)
            self.print_sample_records(samples)
            self.print_candidate_analysis(candidates)

            # 6. 生成可视化图表
            self.create_visualization(status_dist, completeness_dist)

            # 7. 输出建议
            print("\n" + "="*80)
            print("💡 调试建议")
            print("="*80)

            if candidates.get('combined_candidates', 0) == 0:
                print("⚠️ 没有找到符合当前筛选条件的回填候选！")
                print("\n🔧 可能的解决方案:")
                print("1. 检查 status 字段 - 当前筛选条件可能过于严格")
                print("2. 检查 data_completeness 字段 - 可能的值与预期不符")
                print("3. 验证 fotmob_id 字段 - 确保有足够的有效 ID")
                print("4. 调整 generate_backfill_queue.py 中的筛选条件")

                if status_dist:
                    print(f"\n📋 建议 status 值:")
                    for item in status_dist:
                        print(f"   '{item['status']}' (出现 {item['count']} 次)")

                if completeness_dist:
                    print(f"\n📋 建议 data_completeness 值:")
                    for item in completeness_dist:
                        print(f"   '{item['data_completeness']}' (出现 {item['count']} 次)")
            else:
                print(f"✅ 找到 {candidates.get('combined_candidates', 0)} 个回填候选")
                print("💡 如果这个数字符合预期，请检查 generate_backfill_queue.py 的筛选逻辑")

            print("="*80)
            logger.info("🎉 数据库诊断完成！")

        except Exception as e:
            logger.error(f"❌ 数据库诊断失败: {e}", exc_info=True)
            sys.exit(1)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="数据库数据诊断脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--sample-size', '-s',
        type=int,
        default=10,
        help='采样记录数量 (默认: 10)'
    )

    parser.add_argument(
        '--show-all-fields', '-a',
        action='store_true',
        help='显示采样记录的所有字段'
    )

    parser.add_argument(
        '--no-charts', '-nc',
        action='store_true',
        help='不生成可视化图表'
    )

    parser.add_argument(
        '--output-dir', '-o',
        default='data',
        help='输出目录 (默认: data)'
    )

    args = parser.parse_args()

    # 构建配置
    config = InspectionConfig(
        sample_size=args.sample_size,
        show_all_fields=args.show_all_fields,
        output_charts=not args.no_charts,
        output_dir=args.output_dir
    )

    # 创建诊断器并运行
    inspector = DatabaseInspector(config)
    await inspector.run()


if __name__ == "__main__":
    # 运行诊断
    asyncio.run(main())