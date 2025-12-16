#!/usr/bin/env python3
"""
生成真实感的模拟数据
基于真实的足球统计规律生成高质量的模拟比赛数据
"""

import asyncio
import random
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import psycopg2
from psycopg2.extras import execute_values

# 数据库连接 (Docker容器内)
DB_CONFIG = {
    'host': 'db',
    'port': 5432,
    'database': 'football_prediction_dev',
    'user': 'football_user',
    'password': 'football_pass'
}

class RealisticDataGenerator:
    """生成真实感的足球比赛数据"""

    def __init__(self):
        self.teams = self._get_real_teams()
        self.referees = self._get_real_referees()
        self.stadiums = self._get_real_stadiums()

    def _get_real_teams(self) -> List[Dict]:
        """获取真实球队列表"""
        return [
            {'name': 'Manchester United', 'strength': 8.5, 'league': 1},
            {'name': 'Manchester City', 'strength': 9.2, 'league': 1},
            {'name': 'Liverpool', 'strength': 8.8, 'league': 1},
            {'name': 'Chelsea', 'strength': 8.3, 'league': 1},
            {'name': 'Arsenal', 'strength': 8.6, 'league': 1},
            {'name': 'Tottenham', 'strength': 8.1, 'league': 1},
            {'name': 'Newcastle', 'strength': 7.8, 'league': 1},
            {'name': 'Leicester', 'strength': 7.2, 'league': 1},
            {'name': 'West Ham', 'strength': 7.5, 'league': 1},
            {'name': 'Everton', 'strength': 6.9, 'league': 1},
            {'name': 'Aston Villa', 'strength': 7.4, 'league': 1},
            {'name': 'Crystal Palace', 'strength': 7.1, 'league': 1},
            {'name': 'Wolves', 'strength': 6.8, 'league': 1},
            {'name': 'Fulham', 'strength': 6.6, 'league': 1},
            {'name': 'Brentford', 'strength': 7.0, 'league': 1},
            {'name': 'Brighton', 'strength': 7.3, 'league': 1},
            {'name': 'Bournemouth', 'strength': 6.5, 'league': 1},
            {'name': 'Nottingham Forest', 'strength': 6.7, 'league': 1},
            {'name': 'Sheffield United', 'strength': 6.2, 'league': 1},
            {'name': 'Burnley', 'strength': 6.4, 'league': 1},
            # 意甲球队
            {'name': 'Inter Milan', 'strength': 9.0, 'league': 2},
            {'name': 'AC Milan', 'strength': 8.7, 'league': 2},
            {'name': 'Juventus', 'strength': 8.9, 'league': 2},
            {'name': 'AS Roma', 'strength': 8.4, 'league': 2},
            {'name': 'Napoli', 'strength': 8.8, 'league': 2},
            {'name': 'Lazio', 'strength': 8.2, 'league': 2},
            {'name': 'Atalanta', 'strength': 8.5, 'league': 2},
            {'name': 'Fiorentina', 'strength': 7.9, 'league': 2},
            # 西甲球队
            {'name': 'Real Madrid', 'strength': 9.5, 'league': 3},
            {'name': 'Barcelona', 'strength': 9.3, 'league': 3},
            {'name': 'Atletico Madrid', 'strength': 8.7, 'league': 3},
            {'name': 'Sevilla', 'strength': 8.1, 'league': 3},
            {'name': 'Real Sociedad', 'strength': 7.8, 'league': 3},
            {'name': 'Villarreal', 'strength': 8.0, 'league': 3},
            # 德甲球队
            {'name': 'Bayern Munich', 'strength': 9.4, 'league': 4},
            {'name': 'Borussia Dortmund', 'strength': 8.8, 'league': 4},
            {'name': 'RB Leipzig', 'strength': 8.6, 'league': 4},
            {'name': 'Bayer Leverkusen', 'strength': 8.7, 'league': 4},
            {'name': 'Eintracht Frankfurt', 'strength': 7.9, 'league': 4},
        ]

    def _get_real_referees(self) -> List[str]:
        """获取真实裁判列表"""
        return [
            'Michael Oliver', 'Anthony Taylor', 'Craig Pawson', 'Paul Tierney',
            'Martin Atkinson', 'Stuart Attwell', 'Michael Salisbury', 'David Coote',
            'Robert Jones', 'John Brooks', 'Simon Hooper', 'Jarred Gillett',
            'Andre Marriner', 'Lee Mason', 'Chris Kavanagh', 'Peter Bankes'
        ]

    def _get_real_stadiums(self) -> List[str]:
        """获取真实体育场列表"""
        return [
            'Old Trafford', 'Etihad Stadium', 'Anfield', 'Stamford Bridge', 'Emirates Stadium',
            'Tottenham Hotspur Stadium', 'King Power Stadium', 'Selhurst Park', 'Villa Park',
            'Goodison Park', 'London Stadium', 'Molineux Stadium', 'St. Mary\'s Stadium',
            'The Amex Stadium', 'Old Trafford', 'Vitality Stadium', 'Bramall Lane',
            'Turf Moor', 'Stadio San Siro', 'Stadio Giuseppe Meazza', 'Allianz Arena',
            'Signal Iduna Park', 'Santiago Bernabeu', 'Camp Nou', 'Wanda Metropolitano'
        ]

    def _generate_team_ratings(self, team: Dict, is_home: bool = True) -> Dict:
        """生成球队评分 - Phase 8核心特征"""
        base_strength = team['strength']

        # 主场优势
        home_advantage = 0.2 if is_home else -0.2

        # 首发评分 (6-10范围)
        xi_rating = min(10.0, max(6.0, base_strength + random.uniform(-0.3, 0.3) + home_advantage))

        # 球星评分通常比首发略高
        star_rating = min(10.0, max(6.0, xi_rating + random.uniform(0.1, 0.5)))

        # 替补评分通常比首发低
        bench_rating = max(6.0, xi_rating - random.uniform(0.3, 1.0))

        return {
            'xi_rating': round(xi_rating, 2),
            'star_rating': round(star_rating, 2),
            'bench_rating': round(bench_rating, 2)
        }

    def _simulate_match_result(self, home_team: Dict, away_team: Dict) -> Tuple[int, int, int, int]:
        """基于球队实力模拟比赛结果"""
        home_strength = home_team['strength']
        away_strength = away_team['strength']

        # 基础期望值
        home_expected = home_strength / (home_strength + away_strength)

        # 加入随机性
        home_prob = home_expected + random.uniform(-0.15, 0.15)
        home_prob = max(0.1, min(0.9, home_prob))  # 限制在10%-90%之间

        # 模拟比赛结果
        home_win = random.random() < home_prob

        if home_win:
            # 主队获胜
            if random.random() < 0.7:  # 70%概率小胜
                home_score = random.randint(1, 3)
                away_score = random.randint(0, home_score - 1)
            else:  # 30%概率大胜
                home_score = random.randint(3, 6)
                away_score = random.randint(0, 2)
        else:
            # 客队不败
            if random.random() < 0.6:  # 60%概率客队小胜或平局
                away_score = random.randint(1, 2)
                home_score = random.randint(0, away_score)
            else:  # 40%概率客队大胜
                away_score = random.randint(3, 5)
                home_score = random.randint(0, 1)

        # 模拟半场比分
        home_ht = min(home_score, random.randint(0, max(1, home_score - 1)))
        away_ht = min(away_score, random.randint(0, max(1, away_score - 1)))

        # 红牌模拟 (相对少见)
        home_reds = 1 if random.random() < 0.08 else 0  # 8%概率
        away_reds = 1 if random.random() < 0.08 else 0  # 8%概率
        if random.random() < 0.02:  # 2%概率第二张红牌
            if home_reds == 1 and random.random() < 0.5:
                home_reds = 2
            elif away_reds == 1:
                away_reds = 2

        return home_score, away_score, home_ht, away_ht, home_reds, away_reds

    def generate_matches(self, num_matches: int = 1000) -> List[Dict]:
        """生成比赛数据"""
        matches = []

        # 生成分配给不同联赛的比赛
        league_distribution = {
            1: num_matches // 5,  # 英超 20%
            2: num_matches // 10, # 意甲 10%
            3: num_matches // 10, # 西甲 10%
            4: num_matches // 20, # 德甲 5%
        }

        start_date = datetime(2024, 8, 1)  # 赛季开始

        for i in range(num_matches):
            # 随机选择联赛
            if random.random() < 0.5:  # 50%概率英超
                league_id = 1
                season = "2024-25"
                available_teams = [t for t in self.teams if t['league'] == 1]
            elif random.random() < 0.7:  # 剩余中25%概率意甲
                league_id = 2
                season = "2024-25"
                available_teams = [t for t in self.teams if t['league'] == 2]
            elif random.random() < 0.85:  # 剩余中50%概率西甲
                league_id = 3
                season = "2024-25"
                available_teams = [t for t in self.teams if t['league'] == 3]
            else:  # 剩余概率德甲
                league_id = 4
                season = "2024-25"
                available_teams = [t for t in self.teams if t['league'] == 4]

            # 选择主客队
            home_team = random.choice(available_teams)
            away_team = random.choice([t for t in available_teams if t['name'] != home_team['name']])

            # 生成比赛日期（赛季内随机分布）
            days_offset = random.randint(0, 120)  # 赛季前4个月
            match_date = start_date + timedelta(days=days_offset)
            match_date += timedelta(hours=random.randint(14, 21))  # 比赛时间

            # 模拟比赛结果
            home_score, away_score, home_ht, away_ht, home_reds, away_reds = self._simulate_match_result(home_team, away_team)

            # Phase 8 核心特征 - Player Ratings
            home_ratings = self._generate_team_ratings(home_team, is_home=True)
            away_ratings = self._generate_team_ratings(away_team, is_home=False)

            match = {
                'home_team_name': home_team['name'],
                'away_team_name': away_team['name'],
                'league_id': league_id,
                'season': season,
                'match_date': match_date.strftime('%Y-%m-%d %H:%M:%S'),
                'home_score': home_score,
                'away_score': away_score,
                'home_goals_ht': home_ht,
                'away_goals_ht': away_ht,
                'match_status': 'finished',

                # Phase 8 Player Ratings特征 (🎯 核心!)
                'home_xi_rating': home_ratings['xi_rating'],
                'away_xi_rating': away_ratings['xi_rating'],
                'home_star_rating': home_ratings['star_rating'],
                'away_star_rating': away_ratings['star_rating'],
                'home_bench_rating': home_ratings['bench_rating'],
                'away_bench_rating': away_ratings['bench_rating'],

                # Phase 8 Metadata特征
                'referee': random.choice(self.referees),
                'stadium': random.choice(self.stadiums),
                'attendance': random.randint(30000, 80000),

                # Phase 8 纪律特征
                'home_red_cards': home_reds,
                'away_red_cards': away_reds
            }

            matches.append(match)

        # 按日期排序
        matches.sort(key=lambda x: x['match_date'])

        return matches

    def save_to_database(self, matches: List[Dict]):
        """保存数据到数据库"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        try:
            # 先确保球队和联赛数据存在
            self._ensure_teams_and_leagues(cursor)

            # 插入比赛数据
            insert_query = """
            INSERT INTO matches (
                home_team_id, away_team_id, league_id, season, match_date, match_status,
                home_score, away_score, home_goals_ht, away_goals_ht, created_at, updated_at,
                home_xi_rating, away_xi_rating, home_star_rating, away_star_rating,
                home_bench_rating, away_bench_rating, referee, stadium, attendance,
                home_red_cards, away_red_cards
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            team_name_to_id = self._get_team_name_to_id(cursor)

            values = []
            for match in matches:
                home_team_id = team_name_to_id.get(match['home_team_name'], random.randint(1, 30))
                away_team_id = team_name_to_id.get(match['away_team_name'], random.randint(1, 30))

                values.append((
                    home_team_id, away_team_id, match['league_id'], match['season'],
                    match['match_date'], match['match_status'], match['home_score'],
                    match['away_score'], match['home_goals_ht'], match['away_goals_ht'],
                    datetime.now(), datetime.now(),
                    match['home_xi_rating'], match['away_xi_rating'],
                    match['home_star_rating'], match['away_star_rating'],
                    match['home_bench_rating'], match['away_bench_rating'],
                    match['referee'], match['stadium'], match['attendance'],
                    match['home_red_cards'], match['away_red_cards']
                ))

            execute_values(cursor, insert_query, values)
            conn.commit()

            print(f"✅ 成功插入 {len(matches)} 场比赛到数据库")

        except Exception as e:
            print(f"❌ 数据库操作失败: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _ensure_teams_and_leagues(self, cursor):
        """确保球队和联赛数据存在"""
        # 确保联赛存在
        leagues_data = [
            (1, 'Premier League', 'EPL', 'England'),
            (2, 'Serie A', 'SA', 'Italy'),
            (3, 'La Liga', 'LL', 'Spain'),
            (4, 'Bundesliga', 'BL', 'Germany')
        ]

        for league_id, name, code, country in leagues_data:
            cursor.execute("""
                INSERT INTO leagues (id, league_name, league_code, country, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (league_id, name, code, country, True, datetime.now(), datetime.now()))

        # 确保球队存在
        for i, team in enumerate(self.teams, 1):
            cursor.execute("""
                INSERT INTO teams (id, team_name, team_code, country, league_id, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET team_name = EXCLUDED.team_name
            """, (i, team['name'], team['name'][:3].upper(),
                  'England' if team['league'] == 1 else 'Italy' if team['league'] == 2 else 'Spain' if team['league'] == 3 else 'Germany',
                  team['league'], True, datetime.now(), datetime.now()))

    def _get_team_name_to_id(self, cursor) -> Dict[str, int]:
        """获取球队名称到ID的映射"""
        cursor.execute("SELECT id, team_name FROM teams")
        return {name: id for id, name in cursor.fetchall()}


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成真实感的模拟足球数据')
    parser.add_argument('--matches', type=int, default=500, help='生成比赛数量')

    args = parser.parse_args()

    print("🎯 Phase 8: 生成真实感的模拟数据")
    print(f"📊 目标: 生成 {args.matches} 场比赛")

    generator = RealisticDataGenerator()

    # 生成数据
    print("🔄 生成比赛数据...")
    matches = generator.generate_matches(args.matches)

    print(f"✅ 成功生成 {len(matches)} 场比赛")

    # 显示一些统计信息
    print("\n📈 数据统计:")
    print(f"   - 平均主队xi_rating: {np.mean([m['home_xi_rating'] for m in matches]):.2f}")
    print(f"   - 平均客队xi_rating: {np.mean([m['away_xi_rating'] for m in matches]):.2f}")
    print(f"   - xi_rating差值范围: {min([abs(m['home_xi_rating'] - m['away_xi_rating']) for m in matches]):.2f} - {max([abs(m['home_xi_rating'] - m['away_xi_rating']) for m in matches]):.2f}")
    print(f"   - 平均上座率: {np.mean([m['attendance'] for m in matches]):.0f}")
    print(f"   - 主队胜率: {len([m for m in matches if m['home_score'] > m['away_score']]) / len(matches) * 100:.1f}%")

    # 保存到数据库
    print("\n💾 保存数据到数据库...")
    generator.save_to_database(matches)

    print("🎉 Phase 8 数据准备完成！可以开始模型训练了")


if __name__ == "__main__":
    asyncio.run(main())