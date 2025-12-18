#!/usr/bin/env python3
"""
XGBoost模型优化器
专门为足球赛果预测系统设计的模型优化工具
"""

import optuna
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import mlflow
import mlflow.xgboost
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.feature_selection import SelectKBest, mutual_info_classif
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Any
import joblib
import json
import warnings
warnings.filterwarnings('ignore')

class FootballPredictionOptimizer:
    """足球赛果预测XGBoost优化器"""

    def __init__(self, target_accuracy: float = 0.65, target_latency_ms: float = 100.0):
        self.target_accuracy = target_accuracy
        self.target_latency_ms = target_latency_ms
        self.best_params = None
        self.best_score = 0
        self.feature_importance = None
        self.shap_explainer = None

    def optimize_hyperparameters(self, X_train, y_train, X_val, y_val, n_trials: int = 100):
        """使用Optuna进行超参数优化"""

        def objective(trial):
            # 定义搜索空间
            params = {
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_loguniform('learning_rate', 0.01, 0.3),
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'subsample': trial.suggest_uniform('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_uniform('colsample_bytree', 0.6, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                'gamma': trial.suggest_uniform('gamma', 0, 5),
                'reg_alpha': trial.suggest_uniform('reg_alpha', 0, 1),
                'reg_lambda': trial.suggest_uniform('reg_lambda', 0, 1),
                'objective': 'multi:softprob',
                'num_class': 3,  # HOME, DRAW, AWAY
                'eval_metric': 'mlogloss',
                'random_state': 42,
                'tree_method': 'hist',  # 快速训练
                'n_jobs': -1
            }

            # 创建模型
            model = xgb.XGBClassifier(**params)

            # 交叉验证
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            scores = cross_val_score(model, X_train, y_train, cv=cv, scoring='accuracy')

            # 记录到MLflow
            with mlflow.start_run(nested=True):
                mlflow.log_params(params)
                mlflow.log_metric("cv_accuracy", scores.mean())
                mlflow.log_metric("cv_std", scores.std())

            return scores.mean()

        # 创建study
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42),
            pruner=optuna.pruners.MedianPruner(n_startup_trials=10)
        )

        # 优化
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

        self.best_params = study.best_params
        self.best_score = study.best_value

        print(f"最佳参数: {self.best_params}")
        print(f"最佳交叉验证分数: {self.best_score:.4f}")

        return self.best_params, self.best_score

    def select_features(self, X, y, k: int = 20) -> Tuple[pd.DataFrame, List[str]]:
        """特征选择"""
        # 使用互信息进行特征选择
        selector = SelectKBest(mutual_info_classif, k=k)
        X_selected = selector.fit_transform(X, y)

        selected_features = X.columns[selector.get_support()].tolist()

        print(f"选择了 {k} 个最重要的特征: {selected_features}")

        return pd.DataFrame(X_selected, columns=selected_features), selected_features

    def train_final_model(self, X_train, y_train, X_val, y_val, params: Dict = None):
        """训练最终模型"""
        if params is None:
            params = self.best_params or self._get_default_params()

        # 添加最终训练参数
        final_params = params.copy()
        final_params.update({
            'objective': 'multi:softprob',
            'num_class': 3,
            'eval_metric': 'mlogloss',
            'random_state': 42,
            'tree_method': 'hist',
            'n_jobs': -1
        })

        # 创建模型
        model = xgb.XGBClassifier(**final_params)

        # 训练模型
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )

        # 评估模型
        y_pred = model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)

        print(f"验证集准确率: {accuracy:.4f}")
        print("\n分类报告:")
        print(classification_report(y_val, y_pred, target_names=['HOME', 'DRAW', 'AWAY']))

        # 保存特征重要性
        self.feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        # 创建SHAP解释器
        self.shap_explainer = shap.TreeExplainer(model)

        return model, accuracy

    def analyze_with_shap(self, model, X_sample, max_display: int = 10):
        """使用SHAP进行模型解释"""
        # 计算SHAP值
        shap_values = self.shap_explainer.shap_values(X_sample)

        # 创建可视化
        plt.figure(figsize=(12, 8))

        # 特征重要性摘要图
        shap.summary_plot(shap_values, X_sample, max_display=max_display,
                         class_names=['HOME', 'DRAW', 'AWAY'])

        # 保存图表
        plt.savefig('shap_summary.png', dpi=300, bbox_inches='tight')
        plt.show()

        return shap_values

    def evaluate_performance(self, model, X_test, y_test):
        """全面评估模型性能"""
        # 预测
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)

        # 准确率
        accuracy = accuracy_score(y_test, y_pred)

        # 混淆矩阵
        cm = confusion_matrix(y_test, y_pred)

        # 分类报告
        report = classification_report(y_test, y_pred, target_names=['HOME', 'DRAW', 'AWAY'])

        print(f"测试集准确率: {accuracy:.4f}")
        print(f"目标准确率: {self.target_accuracy:.4f}")
        print(f"达到目标: {'✅' if accuracy >= self.target_accuracy else '❌'}")

        print("\n混淆矩阵:")
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['HOME', 'DRAW', 'AWAY'],
                   yticklabels=['HOME', 'DRAW', 'AWAY'])
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight')
        plt.show()

        print("\n分类报告:")
        print(report)

        return {
            'accuracy': accuracy,
            'confusion_matrix': cm,
            'classification_report': report,
            'probabilities': y_proba
        }

    def check_inference_latency(self, model, X_sample, n_runs: int = 1000):
        """检查推理延迟"""
        import time

        start_time = time.time()
        for _ in range(n_runs):
            _ = model.predict_proba(X_sample[:1])
        end_time = time.time()

        avg_latency_ms = (end_time - start_time) * 1000 / n_runs

        print(f"平均推理延迟: {avg_latency_ms:.2f} ms")
        print(f"目标延迟: {self.target_latency_ms:.2f} ms")
        print(f"达到目标: {'✅' if avg_latency_ms <= self.target_latency_ms else '❌'}")

        return avg_latency_ms

    def save_optimization_results(self, model, results_dir: str = 'optimization_results'):
        """保存优化结果"""
        import os
        os.makedirs(results_dir, exist_ok=True)

        # 保存模型
        joblib.dump(model, f'{results_dir}/optimized_model.joblib')

        # 保存最佳参数
        if self.best_params:
            with open(f'{results_dir}/best_params.json', 'w') as f:
                json.dump(self.best_params, f, indent=2)

        # 保存特征重要性
        if self.feature_importance is not None:
            self.feature_importance.to_csv(f'{results_dir}/feature_importance.csv', index=False)

        # 保存优化报告
        report = {
            'best_cv_score': self.best_score,
            'target_accuracy': self.target_accuracy,
            'target_latency_ms': self.target_latency_ms,
            'feature_count': len(self.feature_importance) if self.feature_importance is not None else 0
        }

        with open(f'{results_dir}/optimization_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"优化结果已保存到 {results_dir}")

    def _get_default_params(self):
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


def main():
    """主函数示例"""
    # 这里需要根据实际数据加载逻辑修改
    print("足球赛果预测模型优化器")
    print("=" * 50)

    # 初始化优化器
    optimizer = FootballPredictionOptimizer(target_accuracy=0.65, target_latency_ms=100.0)

    # 示例：你需要根据实际情况加载数据
    # X, y = load_football_data()
    # X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    # X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

    print("请根据实际数据情况调用以下方法:")
    print("1. optimizer.optimize_hyperparameters(X_train, y_train, X_val, y_val)")
    print("2. optimizer.select_features(X_train, y_train, k=20)")
    print("3. model, accuracy = optimizer.train_final_model(X_train, y_train, X_val, y_val)")
    print("4. optimizer.evaluate_performance(model, X_test, y_test)")
    print("5. optimizer.check_inference_latency(model, X_test)")
    print("6. optimizer.save_optimization_results(model)")


if __name__ == "__main__":
    main()