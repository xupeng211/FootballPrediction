#!/usr/bin/env python3
"""
首席AI科学家专用 - V1 XGBoost模型训练器
基于高质量数据训练新一代预测模型
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from datetime import datetime
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class V1XGBoostTrainer:
    """V1 XGBoost训练器"""

    def __init__(self):
        self.data = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []

    def load_dataset(self):
        """加载数据集"""
        try:
            dataset_path = Path("data/training_sets/v1_dataset.csv")
            if not dataset_path.exists():
                logger.error(f"❌ 数据集文件不存在: {dataset_path}")
                return False

            self.data = pd.read_csv(dataset_path)
            logger.info(f"✅ 加载数据集: {self.data.shape}")

            # 显示数据集信息
            logger.info(
                f"📊 比赛时间范围: {self.data['match_date'].min()} 到 {self.data['match_date'].max()}"
            )
            logger.info(f"🎯 目标分布: {self.data['result'].value_counts().to_dict()}")

            return True

        except Exception as e:
            logger.error(f"❌ 加载数据集失败: {e}")
            return False

    def prepare_features(self):
        """准备特征和目标变量"""
        logger.info("🔧 准备特征和目标变量...")

        # 选择特征列
        feature_cols = [
            col for col in self.data.columns if "avg_" in col or "games_" in col
        ]
        self.feature_names = feature_cols

        logger.info(f"🔧 特征列: {feature_cols}")
        logger.info(f"📊 特征数量: {len(feature_cols)}")

        # 准备特征矩阵X和目标变量y
        X = self.data[feature_cols].copy()
        y = self.data["result"].copy()

        # 处理NaN值（用0填充）
        X = X.fillna(0)

        # 显示特征统计
        logger.info("📈 特征统计:")
        for col in feature_cols:
            null_count = X[col].isnull().sum()
            mean_val = X[col].mean()
            std_val = X[col].std()
            logger.info(
                f"   {col}: 均值={mean_val:.3f}, 标准差={std_val:.3f}, NaN={null_count}"
            )

        return X, y

    def time_split_data(self, X, y):
        """按时间切分数据（模拟真实预测场景）"""
        logger.info("📅 按时间切分数据...")

        # 按时间排序
        self.data = self.data.sort_values("match_date")

        # 前80%做训练，后20%做测试
        split_idx = int(len(self.data) * 0.8)
        train_idx = self.data.iloc[:split_idx].index
        test_idx = self.data.iloc[split_idx:].index

        X_train = X.loc[train_idx]
        X_test = X.loc[test_idx]
        y_train = y.loc[train_idx]
        y_test = y.loc[test_idx]

        self.X_train = X_train
        self.X_test = X_test
        self.y_train = y_train
        self.y_test = y_test

        logger.info(f"📊 训练集: {len(X_train)} 场比赛")
        logger.info(f"📊 测试集: {len(X_test)} 场比赛")
        logger.info(
            f"📅 训练时间范围: {self.data.iloc[train_idx]['match_date'].min()} 到 {self.data.iloc[train_idx]['match_date'].max()}"
        )
        logger.info(
            f"📅 测试时间范围: {self.data.iloc[test_idx]['match_date'].min()} 到 {self.data.iloc[test_idx]['match_date'].max()}"
        )

        return True

    def train_model(self):
        """训练XGBoost模型"""
        logger.info("🚀 开始训练XGBoost模型...")

        # 标准化特征
        self.X_train_scaled = self.scaler.fit_transform(self.X_train)
        self.X_test_scaled = self.scaler.transform(self.X_test)

        # 配置XGBoost参数
        params = {
            "objective": "multi:softmax",  # 多分类
            "num_class": 3,  # 3个类别：0=客胜, 1=平局, 2=主胜
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "eval_metric": "mlogloss",
            "early_stopping_rounds": 20,
            "verbosity": 1,
        }

        # 训练模型
        self.model = xgb.XGBClassifier(**params)

        # 使用验证集进行早停
        self.model.fit(
            self.X_train_scaled,
            self.y_train,
            eval_set=[(self.X_test_scaled, self.y_test)],
            verbose=False,
        )

        logger.info("✅ 模型训练完成")
        logger.info(f"🌳 最佳迭代次数: {self.model.best_iteration}")

        return True

    def evaluate_model(self):
        """评估模型性能"""
        logger.info("📊 评估模型性能...")

        # 预测
        y_pred = self.model.predict(self.X_test_scaled)
        y_pred_proba = self.model.predict_proba(self.X_test_scaled)

        # 计算准确率
        accuracy = accuracy_score(self.y_test, y_pred)
        logger.info(f"🎯 准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")

        # 详细分类报告
        logger.info("📋 分类报告:")
        report = classification_report(
            self.y_test, y_pred, target_names=["客胜", "平局", "主胜"], digits=4
        )
        logger.info(report)

        # 混淆矩阵
        cm = confusion_matrix(self.y_test, y_pred)
        logger.info("🔀 混淆矩阵:")
        logger.info(f"   实际\\预测  客胜  平局  主胜")
        for i, row in enumerate(cm):
            logger.info(
                f"   {['客胜','平局','主胜'][i]:6} {row[0]:6} {row[1]:6} {row[2]:6}"
            )

        return accuracy, cm, y_pred_proba

    def analyze_feature_importance(self):
        """分析特征重要性"""
        logger.info("🔍 分析特征重要性...")

        # 获取特征重要性
        importance = self.model.feature_importances_
        feature_importance_df = pd.DataFrame(
            {"feature": self.feature_names, "importance": importance}
        ).sort_values("importance", ascending=False)

        logger.info("📊 特征重要性排名:")
        for idx, row in feature_importance_df.iterrows():
            logger.info(f"   {row['feature']:25} {row['importance']:.4f}")

        # 可视化特征重要性
        try:
            plt.figure(figsize=(10, 6))
            sns.barplot(
                data=feature_importance_df.head(10), x="importance", y="feature"
            )
            plt.title("XGBoost 特征重要性 (Top 10)")
            plt.xlabel("重要性")
            plt.ylabel("特征")
            plt.tight_layout()

            # 保存图片
            plot_path = Path("results/feature_importance_v1.png")
            plot_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(plot_path, dpi=300, bbox_inches="tight")
            logger.info(f"💾 特征重要性图已保存: {plot_path}")

        except Exception as e:
            logger.warning(f"⚠️ 无法保存特征重要性图: {e}")

        return feature_importance_df

    def simulate_betting(self, y_pred_proba):
        """模拟下注ROI"""
        logger.info("💰 模拟下注ROI分析...")

        # 获取预测概率
        predicted_probs = y_pred_proba
        predicted_classes = np.argmax(predicted_probs, axis=1)
        actual_classes = self.y_test.values

        # 模拟投注：每场比赛投1元到概率最高的结果
        total_bet = len(predicted_classes)
        wins = 0
        total_payout = 0

        for i in range(len(predicted_classes)):
            if predicted_classes[i] == actual_classes[i]:
                # 假设公平赔率：1/predicted_probability
                prob = predicted_probs[i][predicted_classes[i]]
                fair_odds = 1.0 / prob if prob > 0 else 1.0

                # 赢得投注
                total_payout += fair_odds
                wins += 1

        # 计算ROI
        total_investment = total_bet  # 每场投1元
        net_profit = total_payout - total_investment
        roi = (net_profit / total_investment) * 100
        hit_rate = (wins / total_bet) * 100

        logger.info("💰 下注模拟结果:")
        logger.info(f"   总投注: {total_bet} 元")
        logger.info(f"   胜场数: {wins} 场")
        logger.info(f"   命中率: {hit_rate:.2f}%")
        logger.info(f"   总赔付: {total_payout:.2f} 元")
        logger.info(f"   净收益: {net_profit:.2f} 元")
        logger.info(f"   ROI: {roi:.2f}%")

        # 按类别分析
        logger.info("📊 按结果类别分析:")
        for result_class, class_name in enumerate(["客胜", "平局", "主胜"]):
            class_mask = actual_classes == result_class
            class_total = class_mask.sum()
            class_wins = (
                predicted_classes[class_mask] == actual_classes[class_mask]
            ).sum()
            class_hit_rate = (class_wins / class_total * 100) if class_total > 0 else 0

            logger.info(
                f"   {class_name}: {class_total} 场, 命中 {class_wins} 场, 命中率 {class_hit_rate:.2f}%"
            )

        return roi, hit_rate

    def save_model(self):
        """保存模型"""
        try:
            model_dir = Path("models")
            model_dir.mkdir(parents=True, exist_ok=True)

            # 保存模型
            model_path = model_dir / "v1_xgboost_model.json"
            self.model.save_model(str(model_path))

            # 保存标准化器
            import joblib

            scaler_path = model_dir / "v1_scaler.pkl"
            joblib.dump(self.scaler, scaler_path)

            # 保存特征名称
            features_path = model_dir / "v1_features.json"
            import json

            with open(features_path, "w") as f:
                json.dump(self.feature_names, f, indent=2)

            logger.info(f"💾 模型已保存: {model_path}")
            logger.info(f"💾 标准化器已保存: {scaler_path}")
            logger.info(f"💾 特征列表已保存: {features_path}")

            return True

        except Exception as e:
            logger.error(f"❌ 保存模型失败: {e}")
            return False

    def run(self):
        """执行完整的训练流程"""
        logger.info("🚀 启动首席AI科学家 - V1 XGBoost训练器")
        start_time = datetime.now()

        # 1. 加载数据集
        if not self.load_dataset():
            return False

        # 2. 准备特征
        X, y = self.prepare_features()

        # 3. 时间切分
        if not self.time_split_data(X, y):
            return False

        # 4. 训练模型
        if not self.train_model():
            return False

        # 5. 评估模型
        accuracy, cm, y_pred_proba = self.evaluate_model()

        # 6. 分析特征重要性
        feature_importance = self.analyze_feature_importance()

        # 7. 模拟下注
        roi, hit_rate = self.simulate_betting(y_pred_proba)

        # 8. 保存模型
        self.save_model()

        # 计算总耗时
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️  总耗时: {duration:.1f}秒")

        # 最终总结
        logger.info("=" * 60)
        logger.info("🎉 V1 XGBoost模型训练完成！")
        logger.info("=" * 60)
        logger.info(f"🎯 准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")
        logger.info(f"💰 ROI: {roi:.2f}%")
        logger.info(f"🔫 命中率: {hit_rate:.2f}%")
        logger.info(f"📊 测试样本: {len(self.y_test)} 场比赛")

        # 与baseline比较
        baseline_accuracy = 0.46  # 之前提到的46%
        improvement = ((accuracy - baseline_accuracy) / baseline_accuracy) * 100
        logger.info(f"📈 相比Baseline提升: {improvement:+.2f}%")

        if accuracy > baseline_accuracy:
            logger.info("🎊 新模型超越了Baseline！")
        else:
            logger.warning("⚠️ 新模型未达到Baseline水平")

        return True


def main():
    """主函数"""
    try:
        trainer = V1XGBoostTrainer()
        success = trainer.run()

        if success:
            logger.info("✅ V1 XGBoost模型训练成功")
            return 0
        else:
            logger.error("❌ V1 XGBoost模型训练失败")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
