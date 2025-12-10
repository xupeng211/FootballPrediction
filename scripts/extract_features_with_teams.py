#!/usr/bin/env python3
"""
重新提取包含team_name的完整特征数据集
为滚动特征工程准备基础数据
"""

import sys
import os
from pathlib import Path
import pandas as pd
import asyncio
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.features.enhanced_feature_extractor import EnhancedFeatureExtractor, FeatureConfig
from src.database.async_manager import AsyncDatabaseManager
from sqlalchemy import text


async def extract_features_with_teams():
    """提取包含team_name的完整特征数据集"""
    print("🔄 提取包含team_name的完整特征数据集")
    print("=" * 60)

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

    # 手动创建数据库连接
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 获取所有有数据的比赛，包括team_name
            query = """
                SELECT
                    m.*,
                    ht.name as home_team_name,
                    at.name as away_team_name
                FROM matches m
                LEFT JOIN teams ht ON m.home_team_id = ht.id
                LEFT JOIN teams at ON m.away_team_id = at.id
                WHERE m.home_score IS NOT NULL
                AND m.away_score IS NOT NULL
                AND m.home_xg IS NOT NULL
                AND m.away_xg IS NOT NULL
                AND m.stats_json IS NOT NULL
                ORDER BY m.match_date
                LIMIT 2000
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

                    # 添加team_name到特征中
                    features['home_team_name'] = match_data['home_team_name']
                    features['away_team_name'] = match_data['away_team_name']

                    # 添加match_date
                    features['match_date'] = match_data['match_date']

                    all_features.append(features)
                    successful_extractions += 1

                    if i % 100 == 0:
                        print(f"   ✅ 已处理 {i}/{len(matches)} 场比赛")

                except Exception as e:
                    print(f"   ❌ 比赛ID {match_data['id']} 提取失败: {e}")
                    continue

            print(f"\n📈 特征提取完成:")
            print(f"   成功提取: {successful_extractions}/{len(matches)} 场比赛")

            if all_features:
                # 创建DataFrame
                df = pd.DataFrame(all_features)

                print(f"\n📊 数据集信息:")
                print(f"   形状: {df.shape}")
                print(f"   特征数: {len(df.columns)}")

                # 检查team_name列
                if 'home_team_name' in df.columns and 'away_team_name' in df.columns:
                    print(f"   ✅ 包含team_name列")
                    print(f"   🏠 主队数量: {df['home_team_name'].nunique()}")
                    print(f"   🏃 客队数量: {df['away_team_name'].nunique()}")
                else:
                    print(f"   ❌ 缺少team_name列")

                # 检查比赛结果分布
                if 'result' in df.columns:
                    print(f"\n🎯 比赛结果分布:")
                    print(f"   {df['result'].value_counts().to_dict()}")

                # 检查日期范围
                if 'match_date' in df.columns:
                    df['match_date'] = pd.to_datetime(df['match_date'])
                    print(f"\n📅 日期范围: {df['match_date'].min()} 到 {df['match_date'].max()}")

                # 保存数据集
                output_path = "data/processed/features_with_teams.csv"
                df.to_csv(output_path, index=False)

                file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
                print(f"\n💾 数据集已保存:")
                print(f"   文件: {output_path}")
                print(f"   大小: {file_size:.2f} MB")

                return df
            else:
                print("❌ 没有成功提取的特征数据")
                return None

    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
        return None
    finally:
        await engine.dispose()


async def main():
    """主函数"""
    await extract_features_with_teams()


if __name__ == "__main__":
    asyncio.run(main())