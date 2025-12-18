"""
生产模型加载器
单例模式加载Phase 2训练的XGBoost模型和相关工件

功能:
1. 启动时加载模型工件 (仅一次)
2. 提供预测接口
3. 确保线程安全和内存效率

作者: Backend Engineer
创建时间: 2025-12-10
版本: 1.0.0 - Phase 3 Inference
"""

import json
import pickle
import logging
from pathlib import Path
from typing import Dict, Any
import numpy as np
import xgboost as xgb

from ..features.enhanced_feature_extractor import (
    EnhancedFeatureExtractor,
    FeatureConfig,
)

logger = logging.getLogger(__name__)


class ModelLoader:
    """单例模型加载器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.model = None
            self.label_encoder = None
            self.feature_columns = None
            self.feature_extractor = None
            self.model_metadata = None
            self._initialized = True
            logger.info("🔧 ModelLoader实例已创建")

    def load_model_artifacts(self) -> bool:
        """加载模型工件"""
        try:
            logger.info("📦 开始加载模型工件...")

            models_dir = Path("models")
            model_name = "football_xgboost_baseline"

            # 1. 加载XGBoost模型 (JSON格式)
            model_json_path = models_dir / f"{model_name}.json"
            if not model_json_path.exists():
                raise FileNotFoundError(f"模型文件不存在: {model_json_path}")

            self.model = xgb.XGBClassifier()
            self.model.load_model(str(model_json_path))
            logger.info(f"   ✅ XGBoost模型已加载: {model_json_path}")

            # 2. 加载LabelEncoder
            encoder_path = models_dir / f"{model_name}_label_encoder.pkl"
            if not encoder_path.exists():
                raise FileNotFoundError(f"编码器文件不存在: {encoder_path}")

            with open(encoder_path, "rb") as f:
                self.label_encoder = pickle.load(f)
            logger.info(f"   ✅ LabelEncoder已加载: {encoder_path}")

            # 3. 加载特征列表
            features_path = models_dir / f"{model_name}_features.json"
            if not features_path.exists():
                raise FileNotFoundError(f"特征文件不存在: {features_path}")

            with open(features_path, "r") as f:
                features_data = json.load(f)
                self.feature_columns = features_data["feature_columns"]
            logger.info(f"   ✅ 特征列表已加载: {len(self.feature_columns)}个特征")

            # 4. 加载模型元数据
            metadata_path = models_dir / f"{model_name}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    self.model_metadata = json.load(f)
                logger.info("   ✅ 模型元数据已加载")

            # 5. 初始化特征提取器
            config = FeatureConfig(
                include_metadata=True,
                include_basic_stats=True,
                include_advanced_stats=True,
                include_context=True,
                include_derived_features=True,
            )
            self.feature_extractor = EnhancedFeatureExtractor(config)
            logger.info("   ✅ 特征提取器已初始化")

            logger.info("🎉 所有模型工件加载完成!")
            return True

        except Exception as e:
            logger.error(f"❌ 模型工件加载失败: {e}")
            return False

    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return (
            self.model is not None
            and self.label_encoder is not None
            and self.feature_columns is not None
            and self.feature_extractor is not None
        )

    def predict(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        对单场比赛进行预测

        Args:
            match_data: 比赛数据字典

        Returns:
            预测结果字典
        """
        if not self.is_loaded():
            raise RuntimeError("模型未加载，请先调用load_model_artifacts()")

        try:
            # 1. 特征提取
            features = self.feature_extractor.extract_features(match_data)

            # 2. 确保特征顺序正确
            feature_vector = []
            missing_features = []

            for feature_name in self.feature_columns:
                if feature_name in features:
                    value = features[feature_name]
                    # 处理None/NaN值
                    if value is None or (isinstance(value, float) and np.isnan(value)):
                        feature_vector.append(0.0)
                    else:
                        feature_vector.append(float(value))
                else:
                    feature_vector.append(0.0)  # 默认值
                    missing_features.append(feature_name)

            if missing_features:
                logger.warning(f"⚠️ 缺失特征: {missing_features[:5]}...")  # 只显示前5个

            # 3. 转换为numpy数组
            X = np.array(feature_vector).reshape(1, -1)

            # 4. 模型预测
            prediction_encoded = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]

            # 5. 解码预测结果
            prediction_label = self.label_encoder.inverse_transform(
                [prediction_encoded]
            )[0]

            # 6. 构建概率字典
            class_names = self.label_encoder.classes_
            prob_dict = {}
            for i, class_name in enumerate(class_names):
                prob_dict[class_name] = float(probabilities[i])

            # 7. 确保概率和为1
            total_prob = sum(prob_dict.values())
            if total_prob > 0:
                prob_dict = {k: v / total_prob for k, v in prob_dict.items()}

            return {
                "prediction": prediction_label,
                "probabilities": prob_dict,
                "confidence": max(prob_dict.values()),
                "feature_count": len(self.feature_columns),
                "missing_features": len(missing_features),
            }

        except Exception as e:
            logger.error(f"❌ 预测失败: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        if not self.is_loaded():
            return {"status": "not_loaded"}

        info = {
            "status": "loaded",
            "model_type": "XGBoost Classifier",
            "feature_count": len(self.feature_columns) if self.feature_columns else 0,
            "target_classes": list(self.label_encoder.classes_)
            if self.label_encoder
            else [],
            "model_metadata": self.model_metadata or {},
        }

        return info


# 全局模型加载器实例
model_loader = ModelLoader()
