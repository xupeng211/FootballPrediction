#!/usr/bin/env python3
"""
增强的XGBoost模型优化器
集成了机器学习工程技能的专业优化工具
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score

logger = logging.getLogger(__name__)

# 尝试导入机器学习工程组件
try:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent.parent / ".claude" / "skills" / "machine-learning-engineering" / "scripts"))
    from xgboost_optimizer import FootballPredictionOptimizer
    from feature_engineering_analyzer import FootballFeatureAnalyzer
    ML_ENGINEERING_ENABLED = True
except ImportError as e:
    logger.warning(f"机器学习工程组件导入失败: {e}")
    ML_ENGINEERING_ENABLED = False


class EnhancedXGBooostOptimizer:
    """
    增强的XGBoost模型优化器
    集成了先进的超参数优化、特征工程和模型解释功能
    """

    def __init__(self, target_accuracy: float = 0.65, target_latency_ms: float = 100.0):
        self.target_accuracy = target_accuracy
        self.target_latency_ms = target_latency_ms
        self.model = None
        self.best_params = None
        self.best_score = 0.0
        self.feature_importance = None
        self.training_history = []

        # 尝试初始化机器学习工程组件
        if ML_ENGINEERING_ENABLED:
            try:
                self.prediction_optimizer = FootballPredictionOptimizer(
                    target_accuracy=target_accuracy,
                    target_latency_ms=target_latency_ms
                )
                self.feature_analyzer = FootballFeatureAnalyzer()
                logger.info("✅ 机器学习工程组件初始化成功")
            except Exception as e:
                logger.error(f"机器学习工程组件初始化失败: {e}")
                self.prediction_optimizer = None
                self.feature_analyzer = None
        else:
            self.prediction_optimizer = None
            self.feature_analyzer = None

    def optimize_hyperparameters(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        n_trials: int = 100,
        use_optuna: bool = True
    ) -> Tuple[Dict[str, Any], float]:
        """
        超参数优化
        支持Optuna自动调优和网格搜索
        """
        logger.info(f"🎯 开始超参数优化，目标: {self.target_accuracy}")

        if use_optuna and ML_ENGINEERING_ENABLED and self.prediction_optimizer:
            # 使用Optuna自动优化
            try:
                best_params, best_score = asyncio.run(
                    self.prediction_optimizer.optimize_hyperparameters(
                        X_train, y_train, X_val, y_val, n_trials=n_trials
                    )
                )
                self.best_params = best_params
                self.best_score = best_score
                logger.info(f"✅ Optuna优化完成: 准确率 {best_score:.4f}")
                return best_params, best_score
            except Exception as e:
                logger.error(f"Optuna优化失败: {e}")
                logger.info("降级到手动优化")

        # 手动优化（降级方案）
        param_grid = {
            'max_depth': [4, 6, 8],
            'learning_rate': [0.01, 0.05, 0.1],
            'n_estimators': [100, 200, 300],
            'subsample': [0.8, 0.9, 1.0],
            'colsample_bytree': [0.8, 0.9, 1.0],
            'min_child_weight': [1, 3, 5],
            'gamma': [0, 0.1, 0.2]
        }

        best_params = self._manual_grid_search(X_train, y_train, X_val, y_val, param_grid)
        return best_params, self.best_score

    def _manual_grid_search(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        param_grid: Dict[str, List]
    ) -> Dict[str, Any]:
        """手动网格搜索（降级方案）"""
        from itertools import product

        keys = list(param_grid.keys())
        values = list(param_grid.values())

        best_params = {}
        best_score = 0.0
        total_combinations = np.prod([len(v) for v in values])

        logger.info(f"手动网格搜索: {total_combinations} 种参数组合")

        for i, combination in enumerate(product(*values)):
            params = dict(zip(keys, combination))

            # 设置固定参数
            params.update({
                'objective': 'multi:softprob',
                'num_class': 3,
                'eval_metric': 'mlogloss',
                'random_state': 42,
                'n_jobs': -1
            })

            try:
                model = xgb.XGBClassifier(**params)
                model.fit(X_train, y_train)

                y_pred = model.predict(X_val)
                accuracy = accuracy_score(y_val, y_pred)

                if accuracy > best_score:
                    best_score = accuracy
                    best_params = params.copy()

                if (i + 1) % 10 == 0:
                    logger.info(f"进度: {i + 1}/{total_combinations}, 当前最佳: {best_score:.4f}")

            except Exception as e:
                logger.warning(f"参数组合 {params} 失败: {e}")
                continue

        self.best_params = best_params
        self.best_score = best_score
        logger.info(f"✅ 手动优化完成: 准确率 {best_score:.4f}")

        return best_params

    def enhance_features(
        self,
        df: pd.DataFrame,
        target_col: str = 'target'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        特征工程增强
        """
        logger.info("🔧 开始特征工程增强...")

        if ML_ENGINEERING_ENABLED and self.feature_analyzer:
            try:
                # 使用特征分析器
                analysis_results = self.feature_analyzer.analyze_feature_quality(df, target_col)
                suggestions = self.feature_analyzer.suggest_feature_engineering(analysis_results)

                # 应用建议
                df_enhanced = self._apply_feature_suggestions(df, suggestions)

                # 特征选择
                X = df_enhanced.drop(columns=[target_col])
                y = df_enhanced[target_col]

                X_selected, selected_features = self.feature_analyzer.optimize_features(X, y, k=20)

                logger.info(f"✅ 特征工程完成: {len(selected_features)} 个特征")
                return X_selected, selected_features

            except Exception as e:
                logger.error(f"特征工程增强失败: {e}")
                logger.info("使用基础特征处理")

        # 基础特征处理
        return self._basic_feature_engineering(df, target_col)

    def _apply_feature_suggestions(self, df: pd.DataFrame, suggestions: Dict) -> pd.DataFrame:
        """应用特征工程建议"""
        df_enhanced = df.copy()

        for suggestion in suggestions.get('suggestions', []):
            action = suggestion.get('action')
            features = suggestion.get('features', [])

            if action == 'drop_features' and features:
                df_enhanced = df_enhanced.drop(columns=features)
                logger.info(f"删除特征: {features}")

        # 创建新特征
        df_enhanced = self._create_interaction_features(df_enhanced)

        return df_enhanced

    def _create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建交互特征"""
        df_enhanced = df.copy()

        # 找出数值列
        numeric_cols = df_enhanced.select_dtypes(include=[np.number]).columns

        # 创建简单的交互特征
        if len(numeric_cols) >= 2:
            col1, col2 = numeric_cols[0], numeric_cols[1]
            df_enhanced[f'{col1}_x_{col2}'] = df_enhanced[col1] * df_enhanced[col2]
            df_enhanced[f'{col1}_div_{col2}'] = df_enhanced[col1] / (df_enhanced[col2] + 1e-8)

        return df_enhanced

    def _basic_feature_engineering(self, df: pd.DataFrame, target_col: str) -> Tuple[pd.DataFrame, List[str]]:
        """基础特征工程"""
        # 分离特征和目标
        if target_col in df.columns:
            X = df.drop(columns=[target_col])
            y = df[target_col]
        else:
            X = df
            y = None

        # 基础清理
        # 移除常数特征
        constant_cols = [col for col in X.columns if X[col].nunique() <= 1]
        X = X.drop(columns=constant_cols)

        # 移除高相关性特征
        if len(X.columns) > 20:
            corr_matrix = X.corr().abs()
            high_corr_pairs = np.where(np.triu(corr_matrix, 1) > 0.95)
            cols_to_drop = set()

            for i, j in zip(*high_corr_pairs):
                if i < len(X.columns):
                    cols_to_drop.add(X.columns[j])

            X = X.drop(columns=list(cols_to_drop))

        logger.info(f"基础特征工程完成: {len(X.columns)} 个特征")
        return X, X.columns.tolist()

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        params: Optional[Dict[str, Any]] = None
    ) -> xgb.XGBClassifier:
        """
        训练最终模型
        """
        logger.info("🚀 开始模型训练...")

        if params is None:
            params = self.best_params or self._get_default_params()

        # 确保参数完整性
        final_params = params.copy()
        final_params.update({
            'objective': 'multi:softprob',
            'num_class': 3,
            'eval_metric': 'mlogloss',
            'random_state': 42,
            'n_jobs': -1
        })

        # 创建并训练模型
        self.model = xgb.XGBClassifier(**final_params)

        # 训练模型
        start_time = time.time()
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )
        training_time = time.time() - start_time

        # 评估模型
        y_pred = self.model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)

        # 记录训练历史
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'params': final_params,
            'accuracy': accuracy,
            'training_time': training_time,
            'feature_count': X_train.shape[1]
        })

        # 获取特征重要性
        self.feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        logger.info(f"✅ 模型训练完成: 准确率 {accuracy:.4f}, 用时 {training_time:.2f}s")

        # 检查是否达到目标
        if accuracy >= self.target_accuracy:
            logger.info(f"🎉 达到目标准确率: {accuracy:.4f} >= {self.target_accuracy:.4f}")
        else:
            gap = self.target_accuracy - accuracy
            logger.info(f"📈 还需提升: {gap:.4f} 准确率")

        return self.model

    def evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        全面评估模型
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用 train_model")

        logger.info("📊 开始模型评估...")

        # 预测
        start_time = time.time()
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)
        inference_time = time.time() - start_time

        # 基础指标
        accuracy = accuracy_score(y_test, y_pred)

        # 详细报告
        class_report = classification_report(
            y_test, y_pred,
            target_names=['HOME', 'DRAW', 'AWAY'],
            output_dict=True
        )

        # 混淆矩阵
        conf_matrix = confusion_matrix(y_test, y_pred)

        # 响应时间检查
        avg_inference_time = inference_time / len(X_test) * 1000  # ms

        results = {
            'accuracy': accuracy,
            'target_accuracy': self.target_accuracy,
            'target_latency_ms': self.target_latency_ms,
            'avg_inference_time_ms': avg_inference_time,
            'meets_accuracy_target': accuracy >= self.target_accuracy,
            'meets_latency_target': avg_inference_time <= self.target_latency_ms,
            'classification_report': class_report,
            'confusion_matrix': conf_matrix.tolist(),
            'feature_importance': self.feature_importance.to_dict('records') if self.feature_importance is not None else None,
            'training_history': self.training_history[-1] if self.training_history else None
        }

        logger.info(f"✅ 评估完成: 准确率 {accuracy:.4f}, 推理时间 {avg_inference_time:.2f}ms")

        return results

    def save_model(self, filepath: str):
        """保存模型和配置"""
        if self.model is None:
            raise ValueError("模型未训练")

        model_data = {
            'model': self.model,
            'best_params': self.best_params,
            'best_score': self.best_score,
            'feature_importance': self.feature_importance,
            'training_history': self.training_history,
            'metadata': {
                'target_accuracy': self.target_accuracy,
                'target_latency_ms': self.target_latency_ms,
                'created_at': datetime.now().isoformat()
            }
        }

        joblib.dump(model_data, filepath)
        logger.info(f"✅ 模型已保存到 {filepath}")

    def load_model(self, filepath: str):
        """加载模型"""
        model_data = joblib.load(filepath)

        self.model = model_data['model']
        self.best_params = model_data['best_params']
        self.best_score = model_data['best_score']
        self.feature_importance = model_data['feature_importance']
        self.training_history = model_data['training_history']

        logger.info(f"✅ 模型已从 {filepath} 加载")

    def _get_default_params(self) -> Dict[str, Any]:
        """默认参数"""
        return {
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 1,
            'gamma': 0,
            'reg_alpha': 0,
            'reg_lambda': 1
        }

    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        return {
            'target_accuracy': self.target_accuracy,
            'target_latency_ms': self.target_latency_ms,
            'best_score': self.best_score,
            'best_params': self.best_params,
            'feature_count': len(self.feature_importance) if self.feature_importance is not None else 0,
            'training_history': self.training_history,
            'ml_engineering_enabled': ML_ENGINEERING_ENABLED
        }


# 便捷函数
async def quick_optimize_pipeline(
    df: pd.DataFrame,
    target_col: str = 'target',
    target_accuracy: float = 0.65
) -> Dict[str, Any]:
    """快速优化流水线"""
    optimizer = EnhancedXGBooostOptimizer(target_accuracy=target_accuracy)

    # 特征工程
    X, selected_features = optimizer.enhance_features(df, target_col)

    # 分离目标
    y = df[target_col]

    # 数据分割
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

    # 超参数优化
    best_params, best_score = optimizer.optimize_hyperparameters(X_train, y_train, X_val, y_val)

    # 训练最终模型
    model = optimizer.train_model(X_train, y_train, X_val, y_val, best_params)

    # 评估模型
    results = optimizer.evaluate_model(X_test, y_test)

    return {
        'optimizer': optimizer,
        'results': results,
        'model': model,
        'selected_features': selected_features
    }