#!/usr/bin/env python3
"""
从stats数据中提取真实比分的脚本
"""

import psycopg2
import json
import pandas as pd
import sys
from pathlib import Path

# 添加项目根路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

DATABASE_URL = (
    "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
)


def extract_real_scores():
    """从stats字段中提取真实比分"""
    try:
        conn = psycopg2.connect(DATABASE_URL)

        # 获取包含完整数据的比赛
        query = """
            SELECT fotmob_id, stats, home_score, away_score,
                   ht.name as home_team_name, at.name as away_team_name
            FROM matches m
            LEFT JOIN teams ht ON m.home_team_id = ht.id
            LEFT JOIN teams at ON m.away_team_id = at.id
            WHERE m.data_completeness = 'complete'
            LIMIT 10
        """

        df = pd.read_sql_query(query, conn)
        print(f"📊 检查 {len(df)} 场比赛的比分数据")
        print("=" * 80)

        for idx, row in df.iterrows():
            print(
                f"\n⚽ 比赛 {idx + 1}: {row['home_team_name']} vs {row['away_team_name']}"
            )
            print(f"   数据库比分: {row['home_score']}:{row['away_score']}")

            # 解析stats数据
            if row["stats"]:
                try:
                    if isinstance(row["stats"], str):
                        stats_data = json.loads(row["stats"])
                    else:
                        stats_data = row["stats"]

                    # 寻找比分信息
                    real_score = None

                    # 方法1：查找general字段中的比分
                    if "general" in stats_data:
                        general = stats_data["general"]
                        if "homeTeam" in general and "awayTeam" in general:
                            home_score = general["homeTeam"].get("score")
                            away_score = general["awayTeam"].get("score")
                            if home_score is not None and away_score is not None:
                                real_score = f"{home_score}:{away_score}"

                    # 方法2：查找infoBox中的比分
                    if not real_score and "infoBox" in stats_data:
                        info_box = stats_data["infoBox"]
                        if isinstance(info_box, list):
                            for item in info_box:
                                if "title" in item and "FT" in str(item["title"]):
                                    # 寻找比分格式
                                    if "value" in item:
                                        score_str = str(item["value"])
                                        if ":" in score_str or "-" in score_str:
                                            real_score = score_str

                    # 方法3：查找events中的最终比分
                    if not real_score and "events" in stats_data:
                        stats_data["events"]
                        # 这里可以查找比赛结束事件中的比分信息

                    # 方法4：查找match相关字段
                    score_fields = [
                        "homeScore",
                        "awayScore",
                        "score",
                        "result",
                        "finalScore",
                    ]
                    for field in score_fields:
                        if field in stats_data:
                            print(f"   发现比分字段: {field} = {stats_data[field]}")

                    # 检查teamForm或其他字段
                    if "teamForm" in stats_data:
                        team_form = stats_data["teamForm"]
                        print(f"   TeamForm数据类型: {type(team_form)}")

                    if real_score:
                        print(f"   ✅ 发现真实比分: {real_score}")
                    else:
                        print("   ❌ 未能找到真实比分")

                    # 显示stats字段的主要键
                    main_keys = list(stats_data.keys())[:10]
                    print(f"   Stats主要字段: {main_keys}")

                except Exception as e:
                    print(f"   ❌ Stats解析失败: {e}")
            else:
                print("   ❌ 无Stats数据")

            print("-" * 60)

        conn.close()

    except Exception as e:
        print(f"❌ 检查失败: {e}")


if __name__ == "__main__":
    extract_real_scores()
