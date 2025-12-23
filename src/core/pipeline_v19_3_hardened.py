#!/usr/bin/env python3
"""
V19.3 硬化版本流水线 - Model Hardening

基于 V19.2 审计报告的重铸版本：
1. 强正则化配置 - 防止过拟合
2. TimeSeriesSplit 5折验证 - 确保跨季度稳定性
3. 特征重要性过滤 - 移除噪音特征
4. Scaler 完整持久化 - 修复 H-03

目标：实现真实的跨季度泛化能力，平均 ROI > 10%

Author: Model Hardening Expert
Version: V19.3 Hardened
Date: 2025-12-23
"""

import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import pandas as pd
import json
import joblib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
from src.ml.features.v19_advanced_features import V19AdvancedFeatureExtractor
from src.ml.features.standings_calculator import initialize_global_calculator, get_global_calculator
from src.ml.v19_probability_calibrator import V19ProbabilityCalibrator
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, brier_score_loss
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class HardenedMetrics:
    """V19.3 硬化版本指标"""
    version: str
    timestamp: str

    # 模型配置
    model_params: Dict[str, Any]

    # 特征信息
    total_features: int
    removed_features: List[str]
    remaining_features: List[str]

    # 交叉验证结果 (5折)
    cv_fold_results: List[Dict[str, float]]
    cv_avg_roi: float
    cv_std_roi: float
    cv_min_roi: float
    cv_max_roi: float
    cv_avg_accuracy: float

    # 最终模型性能
    final_train_accuracy: float
    final_test_accuracy: float
    final_test_roi: float
    final_brier_score: float

    # 部署建议
    can_deploy: bool
    deploy_reason: str


