#!/usr/bin/env python3
"""
Greedy Mode 冒烟测试脚本
Greedy Mode Smoke Test

此脚本用于验证：
1. 数据库结构是否已正确同步（新增的JSON列）
2. Greedy Mode数据采集是否正常工作
3. xG、阵容、战意等高价值数据是否成功提取

作者: QA Engineer & DBA
版本: 1.0.0
日期: 2025-01-08
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入项目模块（直接导入以避免循环导入问题）
from database.async_manager import get_db_session, initialize_database
from src.collectors.fotmob_api_collector import FotMobAPICollector, MatchDetailData

# 测试配置
TEST_MATCH_ID = "4193826"  # 推荐的近期英超比赛ID
EXPECTED_JSON_COLUMNS = [
    "stats_json",
    "lineups_json",
    "odds_snapshot_json",
    "match_info"
]

# 数据库连接配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/football_prediction"
)

class GreedyModeSmokeTest:
    """Greedy Mode 冒烟测试类"""

    def __init__(self):
        self.test_passed = True
        self.test_results = {
            "schema_check": False,
            "data_fetch": False,
            "validation": {
                "stats_json": False,
                "lineups_json": False,
                "odds_snapshot_json": False,
                "match_info": False
            }
        }

    async def run(self) -> bool:
        """运行完整的冒烟测试"""
        logger.info("🚀 启动 Greedy Mode 冒烟测试")
        logger.info(f"📊 测试Match ID: {TEST_MATCH_ID}")
        logger.info(f"🗄️ 数据库URL: {DATABASE_URL.split('@')[-1]}")  # 只显示主机部分

        try:
            # 步骤1: 数据库迁移检查
            logger.info("\n" + "="*50)
            logger.info("📋 步骤1: 数据库迁移检查")
            logger.info("="*50)
            await self._check_database_schema()

            # 步骤2: 真实数据抓取测试
            logger.info("\n" + "="*50)
            logger.info("🔍 步骤2: 真实数据抓取测试")
            logger.info("="*50)
            match_data = await self._test_data_fetching()

            if match_data:
                # 步骤3: 验证和打印
                logger.info("\n" + "="*50)
                logger.info("✅ 步骤3: 验证和打印结果")
                logger.info("="*50)
                await self._validate_and_print_results(match_data)

            # 最终结果
            logger.info("\n" + "="*50)
            logger.info("🏁 测试结果汇总")
            logger.info("="*50)
            self._print_final_results()

            return self.test_passed

        except Exception as e:
            logger.error(f"💥 测试过程中发生异常: {e}")
            logger.error("❌ SMOKE TEST FAILED")
            return False

    async def _check_database_schema(self):
        """检查数据库表结构是否包含新增的JSON列"""
        try:
            await initialize_database()

            async with get_db_session() as session:
                # 获取表结构信息
                result = await session.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'matches'
                    AND table_schema = 'public'
                    ORDER BY ordinal_position;
                """)

                columns = result.fetchall()
                existing_columns = [row[0] for row in columns]

                logger.info(f"📊 'matches' 表总列数: {len(columns)}")

                # 检查必需的JSON列是否存在
                missing_columns = []
                for col in EXPECTED_JSON_COLUMNS:
                    if col in existing_columns:
                        logger.info(f"✅ 找到列: {col}")
                    else:
                        missing_columns.append(col)
                        logger.warning(f"❌ 缺失列: {col}")

                # 如果有缺失的列，执行迁移
                if missing_columns:
                    logger.info(f"🔧 需要添加 {len(missing_columns)} 个缺失的列")
                    await self._add_missing_columns(missing_columns)

                self.test_results["schema_check"] = len(missing_columns) == 0

        except Exception as e:
            logger.error(f"❌ 数据库结构检查失败: {e}")
            self.test_results["schema_check"] = False

    async def _add_missing_columns(self, missing_columns: list[str]):
        """动态添加缺失的列"""
        try:
            async with get_db_session() as session:
                # 判断数据库类型
                await session.execute("SELECT current_database();")
                db_type = "postgresql"  # 默认假设是PostgreSQL

                # 如果是SQLite，使用不同的SQL语法
                try:
                    await session.execute("PRAGMA table_info('matches');")
                    db_type = "sqlite"
                except:
                    pass  # 如果PRAGMA失败，继续使用PostgreSQL

                # 根据数据库类型构建ALTER语句
                alter_statements = []
                for col in missing_columns:
                    if db_type == "sqlite":
                        alter_statements.append(f"ALTER TABLE matches ADD COLUMN {col} JSON;")
                    else:  # PostgreSQL
                        alter_statements.append(f"ALTER TABLE matches ADD COLUMN {col} JSONB;")

                # 执行ALTER语句
                for statement in alter_statements:
                    logger.info(f"🔧 执行: {statement}")
                    await session.execute(text(statement))

                await session.commit()
                logger.info("✅ 数据库迁移完成")

        except Exception as e:
            logger.error(f"❌ 数据库迁移失败: {e}")
            raise

    async def _test_data_fetching(self) -> Optional[MatchDetailData]:
        """测试真实数据抓取"""
        try:
            # 初始化采集器
            collector = FotMobAPICollector(
                max_concurrent=1,
                timeout=30,
                max_retries=3
            )

            await collector.initialize()

            logger.info(f"🌐 开始抓取比赛数据: {TEST_MATCH_ID}")

            # 调用数据采集方法
            match_data = await collector.collect_match_details(TEST_MATCH_ID)

            if match_data:
                logger.info("✅ 数据抓取成功")
                self.test_results["data_fetch"] = True
            else:
                logger.error("❌ 数据抓取失败 - 返回None")
                self.test_results["data_fetch"] = False

            await collector.close()
            return match_data

        except Exception as e:
            logger.error(f"❌ 数据抓取异常: {e}")
            self.test_results["data_fetch"] = False
            return None

    async def _validate_and_print_results(self, match_data: MatchDetailData):
        """验证并打印测试结果"""
        try:
            # 验证stats_json
            if match_data.stats_json:
                stats_keys = list(match_data.stats_json.keys())
                logger.info(f"📊 stats_json 包含 {len(stats_keys)} 个字段")
                logger.info(f"   关键字段: xG={('xg' in stats_keys)}, possession={('possession' in stats_keys)}")

                # 检查具体的数据内容
                xg_data = match_data.stats_json.get("xg", {})
                if xg_data:
                    logger.info(f"   xG数据: {xg_data}")

                possession_data = match_data.stats_json.get("possession", {})
                if possession_data:
                    logger.info(f"   控球率数据: {possession_data}")

                self.test_results["validation"]["stats_json"] = True
            else:
                logger.warning("❌ stats_json 为空")
                self.test_results["validation"]["stats_json"] = False

            # 验证lineups_json
            if match_data.lineups_json:
                lineup_keys = list(match_data.lineups_json.keys())
                logger.info(f"👥 lineups_json 包含 {len(lineup_keys)} 个部分: {lineup_keys}")

                # 检查阵容完整性
                has_unavailable = 'unavailable' in match_data.lineups_json
                has_ratings = False

                # 检查首发阵容中是否包含评分
                home_starters = match_data.lineups_json.get("home_team", {}).get("starters", [])
                away_starters = match_data.lineups_json.get("away_team", {}).get("starters", [])

                if home_starters:
                    for starter in home_starters:
                        if isinstance(starter, dict) and 'rating' in starter:
                            has_ratings = True
                            break

                if away_starters:
                    for starter in away_starters:
                        if isinstance(starter, dict) and 'rating' in starter:
                            has_ratings = True
                            break

                logger.info(f"   包含伤停名单: {has_unavailable}")
                logger.info(f"   包含球员评分: {has_ratings}")

                self.test_results["validation"]["lineups_json"] = True
            else:
                logger.warning("❌ lineups_json 为空")
                self.test_results["validation"]["lineups_json"] = False

            # 验证odds_snapshot_json
            if match_data.odds_snapshot_json:
                odds_keys = list(match_data.odds_snapshot_json.keys())
                logger.info(f"💰 odds_snapshot_json 包含 {len(odds_keys)} 个部分: {odds_keys}")

                if 'snapshot_time' in match_data.odds_snapshot_json:
                    logger.info(f"   赔率快照时间: {match_data.odds_snapshot_json['snapshot_time']}")

                self.test_results["validation"]["odds_snapshot_json"] = True
            else:
                logger.warning("❌ odds_snapshot_json 为空")
                self.test_results["validation"]["odds_snapshot_json"] = False

            # 验证match_info
            if match_data.match_info:
                info_keys = list(match_data.match_info.keys())
                logger.info(f"🎯 match_info 包含 {len(info_keys)} 个部分: {info_keys}")

                has_league_table = 'league_table' in match_data.match_info
                has_round_info = 'round_info' in match_info

                logger.info(f"   包含赛前排名: {has_league_table}")
                logger.info(f"   包含轮次信息: {has_round_info}")

                if has_league_table:
                    league_table = match_data.match_info['league_table']
                    logger.info(f"   排名数据: {league_table}")

                self.test_results["validation"]["match_info"] = True
            else:
                logger.warning("❌ match_info 为空")
                self.test_results["validation"]["match_info"] = False

        except Exception as e:
            logger.error(f"❌ 结果验证异常: {e}")

    def _print_final_results(self):
        """打印最终测试结果"""
        logger.info(f"📋 数据库迁移检查: {'✅ 通过' if self.test_results['schema_check'] else '❌ 失败'}")
        logger.info(f"📋 数据抓取测试: {'✅ 通过' if self.test_results['data_fetch'] else '❌ 失败'}")

        validation_passed = all(self.test_results['validation'].values())
        logger.info(f"📋 数据验证测试: {'✅ 通过' if validation_passed else '❌ 失败'}")

        # 详细验证结果
        logger.info("\n📋 详细验证结果:")
        for field, passed in self.test_results['validation'].items():
            status = "✅" if passed else "❌"
            logger.info(f"   {field}: {status}")

        # 最终判断
        overall_passed = (
            self.test_results['schema_check'] and
            self.test_results['data_fetch'] and
            validation_passed
        )

        if overall_passed:
            logger.info("\n🎉 ✅ SMOKE TEST PASSED")
            logger.info("🚀 Greedy Mode 已准备就绪，可以开始大规模数据回填!")
        else:
            logger.error("\n💥 ❌ SMOKE TEST FAILED")
            logger.error("🚨 请检查上述失败的步骤后再继续")

        self.test_passed = overall_passed

async def main():
    """主函数"""
    logger.info("🚀 启动 Greedy Mode 冒烟测试工具")

    # 设置环境变量（如果未设置）
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = DATABASE_URL
        logger.info("🔧 设置默认数据库连接")

    # 运行测试
    tester = GreedyModeSmokeTest()
    success = await tester.run()

    if success:
        logger.info("✅ 冒烟测试任务完成!")
        sys.exit(0)
    else:
        logger.error("❌ 冒烟测试任务失败!")
        sys.exit(1)

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
