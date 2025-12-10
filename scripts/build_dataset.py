#!/usr/bin/env python3
"""
数据集构建脚本 - Dataset Builder (ETL Pipeline)
Phase 2: 构建机器学习的黄金数据集

MLOps最佳实践:
1. Extract: 从数据库提取完整比赛数据
2. Transform: 批量特征提取和工程
3. Load: 保存为版本化的静态数据集

作者: Data Engineer
创建时间: 2025-12-10
版本: 1.0.0 - Golden Dataset v1
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.features.enhanced_feature_extractor import EnhancedFeatureExtractor, FeatureConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetBuilder:
    """数据集构建器 - ETL流水线"""

    def __init__(self):
        self.feature_extractor = EnhancedFeatureExtractor(
            FeatureConfig(
                include_metadata=True,
                include_basic_stats=True,
                include_advanced_stats=True,
                include_context=True,
                include_derived_features=True
            )
        )

        # 处理统计
        self.stats = {
            'total_matches': 0,
            'processed_matches': 0,
            'failed_matches': 0,
            'skipped_matches': 0,
            'start_time': None,
            'end_time': None,
            'error_details': []
        }

    async def extract(self) -> List[Dict[str, Any]]:
        """
        Extract: 从数据库提取完整的比赛数据

        Returns:
            比赛数据列表
        """
        logger.info("🔄 Step 1: Extract - 开始从数据库提取比赛数据")

        # 数据库连接配置
        database_url = os.getenv("ASYNC_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction")

        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with async_session() as session:
                # 查询所有完整比赛
                query = """
                    SELECT COUNT(*) as total
                    FROM matches
                    WHERE status = 'FT'
                    AND stats_json IS NOT NULL
                    AND home_xg IS NOT NULL
                    AND away_xg IS NOT NULL
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                """

                result = await session.execute(text(query))
                total_matches = result.scalar()
                self.stats['total_matches'] = total_matches

                logger.info(f"📊 找到 {total_matches:,} 场完整比赛")

                if total_matches == 0:
                    logger.warning("⚠️ 未找到符合条件的比赛数据")
                    return []

                # 分批提取数据（避免内存问题）
                batch_size = 500
                all_matches = []

                for offset in range(0, total_matches, batch_size):
                    batch_query = """
                        SELECT *
                        FROM matches
                        WHERE status = 'FT'
                        AND stats_json IS NOT NULL
                        AND home_xg IS NOT NULL
                        AND away_xg IS NOT NULL
                        AND home_score IS NOT NULL
                        AND away_score IS NOT NULL
                        ORDER BY match_date DESC
                        LIMIT :batch_size OFFSET :offset
                    """

                    result = await session.execute(
                        text(batch_query),
                        {"batch_size": batch_size, "offset": offset}
                    )
                    batch_matches = result.fetchall()

                    # 转换为字典列表
                    batch_dicts = [dict(row._mapping) for row in batch_matches]
                    all_matches.extend(batch_dicts)

                    logger.info(f"📦 提取批次 {offset//batch_size + 1}: {len(batch_dicts)} 场比赛")

                logger.info(f"✅ Extract 完成: 总共提取 {len(all_matches):,} 场比赛")
                return all_matches

        except Exception as e:
            logger.error(f"❌ Extract 失败: {e}")
            raise
        finally:
            await engine.dispose()

    async def transform(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform: 批量特征提取

        Args:
            matches: 原始比赛数据列表

        Returns:
            特征数据列表
        """
        logger.info("🔄 Step 2: Transform - 开始批量特征提取")

        features_list = []

        for i, match_data in enumerate(matches, 1):
            try:
                # 特征提取
                features = self.feature_extractor.extract_features(match_data)

                if features:
                    # 添加处理元数据
                    features['_processing_timestamp'] = datetime.now().isoformat()
                    features['_source_match_id'] = match_data.get('id')

                    features_list.append(features)
                    self.stats['processed_matches'] += 1

                    # 进度报告
                    if i % 100 == 0 or i == len(matches):
                        progress = (i / len(matches)) * 100
                        logger.info(f"⚡ 处理进度: {i}/{len(matches)} ({progress:.1f}%)")
                else:
                    self.stats['failed_matches'] += 1
                    logger.warning(f"⚠️ 特征提取失败: Match ID {match_data.get('id')}")

            except Exception as e:
                self.stats['failed_matches'] += 1
                error_detail = {
                    'match_id': match_data.get('id'),
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.stats['error_details'].append(error_detail)
                logger.warning(f"⚠️ 处理失败: Match ID {match_data.get('id')} - {e}")

        logger.info(f"✅ Transform 完成: 成功 {self.stats['processed_matches']:,}, 失败 {self.stats['failed_matches']:,}")
        return features_list

    def load(self, features_list: List[Dict[str, Any]], output_path: str) -> pd.DataFrame:
        """
        Load: 保存特征数据为CSV文件

        Args:
            features_list: 特征数据列表
            output_path: 输出文件路径

        Returns:
            pandas DataFrame
        """
        logger.info("🔄 Step 3: Load - 开始保存数据集")

        try:
            # 转换为DataFrame
            df = pd.DataFrame(features_list)

            # 确保输出目录存在
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # 保存为CSV
            df.to_csv(output_path, index=False, encoding='utf-8')

            # 文件大小信息
            file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB

            logger.info(f"✅ Load 完成:")
            logger.info(f"   📁 输出文件: {output_path}")
            logger.info(f"   📊 数据形状: {df.shape}")
            logger.info(f"   💾 文件大小: {file_size:.2f} MB")
            logger.info(f"   📋 特征数量: {len(df.columns)}")

            return df

        except Exception as e:
            logger.error(f"❌ Load 失败: {e}")
            raise

    def generate_report(self, df: pd.DataFrame, output_path: str):
        """生成数据集报告"""
        logger.info("📋 生成数据集质量报告")

        print("\n" + "="*80)
        print("🏆 FOOTBALL PREDICTION GOLDEN DATASET v1")
        print("="*80)

        # 处理统计
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        print(f"📊 处理统计:")
        print(f"   总比赛数:     {self.stats['total_matches']:,}")
        print(f"   成功处理:     {self.stats['processed_matches']:,}")
        print(f"   处理失败:     {self.stats['failed_matches']:,}")
        print(f"   成功率:       {(self.stats['processed_matches']/self.stats['total_matches']*100):.1f}%")
        print(f"   处理耗时:     {duration:.1f} 秒")
        print(f"   处理速度:     {self.stats['processed_matches']/duration:.1f} 场/秒")

        print(f"\n📋 数据集信息:")
        print(f"   输出文件:     {output_path}")
        print(f"   数据形状:     {df.shape}")
        print(f"   特征数量:     {len(df.columns)}")
        print(f"   内存占用:     {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

        print(f"\n🔍 数据质量:")

        # 按类别统计特征
        feature_categories = {
            '元数据特征': ['match_id', 'year', 'month', 'day_of_week', 'day_of_year', 'is_weekend'],
            '目标变量': ['home_score', 'away_score', 'result', 'result_numeric', 'has_winner', 'goal_difference', 'total_goals', 'over_2_5_goals'],
            '高级统计': ['home_xg', 'away_xg', 'xg_difference', 'total_xg', 'home_xg_vs_actual', 'away_xg_vs_actual', 'total_xg_vs_actual'],
            '基础统计': [col for col in df.columns if any(keyword in col for keyword in ['possession', 'shots', 'corners', 'fouls', 'cards', 'passes', 'tackles'])],
            '上下文特征': [col for col in df.columns if any(keyword in col for keyword in ['referee', 'stadium', 'weather', 'odds'])],
            '衍生特征': [col for col in df.columns if any(keyword in col for keyword in ['accuracy', 'overperformance', 'advantage', 'difference', 'ratio'])]
        }

        for category, features in feature_categories.items():
            existing_features = [f for f in features if f in df.columns]
            if existing_features:
                non_null_count = df[existing_features].notna().any(axis=1).sum()
                coverage = (non_null_count / len(df)) * 100
                print(f"   {category:12}: {len(existing_features):2} 个特征, 覆盖率: {coverage:5.1f}%")

        # 数据完整性统计
        print(f"\n📈 数据完整性:")
        null_counts = df.isnull().sum()
        important_features = ['home_xg', 'away_xg', 'home_score', 'away_score', 'result', 'home_possession', 'away_possession']

        for feature in important_features:
            if feature in df.columns:
                null_count = null_counts[feature]
                non_null_count = len(df) - null_count
                coverage = (non_null_count / len(df)) * 100
                print(f"   {feature:20}: {non_null_count:6,}/{len(df):6,} ({coverage:5.1f}%)")

        if self.stats['error_details']:
            print(f"\n⚠️ 错误详情 (前5个):")
            for error in self.stats['error_details'][:5]:
                print(f"   Match {error['match_id']}: {error['error']}")

        print(f"\n🎯 数据集就绪用途:")
        print(f"   • 机器学习模型训练")
        print(f"   • 特征重要性分析")
        print(f"   • 模型性能基准测试")
        print(f"   • 实时预测服务开发")

        print("="*80)

    async def build_dataset(self, output_path: str = "data/processed/features_v1.csv"):
        """
        完整的ETL流水线

        Args:
            output_path: 输出文件路径
        """
        logger.info("🚀 开始构建 Golden Dataset v1")
        self.stats['start_time'] = datetime.now()

        try:
            # Step 1: Extract
            matches = await self.extract()

            if not matches:
                logger.error("❌ 没有数据可处理")
                return None

            # Step 2: Transform
            features_list = await self.transform(matches)

            if not features_list:
                logger.error("❌ 没有成功提取的特征数据")
                return None

            # Step 3: Load
            df = self.load(features_list, output_path)

            self.stats['end_time'] = datetime.now()

            # 生成报告
            self.generate_report(df, output_path)

            logger.info("🎉 Golden Dataset v1 构建完成!")
            return df

        except Exception as e:
            logger.error(f"❌ 数据集构建失败: {e}")
            raise


async def main():
    """主函数"""
    # 构建数据集
    builder = DatasetBuilder()

    try:
        df = await builder.build_dataset()

        if df is not None:
            print(f"\n✅ 数据集构建成功!")
            print(f"📊 数据预览:")
            print(df.head())
            print(f"\n📋 数据信息:")
            df.info()

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断操作")
    except Exception as e:
        logger.error(f"❌ 脚本执行失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())