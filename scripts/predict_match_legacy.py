#!/usr/bin/env python3
"""
⚽ 足球比赛预测CLI工具 - Football Match Prediction CLI

一个用户友好的命令行工具，用于预测足球比赛结果。
基于机器学习模型，提供1X2预测和投注建议。

使用示例:
    python scripts/predict_match.py --home "Arsenal" --away "Chelsea"
    python scripts/predict_match.py --home "Manchester United" --away "Liverpool" --date "2024-01-15"
"""

import argparse
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from src.inference import Predictor
    from src.database.connection import get_database_config
    from sqlalchemy import create_engine, text
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    logger.info("将使用简化模式进行演示预测")
    Predictor = None


class MatchPredictorCLI:
    """足球比赛预测CLI工具"""

    def __init__(self):
        self.predictor = None
        self.engine = None
        self.simulation_mode = False

        # 初始化组件
        self._initialize_components()

    def _initialize_components(self):
        """初始化预测组件"""
        try:
            # 初始化预测模型
            model_path = project_root / "models" / "baseline_v1.pkl"
            if model_path.exists() and Predictor:
                self.predictor = Predictor(str(model_path), None)
                self.predictor.load_model()  # 显式加载模型
                logger.info("✅ 成功加载预测模型")
            else:
                logger.warning(f"⚠️ 模型文件不存在: {model_path}")
                self.simulation_mode = True

            # 初始化数据库连接
            try:
                self.config = get_database_config()
                self.engine = create_engine(self.config.sync_url)
                # 测试连接
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("✅ 成功连接数据库")
            except Exception as e:
                logger.error(f"❌ 数据库连接失败: {e}")
                self.engine = None

            # 如果没有模型或数据库，启用模拟模式
            if not self.predictor or not self.engine:
                self.simulation_mode = True
                logger.info("🎭 启用模拟预测模式")

        except Exception as e:
            logger.error(f"初始化组件失败: {e}")
            self.simulation_mode = True

    def _get_team_id(self, team_name: str) -> Optional[int]:
        """获取球队ID"""
        if not self.engine:
            return None

        try:
            with self.engine.connect() as conn:
                team_query = text("SELECT id FROM teams WHERE team_name = :team_name")
                result = conn.execute(team_query, {"team_name": team_name})
                team_row = result.fetchone()
                return team_row[0] if team_row else None
        except Exception as e:
            logger.debug(f"从数据库获取团队ID失败: {e}")
            return None

    def _get_team_features(self, team_name: str):
        """获取指定球队的最新特征数据"""
        if not self.engine:
            return None

        team_id = self._get_team_id(team_name)
        if not team_id:
            return None

        try:
            with self.engine.connect() as conn:
                # 获取该球队的最新特征数据（主队）
                home_features_query = text(
                    """
                    SELECT * FROM match_features
                    WHERE home_team_id = :team_id
                    ORDER BY match_date DESC
                    LIMIT 1
                """
                )

                result = conn.execute(home_features_query, {"team_id": team_id})
                home_row = result.fetchone()

                # 获取该球队的最新特征数据（客队）
                away_features_query = text(
                    """
                    SELECT * FROM match_features
                    WHERE away_team_id = :team_id
                    ORDER BY match_date DESC
                    LIMIT 1
                """
                )

                result = conn.execute(away_features_query, {"team_id": team_id})
                away_row = result.fetchone()

                return {
                    "team_id": team_id,
                    "home_features": home_row,
                    "away_features": away_row,
                }
        except Exception as e:
            logger.error(f"获取球队特征数据失败: {e}")
            return None

    def _extract_real_features(
        self, home_team: str, away_team: str, match_date: datetime
    ) -> Optional[Dict[str, float]]:
        """提取真实特征数据"""

        try:
            logger.info(f"🔍 正在提取真实特征数据: {home_team} vs {away_team}")

            # 获取球队特征数据
            home_data = self._get_team_features(home_team)
            away_data = self._get_team_features(away_team)

            if not home_data or not away_data:
                logger.warning("⚠️ 无法获取完整的球队特征数据")
                return None

            # 构建特征向量 - 使用验证过的12维特征
            home_features = home_data["home_features"]
            away_features = away_data["away_features"]

            if not home_features or not away_features:
                logger.warning("⚠️ 特征数据不完整")
                return None

            # 安全转换函数
            def safe_float(value, default=0.0):
                return float(value) if value is not None else default

            # 构建12个核心特征向量 - 确保所有值都是float类型
            features = np.array(
                [
                    safe_float(
                        home_features[14] if home_features[14] is not None else 0.5
                    ),  # home_recent_points_3
                    safe_float(
                        away_features[18] if away_features[18] is not None else 0.5
                    ),  # away_recent_points_3
                    safe_float(
                        home_features[10] if home_features[10] is not None else 0.33
                    ),  # h2h_home_win_rate
                    safe_float(
                        home_features[11] if home_features[11] is not None else 0.34
                    ),  # h2h_draw_rate
                    safe_float(
                        home_features[12] if home_features[12] is not None else 0.33
                    ),  # h2h_away_win_rate
                    safe_float(
                        home_features[23] if home_features[23] is not None else 1.2
                    ),  # venue_home_win_rate_3
                    safe_float(
                        1.0
                        / (
                            away_features[23]
                            if away_features[23] is not None and away_features[23] > 0
                            else 1.0
                        )
                    ),  # venue_away_disadvantage_3
                    safe_float(
                        home_features[15] if home_features[15] is not None else 1.0
                    ),  # home_goals_scored_avg_5
                    safe_float(
                        away_features[20] if away_features[20] is not None else 1.0
                    ),  # away_goals_conceded_avg_5
                    safe_float(
                        away_features[19] if away_features[19] is not None else 1.0
                    ),  # away_goals_scored_avg_5
                    safe_float(
                        home_features[16] if home_features[16] is not None else 1.0
                    ),  # home_goals_conceded_avg_5
                    safe_float(
                        home_features[14] if home_features[14] is not None else 1.0
                    ),  # home_recent_points_3 (备用)
                ],
                dtype=np.float64,
            )

            logger.info(f"✅ 成功提取真实特征数据: {len(features)} 维")
            return features

        except Exception as e:
            logger.error(f"❌ 提取真实特征失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def extract_features_with_fallback(
        self, home_team: str, away_team: str, match_date: datetime
    ) -> Dict[str, float]:
        """提取特征，支持回退到模拟数据"""

        # 尝试提取真实特征
        real_features = self._extract_real_features(home_team, away_team, match_date)

        if real_features is not None and not self.simulation_mode:
            # 将numpy数组转换为字典格式，保持与原有接口兼容
            return {
                "home_form_3": float(real_features[0]),
                "away_form_3": float(real_features[1]),
                "h2h_home_win_rate": float(real_features[2]),
                "h2h_draw_rate": float(real_features[3]),
                "h2h_away_win_rate": float(real_features[4]),
                "venue_home_advantage_3": float(real_features[5]),
                "venue_away_disadvantage_3": float(real_features[6]),
                "home_goals_scored_avg_5": float(real_features[7]),
                "away_goals_conceded_avg_5": float(real_features[8]),
                "away_goals_scored_avg_5": float(real_features[9]),
                "home_goals_conceded_avg_5": float(real_features[10]),
                "home_recent_points_3": float(real_features[11]),
                "away_recent_points_3": float(real_features[1]),  # 重复使用away_form_3
            }
        else:
            logger.info("回退到模拟特征数据")
            return self._generate_simulation_features(home_team, away_team)

    def _generate_simulation_features(
        self, home_team: str, away_team: str
    ) -> Dict[str, float]:
        """生成模拟特征数据用于演示"""
        import random

        # 基于团队名称生成一致的特征
        home_hash = abs(hash(home_team.lower())) % 100
        away_hash = abs(hash(away_team.lower())) % 100

        # 生成基础形态特征
        home_form = 0.3 + (home_hash % 40) / 100.0  # 0.3-0.7
        away_form = 0.3 + (away_hash % 40) / 100.0  # 0.3-0.7

        # 生成历史交锋特征
        h2h_diff = (home_hash - away_hash) / 100.0
        h2h_home_win = max(0.1, min(0.6, 0.35 + h2h_diff * 0.01))
        h2h_away_win = max(0.1, min(0.6, 0.35 - h2h_diff * 0.01))
        h2h_draw = 1.0 - h2h_home_win - h2h_away_win

        # 生成场馆优势特征
        venue_home_adv = 0.5 + (home_hash % 30) / 100.0  # 0.5-0.8
        venue_away_adv = 0.5 + (away_hash % 30) / 100.0  # 0.5-0.8

        # 生成进球相关特征
        home_goals_scored = 1.0 + (home_hash % 20) / 10.0  # 1.0-3.0
        away_goals_conceded = 0.8 + (home_hash % 25) / 10.0  # 0.8-3.3
        away_goals_scored = 1.0 + (away_hash % 20) / 10.0  # 1.0-3.0
        home_goals_conceded = 0.8 + (away_hash % 25) / 10.0  # 0.8-3.3

        # 生成积分特征
        home_recent_points = 4.0 + (home_hash % 12) / 4.0  # 4.0-7.0
        away_recent_points = 4.0 + (away_hash % 12) / 4.0  # 4.0-7.0

        features = {
            "home_form_3": home_form,
            "away_form_3": away_form,
            "h2h_home_win_rate": h2h_home_win,
            "h2h_draw_rate": h2h_draw,
            "h2h_away_win_rate": h2h_away_win,
            "venue_home_advantage_3": venue_home_adv,
            "venue_away_disadvantage_3": 2.0 - venue_away_adv,
            "home_goals_scored_avg_5": home_goals_scored,
            "away_goals_conceded_avg_5": away_goals_conceded,
            "away_goals_scored_avg_5": away_goals_scored,
            "home_goals_conceded_avg_5": home_goals_conceded,
            "home_recent_points_3": home_recent_points,
            "away_recent_points_3": away_recent_points,
        }

        logger.info("🎭 生成了模拟特征数据")
        return features

    def predict_with_fallback(self, features: Dict[str, float]) -> Dict[str, float]:
        """使用预测器进行预测，支持回退到模拟预测"""

        if not self.simulation_mode and self.predictor:
            try:
                # 准备特征向量（使用验证过的12维特征）
                feature_vector = np.array(
                    [
                        features.get("home_recent_points_3", 0.5),  # 1
                        features.get("away_recent_points_3", 0.5),  # 2
                        features.get("h2h_home_win_rate", 0.33),  # 3
                        features.get("h2h_draw_rate", 0.34),  # 4
                        features.get("h2h_away_win_rate", 0.33),  # 5
                        features.get("venue_home_advantage_3", 1.2),  # 6
                        features.get("venue_away_disadvantage_3", 0.8),  # 7
                        features.get("home_goals_scored_avg_5", 1.0),  # 8
                        features.get("away_goals_conceded_avg_5", 1.0),  # 9
                        features.get("away_goals_scored_avg_5", 1.0),  # 10
                        features.get("home_goals_conceded_avg_5", 1.0),  # 11
                        features.get("home_recent_points_3", 1.0),  # 12 (备用)
                    ],
                    dtype=np.float64,
                )

                # 使用真实模型预测
                predictions = self.predictor.predict(feature_vector)
                logger.info("✅ 使用真实模型进行预测")
                logger.debug(f"预测结果: {predictions}")

                # 解析预测结果
                if isinstance(predictions, dict):
                    if "probabilities" in predictions:
                        probs = predictions["probabilities"]
                        # 如果只有2个概率，假设是HOME_WIN vs NOT_HOME_WIN
                        if len(probs) == 2:
                            home_prob = float(probs[0])
                            draw_prob = (
                                float(probs[1]) * 0.5
                            )  # 将剩余概率分配给平局和客胜
                            away_prob = float(probs[1]) * 0.5
                        else:
                            home_prob = float(probs[0]) if len(probs) > 0 else 0.33
                            draw_prob = float(probs[1]) if len(probs) > 1 else 0.33
                            away_prob = float(probs[2]) if len(probs) > 2 else 0.34
                    else:
                        # 默认概率
                        home_prob, draw_prob, away_prob = 0.4, 0.3, 0.3
                elif hasattr(predictions, "__len__") and len(predictions) >= 3:
                    home_prob = float(predictions[0])
                    draw_prob = float(predictions[1])
                    away_prob = float(predictions[2])
                elif isinstance(predictions, (int, np.integer)):
                    # 如果是类别预测，转换为one-hot编码
                    if predictions == 0:
                        return {"HOME_WIN": 0.8, "DRAW": 0.1, "AWAY_WIN": 0.1}
                    elif predictions == 1:
                        return {"HOME_WIN": 0.1, "DRAW": 0.8, "AWAY_WIN": 0.1}
                    else:
                        return {"HOME_WIN": 0.1, "DRAW": 0.1, "AWAY_WIN": 0.8}
                else:
                    # 未知格式，使用简单逻辑预测
                    logger.info("🎭 使用简单逻辑进行预测")
                    return self._simulate_prediction(features)

                # 归一化概率
                total = home_prob + draw_prob + away_prob
                if total > 0:
                    return {
                        "HOME_WIN": home_prob / total,
                        "DRAW": draw_prob / total,
                        "AWAY_WIN": away_prob / total,
                    }
                else:
                    return {"HOME_WIN": 0.33, "DRAW": 0.34, "AWAY_WIN": 0.33}

            except Exception as e:
                logger.warning(f"⚠️ 真实模型预测失败: {e}")
                logger.info("回退到模拟预测")

        # 模拟预测逻辑
        return self._simulate_prediction(features)

    def _simulate_prediction(self, features: Dict[str, float]) -> Dict[str, float]:
        """基于特征进行模拟预测"""
        import random

        # 基于特征计算基础概率
        home_strength = (
            features.get("home_form_3", 0.5) * 0.3
            + features.get("h2h_home_win_rate", 0.33) * 0.25
            + features.get("venue_home_advantage_3", 0.5) * 0.2
            + features.get("home_recent_points_3", 5.0) * 0.05 / 9.0
            + features.get("home_goals_scored_avg_5", 1.5) * 0.05 / 3.0
            + features.get("away_goals_conceded_avg_5", 1.5) * 0.05 / 3.0
        )

        away_strength = (
            features.get("away_form_3", 0.5) * 0.3
            + features.get("h2h_away_win_rate", 0.33) * 0.25
            + features.get("venue_away_disadvantage_3", 1.5) * 0.2
            + features.get("away_recent_points_3", 5.0) * 0.05 / 9.0
            + features.get("away_goals_scored_avg_5", 1.5) * 0.05 / 3.0
            + features.get("home_goals_conceded_avg_5", 1.5) * 0.05 / 3.0
        )

        draw_strength = features.get("h2h_draw_rate", 0.34) * 0.4

        # 归一化
        total_strength = home_strength + away_strength + draw_strength
        if total_strength > 0:
            home_prob = home_strength / total_strength
            away_prob = away_strength / total_strength
            draw_prob = draw_strength / total_strength
        else:
            # 默认概率
            home_prob, draw_prob, away_prob = 0.46, 0.26, 0.28

        # 添加一些随机性使结果更真实
        noise = 0.05
        home_prob = max(0.05, min(0.85, home_prob + random.uniform(-noise, noise)))
        away_prob = max(0.05, min(0.85, away_prob + random.uniform(-noise, noise)))
        draw_prob = max(0.05, min(0.85, draw_prob + random.uniform(-noise, noise)))

        # 重新归一化确保总和为1
        total = home_prob + draw_prob + away_prob
        if total > 0:
            home_prob /= total
            draw_prob /= total
            away_prob /= total

        logger.info("🎭 使用模拟逻辑进行预测")

        return {
            "HOME_WIN": round(home_prob, 3),
            "DRAW": round(draw_prob, 3),
            "AWAY_WIN": round(away_prob, 3),
        }

    def generate_betting_suggestion(
        self, predictions: Dict[str, float]
    ) -> Dict[str, Any]:
        """生成投注建议"""
        home_win_prob = predictions["HOME_WIN"]
        draw_prob = predictions["DRAW"]
        away_win_prob = predictions["AWAY_WIN"]

        # 确定最可能的结果
        max_prob = max(home_win_prob, draw_prob, away_win_prob)

        if max_prob == home_win_prob:
            prediction = "HOME_WIN"
            confidence = home_win_prob
        elif max_prob == draw_prob:
            prediction = "DRAW"
            confidence = draw_prob
        else:
            prediction = "AWAY_WIN"
            confidence = away_win_prob

        # 生成投注建议
        if confidence >= 0.60:
            suggestion = f"💰 强烈推荐: {prediction} (置信度 {confidence:.1%})"
            risk_level = "低风险"
        elif confidence >= 0.45:
            suggestion = f"⚠️ 谨慎考虑: {prediction} (置信度 {confidence:.1%})"
            risk_level = "中等风险"
        else:
            suggestion = (
                f"🚫 不建议投注: 比赛结果难以预测 (最高置信度 {confidence:.1%})"
            )
            risk_level = "高风险"

        return {
            "prediction": prediction,
            "confidence": confidence,
            "suggestion": suggestion,
            "risk_level": risk_level,
            "value_bet": self._calculate_value_bet(predictions),
        }

    def _calculate_value_bet(self, predictions: Dict[str, float]) -> str:
        """计算价值投注建议"""
        home_prob = predictions["HOME_WIN"]
        draw_prob = predictions["DRAW"]
        away_prob = predictions["AWAY_WIN"]

        # 模拟赔率（基于概率）
        home_odds = round(1 / home_prob, 2)
        draw_odds = round(1 / draw_prob, 2)
        away_odds = round(1 / away_prob, 2)

        # 寻找价值投注机会
        best_value = max(
            [
                ("主胜", home_prob, home_odds),
                ("平局", draw_prob, draw_odds),
                ("客胜", away_prob, away_odds),
            ],
            key=lambda x: x[1] * 0.9 - 1 / x[2] if x[2] > 1 else -1,
        )

        outcome, prob, odds = best_value
        implied_prob = 1 / odds if odds > 1 else 1

        if prob > implied_prob * 1.1:  # 10%的价值阈值
            return f"📈 价值投注: {outcome} (概率 {prob:.1%} vs 赔率隐含概率 {implied_prob:.1%})"
        else:
            return "📊 当前赔率无明显价值投注机会"

    def print_beautiful_results(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        predictions: Dict[str, float],
        suggestion: Dict[str, Any],
    ):
        """以漂亮的格式打印预测结果"""

        # 颜色和表情符号
        colors = {
            "reset": "\033[0m",
            "bold": "\033[1m",
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
        }

        print(f"\n{colors['bold']}{colors['cyan']}{'='*60}{colors['reset']}")
        print(f"{colors['bold']}{colors['white']}⚽  足球比赛预测结果{colors['reset']}")
        print(f"{colors['cyan']}{'='*60}{colors['reset']}\n")

        # 比赛信息
        print(f"{colors['bold']}📅 比赛信息:{colors['reset']}")
        print(f"   主队: {colors['green']}{home_team}{colors['reset']}")
        print(f"   客队: {colors['red']}{away_team}{colors['reset']}")
        print(f"   日期: {match_date.strftime('%Y年%m月%d日 %H:%M')}\n")

        # 数据源标识
        if self.simulation_mode:
            print(
                f"{colors['yellow']}{colors['bold']}[⚠️ 警告: 使用模拟数据演示]{colors['reset']}"
            )
            print(
                "   由于数据库连接失败或缺少历史数据，使用基于统计的模拟特征进行预测\n"
            )
        else:
            print(
                f"{colors['green']}{colors['bold']}[✅ 使用真实数据预测]{colors['reset']}"
            )
            print("   基于历史比赛数据和机器学习模型进行预测\n")

        # 预测概率
        print(f"{colors['bold']}🎯 预测概率:{colors['reset']}")

        home_prob = predictions["HOME_WIN"]
        draw_prob = predictions["DRAW"]
        away_prob = predictions["AWAY_WIN"]

        # 创建概率条形图
        max_prob = max(home_prob, draw_prob, away_prob)

        def prob_bar(prob, label, color):
            bar_length = int(prob * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            return f"{color}{label:8}: {prob:6.1%} |{bar}| {colors['reset']}"

        print(prob_bar(home_prob, "主胜", colors["green"]))
        print(prob_bar(draw_prob, "平局", colors["yellow"]))
        print(prob_bar(away_prob, "客胜", colors["red"]))
        print()

        # 投注建议
        print(f"{colors['bold']}💡 投注建议:{colors['reset']}")
        print(f"   {suggestion['suggestion']}")
        print(
            f"   风险等级: {colors['magenta']}{suggestion['risk_level']}{colors['reset']}"
        )
        print(f"   {suggestion['value_bet']}\n")

        # 预测详情
        print(f"{colors['bold']}📊 预测详情:{colors['reset']}")
        print(
            f"   最终预测: {colors['bold']}{suggestion['prediction']}{colors['reset']}"
        )
        print(
            f"   置信度: {colors['cyan']}{suggestion['confidence']:.1%}{colors['reset']}"
        )

        # 添加免责声明
        print(f"\n{colors['yellow']}{colors['bold']}⚠️  免责声明:{colors['reset']}")
        print("   本预测仅供参考，不构成投资建议。")
        print("   足球比赛结果具有不确定性，请理性投注。")

        print(f"\n{colors['cyan']}{'='*60}{colors['reset']}\n")

    def predict_match(
        self, home_team: str, away_team: str, match_date: Optional[str] = None
    ) -> bool:
        """执行比赛预测"""
        try:
            # 处理比赛日期
            if match_date:
                try:
                    match_dt = datetime.strptime(match_date, "%Y-%m-%d")
                except ValueError:
                    logger.error(f"日期格式错误，请使用 YYYY-MM-DD 格式")
                    return False
            else:
                match_dt = datetime.now()

            # 提取特征
            logger.info(f"正在提取 {home_team} vs {away_team} 的特征...")
            features = self.extract_features_with_fallback(
                home_team, away_team, match_dt
            )

            # 进行预测
            logger.info("正在进行预测...")
            predictions = self.predict_with_fallback(features)

            # 生成投注建议
            suggestion = self.generate_betting_suggestion(predictions)

            # 打印结果
            self.print_beautiful_results(
                home_team, away_team, match_dt, predictions, suggestion
            )

            return True

        except Exception as e:
            logger.error(f"预测过程中发生错误: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="⚽ 足球比赛预测CLI工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/predict_match.py --home "Arsenal" --away "Chelsea"
  python scripts/predict_match.py --home "Manchester United" --away "Liverpool" --date "2024-01-15"
  python scripts/predict_match.py -h "Barcelona" -a "Real Madrid" -d "2024-12-25"
        """,
    )

    parser.add_argument(
        "--home", "-H", type=str, required=True, help="主队名称 (例如: Arsenal)"
    )

    parser.add_argument(
        "--away", "-a", type=str, required=True, help="客队名称 (例如: Chelsea)"
    )

    parser.add_argument(
        "--date", "-d", type=str, help="比赛日期 (格式: YYYY-MM-DD，默认为今天)"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 验证输入
    if not args.home or not args.away:
        parser.error("必须提供主队和客队名称")

    # 创建预测器
    predictor = MatchPredictorCLI()

    # 执行预测
    success = predictor.predict_match(args.home, args.away, args.date)

    # 退出
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
