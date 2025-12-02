#!/usr/bin/env python3
"""
基于 Optuna 的 XGBoost 超参数优化脚本
XGBoost Hyperparameter Tuning with Optuna

该脚本使用 Optuna 框架自动寻找 XGBoost 的最佳参数组合，以提升预测准确率。
脚本会加载现有数据，进行特征工程，然后执行超参数优化。

使用方法 / Usage:
    python scripts/tune_model_optuna.py

输出 / Output:
    - Optuna 优化过程日志
    - 最佳参数组合
    - 提升后的准确率
    - 优化后的模型文件
"""

import os
import sys
import logging
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入核心依赖
try:
    import pandas as pd
    import numpy as np
    import optuna
    from optuna.samplers import TPESampler
    from optuna.visualization import plot_optimization_history, plot_parallel_coordinate
    import xgboost as xgb
    from sklearn.model_selection import train_test_split, StratifiedKFold
    from sklearn.metrics import accuracy_score, f1_score, classification_report
    from sklearn.preprocessing import LabelEncoder, StandardScaler

    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    print(f"❌ 缺少依赖: {e}")
    print("请安装: pip install optuna xgboost scikit-learn pandas numpy")
    sys.exit(1)

# 导入项目模块
try:
    from src.ml.xgboost_hyperparameter_optimization import (
        XGBoostHyperparameterOptimizer,
    )
    from src.ml.enhanced_feature_engineering import EnhancedFeatureEngineering

    HAS_PROJECT_MODULES = True
