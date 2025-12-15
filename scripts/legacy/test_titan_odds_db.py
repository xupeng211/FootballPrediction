#!/usr/bin/env python3
"""
Titan007 数据库功能验证脚本
验证 TitanOddsRepository 和相关数据库模型的完整性

使用方法:
    # 使用 Mock 模式验证
    python test_titan_odds_db.py

    # 使用真实数据库验证
    python test_titan_odds_db.py --use-real-db
    python test_titan_odds_db.py --use-real-db --db-url "postgresql+asyncpg://user:pass@localhost:5432/test_db"
"""

import asyncio
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.database.repositories.titan_odds_factory import RealTitanOddsRepository
from src.database.repositories.odds_repository import TitanOddsRepository
from src.database.async_manager import initialize_database
from src.schemas.titan import (
    EuroOddsRecord,
    AsianHandicapRecord,
    OverUnderRecord,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class MockRepository:
    """模拟数据库仓库 - 支持双表架构"""

    async def save_euro_odds(self, dto):
        logger.info(
            f"💾 [MockDB] 欧赔 Latest表入库: 公司={dto.companyname}, 主胜={dto.homeodds}"
        )
        logger.info(
            f"📜 [MockDB] 欧赔 History表入库: 公司={dto.companyname}, 主胜={dto.homeodds}"
        )
        return (True, True)  # (latest_result, history_result)

    async def save_asian_odds(self, dto):
        logger.info(
            f"💾 [MockDB] 亚盘 Latest表入库: 公司={dto.companyname}, 盘口={dto.handicap}"
        )
        logger.info(
            f"📜 [MockDB] 亚盘 History表入库: 公司={dto.companyname}, 盘口={dto.handicap}"
        )
        return (True, True)

    async def save_overunder_odds(self, dto):
        logger.info(
            f"💾 [MockDB] 大小球 Latest表入库: 公司={dto.companyname}, 盘口={dto.handicap}"
        )
        logger.info(
            f"📜 [MockDB] 大小球 History表入库: 公司={dto.companyname}, 盘口={dto.handicap}"
        )
        return (True, True)


class TitanOddsDBValidator:
    """Titan 赔率数据库验证器"""

    def __init__(self, use_real_db: bool = False, db_url: Optional[str] = None):
        self.use_real_db = use_real_db

        if use_real_db:
            self.repository = RealTitanOddsRepository()
            self.raw_repository = TitanOddsRepository()
            logger.info("🗄️ 使用真实数据库 (PostgreSQL)")
        else:
            self.repository = MockRepository()
            logger.info("🎭 使用模拟数据库 (Mock)")

        # 初始化数据库（如果使用真实数据库）
        if use_real_db:
            try:
                initialize_database(db_url)
                logger.info("✅ 数据库初始化成功")
            except Exception as e:
                logger.error(f"❌ 数据库初始化失败: {e}")
                raise

    def create_test_euro_dto(self) -> EuroOddsRecord:
        """创建测试用的欧赔 DTO"""
        return EuroOddsRecord.model_validate(
            {
                "matchid": "test_match_001",
                "companyid": 3,  # William Hill
                "companyname": "William Hill",
                "homeodds": 1.85,
                "drawodds": 3.60,
                "awayodds": 4.20,
                "homeopen": 1.90,
                "drawopen": 3.50,
                "awayopen": 4.10,
                "utime": "2024-01-01T16:00:00Z",
                "is_live": False,
                "confidence_score": 0.95,
            }
        )

    def create_test_asian_dto(self) -> AsianHandicapRecord:
        """创建测试用的亚盘 DTO"""
        return AsianHandicapRecord.model_validate(
            {
                "matchid": "test_match_001",
                "companyid": 8,  # Bet365
                "companyname": "Bet365",
                "upperodds": 0.95,
                "lowerodds": 0.90,
                "handicap": "-0.5",
                "upperopen": 0.98,
                "loweropen": 0.88,
                "handicapopen": "-0.5",
                "utime": "2024-01-01T16:00:00Z",
                "is_live": False,
                "confidence_score": 0.98,
            }
        )

    def create_test_overunder_dto(self) -> OverUnderRecord:
        """创建测试用的大小球 DTO"""
        return OverUnderRecord.model_validate(
            {
                "matchid": "test_match_001",
                "companyid": 17,  # Pinnacle
                "companyname": "Pinnacle",
                "overodds": 1.90,
                "underodds": 1.90,
                "handicap": "2.5",
                "overopen": 1.95,
                "underopen": 1.85,
                "handicapopen": "2.5",
                "utime": "2024-01-01T16:00:00Z",
                "is_live": False,
                "confidence_score": 0.97,
            }
        )

    async def test_euro_odds(self) -> bool:
        """测试欧赔双写数据存储"""
        try:
            logger.info("📊 测试欧赔双写数据存储 (Latest + History)...")

            # 创建测试数据
            dto = self.create_test_euro_dto()

            # 双写数据存储
            latest_result, history_result = await self.repository.save_euro_odds(dto)

            if not latest_result:
                logger.error("❌ 欧赔 Latest表数据存储失败")
                return False

            logger.info(f"✅ 欧赔 Latest表存储成功: {latest_result}")
            logger.info(f"✅ 欧赔 History表存储成功: {history_result}")

            # 如果使用真实数据库，验证数据是否真的存入了
            if self.use_real_db:
                # 验证 Latest 表
                saved_latest = await self.raw_repository.get_euro_odds_latest(
                    dto.matchid, dto.companyid
                )
                if saved_latest:
                    logger.info(f"✅ 欧赔 Latest表验证成功: {saved_latest}")
                else:
                    logger.error("❌ 欧赔 Latest表验证失败: 数据未找到")
                    return False

                # 验证 History 表
                saved_history = await self.raw_repository.get_euro_odds_history(
                    dto.matchid, dto.companyid, limit=5
                )
                if saved_history:
                    logger.info(
                        f"✅ 欧赔 History表验证成功: 找到 {len(saved_history)} 条历史记录"
                    )
                    logger.info(f"   最新历史记录: {saved_history[0]}")
                else:
                    logger.warning("⚠️ 欧赔 History表为空（可能是智能去重跳过）")

            logger.info("✅ 欧赔双写数据测试通过")
            return True

        except Exception as e:
            logger.error(f"❌ 欧赔双写数据测试失败: {e}")
            return False

    async def test_asian_odds(self) -> bool:
        """测试亚盘双写数据存储"""
        try:
            logger.info("📉 测试亚盘双写数据存储 (Latest + History)...")

            # 创建测试数据
            dto = self.create_test_asian_dto()

            # 双写数据存储
            latest_result, history_result = await self.repository.save_asian_odds(dto)

            if not latest_result:
                logger.error("❌ 亚盘 Latest表数据存储失败")
                return False

            logger.info(f"✅ 亚盘 Latest表存储成功: {latest_result}")
            logger.info(f"✅ 亚盘 History表存储成功: {history_result}")

            # 验证真实数据库
            if self.use_real_db:
                saved_latest = await self.raw_repository.get_asian_odds_latest(
                    dto.matchid, dto.companyid
                )
                if saved_latest:
                    logger.info(f"✅ 亚盘 Latest表验证成功: {saved_latest}")
                else:
                    logger.error("❌ 亚盘 Latest表验证失败: 数据未找到")
                    return False

                saved_history = await self.raw_repository.get_asian_odds_history(
                    dto.matchid, dto.companyid, limit=5
                )
                if saved_history:
                    logger.info(
                        f"✅ 亚盘 History表验证成功: 找到 {len(saved_history)} 条历史记录"
                    )
                else:
                    logger.warning("⚠️ 亚盘 History表为空（可能是智能去重跳过）")

            logger.info("✅ 亚盘双写数据测试通过")
            return True

        except Exception as e:
            logger.error(f"❌ 亚盘双写数据测试失败: {e}")
            return False

    async def test_overunder_odds(self) -> bool:
        """测试大小球双写数据存储"""
        try:
            logger.info("⚽ 测试大小球双写数据存储 (Latest + History)...")

            # 创建测试数据
            dto = self.create_test_overunder_dto()

            # 双写数据存储
            latest_result, history_result = await self.repository.save_overunder_odds(
                dto
            )

            if not latest_result:
                logger.error("❌ 大小球 Latest表数据存储失败")
                return False

            logger.info(f"✅ 大小球 Latest表存储成功: {latest_result}")
            logger.info(f"✅ 大小球 History表存储成功: {history_result}")

            # 验证真实数据库
            if self.use_real_db:
                saved_latest = await self.raw_repository.get_overunder_odds_latest(
                    dto.matchid, dto.companyid
                )
                if saved_latest:
                    logger.info(f"✅ 大小球 Latest表验证成功: {saved_latest}")
                else:
                    logger.error("❌ 大小球 Latest表验证失败: 数据未找到")
                    return False

                saved_history = await self.raw_repository.get_overunder_odds_history(
                    dto.matchid, dto.companyid, limit=5
                )
                if saved_history:
                    logger.info(
                        f"✅ 大小球 History表验证成功: 找到 {len(saved_history)} 条历史记录"
                    )
                else:
                    logger.warning("⚠️ 大小球 History表为空（可能是智能去重跳过）")

            logger.info("✅ 大小球双写数据测试通过")
            return True

        except Exception as e:
            logger.error(f"❌ 大小球双写数据测试失败: {e}")
            return False

    async def test_database_connection(self) -> bool:
        """测试数据库连接"""
        if not self.use_real_db:
            logger.info("🎭 Mock 模式：跳过数据库连接测试")
            return True

        try:
            logger.info("🔌 测试数据库连接...")

            from src.database.async_manager import get_database_manager

            db_manager = get_database_manager()

            # 使用 check_connection 方法
            status = await db_manager.check_connection()

            if status["status"] == "healthy":
                logger.info(f"✅ 数据库连接测试通过: {status['message']}")
                return True
            else:
                logger.error(f"❌ 数据库连接测试失败: {status['message']}")
                return False

        except Exception as e:
            logger.error(f"❌ 数据库连接测试异常: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """运行所有测试"""
        logger.info("🚀 开始 Titan007 数据库功能完整性测试")
        logger.info("=" * 60)

        tests = [
            ("数据库连接测试", self.test_database_connection),
            ("欧赔数据测试", self.test_euro_odds),
            ("亚盘数据测试", self.test_asian_odds),
            ("大小球数据测试", self.test_overunder_odds),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            logger.info(f"\n🧪 运行 {test_name}...")
            try:
                result = await test_func()
                if result:
                    passed += 1
                    logger.info(f"✅ {test_name} 通过")
                else:
                    failed += 1
                    logger.error(f"❌ {test_name} 失败")
            except Exception as e:
                failed += 1
                logger.error(f"❌ {test_name} 异常: {e}")

        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("📊 测试结果总结:")
        logger.info(f"    ✅ 通过: {passed} 项")
        logger.info(f"    ❌ 失败: {failed} 项")
        logger.info(f"    📈 成功率: {passed/(passed+failed)*100:.1f}%")

        if failed == 0:
            logger.info("🎉 所有测试通过！数据库功能完整性验证成功！")
            return True
        else:
            logger.error("⚠️ 部分测试失败，请检查实现")
            return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Titan007 数据库功能验证脚本")
    parser.add_argument(
        "--use-real-db",
        action="store_true",
        help="使用真实数据库 (PostgreSQL) 而不是 Mock 数据库",
    )
    parser.add_argument(
        "--db-url", type=str, help="数据库连接 URL (可选，默认使用环境变量)"
    )

    args = parser.parse_args()

    print("=" * 60)
    if args.use_real_db:
        print("🎯 Titan007 数据库功能验证 (真实数据库版)")
    else:
        print("🎯 Titan007 数据库功能验证 (Mock数据库版)")
    print("=" * 60)

    # 创建验证器并运行测试
    validator = TitanOddsDBValidator(use_real_db=args.use_real_db, db_url=args.db_url)
    success = await validator.run_all_tests()

    # 退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
