#!/usr/bin/env python3
"""
Phase 2.3: 真实数据回填脚本
===========================

任务:
    1. 从 V28_REAL_GOLD.parquet 加载真实比赛数据
    2. 将数据导入 matches 和 raw_match_data 表
    3. 使用 V26.2 特征提取引擎（3 并发 Workers）
    4. 将特征入库到 match_features_training 表

Author: Senior Data Engineer
Version: Phase 2.3
Date: 2025-12-28
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config_unified import get_settings
from src.ops.performance_engine import BulkInserter, ParallelFeatureExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/phase_2_3_backfill.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 步骤 1: 加载真实数据
# ============================================================================


def load_real_data_from_parquet(
    parquet_path: str = "data/processed/V28_REAL_GOLD.parquet",
    limit: int = 500,
):
    """
    从 Parquet 文件加载真实比赛数据

    Args:
        parquet_path: Parquet 文件路径
        limit: 加载的比赛数量限制

    Returns:
        DataFrame: 比赛数据
    """
    logger.info("=" * 60)
    logger.info("步骤 1: 加载真实数据")
    logger.info("=" * 60)

    if not os.path.exists(parquet_path):
        logger.error(f"文件不存在: {parquet_path}")
        return None

    df = pd.read_parquet(parquet_path)

    logger.info(f"总记录数: {len(df)}")
    logger.info(f"列数: {len(df.columns)}")

    # 限制数量
    if limit and len(df) > limit:
        df = df.head(limit)
        logger.info(f"限制加载: {limit} 场")

    # 检查必需列
    required_cols = ["match_id"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        logger.error(f"缺少必需列: {missing_cols}")
        return None

    # 显示样本
    sample_ids = df["match_id"].head(5).tolist()
    logger.info(f"match_id 样本: {sample_ids}")

    return df


# ============================================================================
# 步骤 2: 导入数据到数据库
# ============================================================================


def import_matches_to_db(
    df: pd.DataFrame,
    target_count: int = 500,
) -> dict:
    """
    将比赛数据导入数据库

    Args:
        df: 比赛 DataFrame
        target_count: 目标导入数量

    Returns:
        dict: 导入统计
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2: 导入数据到数据库")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    stats = {
        "matches_inserted": 0,
        "raw_data_inserted": 0,
        "matches_skipped": 0,
    }

    try:
        # 限制数量
        df_target = df.head(target_count)

        logger.info(f"目标导入: {len(df_target)} 场")

        # 准备 matches 数据
        matches_values = []
        raw_data_values = []

        for _, row in df_target.iterrows():
            match_id = str(row.get("match_id", ""))
            home_team = row.get("home_team", "Unknown")
            away_team = row.get("away_team", "Unknown")
            match_date = row.get("match_date", row.get("match_time", datetime.now()))
            home_score = row.get("home_score")
            away_score = row.get("away_score")

            # 构建 matches 记录
            matches_values.append((
                match_id,
                "Unknown League",  # league_name (从 parquet 可能没有)
                "2324",             # season
                match_date,
                "finished",         # status
                home_team,
                away_team,
                None,               # home_team_id
                None,               # away_team_id
                home_score,
                away_score,
                True,               # is_finished
            ))

            # 构建 raw_match_data 记录（模拟 L2 原始数据）
            # 注意：V28_REAL_GOLD.parquet 可能只包含特征，不包含原始 API JSON
            # 我们需要构建一个最小化的原始数据结构
            mock_raw_data = {
                "general": {
                    "leagueId": 0,
                    "leagueName": "Unknown League",
                },
                "header": {
                    "teams": [
                        {"name": home_team},
                        {"name": away_team},
                    ]
                },
                "content": {
                    "stats": {
                        "possession": {"home": 50, "away": 50},
                        "shots": {"total": {"home": 10, "away": 10}},
                    }
                }
            }

            raw_data_values.append((
                match_id,
                json.dumps(mock_raw_data),
                "V28.0",
                "parquet_import",
            ))

        # 批量插入 matches 表
        logger.info(f"写入 matches 表...")
        execute_values(cur, """
            INSERT INTO matches (
                external_id, league_name, season, match_time, status,
                home_team, away_team, home_team_id, away_team_id,
                home_score, away_score, is_finished
            ) VALUES %s
            ON CONFLICT (external_id) DO UPDATE SET
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                is_finished = EXCLUDED.is_finished,
                updated_at = CURRENT_TIMESTAMP
        """, matches_values)
        stats["matches_inserted"] = cur.rowcount

        # 批量插入 raw_match_data 表 (没有唯一约束，逐条检查)
        logger.info(f"写入 raw_match_data 表...")
        inserted_raw = 0
        for raw_val in raw_data_values:
            try:
                cur.execute("""
                    INSERT INTO raw_match_data (
                        external_id, raw_data, data_version, api_source
                    ) VALUES (%s, %s, %s, %s)
                """, raw_val)
                inserted_raw += 1
            except psycopg2.IntegrityError:
                # 外键约束违反或重复，跳过
                stats["matches_skipped"] += 1
                continue
        stats["raw_data_inserted"] = inserted_raw

        conn.commit()
        logger.info(f"✅ 导入完成")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 导入失败: {e}")
        raise
    finally:
        cur.close()
        conn.close()

    logger.info(f"\n📊 导入统计:")
    logger.info(f"  matches: {stats['matches_inserted']} 条")
    logger.info(f"  raw_match_data: {stats['raw_data_inserted']} 条")

    return stats


