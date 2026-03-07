#!/usr/bin/env python3
"""
V26.8 推理引擎 - ModelDispatcher & Predictor
==============================================

职责:
- V26.4 Predictor: 统一推理接口
- V26.8 ModelDispatcher: 联赛专项模型分发器

从 src.ml.engine 拆分 (Genesis.GoldenLayout)
"""

import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# V26.4 Predictor - 统一推理接口
# ============================================================================


class Predictor:
    """
    V26.4 统一推理类

    职责:
    - 加载和管理训练好的模型
    - 集成特征适配层
    - 提供统一的预测接口
    - 支持多种模型类型
    """

    # 预测结果映射
    LABEL_MAPPING = {0: "Away", 1: "Draw", 2: "Home"}

    def __init__(self, model_path: str | None = None, model_type: str = "v26_mini"):
        """
        初始化预测器

        Args:
            model_path: 模型文件路径，为 None 则使用默认路径
            model_type: 模型类型 (v26_mini, v19_rolling, v26_5_production, v26_6_pre_match, v26_7_aligned)
        """

        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_names = []

        # 加载特征适配器
        from src.ml.feature_adapter import FeatureAdapterFactory, ModelType

        # V26.8 联赛专项模型（使用 V26_6 适配器，特征集相同）
        if model_type.startswith("v26_8_"):
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_6_PRE_MATCH)
        elif model_type == "v26_mini":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_MINI)
        elif model_type == "v19_rolling":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V19_ROLLING)
        elif model_type == "v26_5_production":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_5_PRODUCTION)
        elif model_type == "v26_6_pre_match":
            self.adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_6_PRE_MATCH)
        elif model_type == "v26_7_aligned":
            self.adapter = FeatureAdapterFactory.get_adapter(
                ModelType.V26_6_PRE_MATCH
            )  # Reuse V26_6 adapter
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        # 加载模型
        if model_path is None:
            model_path = self._get_default_model_path(model_type)

        if os.path.exists(model_path):
            self._load_model(model_path)
        else:
            logger.warning(f"模型文件不存在: {model_path}，将创建新的微型模型")
            self._create_mini_model()

    def _get_default_model_path(self, model_type: str) -> str:
        """获取默认模型路径"""
        # V26.8 联赛专项模型
        if model_type.startswith("v26_8_"):
            return f"model_zoo/production/{model_type}_production.pkl"
        if model_type == "v26_mini":
            return "model_zoo/production/v26.5_mini.pkl"
        if model_type == "v19_rolling":
            return "model_zoo/production/v19.4_draw_sensitivity_model.pkl"
        if model_type == "v26_5_production":
            return "model_zoo/production/v26.5_production.pkl"
        if model_type == "v26_6_pre_match":
            return "model_zoo/production/v26.6_pre_match.pkl"
        if model_type == "v26_7_aligned":
            return "model_zoo/production/v26.7_aligned_production.pkl"
        return "model_zoo/production/v26.5_mini.pkl"

    def _load_model(self, model_path: str):
        """加载模型文件"""
        import joblib

        logger.info(f"加载模型: {model_path}")
        model_data = joblib.load(model_path)

        # 处理不同的模型格式
        if isinstance(model_data, dict):
            self.model = model_data.get("model")
            self.scaler = model_data.get("scaler")
            self.feature_names = model_data.get("feature_columns", [])
        else:
            self.model = model_data
            self.scaler = None
            self.feature_names = (
                list(self.model.feature_names_in_)
                if hasattr(self.model, "feature_names_in_")
                else []
            )

        logger.info(f"✅ 模型加载成功，特征数: {len(self.feature_names)}")

    def _create_mini_model(self):
        """创建微型模型（用于测试）"""
        import numpy as np
        from sklearn.preprocessing import StandardScaler
        import xgboost as xgb

        logger.info("创建微型 V26.4 模型...")

        # V26 微型特征集
        mini_features = self.adapter.get_required_features()

        # 创建简单的训练数据
        np.random.seed(42)
        n_samples = 100
        X = np.random.randn(n_samples, len(mini_features))
        y = np.random.randint(0, 3, n_samples)

        # 训练微型模型
        params = {
            "n_estimators": 50,
            "max_depth": 3,
            "learning_rate": 0.1,
            "objective": "multi:softprob",
            "num_class": 3,
            "random_state": 42,
        }

        self.model = xgb.XGBClassifier(**params)
        self.model.fit(X, y)

        # 创建 scaler
        self.scaler = StandardScaler()
        self.scaler.fit(X)

        self.feature_names = mini_features

        # 保存模型
        self.save()

        logger.info("✅ 微型模型创建完成")

    def predict(self, raw_match_data: dict) -> dict:
        """
        对原始比赛数据进行预测

        Args:
            raw_match_data: V25.1 提取的原始特征字典

        Returns:
            预测结果字典，包含 prediction, probabilities, confidence
        """
        if self.model is None:
            raise ValueError("模型未加载")

        # 1. 特征适配
        adaptation_result = self.adapter.adapt(raw_match_data)

        if not adaptation_result.success:
            raise ValueError(f"特征适配失败: {adaptation_result.errors}")

        features_df = adaptation_result.features

        # 2. 特征标准化
        features_scaled = self.scaler.transform(features_df) if self.scaler else features_df.values

        # 3. 模型预测
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]

        return {
            "prediction": self.LABEL_MAPPING[prediction],
            "probabilities": {
                "Away": float(probabilities[0]),
                "Draw": float(probabilities[1]),
                "Home": float(probabilities[2]),
            },
            "confidence": float(probabilities.max()),
            "model_type": self.model_type,
        }

    def predict_batch(self, raw_match_data_list: list[dict]) -> list[dict]:
        """
        批量预测

        Args:
            raw_match_data_list: 原始比赛数据列表

        Returns:
            预测结果列表
        """
        return [self.predict(data) for data in raw_match_data_list]

    def save(self, path: str | None = None):
        """保存模型"""
        import joblib

        if path is None:
            path = self._get_default_model_path(self.model_type)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_columns": self.feature_names,
            "model_type": self.model_type,
            "version": "26.4",
        }

        joblib.dump(model_data, path)
        logger.info(f"✅ 模型已保存: {path}")

    @classmethod
    def create_v26_mini(cls) -> "Predictor":
        """创建 V26.5 微型预测器"""
        predictor = cls(model_type="v26_mini")
        predictor._create_mini_model()
        return predictor

    @classmethod
    def create_v26_5_production(cls) -> "Predictor":
        """创建 V26.5 生产预测器（加载真实训练的模型）"""
        return cls(model_type="v26_5_production")

    @classmethod
    def create_v26_6_pre_match(cls) -> "Predictor":
        """创建 V26.6 真赛前预测器（无数据泄露）"""
        return cls(model_type="v26_6_pre_match")

    @classmethod
    def create_v26_7_aligned(cls) -> "Predictor":
        """创建 V26.7 对齐预测器（训练-推理完全对齐）"""
        return cls(model_type="v26_7_aligned")


