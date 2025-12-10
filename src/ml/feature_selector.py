#!/usr/bin/env python3
"""
高级特征选择器 - 基于模型重要性、共线性检测和多重策略的自动化特征选择工具。
支持分类和回归任务，提供详细的特征分析报告。
"""

import logging
from typing import Any, , , Optional, , Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_selection import (
    RFE,
    SelectKBest,
    f_classif,
    f_regression,
    mutual_info_classif,
    mutual_info_regression,
)
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


class AdvancedFeatureSelector:
    """
    高级特征选择器 - 基于模型重要性、共线性检测和多重策略的自动化特征选择工具。
    支持分类和回归任务，提供详细的特征分析报告。
    """

    def __init__(
        self,
        task_type: str = "classification",  # "classification" 或 "regression"
        correlation_threshold: float = 0.95,
        min_features: int = 5,
        max_features: int = 100,
        random_state: int = 42,
        n_jobs: int = -1,
    ):
        """
        初始化特征选择器.

        Args:
            task_type: 任务类型，'classification' 或 'regression'
            correlation_threshold: 相关性阈值，超过此值的特征会被移除
            min_features: 最少保留特征数
            max_features: 最多保留特征数
            random_state: 随机种子
            n_jobs: 并行作业数
        """
        self.task_type = task_type
        self.correlation_threshold = correlation_threshold
        self.min_features = min_features
        self.max_features = max_features
        self.random_state = random_state
        self.n_jobs = n_jobs

        # 存储结果
        self.selected_features: list[str] = []
        self.feature_importance: dict[str, float] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.removed_features: list[str] = []
        self.selection_report: dict[str, Any] = {}

        # 初始化基础模型
        self._init_base_models()

    def _init_base_models(self):
        """初始化基础模型用于特征重要性评估."""
        # 随机森林模型
        self.rf_model = (
            RandomForestClassifier(
                n_estimators=100,
                random_state=self.random_state,
                n_jobs=self.n_jobs,
                max_depth=10,
            )
            if self.task_type == "classification"
            else RandomForestRegressor(
                n_estimators=100,
                random_state=self.random_state,
                n_jobs=self.n_jobs,
                max_depth=10,
            )
        )

        # XGBoost模型（如果可用）
        self.xgb_model = None
        try:
            import xgboost as xgb

            self.xgb_model = (
                xgb.XGBClassifier(
                    n_estimators=100,
                    random_state=self.random_state,
                    n_jobs=self.n_jobs,
                    max_depth=6,
                    learning_rate=0.1,
                )
                if self.task_type == "classification"
                else xgb.XGBRegressor(
                    n_estimators=100,
                    random_state=self.random_state,
                    n_jobs=self.n_jobs,
                    max_depth=6,
                    learning_rate=0.1,
                )
            )
        except ImportError:
            logger.warning("XGBoost not available, using only RandomForest")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "AdvancedFeatureSelector":
        """
        执行特征选择流程.

        Args:
            X: 特征矩阵
            y: 目标变量

        Returns:
            self: 返回自身实例
        """
        logger.info(f"🔍 开始特征选择流程 - 任务类型: {self.task_type}")
        logger.info(f"📊 输入特征数量: {X.shape[1]}")

        # 1. 数据预处理
        X_clean = self._preprocess_data(X)

        # 2. 移除常数特征
        X_clean, constant_removed = self._remove_constant_features(X_clean)
        logger.info(f"📊 移除常数特征后: {X_clean.shape[1]}")

        # 3. 移除高相关性特征
        X_clean, correlation_removed = self._remove_high_correlation_features(X_clean)
        logger.info(f"📊 移除高相关性特征后: {X_clean.shape[1]}")

        # 4. 基于模型重要性的特征选择
        X_clean, model_removed = self._select_by_model_importance(X_clean, y)
        logger.info(f"📊 模型重要性选择后: {X_clean.shape[1]}")

        # 5. 基于统计测试的特征选择
        X_clean, statistical_removed = self._select_by_statistical_tests(X_clean, y)
        logger.info(f"📊 统计测试选择后: {X_clean.shape[1]}")

        # 6. 递归特征消除
        X_clean, rfe_removed = self._recursive_feature_elimination(X_clean, y)
        logger.info(f"📊 递归特征消除后: {X_clean.shape[1]}")

        # 7. 最终特征数量调整
        X_clean = self._adjust_feature_count(X_clean, y)
        logger.info(f"📊 最终特征数量: {X_clean.shape[1]}")

        # 存储结果
        self.selected_features = X_clean.columns.tolist()
        self.selection_report = {
            "original_features": X.shape[1],
            "constant_removed": constant_removed,
            "correlation_removed": correlation_removed,
            "model_removed": model_removed,
            "statistical_removed": statistical_removed,
            "rfe_removed": rfe_removed,
            "final_features": len(self.selected_features),
        }

        logger.info(f"✅ 特征选择完成，保留 {len(self.selected_features)} 个特征")

        return self

    def _preprocess_data(self, X: pd.DataFrame) -> pd.DataFrame:
        """数据预处理."""
        # 处理缺失值
        X_clean = X.copy()

        # 数值型特征用中位数填充
        numeric_cols = X_clean.select_dtypes(include=[np.number]).columns
        X_clean[numeric_cols] = X_clean[numeric_cols].fillna(
            X_clean[numeric_cols].median()
        )

        # 分类特征用众数填充
        categorical_cols = X_clean.select_dtypes(include=["object"]).columns
        for col in categorical_cols:
            X_clean[col] = X_clean[col].fillna(
                X_clean[col].mode()[0] if len(X_clean[col].mode()) > 0 else "Unknown"
            )

        return X_clean

    def _remove_constant_features(
        self, X: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[str]]:
        """移除常数特征."""
        constant_features = []

        for col in X.columns:
            unique_values = X[col].nunique()
            if unique_values <= 1:
                constant_features.append(col)

        X_clean = X.drop(columns=constant_features)
        self.removed_features.extend(
            [f"Constant feature: {col}" for col in constant_features]
        )

        return X_clean, constant_features

    def _remove_high_correlation_features(
        self, X: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[str]]:
        """移除高相关性特征."""
        # 只对数值型特征计算相关性
        numeric_cols = X.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) <= 1:
            return X, []

        correlation_matrix = X[numeric_cols].corr().abs()

        # 找到高相关性的特征对
        high_corr_features = set()
        for i in range(len(correlation_matrix.columns)):
            for j in range(i + 1, len(correlation_matrix.columns)):
                if correlation_matrix.iloc[i, j] > self.correlation_threshold:
                    col_i = correlation_matrix.columns[i]
                    col_j = correlation_matrix.columns[j]
                    # 移除相关性较高的特征（保留在字典中顺序靠后的）
                    if correlation_matrix.columns.get_loc(
                        col_i
                    ) < correlation_matrix.columns.get_loc(col_j):
                        high_corr_features.add(col_i)
                        self.removed_features.append(
                            f"High correlation: {col_i} with {col_j}"
                        )

        self.correlation_matrix = correlation_matrix
        X_clean = X.drop(columns=list(high_corr_features))

        return X_clean, list(high_corr_features)

    def _select_by_model_importance(
        self, X: pd.DataFrame, y: pd.Series
    ) -> tuple[pd.DataFrame, list[str]]:
        """基于模型重要性选择特征."""
        # 随机森林重要性
        rf_scores = self._get_rf_importance(X, y)

        # XGBoost重要性（如果可用）
        xgb_scores = {}
        if self.xgb_model is not None:
            xgb_scores = self._get_xgb_importance(X, y)

        # 合并重要性得分
        feature_scores = {}
        for feature in X.columns:
            score = rf_scores.get(feature, 0)
            if xgb_scores:
                score = (score + xgb_scores.get(feature, 0)) / 2
            feature_scores[feature] = score

        # 按重要性排序并选择
        sorted_features = sorted(
            feature_scores.items(), key=lambda x: x[1], reverse=True
        )
        self.feature_importance = dict(sorted_features)

        # 保留重要性较高的特征
        importance_threshold = np.percentile(
            list(feature_scores.values()), 50
        )  # 中位数作为阈值
        selected_features = [f for f, s in sorted_features if s >= importance_threshold]

        if len(selected_features) < self.min_features:
            selected_features = [f for f, s in sorted_features[: self.min_features]]

        removed_features = [f for f in X.columns if f not in selected_features]
        self.removed_features.extend([f"Low importance: {f}" for f in removed_features])

        return X[selected_features], removed_features

    def _get_rf_importance(self, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        """获取随机森林特征重要性."""
        self.rf_model.fit(X, y)
        return dict(zip(X.columns, self.rf_model.feature_importances_, strict=False))

    def _get_xgb_importance(self, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        """获取XGBoost特征重要性."""
        self.xgb_model.fit(X, y)
        if hasattr(self.xgb_model, "feature_importances_"):
            return dict(
                zip(X.columns, self.xgb_model.feature_importances_, strict=False)
            )
        return {}

    def _select_by_statistical_tests(
        self, X: pd.DataFrame, y: pd.Series
    ) -> tuple[pd.DataFrame, list[str]]:
        """基于统计测试选择特征."""
        if self.task_type == "classification":
            selector = SelectKBest(f_classif, k=min(len(X.columns), 50))
        else:
            selector = SelectKBest(f_regression, k=min(len(X.columns), 50))

        selector.fit(X, y)
        X.columns[selector.get_support()].tolist()

        # 选择分数最高的特征
        scores = selector.scores_
        feature_scores = dict(zip(X.columns, scores, strict=False))
        sorted_features = sorted(
            feature_scores.items(), key=lambda x: x[1], reverse=True
        )

        # 保留分数较高的特征
        score_threshold = np.percentile(scores[~np.isnan(scores)], 50)
        final_selected = [f for f, s in sorted_features if s >= score_threshold]

        if len(final_selected) < self.min_features:
            final_selected = [f for f, s in sorted_features[: self.min_features]]

        removed_features = [f for f in X.columns if f not in final_selected]
        self.removed_features.extend(
            [f"Low statistical score: {f}" for f in removed_features]
        )

        return X[final_selected], removed_features

    def _recursive_feature_elimination(
        self, X: pd.DataFrame, y: pd.Series
    ) -> tuple[pd.DataFrame, list[str]]:
        """递归特征消除."""
        n_features_to_select = min(len(X.columns), max(self.min_features, 20))

        rfe = RFE(
            estimator=self.rf_model,
            n_features_to_select=n_features_to_select,
            step=1,
        )

        rfe.fit(X, y)
        selected_features = X.columns[rfe.support_].tolist()
        removed_features = [f for f in X.columns if f not in selected_features]
        self.removed_features.extend([f"RFE eliminated: {f}" for f in removed_features])

        return X[selected_features], removed_features

    def _adjust_feature_count(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """调整最终特征数量."""
        current_features = len(X.columns)

        if current_features > self.max_features:
            # 使用交叉验证选择最佳特征数量
            best_features = self._select_best_features_by_cv(X, y, self.max_features)
            return X[best_features]
        elif current_features < self.min_features:
            # 如果特征太少，返回所有特征
            logger.warning(
                f"特征数量({current_features})少于最小要求({self.min_features})"
            )

        return X

    def _select_best_features_by_cv(
        self, X: pd.DataFrame, y: pd.Series, max_features: int
    ) -> list[str]:
        """使用交叉验证选择最佳特征组合."""
        feature_scores = {}

        for feature in X.columns:
            # 单特征交叉验证
            single_feature = X[[feature]]
            scores = cross_val_score(
                self.rf_model,
                single_feature,
                y,
                cv=5,
                scoring=(
                    "f1"
                    if self.task_type == "classification"
                    else "neg_mean_squared_error"
                ),
            )
            feature_scores[feature] = np.mean(scores)

        # 按分数排序并选择最佳特征
        sorted_features = sorted(
            feature_scores.items(), key=lambda x: x[1], reverse=True
        )
        return [f for f, s in sorted_features[:max_features]]

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """转换数据，只保留选择的特征."""
        missing_features = [f for f in self.selected_features if f not in X.columns]
        if missing_features:
            logger.warning(f"输入数据缺少特征: {missing_features}")

        # 只返回存在的选择特征
        available_features = [f for f in self.selected_features if f in X.columns]
        return X[available_features]

    def get_support(self) -> list[bool]:
        """
        获取特征掩码.

        Returns:
            bool列表，长度等于输入特征数，True表示被选择
        """
        if not hasattr(self, "_input_feature_names"):
            return []

        support = [
            feature in self.selected_features for feature in self._input_feature_names
        ]
        return support

    def get_feature_importance_ranking(self) -> list[tuple[str, float]]:
        """获取特征重要性排名."""
        if not self.feature_importance:
            return []

        return sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)

    def plot_feature_importance(
        self, top_n: int = 20, figsize: tuple[int, int] = (12, 8)
    ):
        """绘制特征重要性图表."""
        if not self.feature_importance:
            logger.warning("没有特征重要性数据可绘制")
            return

        # 获取top_n特征
        top_features = self.get_feature_importance_ranking()[:top_n]
        features, importance = zip(*top_features, strict=False)

        plt.figure(figsize=figsize)
        sns.barplot(x=list(importance), y=list(features))
        plt.title(f"Top {top_n} Feature Importance")
        plt.xlabel("Importance Score")
        plt.ylabel("Features")

        # 添加数值标签
        for i, v in enumerate(importance):
            plt.text(v + 0.001, i, f"{v:.4f}", va="center")

        plt.tight_layout()
        plt.show()

    def plot_correlation_matrix(self, figsize: tuple[int, int] = (12, 10)):
        """绘制相关性矩阵热图."""
        if self.correlation_matrix is None:
            logger.warning("没有相关性矩阵数据可绘制")
            return

        plt.figure(figsize=figsize)
        sns.heatmap(
            self.correlation_matrix,
            annot=True,
            cmap="coolwarm",
            center=0,
            square=True,
            fmt=".2f",
        )
        plt.title("Feature Correlation Matrix")
        plt.tight_layout()
        plt.show()

    def generate_report(self) -> dict[str, Any]:
        """生成详细的特征选择报告."""
        if not self.selection_report:
            logger.warning("请先运行fit方法")
            return {}

        report = {
            **self.selection_report,
            "selected_features": self.selected_features,
            "removed_features_count": len(self.removed_features),
            "removed_features": self.removed_features,
            "feature_importance": self.feature_importance,
            "correlation_threshold": self.correlation_threshold,
            "min_features": self.min_features,
            "max_features": self.max_features,
        }

        # 添加统计信息
        if self.feature_importance:
            importance_scores = list(self.feature_importance.values())
            report["importance_stats"] = {
                "mean": np.mean(importance_scores),
                "std": np.std(importance_scores),
                "min": np.min(importance_scores),
                "max": np.max(importance_scores),
            }

        return report

    def save_report(self, filepath: str):
        """保存报告到文件."""
        report = self.generate_report()

        if filepath.endswith(".json"):
            import json

            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=str)
        else:
            with open(filepath, "w") as f:
                f.write("Feature Selection Report\n")
                f.write("=" * 50 + "\n\n")

                for key, value in report.items():
                    f.write(f"{key}:\n")
                    if isinstance(value, list):
                        for item in value:
                            f.write(f"  - {item}\n")
                    else:
                        f.write(f"  {value}\n")
                    f.write("\n")

        logger.info(f"特征选择报告已保存到: {filepath}")


# 使用示例
def example_usage():
    """使用示例."""
    # 创建示例数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)],
    )

    # 添加一些相关的特征
    X["feature_21"] = X["feature_1"] * 0.9 + np.random.randn(n_samples) * 0.1
    X["feature_22"] = X["feature_2"] * 0.8 + np.random.randn(n_samples) * 0.2

    # 创建分类目标
    y = pd.Series(np.random.choice([0, 1], n_samples))

    # 初始化特征选择器
    selector = AdvancedFeatureSelector(
        task_type="classification",
        correlation_threshold=0.9,
        min_features=5,
        max_features=15,
    )

    # 执行特征选择
    selector.fit(X, y)

    # 获取报告
    report = selector.generate_report()
    print(f"原始特征数: {report['original_features']}")
    print(f"最终特征数: {report['final_features']}")
    print(f"选择的特征: {report['selected_features']}")

    # 转换数据
    X_transformed = selector.transform(X)
    print(f"转换后数据形状: {X_transformed.shape}")


if __name__ == "__main__":
    example_usage()
