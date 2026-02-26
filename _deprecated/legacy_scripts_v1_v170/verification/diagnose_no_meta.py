#!/usr/bin/env python3
"""
NO_META 错误诊断脚本
======================

功能:
  1. 从数据库中抽取 5 条 NO_META 错误样本
  2. 分析为什么 _flatten_l2_json 无法解析
  3. 给出修复建议

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
    # 从环境变量读取数据库名称
    import os
    db_name = os.getenv("DB_NAME", settings.database.name)
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=db_name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


def get_no_meta_samples(limit: int = 5) -> list[dict[str, Any]]:
    """
    获取样本进行分析

    由于 raw_match_data 为空，我们从 matches 表中抽样分析

    Args:
        limit: 获取样本数量

    Returns:
        样本列表
    """
    query = """
        SELECT
            m.match_id,
            m.l2_raw_json as raw_data,
            m.data_source,
            m.data_version,
            m.home_team,
            m.away_team
        FROM matches m
        WHERE m.l2_raw_json IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (limit,))
            rows = [dict(row) for row in cursor.fetchall()]

            # 添加兼容字段
            for row in rows:
                row['id'] = row.pop('match_id')
                row['external_id'] = row['id']
                row['collection_status'] = 'TESTING'
                row['error_message'] = 'N/A (抽取的随机样本)'

            return rows


def validate_data_source_structure(raw_data: dict, data_source: str) -> dict[str, Any]:
    """
    V26.5: 数据源感知验证 - 根据 data_source 切换验证策略

    Args:
        raw_data: 原始 JSON 数据
        data_source: 数据源类型 ('FotMob', 'OddsPortal', 或其他)

    Returns:
        验证结果字典
    """
    validation_result = {
        "data_source": data_source,
        "is_valid": False,
        "missing_keys": [],
        "expected_keys": [],
        "validation_strategy": "Generic"
    }

    if not isinstance(raw_data, dict):
        validation_result["issue"] = "NOT_DICT"
        validation_result["details"] = f"原始数据不是字典类型: {type(raw_data).__name__}"
        return validation_result

    if data_source == "FotMob":
        # FotMob 数据源: 验证 header, content, stats 结构
        validation_result["validation_strategy"] = "FotMob"
        validation_result["expected_keys"] = ["header", "content"]

        has_header = "header" in raw_data
        has_content = "content" in raw_data

        if has_header:
            has_teams = "teams" in raw_data.get("header", {})
            if not has_teams:
                validation_result["missing_keys"].append("header.teams")

        if has_content:
            has_stats = "stats" in raw_data.get("content", {})
            if not has_stats:
                validation_result["missing_keys"].append("content.stats")

        validation_result["is_valid"] = has_header and has_content

        if not validation_result["is_valid"]:
            if not has_header:
                validation_result["missing_keys"].append("header")
            if not has_content:
                validation_result["missing_keys"].append("content")

    elif data_source == "OddsPortal":
        # OddsPortal 数据源: 验证 nav, general 结构
        validation_result["validation_strategy"] = "OddsPortal"
        validation_result["expected_keys"] = ["nav", "general"]

        has_nav = "nav" in raw_data
        has_general = "general" in raw_data

        validation_result["is_valid"] = has_nav and has_general

        if not validation_result["is_valid"]:
            if not has_nav:
                validation_result["missing_keys"].append("nav")
            if not has_general:
                validation_result["missing_keys"].append("general")
    else:
        # 通用验证: 检查是否有任何有效数据
        validation_result["validation_strategy"] = "Generic"
        validation_result["expected_keys"] = ["l2_json", "l2", "L2"]
        validation_result["is_valid"] = any(key in raw_data for key in validation_result["expected_keys"])

    return validation_result


