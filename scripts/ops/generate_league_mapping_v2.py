#!/usr/bin/env python3
"""
V29.0 新联赛对齐脚本 V2 - 强制哈希校验版本

核心改进：
1. 严禁拼接不带 8 位 Hash 的 URL
2. 新增"打靶验证"环节：HEAD 请求验证 URL 有效性
3. 只有验证通过的 URL 才能标记为 verified

准入红线：如果不包含有效的 8 位 OddsPortal Hash，严禁向 matches_mapping 插入任何记录！

Author: 高级 DevOps 架构师
Date: 2026-01-11
Version: V2.0 (Industrial Ops Upgrade)
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional
import re
import httpx

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from src.config_unified import get_settings
from src.utils.team_alias import normalize_team_name


# ============================================================================
# 配置常量
# ============================================================================

ODDSPORTAL_BASE_URL = "https://www.oddsportal.com"
HEAD_TIMEOUT = 10.0  # HEAD 请求超时（秒）

# 哈希模式：8-12 位字母数字混合（至少 1 位大写或数字）
HASH_PATTERN = re.compile(r'^[a-zA-Z0-9]{8,12}$')


# ============================================================================
# 哈希验证
# ============================================================================

def has_valid_hash(url: str) -> bool:
    """检查 URL 是否包含有效的 8 位哈希

    Args:
        url: OddsPortal URL

    Returns:
        是否包含有效哈希
    """
    if not url:
        return False

    # 提取 URL 的最后一段
    parts = url.rstrip('/').split('/')
    if not parts:
        return False

    last_part = parts[-1]

    # 检查是否符合哈希模式
    return bool(HASH_PATTERN.match(last_part))


async def verify_url_with_head(url_path: str) -> Dict[str, any]:
    """使用 HEAD 请求验证 URL 有效性

    Args:
        url_path: URL 路径（不包含域名）

    Returns:
        验证结果字典
    """
    full_url = f"{ODDSPORTAL_BASE_URL}{url_path}"

    try:
        async with httpx.AsyncClient(timeout=HEAD_TIMEOUT) as client:
            response = await client.head(full_url, follow_redirects=True)

            return {
                'url': full_url,
                'status_code': response.status_code,
                'is_valid': response.status_code == 200,
                'error': None
            }

    except httpx.TimeoutException:
        return {
            'url': full_url,
            'status_code': None,
            'is_valid': False,
            'error': 'Timeout'
        }
    except Exception as e:
        return {
            'url': full_url,
            'status_code': None,
            'is_valid': False,
            'error': str(e)
        }


# ============================================================================
# 数据库操作
# ============================================================================

def fetch_matches_from_league(league_name: str, season: str = '2023/2024', limit: int = 100) -> List[Dict]:
    """从 matches 表中获取指定联赛的比赛数据

    Args:
        league_name: 联赛名称
        season: 赛季代码
        limit: 限制数量

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
        LIMIT %s;
    """, (league_name, season, limit))

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


# ============================================================================
# URL 生成（仅用于演示，实际需要通过搜索获取）
# ============================================================================

def generate_oddsportal_url_placeholder(home_team: str, away_team: str,
                                       league_name: str) -> Optional[str]:
    """
    生成 OddsPortal URL 占位符

    ⚠️ 准入红线：此函数仅返回 NULL，因为无法推断哈希！
    实际哈希必须通过 OddsPortal 搜索页面获取。

    Args:
        home_team: 主队名
        away_team: 客队名
        league_name: 联赛名称

    Returns:
        NULL（因为无法推断哈希）
    """
    # 标准化队名
    home_normalized = normalize_team_name(home_team).replace(' ', '-').lower()
    away_normalized = normalize_team_name(away_team).replace(' ', '-').lower()

    # ❌ 不返回任何 URL，因为缺少哈希
    # ⚠️ 实际应用中需要通过 OddsPortal 搜索功能获取真实 URL
    return None


# ============================================================================
# 插入逻辑（带验证）
# ============================================================================

async def insert_matches_mapping_verified(matches: List[Dict], dry_run: bool = True) -> Dict:
    """插入 matches_mapping 记录（强制哈希校验）

    Args:
        matches: 比赛列表
        dry_run: 是否为干运行模式

    Returns:
        插入结果字典
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
        'rejected_no_hash': 0,
        'rejected_invalid_url': 0,
        'verified': 0,
        'dry_run': dry_run
    }

    for match in matches:
        fotmob_id = match['match_id']

        # 检查是否已存在
        if check_existing_mapping(fotmob_id):
            results['skipped'] += 1
            continue

        # 生成 URL（目前返回 None，因为无法推断哈希）
        url = generate_oddsportal_url_placeholder(
            match['home_team'],
            match['away_team'],
            match['league_name']
        )

        # ⚠️ 准入红线检查：必须有哈希才能插入
        if url is None or not has_valid_hash(url):
            results['rejected_no_hash'] += 1
            if not dry_run:
                logger.warning(f"❌ 拒绝（无哈希）: {fotmob_id} - {match['home_team']} vs {match['away_team']}")
            continue

        # HEAD 请求验证 URL 有效性
        verification = await verify_url_with_head(url)

        if not verification['is_valid']:
            results['rejected_invalid_url'] += 1
            if not dry_run:
                logger.warning(f"❌ 拒绝（URL无效）: {fotmob_id} - HTTP {verification['status_code']}")
            continue

        # 通过所有验证，准备插入
        if not dry_run:
            try:
                cursor.execute("""
                    INSERT INTO matches_mapping
                    (fotmob_id, oddsportal_url, league_name, home_team, away_team,
                     match_date, mapping_method, confidence, review_status, status,
                     verified_at, created_at, updated_at)
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW());
                """, (
                    fotmob_id,
                    url,
                    match['league_name'],
                    match['home_team'],
                    match['away_team'],
                    match['match_date'],
                    'verified',     # 映射方法：已验证
                    1.0,            # 置信度：100%
                    'approved',     # 审核状态：已批准
                    'verified'      # 记录状态：已验证
                ))

                results['inserted'] += 1
                results['verified'] += 1

            except Exception as e:
                logger.error(f"❌ 插入失败: {fotmob_id} - {e}")
        else:
            # 干运行模式，只计数
            results['inserted'] += 1
            results['verified'] += 1

    if not dry_run:
        conn.commit()

    cursor.close()
    conn.close()

    return results


