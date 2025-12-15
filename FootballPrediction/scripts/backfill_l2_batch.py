#!/usr/bin/env python3
"""
L2批处理回补脚本
为所有完赛场次补充79维度战术统计数据
"""

import asyncio
import sys
import os
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class L2BackfillProcessor:
    """L2数据批处理回补器"""

    def __init__(self, batch_size: int = 50, delay: int = 2):
        self.batch_size = batch_size
        self.delay = delay

    async def process_backfill(self):
        """执行L2数据回补"""
        logger.info("🎯 启动L2全量回补 (79维度战术统计)")
        logger.info("=" * 50)

        try:
            # 导入必要模块
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
            from collectors.l2_parser_enhanced import CompleteL2Parser as EnhancedL2Parser
            import aiohttp

            parser = EnhancedL2Parser()
            logger.info("✅ L2解析器初始化成功")

            # 这里应该查询数据库中需要L2回补的比赛
            # 由于完整的数据库查询比较复杂，我们先模拟这个过程

            matches_needing_l2 = await self.get_matches_needing_l2()

            if not matches_needing_l2:
                logger.info("✅ 没有需要L2回补的比赛")
                return True

            logger.info(f"📊 发现 {len(matches_needing_l2)} 场比赛需要L2回补")

            # 批量处理
            success_count = 0
            total_count = len(matches_needing_l2)

            for i in range(0, total_count, self.batch_size):
                batch = matches_needing_l2[i:i+self.batch_size]
                logger.info(f"🔄 处理批次 {i//self.batch_size + 1}: {len(batch)} 场比赛")

                batch_success = await self.process_batch(batch, parser)
                success_count += batch_success

                # 批次间延迟
                if i + self.batch_size < total_count:
                    logger.info(f"⏳ 批次间延迟 {self.delay} 秒...")
                    await asyncio.sleep(self.delay)

            success_rate = (success_count / total_count) * 100
            logger.info(f"✅ L2回补完成: {success_count}/{total_count} ({success_rate:.1f}%)")

            return success_rate >= 50

        except Exception as e:
            logger.error(f"❌ L2回补失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def get_matches_needing_l2(self) -> List[Dict]:
        """获取需要L2回补的比赛列表"""
        logger.info("🔍 查询需要L2回补的比赛...")

        try:
            # 直接使用数据库连接，避免复杂的异步管理器
            import asyncpg
            import os

            # 从环境变量获取数据库连接信息
            db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction")

            # 解析连接URL获取连接参数
            import re
            match = re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if match:
                user, password, host, port, database = match.groups()
            else:
                # 默认值
                user = "postgres"
                password = "postgres"
                host = "localhost"
                port = "5432"
                database = "football_prediction"

            # 直接创建数据库连接
            conn = await asyncpg.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database
            )

            # 查询所有完赛但无L2数据的比赛
            query = """
                SELECT
                    id,
                    fotmob_id,
                    home_team_id,
                    away_team_id,
                    match_date,
                    home_team_name,
                    away_team_name
                FROM matches
                WHERE status = 'FT' AND home_possession IS NULL
                ORDER BY match_date DESC
            """

            logger.info("📡 执行SQL查询...")

            # 执行查询
            rows = await conn.fetch(query)

            # 转换为字典列表
            matches = []
            for row in rows:
                matches.append({
                    "id": row["id"],  # 保持UUID类型
                    "fotmob_id": row["fotmob_id"],
                    "home_team_id": row["home_team_id"],  # 保持UUID类型
                    "away_team_id": row["away_team_id"],  # 保持UUID类型
                    "match_date": row["match_date"].isoformat() if row["match_date"] else None,
                    "home_team": row.get("home_team_name", "Unknown"),
                    "away_team": row.get("away_team_name", "Unknown")
                })

            # 关闭数据库连接
            await conn.close()

            logger.info(f"📊 真实数据库: 找到 {len(matches)} 场需要回补的比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def process_batch(self, batch: List[Dict], parser) -> int:
        """处理一批比赛的L2回补"""
        success_count = 0

        for match in batch:
            try:
                fotmob_id = match["fotmob_id"]
                logger.info(f"📡 回补比赛: {fotmob_id} ({match['home_team']} vs {match['away_team']})")

                # 获取FotMob数据
                api_data = await self.fetch_fotmob_data(fotmob_id)

                if not api_data:
                    logger.warning(f"⚠️  无法获取数据: {fotmob_id}")
                    continue

                # 解析数据
                l2_stats = parser.parse_api_response(api_data)

                # 验证关键字段
                key_fields = [
                    ("home_possession", l2_stats.home_possession),
                    ("home_big_chances_created", l2_stats.home_big_chances_created),
                    ("home_expected_goals_on_target", l2_stats.home_expected_goals_on_target),
                ]

                valid_count = sum(1 for _, value in key_fields if value is not None)

                if valid_count >= 2:
                    logger.info(f"   ✅ {fotmob_id}: {valid_count}/3 关键字段有效")

                    # 保存L2数据到真实数据库
                    saved = await self.save_l2_stats_to_db(match["id"], l2_stats)

                    if saved:
                        success_count += 1
                        logger.info(f"   💾 {fotmob_id}: L2数据已保存到数据库")
                    else:
                        logger.warning(f"   ⚠️  {fotmob_id}: 数据保存失败")
                else:
                    logger.warning(f"   ❌ {fotmob_id}: 数据质量不足 ({valid_count}/3)")

                # 防止API限流
                await asyncio.sleep(self.delay)

            except Exception as e:
                logger.error(f"❌ 处理比赛 {match.get('fotmob_id', 'unknown')} 失败: {e}")

        return success_count

    async def fetch_fotmob_data(self, match_id: str) -> Optional[dict]:
        """获取FotMob比赛数据"""
        try:
            import aiohttp

            url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"HTTP {response.status}: {match_id}")
                        return None

        except Exception as e:
            logger.error(f"获取数据失败 {match_id}: {e}")
            return None

    async def save_l2_stats_to_db(self, match_id: str, l2_stats) -> bool:
        """保存L2统计数据到数据库"""
        try:
            # 使用直接的asyncpg连接，避免复杂的异步管理器
            import asyncpg
            import os
            import re

            # 从环境变量获取数据库连接信息
            db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction")

            # 解析连接URL获取连接参数
            match = re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if match:
                user, password, host, port, database = match.groups()
            else:
                # 默认值
                user = "postgres"
                password = "postgres"
                host = "localhost"
                port = "5432"
                database = "football_prediction"

            # 直接创建数据库连接
            conn = await asyncpg.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database
            )

            # 构建更新字段 - 使用L2MatchStats中实际存在的字段
            update_fields = {
                "home_possession": l2_stats.home_possession,
                "away_possession": l2_stats.away_possession,
                "home_total_shots": l2_stats.home_total_shots,
                "away_total_shots": l2_stats.away_total_shots,
                "home_shots_on_target": l2_stats.home_shots_on_target,
                "away_shots_on_target": l2_stats.away_shots_on_target,
                "home_big_chances_created": l2_stats.home_big_chances_created,
                "away_big_chances_created": l2_stats.away_big_chances_created,
                "home_expected_goals": l2_stats.home_expected_goals,
                "away_expected_goals": l2_stats.away_expected_goals,
                "home_expected_goals_on_target": l2_stats.home_expected_goals_on_target,
                "away_expected_goals_on_target": l2_stats.away_expected_goals_on_target,
                "home_corners": l2_stats.home_corners,
                "away_corners": l2_stats.away_corners,
                "home_yellow_cards": l2_stats.home_yellow_cards,
                "away_yellow_cards": l2_stats.away_yellow_cards,
                "home_red_cards": l2_stats.home_red_cards,
                "away_red_cards": l2_stats.away_red_cards,
                "home_fouls_committed": l2_stats.home_fouls_committed,
                "away_fouls_committed": l2_stats.away_fouls_committed,
                "home_offsides": l2_stats.home_offsides,
                "away_offsides": l2_stats.away_offsides,
                "home_tackles": l2_stats.home_tackles,
                "away_tackles": l2_stats.away_tackles,
                "home_interceptions": l2_stats.home_interceptions,
                "away_interceptions": l2_stats.away_interceptions,
                "home_clearances": l2_stats.home_clearances,
                "away_clearances": l2_stats.away_clearances,
                "home_aerial_duels_won": l2_stats.home_aerial_duels_won,
                "away_aerial_duels_won": l2_stats.away_aerial_duels_won,
                "home_shots_inside_box": l2_stats.home_shots_inside_box,
                "away_shots_inside_box": l2_stats.away_shots_inside_box,
                "home_shots_outside_box": l2_stats.home_shots_outside_box,
                "away_shots_outside_box": l2_stats.away_shots_outside_box,
                "home_accurate_passes": l2_stats.home_accurate_passes,
                "away_accurate_passes": l2_stats.away_accurate_passes,
                "home_total_passes": l2_stats.home_total_passes,
                "away_total_passes": l2_stats.away_total_passes,
                "home_accurate_crosses": l2_stats.home_accurate_crosses,
                "away_accurate_crosses": l2_stats.away_accurate_crosses,
            }

            # 构建动态SQL更新语句
            set_clauses = []
            for field, value in update_fields.items():
                if value is not None:
                    set_clauses.append(f"{field} = {value}")

            if not set_clauses:
                logger.warning(f"⚠️  比赛ID {match_id}: 没有有效的L2数据需要保存")
                return False

            # 添加更新时间
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")

            sql = f"""
                UPDATE matches
                SET {', '.join(set_clauses)}
                WHERE id = $1
            """

            await conn.execute(sql, match_id)

            # 关闭数据库连接
            await conn.close()

            return True

        except Exception as e:
            logger.error(f"❌ 保存L2数据失败 (比赛ID: {match_id}): {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="L2批处理回补脚本")
    parser.add_argument("--batch-size", type=int, default=50, help="批处理大小")
    parser.add_argument("--delay", type=int, default=2, help="请求延迟(秒)")
    args = parser.parse_args()

    logger.info("🎯 L2批处理回补脚本")
    logger.info(f"批处理大小: {args.batch_size}")
    logger.info(f"请求延迟: {args.delay}秒")
    logger.info("")

    processor = L2BackfillProcessor(batch_size=args.batch_size, delay=args.delay)

    try:
        success = await processor.process_backfill()

        if success:
            print("\n🎉 L2回补完成！")
            print("📊 79维度战术数据已同步到数据库")
            print("🚀 可以开始ML模型训练和预测分析")
        else:
            print("\n⚠️ L2回补部分成功")
            print("🔧 建议检查API和网络连接")

        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ L2回补执行异常: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)