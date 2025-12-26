#!/usr/bin/env python3
"""
V50.0 第一阶段演示版（快速）
============================
只处理少量比赛来展示 Rich L1 功能
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import aiohttp


async def fetch_match_details(session, match_id: int) -> tuple:
    """获取比赛详情（包括比分）"""
    # 正确的端点格式：/matchDetails?matchId={match_id}
    url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                header = data.get('header', {})
                teams = header.get('teams', [])
                if len(teams) >= 2:
                    home_score = teams[0].get('score')
                    away_score = teams[1].get('score')
                    return (home_score, away_score)
    except:
        pass
    return (None, None)


async def demo_rich_l1_scan():
    """演示 Rich L1 扫描"""
    print("🚀 V50.0 Rich L1 演示版")
    print("=" * 70)

    # 使用英冠联赛（ID=48），只扫描最近一个赛季
    league_id = 48
    league_name = "Championship"
    season_code = "2324"  # 23/24 赛季
    season_name = "23/24"

    print(f"\n🎯 扫描 {league_name} - {season_name} 赛季")
    print("-" * 70)

    matches = []
    finished_matches = []

    # 第一步：获取比赛列表
    async with aiohttp.ClientSession() as session:
        url = f"https://www.fotmob.com/api/leagues?id={league_id}&season={season_code}"

        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                fixtures = data.get('fixtures', {})
                all_matches = fixtures.get('allMatches', [])

                print(f"  总比赛数: {len(all_matches)}")

                for match_data in all_matches:
                    match_id = match_data.get('id')
                    if not match_id:
                        continue

                    home_team = match_data.get('home', {})
                    away_team = match_data.get('away', {})
                    status_obj = match_data.get('status', {})

                    is_finished = status_obj.get('finished', False)
                    is_started = status_obj.get('started', False)

                    status = 'finished' if is_finished else ('ongoing' if is_started else 'scheduled')

                    match_info = {
                        'match_id': match_id,
                        'league_id': league_id,
                        'season_name': season_name,
                        'home_team': home_team.get('name', 'Unknown'),
                        'away_team': away_team.get('name', 'Unknown'),
                        'status': status,
                        'match_time_utc': status_obj.get('utcTime', ''),
                        'home_score': None,
                        'away_score': None,
                    }

                    matches.append(match_info)

                    if is_finished:
                        finished_matches.append((match_info, len(matches) - 1))

                print(f"  已完赛: {len(finished_matches)}")

        # 第二步：获取比分（限制前 50 场）
        limit = 50
        to_fetch = finished_matches[:limit]

        print(f"\n🎯 获取前 {limit} 场已完赛比赛的比分...")
        fetched_count = 0

        for match_info, idx in to_fetch:
            home_score, away_score = await fetch_match_details(session, match_info['match_id'])

            if home_score is not None and away_score is not None:
                matches[idx]['home_score'] = home_score
                matches[idx]['away_score'] = away_score
                fetched_count += 1

            if (fetched_count + 1) % 10 == 0:
                print(f"  进度: {fetched_count + 1}/{limit}")

            await asyncio.sleep(0.1)

        print(f"  ✅ 比分获取完成: {fetched_count}/{limit} 场成功")

    # 统计和展示
    total = len(matches)
    finished = [m for m in matches if m['status'] == 'finished']
    with_score = [m for m in finished if m['home_score'] is not None]
    without_score = [m for m in finished if m['home_score'] is None]

    print("\n" + "=" * 70)
    print("📊 Rich L1 数据分布表")
    print("=" * 70)
    print(f"\n总比赛数: {total}")
    print(f"已完赛: {len(finished)}")
    print(f"带比分: {len(with_score)}")
    print(f"缺比分: {len(without_score)}")

    if finished:
        coverage = len(with_score) / len(finished) * 100
        print(f"比分覆盖率: {coverage:.1f}%")

    # 显示前 10 场带比分的比赛
    print("\n🏆 已完赛带比分比赛（前 10 场）:")
    print("-" * 70)

    count = 0
    for match in matches:
        if match['status'] == 'finished' and match['home_score'] is not None:
            result_code = 'H' if match['home_score'] > match['away_score'] else ('A' if match['home_score'] < match['away_score'] else 'D')
            print(f"  {match['home_team']:20s} {match['home_score']:2d} - {match['away_score']:2d} {match['away_team']:20s} [{result_code}]")
            count += 1
            if count >= 10:
                break

    print("=" * 70)

    # 保存结果
    output_dir = Path("data/production/v50_phase1_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"v50_phase1_demo_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'version': 'V50.0-Demo',
                'league': league_name,
                'season': season_name,
                'timestamp': datetime.now().isoformat(),
                'total_matches': len(matches),
                'finished_matches': len(finished),
                'matches_with_score': len(with_score),
                'score_coverage': coverage if finished else 0,
            },
            'matches': matches,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 数据已保存: {output_file}")
    print("\n✅ V50.0 Rich L1 演示完成！")
    print("\n📋 架构总结:")
    print("  1. ✅ 扫描比赛 ID (来自 /api/leagues 端点)")
    print("  2. ✅ 获取比分数据 (来自 /api/matches/{id} 端点)")
    print("  3. ✅ 身首合一：比分和状态第一时间进入数据结构")
    print("  4. ✅ Rich L1 Tuple: {match_id, home_score, away_score, status, match_time_utc, ...}")


if __name__ == "__main__":
    asyncio.run(demo_rich_l1_scan())