# ============================================================================
# V26.8 ModelDispatcher - 联赛专项模型分发器
# ============================================================================


class ModelDispatcher:
    """
    V26.8 联赛专项模型分发器（V5 Pure - 含降级策略）

    职责:
    - 根据比赛所属联赛自动选择合适的模型
    - 优先使用联赛专项模型，回退使用通用模型
    - 返回预测结果时标注模型来源
    - Serie A 数据不足，强制回退到通用模型

    模型映射（V5 Pure 纯净过滤）:
    - Premier League (league_id=47): v26.8_epl ✅ 1751 场纯净数据
    - Serie A (league_id=135): ❌ 数据不足 (4场)，强制回退
    - La Liga (league_id=55): v26.8_la_liga ✅ 1640 场纯净数据
    - Bundesliga (league_id=54): v26.8_bund ✅ 1432 场纯净数据
    - Ligue 1 (league_id=61): v26.8_ligue1 ✅ 1489 场纯净数据
    - 其他联赛: v26.7_aligned (通用底座)
    """

    # 联赛 ID 到模型映射
    LEAGUE_MODEL_MAPPING = {
        47: "v26_8_epl",  # Premier League ✅
        135: "v26_8_serie_a",  # Serie A ⚠️ 数据不足，将强制回退
        55: "v26_8_la_liga",  # La Liga ✅
        54: "v26_8_bund",  # Bundesliga ✅
        61: "v26_8_ligue1",  # Ligue 1 ✅
    }

    # V5 Pure: 数据不足联赛（强制回退到通用模型）
    INSUFFICIENT_DATA_LEAGUES = {135}  # Serie A (league_id=135)

    # 回退通用模型
    FALLBACK_MODEL = "v26_7_aligned"

    # 模型文件路径映射
    MODEL_PATHS = {
        "v26_7_aligned": "model_zoo/production/v26.7_aligned_production.pkl",
        "v26_8_epl": "model_zoo/production/v26.8_epl_production.pkl",
        "v26_8_serie_a": "model_zoo/production/v26.8_serie_a_production.pkl",
        "v26_8_la_liga": "model_zoo/production/v26.8_la_liga_production.pkl",
        "v26_8_bund": "model_zoo/production/v26.8_bund_production.pkl",
        "v26_8_ligue1": "model_zoo/production/v26.8_ligue1_production.pkl",
    }

    def __init__(self):
        """初始化分发器"""
        self.loaded_models = {}
        self._load_base_model()

    def _load_base_model(self):
        """加载通用底座模型（确保至少有一个可用模型）"""
        base_model_path = self.MODEL_PATHS[self.FALLBACK_MODEL]
        if os.path.exists(base_model_path):
            self.loaded_models[self.FALLBACK_MODEL] = Predictor(
                model_path=base_model_path, model_type="v26_7_aligned"
            )
            logger.info(f"✅ 通用底座模型已加载: {self.FALLBACK_MODEL}")
        else:
            logger.warning(f"⚠️  通用底座模型未找到: {base_model_path}")

    def _detect_league(self, match_data: dict) -> int | None:
        """
        检测比赛所属联赛

        Args:
            match_data: 比赛数据字典

        Returns:
            联赛 ID，如果无法检测则返回 None
        """
        # 优先从 league_id 字段获取
        if "league_id" in match_data and match_data["league_id"] is not None:
            return int(match_data["league_id"])

        # 尝试从 league_name 推断
        if "league_name" in match_data:
            league_name = match_data["league_name"].lower()

            # 联赛名称到 ID 的映射
            name_to_id = {
                "premier league": 47,
                "english premier league": 47,
                "epl": 47,
                "serie a": 135,
                "italian serie a": 135,
                "la liga": 55,
                "primera división": 55,
                "bundesliga": 54,
                "german bundesliga": 54,
                "ligue 1": 61,
                "french ligue 1": 61,
            }

            for name, league_id in name_to_id.items():
                if name in league_name:
                    return league_id

        return None

    def _select_model(self, league_id: int | None) -> Predictor:
        """
        选择合适的模型（V5 Pure - 含数据不足降级策略）

        Args:
            league_id: 联赛 ID

        Returns:
            选择的预测器实例
        """
        # V5 Pure: 检查是否为数据不足联赛（强制回退）
        if league_id is not None and league_id in self.INSUFFICIENT_DATA_LEAGUES:
            logger.info(
                f"⚠️  联赛 ID {league_id} 数据不足，强制回退到通用模型 {self.FALLBACK_MODEL}"
            )
            return self._get_fallback_model()

        # 如果有联赛 ID，尝试使用专项模型
        if league_id is not None and league_id in self.LEAGUE_MODEL_MAPPING:
            model_type = self.LEAGUE_MODEL_MAPPING[league_id]
            model_path = self.MODEL_PATHS.get(model_type)

            if model_path and os.path.exists(model_path):
                # 检查是否已加载
                if model_type not in self.loaded_models:
                    try:
                        self.loaded_models[model_type] = Predictor(
                            model_path=model_path, model_type=model_type
                        )
                        logger.info(f"✅ 加载联赛专项模型: {model_type}")
                    except Exception as e:
                        logger.warning(f"⚠️  加载联赛专项模型失败 {model_type}: {e}")
                        # 回退到通用模型
                        return self._get_fallback_model()

                return self.loaded_models[model_type]
            logger.warning(f"⚠️  联赛专项模型文件不存在: {model_path}")

        # 回退到通用模型
        return self._get_fallback_model()

    def _get_fallback_model(self) -> Predictor:
        """获取回退模型（通用底座）"""
        if self.FALLBACK_MODEL in self.loaded_models:
            return self.loaded_models[self.FALLBACK_MODEL]
        raise ValueError(f"回退模型 {self.FALLBACK_MODEL} 未加载！")

    def predict(self, match_data: dict) -> dict:
        """
        执行智能预测（自动选择模型）

        Args:
            match_data: 比赛数据字典，需包含 league_id 或 league_name

        Returns:
            预测结果字典，额外包含 model_source 字段
        """
        # 检测联赛
        league_id = self._detect_league(match_data)

        # 选择模型
        predictor = self._select_model(league_id)

        # 执行预测
        result = predictor.predict(match_data)

        # 添加模型来源信息
        result["model_source"] = predictor.model_type
        result["league_id"] = league_id

        if league_id in self.LEAGUE_MODEL_MAPPING:
            result["model_type"] = "specialized"
            result["league_specific"] = True
        else:
            result["model_type"] = "general"
            result["league_specific"] = False

        logger.info(
            f"预测完成 (联赛ID: {league_id}, 模型: {predictor.model_type}, "
            f"类型: {'专项' if result['league_specific'] else '通用'})"
        )

        return result

    def get_available_models(self) -> dict[str, bool]:
        """获取所有模型的可用状态"""
        availability = {}
        for model_type, model_path in self.MODEL_PATHS.items():
            availability[model_type] = os.path.exists(model_path)
        return availability

    def get_model_info(self) -> dict:
        """获取模型分发器信息（V5 Pure - 含降级策略）"""
        available_models = self.get_available_models()

        return {
            "dispatcher_version": "26.8",
            "dispatcher_phase": "V5_Pure",
            "league_model_mapping": self.LEAGUE_MODEL_MAPPING,
            "insufficient_data_leagues": list(self.INSUFFICIENT_DATA_LEAGUES),
            "insufficient_data_league_names": {135: "Serie A (数据不足: 4 场 < 500 阈值)"},
            "fallback_model": self.FALLBACK_MODEL,
            "available_models": available_models,
            "loaded_models": list(self.loaded_models.keys()),
        }
