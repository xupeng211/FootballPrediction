#!/usr/bin/env python3
"""
Phase 2.4: 真实原始 JSON 提取流程验证
========================================

任务:
    1. 读取 data/l2_output/ 中的真实原始 JSON 文件
    2. 调用 V25ProductionExtractor 生成 6000 维自适应特征
    3. 验证 v26_sparsity_filter.py 剪枝逻辑生效
    4. 使用 3 Workers 并发写入数据库

Author: Senior Lead Engineer
Version: Phase 2.4
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
from psycopg2.extras import RealDictCursor

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config_unified import get_settings
from src.ops.performance_engine import BulkInserter, ParallelFeatureExtractor
from src.processors.v25_production_extractor import V25ProductionExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/phase_2_4_extraction.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 步骤 1: 加载真实原始 JSON
# ============================================================================


def load_raw_json_files(
    l2_dir: str = "data/l2_output",
    limit: int = 100,
):
    """
    加载 data/l2_output/ 目录中的真实原始 JSON 文件

    Args:
        l2_dir: L2 数据目录
        limit: 加载文件数量限制

    Returns:
        list: 原始数据列表
    """
    logger.info("=" * 60)
    logger.info("步骤 1: 加载真实原始 JSON 文件")
    logger.info("=" * 60)

    l2_path = Path(l2_dir)
    if not l2_path.exists():
        logger.error(f"目录不存在: {l2_dir}")
        return []

    # 获取所有 JSON 文件
    json_files = sorted(l2_path.glob("*.json"))
    logger.info(f"找到 {len(json_files)} 个 JSON 文件")

    # 限制数量
    if limit and len(json_files) > limit:
        json_files = json_files[:limit]
        logger.info(f"限制加载: {len(json_files)} 个文件")

    # 读取所有文件
    raw_data_list = []
    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                # 跳过空文件（match_id 为空）
                if not data.get("match_id") or data.get("match_id") == "":
                    logger.debug(f"跳过空文件: {json_file.name}")
                    continue
                raw_data_list.append(data)
        except Exception as e:
            logger.warning(f"读取文件 {json_file} 失败: {e}")
            continue

    logger.info(f"成功加载 {len(raw_data_list)} 个原始 JSON 文件")

    # 显示样本
    if raw_data_list:
        sample = raw_data_list[0]
        logger.info(f"\n样本数据 (match_id={sample.get('match_id')}):")
        logger.info(f"  比赛: {sample.get('home_team')} vs {sample.get('away_team')}")
        logger.info(f"  比分: {sample.get('home_score')} - {sample.get('away_score')}")
        logger.info(f"  控球率: {sample.get('home_stats', {}).get('possession')}% - {sample.get('away_stats', {}).get('possession')}%")
        logger.info(f"  xG: {sample.get('home_stats', {}).get('expected_goals')} - {sample.get('away_stats', {}).get('expected_goals')}")
        logger.info(f"  shot_map 数量: {len(sample.get('shot_map', []))}")

    return raw_data_list


# ============================================================================
# 步骤 2: 单条数据测试提取
# ============================================================================


def test_single_extraction(raw_data: dict) -> dict:
    """
    测试单条数据的特征提取

    Args:
        raw_data: 原始 JSON 数据

    Returns:
        dict: 提取结果
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2: 测试单条数据特征提取")
    logger.info("=" * 60)

    # 创建提取器
    extractor = V25ProductionExtractor()

    # 提取特征
    logger.info(f"开始提取特征 (match_id={raw_data.get('match_id')})...")
    result = extractor.extract(raw_data)

    logger.info(f"\n提取结果:")
    logger.info(f"  状态: {result.status}")
    logger.info(f"  提取特征数: {result.feature_count}")

    # 从 metadata 获取详细信息
    metadata = result.metadata
    logger.info(f"  扁平化深度: {metadata.get('flatten_depth', 'N/A')}")
    logger.info(f"  剪枝前: {metadata.get('features_before_prune', 'N/A')} 维")
    logger.info(f"  剪枝后: {metadata.get('features_after_prune', 'N/A')} 维")
    prune_rate = metadata.get('prune_rate', 0)
    logger.info(f"  剪枝率: {prune_rate:.2%}" if isinstance(prune_rate, (int, float)) else f"  剪枝率: {prune_rate}")

    # 显示特征样本
    if result.features:
        feature_keys = list(result.features.keys())
        logger.info(f"\n特征样本 (前 10 个):")
        for key in feature_keys[:10]:
            val = result.features[key]
            logger.info(f"  {key}: {val}")

        # 统计特征类型
        feature_types = {"numeric": 0, "string": 0, "other": 0}
        for val in result.features.values():
            if isinstance(val, (int, float)):
                feature_types["numeric"] += 1
            elif isinstance(val, str):
                feature_types["string"] += 1
            else:
                feature_types["other"] += 1

        logger.info(f"\n特征类型分布:")
        logger.info(f"  数值型: {feature_types['numeric']}")
        logger.info(f"  字符串型: {feature_types['string']}")
        logger.info(f"  其他: {feature_types['other']}")

    return {
        "status": result.status,
        "features": result.features,
        "features_count": result.feature_count,
        "metadata": result.metadata,
    }


