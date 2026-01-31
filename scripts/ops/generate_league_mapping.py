#!/usr/bin/env python3
"""
V29.0 新联赛对齐脚本 - 为西甲、意甲等联赛生成 matches_mapping 记录

功能：
1. 从 matches 表中读取指定联赛的比赛数据
2. 使用 team_alias 引擎进行队名标准化
3. 生成 OddsPortal URL 映射（基于 URL 模式推断）
4. 插入 matches_mapping 表

Author: 数据增长策略专家
Date: 2026-01-11
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from src.config_unified import get_settings
from src.utils.team_alias import normalize_team_name


# ============================================================================
# 联赛配置 - OddsPortal URL 模式
# ============================================================================

LEAGUE_URL_PATTERNS = {
    'Premier League': {
        'url_pattern': 'england/premier-league-2023-2024',
        'season_code': '2023-2024',
        'country': 'england'
    },
    'La Liga': {
        'url_pattern': 'spain/la-liga-2023-2024',
        'season_code': '2023-2024',
        'country': 'spain'
    },
    'Serie A': {
        'url_pattern': 'italy/serie-a-2023-2024',
        'season_code': '2023-2024',
        'country': 'italy'
    },
    'Bundesliga': {
        'url_pattern': 'germany/bundesliga-2023-2024',
        'season_code': '2023-2024',
        'country': 'germany'
    },
    'Ligue 1': {
        'url_pattern': 'france/ligue-1-2023-2024',
        'season_code': '2023-2024',
        'country': 'france'
    },
}


def fetch_matches_from_league(league_name: str, season: str = '23/24') -> List[Dict]:
    """从 matches 表中获取指定联赛的比赛数据

    Args:
        league_name: 联赛名称
        season: 赛季代码（如 '23/24'）

    Returns:
        比赛列表
    """
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            match_id,
            home_team,
            away_team,
            league_name,
            season,
            match_date
        FROM matches
        WHERE league_name = %s
          AND season = %s
        ORDER BY match_date DESC
        LIMIT 100;
    """, (league_name, season))

    columns = ['match_id', 'home_team', 'away_team', 'league_name', 'season', 'match_date']
    matches = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return matches


