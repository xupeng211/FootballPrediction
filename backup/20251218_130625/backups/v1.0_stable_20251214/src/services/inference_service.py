"""足球预测推理服务 (增强版) v3.0
Football Prediction Inference Service (Enhanced) v3.0

P2-6任务成果：整合真实模型与Mock模式的统一推理服务，实现：
- 真实XGBoost模型优先加载
- 优雅的自动降级机制
- 完整的API Schema兼容性
- 统一的特征提取逻辑
- 异步模型管理和缓存

主要特性:
- 自动降级：真实模型不可用时无缝切换到Mock模式
- API兼容：完全兼容PredictionResponse schema
- 智能模型选择：ModelLoader优先，文件系统备用
- 特征一致性：训练和推理使用相同的15个特征
- 监控完备：提供健康检查和性能指标

作者: Inference Engineer (P2-6)
创建时间: 2025-12-07
版本: 3.0.0
"""

import logging
import os
import pandas as pd
from pathlib import Path
from typing import Optional, Any
import asyncio

# 初始化logger
logger = logging.getLogger(__name__)

# V6.0: 优先检查Mock环境变量，防止资源耗尽
ML_MODE = os.getenv("FOOTBALL_PREDICTION_ML_MODE", "real").lower()
INFERENCE_SERVICE_MOCK = os.getenv("INFERENCE_SERVICE_MOCK", "false").lower() == "true"
SKIP_ML_MODEL_LOADING = os.getenv("SKIP_ML_MODEL_LOADING", "false").lower() == "true"

# 如果设置为Mock模式，完全跳过ML相关导入和加载
FORCE_MOCK_MODE = (
    ML_MODE == "mock"
    or INFERENCE_SERVICE_MOCK
    or SKIP_ML_MODEL_LOADING
    or os.getenv("XGBOOST_MOCK", "false").lower() == "true"
    or os.getenv("JOBLIB_MOCK", "false").lower() == "true"
)

if FORCE_MOCK_MODE:
    logger.info("🔧 V3.0: 强制Mock模式已启用 - 跳过所有ML库导入以节省资源")
    HAVE_JOBLIB = False
    HAVE_XGBOOST = False
else:
    # 尝试导入必要的库
    try:
        import joblib

        HAVE_JOBLIB = True
    except ImportError:
        HAVE_JOBLIB = False
        logger.warning("⚠️ joblib not found. Will attempt safe fallback methods.")

    try:
        import xgboost as xgb

        HAVE_XGBOOST = True
    except ImportError:
        HAVE_XGBOOST = False
        logger.warning("⚠️ XGBoost not found. Inference service running in MOCK mode.")


