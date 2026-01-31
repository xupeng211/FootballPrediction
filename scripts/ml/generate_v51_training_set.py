#!/usr/bin/env python3
"""
V51.0 黄金数据集生成脚本
==========================

用途: 生成基于 V51.0 特征提取引擎的完整训练数据集

目标:
    - 提取所有 finished 比赛的 V51 特征 (约 9000 场)
    - 生成 model_zoo/v51_features_all.csv
    - 作为 V51.0 模型训练的黄金数据集

Author: ML Engineering Team
Version: V51.0
Date: 2025-12-31
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.processors.v51_feature_refiner import extract_features_from_db
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 70)
    print("V51.0 黄金数据集生成")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 提取所有比赛特征
    print("\n[1/3] 提取 V51 特征...")
    print("  目标: 所有 finished 比赛 (约 9000 场)")
    print("  特征维度: 642")
    print("  进度:")

    df, stats = extract_features_from_db(
        limit=None,  # 提取所有
        max_features=500,
        enable_whitelist=True,
        show_progress=True,
    )

    print(f"\n  ✓ 提取完成: {len(df)} 场比赛")
    print(f"  ✓ 特征维度: {len(df.columns)}")

    # 2. 移除元数据列 (只保留数值特征)
    print("\n[2/3] 清洗数据...")
    metadata_cols = ["match_id"]
    metadata_cols_found = [col for col in metadata_cols if col in df.columns]

    if metadata_cols_found:
        print(f"  移除元数据列: {metadata_cols_found}")
        df_features = df.drop(columns=metadata_cols_found)
    else:
        df_features = df.copy()

    # 检查是否有 league_name 等其他元数据
    for col in df_features.columns:
        if df_features[col].dtype == "object":
            print(f"  ⚠️  发现非数值列: {col} (dtype: {df_features[col].dtype})")
            # 转换或删除
            try:
                df_features[col] = pd.to_numeric(df_features[col], errors="coerce")
                print(f"     → 尝试转换为数值")
            except:
                df_features = df_features.drop(columns=[col])
                print(f"     → 已删除")

    print(f"  ✓ 清洗后维度: {len(df_features.columns)}")

    # 3. 保存数据集
    print("\n[3/3] 保存数据集...")
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "v51_features_all.csv"
    df.to_csv(output_path, index=False)
    print(f"  ✓ 完整数据集 (含元数据): {output_path}")

    output_path_features = output_dir / "v51_features_all_numeric.csv"
    df_features.to_csv(output_path_features, index=False)
    print(f"  ✓ 特征数据集 (仅数值): {output_path_features}")

    # 4. 输出统计摘要
    print("\n" + "=" * 70)
    print("数据集摘要")
    print("=" * 70)
    print(f"样本数量: {len(df)} 场")
    print(f"特征维度: {len(df.columns)} (完整) / {len(df_features.columns)} (数值)")
    print(f"数据范围: {df.get('match_id', 'N/A')}")

    # 按年份统计
    if "match_id" in df.columns:
        print("\n样本分布:")
        print(f"  总数: {len(df)} 场")

    print("\n" + str(stats))

    print("\n" + "=" * 70)
    print("✅ V51.0 黄金数据集生成完成！")
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
