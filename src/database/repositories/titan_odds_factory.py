"""
Titan007 赔率数据库工厂
Titan007 Odds Database Factory

提供便捷的数据库操作接口，用于替换集成脚本中的 MockRepository。
Provides convenient database operations interface to replace MockRepository in integration scripts.
"""

import logging

from src.database.repositories.odds_repository import TitanOddsRepository
from src.schemas.titan import (
    EuroOddsRecord,
    AsianHandicapRecord,
    OverUnderRecord,
)

logger = logging.getLogger(__name__)


class RealTitanOddsRepository:
    """
    真实的 Titan 赔率数据库仓库

    这个类提供了与 MockRepository 相同的接口，但使用真实的数据库存储。
    This class provides the same interface as MockRepository but uses real database storage.
    """

    def __init__(self):
        """初始化仓库"""
        self.repository = TitanOddsRepository()

    async def save_euro_odds(self, dto: EuroOddsRecord) -> bool:
        """
        保存欧赔数据

        Args:
            dto: 欧赔数据传输对象

        Returns:
            bool: 保存是否成功
        """
        try:
            await self.repository.upsert_euro_odds(dto)
            logger.info(
                f"💾 [RealDB] 欧赔数据已入库: 公司={dto.companyname}, 主胜={dto.homeodds}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ [RealDB] 欧赔数据保存失败: {e}")
            return False

    async def save_asian_odds(self, dto: AsianHandicapRecord) -> bool:
        """
        保存亚盘数据

        Args:
            dto: 亚盘数据传输对象

        Returns:
            bool: 保存是否成功
        """
        try:
            await self.repository.upsert_asian_odds(dto)
            logger.info(
                f"💾 [RealDB] 亚盘数据已入库: 公司={dto.companyname}, 盘口={dto.handicap}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ [RealDB] 亚盘数据保存失败: {e}")
            return False

    async def save_overunder_odds(self, dto: OverUnderRecord) -> bool:
        """
        保存大小球数据

        Args:
            dto: 大小球数据传输对象

        Returns:
            bool: 保存是否成功
        """
        try:
            await self.repository.upsert_overunder_odds(dto)
            logger.info(
                f"💾 [RealDB] 大小球数据已入库: 公司={dto.companyname}, 盘口={dto.handicap}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ [RealDB] 大小球数据保存失败: {e}")
            return False

    # 可选：添加查询方法用于验证
    async def verify_euro_odds_saved(self, match_id: str, company_id: int) -> bool:
        """验证欧赔数据是否已保存"""
        odds = await self.repository.get_euro_odds(match_id, company_id)
        return odds is not None

    async def verify_asian_odds_saved(self, match_id: str, company_id: int) -> bool:
        """验证亚盘数据是否已保存"""
        odds = await self.repository.get_asian_odds(match_id, company_id)
        return odds is not None

    async def verify_overunder_odds_saved(self, match_id: str, company_id: int) -> bool:
        """验证大小球数据是否已保存"""
        odds = await self.repository.get_overunder_odds(match_id, company_id)
        return odds is not None


# 导出
__all__ = [
    "RealTitanOddsRepository",
]