# ============================================================================
# 报告生成
# ============================================================================

def print_report(league_name: str, season: str, results: Dict):
    """打印对齐报告

    Args:
        league_name: 联赛名称
        season: 赛季
        results: 结果字典
    """
    print("=" * 70)
    print(f"🌍 {league_name} 对齐任务报告 (V2.0 - 强制哈希校验)")
    print("=" * 70)
    print()

    print(f"📊 赛季: {season}")
    print()

    print(f"📈 对齐结果:")
    print("-" * 70)
    print(f"  总比赛数:           {results['total']}")
    print(f"  跳过已存在:         {results['skipped']}")
    print(f"  新增记录:           {results['inserted']}")
    print(f"  已验证记录:         {results['verified']}")
    print()
    print(f"🚫 拒绝统计:")
    print("-" * 70)
    print(f"  无哈希拒绝:         {results['rejected_no_hash']}")
    print(f"  URL 无效拒绝:       {results['rejected_invalid_url']}")

    if results['dry_run']:
        print()
        print("⚠️  当前为干运行模式，未实际插入记录")
        print()
        print("💡 要执行实际插入操作，请运行:")
        print(f"   python {__file__} --league \"{league_name}\" --execute")
        print()

    print("=" * 70)


# ============================================================================
# 主函数
# ============================================================================

async def main_async():
    """异步主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V29.0 新联赛对齐脚本 V2 - 强制哈希校验版本"
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
        default='2023/2024',
        help='赛季代码（默认: 2023/2024）'
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
    dry_run = not args.execute

    # 步骤 1: 获取比赛数据
    print(f"\n📊 步骤 1: 从 matches 表获取 {league_name} ({args.season}) 的比赛数据...")
    matches = fetch_matches_from_league(league_name, args.season, args.limit)
    print(f"✅ 获取到 {len(matches)} 场比赛")

    # 步骤 2: 插入 matches_mapping（强制哈希校验）
    print(f"\n🔗 步骤 2: 生成 matches_mapping 记录（强制哈希校验）...")
    results = await insert_matches_mapping_verified(matches, dry_run=dry_run)

    # 步骤 3: 打印报告
    print()
    print_report(league_name, args.season, results)

    # 步骤 4: 说明当前限制
    print("\n" + "=" * 70)
    print("⚠️  当前限制说明")
    print("=" * 70)
    print()
    print("由于 OddsPortal URL 的哈希无法推断，当前版本无法自动生成有效 URL。")
    print()
    print("💡 推荐方案：")
    print("  1. 使用 OddsPortal 搜索功能获取真实 URL")
    print("  2. 通过浏览器自动化搜索队名获取哈希")
    print("  3. 使用第三方数据源获取 OddsPortal 映射关系")
    print()
    print("🚨 准入红线：")
    print("  严禁插入无有效 8 位哈希的记录！")
    print()

    print("✅ 对齐任务完成")


def main():
    """命令行入口"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
