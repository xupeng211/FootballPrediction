#!/usr/bin/env python3
"""
V29.0 数据清洗脚本 - 清理 L2 结构不完整的坏账记录

准入红线：删除 home/draw/away 键值不全的记录，确保数据结构完整性

Author: 数据质量专家
Date: 2026-01-11
"""

import sys
from pathlib import Path

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from src.config_unified import get_settings


def check_malformed_records() -> dict:
    """检查 L2 数据结构不完整的记录

    Returns:
        统计信息字典
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

    # 检查不完整的记录
    cursor.execute("""
        SELECT
            COUNT(*) as total_with_l2,
            COUNT(CASE
                WHEN l2_raw_json IS NOT NULL
                  AND (l2_raw_json->>'home' IS NULL
                       OR l2_raw_json->>'draw' IS NULL
                       OR l2_raw_json->>'away' IS NULL)
                THEN 1
            END) as malformed_count,
            COUNT(CASE
                WHEN l2_raw_json IS NOT NULL
                  AND l2_raw_json->>'home' IS NOT NULL
                  AND l2_raw_json->>'draw' IS NOT NULL
                  AND l2_raw_json->>'away' IS NOT NULL
                THEN 1
            END) as complete_count
        FROM matches_mapping
        WHERE l2_raw_json IS NOT NULL;
    """)

    total, malformed, complete = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        'total_with_l2': total,
        'malformed_count': malformed,
        'complete_count': complete,
        'malformed_rate': round(malformed / total * 100, 2) if total > 0 else 0
    }


def clean_malformed_records(dry_run: bool = True) -> dict:
    """清理不完整的 L2 记录

    Args:
        dry_run: 是否为干运行模式

    Returns:
        清理结果字典
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

    # 查询不完整记录的详情
    cursor.execute("""
        SELECT
            id,
            fotmob_id,
            league_name,
            home_team,
            away_team,
            l2_raw_json
        FROM matches_mapping
        WHERE l2_raw_json IS NOT NULL
          AND (l2_raw_json->>'home' IS NULL
               OR l2_raw_json->>'draw' IS NULL
               OR l2_raw_json->>'away' IS NULL)
        ORDER BY league_name, id;
    """)

    malformed_records = cursor.fetchall()
    columns = ['id', 'fotmob_id', 'league_name', 'home_team', 'away_team', 'l2_raw_json']
    records_list = [dict(zip(columns, row)) for row in malformed_records]

    result = {
        'dry_run': dry_run,
        'records_to_delete': len(records_list),
        'records': records_list[:10]  # 只显示前 10 条
    }

    if not dry_run:
        # 执行删除操作
        cursor.execute("""
            DELETE FROM matches_mapping
            WHERE l2_raw_json IS NOT NULL
              AND (l2_raw_json->>'home' IS NULL
                   OR l2_raw_json->>'draw' IS NULL
                   OR l2_raw_json->>'away' IS NULL);
        """)

        deleted = cursor.rowcount
        conn.commit()

        result['deleted_count'] = deleted
        result['success'] = True
    else:
        result['deleted_count'] = 0
        result['success'] = False

    cursor.close()
    conn.close()

    return result


def print_report(stats: dict, clean_result: dict = None):
    """打印清洗报告

    Args:
        stats: 统计信息
        clean_result: 清理结果（可选）
    """
    print("=" * 70)
    print("📊 V29.0 数据质量报告 - L2 结构完整性检查")
    print("=" * 70)
    print()

    print("📈 当前状态:")
    print("-" * 70)
    print(f"  总 L2 记录数:     {stats['total_with_l2']}")
    print(f"  完整结构记录:     {stats['complete_count']} ({stats['complete_count']/stats['total_with_l2']*100:.1f}%)")
    print(f"  不完整结构记录:   {stats['malformed_count']} ({stats['malformed_rate']:.1f}%)")
    print()

    if clean_result:
        if clean_result['dry_run']:
            print("🔍 干运行模式 - 预览删除操作:")
            print("-" * 70)
            print(f"  预计删除记录数: {clean_result['records_to_delete']}")
            print()
            print("📋 待删除记录预览 (前 10 条):")
            print("-" * 70)
            for i, record in enumerate(clean_result['records'], 1):
                print(f"  {i}. ID={record['id']} | {record['league_name']}")
                print(f"     {record['home_team']} vs {record['away_team']}")
                print(f"     fotmob_id: {record['fotmob_id']}")
                print()
        else:
            print("🧹 清洗操作已完成:")
            print("-" * 70)
            print(f"  已删除记录数: {clean_result['deleted_count']}")
            print(f"  操作状态: {'✅ 成功' if clean_result['success'] else '❌ 失败'}")
            print()

    print("=" * 70)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V29.0 数据清洗脚本 - 清理 L2 结构不完整的坏账记录"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='干运行模式（预览删除操作，不实际执行）'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='执行实际删除操作'
    )

    args = parser.parse_args()

    # 如果指定了 --execute，则关闭干运行模式
    dry_run = args.dry_run and not args.execute

    # 步骤 1: 检查当前状态
    print("\n🔍 步骤 1: 检查 L2 数据结构完整性...")
    stats = check_malformed_records()

    # 步骤 2: 执行清理
    if stats['malformed_count'] > 0:
        print(f"\n🧹 步骤 2: 检测到 {stats['malformed_count']} 条不完整记录，执行清理...")
        clean_result = clean_malformed_records(dry_run=dry_run)

        # 步骤 3: 打印报告
        print_report(stats, clean_result)

        # 如果是干运行模式，提示用户如何执行
        if dry_run and stats['malformed_count'] > 0:
            print("⚠️  当前为干运行模式，未实际删除记录")
            print()
            print("💡 要执行实际删除操作，请运行:")
            print(f"   python {__file__} --execute")
            print()
    else:
        print("\n✅ 所有 L2 记录结构完整，无需清洗")
        print_report(stats)

    print("✅ 数据质量检查完成")


if __name__ == "__main__":
    main()
