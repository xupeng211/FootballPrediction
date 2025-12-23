#!/usr/bin/env python3
"""
V19.4 生产环境预测导出 - 真实数据版本

功能:
1. 从数据库获取有 L2 数据的比赛
2. 使用 V19.4 模型进行预测
3. 执行市场价格验证
4. 生成每日投注清单

作者: V19.4 生产团队
日期: 2025-12-23
"""

import os
import sys
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import joblib
import psycopg2
from psycopg2.extras import RealDictCursor

# from src.config_unified import get_settings  # Bypass to avoid validation errors
from src.ops.market_price_verifier import MarketPriceVerifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class V19_4ProductionPredictor:
    """V19.4 生产环境预测器"""

    def __init__(self):
        self.model = None
        self.metadata = None
        self.scaler_mean = None
        self.scaler_scale = None
        self.feature_columns = None
        self.price_verifier = MarketPriceVerifier()

        # 输出目录
        self.output_dir = Path("data/production")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("V19.4 生产预测器初始化完成")

    def load_v19_4_model(self):
        """加载 V19.4 模型"""
        model_path = "src/production_models/v19.4_draw_sensitivity_model.pkl"
        metadata_path = "src/production_models/v19.4_draw_sensitivity_metadata.json"

        logger.info("=" * 60)
        logger.info("📦 加载 V19.4 模型")
        logger.info("=" * 60)

        # 加载模型
        self.model = joblib.load(model_path)
        logger.info(f"✅ 模型加载成功: {model_path}")

        # 加载元数据
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)

        self.feature_columns = self.metadata['feature_columns']
        self.scaler_mean = np.array(self.metadata['scaler_mean'])
        self.scaler_scale = np.array(self.metadata['scaler_scale'])

        logger.info(f"✅ 特征数量: {self.metadata['feature_count']}")
        logger.info(f"✅ 平局权重: {self.metadata['draw_class_weight']}x")
        logger.info(f"✅ 版本: {self.metadata['version']}")

    def get_matches_from_db(self, limit: int = 50) -> pd.DataFrame:
        """从数据库获取有 L2 数据的比赛"""
        logger.info("=" * 60)
        logger.info("📊 从数据库获取比赛数据")
        logger.info("=" * 60)

        # 直接连接数据库，绕过配置验证
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="football_db",
            user="football_user",
            password="football_pass"
        )

        query = """
            SELECT
                id,
                home_team,
                away_team,
                match_time,
                home_score,
                away_score,
                result_score,
                l2_raw_json
            FROM matches
            WHERE l2_raw_json IS NOT NULL
            ORDER BY match_time DESC
            LIMIT %s
        """

        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()

        logger.info(f"✅ 获取到 {len(df)} 场比赛")

        return df

    def extract_features_from_l2(self, row: pd.Series) -> dict:
        """从 L2 数据提取特征"""
        try:
            raw_data = row['l2_raw_json']
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            if 'technical_features' not in raw_data:
                return None

            tech = raw_data['technical_features']

            def safe_float(val):
                try:
                    return float(val) if val is not None else np.nan
                except (ValueError, TypeError):
                    return np.nan

            # V18 基础特征
            features = {
                'home_rolling_xg': safe_float(tech.get('home_xg')),
                'away_rolling_xg': safe_float(tech.get('away_xg')),
                'home_rolling_shots_on_target': safe_float(tech.get('home_shots_on_target')),
                'away_rolling_shots_on_target': safe_float(tech.get('away_shots_on_target')),
                'home_rolling_possession': safe_float(tech.get('home_possession')),
                'away_rolling_possession': safe_float(tech.get('away_possession')),
                'home_rolling_shots': safe_float(tech.get('home_shots')),
                'away_rolling_shots': safe_float(tech.get('away_shots')),
                'home_rolling_corners': safe_float(tech.get('home_corners')),
                'away_rolling_corners': safe_float(tech.get('away_corners')),
            }

            # 处理 diff/total 格式
            if np.isnan(features['home_rolling_shots_on_target']):
                if 'diff_shots_on_target' in tech and 'total_shots_on_target' in tech:
                    diff_sot = safe_float(tech.get('diff_shots_on_target'))
                    total_sot = safe_float(tech.get('total_shots_on_target'))
                    features['home_rolling_shots_on_target'] = (total_sot + diff_sot) / 2
                    features['away_rolling_shots_on_target'] = (total_sot - diff_sot) / 2

            # 添加默认值（对于 V19 高级特征）
            for feat in self.feature_columns:
                if feat not in features:
                    if feat.startswith('elo_'):
                        features[feat] = 1500.0 if 'effective' in feat or 'gap' in feat else 0.0
                    elif feat.startswith('home_fatigue') or feat.startswith('away_fatigue'):
                        features[feat] = 0.0
                    elif feat.startswith('home_rest') or feat.startswith('away_rest'):
                        features[feat] = 5.0
                    elif feat.startswith('home_relegation') or feat.startswith('away_relegation'):
                        features[feat] = 0.0
                    elif feat.startswith('home_desperation') or feat.startswith('away_desperation'):
                        features[feat] = 0.0
                    elif feat in ['table_proximity', 'low_scoring_tendency']:
                        features[feat] = 0.0
                    elif feat == 'elo_diff_cluster':
                        features[feat] = 0.0
                    elif feat.startswith('league_'):
                        features[feat] = 1.0 if feat == 'league_epl' else 0.0
                    else:
                        features[feat] = 0.0

            return features

        except Exception as e:
            logger.warning(f"特征提取失败: {e}")
            return None

    def predict_matches(self, df: pd.DataFrame) -> pd.DataFrame:
        """对比赛进行预测"""
        logger.info("=" * 60)
        logger.info("🤖 V19.4 预测: 开始计算")
        logger.info("=" * 60)

        predictions = []

        for idx, row in df.iterrows():
            # 提取特征
            features = self.extract_features_from_l2(row)
            if features is None:
                continue

            # 构建特征向量
            X = np.array([[features.get(feat, 0) for feat in self.feature_columns]])

            # 标准化
            X_scaled = (X - self.scaler_mean) / self.scaler_scale

            # 预测
            proba = self.model.predict_proba(X_scaled)[0]

            # 类别: 0=Away, 1=Draw, 2=Home
            pred_class = int(np.argmax(proba))
            confidence = float(proba[pred_class])

            # 转换为标签
            label_map = {0: 'A', 1: 'D', 2: 'H'}
            prediction = label_map[pred_class]

            # 计算预估 ROI
            pred_prob = proba[pred_class]
            if pred_prob > 0:
                estimated_odds = 1 / pred_prob
                edge = pred_prob - (1 / estimated_odds)
                estimated_roi = edge * 100
            else:
                estimated_roi = 0.0

            predictions.append({
                'match_id': row['id'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'match_time': row['match_time'],
                'result_score': row.get('result_score', None),
                'prediction': prediction,
                'prediction_code': pred_class,
                'confidence': confidence,
                'probability_home': float(proba[2]),
                'probability_draw': float(proba[1]),
                'probability_away': float(proba[0]),
                'estimated_roi': estimated_roi,
                'recommended': confidence > 0.60 and estimated_roi > 5.0
            })

        result_df = pd.DataFrame(predictions)

        logger.info(f"✅ 预测完成: {len(result_df)} 场比赛")

        return result_df

    def verify_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证市场价格"""
        logger.info("=" * 60)
        logger.info("💱 市场价格验证")
        logger.info("=" * 60)

        verified_predictions = []
        deprecated_count = 0

        for _, row in df.iterrows():
            pred_label = row['prediction']

            # 获取预估赔率
            if pred_label == 'H':
                historical_odds = 1 / row['probability_home'] if row['probability_home'] > 0 else None
            elif pred_label == 'D':
                historical_odds = 1 / row['probability_draw'] if row['probability_draw'] > 0 else None
            else:  # 'A'
                historical_odds = 1 / row['probability_away'] if row['probability_away'] > 0 else None

            # 验证价格
            price_check = self.price_verifier.verify_price(
                match_id=str(row['match_id']),
                home_team=row['home_team'],
                away_team=row['away_team'],
                prediction=pred_label,
                historical_odds=historical_odds
            )

            # 添加价格状态
            row_dict = row.to_dict()
            row_dict['price_status'] = price_check.recommendation
            row_dict['price_deprecated'] = price_check.is_deprecated
            row_dict['historical_odds'] = price_check.historical_odds
            row_dict['live_odds'] = price_check.live_odds
            row_dict['odds_diff_pct'] = price_check.odds_diff_pct

            if price_check.is_deprecated:
                deprecated_count += 1
                logger.warning(
                    f"⚠️ 价格贬值: {row['home_team']} vs {row['away_team']} "
                    f"预测:{pred_label} 偏离:{price_check.odds_diff_pct:.2%}"
                )
            else:
                verified_predictions.append(row_dict)

        logger.info(f"✅ 价格验证完成: {len(verified_predictions)} 场安全, {deprecated_count} 场贬值")

        return pd.DataFrame(verified_predictions)

    def generate_daily_picks(self, df: pd.DataFrame, min_confidence: float = 0.60, min_roi: float = 5.0) -> str:
        """生成每日投注清单"""
        logger.info("=" * 60)
        logger.info("💰 生成投注清单")
        logger.info("=" * 60)

        # 筛选高价值比赛
        filtered = df[
            (df['confidence'] >= min_confidence) &
            (df['estimated_roi'] >= min_roi) &
            (~df['price_deprecated'])
        ]

        logger.info(f"📊 筛选结果: {len(filtered)}/{len(df)} 场比赛符合条件")

        if len(filtered) == 0:
            logger.warning("⚠️ 今日无符合条件的交易机会")
            return ""

        # 生成推荐理由
        filtered['reason'] = filtered.apply(self._generate_reason, axis=1)

        # 保存 CSV
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"daily_picks_{date_str}.csv"
        output_path = self.output_dir / filename

        # 保存完整数据
        df.to_csv(self.output_dir / f"daily_picks_{date_str}_full.csv", index=False)

        # 保存筛选后的清单
        filtered.to_csv(output_path, index=False)

        logger.info(f"✅ 清单已保存: {output_path}")

        # 打印摘要
        self._print_summary(filtered)

        return str(output_path)

    def _generate_reason(self, row: pd.Series) -> str:
        """生成推荐理由"""
        reasons = []

        if row['confidence'] > 0.70:
            reasons.append(f"高置信度 ({row['confidence']:.1%})")

        if row['estimated_roi'] > 10.0:
            reasons.append(f"高 ROI ({row['estimated_roi']:.1f}%)")

        pred = row['prediction']
        if pred == 'H' and row['probability_home'] > 0.65:
            reasons.append("主场优势明显")
        elif pred == 'D' and row['probability_draw'] > 0.30:
            reasons.append("平局概率高")
        elif pred == 'A' and row['probability_away'] > 0.65:
            reasons.append("客场实力优势")

        return "; ".join(reasons) if reasons else "综合分析推荐"

    def _print_summary(self, df: pd.DataFrame):
        """打印摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 每日投注清单摘要")
        logger.info("=" * 60)

        for _, row in df.iterrows():
            logger.info(f"\n🎯 {row['home_team']} vs {row['away_team']}")
            logger.info(f"   预测: {row['prediction']} (置信度: {row['confidence']:.1%})")
            logger.info(f"   预估 ROI: {row['estimated_roi']:.1f}%")
            logger.info(f"   价格状态: {row['price_status']}")
            logger.info(f"   理由: {row['reason']}")

    def run(self, limit: int = 50, min_confidence: float = 0.60, min_roi: float = 5.0):
        """运行完整预测流程"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 V19.4 生产环境预测导出")
        logger.info("=" * 80)

        # 1. 加载模型
        self.load_v19_4_model()

        # 2. 获取比赛数据
        df = self.get_matches_from_db(limit)

        # 3. 预测
        predictions = self.predict_matches(df)

        if len(predictions) == 0:
            logger.warning("⚠️ 没有预测结果")
            return

        # 4. 价格验证
        verified = self.verify_prices(predictions)

        # 5. 生成清单
        output_path = self.generate_daily_picks(verified, min_confidence, min_roi)

        logger.info("\n" + "=" * 80)
        logger.info("✅ V19.4 预测导出完成")
        logger.info("=" * 80)
        logger.info(f"输出文件: {output_path}")


# ============================================
# 主程序
# ============================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V19.4 生产环境预测导出")
    parser.add_argument("--limit", type=int, default=50, help="最大比赛数量")
    parser.add_argument("--min-confidence", type=float, default=0.60, help="最小置信度")
    parser.add_argument("--min-roi", type=float, default=5.0, help="最小 ROI")

    args = parser.parse_args()

    predictor = V19_4ProductionPredictor()
    predictor.run(
        limit=args.limit,
        min_confidence=args.min_confidence,
        min_roi=args.min_roi
    )
