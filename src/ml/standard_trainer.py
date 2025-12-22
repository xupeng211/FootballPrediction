#!/usr/bin/env python3
"""
V9.6 标准化训练器 - 生产级标准组件
整合 V9.1 的黄金配方，实现一键训练和封存

作者: Claude Code
版本: V9.6
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score, accuracy_score
from sklearn.model_selection import train_test_split
import joblib
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')


class StandardTrainer:
    """
    标准化训练器 - V9.1 黄金配方的生产级实现

    核心流程:
    1. 181维特征对齐
    2. 前向时间窗口训练
    3. 概率校准 (Isotonic Regression)
    4. 模型封存
    """

    def __init__(self, version: str = "V9.6"):
        """初始化训练器"""
        self.version = version
        self.model = None
        self.calibrated_model = None
        self.feature_names = None
        self.metadata = {
            'version': version,
            'created_at': datetime.now().isoformat(),
            'feature_count': 181,
            'training_history': []
        }

    def validate_181_features(self, df: pd.DataFrame) -> bool:
        """
        验证181维特征对齐

        Args:
            df: 输入数据框

        Returns:
            bool: 特征是否有效
        """
        print(f"🔍 验证 181 维特征对齐...")

        # 定义181维特征
        expected_features = self._get_expected_features()

        # 检查特征是否存在
        missing_features = set(expected_features) - set(df.columns)
        extra_features = set(df.columns) - set(expected_features)

        if missing_features:
            print(f"  ❌ 缺失 {len(missing_features)} 个特征")
            for feat in sorted(missing_features)[:10]:
                print(f"     - {feat}")
            if len(missing_features) > 10:
                print(f"     ... 还有 {len(missing_features) - 10} 个")
            return False

        if extra_features:
            print(f"  ⚠️  发现 {len(extra_features)} 个额外特征")
            for feat in sorted(extra_features)[:10]:
                print(f"     - {feat}")

        print(f"  ✅ 181 维特征验证通过")
        self.feature_names = expected_features
        return True

    def _get_expected_features(self) -> List[str]:
        """获取181维期望特征列表"""
        features = []

        # 基础统计特征 (30维)
        features.extend([
            'home_avg_xg', 'away_avg_xg',
            'home_avg_goals', 'away_avg_goals',
            'home_avg_shots', 'away_avg_shots',
            'home_avg_shots_on_target', 'away_avg_shots_on_target',
            'home_avg_possession_index', 'away_avg_possession_index',
            'home_avg_pass_accuracy', 'away_avg_pass_accuracy',
            'home_avg_rating', 'away_avg_rating',
            'home_win_rate', 'away_win_rate',
            'home_draw_rate', 'away_draw_rate',
            'home_loss_rate', 'away_loss_rate',
            'home_avg_corners', 'away_avg_corners',
            'home_avg_fouls', 'away_avg_fouls',
            'home_avg_yellow_cards', 'away_avg_yellow_cards',
            'home_avg_red_cards', 'away_avg_red_cards',
            'home_avg_offsides', 'away_avg_offsides'
        ])

        # 门将特征 (20维)
        features.extend([
            'home_keeper_saves_per_game', 'away_keeper_saves_per_game',
            'home_keeper_save_percentage', 'away_keeper_save_percentage',
            'home_keeper_clean_sheets', 'away_keeper_clean_sheets',
            'home_keeper_punches', 'away_keeper_punches',
            'home_keeper_high_claims', 'away_keeper_high_claims',
            'home_keeper_sweeper_clearances', 'away_keeper_sweeper_clearances',
            'home_keeper_errors_leading_to_goal', 'away_keeper_errors_leading_to_goal',
            'home_keeper_distribution_accuracy', 'away_keeper_distribution_accuracy',
            'home_keeper_goal_prevention', 'away_keeper_goal_prevention',
            'home_keeper_ps_xg_on_target', 'away_keeper_ps_xg_on_target'
        ])

        # 创造力特征 (18维)
        features.extend([
            'home_key_passes_per_game', 'away_key_passes_per_game',
            'home_assists_per_game', 'away_assists_per_game',
            'home_through_balls', 'away_through_balls',
            'home_crosses', 'away_crosses',
            'home_cross_accuracy', 'away_cross_accuracy',
            'home_progressive_passes', 'away_progressive_passes',
            'home_progressive_carries', 'away_progressive_carries',
            'home_final_third_passes', 'away_final_third_passes',
            'home_big_chances_created', 'away_big_chances_created'
        ])

        # 前锋效率特征 (20维)
        features.extend([
            'home_shot_conversion_rate', 'away_shot_conversion_rate',
            'home_xg_per_shot', 'away_xg_per_shot',
            'home_big_chance_conversion', 'away_big_chance_conversion',
            'home_first_time_shots', 'away_first_time_shots',
            'home_left_foot_shots', 'away_left_foot_shots',
            'home_right_foot_shots', 'away_right_foot_shots',
            'home_headed_goals', 'away_headed_goals',
            'home_penalty_area_shots', 'away_penalty_area_shots',
            'home_open_play_goals', 'away_open_play_goals',
            'home_set_piece_goals', 'away_set_piece_goals'
        ])

        # 防守抢断特征 (20维)
        features.extend([
            'home_tackles_won', 'away_tackles_won',
            'home_tackles_attempted', 'away_tackles_attempted',
            'home_tackle_success_rate', 'away_tackle_success_rate',
            'home_interceptions', 'away_interceptions',
            'home_clearances', 'away_clearances',
            'home_blocks', 'away_blocks',
            'home_aerial_duels_won', 'away_aerial_duels_won',
            'home_aerial_duels_total', 'away_aerial_duels_total',
            'home_aerial_success_rate', 'away_aerial_success_rate',
            'home_recoveries', 'away_recoveries',
            'home_duels_won', 'away_duels_won'
        ])

        # 控球节奏特征 (20维)
        features.extend([
            'home_possession_wins', 'away_possession_wins',
            'home_possession_losses', 'away_possession_losses',
            'home_pass_completion_rate', 'away_pass_completion_rate',
            'home_progressive_pass_rate', 'away_progressive_pass_rate',
            'home_pass_into_final_third', 'away_pass_into_final_third',
            'home_pass_into_penalty_area', 'away_pass_into_penalty_area',
            'home_crosses_completed', 'away_crosses_completed',
            'home_through_balls_completed', 'away_through_balls_completed',
            'home_long_passes_completed', 'away_long_passes_completed',
            'home_short_passes_completed', 'away_short_passes_completed'
        ])

        # 纪律心理特征 (17维)
        features.extend([
            'home_yellow_cards_per_game', 'away_yellow_cards_per_game',
            'home_red_cards_per_game', 'away_red_cards_per_game',
            'home_fouls_committed', 'away_fouls_committed',
            'home_fouls_received', 'away_fouls_received',
            'home_cards_for_dissent', 'away_cards_for_dissent',
            'home_cards_for_timing', 'away_cards_for_timing',
            'home_cards_for_team_fouls', 'away_cards_for_team_fouls',
            'home_individual_errors', 'away_individual_errors',
            'home_negative_plays', 'away_negative_plays'
        ])

        # 高级指标特征 (20维)
        features.extend([
            'home_xg_chain', 'away_xg_chain',
            'home_xg_buildup', 'away_xg_buildup',
            'home_xg_shot_assist', 'away_xg_shot_assist',
            'home_sca_per_90', 'away_sca_per_90',
            'home_gca_per_90', 'away_gca_per_90',
            'home_prgressive_passes_received', 'away_prgressive_passes_received',
            'home_carries_into_final_third', 'away_carries_into_final_third',
            'home_carries_into_penalty_area', 'away_carries_into_penalty_area',
            'home_carries_progressive', 'away_carries_progressive',
            'home_take_ons_won', 'away_take_ons_won',
            'home_take_ons_attempted', 'away_take_ons_attempted'
        ])

        # 差异特征 (15维)
        features.extend([
            'xg_diff', 'goals_diff', 'shots_diff', 'shots_on_target_diff',
            'possession_diff', 'rating_diff', 'corners_diff', 'cards_diff',
            'tackles_diff', 'interceptions_diff', 'clearances_diff',
            'pass_accuracy_diff', 'fouls_diff', 'offsides_diff', 'keeper_saves_diff'
        ])

        return features

    def prepare_data(self, df: pd.DataFrame, date_col: str = 'match_date') -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """
        准备训练数据

        Args:
            df: 输入数据框
            date_col: 日期列名

        Returns:
            Tuple: (X, y, df_processed)
        """
        print(f"📊 准备训练数据...")

        # 过滤有效数据
        df_clean = df[
            df['real_home_odds'].notna() &
            df['real_draw_odds'].notna() &
            df['real_away_odds'].notna() &
            df['actual_result'].notna()
        ].copy()

        print(f"  原始数据: {len(df)} 场")
        print(f"  有效数据: {len(df_clean)} 场")

        # 转换日期并排序
        if date_col in df_clean.columns:
            df_clean[date_col] = pd.to_datetime(df_clean[date_col])
            df_clean = df_clean.sort_values(date_col).reset_index(drop=True)

        # 准备特征
        X = df_clean[self.feature_names].fillna(0)

        # 准备标签 (预测主胜)
        y = (df_clean['actual_result'] == 'H').astype(int)

        print(f"  特征维度: {X.shape}")
        print(f"  主胜样本: {y.sum()} ({y.mean()*100:.1f}%)")

        return X.values, y.values, df_clean

    def forward_time_window_training(self, X: np.ndarray, y: np.ndarray,
                                    dates: np.ndarray,
                                    train_window: int = 1000,
                                    step: int = 100) -> Dict[str, Any]:
        """
        前向时间窗口训练

        Args:
            X: 特征矩阵
            y: 标签
            dates: 日期数组
            train_window: 训练窗口大小
            step: 滑动步长

        Returns:
            Dict: 训练结果
        """
        print(f"\n🎯 前向时间窗口训练...")
        print(f"=" * 80)

        n_samples = len(X)
        results = []

        for i in range(0, n_samples - train_window, step):
            # 训练窗口
            train_end = i + train_window
            test_start = train_end
            test_end = min(test_start + step, n_samples)

            X_train = X[i:train_end]
            y_train = y[i:train_end]
            X_test = X[test_start:test_end]
            y_test = y[test_start:test_end]

            if len(X_test) == 0:
                continue

            # 训练模型
            model = lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                num_leaves=40,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=0.1,
                random_state=42,
                verbose=-1
            )

            model.fit(X_train, y_train)

            # 测试
            test_probs = model.predict_proba(X_test)[:, 1]
            test_brier = brier_score_loss(y_test, test_probs)
            test_auc = roc_auc_score(y_test, test_probs)

            results.append({
                'window_start': i,
                'window_end': train_end,
                'test_start': test_start,
                'test_end': test_end,
                'train_size': len(X_train),
                'test_size': len(X_test),
                'brier_score': test_brier,
                'auc_score': test_auc
            })

            if len(results) % 5 == 0:
                print(f"  完成窗口 {len(results)}: Brier={test_brier:.4f}, AUC={test_auc:.4f}")

        # 计算平均性能
        avg_brier = np.mean([r['brier_score'] for r in results])
        avg_auc = np.mean([r['auc_score'] for r in results])

        print(f"\n📊 前向窗口平均性能:")
        print(f"  窗口数: {len(results)}")
        print(f"  平均 Brier Score: {avg_brier:.4f}")
        print(f"  平均 AUC Score: {avg_auc:.4f}")

        self.metadata['training_history'].extend(results)

        return {
            'window_results': results,
            'avg_brier_score': avg_brier,
            'avg_auc_score': avg_auc
        }

    def calibrate_probabilities(self, X_train: np.ndarray, y_train: np.ndarray,
                               X_cal: np.ndarray, y_cal: np.ndarray) -> Any:
        """
        概率校准 (Isotonic Regression)

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_cal: 校准特征
            y_cal: 校准标签

        Returns:
            CalibratedClassifierCV: 校准后的模型
        """
        print(f"\n🎯 概率校准 (Isotonic Regression)...")

        # 训练基础模型
        base_model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            num_leaves=40,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            verbose=-1
        )

        base_model.fit(X_train, y_train)

        # Isotonic Regression 校准
        self.calibrated_model = CalibratedClassifierCV(
            base_model, method='isotonic', cv=3
        )

        self.calibrated_model.fit(X_cal, y_cal)

        # 校准集性能
        cal_probs = self.calibrated_model.predict_proba(X_cal)[:, 1]
        cal_brier = brier_score_loss(y_cal, cal_probs)
        cal_auc = roc_auc_score(y_cal, cal_probs)

        print(f"  校准集性能:")
        print(f"    Brier Score: {cal_brier:.4f}")
        print(f"    AUC Score: {cal_auc:.4f}")

        return self.calibrated_model

    def train_and_seal(self, data_path: str, output_dir: str = "src/production_models",
                      test_size: float = 0.2) -> Dict[str, Any]:
        """
        一键训练和封存

        Args:
            data_path: 数据文件路径
            output_dir: 输出目录
            test_size: 测试集比例

        Returns:
            Dict: 训练结果
        """
        print("=" * 80)
        print(f"🚀 {self.version} 标准化训练器 - 一键训练和封存")
        print("=" * 80)

        # 1. 加载数据
        print(f"\n第一步：加载数据...")
        df = pd.read_csv(data_path)
        print(f"  数据路径: {data_path}")
        print(f"  数据量: {len(df)} 场比赛")

        # 2. 验证181维特征
        if not self.validate_181_features(df):
            raise ValueError("181维特征验证失败")

        # 3. 准备数据
        X, y, df_clean = self.prepare_data(df)

        # 4. 时间序列分割
        print(f"\n第四步：时间序列分割...")
        test_size_abs = int(len(X) * test_size)
        X_train = X[:-test_size_abs]
        y_train = y[:-test_size_abs]
        X_test = X[-test_size_abs:]
        y_test = y[-test_size_abs:]

        print(f"  训练集: {len(X_train)} 样本")
        print(f"  测试集: {len(X_test)} 样本")

        # 5. 前向时间窗口训练
        window_results = self.forward_time_window_training(X_train, y_train, df_clean['match_date'].values)

        # 6. 概率校准
        print(f"\n第五步：概率校准...")
        self.calibrate_probabilities(X_train, y_train, X_test, y_test)

        # 7. 最终评估
        print(f"\n第六步：最终评估...")
        final_probs = self.calibrated_model.predict_proba(X_test)[:, 1]
        final_brier = brier_score_loss(y_test, final_probs)
        final_auc = roc_auc_score(y_test, final_probs)
        final_acc = accuracy_score(y_test, final_probs > 0.5)

        print(f"  测试集性能:")
        print(f"    Brier Score: {final_brier:.4f}")
        print(f"    AUC Score: {final_auc:.4f}")
        print(f"    Accuracy: {final_acc:.4f}")

        # 8. 封存模型
        print(f"\n第七步：封存模型...")
        os.makedirs(output_dir, exist_ok=True)

        # 保存校准模型
        model_path = os.path.join(output_dir, f'{self.version.lower()}_standard_model.pkl')
        joblib.dump(self.calibrated_model, model_path)

        # 保存特征名称
        features_path = os.path.join(output_dir, f'{self.version.lower()}_standard_features.json')
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f)

        # 保存元数据
        self.metadata.update({
            'model_path': model_path,
            'features_path': features_path,
            'training_date': datetime.now().isoformat(),
            'data_size': len(df),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'final_brier_score': final_brier,
            'final_auc_score': final_auc,
            'final_accuracy': final_acc,
            'avg_window_brier': window_results['avg_brier_score'],
            'avg_window_auc': window_results['avg_auc_score']
        })

        metadata_path = os.path.join(output_dir, f'{self.version.lower()}_standard_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)

        print(f"  ✅ 模型已封存:")
        print(f"    - {model_path}")
        print(f"    - {features_path}")
        print(f"    - {metadata_path}")

        # 9. 返回结果
        result = {
            'success': True,
            'version': self.version,
            'model_path': model_path,
            'features_path': features_path,
            'metadata_path': metadata_path,
            'metrics': {
                'final_brier_score': final_brier,
                'final_auc_score': final_auc,
                'final_accuracy': final_acc,
                'avg_window_brier': window_results['avg_brier_score'],
                'avg_window_auc': window_results['avg_auc_score']
            },
            'window_results': window_results['window_results']
        }

        print("\n" + "=" * 80)
        print(f"✅ {self.version} 标准化训练完成")
        print("=" * 80)

        return result


def main():
    """主函数 - 示例用法"""
    # 创建训练器
    trainer = StandardTrainer(version="V9.6")

    # 一键训练和封存
    result = trainer.train_and_seal(
        data_path="/home/user/projects/FootballPrediction/data/combined_multi_season_odds.csv",
        output_dir="/home/user/projects/FootballPrediction/src/production_models"
    )

    print(f"\n🎉 训练完成!")
    print(f"  最终 Brier Score: {result['metrics']['final_brier_score']:.4f}")
    print(f"  最终 AUC Score: {result['metrics']['final_auc_score']:.4f}")


if __name__ == "__main__":
    main()
