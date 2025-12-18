#!/usr/bin/env python3
"""
赔率数据集成脚本 - 工作演示版本
Odds Data Integration Script - Working Demo Version

演示如何将Titan007赔率数据集成到matches表中的完整流程。
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import random

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 数据库配置
DATABASE_URL = "sqlite:///data/football_prediction.db"


class MockTitanEuroCollector:
    """模拟的Titan欧赔收集器 - 演示用"""

    def __init__(self):
        self.initialized = True
        logger.info("MockTitanEuroCollector initialized (demo mode)")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def fetch_euro_odds(self, match_id: str, company_id: int) -> Optional[Dict[str, Any]]:
        """
        模拟获取欧赔数据

        Args:
            match_id: 比赛ID
            company_id: 博彩公司ID

        Returns:
            Dict: 模拟的赔率数据
        """
        # 模拟网络延迟
        await asyncio.sleep(0.1)

        # 基于match_id和company_id生成一致的模拟赔率
        random.seed(hash(f"{match_id}_{company_id}") % 1000000)

        # 生成合理的赔率范围
        home_win = round(random.uniform(1.5, 4.0), 2)
        draw = round(random.uniform(2.8, 4.5), 2)
        away_win = round(random.uniform(2.0, 6.0), 2)

        # 确保赔率合理性：主胜 < 平局 < 客胜（通常情况）
        if home_win > away_win:
            home_win, away_win = away_win, home_win

        return {
            'match_id': match_id,
            'company_id': company_id,
            'home_win': home_win,
            'draw': draw,
            'away_win': away_win,
            'source_company': self._get_company_name(company_id)
        }

    def _get_company_name(self, company_id: int) -> str:
        """获取公司名称"""
        company_names = {
            8: "Bet365",
            17: "Pinnacle",
            3: "William Hill"
        }
        return company_names.get(company_id, "Unknown")


import asyncio


class OddsDataIntegrator:
    """赔率数据集成器 - 适配器模式"""

    def __init__(self, demo_mode: bool = True):
        """
        初始化集成器

        Args:
            demo_mode: 是否使用演示模式（模拟数据）
        """
        self.demo_mode = demo_mode

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

        logger.info(f"OddsDataIntegrator initialized (demo_mode={demo_mode})")

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
        为单场比赛收集欧赔数据

        Args:
            match_id: 数据库中的比赛ID
            fotmob_id: FotMob比赛ID，用于Titan匹配

        Returns:
            Dict: 收集到的赔率数据
        """
        odds_data = {}

        # 常用博彩公司ID
        COMPANY_BET365 = 8  # Bet365
        COMPANY_PINNACLE = 17  # Pinnacle
        COMPANY_WILLIAM_HILL = 3  # William Hill

        try:
            # 使用模拟收集器或真实的Titan收集器
            if self.demo_mode:
                collector_class = MockTitanEuroCollector
            else:
                # 这里应该导入真实的收集器
                from src.collectors.titan.collectors import TitanEuroCollector
                collector_class = TitanEuroCollector

            async with collector_class() as collector:
                # 优先尝试 Pinnacle (专业投注者首选，数据质量高)
                try:
                    logger.debug(f"Fetching Pinnacle odds for fotmob_id: {fotmob_id}")
                    pinnacle_odds = await collector.fetch_euro_odds(fotmob_id, COMPANY_PINNACLE)
                    if pinnacle_odds and pinnacle_odds.get('home_win'):
                        odds_data.update({
                            'home_win_odds': pinnacle_odds['home_win'],
                            'draw_odds': pinnacle_odds['draw'],
                            'away_win_odds': pinnacle_odds['away_win'],
                            'source_company': 'Pinnacle'
                        })
                        logger.info(f"Successfully fetched Pinnacle odds for {fotmob_id}")
                        return odds_data
                except Exception as e:
                    logger.warning(f"Failed to fetch Pinnacle odds for {fotmob_id}: {e}")

                # 备选：Bet365 (市场占有率最高)
                try:
                    logger.debug(f"Fetching Bet365 odds for fotmob_id: {fotmob_id}")
                    bet365_odds = await collector.fetch_euro_odds(fotmob_id, COMPANY_BET365)
                    if bet365_odds and bet365_odds.get('home_win'):
                        odds_data.update({
                            'home_win_odds': bet365_odds['home_win'],
                            'draw_odds': bet365_odds['draw'],
                            'away_win_odds': bet365_odds['away_win'],
                            'source_company': 'Bet365'
                        })
                        logger.info(f"Successfully fetched Bet365 odds for {fotmob_id}")
                        return odds_data
                except Exception as e:
                    logger.warning(f"Failed to fetch Bet365 odds for {fotmob_id}: {e}")

                # 最后尝试：William Hill
                try:
                    logger.debug(f"Fetching William Hill odds for fotmob_id: {fotmob_id}")
                    wh_odds = await collector.fetch_euro_odds(fotmob_id, COMPANY_WILLIAM_HILL)
                    if wh_odds and wh_odds.get('home_win'):
                        odds_data.update({
                            'home_win_odds': wh_odds['home_win'],
                            'draw_odds': wh_odds['draw'],
                            'away_win_odds': wh_odds['away_win'],
                            'source_company': 'William Hill'
                        })
                        logger.info(f"Successfully fetched William Hill odds for {fotmob_id}")
                        return odds_data
                except Exception as e:
                    logger.warning(f"Failed to fetch William Hill odds for {fotmob_id}: {e}")

        except Exception as e:
            logger.error(f"Collector initialization failed for {fotmob_id}: {e}")

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
        mode_text = "DEMO MODE" if self.demo_mode else "PRODUCTION MODE"
        logger.info(f"Starting odds data collection ({mode_text})...")
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

                    # 安全延迟：模拟网络请求延迟
                    if i < len(matches) - 1:  # 最后一次不需要等待
                        if self.demo_mode:
                            await asyncio.sleep(0.2)  # 演示模式：快速
                        else:
                            time.sleep(2)  # 生产模式：真实延迟

                except Exception as e:
                    logger.error(f"Error processing match {i+1}: {e}")
                    self.stats['failed_updates'] += 1
                    self.stats['total_processed'] += 1

            # 最终统计
            elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds()
            success_rate = (self.stats['successful_updates'] / max(self.stats['total_processed'], 1)) * 100

            logger.info(
                f"Odds data collection completed! ({mode_text})\n"
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

    parser = argparse.ArgumentParser(description="赔率数据集成脚本 - Titan007适配器")
    parser.add_argument("--limit", "-l", type=int, help="限制处理比赛数量")
    parser.add_argument("--demo", "-d", action="store_true", help="使用演示模式（模拟数据）")
    parser.add_argument("--production", "-p", action="store_true", help="使用生产模式（真实API）")

    args = parser.parse_args()

    # 确定运行模式
    demo_mode = not args.production  # 默认为演示模式

    # 运行集成
    integrator = OddsDataIntegrator(demo_mode=demo_mode)

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
        print(f"   Mode: {'DEMO' if demo_mode else 'PRODUCTION'}")

    except KeyboardInterrupt:
        print("\n⏹️ Odds data collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Odds data collection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()