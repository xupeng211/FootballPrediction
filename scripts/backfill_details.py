#!/usr/bin/env python3
"""
FBref详情页数据回填脚本
高级数据挖掘工程师: 深度数据补全专家

Purpose: Phase 2 - 基于已有的match_report_url获取阵容和详细统计数据
将数据完整性从'partial'提升到'complete'
"""

import asyncio
import logging
import sys
import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入数据库连接和详情页采集器
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from src.data.collectors.fbref_details_collector import FBrefDetailsCollector

    DB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"数据库模块导入失败: {e}")
    DB_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="🔍 %(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class FBrefDetailsBackfiller:
    """
    FBref详情页数据回填管理器

    功能：
    1. 查询部分完整的比赛记录
    2. 批量获取详情页数据
    3. 更新数据库记录
    4. 数据完整性监控
    """

    def __init__(self):
        if not DB_AVAILABLE:
            raise ImportError("数据库组件不可用，无法初始化回填器")

        # 创建数据库连接
        self.engine = self._create_database_connection()
        if not self.engine:
            raise ConnectionError("数据库连接失败")

        # 初始化详情页采集器
        self.details_collector = FBrefDetailsCollector()

        # 回填配置
        self.batch_size = 50  # 每批处理50场比赛
        self.request_delay = (3, 6)  # 请求间隔3-6秒
        self.error_delay = (15, 30)  # 错误重试间隔15-30秒

    def _create_database_connection(self):
        """创建数据库连接"""
        try:
            # 使用相同的数据库连接配置
            database_urls = [
                "postgresql://postgres:postgres-dev-password@db:5432/football_prediction",
                "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",
            ]

            engine = None
            for db_url in database_urls:
                try:
                    engine = create_engine(db_url, connect_args={"connect_timeout": 10})
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    logger.info(
                        f"✅ 数据库连接成功: {db_url.split('@')[1].split('/')[0]}"
                    )
                    break
                except Exception:
                    if engine:
                        engine.dispose()
                        engine = None
                    continue

            return engine

        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            return None

    def get_partial_matches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取需要详情页补全的比赛记录"""
        logger.info(f"🔍 查询部分完整的比赛记录 (限制: {limit})")

        try:
            with self.engine.connect() as conn:
                query = text(
                    """
                    SELECT
                        m.id,
                        m.match_date,
                        ht.name as home_team,
                        at.name as away_team,
                        m.data_source,
                        m.data_completeness,
                        m.match_metadata,
                        m.stats,
                        -- 从stats字段提取match_report_url
                        (m.stats->>'match_report_url') as match_report_url,
                        m.created_at
                    FROM matches m
                    LEFT JOIN teams ht ON m.home_team_id = ht.id
                    LEFT JOIN teams at ON m.away_team_id = at.id
                    WHERE m.data_source = 'fbref'
                    AND m.data_completeness = 'partial'
                    AND (m.stats->>'match_report_url') IS NOT NULL
                    AND (m.stats->>'match_report_url') != ''
                    ORDER BY m.match_date DESC, m.created_at ASC
                    LIMIT :limit
                """
                )

                result = conn.execute(query, {"limit": limit})
                rows = result.fetchall()

                matches = []
                for row in rows:
                    match = {
                        "id": row[0],
                        "match_date": row[1],
                        "home_team": row[2],
                        "away_team": row[3],
                        "data_source": row[4],
                        "data_completeness": row[5],
                        "match_metadata": row[6],
                        "stats": row[7],
                        "match_report_url": row[8],
                        "created_at": row[9],
                    }
                    matches.append(match)

                logger.info(f"📊 找到 {len(matches)} 场需要补全的比赛")
                return matches

        except Exception as e:
            logger.error(f"❌ 查询部分完整比赛失败: {e}")
            return []

    async def process_match_details(
        self, match: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """处理单场比赛的详情数据"""
        match_id = match["id"]
        match_report_url = match["match_report_url"]
        home_team = match["home_team"]
        away_team = match["away_team"]

        logger.info(f"🔄 处理比赛详情: {home_team} vs {away_team} (ID: {match_id})")

        try:
            # 获取详情页数据
            details = await self.details_collector.fetch_match_details(match_report_url)

            if not details:
                logger.warning(f"⚠️ 无法获取比赛 {match_id} 的详情数据")
                return None

            # 验证数据完整性
            lineups = details.get("lineups", {})
            detailed_stats = details.get("detailed_stats", {})

            # 至少要有阵容或统计数据
            if (
                not lineups.get("home")
                and not lineups.get("away")
                and not detailed_stats
            ):
                logger.warning(f"⚠️ 比赛 {match_id} 详情数据为空")
                return None

            # 构建更新数据
            update_data = {
                "lineups": lineups,
                "detailed_stats": detailed_stats,
                "extra_info": details.get("extra_info", {}),
                "details_extracted_at": details.get("extracted_at"),
                "details_source_url": details.get("source_url"),
            }

            # 打印关键信息（验证用）
            home_lineup = lineups.get("home", [])
            away_lineup = lineups.get("away", [])

            if home_lineup:
                logger.info(f"🔴 主队阵容: {len(home_lineup)} 名球员")
                # 打印前锋球员（通常位置靠前的是前锋）
                forwards = [
                    p["name"]
                    for p in home_lineup[:3]
                    if "forward" in p.get("position", "").lower()
                ]
                if forwards:
                    logger.info(f"⚡ 主队前锋: {', '.join(forwards)}")

            if away_lineup:
                logger.info(f"🔵 客队阵容: {len(away_lineup)} 名球员")

            # 打印关键统计数据
            if "possession_pct" in detailed_stats:
                logger.info(f"📈 主队控球率: {detailed_stats['possession_pct']}")

            if "shots_on_target" in detailed_stats:
                logger.info(f"🎯 射正次数: {detailed_stats['shots_on_target']}")

            logger.info(f"✅ 比赛 {match_id} 详情数据提取成功")
            return update_data

        except Exception as e:
            logger.error(f"❌ 处理比赛 {match_id} 详情失败: {e}")
            return None

    def update_match_in_database(
        self, match_id: int, details_data: Dict[str, Any]
    ) -> bool:
        """更新数据库中的比赛记录"""
        try:
            with self.engine.connect() as conn:
                # 获取现有的stats数据
                current_stats_query = text("SELECT stats FROM matches WHERE id = :id")
                current_result = conn.execute(current_stats_query, {"id": match_id})
                current_stats_row = current_result.fetchone()

                if not current_stats_row:
                    logger.error(f"❌ 找不到比赛 {match_id}")
                    return False

                # 解析现有的stats数据
                current_stats = {}
                if current_stats_row[0]:
                    try:
                        current_stats = json.loads(current_stats_row[0])
                    except (json.JSONDecodeError, TypeError):
                        current_stats = {}

                # 更新stats数据
                current_stats.update(
                    {
                        "lineups": details_data["lineups"],
                        "detailed_stats": details_data["detailed_stats"],
                        "extra_info": details_data["extra_info"],
                        "details_extracted_at": details_data["details_extracted_at"],
                        "details_source_url": details_data["details_source_url"],
                    }
                )

                # 更新数据库记录
                update_query = text(
                    """
                    UPDATE matches
                    SET lineups = :lineups,
                        stats = :stats,
                        data_completeness = :completeness,
                        updated_at = NOW()
                    WHERE id = :id
                """
                )

                conn.execute(
                    update_query,
                    {
                        "id": match_id,
                        "lineups": json.dumps(details_data["lineups"]),
                        "stats": json.dumps(current_stats),
                        "completeness": "complete",
                    },
                )

                conn.commit()
                logger.info(f"✅ 比赛 {match_id} 数据库更新成功")
                return True

        except Exception as e:
            logger.error(f"❌ 更新比赛 {match_id} 数据库失败: {e}")
            return False

    async def process_batch(self, matches: List[Dict[str, Any]]) -> Tuple[int, int]:
        """处理一批比赛"""
        logger.info(f"🔄 开始处理批次: {len(matches)} 场比赛")

        processed_count = 0
        success_count = 0

        for match in matches:
            try:
                # 处理比赛详情
                details_data = await self.process_match_details(match)

                if details_data:
                    # 更新数据库
                    if self.update_match_in_database(match["id"], details_data):
                        success_count += 1

                processed_count += 1

                # 请求间隔
                delay = random.uniform(*self.request_delay)
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"❌ 处理比赛 {match.get('id', 'unknown')} 失败: {e}")

                # 错误延迟
                error_delay = random.uniform(*self.error_delay)
                await asyncio.sleep(error_delay)

        logger.info(f"📊 批次处理完成: {success_count}/{processed_count} 成功")
        return processed_count, success_count

    async def run_backfill(self, max_iterations: int = 10) -> bool:
        """运行详情页回填"""
        logger.info("🚀 开始FBref详情页数据回填 (Phase 2)")
        logger.info("=" * 80)

        total_processed = 0
        total_success = 0

        try:
            for iteration in range(max_iterations):
                logger.info(f"🔄 回填迭代 {iteration + 1}/{max_iterations}")

                # 获取待处理的比赛
                matches = self.get_partial_matches(self.batch_size)

                if not matches:
                    logger.info("🎉 所有比赛详情已补全，回填完成!")
                    break

                # 处理这批比赛
                processed, success = await self.process_batch(matches)

                total_processed += processed
                total_success += success

                logger.info(
                    f"📈 进度统计: 总处理 {total_processed}, 成功 {total_success}"
                )

                # 批次间延迟
                if len(matches) == self.batch_size:  # 可能还有更多数据
                    batch_delay = random.uniform(10, 20)
                    logger.info(f"⏳ 批次间延迟 {batch_delay:.1f}s...")
                    await asyncio.sleep(batch_delay)

        except Exception as e:
            logger.error(f"❌ 回填过程异常: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # 关闭详情页采集器
            await self.details_collector.close()

        logger.info("=" * 80)
        logger.info("🎉 FBref详情页数据回填完成!")
        logger.info(
            f"📊 最终统计: 总处理 {total_processed} 场比赛, 成功 {total_success} 场"
        )
        logger.info(
            f"✅ 成功率: {total_success/total_processed*100:.1f}%"
            if total_processed > 0
            else "✅ 成功率: N/A"
        )

        return total_success > 0


async def main():
    """主函数"""
    logger.info("🏭 FBref详情页数据回填系统")
    logger.info(f"🕐 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 初始化回填器
        backfiller = FBrefDetailsBackfiller()
        logger.info("✅ 详情页回填器初始化成功")

        # 运行回填
        success = await backfiller.run_backfill(max_iterations=20)

        if success:
            logger.info("🎯 详情页回填任务成功!")
            sys.exit(0)
        else:
            logger.error("💥 详情页回填任务失败!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"💥 系统异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
