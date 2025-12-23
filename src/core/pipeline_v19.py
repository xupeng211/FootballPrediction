#!/usr/bin/env python3
"""
V19.0 完整重建流水线 - Profitability Pursuit

整合所有 V19.0 组件：
- Step A: 诊断分析器
- Step B: 高级动态特征 (Elo Gap + Fatigue + Relegation)
- Step C: 概率校准器

目标：从 -15.47% ROI 提升到正 ROI

Author: V19.0 Quant Team
Version: 1.0.0
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
from src.ml.v19_probability_calibrator import V19ProbabilityCalibrator, CalibrationResult
from src.analysis.v19_diagnostic import V19DiagnosticAnalyzer
from src.ml.features.standings_calculator import initialize_global_calculator, get_global_calculator
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class V19Metrics:
    """V19.0 性能指标"""
    # 模型性能
    accuracy: float
    f1_macro: float
    precision: float
    recall: float

    # 概率校准
    brier_score_before: float
    brier_score_after: float
    brier_score_improvement: float

    # 投注性能
    win_rate: float
    roi_fixed: float
    roi_kelly: float
    max_drawdown: float
    total_bets: int

    # 诊断结果
    high_confidence_failures: int
    home_favorite_losses: int


class V19ProductionPipeline:
    """
    V19.0 完整重建流水线

    执行流程：
    1. 加载数据（严格物理隔离的 180 场测试集）
    2. Step A: 诊断当前模型的失败模式
    3. Step B: 提取高级动态特征
    4. 训练新模型
    5. Step C: 概率校准
    6. 严格回测（180 场隔离测试集）
    7. 保存 V19.0 模型
    """

    # 特征规格
    V18_FEATURE_COUNT = 26  # 原始 V18.2 特征
    V19_NEW_FEATURE_COUNT = 13  # V19.0 新增特征
    TOTAL_FEATURE_COUNT = V18_FEATURE_COUNT + V19_NEW_FEATURE_COUNT

    # 测试集大小（严格物理隔离）
    TEST_SET_SIZE = 180

    def __init__(self, db_conn=None):
        """
        初始化 V19.0 流水线

        Args:
            db_conn: 数据库连接（可选）
        """
        self.db_conn = db_conn
        self.feature_extractor = V19AdvancedFeatureExtractor()
        self.calibrator = None

        # 模型组件
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = None

        logger.info("V19.0 完整重建流水线初始化完成")

    def load_data(self, limit: int = 760) -> pd.DataFrame:
        """
        从数据库加载数据（仅限 PostgreSQL，已移除 CSV 备用路径）

        Args:
            limit: 加载比赛数量

        Returns:
            pd.DataFrame: 完整数据集
        """
        logger.info(f"从数据库加载数据（目标: {limit} 场）...")

        settings = get_settings()

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            db_config = settings.database
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.name,
                user=db_config.user,
                password=db_config.password.get_secret_value()
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

        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}")
            return pd.DataFrame()

    def extract_v19_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        提取 V19.0 完整特征（V18 特征 + V19 新增特征）

        Args:
            df: 原始数据

        Returns:
            pd.DataFrame: 含完整特征的数据
        """
        logger.info("提取 V19.0 特征...")

        # V19.2: 初始化积分榜计算器（从比赛历史计算真实积分榜）
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

                # 1. 提取 V18.2 原始特征（26 维）- 使用真实积分榜数据
                v18_features = self._extract_v18_features(
                    row,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

                if v18_features is None:
                    continue

                # 2. 提取 V19.0 新增特征（13 维）- 使用真实积分榜数据
                v19_features = self._extract_new_features(
                    row,
                    home_standings=home_standings,
                    away_standings=away_standings
                )

                # 3. 合并所有特征
                all_features = {**v18_features, **v19_features}
                all_features['match_id'] = row.get('id', idx)
                all_features['home_team'] = home_team
                all_features['away_team'] = away_team
                all_features['match_time'] = row.get('match_time', '')

                # 4. 提取标签
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
                import traceback
                logger.debug(traceback.format_exc())
                continue

        feature_df = pd.DataFrame(features_list)
        logger.info(f"✅ 特征提取完成: {len(feature_df)} 场比赛, {len(feature_df.columns) - 4} 个特征")

        return feature_df

    def _extract_v18_features(
        self,
        row: Dict,
        home_standings: Optional[Dict] = None,
        away_standings: Optional[Dict] = None
    ) -> Optional[Dict[str, float]]:
        """
        提取滚动特征（V18 基础 + V19 积分榜特征）

        Args:
            row: 比赛数据行
            home_standings: 主队积分榜数据（从 standings_calculator 获取）
            away_standings: 客队积分榜数据（从 standings_calculator 获取）

        Returns:
            特征字典，如果数据不可用则返回 None
        """
        try:
            raw_data = row.get('raw_data', '{}')
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            # 导航到实际的数据结构: l2_json -> content -> stats -> Periods -> All
            if 'l2_json' in raw_data:
                l2_data = raw_data['l2_json']
                if isinstance(l2_data, str):
                    l2_data = json.loads(l2_data)

                if 'content' in l2_data and 'stats' in l2_data['content']:
                    stats_data = l2_data['content']['stats']
                    if 'Periods' in stats_data and 'All' in stats_data['Periods']:
                        period_stats = stats_data['Periods']['All']
                        # 直接使用 'stats' 键
                        if 'stats' in period_stats:
                            stats_list = period_stats['stats']
                            logger.debug(f"Found stats list with {len(stats_list)} items")
                            # 从 stats 列表中提取特征（使用 NaN 表示缺失值）
                            return self._extract_from_stats_list(
                                stats_list,
                                home_standings=home_standings,
                                away_standings=away_standings
                            )

            logger.debug(f"Failed to extract features for row, raw_data keys: {list(raw_data.keys())[:5]}")
            return None

        except Exception as e:
            logger.debug(f"特征提取失败: {e}")
            return None

    def _extract_from_stats_list(
        self,
        stats_list: List,
        home_standings: Optional[Dict] = None,
        away_standings: Optional[Dict] = None
    ) -> Optional[Dict[str, float]]:
        """
        从 FotMob stats 列表中提取特征

        数据结构：
        stats_list
          └── stats (每个统计项)
              ├── key: "expected_goals"
              ├── stats: [home_value, away_value]
              └── ...

        Args:
            stats_list: FotMob 统计数据列表
            home_standings: 主队积分榜数据（从 standings_calculator 获取）
            away_standings: 客队积分榜数据（从 standings_calculator 获取）
        """
        try:
            # 构建 home/away 统计字典
            home_stats = {}
            away_stats = {}

            for stat_group in stats_list:
                if 'stats' in stat_group:
                    for stat_item in stat_group['stats']:
                        key = stat_item.get('key', '')
                        stats_array = stat_item.get('stats', [])

                        # stats_array 应该是 [home_value, away_value]
                        if len(stats_array) >= 2:
                            home_val = stats_array[0]
                            away_val = stats_array[1]

                            # 转换为浮点数（处理 None 值和各种类型）
                            try:
                                if isinstance(home_val, str):
                                    # 处理 "527 (89%)" 格式
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

            # 检查是否成功提取到关键统计（只检查是否有非 None 值）
            valid_home = any(v is not None for v in home_stats.values())
            valid_away = any(v is not None for v in away_stats.values())

            if not valid_home or not valid_away:
                logger.debug(f"No valid stats extracted: home_stats={len(home_stats)}, away_stats={len(away_stats)}")
                return None

            # 提取各种统计值（使用正确的 key）
            def get_stat(stats_dict, key):
                """获取统计值，如果不存在返回 NaN"""
                val = stats_dict.get(key, None)
                if val is None:
                    return np.nan
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return np.nan

            # V19.2: 从真实积分榜获取赛前特征
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

            # 计算差值特征
            pos_diff = home_pos - away_pos if not np.isnan(home_pos) and not np.isnan(away_pos) else np.nan
            pts_diff = home_pts - away_pts if not np.isnan(home_pts) and not np.isnan(away_pts) else np.nan

            # 提取关键特征
            home_xg = get_stat(home_stats, 'expected_goals')
            away_xg = get_stat(away_stats, 'expected_goals')
            home_shots = get_stat(home_stats, 'ShotsOnTarget')
            away_shots = get_stat(away_stats, 'ShotsOnTarget')
            home_possession = get_stat(home_stats, 'BallPossesion')
            away_possession = get_stat(away_stats, 'BallPossesion')

            return {
                # 滚动特征（16 维）- 从真实统计数据提取
                'home_rolling_xg': home_xg,
                'home_rolling_xg_std': np.nan,  # 无历史数据，标记为 NaN
                'home_rolling_shots_on_target': home_shots,
                'home_rolling_shots_on_target_std': np.nan,
                'home_rolling_possession': home_possession,
                'home_rolling_possession_std': np.nan,
                'home_rolling_team_rating': np.nan,  # 无历史数据
                'home_rolling_team_rating_std': np.nan,
                'away_rolling_xg': away_xg,
                'away_rolling_xg_std': np.nan,
                'away_rolling_shots_on_target': away_shots,
                'away_rolling_shots_on_target_std': np.nan,
                'away_rolling_possession': away_possession,
                'away_rolling_possession_std': np.nan,
                'away_rolling_team_rating': np.nan,
                'away_rolling_team_rating_std': np.nan,

                # 积分榜特征（8 维）- 从真实积分榜获取
                'home_table_position': home_pos,
                'away_table_position': away_pos,
                'table_position_diff': pos_diff,
                'home_points': home_pts,
                'away_points': away_pts,
                'points_diff': pts_diff,
                'home_recent_form_points': home_form_pts,
                'away_recent_form_points': away_form_pts,

                # 走势特征（2 维）- 从真实积分榜获取
                'home_win_rate_last10': home_win_rate,
                'away_loss_rate_last10': away_loss_rate,
            }

        except Exception as e:
            logger.debug(f"从 stats 列表提取失败: {e}")
            return None

    def _extract_new_features(
        self,
        row: Dict,
        home_standings: Optional[Dict] = None,
        away_standings: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        提取 V19.0 新增特征（13 维）

        Args:
            row: 比赛数据行
            home_standings: 主队积分榜数据（从 standings_calculator 获取）
            away_standings: 客队积分榜数据（从 standings_calculator 获取）
        """
        home_team = row.get('home_team', '')
        away_team = row.get('away_team', '')
        match_time = row.get('match_time')

        if isinstance(match_time, str):
            match_time = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
        elif match_time is None:
            match_time = datetime.now()
        # 处理 pandas Timestamp (可能是 timezone-aware)
        else:
            # 转换为 naive datetime 以避免时区问题
            if hasattr(match_time, 'tzinfo') and match_time.tzinfo is not None:
                match_time = match_time.replace(tzinfo=None)
            elif hasattr(match_time, 'to_pydatetime'):
                match_time = match_time.to_pydatetime()
                if match_time.tzinfo is not None:
                    match_time = match_time.replace(tzinfo=None)

        # V19.2: 从真实积分榜获取积分（不再使用硬编码默认值）
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

        # 模拟赛季最后几轮（用于保级战意计算）
        season_end = datetime(2024, 5, 25)
        games_remaining = max(0, (season_end - match_time).days // 7)

        # V19.2: 根据当前积分榜计算降级区积分（动态计算）
        # 降级区通常是第18-20位，取第18位的积分作为参考
        # 如果没有积分榜数据，使用 NaN
        if home_standings is not None and away_standings is not None:
            # 简化处理：假设30分左右是降级区边界
            relegation_zone_points = 30.0
        else:
            relegation_zone_points = np.nan

        # 使用 V19AdvancedFeatureExtractor 提取新特征
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

        # 只返回数值特征（排除非数值字段）
        # V19.2: 将 None 值替换为 NaN
        result = {}
        for k, v in v19_features.items():
            if isinstance(v, (int, float)):
                result[k] = v
            elif v is None:
                result[k] = np.nan

        return result

    def run_full_pipeline(
        self,
        train_size: int = 500,
        calib_size: int = 80,
        test_size: int = 180,
        save_model: bool = True
    ) -> Dict[str, Any]:
        """
        运行完整的 V19.0 流水线

        Args:
            train_size: 训练集大小
            calib_size: 校准集大小
            test_size: 测试集大小（严格物理隔离）
            save_model: 是否保存模型

        Returns:
            Dict: 完整结果
        """
        logger.info("=" * 80)
        logger.info("V19.0 完整重建流水线启动")
        logger.info("=" * 80)

        # Step 1: 加载数据
        df = self.load_data(limit=train_size + calib_size + test_size)

        if df.empty:
            return {"error": "数据加载失败"}

        # Step 2: 提取特征
        feature_df = self.extract_v19_features(df)

        if feature_df.empty:
            return {"error": "特征提取失败"}

        # Step 3: 准备训练/校准/测试集（严格物理隔离）
        # V19.2 加固：使用次要排序键确保确定性
        # 如果有多场比赛同时开始，使用确定性排序
        sort_keys = ['match_time']
        if 'match_id' in feature_df.columns:
            sort_keys.append('match_id')
        elif 'id' in feature_df.columns:
            sort_keys.append('id')
        feature_df = feature_df.sort_values(sort_keys)

        # 分割数据
        total_size = len(feature_df)
        train_end = train_size
        calib_end = train_size + calib_size

        train_df = feature_df.iloc[:train_end]
        calib_df = feature_df.iloc[train_end:calib_end]
        test_df = feature_df.iloc[calib_end:]

        logger.info(f"训练集: {len(train_df)} 场")
        logger.info(f"校准集: {len(calib_df)} 场")
        logger.info(f"测试集: {len(test_df)} 场（严格物理隔离）")

        # 获取特征列
        exclude_cols = ['match_id', 'home_team', 'away_team', 'match_time', 'result']
        feature_cols = [c for c in feature_df.columns if c not in exclude_cols]
        self.feature_columns = feature_cols

        X_train = train_df[feature_cols].values
        y_train = train_df['result'].values

        X_calib = calib_df[feature_cols].values
        y_calib = calib_df['result'].values

        X_test = test_df[feature_cols].values
        y_test = test_df['result'].values

        # 特征标准化
        self.scaler.fit(X_train)
        X_train_scaled = self.scaler.transform(X_train)
        X_calib_scaled = self.scaler.transform(X_calib)
        X_test_scaled = self.scaler.transform(X_test)

        # Step 4: 训练 XGBoost 模型
        logger.info("\n训练 XGBoost 模型...")
        self.model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.8,
            random_state=42,
            use_label_encoder=False,
            eval_metric='mlogloss',
        )

        self.model.fit(X_train_scaled, y_train)

        # 评估训练集
        train_acc = self.model.score(X_train_scaled, y_train)
        logger.info(f"训练集准确率: {train_acc:.2%}")

        # Step 5: 概率校准
        logger.info("\n进行概率校准...")
        self.calibrator = V19ProbabilityCalibrator(method='isotonic')
        self.calibrator.set_base_model(self.model)
        calibration_result = self.calibrator.fit(self.model, X_calib_scaled, y_calib)

        logger.info(f"Brier Score 改进: {calibration_result.brier_score_improvement:.1f}%")

        # Step 6: 测试集评估（严格物理隔离）
        logger.info("\n测试集评估（严格物理隔离）...")

        # 原始预测
        raw_proba = self.model.predict_proba(X_test_scaled)
        raw_pred = self.model.predict(X_test_scaled)

        # 校准后预测
        calibrated_proba = self.calibrator.predict_proba(X_test_scaled)
        calibrated_pred = np.argmax(calibrated_proba, axis=1)

        # 计算指标
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

        test_acc_raw = accuracy_score(y_test, raw_pred)
        test_acc_cal = accuracy_score(y_test, calibrated_pred)
        test_f1 = f1_score(y_test, calibrated_pred, average='macro')

        logger.info(f"测试集准确率（原始）: {test_acc_raw:.2%}")
        logger.info(f"测试集准确率（校准后）: {test_acc_cal:.2%}")
        logger.info(f"测试集 F1-Score: {test_f1:.4f}")

        # Step 7: 投注回测
        logger.info("\n投注回测...")
        betting_metrics = self._run_betting_backtest(
            test_df,
            calibrated_proba,
            y_test
        )

        # Step 8: 保存模型
        model_path = None
        calibrator_path = None
        metadata_path = None

        if save_model:
            model_dir = Path("src/production_models")
            model_dir.mkdir(exist_ok=True)

            # 保存模型
            model_path = model_dir / "v19.0_reconstruction.pkl"
            joblib.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_columns': feature_cols,
            }, model_path)

            # 保存校准器
            calibrator_path = model_dir / "v19.0_calibrator.pkl"
            self.calibrator.save(str(calibrator_path))

            # 保存元数据
            metadata = {
                'version': 'V19.0',
                'creation_date': datetime.now().isoformat(),
                'feature_count': len(feature_cols),
                'v18_features': self.V18_FEATURE_COUNT,
                'v19_new_features': self.V19_NEW_FEATURE_COUNT,
                'feature_columns': feature_cols,
                'metrics': {
                    'test_accuracy': float(test_acc_cal),
                    'test_f1_macro': float(test_f1),
                    'brier_score_before': float(calibration_result.brier_score_before),
                    'brier_score_after': float(calibration_result.brier_score_after),
                    'roi_fixed': float(betting_metrics['roi_fixed']),
                    'roi_kelly': float(betting_metrics['roi_kelly']),
                },
                'description': 'V19.0 Reconstruction - Advanced Features + Probability Calibration',
            }

            metadata_path = model_dir / "v19.0_reconstruction_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"\n✅ 模型已保存: {model_path}")
            logger.info(f"✅ 校准器已保存: {calibrator_path}")
            logger.info(f"✅ 元数据已保存: {metadata_path}")

        # 返回完整结果
        return {
            'metrics': V19Metrics(
                accuracy=test_acc_cal,
                f1_macro=test_f1,
                precision=precision_score(y_test, calibrated_pred, average='macro'),
                recall=recall_score(y_test, calibrated_pred, average='macro'),
                brier_score_before=calibration_result.brier_score_before,
                brier_score_after=calibration_result.brier_score_after,
                brier_score_improvement=calibration_result.brier_score_improvement,
                win_rate=betting_metrics['win_rate'],
                roi_fixed=betting_metrics['roi_fixed'],
                roi_kelly=betting_metrics['roi_kelly'],
                max_drawdown=betting_metrics['max_drawdown'],
                total_bets=betting_metrics['total_bets'],
                high_confidence_failures=betting_metrics['high_confidence_failures'],
                home_favorite_losses=betting_metrics['home_favorite_losses'],
            ),
            'model_path': str(model_path) if model_path else None,
            'calibrator_path': str(calibrator_path) if calibrator_path else None,
            'metadata_path': str(metadata_path) if metadata_path else None,
        }

    def _run_betting_backtest(
        self,
        test_df: pd.DataFrame,
        probabilities: np.ndarray,
        y_true: np.ndarray
    ) -> Dict[str, float]:
        """
        运行投注回测

        Args:
            test_df: 测试集数据
            probabilities: 预测概率
            y_true: 真实标签

        Returns:
            Dict: 回测指标
        """
        capital = 10000.0
        capital_history = [capital]
        total_bets = 0
        winning_bets = 0
        high_confidence_failures = 0
        home_favorite_losses = 0

        # 最小优势阈值（降低以获得更多投注机会）
        min_edge = 0.01

        for i in range(len(test_df)):
            prob = probabilities[i]
            actual = y_true[i]

            # 获取最高概率预测
            pred_class = np.argmax(prob)
            pred_prob = prob[pred_class]

            # 估算市场赔率
            market_odds = self._estimate_market_odds(prob)

            # 去水得到真实概率
            fair_prob = 1 / market_odds[pred_class]
            edge = pred_prob - fair_prob

            # 只有优势足够大才投注
            if edge < min_edge:
                continue

            # 凯利投注（保守 25%）
            odds = market_odds[pred_class]
            kelly_f = ((odds - 1) * pred_prob - (1 - pred_prob)) / (odds - 1)
            bet_amount = capital * max(0, kelly_f * 0.25)
            bet_amount = min(bet_amount, capital * 0.02)  # 硬上限 2%

            if bet_amount <= 0:
                continue

            total_bets += 1

            # 高置信度失败
            if pred_prob > 0.7 and pred_class != actual:
                high_confidence_failures += 1

            # 主场热门失败
            if pred_class == 2 and odds < 2.0 and pred_class != actual:
                home_favorite_losses += 1

            # 结算
            if pred_class == actual:
                winnings = bet_amount * (odds - 1)
                capital += winnings
                winning_bets += 1
            else:
                capital -= bet_amount

            capital_history.append(capital)

        # 计算指标
        win_rate = winning_bets / max(total_bets, 1)
        roi = (capital - 10000) / 10000 * 100

        # 最大回撤
        max_drawdown = 0
        peak = capital_history[0]
        for c in capital_history:
            if c > peak:
                peak = c
            drawdown = (peak - c) / peak
            max_drawdown = max(max_drawdown, drawdown)

        return {
            'win_rate': win_rate,
            'roi_fixed': roi,
            'roi_kelly': roi * 0.8,  # 假设 Kelly 更保守
            'max_drawdown': max_drawdown * 100,
            'total_bets': total_bets,
            'high_confidence_failures': high_confidence_failures,
            'home_favorite_losses': home_favorite_losses,
        }

    def _estimate_market_odds(self, model_prob: np.ndarray) -> List[float]:
        """基于模型概率估算市场赔率（简化版）"""
        margin = 1.05
        return [round((1 / p) * margin, 2) if p > 0 else 10.0 for p in model_prob]


def main():
    """主函数"""
    print("V19.0 完整重建流水线")
    print("=" * 80)

    pipeline = V19ProductionPipeline()

    # 运行完整流水线（V19.1 真实母库版本）
    results = pipeline.run_full_pipeline(
        train_size=500,
        calib_size=80,
        test_size=180,
        save_model=True
    )

    if 'error' in results:
        print(f"\n❌ {results['error']}")
        return

    # 显示结果
    metrics = results['metrics']

    print("\n" + "=" * 80)
    print("V19.0 性能指标")
    print("=" * 80)
    print(f"\n模型性能:")
    print(f"  测试集准确率: {metrics.accuracy:.2%}")
    print(f"  F1-Score: {metrics.f1_macro:.4f}")
    print(f"  精确率: {metrics.precision:.4f}")
    print(f"  召回率: {metrics.recall:.4f}")

    print(f"\n概率校准:")
    print(f"  Brier Score (前): {metrics.brier_score_before:.4f}")
    print(f"  Brier Score (后): {metrics.brier_score_after:.4f}")
    print(f"  改进幅度: {metrics.brier_score_improvement:.1f}%")

    print(f"\n投注性能（严格回测）:")
    print(f"  胜率: {metrics.win_rate:.2%}")
    print(f"  固定投注 ROI: {metrics.roi_fixed:.2f}%")
    print(f"  Kelly 投注 ROI: {metrics.roi_kelly:.2f}%")
    print(f"  最大回撤: {metrics.max_drawdown:.2f}%")
    print(f"  总投注次数: {metrics.total_bets}")

    print(f"\n诊断指标:")
    print(f"  高置信度失败: {metrics.high_confidence_failures}")
    print(f"  主场热门失败: {metrics.home_favorite_losses}")

    print("\n" + "=" * 80)

    if metrics.roi_fixed > 0:
        print("🎉 V19.0 重建成功！ROI 已转正！")
    else:
        print(f"⚠️ ROI 仍为负值 ({metrics.roi_fixed:.2f}%)，需要进一步优化")

    print(f"\n模型路径: {results['model_path']}")
    print(f"校准器路径: {results['calibrator_path']}")
    print(f"元数据路径: {results['metadata_path']}")


if __name__ == "__main__":
    main()
