#!/usr/bin/env python3
"""
V41.58: 全库哈希错位深度扫描与修复
====================================
用途: 扫描所有 matches_mapping 记录，检测 URL 赛季与 season 字段不匹配的记录
执行: python scripts/ops/v41_58_deep_season_scan.py
"""

import re
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor


def extract_season_from_url(url: str) -> str | None:
    """从 OddsPortal URL 中提取赛季"""
    if not url:
        return None

    # 匹配模式: 2023-2024, 2024-2025, 2020-2021 等
    match = re.search(r'(\d{4}-\d{4})', url)
    if match:
        season_raw = match.group(1)
        # 转换为数据库格式: 2023-2024 -> 2023/2024
        return season_raw.replace('-', '/')
    return None


def normalize_season(season: str) -> str:
    """标准化赛季格式"""
    if not season:
        return season

    # 处理简化格式: 23/24 -> 2023/2024
    if re.match(r'^\d{2}/\d{2}$', season):
        parts = season.split('/')
        return f"20{parts[0]}/20{parts[1]}"

    return season


def scan_and_fix_misaligned_records():
    """扫描并修复错位记录"""
    settings = get_settings()

    print("=" * 60)
    print("V41.58: 全库哈希错位深度扫描与修复")
    print("=" * 60)
    print(f"数据库: {settings.database.name}")
    print(f"主机: {settings.database.host}")
    print("")

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        with conn.cursor() as cur:
            # =====================================================
            # 步骤 1: 扫描所有有 URL 的记录
            # =====================================================
            print("📊 步骤 1: 扫描所有带 URL 的记录...")

            scan_query = """
                SELECT
                    fotmob_id,
                    league_name,
                    season,
                    oddsportal_url,
                    oddsportal_hash
                FROM matches_mapping
                WHERE oddsportal_url IS NOT NULL
                  AND fotmob_id ~ '^[0-9]+$'  -- 只扫描纯数字 ID
                ORDER BY league_name, season;
            """

            cur.execute(scan_query)
            records = cur.fetchall()

            total_records = len(records)
            print(f"✅ 扫描完成: {total_records} 条带 URL 的记录")
            print("")

            # =====================================================
            # 步骤 2: 检测错位记录
            # =====================================================
            print("🔍 步骤 2: 检测赛季错位...")

            misaligned = []
            for record in records:
                fotmob_id = record['fotmob_id']
                league_name = record['league_name']
                db_season = record['season']
                url = record['oddsportal_url']

                # 标准化数据库赛季
                normalized_db_season = normalize_season(db_season)

                # 提取 URL 赛季
                url_season = extract_season_from_url(url)

                if url_season:
                    # 标准化 URL 赛季
                    normalized_url_season = normalize_season(url_season)

                    # 检查是否匹配
                    if normalized_db_season != normalized_url_season:
                        misaligned.append({
                            'fotmob_id': fotmob_id,
                            'league_name': league_name,
                            'db_season': db_season,
                            'url_season': url_season,
                            'url': url
                        })

            misaligned_count = len(misaligned)

            if misaligned_count == 0:
                print("✅ 恭喜！未发现任何赛季错位记录")
                print("")
                return
            else:
                print(f"⚠️  发现 {misaligned_count} 条错位记录")
                print("")

                # 按联赛分组统计
                league_stats = {}
                for record in misaligned:
                    league = record['league_name']
                    if league not in league_stats:
                        league_stats[league] = []
                    league_stats[league].append(record)

                print("📋 错位记录按联赛分布:")
                for league, records in sorted(league_stats.items()):
                    print(f"  - {league}: {len(records)} 条")
                print("")

                # 显示前 10 条错位记录
                print("🔍 错位记录详情（前 10 条）:")
                for i, record in enumerate(misaligned[:10], 1):
                    print(f"  {i}. [{record['league_name']}] fotmob_id={record['fotmob_id']}")
                    print(f"     DB Season: {record['db_season']} | URL Season: {record['url_season']}")
                    print(f"     URL: {record['url'][:80]}...")
                print("")

                if misaligned_count > 10:
                    print(f"  ... 还有 {misaligned_count - 10} 条错位记录")
                    print("")

            # =====================================================
            # 步骤 3: 询问是否修复
            # =====================================================
            print("🚨 V41.58: 检测到错位记录，需要修复！")
            print("")
            response = input("是否立即修复这些错位记录？(yes/no): ").strip().lower()

            if response not in ['yes', 'y']:
                print("❌ 取消修复操作")
                return

            # =====================================================
            # 步骤 4: 执行修复
            # =====================================================
            print("")
            print("🔧 步骤 3: 执行修复...")

            fixed_count = 0
            for record in misaligned:
                fotmob_id = record['fotmob_id']

                # 重置 URL 和 Hash
                fix_query = """
                    UPDATE matches_mapping
                    SET oddsportal_url = NULL,
                        oddsportal_hash = NULL,
                        updated_at = NOW()
                    WHERE fotmob_id = %s;
                """

                cur.execute(fix_query, (fotmob_id,))
                fixed_count += 1

            # 提交事务
            conn.commit()

            print(f"✅ 修复完成: {fixed_count} 条记录已重置")
            print("")

            # =====================================================
            # 步骤 5: 验证修复结果
            # =====================================================
            print("🔍 步骤 4: 验证修复结果...")

            # 重新扫描
            cur.execute(scan_query)
            records_after = cur.fetchall()

            misaligned_after = []
            for record in records_after:
                fotmob_id = record['fotmob_id']
                db_season = record['season']
                url = record['oddsportal_url']

                normalized_db_season = normalize_season(db_season)
                url_season = extract_season_from_url(url)

                if url_season:
                    normalized_url_season = normalize_season(url_season)
                    if normalized_db_season != normalized_url_season:
                        misaligned_after.append(record)

            remaining_misaligned = len(misaligned_after)

            if remaining_misaligned == 0:
                print("✅ 验证通过: 所有错位记录已修复")
            else:
                print(f"⚠️  仍有 {remaining_misaligned} 条错位记录")

            print("")

    finally:
        conn.close()


def main():
    """主函数"""
    try:
        scan_and_fix_misaligned_records()

        print("=" * 60)
        print("V41.58: 物理清淤完成 ✅")
        print("=" * 60)
        print("")
        print("📀 数据库已准备就绪，可以开始收割！")
        print("")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
