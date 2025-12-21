#!/usr/bin/env python3
"""
XGBoost 2.0+ 优化模型重训配置
针对180+维特征和517场数据，优化10-Fold CV准确率至58%+
重点解决平局预测偏差问题
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, log_loss
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif, RFE
from sklearn.decomposition import PCA
import xgboost as xgb
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class XGBoostOptimizedConfig:
    """XGBoost 2.0+优化配置"""

    # === 核心超参数（针对高维特征优化） ===
    n_estimators: int = 800          # 增加树的数量以捕获复杂模式
    max_depth: int = 6               # 控制树深度，防止过拟合（特征数/10）
    learning_rate: float = 0.03      # 降低学习率，配合更多树
    min_child_weight: int = 3        # 增加最小子节点权重，防止过拟合
    subsample: float = 0.75          # 行采样，降低相关性
    colsample_bytree: float = 0.7    # 列采样，防止过拟合
    colsample_bylevel: float = 0.8   # 每层列采样
    gamma: float = 0.1               # 最小分裂增益
    reg_alpha: float = 0.1           # L1正则化，特征选择
    reg_lambda: float = 1.5          # L2正则化，权重平滑

    # === XGBoost 2.0+新特性 ===
    max_bin: int = 256               # 直方图算法分箱数
    grow_policy: str = "lossguide"   # 按损失增长分裂（depthwise/lossguide）
    max_leaves: int = 0              # 最大叶子数（0=无限制）
    # tree_method: str = "hist"       # 直方图算法（自动选择）

    # === 类别不平衡处理 ===
    scale_pos_weight: Optional[float] = None  # 动态计算
    # 使用class_weights替代scale_pos_weight

    # === 早停和学习率调度 ===
    early_stopping_rounds: int = 100
    eval_metric: str = "mlogloss"

    # === 目标函数和输出 ===
    objective: str = "multi:softprob"
    num_class: int = 3
    response_method: str = "predict_proba"

    # === 随机性和并行 ===
    random_state: int = 42
    n_jobs: int = -1                 # 使用所有CPU核心
    verbosity: int = 0


class ClassWeightCalculator:
    """类别权重计算器 - 解决平局预测偏差"""

    @staticmethod
    def calculate_balanced_weights(y: np.ndarray) -> Dict[int, float]:
        """
        计算平衡的类别权重

        Args:
            y: 标签数组

        Returns:
            类别权重字典
        """
        unique, counts = np.unique(y, return_counts=True)
        total = len(y)
        n_classes = len(unique)

        # 基础权重：逆频率加权
        base_weights = {}
        for cls, count in zip(unique, counts):
            base_weights[cls] = total / (n_classes * count)

        # 特殊处理：增强平局类别（通常是中间类别）
        if 1 in base_weights:  # 假设1是平局
            # 给平局类别额外20%的权重
            base_weights[1] *= 1.2

        # 归一化权重，使平均权重为1.0
        avg_weight = np.mean(list(base_weights.values()))
        normalized_weights = {k: v / avg_weight for k, v in base_weights.items()}

        logger.info(f"计算的类别权重: {normalized_weights}")
        return normalized_weights

    @staticmethod
    def get_focal_loss_weights(y: np.ndarray, alpha: float = 0.25, gamma: float = 2.0) -> np.ndarray:
        """
        计算Focal Loss权重（可选方案）

        Args:
            y: 标签数组
            alpha: 平衡因子
            gamma: 聚焦因子

        Returns:
            每个样本的权重
        """
        unique, counts = np.unique(y, return_counts=True)
        class_weights = {}

        # 计算每个类别的Focal Loss权重
        for cls in unique:
            freq = counts[cls] / len(y)
            class_weights[cls] = alpha * (1 - freq) ** gamma

        # 为每个样本分配权重
        sample_weights = np.array([class_weights[cls] for cls in y])

        # 归一化
        sample_weights = sample_weights / np.mean(sample_weights)

        return sample_weights


class FeatureSelector:
    """特征选择器 - 处理高维特征"""

    def __init__(self, method: str = "hybrid", k_best: int = 120):
        self.method = method
        self.k_best = k_best
        self.selected_features = None
        self.feature_scores = None

    def fit_transform(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """
        选择最优特征

        Args:
            X: 特征数据
            y: 标签数据

        Returns:
            选择后的特征数据
        """
        logger.info(f"开始特征选择，原始特征数: {X.shape[1]}")

        if self.method == "hybrid":
            # 混合方法：统计 + 递归消除
            X_selected = self._hybrid_selection(X, y)
        elif self.method == "statistical":
            # 纯统计方法
            X_selected = self._statistical_selection(X, y)
        elif self.method == "rfe":
            # 递归特征消除
            X_selected = self._rfe_selection(X, y)
        else:
            # 不进行选择
            X_selected = X

        logger.info(f"特征选择完成，最终特征数: {X_selected.shape[1]}")
        return X_selected

    def _hybrid_selection(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """混合特征选择方法"""

        # 第一步：基于统计的初筛
        selector_kbest = SelectKBest(score_func=f_classif, k=min(200, X.shape[1]))
        X_kbest = selector_kbest.fit_transform(X, y)
        selected_indices_kbest = selector_kbest.get_support(indices=True)
        selected_features_kbest = X.columns[selected_indices_kbest].tolist()

        # 获取特征分数
        feature_scores = pd.DataFrame({
            'feature': X.columns,
            'score': selector_kbest.scores_,
            'selected': False
        })
        feature_scores.loc[selected_indices_kbest, 'selected'] = True
        self.feature_scores = feature_scores

        # 第二步：基于模型的递归消除（减少计算量）
        X_kbest_df = pd.DataFrame(X_kbest, columns=selected_features_kbest, index=X.index)

        # 使用较简单的XGBoost进行RFE
        base_xgb = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            verbosity=0
        )

        rfe = RFE(
            estimator=base_xgb,
            n_features_to_select=self.k_best,
            step=0.1  # 每次移除10%的特征
        )

        X_rfe = rfe.fit_transform(X_kbest_df, y)
        selected_mask = rfe.support_

        # 获取最终选择的特征
        final_features = []
        for i, selected in enumerate(selected_mask):
            if selected:
                final_features.append(selected_features_kbest[i])

        self.selected_features = final_features

        # 返回最终选择的特征
        return X[final_features]

    def _statistical_selection(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """基于统计的特征选择"""
        selector = SelectKBest(score_func=f_classif, k=self.k_best)
        X_selected = selector.fit_transform(X, y)
        selected_features = X.columns[selector.get_support(indices=True)].tolist()

        self.selected_features = selected_features
        self.feature_scores = pd.DataFrame({
            'feature': X.columns,
            'score': selector.scores_,
            'selected': selector.get_support()
        })

        return pd.DataFrame(X_selected, columns=selected_features, index=X.index)

    def _rfe_selection(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """递归特征消除"""
        base_estimator = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            verbosity=0
        )

        rfe = RFE(
            estimator=base_estimator,
            n_features_to_select=self.k_best,
            step=0.1
        )

        X_selected = rfe.fit_transform(X, y)
        selected_features = X.columns[rfe.support_].tolist()

        self.selected_features = selected_features

        return pd.DataFrame(X_selected, columns=selected_features, index=X.index)


class OptimizedModelTrainer:
    """优化的模型训练器"""

    def __init__(self, config: XGBoostOptimizedConfig):
        self.config = config
        self.feature_selector = FeatureSelector(method="hybrid", k_best=120)
        self.scaler = StandardScaler()
        self.model = None
        self.training_history = {}

    def train_with_cv(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv_folds: int = 10,
        use_class_weights: bool = True
    ) -> Dict:
        """
        使用交叉验证训练模型

        Args:
            X: 特征数据
            y: 标签数据
            cv_folds: 交叉验证折数
            use_class_weights: 是否使用类别权重

        Returns:
            训练结果字典
        """
        logger.info("开始优化的模型训练...")

        # 1. 特征选择
        X_selected = self.feature_selector.fit_transform(X, y)

        # 2. 特征标准化
        X_scaled = self.scaler.fit_transform(X_selected)

        # 3. 计算类别权重
        if use_class_weights:
            class_weights = ClassWeightCalculator.calculate_balanced_weights(y.values)
            # XGBoost 2.0+支持样本权重
            sample_weights = np.array([class_weights[cls] for cls in y.values])
        else:
            sample_weights = None

        # 4. 创建优化的XGBoost模型
        self.model = xgb.XGBClassifier(
            # 核心参数
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            learning_rate=self.config.learning_rate,
            min_child_weight=self.config.min_child_weight,
            subsample=self.config.subsample,
            colsample_bytree=self.config.colsample_bytree,
            colsample_bylevel=self.config.colsample_bylevel,
            gamma=self.config.gamma,
            reg_alpha=self.config.reg_alpha,
            reg_lambda=self.config.reg_lambda,

            # XGBoost 2.0+特性
            max_bin=self.config.max_bin,
            grow_policy=self.config.grow_policy,
            max_leaves=self.config.max_leaves,
            tree_method="hist",  # 使用直方图算法加速

            # 目标和评估
            objective=self.config.objective,
            num_class=self.config.num_class,
            eval_metric=self.config.eval_metric,

            # 随机性和并行
            random_state=self.config.random_state,
            n_jobs=self.config.n_jobs,
            verbosity=self.config.verbosity
        )

        # 5. 执行分层K折交叉验证
        logger.info(f"执行{cv_folds}折交叉验证...")
        skf = StratifiedKFold(
            n_splits=cv_folds,
            shuffle=True,
            random_state=self.config.random_state
        )

        cv_scores = []
        cv_logloss = []
        fold_results = []

        for fold, (train_idx, val_idx) in enumerate(skf.split(X_scaled, y), 1):
            logger.info(f"训练第 {fold}/{cv_folds} 折...")

            X_train_fold = X_scaled[train_idx]
            X_val_fold = X_scaled[val_idx]
            y_train_fold = y.iloc[train_idx]
            y_val_fold = y.iloc[val_idx]

            # 当前折的样本权重
            if sample_weights is not None:
                train_weights = sample_weights[train_idx]
            else:
                train_weights = None

            # 创建当前折的模型
            fold_model = xgb.XGBClassifier(**self.model.get_params())

            # 训练模型（使用验证集进行早停）
            fold_model.fit(
                X_train_fold, y_train_fold,
                sample_weight=train_weights,
                eval_set=[(X_val_fold, y_val_fold)],
                early_stopping_rounds=self.config.early_stopping_rounds,
                verbose=False
            )

            # 预测和评估
            y_pred = fold_model.predict(X_val_fold)
            y_pred_proba = fold_model.predict_proba(X_val_fold)

            accuracy = np.mean(y_pred == y_val_fold)
            logloss_val = log_loss(y_val_fold, y_pred_proba)

            cv_scores.append(accuracy)
            cv_logloss.append(logloss_val)

            # 保存折结果
            fold_result = {
                'fold': fold,
                'accuracy': accuracy,
                'logloss': logloss_val,
                'best_iteration': fold_model.best_iteration,
                'feature_importance': dict(zip(
                    self.feature_selector.selected_features,
                    fold_model.feature_importances_
                ))
            }
            fold_results.append(fold_result)

            logger.info(f"第{fold}折 - 准确率: {accuracy:.4f}, LogLoss: {logloss_val:.4f}")

        # 6. 在全部数据上训练最终模型
        logger.info("在全部数据上训练最终模型...")
        final_model = xgb.XGBClassifier(**self.model.get_params())

        # 没有验证集，不使用早停
        final_model.fit(
            X_scaled, y,
            sample_weight=sample_weights,
            verbose=False
        )

        self.model = final_model

        # 7. 汇总结果
        cv_mean_accuracy = np.mean(cv_scores)
        cv_std_accuracy = np.std(cv_scores)
        cv_mean_logloss = np.mean(cv_logloss)

        self.training_history = {
            'cv_scores': cv_scores,
            'cv_logloss': cv_logloss,
            'fold_results': fold_results,
            'mean_accuracy': cv_mean_accuracy,
            'std_accuracy': cv_std_accuracy,
            'mean_logloss': cv_mean_logloss,
            'feature_importance': dict(zip(
                self.feature_selector.selected_features,
                self.model.feature_importances_
            )),
            'selected_features': self.feature_selector.selected_features,
            'feature_scores': self.feature_selector.feature_scores.to_dict('records') if self.feature_selector.feature_scores is not None else None
        }

        logger.info(f"训练完成！")
        logger.info(f"10-Fold CV准确率: {cv_mean_accuracy:.4f} ± {cv_std_accuracy:.4f}")
        logger.info(f"目标达成: {'✅ 是' if cv_mean_accuracy >= 0.58 else '❌ 否'} (58%+)")

        return self.training_history

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        使用训练好的模型进行预测

        Args:
            X: 特征数据

        Returns:
            (预测类别, 预测概率)
        """
        if self.model is None:
            raise ValueError("模型尚未训练，请先调用train_with_cv方法")

        # 使用相同的特征选择和标准化
        X_selected = X[self.feature_selector.selected_features]
        X_scaled = self.scaler.transform(X_selected)

        y_pred = self.model.predict(X_scaled)
        y_pred_proba = self.model.predict_proba(X_scaled)

        return y_pred, y_pred_proba

    def save_model(self, path: str):
        """保存模型和相关组件"""
        import joblib

        model_data = {
            'model': self.model,
            'feature_selector': self.feature_selector,
            'scaler': self.scaler,
            'config': self.config,
            'training_history': self.training_history
        }

        joblib.dump(model_data, path)
        logger.info(f"模型已保存到: {path}")

    def load_model(self, path: str):
        """加载模型和相关组件"""
        import joblib

        model_data = joblib.load(path)

        self.model = model_data['model']
        self.feature_selector = model_data['feature_selector']
        self.scaler = model_data['scaler']
        self.config = model_data['config']
        self.training_history = model_data['training_history']

        logger.info(f"模型已从 {path} 加载")


