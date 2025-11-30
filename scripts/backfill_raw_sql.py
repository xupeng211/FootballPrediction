#!/usr/bin/env python3
"""
纯SQL版本的数据回填脚本 - 完全绕过ORM
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import random

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database.base import get_async_db
from src.collectors.football_data_collector import FootballDataCollector
from src.data.collectors.base_collector import BaseCollector


class RawSQLBackfillService:
    """纯SQL数据回填服务"""

    def __init__(self):
        self.football_collector = FootballDataCollector()
        self.fotmob_collector = BaseCollector()
        self.min_delay = 1.0
        self.max_delay = 3.0

    async def collect_daily_data(self, date_str: str, sources: List[str] = None) -> Dict[str, Any]:
        """收集每日数据"""
        sources = sources or ['all']

        result = {
            'date': date_str,
            'football_data_matches': [],
            'fotmob_matches': [],
            'success': False,
            'total_matches': 0,
            'errors': []
        }

        try:
            # 收集Football-Data.org数据
            if 'all' in sources or 'football-data' in sources:
                matches_result = await self.football_collector.collect_matches(date=date_str)
                if matches_result.success:
                    result['football_data_matches'] = matches_result.data.get("matches", [])
                else:
                    result['errors'].append(f"Football-Data.org收集失败: {matches_result.error}")

            # 收集FotMob数据
            if 'all' in sources or 'fotmob' in sources:
                fotmob_result = await self.fotmob_collector.collect_matches_by_date(date_str)
                if fotmob_result.success:
                    result['fotmob_matches'] = fotmob_result.data.get("matches", [])
                else:
                    result['errors'].append(f"FotMob收集失败: {fotmob_result.error}")

            result['total_matches'] = len(result['football_data_matches']) + len(result['fotmob_matches'])
            result['success'] = result['total_matches'] > 0 or len(result['errors']) == 0

        except Exception as e:
            result['errors'].append(f"数据收集异常: {e}")

        return result

    async def save_with_raw_sql(self, data_result: Dict[str, Any]) -> int:
        """使用纯SQL保存数据"""
        try:
            async for db in get_async_db():
                saved_count = 0
                all_teams_to_save = set()

                # 收集所有球队
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

                for match_data in data_result['fotmob_matches']:
                    home_team = match_data.get('home', {})
                    away_team = match_data.get('away', {})

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

                # 纯SQL插入球队
                if all_teams_to_save:
                    print(f"🏆 纯SQL保存 {len(all_teams_to_save)} 个球队...")

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
                                print(f"❌ 球队插入失败 {team_id}: {e}")

                # 纯SQL插入比赛
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

                # 处理FotMob比赛
                for match_data in data_result['fotmob_matches']:
                    try:
                        match_info = match_data.get('matchInfo', {})
                        if not match_info:
                            continue

                        home_team = match_data.get('home', {})
                        away_team = match_data.get('away', {})

                        home_team_id = home_team.get('id', 0)
                        away_team_id = away_team.get('id', 0)

                        if home_team_id == 0 or away_team_id == 0:
                            continue

                        # 解析日期
                        match_date_str = match_info.get('startDate', {}).get('ts', None)
                        if not match_date_str:
                            match_date_str = match_info.get('time', {}).get('longTs', None)

                        if not match_date_str:
                            continue

                        try:
                            raw_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                            match_date = raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date
                        except ValueError:
                            try:
                                raw_date = datetime.strptime(match_date_str, '%d.%m.%Y %H:%M')
                                match_date = raw_date
                            except ValueError:
                                timestamp = int(match_date_str) / 1000
                                match_date = datetime.fromtimestamp(timestamp)

                        # 获取比分
                        status_str = match_info.get('status', {}).get('scoreStr', '0-0')
                        if isinstance(status_str, str) and ':' in status_str:
                            scores = status_str.split(':')
                            home_score_val = int(scores[0])
                            away_score_val = int(scores[1])
                        else:
                            home_score_val = 0
                            away_score_val = 0

                        status = 'CANCELLED' if match_info.get('status', {}).get('cancelled', False) else ('FINISHED' if ':' in status_str and status_str != '0-0' else 'SCHEDULED')

                        await db.execute(sql_match, {
                            'home_team_id': home_team_id,
                            'away_team_id': away_team_id,
                            'home_score': home_score_val,
                            'away_score': away_score_val,
                            'match_date': match_date,
                            'status': status,
                            'league_id': 0,
                            'season': data_result['date'][:4]
                        })

                        saved_count += 1
                        print(f"✅ FotMob比赛插入成功: {home_team_id} vs {away_team_id}")

                    except Exception as e:
                        print(f"❌ FotMob比赛插入失败: {e}")

                await db.commit()
                print(f"✅ 纯SQL保存成功: {data_result['date']} - {saved_count} 场比赛")
                return saved_count

        except Exception as e:
            print(f"❌ 纯SQL保存失败: {e}")
            raise

    async def run_backfill(self, start_date: str = "2022-01-01", days: int = 5):
        """运行回填"""
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")

        for i in range(days):
            date_str = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")

            print(f"\n📅 处理日期: {date_str}")

            # 收集数据
            data_result = await self.collect_daily_data(date_str, ['all'])

            if not data_result['success']:
                print(f"❌ 数据收集失败: {data_result['errors']}")
                continue

            print(f"✅ 收集到 {data_result['total_matches']} 场比赛")

            # 保存数据
            saved_count = await self.save_with_raw_sql(data_result)
            print(f"✅ 保存了 {saved_count} 场比赛")

            # 延迟
            if i < days - 1:
                delay = random.uniform(self.min_delay, self.max_delay)
                print(f"⏱️ 等待 {delay:.1f} 秒...")
                await asyncio.sleep(delay)


from datetime import timedelta

async def main():
    """主函数"""
    print("🚀 启动纯SQL数据回填服务...")

    service = RawSQLBackfillService()

    try:
        await service.run_backfill(start_date="2022-01-01", days=3)
        print("\n🎉 纯SQL回填完成!")
    except Exception as e:
        print(f"❌ 回填失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())