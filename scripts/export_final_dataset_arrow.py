#!/usr/bin/env python3
"""
V26.1 黄金训练数据集导出脚本（PyArrow 流式写入版）

导出 match_features_training 表中的全部 V26.0 特征数据。
使用 PyArrow 流式写入避免内存溢出。

输出: data/processed/V26_Gold_9305.parquet
"""

import os
import sys
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.database.db_pool import SyncDatabasePool, DatabasePoolConfig


def export_with_arrow(output_path, batch_size=100):
    """使用 PyArrow 流式写入导出"""
    print(f"🔄 使用 PyArrow 流式导出 (批次大小: {batch_size})...")

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

    # 获取所有 match_id
    with pool.get_connection() as conn:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET statement_timeout = 0")
            cur.execute("""
                SELECT match_id FROM match_features_training
                WHERE feature_version = 'V26.0'
                ORDER BY match_id
            """)
            all_ids = [row['match_id'] for row in cur.fetchall()]

    print(f"📊 总计 {len(all_ids)} 条记录")

    # 创建 ParquetWriter（无模式，使用第一批数据定义）
    writer = None
    schema = None
    batch_count = 0

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
                        mft.season,
                        m.status,
                        m.is_finished
                    FROM match_features_training mft
                    INNER JOIN matches m ON mft.match_id = m.match_id
                    WHERE mft.match_id IN ({placeholders})
                """, batch_ids)
                rows = cur.fetchall()

        # 处理数据 - 展开 JSONB
        batch_records = []
        for row in rows:
            row_dict = dict(row)
            features = row_dict.pop('adaptive_features', {})
            if isinstance(features, dict):
                row_dict.update(features)
            batch_records.append(row_dict)

        # 第一批：建立 schema
        if batch_count == 0:
            # 收集所有可能的键
            all_keys = set()
            for record in batch_records:
                all_keys.update(record.keys())

            # 构建 schema
            fields = []
            for key in sorted(all_keys):
                val = batch_records[0].get(key)
                if val is None:
                    pa_type = pa.string()
                elif isinstance(val, bool):
                    pa_type = pa.bool_()
                elif isinstance(val, int):
                    pa_type = pa.int32()
                elif isinstance(val, float):
                    pa_type = pa.float32()
                else:
                    pa_type = pa.string()

                fields.append(pa.field(key, pa_type))

            schema = pa.schema(fields)
            print(f"    建立 Schema，字段数: {len(schema)}")

            # 创建 writer
            writer = pq.ParquetWriter(output_path, schema, compression='snappy')

        # 转换为 Arrow RecordBatch
        arrays = []
        for field_name in schema.names:
            values = []
            for record in batch_records:
                val = record.get(field_name)
                # 类型转换
                if pa.types.is_boolean(schema.field(field_name).type):
                    values.append(bool(val) if val is not None else None)
                elif pa.types.is_int32(schema.field(field_name).type):
                    values.append(int(val) if val is not None else None)
                elif pa.types.is_float32(schema.field(field_name).type):
                    values.append(float(val) if val is not None else None)
                else:
                    values.append(str(val) if val is not None else None)
            arrays.append(pa.array(values, type=schema.field(field_name).type))

        batch = pa.RecordBatch.from_arrays(arrays, schema=schema)
        writer.write_batch(batch)
        batch_count += 1

    # 关闭 writer
    if writer:
        writer.close()

    # 读取最终文件获取统计
    final_df = pq.read_table(output_path).to_pandas()
    return final_df


def main():
    """主函数"""
    print("=" * 60)
    print("V26.1 黄金训练数据集导出 (PyArrow 流式版)")
    print("=" * 60)

    output_path = Path("data/processed/V26_Gold_9305.parquet")

    try:
        df = export_with_arrow(output_path, batch_size=100)

        if df.empty:
            print("❌ 没有找到数据!")
            return

        print(f"\n📊 数据状态:")
        print(f"  - 总记录数: {len(df)}")
        print(f"  - 总列数: {len(df.columns)}")
        print(f"  - 有比分数据: {(df['home_score'].notna() & df['away_score'].notna()).sum()}")

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ 导出完成!")
        print(f"  - 文件路径: {output_path}")
        print(f"  - 文件大小: {file_size_mb:.1f} MB")

        print(f"\n📋 数据预览:")
        print(df[['match_id', 'home_team', 'away_team', 'match_date']].head(3))

    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
