#!/usr/bin/env python3
"""
数据洁癖审计师 - 提取真实xG样本
直接查看包含xG数据的实际记录
"""

import asyncio
import asyncpg
import json


async def extract_real_xg_samples():
    conn = await asyncpg.connect("postgresql://postgres:postgres-dev-password@db:5432/football_prediction")

    print("🔍 数据洁癖审计师 - 提取真实xG样本")
    print("="*60)

    # 查找包含xg关键词的记录
    xg_matches = await conn.fetch("""
        SELECT id, home_score, away_score, stats, match_date
        FROM matches
        WHERE status IN ('completed', 'finished')
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND stats IS NOT NULL
          AND stats != 'null'
          AND stats::text ILIKE '%xg%'
        ORDER BY match_date
        LIMIT 10
    """)

    print(f"📊 找到 {len(xg_matches)} 条包含明确xG字段的记录")

    valid_samples = 0

    for i, match in enumerate(xg_matches):
        print(f"\n--- 样本 {i+1} (ID: {match['id']}) ---")
        print(f"比分: {match['home_score']}-{match['away_score']}")
        print(f"日期: {match['match_date']}")

        try:
            stats_data = json.loads(match['stats'])

            # 直接查找xg_home和xg_away
            xg_home = None
            xg_away = None

            if isinstance(stats_data, dict):
                if 'xg_home' in stats_data:
                    xg_home = stats_data['xg_home']
                if 'xg_away' in stats_data:
                    xg_away = stats_data['xg_away']

                # 如果直接找不到，递归搜索
                if xg_home is None or xg_away is None:
                    def find_xg_fields(obj, depth=0):
                        if depth > 5:  # 防止过深递归
                            return None, None
                        if isinstance(obj, dict):
                            local_xg_home = obj.get('xg_home')
                            local_xg_away = obj.get('xg_away')
                            if local_xg_home is not None or local_xg_away is not None:
                                return local_xg_home, local_xg_away
                            for key, value in obj.items():
                                if isinstance(value, dict):
                                    h, a = find_xg_fields(value, depth + 1)
                                    if h is not None or a is not None:
                                        return h, a
                        elif isinstance(obj, list):
                            for item in obj:
                                if isinstance(item, dict):
                                    h, a = find_xg_fields(item, depth + 1)
                                    if h is not None or a is not None:
                                        return h, a
                        return None, None

                    found_h, found_a = find_xg_fields(stats_data)
                    if found_h is not None:
                        xg_home = found_h
                    if found_a is not None:
                        xg_away = found_a

            print(f"xG Home: {xg_home}")
            print(f"xG Away: {xg_away}")

            # 验证数据
            if (xg_home is not None and xg_away is not None and
                isinstance(xg_home, (int, float)) and isinstance(xg_away, (int, float)) and
                xg_home >= 0 and xg_away >= 0):
                valid_samples += 1
                print(f"✅ 有效xG数据!")
            else:
                print(f"❌ 无效xG数据")

            # 显示stats的部分结构
            if isinstance(stats_data, dict):
                print(f"Stats键: {list(stats_data.keys())[:5]}")
            else:
                print(f"Stats类型: {type(stats_data)}")

        except Exception as e:
            print(f"❌ 解析失败: {e}")

    print(f"\n📊 总结:")
    print(f"   搜索到的记录: {len(xg_matches)}")
    print(f"   有效xG样本: {valid_samples}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(extract_real_xg_samples())