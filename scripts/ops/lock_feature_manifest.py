#!/usr/bin/env python3
"""
V26.7 特征清单锁定脚本

目的：使用黄金样本锁定 6000+ 维特征字典清单

执行流程：
1. 读取黄金样本 tests/fixtures/premium_match_sample.json
2. 提取所有特征 Keys
3. 更新 config/v26_feature_manifest.json

作者：高级软件质量保证架构师
日期：2026-01-07
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# V29.0 P0 整改: 标准化 .env 加载 (为一致性统一添加)
from dotenv import load_dotenv
load_dotenv(override=True)


def load_gold_sample() -> Dict[str, Any]:
    """加载黄金样本"""
    fixture_path = Path(__file__).parent.parent.parent / "tests/fixtures/premium_match_sample.json"

    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_feature_keys(features: Dict[str, Any]) -> List[str]:
    """
    提取特征 Keys（排除元数据）

    Args:
        features: 特征字典

    Returns:
        特征 Key 列表（排序后）
    """
    # 排除元数据字段
    keys = [k for k in features.keys() if not k.startswith('_')]
    return sorted(keys)


def categorize_features(keys: List[str]) -> Dict[str, List[str]]:
    """
    分类特征

    Args:
        keys: 所有特征 Keys

    Returns:
        分类后的特征字典
    """
    categories = {
        "match_info": [],
        "content_stats": [],
        "content_matchstats": [],
        "content_lineup": [],
        "content_shots": [],
        "content_h2h": [],
        "content_general": [],
        "header": [],
        "other": []
    }

    for key in keys:
        if key.startswith("content_stats"):
            categories["content_stats"].append(key)
        elif key.startswith("content_matchstats"):
            categories["content_matchstats"].append(key)
        elif key.startswith("content_lineup"):
            categories["content_lineup"].append(key)
        elif key.startswith("content_shots"):
            categories["content_shots"].append(key)
        elif key.startswith("content_h2h"):
            categories["content_h2h"].append(key)
        elif key.startswith("content_general"):
            categories["content_general"].append(key)
        elif key.startswith("header"):
            categories["header"].append(key)
        else:
            categories["other"].append(key)

    return categories


def generate_manifest(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成特征清单

    Args:
        features: 黄金样本的特征字典

    Returns:
        特征清单字典
    """
    keys = extract_feature_keys(features)
    categories = categorize_features(keys)

    manifest = {
        "manifest_version": "V26.7-GOLD",
        "manifest_created": "2026-01-07",
        "manifest_description": "V26.7 黄金样本锁定的特征清单（7850 维真实数据）",
        "gold_sample_info": {
            "match_id": features.get("_meta", {}).get("match_id", "unknown"),
            "feature_count": len(keys),
            "extracted_at": features.get("_meta", {}).get("extraction_timestamp", "unknown")
        },
        "feature_schema": {},
        "feature_registry": {
            "total_features": len(keys),
            "features": {key: idx for idx, key in enumerate(keys)}
        },
        "alignment_rules": {
            "strict_mode": True,
            "allow_new_features": False,
            "fill_missing": True,
            "default_value": 0.0,
            "preserve_order": True
        },
        "extraction_config": {
            "max_features": 8000,
            "min_features": 5000,
            "sparsity_threshold": 0.90,
            "flatten_depth": 25,
            "flatten_lists": True,
            "flatten_nested_objects": True
        }
    }

    # 添加分类统计
    for category, cat_keys in categories.items():
        if cat_keys:
            manifest["feature_schema"][category] = {
                "count": len(cat_keys),
                "sample_keys": cat_keys[:5]  # 只显示前 5 个作为示例
            }

    return manifest


def main():
    """主函数"""
    print("="*80)
    print("🔒 V26.7 特征清单锁定")
    print("="*80)

    # Step 1: 加载黄金样本
    print("\n📋 Step 1: 加载黄金样本...")
    gold_sample = load_gold_sample()

    match_info = gold_sample["match_id"]
    home_team = gold_sample["home_team"]
    away_team = gold_sample["away_team"]
    features = gold_sample["extracted_features"]
    feature_count = gold_sample["feature_count"]

    print(f"  比赛: {home_team} vs {away_team}")
    print(f"  Match ID: {match_info}")
    print(f"  特征维度: {feature_count}")

    # Step 2: 提取特征 Keys
    print(f"\n🔑 Step 2: 提取特征 Keys...")
    keys = extract_feature_keys(features)
    print(f"  总特征数: {len(keys)}")
    print(f"  前 10 个: {keys[:10]}")

    # Step 3: 分类特征
    print(f"\n📊 Step 3: 分类特征...")
    categories = categorize_features(keys)
    for category, cat_keys in categories.items():
        if cat_keys:
            print(f"  {category}: {len(cat_keys)} 个特征")

    # Step 4: 生成清单
    print(f"\n📝 Step 4: 生成清单...")
    manifest = generate_manifest(features)

    # Step 5: 保存清单
    print(f"\n💾 Step 5: 保存清单...")
    manifest_path = Path(__file__).parent.parent.parent / "config/v26_feature_manifest.json"

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"  ✅ 清单已保存: {manifest_path}")

    # Step 6: 验证
    print(f"\n" + "="*80)
    print(f"📊 锁定验证")
    print(f"="*80)
    print(f"特征总数: {manifest['feature_registry']['total_features']}")
    print(f"满足 >= 5800 要求: {'✅ 是' if manifest['feature_registry']['total_features'] >= 5800 else '❌ 否'}")
    print(f"严格模式: {'✅ 启用' if manifest['alignment_rules']['strict_mode'] else '❌ 禁用'}")
    print(f"允许新特征: {'❌ 否' if not manifest['alignment_rules']['allow_new_features'] else '✅ 是'}")

    print(f"\n✅ 特征清单锁定完成！")
    print(f"   - {manifest['feature_registry']['total_features']} 维特征已永久锁定")
    print(f"   - 所有批次将使用相同的特征字典")
    print("="*80)


if __name__ == "__main__":
    main()
