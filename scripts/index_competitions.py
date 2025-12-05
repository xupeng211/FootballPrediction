#!/usr/bin/env python3
"""
天网计划 - Step 1: 构建世界赛事索引
Project Skynet - Step 1: World Competitions Index Builder

访问 FBref 赛事总览页，发现全球所有重要赛事
"""

import asyncio
import sys
import os
import logging
import pandas as pd
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector_stealth import StealthFBrefCollector
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO
    format="%(asctime)s - %(levelname)s - %(message)s"
    handlers=[
        logging.FileHandler("logs/skynet_competitions.log")
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WorldCompetitionsIndexer:
    """世界赛事索引构建器"""

    def __init__(self):
        self.collector = StealthFBrefCollector()
        self.engine = create_engine("postgresql://postgres@db:5432/football_prediction")

        # FBref 赛事总览页
        self.base_url = "https://fbref.com/en/comps/"

        # 目标赛事类别
        self.target_categories = {
            # Big 5 Leagues (五大联赛)
            "Big 5": {
                "England": {
                    "name": "Premier League"
                    "url": "https://fbref.com/en/comps/9/Premier-League-Stats"
                    "tier": "1"
                }
                "Spain": {
                    "name": "La Liga"
                    "url": "https://fbref.com/en/comps/12/La-Liga-Stats"
                    "tier": "1"
                }
                "Germany": {
                    "name": "Bundesliga"
                    "url": "https://fbref.com/en/comps/20/Bundesliga-Stats"
                    "tier": "1"
                }
                "Italy": {
                    "name": "Serie A"
                    "url": "https://fbref.com/en/comps/11/Serie-A-Stats"
                    "tier": "1"
                }
                "France": {
                    "name": "Ligue 1"
                    "url": "https://fbref.com/en/comps/13/Ligue-1-Stats"
                    "tier": "1"
                }
            }
            # International (国际赛事)
            "International": {
                "World Cup": {
                    "name": "FIFA World Cup"
                    "url": "https://fbref.com/en/comps/1/world-cup"
                    "tier": "1"
                    "category": "International"
                }
                "Euros": {
                    "name": "UEFA European Championship"
                    "url": "https://fbref.com/en/comps/2/european-championship"
                    "tier": "1"
                    "category": "International"
                }
                "Copa America": {
                    "name": "Copa América"
                    "url": "https://fbref.com/en/comps/3/copa-america"
                    "tier": "1"
                    "category": "International"
                }
            }
            # Domestic Cups (国内杯赛)
            "Domestic Cups": {
                "FA Cup": {
                    "name": "FA Cup"
                    "url": "https://fbref.com/en/comps/37/FA-Cup"
                    "tier": "2"
                    "category": "Club"
                }
                "Copa del Rey": {
                    "name": "Copa del Rey"
                    "url": "https://fbref.com/en/comps/79/Copa-del-Rey"
                    "tier": "2"
                    "category": "Club"
                }
                "DFB-Pokal": {
                    "name": "DFB-Pokal"
                    "url": "https://fbref.com/en/comps/81/DFB-Pokal"
                    "tier": "2"
                    "category": "Club"
                }
                "Coppa Italia": {
                    "name": "Coppa Italia"
                    "url": "https://fbref.com/en/comps/82/Coppa-Italia"
                    "tier": "2"
                    "category": "Club"
                }
                "Coupe de France": {
                    "name": "Coupe de France"
                    "url": "https://fbref.com/en/comps/85/Coupe-de-France"
                    "tier": "2"
                    "category": "Club"
                }
            }
            # Club Continental (俱乐部洲际赛事)
            "Club Continental": {
                "Champions League": {
                    "name": "UEFA Champions League"
                    "url": "https://fbref.com/en/comps/8/champions-league"
                    "tier": "1"
                    "category": "Club"
                }
                "Europa League": {
                    "name": "UEFA Europa League"
                    "url": "https://fbref.com/en/comps/19/europa-league"
                    "tier": "1"
                    "category": "Club"
                }
                "Europa Conference": {
                    "name": "UEFA Europa Conference League"
                    "url": "https://fbref.com/en/comps/951/europa-conference-league"
                    "tier": "1"
                    "category": "Club"
                }
                "Copa Libertadores": {
                    "name": "Copa Libertadores"
                    "url": "https://fbref.com/en/comps/5/copa-libertadores"
                    "tier": "1"
                    "category": "Club"
                }
            }
            # Top Tier 2 (次级联赛)
            "Top Tier 2": {
                "Championship": {
                    "name": "EFL Championship"
                    "url": "https://fbref.com/en/comps/10/Championship-Stats"
                    "tier": "2"
                    "category": "Club"
                }
                "Eredivisie": {
                    "name": "Eredivisie"
                    "url": "https://fbref.com/en/comps/23/Eredivisie-Stats"
                    "tier": "2"
                    "category": "Club"
                }
                "Primeira Liga": {
                    "name": "Primeira Liga"
                    "url": "https://fbref.com/en/comps/32/Primeira-Liga-Stats"
                    "tier": "2"
                    "category": "Club"
                }
                "MLS": {
                    "name": "Major League Soccer"
                    "url": "https://fbref.com/en/comps/22/MLS-Stats"
                    "tier": "2"
                    "category": "Club"
                }
                "Brasileirão": {
                    "name": "Brasileirão"
                    "url": "https://fbref.com/en/comps/26/Serie-A-Stats"
                    "tier": "1"
                    "category": "Club"
                }
            }
        }

        # 统计信息
        self.stats = {
            "total_competitions": 0
            "new_competitions": 0
            "existing_competitions": 0
            "failed_competitions": []
        }

    async def fetch_competitions_page(self) -> pd.DataFrame:
        """获取FBref赛事总览页面"""
        logger.info(f"🗺️ 访问FBref赛事总览页: {self.base_url}")

        try:
            # 访问总览页
            df = await self.collector.get_season_schedule_stealth(self.base_url)

            if df is None or df.empty:
                logger.error("❌ 无法获取赛事总览页面")
                return pd.DataFrame()

            logger.info(f"✅ 获取到赛事列表: {len(df)} 行")
            logger.info(f"📋 列名: {list(df.columns)}")

            return df

        except Exception as e:
            logger.error(f"❌ 获取赛事页面失败: {e}")
            import traceback

            traceback.print_exc()
            return pd.DataFrame()

    def parse_competition_urls(self) -> list[dict]:
        """解析目标赛事URL列表"""
        competitions = []

        logger.info("📋 解析目标赛事列表...")

        for category_name, category_data in self.target_categories.items():
            logger.info(f"\n🔍 处理类别: {category_name}")

            for key, comp_data in category_data.items():
                comp_info = {
                    "name": comp_data["name"]
                    "fbref_url": comp_data["url"]
                    "category": comp_data.get("category", "Club")
                    "tier": comp_data["tier"]
                    "source_category": category_name
                    "country": key if category_name == "Big 5" else None
                }

                competitions.append(comp_info)
                logger.info(f"  ✅ {comp_info['name']} - {comp_info['fbref_url']}")

        self.stats["total_competitions"] = len(competitions)
        logger.info(f"\n📊 总计: {len(competitions)} 个目标赛事")

        return competitions

    def save_competitions_to_db(self, competitions: list[dict]) -> int:
        """保存赛事到数据库"""
        logger.info(f"\n💾 保存 {len(competitions)} 个赛事到数据库...")

        saved_count = 0
        skipped_count = 0

        try:
            with self.engine.connect() as conn:
                for comp in competitions:
                    try:
                        # 检查是否已存在
                        result = conn.execute(
                            text("SELECT id FROM leagues WHERE name = :name")
                            {"name": comp["name"]}
                        ).fetchone()

                        if result:
                            # 更新现有记录
                            conn.execute(
                                text(
                                    """
                                    UPDATE leagues SET
                                        fbref_url = :fbref_url
                                        category = :category
                                        tier = :tier
                                        updated_at = NOW()
                                    WHERE name = :name
                                """
                                )
                                {
                                    "name": comp["name"]
                                    "fbref_url": comp["fbref_url"]
                                    "category": comp["category"]
                                    "tier": comp["tier"]
                                }
                            )
                            skipped_count += 1
                            logger.debug(f"  🔄 更新: {comp['name']}")
                        else:
                            # 创建新记录
                            conn.execute(
                                text(
                                    """
                                    INSERT INTO leagues (
                                        name, fbref_url, category, tier
                                        country, is_active, created_at, updated_at
                                    ) VALUES (
                                        :name, :fbref_url, :category, :tier
                                        :country, true, NOW(), NOW()
                                    )
                                """
                                )
                                {
                                    "name": comp["name"]
                                    "fbref_url": comp["fbref_url"]
                                    "category": comp["category"]
                                    "tier": comp["tier"]
                                    "country": comp.get(
                                        "country"
                                        (
                                            "International"
                                            if comp["category"] == "International"
                                            else None
                                        )
                                    )
                                }
                            )
                            saved_count += 1
                            logger.info(
                                f"  ➕ 新增: {comp['name']} ({comp['category']})"
                            )

                    except Exception as e:
                        logger.error(f"  ❌ 保存失败 {comp['name']}: {e}")
                        self.stats["failed_competitions"].append(comp["name"])
                        continue

                conn.commit()

        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {e}")
            return 0

        self.stats["new_competitions"] = saved_count
        self.stats["existing_competitions"] = skipped_count

        return saved_count

    def print_summary(self):
        """打印统计摘要"""
        logger.info("\n" + "=" * 80)
        logger.info("🌍 天网计划 - Step 1 完成：世界赛事索引构建")
        logger.info("=" * 80)

        logger.info("\n📊 统计信息:")
        logger.info(f"  目标赛事总数: {self.stats['total_competitions']}")
        logger.info(f"  新增赛事: {self.stats['new_competitions']}")
        logger.info(f"  更新赛事: {self.stats['existing_competitions']}")
        logger.info(f"  失败赛事: {len(self.stats['failed_competitions'])}")

        if self.stats["failed_competitions"]:
            logger.info("\n❌ 失败列表:")
            for comp in self.stats["failed_competitions"]:
                logger.info(f"  - {comp}")

        # 数据库验证
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                    SELECT category, tier, COUNT(*) as count
                    FROM leagues
                    GROUP BY category, tier
                    ORDER BY category, tier
                """
                    )
                ).fetchall()

                logger.info("\n📋 数据库中赛事分类:")
                for row in result:
                    logger.info(f"  {row.category} (Tier {row.tier}): {row.count} 个")

        except Exception as e:
            logger.error(f"验证查询失败: {e}")

        logger.info("=" * 80)

    async def run(self):
        """运行索引构建"""
        logger.info("🚀 启动天网计划 - Step 1: 世界赛事索引构建")
        logger.info("目标: 构建全球重要足球赛事的完整索引")

        # Step 1: 解析目标赛事列表
        competitions = self.parse_competition_urls()

        # Step 2: 保存到数据库
        saved_count = self.save_competitions_to_db(competitions)

        # Step 3: 打印摘要
        self.print_summary()

        return saved_count > 0


def main():
    """主函数"""
    # 确保日志目录
    Path("logs").mkdir(exist_ok=True)

    try:
        indexer = WorldCompetitionsIndexer()
        success = asyncio.run(indexer.run())

        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