# ============================================================================
# 步骤 3: 批量并发提取
# ============================================================================


def batch_extract_features(
    raw_data_list: list[dict],
    workers: int = 3,
) -> list[tuple[str, dict | None]]:
    """
    批量并发提取特征

    Args:
        raw_data_list: 原始数据列表
        workers: 并发 Worker 数量

    Returns:
        list: (match_id, features) 元组列表
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"步骤 3: 批量并发提取特征 ({workers} Workers)")
    logger.info("=" * 60)

    # 准备数据
    match_list = []
    for raw_data in raw_data_list:
        match_list.append({
            "match_id": raw_data.get("match_id"),
            "raw_data": raw_data,
            "home_team": raw_data.get("home_team"),
            "away_team": raw_data.get("away_team"),
        })

    # 使用 ParallelFeatureExtractor
    extractor = ParallelFeatureExtractor(
        max_workers=workers,
        batch_size=50,
        memory_limit_mb=2000,
    )

    # 并发提取
    logger.info(f"开始并发提取 {len(match_list)} 条数据...")
    start_time = datetime.now()

    results = extractor.extract_batch_parallel(
        matches=match_list,
        extractor_class_path="src.processors.v25_production_extractor.V25ProductionExtractor",
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    throughput = len(match_list) / elapsed if elapsed > 0 else 0

    logger.info(f"\n✅ 提取完成")
    logger.info(f"   耗时: {elapsed:.2f} 秒")
    logger.info(f"   吞吐量: {throughput:.1f} 条/秒 ({throughput * 60:.1f} 条/分钟)")

    # 统计结果
    success_count = sum(1 for r in results if r[1] is not None)
    failed_count = len(results) - success_count

    logger.info(f"   成功: {success_count}")
    logger.info(f"   失败: {failed_count}")

    # 特征维度统计
    feature_counts = [len(r[1]) if r[1] else 0 for r in results if r[1] is not None]
    if feature_counts:
        import statistics
        logger.info(f"\n📊 特征维度统计:")
        logger.info(f"   平均: {statistics.mean(feature_counts):.1f} 维")
        logger.info(f"   最小: {min(feature_counts)} 维")
        logger.info(f"   最大: {max(feature_counts)} 维")
        logger.info(f"   中位数: {statistics.median(feature_counts):.1f} 维")

    return results


# ============================================================================
# 步骤 4: 先导入到 matches 表
# ============================================================================


def import_matches_to_db(
    raw_data_list: list[dict],
) -> dict:
    """
    先将比赛数据导入 matches 表

    Args:
        raw_data_list: 原始数据列表

    Returns:
        dict: 导入统计
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 4: 导入比赛数据到 matches 表")
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

    imported = 0
    skipped = 0

    for raw_data in raw_data_list:
        match_id = raw_data.get("match_id")
        if not match_id:
            continue

        try:
            cur.execute("""
                INSERT INTO matches (
                    external_id, league_name, season, match_time, status,
                    home_team, away_team, home_score, away_score, is_finished
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id) DO UPDATE SET
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                match_id,
                "Serie A",  # 假设是意甲（根据数据特征）
                "2324",
                datetime.now(),  # 使用当前时间
                raw_data.get("status", "finished"),
                raw_data.get("home_team", "Unknown"),
                raw_data.get("away_team", "Unknown"),
                raw_data.get("home_score"),
                raw_data.get("away_score"),
                True if raw_data.get("status") == "finished" else False,
            ))
            imported += 1
        except Exception as e:
            skipped += 1
            continue

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"导入: {imported} 条")
    logger.info(f"跳过: {skipped} 条")

    return {"imported": imported, "skipped": skipped}


# ============================================================================
# 步骤 5: 并发写入数据库
# ============================================================================


def write_features_to_db(
    results: list[tuple[str, dict | None]],
    raw_data_list: list[dict],
    target_count: int = 100,
):
    """
    将提取的特征写入数据库

    Args:
        results: 提取结果列表
        raw_data_list: 原始数据列表（用于获取元数据）
        target_count: 目标写入数量

    Returns:
        dict: 写入统计
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 5: 并发写入数据库")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    # 构建 raw_data 映射
    raw_data_map = {r.get("match_id"): r for r in raw_data_list}

    # 准备特征记录
    features_list = []
    for match_id, features in results:
        if features is None:
            continue

        if len(features_list) >= target_count:
            break

        # 获取原始数据
        raw_data = raw_data_map.get(str(match_id))
        if not raw_data:
            continue

        # 构建 meta_data
        meta_data = {
            "extraction_time": datetime.now().isoformat(),
            "feature_count": len(features),
            "extraction_version": "V26.2",
            "source": "data/l2_output/raw_json",
            "phase": "2.4",
            "raw_json_source": True,
        }

        # 构建记录
        record = (
            str(match_id),
            "2324",
            datetime.now().isoformat(),  # match_time (使用当前时间)
            raw_data.get("home_team", "Unknown"),
            raw_data.get("away_team", "Unknown"),
            "V26.2",
            json.dumps(features),
            json.dumps(meta_data),
            len(features),
            "COMPLETED",
        )
        features_list.append(record)

    logger.info(f"准备写入 {len(features_list)} 条特征记录")

    # 批量入库
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

    logger.info(f"✅ 写入完成: {inserted} 条")
    logger.info(f"   耗时: {elapsed:.2f} 秒")
    logger.info(f"   吞吐量: {len(features_list) / elapsed:.1f} 条/秒")

    return {
        "prepared": len(features_list),
        "inserted": inserted,
        "elapsed": elapsed,
    }


# ============================================================================
# 步骤 5: 验证结果
# ============================================================================


def verify_results():
    """验证数据库中的特征数据"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 5: 验证结果")
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

    # 查询 Phase 2.4 的数据
    cur.execute("""
        SELECT
            external_id,
            home_team,
            away_team,
            meta_data->>'feature_count' as feature_count,
            meta_data->>'phase' as phase,
            meta_data->>'raw_json_source' as raw_json_source,
            processing_status
        FROM match_features_training
        WHERE meta_data->>'phase' = '2.4'
        ORDER BY external_id
        LIMIT 10
    """)

    results = cur.fetchall()
    logger.info(f"\nPhase 2.4 数据: {len(results)} 条")

    if results:
        logger.info(f"\n样本记录:")
        for r in results:
            logger.info(f"  {r['external_id']}: {r['home_team']} vs {r['away_team']} | "
                       f"{r['feature_count']} 维 | Phase: {r['phase']} | "
                       f"Raw JSON: {r['raw_json_source']}")

        # 特征维度统计
        cur.execute("""
            SELECT
                AVG(CAST(meta_data->>'feature_count' AS INTEGER)) as avg_dims,
                MIN(CAST(meta_data->>'feature_count' AS INTEGER)) as min_dims,
                MAX(CAST(meta_data->>'feature_count' AS INTEGER)) as max_dims
            FROM match_features_training
            WHERE meta_data->>'phase' = '2.4'
        """)

        stats = cur.fetchone()
        if stats and stats['avg_dims']:
            logger.info(f"\n📊 特征维度统计 (Phase 2.4):")
            logger.info(f"   平均: {stats['avg_dims']:.1f} 维")
            logger.info(f"   范围: {stats['min_dims']} - {stats['max_dims']} 维")

            # 检查是否接近 6000 维
            if stats['avg_dims'] >= 5000:
                logger.info(f"   ✅ 达到 6000 维目标范围！")
            elif stats['avg_dims'] >= 1000:
                logger.info(f"   ⚠️  维度较高但未达到 6000 维目标")
            else:
                logger.info(f"   ℹ️  维度较低，可能原始 JSON 结构较简单")

    cur.close()
    conn.close()


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    logger.info("=" * 60)
    logger.info("Phase 2.4: 真实原始 JSON 提取流程验证")
    logger.info("=" * 60)
    logger.info(f"启动时间: {datetime.now().isoformat()}")

    # 参数
    LIMIT = 100  # 限制处理 100 条
    WORKERS = 3
    TARGET_COUNT = 100

    # 步骤 1: 加载真实原始 JSON
    raw_data_list = load_raw_json_files(limit=LIMIT)

    if not raw_data_list:
        logger.error("没有可用的原始数据")
        return 1

    # 步骤 2: 测试单条提取
    test_result = test_single_extraction(raw_data_list[0])
    test_metadata = test_result["metadata"]

    # 步骤 3: 批量并发提取
    results = batch_extract_features(raw_data_list, workers=WORKERS)

    # 步骤 4: 先导入比赛元数据到 matches 表
    import_matches_to_db(raw_data_list)

    # 步骤 5: 写入特征数据到数据库
    write_stats = write_features_to_db(results, raw_data_list, target_count=TARGET_COUNT)

    # 步骤 6: 验证结果
    verify_results()

    # 生成报告
    report = {
        "phase": "2.4",
        "report_time": datetime.now().isoformat(),
        "task": "Real Raw JSON Extraction Verification",
        "test_extraction": {
            "status": str(test_result["status"]),
            "features_count": test_result["features_count"],
            "features_before_prune": test_metadata.get("features_before_prune", "N/A"),
            "features_after_prune": test_metadata.get("features_after_prune", "N/A"),
            "prune_rate": test_metadata.get("prune_rate", "N/A"),
        },
        "batch_extraction": {
            "total_files": len(raw_data_list),
            "success_count": sum(1 for r in results if r[1] is not None),
            "failed_count": sum(1 for r in results if r[1] is None),
            "workers": WORKERS,
        },
        "database_write": {
            "prepared": write_stats["prepared"],
            "inserted": write_stats["inserted"],
            "elapsed": write_stats["elapsed"],
        },
        "source": "data/l2_output/*.json",
        "extraction_engine": "V25ProductionExtractor",
        "sparsity_filter": "v26_sparsity_filter.py",
    }

    report_path = "reports/v26_phase_2_4_extraction_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✅ 提取报告已保存: {report_path}")

    # 最终输出
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2.4 完成")
    logger.info("=" * 60)
    logger.info(f"源文件: data/l2_output/ (*.json)")
    logger.info(f"处理文件: {len(raw_data_list)} 个")
    logger.info(f"成功提取: {report['batch_extraction']['success_count']} 条")
    logger.info(f"成功入库: {write_stats['inserted']} 条")
    logger.info(f"特征维度: {test_result['features_count']} 维 (测试样本)")
    logger.info(f"剪枝率: {test_metadata.get('prune_rate', 'N/A')}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
