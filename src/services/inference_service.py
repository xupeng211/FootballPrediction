"""足球预测推理服务
Football Prediction Inference Service.

提供基于XGBoost模型的实时推理服务，包括：
- 模型加载和管理
- 特征提取和预处理
- 预测结果生成
"""

import json
import logging
import os
import pandas as pd
from pathlib import Path
from typing import Optional

# 尝试导入XGBoost，如果失败则运行在Mock模式
try:
    import xgboost as xgb

    HAVE_XGBOOST = True
except ImportError:
    HAVE_XGBOOST = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ XGBoost not found. Inference service running in MOCK mode.")

logger = logging.getLogger(__name__)


class InferenceService:
    """足球预测推理服务单例类."""

    _instance = None
    _model = None
    _model_metadata = None
    _feature_data = None
    _feature_columns = None

    def __new__(cls):
        """单例模式实现."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化推理服务."""
        if not hasattr(self, "_initialized"):
            self._initialized = False
            self._load_model()
            self._load_feature_data()
            self._initialized = True
            logger.info("✅ 推理服务初始化完成")

    def _load_model(self):
        """加载训练好的XGBoost模型."""
        if not HAVE_XGBOOST:
            logger.warning("⚠️ XGBoost不可用，跳过模型加载，使用Mock模式")
            self._model = None
            self._model_metadata = {
                "model_version": "mock_v1",
                "target_classes": ["平局", "主队胜", "客队胜"],
            }
            self._feature_columns = [
                "home_team_id",
                "away_team_id",
                "home_last_5_points",
                "away_last_5_points",
                "home_last_5_avg_goals",
                "away_last_5_avg_goals",
                "h2h_last_3_home_wins",
                "home_last_5_goal_diff",
                "away_last_5_goal_diff",
                "home_win_streak",
                "away_win_streak",
                "home_last_5_win_rate",
                "away_last_5_win_rate",
                "home_rest_days",
                "away_rest_days",
            ]
            return

        try:
            # 优先加载最新的V4 Optuna优化模型
            v4_model_path = Path("models/football_prediction_v4_optuna.pkl")
            v4_results_path = Path("models/football_prediction_v4_optuna_results.json")

            # 备用：v2模型路径 (注意：当前已移动到scripts/temp/)
            # v2_model_path = Path("models/football_prediction_v2.pkl")
            # v2_metadata_path = Path("models/model_metadata.json")

            # 备用：旧模型路径
            pkl_model_path = Path("models/football_xgboost_v2_best.pkl")
            json_model_path = Path("models/football_model_v1.json")
            metadata_path = Path("models/football_model_v1_metadata.json")

            # 优先使用最新的V4 Optuna优化模型
            if v4_model_path.exists():
                logger.info(f"🚀 加载V4 Optuna优化模型: {v4_model_path}")
                import pickle

                with open(v4_model_path, 'rb') as f:
                    self._model = pickle.load(f)

                # 加载V4模型的优化结果作为元数据
                if v4_results_path.exists():
                    with open(v4_results_path) as f:
                        v4_results = json.load(f)

                    self._model_metadata = {
                        "model_version": "v4_optuna",
                        "model_type": "XGBClassifier",
                        "target_classes": ["客队胜", "平局", "主队胜"],  # away_win, draw, home_win
                        "best_score": v4_results.get("best_score"),
                        "n_trials": v4_results.get("n_trials"),
                        "optimization_time": v4_results.get("optimization_time"),
                        "test_accuracy": v4_results.get("best_score"),
                        "feature_count": len(v4_results.get("feature_names", [])),
                        "label_encoder_classes": v4_results.get("label_encoder_classes"),
                    }

                    self._feature_columns = v4_results.get("feature_names", [])
                    logger.info("✅ V4模型元数据加载成功")
                    logger.info(f"📊 V4模型准确率: {v4_results.get('best_score', 'N/A'):.4f}")
                    logger.info(f"🔧 V4模型特征数量: {len(self._feature_columns)}")
                else:
                    logger.warning("⚠️ V4元数据文件不存在，使用默认设置")
                    self._model_metadata = {
                        "model_version": "v4_optuna",
                        "target_classes": ["客队胜", "平局", "主队胜"],
                        "model_type": "XGBClassifier",
                    }
                    # 如果没有元数据，尝试从模型推断特征
                    if hasattr(self._model, 'feature_names'):
                        self._feature_columns = list(self._model.feature_names)
                    else:
                        logger.warning("⚠️ 无法获取V4模型特征名称")
                        self._feature_columns = []

                logger.info("✅ V4 Optuna优化模型加载成功")

            # 备用：使用旧模型
            elif pkl_model_path.exists():
                logger.info(f"🔄 加载备用PKL模型: {pkl_model_path}")
                import joblib

                self._model = joblib.load(pkl_model_path)
                logger.info("✅ XGBoost PKL模型加载成功")

                # 尝试加载JSON格式的元数据
                if metadata_path.exists():
                    with open(metadata_path, encoding="utf-8") as f:
                        self._model_metadata = json.load(f)
                    logger.info("✅ 模型元数据加载成功")
                else:
                    # 如果没有元数据，使用默认设置
                    self._model_metadata = {
                        "model_version": "v2_best",
                        "target_classes": ["平局", "主队胜", "客队胜"],
                        "model_type": "xgboost_v2",
                    }
                    logger.warning("⚠️ 使用默认模型元数据")

            elif json_model_path.exists():
                logger.info(f"🔄 加载JSON格式模型: {json_model_path}")
                self._model = xgb.XGBClassifier()
                self._model.load_model(str(json_model_path))
                logger.info("✅ XGBoost JSON模型加载成功")

                # 加载模型元数据
                if not metadata_path.exists():
                    raise FileNotFoundError(f"模型元数据文件不存在: {metadata_path}")
                with open(metadata_path, encoding="utf-8") as f:
                    self._model_metadata = json.load(f)
                logger.info("✅ 模型元数据加载成功")
            else:
                raise FileNotFoundError("未找到可用的模型文件")

            # 强制使用正确的特征名称（基于实际模型的feature_names）
            actual_feature_names = (
                self._model.get_booster().feature_names
                if hasattr(self._model.get_booster(), "feature_names")
                else None
            )
            if actual_feature_names:
                self._feature_columns = actual_feature_names
                logger.info(f"✅ 使用模型实际的特征名称: {self._feature_columns}")
            else:
                self._feature_columns = [
                    "feature_0",
                    "feature_1",
                    "feature_2",
                    "feature_3",
                    "feature_4",
                ]
                logger.warning(
                    f"⚠️ 无法获取模型特征名称，使用默认值: {self._feature_columns}"
                )

            logger.info(
                f"✅ 模型设置完成，特征列: {len(self._feature_columns)}, 模型版本: {self._model_metadata.get('model_version', 'unknown')}"
            )

        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            # 降级到Mock模式
            logger.warning("🔄 降级到Mock模式")
            self._model = None
            self._model_metadata = {
                "model_version": "mock_v1",
                "target_classes": ["平局", "主队胜", "客队胜"],
            }
            self._feature_columns = [
                "home_team_id",
                "away_team_id",
                "home_last_5_points",
                "away_last_5_points",
                "home_last_5_avg_goals",
                "away_last_5_avg_goals",
                "h2h_last_3_home_wins",
                "home_last_5_goal_diff",
                "away_last_5_goal_diff",
                "home_win_streak",
                "away_win_streak",
                "home_last_5_win_rate",
                "away_last_5_win_rate",
                "home_rest_days",
                "away_rest_days",
            ]

    def _load_feature_data(self):
        """加载特征数据用于推理."""
        try:
            dataset_path = Path("data/dataset_v1.csv")

            if not dataset_path.exists():
                logger.warning(f"⚠️ 特征数据文件不存在: {dataset_path}")
                self._feature_data = pd.DataFrame()
                return

            # 加载特征数据
            self._feature_data = pd.read_csv(dataset_path)

            # 确保日期列是datetime类型
            if "match_date" in self._feature_data.columns:
                self._feature_data["match_date"] = pd.to_datetime(
                    self._feature_data["match_date"]
                )

            logger.info(f"✅ 特征数据加载成功: {len(self._feature_data)} 条记录")

        except Exception as e:
            logger.error(f"❌ 特征数据加载失败: {e}")
            self._feature_data = pd.DataFrame()

    async def _get_features_for_match(self, match_id: int) -> dict | None:
        """根据比赛ID从数据库获取特征数据.

        Args:
            match_id: 比赛ID

        Returns:
            特征数据字典，如果未找到返回None
        """
        try:
            logger.info(f"🔍 Fetching features from DB for match {match_id}")

            # 导入数据库连接管理器
            from src.database.connection import DatabaseManager

            # 获取数据库管理器实例
            db_manager = DatabaseManager()

            # 确保数据库管理器已初始化
            if not hasattr(db_manager, "_initialized") or not db_manager._initialized:
                from src.core.config import get_settings

                settings = get_settings()
                db_manager.initialize(database_url=settings.database_url)

            # 使用异步会话查询数据库
            async with db_manager.get_async_session() as session:
                from sqlalchemy import text

                # 执行SQL查询
                result = await session.execute(
                    text(
                        "SELECT feature_data FROM features WHERE match_id = :match_id"
                    ),
                    {"match_id": match_id},
                )
                row = result.first()

                if row and row[0]:  # feature_data 存在
                    # 处理JSONB对象，确保正确转换为Python字典
                    features_data = row[0]
                    if isinstance(features_data, str):
                        # 如果是字符串，需要解析JSON
                        features_dict = json.loads(features_data)
                    elif hasattr(features_data, '__dict__'):
                        # 如果是对象，尝试转换为字典
                        features_dict = dict(features_data)
                    else:
                        # 如果已经是字典，直接使用
                        features_dict = features_data

                    logger.info(
                        f"✅ Successfully fetched features for match {match_id}: {len(features_dict)} features"
                    )
                    return features_dict
                else:
                    logger.warning(f"⚠️ No features found for match {match_id}")
                    return None

        except Exception as e:
            logger.error(f"❌ 获取特征失败 (match_id={match_id}): {e}")
            return self._get_default_features()

    def _get_default_features(self) -> dict:
        """获取默认特征数据."""
        return {
            "home_team_id": 1,
            "away_team_id": 2,
            "home_last_5_points": 6,
            "away_last_5_points": 7,
            "home_last_5_avg_goals": 1.4,
            "away_last_5_avg_goals": 1.5,
            "h2h_last_3_home_wins": 1,
            "home_last_5_goal_diff": 0,
            "away_last_5_goal_diff": 0,
            "home_win_streak": 0,
            "away_win_streak": 0,
            "home_last_5_win_rate": 0.37,
            "away_last_5_win_rate": 0.38,
            "home_rest_days": 7,
            "away_rest_days": 7,
        }

    async def predict_match(self, match_id: int) -> dict:
        """对指定比赛进行预测.

        Args:
            match_id: 比赛ID

        Returns:
            包含预测结果的字典
        """
        # 如果XGBoost不可用，返回Mock数据
        if not HAVE_XGBOOST:
            logger.info(f"🔮 Mock模式预测比赛 {match_id}")
            return {
                "match_id": match_id,
                "prediction": "home_win",
                "confidence": 0.60,
                "home_win_prob": 0.6,
                "draw_prob": 0.2,
                "away_win_prob": 0.2,
                "status": "mock_data",
                "note": "XGBoost not installed (Docker lightweight mode)",
                "success": True,
                "model_version": "mock_v1",
                "suggestion": "Mock模式预测，主队胜，置信度中等(60%)",
            }

        try:
            logger.info(f"🔮 开始预测比赛 {match_id}")

            # 获取特征数据
            features = await self._get_features_for_match(match_id)
            if features is None:
                return {
                    "match_id": match_id,
                    "error": "无法获取比赛特征数据",
                    "success": False,
                }

            # 使用v2模型的真实特征列进行预测
            try:
                logger.info("🎯 使用v2模型的13个真实特征进行预测")
                logger.info(f"📋 模型特征列: {self._feature_columns}")

                # 直接使用模型的特征列映射，确保特征顺序一致
                feature_vector = []
                for col in self._feature_columns:
                    if col in features:
                        feature_vector.append(features[col])
                    else:
                        logger.warning(f"⚠️ 缺失特征列: {col}，使用默认值0")
                        feature_vector.append(0)

                logger.info(f"✅ 构建的特征向量: {feature_vector}")

            except Exception as e:
                logger.error(f"❌ 特征映射失败: {e}")
                # 使用默认特征向量（基于新特征的默认值）
                feature_vector = [6, 7, 1.4, 1.5, 0, 0, 0, 0, 0.37, 0.38, 7, 7, 1]

            # 转换为DataFrame
            feature_df = pd.DataFrame([feature_vector], columns=self._feature_columns)

            # 进行预测
            prediction = self._model.predict(feature_df)[0]
            probabilities = self._model.predict_proba(feature_df)[0]

            # 根据模型类别数量动态映射结果
            model_classes = self._model.classes_
            if len(model_classes) == 2:
                # 二分类模型：0=平局/客队胜, 1=主队胜
                result_names = {0: "away_or_draw", 1: "home_win"}
            else:
                # 三分类模型 - 支持V4模型的英文标签和旧模型的中文标签
                if hasattr(self._model, 'classes_') and len(self._model.classes_) == 3:
                    # 检查模型标签类型
                    class_list = list(self._model.classes_)
                    if 'away_win' in class_list and 'draw' in class_list and 'home_win' in class_list:
                        # V4模型英文标签映射 (away_win, draw, home_win)
                        away_idx = class_list.index('away_win')
                        draw_idx = class_list.index('draw')
                        home_idx = class_list.index('home_win')
                        result_names = {away_idx: "客队胜", draw_idx: "平局", home_idx: "主队胜"}
                        logger.info(f"🏷️ 使用V4模型英文标签映射: {result_names}")
                    elif 'Away' in class_list and 'Draw' in class_list and 'Home' in class_list:
                        # 新模型英文标签映射
                        away_idx = class_list.index('Away')
                        draw_idx = class_list.index('Draw')
                        home_idx = class_list.index('Home')
                        result_names = {away_idx: "客队胜", draw_idx: "平局", home_idx: "主队胜"}
                        logger.info(f"🏷️ 使用新模型英文标签映射: {result_names}")
                    else:
                        # 旧模型中文标签映射
                        result_names = {0: "平局", 1: "主队胜", 2: "客队胜"}
                else:
                    # 默认中文标签映射
                    result_names = {0: "平局", 1: "主队胜", 2: "客队胜"}

            # 计算置信度（最高概率）
            confidence = max(probabilities)

            # 生成投注建议
            if confidence > 0.6:
                suggestion = (
                    f"模型预测{result_names[prediction]}，置信度较高({confidence:.1%})"
                )
            elif confidence > 0.4:
                suggestion = f"模型倾向{result_names[prediction]}，但不确定性较大({confidence:.1%})"
            else:
                suggestion = f"预测结果不确定性很高({confidence:.1%})，建议谨慎参考"

            # 根据模型类型格式化概率输出
            if len(model_classes) == 2:
                # 二分类模型：probabilities = [P(非主队胜), P(主队胜)]
                prob_home_win = round(float(probabilities[1]), 3)
                prob_not_home_win = round(float(probabilities[0]), 3)

                # 将非主队胜概率分配给平局和客队胜
                prob_draw = round(prob_not_home_win * 0.3, 3)  # 30% 分配给平局
                prob_away_win = round(prob_not_home_win * 0.7, 3)  # 70% 分配给客队胜

                predicted_outcome = "home" if prediction == 1 else "away_or_draw"
            else:
                # 三分类模型 - 智能处理V4模型、新模型和旧模型的标签顺序
                class_list = list(model_classes)

                # 检查是否是V4模型的英文标签 (away_win, draw, home_win)
                if 'away_win' in class_list and 'draw' in class_list and 'home_win' in class_list:
                    # V4模型：按实际索引获取概率
                    away_prob = float(probabilities[class_list.index('away_win')])
                    draw_prob = float(probabilities[class_list.index('draw')])
                    home_prob = float(probabilities[class_list.index('home_win')])

                    prob_home_win = round(home_prob, 3)
                    prob_draw = round(draw_prob, 3)
                    prob_away_win = round(away_prob, 3)

                    # 根据预测结果确定outcome
                    if prediction == class_list.index('home_win'):
                        predicted_outcome = "home"
                    elif prediction == class_list.index('draw'):
                        predicted_outcome = "draw"
                    else:
                        predicted_outcome = "away"

                    logger.info(f"🎯 V4模型概率分布: Home={prob_home_win}, Draw={prob_draw}, Away={prob_away_win}")
                elif 'Away' in class_list and 'Draw' in class_list and 'Home' in class_list:
                    # 新模型：按实际索引获取概率
                    away_prob = float(probabilities[class_list.index('Away')])
                    draw_prob = float(probabilities[class_list.index('Draw')])
                    home_prob = float(probabilities[class_list.index('Home')])

                    prob_home_win = round(home_prob, 3)
                    prob_draw = round(draw_prob, 3)
                    prob_away_win = round(away_prob, 3)

                    # 根据预测结果确定outcome
                    if prediction == class_list.index('Home'):
                        predicted_outcome = "home"
                    elif prediction == class_list.index('Draw'):
                        predicted_outcome = "draw"
                    else:
                        predicted_outcome = "away"

                    logger.info(f"🎯 新模型概率分布: Home={prob_home_win}, Draw={prob_draw}, Away={prob_away_win}")
                else:
                    # 旧模型：假设顺序是 [平局, 主队胜, 客队胜]
                    prob_home_win = round(float(probabilities[1]), 3)
                    prob_draw = round(float(probabilities[0]), 3) if len(probabilities) > 2 else 0.0
                    prob_away_win = round(float(probabilities[2]), 3) if len(probabilities) > 2 else 0.0

                    predicted_outcome = (
                        "home"
                        if prediction == 1
                        else ("draw" if prediction == 0 else "away")
                    )

            result = {
                "match_id": match_id,
                "prediction": result_names[prediction],
                "predicted_outcome": predicted_outcome,
                "home_win_prob": prob_home_win,
                "draw_prob": prob_draw,
                "away_win_prob": prob_away_win,
                "confidence": float(confidence),
                "suggestion": suggestion,
                "success": True,
                "features_used": self._feature_columns,
                "model_version": self._model_metadata.get("model_version", "v1"),
            }

            logger.info(
                f"✅ 预测完成: {result_names[prediction]} (置信度: {confidence:.1%})"
            )
            return result

        except Exception as e:
            logger.error(f"❌ 预测失败 (match_id={match_id}): {e}")
            return {
                "match_id": match_id,
                "error": f"预测服务错误: {str(e)}",
                "success": False,
            }

    def predict_batch(self, match_ids: list[int]) -> list[dict]:
        """批量预测比赛结果.

        Args:
            match_ids: 比赛ID列表

        Returns:
            预测结果列表
        """
        results = []
        for match_id in match_ids:
            result = self.predict_match(match_id)
            results.append(result)
        return results

    def get_model_info(self) -> dict:
        """获取模型信息."""
        if not self._model_metadata:
            return {"error": "模型未加载"}

        return {
            "model_version": self._model_metadata.get("model_version"),
            "training_date": self._model_metadata.get("training_date"),
            "feature_count": len(self._feature_columns),
            "target_classes": self._model_metadata.get("target_classes"),
            "test_accuracy": self._model_metadata.get("test_accuracy"),
            "feature_names": self._feature_columns,
        }

    def health_check(self) -> dict:
        """健康检查."""
        try:
            if not HAVE_XGBOOST:
                return {
                    "status": "degraded",
                    "model_loaded": False,
                    "feature_data_loaded": not self._feature_data.empty,
                    "feature_count": len(self._feature_columns)
                    if self._feature_columns
                    else 0,
                    "initialized": self._initialized,
                    "note": "XGBoost not available - running in mock mode",
                    "xgboost_available": False,
                }

            model_loaded = self._model is not None
            feature_data_loaded = self._feature_data is not None
            feature_count = len(self._feature_columns) if self._feature_columns else 0

            return {
                "status": "healthy" if model_loaded else "unhealthy",
                "model_loaded": model_loaded,
                "feature_data_loaded": not self._feature_data.empty
                if feature_data_loaded
                else False,
                "feature_count": feature_count,
                "initialized": self._initialized,
                "xgboost_available": True,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# 全局推理服务实例
inference_service = InferenceService()
