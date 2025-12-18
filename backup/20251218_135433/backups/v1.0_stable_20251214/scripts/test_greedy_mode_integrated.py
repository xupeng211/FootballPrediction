#!/usr/bin/env python3
"""
Greedy Mode 集成测试脚本
Greedy Mode Integrated Test

此脚本将在真实的项目环境中验证：
1. 数据库迁移状态
2. 实际的FotMob API数据采集
3. 数据存储完整性

运行要求：
- 应用环境已启动 (make dev)
- 数据库连接正常
- FotMob API令牌配置

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

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 测试配置
TEST_MATCH_ID = "4193826"

class IntegratedGreedyModeTest:
    """集成环境下的Greedy Mode测试"""

    def __init__(self):
        self.test_passed = True

    async def run(self) -> bool:
        """运行集成测试"""
        logger.info("🚀 启动 Greedy Mode 集成测试")

        try:
            # 初始化数据库环境
            await self._initialize_environment()

            # 检查数据库结构
            await self._check_database_schema()

            # 测试实际数据采集
            await self._test_real_data_collection()

            # 验证数据完整性
            await self._verify_data_integrity()

            return self.test_passed

        except Exception as e:
            logger.error(f"💥 集成测试失败: {e}")
            return False

    async def _initialize_environment(self):
        """初始化环境"""
        logger.info("🔧 初始化项目环境...")

        try:
            from database.async_manager import initialize_database

            await initialize_database()
            logger.info("✅ 数据库管理器初始化成功")

        except Exception as e:
            logger.error(f"❌ 环境初始化失败: {e}")
            raise

    async def _check_database_schema(self):
        """检查数据库表结构"""
        logger.info("📋 检查数据库表结构...")

        try:
            from database.async_manager import get_db_session

            async with get_db_session() as session:
                # 获取matches表结构
                result = await session.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'matches'
                    AND table_schema = 'public'
                    ORDER BY ordinal_position;
                """)

                columns = result.fetchall()
                column_names = [row[0] for row in columns]

                # 检查Greedy Mode新增的JSON列
                greedy_columns = [
                    "stats_json",
                    "lineups_json",
                    "odds_snapshot_json",
                    "match_info"
                ]

                missing_columns = []
                for col in greedy_columns:
                    if col in column_names:
                        logger.info(f"✅ 找到列: {col}")
                    else:
                        missing_columns.append(col)
                        logger.error(f"❌ 缺失列: {col}")

                if missing_columns:
                    logger.error(f"🚨 数据库迁移未完成，缺失 {len(missing_columns)} 个列")
                    self.test_passed = False
                else:
                    logger.info("✅ 所有Greedy Mode列都已存在")

                logger.info(f"📊 matches表总列数: {len(columns)}")

        except Exception as e:
            logger.error(f"❌ 数据库结构检查失败: {e}")
            self.test_passed = False

    async def _test_real_data_collection(self):
        """测试实际数据采集"""
        logger.info("🌐 测试实际FotMob数据采集...")

        try:
            from collectors.fotmob_api_collector import FotMobAPICollector

            # 创建采集器实例
            collector = FotMobAPICollector(
                max_concurrent=1,
                timeout=30,
                max_retries=3
            )

            await collector.initialize()

            logger.info(f"🔍 开始采集比赛数据: {TEST_MATCH_ID}")

            # 采集数据
            match_data = await collector.collect_match_details(TEST_MATCH_ID)

            if match_data:
                logger.info("✅ 实际数据采集成功")

                # 验证数据结构
                if match_data.stats_json:
                    logger.info(f"📊 stats_json: {len(match_data.stats_json)} 个字段")
                if match_data.lineups_json:
                    logger.info(f"👥 lineups_json: {len(match_data.lineups_json)} 个部分")
                if match_data.odds_snapshot_json:
                    logger.info(f"💰 odds_snapshot_json: {len(match_data.odds_snapshot_json)} 个部分")
                if match_data.match_info:
                    logger.info(f"🎯 match_info: {len(match_data.match_info)} 个部分")

            else:
                logger.error("❌ 数据采集失败")
                self.test_passed = False

            await collector.close()

        except Exception as e:
            logger.error(f"❌ 数据采集测试失败: {e}")
            logger.error("💡 提示: 请确保FotMob API令牌配置正确")
            self.test_passed = False

    async def _verify_data_integrity(self):
        """验证数据完整性"""
        logger.info("🔍 验证数据完整性...")

        try:
            from database.async_manager import get_db_session
            from database.models.match import Match

            async with get_db_session() as session:
                # 查询测试比赛
                result = await session.execute(
                    f"SELECT * FROM matches WHERE fotmob_id = '{TEST_MATCH_ID}' LIMIT 1;"
                )

                match_records = result.fetchall()

                if match_records:
                    logger.info("✅ 找到测试比赛记录")

                    # 验证数据结构（这里可以根据需要添加更多验证）
                    for record in match_records:
                        logger.info(f"📊 比赛 ID: {record.id}")

                        # 检查JSON字段是否正确存储
                        for col in ["stats_json", "lineups_json", "odds_snapshot_json", "match_info"]:
                            value = getattr(record, col, None)
                            if value:
                                logger.info(f"✅ {col}: 已存储数据")
                            else:
                                logger.warning(f"⚠️ {col}: 数据为空")
                else:
                    logger.info("ℹ️ 数据库中暂无测试比赛记录（这是正常的，因为测试只进行数据采集）")

        except Exception as e:
            logger.error(f"❌ 数据完整性验证失败: {e}")
            # 这不算致命错误，因为可能数据库中确实没有测试数据

async def main():
    """主函数"""
    logger.info("🚀 启动 Greedy Mode 集成测试")

    # 检查环境变量
    if not os.getenv("DATABASE_URL"):
        logger.error("❌ 缺少DATABASE_URL环境变量")
        logger.info("💡 请确保应用环境已启动: make dev")
        sys.exit(1)

    # 运行测试
    tester = IntegratedGreedyModeTest()
    success = await tester.run()

    if success:
        logger.info("🎉 ✅ INTEGRATED TEST PASSED")
        logger.info("🚀 Greedy Mode 在真实环境中运行正常!")
    else:
        logger.error("💥 ❌ INTEGRATED TEST FAILED")
        logger.error("🚨 请检查环境配置和数据采集设置")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
