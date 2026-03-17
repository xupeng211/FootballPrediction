#!/usr/bin/env python3
import sys
import json

sys.path.insert(0, '/home/xupeng/projects/FootballPrediction')

print('=' * 80)
print('Task 4: 闭环小样回测 - Value 计算')
print('=' * 80)

# 加载数据
with open('/tmp/epl_pilot_odds.json', 'r') as f:
    odds_data = json.load(f)

# 筛选历史比赛（已完赛）
historical = [r for r in odds_data if r['status'] == 'finished']

print(f'\n📊 回测样本: {len(historical)} 场已完赛比赛')
print('-' * 80)

# 使用 Mock 模型概率
def mock_model_probability(home_team, away_team):
    top_teams = ['Manchester City', 'Liverpool', 'Arsenal', 'Chelsea', 'Manchester United', 'Tottenham Hotspur']
    
    home_strength = 1.5 if home_team in top_teams else 1.0
    away_strength = 1.5 if away_team in top_teams else 1.0
    home_advantage = 1.2
    
    total = home_strength * home_advantage + away_strength + 1.0
    p_home = (home_strength * home_advantage) / total * 0.9
    p_away = away_strength / total * 0.9
    p_draw = 1.0 - p_home - p_away
    
    return {'H': round(p_home, 3), 'D': round(p_draw, 3), 'A': round(p_away, 3)}

def calculate_value(prob, odds):
    return round(prob * odds - 1, 3)

print('\n📈 Value 分值计算（假设使用 Mock 模型概率）')
print('-' * 80)
print(f'\n{"Match":<45} {"Result":<6} {"P(H)":<7} {"P(D)":<7} {"P(A)":<7} {"Odds(H/D/A)":<20} {"Value(H/D/A)":<25}')
print('=' * 120)

results_summary = []

for match in historical:
    home = match['home_team']
    away = match['away_team']
    match_str = f"{home[:18]} vs {away[:18]}"
    result = match['result']
    
    probs = mock_model_probability(home, away)
    p_h, p_d, p_a = probs['H'], probs['D'], probs['A']
    
    o_h = match['odds_home_close']
    o_d = match['odds_draw_close']
    o_a = match['odds_away_close']
    
    v_h = calculate_value(p_h, o_h)
    v_d = calculate_value(p_d, o_d)
    v_a = calculate_value(p_a, o_a)
    
    value_str = f"{v_h:+.2f}/{v_d:+.2f}/{v_a:+.2f}"
    
    if result == 'H' and v_h > 0:
        value_str += " ✅"
    elif result == 'D' and v_d > 0:
        value_str += " ✅"
    elif result == 'A' and v_a > 0:
        value_str += " ✅"
    elif (result == 'H' and v_h < 0) or (result == 'D' and v_d < 0) or (result == 'A' and v_a < 0):
        value_str += " ❌"
    else:
        value_str += " ⚪"
    
    print(f'{match_str:<45} {result:<6} {p_h:<7.3f} {p_d:<7.3f} {p_a:<7.3f} {o_h:.2f}/{o_d:.2f}/{o_a:.2f}       {value_str}')
    
    results_summary.append({
        'match_id': match['match_id'],
        'home': home,
        'away': away,
        'result': result,
        'probs': probs,
        'values': {'H': v_h, 'D': v_d, 'A': v_a}
    })

print('\n' + '=' * 120)
print('\n📊 回测统计：')
print('-' * 80)

value_bets = []
for r in results_summary:
    max_value = max(r['values'].values())
    if max_value > 0:
        predicted = max(r['values'], key=r['values'].get)
        actual = r['result']
        is_correct = predicted == actual
        value_bets.append({
            'match': f"{r['home']} vs {r['away']}",
            'predicted': predicted,
            'actual': actual,
            'correct': is_correct,
            'value': max_value
        })

if value_bets:
    correct_count = sum(1 for b in value_bets if b['correct'])
    accuracy = correct_count / len(value_bets) * 100
    
    print(f'   Value > 0 的投注次数: {len(value_bets)} 场')
    print(f'   命中次数: {correct_count} 场')
    print(f'   命中率: {accuracy:.1f}%')
    
    print('\n   详细结果:')
    for bet in value_bets:
        status = '命中' if bet['correct'] else '未中'
        match_name = bet['match']
        pred = bet['predicted']
        actual = bet['actual']
        val = bet['value']
        print(f'      {match_name:<45} -> 预测: {pred}, 实际: {actual} {status} (Value: {val:+.2f})')
else:
    print('   无 Value > 0 的投注机会')

print('\n💰 假设 ROI 计算（每场均注 1 单位）：')
print('-' * 80)

roi_results = []
for i, r in enumerate(results_summary):
    max_value_dir = max(r['values'], key=r['values'].get)
    max_value = r['values'][max_value_dir]
    
    if max_value > 0:
        if max_value_dir == 'H':
            odds = historical[i]['odds_home_close']
        elif max_value_dir == 'D':
            odds = historical[i]['odds_draw_close']
        else:
            odds = historical[i]['odds_away_close']
        
        if r['result'] == max_value_dir:
            profit = odds - 1
        else:
            profit = -1
        
        roi_results.append(profit)

if roi_results:
    total_profit = sum(roi_results)
    avg_profit = total_profit / len(roi_results)
    print(f'   总盈亏: {total_profit:+.2f} 单位')
    print(f'   平均盈亏: {avg_profit:+.2f} 单位/场')
    print(f'   ROI: {(total_profit / len(roi_results) * 100):+.1f}%')
else:
    print('   无投注记录')

print('\n' + '=' * 80)
print('注意: 以上使用 Mock 概率演示逻辑，实际应使用 TITAN 模型输出')
print('=' * 80)
