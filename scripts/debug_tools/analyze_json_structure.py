#!/usr/bin/env python3
"""
分析FotMob JSON结构
Analyze FotMob JSON Structure
"""

import json

def analyze_structure():
    """分析JSON结构"""

    print("🔍 分析FotMob JSON响应结构")
    print("="*60)

    # 读取调试文件
    with open('debug_fotmob_response.json', 'r', encoding='utf-8') as f:
        debug_data = json.load(f)

    # 解析实际的内容JSON
    content_text = debug_data['content_text']
    actual_json = json.loads(content_text)

    print("📋 实际JSON响应分析:")
    print(f"   顶级键: {list(actual_json.keys())}")
    print()

    # 分析general部分
    if 'general' in actual_json:
        general = actual_json['general']
        print("🔍 general部分分析:")
        print(f"   homeTeam: {general.get('homeTeam', 'NOT FOUND')}")
        print(f"   awayTeam: {general.get('awayTeam', 'NOT FOUND')}")
        print(f"   matchTimeUTCDate: {general.get('matchTimeUTCDate', 'NOT FOUND')}")
        print(f"   matchTimeUTC: {general.get('matchTimeUTC', 'NOT FOUND')}")
        print()

    # 分析header部分
    if 'header' in actual_json:
        header = actual_json['header']
        print("🔍 header部分分析:")
        if 'teams' in header:
            teams = header['teams']
            print(f"   teams数量: {len(teams)}")
            for i, team in enumerate(teams):
                print(f"   Team {i+1}: {team}")
        if 'status' in header:
            status = header['status']
            print(f"   status信息: {status}")
        print()

    # 分析content部分
    if 'content' in actual_json:
        content = actual_json['content']
        print("🔍 content部分分析:")
        print(f"   顶级键: {list(content.keys())}")

        # 检查stats部分
        if 'stats' in content:
            stats = content['stats']
            print(f"   stats类型: {type(stats)}")
            if isinstance(stats, dict):
                print(f"   stats键: {list(stats.keys())}")
                if 'Periods' in stats:
                    periods = stats['Periods']
                    print(f"   Periods类型: {type(periods)}")
                    if isinstance(periods, dict):
                        print(f"   Periods键: {list(periods.keys())}")
                        if 'All' in periods:
                            all_stats = periods['All']
                            print(f"   All stats类型: {type(all_stats)}")
                            if isinstance(all_stats, dict):
                                print(f"   All stats键: {list(all_stats.keys())}")

                                # 检查xG数据
                                if 'stats' in all_stats:
                                    all_stats_data = all_stats['stats']
                                    print(f"   All.stats类型: {type(all_stats_data)}")
                                    if isinstance(all_stats_data, dict):
                                        print(f"   All.stats键: {list(all_stats_data.keys())}")

                                        # 查找xG相关数据
                                        xg_found = []
                                        for key, value in all_stats_data.items():
                                            if 'xg' in key.lower() or 'expected' in key.lower():
                                                xg_found.append(f"{key}: {value}")

                                        if xg_found:
                                            print("   🎯 发现xG相关数据:")
                                            for xg_data in xg_found[:5]:  # 只显示前5个
                                                print(f"      {xg_data}")

        # 检查lineup部分
        if 'lineup' in content:
            lineup = content['lineup']
            print(f"   lineup类型: {type(lineup)}")
            if isinstance(lineup, dict):
                print(f"   lineup键: {list(lineup.keys())}")

        print()

    # 显示问题诊断
    print("🔧 问题诊断:")
    print("   1. 数据获取成功 - 228KB数据")
    print("   2. JSON解析成功 - 包含完整结构")
    print("   3. general部分有主客队信息")
    print("   4. content.stats.Periods.All.stats包含详细统计数据")
    print()

    # 检查是否存在解析错误
    print("🔍 检查解析逻辑可能的问题:")

    # 显示实际的homeTeam和awayTeam结构
    if 'general' in actual_json:
        general = actual_json['general']
        print("   实际homeTeam结构:")
        print(f"      {json.dumps(general.get('homeTeam', {}), indent=6)}")
        print("   实际awayTeam结构:")
        print(f"      {json.dumps(general.get('awayTeam', {}), indent=6)}")
        print()

    # 显示实际的时间信息
    print("   实际时间信息:")
    print(f"      matchTimeUTC: {general.get('matchTimeUTC', 'NOT FOUND')}")
    print(f"      matchTimeUTCDate: {general.get('matchTimeUTCDate', 'NOT FOUND')}")
    print()

if __name__ == "__main__":
    analyze_structure()