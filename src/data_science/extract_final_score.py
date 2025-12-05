#!/usr/bin/env python3
"""
提取最终比分和关键特征的详细脚本
"""

import psycopg2
import json
import sys
from pathlib import Path

# 添加项目根路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

DATABASE_URL = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"

def extract_final_score_and_features():
    """提取最终比分和S-Tier特征"""
    try:
        conn = psycopg2.connect(DATABASE_URL)

        query = """
            SELECT fotmob_id, stats, lineups
            FROM matches
            WHERE data_completeness = 'complete'
            AND stats IS NOT NULL
            LIMIT 5
        """

        cur = conn.cursor()
        cur.execute(query)
        matches = cur.fetchall()

        print("🎯 提取最终比分和S-Tier特征")
        print("=" * 80)

        for i, (fotmob_id, stats, lineups) in enumerate(matches, 1):
            print(f"\n⚽ 比赛 {i}: ID {fotmob_id}")
            print("-" * 60)

            # 1. 提取最终比分
            final_home_score = 0
            final_away_score = 0

            if stats:
                try:
                    if isinstance(stats, str):
                        stats_data = json.loads(stats)
                    else:
                        stats_data = stats

                    # 方法1: 从events中提取最终比分
                    events = stats_data.get('events', {}).get('events', [])
                    final_scores = []

                    for event in events:
                        if 'newScore' in event:
                            score_list = event['newScore']
                            if isinstance(score_list, list) and len(score_list) == 2:
                                final_scores.append(score_list)

                    if final_scores:
                        # 取最后一个比分（最终比分）
                        final_home_score, final_away_score = final_scores[-1]
                        print(f"✅ 最终比分 (从events): {final_home_score}:{final_away_score}")

                    # 方法2: 从topPlayers中获取球队评分
                    top_players = stats_data.get('topPlayers', {})
                    if isinstance(top_players, dict):
                        print(f"📊 TopPlayers结构: {list(top_players.keys())}")

                except Exception as e:
                    print(f"❌ Stats解析失败: {e}")

            # 2. 提取红黄牌数据
            yellow_cards = {'home': 0, 'away': 0}
            red_cards = {'home': 0, 'away': 0}

            if stats:
                try:
                    events = stats_data.get('events', {}).get('events', [])
                    for event in events:
                        card_type = event.get('card')
                        team_type = event.get('teamType', '')  # home/away

                        if card_type == 'Yellow':
                            yellow_cards[team_type] += 1
                        elif card_type == 'Red':
                            red_cards[team_type] += 1

                    print(f"🟨 黄牌: 主队{yellow_cards['home']} - 客队{yellow_cards['away']}")
                    print(f"🟥 红牌: 主队{red_cards['home']} - 客队{red_cards['away']}")

                except Exception as e:
                    print(f"❌ 红黄牌提取失败: {e}")

            # 3. 提取球队评分
            home_team_rating = 0.0
            away_team_rating = 0.0

            if lineups:
                try:
                    if isinstance(lineups, str):
                        lineups_data = json.loads(lineups)
                    else:
                        lineups_data = lineups

                    # 主队数据
                    home_team = lineups_data.get('homeTeam', {})
                    away_team = lineups_data.get('awayTeam', {})

                    # 主队评分
                    if 'rating' in home_team:
                        home_team_rating = home_team['rating']
                        print(f"⭐ 主队评分: {home_team_rating}")

                    # 客队评分
                    if 'rating' in away_team:
                        away_team_rating = away_team['rating']
                        print(f"⭐ 客队评分: {away_team_rating}")

                    # 计算首发球员平均评分
                    home_starters = home_team.get('starters', [])
                    away_starters = away_team.get('starters', [])

                    home_player_ratings = []
                    away_player_ratings = []

                    for player in home_starters:
                        if isinstance(player, dict) and 'performance' in player:
                            rating = player['performance'].get('rating', 0)
                            if rating:
                                home_player_ratings.append(float(rating))

                    for player in away_starters:
                        if isinstance(player, dict) and 'performance' in player:
                            rating = player['performance'].get('rating', 0)
                            if rating:
                                away_player_ratings.append(float(rating))

                    if home_player_ratings:
                        avg_home_rating = sum(home_player_ratings) / len(home_player_ratings)
                        print(f"👥 主队首发平均评分: {avg_home_rating:.2f} (基于{len(home_player_ratings)}名球员)")

                    if away_player_ratings:
                        avg_away_rating = sum(away_player_ratings) / len(away_player_ratings)
                        print(f"👥 客队首发平均评分: {avg_away_rating:.2f} (基于{len(away_player_ratings)}名球员)")

                except Exception as e:
                    print(f"❌ 评分提取失败: {e}")

            # 4. 提取比赛环境信息
            if stats:
                try:
                    info_box = stats_data.get('infoBox', {})
                    if isinstance(info_box, dict):
                        stadium = info_box.get('Stadium', {})
                        attendance = info_box.get('Attendance', 0)
                        referee = info_box.get('Referee', {})

                        if stadium:
                            stadium_name = stadium.get('name', 'Unknown')
                            print(f"🏟️  体育场: {stadium_name}")

                        if attendance:
                            print(f"👥 上座率: {attendance:,}")

                        if referee:
                            referee_name = referee.get('text', 'Unknown')
                            print(f"👨‍⚖️  裁判: {referee_name}")

                except Exception as e:
                    print(f"❌ 环境信息提取失败: {e}")

            print("=" * 80)

        conn.close()

    except Exception as e:
        print(f"❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    extract_final_score_and_features()
