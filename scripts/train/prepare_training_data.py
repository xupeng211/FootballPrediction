#!/usr/bin/env python3
"""
训练数据准备脚本 (Prepare Training Data)

从数据库读取matches表，构建特征集和标签，为模型训练做准备。

特征 (X):
- home_xg, away_xg (期望进球数)
- home_possession, away_possession (控球率)
- home_shots, away_shots (射门数)
- home_shots_on_target, away_shots_on_target (射正数)

标签 (y):
- 0: Home Win, 1: Draw, 2: Away Win

作者: ML Engineer (P2-5)
创建时间: 2025-12-06
版本: 1.0.0
"""

import logging
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.async_manager import get_db_session
from src.database.models import Match
from sqlalchemy import select, and_, or_

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"/tmp/prepare_training_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)


class TrainingDataPreparer:
    """训练数据准备器"""

    def __init__(self):
        self.required_features = [
            'home_xg', 'away_xg',
            'home_possession', 'away_possession',
            'home_shots', 'away_shots',
            'home_shots_on_target', 'away_shots_on_target'
        ]

    async def load_matches_from_database(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        从数据库加载比赛数据

        Args:
            limit: 限制加载的记录数，None表示加载所有

        Returns:
            包含比赛数据的DataFrame
        """
        logger.info("📊 从数据库加载比赛数据...")

        async with get_db_session() as session:
            # 构建查询条件
            conditions = [
                Match.status.in_(["finished", "completed"]),
                Match.home_score.isnot(None),
                Match.away_score.isnot(None)
            ]

            query = select(Match).where(and_(*conditions)).order_by(Match.match_date.desc())

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            matches = result.scalars().all()

            logger.info(f"   加载了 {len(matches)} 场比赛数据")

            # 转换为DataFrame
            matches_data = []
            for match in matches:
                match_dict = {
                    'id': match.id,
                    'home_team_id': match.home_team_id,
                    'away_team_id': match.away_team_id,
                    'home_score': match.home_score,
                    'away_score': match.away_score,
                    'match_date': match.match_date,
                    'status': match.status,
                    'league_id': match.league_id,
                    'season': match.season,
                }

                # 添加新增的统计字段（使用getattr处理可能不存在的字段）
                for feature in self.required_features:
                    value = getattr(match, feature, None)
                    match_dict[feature] = value

                matches_data.append(match_dict)

            df = pd.DataFrame(matches_data)
            logger.info(f"   DataFrame形状: {df.shape}")

            return df

    def prepare_features_and_labels(self, df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
        """
        准备特征和标签

        Args:
            df: 原始比赛数据DataFrame

        Returns:
            (特征DataFrame, 标签数组)
        """
        logger.info("🔧 准备特征和标签...")

        # 数据质量检查
        original_count = len(df)
        df = self._clean_data(df)
        logger.info(f"   数据清洗后: {len(df)} 条记录 (原始: {original_count})")

        if len(df) == 0:
            raise ValueError("没有可用的训练数据")

        # 构建特征矩阵 X
        X = df[self.required_features].copy()

        # 特征工程
        X = self._engineer_features(X)

        logger.info(f"   特征矩阵形状: {X.shape}")
        logger.info(f"   特征列: {list(X.columns)}")

        # 构建标签 y
        y = self._create_labels(df)

        logger.info(f"   标签分布: {np.bincount(y)} (Home:0, Draw:1, Away:2)")

        # 特征统计
        self._log_feature_stats(X)

        return X, y

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        logger.info("   开始数据清洗...")

        original_count = len(df)

        # 移除关键字段为空的记录
        required_fields = ['home_score', 'away_score'] + self.required_features
        for field in required_fields:
            if field in df.columns:
                null_count = df[field].isnull().sum()
                if null_count > 0:
                    logger.warning(f"   字段 {field} 有 {null_count} 个空值")

        # 删除所有关键字段都为空的记录
        df_cleaned = df.dropna(subset=required_fields, how='any')

        # 删除重复记录
        df_cleaned = df_cleaned.drop_duplicates()

        logger.info("   数据清洗完成:")
        logger.info(f"     删除空值记录: {original_count - len(df_cleaned)} 条")
        logger.info(f"     删除重复记录: {len(df) - len(df_cleaned)} 条")
        logger.info(f"     最终记录数: {len(df_cleaned)} 条")

        return df_cleaned

    def _engineer_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """特征工程"""
        logger.info("   执行特征工程...")

        X_engineered = X.copy()

        # 1. 填充缺失值（使用中位数）
        for col in X_engineered.columns:
            if X_engineered[col].isnull().any():
                median_val = X_engineered[col].median()
                X_engineered[col] = X_engineered[col].fillna(median_val)
                logger.info(f"     填充 {col} 缺失值: 中位数={median_val}")

        # 2. 创建衍生特征
        if all(col in X_engineered.columns for col in ['home_xg', 'away_xg']):
            # xG差值
            X_engineered['xg_difference'] = X_engineered['home_xg'] - X_engineered['away_xg']

            # xG比率
            X_engineered['xg_ratio'] = X_engineered['home_xg'] / (X_engineered['away_xg'] + 0.001)  # 避免0除

        if all(col in X_engineered.columns for col in ['home_possession', 'away_possession']):
            # 控球率差值
            X_engineered['possession_difference'] = X_engineered['home_possession'] - X_engineered['away_possession']

        if all(col in X_engineered.columns for col in ['home_shots', 'away_shots']):
            # 射门差值
            X_engineered['shots_difference'] = X_engineered['home_shots'] - X_engineered['away_shots']

            # 射门效率
            X_engineered['home_shot_efficiency'] = X_engineered['home_shots_on_target'] / (X_engineered['home_shots'] + 0.001)
            X_engineered['away_shot_efficiency'] = X_engineered['away_shots_on_target'] / (X_engineered['away_shots'] + 0.001)

        logger.info(f"     衍生特征后的形状: {X_engineered.shape}")

        return X_engineered

    def _create_labels(self, df: pd.DataFrame) -> np.ndarray:
        """创建标签"""
        def determine_result(row):
            home_score = row['home_score']
            away_score = row['away_score']

            if home_score > away_score:
                return 0  # Home Win
            elif away_score > home_score:
                return 2  # Away Win
            else:
                return 1  # Draw

        y = df.apply(determine_result, axis=1).values
        return y

    def _log_feature_stats(self, X: pd.DataFrame):
        """记录特征统计信息"""
        logger.info("   特征统计信息:")

        for col in X.columns:
            if X[col].dtype in ['float64', 'int64']:
                stats = {
                    'count': X[col].count(),
                    'mean': X[col].mean(),
                    'std': X[col].std(),
                    'min': X[col].min(),
                    'max': X[col].max(),
                    'null_count': X[col].isnull().sum()
                }

                logger.info(f"     {col:<25}: "
                           f"count={stats['count']:>5}, "
                           f"mean={stats['mean']:>7.3f}, "
                           f"std={stats['std']:>7.3f}, "
                           f"min={stats['min']:>7.3f}, "
                           f"max={stats['max']:>7.3f}")

    async def save_training_data(self, X: pd.DataFrame, y: np.ndarray,
                               output_path: str = "data/training_set_v1.parquet") -> None:
        """
        保存训练数据

        Args:
            X: 特征DataFrame
            y: 标签数组
            output_path: 输出文件路径
        """
        logger.info(f"💾 保存训练数据到: {output_path}")

        # 创建输出目录
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存特征和标签
        X.to_parquet(output_path, index=False)

        # 保存标签
        y_path = output_path.replace('.parquet', '_labels.npz')
        np.save(y_path, y)

        logger.info(f"   特征数据: {X.shape}, 标签数据: {y.shape}")
        logger.info(f"   特征文件: {output_path}")
        logger.info(f"   标签文件: {y_path}")

    async def prepare_training_data(self, limit: Optional[int] = None,
                                   output_path: str = "data/training_set_v1.parquet") -> tuple[pd.DataFrame, np.ndarray]:
        """
        执行完整的训练数据准备流程

        Args:
            limit: 限制记录数
            output_path: 输出文件路径

        Returns:
            (特征DataFrame, 标签数组)
        """
        logger.info("🚀 开始训练数据准备流程")

        # 1. 从数据库加载数据
        df = await self.load_matches_from_database(limit)

        # 2. 准备特征和标签
        X, y = self.prepare_features_and_labels(df)

        # 3. 保存训练数据
        await self.save_training_data(X, y, output_path)

        logger.info("✅ 训练数据准备完成")
        return X, y


async def main():
    """主函数"""
    print("🤖 训练数据准备开始")
    print("=" * 50)

    preparer = TrainingDataPreparer()

    try:
        # 准备训练数据
        # 可以设置limit参数来限制数据量，用于快速测试
        X, y = await preparer.prepare_training_data(
            limit=None,  # 设置为None使用所有可用数据
            output_path="data/training_set_v1.parquet"
        )

        print("\n📊 数据准备完成:")
        print(f"   特征矩阵: {X.shape}")
        print(f"   标签向量: {y.shape}")
        print(f"   标签分布: Home(0): {np.sum(y == 0)}, Draw(1): {np.sum(y == 1)}, Away(2): {np.sum(y == 2)}")

        print("\n💾 数据已保存到: data/training_set_v1.parquet")
        print("✅ 训练数据准备完成!")

        return 0

    except Exception as e:
        logger.error(f"❌ 训练数据准备失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
