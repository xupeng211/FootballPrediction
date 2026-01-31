#!/usr/bin/env python3
"""
Football Prediction Inference Engine
实战预测推理引擎 - V2.0 真实比分版本

核心功能：
- 加载训练好的XGBoost模型
- 实时足球比赛预测
- 概率输出和推荐建议
- 凯利公式金融风险控制
- Docker容器化部署
"""

import json
import logging
import os
from pathlib import Path
import sys

import joblib
import numpy as np

# 添加项目路径
sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
sys.path.append("src")

# 导入凯利公式模块
from strategy.kelly_criterion_v1 import KellyCriterionV1, calculate_kelly_for_prediction

logger = logging.getLogger(__name__)


class FootballPredictionInference:
    """足球预测推理引擎"""

    def __init__(self, model_path: str | None = None):
        """
        初始化推理引擎

        Args:
            model_path: 训练好的模型路径（可选，默认使用相对路径）
        """
        # 使用pathlib处理跨平台路径兼容性
        if model_path is None:
            # 获取项目根目录的models文件夹
            project_root = Path(__file__).parent.parent.parent
            self.model_path = project_root / "data/models" / "xgb_football_v2_real_scores.joblib"
        else:
            self.model_path = Path(model_path)
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.feature_names = []

        # 初始化凯利公式计算器
        self.kelly_calculator = KellyCriterionV1()
        self.is_loaded = False

    def load_model(self) -> bool:
        """加载训练好的模型和相关组件"""
        try:
            logger.info(f"🔄 加载预测模型: {self.model_path}")

            # 加载模型
            self.model = joblib.load(self.model_path)
            logger.info("✅ XGBoost模型加载成功")

            # 加载元数据 - 使用pathlib处理路径
            metadata_path = self.model_path.with_suffix(".json").with_name(
                self.model_path.stem.replace("_metadata", "") + "_metadata.json"
            )
            with open(metadata_path) as f:
                metadata = json.load(f)

            # 重建标准化器和标签编码器
            from sklearn.preprocessing import LabelEncoder, StandardScaler

            self.scaler = StandardScaler()
            self.scaler.mean_ = np.array(metadata["scaler_mean"])
            self.scaler.scale_ = np.array(metadata["scaler_scale"])

            self.label_encoder = LabelEncoder()
            self.label_encoder.classes_ = np.array(metadata["label_encoder_classes"])

            self.feature_names = metadata["feature_names"]
            self.is_loaded = True

            logger.info("✅ 模型组件加载完成")
            logger.info(f"📊 特征数量: {len(self.feature_names)}")
            logger.info(f"🏷️ 标签类别: {metadata['label_encoder_classes']}")
            logger.info(f"🎯 模型版本: {metadata['version']}")

            return True

        except Exception as e:
            logger.exception(f"❌ 模型加载失败: {e}")
            return False

    def prepare_features(self, match_features: dict) -> np.ndarray:
        """
        准备预测特征

        Args:
            match_features: 比赛特征字典，包含xG、控球率、赔率等

        Returns:
            标准化后的特征数组
        """
        try:
            # 确保所有必需特征都存在
            feature_dict = {}
            for feature_name in self.feature_names:
                if feature_name in match_features:
                    feature_dict[feature_name] = match_features[feature_name]
                # 使用默认值
                elif "xg" in feature_name.lower():
                    feature_dict[feature_name] = 1.0  # 默认xG
                elif "possession" in feature_name.lower():
                    feature_dict[feature_name] = 50.0  # 默认控球率
                elif "odds" in feature_name.lower():
                    feature_dict[feature_name] = 2.0  # 默认赔率
                else:
                    feature_dict[feature_name] = 0.0

            # 创建衍生特征
            if "home_xg" in feature_dict and "away_xg" in feature_dict:
                feature_dict["xg_difference"] = feature_dict["home_xg"] - feature_dict["away_xg"]
                feature_dict["xg_total"] = feature_dict["home_xg"] + feature_dict["away_xg"]

            if "home_possession" in feature_dict and "away_possession" in feature_dict:
                feature_dict["possession_difference"] = (
                    feature_dict["home_possession"] - feature_dict["away_possession"]
                )

            if "home_opening_odds" in feature_dict and "home_current_odds" in feature_dict:
                if feature_dict["home_opening_odds"] > 0 and feature_dict["home_current_odds"] > 0:
                    feature_dict["odds_movement"] = (
                        feature_dict["home_current_odds"] - feature_dict["home_opening_odds"]
                    ) / feature_dict["home_opening_odds"]
                else:
                    feature_dict["odds_movement"] = 0.0

            # 构建特征向量
            feature_vector = []
            for feature_name in self.feature_names:
                feature_vector.append(feature_dict.get(feature_name, 0.0))

            features = np.array(feature_vector).reshape(1, -1)

            # 标准化
            return self.scaler.transform(features)


        except Exception as e:
            logger.exception(f"❌ 特征准备失败: {e}")
            return None

    def predict_match(self, home_team: str, away_team: str, match_features: dict) -> dict:
        """
        预测单场比赛结果

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_features: 比赛特征字典

        Returns:
            预测结果字典
        """
        if not self.is_loaded and not self.load_model():
            return {"error": "模型加载失败"}

        try:
            # 准备特征
            features = self.prepare_features(match_features)
            if features is None:
                return {"error": "特征准备失败"}

            # 预测概率
            probabilities = self.model.predict_proba(features)[0]
            predicted_class = self.model.predict(features)[0]

            # 解析结果
            result_map = {0: "客胜", 1: "平局", 2: "主胜"}

            # 🎰 凯利公式金融风险控制计算
            # 获取市场赔率（如果没有提供，使用模拟赔率）
            home_odds = match_features.get("home_current_odds", 2.1)
            draw_odds = match_features.get("draw_odds", 3.2)
            away_odds = match_features.get("away_current_odds", 3.8)

            # 计算凯利公式建议
            kelly_recommendations = calculate_kelly_for_prediction(
                float(probabilities[2]),  # home_win
                float(probabilities[1]),  # draw
                float(probabilities[0]),  # away_win
                home_odds,
                draw_odds,
                away_odds,
            )

            # 获取最佳投注建议
            best_bet = max(kelly_recommendations.items(), key=lambda x: x[1].recommended_stake_percent)
            best_outcome, best_kelly = best_bet

            return {
                "home_team": home_team,
                "away_team": away_team,
                "predicted_class": int(predicted_class),
                "predicted_result": result_map[int(predicted_class)],
                "probabilities": {
                    "away_win": float(probabilities[0]),
                    "draw": float(probabilities[1]),
                    "home_win": float(probabilities[2]),
                },
                "confidence": float(np.max(probabilities)),
                "recommendation": self._generate_recommendation(probabilities),
                "model_version": "v2.0_real_scores",
                # 🎰 凯利公式相关
                "market_odds": {"home": home_odds, "draw": draw_odds, "away": away_odds},
                "kelly_recommendations": {
                    "home": kelly_recommendations["home"].recommended_stake_percent,
                    "draw": kelly_recommendations["draw"].recommended_stake_percent,
                    "away": kelly_recommendations["away"].recommended_stake_percent,
                },
                "best_bet": {
                    "outcome": best_outcome,
                    "stake_percent": best_kelly.recommended_stake_percent,
                    "edge": best_kelly.edge,
                    "risk_level": best_kelly.risk_level,
                    "confidence": best_kelly.confidence,
                },
                "kelly_summary": f"[KELLY] Recommended Stake: {best_kelly.recommended_stake_percent:.1f}%",
            }


        except Exception as e:
            logger.exception(f"❌ 预测失败: {e}")
            return {"error": f"预测失败: {e}"}

    def _generate_recommendation(self, probabilities: np.ndarray) -> str:
        """生成投注建议"""
        max_prob = np.max(probabilities)
        max_idx = np.argmax(probabilities)

        if max_idx == 2:  # 主胜
            if max_prob > 0.65:
                return "强烈推荐主胜"
            if max_prob > 0.55:
                return "推荐主胜"
            return "谨慎看好主胜"
        if max_idx == 1:  # 平局
            if max_prob > 0.35:
                return "可考虑平局"
            return "平局概率较低"
        if max_prob > 0.65:
            return "强烈推荐客胜"
        if max_prob > 0.55:
            return "推荐客胜"
        return "谨慎看好客胜"

    def predict_batch(self, matches: list[dict]) -> list[dict]:
        """
        批量预测比赛

        Args:
            matches: 比赛列表，每个元素包含home_team, away_team, features

        Returns:
            预测结果列表
        """
        results = []
        for match in matches:
            result = self.predict_match(
                match.get("home_team", ""), match.get("away_team", ""), match.get("features", {})
            )
            results.append(result)

        return results

    def format_prediction_log(self, prediction: dict) -> str:
        """
        格式化预测日志输出

        Args:
            prediction: 预测结果字典

        Returns:
            格式化的日志字符串
        """
        if "error" in prediction:
            return f"[PREDICT_ERROR] {prediction.get('home_team', 'Unknown')} vs {prediction.get('away_team', 'Unknown')} - {prediction['error']}"

        probs = prediction["probabilities"]
        home_win_pct = probs["home_win"] * 100
        draw_pct = probs["draw"] * 100
        away_win_pct = probs["away_win"] * 100

        return (
            f"[PREDICT] {prediction['home_team']} vs {prediction['away_team']} | "
            f"Home Win: {home_win_pct:.1f}% | "
            f"Draw: {draw_pct:.1f}% | "
            f"Away Win: {away_win_pct:.1f}% | "
            f"Recommendation: {prediction['recommendation']} | "
            f"Confidence: {prediction['confidence']:.1f}"
        )



# 全局推理引擎实例
_inference_engine = None


def get_inference_engine() -> FootballPredictionInference:
    """获取全局推理引擎实例"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = FootballPredictionInference()
    return _inference_engine


def predict_match_from_features(home_team: str, away_team: str, features: dict) -> dict:
    """
    便捷函数：从特征预测比赛

    Args:
        home_team: 主队
        away_team: 客队
        features: 特征字典

    Returns:
        预测结果
    """
    engine = get_inference_engine()
    return engine.predict_match(home_team, away_team, features)
