#!/usr/bin/env python3
"""
V17.0 生产流水线
整合 L1 采集 -> L2 解析 -> L3 滚动特征 -> 模型训练 的完整流程
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class V17ProductionPipeline:
    """
    V17.0 生产流水线

    完整流程:
    - Phase 1 (L1): 比赛清单采集
    - Phase 2 (L2): FotMob API 数据采集和解析
    - Phase 3 (L3): 滚动特征计算
    - Phase 4: 模型训练和评估
    """

    # V17.0 滚动特征列表（16维 - 无数据泄露）
    ROLLING_FEATURES = [
        # 主队滚动特征 (8个)
        'home_rolling_xg',
        'home_rolling_xg_std',
        'home_rolling_shots_on_target',
        'home_rolling_shots_on_target_std',
        'home_rolling_possession',
        'home_rolling_possession_std',
        'home_rolling_team_rating',
        'home_rolling_team_rating_std',
        # 客队滚动特征 (8个)
        'away_rolling_xg',
        'away_rolling_xg_std',
        'away_rolling_shots_on_target',
        'away_rolling_shots_on_target_std',
        'away_rolling_possession',
        'away_rolling_possession_std',
        'away_rolling_team_rating',
        'away_rolling_team_rating_std',
    ]

    # 核心指标列表
    CORE_METRICS = ['xg', 'shots_on_target', 'possession', 'team_rating']

    def __init__(self, db_config: Optional[Dict] = None):
        """
        初始化流水线

        Args:
            db_config: 数据库配置（可选，默认使用 Docker 本地配置）
        """
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'football_db',
            'user': 'football_user',
            'password': 'football_pass'
        }

        # 标签映射
        self.label_mapping = {'A': 0, 'D': 1, 'H': 2}
        self.reverse_mapping = {0: 'A', 1: 'D', 2: 'H'}

    def get_connection(self):
        """获取数据库连接"""
        import psycopg2
        return psycopg2.connect(**self.db_config)

    # ========================================================================
    # Phase 3: L3 滚动特征计算
    # ========================================================================

    def extract_match_data(self, season: str = '23/24') -> pd.DataFrame:
        """
        从数据库提取比赛数据，按时间排序

        Args:
            season: 赛季标识

        Returns:
            按时间排序的比赛数据 DataFrame
        """
        from psycopg2.extras import RealDictCursor

        logger.info("=" * 60)
        logger.info("Phase 3: L3 滚动特征计算 - 数据提取")
        logger.info("=" * 60)

        conn = None
        try:
            conn = self.get_connection()

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        external_id,
                        home_team,
                        away_team,
                        match_time,
                        home_score,
                        away_score,
                        actual_result,
                        player_stats
                    FROM matches
                    WHERE season = %s
                        AND player_stats IS NOT NULL
                    ORDER BY match_time ASC
                """, (season,))

                rows = cur.fetchall()
                matches = [dict(row) for row in rows]

                logger.info(f"📊 从数据库提取 {len(matches)} 场比赛")

                df = pd.DataFrame(matches)
                df['parsed_stats'] = df['player_stats'].apply(self._parse_stats)

                logger.info(f"✅ 数据时间范围: {df['match_time'].min()} 至 {df['match_time'].max()}")

                return df

        finally:
            if conn:
                conn.close()

    def _parse_stats(self, stats_str: str) -> dict:
        """解析 player_stats JSON"""
        import json
        try:
            if isinstance(stats_str, str):
                return json.loads(stats_str)
            return stats_str
        except:
            return {}

    def build_team_history(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        构建每支球队的比赛历史

        Args:
            df: 比赛数据 DataFrame

        Returns:
            球队历史数据字典
        """
        logger.info("📊 构建球队历史数据")

        team_history = {}
        all_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())

        logger.info(f"📊 发现 {len(all_teams)} 支球队")

        for team in all_teams:
            home_matches = df[df['home_team'] == team][['external_id', 'match_time', 'parsed_stats']].copy()
            away_matches = df[df['away_team'] == team][['external_id', 'match_time', 'parsed_stats']].copy()

            home_matches['is_home'] = True
            away_matches['is_home'] = False

            home_matches = home_matches.rename(columns={'parsed_stats': 'stats'})
            away_matches = away_matches.rename(columns={'parsed_stats': 'stats'})

            team_matches = pd.concat([home_matches, away_matches], ignore_index=True)
            team_matches = team_matches.sort_values('match_time').reset_index(drop=True)

            team_history[team] = team_matches

        logger.info(f"✅ 构建了 {len(team_history)} 支球队的历史数据")
        return team_history

    def calculate_rolling_features(
        self,
        team_history: Dict[str, pd.DataFrame],
        match_id: str,
        home_team: str,
        away_team: str,
        match_time: str,
        window: int = 10
    ) -> Dict[str, float]:
        """
        计算指定比赛的滚动特征

        Args:
            team_history: 球队历史数据
            match_id: 比赛 ID
            home_team: 主队
            away_team: 客队
            match_time: 比赛时间
            window: 滚动窗口大小

        Returns:
            滚动特征字典
        """
        # 获取主队在当前比赛之前的比赛
        home_hist = team_history[home_team]
        home_before = home_hist[home_hist['match_time'] < match_time].tail(window)

        # 获取客队在当前比赛之前的比赛
        away_hist = team_history[away_team]
        away_before = away_hist[away_hist['match_time'] < match_time].tail(window)

        features = {
            'match_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            'match_time': match_time,
            'home_matches_count': len(home_before),
            'away_matches_count': len(away_before)
        }

        # 主队滚动均值
        for metric in self.CORE_METRICS:
            home_values = []
            for _, row in home_before.iterrows():
                stats = row.get('stats', {})
                if row['is_home']:
                    val = stats.get(f'home_{metric}')
                else:
                    val = stats.get(f'away_{metric}')

                if val is not None:
                    try:
                        home_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if home_values:
                features[f'home_rolling_{metric}'] = np.mean(home_values)
                features[f'home_rolling_{metric}_std'] = np.std(home_values)
            else:
                features[f'home_rolling_{metric}'] = 0.0
                features[f'home_rolling_{metric}_std'] = 0.0

        # 客队滚动均值
        for metric in self.CORE_METRICS:
            away_values = []
            for _, row in away_before.iterrows():
                stats = row.get('stats', {})
                if row['is_home']:
                    val = stats.get(f'home_{metric}')
                else:
                    val = stats.get(f'away_{metric}')

                if val is not None:
                    try:
                        away_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if away_values:
                features[f'away_rolling_{metric}'] = np.mean(away_values)
                features[f'away_rolling_{metric}_std'] = np.std(away_values)
            else:
                features[f'away_rolling_{metric}'] = 0.0
                features[f'away_rolling_{metric}_std'] = 0.0

        return features

    def build_rolling_dataset(self, df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
        """
        构建完整的滚动特征数据集

        Args:
            df: 原始比赛数据
            window: 滚动窗口大小

        Returns:
            包含滚动特征的数据集
        """
        logger.info(f"📊 滚动窗口大小: {window} 场")

        team_history = self.build_team_history(df)

        rolling_features = []

        for idx, row in df.iterrows():
            match_id = row['external_id']
            home_team = row['home_team']
            away_team = row['away_team']
            match_time = row['match_time']

            try:
                features = self.calculate_rolling_features(
                    team_history, match_id, home_team, away_team, match_time, window
                )
                rolling_features.append(features)

                if (idx + 1) % 50 == 0:
                    logger.info(f"  处理进度: {idx + 1}/{len(df)}")

            except Exception as e:
                logger.warning(f"⚠️  比赛 {match_id} 计算失败: {e}")
                continue

        rolling_df = pd.DataFrame(rolling_features)
        logger.info(f"✅ 滚动特征计算完成: {len(rolling_df)} 场")

        return rolling_df

    def save_rolling_dataset(self, df: pd.DataFrame, output_path: str = "data/V17_ROLLING_FEATURES.csv"):
        """保存滚动特征数据集"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"✅ 滚动特征数据集已保存: {output_path}")

    # ========================================================================
    # Phase 4: 模型训练
    # ========================================================================

    def prepare_training_data(self, rolling_df: pd.DataFrame, original_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        准备训练数据

        Args:
            rolling_df: 滚动特征数据
            original_df: 原始比赛数据

        Returns:
            特征矩阵 X 和标签 y
        """
        logger.info("=" * 60)
        logger.info("Phase 4: 模型训练 - 数据准备")
        logger.info("=" * 60)

        # 合并数据
        merged_df = original_df.merge(
            rolling_df,
            left_on='external_id',
            right_on='match_id',
            how='inner'
        )

        # 提取特征
        X = merged_df[self.ROLLING_FEATURES].copy()

        # 过滤掉没有足够历史数据的比赛
        valid_mask = (merged_df['home_matches_count'] >= 5) & (merged_df['away_matches_count'] >= 5)
        valid_count = valid_mask.sum()

        logger.info(f"📊 有效比赛数量: {valid_count}/{len(merged_df)} (需要双方都有≥5场历史)")

        X_valid = X[valid_mask].reset_index(drop=True)
        df_valid = merged_df[valid_mask].reset_index(drop=True)

        y = df_valid['actual_result'].map(self.label_mapping)

        logger.info(f"✅ 特征矩阵: {X_valid.shape}")
        logger.info(f"✅ 标签分布:")
        for label, name in self.reverse_mapping.items():
            count = (y == label).sum()
            pct = 100 * count / len(y)
            logger.info(f"   {name}: {count} ({pct:.1f}%)")

        return X_valid, y

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        n_estimators: int = 200,
        max_depth: int = 4,
        learning_rate: float = 0.05
    ):
        """
        训练 XGBoost 模型

        Args:
            X_train: 训练特征
            y_train: 训练标签
            n_estimators: 树的数量
            max_depth: 树的最大深度
            learning_rate: 学习率

        Returns:
            训练好的模型
        """
        import xgboost as xgb

        logger.info("=" * 60)
        logger.info("Phase 4: 模型训练 - 训练中")
        logger.info("=" * 60)

        model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            min_child_weight=3,
            reg_alpha=0.5,
            reg_lambda=1.0,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='multi:softprob',
            num_class=3,
            eval_metric='mlogloss',
            random_state=42,
            n_jobs=-1,
        )

        logger.info(f"📊 模型参数:")
        logger.info(f"   n_estimators: {n_estimators}")
        logger.info(f"   max_depth: {max_depth}")
        logger.info(f"   learning_rate: {learning_rate}")

        model.fit(X_train, y_train, verbose=False)
        logger.info("✅ 模型训练完成")

        return model

    def evaluate_model(self, model, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """
        评估模型性能

        Args:
            model: 训练好的模型
            X_test: 测试特征
            y_test: 测试标签

        Returns:
            评估指标字典
        """
        from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report

        logger.info("=" * 60)
        logger.info("Phase 4: 模型训练 - 评估")
        logger.info("=" * 60)

        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average='macro')

        logger.info(f"📊 测试集准确率: {accuracy*100:.2f}%")
        logger.info(f"📊 F1 Score (Macro): {f1_macro:.4f}")

        # 混淆矩阵
        cm = confusion_matrix(y_test, y_pred)
        logger.info(f"\n📊 混淆矩阵:")
        logger.info(f"              预测Away  预测Draw  预测Home")
        for i, label in enumerate(['实际Away', '实际Draw', '实际Home']):
            logger.info(f"{label:10s}  {cm[i][0]:8d}  {cm[i][1]:8d}  {cm[i][2]:8d}")

        return {
            'accuracy': accuracy,
            'f1_macro': f1_macro,
            'confusion_matrix': cm.tolist()
        }

    def save_model(self, model, output_dir: str = "src/production_models"):
        """保存模型"""
        import joblib
        import json

        os.makedirs(output_dir, exist_ok=True)

        model_path = os.path.join(output_dir, "v17.0_rolling_model.pkl")
        joblib.dump(model, model_path)
        logger.info(f"✅ 模型已保存: {model_path}")

        metadata = {
            'version': 'V17.0',
            'model_type': 'XGBoost',
            'features': self.ROLLING_FEATURES,
            'feature_count': len(self.ROLLING_FEATURES),
            'label_mapping': self.label_mapping,
            'reverse_mapping': self.reverse_mapping,
            'creation_date': datetime.now().isoformat(),
            'description': 'V17.0 Rolling Features Model - No Data Leakage',
            'training_data': 'Premier League 23/24 Season',
            'notes': 'Uses 10-match rolling averages (xG, shots, possession, rating)'
        }

        metadata_path = os.path.join(output_dir, "v17.0_rolling_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✅ 元数据已保存: {metadata_path}")

    # ========================================================================
    # 完整流水线
    # ========================================================================

    def run_full_pipeline(
        self,
        train_size: int = 300,
        rolling_window: int = 10,
        save_model: bool = True
    ) -> Dict:
        """
        运行完整的 V17.0 生产流水线

        Args:
            train_size: 训练集大小
            rolling_window: 滚动窗口大小
            save_model: 是否保存模型

        Returns:
            流水线执行结果
        """
        logger.info("=" * 80)
        logger.info("🚀 V17.0 生产流水线启动")
        logger.info("=" * 80)

        results = {}

        # Phase 3: L3 滚动特征计算
        df = self.extract_match_data()
        rolling_df = self.build_rolling_dataset(df, window=rolling_window)

        # Phase 4: 模型训练
        X, y = self.prepare_training_data(rolling_df, df.merge(rolling_df, left_on='external_id', right_on='match_id', how='inner'))

        # 时间序列分割
        X_train = X.iloc[:train_size]
        y_train = y[:train_size]
        X_test = X.iloc[train_size:]
        y_test = y[train_size:]

        logger.info(f"📊 训练集: {len(X_train)} 场")
        logger.info(f"📊 测试集: {len(X_test)} 场")

        # 训练模型
        model = self.train_model(X_train, y_train)

        # 评估模型
        metrics = self.evaluate_model(model, X_test, y_test)
        results['metrics'] = metrics
        results['train_size'] = len(X_train)
        results['test_size'] = len(X_test)

        # 保存模型
        if save_model:
            self.save_model(model)

        logger.info("")
        logger.info("=" * 80)
        logger.info("🎉 V17.0 生产流水线完成！")
        logger.info("=" * 80)
        logger.info("")
        logger.info("📊 模型性能摘要:")
        logger.info(f"   测试集准确率: {metrics['accuracy']*100:.2f}%")
        logger.info(f"   F1 Score (Macro): {metrics['f1_macro']:.4f}")
        logger.info("")

        return results


def main():
    """主函数 - 用于测试"""
    pipeline = V17ProductionPipeline()
    results = pipeline.run_full_pipeline(train_size=300, rolling_window=10)
    return 0 if results['metrics']['accuracy'] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
