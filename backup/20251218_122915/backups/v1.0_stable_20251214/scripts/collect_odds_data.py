#!/usr/bin/env python3
"""
赔率数据集成脚本 - Titan007 适配器 (修复版)
Odds Data Integration Script - Titan007 Adapter (Fixed Version)

复用现有的 Titan 收集器，将赔率数据集成到 matches 表中。
修复了 RateLimiter 初始化问题。
"""

import sys
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入Titan收集器
from src.collectors.titan.collectors import TitanEuroCollector

# 数据库配置
DATABASE_URL = "sqlite:///data/football_prediction.db"

# 常用博彩公司ID (基于枚举定义)
COMPANY_COMPANY = None  # 让Titan使用默认公司
COMPANY_COMPANY_ID = None


class OddsDataIntegrator:
    """赔率数据集成器 - 适配器模式 (修复版)"""

    def __init__(self):
        """初始化集成器"""
        # 数据库连接
        self._engine = create_engine(DATABASE_URL)
        self._SessionLocal = sessionmaker(bind=self._engine)

        # 统计信息
        self.stats = {
            'total_processed': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'start_time': datetime.now()
        }

        logger.info("OddsDataIntegrator initialized (Fixed Version)")

    def get_matches_without_odds(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取没有赔率数据的比赛

        Args:
            limit: 限制处理数量，用于测试

        Returns:
            List[Dict]: 比赛信息列表
        """
        logger.info("Fetching matches without odds data...")

        with self._SessionLocal() as session:
            query = text("""
                SELECT
                    m.id,
                    m.fotmob_id,
                    t1.name as home_team_name,
                    t2.name as away_team_name,
                    m.match_date,
                    m.status
                FROM matches m
                JOIN teams t1 ON m.home_team_id = t1.id
                JOIN teams t2 ON m.away_team_id = t2.id
                WHERE m.fotmob_id IS NOT NULL
                  AND m.home_win_odds IS NULL
                ORDER BY m.match_date DESC
                LIMIT :limit
            """)

            params = {"limit": limit if limit else 1000}
            result = session.execute(query, params).fetchall()

            matches = []
            for row in result:
                matches.append({
                    'id': row[0],
                    'fotmob_id': row[1],
                    'home_team': row[2],
                    'away_team': row[3],
                    'match_date': row[4],
                    'status': row[5]
                })

            logger.info(f"Found {len(matches)} matches without odds data")
            return matches

    async def collect_euro_odds_for_match(self, match_id: str, fotmob_id: str) -> Dict[str, Any]:
        """
        为单场比赛收集欧赔数据 (修复版)

        Args:
            match_id: 数据库中的比赛ID
            fotmob_id: FotMob比赛ID，用于Titan匹配

        Returns:
            Dict: 收集到的赔率数据
        """
        odds_data = {}
        collector = None

        try:
            # 完全无参初始化，让Titan使用其内部默认配置
            logger.debug(f"Initializing TitanEuroCollector for fotmob_id: {fotmob_id}")
            collector = TitanEuroCollector()

            # 尝试获取任意可用的赔率数据，不指定特定公司
            try:
                logger.debug(f"Fetching Euro odds for fotmob_id: {fotmob_id}")

                # 传入参数确保是字符串类型
                fotmob_id_str = str(fotmob_id)

                # 调用fetch_euro_odds，不指定公司ID让它使用默认的
                odds_result = await collector.fetch_euro_odds(fotmob_id_str)

                logger.debug(f"TitanEuroCollector result: {odds_result}")

                if odds_result and odds_result.get('home_win'):
                    odds_data.update({
                        'home_win_odds': odds_result.get('home_win'),
                        'draw_odds': odds_result.get('draw'),
                        'away_win_odds': odds_result.get('away_win'),
                        'source_company': odds_result.get('company_name', 'Titan')
                    })
                    logger.info(f"Successfully fetched Euro odds for {fotmob_id}")
                    return odds_data
                else:
                    logger.warning(f"No valid odds data returned for {fotmob_id}")

            except Exception as e:
                logger.warning(f"Failed to fetch Euro odds for {fotmob_id}: {e}")

        except Exception as e:
            logger.error(f"TitanEuroCollector initialization failed for {fotmob_id}: {e}")
            logger.exception(f"Full error details: {type(e).__name__}: {str(e)}")

        finally:
            # 显式关闭收集器
            if collector:
                try:
                    await collector.close()
                    logger.debug(f"Successfully closed TitanEuroCollector for {fotmob_id}")
                except Exception as e:
                    logger.warning(f"Error closing TitanEuroCollector for {fotmob_id}: {e}")

        return odds_data

    def update_odds_in_database(self, match_id: int, odds_data: Dict[str, Any]) -> bool:
        """
        更新数据库中的赔率数据

        Args:
            match_id: 数据库中的比赛ID
            odds_data: 赔率数据

        Returns:
            bool: 更新是否成功
        """
        if not odds_data or 'home_win_odds' not in odds_data:
            logger.warning(f"No valid odds data to update for match_id: {match_id}")
            return False

        try:
            with self._SessionLocal() as session:
                update_query = text("""
                    UPDATE matches
                    SET home_win_odds = :home_win_odds,
                        draw_odds = :draw_odds,
                        away_win_odds = :away_win_odds,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :match_id
                """)

                params = {
                    'home_win_odds': odds_data.get('home_win_odds'),
                    'draw_odds': odds_data.get('draw_odds'),
                    'away_win_odds': odds_data.get('away_win_odds'),
                    'match_id': match_id
                }

                result = session.execute(update_query, params)
                session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"Updated odds for match_id {match_id}: "
                        f"{odds_data.get('home_win_odds')}-{odds_data.get('draw_odds')}-{odds_data.get('away_win_odds')} "
                        f"(source: {odds_data.get('source_company', 'Unknown')})"
                    )
                    return True
                else:
                    logger.warning(f"No rows updated for match_id: {match_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to update odds in database for match_id {match_id}: {e}")
            return False

    async def process_match(self, match_info: Dict[str, Any]) -> bool:
        """
        处理单场比赛的赔率数据收集

        Args:
            match_info: 比赛信息

        Returns:
            bool: 处理是否成功
        """
        match_id = match_info['id']
        fotmob_id = match_info['fotmob_id']
        home_team = match_info['home_team']
        away_team = match_info['away_team']

        logger.info(f"Processing odds for match: {home_team} vs {away_team} (fotmob_id: {fotmob_id})")

        try:
            # 收集赔率数据
            odds_data = await self.collect_euro_odds_for_match(str(match_id), fotmob_id)

            if not odds_data:
                logger.warning(f"No odds data collected for match {fotmob_id}")
                return False

            # 更新数据库
            success = self.update_odds_in_database(match_id, odds_data)

            return success

        except Exception as e:
            logger.error(f"Error processing match {fotmob_id}: {e}")
            return False

    async def run_collection(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        运行赔率数据收集主流程

        Args:
            limit: 限制处理数量，用于测试

        Returns:
            Dict: 收集统计信息
        """
        logger.info("Starting odds data collection...")
        self.stats['start_time'] = datetime.now()

        try:
            # 获取需要处理的比赛
            matches = self.get_matches_without_odds(limit)
            if not matches:
                logger.info("No matches need odds data processing")
                return self.stats

            logger.info(f"Processing {len(matches)} matches for odds data")

            # 处理每场比赛
            for i, match_info in enumerate(matches):
                try:
                    success = await self.process_match(match_info)
                    self.stats['total_processed'] += 1

                    if success:
                        self.stats['successful_updates'] += 1
                        logger.debug(f"Success {i+1}/{len(matches)}")
                    else:
                        self.stats['failed_updates'] += 1
                        logger.warning(f"Failed {i+1}/{len(matches)}")

                    # 定期记录进度
                    if self.stats['total_processed'] % 5 == 0:
                        logger.info(f"Progress: {self.stats['total_processed']}/{len(matches)}")

                    # 安全延迟：每次请求后等待2秒，防止被封
                    if i < len(matches) - 1:  # 最后一次不需要等待
                        logger.debug("Waiting 2 seconds before next request...")
                        time.sleep(2)

                except Exception as e:
                    logger.error(f"Error processing match {i+1}: {e}")
                    self.stats['failed_updates'] += 1
                    self.stats['total_processed'] += 1

            # 最终统计
            elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds()
            success_rate = (self.stats['successful_updates'] / max(self.stats['total_processed'], 1)) * 100

            logger.info(
                f"Odds data collection completed!\n"
                f"Statistics:\n"
                f"  Total processed: {self.stats['total_processed']}\n"
                f"  Successful: {self.stats['successful_updates']}\n"
                f"  Failed: {self.stats['failed_updates']}\n"
                f"  Success rate: {success_rate:.2f}%\n"
                f"  Elapsed time: {elapsed_time:.2f} seconds"
            )

            return self.stats

        except Exception as e:
            logger.error(f"Fatal error in odds collection process: {e}")
            raise


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="赔率数据集成脚本 - Titan007适配器 (修复版)")
    parser.add_argument("--limit", "-l", type=int, help="限制处理比赛数量")
    parser.add_argument("--dry-run", "-d", action="store_true", help="只记录不实际写入数据库")

    args = parser.parse_args()

    # 运行集成
    integrator = OddsDataIntegrator()

    try:
        # 使用 asyncio.run 运行异步主流程
        stats = asyncio.run(integrator.run_collection(args.limit))
        print("\n🎉 Odds data collection completed!")
        print("📊 Statistics:")
        print(f"   Total processed: {stats['total_processed']}")
        print(f"   Successful: {stats['successful_updates']}")
        print(f"   Failed: {stats['failed_updates']}")
        print(f"   Success rate: {(stats['successful_updates'] / max(stats['total_processed'], 1) * 100):.2f}%")
        print(f"   Elapsed time: {(datetime.now() - stats['start_time']).total_seconds():.2f} seconds")

    except KeyboardInterrupt:
        print("\n⏹️ Odds data collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Odds data collection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()