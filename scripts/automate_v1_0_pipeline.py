#!/usr/bin/env python3
"""
V1.0 主流水线 - 全自动化数据流处理
===================================

功能:
1. 检查 L2 原始数据更新 (raw_match_data 表)
2. 触发 L3 特征提取 (V38.5.1-Hardened)
3. 准备 V27.0 训练数据

作者: Senior DevOps Engineer
日期: 2025-12-29
Phase: V1.0 Production Pipeline
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from tabulate import tabulate

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.collectors.l3_feature_processor_v38_5_1 import (
    L3FeatureExtractor,
    L3FeaturePersister,
)
from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================
# 步骤 1: 检查 L2 更新
# ============================================


def check_l2_updates(conn) -> dict:
    """
    检查 L2 原始数据表中的新比赛

    Returns:
        dict: {
            "total_matches": int,
            "pending_extraction": int,
            "new_matches": list[dict]
        }
    """
    logger.info("步骤 1: 检查 L2 原始数据更新...")

    # 检查 raw_match_data 中的比赛总数
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT COUNT(*) as total_count
            FROM raw_match_data
        """)
        total_count = cursor.fetchone()["total_count"]

        # 检查未提取的比赛 (不在 match_features_v1 中的)
        cursor.execute("""
            SELECT rmd.match_id, m.league_id, m.season, m.match_date
            FROM raw_match_data rmd
            LEFT JOIN matches m ON rmd.match_id = m.match_id
            LEFT JOIN match_features_v1 mf ON rmd.match_id = mf.match_id
            WHERE mf.match_id IS NULL
            ORDER BY m.match_date DESC
            LIMIT 1000
        """)
        new_matches = cursor.fetchall()

    result = {
        "total_matches": total_count,
        "pending_extraction": len(new_matches),
        "new_matches": new_matches,
    }

    logger.info(f"  L2 总数: {result['total_matches']} 场")
    logger.info(f"  待提取: {result['pending_extraction']} 场")

    return result


# ============================================
# 步骤 2: 触发 L3 特征提取
# ============================================


def trigger_l3_extraction(conn, new_matches: list, batch_size: int = 100) -> dict:
    """
    批量触发 L3 特征提取

    Args:
        conn: 数据库连接
        new_matches: 待提取的比赛列表
        batch_size: 批量大小

    Returns:
        dict: 提取结果统计
    """
    logger.info("步骤 2: 触发 L3 特征提取...")

    # 初始化提取器和持久化器
    extractor = L3FeatureExtractor()
    persister = L3FeaturePersister()
    persister.connect()
    persister.create_table()

    stats = {
        "success": 0,
        "failed": 0,
        "partial": 0,
        "warnings": 0,
    }

    # 批量处理
    total = len(new_matches)
    for i in range(0, total, batch_size):
        batch = new_matches[i : i + batch_size]
        logger.info(f"  处理批次 {i // batch_size + 1}/{(total + batch_size - 1) // batch_size} ({len(batch)} 场)")

        for match in batch:
            try:
                # 从数据库获取原始 JSON
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT raw_data
                        FROM raw_match_data
                        WHERE match_id = %s
                    """,
                        (match["match_id"],),
                    )
                    row = cursor.fetchone()

                    if not row or not row.get("raw_data"):
                        logger.warning(f"    比赛 {match['match_id']} 无原始数据")
                        stats["failed"] += 1
                        continue

                    raw_data = row["raw_data"]

                # 提取特征
                features = extractor.extract_features(
                    match_id=match["match_id"],
                    league_id=match.get("league_id", 0),
                    season=match.get("season", "unknown"),
                    raw_data=raw_data,
                )

                # 持久化
                persister.add_to_buffer(features)

                # 更新统计
                if features.extraction_quality == "full":
                    stats["success"] += 1
                elif features.extraction_quality == "partial":
                    stats["partial"] += 1
                else:
                    stats["failed"] += 1

                if features.warnings:
                    stats["warnings"] += len(features.warnings)

            except Exception as e:
                logger.error(f"    比赛 {match['match_id']} 提取失败: {e}")
                stats["failed"] += 1

        # 批量写入
        persister.force_flush()

    persister.close()

    logger.info(f"  提取完成: 成功 {stats['success']}, 部分成功 {stats['partial']}, 失败 {stats['failed']}")
    logger.info(f"  警告数: {stats['warnings']}")

    return stats


# ============================================
# 步骤 3: 准备 V27.0 训练数据
# ============================================


def prepare_training_data(conn, league_id: int = 47) -> dict:
    """
    准备 V27.0 训练数据

    Args:
        conn: 数据库连接
        league_id: 联赛 ID (默认 47 = 英超)

    Returns:
        dict: 训练数据统计
    """
    logger.info("步骤 3: 准备 V27.0 训练数据...")

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # 获取可训练的比赛数据
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN extraction_quality = 'full' THEN 1 END) as full_quality,
                COUNT(CASE WHEN season = '24/25' THEN 1 END) as current_season,
                AVG(valid_feature_count) as avg_features
            FROM match_features_v1
            WHERE league_id = %s
        """,
            (league_id,),
        )

        row = cursor.fetchone()

        # 按赛季统计
        cursor.execute(
            """
            SELECT
                season,
                COUNT(*) as count,
                AVG(valid_feature_count) as avg_features
            FROM match_features_v1
            WHERE league_id = %s
            GROUP BY season
            ORDER BY season
        """,
            (league_id,),
        )
        seasons = cursor.fetchall()

    result = {
        "league_id": league_id,
        "total": row["total"],
        "full_quality": row["full_quality"],
        "current_season": row["current_season"],
        "avg_features": round(row["avg_features"], 2),
        "by_season": list(seasons),
    }

    logger.info(f"  联赛 {league_id}: {result['total']} 场")
    logger.info(f"  Full 质量: {result['full_quality']} 场")
    logger.info(f"  平均特征数: {result['avg_features']}")

    return result


