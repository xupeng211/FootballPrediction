#!/usr/bin/env python3
"""
V26.1 黄金训练数据集导出脚本（增量写入版）

导出 match_features_training 表中的全部 V26.0 特征数据。
使用增量写入避免内存溢出。

注意：由于 matches 表中的 home_score/away_score 字段为空，
当前导出不含训练标签。需要先补充比分数据后才能生成标签。

输出: data/processed/V26_Gold_9305.parquet
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import tempfile

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.database.db_pool import SyncDatabasePool, DatabasePoolConfig


def export_features_incremental(output_path, batch_size=200):
    """增量导出特征数据，逐批写入避免内存溢出"""
    print(f"🔄 开始增量导出 (批次大小: {batch_size})...")

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

    # 确保目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 获取所有 match_id
    with pool.get_connection() as conn:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET statement_timeout = 0")

            # 获取所有 match_id
            id_query = """
            SELECT mft.match_id
            FROM match_features_training mft
            WHERE mft.feature_version = 'V26.0'
            ORDER BY mft.match_id
            """
            cur.execute(id_query)
            all_ids = [row['match_id'] for row in cur.fetchall()]

    print(f"📊 总计 {len(all_ids)} 条记录")

    # 使用临时文件存储第一批数据作为模板
    temp_parquet_path = output_path.with_suffix('.tmp.parquet')

    first_batch = True
    total_columns = None

    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_ids) - 1) // batch_size + 1

        print(f"  处理批次 {batch_num}/{total_batches} ({len(batch_ids)} 条)...")

        with pool.get_connection() as conn:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SET statement_timeout = 0")

                placeholders = ','.join(['%s'] * len(batch_ids))
                query = f"""
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
                WHERE mft.match_id IN ({placeholders})
                """
                cur.execute(query, batch_ids)
                rows = cur.fetchall()

        # 处理当前批次
        batch_data = []
        for row in rows:
            row_dict = dict(row)
            features = row_dict.pop('adaptive_features', {})
            if isinstance(features, dict):
                row_dict.update(features)
            batch_data.append(row_dict)

        batch_df = pd.DataFrame(batch_data)

        # 优化数据类型
        for col in batch_df.columns:
            if batch_df[col].dtype == 'float64':
                batch_df[col] = batch_df[col].astype('float32')
            elif batch_df[col].dtype == 'int64':
                batch_df[col] = batch_df[col].astype('int32')

        # 第一批创建文件，后续批次追加
        if first_batch:
            total_columns = list(batch_df.columns)
            batch_df.to_parquet(temp_parquet_path, index=False, compression='snappy')
            first_batch = False
            print(f"    创建文件，列数: {len(total_columns)}")
        else:
            # 确保列顺序一致
            batch_df = batch_df.reindex(columns=total_columns)
            # 追加到现有文件
            existing_df = pd.read_parquet(temp_parquet_path)
            combined_df = pd.concat([existing_df, batch_df], ignore_index=True)
            combined_df.to_parquet(temp_parquet_path, index=False, compression='snappy')
            print(f"    追加完成，累计记录: {len(combined_df)}")

    # 重命名为最终文件
    temp_parquet_path.rename(output_path)

    # 读取最终文件获取统计
    final_df = pd.read_parquet(output_path)

    return final_df


def export_to_parquet(df, output_path):
    """显示导出结果"""
    file_size_mb = output_path.stat().st_size / (1024 * 1024)

    print(f"\n✅ 导出完成!")
    print(f"  - 文件路径: {output_path}")
    print(f"  - 文件大小: {file_size_mb:.1f} MB")
    print(f"  - 记录数: {len(df)}")
    print(f"  - 总列数: {len(df.columns)}")


def preview_data(df, n=3):
    """预览数据"""
    print(f"\n📋 数据预览 (前 {n} 场比赛):")
    print("=" * 100)

    # 显示基础列
    base_cols = ['match_id', 'home_team', 'away_team', 'match_date', 'home_score', 'away_score']
    available_base_cols = [col for col in base_cols if col in df.columns]

    preview = df[available_base_cols].head(n)
    for idx, row in preview.iterrows():
        print(f"\n{row['home_team']} vs {row['away_team']} ({row['match_date']})")
        if pd.notna(row['home_score']) and pd.notna(row['away_score']):
            print(f"  比分: {row['home_score']} - {row['away_score']}")
        else:
            print(f"  比分: N/A (无数据)")
        print(f"  Match ID: {row['match_id']}")

    # 显示特征列样本
    all_feature_cols = [col for col in df.columns if col not in base_cols + ['season', 'feature_version', 'status', 'is_finished']]
    print(f"\n📊 特征统计:")
    print(f"  - 总特征列数: {len(all_feature_cols)}")
    print(f"  - 前 10 个特征: {all_feature_cols[:10]}")


def main():
    """主函数"""
    print("=" * 60)
    print("V26.1 黄金训练数据集导出 (增量写入版)")
    print("=" * 60)

    # 1. 增量导出数据
    output_path = Path("data/processed/V26_Gold_9305.parquet")
    df = export_features_incremental(output_path, batch_size=200)

    if df.empty:
        print("❌ 没有找到数据!")
        return

    print(f"\n📊 数据状态:")
    print(f"  - 总记录数: {len(df)}")
    print(f"  - 有比分数据: {(df['home_score'].notna() & df['away_score'].notna()).sum()}")
    print(f"  - 状态分布: {df['status'].value_counts().to_dict()}")

    # 2. 显示导出结果
    export_to_parquet(df, output_path)

    # 3. 预览
    preview_data(df)

    print("\n" + "=" * 60)
    print("✅ 导出完成!")
    print("=" * 60)
    print("\n📌 后续步骤:")
    print("1. 补充比分数据: 运行 L1 采集获取比赛比分")
    print("2. 生成标签: 重新运行此脚本生成 target_win, target_goals 等标签")
    print("3. 模型训练: 使用完整数据集训练 XGBoost 模型")


if __name__ == "__main__":
    main()
