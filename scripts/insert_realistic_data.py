#!/usr/bin/env python3
"""
直接在Docker容器中插入真实感的模拟数据
"""

import sys
import random
import psycopg2
from datetime import datetime, timedelta

# 数据库连接配置 (Docker容器内)
DB_CONFIG = {
    'host': 'db',
    'port': 5432,
    'database': 'football_prediction_dev',
    'user': 'football_user',
    'password': 'football_pass'
}

def insert_realistic_data():
    """插入真实感的模拟数据"""

    # 真实球队数据
    teams = [
        {'name': 'Manchester United', 'strength': 8.5},
        {'name': 'Manchester City', 'strength': 9.2},
        {'name': 'Liverpool', 'strength': 8.8},
        {'name': 'Chelsea', 'strength': 8.3},
        {'name': 'Arsenal', 'strength': 8.6},
        {'name': 'Tottenham', 'strength': 8.1},
        {'name': 'Newcastle', 'strength': 7.8},
        {'name': 'Leicester', 'strength': 7.2},
        {'name': 'West Ham', 'strength': 7.5},
        {'name': 'Everton', 'strength': 6.9},
        {'name': 'Aston Villa', 'strength': 7.4},
        {'name': 'Crystal Palace', 'strength': 7.1},
        {'name': 'Wolves', 'strength': 6.8},
        {'name': 'Fulham', 'strength': 6.6},
        {'name': 'Brentford', 'strength': 7.0},
        {'name': 'Brighton', 'strength': 7.3},
        {'name': 'Bournemouth', 'strength': 6.5},
        {'name': 'Nottingham Forest', 'strength': 6.7},
        {'name': 'Sheffield United', 'strength': 6.2},
        {'name': 'Burnley', 'strength': 6.4},
    ]

    referees = [
        'Michael Oliver', 'Anthony Taylor', 'Craig Pawson', 'Paul Tierney',
        'Martin Atkinson', 'Stuart Attwell', 'Michael Salisbury'
    ]

    stadiums = [
        'Old Trafford', 'Etihad Stadium', 'Anfield', 'Stamford Bridge',
        'Emirates Stadium', 'Tottenham Hotspur Stadium', 'King Power Stadium',
        'Selhurst Park', 'Villa Park', 'Goodison Park'
    ]

    print("🎯 连接数据库...")

    # 连接数据库
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # 生成300场比赛数据
        matches = []
        start_date = datetime(2024, 8, 1)

        for i in range(300):
            # 选择主客队
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t['name'] != home_team['name']])

            # 模拟比赛结果
            home_strength = home_team['strength'] + 0.2  # 主场优势
            away_strength = away_team['strength'] - 0.2

            home_prob = home_strength / (home_strength + away_strength)
            home_win = random.random() < home_prob + random.uniform(-0.15, 0.15)

            if home_win:
                home_score = random.randint(1, 3) if random.random() < 0.7 else random.randint(3, 6)
                away_score = random.randint(0, max(0, home_score - 1))
            else:
                away_score = random.randint(1, 2) if random.random() < 0.6 else random.randint(3, 5)
                home_score = random.randint(0, away_score)

            # 半场比分
            home_ht = min(home_score, random.randint(0, max(1, home_score - 1)))
            away_ht = min(away_score, random.randint(0, max(1, away_score - 1)))

            # 比赛日期
            days_offset = random.randint(0, 120)
            match_date = start_date + timedelta(days=days_offset, hours=random.randint(14, 21))

            # Phase 8 Player Ratings特征
            home_xi_rating = min(10.0, max(6.0, home_team['strength'] + random.uniform(-0.3, 0.3)))
            away_xi_rating = min(10.0, max(6.0, away_team['strength'] + random.uniform(-0.3, 0.3)))

            match = {
                'home_team_id': teams.index(home_team) + 1,
                'away_team_id': teams.index(away_team) + 1,
                'league_id': 1,
                'season': '2024-25',
                'match_date': match_date,
                'match_status': 'finished',
                'home_score': home_score,
                'away_score': away_score,
                'home_goals_ht': home_ht,
                'away_goals_ht': away_ht,

                # Phase 8 Player Ratings (🎯 核心!)
                'home_xi_rating': round(home_xi_rating, 2),
                'away_xi_rating': round(away_xi_rating, 2),
                'home_star_rating': round(home_xi_rating + random.uniform(0.1, 0.5), 2),
                'away_star_rating': round(away_xi_rating + random.uniform(0.1, 0.5), 2),
                'home_bench_rating': round(max(6.0, home_xi_rating - random.uniform(0.3, 1.0)), 2),
                'away_bench_rating': round(max(6.0, away_xi_rating - random.uniform(0.3, 1.0)), 2),

                # Phase 8 Metadata
                'referee': random.choice(referees),
                'stadium': random.choice(stadiums),
                'attendance': random.randint(30000, 80000),

                # Phase 8 纪律
                'home_red_cards': 1 if random.random() < 0.08 else 0,
                'away_red_cards': 1 if random.random() < 0.08 else 0
            }

            matches.append(match)

        # 按日期排序
        matches.sort(key=lambda x: x['match_date'])

        print(f"📊 生成 {len(matches)} 场比赛数据")

              # 插入数据
        print("💾 插入数据到数据库...")

        for match in matches:
            cursor.execute("""
                INSERT INTO matches (
                    home_team_id, away_team_id, league_id, season, match_date, match_status,
                    home_score, away_score, home_goals_ht, away_goals_ht, created_at, updated_at,
                    home_xi_rating, away_xi_rating, home_star_rating, away_star_rating,
                    home_bench_rating, away_bench_rating, referee, stadium, attendance,
                    home_red_cards, away_red_cards
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match['home_team_id'], match['away_team_id'], match['league_id'],
                match['season'], match['match_date'], match['match_status'],
                match['home_score'], match['away_score'], match['home_goals_ht'],
                match['away_goals_ht'], datetime.now(), datetime.now(),
                match['home_xi_rating'], match['away_xi_rating'], match['home_star_rating'],
                match['away_star_rating'], match['home_bench_rating'], match['away_bench_rating'],
                match['referee'], match['stadium'], match['attendance'],
                match['home_red_cards'], match['away_red_cards']
            ))

        conn.commit()

        print(f"✅ 成功插入 {len(matches)} 场比赛到数据库!")

        # 显示一些统计信息
        home_xi_ratings = [m['home_xi_rating'] for m in matches]
        away_xi_ratings = [m['away_xi_rating'] for m in matches]

        print(f"\n📈 Phase 8 特征统计:")
        print(f"   - 平均主队xi_rating: {sum(home_xi_ratings)/len(home_xi_ratings):.2f}")
        print(f"   - 平均客队xi_rating: {sum(away_xi_ratings)/len(away_xi_ratings):.2f}")
        print(f"   - xi_rating差值范围: {min([abs(h-a) for h,a in zip(home_xi_ratings, away_xi_ratings)]):.2f} - {max([abs(h-a) for h,a in zip(home_xi_ratings, away_xi_ratings)]):.2f}")
        print(f"   - 主队胜率: {len([m for m in matches if m['home_score'] > m['away_score']])/len(matches)*100:.1f}%")

    finally:
        cursor.close()
        conn.close()

    print("🎉 Phase 8 真实数据准备完成!")

if __name__ == "__main__":
    insert_realistic_data()