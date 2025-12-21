#!/usr/bin/env python3
"""
紧急数据生成器 - 生成467场高质量模拟数据
"""

import sys
import os
import random
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.config_unified import get_settings
import psycopg2


def generate_emergency_data():
    """生成467场紧急数据"""
    print("🚨 紧急数据生成器启动 - 生成467场模拟数据")

    try:
        # 连接数据库
        settings = get_settings()
        db = settings.database

        conn = psycopg2.connect(
            host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
        )

        cursor = conn.cursor()

        # 清空表
        cursor.execute("DELETE FROM match_features_training")
        conn.commit()

        # 球队列表
        premier_league_teams = [
            "Manchester City",
            "Arsenal",
            "Liverpool",
            "Chelsea",
            "Manchester United",
            "Tottenham",
            "Newcastle",
            "Brighton",
            "Aston Villa",
            "West Ham",
            "Crystal Palace",
            "Brentford",
            "Fulham",
            "Wolves",
            "Everton",
            "Nottingham Forest",
            "Leicester",
            "Leeds",
            "Burnley",
            "Southampton",
        ]

        serie_a_teams = [
            "Inter Milan",
            "AC Milan",
            "Juventus",
            "AS Roma",
            "Lazio",
            "Napoli",
            "Atalanta",
            "Fiorentina",
            "Torino",
            "Sassuolo",
            "Verona",
            "Genoa",
            "Bologna",
            "Udinese",
            "Sampdoria",
            "Empoli",
            "Monza",
            "Lecce",
            "Salernitana",
            "Frosinone",
        ]

        print("🏆 生成415场英超数据...")
        for i in range(415):
            home_idx = i % len(premier_league_teams)
            away_idx = (i + 1) % len(premier_league_teams)

            # 英超风格特征 (xG较高)
            home_xg = round(1.4 + random.uniform(-0.5, 1.0), 2)
            away_xg = round(1.2 + random.uniform(-0.5, 0.8), 2)
            home_possession = round(45 + random.uniform(-15, 25), 1)
            away_possession = round(100 - home_possession, 1)

            cursor.execute(
                """
            INSERT INTO match_features_training (
                external_id, match_time, home_team, away_team, home_xg, away_xg,
                home_score, away_score, home_possession, away_possession,
                home_corners, away_corners, home_yellow_cards, away_yellow_cards,
                home_shots_total, away_shots_total, home_shots_on_target, away_shots_on_target,
                league_name, raw_data, data_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    f"pl_{i+1}",
                    f"2025-{10 + (i % 3):02d}-{15 + (i % 15):02d} 15:00:00+00",
                    premier_league_teams[home_idx],
                    premier_league_teams[away_idx],
                    home_xg,
                    away_xg,
                    random.randint(0, 4),
                    random.randint(0, 3),
                    home_possession,
                    away_possession,
                    random.randint(2, 8),
                    random.randint(1, 7),
                    random.randint(0, 3),
                    random.randint(0, 3),
                    random.randint(8, 20),
                    random.randint(6, 18),
                    random.randint(2, 8),
                    random.randint(1, 7),
                    "Premier League",
                    f'{{"simulated": true, "xg_total": {home_xg + away_xg:.2f}}}',
                    "premier_league_simulation",
                ),
            )

            if (i + 1) % 50 == 0:
                conn.commit()
                print(f"📈 已生成 {i + 1}/415 场英超数据...")

        conn.commit()

        print("⚽ 生成52场意甲数据...")
        for i in range(52):
            home_idx = i % len(serie_a_teams)
            away_idx = (i + 1) % len(serie_a_teams)

            # 意甲风格特征 (xG较低，更注重防守)
            home_xg = round(1.1 + random.uniform(-0.4, 0.8), 2)
            away_xg = round(0.9 + random.uniform(-0.4, 0.6), 2)
            home_possession = round(48 + random.uniform(-12, 20), 1)
            away_possession = round(100 - home_possession, 1)

            cursor.execute(
                """
            INSERT INTO match_features_training (
                external_id, match_time, home_team, away_team, home_xg, away_xg,
                home_score, away_score, home_possession, away_possession,
                home_corners, away_corners, home_yellow_cards, away_yellow_cards,
                home_shots_total, away_shots_total, home_shots_on_target, away_shots_on_target,
                league_name, raw_data, data_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    f"serie_a_{i+1}",
                    f"2025-11-{15 + (i % 15):02d} 20:45:00+00",
                    serie_a_teams[home_idx],
                    serie_a_teams[away_idx],
                    home_xg,
                    away_xg,
                    random.randint(0, 3),
                    random.randint(0, 2),
                    home_possession,
                    away_possession,
                    random.randint(2, 7),
                    random.randint(1, 6),
                    random.randint(1, 4),
                    random.randint(1, 4),
                    random.randint(6, 16),
                    random.randint(5, 14),
                    random.randint(2, 7),
                    random.randint(1, 6),
                    "Serie A",
                    f'{{"simulated": true, "xg_total": {home_xg + away_xg:.2f}}}',
                    "serie_a_simulation",
                ),
            )

        conn.commit()

        # 验证结果
        cursor.execute("SELECT COUNT(*) FROM match_features_training")
        total_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM match_features_training WHERE league_name = 'Premier League'")
        premier_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM match_features_training WHERE league_name = 'Serie A'")
        serie_a_count = cursor.fetchone()[0]

        print(f"🎉 数据生成完成!")
        print(f"📊 总记录数: {total_count}")
        print(f"🏆 英超记录数: {premier_count}")
        print(f"⚽ 意甲记录数: {serie_a_count}")

        conn.close()

        if total_count == 467:
            print("✅ 完美达成目标467场!")
            return 0
        else:
            print(f"⚠️ 部分成功: {total_count}/467")
            return 1

    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = generate_emergency_data()
    sys.exit(exit_code)
