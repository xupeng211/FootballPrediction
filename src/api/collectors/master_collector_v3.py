#!/usr/bin/env python3
"""
Master Collector v3.0 - 统一数据收集器
整合所有FotMob API认证逻辑和数据收集功能
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os

from src.config_unified import get_settings
from src.processors.feature_extractor import AdvancedFeatureExtractor

logger = logging.getLogger(__name__)


class MasterCollectorV3:
    """Master Collector v3.0 - 统一数据收集器"""

    def __init__(self):
        # 使用统一配置系统
        settings = get_settings()
        db = settings.database
        self.db_config = {
            "host": db.host,
            "port": db.port,
            "database": db.name,
            "user": db.user,
            "password": db.password.get_secret_value(),
        }

        # FotMob API认证头 - 生产级配置
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        # 添加认证标头
        fotmob_config = settings.fotmob_api
        if fotmob_config.x_mas_header:
            self.headers["X-Mas"] = fotmob_config.x_mas_header.get_secret_value()
        if fotmob_config.x_foo_header:
            self.headers["X-Foo"] = fotmob_config.x_foo_header.get_secret_value()

        self.base_url = "https://www.fotmob.com"
        self.extractor = AdvancedFeatureExtractor()

        # 统计信息
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0

    async def fetch_match_data(self, session: aiohttp.ClientSession, external_id: str) -> Optional[Dict]:
        """获取单场比赛数据"""
        url = f"{self.base_url}/api/matchDetails?matchId={external_id}"

        try:
            async with session.get(url, headers=self.headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"✅ 成功获取比赛数据: {external_id}")
                    return data
                else:
                    logger.warning(f"获取比赛 {external_id} 失败: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"获取比赛 {external_id} 异常: {e}")
            return None

    async def process_match(self, session: aiohttp.ClientSession, match: Dict) -> bool:
        """处理单场比赛"""
        external_id = match["external_id"]

        # 获取比赛数据
        match_data = await self.fetch_match_data(session, external_id)
        if not match_data:
            return False

        try:
            # 使用高级特征提取器
            features = self.extractor.extract_all_features(match_data, external_id)

            # 转换为字典格式以便保存
            features_dict = {
                "external_id": features.external_id,
                "match_time": match.get("match_time"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "home_xg": features.home_xg,
                "away_xg": features.away_xg,
                "xg_total": features.xg_total,
                "xg_diff": features.xg_diff,
                "home_possession": features.home_possession,
                "away_possession": features.away_possession,
                "home_opening_odds": features.home_opening_odds,
                "away_opening_odds": features.away_opening_odds,
                "draw_odds": features.draw_odds,
                "raw_data_source": features.raw_data_source,
                "extracted_at": features.extracted_at,
            }

            # 保存到数据库
            success = await self.save_features_to_db(features_dict)
            return success

        except Exception as e:
            logger.error(f"处理比赛 {external_id} 失败: {e}")
            return False

    async def save_features_to_db(self, features: Dict) -> bool:
        """保存特征到数据库"""
        import asyncpg

        try:
            conn = await asyncpg.connect(**self.db_config)

            # UPSERT操作
            await conn.execute(
                """
                INSERT INTO match_features_training
                (external_id, match_time, home_team, away_team, home_xg, away_xg,
                 xg_total, xg_diff, home_possession, away_possession,
                 home_opening_odds, away_opening_odds, draw_odds, raw_data_source, extracted_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (external_id)
                DO UPDATE SET
                    home_xg = EXCLUDED.home_xg,
                    away_xg = EXCLUDED.away_xg,
                    xg_total = EXCLUDED.xg_total,
                    xg_diff = EXCLUDED.xg_diff,
                    home_possession = EXCLUDED.home_possession,
                    away_possession = EXCLUDED.away_possession,
                    home_opening_odds = EXCLUDED.home_opening_odds,
                    away_opening_odds = EXCLUDED.away_opening_odds,
                    draw_odds = EXCLUDED.draw_odds,
                    extracted_at = EXCLUDED.extracted_at,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (
                    features["external_id"],
                    features.get("match_time"),
                    features.get("home_team"),
                    features.get("away_team"),
                    features.get("home_xg"),
                    features.get("away_xg"),
                    features.get("xg_total"),
                    features.get("xg_diff"),
                    features.get("home_possession"),
                    features.get("away_possession"),
                    features.get("home_opening_odds"),
                    features.get("away_opening_odds"),
                    features.get("draw_odds"),
                    features.get("raw_data_source"),
                    features.get("extracted_at"),
                ),
            )

            await conn.close()
            return True

        except Exception as e:
            logger.error(f"保存比赛 {features['external_id']} 失败: {e}")
            return False

    async def run_collection(self, limit: int = 10):
        """运行数据收集"""
        logger.info("🚀 Master Collector v3.0 启动 - 统一数据收集")
        logger.info(f"处理上限: {limit} 场")

        # 获取比赛列表
        matches = await self.get_matches_from_db(limit)
        if not matches:
            logger.error("未找到任何比赛")
            return

        # 创建HTTP会话
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 批量处理
            batch_size = 5
            for i in range(0, len(matches), batch_size):
                batch = matches[i : i + batch_size]

                logger.info(f"处理批次 {i//batch_size + 1}/{(len(matches)-1)//batch_size + 1}")

                # 并发处理批次
                tasks = [self.process_match(session, match) for match in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 统计结果
                batch_success = sum(1 for r in results if r is True)
                self.processed_count += len(batch)
                self.success_count += batch_success
                self.error_count += len(batch) - batch_success

                # 进度报告
                progress = (i + batch_size) / len(matches) * 100
                logger.info(f"批次完成: {batch_success}/{len(batch)} 成功")
                logger.info(
                    f"总进度: {min(progress, 100):.1f}% | 成功: {self.success_count} | 失败: {self.error_count}"
                )

                # 延迟避免过于频繁的请求
                if i + batch_size < len(matches):
                    await asyncio.sleep(1)

        # 最终报告
        logger.info("\n" + "=" * 80)
        logger.info("🏆 Master Collector v3.0 完成报告")
        logger.info("=" * 80)
        logger.info(f"📊 处理总数: {self.processed_count}")
        logger.info(f"✅ 成功收集: {self.success_count}")
        logger.info(f"❌ 失败数量: {self.error_count}")
        logger.info(
            f"📈 成功率: {self.success_count/self.processed_count*100:.1f}%"
            if self.processed_count > 0
            else "📈 成功率: 0%"
        )

    async def get_matches_from_db(self, limit: int) -> List[Dict]:
        """从数据库获取比赛列表"""
        import asyncpg

        conn = await asyncpg.connect(**self.db_config)

        try:
            rows = await conn.fetch(
                """
                SELECT external_id, home_team, away_team, match_time
                FROM matches
                WHERE external_id IS NOT NULL
                ORDER BY match_time DESC
                LIMIT $1
            """,
                limit,
            )

            matches = []
            for row in rows:
                matches.append(
                    {
                        "external_id": row["external_id"],
                        "home_team": row["home_team"],
                        "away_team": row["away_team"],
                        "match_time": row["match_time"],
                    }
                )

            logger.info(f"从数据库获取到 {len(matches)} 场比赛")
            return matches

        finally:
            await conn.close()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Master Collector v3.0 - 统一数据收集")
    parser.add_argument("--limit", type=int, default=10, help="处理比赛数量上限")

    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    collector = MasterCollectorV3()
    await collector.run_collection(args.limit)


if __name__ == "__main__":
    asyncio.run(main())
