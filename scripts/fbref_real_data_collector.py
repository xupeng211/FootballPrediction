#!/usr/bin/env python3
"""
FBref真实数据采集器 - 修复版
Real FBref Data Collector - Fixed Version

目标：采集FBref真实英超数据，确保数据真实性
"""

import asyncio
import sys
import os
import time
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector_stealth import StealthFBrefCollector
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/fbref_real_data.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class RealFBrefCollector:
    """真实FBref数据采集器"""

    def __init__(self):
        # 英超配置
        self.premier_league_id = 2

        # FBref真实URLs
        self.seasons = {
            '2023-2024': {
                'url': 'https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures',
                'season_id': '2023-2024'
            },
        }

        self.collector = StealthFBrefCollector()
        # 使用容器网络连接数据库（使用正确密码）
        self.engine = create_engine("postgresql://postgres:football_prediction_2024@db:5432/football_prediction")

    def clean_fbref_data(self, df, season_name: str) -> List[Dict]:
        """
        修复版数据清洗 - 使用正确的字段名
        """
        logger.info(f"🧹 开始清洗 {season_name} 赛季数据...")

        cleaned_matches = []

        for _, row in df.iterrows():
            try:
                # 使用正确的字段名
                home_team = row.get('Home')
                away_team = row.get('Away')
                score = row.get('Score')
                match_date = row.get('Date')

                # 基本验证
                if not home_team or not away_team:
                    continue

                # 检查是否已完成比赛 - 关键修复！
                # FBref中，如果Score为空或包含特定标记，则表示未完成
                if pd.isna(score) or score == '' or str(score).strip() == '':
                    logger.debug(f"跳过未完成比赛: {home_team} vs {away_team}")
                    continue

                # 解析比分 - 支持FBref的en dash (–) 和普通连字符 (-)
                try:
                    score_str = str(score).strip()
                    # 支持多种分隔符：en dash (–), em dash (—), 普通连字符 (-)
                    if '–' in score_str:
                        home_goals, away_goals = score_str.split('–')
                    elif '—' in score_str:
                        home_goals, away_goals = score_str.split('—')
                    elif '-' in score_str:
                        home_goals, away_goals = score_str.split('-')
                    else:
                        # 如果不是标准比分格式，跳过
                        logger.debug(f"跳过非标准比分: {score}")
                        continue

                    home_score = int(home_goals.strip())
                    away_score = int(away_goals.strip())
                except (ValueError, AttributeError) as e:
                    logger.debug(f"跳过无效比分: {score} ({e})")
                    continue

                # 构建匹配记录
                match_data = {
                    'home_team': home_team.strip(),
                    'away_team': away_team.strip(),
                    'home_score': home_score,
                    'away_score': away_score,
                    'date': match_date,
                    'season': season_name,
                    'league_id': self.premier_league_id,
                    'data_source': 'fbref',  # 标记为真实数据
                    'status': 'completed'
                }

                cleaned_matches.append(match_data)
                logger.debug(f"✅ 有效比赛: {home_team} {home_score}-{away_score} {away_team}")

            except Exception as e:
                logger.warning(f"清洗记录失败: {e}")
                continue

        logger.info(f"🔍 {season_name}: {len(df)} → {len(cleaned_matches)} 条有效记录")
        return cleaned_matches

    def save_to_database(self, matches: List[Dict]) -> int:
        """
        保存数据到数据库
        """
        saved_count = 0

        try:
            with self.engine.connect() as conn:
                for match in matches:
                    try:
                        # 获取球队ID
                        home_team_id = self.get_team_id(conn, match['home_team'])
                        away_team_id = self.get_team_id(conn, match['away_team'])

                        if not home_team_id or not away_team_id:
                            logger.warning(f"球队未找到: {match['home_team']} / {match['away_team']}")
                            continue

                        # 插入比赛
                        query = text("""
                            INSERT INTO matches (
                                home_team_id, away_team_id, home_score, away_score,
                                match_date, league_id, season, status, data_source,
                                created_at, updated_at
                            ) VALUES (
                                :home_team_id, :away_team_id, :home_score, :away_score,
                                :match_date, :league_id, :season, :status, :data_source,
                                NOW(), NOW()
                            )
                        """)

                        conn.execute(query, {
                            'home_team_id': home_team_id,
                            'away_team_id': away_team_id,
                            'home_score': match['home_score'],
                            'away_score': match['away_score'],
                            'match_date': match['date'],
                            'league_id': match['league_id'],
                            'season': match['season'],
                            'status': match['status'],
                            'data_source': match['data_source']
                        })

                        saved_count += 1

                    except Exception as e:
                        logger.warning(f"保存比赛失败: {e}")
                        continue

                conn.commit()
                logger.info(f"✅ 成功保存 {saved_count} 场比赛")

        except Exception as e:
            logger.error(f"数据库保存失败: {e}")
            return 0

        return saved_count

    def get_team_id(self, conn, team_name: str) -> Optional[int]:
        """获取球队ID"""
        try:
            query = text("SELECT id FROM teams WHERE name ILIKE :team_name")
            result = conn.execute(query, {'team_name': f'%{team_name}%'}).fetchone()
            return result.id if result else None
        except Exception as e:
            logger.warning(f"获取球队ID失败 {team_name}: {e}")
            return None

    async def collect_season(self, season_name: str, season_config: Dict) -> bool:
        """采集单个赛季"""
        url = season_config['url']
        season_id = season_config['season_id']

        logger.info(f"🏆 开始采集 {season_name} 赛季")
        logger.info(f"🔗 URL: {url}")

        try:
            # 访问FBref
            delay = 5
            logger.info(f"⏱️ 延迟 {delay} 秒...")
            await asyncio.sleep(delay)

            logger.info(f"📡 连接FBref服务器...")
            season_data = await self.collector.get_season_schedule_stealth(url)

            if season_data is None or season_data.empty:
                logger.error(f"❌ {season_name}: 无数据返回")
                return False

            logger.info(f"📊 {season_name}: 获取到 {len(season_data)} 条原始记录")
            logger.info(f"📋 列名: {list(season_data.columns)}")

            # 数据清洗
            cleaned_data = self.clean_fbref_data(season_data, season_name)

            if not cleaned_data:
                logger.error(f"❌ {season_name}: 清洗后无有效数据")
                return False

            logger.info(f"✅ {season_name}: 清洗后 {len(cleaned_data)} 场有效比赛")

            # 保存到数据库
            saved_count = self.save_to_database(cleaned_data)

            if saved_count > 0:
                logger.info(f"🎉 {season_name}: 成功采集并保存 {saved_count} 场比赛")
                return True
            else:
                logger.error(f"❌ {season_name}: 保存失败")
                return False

        except Exception as e:
            logger.error(f"❌ {season_name}: 采集异常 - {e}")
            import traceback
            traceback.print_exc()
            return False

    def print_summary(self):
        """打印采集摘要"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT season, COUNT(*) as match_count
                    FROM matches
                    WHERE data_source = 'fbref'
                    GROUP BY season
                    ORDER BY season DESC
                """)).fetchall()

                logger.info("\n" + "="*60)
                logger.info("📊 真实数据采集摘要")
                logger.info("="*60)

                total = 0
                for row in result:
                    logger.info(f"  {row.season}: {row.match_count} 场比赛")
                    total += row.match_count

                logger.info(f"\n✅ 总计: {total} 场真实比赛数据")

                # 验证数据
                sample = conn.execute(text("""
                    SELECT m.home_score, m.away_score, ht.name as home_team, at.name as away_team
                    FROM matches m
                    JOIN teams ht ON m.home_team_id = ht.id
                    JOIN teams at ON m.away_team_id = at.id
                    WHERE m.data_source = 'fbref'
                    ORDER BY m.created_at DESC
                    LIMIT 5
                """)).fetchall()

                logger.info(f"\n🔍 最新5场比赛样本:")
                for row in sample:
                    logger.info(f"  {row.home_team} {row.home_score}-{row.away_score} {row.away_team}")

                logger.info("="*60)

        except Exception as e:
            logger.error(f"打印摘要失败: {e}")

    async def run(self):
        """运行采集任务"""
        logger.info("🚀 FBref真实数据采集器启动")
        logger.info("目标: 采集真实英超比赛数据")

        for season_name, season_config in self.seasons.items():
            logger.info(f"\n📈 开始采集: {season_name}")
            success = await self.collect_season(season_name, season_config)

            if success:
                logger.info(f"✅ {season_name} 采集成功")
            else:
                logger.error(f"❌ {season_name} 采集失败")

            # 休息
            await asyncio.sleep(10)

        # 打印摘要
        self.print_summary()


def main():
    """主函数"""
    import pandas as pd  # 需要导入pandas

    # 确保日志目录
    Path("logs").mkdir(exist_ok=True)

    try:
        collector = RealFBrefCollector()
        asyncio.run(collector.run())
        return 0
    except Exception as e:
        logger.error(f"采集失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
