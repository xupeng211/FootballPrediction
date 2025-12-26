#!/usr/bin/env python3
"""
V25.1 单场特征提取测试脚本

用于验证 V25.1 特征提取器在生产环境中的工作状态。
"""
import os
import sys
import json
import psycopg2
from pathlib import Path
from datetime import datetime

# 强制设置非 Docker 环境变量（必须在导入 config_unified 之前设置）
os.environ['DOCKER_ENV'] = 'false'

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.processors import ExtractorRegistry
from src.processors.v25_production_extractor import V25ProductionExtractor

# 目标比赛 ID
MATCH_ID = 4813374

def run_extraction():
    """运行 V25.0 特征提取"""
    print("=" * 70)
    print(f"V25.1 特征提取测试 - Match {MATCH_ID}")
    print("=" * 70)

    # 获取配置
    settings = get_settings()
    db = settings.database

    # 修复：使用正确的数据库名称
    correct_db_name = "football_db"

    print(f"\n📡 数据库配置:")
    print(f"  主机: {db.host}")
    print(f"  端口: {db.port}")
    print(f"  数据库: {correct_db_name} (从 {db.name} 修正)")
    print(f"  用户: {db.user}")

    # 创建数据库连接（使用修正后的数据库名）
    print(f"\n🔗 连接数据库...")
    conn = psycopg2.connect(
        host=db.host,
        port=db.port,
        database=correct_db_name,
        user=db.user,
        password=db.password.get_secret_value()
    )
    print(f"✅ 数据库连接成功")

    # 查询比赛数据
    print(f"\n🔍 查询比赛 {MATCH_ID} 数据...")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.id, m.external_id, m.l2_raw_json,
                   m.home_team, m.away_team, m.match_time
            FROM matches m
            WHERE m.id = %s OR m.external_id = %s::text
        """, (MATCH_ID, str(MATCH_ID)))

        match_data = cur.fetchone()

        if not match_data:
            print(f"❌ 未找到比赛 ID {MATCH_ID}")
            return

        db_id, external_id, l2_raw_json, home_team, away_team, match_time = match_data

        print(f"✅ 找到比赛:")
        print(f"  数据库 ID: {db_id}")
        print(f"  外部 ID: {external_id}")
        print(f"  比赛: {home_team} vs {away_team}")
        print(f"  时间: {match_time}")

        if not l2_raw_json:
            print(f"❌ 比赛 {MATCH_ID} 没有 L2 原始数据，请先运行 L1 数据收割")
            return

        # 解析 JSON
        if isinstance(l2_raw_json, str):
            raw_data = json.loads(l2_raw_json)
        else:
            raw_data = l2_raw_json

        print(f"  原始数据大小: {len(json.dumps(raw_data))} bytes")

    # 创建 V25.1 提取器
    print(f"\n🔧 创建 V25.1 特征提取器...")
    extractor = ExtractorRegistry.create("V25.1")
    print(f"✅ 提取器: {extractor.__class__.__name__}")

    # 提取特征
    print(f"\n⚙️  开始特征提取...")
    result = extractor.extract_with_validation(raw_data, skip_validation=False)

    # 显示结果
    print(f"\n" + "=" * 70)
    print(f"提取结果:")
    print(f"=" * 70)
    print(f"  状态: {result.status.value}")
    print(f"  特征数量: {result.feature_count}")
    print(f"  是否成功: {result.is_success}")

    if result.warnings:
        print(f"  警告: {len(result.warnings)} 条")
        for warning in result.warnings[:5]:
            print(f"    - {warning}")

    if result.errors:
        print(f"  错误: {len(result.errors)} 条")
        for error in result.errors[:5]:
            print(f"    - {error}")

    # 显示部分特征
    if result.features:
        print(f"\n📊 特征示例 (前 20 个):")
        feature_keys = list(result.features.keys())
        for i, key in enumerate(feature_keys[:20], 1):
            value = result.features[key]
            if isinstance(value, (int, float)):
                print(f"  {i:2d}. {key:40s} = {value}")
            elif isinstance(value, dict):
                print(f"  {i:2d}. {key:40s} = <dict>")
            else:
                value_str = str(value)[:50]
                print(f"  {i:2d}. {key:40s} = {value_str}")

        print(f"\n  ... (共 {len(result.features)} 个特征)")

    # 数据库持久化
    print(f"\n💾 保存特征到数据库...")
    with conn.cursor() as cur:
        # 检查是否已存在
        cur.execute("""
            SELECT id, extraction_version FROM match_features_training
            WHERE match_id = %s
        """, (db_id,))
        existing = cur.fetchone()

        # 准备元数据
        metadata = {
            "extraction_version": "V25.1",
            "extraction_timestamp": datetime.now().isoformat(),
            "feature_count": result.feature_count,
            "status": result.status.value,
        }
        if result.warnings:
            metadata["warnings"] = result.warnings[:3]

        # 添加比赛基础信息
        features_with_meta = result.features.copy()
        features_with_meta["_match_info"] = {
            "home_team": home_team,
            "away_team": away_team,
            "match_time": str(match_time) if match_time else None,
        }

        if existing:
            # UPDATE
            existing_id, old_version = existing
            cur.execute("""
                UPDATE match_features_training
                SET enriched_features = %s,
                    meta_data = %s,
                    extraction_version = 'V25.1',
                    extraction_timestamp = NOW(),
                    updated_at = NOW(),
                    status = 'ready'
                WHERE match_id = %s
            """, (
                json.dumps(features_with_meta),
                json.dumps(metadata),
                db_id
            ))
            print(f"  ✅ 更新现有记录 (ID: {existing_id}, 版本: {old_version} -> V25.1)")
        else:
            # INSERT
            cur.execute("""
                INSERT INTO match_features_training (
                    match_id, league_id, season_id, home_team, away_team, match_time,
                    enriched_features, meta_data, extraction_version, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'V25.1', 'ready', NOW(), NOW())
            """, (
                db_id,
                None,  # league_id - 从 matches 表获取
                None,  # season_id - 从 matches 表获取
                home_team,
                away_team,
                match_time,
                json.dumps(features_with_meta),
                json.dumps(metadata)
            ))
            print(f"  ✅ 插入新记录 (match_id: {db_id})")

        conn.commit()

        # 验证：读取保存的数据
        cur.execute("""
            SELECT id, extraction_version,
                   jsonb_object_keys(enriched_features) as feature_keys,
                   meta_data->>'feature_count' as meta_count
            FROM match_features_training
            WHERE match_id = %s AND extraction_version = 'V25.1'
        """, (db_id,))

        saved = cur.fetchone()
        if saved:
            saved_id, saved_version, feature_keys, meta_count = saved
            # 计算特征数量（排除 _meta 和 _match_info）
            feature_count = len([k for k in feature_keys if not k.startswith('_')])
            print(f"\n📋 数据库验证:")
            print(f"  记录 ID: {saved_id}")
            print(f"  版本: {saved_version}")
            print(f"  特征数: {feature_count} (元数据: {meta_count})")
        else:
            print(f"\n⚠️  警告: 无法验证保存的数据")

    conn.close()

    print(f"\n" + "=" * 70)
    if result.is_success:
        print(f"✅ V25.1 特征提取成功！")
    else:
        print(f"⚠️  特征提取状态: {result.status.value}")
    print(f"=" * 70)

    return result


if __name__ == "__main__":
    result = run_extraction()
