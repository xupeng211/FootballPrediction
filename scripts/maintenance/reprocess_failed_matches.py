#!/usr/bin/env python3
"""
重新处理 FAILED 状态的比赛记录
================================

功能:
  1. 查询 collection_status = 'FAILED' 且有 l2_raw_json 的记录
  2. 使用 V25ProductionExtractor 重新提取特征
  3. 更新 l2_extracted_features 和状态

Author: Senior Development Engineer
Version: V1.0
Date: 2026-01-06
"""

import json
import sys
from typing import Any

sys.path.insert(0, "/home/user/projects/FootballPrediction")

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.processors.v25_production_extractor import V25ProductionExtractor


def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


def get_failed_matches(limit: int = 100) -> list[dict[str, Any]]:
    """
    获取需要重新处理的 FAILED 记录（V26.5: 按联赛优先级排序）

    筛选条件:
    - collection_status = 'FAILED'
    - l2_raw_json IS NOT NULL (有原始数据可重新提取)

    排序规则（V26.5 抢救优先级）:
    1. Tier 1: 5 大联赛（英超、西甲、德甲、意甲、法甲）
    2. Tier 2: 次级联赛（英冠、西乙等）
    3. Tier 3: 其他联赛
    4. 同等级内按 updated_at DESC（最新优先）

    Args:
        limit: 最大处理数量

    Returns:
        失败记录列表（按优先级排序）
    """
    query = """
        SELECT
            match_id,
            l2_raw_json,
            home_team,
            away_team,
            league_name,
            season,
            match_date,
            last_error
        FROM matches
        WHERE collection_status = 'FAILED'
          AND l2_raw_json IS NOT NULL
        ORDER BY
            -- V26.5: 联赛优先级排序（5 大联赛优先）
            CASE
                WHEN league_name IN ('Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1') THEN 1
                WHEN league_name IN ('Championship', 'Segunda División', '2. Bundesliga', 'Serie B', 'Ligue 2') THEN 2
                ELSE 3
            END ASC,
            updated_at DESC
        LIMIT %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]


def reprocess_match(
    match: dict[str, Any],
    extractor: V25ProductionExtractor,
) -> dict[str, Any]:
    """
    重新处理单条记录

    Args:
        match: 比赛记录
        extractor: V25ProductionExtractor 实例

    Returns:
        处理结果
    """
    match_id = match["match_id"]
    raw_json = match["l2_raw_json"]

    # 如果 l2_raw_json 是字符串，先解析
    if isinstance(raw_json, str):
        raw_json = json.loads(raw_json)

    try:
        # 重新提取特征
        result = extractor.extract(raw_json)

        # 保存结果到数据库
        update_query = """
            UPDATE matches SET
                l2_extracted_features = %s::jsonb,
                l2_data_version = %s,
                extracted_at = NOW(),
                collection_status = %s,
                last_error = %s,
                updated_at = NOW()
            WHERE match_id = %s;
        """

        # 准备错误信息
        error_msg = None
        if result.status.value == "FAILED":
            error_msg = "; ".join(result.errors) if result.errors else "Extraction failed"

        params = (
            json.dumps(result.features),
            extractor.version,
            result.status.value,
            error_msg,
            match_id,
        )

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_query, params)
                conn.commit()

        return {
            "match_id": match_id,
            "status": result.status.value,
            "feature_count": len(result.features),
            "success": True,
            "error": None,
        }

    except Exception as e:
        # 记录错误但继续处理下一条
        return {
            "match_id": match_id,
            "status": "ERROR",
            "feature_count": 0,
            "success": False,
            "error": str(e),
        }


def print_summary(results: list[dict[str, Any]]) -> None:
    """打印处理摘要"""
    print("\n" + "=" * 80)
    print("重新处理结果摘要")
    print("=" * 80)

    # 统计
    total = len(results)
    success = sum(1 for r in results if r["success"])
    failed = total - success

    by_status = {}
    for r in results:
        status = r["status"]
        by_status[status] = by_status.get(status, 0) + 1

    print(f"\n总计: {total} 条")
    print(f"成功: {success} 条 ({success/total*100:.1f}%)")
    print(f"失败: {failed} 条 ({failed/total*100:.1f}%)")

    print("\n按状态分布:")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count} 条")

    # 打印失败的记录
    failed_results = [r for r in results if not r["success"]]
    if failed_results:
        print("\n失败详情:")
        for r in failed_results:
            print(f"  {r['match_id']}: {r['error']}")


def main() -> int:
    """主函数"""
    print("=" * 80)
    print("重新处理 FAILED 比赛记录")
    print("=" * 80)

    # 1. 获取需要重新处理的记录
    print("\n正在查找 FAILED 记录...")
    failed_matches = get_failed_matches(limit=100)

    if not failed_matches:
        print("✅ 没有需要重新处理的记录")
        return 0

    print(f"✅ 找到 {len(failed_matches)} 条可重新处理的记录")

    # 2. 创建提取器
    extractor = V25ProductionExtractor()

    # 3. 逐条处理
    results = []
    for i, match in enumerate(failed_matches, 1):
        print(f"\n[{i}/{len(failed_matches)}] 处理 {match['match_id']}: "
              f"{match['home_team']} vs {match['away_team']}")

        if match.get("last_error"):
            print(f"  原错误: {match['last_error']}")

        result = reprocess_match(match, extractor)
        results.append(result)

        if result["success"]:
            print(f"  ✅ 成功: {result['status']}, "
                  f"特征数: {result['feature_count']}")
        else:
            print(f"  ❌ 失败: {result['error']}")

    # 4. 打印摘要
    print_summary(results)

    # 5. 更新数据库统计
    print("\n正在更新数据库统计...")

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    collection_status,
                    COUNT(*) as count
                FROM matches
                GROUP BY collection_status
                ORDER BY count DESC;
            """)
            stats = cursor.fetchall()

            print("\n最新状态分布:")
            for row in stats:
                print(f"  {row['collection_status']}: {row['count']} 条")

    # 返回状态
    has_failures = any(not r["success"] for r in results)

    print("\n" + "=" * 80)
    if has_failures:
        print("⚠️  部分记录处理失败")
        print("=" * 80)
        return 1
    else:
        print("✅ 所有记录处理成功")
        print("=" * 80)
        return 0


if __name__ == "__main__":
    sys.exit(main())
