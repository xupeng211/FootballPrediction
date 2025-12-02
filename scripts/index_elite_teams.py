#!/usr/bin/env python3
"""
天网计划 - Step 2: 构建豪门球队索引
Project Skynet - Step 2: Elite Teams Index Builder

从五大联赛中提取所有豪门球队，构建完整索引
"""

import asyncio
import sys
import os
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector_stealth import StealthFBrefCollector
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/skynet_teams.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class EliteTeamsIndexer:
    """豪门球队索引构建器"""

    def __init__(self):
        self.collector = StealthFBrefCollector()
        self.engine = create_engine("postgresql://postgres@db:5432/football_prediction")

        # 五大联赛的URL和名称映射
        self.big5_leagues = {
            "Premier League": {
                "name": "Premier League",
                "url": "https://fbref.com/en/comps/9/Premier-League-Stats",
                "country": "England"
            },
            "La Liga": {
                "name": "La Liga",
                "url": "https://fbref.com/en/comps/12/La-Liga-Stats",
                "country": "Spain"
            },
            "Bundesliga": {
                "name": "Bundesliga",
                "url": "https://fbref.com/en/comps/20/Bundesliga-Stats",
                "country": "Germany"
            },
            "Serie A": {
                "name": "Serie A",
                "url": "https://fbref.com/en/comps/11/Serie-A-Stats",
                "country": "Italy"
            },
            "Ligue 1": {
                "name": "Ligue 1",
                "url": "https://fbref.com/en/comps/13/Ligue-1-Stats",
                "country": "France"
            }
        }

        # 统计信息
        self.stats = {
            'total_leagues': len(self.big5_leagues),
            'processed_leagues': 0,
            'total_teams': 0,
            'new_teams': 0,
            'updated_teams': 0,
            'failed_teams': []
        }

    async def fetch_league_standings(self, league_name: str, league_url: str) -> Optional[pd.DataFrame]:
        """获取联赛积分榜（包含球队信息）"""
        logger.info(f"\n🏆 获取 {league_name} 积分榜...")

        try:
            # 访问联赛页面
            df = await self.collector.get_season_schedule_stealth(league_url)

            if df is None or df.empty:
                logger.error(f"❌ 无法获取 {league_name} 页面")
                return None

            logger.info(f"✅ {league_name}: 获取到 {len(df)} 行数据")
            logger.info(f"📋 列名: {list(df.columns)}")

            return df

        except Exception as e:
            logger.error(f"❌ 获取 {league_name} 失败: {e}")
            return None

    def extract_teams_from_standings(self, df: pd.DataFrame, league_name: str) -> List[Dict]:
        """从积分榜中提取球队信息"""
        logger.info(f"\n🔍 从 {league_name} 提取球队信息...")

        teams = []
        team_links = []  # 存储球队链接URL

        try:
            # 查找包含球队名称和链接的列
            # FBref的积分榜通常包含球队名称和链接
            for col in df.columns:
                if 'squad' in str(col).lower() or 'team' in str(col).lower() or 'home' in str(col).lower():
                    # 这可能是球队列
                    logger.info(f"  检查列: {col}")
                    logger.info(f"  样本数据: {df[col].head().tolist()}")

            # 常见情况：球队信息在第一列，且包含链接
            if len(df) > 0:
                # 查找第一列中的链接
                first_col = df.iloc[:, 0]  # 第一列
                for idx, value in enumerate(first_col):
                    if pd.notna(value) and isinstance(value, str):
                        # 检查是否包含链接格式
                        if '/en/squads/' in str(value):
                            try:
                                # 提取球队名称和URL
                                # FBref链接格式: <a href="/en/squads/b8fd03ef/Manchester-City-Stats">Manchester City</a>
                                import re
                                link_match = re.search(r'href="(/en/squads/[^"]+)"[^>]*>([^<]+)</a>', str(value))

                                if link_match:
                                    team_url = link_match.group(1)
                                    team_name = link_match.group(2).strip()

                                    teams.append({
                                        'name': team_name,
                                        'fbref_url': team_url,
                                        'fbref_id': team_url.split('/')[-2] if '/' in team_url else None
                                    })

                                    logger.info(f"  ✅ 发现球队: {team_name} ({team_url})")

                            except Exception as e:
                                logger.warning(f"    解析失败 {value}: {e}")
                                continue

                # 如果上面方法失败，尝试其他方法
                if not teams:
                    logger.warning("  ⚠️ 链接解析失败，尝试备用方法...")
                    # 备用：直接从列值中提取球队名
                    for col in df.columns:
                        if df[col].dtype == 'object':  # 文本列
                            unique_values = df[col].dropna().unique()
                            for val in unique_values[:20]:  # 只检查前20个
                                if isinstance(val, str) and len(val) > 3:
                                    teams.append({
                                        'name': val.strip(),
                                        'fbref_url': None,
                                        'fbref_id': None
                                    })
                                    logger.info(f"  📝 记录球队: {val.strip()}")

        except Exception as e:
            logger.error(f"❌ 提取球队信息失败: {e}")
            import traceback
            traceback.print_exc()

        self.stats['total_teams'] += len(teams)
        logger.info(f"  📊 {league_name}: 提取到 {len(teams)} 支球队")

        return teams

    def save_teams_to_db(self, teams: List[Dict], league_name: str, country: str) -> Tuple[int, int]:
        """保存球队信息到数据库"""
        logger.info(f"\n💾 保存 {league_name} 的 {len(teams)} 支球队...")

        new_count = 0
        update_count = 0

        try:
            with self.engine.connect() as conn:
                for team in teams:
                    try:
                        # 首先尝试通过 fbref_external_id 查找
                        if team.get('fbref_id'):
                            result = conn.execute(
                                text("SELECT id FROM teams WHERE fbref_external_id = :fbref_id"),
                                {'fbref_id': team['fbref_id']}
                            ).fetchone()

                        # 如果没找到，尝试通过名称查找
                        if not result:
                            result = conn.execute(
                                text("SELECT id FROM teams WHERE name ILIKE :name"),
                                {'name': team['name']}
                            ).fetchone()

                        if result:
                            # 更新现有记录
                            update_data = {
                                'name': team['name'],
                                'fbref_url': team.get('fbref_url'),
                                'fbref_external_id': team.get('fbref_id'),
                                'country': country
                            }

                            conn.execute(
                                text("""
                                    UPDATE teams SET
                                        name = :name,
                                        fbref_url = :fbref_url,
                                        fbref_external_id = :fbref_external_id,
                                        country = :country,
                                        updated_at = NOW()
                                    WHERE id = :id
                                """),
                                {**update_data, 'id': result.id}
                            )
                            update_count += 1
                            logger.debug(f"  🔄 更新: {team['name']}")
                        else:
                            # 创建新记录
                            conn.execute(
                                text("""
                                    INSERT INTO teams (
                                        name, country, fbref_url, fbref_external_id,
                                        created_at, updated_at
                                    ) VALUES (
                                        :name, :country, :fbref_url, :fbref_external_id,
                                        NOW(), NOW()
                                    )
                                """),
                                {
                                    'name': team['name'],
                                    'country': country,
                                    'fbref_url': team.get('fbref_url'),
                                    'fbref_external_id': team.get('fbref_id')
                                }
                            )
                            new_count += 1
                            logger.info(f"  ➕ 新增: {team['name']} ({country})")

                    except Exception as e:
                        logger.error(f"  ❌ 保存失败 {team['name']}: {e}")
                        self.stats['failed_teams'].append(team['name'])
                        continue

                conn.commit()

        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {e}")
            return 0, 0

        self.stats['new_teams'] += new_count
        self.stats['updated_teams'] += update_count

        return new_count, update_count

    def print_summary(self):
        """打印统计摘要"""
        logger.info("\n" + "="*80)
        logger.info("⚽ 天网计划 - Step 2 完成：豪门球队索引构建")
        logger.info("="*80)

        logger.info(f"\n📊 统计信息:")
        logger.info(f"  处理联赛: {self.stats['processed_leagues']}/{self.stats['total_leagues']}")
        logger.info(f"  发现球队总数: {self.stats['total_teams']}")
        logger.info(f"  新增球队: {self.stats['new_teams']}")
        logger.info(f"  更新球队: {self.stats['updated_teams']}")
        logger.info(f"  失败球队: {len(self.stats['failed_teams'])}")

        if self.stats['failed_teams']:
            logger.info(f"\n❌ 失败列表:")
            for team in self.stats['failed_teams'][:10]:  # 只显示前10个
                logger.info(f"  - {team}")

        # 数据库验证
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT country, COUNT(*) as count
                    FROM teams
                    WHERE country IN ('England', 'Spain', 'Germany', 'Italy', 'France')
                    GROUP BY country
                    ORDER BY count DESC
                """)).fetchall()

                logger.info(f"\n📋 五大联赛球队统计:")
                for row in result:
                    logger.info(f"  {row.country}: {row.count} 支球队")

                # 统计有FBref链接的球队
                fbref_count = conn.execute(text("""
                    SELECT COUNT(*) FROM teams WHERE fbref_url IS NOT NULL
                """)).scalar()

                logger.info(f"\n🔗 有FBref链接的球队: {fbref_count}")

        except Exception as e:
            logger.error(f"验证查询失败: {e}")

        logger.info("="*80)

    async def run(self):
        """运行球队索引构建"""
        logger.info("🚀 启动天网计划 - Step 2: 豪门球队索引构建")
        logger.info("目标: 构建五大联赛所有球队的完整索引")

        # 遍历五大联赛
        for league_name, league_info in self.big5_leagues.items():
            logger.info(f"\n" + "="*60)
            logger.info(f"🏆 处理联赛: {league_name} ({league_info['country']})")
            logger.info(f"📡 URL: {league_info['url']}")
            logger.info("="*60)

            # Step 1: 获取联赛页面
            df = await self.fetch_league_standings(league_name, league_info['url'])

            if df is None:
                logger.error(f"❌ 跳过 {league_name}，无法获取数据")
                continue

            # Step 2: 提取球队信息
            teams = self.extract_teams_from_standings(df, league_name)

            if not teams:
                logger.warning(f"⚠️ {league_name}: 未发现球队信息")
                continue

            # Step 3: 保存到数据库
            new_count, update_count = self.save_teams_to_db(
                teams, league_name, league_info['country']
            )

            self.stats['processed_leagues'] += 1
            logger.info(f"  ✅ {league_name}: 新增 {new_count}, 更新 {update_count}")

            # 防止请求过快
            await asyncio.sleep(5)

        # 打印摘要
        self.print_summary()

        return self.stats['total_teams'] > 0


def main():
    """主函数"""
    # 确保日志目录
    Path("logs").mkdir(exist_ok=True)

    try:
        indexer = EliteTeamsIndexer()
        success = asyncio.run(indexer.run())

        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
