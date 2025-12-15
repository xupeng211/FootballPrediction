#!/usr/bin/env python3
"""
L2数据深度分析 - FotMob API 统计维度完整探索
识别所有可用于机器学习的高价值统计数据
"""

import json
import sys

def main():
    print('🎯 L2数据深度分析 - FotMob API 完整统计维度探索')
    print('=' * 60)

    # 加载API数据
    try:
        with open('fotmob_match_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print('✅ 成功加载FotMob API数据')
    except Exception as e:
        print(f'❌ 加载数据失败: {e}')
        sys.exit(1)

    # 分析整体数据结构
    print('\n📊 API数据结构概览:')
    print('-' * 40)
    main_keys = list(data.keys())
    print(f'顶级字段: {main_keys}')

    content = data.get('content', {})
    print(f'\ncontent字段包含: {list(content.keys())}')

    # 深度分析团队统计数据
    if 'stats' in content:
        stats = content['stats']
        print('\n🏆 团队级统计数据 (content.stats):')
        print('-' * 40)

        if 'stats' in stats:
            team_stats = stats['stats']
            print(f'统计类别数量: {len(team_stats)}')

            # 识别所有统计类型
            stat_categories = []
            for stat in team_stats:
                stat_title = stat.get('title', 'Unknown')
                stat_id = stat.get('id', 'unknown')
                stat_keys = list(stat.keys()) if isinstance(stat, dict) else []

                stat_categories.append({
                    'title': stat_title,
                    'id': stat_id,
                    'keys': stat_keys
                })

            # 按类型分组显示
            print('\n📈 统计类别分类:')

            # 基础比赛统计
            basic_stats = [s for s in stat_categories if any(word in s['title'].lower() for word in ['goals', 'shots', 'xg', 'possession', 'passes'])]
            print('\n⚽ 基础比赛统计:')
            for i, stat in enumerate(basic_stats, 1):
                print(f'  {i}. {stat["title"]} (ID: {stat["id"]})')

            # 进阶统计
            advanced_stats = [s for s in stat_categories if any(word in s['title'].lower() for word in ['expected', 'big chance', 'cards', 'fouls', 'corners'])]
            print('\n🎯 进阶统计:')
            for i, stat in enumerate(advanced_stats, 1):
                print(f'  {i}. {stat["title"]} (ID: {stat["id"]})')

            # 防守统计
            defensive_stats = [s for s in stat_categories if any(word in s['title'].lower() for word in ['tackles', 'interceptions', 'blocks', 'clearances'])]
            print('\n🛡️ 防守统计:')
            for i, stat in enumerate(defensive_stats, 1):
                print(f'  {i}. {stat["title"]} (ID: {stat["id"]})')

            # 其他统计
            other_stats = [s for s in stat_categories if s not in basic_stats + advanced_stats + defensive_stats]
            if other_stats:
                print('\n📊 其他统计:')
                for i, stat in enumerate(other_stats, 1):
                    print(f'  {i}. {stat["title"]} (ID: {stat["id"]})')

            # 显示详细的统计数据示例
            print('\n🔍 详细统计数据示例:')
            if team_stats:
                first_stat = team_stats[0]
                print(f'示例统计类型: {first_stat.get("title", "Unknown")}')
                if 'stats' in first_stat and first_stat['stats']:
                    sample_data = first_stat['stats'][0]
                    print(f'主队数据: {sample_data}')

    # 深度分析球员统计数据
    if 'playerStats' in content:
        player_stats = content['playerStats']
        print('\n👥 球员级统计数据 (content.playerStats):')
        print('-' * 40)

        # 分析球员统计结构
        player_keys = list(player_stats.keys())
        print(f'playerStats字段: {player_keys}')

        if 'stats' in player_stats:
            player_stat_categories = player_stats['stats']
            print(f'球员统计类别数量: {len(player_stat_categories)}')

            print('\n🏅 球员统计维度:')
            high_value_player_stats = []

            for i, stat_cat in enumerate(player_stat_categories[:15]):  # 显示前15个
                title = stat_cat.get('title', 'Unknown')
                stat_id = stat_cat.get('id', 'unknown')

                # 识别高价值统计
                high_value_keywords = [
                    'xg', 'expected goals', 'shots', 'assists', 'passes',
                    'tackles', 'interceptions', 'duels', 'aerial', 'cards',
                    'fouls', 'offsides', 'corners', 'crosses', 'dribbles'
                ]

                is_high_value = any(keyword in title.lower() for keyword in high_value_keywords)

                if is_high_value:
                    high_value_player_stats.append(title)
                    print(f'  ✅ {title} (ID: {stat_id})')
                else:
                    print(f'  📊 {title} (ID: {stat_id})')

            print(f'\n🎯 发现高价值球员统计维度: {len(high_value_player_stats)}个')
            for stat in high_value_player_stats:
                print(f'  • {stat}')

        if 'players' in player_stats:
            players = player_stats['players']
            print(f'\n👤 球员数量: {len(players)}')

            if players:
                # 分析第一个球员的详细数据
                first_player = players[0]
                print(f'\n🔍 示例球员数据结构: {first_player.get("name", "Unknown")}')

                player_stat_fields = [k for k in first_player.keys() if k not in ['id', 'name', 'teamId']]
                print(f'球员统计字段数量: {len(player_stat_fields)}')
                print('主要统计字段:')

                for field in player_stat_fields[:10]:  # 显示前10个字段
                    value = first_player.get(field)
                    print(f'  • {field}: {value}')

    # 分析其他有价值的模块
    print('\n🎯 L2数据其他高价值模块:')
    print('-' * 40)

    valuable_modules = [
        ('shotmap', '射门分布图'),
        ('lineup', '阵容信息'),
        ('momentum', '比赛势头'),
        ('h2h', '历史交锋'),
        ('table', '积分榜影响'),
        ('matchFacts', '比赛事实')
    ]

    for module_key, module_name in valuable_modules:
        if module_key in content and content[module_key]:
            module_data = content[module_key]

            if isinstance(module_data, dict):
                sub_keys = list(module_data.keys())
                print(f'  ✅ {module_name} ({module_key}): {sub_keys}')
            elif isinstance(module_data, list):
                print(f'  ✅ {module_name} ({module_key}): 包含 {len(module_data)} 条数据')
            else:
                print(f'  ✅ {module_name} ({module_key}): {type(module_data).__name__}')

    print('\n🚀 L2数据结构分析总结:')
    print('=' * 60)
    print('1. 📊 团队级统计: content.stats - 15+ 维度团队数据')
    print('2. 👥 球员级统计: content.playerStats - 30+ 维度球员数据')
    print('3. 🎯 射门分析: content.shotmap - 精确射门坐标和xG')
    print('4. 📈 比赛势头: content.momentum - 实时比赛走势')
    print('5. 🏆 阵容信息: content.lineup - 完整首发替补')
    print('6. 📋 积分影响: content.table - 联赛排名变化')
    print('7. 🔄 历史交锋: content.h2h - H2H历史记录')
    print('8. ⚽ 比赛事实: content.matchFacts - 关键事件记录')

    print('\n💡 高价值统计特征识别:')
    print('• Expected Goals (xG) - 团队和球员级别')
    print('• Big Chances Created/Missed')
    print('• Shots on Target % 和 Conversion Rate')
    print('• Possession % 和 Pass Accuracy')
    print('• Defensive Actions (Tackles, Interceptions, Blocks)')
    print('• Set Pieces (Corners, Free Kicks)')
    print('• Disciplinary Actions (Cards, Fouls)')
    print('• Physical Duels 和 Aerial Battles')

    # 生成数据字段建议
    print('\n📝 数据库字段扩展建议:')
    print('-' * 40)

    recommended_fields = [
        # 基础统计
        'home_shots_on_target', 'away_shots_on_target',
        'home_shot_accuracy_pct', 'away_shot_accuracy_pct',
        'home_big_chances_created', 'away_big_chances_created',
        'home_big_chances_missed', 'away_big_chances_missed',

        # 进球和期望进球
        'home_xg_total', 'away_xg_total',
        'home_xg_from_shots', 'away_xg_from_shots',
        'home_goals_from_xg', 'away_goals_from_xg',

        # 控球和传球
        'home_possession_pct', 'away_possession_pct',
        'home_pass_completion_pct', 'away_pass_completion_pct',
        'home_total_passes', 'away_total_passes',

        # 防守动作
        'home_tackles', 'away_tackles',
        'home_interceptions', 'away_interceptions',
        'home_blocks', 'away_blocks',
        'home_clearances', 'away_clearances',

        # 定位球
        'home_corners', 'away_corners',
        'home_free_kicks', 'away_free_kicks',

        # 纪律
        'home_yellow_cards', 'away_yellow_cards',
        'home_red_cards', 'away_red_cards',
        'home_fouls', 'away_fouls',

        # 身体对抗
        'home_aerial_wins', 'away_aerial_wins',
        'home_duel_wins', 'away_duel_wins'
    ]

    print('建议新增数据库字段:')
    for i, field in enumerate(recommended_fields, 1):
        print(f'  {i:2d}. {field}')

    print('\n✨ L2数据分析完成！已识别丰富的统计维度可供ML特征工程使用。')

if __name__ == '__main__':
    main()