def analyze_sample(sample: dict[str, Any], index: int) -> dict[str, Any]:
    """
    分析单个样本 (V26.5 增强版: 集成数据源感知验证)

    Args:
        sample: 样本数据
        index: 样本编号

    Returns:
        分析结果
    """
    print(f"\n{'='*80}")
    print(f"样本 #{index + 1}")
    print(f"{'='*80}")
    print(f"ID: {sample['id']}")
    print(f"External ID: {sample['external_id']}")
    print(f"Data Source: {sample.get('data_source', 'Unknown')}")
    print(f"Collection Status: {sample['collection_status']}")
    print(f"Error Message: {sample['error_message']}")

    raw_data = sample.get("raw_data")
    data_source = sample.get("data_source", "Unknown")

    # 检查原始数据类型
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "data_source": data_source,
                "issue": "INVALID_JSON",
                "details": f"无法解析 JSON: {e}",
                "raw_type": type(sample.get("raw_data")).__name__,
            }

    # V26.5: 首先执行数据源感知验证
    if isinstance(raw_data, dict):
        structure_validation = validate_data_source_structure(raw_data, data_source)

        if not structure_validation["is_valid"]:
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "data_source": data_source,
                "issue": "INVALID_STRUCTURE",
                "details": f"数据源 {data_source} 结构验证失败",
                "validation_strategy": structure_validation["validation_strategy"],
                "expected_keys": structure_validation["expected_keys"],
                "missing_keys": structure_validation["missing_keys"],
            }

        print(f"✅ 数据源 {data_source} 结构验证通过 (策略: {structure_validation['validation_strategy']})")

    # 检查原始数据结构
    if not isinstance(raw_data, dict):
        return {
            "sample_id": sample["id"],
            "external_id": sample["external_id"],
            "data_source": data_source,
            "issue": "NOT_DICT",
            "details": f"原始数据不是字典类型: {type(raw_data).__name__}",
            "raw_value": str(raw_data)[:200],
        }

    # 检查顶层键
    top_keys = list(raw_data.keys())
    print(f"顶层键: {top_keys}")

    # 检查是否有 L2 数据
    has_l2 = "L2" in raw_data or "l2" in raw_data or any("l2" in str(k).lower() for k in top_keys)

    if not has_l2:
        return {
            "sample_id": sample["id"],
            "external_id": sample["external_id"],
            "data_source": data_source,
            "issue": "NO_L2_DATA",
            "details": "原始数据中没有找到 L2 相关键",
            "top_level_keys": top_keys,
        }

    # 尝试使用 V25ProductionExtractor 提取特征
    try:
        extractor = V25ProductionExtractor()
        result = extractor.extract(raw_data)

        # 检查提取状态
        if result.status.value == "SUCCESS":
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "issue": "SUCCESS_NOW",
                "details": "本次测试成功通过，V26.2 可能已修复问题",
                "feature_count": len(result.features),
                "status": result.status.value,
            }
        else:
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "issue": f"EXTRACT_{result.status.value}",
                "details": f"提取状态: {result.status.value}, 特征数: {len(result.features)}",
                "feature_count": len(result.features),
                "errors": result.errors,
                "warnings": result.warnings,
            }

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        if "InsufficientFeaturesError" in error_type or "特征维度不足" in error_msg:
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "issue": "INSUFFICIENT_FEATURES",
                "details": error_msg,
                "error_type": error_type,
            }
        elif "has no attribute" in error_msg or "NoneType" in error_msg:
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "issue": "NULL_VALUE",
                "details": error_msg,
                "error_type": error_type,
            }
        elif "list" in error_msg.lower() or "index" in error_msg.lower():
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "issue": "TYPE_MISMATCH",
                "details": error_msg,
                "error_type": error_type,
            }
        else:
            return {
                "sample_id": sample["id"],
                "external_id": sample["external_id"],
                "issue": "UNKNOWN",
                "details": error_msg,
                "error_type": error_type,
            }