def create_optimized_training_config() -> XGBoostOptimizedConfig:
    """
    创建针对当前数据的优化配置

    Returns:
        优化的配置对象
    """
    config = XGBoostOptimizedConfig()

    # 基于数据量调整参数
    # 517个样本，180+特征
    config.n_estimators = 600        # 样本量适中，增加树的数量
    config.max_depth = 5             # 控制深度，防止过拟合
    config.learning_rate = 0.04      # 较小的学习率

    # 特征采样（因为特征维度高）
    config.colsample_bytree = 0.65   # 每棵树使用65%的特征
    config.colsample_bylevel = 0.75  # 每层使用75%的特征
    config.subsample = 0.8           # 每棵树使用80%的样本

    # 正则化（防止过拟合）
    config.reg_alpha = 0.15          # L1正则化
    config.reg_lambda = 1.8          # L2正则化
    config.gamma = 0.15              # 最小分裂增益
    config.min_child_weight = 4      # 增加最小子节点权重

    # XGBoost 2.0+优化
    config.max_bin = 200             # 减少分箱数防止过拟合
    config.grow_policy = "lossguide" # 按损失增长分裂

    logger.info("已创建优化的训练配置")
    logger.info(f"配置详情: n_estimators={config.n_estimators}, max_depth={config.max_depth}")
    logger.info(f"正则化: reg_alpha={config.reg_alpha}, reg_lambda={config.reg_lambda}")

    return config


# 使用示例和最佳实践
def main():
    """主训练函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("开始XGBoost 2.0+优化模型训练")

    # 这里需要加载您的数据
    # X, y = load_your_data()

    # 创建优化配置
    config = create_optimized_training_config()

    # 创建训练器
    trainer = OptimizedModelTrainer(config)

    # 训练模型
    # training_results = trainer.train_with_cv(X, y, cv_folds=10)

    # 保存模型
    # trainer.save_model('optimized_xgb_model.joblib')

    logger.info("模型训练完成！")


if __name__ == "__main__":
    main()