class V19_3HardenedPipeline:
    """
    V19.3 硬化版本流水线

    基于 V19.2 审计报告的改进：
    - 强正则化配置
    - TimeSeriesSplit 验证
    - 特征重要性过滤
    - 完整 Scaler 持久化
    """

    # ============================================================
    # 强正则化配置 (基于审计测试1验证)
    # ============================================================
    HARDENED_PARAMS = {
        'n_estimators': 200,        # 适度减少树数量
        'max_depth': 3,              # 强制降低深度 (审计验证有效)
        'learning_rate': 0.01,       # 慢火炖肉 (原 0.05)
        'min_child_weight': 5,       # 增加最小子节点权重
        'gamma': 0.5,                # 剪枝阈值 (审计验证有效)
        'subsample': 0.7,            # 增加随机性 (原 0.9)
        'colsample_bytree': 0.7,     # 特征采样 (原 0.8)
        'reg_alpha': 1.0,            # L1 正则化 (审计验证有效)
        'reg_lambda': 2.0,           # L2 正则化 (审计验证有效)
        'random_state': 42,
        'use_label_encoder': False,
        'eval_metric': 'mlogloss',
    }

    # 特征过滤配置
    TOP_FEATURES_TO_KEEP = 45  # 保留前 45 个特征 (移除约 11 个低贡献特征)
    N_SPLITS = 5               # 5折时间序列交叉验证

    def __init__(self):
        """初始化 V19.3 硬化流水线"""
        self.feature_extractor = V19AdvancedFeatureExtractor()
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.removed_features = []

        logger.info("V19.3 硬化版本流水线初始化完成")
        logger.info(f"强正则化配置: {self.HARDENED_PARAMS}")

    def load_data(self, limit: int = 760) -> pd.DataFrame:
        """从数据库加载数据"""
        logger.info(f"从数据库加载数据（目标: {limit} 场）...")

        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="football_db",
            user="football_user",
            password="football_pass"
        )

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
        SELECT
            m.id,
            m.home_team,
            m.away_team,
            m.match_time,
            m.home_score,
            m.away_score,
            m.status,
            m.actual_result,
            m.l2_raw_json as raw_data
        FROM matches m
        WHERE m.status = 'Finished'
        AND m.home_score IS NOT NULL
        ORDER BY m.match_time ASC
        LIMIT %s
        """

        cursor.execute(query, (limit,))
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        df = pd.DataFrame([dict(m) for m in matches])
        logger.info(f"✅ 已从数据库加载 {len(df)} 场比赛")

        return df

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取特征（复用 V19 流水线逻辑）"""
        logger.info("提取 V19.0 特征...")

        initialize_global_calculator(df)
        calculator = get_global_calculator()

        features_list = []

        for idx, row in df.iterrows():
            try:
                home_team = row.get('home_team', '')
                away_team = row.get('away_team', '')

                home_standings = calculator.get_team_stats_at_match(idx, home_team)
                away_standings = calculator.get_team_stats_at_match(idx, away_team)

                v18_features = self._extract_v18_features(
                    row,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

                if v18_features is None:
                    continue

                v19_features = self._extract_new_features(
                    row,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

                all_features = {**v18_features, **v19_features}
                all_features['match_id'] = row.get('id', idx)
                all_features['home_team'] = home_team
                all_features['away_team'] = away_team
                all_features['match_time'] = row.get('match_time', '')

                # 联赛编码
                all_features['league_epl'] = 1.0
                all_features['league_championship'] = 0.0
                all_features['league_laliga'] = 0.0
                all_features['league_bundesliga'] = 0.0
                all_features['league_serie_a'] = 0.0
                all_features['league_ligue_1'] = 0.0
                all_features['league_tier_1'] = 1.0
                all_features['league_tier_2'] = 0.0
                all_features['league_tier_3'] = 0.0

                # 提取标签
                home_score = row.get('home_score', 0)
                away_score = row.get('away_score', 0)

                if home_score > away_score:
                    all_features['result'] = 2
                elif home_score < away_score:
                    all_features['result'] = 0
                else:
                    all_features['result'] = 1

                features_list.append(all_features)

            except Exception as e:
                logger.debug(f"特征提取失败 (行 {idx}): {e}")
                continue

        feature_df = pd.DataFrame(features_list)
        logger.info(f"✅ 特征提取完成: {len(feature_df)} 场比赛")

        return feature_df

    def _extract_v18_features(
        self,
        row: Dict,
        home_standings: Optional[Dict] = None,
        away_standings: Optional[Dict] = None
    ) -> Optional[Dict[str, float]]:
        """提取 V18 基础特征"""
        try:
            raw_data = row.get('raw_data', '{}')
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            if 'home_stats' in raw_data and 'away_stats' in raw_data:
                return self._extract_from_simple_format(
                    raw_data,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

            if 'l2_json' in raw_data:
                l2_data = raw_data['l2_json']
                if isinstance(l2_data, str):
                    l2_data = json.loads(l2_data)

                if 'content' in l2_data and 'stats' in l2_data['content']:
                    stats_data = l2_data['content']['stats']
                    if 'Periods' in stats_data and 'All' in stats_data['Periods']:
                        period_stats = stats_data['Periods']['All']
                        if 'stats' in period_stats:
                            stats_list = period_stats['stats']
                            return self._extract_from_stats_list(
                                stats_list,
                                home_standings=home_standings,
                                away_standings=away_standings
                            )

            return None

        except Exception as e:
            logger.debug(f"特征提取失败: {e}")
            return None

    def _extract_from_simple_format(
        self,
        raw_data: Dict,
        home_standings: Optional[Dict] = None,
        away_standings: Optional[Dict] = None
    ) -> Optional[Dict[str, float]]:
        """从简化格式提取特征"""
        try:
            home_stats = raw_data.get('home_stats', {})
            away_stats = raw_data.get('away_stats', {})

            if not home_stats or not away_stats:
                return None

            def get_stat(stats_dict, key):
                val = stats_dict.get(key, None)
                if val is None:
                    return np.nan
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return np.nan

            if home_standings is not None:
                home_pos = home_standings.get('position', np.nan)
                home_pts = home_standings.get('points', np.nan)
                home_form_pts = home_standings.get('form_points', np.nan)
                home_win_rate = home_standings.get('win_rate', np.nan)
            else:
                home_pos = np.nan
                home_pts = np.nan
                home_form_pts = np.nan
                home_win_rate = np.nan

            if away_standings is not None:
                away_pos = away_standings.get('position', np.nan)
                away_pts = away_standings.get('points', np.nan)
                away_form_pts = away_standings.get('form_points', np.nan)
                away_loss_rate = away_standings.get('loss_rate', np.nan)
            else:
                away_pos = np.nan
                away_pts = np.nan
                away_form_pts = np.nan
                away_loss_rate = np.nan

            pos_diff = home_pos - away_pos if not np.isnan(home_pos) and not np.isnan(away_pos) else np.nan
            pts_diff = home_pts - away_pts if not np.isnan(home_pts) and not np.isnan(away_pts) else np.nan

            home_xg = get_stat(home_stats, 'expected_goals')
            away_xg = get_stat(away_stats, 'expected_goals')
            home_shots_on_target = get_stat(home_stats, 'shots_on_target')
            away_shots_on_target = get_stat(away_stats, 'shots_on_target')
            home_possession = get_stat(home_stats, 'possession')
            away_possession = get_stat(away_stats, 'possession')
            home_shots = get_stat(home_stats, 'shots')
            away_shots = get_stat(away_stats, 'shots')
            home_corners = get_stat(home_stats, 'corners')
            away_corners = get_stat(away_stats, 'corners')

            features = {
                'home_rolling_xg': home_xg,
                'away_rolling_xg': away_xg,
                'home_rolling_shots_on_target': home_shots_on_target,
                'away_rolling_shots_on_target': away_shots_on_target,
                'home_rolling_possession': home_possession,
                'away_rolling_possession': away_possession,
                'home_rolling_shots': home_shots,
                'away_rolling_shots': away_shots,
                'home_rolling_corners': home_corners,
                'away_rolling_corners': away_corners,
                'home_table_position': home_pos,
                'away_table_position': away_pos,
                'table_position_diff': pos_diff,
                'home_points': home_pts,
                'away_points': away_pts,
                'points_diff': pts_diff,
                'home_recent_form_points': home_form_pts,
                'away_recent_form_points': away_form_pts,
            }

            return features

        except Exception as e:
            return None

    def _extract_from_stats_list(
        self,
        stats_list: List,
        home_standings: Optional[Dict] = None,
        away_standings: Optional[Dict] = None
    ) -> Optional[Dict[str, float]]:
        """从 FotMob stats 列表提取特征"""
        try:
            home_stats = {}
            away_stats = {}

            for stat_group in stats_list:
                if 'stats' in stat_group:
                    for stat_item in stat_group['stats']:
                        key = stat_item.get('key', '')
                        stats_array = stat_item.get('stats', [])

                        if len(stats_array) >= 2:
                            home_val = stats_array[0]
                            away_val = stats_array[1]

                            try:
                                if isinstance(home_val, str):
                                    home_val = home_val.split()[0]
                                home_stats[key] = float(home_val)
                            except (ValueError, AttributeError, TypeError):
                                home_stats[key] = None

                            try:
                                if isinstance(away_val, str):
                                    away_val = away_val.split()[0]
                                away_stats[key] = float(away_val)
                            except (ValueError, AttributeError, TypeError):
                                away_stats[key] = None

            valid_home = any(v is not None for v in home_stats.values())
            valid_away = any(v is not None for v in away_stats.values())

            if not valid_home or not valid_away:
                return None

            def get_stat(stats_dict, key):
                val = stats_dict.get(key, None)
                if val is None:
                    return np.nan
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return np.nan

            if home_standings is not None:
                home_pos = home_standings.get('position', np.nan)
                home_pts = home_standings.get('points', np.nan)
                home_form_pts = home_standings.get('form_points', np.nan)
                home_win_rate = home_standings.get('win_rate', np.nan)
            else:
                home_pos = np.nan
                home_pts = np.nan
                home_form_pts = np.nan
                home_win_rate = np.nan

            if away_standings is not None:
                away_pos = away_standings.get('position', np.nan)
                away_pts = away_standings.get('points', np.nan)
                away_form_pts = away_standings.get('form_points', np.nan)
                away_loss_rate = away_standings.get('loss_rate', np.nan)
            else:
                away_pos = np.nan
                away_pts = np.nan
                away_form_pts = np.nan
                away_loss_rate = np.nan

            pos_diff = home_pos - away_pos if not np.isnan(home_pos) and not np.isnan(away_pos) else np.nan
            pts_diff = home_pts - away_pts if not np.isnan(home_pts) and not np.isnan(away_pts) else np.nan

            home_xg = get_stat(home_stats, 'expected_goals')
            away_xg = get_stat(away_stats, 'expected_goals')
            home_shots = get_stat(home_stats, 'ShotsOnTarget')
            away_shots = get_stat(away_stats, 'ShotsOnTarget')
            home_possession = get_stat(home_stats, 'BallPossesion')
            away_possession = get_stat(away_stats, 'BallPossesion')

            return {
                'home_rolling_xg': home_xg,
                'home_rolling_xg_std': np.nan,
                'home_rolling_shots_on_target': home_shots,
                'home_rolling_shots_on_target_std': np.nan,
                'home_rolling_possession': home_possession,
                'home_rolling_possession_std': np.nan,
                'home_rolling_team_rating': np.nan,
                'home_rolling_team_rating_std': np.nan,
                'away_rolling_xg': away_xg,
                'away_rolling_xg_std': np.nan,
                'away_rolling_shots_on_target': away_shots,
                'away_rolling_shots_on_target_std': np.nan,
                'away_rolling_possession': away_possession,
                'away_rolling_possession_std': np.nan,
                'away_rolling_team_rating': np.nan,
                'away_rolling_team_rating_std': np.nan,
                'home_table_position': home_pos,
                'away_table_position': away_pos,
                'table_position_diff': pos_diff,
                'home_points': home_pts,
                'away_points': away_pts,
                'points_diff': pts_diff,
                'home_recent_form_points': home_form_pts,
                'away_recent_form_points': away_form_pts,
                'home_win_rate_last10': home_win_rate,
                'away_loss_rate_last10': away_loss_rate,
            }

        except Exception as e:
            return None

    def _extract_new_features(
        self,
        row: Dict,
        home_standings: Optional[Dict] = None,
        away_standings: Optional[Dict] = None
    ) -> Dict[str, float]:
        """提取 V19.0 新增特征"""
        home_team = row.get('home_team', '')
        away_team = row.get('away_team', '')
        match_time = row.get('match_time')

        if isinstance(match_time, str):
            match_time = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
        elif match_time is None:
            match_time = datetime.now()
        else:
            if hasattr(match_time, 'tzinfo') and match_time.tzinfo is not None:
                match_time = match_time.replace(tzinfo=None)
            elif hasattr(match_time, 'to_pydatetime'):
                match_time = match_time.to_pydatetime()
                if match_time.tzinfo is not None:
                    match_time = match_time.replace(tzinfo=None)

        if home_standings is not None:
            home_points = home_standings.get('points', np.nan)
            home_position = home_standings.get('position', np.nan)
        else:
            home_points = np.nan
            home_position = np.nan

        if away_standings is not None:
            away_points = away_standings.get('points', np.nan)
            away_position = away_standings.get('position', np.nan)
        else:
            away_points = np.nan
            away_position = np.nan

        season_end = datetime(2024, 5, 25)
        games_remaining = max(0, (season_end - match_time).days // 7)
        relegation_zone_points = 30.0

        v19_features = self.feature_extractor.extract_features(
            home_team=home_team,
            away_team=away_team,
            match_date=match_time,
            season="23/24",
            home_points=home_points,
            away_points=away_points,
            relegation_zone_points=relegation_zone_points,
            games_remaining=games_remaining,
        )

        result = {}
        for k, v in v19_features.items():
            if isinstance(v, (int, float)):
                result[k] = v
            elif v is None:
                result[k] = np.nan

        return result

    def compute_feature_importance(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_cols: List[str]
    ) -> pd.DataFrame:
        """
        计算特征重要性

        返回按重要性排序的特征 DataFrame
        """
        logger.info("计算特征重要性...")

        # 使用强正则化参数训练临时模型
        temp_model = xgb.XGBClassifier(**self.HARDENED_PARAMS)
        temp_model.fit(X, y)

        # 获取特征重要性
        importance = temp_model.feature_importances_

        # 创建排序的 DataFrame
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'importance': importance
        }).sort_values('importance', ascending=False)

        logger.info(f"\n特征重要性 Top 20:")
        for i, row in importance_df.head(20).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        logger.info(f"\n特征重要性 Bottom 10:")
        for i, row in importance_df.tail(10).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        return importance_df

    def filter_features(
        self,
        importance_df: pd.DataFrame,
        feature_df: pd.DataFrame
    ) -> Tuple[List[str], List[str]]:
        """
        过滤特征：保留高重要性特征

        返回: (保留的特征列表, 移除的特征列表)
        """
        logger.info(f"\n特征过滤：保留 Top {self.TOP_FEATURES_TO_KEEP} 个特征")

        top_features = importance_df.head(self.TOP_FEATURES_TO_KEEP)['feature'].tolist()
        removed_features = importance_df.iloc[self.TOP_FEATURES_TO_KEEP:]['feature'].tolist()

        logger.info(f"保留特征数: {len(top_features)}")
        logger.info(f"移除特征数: {len(removed_features)}")
        logger.info(f"移除的特征: {removed_features}")

        self.removed_features = removed_features

        return top_features, removed_features

    def run_timeseries_cv(
        self,
        feature_df: pd.DataFrame,
        feature_cols: List[str]
    ) -> Tuple[List[Dict[str, float]], float, float]:
        """
        执行 TimeSeriesSplit 5折交叉验证

        返回: (每折结果, 平均ROI, ROI标准差)
        """
        logger.info("\n" + "="*80)
        logger.info("执行 TimeSeriesSplit 5折交叉验证")
        logger.info("="*80)

        exclude_cols = ['match_id', 'home_team', 'away_team', 'match_time', 'result']
        valid_features = [f for f in feature_cols if f in feature_df.columns]

        X = feature_df[valid_features].values
        y = feature_df['result'].values

        # TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=self.N_SPLITS)

        fold_results = []
        rois = []

        for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
            logger.info(f"\n--- Fold {fold_idx} ---")
            logger.info(f"训练集: {len(train_idx)} 场, 测试集: {len(test_idx)} 场")

            X_train = X[train_idx]
            y_train = y[train_idx]
            X_test = X[test_idx]
            y_test = y[test_idx]

            # 标准化
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # 训练模型
            model = xgb.XGBClassifier(**self.HARDENED_PARAMS)
            model.fit(X_train_scaled, y_train)

            # 预测
            train_pred = model.predict(X_train_scaled)
            test_pred = model.predict(X_test_scaled)

            train_acc = accuracy_score(y_train, train_pred)
            test_acc = accuracy_score(y_test, test_pred)

            # 投注回测
            test_proba = model.predict_proba(X_test_scaled)
            roi = self._calculate_roi(test_proba, y_test)

            fold_result = {
                'fold': fold_idx,
                'train_size': len(train_idx),
                'test_size': len(test_idx),
                'train_accuracy': train_acc,
                'test_accuracy': test_acc,
                'roi': roi,
            }

            fold_results.append(fold_result)
            rois.append(roi)

            logger.info(f"训练集准确率: {train_acc:.2%}")
            logger.info(f"测试集准确率: {test_acc:.2%}")
            logger.info(f"测试集 ROI: {roi:.2f}%")

        # 统计汇总
        avg_roi = np.mean(rois)
        std_roi = np.std(rois)
        min_roi = np.min(rois)
        max_roi = np.max(rois)
        avg_acc = np.mean([r['test_accuracy'] for r in fold_results])

        logger.info(f"\n=== 5折交叉验证汇总 ===")
        logger.info(f"平均 ROI: {avg_roi:.2f}%")
        logger.info(f"ROI 标准差: {std_roi:.2f}%")
        logger.info(f"最小/最大 ROI: {min_roi:.2f}% / {max_roi:.2f}%")
        logger.info(f"平均测试集准确率: {avg_acc:.2%}")

        # 验证标准
        if avg_roi > 10 and std_roi < 25:
            logger.info("✅ 交叉验证通过：平均 ROI > 10%，波动可控")
        else:
            logger.warning(f"⚠️ 交叉验证未达标：平均 ROI = {avg_roi:.2f}%, 标准差 = {std_roi:.2f}%")

        return fold_results, avg_roi, std_roi

    def _calculate_roi(self, probabilities: np.ndarray, y_true: np.ndarray) -> float:
        """计算 ROI"""
        capital = 10000.0
        min_edge = 0.01

        for i in range(len(probabilities)):
            prob = probabilities[i]
            actual = y_true[i]

            pred_class = np.argmax(prob)
            pred_prob = prob[pred_class]

            # 🚨 物理隔离: 使用真实市场价格
            try:
                market_odds = self._get_real_market_odds(test_df.iloc[i])
            except ValueError:
                continue
            fair_prob = 1 / market_odds[pred_class]
            edge = pred_prob - fair_prob

            if edge < min_edge:
                continue

            odds = market_odds[pred_class]
            kelly_f = ((odds - 1) * pred_prob - (1 - pred_prob)) / (odds - 1)
            bet_amount = capital * max(0, kelly_f * 0.25)
            bet_amount = min(bet_amount, capital * 0.02)

            if bet_amount <= 0:
                continue

            if pred_class == actual:
                winnings = bet_amount * (odds - 1)
                capital += winnings
            else:
                capital -= bet_amount

        roi = (capital - 10000) / 10000 * 100
        return roi

    # =============================================================
    # 🚨 物理隔离重构 - 已移除模拟定价逻辑 (2024-12-23)
    # 原代码使用模型概率反推赔率，导致因果逻辑错误和数据泄露
    # 新代码强制使用数据库中的真实市场价格 (real_price_h/d/a)
    # =============================================================
    def _get_real_market_odds(self, match_row: Dict) -> List[float]:
        """
        从数据库获取真实市场价格

        Args:
            match_row: 包含 real_price_h/d/a 的比赛数据

        Returns:
            [主胜赔率, 平局赔率, 客胜赔率]
        """
        h = match_row.get('real_price_h')
        d = match_row.get('real_price_d')
        a = match_row.get('real_price_a')

        # 验证赔率完整性
        if h is None or d is None or a is None:
            raise ValueError(f"缺少真实市场价格数据: h={h}, d={d}, a={a}")

        # 验证赔率合理性
        if not all(x > 1.0 for x in [h, d, a]):
            raise ValueError(f"赔率数据不合理: h={h}, d={d}, a={a}")

        return [float(h), float(d), float(a)]

    def train_final_model(
        self,
        feature_df: pd.DataFrame,
        feature_cols: List[str],
        train_size: int = 650,
        test_size: int = 110
    ) -> HardenedMetrics:
        """
        训练最终生产模型

        使用前 650 场训练，后 110 场测试
        """
        logger.info("\n" + "="*80)
        logger.info("训练 V19.3 硬化生产模型")
        logger.info("="*80)

        exclude_cols = ['match_id', 'home_team', 'away_team', 'match_time', 'result']
        valid_features = [f for f in feature_cols if f in feature_df.columns]

        # 按时间排序
        feature_df = feature_df.sort_values(['match_time', 'match_id'])

        # 分割数据
        train_df = feature_df.iloc[:train_size]
        test_df = feature_df.iloc[train_size:]

        X_train = train_df[valid_features].values
        y_train = train_df['result'].values
        X_test = test_df[valid_features].values
        y_test = test_df['result'].values

        logger.info(f"训练集: {len(X_train)} 场")
        logger.info(f"测试集: {len(X_test)} 场")

        # 标准化
        self.scaler.fit(X_train)
        X_train_scaled = self.scaler.transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # 训练模型
        logger.info(f"训练参数: {self.HARDENED_PARAMS}")
        model = xgb.XGBClassifier(**self.HARDENED_PARAMS)
        model.fit(X_train_scaled, y_train)

        # 评估
        train_pred = model.predict(X_train_scaled)
        test_pred = model.predict(X_test_scaled)
        test_proba = model.predict_proba(X_test_scaled)

        train_acc = accuracy_score(y_train, train_pred)
        test_acc = accuracy_score(y_test, test_pred)

        # 计算 Brier Score
        brier = brier_score_loss(
            pd.get_dummies(y_test).values,
            test_proba,
            sample_weight=None
        )

        # 投注回测
        test_roi = self._calculate_roi(test_proba, y_test)

        logger.info(f"\n最终模型性能:")
        logger.info(f"训练集准确率: {train_acc:.2%}")
        logger.info(f"测试集准确率: {test_acc:.2%}")
        logger.info(f"测试集 ROI: {test_roi:.2f}%")
        logger.info(f"Brier Score: {brier:.4f}")

        # 保存模型
        self._save_model(model, valid_features)

        return HardenedMetrics(
            version="V19.3_Hardened",
            timestamp=datetime.now().isoformat(),
            model_params=self.HARDENED_PARAMS,
            total_features=len(valid_features),
            removed_features=self.removed_features,
            remaining_features=valid_features,
            cv_fold_results=[],
            cv_avg_roi=0,
            cv_std_roi=0,
            cv_min_roi=0,
            cv_max_roi=0,
            cv_avg_accuracy=0,
            final_train_accuracy=train_acc,
            final_test_accuracy=test_acc,
            final_test_roi=test_roi,
            final_brier_score=brier,
            can_deploy=(test_roi > 10),
            deploy_reason="测试集 ROI > 10%" if test_roi > 10 else "测试集 ROI 不达标"
        )

    def _save_model(self, model: xgb.XGBClassifier, feature_cols: List[str]):
        """保存生产模型（完整 Scaler 持久化）"""
        model_dir = Path("src/production_models")
        model_dir.mkdir(exist_ok=True)

        # H-03 修复：完整保存 Scaler 对象
        model_path = model_dir / "v19.3_hardened_model.pkl"
        joblib.dump({
            'model': model,
            'scaler': self.scaler,  # ✅ 完整持久化
            'feature_columns': feature_cols,
            'removed_features': self.removed_features,
            'version': 'V19.3_Hardened',
        }, model_path)

        # 保存元数据
        metadata = {
            'version': 'V19.3_Hardened',
            'creation_date': datetime.now().isoformat(),
            'feature_count': len(feature_cols),
            'removed_features': self.removed_features,
            'feature_columns': feature_cols,
            'model_params': self.HARDENED_PARAMS,
            'scaler_mean': self.scaler.mean_.tolist(),
            'scaler_scale': self.scaler.scale_.tolist(),
            'scaler_n_features': int(self.scaler.n_features_in_),
            'description': 'V19.3 Hardened - Strong Regularization + Feature Selection',
        }

        metadata_path = model_dir / "v19.3_hardened_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"\n✅ 模型已保存: {model_path}")
        logger.info(f"✅ 元数据已保存: {metadata_path}")

    def run_full_pipeline(self) -> HardenedMetrics:
        """运行完整硬化流水线"""
        logger.info("="*80)
        logger.info("V19.3 硬化版本流水线启动")
        logger.info("="*80)

        # 1. 加载数据
        df = self.load_data(limit=760)
        if df.empty:
            raise ValueError("数据加载失败")

        # 2. 提取特征
        feature_df = self.extract_features(df)
        if feature_df.empty:
            raise ValueError("特征提取失败")

        # 3. 初始特征选择
        exclude_cols = ['match_id', 'home_team', 'away_team', 'match_time', 'result']
        initial_features = [c for c in feature_df.columns if c not in exclude_cols]

        logger.info(f"\n初始特征数: {len(initial_features)}")

        # 4. 计算特征重要性（使用部分数据加速）
        sample_size = min(500, len(feature_df))
        sample_df = feature_df.iloc[:sample_size]

        X_sample = sample_df[initial_features].fillna(0).values
        y_sample = sample_df['result'].values

        importance_df = self.compute_feature_importance(X_sample, y_sample, initial_features)

        # 5. 过滤特征
        top_features, removed_features = self.filter_features(importance_df, feature_df)

        # 6. TimeSeriesSplit 5折验证
        fold_results, avg_roi, std_roi = self.run_timeseries_cv(feature_df, top_features)

        # 7. 训练最终模型
        final_metrics = self.train_final_model(feature_df, top_features)

        # 更新交叉验证结果
        final_metrics.cv_fold_results = fold_results
        final_metrics.cv_avg_roi = avg_roi
        final_metrics.cv_std_roi = std_roi
        final_metrics.cv_min_roi = min([r['roi'] for r in fold_results])
        final_metrics.cv_max_roi = max([r['roi'] for r in fold_results])
        final_metrics.cv_avg_accuracy = np.mean([r['test_accuracy'] for r in fold_results])

        # 部署决策
        final_metrics.can_deploy = (avg_roi > 10 and std_roi < 25)
        if final_metrics.can_deploy:
            final_metrics.deploy_reason = f"5折平均 ROI={avg_roi:.2f}%, 标准差={std_roi:.2f}%, 满足部署条件"
        else:
            final_metrics.deploy_reason = f"5折平均 ROI={avg_roi:.2f}%, 标准差={std_roi:.2f}%, 不满足部署条件"

        return final_metrics


def main():
    """主函数"""
    print("V19.3 硬化版本流水线")
    print("=" * 80)
    print("基于 V19.2 审计报告的重铸版本")
    print("- 强正则化配置")
    print("- TimeSeriesSplit 5折验证")
    print("- 特征重要性过滤")
    print("- 完整 Scaler 持久化")
    print("=" * 80)

    pipeline = V19_3HardenedPipeline()

    try:
        metrics = pipeline.run_full_pipeline()

        # 显示结果
        print("\n" + "=" * 80)
        print("V19.3 硬化版本 - 性能报告")
        print("=" * 80)

        print(f"\n【特征信息】")
        print(f"总特征数: {metrics.total_features}")
        print(f"移除特征: {len(metrics.removed_features)}")
        print(f"保留特征: {len(metrics.remaining_features)}")

        print(f"\n【5折交叉验证】")
        print(f"平均 ROI: {metrics.cv_avg_roi:.2f}%")
        print(f"ROI 标准差: {metrics.cv_std_roi:.2f}%")
        print(f"最小/最大 ROI: {metrics.cv_min_roi:.2f}% / {metrics.cv_max_roi:.2f}%")
        print(f"平均测试集准确率: {metrics.cv_avg_accuracy:.2%}")

        print(f"\n各折叠详情:")
        for fold in metrics.cv_fold_results:
            print(f"  Fold {fold['fold']}: Train={fold['train_accuracy']:.2%}, Test={fold['test_accuracy']:.2%}, ROI={fold['roi']:.2f}%")

        print(f"\n【最终模型性能】")
        print(f"训练集准确率: {metrics.final_train_accuracy:.2%}")
        print(f"测试集准确率: {metrics.final_test_accuracy:.2%}")
        print(f"测试集 ROI: {metrics.final_test_roi:.2f}%")
        print(f"Brier Score: {metrics.final_brier_score:.4f}")

        print(f"\n【部署决策】")
        print(f"可部署: {'✅ 是' if metrics.can_deploy else '❌ 否'}")
        print(f"原因: {metrics.deploy_reason}")

        print("\n" + "=" * 80)

        # 生成对比报告
        generate_comparison_report(metrics)

    except Exception as e:
        logger.error(f"流水线执行失败: {e}")
        import traceback
        traceback.print_exc()


def generate_comparison_report(metrics: HardenedMetrics):
    """生成 V19.2 vs V19.3 对比报告"""
    report = {
        'comparison_date': datetime.now().isoformat(),
        'v19_2_audit': {
            'avg_roi': -33.07,
            'roi_std': 12.02,
            'min_roi': -42.09,
            'max_roi': -12.47,
            'train_accuracy': 1.00,
            'test_accuracy': 0.62,
            'note': '审计版：时间序列交叉验证结果'
        },
        'v19_3_hardened': {
            'avg_roi': metrics.cv_avg_roi,
            'roi_std': metrics.cv_std_roi,
            'min_roi': metrics.cv_min_roi,
            'max_roi': metrics.cv_max_roi,
            'train_accuracy': metrics.final_train_accuracy,
            'test_accuracy': metrics.final_test_accuracy,
            'note': '硬化版：强正则化 + 特征过滤'
        },
        'improvement': {
            'roi_improvement': metrics.cv_avg_roi - (-33.07),
            'stability_improvement': 12.02 - metrics.cv_std_roi if metrics.cv_std_roi < 12.02 else -(metrics.cv_std_roi - 12.02),
        }
    }

    report_path = Path("docs/V19.2_vs_V19.3_COMPARISON.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ 对比报告已保存: {report_path}")

    # 显示对比
    print("\n" + "=" * 80)
    print("V19.2 (审计版) vs V19.3 (硬化版) 对比")
    print("=" * 80)
    print(f"\n{'指标':<20} {'V19.2':<15} {'V19.3':<15} {'改进':<15}")
    print("-" * 65)
    print(f"{'5折平均 ROI':<20} {report['v19_2_audit']['avg_roi']:<15.2f} {report['v19_3_hardened']['avg_roi']:<15.2f} {report['improvement']['roi_improvement']:<15.2f}")
    print(f"{'ROI 标准差':<20} {report['v19_2_audit']['roi_std']:<15.2f} {report['v19_3_hardened']['roi_std']:<15.2f} {report['improvement']['stability_improvement']:<15.2f}")
    print(f"{'训练集准确率':<20} {report['v19_2_audit']['train_accuracy']:<15.2%} {report['v19_3_hardened']['train_accuracy']:<15.2%} {'N/A':<15}")
    print("=" * 80)


if __name__ == "__main__":
    main()
