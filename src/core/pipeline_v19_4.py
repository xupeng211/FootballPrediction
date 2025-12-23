#!/usr/bin/env python3
"""
V19.4 训练流水线 - Draw Sensitivity + Weighted Loss
=====================================================

针对V19.3审计中发现的两个核心问题：
1. 平局识别率为0% -> 引入平局敏感度特征 + 加权损失函数
2. 绩效为-4.65% -> 引入执行阈值过滤机制

核心改进：
- 3个平局敏感度特征 (table_proximity, low_scoring_tendency, elo_diff_cluster)
- 多分类损失函数加权 (draw_class_weight=3.0)
- 48维特征 (45原V19.3特征 + 3新特征)

作者: V19.4量化策略团队
日期: 2025-12-23
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
from src.ml.features.draw_sensitivity_features import DrawSensitivityFeatureExtractor
from src.ml.features.standings_calculator import initialize_global_calculator, get_global_calculator
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class V19_4Metrics:
    """V19.4 性能指标"""
    accuracy: float
    f1_macro: float
    precision_macro: float
    recall_macro: float

    # 分类别指标
    home_win_accuracy: float
    draw_accuracy: float
    away_win_accuracy: float

    # 特征维度
    feature_count: int


class V19_4TrainingPipeline:
    """
    V19.4 训练流水线

    核心功能:
    1. 数据加载（从数据库读取比赛数据）
    2. 特征提取（V18 + V19 + V19.4 平局敏感度）
    3. 加权损失函数训练
    4. 模型评估和保存
    """

    # V19.4 平局类别权重配置
    DRAW_CLASS_WEIGHT = 3.0  # 平类类别权重（提高平局识别）

    # 模型参数
    MODEL_PARAMS = {
        'n_estimators': 200,
        'max_depth': 3,
        'learning_rate': 0.01,
        'min_child_weight': 5,
        'gamma': 0.5,
        'subsample': 0.7,
        'colsample_bytree': 0.7,
        'reg_alpha': 1.0,
        'reg_lambda': 2.0,
        'random_state': 42,
        'use_label_encoder': False,
        'eval_metric': 'mlogloss',
        'objective': 'multi:softprob',  # 多分类
        'num_class': 3  # H/D/A
    }

    def __init__(self, db_conn=None):
        """
        初始化 V19.4 训练流水线

        Args:
            db_conn: 数据库连接（可选）
        """
        self.db_conn = db_conn
        self.feature_extractor = V19AdvancedFeatureExtractor()
        self.draw_sensitivity_extractor = DrawSensitivityFeatureExtractor()

        # 模型组件
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = None

        logger.info("V19.4 训练流水线初始化完成（含平局敏感度特征 + 加权损失）")

    def load_data(self, limit: int = 760) -> pd.DataFrame:
        """
        从数据库加载数据

        Args:
            limit: 加载比赛数量

        Returns:
            pd.DataFrame: 完整数据集
        """
        logger.info(f"从数据库加载数据（目标: {limit} 场）...")

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

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
                m.result_score,
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

        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}")
            return pd.DataFrame()

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        提取 V19.4 完整特征（V18 + V19 + V19.4 平局敏感度）

        Args:
            df: 原始数据

        Returns:
            pd.DataFrame: 含完整特征的数据
        """
        logger.info("提取 V19.4 特征...")

        # 初始化积分榜计算器
        initialize_global_calculator(df)
        calculator = get_global_calculator()

        features_list = []

        for idx, row in df.iterrows():
            try:
                # 获取比赛时的真实积分榜数据
                home_team = row.get('home_team', '')
                away_team = row.get('away_team', '')

                home_standings = calculator.get_team_stats_at_match(idx, home_team)
                away_standings = calculator.get_team_stats_at_match(idx, away_team)

                # 1. 提取 V18.2 原始特征（26 维）
                v18_features = self._extract_v18_features(
                    row,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

                if v18_features is None:
                    continue

                # 2. 提取 V19.0 新增特征（13 维）
                v19_features = self._extract_v19_features(
                    row,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

                # 3. 提取 V19.4 平局敏感度特征（3 维）
                draw_features = self._extract_draw_sensitivity_features(
                    row,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

                # 4. 合并所有特征
                all_features = {**v18_features, **v19_features, **draw_features}
                all_features['match_id'] = row.get('id', idx)
                all_features['home_team'] = home_team
                all_features['away_team'] = away_team
                all_features['match_time'] = row.get('match_time', '')

                # 5. 联赛编码特征
                league_id = row.get('league_id', 47)
                league_features = self._encode_league(league_id)
                all_features.update(league_features)

                # 6. 提取标签
                home_score = row.get('home_score', 0)
                away_score = row.get('away_score', 0)

                if home_score > away_score:
                    all_features['result'] = 2  # Home
                elif home_score < away_score:
                    all_features['result'] = 0  # Away
                else:
                    all_features['result'] = 1  # Draw

                features_list.append(all_features)

            except Exception as e:
                logger.debug(f"特征提取失败 (行 {idx}): {e}")
                continue

        feature_df = pd.DataFrame(features_list)
        logger.info(f"✅ 特征提取完成: {len(feature_df)} 场比赛, {len(feature_df.columns) - 4} 个特征")

        return feature_df

    def _extract_v18_features(self, row: Dict, **kwargs) -> Optional[Dict[str, float]]:
        """提取 V18 滚动特征（支持 technical_features 格式）"""
        try:
            raw_data = row.get('raw_data', {})

            # 处理数据格式：如果是字符串则解析
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            # 首先尝试从 technical_features 获取数据（实际数据库格式）
            if 'technical_features' in raw_data:
                tech = raw_data['technical_features']
                # technical_features 中的数据是 home_xg, away_xg, home_corners 等
                home_xg = tech.get('home_xg', np.nan)
                away_xg = tech.get('away_xg', np.nan)
                home_corners = tech.get('home_corners', np.nan)
                away_corners = tech.get('away_corners', np.nan)

                # 对于没有 home/away 前缀的特征，使用 diff 和 total 计算
                # 例如: diff_shots, total_shots -> home_shots = (total + diff) / 2

                # 获取可用特征列表
                def safe_float(val):
                    try:
                        return float(val) if val is not None else np.nan
                    except (ValueError, TypeError):
                        return np.nan

                # 射正数据（shots_on_target）- 可能存在不同的键名
                home_shots_on_target = tech.get('home_shots_on_target', np.nan)
                away_shots_on_target = tech.get('away_shots_on_target', np.nan)

                # 控球率
                home_possession = tech.get('home_possession', np.nan)
                away_possession = tech.get('away_possession', np.nan)

                # 射门
                home_shots = tech.get('home_shots', np.nan)
                away_shots = tech.get('away_shots', np.nan)

                # 处理 diff/total 格式的特征
                if np.isnan(home_shots_on_target) and 'diff_shots_on_target' in tech and 'total_shots_on_target' in tech:
                    diff_sot = safe_float(tech.get('diff_shots_on_target'))
                    total_sot = safe_float(tech.get('total_shots_on_target'))
                    home_shots_on_target = (total_sot + diff_sot) / 2
                    away_shots_on_target = (total_sot - diff_sot) / 2

                if np.isnan(home_shots) and 'diff_shots' in tech and 'total_shots' in tech:
                    diff_shots = safe_float(tech.get('diff_shots'))
                    total_shots = safe_float(tech.get('total_shots'))
                    home_shots = (total_shots + diff_shots) / 2
                    away_shots = (total_shots - diff_shots) / 2

                if np.isnan(home_possession) and 'diff_possession' in tech and 'total_possession' in tech:
                    diff_poss = safe_float(tech.get('diff_possession'))
                    total_poss = safe_float(tech.get('total_possession'))
                    home_possession = (total_poss + diff_poss) / 2
                    away_possession = (total_poss - diff_poss) / 2

            # 备用方案：从 home_stats/away_stats 获取（兼容旧格式）
            elif 'home_stats' in raw_data and 'away_stats' in raw_data:
                home_stats = raw_data['home_stats']
                away_stats = raw_data['away_stats']

                def get_stat(stats_dict, key):
                    val = stats_dict.get(key, None)
                    if val is None:
                        return np.nan
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return np.nan

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
            else:
                return None

            # 获取积分榜数据
            home_standings = kwargs.get('home_standings')
            away_standings = kwargs.get('away_standings')

            if home_standings is not None:
                home_pos = safe_float(home_standings.get('position'))
                home_pts = safe_float(home_standings.get('points'))
                home_form_pts = safe_float(home_standings.get('form_points'))
            else:
                home_pos = home_pts = home_form_pts = np.nan

            if away_standings is not None:
                away_pos = safe_float(away_standings.get('position'))
                away_pts = safe_float(away_standings.get('points'))
                away_form_pts = safe_float(away_standings.get('form_points'))
            else:
                away_pos = away_pts = away_form_pts = np.nan

            pos_diff = home_pos - away_pos if not np.isnan(home_pos) and not np.isnan(away_pos) else np.nan
            pts_diff = home_pts - away_pts if not np.isnan(home_pts) and not np.isnan(away_pts) else np.nan

            def safe_float(val):
                try:
                    return float(val) if val is not None and not np.isnan(val) else np.nan
                except (ValueError, TypeError):
                    return np.nan

            return {
                'home_rolling_xg': safe_float(home_xg),
                'away_rolling_xg': safe_float(away_xg),
                'home_rolling_shots_on_target': safe_float(home_shots_on_target),
                'away_rolling_shots_on_target': safe_float(away_shots_on_target),
                'home_rolling_possession': safe_float(home_possession),
                'away_rolling_possession': safe_float(away_possession),
                'home_rolling_shots': safe_float(home_shots),
                'away_rolling_shots': safe_float(away_shots),
                'home_rolling_corners': safe_float(home_corners),
                'away_rolling_corners': safe_float(away_corners),
                'home_table_position': home_pos,
                'away_table_position': away_pos,
                'table_position_diff': pos_diff,
                'home_points': home_pts,
                'away_points': away_pts,
                'points_diff': pts_diff,
                'home_recent_form_points': home_form_pts,
                'away_recent_form_points': away_form_pts,
            }

        except Exception as e:
            logger.debug(f"V18 特征提取失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _extract_v19_features(self, row: Dict, **kwargs) -> Dict[str, float]:
        """提取 V19 高级特征"""
        home_team = row.get('home_team', '')
        away_team = row.get('away_team', '')

        v19_features = self.feature_extractor.extract_features(
            home_team=home_team,
            away_team=away_team,
            match_date=datetime.now(),
            season="23/24",
            home_points=kwargs.get('home_standings', {}).get('points', np.nan) if kwargs.get('home_standings') else np.nan,
            away_points=kwargs.get('away_standings', {}).get('points', np.nan) if kwargs.get('away_standings') else np.nan,
            relegation_zone_points=30.0,
            games_remaining=5,
        )

        result = {}
        for k, v in v19_features.items():
            if isinstance(v, (int, float)):
                result[k] = v
            elif v is None:
                result[k] = np.nan

        return result

    def _extract_draw_sensitivity_features(self, row: Dict, **kwargs) -> Dict[str, float]:
        """提取 V19.4 平局敏感度特征（支持 technical_features 格式）"""
        try:
            raw_data = row.get('raw_data', {})
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            # 处理 technical_features 格式
            if 'technical_features' in raw_data:
                tech = raw_data['technical_features']
                home_pos = np.nan
                away_pos = np.nan
                home_xg = tech.get('home_xg', np.nan)
                away_xg = tech.get('away_xg', np.nan)
                home_shots = tech.get('home_shots_on_target', np.nan)
                away_shots = tech.get('away_shots_on_target', np.nan)

                # 处理 diff/total 格式
                def safe_float(val):
                    try:
                        return float(val) if val is not None else np.nan
                    except (ValueError, TypeError):
                        return np.nan

                if np.isnan(home_shots) and 'diff_shots_on_target' in tech and 'total_shots_on_target' in tech:
                    diff_sot = safe_float(tech.get('diff_shots_on_target'))
                    total_sot = safe_float(tech.get('total_shots_on_target'))
                    home_shots = (total_sot + diff_sot) / 2
                    away_shots = (total_sot - diff_sot) / 2

                # 获取积分榜位置
                home_standings = kwargs.get('home_standings')
                away_standings = kwargs.get('away_standings')
                if home_standings:
                    home_pos = safe_float(home_standings.get('position'))
                if away_standings:
                    away_pos = safe_float(away_standings.get('position'))

            # 备用方案：home_stats/away_stats 格式
            elif 'home_stats' in raw_data and 'away_stats' in raw_data:
                home_stats = raw_data['home_stats']
                away_stats = raw_data['away_stats']

                def get_stat(stats_dict, key):
                    val = stats_dict.get(key, None)
                    if val is None:
                        return np.nan
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return np.nan

                home_standings = kwargs.get('home_standings')
                away_standings = kwargs.get('away_standings')
                home_pos = home_standings.get('position', np.nan) if home_standings else np.nan
                away_pos = away_standings.get('position', np.nan) if away_standings else np.nan
                home_xg = get_stat(home_stats, 'expected_goals')
                away_xg = get_stat(away_stats, 'expected_goals')
                home_shots = get_stat(home_stats, 'shots_on_target')
                away_shots = get_stat(away_stats, 'shots_on_target')
            else:
                return {
                    'table_proximity': np.nan,
                    'low_scoring_tendency': np.nan,
                    'elo_diff_cluster': 0.0
                }

            # 默认 ELO 值（实际应从 V19 特征中获取）
            home_elo = 1500.0
            away_elo = 1500.0

            temp_df = pd.DataFrame({
                'home_table_position': [home_pos],
                'away_table_position': [away_pos],
                'home_rolling_xg': [home_xg],
                'away_rolling_xg': [away_xg],
                'home_rolling_shots_on_target': [home_shots],
                'away_rolling_shots_on_target': [away_shots],
                'home_elo_rating': [home_elo],
                'away_elo_rating': [away_elo]
            })

            result_df = self.draw_sensitivity_extractor.extract(temp_df)

            if len(result_df) > 0:
                return {
                    'table_proximity': result_df.iloc[0]['table_proximity'],
                    'low_scoring_tendency': result_df.iloc[0]['low_scoring_tendency'],
                    'elo_diff_cluster': result_df.iloc[0]['elo_diff_cluster']
                }
            else:
                return {
                    'table_proximity': np.nan,
                    'low_scoring_tendency': np.nan,
                    'elo_diff_cluster': 0.0
                }

        except Exception as e:
            logger.debug(f"平局敏感度特征提取失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                'table_proximity': np.nan,
                'low_scoring_tendency': np.nan,
                'elo_diff_cluster': 0.0
            }

    def _encode_league(self, league_id: int) -> Dict[str, float]:
        """联赛编码"""
        return {
            'league_epl': 1.0 if league_id == 47 else 0.0,
            'league_championship': 1.0 if league_id == 48 else 0.0,
        }

    def train_model(
        self,
        feature_df: pd.DataFrame,
        train_size: int = 600,
        test_size: int = 160,
        apply_draw_weight: bool = True
    ) -> V19_4Metrics:
        """
        训练 V19.4 模型（带加权损失函数）

        Args:
            feature_df: 特征数据框
            train_size: 训练集大小
            test_size: 测试集大小
            apply_draw_weight: 是否应用平局类别权重

        Returns:
            V19_4Metrics: 性能指标
        """
        logger.info("开始训练 V19.4 模型...")

        # 准备数据
        exclude_cols = ['match_id', 'home_team', 'away_team', 'match_time', 'result', 'id']
        self.feature_columns = [c for c in feature_df.columns if c not in exclude_cols]

        X = feature_df[self.feature_columns].values
        y = feature_df['result'].values

        # 处理 NaN 值
        X = np.nan_to_num(X, nan=0.0)

        # 划分数据集（时间序列分割）
        X_train = X[:train_size]
        y_train = y[:train_size]
        X_test = X[train_size:train_size + test_size]
        y_test = y[train_size:train_size + test_size]

        logger.info(f"训练集: {len(X_train)} 场, 测试集: {len(X_test)} 场")

        # 标准化特征
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # 计算类别权重
        if apply_draw_weight:
            # 计算样本权重（提高平类权重）
            sample_weights = np.ones(len(y_train))
            for i, label in enumerate(y_train):
                if label == 1:  # Draw
                    sample_weights[i] = self.DRAW_CLASS_WEIGHT

            logger.info(f"应用平局类别权重: {self.DRAW_CLASS_WEIGHT}x")
        else:
            sample_weights = None

        # 训练模型
        self.model = xgb.XGBClassifier(**self.MODEL_PARAMS)

        self.model.fit(
            X_train_scaled,
            y_train,
            sample_weight=sample_weights,
            verbose=False
        )

        # 预测和评估
        y_pred = self.model.predict(X_test_scaled)

        # 计算指标
        accuracy = accuracy_score(y_test, y_pred)

        # 分类别准确率
        home_mask = y_test == 2
        draw_mask = y_test == 1
        away_mask = y_test == 0

        home_acc = accuracy_score(y_test[home_mask], y_pred[home_mask]) if home_mask.sum() > 0 else 0
        draw_acc = accuracy_score(y_test[draw_mask], y_pred[draw_mask]) if draw_mask.sum() > 0 else 0
        away_acc = accuracy_score(y_test[away_mask], y_pred[away_mask]) if away_mask.sum() > 0 else 0

        # 分类报告
        report = classification_report(
            y_test,
            y_pred,
            target_names=['Away', 'Draw', 'Home'],
            output_dict=True,
            zero_division=0
        )

        metrics = V19_4Metrics(
            accuracy=accuracy,
            f1_macro=report['macro avg']['f1-score'],
            precision_macro=report['macro avg']['precision'],
            recall_macro=report['macro avg']['recall'],
            home_win_accuracy=home_acc,
            draw_accuracy=draw_acc,
            away_win_accuracy=away_acc,
            feature_count=len(self.feature_columns)
        )

        logger.info("训练完成:")
        logger.info(f"  整体准确率: {accuracy * 100:.2f}%")
        logger.info(f"  主胜准确率: {home_acc * 100:.2f}%")
        logger.info(f"  平局准确率: {draw_acc * 100:.2f}%")
        logger.info(f"  客胜准确率: {away_acc * 100:.2f}%")
        logger.info(f"  特征维度: {metrics.feature_count}")

        return metrics

    def save_model(self, output_dir: str = None):
        """保存模型和元数据"""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "production_models"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True)

        # 保存模型
        model_path = output_dir / "v19.4_draw_sensitivity_model.pkl"
        joblib.dump(self.model, model_path)
        logger.info(f"✅ 模型已保存: {model_path}")

        # 保存标准化器
        scaler_path = output_dir / "v19.4_draw_sensitivity_scaler.pkl"
        joblib.dump(self.scaler, scaler_path)

        # 保存元数据
        metadata = {
            "version": "V19.4_Draw_Sensitivity",
            "creation_date": datetime.now().isoformat(),
            "feature_count": len(self.feature_columns),
            "feature_columns": self.feature_columns,
            "model_params": self.MODEL_PARAMS,
            "draw_class_weight": self.DRAW_CLASS_WEIGHT,
            "scaler_mean": self.scaler.mean_.tolist(),
            "scaler_scale": self.scaler.scale_.tolist(),
            "scaler_n_features": self.scaler.n_features_in_,
            "description": "V19.4 Draw Sensitivity + Weighted Loss - Address 0% Draw ID Rate"
        }

        metadata_path = output_dir / "v19.4_draw_sensitivity_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✅ 元数据已保存: {metadata_path}")


def main():
    """主训练流程"""
    logger.info("=" * 70)
    logger.info("V19.4 训练流水线 - Draw Sensitivity + Weighted Loss")
    logger.info("=" * 70)

    pipeline = V19_4TrainingPipeline()

    # 1. 加载数据
    df = pipeline.load_data(limit=760)
    if df.empty:
        logger.error("数据加载失败，退出训练")
        return

    # 2. 提取特征
    feature_df = pipeline.extract_features(df)
    if feature_df.empty:
        logger.error("特征提取失败，退出训练")
        return

    # 3. 训练模型
    metrics = pipeline.train_model(feature_df, train_size=600, test_size=160)

    # 4. 保存模型
    pipeline.save_model()

    logger.info("=" * 70)
    logger.info("✅ V19.4 模型训练完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