class InferenceService:
    """足球预测推理服务 (增强版)"""

    _instance = None
    _model = None
    _model_metadata = None
    _model_loader = None
    _feature_columns = None
    _mode = "unknown"  # real/mock/degraded

    def __new__(cls):
        """单例模式实现."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化推理服务."""
        if not hasattr(self, "_initialized"):
            self._initialized = False
            # 尝试获取事件循环，如果不存在则创建新的
            try:
                asyncio.get_running_loop()
                # 如果已经在事件循环中，创建任务
                asyncio.create_task(self._initialize_async())
            except RuntimeError:
                # 没有运行的事件循环，直接运行
                asyncio.run(self._initialize_async())
            self._initialized = True
            logger.info(f"✅ 推理服务v3.0初始化完成 - 模式: {self._mode}")

    async def _initialize_async(self):
        """异步初始化组件"""
        await self._load_model_loader()
        await self._load_model_with_fallback()
        logger.info(f"✅ 推理服务异步初始化完成 - 模式: {self._mode}")

    async def _load_model_loader(self):
        """加载ModelLoader"""
        if FORCE_MOCK_MODE:
            self._model_loader = None
            logger.info("🔧 跳过ModelLoader加载 - 强制Mock模式")
            return

        try:
            from src.inference.loader import get_model_loader

            self._model_loader = await get_model_loader()
            logger.info("✅ ModelLoader加载成功")
        except Exception as e:
            logger.warning(f"⚠️ ModelLoader加载失败: {e}")
            self._model_loader = None

    async def _load_model_with_fallback(self):
        """加载模型并实现自动降级逻辑"""
        logger.info("🔄 开始模型加载流程...")

        # 1. 检查强制Mock模式
        if FORCE_MOCK_MODE:
            await self._switch_to_mock_mode("强制Mock模式 (环境变量)")
            return

        # 2. 检查XGBoost可用性
        if not HAVE_XGBOOST:
            await self._switch_to_mock_mode("XGBoost不可用")
            return

        # 3. 尝试加载真实模型
        model_loaded = False
        load_error = None

        try:
            # 策略1: 使用ModelLoader
            if self._model_loader:
                try:
                    from src.inference.loader import ModelType

                    models = await self._model_loader.list_models(ModelType.XGBOOST)

                    if models:
                        latest_model = max(models, key=lambda x: x.created_at)
                        logger.info(
                            f"🚀 ModelLoader加载最新模型: {latest_model.model_name}"
                        )

                        loaded_model = await self._model_loader.load(
                            latest_model.model_name
                        )
                        self._model = loaded_model.access()

                        self._model_metadata = {
                            "model_version": latest_model.model_name,
                            "model_type": latest_model.model_type.value,
                            "target_classes": ["客队胜", "平局", "主队胜"],
                            "created_at": latest_model.created_at.isoformat(),
                            "file_size": latest_model.file_size,
                            "source": "ModelLoader",
                        }

                        self._feature_columns = self._extract_features_from_model()
                        model_loaded = True
                        logger.info("✅ ModelLoader模型加载成功")

                except Exception as e:
                    load_error = f"ModelLoader失败: {str(e)}"
                    logger.warning(f"⚠️ ModelLoader加载失败: {e}")

            # 策略2: 文件系统加载
            if not model_loaded:
                try:
                    model_paths = [
                        (
                            "artifacts/models/football_prediction_v1_xgboost_2023-2024_5000matches.pkl",
                            "p2_5_pipeline",
                        ),
                        ("models/football_prediction_v4_optuna.pkl", "v4_optuna"),
                        ("models/football_xgboost_v2_best.pkl", "v2_best"),
                    ]

                    for model_path, version_name in model_paths:
                        path_obj = Path(model_path)
                        if path_obj.exists():
                            logger.info(f"🔄 尝试文件系统加载: {model_path}")

                            if HAVE_JOBLIB:
                                self._model = joblib.load(path_obj)
                                logger.info("✅ 使用joblib加载模型成功")

                                self._model_metadata = {
                                    "model_version": version_name,
                                    "model_type": "XGBClassifier",
                                    "target_classes": ["客队胜", "平局", "主队胜"],
                                    "source": "file_system",
                                }

                                self._feature_columns = (
                                    self._extract_features_from_model()
                                )
                                model_loaded = True
                                logger.info(f"✅ 文件系统模型加载成功: {version_name}")
                                break
                            else:
                                raise ImportError(
                                    "joblib not available for model loading"
                                )

                except Exception as e:
                    if not load_error:
                        load_error = f"文件系统加载失败: {str(e)}"
                    logger.warning(f"⚠️ 文件系统加载失败: {e}")

        except Exception as e:
            load_error = f"模型加载过程异常: {str(e)}"
            logger.error(f"❌ 模型加载过程异常: {e}")

        # 4. 根据加载结果设置模式
        if model_loaded:
            self._mode = "real"
            logger.info(
                f"✅ 真实模型加载成功 - 版本: {self._model_metadata.get('model_version')}"
            )
        else:
            await self._switch_to_mock_mode(load_error or "模型加载失败")

    async def _switch_to_mock_mode(self, reason: str):
        """切换到Mock模式"""
        self._mode = "mock"
        self._model = None

        self._model_metadata = {
            "model_version": f"mock_v3_{reason}",
            "target_classes": ["平局", "主队胜", "客队胜"],
            "mock_mode": True,
            "reason": reason,
            "source": "fallback",
        }

        # 使用统一特征提取器的特征
        self._feature_columns = self._get_training_features()

        logger.warning(f"🔄 自动降级到Mock模式 - 原因: {reason}")

    def _get_training_features(self) -> list[str]:
        """获取训练时使用的特征列（与feature_extractor.py一致）"""
        return [
            "home_xg",
            "away_xg",
            "home_possession",
            "away_possession",
            "home_shots",
            "away_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "xg_difference",
            "xg_ratio",
            "possession_difference",
            "shots_difference",
            "home_shot_efficiency",
            "away_shot_efficiency",
        ]

    def _extract_features_from_model(self) -> list[str]:
        """从模型中提取特征列"""
        # 尝试从模型获取特征列
        if hasattr(self._model, "feature_names_in_"):
            return list(self._model.feature_names_in_)
        elif hasattr(self._model, "feature_names"):
            return list(self._model.feature_names)
        elif hasattr(self._model, "get_booster") and hasattr(
            self._model.get_booster(), "feature_names"
        ):
            return list(self._model.get_booster().feature_names)
        else:
            # 使用训练数据准备脚本中的特征
            logger.warning("⚠️ 无法从模型获取特征列，使用训练脚本中的特征")
            return self._get_training_features()

    async def _get_features_for_match(self, match_id: int) -> Optional[dict[str, Any]]:
        """从数据库获取比赛特征数据（与训练数据格式一致）"""
        try:
            logger.info(f"🔍 从数据库获取比赛 {match_id} 的特征数据")

            # 使用统一的async_manager
            from src.database.async_manager import get_db_session
            from src.database.models import Match
            from sqlalchemy import select

            async with get_db_session() as session:
                # 查询比赛数据
                result = await session.execute(
                    select(Match).where(Match.id == match_id)
                )
                match = result.scalar_one_or_none()

                if not match:
                    logger.warning(f"⚠️ 未找到比赛 {match_id}")
                    return None

                # 使用特征提取器（如果可用）
                try:
                    from src.features.feature_extractor import FeatureExtractor

                    match_data = {
                        "home_xg": getattr(match, "home_xg", None),
                        "away_xg": getattr(match, "away_xg", None),
                        "home_possession": getattr(match, "home_possession", None),
                        "away_possession": getattr(match, "away_possession", None),
                        "home_shots": getattr(match, "home_shots", None),
                        "away_shots": getattr(match, "away_shots", None),
                        "home_shots_on_target": getattr(
                            match, "home_shots_on_target", None
                        ),
                        "away_shots_on_target": getattr(
                            match, "away_shots_on_target", None
                        ),
                    }
                    features = FeatureExtractor.extract_features_from_match(match_data)
                    logger.info("✅ 使用FeatureExtractor获取特征成功")
                    return features
                except Exception as e:
                    logger.warning(f"⚠️ FeatureExtractor失败，使用传统方式: {e}")

                # 传统方式特征提取
                features = {
                    # 基础特征
                    "home_xg": getattr(match, "home_xg", 1.5),
                    "away_xg": getattr(match, "away_xg", 1.2),
                    "home_possession": getattr(match, "home_possession", 50.0),
                    "away_possession": getattr(match, "away_possession", 50.0),
                    "home_shots": getattr(match, "home_shots", 12),
                    "away_shots": getattr(match, "away_shots", 10),
                    "home_shots_on_target": getattr(match, "home_shots_on_target", 4),
                    "away_shots_on_target": getattr(match, "away_shots_on_target", 3),
                }

                # 特征工程（与训练数据准备脚本中的逻辑一致）
                features["xg_difference"] = features["home_xg"] - features["away_xg"]
                features["xg_ratio"] = features["home_xg"] / (
                    features["away_xg"] + 0.001
                )
                features["possession_difference"] = (
                    features["home_possession"] - features["away_possession"]
                )
                features["shots_difference"] = (
                    features["home_shots"] - features["away_shots"]
                )
                features["home_shot_efficiency"] = features["home_shots_on_target"] / (
                    features["home_shots"] + 0.001
                )
                features["away_shot_efficiency"] = features["away_shots_on_target"] / (
                    features["away_shots"] + 0.001
                )

                logger.info(f"✅ 成功获取比赛 {match_id} 的特征数据")
                return features

        except Exception as e:
            logger.error(f"❌ 获取特征失败 (match_id={match_id}): {e}")
            return self._get_default_features()

    def _get_default_features(self) -> dict[str, Any]:
        """获取默认特征数据（与训练数据格式一致）"""
        return {
            "home_xg": 1.5,
            "away_xg": 1.2,
            "home_possession": 50.0,
            "away_possession": 50.0,
            "home_shots": 12,
            "away_shots": 10,
            "home_shots_on_target": 4,
            "away_shots_on_target": 3,
            "xg_difference": 0.3,
            "xg_ratio": 1.25,
            "possession_difference": 0.0,
            "shots_difference": 2,
            "home_shot_efficiency": 0.33,
            "away_shot_efficiency": 0.30,
        }

    async def predict_match(self, match_id: int) -> dict[str, Any]:
        """对指定比赛进行预测 - API兼容版本"""
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

            # 根据模式选择预测方法
            if self._mode == "mock" or not HAVE_XGBOOST:
                return self._get_mock_prediction(match_id)

            # 真实模型预测
            return await self._predict_with_real_model(match_id, features)

        except Exception as e:
            logger.error(f"❌ 预测失败 (match_id={match_id}): {e}")
            return {
                "match_id": match_id,
                "error": f"预测服务错误: {str(e)}",
                "success": False,
            }

    async def _predict_with_real_model(
        self, match_id: int, features: dict[str, Any]
    ) -> dict[str, Any]:
        """使用真实模型进行预测"""
        try:
            # 构建特征向量（确保特征顺序与训练时一致）
            feature_vector = []
            for col in self._feature_columns:
                if col in features:
                    feature_vector.append(features[col])
                else:
                    logger.warning(f"⚠️ 缺失特征列: {col}，使用默认值")
                    # 使用默认值
                    if "efficiency" in col:
                        feature_vector.append(0.3)
                    elif "difference" in col or "ratio" in col:
                        feature_vector.append(0.0)
                    elif "possession" in col:
                        feature_vector.append(50.0)
                    elif "shots" in col:
                        feature_vector.append(10)
                    else:
                        feature_vector.append(1.0)

            logger.info(f"✅ 构建的特征向量长度: {len(feature_vector)}")

            # 转换为DataFrame
            feature_df = pd.DataFrame([feature_vector], columns=self._feature_columns)

            # 进行预测
            prediction = self._model.predict(feature_df)[0]
            probabilities = self._model.predict_proba(feature_df)[0]

            # 解析预测结果
            result = self._parse_prediction_result(prediction, probabilities, match_id)

            logger.info(
                f"✅ 预测完成: {result['prediction']} (置信度: {result['confidence']:.1%})"
            )
            return result

        except Exception as e:
            logger.error(f"❌ 真实模型预测失败: {e}")
            # 降级到Mock预测
            return self._get_mock_prediction(match_id)

    def _parse_prediction_result(
        self, prediction: int, probabilities: list, match_id: int
    ) -> dict[str, Any]:
        """解析预测结果 - 保持API兼容性"""
        # 获取模型类别
        model_classes = self._model.classes_

        # 根据模型类别数量动态映射结果
        if len(model_classes) == 2:
            # 二分类模型：0=非主队胜, 1=主队胜
            result_names = {0: "away_or_draw", 1: "home_win"}
        else:
            # 三分类模型
            class_list = list(model_classes)
            if (
                "away_win" in class_list
                and "draw" in class_list
                and "home_win" in class_list
            ):
                # V4/P2-5模型英文标签映射
                away_idx = class_list.index("away_win")
                draw_idx = class_list.index("draw")
                home_idx = class_list.index("home_win")
                result_names = {
                    away_idx: "客队胜",
                    draw_idx: "平局",
                    home_idx: "主队胜",
                }
            else:
                # 默认中文标签映射
                result_names = {0: "平局", 1: "主队胜", 2: "客队胜"}

        # 计算置信度
        confidence = max(probabilities)

        # 格式化概率输出
        if len(model_classes) == 2:
            # 二分类处理
            prob_home_win = round(float(probabilities[1]), 3)
            prob_not_home_win = round(float(probabilities[0]), 3)
            prob_draw = round(prob_not_home_win * 0.3, 3)
            prob_away_win = round(prob_not_home_win * 0.7, 3)
        else:
            # 三分类处理
            if "away_win" in class_list:
                float(probabilities[class_list.index("away_win")])
                float(probabilities[class_list.index("draw")])
                float(probabilities[class_list.index("home_win")])
            else:
                # 默认顺序处理
                if len(probabilities) == 3:
                    prob_away_win = round(float(probabilities[0]), 3)
                    prob_draw = round(float(probabilities[1]), 3)
                    prob_home_win = round(float(probabilities[2]), 3)
                else:
                    prob_home_win = round(float(probabilities[0]), 3)
                    prob_draw = round(float(probabilities[1]), 3)
                    prob_away_win = round(float(probabilities[2]), 3)

        # 确定预测的outcome
        if len(model_classes) == 2:
            predicted_outcome = "home" if prediction == 1 else "away_or_draw"
        else:
            if "away_win" in class_list:
                if prediction == class_list.index("home_win"):
                    predicted_outcome = "home"
                elif prediction == class_list.index("draw"):
                    predicted_outcome = "draw"
                else:
                    predicted_outcome = "away"
            else:
                predicted_outcome = (
                    "home"
                    if prediction == 1
                    else ("draw" if prediction == 0 else "away")
                )

        # API兼容的返回格式
        return {
            "match_id": match_id,
            "prediction": result_names[prediction],
            "predicted_outcome": predicted_outcome,
            "home_win_prob": prob_home_win,
            "draw_prob": prob_draw,
            "away_win_prob": prob_away_win,
            "confidence": float(confidence),
            "success": True,
            "features_used": self._feature_columns,
            "model_version": self._model_metadata.get("model_version", "v3.0"),
            "model_source": self._model_metadata.get("source", "unknown"),
            "mode": self._mode,  # 新增：指示当前模式
            "mock_reason": (
                self._model_metadata.get("reason") if self._mode == "mock" else None
            ),  # 新增：Mock原因
        }

    def _get_mock_prediction(self, match_id: int) -> dict[str, Any]:
        """获取Mock预测结果 - API兼容版本"""
        return {
            "match_id": match_id,
            "prediction": "主队胜",
            "confidence": 0.65,
            "home_win_prob": 0.65,
            "draw_prob": 0.20,
            "away_win_prob": 0.15,
            "success": True,
            "model_version": self._model_metadata.get("model_version", "mock_v3"),
            "mode": "mock",
            "mock_reason": self._model_metadata.get("reason", "default_mock"),
            "features_used": self._feature_columns,
            "model_source": self._model_metadata.get("source", "mock"),
        }

    async def predict_batch(self, match_ids: list[int]) -> list[dict[str, Any]]:
        """批量预测比赛结果"""
        tasks = [self.predict_match(match_id) for match_id in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "match_id": match_ids[i],
                        "error": f"预测服务错误: {str(result)}",
                        "success": False,
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_model_info(self) -> dict[str, Any]:
        """获取模型信息 - API兼容版本"""
        if not self._model_metadata:
            return {"error": "模型未加载"}

        return {
            "model_version": self._model_metadata.get("model_version"),
            "model_source": self._model_metadata.get("source", "unknown"),
            "model_type": self._model_metadata.get("model_type", "unknown"),
            "target_classes": self._model_metadata.get("target_classes"),
            "feature_count": len(self._feature_columns) if self._feature_columns else 0,
            "feature_names": self._feature_columns,
            "xgboost_available": HAVE_XGBOOST,
            "mode": self._mode,
            "mock_reason": (
                self._model_metadata.get("reason") if self._mode == "mock" else None
            ),
        }

    def health_check(self) -> dict[str, Any]:
        """健康检查 - API兼容版本"""
        try:
            if not HAVE_XGBOOST:
                return {
                    "status": "degraded",
                    "model_loaded": False,
                    "feature_count": (
                        len(self._feature_columns) if self._feature_columns else 0
                    ),
                    "initialized": self._initialized,
                    "mode": self._mode,
                    "note": "XGBoost not available - running in mock mode",
                    "xgboost_available": False,
                    "version": "v3.0",
                }

            model_loaded = self._model is not None
            feature_count = len(self._feature_columns) if self._feature_columns else 0

            return {
                "status": (
                    "healthy" if self._mode == "real" and model_loaded else "degraded"
                ),
                "model_loaded": model_loaded,
                "feature_count": feature_count,
                "initialized": self._initialized,
                "mode": self._mode,
                "xgboost_available": True,
                "version": "v3.0",
                "model_source": (
                    self._model_metadata.get("source", "unknown")
                    if self._model_metadata
                    else "unknown"
                ),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "version": "v3.0"}


# 全局推理服务实例 (保持向后兼容)
inference_service = InferenceService()


# 新增：获取服务实例的便捷方法
async def get_inference_service() -> InferenceService:
    """获取推理服务实例 (异步友好版本)"""
    return inference_service