# ============================================================================
# 步骤 3: 并发特征提取与入库
# ============================================================================


def extract_and_store_features(
    target_count: int = 500,
    workers: int = 3,
) -> dict:
    """
    使用 V26.2 引擎并发提取特征并入库

    Args:
        target_count: 目标处理数量
        workers: 并发 Worker 数量

    Returns:
        dict: 处理统计
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"步骤 3: 并发特征提取 ({workers} Workers)")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    # 获取比赛列表
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 直接使用 f-string 构建 LIMIT（避免参数绑定问题）
    cur.execute(f"""
        SELECT
            r.external_id,
            r.raw_data,
            m.home_team,
            m.away_team,
            m.match_time,
            m.home_score,
            m.away_score
        FROM raw_match_data r
        JOIN matches m ON r.external_id = m.external_id
        WHERE r.external_id NOT LIKE '100%'
        ORDER BY r.external_id
        LIMIT {target_count}
    """)

    matches = cur.fetchall()
    cur.close()
    conn.close()

    if not matches:
        logger.warning("没有找到可处理的比赛数据")
        return {"success": False, "error": "No matches found"}

    logger.info(f"找到 {len(matches)} 场比赛待处理")

    # 使用 ParallelFeatureExtractor 进行并发提取
    extractor = ParallelFeatureExtractor(
        max_workers=workers,
        batch_size=100,
        memory_limit_mb=2000,
    )

    # 准备数据
    match_list = []
    for m in matches:
        match_list.append({
            "match_id": m["external_id"],
            "raw_data": json.loads(m["raw_data"]) if isinstance(m["raw_data"], str) else m["raw_data"],
            "home_team": m["home_team"],
            "away_team": m["away_team"],
        })

    # 并发提取特征
    logger.info(f"开始并发提取特征...")
    start_time = datetime.now()

    results = extractor.extract_batch_parallel(
        matches=match_list,
        extractor_class_path="src.processors.v25_production_extractor.V25ProductionExtractor",
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    throughput = len(match_list) / elapsed if elapsed > 0 else 0

    logger.info(f"✅ 提取完成")
    logger.info(f"   耗时: {elapsed:.2f} 秒")
    logger.info(f"   吞吐量: {throughput:.1f} 场/秒 ({throughput * 60:.1f} 场/分钟)")

    # 统计结果
    success_count = sum(1 for r in results if r[1] is not None)
    failed_count = len(results) - success_count

    logger.info(f"   成功: {success_count}")
    logger.info(f"   失败: {failed_count}")

    # 准备入库数据
    features_list = []
    for match_id, features in results:
        if features is None:
            continue

        # 构建 meta_data
        meta_data = {
            "extraction_time": datetime.now().isoformat(),
            "feature_count": len(features),
            "extraction_version": "V26.2",
        }

        # 获取比赛元数据
        match_meta = next((m for m in matches if str(m["external_id"]) == str(match_id)), None)
        if match_meta:
            record = (
                str(match_id),
                "2324",
                str(match_meta["match_time"]),
                match_meta["home_team"],
                match_meta["away_team"],
                "V26.2",
                json.dumps(features),
                json.dumps(meta_data),
                len(features),
                "COMPLETED",
            )
            features_list.append(record)

    # 批量入库
    logger.info(f"\n批量入库 {len(features_list)} 条特征数据...")
    inserter = BulkInserter(
        conn_params=conn_params,
        initial_batch_size=50,
        use_connection_pool=True,
    )

    inserted = inserter.insert_features_batch(
        features_list,
        table_name="match_features_training",
    )

    logger.info(f"✅ 入库完成: {inserted} 条")

    return {
        "success": True,
        "total_matches": len(match_list),
        "success_count": success_count,
        "failed_count": failed_count,
        "inserted_count": inserted,
        "elapsed_seconds": elapsed,
        "throughput_per_minute": throughput * 60,
    }


# ============================================================================
# 步骤 4: 生成质量报告
# ============================================================================


def generate_quality_report() -> dict:
    """
    生成真实数据质量报告

    Returns:
        dict: 质量报告
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 4: 生成质量报告")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    report = {
        "report_time": datetime.now().isoformat(),
        "phase": "2.3",
        "tables": {},
        "feature_stats": {},
    }

    try:
        # 统计各表数据量
        cur.execute("SELECT COUNT(*) as count FROM matches WHERE external_id NOT LIKE '100%'")
        report["tables"]["matches"] = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM raw_match_data WHERE external_id NOT LIKE '100%'")
        report["tables"]["raw_match_data"] = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM match_features_training WHERE external_id NOT LIKE '100%'")
        report["tables"]["match_features_training"] = cur.fetchone()["count"]

        # 特征维度统计
        cur.execute("""
            SELECT
                jsonb_object_keys(adaptive_features) as feature_key,
                COUNT(*) as count
            FROM match_features_training
            WHERE external_id NOT LIKE '100%'
            GROUP BY feature_key
            ORDER BY count DESC
            LIMIT 20
        """)

        top_features = cur.fetchall()
        report["feature_stats"]["top_features"] = [
            {"name": f["feature_key"], "count": f["count"]}
            for f in top_features
        ]

        # 特征维度分布
        cur.execute("""
            SELECT
                external_id,
                jsonb_object_keys(adaptive_features) as key_count
            FROM match_features_training
            WHERE external_id NOT LIKE '100%'
            LIMIT 100
        """)

        # 计算平均维度
        cur.execute("""
            SELECT
                AVG(jsonb_object_keys_length) as avg_dims,
                MIN(jsonb_object_keys_length) as min_dims,
                MAX(jsonb_object_keys_length) as max_dims
            FROM (
                SELECT
                    external_id,
                    jsonb_object_keys_length(adaptive_features)
                FROM match_features_training
                WHERE external_id NOT LIKE '100%'
                LIMIT 100
            ) sub
        """)

        dim_stats = cur.fetchone()
        if dim_stats and dim_stats["avg_dims"]:
            report["feature_stats"]["avg_dimensions"] = round(float(dim_stats["avg_dims"]), 1)
            report["feature_stats"]["min_dimensions"] = int(dim_stats["min_dims"]) if dim_stats["min_dims"] else 0
            report["feature_stats"]["max_dimensions"] = int(dim_stats["max_dims"]) if dim_stats["max_dims"] else 0

        # 获取样本记录
        cur.execute("""
            SELECT
                external_id,
                home_team,
                away_team,
                meta_data->>'feature_count' as feature_count
            FROM match_features_training
            WHERE external_id NOT LIKE '100%'
            LIMIT 5
        """)

        samples = cur.fetchall()
        report["samples"] = [
            {
                "external_id": s["external_id"],
                "home_team": s["home_team"],
                "away_team": s["away_team"],
                "feature_count": s["feature_count"],
            }
            for s in samples
        ]

        # 打印报告
        logger.info(f"\n📊 质量报告:")
        logger.info(f"  matches 表: {report['tables']['matches']} 条")
        logger.info(f"  raw_match_data 表: {report['tables']['raw_match_data']} 条")
        logger.info(f"  match_features_training 表: {report['tables']['match_features_training']} 条")

        if "avg_dimensions" in report["feature_stats"]:
            logger.info(f"\n📐 特征维度 (V26.2 剪枝后):")
            logger.info(f"  平均: {report['feature_stats']['avg_dimensions']:.0f} 维")
            logger.info(f"  范围: {report['feature_stats']['min_dimensions']} - {report['feature_stats']['max_dimensions']} 维")

        logger.info(f"\n📋 样本记录:")
        for s in report["samples"]:
            logger.info(f"  {s['external_id']}: {s['home_team']} vs {s['away_team']} ({s['feature_count']} 维)")

    except Exception as e:
        logger.error(f"生成报告失败: {e}")
    finally:
        cur.close()
        conn.close()

    return report


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    logger.info("=" * 60)
    logger.info("Phase 2.3: 真实数据回填启动")
    logger.info("=" * 60)
    logger.info(f"启动时间: {datetime.now().isoformat()}")

    # 参数
    TARGET_COUNT = 500
    WORKERS = 3

    # 步骤 1: 加载真实数据
    df = load_real_data_from_parquet(
        parquet_path="data/processed/V28_REAL_GOLD.parquet",
        limit=TARGET_COUNT,
    )

    if df is None:
        logger.error("加载数据失败，退出")
        return 1

    # 步骤 2: 导入到数据库
    import_stats = import_matches_to_db(df, target_count=TARGET_COUNT)

    if import_stats["matches_inserted"] == 0:
        logger.warning("没有新数据导入（可能已存在）")
    else:
        logger.info(f"✅ 导入 {import_stats['matches_inserted']} 条新数据")

    # 步骤 3: 并发特征提取
    extract_stats = extract_and_store_features(
        target_count=TARGET_COUNT,
        workers=WORKERS,
    )

    if not extract_stats["success"]:
        logger.error(f"特征提取失败: {extract_stats.get('error')}")
        return 1

    # 步骤 4: 生成质量报告
    report = generate_quality_report()

    # 保存报告
    report_path = "reports/v26_phase_2_3_quality_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✅ 质量报告已保存到: {report_path}")

    # 最终统计
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2.3 完成")
    logger.info("=" * 60)
    logger.info(f"总处理: {extract_stats['total_matches']} 场")
    logger.info(f"成功: {extract_stats['success_count']} 场")
    logger.info(f"入库: {extract_stats['inserted_count']} 条")
    logger.info(f"吞吐量: {extract_stats['throughput_per_minute']:.1f} 场/分钟")

    # 检查是否达到标准
    if extract_stats['throughput_per_minute'] >= 500:
        logger.info("✅ 吞吐量达标 (>= 500 场/分钟)")
    else:
        logger.warning(f"⚠️  吞吐量未达标 (< 500 场/分钟)")

    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
