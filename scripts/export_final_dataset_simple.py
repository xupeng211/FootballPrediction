#!/usr/bin/env python3
"""
V26.1 黄金训练数据集导出脚本（精简版）

导出基础信息 + JSONB 特征（保持原格式，不展开）。

输出: data/processed/V26_Gold_9305.parquet
"""

import os
import sys
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.database.db_pool import SyncDatabasePool, DatabasePoolConfig


def export_features_simple(output_path):
    """导出基础信息 + JSONB 特征（不展开）"""
    print(f"🔄 开始导出（保持 JSONB 格式）...")

    # 使用同步连接池
    settings = get_settings()
    config = DatabasePoolConfig(
        host=settings.database.host,
        port=settings.database.port,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        database=settings.database.name,
    )
    pool = SyncDatabasePool.get_instance(config)
    pool.init_pool()

    # 分批导出
    batch_size = 500
    all_dfs = []

    with pool.get_connection() as conn:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET statement_timeout = 0")
            cur.execute("""
                SELECT COUNT(*) as total FROM match_features_training
                WHERE feature_version = 'V26.0'
            """)
            total = cur.fetchone()['total']

    print(f"📊 总计 {total} 条记录")

    offset = 0
    batch_num = 0

    while offset < total:
        batch_num += 1
        print(f"  处理批次 {batch_num} (offset {offset})...")

        with pool.get_connection() as conn:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SET statement_timeout = 0")
                cur.execute(f"""
                    SELECT
                        mft.match_id,
                        mft.home_team,
                        mft.away_team,
                        mft.match_date,
                        m.home_score,
                        m.away_score,
                        mft.adaptive_features,
                        mft.feature_version,
                        mft.feature_count,
                        mft.season,
                        m.status,
                        m.is_finished
                    FROM match_features_training mft
                    INNER JOIN matches m ON mft.match_id = m.match_id
                    WHERE mft.feature_version = 'V26.0'
                    ORDER BY mft.match_id
                    LIMIT {batch_size} OFFSET {offset}
                """)
                rows = cur.fetchall()

        batch_df = pd.DataFrame([dict(row) for row in rows])
        all_dfs.append(batch_df)

        offset += len(rows)

        if len(rows) < batch_size:
            break

    # 合并所有批次
    print("🔧 合并数据...")
    df = pd.concat(all_dfs, ignore_index=True)

    return df


def main():
    """主函数"""
    print("=" * 60)
    print("V26.1 黄金训练数据集导出（精简版 - JSONB 不展开）")
    print("=" * 60)

    output_path = Path("data/processed/V26_Gold_9305.parquet")

    try:
        df = export_features_simple(output_path)

        if df.empty:
            print("❌ 没有找到数据!")
            return

        print(f"\n📊 数据状态:")
        print(f"  - 总记录数: {len(df)}")
        print(f"  - 总列数: {len(df.columns)}")
        print(f"  - 有比分数据: {(df['home_score'].notna() & df['away_score'].notna()).sum()}")

        # 导出为 Parquet
        print(f"\n💾 导出到 {output_path}...")
        df.to_parquet(output_path, index=False, compression='snappy')

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ 导出完成!")
        print(f"  - 文件路径: {output_path}")
        print(f"  - 文件大小: {file_size_mb:.1f} MB")

        print(f"\n📋 数据预览:")
        print(df[['match_id', 'home_team', 'away_team', 'match_date', 'feature_count']].head(3))

        print(f"\n📌 使用说明:")
        print(f"  - adaptive_features 列包含完整的 JSONB 特征")
        print(f"  - 使用 pd.json_normalize() 展开特征")
        print(f"  - 示例: features = pd.json_normalize(df['adaptive_features'])")

    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