except ImportError:
    HAS_PROJECT_MODULES = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class OptunaHyperparameterTuner:
    """基于 Optuna 的 XGBoost 超参数优化器."""

    def __init__(
        self,
        n_trials: int = 50,
        cv_folds: int = 5,
        random_state: int = 42,
        model_save_path: str = "models/football_prediction_v4_optuna.pkl",
    ):
        """初始化优化器.

        Args:
            n_trials: 试验次数
            cv_folds: 交叉验证折数
            random_state: 随机种子
            model_save_path: 模型保存路径
        """
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.model_save_path = model_save_path

        # 初始化变量
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.study = None
        self.best_model = None
        self.best_params = None
        self.best_score = None
        self.feature_names = None
        self.label_encoder = None

        # 确保目录存在
        Path("logs").mkdir(exist_ok=True, parents=True)
        Path("models").mkdir(exist_ok=True, parents=True)

        logger.info("🚀 初始化 Optuna 超参数优化器")
        logger.info(f"📊 试验次数: {n_trials}, 交叉验证: {cv_folds}折")

    def load_and_prepare_data(
        self, data_path: str = "data/advanced_features.csv"
    ) -> bool:
        """加载并准备训练数据.

        Args:
            data_path: 数据文件路径

        Returns:
            bool: 加载是否成功
        """
        try:
            logger.info(f"📁 加载数据集: {data_path}")

            # 检查数据文件是否存在
            if not os.path.exists(data_path):
                logger.error(f"❌ 数据文件不存在: {data_path}")
                # 尝试其他可能的数据文件
                alternative_paths = [
                    "data/processed_dataset.csv",
                    "data/football_matches.csv",
                    "data/matches_features.csv",
                ]
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        data_path = alt_path
                        logger.info(f"🔄 使用替代数据文件: {data_path}")
                        break
                else:
                    logger.error("❌ 未找到可用的数据文件")
                    return False

            # 加载数据
            data = pd.read_csv(data_path)
            logger.info(f"✅ 数据加载成功: {data.shape}")

            # 数据预处理
            logger.info("🔧 开始数据预处理...")

            # 检查必要的列
            required_columns = ["result"]  # 目标变量
            missing_columns = [
                col for col in required_columns if col not in data.columns
            ]
            if missing_columns:
                logger.error(f"❌ 缺少必要列: {missing_columns}")
                logger.info(f"📋 可用列: {list(data.columns)}")
                return False

            # 移除不必要的列
            columns_to_drop = [
                "match_id",
                "match_date",
                "home_team_id",
                "away_team_id",
                "league_id",
                "season",
                "home_score",
                "away_score",
                "goal_difference",
                "total_goals",
                "over_2_5_goals",
                "both_teams_score",
            ]
            columns_to_drop = [col for col in columns_to_drop if col in data.columns]
            data = data.drop(columns=columns_to_drop)

            # 分离特征和目标
            X = data.drop("result", axis=1)
            y = data["result"]

            # 处理缺失值
            X = X.fillna(X.median())

            # 编码目标变量
            if y.dtype == "object":
                self.label_encoder = LabelEncoder()
                y_encoded = self.label_encoder.fit_transform(y)
                logger.info(f"🏷️ 目标变量编码: {self.label_encoder.classes_}")
            else:
                y_encoded = y
                self.label_encoder = None

            # 特征选择：移除常数特征
            constant_features = X.columns[X.nunique() <= 1].tolist()
            if constant_features:
                logger.info(f"🗑️ 移除常数特征: {constant_features}")
                X = X.drop(columns=constant_features)

            # 特征缩放
            scaler = StandardScaler()
            X_scaled = pd.DataFrame(
                scaler.fit_transform(X), columns=X.columns, index=X.index
            )

            # 分割训练集和测试集
            self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
                X_scaled,
                y_encoded,
                test_size=0.2,
                random_state=self.random_state,
                stratify=y_encoded,
            )

            self.feature_names = list(X_scaled.columns)

            logger.info("📊 最终数据形状:")
            logger.info(f"   训练集: {self.X_train.shape}")
            logger.info(f"   测试集: {self.X_test.shape}")
            logger.info(f"   特征数量: {len(self.feature_names)}")

            # 目标变量分布
            unique, counts = np.unique(self.y_train, return_counts=True)
            logger.info("🎯 训练集目标变量分布:")
            for cls, count in zip(unique, counts, strict=False):
                percentage = count / len(self.y_train) * 100
                if self.label_encoder:
                    cls_name = self.label_encoder.inverse_transform([cls])[0]
                    logger.info(f"   {cls_name}: {count} ({percentage:.1f}%)")
                else:
                    logger.info(f"   类别 {cls}: {count} ({percentage:.1f}%)")

            return True

        except Exception:
            logger.error(f"❌ 数据准备失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def objective(self, trial: optuna.Trial) -> float:
        """Optuna 目标函数.

        Args:
            trial: Optuna 试验对象

        Returns:
            float: 验证集准确率
        """
        # 定义超参数搜索空间
        param = {
            "objective": (
                "binary:logistic"
                if len(np.unique(self.y_train)) == 2
                else "multi:softprob"
            ),
            "eval_metric": "mlogloss",
            "random_state": self.random_state,
            "use_label_encoder": False,
            # 主要超参数
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            # 正则化参数
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 2.0),
            "min_child_weight": trial.suggest_float("min_child_weight", 1, 10),
            # 其他参数
            "gamma": trial.suggest_float("gamma", 0.0, 1.0),
            "max_leaves": trial.suggest_int("max_leaves", 0, 100),
        }

        # 设置多分类参数
        if len(np.unique(self.y_train)) > 2:
            param["num_class"] = len(np.unique(self.y_train))

        # 交叉验证
        cv = StratifiedKFold(
            n_splits=self.cv_folds, shuffle=True, random_state=self.random_state
        )
        cv_scores = []

        for train_idx, val_idx in cv.split(self.X_train, self.y_train):
            X_tr, X_val = self.X_train.iloc[train_idx], self.X_train.iloc[val_idx]
            y_tr, y_val = self.y_train[train_idx], self.y_train[val_idx]

            # 训练模型
            model = xgb.XGBClassifier(**param)

            # 早停
            eval_set = [(X_val, y_val)]
            model.fit(
                X_tr, y_tr, eval_set=eval_set, early_stopping_rounds=50, verbose=False
            )

            # 预测和评估
            y_pred = model.predict(X_val)
            accuracy = accuracy_score(y_val, y_pred)
            cv_scores.append(accuracy)

        # 返回平均准确率
        mean_accuracy = np.mean(cv_scores)

        # 记录中间结果
        trial.report(mean_accuracy, step=0)

        # 检查是否应该中断（剪枝）
        if trial.should_prune():
            raise optuna.exceptions.TrialPruned()

        return mean_accuracy

    def optimize(self) -> dict[str, Any]:
        """执行超参数优化.

        Returns:
            Dict: 优化结果
        """
        if self.X_train is None:
            raise ValueError("请先调用 load_and_prepare_data() 准备数据")

        logger.info("🎯 开始超参数优化...")

        # 创建研究
        self.study = optuna.create_study(
            direction="maximize",
            sampler=TPESampler(seed=self.random_state),
            pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=3),
        )

        # 定义回调函数
        def callback(study: optuna.Study, trial: optuna.Trial) -> None:
            if trial.number % 10 == 0 or trial.number == self.n_trials - 1:
                logger.info(
                    f"📊 Trial {trial.number + 1}/{self.n_trials} - "
                    f"Best Score: {study.best_value:.4f} - "
                    f"Current Score: {trial.value if trial.value else 'N/A':.4f}"
                )

        # 执行优化
        self.study.optimize(
            self.objective, n_trials=self.n_trials, callbacks=[callback]
        )

        # 获取最佳结果
        self.best_params = self.study.best_params
        self.best_score = self.study.best_value

        logger.info("🎉 优化完成!")
        logger.info(f"🏆 最佳准确率: {self.best_score:.4f}")
        logger.info(f"⚙️ 最佳参数: {json.dumps(self.best_params, indent=2)}")

        # 使用最佳参数训练最终模型
        logger.info("🔧 使用最佳参数训练最终模型...")
        best_params_full = self.best_params.copy()
        best_params_full.update(
            {
                "objective": (
                    "binary:logistic"
                    if len(np.unique(self.y_train)) == 2
                    else "multi:softprob"
                ),
                "eval_metric": "mlogloss",
                "random_state": self.random_state,
                "use_label_encoder": False,
            }
        )

        if len(np.unique(self.y_train)) > 2:
            best_params_full["num_class"] = len(np.unique(self.y_train))

        self.best_model = xgb.XGBClassifier(**best_params_full)

        # 训练最终模型
        eval_set = [(self.X_test, self.y_test)]
        self.best_model.fit(
            self.X_train,
            self.y_train,
            eval_set=eval_set,
            early_stopping_rounds=100,
            verbose=False,
        )

        # 评估模型
        train_score = accuracy_score(
            self.y_train, self.best_model.predict(self.X_train)
        )
        test_score = accuracy_score(self.y_test, self.best_model.predict(self.X_test))

        logger.info("📊 最终模型性能:")
        logger.info(f"   训练集准确率: {train_score:.4f}")
        logger.info(f"   测试集准确率: {test_score:.4f}")

        # 保存结果
        self.save_results()

        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "train_accuracy": train_score,
            "test_accuracy": test_score,
            "n_trials": len(self.study.trials),
            "study_name": self.study.study_name,
        }

    def save_results(self) -> None:
        """保存优化结果和模型."""
        try:
            # 保存模型
            with open(self.model_save_path, "wb") as f:
                pickle.dump(self.best_model, f)
            logger.info(f"💾 模型已保存: {self.model_save_path}")

            # 保存优化结果
            results = {
                "best_params": self.best_params,
                "best_score": float(self.best_score),
                "n_trials": len(self.study.trials),
                "study_name": self.study.study_name,
                "feature_names": self.feature_names,
                "optimization_time": datetime.now().isoformat(),
                "label_encoder_classes": (
                    self.label_encoder.classes_.tolist() if self.label_encoder else None
                ),
            }

            results_path = self.model_save_path.replace(".pkl", "_results.json")
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"📄 优化结果已保存: {results_path}")

            # 保存研究
            study_path = self.model_save_path.replace(".pkl", "_study.pkl")
            with open(study_path, "wb") as f:
                pickle.dump(self.study, f)
            logger.info(f"🔬 Optuna 研究已保存: {study_path}")

        except Exception:
            logger.error(f"❌ 保存结果失败: {e}")

    def generate_report(self) -> None:
        """生成优化报告."""
        if not self.study:
            logger.warning("⚠️ 没有可用的研究来生成报告")
            return

        try:
            logger.info("📊 生成优化报告...")

            # 基础统计
            logger.info("📈 优化统计:")
            logger.info(f"   总试验次数: {len(self.study.trials)}")
            logger.info(f"   最佳准确率: {self.study.best_value:.4f}")
            completed_trials = len(
                [
                    t
                    for t in self.study.trials
                    if t.state == optuna.trial.TrialState.COMPLETE
                ]
            )
            logger.info(f"   改进次数: {completed_trials}")

            # 参数重要性
            try:
                importance = optuna.importance.get_param_importances(self.study)
                logger.info("🔍 参数重要性:")
                for param, imp in sorted(
                    importance.items(), key=lambda x: x[1], reverse=True
                ):
                    logger.info(f"   {param}: {imp:.4f}")
            except Exception:
                logger.warning(f"⚠️ 无法计算参数重要性: {e}")

            # 最佳试验详情
            best_trial = self.study.best_trial
            logger.info(f"🏆 最佳试验 (Trial {best_trial.number}):")
            for param, value in best_trial.params.items():
                logger.info(f"   {param}: {value}")

            logger.info("📋 优化过程:")
            for _i, trial in enumerate(self.study.trials[:10]):  # 显示前10个试验
                if trial.state == optuna.trial.TrialState.COMPLETE:
                    logger.info(f"   Trial {trial.number}: {trial.value:.4f}")
                elif trial.state == optuna.trial.TrialState.PRUNED:
                    logger.info(f"   Trial {trial.number}: Pruned")

            if len(self.study.trials) > 10:
                logger.info(f"   ... 还有 {len(self.study.trials) - 10} 个试验")

        except Exception:
            logger.error(f"❌ 生成报告失败: {e}")


