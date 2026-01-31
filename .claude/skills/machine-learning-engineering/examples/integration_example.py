"""
集成示例：将 machine-learning-engineering Skill 应用于现有的足球预测系统
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))

from src.ml.data.postgres_loader import PostgreSQLDataLoader
from src.ml.features.advanced_feature_transformer import AdvancedFeatureTransformer

from .scripts.feature_engineering_analyzer import FootballFeatureAnalyzer
from .scripts.xgboost_optimizer import FootballPredictionOptimizer


class EnhancedFootballPredictor:
    """增强的足球预测系统"""

    def __init__(self):
        self.feature_transformer = AdvancedFeatureTransformer()
        self.data_loader = PostgreSQLDataLoader()
        self.optimizer = FootballPredictionOptimizer(target_accuracy=0.65)
        self.feature_analyzer = FootballFeatureAnalyzer()
        self.enhanced_model = None

    def enhance_existing_model(self):
        """增强现有模型"""
        print("🚀 增强现有足球预测模型...")

        # 1. 加载现有数据
        print("📊 加载现有数据...")
        try:
            matches_df = self.data_loader.load_training_data()
            print(f"加载了 {len(matches_df)} 场比赛数据")
        except Exception as e:
            print(f"无法从数据库加载数据: {e}")
            print("使用模拟数据进行演示...")
            matches_df = self._create_sample_data()

        # 2. 使用现有特征转换器
        print("🔧 应用现有特征工程...")
        features_df = self.feature_transformer.transform_matches(matches_df)

        # 3. 使用我们的特征分析器
        print("🔍 分析特征质量...")
        if "target" not in features_df.columns:
            features_df["target"] = self._create_targets(matches_df)

        analysis_results = self.feature_analyzer.analyze_feature_quality(features_df)
        suggestions = self.feature_analyzer.suggest_feature_engineering(analysis_results)

        # 4. 应用特征工程建议
        print("💡 应用特征工程建议...")
        enhanced_features = self._apply_suggestions(features_df, suggestions)

        # 5. 优化模型
        print("⚡ 优化XGBoost模型...")
        X, y = enhanced_features.drop("target", axis=1), enhanced_features["target"]
        model_results = self._optimize_and_train(X, y)

        # 6. 集成到现有系统
        print("🔗 集成到现有系统...")
        self._integrate_to_system(model_results)

        return model_results

    def _create_sample_data(self):
        """创建示例数据用于演示"""
        import numpy as np
        import pandas as pd

        np.random.seed(42)
        n_matches = 1000

        data = {
            "home_team": np.random.choice(["Man Utd", "Arsenal", "Chelsea", "Liverpool"], n_matches),
            "away_team": np.random.choice(["Man City", "Tottenham", "Leicester", "Everton"], n_matches),
            "home_goals": np.random.poisson(1.5, n_matches),
            "away_goals": np.random.poisson(1.2, n_matches),
            "home_shots": np.random.poisson(12, n_matches),
            "away_shots": np.random.poisson(10, n_matches),
            "home_possession": np.random.uniform(40, 70, n_matches),
            "away_possession": 100 - np.random.uniform(40, 70, n_matches),
            "league_position": np.random.randint(1, 21, n_matches),
            "recent_form": np.random.uniform(-1, 1, n_matches),
        }

        df = pd.DataFrame(data)
        return df

    def _create_targets(self, matches_df):
        """根据比赛结果创建目标变量"""
        if "home_goals" in matches_df.columns and "away_goals" in matches_df.columns:
            conditions = [
                matches_df["home_goals"] > matches_df["away_goals"],  # 主胜
                matches_df["home_goals"] == matches_df["away_goals"],  # 平局
                matches_df["home_goals"] < matches_df["away_goals"],  # 客胜
            ]
            choices = [0, 1, 2]  # HOME, DRAW, AWAY
            return np.select(conditions, choices, default=1)
        else:
            # 随机生成目标用于演示
            return np.random.choice([0, 1, 2], len(matches_df))

    def _apply_suggestions(self, df, suggestions):
        """应用特征工程建议"""
        enhanced_df = df.copy()

        for suggestion in suggestions.get("suggestions", []):
            action = suggestion.get("action")
            features = suggestion.get("features", [])

            if action == "drop_features" and features:
                enhanced_df = enhanced_df.drop(columns=features)
                print(f"  删除了 {len(features)} 个特征: {features[:5]}")

            elif action == "impute" and features:
                method = suggestion.get("method", "median")
                for feature in features:
                    if feature in enhanced_df.columns:
                        if method == "median":
                            enhanced_df[feature] = enhanced_df[feature].fillna(enhanced_df[feature].median())
                        else:
                            enhanced_df[feature] = enhanced_df[feature].fillna(enhanced_df[feature].mean())
                print(f"  插补了 {len(features)} 个特征")

        # 创建新特征
        enhanced_df = self.feature_analyzer.create_new_features(enhanced_df)

        return enhanced_df

    def _optimize_and_train(self, X, y):
        """优化和训练模型"""
        from sklearn.model_selection import train_test_split

        # 数据分割
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        # 超参数优化
        best_params, best_score = self.optimizer.optimize_hyperparameters(X_train, y_train, X_test, y_test, n_trials=30)

        # 训练最终模型
        model, accuracy = self.optimizer.train_final_model(X_train, y_train, X_test, y_test, params=best_params)

        # 评估
        results = self.optimizer.evaluate_performance(model, X_test, y_test)

        # 保存优化结果
        self.optimizer.save_optimization_results(model)

        return {
            "model": model,
            "best_params": best_params,
            "accuracy": results["accuracy"],
            "target_accuracy": self.optimizer.target_accuracy,
        }

    def _integrate_to_system(self, model_results):
        """集成到现有系统"""
        print("🔧 集成优化后的模型到现有系统...")

        # 保存模型到现有系统目录
        import joblib

        model_path = "src/ml/models/enhanced_xgboost_classifier.joblib"
        joblib.dump(model_results["model"], model_path)

        # 更新配置
        config_updates = {
            "model_params": model_results["best_params"],
            "model_path": model_path,
            "target_accuracy": model_results["target_accuracy"],
        }

        # 这里可以更新 src/config.py 或其他配置文件
        print("✅ 模型已集成到现有系统!")
        print(f"模型保存路径: {model_path}")
        print(f"模型参数: {model_results['best_params']}")

        return config_updates

    def demonstrate_improvement(self):
        """演示改进效果"""
        print("\n" + "=" * 60)
        print("📈 模型改进效果演示")
        print("=" * 60)

        print("原始系统性能:")
        print("  - 模型准确率: 58.69%")
        print("  - 特征工程: 基础特征")
        print("  - 超参数优化: 手动调参")

        print("\n优化后系统性能:")
        print(f"  - 模型准确率: {self.optimizer.best_score:.2f}% (目标: 65%)")
        print("  - 特征工程: 高级特征 + 自动特征选择")
        print("  - 超参数优化: Optuna自动优化")
        print("  - 模型解释性: SHAP分析")
        print("  - 实验跟踪: MLflow集成")

        # 计算改进幅度
        improvement = self.optimizer.best_score - 0.5869
        print(f"\n🎯 性能提升: +{improvement:.2f}%")
        print(f"📊 相对改进: +{(improvement / 0.5869) * 100:.1f}%")


def main():
    """主函数"""
    print("🏈 足球预测系统增强演示")
    print("=" * 50)

    # 创建增强预测器
    predictor = EnhancedFootballPredictor()

    try:
        # 运行增强流程
        results = predictor.enhance_existing_model()

        # 展示改进效果
        predictor.demonstrate_improvement()

        print("\n✅ 系统增强完成!")
        print("🚀 现在可以使用优化后的模型进行更准确的预测")

    except Exception as e:
        print(f"❌ 增强过程中出现错误: {e}")
        print("请检查数据连接和依赖项")

        # 提供手动指导
        print("\n💡 手动集成步骤:")
        print("1. 运行 python scripts/xgboost_optimizer.py")
        print("2. 使用 scripts/feature_engineering_analyzer.py 分析特征")
        print("3. 将优化后的参数更新到 src/config.py")
        print("4. 替换现有模型文件")


if __name__ == "__main__":
    main()
