#!/usr/bin/env python3
"""
XGBoost高级模型训练脚本 - V3版本
Chief Data Scientist: 基于EWMA特征训练高性能预测模型

核心功能:
- 加载高级特征数据集
- 训练多目标XGBoost模型
- 特征重要性分析
- 模型性能评估
"""

import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("⚠️ matplotlib不可用，跳过可视化生成")

try:
    import seaborn as sns

    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
from datetime import datetime
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class AdvancedXGBoostTrainer:
    """高级XGBoost模型训练器"""

    def __init__(self):
        self.models = {}
        self.feature_importance = {}
        self.label_encoders = {}
        self.evaluation_results = {}

        # 创建输出目录
        os.makedirs("/app/models", exist_ok=True)
        os.makedirs("/app/results", exist_ok=True)

        logger.info("🧠 高级XGBoost训练器初始化完成")

    def load_features_data(
        self, file_path: str = "/app/data/advanced_features.csv"
    ) -> pd.DataFrame:
        """加载特征数据"""
        logger.info(f"📊 加载特征数据: {file_path}")

        df = pd.read_csv(file_path)
        logger.info(f"✅ 数据加载完成: {df.shape}")
        logger.info(f"   特征列: {list(df.columns)}")

        return df

    def prepare_features_and_targets(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
        """准备特征和目标变量"""
        logger.info("⚙️ 准备特征和目标变量...")

        # 识别特征列和目标列
        exclude_cols = [
            "match_id",
            "match_date",
            "result",
            "home_score",
            "away_score",
            "goal_difference",
            "total_goals",
            "over_2_5_goals",
            "both_teams_score",
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        # 处理缺失值 - 填充season列
        df_clean = df.copy()
        if "season" in df_clean.columns:
            df_clean["season"] = df_clean["season"].fillna("2024")

        # 确保所有特征列都是数值型
        X = df_clean[feature_cols].select_dtypes(include=[np.number])

        # 定义目标变量
        targets = {
            "match_result": df_clean["result"],  # 比赛结果分类
            "home_score": df_clean["home_score"],  # 主队进球数
            "away_score": df_clean["away_score"],  # 客队进球数
            "goal_difference": df_clean["goal_difference"],  # 进球差
            "total_goals": df_clean["total_goals"],  # 总进球数
            "over_2_5_goals": df_clean["over_2_5_goals"],  # 大小球
            "both_teams_score": df_clean["both_teams_score"],  # 双方进球
        }

        logger.info(f"✅ 特征准备完成: {X.shape}")
        logger.info(f"   特征数量: {len(feature_cols)}")
        logger.info(f"   目标变量: {list(targets.keys())}")

        return X, targets

    def train_classification_model(
        self, X: pd.DataFrame, y: pd.Series, target_name: str
    ) -> xgb.XGBClassifier:
        """训练分类模型"""
        logger.info(f"🎯 训练分类模型: {target_name}")

        # 编码目标变量
        if y.dtype == "object":
            le = LabelEncoder()
            y_encoded = le.fit_transform(y)
            self.label_encoders[target_name] = le
        else:
            y_encoded = y

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )

        # XGBoost参数
        params = {
            "objective": (
                "multi:softprob" if len(np.unique(y_encoded)) > 2 else "binary:logistic"
            ),
            "num_class": (
                len(np.unique(y_encoded)) if len(np.unique(y_encoded)) > 2 else None
            ),
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "eval_metric": "mlogloss" if len(np.unique(y_encoded)) > 2 else "logloss",
        }

        # 训练模型
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)

        # 评估模型
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        # 交叉验证
        cv_scores = cross_val_score(model, X, y_encoded, cv=5, scoring="accuracy")

        logger.info(f"   测试集准确率: {accuracy:.4f}")
        logger.info(
            f"   交叉验证准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}"
        )

        # 保存评估结果
        self.evaluation_results[target_name] = {
            "test_accuracy": float(accuracy),
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "model_type": "classification",
            "feature_names": list(X.columns),
        }

        return model

    def train_regression_model(
        self, X: pd.DataFrame, y: pd.Series, target_name: str
    ) -> xgb.XGBRegressor:
        """训练回归模型"""
        logger.info(f"🎯 训练回归模型: {target_name}")

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # XGBoost参数
        params = {
            "objective": "reg:squarederror",
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
        }

        # 训练模型
        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train)

        # 评估模型
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        # 交叉验证
        cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")

        logger.info(f"   MSE: {mse:.4f}")
        logger.info(f"   MAE: {mae:.4f}")
        logger.info(f"   R²: {r2:.4f}")
        logger.info(f"   交叉验证R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        # 保存评估结果
        self.evaluation_results[target_name] = {
            "mse": float(mse),
            "mae": float(mae),
            "r2": float(r2),
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "model_type": "regression",
            "feature_names": list(X.columns),
        }

        return model

    def extract_feature_importance(
        self, model, target_name: str, feature_names: list[str]
    ):
        """提取特征重要性"""
        if hasattr(model, "feature_importances_"):
            importance = model.feature_importances_
            # 转换numpy类型为Python原生类型
            feature_importance = {
                feature: float(score)
                for feature, score in zip(feature_names, importance, strict=False)
            }

            # 按重要性排序
            sorted_importance = sorted(
                feature_importance.items(), key=lambda x: x[1], reverse=True
            )
            self.feature_importance[target_name] = sorted_importance

            logger.info(f"📊 {target_name} Top 10 重要特征:")
            for i, (feature, score) in enumerate(sorted_importance[:10]):
                logger.info(f"   {i + 1:2d}. {feature:30s}: {score:.4f}")

    def save_models(self):
        """保存训练好的模型"""
        logger.info("💾 保存训练模型...")

        import joblib

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for target_name, model in self.models.items():
            model_path = f"/app/models/xgboost_{target_name}_{timestamp}.pkl"
            joblib.dump(model, model_path)
            logger.info(f"   模型已保存: {model_path}")

        # 保存标签编码器
        if self.label_encoders:
            encoder_path = f"/app/models/label_encoders_{timestamp}.pkl"
            joblib.dump(self.label_encoders, encoder_path)
            logger.info(f"   标签编码器已保存: {encoder_path}")

    def save_results(self):
        """保存分析结果"""
        logger.info("📋 保存分析结果...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存评估结果
        results_path = f"/app/results/model_evaluation_{timestamp}.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(self.evaluation_results, f, indent=2, ensure_ascii=False)
        logger.info(f"   评估结果已保存: {results_path}")

        # 保存特征重要性
        importance_path = f"/app/results/feature_importance_{timestamp}.json"
        with open(importance_path, "w", encoding="utf-8") as f:
            json.dump(self.feature_importance, f, indent=2, ensure_ascii=False)
        logger.info(f"   特征重要性已保存: {importance_path}")

    def generate_feature_importance_visualization(self):
        """生成特征重要性可视化"""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("⚠️ matplotlib不可用，跳过可视化生成")
            return

        logger.info("📈 生成特征重要性可视化...")

        try:
            # 为主要目标变量生成图表
            main_targets = ["match_result", "total_goals", "over_2_5_goals"]

            for target_name in main_targets:
                if target_name in self.feature_importance:
                    importance_data = self.feature_importance[target_name]

                    # 取前20个重要特征
                    top_features = importance_data[:20]
                    features, scores = zip(*top_features, strict=False)

                    # 创建图表
                    plt.figure(figsize=(12, 8))
                    plt.barh(range(len(features)), scores)
                    plt.yticks(range(len(features)), features)
                    plt.xlabel("特征重要性")
                    plt.title(f"{target_name} - Top 20 特征重要性")
                    plt.gca().invert_yaxis()

                    # 保存图表
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    chart_path = (
                        f"/app/results/feature_importance_{target_name}_{timestamp}.png"
                    )
                    plt.tight_layout()
                    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
                    plt.close()

                    logger.info(f"   {target_name} 特征重要性图表已保存: {chart_path}")

        except Exception:
            logger.warning(f"⚠️ 生成特征重要性图表时出错: {e}")

    def print_summary_report(self):
        """打印模型训练总结报告"""
        print(f"\n{'=' * 80}")
        print("🎯 XGBoost模型训练总结报告")
        print(f"{'=' * 80}")

        print("\n📊 模型性能总览:")
        for target_name, results in self.evaluation_results.items():
            print(f"\n   🔸 {target_name}:")
            if results["model_type"] == "classification":
                print(f"      测试集准确率: {results['test_accuracy']:.4f}")
                print(
                    f"      交叉验证准确率: {results['cv_mean']:.4f} ± {results['cv_std']:.4f}"
                )
            else:
                print(f"      R²: {results['r2']:.4f}")
                print(f"      MSE: {results['mse']:.4f}")
                print(f"      MAE: {results['mae']:.4f}")
                print(
                    f"      交叉验证R²: {results['cv_mean']:.4f} ± {results['cv_std']:.4f}"
                )

        # EWMA特征重要性分析
        print("\n🧠 EWMA特征重要性分析:")
        ewma_features = [
            f
            for f in self.feature_importance.get("match_result", [])
            if "ewma" in f[0] or "rating" in f[0]
        ]

        if ewma_features:
            print("   Top EWMA特征 (match_result):")
            for i, (feature, score) in enumerate(ewma_features[:10]):
                print(f"      {i + 1:2d}. {feature:30s}: {score:.4f}")
        else:
            print("   未找到EWMA特征在Top特征中")

        # 基础特征对比
        print("\n📈 基础特征vs高级特征对比:")
        basic_features = [
            f
            for f in self.feature_importance.get("match_result", [])
            if f[0] in ["home_team_id", "away_team_id", "league_id"]
        ]

        if basic_features:
            print("   基础特征排名:")
            for feature, score in basic_features:
                rank = next(
                    i
                    for i, (f, s) in enumerate(
                        self.feature_importance["match_result"], 1
                    )
                    if f == feature
                )
                print(f"      {feature:15s}: 排名第{rank}位 (重要性: {score:.4f})")
        else:
            print("   基础特征未进入Top重要特征")

        print("\n🏆 模型保存位置:")
        print("   模型文件: /app/models/xgboost_*.pkl")
        print("   评估结果: /app/results/model_evaluation_*.json")
        print("   特征重要性: /app/results/feature_importance_*.json")

        print(f"\n{'=' * 80}")

    def execute_training_pipeline(self):
        """执行完整训练流程"""
        logger.info("🚀 启动高级XGBoost训练流程...")

        try:
            # 1. 加载数据
            df = self.load_features_data()

            if len(df) == 0:
                logger.error("❌ 没有可用的训练数据")
                return False

            # 2. 准备特征和目标
            X, targets = self.prepare_features_and_targets(df)

            # 3. 训练各个模型
            target_configs = {
                "match_result": "classification",
                "total_goals": "regression",
                "over_2_5_goals": "classification",
                "both_teams_score": "classification",
                "home_score": "regression",
                "away_score": "regression",
            }

            for target_name, model_type in target_configs.items():
                if target_name in targets:
                    logger.info(f"\n🎯 开始训练 {target_name} ({model_type})")

                    y = targets[target_name]

                    if model_type == "classification":
                        model = self.train_classification_model(X, y, target_name)
                    else:
                        model = self.train_regression_model(X, y, target_name)

                    self.models[target_name] = model

                    # 提取特征重要性
                    self.extract_feature_importance(model, target_name, list(X.columns))

            # 4. 保存模型和结果
            self.save_models()
            self.save_results()
            self.generate_feature_importance_visualization()

            # 5. 打印总结报告
            self.print_summary_report()

            return True

        except Exception:
            logger.error(f"💥 训练流程异常: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """主函数"""
    print("🚀 XGBoost高级模型训练器 - V3版本")
    print("🎯 目标: 基于EWMA特征训练高性能预测模型")
    print("🧠 架构: 多目标预测 + 特征重要性分析")
    print("=" * 80)

    trainer = AdvancedXGBoostTrainer()

    try:
        success = trainer.execute_training_pipeline()

        if success:
            print("\n🎉 XGBoost模型训练成功完成!")
            print("📁 输出文件:")
            print("   /app/models/ - 训练好的模型文件")
            print("   /app/results/ - 评估结果和特征重要性分析")
            print("🔥 关键验证点: EWMA特征应排名高于基础特征")
        else:
            print("\n❌ XGBoost模型训练失败")

    except Exception:
        logger.error(f"💥 系统异常: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