def main():
    """主函数."""
    logger.info("🚀 开始 Optuna XGBoost 超参数优化")

    # 检查依赖
    if not HAS_DEPENDENCIES:
        logger.error(
            "❌ 缺少必要依赖，请安装: pip install optuna xgboost scikit-learn pandas numpy"
        )
        return

    # 创建优化器
    tuner = OptunaHyperparameterTuner(
        n_trials=30,  # 可以根据需要调整
        cv_folds=5,
        random_state=42,
    )

    # 加载数据
    logger.info("📁 第一步: 加载和准备数据")
    if not tuner.load_and_prepare_data():
        logger.error("❌ 数据加载失败，退出程序")
        return

    # 执行优化
    logger.info("🎯 第二步: 执行超参数优化")
    try:
        results = tuner.optimize()

        # 生成报告
        logger.info("📊 第三步: 生成优化报告")
        tuner.generate_report()

        logger.info("🎉 Optuna 超参数优化完成!")
        logger.info(f"📈 最佳准确率: {results['best_score']:.4f}")
        logger.info(f"💾 模型已保存: {tuner.model_save_path}")

        # 与基准模型比较
        baseline_accuracy = 0.5255  # 基准准确率 52.55%
        improvement = (results["best_score"] - baseline_accuracy) * 100
        logger.info(
            f"🚀 准确率提升: {improvement:+.2f}% (从 {baseline_accuracy:.2%} 到 {results['best_score']:.2%})"
        )

    except Exception:
        logger.error(f"❌ 优化过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