def print_diagnostic_report(results: list[dict[str, Any]]) -> None:
    """打印诊断报告"""
    print(f"\n{'='*80}")
    print("NO_META 诊断报告")
    print(f"{'='*80}")

    # 统计问题类型
    issue_counts = {}
    for result in results:
        issue = result["issue"]
        issue_counts[issue] = issue_counts.get(issue, 0) + 1

    print("\n问题类型分布:")
    for issue, count in issue_counts.items():
        print(f"  {issue}: {count} 条")

    print("\n详细分析:")

    for i, result in enumerate(results):
        print(f"\n样本 #{i + 1}:")
        print(f"  ID: {result['sample_id']}")
        print(f"  External ID: {result['external_id']}")
        print(f"  问题类型: {result['issue']}")
        print(f"  详情: {result['details']}")

        if "top_level_keys" in result:
            print(f"  顶层键: {result['top_level_keys']}")
        if "l2_keys" in result:
            print(f"  L2 键: {result['l2_keys']}")
        if "l2_type" in result:
            print(f"  L2 类型: {result['l2_type']}")


def generate_fix_recommendations(results: list[dict[str, Any]]) -> None:
    """生成修复建议"""
    print(f"\n{'='*80}")
    print("修复建议")
    print(f"{'='*80}")

    issue_types = set(r["issue"] for r in results)

    if "INVALID_JSON" in issue_types:
        print("\n❌ JSON 格式非法:")
        print("   建议: 在采集阶段增加 JSON 验证，丢弃格式错误的数据")
        print("   实现: src/api/collectors/base_extractor.py 中添加 schema 验证")

    if "NO_L2_KEY" in issue_types:
        print("\n⚠️  缺少 L2 键:")
        print("   建议: 检查 FotMob API 返回格式是否变化")
        print("   行动: 1. 运行 test_api.py 查看最新 API 响应")
        print("        2. 更新 src/api/collectors/fotmob_core.py 中的解析逻辑")

    if "NULL_VALUE" in issue_types:
        print("\n🔍 NULL 值问题:")
        print("   建议: 在 _flatten_l2_json 中增加 NULL 值处理")
        print("   实现: 添加 'if value is None: continue' 跳过 NULL 字段")

    if "TYPE_MISMATCH" in issue_types:
        print("\n🔄 类型不匹配:")
        print("   建议: 增加类型转换逻辑")
        print("   实现: 检查是否为 list/dict，递归处理嵌套结构")

    if "UNEXPECTED_SUCCESS" in issue_types:
        print("\n✅ 测试通过:")
        print("   说明: 问题可能已在 V26.2 中修复")
        print("   行动: 运行完整数据回填验证")

    print("\n通用建议:")
    print("  1. 增加 detailed 错误日志，记录原始数据结构")
    print("  2. 添加数据质量监控仪表盘")
    print("  3. 考虑添加数据修复脚本重新处理失败记录")


def main() -> int:
    """主函数"""
    print("="*80)
    print("NO_META 错误诊断工具")
    print("="*80)

    # 获取样本
    print("\n正在获取 NO_META 错误样本...")
    samples = get_no_meta_samples(limit=5)

    if not samples:
        print("✅ 没有找到 NO_META 错误记录")
        return 0

    print(f"✅ 获取到 {len(samples)} 条样本")

    # 分析样本
    results = []
    for i, sample in enumerate(samples):
        result = analyze_sample(sample, i)
        results.append(result)

    # 打印报告
    print_diagnostic_report(results)

    # 生成建议
    generate_fix_recommendations(results)

    # 返回状态
    has_issues = any(r["issue"] not in ["UNEXPECTED_SUCCESS"] for r in results)

    print(f"\n{'='*80}")
    if has_issues:
        print("⚠️  发现需要修复的问题")
        print("="*80)
        return 1
    else:
        print("✅ 所有样本测试通过，问题可能已修复")
        print("="*80)
        return 0


if __name__ == "__main__":
    sys.exit(main())
