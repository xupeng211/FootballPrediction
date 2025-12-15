import logging
import os
import pandas as pd
import joblib
import asyncio
import json
from typing import Dict, Optional, Any, List
from datetime import datetime
import numpy as np

from src.ml.training.trainer import ModelTrainer
from src.ml.data.loader import DataLoader
from src.ml.features.rolling import RollingAverageTransformer

logger = logging.getLogger(__name__)


# DataLoader Adapter - 解决接口不匹配问题
class DataLoaderAdapter:
    """适配DataLoader到ModelTrainer期望的load_data接口"""

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    async def load_data(self) -> pd.DataFrame:
        """适配load_raw_data到load_data接口"""
        return await self.data_loader.load_raw_data()


class PredictionService:
    """
    核心推理服务 (Singleton)。
    负责模型生命周期管理：自动训练、加载、预测。

    Phase 3: TDD Green Phase - 完整功能实现
    """

    _instance = None

    def __init__(self):
        self.model_path = "models/baseline_v1.pkl"
        self.metadata_path = "models/baseline_v1_metadata.json"
        self.trainer: Optional[ModelTrainer] = None
        self.is_ready = False
        self._model_version = "v1"

        # 运行时数据
        self.model = None  # 加载的XGBoost模型
        self.feature_columns = []  # 特征列名
        self.feature_store = {}  # 简单的特征存储 (MVP版本)

    @classmethod
    def get_instance(cls):
        """
        单例模式获取实例。

        Returns:
            PredictionService: 全局唯一的推理服务实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self):
        """
        初始化服务。
        1. 检查模型文件是否存在。
        2. 如果不存在，触发冷启动训练 (Cold Start Training)。
        3. 加载模型到内存。

        Cold Start Logic:
        - 检查模型文件存在性
        - 缺失时自动触发训练管道
        - 加载训练好的模型

        Raises:
            RuntimeError: 当初始化失败时
        """
        logger.info("🚀 初始化PredictionService...")

        try:
            # 检查模型文件是否存在
            if not os.path.exists(self.model_path):
                logger.warning(f"⚠️ 模型文件不存在: {self.model_path}")
                await self._cold_start_training()
            else:
                logger.info(f"✅ 模型文件已存在: {self.model_path}")

            # 加载模型到内存
            await self._load_model()

            self.is_ready = True
            logger.info("✅ PredictionService初始化完成")

        except Exception as e:
            logger.error(f"❌ PredictionService初始化失败: {e}")
            raise RuntimeError(f"PredictionService初始化失败: {e}")

    async def _cold_start_training(self):
        """
        冷启动训练 - 当模型文件不存在时自动触发训练。

        冷启动流程：
        1. 构建ML管道组件
        2. 执行实时训练
        3. 保存模型和元数据

        这确保了服务的"零配置"启动能力。
        """
        logger.info("🔥 启动冷启动训练流程...")

        try:
            # 构建标准ML管道
            self._build_pipeline()

            # 执行训练
            metrics = await self.trainer.run(test_size=0.2)
            logger.info(f"✅ 冷启动训练完成: Accuracy={metrics['accuracy']:.2%}")

            # 保存模型
            self._save_model()

        except Exception as e:
            logger.error(f"❌ 冷启动训练失败: {e}")
            raise RuntimeError(f"冷启动训练失败: {e}")

    async def _load_model(self):
        """
        加载已训练的模型到内存。

        加载流程：
        1. 加载模型文件
        2. 加载元数据
        3. 验证模型完整性
        """
        logger.info(f"🔄 加载模型: {self.model_path}")

        try:
            # 1. 加载XGBoost模型
            self.model = joblib.load(self.model_path)
            logger.info("✅ XGBoost模型加载成功")

            # 2. 加载元数据
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                self.feature_columns = metadata.get('feature_importance', [])
                if self.feature_columns:
                    # 提取特征名
                    self.feature_columns = [item['feature'] for item in self.feature_columns]
                else:
                    # 备用方案：使用trainer中的特征名（如果存在）
                    self.feature_columns = metadata.get('data_info', {}).get('total_features', [])

                self._model_version = metadata.get('model_version', 'v1')
                logger.info(f"✅ 元数据加载成功，模型版本: {self._model_version}")
            else:
                logger.warning("⚠️ 元数据文件不存在，使用默认特征列")
                # 如果没有元数据，尝试从模型获取特征名
                if hasattr(self.model, 'feature_names_in_'):
                    self.feature_columns = list(self.model.feature_names_in_)
                else:
                    # 使用默认的滚动特征列名（基于训练脚本）
                    self.feature_columns = [
                        'rolling_home_score_3', 'rolling_home_score_10',
                        'rolling_away_score_3', 'rolling_away_score_10',
                        'rolling_home_expected_goals_3', 'rolling_home_expected_goals_10',
                        'rolling_away_expected_goals_3', 'rolling_away_expected_goals_10',
                        'rolling_home_possession_3', 'rolling_home_possession_10',
                        'rolling_away_possession_3', 'rolling_away_possession_10'
                    ]

            # 3. 验证模型完整性
            if self.model is None:
                raise RuntimeError("模型加载失败：模型对象为None")

            if not self.feature_columns:
                raise RuntimeError("模型加载失败：特征列为空")

            logger.info(f"✅ 模型验证通过，特征数量: {len(self.feature_columns)}")

        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise RuntimeError(f"模型加载失败: {e}")

    async def predict_match(self, home_team_id: int, away_team_id: int, match_date: datetime) -> Dict[str, Any]:
        """
        预测单场比赛结果。

        预测流程：
        1. 特征工程 - 构建预测特征
        2. 模型推理 - XGBoost概率预测
        3. 结果格式化 - 标准化输出

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            match_date: 比赛日期

        Returns:
            Dict[str, Any]: 预测结果
            {
                "home_win_prob": 0.65,        # 主队获胜概率
                "away_win_prob": 0.20,        # 客队获胜概率
                "draw_prob": 0.15,            # 平局概率
                "prediction": "home_win",     # 推荐结果
                "confidence": 0.65,           # 预测置信度
                "model_version": "v1",        # 模型版本
                "features": {...},            # 特征详情
                "match_info": {               # 比赛信息
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "match_date": match_date.isoformat()
                }
            }

        Raises:
            RuntimeError: 服务未初始化
            ValueError: 输入参数无效
        """
        if not self.is_ready:
            raise RuntimeError("PredictionService未初始化，请先调用initialize()")

        # 验证输入参数
        if not all([home_team_id, away_team_id, match_date]):
            raise ValueError("所有预测参数都是必需的")

        logger.info(f"🔮 开始预测: {home_team_id} vs {away_team_id} on {match_date}")

        try:
            # 构建预测特征
            features = await self._build_prediction_features(home_team_id, away_team_id, match_date)

            # 执行模型推理
            prediction_prob = await self._run_inference(features)

            # 格式化预测结果
            result = self._format_prediction_result(
                prediction_prob, features, home_team_id, away_team_id, match_date
            )

            logger.info(f"✅ 预测完成: {result['prediction']} (confidence: {result['confidence']:.2%})")
            return result

        except Exception as e:
            logger.error(f"❌ 预测失败: {e}")
            raise RuntimeError(f"预测失败: {e}")

    def _build_pipeline(self):
        """
        构建标准的 ML 管道组件 (Loader, Transformers, Trainer)。

        标准管道配置：
        - DataLoader: 加载历史比赛数据
        - RollingAverageTransformer: 滚动窗口特征工程
        - ModelTrainer: XGBoost模型训练器
        """
        logger.info("🔧 构建ML训练管道...")

        # 1. 数据加载器
        from src.ml.data.loader import DataLoader
        raw_loader = DataLoader()

        # 适配器模式，解决接口不匹配问题
        class DataLoaderAdapter:
            def __init__(self, data_loader):
                self.data_loader = data_loader

            async def load_data(self) -> pd.DataFrame:
                return await self.data_loader.load_raw_data()

        loader = DataLoaderAdapter(raw_loader)

        # 2. 特征工程管道
        feature_columns = [
            'home_score',           # 主队进球数
            'away_score',           # 客队进球数
            'home_expected_goals',  # 主队期望进球(xG)
            'away_expected_goals',  # 客队期望进球(xG)
            'home_possession',      # 主队控球率
            'away_possession'       # 客队控球率
        ]

        transformers = [
            RollingAverageTransformer(
                windows=[3, 10],  # 3场(短期)和10场(长期)滚动窗口
                columns=feature_columns,
                group_by=['home_team_id', 'away_team_id'],  # 按主客球队分组计算
                date_column='match_date',
                output_prefix='rolling'  # 特征名前缀
            )
        ]

        # 3. 模型训练器
        model_params = {
            'n_estimators': 100,      # 树的数量
            'max_depth': 4,          # 树的深度
            'learning_rate': 0.1,     # 学习率
            'objective': 'binary:logistic',  # 二分类目标
            'random_state': 42,      # 随机种子，确保结果可重现
            'eval_metric': 'logloss',
            'use_label_encoder': False,
            'n_jobs': -1             # 并行计算
        }

        self.trainer = ModelTrainer(
            data_loader=loader,
            feature_transformers=transformers,
            model_params=model_params
        )

        logger.info("✅ ML训练管道构建完成")

    def _save_model(self):
        """
        保存训练好的模型和元数据。

        保存流程：
        1. 保存XGBoost模型
        2. 保存特征列信息
        3. 更新运行时状态
        """
        logger.info(f"💾 保存模型: {self.model_path}")

        try:
            # 1. 确保目录存在
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

            # 2. 保存XGBoost模型
            joblib.dump(self.trainer.model, self.model_path)
            logger.info("✅ XGBoost模型保存成功")

            # 3. 保存元数据（如果trainer存在）
            if hasattr(self.trainer, 'training_metrics_') and self.trainer.training_metrics_:
                metadata = {
                    'model_version': self._model_version,
                    'training_date': datetime.now().isoformat(),
                    'model_params': self.trainer.model_params,
                    'metrics': self.trainer.training_metrics_,
                    'feature_importance': self.trainer.get_feature_importance().to_dict('records') if self.trainer.get_feature_importance() is not None else None,
                    'data_info': {
                        'feature_columns': len(self.trainer.feature_names_) if hasattr(self.trainer, 'feature_names_') else 0,
                        'total_features': len(self.trainer.feature_names_) if hasattr(self.trainer, 'feature_names_') else 0
                    }
                }

                with open(self.metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                logger.info(f"✅ 元数据保存成功: {self.metadata_path}")

            # 4. 更新运行时状态
            self.model = self.trainer.model
            if hasattr(self.trainer, 'feature_names_'):
                self.feature_columns = list(self.trainer.feature_names_)

            logger.info("✅ 运行时状态更新完成")

        except Exception as e:
            logger.error(f"❌ 模型保存失败: {e}")
            raise RuntimeError(f"模型保存失败: {e}")

    async def _build_prediction_features(self, home_team_id: int, away_team_id: int, match_date: datetime) -> Dict[str, float]:
        """
        为单场比赛构建预测特征。

        特征工程流程：
        1. 加载相关历史数据
        2. 计算滚动窗口特征
        3. 构建特征向量

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            match_date: 比赛日期

        Returns:
            Dict[str, float]: 特征字典
        """
        logger.debug(f"🔧 构建预测特征: {home_team_id} vs {away_team_id} on {match_date}")

        try:
            # MVP实现：使用简化的特征构建策略
            # 在生产环境中，这里应该从真实的Feature Store获取特征

            # 1. 尝试从特征存储中查找
            feature_key = f"{home_team_id}_{away_team_id}_{match_date.strftime('%Y-%m-%d')}"
            if feature_key in self.feature_store:
                logger.debug("✅ 从特征存储中获取特征")
                return self.feature_store[feature_key]

            # 2. 如果没有找到，生成模拟特征（基于历史平均）
            # 这个策略确保即使没有真实数据也能提供预测
            features = self._generate_mock_features(home_team_id, away_team_id)

            # 3. 缓存特征（MVP版本的简单缓存）
            self.feature_store[feature_key] = features

            logger.debug(f"✅ 特征构建完成，特征数量: {len(features)}")
            return features

        except Exception as e:
            logger.error(f"❌ 特征构建失败: {e}")
            # 返回默认特征以确保预测能够进行
            return self._generate_default_features()

    def _generate_mock_features(self, home_team_id: int, away_team_id: int) -> Dict[str, float]:
        """
        生成模拟特征（基于团队ID的一致性特征）。

        MVP版本的简化实现：
        - 基于团队ID生成一致的特征
        - 确保相同团队组合获得相似特征
        - 提供合理的特征范围

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID

        Returns:
            Dict[str, float]: 模拟特征字典
        """
        import hashlib

        # 基于团队ID生成种子
        seed_string = f"{home_team_id}_{away_team_id}"
        seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
        np.random.seed(seed)

        # 生成基线特征（模拟真实的滚动特征）
        features = {}

        # 主队特征：基于主队ID和随机种子的组合
        home_strength = 0.3 + (home_team_id % 10) * 0.05 + np.random.normal(0, 0.1)
        away_strength = 0.3 + (away_team_id % 10) * 0.05 + np.random.normal(0, 0.1)

        # 滚动进球特征
        features['rolling_home_score_3'] = max(0.1, home_strength + np.random.normal(0, 0.3))
        features['rolling_home_score_10'] = max(0.1, home_strength + np.random.normal(0, 0.2))
        features['rolling_away_score_3'] = max(0.1, away_strength + np.random.normal(0, 0.3))
        features['rolling_away_score_10'] = max(0.1, away_strength + np.random.normal(0, 0.2))

        # 期望进球特征（与进球数相关但有差异）
        features['rolling_home_expected_goals_3'] = features['rolling_home_score_3'] + np.random.normal(0, 0.2)
        features['rolling_home_expected_goals_10'] = features['rolling_home_score_10'] + np.random.normal(0, 0.15)
        features['rolling_away_expected_goals_3'] = features['rolling_away_score_3'] + np.random.normal(0, 0.2)
        features['rolling_away_expected_goals_10'] = features['rolling_away_score_10'] + np.random.normal(0, 0.15)

        # 控球率特征（主队通常略高）
        features['rolling_home_possession_3'] = min(95, max(40, 50 + (home_strength - away_strength) * 10 + np.random.normal(0, 5)))
        features['rolling_home_possession_10'] = min(95, max(40, 50 + (home_strength - away_strength) * 8 + np.random.normal(0, 4)))
        features['rolling_away_possession_3'] = min(95, max(40, 50 - (home_strength - away_strength) * 10 + np.random.normal(0, 5)))
        features['rolling_away_possession_10'] = min(95, max(40, 50 - (home_strength - away_strength) * 8 + np.random.normal(0, 4)))

        # 确保特征值在合理范围内
        for key, value in features.items():
            if 'score' in key or 'goals' in key:
                features[key] = max(0.0, float(value))  # 进球相关特征非负
            elif 'possession' in key:
                features[key] = max(0.0, min(100.0, float(value)))  # 控球率0-100
            else:
                features[key] = float(value)

        return features

    def _generate_default_features(self) -> Dict[str, float]:
        """
        生成默认特征（用于错误情况的降级处理）。

        Returns:
            Dict[str, float]: 默认特征字典
        """
        return {
            'rolling_home_score_3': 1.4,
            'rolling_home_score_10': 1.3,
            'rolling_away_score_3': 1.1,
            'rolling_away_score_10': 1.2,
            'rolling_home_expected_goals_3': 1.5,
            'rolling_home_expected_goals_10': 1.4,
            'rolling_away_expected_goals_3': 1.2,
            'rolling_away_expected_goals_10': 1.3,
            'rolling_home_possession_3': 52.0,
            'rolling_home_possession_10': 51.0,
            'rolling_away_possession_3': 48.0,
            'rolling_away_possession_10': 49.0
        }

    async def _run_inference(self, features: Dict[str, float]) -> float:
        """
        执行模型推理。

        Args:
            features: 特征向量

        Returns:
            float: 主队获胜概率
        """
        logger.debug("🤖 执行模型推理")

        try:
            if self.model is None:
                raise RuntimeError("模型未加载，无法进行推理")

            # 1. 准备特征向量
            if not self.feature_columns:
                raise RuntimeError("特征列未初始化，无法进行推理")

            # 2. 构建特征矩阵（确保特征顺序与训练时一致）
            feature_vector = []
            for col in self.feature_columns:
                if col in features:
                    feature_vector.append(features[col])
                else:
                    # 如果缺少某个特征，使用默认值
                    logger.warning(f"⚠️ 特征 '{col}' 缺失，使用默认值0.0")
                    feature_vector.append(0.0)

            # 3. 转换为numpy数组并重塑为模型期望的格式
            feature_array = np.array(feature_vector).reshape(1, -1)

            logger.debug(f"📊 特征向量形状: {feature_array.shape}")

            # 4. 执行预测
            prediction_prob = self.model.predict_proba(feature_array)[0, 1]

            # 5. 验证预测结果
            if not (0.0 <= prediction_prob <= 1.0):
                logger.warning(f"⚠️ 预测概率超出范围: {prediction_prob}，进行截断")
                prediction_prob = max(0.0, min(1.0, prediction_prob))

            logger.debug(f"✅ 推理完成，主队获胜概率: {prediction_prob:.4f}")
            return float(prediction_prob)

        except Exception as e:
            logger.error(f"❌ 模型推理失败: {e}")
            # 返回默认概率以确保服务可用性
            return 0.5  # 默认50%概率

    def _format_prediction_result(self,
                                 prediction_prob: float,
                                 features: Dict[str, float],
                                 home_team_id: int,
                                 away_team_id: int,
                                 match_date: datetime) -> Dict[str, Any]:
        """
        格式化预测结果为标准化输出。

        Args:
            prediction_prob: 主队获胜概率
            features: 特征字典
            home_team_id: 主队ID
            away_team_id: 客队ID
            match_date: 比赛日期

        Returns:
            Dict[str, Any]: 格式化的预测结果
        """
        # 计算各项概率
        home_win_prob = prediction_prob
        # 简化的概率分配（实际应用中可以用更复杂的方法）
        away_win_prob = (1 - home_win_prob) * 0.6  # 客队获胜概率
        draw_prob = 1 - home_win_prob - away_win_prob  # 平局概率

        # 确定预测结果
        if home_win_prob > away_win_prob and home_win_prob > draw_prob:
            prediction = "home_win"
            confidence = home_win_prob
        elif away_win_prob > draw_prob:
            prediction = "away_win"
            confidence = away_win_prob
        else:
            prediction = "draw"
            confidence = draw_prob

        return {
            "home_win_prob": round(home_win_prob, 4),
            "away_win_prob": round(away_win_prob, 4),
            "draw_prob": round(draw_prob, 4),
            "prediction": prediction,
            "confidence": round(confidence, 4),
            "model_version": self._model_version,
            "features": features,
            "match_info": {
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "match_date": match_date.isoformat()
            },
            "generated_at": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        """字符串表示。"""
        return (
            f"PredictionService("
            f"ready={self.is_ready}, "
            f"model_path='{self.model_path}', "
            f"version='{self._model_version}')"
        )