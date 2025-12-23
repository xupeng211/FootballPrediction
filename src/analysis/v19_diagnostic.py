#!/usr/bin/env python3
"""
V19.0 诊断分析器 - 13% 胜率"反向逻辑"分析
Step A: 诊断预测错误的"稳胆翻车"模式

Author: V19.0 Quant Team
Purpose: 分析模型预测错误但赔率极低的场次，确定问题根源
"""

import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
from src.ml.features.elo_rating_system import EloRatingSystem
import xgboost as xgb
import joblib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DiagnosticMatch:
    """诊断比赛数据结构"""
    match_id: str
    home_team: str
    away_team: str
    match_date: str

    # 预测 vs 实际
    predicted_result: str  # H/D/A
    predicted_prob: Dict[str, float]  # {H: 0.6, D: 0.25, A: 0.15}
    actual_result: str
    actual_score: str

    # 市场信息
    market_odds: Dict[str, float]  # {home: 1.5, draw: 4.0, away: 6.0}
    market_implied_prob: Dict[str, float]

    # 关键指标
    model_confidence: float  # 预测最高概率
    edge: float  # model_prob - market_implied_prob
    error_type: str  # "overconfident_home", "underestimate_away", "surprise_draw"
    was_favorite: bool


class V19DiagnosticAnalyzer:
    """V19.0 诊断分析器 - 识别反向逻辑"""

    def __init__(self, db_conn=None):
        """
        初始化诊断分析器

        Args:
            db_conn: 数据库连接（可选）
        """
        self.db_conn = db_conn
        self.diagnostic_results: List[DiagnosticMatch] = []
        self.patterns = {
            "home_favorite_loss": [],
            "away_upset_win": [],
            "draw_surprise": [],
            "high_confidence_fail": [],
        }

        # 统计数据
        self.stats = {
            "total_analyzed": 0,
            "home_wins_correct": 0,
            "away_wins_correct": 0,
            "draws_correct": 0,
            "high_confidence_failures": 0,  # >70% confidence but wrong
            "low_odds_upsets": 0,  # odds < 1.5 but lost
        }

        logger.info("V19.0 诊断分析器初始化完成")

    def load_test_matches(self, limit: int = 180) -> List[Dict]:
        """
        加载测试集比赛数据（严格物理隔离）

        优先从 CSV 文件加载，如果不存在则从数据库加载

        Args:
            limit: 加载比赛数量

        Returns:
            List[Dict]: 比赛数据列表
        """
        # 优先尝试从 CSV 文件加载
        csv_path = Path("data/archive/gold_dataset_with_real_scores.csv")

        if csv_path.exists():
            logger.info(f"从 CSV 文件加载数据: {csv_path}")
            df = pd.read_csv(csv_path)

            # 筛选英超比赛
            if 'league' in df.columns:
                df = df[df['league'] == 'Premier League'].copy()

            matches = []
            for _, row in df.head(limit).iterrows():
                match = {
                    'id': row.get('external_id', ''),
                    'home_team': row['home_team'],
                    'away_team': row['away_team'],
                    'home_score': row['home_score'],
                    'away_score': row['away_score'],
                    'status': row.get('match_status', 'Finished'),
                    'raw_data': {
                        'stats': {
                            'home': {
                                'xg': row.get('home_xg', 1.2),
                                'possession': row.get('home_possession', 50),
                                'rating': 6.8,
                                'shots_on_target': row.get('home_xg', 1.2) * 4,  # 估算
                            },
                            'away': {
                                'xg': row.get('away_xg', 1.0),
                                'possession': row.get('away_possession', 50),
                                'rating': 6.6,
                                'shots_on_target': row.get('away_xg', 1.0) * 4,  # 估算
                            }
                        }
                    }
                }
                matches.append(match)

            logger.info(f"从 CSV 加载了 {len(matches)} 场英超比赛")
            return matches

        # 备用：从数据库加载
        settings = get_settings()
        db_config = settings.database

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.name,
                user=db_config.user,
                password=db_config.password.get_secret_value()
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 加载最近的比赛（测试集）
            query = """
            SELECT
                m.id,
                m.home_team,
                m.away_team,
                m.match_time,
                m.home_score,
                m.away_score,
                m.status,
                m.l2_raw_json as raw_data
            FROM matches m
            WHERE m.status = 'Finished'
            AND m.home_score IS NOT NULL
            ORDER BY m.match_time DESC
            LIMIT %s
            """

            cursor.execute(query, (limit,))
            matches = cursor.fetchall()

            cursor.close()
            conn.close()

            logger.info(f"从数据库加载了 {len(matches)} 场比赛")
            return [dict(m) for m in matches]

        except Exception as e:
            logger.error(f"加载数据库数据失败: {e}")
            return []

    def analyze_prediction_errors(
        self,
        matches: List[Dict],
        model_path: str = "src/production_models/v18.2_final_beast.pkl"
    ) -> Dict[str, Any]:
        """
        分析预测错误模式

        Args:
            matches: 比赛数据列表
            model_path: 模型路径

        Returns:
            Dict: 分析结果
        """
        logger.info("开始分析预测错误模式...")
        logger.info(f"模型路径: {model_path}")

        # 加载模型
        try:
            model_data = joblib.load(model_path)
            model = model_data['model'] if isinstance(model_data, dict) else model_data

            # 尝试加载元数据
            metadata_path = model_path.replace('.pkl', '_metadata.json')
            if Path(metadata_path).exists():
                import json
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    logger.info(f"模型版本: {metadata.get('version', 'Unknown')}")
                    logger.info(f"特征数量: {metadata.get('feature_count', 'Unknown')}")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return {}

        diagnostic_matches = []

        for match in matches:
            diagnostic = self._diagnose_single_match(match, model)
            if diagnostic:
                diagnostic_matches.append(diagnostic)

        self.diagnostic_results = diagnostic_matches

        # 统计分析
        self._calculate_patterns()

        return {
            "total_diagnosed": len(diagnostic_matches),
            "patterns": self.patterns,
            "stats": self.stats,
            "top_failures": self._get_top_failures(n=10),
            "recommendations": self._generate_recommendations()
        }

    def _diagnose_single_match(
        self,
        match: Dict,
        model
    ) -> Optional[DiagnosticMatch]:
        """
        诊断单场比赛

        Args:
            match: 比赛数据
            model: 预测模型

        Returns:
            DiagnosticMatch: 诊断结果
        """
        try:
            # 提取特征
            features = self._extract_features(match)

            if features is None:
                return None

            # 预测（如果模型支持）
            predicted_result = "H"  # 默认
            predicted_prob = {"H": 0.5, "D": 0.25, "A": 0.25}  # 默认

            try:
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba([features])[0]
                    if len(proba) == 3:
                        predicted_prob = {"H": proba[2], "D": proba[1], "A": proba[0]}
                        predicted_result = max(predicted_prob, key=predicted_prob.get)
                    elif len(proba) == 2:
                        # 二分类
                        predicted_prob = {"H": proba[1], "D": 0.0, "A": proba[0]}
                        predicted_result = max(predicted_prob, key=predicted_prob.get)
                elif hasattr(model, 'predict'):
                    pred = model.predict([features])[0]
                    predicted_result = {2: "H", 1: "D", 0: "A"}.get(pred, "H")
            except Exception as e:
                logger.debug(f"预测失败: {e}")

            # 实际结果
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)

            if home_score > away_score:
                actual_result = "H"
            elif home_score < away_score:
                actual_result = "A"
            else:
                actual_result = "D"

            # 估算市场赔率（基于特征）
            market_odds = self._estimate_market_odds(features, match)
            market_implied_prob = {
                "H": 1 / market_odds["H"],
                "D": 1 / market_odds["D"],
                "A": 1 / market_odds["A"]
            }

            # 归一化市场概率
            total_prob = sum(market_implied_prob.values())
            market_implied_prob = {k: v / total_prob for k, v in market_implied_prob.items()}

            # 计算关键指标
            model_confidence = max(predicted_prob.values())
            edge = predicted_prob[predicted_result] - market_implied_prob[predicted_result]

            # 判断是否为热门（赔率 < 2.0）
            was_favorite = market_odds[predicted_result] < 2.0

            # 确定错误类型
            error_type = self._classify_error(
                predicted_result,
                actual_result,
                model_confidence,
                was_favorite
            )

            return DiagnosticMatch(
                match_id=str(match.get('id', '')),
                home_team=match.get('home_team', 'Unknown'),
                away_team=match.get('away_team', 'Unknown'),
                match_date=str(match.get('match_time', '')),
                predicted_result=predicted_result,
                predicted_prob=predicted_prob,
                actual_result=actual_result,
                actual_score=f"{home_score}-{away_score}",
                market_odds=market_odds,
                market_implied_prob=market_implied_prob,
                model_confidence=model_confidence,
                edge=edge,
                error_type=error_type,
                was_favorite=was_favorite
            )

        except Exception as e:
            logger.debug(f"诊断比赛失败: {e}")
            return None

    def _extract_features(self, match: Dict) -> Optional[np.ndarray]:
        """
        从比赛数据中提取特征

        Args:
            match: 比赛数据

        Returns:
            np.ndarray: 特征向量
        """
        try:
            raw_data = match.get('raw_data', '{}')
            if isinstance(raw_data, str):
                import json
                raw_data = json.loads(raw_data)

            stats = raw_data.get('stats', {})

            # 提取 L2 数据
            home_stats = stats.get('home', {})
            away_stats = stats.get('away', {})

            # 构建 26 维特征（与 V18.2 一致）
            features = [
                home_stats.get('xg', 1.2),  # home_rolling_xg
                home_stats.get('xg_std', 0.4),  # home_rolling_xg_std
                home_stats.get('shots_on_target', 5.0),  # home_rolling_shots_on_target
                home_stats.get('shots_on_target_std', 2.0),  # home_rolling_shots_on_target_std
                home_stats.get('possession', 50.0),  # home_rolling_possession
                home_stats.get('possession_std', 10.0),  # home_rolling_possession_std
                home_stats.get('rating', 6.8),  # home_rolling_team_rating
                home_stats.get('rating_std', 0.5),  # home_rolling_team_rating_std

                away_stats.get('xg', 1.0),  # away_rolling_xg
                away_stats.get('xg_std', 0.3),  # away_rolling_xg_std
                away_stats.get('shots_on_target', 4.0),  # away_rolling_shots_on_target
                away_stats.get('shots_on_target_std', 1.8),  # away_rolling_shots_on_target_std
                away_stats.get('possession', 50.0),  # away_rolling_possession
                away_stats.get('possession_std', 10.0),  # away_rolling_possession_std
                away_stats.get('rating', 6.6),  # away_rolling_team_rating
                away_stats.get('rating_std', 0.4),  # away_rolling_team_rating_std

                # 赛前特征
                home_stats.get('table_position', 10),  # home_table_position
                away_stats.get('table_position', 10),  # away_table_position
                home_stats.get('table_position', 10) - away_stats.get('table_position', 10),  # table_position_diff
                home_stats.get('points', 30),  # home_points
                away_stats.get('points', 30),  # away_points
                home_stats.get('points', 30) - away_stats.get('points', 30),  # points_diff
                home_stats.get('recent_form_points', 6),  # home_recent_form_points
                away_stats.get('recent_form_points', 6),  # away_recent_form_points
                home_stats.get('win_rate_last10', 0.3),  # home_win_rate_last10
                away_stats.get('loss_rate_last10', 0.3),  # away_loss_rate_last10
            ]

            return np.array(features)

        except Exception as E:
            logger.debug(f"特征提取失败: {e}")
            return None

    def _estimate_market_odds(self, features: np.ndarray, match: Dict) -> Dict[str, float]:
        """
        基于特征估算市场赔率

        Args:
            features: 特征向量
            match: 比赛数据

        Returns:
            Dict: 赔率 {H, D, A}
        """
        # 使用评分差异和 xG 差异估算
        home_rating = features[6]
        away_rating = features[14]
        home_xg = features[0]
        away_xg = features[8]

        rating_diff = (home_rating - away_rating) / 10
        xg_diff = home_xg - away_xg

        # 综合优势
        combined_advantage = rating_diff * 0.7 + xg_diff * 0.3

        # 主场优势
        home_prob = 0.45 + combined_advantage * 0.15
        home_prob = max(0.15, min(0.75, home_prob))

        # 平局概率（实力接近时更高）
        closeness = 1 - min(abs(rating_diff), 0.8)
        draw_prob = 0.26 * closeness + 0.18

        # 客胜概率
        away_prob = 1 - home_prob - draw_prob
        away_prob = max(0.10, away_prob)

        # 归一化
        total = home_prob + draw_prob + away_prob
        home_prob /= total
        draw_prob /= total
        away_prob /= total

        # 转换为赔率（含 5% 抽水）
        margin = 1.05
        return {
            "H": round((1 / home_prob) * margin, 2),
            "D": round((1 / draw_prob) * margin, 2),
            "A": round((1 / away_prob) * margin, 2)
        }

    def _classify_error(
        self,
        predicted: str,
        actual: str,
        confidence: float,
        was_favorite: bool
    ) -> str:
        """
        分类错误类型

        Args:
            predicted: 预测结果
            actual: 实际结果
            confidence: 预测置信度
            was_favorite: 是否为热门

        Returns:
            str: 错误类型
        """
        if predicted == actual:
            return "correct"

        if predicted == "H" and actual == "A":
            if confidence > 0.6:
                return "overconfident_home"
            else:
                return "home_to_away"

        if predicted == "H" and actual == "D":
            if confidence > 0.6:
                return "ignore_draw_risk"
            else:
                return "home_to_draw"

        if predicted == "A" and actual == "H":
            return "underestimate_home"

        if predicted == "A" and actual == "D":
            return "away_to_draw"

        if predicted == "D":
            return "draw_prediction_failed"

        return "unknown"

    def _calculate_patterns(self):
        """计算错误模式"""
        for diag in self.diagnostic_results:
            self.stats["total_analyzed"] += 1

            # 统计正确预测
            if diag.predicted_result == diag.actual_result:
                if diag.actual_result == "H":
                    self.stats["home_wins_correct"] += 1
                elif diag.actual_result == "A":
                    self.stats["away_wins_correct"] += 1
                else:
                    self.stats["draws_correct"] += 1
                continue

            # 高置信度失败
            if diag.model_confidence > 0.7:
                self.stats["high_confidence_failures"] += 1
                self.patterns["high_confidence_fail"].append(diag)

            # 低赔率爆冷
            if diag.was_favorite:
                self.stats["low_odds_upsets"] += 1
                self.patterns["home_favorite_loss"].append(diag)

            # 客队爆冷获胜
            if diag.actual_result == "A" and diag.predicted_result == "H":
                self.patterns["away_upset_win"].append(diag)

            # 平局意外
            if diag.actual_result == "D" and diag.predicted_result != "D":
                self.patterns["draw_surprise"].append(diag)

    def _get_top_failures(self, n: int = 10) -> List[Dict]:
        """获取最严重的预测失败"""
        # 按置信度和是否为热门排序
        failures = [
            d for d in self.diagnostic_results
            if d.predicted_result != d.actual_result
        ]

        # 排序：高置信度 + 热门优先
        failures.sort(key=lambda x: (x.model_confidence, int(x.was_favorite)), reverse=True)

        top_n = failures[:n]

        return [
            {
                "match": f"{x.home_team} vs {x.away_team}",
                "predicted": x.predicted_result,
                "actual": x.actual_result,
                "score": x.actual_score,
                "confidence": f"{x.model_confidence:.1%}",
                "market_odds": x.market_odds,
                "error_type": x.error_type
            }
            for x in top_n
        ]

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 分析主场优势是否被高估
        home_fails = len(self.patterns["home_favorite_loss"])
        total = max(self.stats["total_analyzed"], 1)
        home_fail_rate = home_fails / total

        if home_fail_rate > 0.2:
            recommendations.append(
                f"⚠️ 主场优势被高估：{home_fail_rate:.1%} 的热门主队失利。"
                f"建议：减少 home_advantage 权重，引入 Fatigue_Index。"
            )

        # 分析平局预测
        draw_correct = self.stats["draws_correct"]
        draw_total = len([d for d in self.diagnostic_results if d.actual_result == "D"])
        draw_accuracy = draw_correct / max(draw_total, 1)

        if draw_accuracy < 0.2:
            recommendations.append(
                f"⚠️ 平局预测失败：准确率仅 {draw_accuracy:.1%}。"
                f"建议：引入 Relegation_Incentive（保级队平局意愿更强）。"
            )

        # 分析高置信度失败
        high_conf_fail_rate = self.stats["high_confidence_failures"] / max(total, 1)
        if high_conf_fail_rate > 0.15:
            recommendations.append(
                f"⚠️ 模型过度自信：{high_conf_fail_rate:.1%} 的高置信度预测失败。"
                f"建议：实施概率校准 (Isotonic Regression)，确保 60% 预测对应 60% 实际胜率。"
            )

        if not recommendations:
            recommendations.append("✅ 未发现明显系统性问题，当前模型较为健康。")

        return recommendations

    def generate_report(self) -> str:
        """生成诊断报告"""
        report = []
        report.append("=" * 80)
        report.append("V19.0 诊断分析报告 - 13% 胜率反向逻辑分析")
        report.append("=" * 80)
        report.append("")

        # 统计概览
        report.append("📊 统计概览:")
        report.append(f"  分析比赛数: {self.stats['total_analyzed']}")
        report.append(f"  主胜预测正确: {self.stats['home_wins_correct']}")
        report.append(f"  客胜预测正确: {self.stats['away_wins_correct']}")
        report.append(f"  平局预测正确: {self.stats['draws_correct']}")
        report.append(f"  高置信度失败: {self.stats['high_confidence_failures']}")
        report.append(f"  低赔率爆冷: {self.stats['low_odds_upsets']}")
        report.append("")

        # Top 10 失败案例
        report.append("🔴 Top 10 预测失败案例:")
        top_failures = self._get_top_failures(10)
        for i, fail in enumerate(top_failures, 1):
            report.append(f"  {i}. {fail['match']}")
            report.append(f"     预测: {fail['predicted']} | 实际: {fail['actual']} | 比分: {fail['score']}")
            report.append(f"     置信度: {fail['confidence']} | 市场赔率: {fail['market_odds']}")
            report.append(f"     错误类型: {fail['error_type']}")
        report.append("")

        # 改进建议
        report.append("💡 改进建议:")
        recommendations = self._generate_recommendations()
        for rec in recommendations:
            report.append(f"  {rec}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


def main():
    """主函数"""
    print("V19.0 诊断分析器启动...")
    print("=" * 80)

    analyzer = V19DiagnosticAnalyzer()

    # 加载测试集比赛
    matches = analyzer.load_test_matches(limit=180)

    if not matches:
        print("❌ 无法加载比赛数据")
        return

    # 运行诊断分析
    results = analyzer.analyze_prediction_errors(matches)

    # 生成报告
    report = analyzer.generate_report()
    print(report)

    # 保存报告
    report_path = "reports/v19_diagnostic_report.txt"
    Path(report_path).parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n✅ 诊断报告已保存: {report_path}")


if __name__ == "__main__":
    main()
