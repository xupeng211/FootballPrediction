#!/usr/bin/env python3
"""
英超 22/23 赛季比赛发现器
通过测试 match_id 范围并验证球队名称来发现真正的英超比赛
"""

import requests
import json
import csv
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 已知英超球队名单 (22/23 赛季)
EPL_TEAMS_2223 = {
    'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton',
    'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds United',
    'Leicester City', 'Liverpool', 'Manchester City', 'Manchester United',
    'Newcastle United', 'Nottingham Forest', 'Southampton', 'Tottenham',
    'West Ham United', 'Wolverhampton Wanderers',
    'AFC Bournemouth', 'Brighton & Hove Albion', 'Wolves'
}

def is_premier_league_match(home_team: str, away_team: str) -> bool:
    """检查是否为英超比赛"""
    return home_team in EPL_TEAMS_2223 and away_team in EPL_TEAMS_2223

def test_match_id(match_id: int) -> dict:
    """测试指定比赛 ID 是否为有效的英超比赛"""
    url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            return {'valid': False, 'reason': 'Not JSON'}

        data = response.json()

        if 'header' in data and data['header'].get('teams'):
            teams = data['header']['teams']
            home_team = teams[0].get('name', '')
            away_team = teams[1].get('name', '')

            if is_premier_league_match(home_team, away_team):
                return {
                    'valid': True,
                    'match_id': match_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'status': data.get('status', {}).get('finished', False),
                    'utc_time': data.get('header', {}).get('status', {}).get('utcTime', ''),
                    'home_score': teams[0].get('score'),
                    'away_score': teams[1].get('score')
                }
            else:
                return {'valid': False, 'reason': 'Not EPL match', 'home': home_team, 'away': away_team}
        else:
            return {'valid': False, 'reason': 'No match data'}

    except Exception as e:
        return {'valid': False, 'reason': str(e)}


def discover_epl_2223_season():
    """
    发现 22/23 赛季英超比赛

    策略: 23/24 赛季从 4193450 开始，我们向前搜索约 10000 个 ID
    """
    logger.info("=" * 60)
    logger.info("22/23 赛季英超比赛发现")
    logger.info("=" * 60)

    # 23/24 赛季首场 ID
    v23_first_id = 4193450

    # 22/23 赛季应该在一赛季前，扩大搜索范围到约 10000 个 ID
    search_start = v23_first_id - 100
    search_end = v23_first_id - 10000

    valid_matches = []

    logger.info(f"搜索范围: {search_end} ~ {search_start} (约 {search_start - search_end} 个 ID)")

    tested_count = 0
    for match_id in range(search_start, search_end, -1):
        tested_count += 1
        result = test_match_id(match_id)

        # 进度报告
        if tested_count % 500 == 0:
            logger.info(f"  已测试 {tested_count} 个 ID，已发现 {len(valid_matches)} 场英超比赛...")

        if result['valid']:
            valid_matches.append({
                'match_id': result['match_id'],
                'external_id': str(result['match_id']),
                'home_team': result['home_team'],
                'away_team': result['away_team'],
                'match_date': result['utc_time'],
                'home_score': result.get('home_score', ''),
                'away_score': result.get('away_score', ''),
                'actual_result': '',
                'round_name': '',
                'league_name': 'Premier League',
                'season_id': '2022/2023',
                'is_finished': result['status'],
                'venue': '',
                'status': 'Finished' if result['status'] else 'Scheduled',
                'collection_date': datetime.utcnow().isoformat(),
                'is_matched': 'True'
            })

            if len(valid_matches) % 50 == 0:
                logger.info(f"  已发现 {len(valid_matches)} 场英超比赛...")

            # 如果已经找到 380 场，停止
            if len(valid_matches) >= 380:
                logger.info(f"✅ 已收集 380 场英超比赛")
                break

        # 减少延迟以加快搜索
        import time
        time.sleep(0.02)

    # 按时间排序
    valid_matches.sort(key=lambda x: x.get('match_date', ''))

    logger.info(f"✅ 发现完成，共找到 {len(valid_matches)} 场英超比赛")

    return valid_matches


def save_manifest(matches, output_path="data/production/harvest_manifest_2223.csv"):
    """保存 manifest 文件"""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = [
        'match_id', 'external_id', 'home_team', 'away_team', 'match_date',
        'home_score', 'away_score', 'actual_result', 'round_name',
        'league_name', 'season_id', 'is_finished', 'venue', 'status',
        'collection_date', 'is_matched'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

    logger.info(f"✅ Manifest 文件已保存: {output_path}")

    # 统计球队
    teams = set()
    for m in matches:
        teams.add(m['home_team'])
        teams.add(m['away_team'])

    logger.info(f"📊 涉及球队: {len(teams)} 支")
    for team in sorted(teams):
        logger.info(f"   - {team}")


if __name__ == "__main__":
    matches = discover_epl_2223_season()

    if matches:
        save_manifest(matches)
        logger.info(f"🎉 成功生成 {len(matches)} 场比赛的 manifest")
    else:
        logger.error("❌ 未发现任何英超比赛")
