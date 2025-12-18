"""
检查实际数据结构的调试脚本
"""

    """检查数据库中的实际数据结构"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 获取包含完整数据的比赛
        cur.execute("""
        """)

        matches = cur.fetchall()

        print(f"📊 检查 {len(matches)} 场比赛的数据结构")
        print("=" * 60)

        for i, (fotmob_id, stats, lineups, odds, home_score, away_score) in enumerate(matches, 1):
            print(f"\n⚽ 比赛 {i}: ID {fotmob_id}, 比分 {home_score}:{away_score}")

            # 检查 stats 结构
            try:
                if isinstance(stats, str):
                    stats_data = json.loads(stats)
                else:
                    stats_data = stats

                print(f"📈 Stats 字段键: {list(stats_data.keys()) if isinstance(stats_data, dict) else 'Not a dict'}")

                # 递归搜索 xG 相关字段
                def find_xg_fields(data, path=""):
                    xg_fields = []
                    if isinstance(data, dict):
                        for key, value in data.items():
                            new_path = f"{path}.{key}" if path else key
                            if 'xg' in key.lower() or 'expected' in key.lower():
                                xg_fields.append((new_path, value))
                            elif isinstance(value, (dict, list)):
                                xg_fields.extend(find_xg_fields(value, new_path))
                    elif isinstance(data, list):
                        for idx, item in enumerate(data):
                            if isinstance(item, (dict, list)):
                                xg_fields.extend(find_xg_fields(item, f"{path}[{idx}]"))
                    return xg_fields

                xg_fields = find_xg_fields(stats_data)
                if xg_fields:
                    print("🎯 找到 xG 字段:")
                    for path, value in xg_fields[:5]:  # 只显示前5个
                        print(f"   {path}: {value}")
                else:
                    print("❌ 未找到 xG 相关字段")

            except Exception as e:
                print(f"❌ Stats 解析失败: {e}")

            # 检查 lineups 结构
            try:
                if isinstance(lineups, str):
                    lineups_data = json.loads(lineups)
                else:
                    lineups_data = lineups

                print(f"👥 Lineups 字段键: {list(lineups_data.keys()) if isinstance(lineups_data, dict) else 'Not a dict'}")
            except Exception as e:
                print(f"❌ Lineups 解析失败: {e}")

            # 检查 odds 结构
            try:
                if isinstance(odds, str):
                    odds_data = json.loads(odds)
                else:
                    odds_data = odds

                print(f"💰 Odds 字段键: {list(odds_data.keys()) if isinstance(odds_data, dict) else 'Not a dict'}")
            except Exception as e:
                print(f"❌ Odds 解析失败: {e}")

            print("-" * 40)

        conn.close()

    except Exception as e:
        print(f"❌ 检查失败: {e}")

if __name__ == "__main__":
    check_data_structure()


# 标准库导入
import json
import sys

# 第三方库导入
from pathlib import Path
import psycopg2


#!/usr/bin/env python3
# 添加项目根路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
DATABASE_URL = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
def check_data_structure():
            SELECT fotmob_id, stats, lineups, odds, home_score, away_score
            FROM matches
            WHERE data_completeness = 'complete'
            AND stats IS NOT NULL
            LIMIT 5