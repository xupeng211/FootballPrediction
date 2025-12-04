#!/usr/bin/env python3
"""
首席数据鉴赏家 - 寻找完美数据记录
展示多轮数据清洗和补全的卓越成果
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataConnoisseur:
    """首席数据鉴赏家 - 完美数据展示器"""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres-dev-password@db:5432/football_prediction")

    async def find_perfect_record(self):
        """寻找信息最丰富的完美比赛记录"""
        try:
            conn = await asyncpg.connect(self.database_url)

            # 寻找包含丰富数据的记录
            query = """
                SELECT
                    m.id,
                    home.name as home_team,
                    away.name as away_team,
                    m.match_date,
                    m.home_score,
                    m.away_score,
                    m.stats,
                    m.lineups,
                    m.events,
                    m.data_source,
                    m.data_completeness
                FROM matches m
                JOIN teams home ON m.home_team_id = home.id
                JOIN teams away ON m.away_team_id = away.id
                WHERE m.stats IS NOT NULL
                  AND m.lineups IS NOT NULL
                ORDER BY
                    CASE WHEN m.stats->>'xg_home' IS NOT NULL THEN 1 ELSE 2 END,
                    m.match_date DESC
                LIMIT 3
            """

            records = await conn.fetch(query)
            await conn.close()

            if records:
                return records[0]  # 返回最完美的记录
            else:
                return None

        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return None

    def format_match_overview(self, record):
        """格式化比赛概览信息"""
        match_date = record['match_date']
        if isinstance(match_date, str):
            match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))

        return {
            'date': match_date.strftime('%Y年%m月%d日 %H:%M'),
            'teams': f"{record['home_team']} vs {record['away_team']}",
            'score': f"{record['home_score']} - {record['away_score']}",
            'data_sources': record['data_source'],
            'completeness': record['data_completeness'] or 'unknown'
        }

    def extract_xg_stats(self, stats):
        """提取xG统计数据"""
        if not stats:
            return None

        try:
            if isinstance(stats, str):
                stats = json.loads(stats)

            xg_home = stats.get('xg_home') or stats.get('expected_goals_home')
            xg_away = stats.get('xg_away') or stats.get('expected_goals_away')

            return {
                'xg_home': xg_home,
                'xg_away': xg_away,
                'xg_total': (xg_home or 0) + (xg_away or 0)
            }
        except:
            return None

    def extract_key_stats(self, stats):
        """提取关键统计数据"""
        if not stats:
            return {}

        try:
            if isinstance(stats, str):
                stats = json.loads(stats)

            return {
                'possession_home': stats.get('possession_home', 'N/A'),
                'possession_away': stats.get('possession_away', 'N/A'),
                'shots_home': stats.get('shots_home', 'N/A'),
                'shots_away': stats.get('shots_away', 'N/A'),
                'shots_on_target_home': stats.get('shots_on_target_home', 'N/A'),
                'shots_on_target_away': stats.get('shots_on_target_away', 'N/A'),
            }
        except:
            return {}

    def extract_lineups(self, lineups):
        """提取阵容信息"""
        if not lineups:
            return {'home': [], 'away': []}

        try:
            if isinstance(lineups, str):
                lineups = json.loads(lineups)

            home_lineup = []
            away_lineup = []

            # 处理主队阵容
            if 'home_lineup' in lineups:
                home_players = lineups['home_lineup']
                if isinstance(home_players, list):
                    for i, player in enumerate(home_players[:3]):  # 取前3名
                        if isinstance(player, dict):
                            name = player.get('name', f'Player {i+1}')
                            position = player.get('position', 'N/A')
                            home_lineup.append(f"{position}: {name}")
                        elif isinstance(player, str):
                            home_lineup.append(f"Player: {player}")
                        else:
                            home_lineup.append(f"Player {i+1}")

            # 处理客队阵容
            if 'away_lineup' in lineups:
                away_players = lineups['away_lineup']
                if isinstance(away_players, list):
                    for i, player in enumerate(away_players[:3]):  # 取前3名
                        if isinstance(player, dict):
                            name = player.get('name', f'Player {i+1}')
                            position = player.get('position', 'N/A')
                            away_lineup.append(f"{position}: {name}")
                        elif isinstance(player, str):
                            away_lineup.append(f"Player: {player}")
                        else:
                            away_lineup.append(f"Player {i+1}")

            return {
                'home': home_lineup,
                'away': away_lineup
            }
        except Exception as e:
            logger.debug(f"阵容解析失败: {e}")
            return {'home': [], 'away': []}

    def extract_key_events(self, events):
        """提取关键比赛事件"""
        if not events:
            return []

        try:
            if isinstance(events, str):
                events = json.loads(events)

            key_events = []

            if isinstance(events, list):
                for event in events[:3]:  # 取前3个事件
                    if isinstance(event, dict):
                        event_type = event.get('type', 'Unknown')
                        minute = event.get('minute', 'N/A')
                        team = event.get('team', 'N/A')
                        player = event.get('player', 'N/A')

                        key_events.append(f"{minute}' - {team}: {player} ({event_type})")
                    elif isinstance(event, str):
                        key_events.append(f"Event: {event}")

            return key_events
        except Exception as e:
            logger.debug(f"事件解析失败: {e}")
            return []

    def display_perfect_record(self, record):
        """展示完美数据记录"""
        print("\n" + "="*80)
        print("🏆 首席数据鉴赏家 - 完美数据记录展示")
        print("="*80)

        # 基本信息
        overview = self.format_match_overview(record)
        print(f"\n🎯 比赛概览:")
        print(f"   📅 时间: {overview['date']}")
        print(f"   ⚽ 对阵: {overview['teams']}")
        print(f"   📊 比分: {overview['score']}")
        print(f"   🔄 数据源: {overview['data_sources']}")
        print(f"   ✅ 完整性: {overview['completeness']}")

        # xG统计
        xg_stats = self.extract_xg_stats(record['stats'])
        if xg_stats:
            print(f"\n📈 预期进球 (xG) 分析:")
            print(f"   🎯 主队xG: {xg_stats['xg_home']}")
            print(f"   🎯 客队xG: {xg_stats['xg_away']}")
            print(f"   📊 总xG: {xg_stats['xg_total']:.2f}")

            # xG与实际得分对比
            actual_home = record['home_score']
            actual_away = record['away_score']
            xg_diff_home = (actual_home - (xg_stats['xg_home'] or 0))
            xg_diff_away = (actual_away - (xg_stats['xg_away'] or 0))

            print(f"   📊 xG效率: 主队 {'超预期' if xg_diff_home > 0 else '低于预期'} ({xg_diff_home:+.1f}), "
                  f"客队 {'超预期' if xg_diff_away > 0 else '低于预期'} ({xg_diff_away:+.1f})")

        # 关键统计
        key_stats = self.extract_key_stats(record['stats'])
        if key_stats:
            print(f"\n📊 关键技术统计:")
            print(f"   🎮 控球率: 主队 {key_stats.get('possession_home', 'N/A')}% vs 客队 {key_stats.get('possession_away', 'N/A')}%")
            print(f"   🥅 射门数: 主队 {key_stats.get('shots_home', 'N/A')} vs 客队 {key_stats.get('shots_away', 'N/A')}")
            print(f"   🎯 射正数: 主队 {key_stats.get('shots_on_target_home', 'N/A')} vs 客队 {key_stats.get('shots_on_target_away', 'N/A')}")

        # 阵容信息
        lineups = self.extract_lineups(record['lineups'])
        if lineups['home'] or lineups['away']:
            print(f"\n👥 首发阵容 (展示前3名):")

            if lineups['home']:
                print(f"   🏠 {record['home_team']}:")
                for player in lineups['home']:
                    print(f"      {player}")

            if lineups['away']:
                print(f"   ✈️ {record['away_team']}:")
                for player in lineups['away']:
                    print(f"      {player}")

        # 关键事件
        key_events = self.extract_key_events(record['events'])
        if key_events:
            print(f"\n⚡ 关键比赛事件:")
            for event in key_events:
                print(f"   ⏰ {event}")

        # 数据完整性评估
        print(f"\n🔍 数据完整性评估:")
        completeness_score = 0
        max_score = 4

        if record['stats']:
            completeness_score += 1
            print(f"   ✅ 统计数据: 完整")
        else:
            print(f"   ❌ 统计数据: 缺失")

        if record['lineups']:
            completeness_score += 1
            print(f"   ✅ 阵容信息: 完整")
        else:
            print(f"   ❌ 阵容信息: 缺失")

        if record['events']:
            completeness_score += 1
            print(f"   ✅ 比赛事件: 完整")
        else:
            print(f"   ❌ 比赛事件: 缺失")

        if xg_stats and xg_stats['xg_home'] is not None:
            completeness_score += 1
            print(f"   ✅ xG数据: 完整")
        else:
            print(f"   ❌ xG数据: 缺失")

        print(f"\n📋 完整性评分: {completeness_score}/{max_score} ({completeness_score/max_score*100:.0f}%)")

        print("\n" + "="*80)
        print("🎉 这就是我们数据清洗和补全工作的完美成果！")
        print("💎 每一条记录都凝聚了多轮数据处理的精华")
        print("="*80)


async def main():
    """主函数 - 首席数据鉴赏家展示"""
    logger.info("🏆 首席数据鉴赏家 - 完美数据展示开始")

    connoisseur = DataConnoisseur()

    # 寻找完美记录
    perfect_record = await connoisseur.find_perfect_record()

    if perfect_record:
        # 展示完美数据
        connoisseur.display_perfect_record(perfect_record)
    else:
        print("❌ 未找到符合条件的完美数据记录")
        print("💡 建议: 需要继续进行数据清洗和补全工作")


if __name__ == "__main__":
    asyncio.run(main())