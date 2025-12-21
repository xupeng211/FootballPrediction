#!/usr/bin/env python3
"""
V3.4: 历史真实赔率提取脚本
Historic Real Odds Extraction Script

目的: 从 FotMob API 重新获取 567 场比赛的【开赛前真实赔率】，物理回填数据库
拒绝模拟赔率！只要真实市场数据！
"""

import asyncio
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import os
import sys
import time
from tenacity import retry, stop_after_attempt, wait_exponential

# 添加项目路径
sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
sys.path.append("src")

from src.api.fotmob_client import FotMobAPIClient
from src.config_unified import get_settings

# 配置日志
log_file = "/app/logs/extract_historic_odds.log" if os.getenv("DOCKER_ENV") else "logs/extract_historic_odds.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HistoricOddsExtractor:
    """V3.4 历史赔率提取器"""

    def __init__(self):
        self.settings = get_settings()
        self.db_config = {
            "host": self.settings.database.host,
            "port": self.settings.database.port,
            "database": self.settings.database.name,
            "user": self.settings.database.user,
            "password": self.settings.database.password.get_secret_value()
        }

        # 提取统计
        self.stats = {
            "total_matches": 0,
            "extracted_odds": 0,
            "failed_extractions": 0,
            "odds_sources": {}
        }

        logger.info("🎯 V3.4 历史赔率提取器初始化完成")
        logger.info(f"📊 数据库: {self.db_config['database']}@{self.db_config['host']}:{self.db_config['port']}")

    def get_all_matches(self) -> List[Tuple[str, str, str]]:
        """获取所有需要提取赔率的比赛

        Returns:
            List[Tuple[str, str, str]]: (external_id, home_team, away_team)
        """
        matches = []

        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            query = """
            SELECT external_id, home_team, away_team, match_time
            FROM match_features_training
            WHERE external_id IS NOT NULL
            ORDER BY match_time DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            for row in results:
                external_id, home_team, away_team, match_time = row
                matches.append((external_id, home_team, away_team))

            conn.close()

            logger.info(f"📋 获取到 {len(matches)} 场比赛需要提取赔率")
            self.stats["total_matches"] = len(matches)
            return matches

        except Exception as e:
            logger.error(f"❌ 获取比赛列表失败: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def extract_odds_for_match(self, match_id: str, fotmob_client: FotMobAPIClient) -> Optional[Dict[str, Any]]:
        """为单场比赛提取赔率

        Args:
            match_id: 比赛 ID
            fotmob_client: FotMob API 客户端

        Returns:
            Optional[Dict[str, Any]]: 赔率数据或 None
        """
        try:
            # 获取比赛详情
            match_data = await fotmob_client.get_match_details(match_id)

            if not match_data:
                logger.warning(f"⚠️ 无法获取比赛 {match_id} 的数据")
                return None

            # 使用 V3.3 新增的真实赔率提取功能
            odds_data = await fotmob_client.extract_betting_odds(match_data)

            if odds_data and odds_data.get("home_odds"):
                source = odds_data.get("bookmaker", "Unknown")
                self.stats["odds_sources"][source] = self.stats["odds_sources"].get(source, 0) + 1

                logger.info(f"✅ 成功提取 {match_id} 赔率: 主胜={odds_data['home_odds']}, 平局={odds_data['draw_odds']}, 客胜={odds_data['away_odds']}")

                return {
                    "external_id": match_id,
                    "home_opening_odds": odds_data.get("home_odds"),
                    "away_opening_odds": odds_data.get("away_odds"),
                    "draw_odds": odds_data.get("draw_odds"),
                    "home_current_odds": odds_data.get("home_odds"),  # 使用相同数据作为当前赔率
                    "away_current_odds": odds_data.get("away_odds"),
                    "draw_current_odds": odds_data.get("draw_odds"),
                    "odds_source": source,
                    "odds_extracted_at": odds_data.get("extracted_at"),
                    "raw_odds_data": json.dumps(odds_data)
                }
            else:
                logger.warning(f"⚠️ 比赛 {match_id} 无可用赔率数据")
                return None

        except Exception as e:
            logger.error(f"❌ 提取比赛 {match_id} 赔率失败: {e}")
            self.stats["failed_extractions"] += 1
            return None

    def update_odds_in_database(self, odds_data: Dict[str, Any]) -> bool:
        """将赔率数据更新到数据库

        Args:
            odds_data: 赔率数据

        Returns:
            bool: 更新是否成功
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # 更新赔率数据
            update_query = """
            UPDATE match_features_training
            SET
                home_opening_odds = %s,
                away_opening_odds = %s,
                draw_odds = %s,
                home_current_odds = %s,
                away_current_odds = %s,
                draw_current_odds = %s,
                raw_data = jsonb_set(
                    raw_data,
                    '{betting_odds}',
                    %s::jsonb,
                    true
                ),
                updated_at = NOW()
            WHERE external_id = %s
            """

            cursor.execute(update_query, (
                odds_data["home_opening_odds"],
                odds_data["away_opening_odds"],
                odds_data["draw_odds"],
                odds_data["home_current_odds"],
                odds_data["away_current_odds"],
                odds_data["draw_current_odds"],
                odds_data["raw_odds_data"],
                odds_data["external_id"]
            ))

            conn.commit()
            conn.close()

            self.stats["extracted_odds"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ 更新赔率数据到数据库失败: {e}")
            return False

    async def process_batch(self, matches: List[Tuple[str, str, str]], batch_size: int = 10) -> None:
        """批量处理比赛赔率提取

        Args:
            matches: 比赛列表
            batch_size: 批处理大小
        """
        processed = 0

        async with FotMobAPIClient() as fotmob_client:
            for i in range(0, len(matches), batch_size):
                batch = matches[i:i + batch_size]

                logger.info(f"🔄 处理批次 {i//batch_size + 1}/{(len(matches)-1)//batch_size + 1} ({len(batch)} 场比赛)")

                # 并发处理当前批次
                tasks = []
                for match_id, home_team, away_team in batch:
                    task = self.extract_odds_for_match(match_id, fotmob_client)
                    tasks.append(task)

                # 等待所有任务完成
                odds_results = await asyncio.gather(*tasks, return_exceptions=True)

                # 更新数据库
                for j, odds_data in enumerate(odds_results):
                    if isinstance(odds_data, Exception):
                        logger.error(f"❌ 比赛 {batch[j][0]} 处理异常: {odds_data}")
                        self.stats["failed_extractions"] += 1
                    elif odds_data:
                        if self.update_odds_in_database(odds_data):
                            logger.info(f"✅ 成功更新 {batch[j][0]} 赔率到数据库")
                        else:
                            logger.error(f"❌ 更新 {batch[j][0]} 赔率到数据库失败")

                processed += len(batch)
                logger.info(f"📊 进度: {processed}/{len(matches)} ({processed/len(matches)*100:.1f}%)")

                # 添加延迟避免 API 限流
                if i + batch_size < len(matches):
                    await asyncio.sleep(2)

    def generate_coverage_report(self) -> None:
        """生成覆盖率报告"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # 查询赔率覆盖率
            coverage_query = """
            SELECT
                COUNT(*) as total_matches,
                COUNT(home_opening_odds) as matches_with_odds,
                ROUND(COUNT(home_opening_odds)::numeric / COUNT(*) * 100, 2) as coverage_percentage
            FROM match_features_training
            """

            cursor.execute(coverage_query)
            result = cursor.fetchone()

            total, with_odds, coverage = result

            logger.info("🎯 V3.4 历史赔率提取完成报告")
            logger.info("="*60)
            logger.info(f"📊 总比赛数: {total}")
            logger.info(f"✅ 成功提取赔率: {with_odds}")
            logger.info(f"📈 覆盖率: {coverage}%")
            logger.info(f"❌ 提取失败: {self.stats['failed_extractions']}")
            logger.info("")
            logger.info("📊 赔率数据源统计:")
            for source, count in self.stats["odds_sources"].items():
                logger.info(f"   • {source}: {count} 场比赛")
            logger.info("="*60)

            if coverage >= 80.0:
                logger.info("🎉 V3.4 赔率覆盖率达标！可以开始真实赔率回测")
            elif coverage >= 50.0:
                logger.warning("⚠️ 赔率覆盖率中等，建议继续提升覆盖率")
            else:
                logger.error("🚨 赔率覆盖率过低，真实回测结果可能不具代表性")

            conn.close()

        except Exception as e:
            logger.error(f"❌ 生成覆盖率报告失败: {e}")

    async def run_extraction(self) -> None:
        """运行完整的赔率提取流程"""
        logger.info("🚀 V3.4 历史真实赔率提取开始")
        logger.info("目标: 拒绝模拟赔率，只要真实市场数据！")

        try:
            # 1. 获取所有比赛
            matches = self.get_all_matches()

            if not matches:
                logger.error("❌ 没有找到需要处理的比赛")
                return

            # 2. 批量提取赔率
            await self.process_batch(matches, batch_size=5)  # 减小批处理避免 API 限流

            # 3. 生成覆盖率报告
            self.generate_coverage_report()

            logger.info("🎉 V3.4 历史赔率提取完成！")

        except Exception as e:
            logger.error(f"❌ 赔率提取流程失败: {e}")
            raise


async def main():
    """主函数"""
    extractor = HistoricOddsExtractor()
    await extractor.run_extraction()


if __name__ == "__main__":
    asyncio.run(main())