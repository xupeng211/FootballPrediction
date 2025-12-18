"""
调试DataFrame列名
"""

    """调试实际创建的DataFrame列名"""
    try:
        conn = psycopg2.connect(DATABASE_URL)

        # 提取数据
        query = """
        """

        data = pd.read_sql_query(query, conn)
        print(f"📊 原始数据列: {list(data.columns)}")

        # 解析JSON字段
        stats_features = []
        lineups_features = []
        odds_features = []

        for _idx, row in data.iterrows():
            # 解析stats
            stats_data = {}
            if row['stats']:
                try:
                    stats_json = json.loads(row['stats']) if isinstance(row['stats'], str) else row['stats']
                except:
                    stats_json = {}

                # 提取xG数据
                home_xg = stats_json.get('home_xg')
                away_xg = stats_json.get('away_xg')

                stats_data['home_xg'] = float(home_xg) if home_xg is not None else 0.0
                stats_data['away_xg'] = float(away_xg) if away_xg is not None else 0.0
                stats_data['xg_difference'] = stats_data['home_xg'] - stats_data['away_xg']
                stats_data['has_xg_data'] = home_xg is not None and away_xg is not None

                stats_features.append(stats_data)

            # 解析lineups
            lineup_data = {}
            if row['lineups']:
                try:
                    lineup_json = json.loads(row['lineups']) if isinstance(row['lineups'], str) else row['lineups']
                except:
                    lineup_json = {}

                lineup_data['has_lineups'] = bool(lineup_json)
                lineup_features.append(lineup_data)

            # 解析odds
            odds_data = {}
            if row['odds']:
                try:
                    odds_json = json.loads(row['odds']) if isinstance(row['odds'], str) else row['odds']
                except:
                    odds_json = {}

                odds_data['has_odds'] = bool(odds_json)
                odds_features.append(odds_data)

        # 创建特征DataFrame
        stats_df = pd.DataFrame(stats_features)
        lineups_df = pd.DataFrame(lineups_features)
        odds_df = pd.DataFrame(odds_features)

        print(f"📈 Stats特征列: {list(stats_df.columns)}")
        print(f"👥 Lineups特征列: {list(lineups_df.columns)}")
        print(f"💰 Odds特征列: {list(odds_df.columns)}")

        # 合并数据
        result_df = data.reset_index(drop=True)
        result_df = pd.concat([result_df, stats_df, lineups_df, odds_df], axis=1)

        print(f"🔗 合并后列: {list(result_df.columns)}")
        print(f"📊 DataFrame形状: {result_df.shape}")

        # 检查has_xg_data列
        if 'has_xg_data' in result_df.columns:
            print(f"✅ has_xg_data列存在，值分布: {result_df['has_xg_data'].value_counts().to_dict()}")
        else:
            print("❌ has_xg_data列不存在")

        conn.close()

    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_columns()


# 标准库导入
import json
import sys

# 第三方库导入
from pathlib import Path
import pandas as pd
import psycopg2


#!/usr/bin/env python3
# 添加项目根路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
DATABASE_URL = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
def debug_columns():
            SELECT
                id,
                fotmob_id,
                home_team_id,
                away_team_id,
                home_score,
                away_score,
                status,
                match_date,
                data_completeness,
                stats,
                lineups,
                odds,
                match_metadata,
                created_at,
                updated_at,
                (SELECT name FROM teams WHERE id = home_team_id) as home_team_name,
                (SELECT name FROM teams WHERE id = away_team_id) as away_team_name
            FROM matches
            WHERE data_completeness = 'complete'
            AND home_score IS NOT NULL
            AND away_score IS NOT NULL
            ORDER BY match_date DESC
            LIMIT 5