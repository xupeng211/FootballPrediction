#!/usr/bin/env python3
"""
V5.2 简化版高维战术模型训练器
基于现有数据库数据训练高维特征模型
"""

import logging
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.impute import SimpleImputer

from src.config_unified import get_settings
from src.database.schema_manager import get_schema_manager

logger = logging.getLogger(__name__)


class V52SimpleTrainer:
    def __init__(self):
        self.settings = get_settings()
        self.schema_manager = get_schema_manager()

    def load_available_features(self):
        """加载可用的特征数据"""
        conn = self.schema_manager.get_connection()

        # 获取有比赛数据的记录，只使用实际存在的字段
        query = """
            SELECT
                external_id,
                home_score, away_score,
                home_xg, away_xg, xg_total, xg_diff,
                home_possession, away_possession, possession_diff,
                home_corners, away_corners, corners_diff,
                home_shots_total, away_shots_total, shots_total_diff,
                home_shots_on_target, away_shots_on_target, shots_on_target_diff,
                home_yellow_cards, away_yellow_cards, yellow_cards_diff,
                home_red_cards, away_red_cards, red_cards_diff,
                home_passes, away_passes, passes_diff,
                home_pass_accuracy, away_pass_accuracy, pass_accuracy_diff,
                home_aerial_won, away_aerial_won, aerial_won_diff,
                home_aerial_won_percentage, away_aerial_won_percentage, aerial_won_percentage_diff,
                big_chances_home, big_chances_away,
                big_chances_missed_home, big_chances_missed_away,
                home_clearances, away_clearances, clearances_diff,
                home_tackles, away_tackles, tackles_diff,
                home_fouls, away_fouls, fouls_diff,
                home_offsides, away_offsides, offsides_diff,
                home_corners_first_half, away_corners_first_half,
                home_corners_second_half, away_corners_second_half,
                home_xg_first_half, away_xg_first_half, xg_total_first_half,
                home_xg_second_half, away_xg_second_half, xg_total_second_half,
                home_yellow_cards_first_half, away_yellow_cards_first_half,
                home_red_cards_first_half, away_red_cards_first_half,
                expected_assists_home, expected_assists_away,
                home_team_form_points, away_team_form_points,
                home_team_recent_goals, away_team_recent_goals,
                home_team_recent_conceded, away_team_recent_conceded,
                home_team_h2h_wins, away_team_h2h_wins,
                home_team_h2h_goals, away_team_h2h_goals,
                temperature,
                home_advantage_score,
                -- 赔率特征
                home_current_odds, away_current_odds, draw_current_odds,
                home_opening_odds, away_opening_odds, draw_opening_odds,
                -- 额外战术特征
                home_crosses, away_crosses, crosses_diff,
                home_successful_passes, away_successful_passes, successful_passes_diff,
                home_shot_accuracy, away_shot_accuracy, shot_accuracy_diff,
                away_shots_blocked, home_shots_blocked, shots_blocked_diff,
                away_shots_off_target, home_shots_off_target, shots_off_target_diff,
                -- 其他特征
                possession_first_half_diff, possession_second_half_diff,
                corners_first_half_diff, corners_second_half_diff,
                yellow_cards_diff, red_cards_diff,
                passes_diff, pass_accuracy_diff,
                implied_home_win_prob, implied_draw_prob, implied_away_win_prob
            FROM match_features_training
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
            ORDER BY updated_at DESC
        """

        df = pd.read_sql(query, conn)
        conn.close()

        logger.info(f"✅ 加载数据: {len(df)} 条记录, {len(df.columns)} 个字段")

        return df

    def create_target(self, df):
        """创建目标变量"""
        def get_result(row):
            if row['home_score'] > row['away_score']:
                return 2  # 主胜
            elif row['home_score'] < row['away_score']:
                return 0  # 客胜
            else:
                return 1  # 平局

        y = df.apply(get_result, axis=1)
        result_counts = y.value_counts().sort_index()
        logger.info(f"📊 结果分布: 客胜={result_counts.get(0,0)}, 平局={result_counts.get(1,0)}, 主胜={result_counts.get(2,0)}")

        return y

    def train_model(self):
        """训练V5.2模型"""
        logger.info("🚀 开始V5.2高维战术模型训练...")

        # 加载数据
        df = self.load_available_features()

        if len(df) == 0:
            logger.error("❌ 没有可用的训练数据")
            return None

        # 创建目标变量
        y = self.create_target(df)

        # 选择特征列（排除非数值字段）
        feature_cols = []
        for col in df.columns:
            if col not in ['external_id', 'home_team', 'away_team', 'match_time'] and df[col].dtype in ['int64', 'float64']:
                feature_cols.append(col)

        logger.info(f"📊 特征列数: {len(feature_cols)}")

        X = df[feature_cols].values

        # 处理缺失值
        imputer = SimpleImputer(strategy='median')
        X = imputer.fit_transform(X)

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        logger.info(f"✅ 数据预处理完成: 特征矩阵{X_scaled.shape}")

        # XGBoost参数
        params = {
            'objective': 'multi:softmax',
            'num_class': 3,
            'max_depth': 5,
            'learning_rate': 0.05,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.6,
            'random_state': 42,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0
        }

        model = xgb.XGBClassifier(**params)

        # 10折交叉验证
        cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')

        logger.info(f"📈 10折CV准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        # 训练最终模型
        model.fit(X_scaled, y)

        # 评估
        y_pred = model.predict(X_scaled)
        accuracy = accuracy_score(y, y_pred)
        logger.info(f"🎯 训练集准确率: {accuracy:.4f}")

        # 特征重要性
        feature_importance = dict(zip(feature_cols, model.feature_importances_))
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        logger.info("🏆 Top 10 重要特征:")
        for i, (feature, importance) in enumerate(sorted_features[:10]):
            logger.info(f"  {i+1:2d}. {feature:25s}: {importance:.4f}")

        # 保存模型
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"xgb_v52_tactical_{timestamp}"

        import os
        os.makedirs("data/models", exist_ok=True)

        model_path = f"data/models/{model_name}.pkl"
        scaler_path = f"data/models/{model_name}_scaler.pkl"

        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)

        # 保存元数据
        import json
        metadata = {
            'model_name': model_name,
            'version': 'V5.2_Simple',
            'accuracy': accuracy,
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'feature_count': len(feature_cols),
            'sample_count': len(df),
            'top_features': sorted_features[:20],
            'training_date': datetime.now().isoformat()
        }

        metadata_path = f"data/models/{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"💾 模型已保存: {model_path}")

        # 检查是否达成目标
        if accuracy >= 0.58:
            logger.info(f"🎉 恭喜！模型准确率 {accuracy:.4f}% 突破58%目标！")
        else:
            gap = 0.58 - accuracy
            logger.info(f"📊 距离58%目标还差 {gap*100:.1f}%")

        return {
            'model_path': model_path,
            'scaler_path': scaler_path,
            'metadata_path': metadata_path,
            'accuracy': accuracy,
            'cv_accuracy_mean': cv_scores.mean(),
            'feature_count': len(feature_cols),
            'sample_count': len(df),
            'top_features': sorted_features,
            'target_achieved': accuracy >= 0.58
        }


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    trainer = V52SimpleTrainer()
    results = trainer.train_model()

    if results:
        print("\n" + "="*60)
        print("🏆 V5.2 高维战术模型训练完成!")
        print("="*60)
        print(f"📊 模型准确率: {results['accuracy']:.4f}")
        print(f"📈 10折CV准确率: {results['cv_accuracy_mean']:.4f}")
        print(f"🎯 58%目标达成: {'✅ 是' if results['target_achieved'] else '❌ 否'}")
        print(f"🔢 特征维度: {results['feature_count']}")
        print(f"📋 训练样本: {results['sample_count']}")
        print(f"💾 模型路径: {results['model_path']}")

        print("\n🏆 Top 10 特征重要性:")
        for i, (feature, importance) in enumerate(results['top_features'][:10]):
            print(f"  {i+1:2d}. {feature:25s}: {importance:.4f}")
    else:
        print("❌ 训练失败")


if __name__ == "__main__":
    main()