#!/usr/bin/env python3
"""
FotMob API 深度数据结构分析
专注于高价值ML特征发现
"""

import json

def main():
    # 加载数据
    with open('fotmob_match_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    content = data.get('content', {})

    print('🎯 深度分析其他高价值模块')
    print('=' * 50)

    # 分析射门分布图 (shotmap)
    if 'shotmap' in content:
        shotmap = content['shotmap']
        print('🎯 射门分布图分析 (shotmap):')
        print('-' * 30)

        if 'shots' in shotmap:
            shots = shotmap['shots']
            print(f'总射门次数: {len(shots)}')

            if shots:
                first_shot = shots[0]
                print(f'射门数据字段: {list(first_shot.keys())}')

                # 统计主客队射门
                home_shots = [s for s in shots if s.get('isHome', False)]
                away_shots = [s for s in shots if not s.get('isHome', True)]

                print(f'主队射门: {len(home_shots)}次')
                print(f'客队射门: {len(away_shots)}次')

                # 分析xG数据
                home_xg = sum(s.get('xg', 0) for s in home_shots)
                away_xg = sum(s.get('xg', 0) for s in away_shots)

                print(f'主队总xG: {home_xg:.2f}')
                print(f'客队总xG: {away_xg:.2f}')

                # 分析射门类型
                shot_types = {}
                for shot in shots:
                    shot_type = shot.get('situation', 'Unknown')
                    shot_types[shot_type] = shot_types.get(shot_type, 0) + 1

                print(f'射门类型分布: {shot_types}')

                # 分析高价值射门特征
                big_chances = [s for s in shots if s.get('bigChance', False)]
                home_big_chances = [s for s in big_chances if s.get('isHome', False)]
                away_big_chances = [s for s in big_chances if not s.get('isHome', True)]

                print(f'重大机会总数: {len(big_chances)} (主队: {len(home_big_chances)}, 客队: {len(away_big_chances)})')

                # 分析进球
                goals = [s for s in shots if s.get('eventType', '').lower() == 'goal']
                home_goals = [s for s in goals if s.get('isHome', False)]
                away_goals = [s for s in goals if not s.get('isHome', True)]

                print(f'进球总数: {len(goals)} (主队: {len(home_goals)}, 客队: {len(away_goals)})')

        print()

    # 分析比赛事实 (matchFacts)
    if 'matchFacts' in content:
        match_facts = content['matchFacts']
        print('⚽ 比赛事实分析 (matchFacts):')
        print('-' * 30)

        if 'events' in match_facts:
            events = match_facts['events']
            print(f'比赛事件数量: {len(events)}')

            if events:
                # 分析事件类型
                event_types = {}
                for event in events:
                    event_type = event.get('type', 'Unknown')
                    event_types[event_type] = event_types.get(event_type, 0) + 1

                print(f'事件类型分布: {event_types}')

                # 统计关键事件
                cards = [e for e in events if e.get('type') in ['Yellow Card', 'Red Card']]
                substitutions = [e for e in events if e.get('type') == 'Substitution']
                offsides = [e for e in events if e.get('type') == 'Offside']

                print(f'黄牌/红牌: {len(cards)}张')
                print(f'换人: {len(substitutions)}次')
                print(f'越位: {len(offsides)}次')

                # 显示进球事件
                goals = [e for e in events if e.get('type') == 'Goal']
                if goals:
                    print(f'进球事件详情 ({len(goals)}个):')
                    for i, goal in enumerate(goals, 1):
                        player = goal.get('player1', {}).get('name', 'Unknown')
                        minute = goal.get('minute', 'Unknown')
                        home_score = goal.get('homeScore', 'N/A')
                        away_score = goal.get('awayScore', 'N/A')
                        print(f'  {i}. {player} - 第{minute}分钟 ({home_score}-{away_score})')

        print()

    # 分析阵容信息 (lineup)
    if 'lineup' in content:
        lineup = content['lineup']
        print('🏆 阵容信息分析 (lineup):')
        print('-' * 30)

        if 'homeTeam' in lineup:
            home_team = lineup['homeTeam']
            print(f'主队阵容字段: {list(home_team.keys()) if isinstance(home_team, dict) else type(home_team)}')

            if 'players' in home_team:
                home_players = home_team['players']
                print(f'主队球员数量: {len(home_players)}')

                # 分析首发阵容
                starters = [p for p in home_players if not p.get('substitute', True)]
                substitutes = [p for p in home_players if p.get('substitute', False)]

                print(f'首发球员: {len(starters)}人')
                print(f'替补球员: {len(substitutes)}人')

                if starters:
                    positions = {}
                    for player in starters[:5]:  # 显示前5个首发球员
                        position = player.get('position', 'Unknown')
                        positions[position] = positions.get(position, 0) + 1
                        player_name = player.get('name', 'Unknown')
                        shirt_num = player.get('shirtNo', 'N/A')
                        print(f'  • {player_name} (#{shirt_num}) - {position}')

                    print(f'首发阵容位置分布: {positions}')

        print()

    # 分析比赛势头 (momentum)
    if 'momentum' in content:
        momentum = content['momentum']
        print('📈 比赛势头分析 (momentum):')
        print('-' * 30)

        momentum_fields = list(momentum.keys()) if isinstance(momentum, dict) else type(momentum)
        print(f'势头数据字段: {momentum_fields}')

        if 'main' in momentum:
            main_momentum = momentum['main']
            if isinstance(main_momentum, dict) and 'data' in main_momentum:
                momentum_data = main_momentum['data']
                print(f'势头数据点数量: {len(momentum_data) if isinstance(momentum_data, list) else "非列表类型"}')

                if isinstance(momentum_data, list) and len(momentum_data) > 0:
                    sample_point = momentum_data[0]
                    print(f'势头数据点字段: {list(sample_point.keys()) if isinstance(sample_point, dict) else type(sample_point)}')

        print()

    # 分析积分榜影响 (table)
    if 'table' in content:
        table = content['table']
        print('📊 积分榜影响分析 (table):')
        print('-' * 30)

        table_fields = list(table.keys()) if isinstance(table, dict) else type(table)
        print(f'积分榜数据字段: {table_fields}')

        if 'teams' in table:
            teams = table['teams']
            print(f'球队数量: {len(teams) if isinstance(teams, list) else "非列表类型"}')

            if isinstance(teams, list) and teams:
                first_team = teams[0]
                print(f'球队数据字段: {list(first_team.keys()) if isinstance(first_team, dict) else type(first_team)}')

        print()

    # 分析历史交锋 (h2h)
    if 'h2h' in content:
        h2h = content['h2h']
        print('🔄 历史交锋分析 (h2h):')
        print('-' * 30)

        h2h_fields = list(h2h.keys()) if isinstance(h2h, dict) else type(h2h)
        print(f'交锋数据字段: {h2h_fields}')

        if 'summary' in h2h:
            summary = h2h['summary']
            print(f'交锋摘要: {summary}')

        if 'matches' in h2h:
            matches = h2h['matches']
            print(f'历史比赛数量: {len(matches) if isinstance(matches, list) else "非列表类型"}')

            if isinstance(matches, list) and matches:
                first_match = matches[0]
                print(f'历史比赛数据字段: {list(first_match.keys()) if isinstance(first_match, dict) else type(first_match)}')

    print('\n🚀 高价值ML特征总结:')
    print('=' * 50)
    print('1. 🎯 射门特征:')
    print('   • total_shots, shots_on_target, shot_accuracy_pct')
    print('   • total_xg, xg_per_shot, big_chances_created')
    print('   • goals_from_shots, conversion_rate')
    print('   • shot_types_distribution (open_play, set_piece, etc.)')

    print('\n2. ⚽ 比赛事件特征:')
    print('   • total_cards, yellow_cards, red_cards')
    print('   • total_substitutions, substitution_timing')
    print('   • offsides_count, fouls_committed')
    print('   • goal_timing (early_goals, late_goals)')

    print('\n3. 🏆 阵容特征:')
    print('   • formation_type, key_players_missing')
    print('   • squad_depth, substitutions_used')
    print('   • player_positions_distribution')

    print('\n4. 📈 比赛势头特征:')
    print('   • momentum_shifts, dominance_periods')
    print('   • comeback_potential, game_control')

    print('\n5. 📊 历史交锋特征:')
    print('   • h2h_win_rate, recent_h2h_form')
    print('   • goal_difference_h2h, scoring_patterns_h2h')

    print('\n✨ 这些特征维度将显著提升ML模型的预测能力！')

if __name__ == '__main__':
    main()