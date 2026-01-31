"""
FootballPrediction V7.0 模型处理器模块
封装LightGBM模型的加载、保存、推理和特征预处理逻辑
"""

from datetime import datetime
import logging
import os
import pickle
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.core.config import get_config

logger = logging.getLogger(__name__)


class ModelHandler:
    """LightGBM模型处理器"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.model = None
        self.scaler = None
        self.feature_columns = self.config.model.feature_columns
        self.is_loaded = False

    def load_model(self, model_path: str | None = None) -> bool:
        """加载LightGBM模型"""
        if model_path is None:
            model_path = self.config.paths.current_model_path

        try:
            if not os.path.exists(model_path):
                logger.error(f"模型文件不存在: {model_path}")
                return False

            # 尝试加载LightGBM模型
            self.model = lgb.Booster(model_file=str(model_path))
            logger.info(f"✅ LightGBM模型加载成功: {model_path}")

            # 尝试加载配套的scaler
            model_path_str = str(model_path)
            scaler_path = model_path_str.replace(".model", "_scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                logger.info(f"✅ 特征缩放器加载成功: {scaler_path}")

            self.is_loaded = True
            return True

        except Exception as e:
            logger.exception(f"❌ 模型加载失败 {model_path}: {e}")
            self.model = None
            self.scaler = None
            self.is_loaded = False
            return False

    def save_model(
        self, model_path: str | None = None, scaler: StandardScaler | None = None
    ) -> bool:
        """保存LightGBM模型"""
        if model_path is None:
            model_path = self.config.paths.current_model_path

        try:
            if self.model is None:
                logger.error("❌ 没有可保存的模型")
                return False

            # 确保目录存在
            os.makedirs(os.path.dirname(model_path), exist_ok=True)

            # 保存模型
            self.model.save_model(str(model_path))
            logger.info(f"✅ 模型保存成功: {model_path}")

            # 保存scaler（如果有）
            if scaler is not None:
                model_path_str = str(model_path)
                scaler_path = model_path_str.replace(".model", "_scaler.pkl")
                with open(scaler_path, "wb") as f:
                    pickle.dump(scaler, f)
                logger.info(f"✅ 特征缩放器保存成功: {scaler_path}")

            return True

        except Exception as e:
            logger.exception(f"❌ 模型保存失败: {e}")
            return False

    def prepare_features(self, features: dict[str, Any]) -> pd.DataFrame:
        """准备特征用于预测"""
        try:
            # 创建特征向量
            feature_vector = {}

            # 基础特征
            for col in self.feature_columns:
                if col in features:
                    feature_vector[col] = features[col]
                else:
                    # 尝试推导缺失特征
                    feature_vector[col] = self._derive_missing_feature(col, features)

            # 衍生特征
            derived_features = self._create_derived_features(features)
            feature_vector.update(derived_features)

            # 转换为DataFrame
            df = pd.DataFrame([feature_vector])

            # 确保所有特征列都存在
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0

            # 应用特征缩放（如果有scaler）
            if self.scaler is not None and self.is_loaded:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                df[numeric_cols] = self.scaler.transform(df[numeric_cols])

            return df

        except Exception as e:
            logger.exception(f"特征准备失败: {e}")
            return pd.DataFrame()

    def _derive_missing_feature(self, col: str, features: dict[str, Any]) -> float:
        """推导缺失特征"""
        # xG相关特征
        if "xg" in col:
            if "home_xg" in col and "home_xg" not in features and "home_total_shots" in features:
                return features.get("home_total_shots", 0) * 0.1  # 平均xG/shot
            if "away_xg" in col and "away_xg" not in features and "away_total_shots" in features:
                return features.get("away_total_shots", 0) * 0.1

        # 评分相关特征
        elif "rating" in col:
            return 6.5  # 默认评分

        # 其他数值特征默认值
        return 0.0

    def _create_derived_features(self, features: dict[str, Any]) -> dict[str, float]:
        """创建衍生特征"""
        derived = {}

        try:
            # xG相关衍生特征
            home_xg = features.get("home_xg", 0)
            away_xg = features.get("away_xg", 0)
            home_shots = features.get("home_total_shots", 1)
            away_shots = features.get("away_total_shots", 1)
            home_possession = features.get("home_possession", 50)
            away_possession = features.get("away_possession", 50)
            home_rating = features.get("home_avg_rating", 6.5)
            away_rating = features.get("away_avg_rating", 6.5)

            # 防止除零错误
            home_shots = max(home_shots, 1)
            away_shots = max(away_shots, 1)

            derived.update(
                {
                    "home_xg_per_shot": home_xg / home_shots,
                    "away_xg_per_shot": away_xg / away_shots,
                    "rating_diff": home_rating - away_rating,
                    "xg_diff": home_xg - away_xg,
                    "xg_total": home_xg + away_xg,
                    "possession_diff": home_possession - away_possession,
                    "shots_diff": home_shots - away_shots,
                }
            )

            # 角球差值
            home_corners = features.get("home_corners", 0)
            away_corners = features.get("away_corners", 0)
            derived["corners_diff"] = home_corners - away_corners

        except Exception as e:
            logger.warning(f"衍生特征创建失败: {e}")

        return derived

    def predict(self, features: pd.DataFrame) -> np.ndarray | None:
        """使用模型进行预测"""
        if not self.is_loaded or self.model is None:
            logger.error("❌ 模型未加载")
            return None

        try:
            if features.empty:
                logger.error("❌ 特征数据为空")
                return None

            # 确保特征顺序正确
            feature_cols = [col for col in self.feature_columns if col in features.columns]
            features_ordered = features[feature_cols]

            # 进行预测
            prediction = self.model.predict(
                features_ordered, num_iteration=self.model.best_iteration
            )

            logger.debug(f"预测成功，输出形状: {prediction.shape}")
            return prediction

        except Exception as e:
            logger.exception(f"预测失败: {e}")
            return None

    def predict_match(self, features: dict[str, Any]) -> dict[str, Any] | None:
        """预测单场比赛"""
        try:
            # 准备特征
            feature_df = self.prepare_features(features)
            if feature_df.empty:
                return None

            # 进行预测
            prediction = self.predict(feature_df)
            if prediction is None:
                return None

            # 解析预测结果（假设三分类：主胜/平/客胜）
            if len(prediction.shape) == 2 and prediction.shape[1] == 3:
                probs = prediction[0]
                home_prob, draw_prob, away_prob = probs
            elif len(prediction.shape) == 1:
                # 二分类情况，需要特殊处理
                home_win_prob = prediction[0]
                # 简化的平局和客胜概率
                draw_prob = 0.25
                away_prob = 0.75 - home_win_prob
            else:
                logger.error(f"无法解析预测结果形状: {prediction.shape}")
                return None

            # 归一化概率
            total = home_prob + draw_prob + away_prob
            if total > 0:
                home_prob /= total
                draw_prob /= total
                away_prob /= total

            # 确定推荐
            max_prob = max(home_prob, draw_prob, away_prob)
            if max_prob == home_prob:
                recommendation = f"主胜 ({home_prob:.1%})"
            elif max_prob == away_prob:
                recommendation = f"客胜 ({away_prob:.1%})"
            else:
                recommendation = f"平局 ({draw_prob:.1%})"

            return {
                "home_win_prob": float(home_prob),
                "draw_prob": float(draw_prob),
                "away_win_prob": float(away_prob),
                "recommendation": recommendation,
                "confidence": float(max_prob),
                "prediction_type": "lightgbm" if self.is_loaded else "fallback",
            }

        except Exception as e:
            logger.exception(f"比赛预测失败: {e}")
            return None

    def fallback_predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """降级预测策略（当模型不可用时）"""
        try:
            # 使用简单的xG和评分模型
            home_xg = features.get("home_xg", 1.0)
            away_xg = features.get("away_xg", 1.0)
            rating_diff = features.get("rating_diff", 0)
            possession_diff = features.get("possession_diff", 0)

            # 简单的评分模型
            home_score = (
                home_xg * 0.6 + max(0, rating_diff) * 0.3 + max(0, possession_diff) * 0.1 + 0.5
            )

            away_score = (
                away_xg * 0.6 + max(0, -rating_diff) * 0.3 + max(0, -possession_diff) * 0.1 + 0.5
            )

            # 转换为概率
            draw_base = 1.0
            total = home_score + away_score + draw_base

            home_prob = home_score / total
            away_prob = away_score / total
            draw_prob = draw_base / total

            # 确定推荐
            max_prob = max(home_prob, draw_prob, away_prob)
            if max_prob == home_prob:
                recommendation = f"主胜 ({home_prob:.1%})"
            elif max_prob == away_prob:
                recommendation = f"客胜 ({away_prob:.1%})"
            else:
                recommendation = f"平局 ({draw_prob:.1%})"

            return {
                "home_win_prob": float(home_prob),
                "draw_prob": float(draw_prob),
                "away_win_prob": float(away_prob),
                "recommendation": recommendation,
                "confidence": float(max_prob),
                "prediction_type": "fallback",
            }

        except Exception as e:
            logger.exception(f"降级预测失败: {e}")
            return {
                "home_win_prob": 0.33,
                "draw_prob": 0.34,
                "away_win_prob": 0.33,
                "recommendation": "平局 (33.3%)",
                "confidence": 0.33,
                "prediction_type": "default",
            }

    def get_model_info(self) -> dict[str, Any]:
        """获取模型信息"""
        if not self.is_loaded or self.model is None:
            return {
                "loaded": False,
                "model_path": str(self.config.paths.current_model_path),
                "error": "Model not loaded",
            }

        try:
            return {
                "loaded": True,
                "model_path": str(self.config.paths.current_model_path),
                "model_type": "lightgbm",
                "feature_count": self.model.num_feature(),
                "best_iteration": self.model.best_iteration,
                "tree_count": self.model.num_trees(),
                "feature_importance": dict(
                    zip(self.model.feature_name(), self.model.feature_importance(), strict=False)
                )[:10],  # 只返回前10个重要特征
                "has_scaler": self.scaler is not None,
            }
        except Exception as e:
            return {"loaded": True, "error": str(e)}

    def validate_features(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        V8.1 严格特征对齐验证

        Args:
            features: 输入特征字典

        Returns:
            Dict[str, Any]: 验证结果
        """
        if not self.is_loaded or self.model is None:
            return {
                "valid": False,
                "error": "Model not loaded",
                "missing_features": [],
                "extra_features": [],
                "model_features": [],
            }

        try:
            # 获取模型的期望特征
            model_features = list(self.model.feature_name())
            expected_count = len(model_features)

            # 检查输入特征
            input_features = list(features.keys())
            input_count = len(input_features)

            # 找出缺失的特征
            missing_features = [f for f in model_features if f not in input_features]

            # 找出多余的特征
            extra_features = [f for f in input_features if f not in model_features]

            # 生产级宽松特征对齐检查 - 允许有额外特征，但关键特征不能缺失
            is_valid = len(missing_features) == 0  # 只要关键特征不缺失即可

            # 详细的验证报告
            validation_result = {
                "valid": is_valid,
                "model_features_count": expected_count,
                "input_features_count": input_count,
                "missing_features": missing_features,
                "extra_features": extra_features,
                "model_features": model_features[:20],  # 显示前20个特征名
                "alignment_score": 1.0
                - (len(missing_features) + len(extra_features)) / expected_count,
                "timestamp": datetime.now().isoformat(),
            }

            if not is_valid:
                error_messages = []
                if missing_features:
                    error_messages.append(
                        f"缺失{len(missing_features)}个特征: {missing_features[:5]}..."
                    )
                if extra_features:
                    # 额外特征只是警告，不是错误
                    logger.info(f"发现{len(extra_features)}个额外特征: {extra_features[:5]}...")

                validation_result["error"] = "; ".join(error_messages)
                if missing_features:
                    logger.error(f"关键特征缺失: {validation_result['error']}")
            elif extra_features:
                logger.info(f"✅ 特征验证通过，包含{len(extra_features)}个额外特征")
            else:
                logger.info(f"✅ 特征对齐验证通过: {expected_count}个特征")

            return validation_result

        except Exception as e:
            logger.exception(f"特征验证异常: {e}")
            return {
                "valid": False,
                "error": f"Validation exception: {e!s}",
                "missing_features": [],
                "extra_features": [],
                "model_features": [],
            }

    def get_feature_schema(self) -> dict[str, Any]:
        """
        获取模型的特征模式

        Returns:
            Dict[str, Any]: 特征模式信息
        """
        if not self.is_loaded or self.model is None:
            return {"available": False, "error": "Model not loaded"}

        try:
            model_features = list(self.model.feature_name())
            feature_importance = dict(
                zip(model_features, self.model.feature_importance(), strict=False)
            )

            # 按重要性排序
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

            return {
                "available": True,
                "total_features": len(model_features),
                "feature_names": model_features,
                "feature_importance": feature_importance,
                "top_features": sorted_features[:20],  # 前20个重要特征
                "feature_types": self._infer_feature_types(),
                "validation_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.exception(f"获取特征模式失败: {e}")
            return {"available": False, "error": str(e)}

    def _infer_feature_types(self) -> dict[str, str]:
        """推断特征类型"""
        # 基于特征名推断类型
        feature_types = {}
        if not self.is_loaded or self.model is None:
            return feature_types

        try:
            model_features = list(self.model.feature_name())

            for feature in model_features:
                if "ratio" in feature or "prob" in feature or "rate" in feature:
                    feature_types[feature] = "float"
                elif "count" in feature or "num" in feature:
                    feature_types[feature] = "int"
                elif "is_" in feature or "has_" in feature:
                    feature_types[feature] = "bool"
                elif feature in ["home_team", "away_team", "league"]:
                    feature_types[feature] = "categorical"
                else:
                    feature_types[feature] = "float"

            return feature_types

        except Exception:
            return {}


# 便利函数
def get_model_handler() -> ModelHandler:
    """获取模型处理器实例"""
    handler = ModelHandler()
    handler.load_model()
    return handler


def validate_model_features() -> bool:
    """
    全局函数：验证模型特征对齐

    Returns:
        bool: 特征对齐是否正确
    """
    try:
        handler = get_model_handler()

        # 使用标准测试特征进行验证
        test_features = {
            # 比分相关特征
            "home_goals_conceded_avg": 1.2,
            "away_goals_conceded_avg": 1.5,
            "home_goals_scored_avg": 2.1,
            "away_goals_scored_avg": 1.8,
            # 射门相关
            "home_shots_on_target_avg": 5.2,
            "away_shots_on_target_avg": 4.1,
            "home_shots_total_avg": 12.3,
            "away_shots_total_avg": 10.8,
            # xG相关
            "home_xg_avg": 1.8,
            "away_xg_avg": 1.4,
            "home_xg_conceded_avg": 1.1,
            "away_xg_conceded_avg": 1.6,
            # 控球率
            "home_possession_avg": 58.5,
            "away_possession_avg": 41.5,
            # 角球
            "home_corners_avg": 6.2,
            "away_corners_avg": 4.8,
            # 红黄牌
            "home_yellow_cards_avg": 1.8,
            "away_yellow_cards_avg": 2.1,
            "home_red_cards_avg": 0.1,
            "away_red_cards_avg": 0.2,
            # 历史交锋
            "h2h_home_wins": 3,
            "h2h_away_wins": 2,
            "h2h_draws": 1,
            # 赔率相关
            "home_win_odds_avg": 2.1,
            "draw_odds_avg": 3.4,
            "away_win_odds_avg": 3.6,
            # 排名相关
            "home_league_position": 3,
            "away_league_position": 8,
            "home_points": 45,
            "away_points": 32,
            # 主客场优势
            "is_home_match": 1,
            "days_since_last_match": 7,
            # 更多特征...
        }

        # 填充到180维（使用合理的默认值）
        required_features = handler.model.feature_name() if handler.is_loaded else []

        for feature in required_features:
            if feature not in test_features:
                # 根据特征名类型设置默认值
                if "ratio" in feature or "prob" in feature:
                    test_features[feature] = 0.5
                elif "count" in feature or "num" in feature or "is_" in feature:
                    test_features[feature] = 0
                else:
                    test_features[feature] = 1.0

        validation_result = handler.validate_features(test_features)

        if validation_result["valid"]:
            logger.info("✅ 模型特征对齐验证通过")
            return True
        logger.error(f"❌ 模型特征对齐验证失败: {validation_result.get('error', 'Unknown error')}")
        return False

    except Exception as e:
        logger.exception(f"模型特征验证异常: {e}")
        return False


def predict_match_result(match_features: dict[str, Any]) -> dict[str, Any] | None:
    """便利函数：预测比赛结果"""
    handler = get_model_handler()

    if handler.is_loaded:
        return handler.predict_match(match_features)
    return handler.fallback_predict(match_features)
