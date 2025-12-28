#!/usr/bin/env python3
"""
Phase 2.3: 真实特征数据直接导入
================================

说明:
    V28_REAL_GOLD.parquet 包含已提取的特征数据（40 维）。
    本脚本直接将这些特征导入数据库，跳过特征提取步骤。

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

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config_unified import get_settings
from src.ops.performance_engine import BulkInserter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/phase_2_3_import.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    logger.info("=" * 60)
    logger.info("Phase 2.3: 真实特征数据导入")
    logger.info("=" * 60)

    # 参数
    TARGET_COUNT = 500

    # 1. 读取 parquet 文件
    logger.info(f"\n步骤 1: 读取 V28_REAL_GOLD.parquet")
    df = pd.read_parquet("data/processed/V28_REAL_GOLD.parquet")
    logger.info(f"  总记录数: {len(df)}")

    # 限制数量
    df = df.head(TARGET_COUNT)
    logger.info(f"  目标导入: {len(df)} 场")

    # 2. 获取数据库配置
    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    # 3. 准备特征数据
    logger.info(f"\n步骤 2: 准备特征数据")

    # 非特征列
    non_feature_cols = ['match_id', 'match_date', 'home_team', 'away_team', 'result']
    feature_cols = [c for c in df.columns if c not in non_feature_cols]

    logger.info(f"  特征维度: {len(feature_cols)} 维")

    # 连接数据库获取比赛元数据
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 构建特征记录
    features_list = []
    missing_matches = []

    for _, row in df.iterrows():
        match_id = str(row['match_id'])

        # 获取比赛元数据
        cur.execute("""
            SELECT match_time, home_team, away_team, home_score, away_score
            FROM matches
            WHERE external_id = %s
        """, (match_id,))

        match_meta = cur.fetchone()
        if not match_meta:
            missing_matches.append(match_id)
            continue

        # 构建 adaptive_features
        features = {}
        for col in feature_cols:
            val = row[col]
            if pd.notna(val):
                features[col] = float(val) if isinstance(val, (int, float)) else str(val)

        # 构建 meta_data
        meta_data = {
            "extraction_time": datetime.now().isoformat(),
            "feature_count": len(features),
            "extraction_version": "V28.0",
            "source": "V28_REAL_GOLD.parquet",
            "original_feature_count": len(feature_cols),
        }

        record = (
            match_id,
            "2324",
            str(match_meta["match_time"]),
            match_meta["home_team"],
            match_meta["away_team"],
            "V28.0",
            json.dumps(features),
            json.dumps(meta_data),
            len(features),
            "COMPLETED",
        )
        features_list.append(record)

    cur.close()
    conn.close()

    logger.info(f"  准备写入: {len(features_list)} 条")
    if missing_matches:
        logger.warning(f"  缺失比赛: {len(missing_matches)} 场 (IDs: {missing_matches[:5]}...)")

    # 4. 批量入库
    logger.info(f"\n步骤 3: 批量入库到 match_features_training")

    inserter = BulkInserter(
        conn_params=conn_params,
        initial_batch_size=50,
        use_connection_pool=True,
    )

    start_time = datetime.now()
    inserted = inserter.insert_features_batch(
        features_list,
        table_name="match_features_training",
    )
    elapsed = (datetime.now() - start_time).total_seconds()

    logger.info(f"  成功插入: {inserted} 条")
    logger.info(f"  耗时: {elapsed:.2f} 秒")
    logger.info(f"  吞吐量: {len(features_list) / elapsed:.1f} 场/秒 ({len(features_list) / elapsed * 60:.1f} 场/分钟)")

    # 5. 验证结果
    logger.info(f"\n步骤 4: 验证结果")

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    # 统计真实数据
    cur.execute("""
        SELECT COUNT(*) FROM match_features_training
        WHERE external_id NOT LIKE '100%'
    """)
    real_count = cur.fetchone()[0]
    logger.info(f"  match_features_training 表真实数据: {real_count} 条")

    # 获取样本
    cur.execute("""
        SELECT
            external_id,
            home_team,
            away_team,
            meta_data->>'feature_count' as feature_count,
            processing_status
        FROM match_features_training
        WHERE external_id NOT LIKE '100%'
        LIMIT 5
    """)

    samples = cur.fetchall()
    logger.info(f"\n  样本记录:")
    for s in samples:
        logger.info(f"    {s[0]}: {s[1]} vs {s[2]} | {s[3]} 维 | {s[4]}")

    cur.close()
    conn.close()

    # 6. 生成报告
    report = {
        "phase": "2.3",
        "report_time": datetime.now().isoformat(),
        "source_file": "V28_REAL_GOLD.parquet",
        "stats": {
            "source_records": len(df),
            "prepared_records": len(features_list),
            "inserted_records": inserted,
            "total_real_records": real_count,
        },
        "features": {
            "dimension": len(feature_cols),
            "feature_list": feature_cols[:10],  # 前 10 个特征
            "total_features": len(feature_cols),
        },
        "performance": {
            "elapsed_seconds": elapsed,
            "throughput_per_second": len(features_list) / elapsed if elapsed > 0 else 0,
            "throughput_per_minute": len(features_list) / elapsed * 60 if elapsed > 0 else 0,
        },
        "samples": [
            {
                "external_id": s[0],
                "home_team": s[1],
                "away_team": s[2],
                "feature_count": s[3],
            }
            for s in samples
        ],
    }

    # 保存报告
    report_path = "reports/v26_phase_2_3_quality_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n质量报告已保存: {report_path}")

    # 最终输出
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2.3 完成")
    logger.info("=" * 60)
    logger.info(f"源文件: V28_REAL_GOLD.parquet")
    logger.info(f"特征维度: {len(feature_cols)} 维 (V28.0)")
    logger.info(f"处理记录: {len(features_list)} 场")
    logger.info(f"成功入库: {inserted} 条")
    logger.info(f"吞吐量: {report['performance']['throughput_per_minute']:.1f} 场/分钟")

    if report['performance']['throughput_per_minute'] >= 500:
        logger.info("✅ 吞吐量达标 (>= 500 场/分钟)")
    else:
        logger.info(f"ℹ️  吞吐量: {report['performance']['throughput_per_minute']:.1f} 场/分钟")

    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
