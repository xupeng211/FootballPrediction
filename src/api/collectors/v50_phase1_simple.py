#!/usr/bin/env python3
"""
V50.0 第一阶段简化执行脚本（基于现有 V35.1 架构）
===================================================
使用已验证的 global_l1_scanner 架构进行数据采集
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
from datetime import datetime

# 添加荷甲和英冠配置
PHASE1_LEAGUES = [
    # (league_id, league_name, fotmob_code_prefix)
    (29, "Eredivisie", "24"),   # 荷甲 - 使用 2024 作为基准
    (48, "Championship", "24"),  # 英冠 - 使用 2024 作为基准
]


async def fetch_match_details(
    session,
    match_id: int
) -> tuple:
    """
    获取比赛详情（包括比分）

    Args:
        session: aiohttp 会话
        match_id: 比赛 ID

    Returns:
        (home_score, away_score) 元组，失败返回 (None, None)
    """
    url = f"https://www.fotmob.com/api/matches/{match_id}"

    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()

                # 从 header.teams 提取比分
                header = data.get('header', {})
                teams = header.get('teams', [])

                if len(teams) >= 2:
                    home_score = teams[0].get('score')
                    away_score = teams[1].get('score')
                    return (home_score, away_score)
    except Exception:
        pass  # 静默失败

    return (None, None)


async def scan_single_league(
    league_id: int,
    league_name: str,
    season_code_prefix: str
) -> list[dict]:
    """
    扫描单个联赛的所有赛季（带 Rich L1 比分）

    Args:
        league_id: 联赛 ID
        league_name: 联赛名称
        season_code_prefix: 赛季代码前缀

    Returns:
        比赛列表
    """
    print(f"\n🎯 开始扫描 {league_name} (ID={league_id})")
    print("-" * 70)

    # 使用 aiohttp 直接请求
    import aiohttp

    matches = []
    finished_matches_to_fetch = []  # 需要获取比分的已完赛比赛
    seasons = ["2021", "2122", "2223", "2324", "2425"]  # 过去 5 年

    # 第一步：扫描所有比赛
    async with aiohttp.ClientSession() as session:
        for season_code in seasons:
            url = f"https://www.fotmob.com/api/leagues?id={league_id}&season={season_code}"

            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        # 解析比赛
                        fixtures = data.get('fixtures', {})
                        all_matches = fixtures.get('allMatches', [])

                        for match_data in all_matches:
                            match_id = match_data.get('id')
                            if not match_id:
                                continue

                            home_team = match_data.get('home', {})
                            away_team = match_data.get('away', {})
                            status_obj = match_data.get('status', {})

                            # 判断状态
                            is_finished = status_obj.get('finished', False)
                            is_started = status_obj.get('started', False)

                            if is_finished:
                                status = 'finished'
                            elif is_started:
                                status = 'ongoing'
                            else:
                                status = 'scheduled'

                            # 构建赛季名称
                            if len(season_code) == 4:
                                season_name = f"{season_code[:2]}/{season_code[2:]}"
                            else:
                                season_name = season_code

                            match_info = {
                                'match_id': match_id,
                                'league_id': league_id,
                                'season_id': season_code,
                                'season_name': season_name,
                                'home_team': home_team.get('name', 'Unknown'),
                                'away_team': away_team.get('name', 'Unknown'),
                                'home_team_id': home_team.get('id', 0),
                                'away_team_id': away_team.get('id', 0),
                                'status': status,
                                'match_time_utc': status_obj.get('utcTime', ''),
                                'home_score': None,  # 初始为 None
                                'away_score': None,  # 初始为 None
                            }

                            matches.append(match_info)

                            # 记录需要获取比分的已完赛比赛
                            if is_finished:
                                finished_matches_to_fetch.append((match_info, len(matches) - 1))

                        print(f"  ✓ {season_code}: {len(all_matches)} 场比赛")

                    await asyncio.sleep(0.5)  # 避免 API 限流

            except Exception as e:
                print(f"  ✗ {season_code}: 扫描失败 - {e}")

        # 第二步：获取已完赛比赛的比分（Rich L1 核心功能）
        if finished_matches_to_fetch:
            print(f"  🎯 获取 {len(finished_matches_to_fetch)} 场已完赛比赛的比分...")

            fetched_count = 0
            for match_info, idx in finished_matches_to_fetch:
                home_score, away_score = await fetch_match_details(session, match_info['match_id'])

                if home_score is not None and away_score is not None:
                    matches[idx]['home_score'] = home_score
                    matches[idx]['away_score'] = away_score
                    fetched_count += 1

                # 避免请求过快
                await asyncio.sleep(0.1)

                # 每获取 100 场显示进度
                if (fetched_count + 1) % 100 == 0:
                    print(f"    进度: {fetched_count + 1}/{len(finished_matches_to_fetch)}")

            print(f"  ✅ 比分获取完成: {fetched_count}/{len(finished_matches_to_fetch)} 场成功")

    print(f"✅ {league_name} 扫描完成: {len(matches)} 场比赛")
    return matches


def print_score_distribution(matches: list[dict], league_name: str):
    """打印比分分布表"""
    print("\n" + "=" * 70)
    print(f"📊 {league_name} - Rich L1 数据分布表")
    print("=" * 70)

    total = len(matches)
    finished = [m for m in matches if m['status'] == 'finished']
    ongoing = [m for m in matches if m['status'] == 'ongoing']
    scheduled = [m for m in matches if m['status'] == 'scheduled']

    # 比分统计
    finished_with_score = [m for m in finished if m['home_score'] is not None]
    finished_without_score = [m for m in finished if m['home_score'] is None]

    print("\n📈 总体统计:")
    print(f"   总比赛数: {total:,}")
    print(f"   已完赛: {len(finished):,} ({len(finished)/total*100:.1f}%)")
    print(f"   进行中: {len(ongoing):,} ({len(ongoing)/total*100:.1f}%)")
    print(f"   未开始: {len(scheduled):,} ({len(scheduled)/total*100:.1f}%)")

    print("\n🎯 比分统计 (Rich L1 核心指标):")
    print(f"   已完赛带比分: {len(finished_with_score):,}")
    print(f"   已完赛缺比分: {len(finished_without_score):,}")
    if finished:
        score_coverage = len(finished_with_score) / len(finished) * 100
        print(f"   比分覆盖率: {score_coverage:.1f}%")

    # 按赛季统计
    season_stats = {}
    for match in matches:
        season = match['season_name']
        if season not in season_stats:
            season_stats[season] = {'total': 0, 'finished': 0, 'with_score': 0}
        season_stats[season]['total'] += 1
        if match['status'] == 'finished':
            season_stats[season]['finished'] += 1
        if match['home_score'] is not None:
            season_stats[season]['with_score'] += 1

    print("\n📅 按赛季分布:")
    for season in sorted(season_stats.keys()):
        stats = season_stats[season]
        print(f"   {season:6s}: {stats['total']:4d} 场 | 完赛 {stats['finished']:4d} | 带比分 {stats['with_score']:4d}")

    # 结果分布
    home_wins = sum(1 for m in finished_with_score if m['home_score'] > m['away_score'])
    draws = sum(1 for m in finished_with_score if m['home_score'] == m['away_score'])
    away_wins = sum(1 for m in finished_with_score if m['home_score'] < m['away_score'])

    if finished_with_score:
        print("\n🏆 结果分布 (已完赛带比分):")
        print(f"   主胜: {home_wins} ({home_wins/len(finished_with_score)*100:.1f}%)")
        print(f"   平局: {draws} ({draws/len(finished_with_score)*100:.1f}%)")
        print(f"   客胜: {away_wins} ({away_wins/len(finished_with_score)*100:.1f}%)")

    print("=" * 70)


async def main():
    """主函数"""
    print("🚀 V50.0 第一阶段：荷甲与英冠全量补课（简化版）")
    print("=" * 70)

    output_dir = Path("data/production/v50_phase1_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_matches_by_league = {}

    for league_id, league_name, season_prefix in PHASE1_LEAGUES:
        # 扫描数据
        matches = await scan_single_league(league_id, league_name, season_prefix)

        if not matches:
            print(f"⚠️ {league_name} 没有扫描到任何比赛")
            continue

        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"v50_phase1_{league_name}_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'version': 'V50.0-Phase1-Simple',
                    'league': league_name,
                    'league_id': league_id,
                    'timestamp': datetime.now().isoformat(),
                    'total_matches': len(matches),
                },
                'matches': matches,
            }, f, indent=2, ensure_ascii=False)

        print(f"💾 数据已保存: {output_file}")

        # 打印分布
        print_score_distribution(matches, league_name)

        all_matches_by_league[league_name] = matches

    # 总体汇总
    if all_matches_by_league:
        print("\n" + "=" * 70)
        print("🎯 第一阶段总体汇总")
        print("=" * 70)

        total_matches = sum(len(m) for m in all_matches_by_league.values())
        total_finished = sum(len([x for x in m if x['status'] == 'finished']) for m in all_matches_by_league.values())
        total_with_score = sum(len([x for x in m if x['home_score'] is not None]) for m in all_matches_by_league.values())

        print("\n📊 联赛汇总:")
        for league_name, matches in all_matches_by_league.items():
            print(f"   {league_name:10s}: {len(matches):,} 场比赛")

        print("\n📈 总体统计:")
        print(f"   总比赛数: {total_matches:,}")
        print(f"   已完赛: {total_finished:,}")
        print(f"   带比分: {total_with_score:,}")
        if total_finished > 0:
            score_coverage = total_with_score / total_finished * 100
            print(f"   比分覆盖率: {score_coverage:.1f}%")

    print("\n" + "=" * 70)
    print("✅ 第一阶段执行完成！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