# ============================================
# 步骤 4: 生成流水线报告
# ============================================


def generate_pipeline_report(l2_result: dict, l3_result: dict, training_result: dict) -> str:
    """生成流水线执行报告"""

    report_lines = [
        "=" * 80,
        " " * 30 + "V1.0 流水线执行报告",
        "=" * 80,
        f"执行时间: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "步骤 1: L2 原始数据检查",
        "-" * 40,
        f"  总比赛数: {l2_result['total_matches']:,}",
        f"  待提取: {l2_result['pending_extraction']:,}",
        "",
        "步骤 2: L3 特征提取",
        "-" * 40,
        f"  成功: {l3_result['success']:,}",
        f"  部分成功: {l3_result['partial']:,}",
        f"  失败: {l3_result['failed']:,}",
        f"  警告: {l3_result['warnings']:,}",
        "",
        "步骤 3: 训练数据准备",
        "-" * 40,
        f"  联赛 ID: {training_result['league_id']}",
        f"  总比赛数: {training_result['total']:,}",
        f"  Full 质量: {training_result['full_quality']:,}",
        f"  当前赛季: {training_result['current_season']:,}",
        f"  平均特征数: {training_result['avg_features']}",
        "",
        "按赛季分布:",
    ]

    # 添加赛季分布表格
    season_table = []
    for s in training_result["by_season"]:
        season_table.append(
            [
                s["season"],
                f"{s['count']:,}",
                f"{s['avg_features']:.1f}",
            ]
        )

    if season_table:
        report_lines.append(tabulate(season_table, headers=["赛季", "比赛数", "平均特征"], tablefmt="grid"))

    report_lines.extend(
        [
            "",
            "=" * 80,
            "状态: 流水线执行完成",
            "=" * 80,
        ]
    )

    return "\n".join(report_lines)


# ============================================
# 主流程
# ============================================


def main():
    """主流水线入口"""
    parser = argparse.ArgumentParser(description="V1.0 主流水线")
    parser.add_argument("--league-id", type=int, default=47, help="联赛 ID (默认 47 = 英超)")
    parser.add_argument("--batch-size", type=int, default=100, help="批量大小 (默认 100)")
    parser.add_argument("--dry-run", action="store_true", help="仅检查，不执行提取")

    args = parser.parse_args()

    print("=" * 80)
    print(" " * 25 + "V1.0 主流水线启动")
    print("=" * 80)
    print(f"执行时间: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"联赛 ID: {args.league_id}")
    print(f"批量大小: {args.batch_size}")
    print(f"模式: {'DRY RUN (仅检查)' if args.dry_run else 'NORMAL (执行提取)'}")
    print("=" * 80)
    print()

    # 连接数据库
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )

    try:
        # 步骤 1: 检查 L2 更新
        l2_result = check_l2_updates(conn)

        if args.dry_run:
            print("\n[DRY RUN] 跳过特征提取步骤")
            l3_result = {"success": 0, "failed": 0, "partial": 0, "warnings": 0}
        else:
            # 步骤 2: 触发 L3 特征提取
            if l2_result["pending_extraction"] > 0:
                l3_result = trigger_l3_extraction(conn, l2_result["new_matches"], args.batch_size)
            else:
                print("\n无新比赛需要提取")
                l3_result = {"success": 0, "failed": 0, "partial": 0, "warnings": 0}

        # 步骤 3: 准备训练数据
        training_result = prepare_training_data(conn, args.league_id)

        # 步骤 4: 生成报告
        report = generate_pipeline_report(l2_result, l3_result, training_result)
        print("\n" + report)

        # 保存报告
        report_path = project_root / "logs" / f"v1_0_pipeline_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.log"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n报告已保存: {report_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
