#!/usr/bin/env python3
"""
英超 22/23 赛季范围快速查找器
使用较大步长快速定位 22/23 赛季的 ID 范围
"""

import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 已知英超球队名单
EPL_TEAMS = {
    'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton',
    'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds United',
    'Leicester City', 'Liverpool', 'Manchester City', 'Manchester United',
    'Newcastle United', 'Nottingham Forest', 'Southampton', 'Tottenham',
    'West Ham United', 'Wolverhampton Wanderers',
    'AFC Bournemouth', 'Brighton & Hove Albion', 'Wolves'
}

def is_epl_match(match_id: int) -> tuple:
    """检查是否为英超比赛，返回 (is_epl, home_team, away_team)"""
    url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if 'application/json' not in response.headers.get('Content-Type', ''):
            return False, '', ''

        data = response.json()
        if 'header' in data and data['header'].get('teams'):
            teams = data['header']['teams']
            home_team = teams[0].get('name', '')
            away_team = teams[1].get('name', '')

            if home_team in EPL_TEAMS and away_team in EPL_TEAMS:
                return True, home_team, away_team

        return False, '', ''

    except Exception as e:
        return False, '', ''


def find_epl_range():
    """
    使用二分查找策略快速找到 22/23 赛季范围

    23/24 赛季从 4193450 开始
    我们向前搜索，每次跳跃测试，找到包含英超比赛的区域
    """
    logger.info("=" * 60)
    logger.info("22/23 赛季快速范围查找")
    logger.info("=" * 60)

    v23_start = 4193450

    # 第一步：使用大步长 (1000) 向前搜索
    logger.info("第一步：大步长扫描 (步长 1000)")
    epl_found_positions = []

    for offset in range(1000, 50000, 1000):
        test_id = v23_start - offset
        is_epl, home, away = is_epl_match(test_id)

        if is_epl:
            epl_found_positions.append((test_id, home, away))
            logger.info(f"  ✓ 找到英超比赛: ID {test_id} - {home} vs {away}")
            if len(epl_found_positions) >= 3:
                break
        else:
            if offset % 5000 == 0:
                logger.info(f"  ✗ ID {test_id}: 不是英超比赛")

    if not epl_found_positions:
        logger.warning("未找到任何英超比赛，尝试更大范围...")
        # 尝试更大的步长
        for offset in range(50000, 200000, 5000):
            test_id = v23_start - offset
            is_epl, home, away = is_epl_match(test_id)
            if is_epl:
                epl_found_positions.append((test_id, home, away))
                logger.info(f"  ✓ 找到英超比赛: ID {test_id} - {home} vs {away}")
                if len(epl_found_positions) >= 3:
                    break

    if not epl_found_positions:
        logger.error("未找到任何 22/23 赛季英超比赛")
        return None, None

    logger.info(f"\n找到 {len(epl_found_positions)} 场英超比赛作为参考点")

    # 第二步：从最远的英超比赛开始向前搜索完整范围
    first_epl_id = min(epl_found_positions, key=lambda x: x[0])[0]
    logger.info(f"\n第二步：从 ID {first_epl_id} 开始向前详细搜索")

    # 向前搜索约 500 个 ID 作为起点的缓冲
    search_start = first_epl_id + 200
    search_end = first_epl_id - 20000

    logger.info(f"详细搜索范围: {search_end} ~ {search_start}")

    return search_start, search_end


if __name__ == "__main__":
    start, end = find_epl_range()

    if start and end:
        logger.info(f"\n建议搜索范围: {end} ~ {start}")
        logger.info(f"范围大小: {start - end} 个 ID")
    else:
        logger.error("未能确定搜索范围")
