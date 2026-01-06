#!/usr/bin/env python3
"""
V150.5: V26 Gold TSV 高速入库脚本
========================================

功能:
  - 从 V26_Gold_9305.tsv 导入 9,308 场比赛数据
  - 使用 pandas 分块读取防止内存溢出
  - 自动解析 adaptive_features JSON 字段
  - 批量插入数据库

使用方式:
  python scripts/maintenance/import_v26_gold.py

Author: Data Migration & Recovery Expert
Date: 2026-01-06
Version: V150.5
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/import_v26_gold.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# TSV 文件路径
TSV_FILE_PATH = Path("/home/user/projects/FootballPrediction/data/processed/V26_Gold_9305.tsv")

# 分块大小（每批处理的行数）
# V150.5 Production: 优化设置为 1000 以平衡内存和性能
CHUNK_SIZE = 1000


def get_db_engine() -> Engine:
    """获取数据库连接引擎"""
    settings = get_settings()

    # 构建连接字符串
    db_url = (
        f"postgresql://{settings.database.user}:"
        f"{settings.database.password.get_secret_value()}@"
        f"{settings.database.host}:{settings.database.port}/"
        f"{settings.database.name}"
    )

    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False
    )

    return engine


def parse_adaptive_features(adaptive_features_str: str) -> dict[str, Any]:
    """解析 adaptive_features JSON 字符串"""
    try:
        if pd.isna(adaptive_features_str) or adaptive_features_str == "":
            logger.debug("跳过空 adaptive_features")
            return {}
        result = json.loads(adaptive_features_str)
        logger.debug(f"成功解析 adaptive_features，特征数: {len(result)}")
        return result
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"❌ JSON 解析失败: {e}，输入前200字符: {str(adaptive_features_str)[:200]}")
        return {}


def import_tsv_to_database():
    """从 TSV 文件导入数据到数据库"""

    logger.info("=" * 80)
    logger.info("V150.5: V26 Gold TSV 高速入库启动")
    logger.info("=" * 80)

    # 检查文件存在
    if not TSV_FILE_PATH.exists():
        logger.error(f"❌ TSV 文件不存在: {TSV_FILE_PATH}")
        return False

    # 获取文件大小
    file_size_gb = TSV_FILE_PATH.stat().st_size / (1024 ** 3)
    logger.info(f"📁 TSV 文件: {TSV_FILE_PATH}")
    logger.info(f"📊 文件大小: {file_size_gb:.2f} GB")

    # 连接数据库
    logger.info("🔗 连接数据库...")
    engine = get_db_engine()

    # 测试连接
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接成功")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False

    # 统计总行数
    logger.info("📈 统计 TSV 文件总行数...")
    total_file_lines = sum(1 for _ in open(TSV_FILE_PATH, 'r'))
    # V150.5 Fix: 减去 "Timing is on." 行和真正的表头行
    total_rows = total_file_lines - 2
    logger.info(f"📊 文件总行数: {total_file_lines:,} (包含标题)")
    logger.info(f"📊 数据行数: {total_rows:,} (跳过 'Timing is on.' 行后)")

    # 分块读取并导入
    logger.info("🚀 开始分块导入...")
    logger.info(f"📦 分块大小: {CHUNK_SIZE} 行/批")

    success_count = 0
    error_count = 0

    # 创建迭代器
    # V150.5 Fix: 跳过第一行 "Timing is on."，真正的表头在第2行
    tsv_iterator = pd.read_csv(
        TSV_FILE_PATH,
        sep='\t',
        chunksize=CHUNK_SIZE,
        low_memory=False,
        skiprows=1  # 跳过 "Timing is on." 行
    )

    # 进度条
    with tqdm(total=total_rows, desc="导入进度", unit="行") as pbar:

        for chunk_index, chunk in enumerate(tsv_iterator, 1):
            try:
                # V150.5 Debug: Chunk 0 详细诊断
                if chunk_index == 1:
                    logger.info("=" * 80)
                    logger.info(f"📊 Chunk 0 诊断信息:")
                    logger.info(f"📋 列名 ({len(chunk.columns)} 列): {list(chunk.columns)}")
                    logger.info(f"📏 Chunk 行数: {len(chunk)}")
                    logger.info(f"📄 第1行数据示例:")
                    first_row = chunk.iloc[0]
                    for col in ['match_id', 'home_team', 'away_team', 'match_date', 'status', 'is_finished']:
                        if col in chunk.columns:
                            logger.info(f"   - {col}: {first_row[col]}")
                    logger.info("=" * 80)

                # 检查必需列是否存在
                required_columns = ['match_id', 'home_team', 'away_team', 'match_date']
                missing_columns = [col for col in required_columns if col not in chunk.columns]
                if missing_columns:
                    logger.error(f"❌ 缺少必需列: {missing_columns}")
                    error_count += CHUNK_SIZE
                    continue

                # 解析 adaptive_features
                if 'adaptive_features' in chunk.columns:
                    chunk['adaptive_features_dict'] = chunk['adaptive_features'].apply(parse_adaptive_features)
                else:
                    chunk['adaptive_features_dict'] = {}
                    logger.warning("⚠️ TSV 文件中没有 'adaptive_features' 列")

                # 准备插入数据
                records = []
                skipped_in_chunk = 0
                for _, row in chunk.iterrows():
                    # 提取基础字段
                    match_id = row.get('match_id')
                    home_team = row.get('home_team')
                    away_team = row.get('away_team')
                    match_date = row.get('match_date')

                    # V150.5: 详细的跳过日志
                    if pd.isna(match_id) or match_id == "":
                        skipped_in_chunk += 1
                        if skipped_in_chunk <= 3:  # 只打印前3个跳过的行
                            logger.warning(f"⚠️ 跳过行: match_id 为空, row_index={row.name}")
                        continue

                    # 构建 l2_raw_json (从 adaptive_features 提取)
                    adaptive_features = row.get('adaptive_features_dict', {})
                    l2_raw_json = {
                        "adaptive_features": adaptive_features,
                        "feature_count": row.get('feature_count', 0),
                        "feature_version": row.get('feature_version', 'V26.1')
                    }

                    records.append({
                        'match_id': str(match_id),
                        'external_id': str(match_id),
                        'home_team': home_team,
                        'away_team': away_team,
                        'match_date': match_date,
                        'l2_raw_json': json.dumps(l2_raw_json),
                        'l2_data_version': 'V26.1',
                        'status': row.get('status', 'unknown'),
                        'collection_date': None  # TSV 中没有此字段，设为 None
                    })

                # 批量插入数据库
                with engine.begin() as conn:
                    for record in records:
                        # 使用 ON CONFLICT DO UPDATE 实现断点续传
                        # V150.5 Fix: 使用 CAST 函数替代 :: 操作符
                        query = text("""
                            INSERT INTO matches (
                                match_id, external_id, home_team, away_team,
                                match_date, l2_raw_json, l2_data_version,
                                status, collection_date
                            ) VALUES (
                                :match_id, :external_id, :home_team, :away_team,
                                :match_date, CAST(:l2_raw_json AS JSONB), :l2_data_version,
                                :status, :collection_date
                            )
                            ON CONFLICT (match_id) DO UPDATE SET
                                l2_raw_json = EXCLUDED.l2_raw_json,
                                l2_data_version = EXCLUDED.l2_data_version,
                                updated_at = NOW()
                        """)

                        conn.execute(query, record)

                # V150.5: 跳过行统计
                if skipped_in_chunk > 0:
                    logger.warning(f"⚠️ Chunk {chunk_index}: 跳过 {skipped_in_chunk} 行 (match_id 为空)")

                success_count += len(records)
                pbar.update(len(chunk))

                # 每 10 批输出一次日志
                if chunk_index % 10 == 0:
                    logger.info(f"✅ 已处理 {success_count:,} 行 ({chunk_index * CHUNK_SIZE:,}/{total_rows:,})")

            except Exception as e:
                error_count += CHUNK_SIZE
                logger.error(f"❌ 批次 {chunk_index} 导入失败: {e}")
                continue

    # 最终统计
    total_processed = success_count + error_count
    logger.info("=" * 80)
    logger.info("📊 导入完成统计:")
    logger.info(f"  ✅ 成功: {success_count:,} 行")
    logger.info(f"  ❌ 失败: {error_count:,} 行")
    if total_processed > 0:
        success_rate = success_count / total_processed * 100
        logger.info(f"  📈 成功率: {success_rate:.2f}%")
    else:
        logger.warning(f"  ⚠️ 没有数据被处理 (total_processed = 0)")
    logger.info("=" * 80)

    return True


def verify_import():
    """验证导入结果"""
    logger.info("🔍 验证导入结果...")

    engine = get_db_engine()

    with engine.connect() as conn:
        # 统计 matches 表行数
        result = conn.execute(text("SELECT COUNT(*) as total FROM matches"))
        total_matches = result.scalar()

        # 统计 l2_raw_json 非空的行数
        result = conn.execute(text("""
            SELECT COUNT(*) as l2_count
            FROM matches
            WHERE l2_raw_json IS NOT NULL
        """))
        l2_count = result.scalar()

        # 统计 l2_data_version
        result = conn.execute(text("""
            SELECT l2_data_version, COUNT(*) as count
            FROM matches
            WHERE l2_data_version IS NOT NULL
            GROUP BY l2_data_version
        """))
        version_stats = result.fetchall()

    logger.info(f"📊 matches 表总行数: {total_matches:,}")
    logger.info(f"📊 l2_raw_json 非空行数: {l2_count:,}")
    logger.info(f"📊 l2_data_version 分布:")
    for version, count in version_stats:
        logger.info(f"  - {version}: {count:,} 行")


def main():
    """主函数"""
    try:
        # 创建日志目录
        Path("logs").mkdir(exist_ok=True)

        # 执行导入
        if import_tsv_to_database():
            # 验证导入
            verify_import()
            logger.info("✅ V150.5 入库完成")
            return 0
        else:
            logger.error("❌ V150.5 入库失败")
            return 1

    except Exception as e:
        logger.error(f"❌ 异常: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
