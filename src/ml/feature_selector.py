"""智能特征选择器
Smart Feature Selector.

基于机器学习模型和统计方法的自动化特征选择工具。
支持基于重要性、共线性检测和多重策略的特征优化。
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
from sklearn.metrics import get_scorer
from sklearn.model_selection import cross_val_score

# XGBoost 支持
try:
    import xgboost as xgb

    HAS_XGB = True
except ImportError:
    HAS_XGB = False

logger = logging.getLogger(__name__)


class FeatureSelector:
    """智能特征选择器.

    基于模型重要性、共线性检测和多重策略的自动化特征选择工具。
    支持分类和回归任务，提供详细的特征分析报告。
    """

    def __init__(
        self
        task_type: str = "classification",  # "classification" 或 "regression"
        correlation_threshold: float = 0.95
        min_features: int = 5
        max_features: int = 100
        random_state: int = 42
        n_jobs: int = -1
    ):
        """初始化特征选择器.

        Args:
            task_type: 任务类型，'classification' 或 'regression'
            correlation_threshold: 共线性检测阈值
            min_features: 最小保留特征数
            max_features: 最大保留特征数
            random_state: 随机种子
            n_jobs: 并行作业数
        """
        self.task_type = task_type
        self.correlation_threshold = correlation_threshold
        self.min_features = min_features
        self.max_features = max_features
        self.random_state = random_state
        self.n_jobs = n_jobs

        # 特征选择历史
        self.selection_history = []
        self.feature_importance_df = None
        self.correlation_matrix = None
        self.selected_features = []
        self.removed_features = []

        # 初始化基础模型
        self._init_base_models()

        logger.info(
            f"FeatureSelector initialized: task_type={task_type}, "
            f"correlation_threshold={correlation_threshold}"
        )

    def _init_base_models(self):
        """初始化基础模型用于特征重要性评估."""
        # 随机森林模型
        self.rf_model = (
            RandomForestClassifier(
                n_estimators=100
                random_state=self.random_state
                n_jobs=self.n_jobs
                max_depth=10
            )
            if self.task_type == "classification"
            else RandomForestRegressor(
                n_estimators=100
                random_state=self.random_state
                n_jobs=self.n_jobs
                max_depth=10
            )
        )

        # XGBoost模型（如果可用）
        self.xgb_model = None
        if HAS_XGB:
            self.xgb_model = (
                xgb.XGBClassifier(
                    n_estimators=100
                    random_state=self.random_state
                    n_jobs=self.n_jobs
                    max_depth=6
                    learning_rate=0.1
                )
                if self.task_type == "classification"
                else xgb.XGBRegressor(
                    n_estimators=100
                    random_state=self.random_state
                    n_jobs=self.n_jobs
                    max_depth=6
                    learning_rate=0.1
                )
            )

    def detect_collinearity(
        self, X: pd.DataFrame, y: Optional[pd.Series] = None
    ) -> tuple[list[str], list[str]]:
        """检测并处理特征间的共线性.

        Args:
            X: 特征矩阵
            y: 目标变量（用于确定保留哪个特征）

        Returns:
            (保留的特征列表, 移除的特征列表)
        """
        logger.info("开始共线性检测...")

        # 计算相关系数矩阵
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return X.columns.tolist(), []

        correlation_matrix = X[numeric_cols].corr().abs()
        self.correlation_matrix = correlation_matrix

        # 找到高相关性的特征对
        high_corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i + 1, len(correlation_matrix.columns)):
                if correlation_matrix.iloc[i, j] > self.correlation_threshold:
                    high_corr_pairs.append(
                        (
                            correlation_matrix.columns[i]
                            correlation_matrix.columns[j]
                            correlation_matrix.iloc[i, j]
                        )
                    )

        # 移除共线性特征
        features_to_remove = set()
        features_to_keep = set(X.columns)

        if y is not None:
            # 计算每个特征与目标变量的相关性
            target_correlations = {}
            for col in numeric_cols:
                if self.task_type == "classification":
                    # 对于分类任务，使用点二列相关系数
                    if X[col].nunique() > 1:
                        corr, _ = stats.pointbiserialr(X[col], y)
                    else:
                        corr = 0
                else:
                    # 对于回归任务，使用皮尔逊相关系数
                    corr, _ = stats.pearsonr(X[col], y)
                target_correlations[col] = abs(corr)

        # 对每个高相关性对，移除与目标变量相关性较低的特征
        for feat1, feat2, _corr_value in high_corr_pairs:
            if (
                y is not None
                and feat1 in target_correlations
                and feat2 in target_correlations
            ):
                if target_correlations[feat1] >= target_correlations[feat2]:
                    features_to_remove.add(feat2)
                    features_to_keep.discard(feat2)
                else:
                    features_to_remove.add(feat1)
                    features_to_keep.discard(feat1)
            else:
                # 如果没有目标变量信息，保留字典序靠前的特征
                if feat1 < feat2:
                    features_to_remove.add(feat2)
                    features_to_keep.discard(feat2)
                else:
                    features_to_remove.add(feat1)
                    features_to_keep.discard(feat1)

        logger.info(
            f"共线性检测完成: 发现 {len(high_corr_pairs)} 个高相关性对, "
            f"移除 {len(features_to_remove)} 个特征"
        )

        return list(features_to_keep), list(features_to_remove)

    def calculate_feature_importance(
        self, X: pd.DataFrame, y: pd.Series
    ) -> pd.DataFrame:
        """计算特征重要性.

        Args:
            X: 特征矩阵
            y: 目标变量

        Returns:
            包含特征重要性的DataFrame
        """
        logger.info("计算特征重要性...")

        importance_scores = {}

        # 1. 随机森林重要性
        try:
            rf_model = clone(self.rf_model)
            rf_model.fit(X, y)
            rf_importance = rf_model.feature_importances_

            for i, feature in enumerate(X.columns):
                importance_scores[f"{feature}_rf"] = rf_importance[i]
        except Exception as e:
            logger.warning(f"随机森林重要性计算失败: {e}")

        # 2. XGBoost重要性（如果可用）
        if self.xgb_model is not None:
            try:
                xgb_model = clone(self.xgb_model)
                xgb_model.fit(X, y)
                xgb_importance = xgb_model.feature_importances_

                for i, feature in enumerate(X.columns):
                    importance_scores[f"{feature}_xgb"] = xgb_importance[i]
            except Exception as e:
                logger.warning(f"XGBoost重要性计算失败: {e}")

        # 3. 互信息
        try:
            if self.task_type == "classification":
                mi_scores = mutual_info_classif(X, y, random_state=self.random_state)
            else:
                mi_scores = mutual_info_regression(X, y, random_state=self.random_state)

            for i, feature in enumerate(X.columns):
                importance_scores[f"{feature}_mi"] = mi_scores[i]
        except Exception as e:
            logger.warning(f"互信息计算失败: {e}")

        # 汇总重要性得分
        feature_importance_list = []
        for feature in X.columns:
            scores = []
            for key, value in importance_scores.items():
                if key.startswith(f"{feature}_"):
                    scores.append(value)

            avg_importance = np.mean(scores) if scores else 0
            max_importance = np.max(scores) if scores else 0
            feature_importance_list.append(
                {
                    "feature": feature
                    "importance_avg": avg_importance
                    "importance_max": max_importance
                    "rf_importance": importance_scores.get(f"{feature}_rf", 0)
                    "xgb_importance": importance_scores.get(f"{feature}_xgb", 0)
                    "mi_importance": importance_scores.get(f"{feature}_mi", 0)
                    "score_count": len(scores)
                }
            )

        self.feature_importance_df = pd.DataFrame(feature_importance_list)
        self.feature_importance_df = self.feature_importance_df.sort_values(
            "importance_avg", ascending=False
        ).reset_index(drop=True)

        logger.info(f"特征重要性计算完成，共 {len(self.feature_importance_df)} 个特征")

        return self.feature_importance_df

    def select_features(
        self
        X: pd.DataFrame
        y: pd.Series
        top_k: int = 20
        remove_collinear: bool = True
        importance_threshold: Optional[float] = None
    ) -> list[str]:
        """选择最重要的特征.

        Args:
            X: 特征矩阵
            y: 目标变量
            top_k: 保留的特征数量
            remove_collinear: 是否移除共线性特征
            importance_threshold: 重要性阈值，低于此值的特征将被过滤

        Returns:
            选择的特征列表
        """
        logger.info(f"开始特征选择: top_k={top_k}, remove_collinear={remove_collinear}")

        # 1. 移除共线性特征
        if remove_collinear:
            features_to_keep, collinear_removed = self.detect_collinearity(X, y)
            X_filtered = X[features_to_keep]
        else:
            X_filtered = X.copy()
            collinear_removed = []

        # 2. 计算特征重要性
        importance_df = self.calculate_feature_importance(X_filtered, y)

        # 3. 应用重要性阈值
        if importance_threshold is not None:
            importance_df = importance_df[
                importance_df["importance_avg"] >= importance_threshold
            ]

        # 4. 选择top_k个特征
        if len(importance_df) > top_k:
            selected_df = importance_df.head(top_k)
        else:
            selected_df = importance_df

        # 5. 确保最少特征数
        if len(selected_df) < self.min_features:
            logger.warning(
                f"选择的特征数 ({len(selected_df)}) 少于最小值 ({self.min_features})"
            )
            selected_df = importance_df.head(self.min_features)

        # 6. 确保最多特征数
        if len(selected_df) > self.max_features:
            selected_df = selected_df.head(self.max_features)

        self.selected_features = selected_df["feature"].tolist()
        self.removed_features = (
            list(set(X.columns) - set(self.selected_features)) + collinear_removed
        )

        # 记录选择历史
        selection_record = {
            "total_features": len(X.columns)
            "selected_features": len(self.selected_features)
            "removed_features": len(self.removed_features)
            "collinear_removed": len(collinear_removed)
            "top_k": top_k
            "importance_threshold": importance_threshold
        }
        self.selection_history.append(selection_record)

        logger.info(
            f"特征选择完成: {len(X.columns)} -> {len(self.selected_features)} 个特征"
        )

        return self.selected_features

    def evaluate_feature_subset(
        self, X: pd.DataFrame, y: pd.Series, feature_subset: list[str]
    ) -> dict[str, float]:
        """评估特征子集的性能.

        Args:
            X: 完整特征矩阵
            y: 目标变量
            feature_subset: 特征子集

        Returns:
            性能指标字典
        """
        if len(feature_subset) == 0:
            return {"score": 0.0}

        X_subset = X[feature_subset]

        # 使用交叉验证评估性能
        try:
            if self.task_type == "classification":
                scoring = "accuracy"
            else:
                scoring = "neg_mean_squared_error"

            scores = cross_val_score(
                self.rf_model, X_subset, y, cv=5, scoring=scoring, n_jobs=self.n_jobs
            )

            return {
                "score": scores.mean()
                "score_std": scores.std()
                "features_count": len(feature_subset)
            }
        except Exception as e:
            logger.warning(f"特征子集评估失败: {e}")
            return {"score": 0.0, "features_count": len(feature_subset)}

    def get_selection_report(self) -> dict:
        """获取特征选择报告.

        Returns:
            详细的选择报告
        """
        report = {
            "task_type": self.task_type
            "correlation_threshold": self.correlation_threshold
            "selected_features": self.selected_features
            "removed_features": self.removed_features
            "selection_history": self.selection_history
            "feature_importance": None
            "correlation_matrix": None
        }

        if self.feature_importance_df is not None:
            report["feature_importance"] = self.feature_importance_df.to_dict("records")

        if self.correlation_matrix is not None:
            report["correlation_matrix"] = self.correlation_matrix.to_dict()

        return report

    def save_selection_results(self, filepath: str):
        """保存特征选择结果.

        Args:
            filepath: 保存路径
        """
        results = {
            "selected_features": self.selected_features
            "removed_features": self.removed_features
            "selection_report": self.get_selection_report()
            "parameters": {
                "task_type": self.task_type
                "correlation_threshold": self.correlation_threshold
                "min_features": self.min_features
                "max_features": self.max_features
                "random_state": self.random_state
            }
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"特征选择结果已保存到: {filepath}")

    def load_selection_results(self, filepath: str):
        """加载特征选择结果.

        Args:
            filepath: 加载路径
        """
        with open(filepath, encoding="utf-8") as f:
            results = json.load(f)

        self.selected_features = results["selected_features"]
        self.removed_features = results["removed_features"]

        # 恢复参数
        params = results["parameters"]
        self.task_type = params["task_type"]
        self.correlation_threshold = params["correlation_threshold"]
        self.min_features = params["min_features"]
        self.max_features = params["max_features"]
        self.random_state = params["random_state"]

        logger.info(f"特征选择结果已从 {filepath} 加载")

    def plot_feature_importance(self, top_k: int = 20, save_path: Optional[str] = None):
        """绘制特征重要性图.

        Args:
            top_k: 显示前k个重要特征
            save_path: 保存路径
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            if self.feature_importance_df is None:
                logger.warning("没有特征重要性数据可供绘制")
                return

            # 取前k个特征
            plot_data = self.feature_importance_df.head(top_k)

            plt.figure(figsize=(12, 8))
            sns.barplot(
                data=plot_data, x="importance_avg", y="feature", palette="viridis"
            )
            plt.title(f"前 {top_k} 个特征的重要性")
            plt.xlabel("平均重要性")
            plt.ylabel("特征名称")
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches="tight")
                logger.info(f"特征重要性图已保存到: {save_path}")

            plt.show()

        except ImportError:
            logger.warning("绘图需要安装 matplotlib 和 seaborn")


def create_feature_selector(
    task_type: str = "classification", correlation_threshold: float = 0.95, **kwargs
) -> FeatureSelector:
    """创建特征选择器的便捷函数.

    Args:
        task_type: 任务类型
        correlation_threshold: 共线性阈值
        **kwargs: 其他参数

    Returns:
        FeatureSelector实例
    """
    return FeatureSelector(
        task_type=task_type, correlation_threshold=correlation_threshold, **kwargs
    )