def check_existing_mapping(fotmob_id: str) -> bool:
    """检查 fotmob_id 是否已在 matches_mapping 表中

    Args:
        fotmob_id: FotMob 比赛 ID

    Returns:
        是否已存在映射
    """
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM matches_mapping WHERE fotmob_id = %s;
    """, (fotmob_id,))

    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count > 0


def generate_oddsportal_url(home_team: str, away_team: str,
                            league_config: Dict) -> Optional[str]:
    """生成 OddsPortal URL（基于队名推断）

    注意：这是一个简化的 URL 生成器，实际 URL 需要通过 OddsPortal 搜索验证

    Args:
        home_team: 主队名
        away_team: 客队名
        league_config: 联赛配置

    Returns:
        推断的 OddsPortal URL 或 None
    """
    # 标准化队名
    home_normalized = normalize_team_name(home_team).replace(' ', '-').lower()
    away_normalized = normalize_team_name(away_team).replace(' ', '-').lower()

    # 构造 URL（注意：实际 match_id 需要通过搜索获取）
    url_pattern = league_config['url_pattern']

    # 简化的 URL（用于后续 URL 健康检查）
    inferred_url = f"/football/{url_pattern}/{home_normalized}-{away_normalized}"

    return inferred_url


def insert_matches_mapping(matches: List[Dict], league_config: Dict,
                          dry_run: bool = True) -> Dict:
    """插入 matches_mapping 记录

    Args:
        matches: 比赛列表
        league_config: 联赛配置
        dry_run: 是否为干运行模式

    Returns:
        插入结果
    """
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cursor = conn.cursor()

    results = {
        'total': len(matches),
        'skipped': 0,
        'inserted': 0,
        'failed': 0,
        'dry_run': dry_run
    }

    for match in matches:
        fotmob_id = match['match_id']

        # 检查是否已存在
        if check_existing_mapping(fotmob_id):
            results['skipped'] += 1
            continue

        # 生成推断的 URL
        inferred_url = generate_oddsportal_url(
            match['home_team'],
            match['away_team'],
            league_config
        )

        if not dry_run:
            try:
                # 插入新记录（使用实际的表结构）
                cursor.execute("""
                    INSERT INTO matches_mapping
                    (fotmob_id, oddsportal_url, league_name, home_team, away_team,
                     match_date, mapping_method, confidence, review_status,
                     verified_at, created_at, updated_at)
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW());
                """, (
                    fotmob_id,
                    inferred_url,
                    match['league_name'],
                    match['home_team'],
                    match['away_team'],
                    match['match_date'],
                    'levenshtein',  # 映射方法
                    0.5,            # 置信度（范围 0.0-1.0）
                    'pending'       # 审核状态
                ))

                results['inserted'] += 1

            except Exception as e:
                results['failed'] += 1
                print(f"  ❌ 插入失败: {fotmob_id} - {e}")
        else:
            # 干运行模式，只计数
            results['inserted'] += 1

    if not dry_run:
        conn.commit()

    cursor.close()
    conn.close()

    return results


def print_report(league_name: str, matches: List[Dict], results: Dict):
    """打印对齐报告

    Args:
        league_name: 联赛名称
        matches: 比赛列表
        results: 结果字典
    """
    print("=" * 70)
    print(f"🌍 {league_name} 对齐任务报告")
    print("=" * 70)
    print()

    print(f"📊 赛季分布统计:")
    print("-" * 70)

    season_counts = {}
    for match in matches:
        season = match['season']
        season_counts[season] = season_counts.get(season, 0) + 1

    for season, count in sorted(season_counts.items(), reverse=True):
        print(f"  {season}: {count} 场")

    print()
    print(f"📈 对齐结果:")
    print("-" * 70)
    print(f"  总比赛数:     {results['total']}")
    print(f"  跳过已存在:   {results['skipped']}")
    print(f"  新增记录:     {results['inserted']}")
    print(f"  失败记录:     {results['failed']}")

    if results['dry_run']:
        print()
        print("⚠️  当前为干运行模式，未实际插入记录")
        print()
        print("💡 要执行实际插入操作，请运行:")
        print(f"   python {__file__} --league \"{league_name}\" --execute")
        print()

    print("=" * 70)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V29.0 新联赛对齐脚本 - 为西甲、意甲等联赛生成 matches_mapping 记录"
    )
    parser.add_argument(
        '--league',
        type=str,
        required=True,
        help='联赛名称（如 "La Liga", "Serie A"）'
    )
    parser.add_argument(
        '--season',
        type=str,
        default='23/24',
        help='赛季代码（默认: 23/24）'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='处理比赛数量限制（默认: 100）'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='执行实际插入操作（默认为干运行模式）'
    )

    args = parser.parse_args()

    league_name = args.league

    # 检查联赛是否支持
    if league_name not in LEAGUE_URL_PATTERNS:
        print(f"❌ 不支持的联赛: {league_name}")
        print()
        print("支持的联赛:")
        for name in LEAGUE_URL_PATTERNS.keys():
            print(f"  - {name}")
        sys.exit(1)

    # 获取联赛配置
    league_config = LEAGUE_URL_PATTERNS[league_name]

    # 步骤 1: 获取比赛数据
    print(f"\n📊 步骤 1: 从 matches 表获取 {league_name} ({args.season}) 的比赛数据...")
    matches = fetch_matches_from_league(league_name, args.season)
    print(f"✅ 获取到 {len(matches)} 场比赛")

    # 步骤 2: 插入 matches_mapping
    print(f"\n🔗 步骤 2: 生成 matches_mapping 记录...")
    dry_run = not args.execute
    results = insert_matches_mapping(matches, league_config, dry_run=dry_run)

    # 步骤 3: 打印报告
    print()
    print_report(league_name, matches, results)

    print("✅ 对齐任务完成")


if __name__ == "__main__":
    main()
