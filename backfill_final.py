#!/usr/bin/env python3
"""
最终生产版回填脚本 - Lead Developer Final Version
使用经过验证的纯SQL逻辑
"""

import asyncio
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database.base import get_async_db
from src.collectors.football_data_collector import FootballDataCollector


class ProductionBackfillService:
    """生产版回填服务 - Lead Developer Final"""

    def __init__(self):
        self.football_collector = FootballDataCollector()
        # 暂时禁用FotMob以专注于核心功能验证
        self.fotmob_collector = None
        self.min_delay = 0.5  # 更快的处理速度
        self.max_delay = 1.5

    async def collect_football_data(self, date_str: str) -> Dict[str, Any]:
        """只收集Football-Data.org数据"""
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            result = await self.football_collector.collect_matches(date_from=date_obj)
            return {
                'date': date_str,
                'football_data_matches': result.data.get("matches", []),
                'success': result.success,
                'total_matches': len(result.data.get("matches", [])),
                'errors': [result.error] if not result.success else []
            }
        except Exception as e:
            return {
                'date': date_str,
                'football_data_matches': [],
                'success': False,
                'total_matches': 0,
                'errors': [str(e)]
            }

    async def save_with_production_sql(self, data_result: Dict[str, Any]) -> int:
        """使用生产级纯SQL保存数据"""
        try:
            async for db in get_async_db():
                saved_count = 0
                all_teams_to_save = set()

                # 🏆 收集所有球队数据
                for match_data in data_result['football_data_matches']:
                    home_team = match_data.get('homeTeam', {})
                    away_team = match_data.get('awayTeam', {})

                    if home_team.get('id'):
                        all_teams_to_save.add((
                            home_team.get('id', 0),
                            home_team.get('name', ''),
                            home_team.get('shortName', ''),
                        ))

                    if away_team.get('id'):
                        all_teams_to_save.add((
                            away_team.get('id', 0),
                            away_team.get('name', ''),
                            away_team.get('shortName', ''),
                        ))

                # 🛡️ 纯SQL批量保存球队（秒级完成）
                if all_teams_to_save:
                    print(f"🏆 纯SQL保存 {len(all_teams_to_save)} 个球队...")

                    # 经过验证的球队插入SQL
                    sql_team = text("""
                        INSERT INTO teams (id, name, short_name, country, venue, website, created_at, updated_at)
                        VALUES (:id, :name, :short_name, 'Unknown', '', '', NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                    """)

                    for team_id, name, short_name in all_teams_to_save:
                        if team_id > 0:
                            try:
                                await db.execute(sql_team, {
                                    'id': team_id,
                                    'name': name or f"Team_{team_id}",
                                    'short_name': short_name or name or f"Team_{team_id}"
                                })
                                print(f"✅ 球队插入成功: {team_id}")
                            except Exception as e:
                                if "Temporary failure" in str(e):
                                    print(f"⚠️ 球队 {team_id} 跳过DNS问题")
                                else:
                                    print(f"❌ 球队 {team_id} 失败: {e}")
                                continue

                # 🎯 纯SQL保存比赛数据
                sql_match = text("""
                    INSERT INTO matches (home_team_id, away_team_id, home_score, away_score,
                                        match_date, status, league_id, season, created_at, updated_at)
                    VALUES (:home_team_id, :away_team_id, :home_score, :away_score,
                            :match_date, :status, :league_id, :season, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """)

                # 处理Football-Data.org比赛
                for match_data in data_result['football_data_matches']:
                    try:
                        home_team = match_data.get('homeTeam', {})
                        away_team = match_data.get('awayTeam', {})
                        score = match_data.get('score', {})

                        home_team_id = home_team.get('id', 0)
                        away_team_id = away_team.get('id', 0)

                        if home_team_id == 0 or away_team_id == 0:
                            continue

                        # 解析比赛时间
                        raw_date = datetime.fromisoformat(match_data.get('utcDate', f"{data_result['date']}T15:00:00Z"))
                        match_date = raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date

                        # 纯SQL插入比赛 - 无需ORM，零延迟
                        await db.execute(sql_match, {
                            'home_team_id': home_team_id,
                            'away_team_id': away_team_id,
                            'home_score': score.get('fullTime', {}).get('home', 0),
                            'away_score': score.get('fullTime', {}).get('away', 0),
                            'match_date': match_date,
                            'status': match_data.get('status', 'SCHEDULED'),
                            'league_id': match_data.get('competition', {}).get('id', 0),
                            'season': match_data.get('season', {}).get('startDate', '')[:4] if match_data.get('season') else data_result['date'][:4]
                        })

                        saved_count += 1
                        print(f"✅ 比赛插入成功: {home_team_id} vs {away_team_id}")

                    except Exception as e:
                        print(f"❌ 比赛插入失败: {e}")
                        continue

                await db.commit()
                print(f"✅ 纯SQL保存成功: {data_result['date']} - {saved_count} 场比赛")
                return saved_count

        except Exception as e:
            print(f"❌ 纯SQL保存失败: {e}")
            raise

    async def run_production_backfill(self, start_date: str = "2022-01-01", days: int = 10):
        """运行生产级回填"""
        print("🚀 Lead Developer Production Backfill Starting...")
        print("=" * 60)

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")

        total_saved = 0
        for i in range(days):
            date_str = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")

            print(f"\n📅 [{i+1:2}/{days}] 处理日期: {date_str}")

            # 收集数据
            data_result = await self.collect_football_data(date_str)

            if not data_result['success']:
                print(f"❌ 数据收集失败: {data_result['errors']}")
                continue

            print(f"✅ 收集到 {data_result['total_matches']} 场比赛")

            # 保存数据
            saved_count = await self.save_with_production_sql(data_result)
            total_saved += saved_count
            print(f"✅ 保存了 {saved_count} 场比赛")

            # 智能延迟
            if i < days - 1:
                delay = random.uniform(self.min_delay, self.max_delay)
                print(f"⏱️ 智能延迟 {delay:.1f} 秒...")
                await asyncio.sleep(delay)

        print("\n" + "=" * 60)
        print(f"🎉 Production Backfill 完成!")
        print(f"📊 总共保存: {total_saved} 场比赛")
        print("=" * 60)


async def main():
    """主函数 - Lead Developer Production Deployment"""
    print("🚀 启动Lead Developer Production回填服务...")

    service = ProductionBackfillService()

    try:
        await service.run_production_backfill(start_date="2022-01-01", days=5)
    except Exception as e:
        print(f"❌ Production回填失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())