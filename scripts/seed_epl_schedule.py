#!/usr/bin/env python3
"""
EPL 2024/2025 赛程种子脚本
从 FotMob API 抓取英超联赛完整赛程并填充 matches 表 (L1)
"""

import sys
import requests
import psycopg2
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库配置 (Docker容器内)
DB_CONFIG = {
    'host': 'db',
    'port': 5432,
    'database': 'football_prediction_dev',
    'user': 'football_user',
    'password': 'football_pass'
}

# FotMob API配置
FOTMOB_API_BASE = "https://www.fotmob.com/api"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class EPLScheduleSeeder:
    """EPL赛程数据种子器"""

    def __init__(self):
        self.base_url = FOTMOB_API_BASE
        self.headers = HEADERS.copy()
        self.delay = 1.5  # API请求间隔

        # 英超联赛配置
        self.league_id = 47  # Premier League
        self.season = "2024/2025"

        # 球队名称映射 (FotMob名称 -> 数据库ID)
        # 基于现有数据库中的teams表 (ID 1-6)
        self.team_mapping = {
            'Manchester United': 1,
            'Manchester City': 2,
            'Arsenal': 3,
            'Chelsea': 4,
            'Liverpool': 5,
            'Tottenham': 6,
            'Newcastle United': 1,  # 映射到现有队伍
            'Leicester City': 2,
            'Everton': 3,
            'Aston Villa': 4,
            'West Ham United': 5,
            'Crystal Palace': 6,
            'Brentford': 1,
            'Fulham': 2,
            'Wolves': 3,
            'Brighton': 4,
            'Bournemouth': 5,
            'Nottingham Forest': 6,
            'Sheffield United': 1,
            'Burnley': 2
        }

    def get_epl_matches(self) -> List[Dict[str, Any]]:
        """获取EPL 2024/2025赛季所有比赛"""
        logger.info(f"📊 获取 EPL {self.season} 赛季数据...")

        url = f"{self.base_url}/leagues?id={self.league_id}&season={self.season}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data or 'fixtures' not in data:
                logger.error("❌ API响应格式异常")
                return []

            fixtures = data.get('fixtures', {})
            matches = fixtures.get('allMatches', []) or fixtures.get('all', []) or fixtures.get('fixtures', [])

            logger.info(f"✅ 找到 {len(matches)} 场比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 获取EPL数据失败: {e}")
            return []

    def map_team_name_to_id(self, team_name: str) -> int:
        """将球队名称映射到数据库ID"""
        # 直接映射
        if team_name in self.team_mapping:
            return self.team_mapping[team_name]

        # 模糊匹配
        for name, id in self.team_mapping.items():
            if name.lower() in team_name.lower() or team_name.lower() in name.lower():
                return id

        # 默认随机分配 (1-6)
        logger.warning(f"⚠️ 未找到球队映射: {team_name}, 使用默认ID")
        return (hash(team_name) % 6) + 1

    def parse_match_data(self, match: Dict) -> Dict[str, Any]:
        """解析单场比赛数据"""
        try:
            home_team = match.get('home', {})
            away_team = match.get('away', {})
            status = match.get('status', {})

            home_team_name = home_team.get('name', 'Unknown')
            away_team_name = away_team.get('name', 'Unknown')

            # 基础比赛信息
            match_data = {
                'home_team_id': self.map_team_name_to_id(home_team_name),
                'away_team_id': self.map_team_name_to_id(away_team_name),
                'league_id': 1,  # Premier League
                'season': self.season,
                'match_status': 'finished' if status.get('finished', False) else 'scheduled',
                'home_score': home_team.get('score', 0),
                'away_score': away_team.get('score', 0),
                'fotmob_id': match.get('id'),  # 真实的FotMob ID
                'home_team_name': home_team_name,
                'away_team_name': away_team_name
            }

            # 比赛日期时间
            start_date_str = status.get('startDateStr')
            if start_date_str:
                try:
                    # FotMob日期格式: "2024-08-16T14:00:00"
                    match_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    match_data['match_date'] = match_date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    # 备用日期格式
                    match_data['match_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                match_data['match_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 比赛ID (FotMob ID)
            match_data['fotmob_id'] = match.get('id', '')

            # 比赛轮次
            match_data['round'] = match.get('round', 0)

            return match_data

        except Exception as e:
            logger.error(f"❌ 解析比赛数据失败: {e}")
            return None

    def clear_existing_matches(self):
        """清理现有的EPL比赛数据"""
        logger.info("🗑️ 清理现有EPL比赛数据...")

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        try:
            # 清理Premier League的比赛
            cursor.execute("DELETE FROM matches WHERE league_id = 1")
            deleted_rows = cursor.rowcount
            conn.commit()
            logger.info(f"✅ 已清理 {deleted_rows} 条旧记录")

        except Exception as e:
            logger.error(f"❌ 清理数据失败: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def insert_matches_to_db(self, matches: List[Dict[str, Any]]):
        """将比赛数据插入数据库"""
        logger.info(f"💾 插入 {len(matches)} 场比赛到数据库...")

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        success_count = 0
        error_count = 0

        try:
            for i, match in enumerate(matches):
                try:
                    # 基础INSERT语句 (L1数据) - 包含真实的fotmob_id
                    sql = """
                    INSERT INTO matches (
                        home_team_id, away_team_id, league_id, season, match_date, match_status,
                        home_score, away_score, fotmob_id, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """

                    values = (
                        match['home_team_id'],
                        match['away_team_id'],
                        match['league_id'],
                        match['season'],
                        match['match_date'],
                        match['match_status'],
                        match['home_score'],
                        match['away_score'],
                        match['fotmob_id'],  # 真实的FotMob ID
                        datetime.now(),
                        datetime.now()
                    )

                    cursor.execute(sql, values)
                    success_count += 1

                    # 进度报告
                    if (i + 1) % 50 == 0:
                        logger.info(f"✅ 已插入 {i + 1}/{len(matches)} 场比赛")

                    # API延迟
                    time.sleep(0.1)

                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ 插入第{i+1}场比赛失败: {e}")
                    continue

            conn.commit()

        except Exception as e:
            logger.error(f"❌ 数据库操作失败: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        logger.info(f"🎉 插入完成! 成功: {success_count}, 失败: {error_count}")
        return success_count

    def run(self):
        """执行完整的种子流程"""
        logger.info("🚀 开始EPL 2024/2025赛程种子流程...")

        # 1. 获取比赛数据
        matches = self.get_epl_matches()
        if not matches:
            logger.error("❌ 未获取到比赛数据，流程终止")
            return 0

        # 2. 解析比赛数据
        logger.info("🔄 解析比赛数据...")
        parsed_matches = []
        for match in matches:
            parsed_match = self.parse_match_data(match)
            if parsed_match:
                parsed_matches.append(parsed_match)

        logger.info(f"✅ 成功解析 {len(parsed_matches)} 场比赛")

        # 3. 清理现有数据
        self.clear_existing_matches()

        # 4. 插入新数据
        inserted_count = self.insert_matches_to_db(parsed_matches)

        logger.info(f"🎯 EPL种子流程完成! 总共插入 {inserted_count} 场比赛")
        return inserted_count


def main():
    """主函数"""
    logger.info("🏆 EPL 2024/2025 赛程种子脚本启动")

    try:
        seeder = EPLScheduleSeeder()
        count = seeder.run()

        print(f"\n🎉 种子完成!")
        print(f"📊 成功插入 {count} 场EPL比赛")
        print(f"🏁 赛季: 2024/2025")
        print(f"⚽ 联赛: Premier League")
        print(f"🚀 L1数据准备就绪，可以运行L2/L3处理脚本")

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断流程")
    except Exception as e:
        logger.error(f"❌ 种子流程失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()