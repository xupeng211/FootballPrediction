"""
足球赛果预测模型训练流水线模板
使用 machine-learning-engineering Skill 的最佳实践
"""

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .feature_engineering_analyzer import FootballFeatureAnalyzer

# 导入我们的优化器
from .xgboost_optimizer import FootballPredictionOptimizer


class FootballModelPipeline:
    """足球预测模型训练流水线"""

    def __init__(self, target_accuracy=0.65, target_latency_ms=100.0):
        self.target_accuracy = target_accuracy
        self.target_latency_ms = target_latency_ms
        self.optimizer = FootballPredictionOptimizer(target_accuracy, target_latency_ms)
        self.feature_analyzer = FootballFeatureAnalyzer()
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()

    def load_data(self, file_path: str):
        """加载和预处理数据"""
        print("📊 加载数据...")
        df = pd.read_csv(file_path)
        print(f"数据形状: {df.shape}")
        return df

    def preprocess_data(self, df: pd.DataFrame, target_col: str = "target"):
        """数据预处理"""
        print("\n🔧 数据预处理...")

        # 分离特征和目标
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found")

        X = df.drop(columns=[target_col])
        y = df[target_col]

        # 处理分类特征
        categorical_cols = X.select_dtypes(include=["object", "category"]).columns
        for col in categorical_cols:
            X[col] = pd.get_dummies(X[col], prefix=col)

        # 标签编码
        if y.dtype == "object":
            y = self.label_encoder.fit_transform(y)

        # 移除缺失值
        X = X.fillna(X.median())

        print(f"预处理后特征数: {X.shape[1]}")
        print(f"类别分布: {np.bincount(y)}")

        return X, y

    def split_data(self, X, y, test_size=0.2, val_size=0.15):
        """数据分割"""
        print("\n✂️  数据分割...")

        # 首先分离测试集
        X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=test_size, random_state=42, stratify=y)

        # 再分离训练和验证集
        val_size_adjusted = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_size_adjusted, random_state=42, stratify=y_temp
        )

        print(f"训练集: {X_train.shape}")
        print(f"验证集: {X_val.shape}")
        print(f"测试集: {X_test.shape}")

        return X_train, X_val, X_test, y_train, y_val, y_test

    def feature_engineering(self, X_train, X_val, X_test, y_train):
        """特征工程和选择"""
        print("\n🎯 特征工程...")

        # 特征分析
        train_df = pd.concat([X_train, pd.Series(y_train, name="target")], axis=1)
        analysis_results = self.feature_analyzer.analyze_feature_quality(train_df)

        # 获取特征工程建议
        suggestions = self.feature_analyzer.suggest_feature_engineering(analysis_results)

        # 创建新特征
        X_train_enhanced = self.feature_analyzer.create_new_features(X_train)
        X_val_enhanced = self.feature_analyzer.create_new_features(X_val)
        X_test_enhanced = self.feature_analyzer.create_new_features(X_test)

        # 特征选择
        X_train_selected, selected_features = self.feature_analyzer.optimize_features(
            X_train_enhanced, y_train, method="mutual_info", k=20
        )

        X_val_selected = X_val_enhanced[selected_features]
        X_test_selected = X_test_enhanced[selected_features]

        # 特征缩放
        X_train_scaled = self.scaler.fit_transform(X_train_selected)
        X_val_scaled = self.scaler.transform(X_val_selected)
        X_test_scaled = self.scaler.transform(X_test_selected)

        print(f"最终特征数: {X_train_scaled.shape[1]}")

        return (
            pd.DataFrame(X_train_scaled, columns=selected_features),
            pd.DataFrame(X_val_scaled, columns=selected_features),
            pd.DataFrame(X_test_scaled, columns=selected_features),
        )

    def train_model(self, X_train, y_train, X_val, y_val, optimize_hyperparams=True):
        """训练模型"""
        print("\n🚀 模型训练...")

        with mlflow.start_run() as run:
            # 超参数优化
            if optimize_hyperparams:
                print("🎛️  超参数优化中...")
                best_params, best_score = self.optimizer.optimize_hyperparameters(
                    X_train, y_train, X_val, y_val, n_trials=50
                )
            else:
                best_params = None
                best_score = 0

            # 训练最终模型
            model, val_accuracy = self.optimizer.train_final_model(X_train, y_train, X_val, y_val, params=best_params)

            # 记录到MLflow
            mlflow.log_params(best_params or {})
            mlflow.log_metric("val_accuracy", val_accuracy)
            mlflow.log_metric("target_accuracy", self.target_accuracy)
            mlflow.log_metric("gap_to_target", self.target_accuracy - val_accuracy)

            print("✅ 模型训练完成!")
            print(f"验证集准确率: {val_accuracy:.4f}")
            print(f"目标准确率: {self.target_accuracy:.4f}")

            return model, val_accuracy

    def evaluate_model(self, model, X_test, y_test):
        """评估模型"""
        print("\n📈 模型评估...")

        # 性能评估
        results = self.optimizer.evaluate_performance(model, X_test, y_test)

        # 延迟测试
        latency = self.optimizer.check_inference_latency(model, X_test)

        # 保存结果
        results["inference_latency_ms"] = latency
        results["target_latency_ms"] = self.target_latency_ms
        results["meets_latency_target"] = latency <= self.target_latency_ms

        return results

    def save_pipeline(self, model, results_dir="football_model_results"):
        """保存整个流水线"""
        print(f"\n💾 保存流水线到 {results_dir}...")

        import os

        os.makedirs(results_dir, exist_ok=True)

        # 保存模型和组件
        import joblib

        joblib.dump(model, f"{results_dir}/model.joblib")
        joblib.dump(self.scaler, f"{results_dir}/scaler.joblib")
        joblib.dump(self.label_encoder, f"{results_dir}/label_encoder.joblib")

        # 保存优化器结果
        self.optimizer.save_optimization_results(model, results_dir)

        # 保存特征列表
        if hasattr(self.feature_analyzer, "selected_features"):
            with open(f"{results_dir}/selected_features.json", "w") as f:
                import json

                json.dump(self.feature_analyzer.selected_features, f, indent=2)

        print("✅ 流水线保存完成!")

    def run_full_pipeline(self, data_path: str, target_col: str = "target"):
        """运行完整流水线"""
        print("🏈 足球赛果预测模型训练流水线")
        print("=" * 50)

        try:
            # 1. 加载数据
            df = self.load_data(data_path)

            # 2. 预处理
            X, y = self.preprocess_data(df, target_col)

            # 3. 数据分割
            X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X, y)

            # 4. 特征工程
            X_train_final, X_val_final, X_test_final = self.feature_engineering(X_train, X_val, X_test, y_train)

            # 5. 模型训练
            model, val_accuracy = self.train_model(X_train_final, y_train, X_val_final, y_val)

            # 6. 模型评估
            results = self.evaluate_model(model, X_test_final, y_test)

            # 7. 保存流水线
            self.save_pipeline(model)

            # 8. 总结报告
            self.print_summary_report(results)

            return model, results

        except Exception as e:
            print(f"❌ 流水线执行失败: {str(e)}")
            raise

    def print_summary_report(self, results):
        """打印总结报告"""
        print("\n" + "=" * 50)
        print("📊 模型训练总结报告")
        print("=" * 50)

        print(f"✅ 测试准确率: {results['accuracy']:.4f}")
        print(f"🎯 目标准确率: {self.target_accuracy:.4f}")
        print(f"📈 达到目标: {'✅' if results['accuracy'] >= self.target_accuracy else '❌'}")

        print(f"\n⚡ 推理延迟: {results['inference_latency_ms']:.2f} ms")
        print(f"🎯 目标延迟: {self.target_latency_ms:.2f} ms")
        print(f"📈 达到目标: {'✅' if results['meets_latency_target'] else '❌'}")

        # 如果使用MLflow，显示run信息
        try:
            print(f"\n🔗 MLflow Run ID: {mlflow.active_run().info.run_id}")
        except:
            pass


# 使用示例
if __name__ == "__main__":
    # 创建流水线
    pipeline = FootballModelPipeline(target_accuracy=0.65, target_latency_ms=100.0)

    # 运行完整流水线
    # model, results = pipeline.run_full_pipeline('data/football_matches.csv', target_col='result')

    print("流水线模板已就绪!")
    print("请调用 pipeline.run_full_pipeline('你的数据文件路径') 开始训练")
