#!/usr/bin/env python3
"""
重新生成完整特征数据集
从数据库重新提取包含真实比分的数据
"""

import sys
import os
from pathlib import Path
import pandas as pd
import asyncio

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.features.enhanced_feature_extractor import EnhancedFeatureExtractor, FeatureConfig
from src.database.async_manager import get_async_db_session, AsyncDatabaseManager
from sqlalchemy import text


async def regenerate_complete_dataset():
    """重新生成完整特征数据集"""
    print("🔄 重新生成完整特征数据集")
    print("=" * 50)

    # 初始化特征提取器
    config = FeatureConfig(
        include_metadata=True,
        include_basic_stats=True,
        include_advanced_stats=True,
        include_context=True,
        include_derived_features=True
    )
    extractor = EnhancedFeatureExtractor(config)

    db_manager = AsyncDatabaseManager()
    async for session in get_async_db_session():
        # 获取所有有数据的比赛
        query = """
            SELECT *
            FROM matches
            WHERE home_score IS NOT NULL
            AND away_score IS NOT NULL
            AND home_xg IS NOT NULL
            AND away_xg IS NOT NULL
            AND stats_json IS NOT NULL
            ORDER BY match_date
            LIMIT 1000
        """

        result = await session.execute(text(query))
        matches = result.fetchall()

        print(f"📊 找到 {len(matches)} 场比赛")

        all_features = []
        successful_extractions = 0

        for i, match_row in enumerate(matches, 1):
            match_data = dict(match_row._mapping)

            # 执行特征提取
            try:
                features = extractor.extract_features(match_data)
                all_features.append(features)
                successful_extractions += 1

                if i % 50 == 0:
                    print(f"   ✅ 已处理 {i} 场比赛")

            except Exception as e:
                print(f"   ❌ 比赛ID {match_data['id']} 提取失败: {e}")
                continue

        print(f"\n📈 特征提取完成:")
        print(f"   成功提取: {successful_extractions}/{len(matches)} 场比赛")

        if all_features:
            # 创建DataFrame
            df = pd.DataFrame(all_features)

            # 添加比赛结果
            def calculate_result(row):
                if row['home_score'] > row['away_score']:
                    return 'Home'
                elif row['home_score'] < row['away_score']:
                    return 'Away'
                else:
                    return 'Draw'

            df['match_result'] = df.apply(calculate_result, axis=1)
            df['result_numeric'] = df.apply(lambda x: {'Home': 1, 'Draw': 0, 'Away': -1}[x['match_result']], axis=1)

            print(f"\n🎯 比赛结果分布:")
            print(f"   {df['match_result'].value_counts().to_dict()}")

            print(f"\n📊 数据集信息:")
            print(f"   形状: {df.shape}")
            print(f"   特征数: {len(df.columns)}")

            # 保存数据集
            output_path = "data/processed/complete_features.csv"
            df.to_csv(output_path, index=False)

            file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
            print(f"\n💾 数据集已保存:")
            print(f"   文件: {output_path}")
            print(f"   大小: {file_size:.2f} MB")

            return df
        else:
            print("❌ 没有成功提取的特征数据")
            return None


async def main():
    """主函数"""
    await regenerate_complete_dataset()


if __name__ == "__main__":
    asyncio.run(main())