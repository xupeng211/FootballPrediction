#!/usr/bin/env python3
"""
生产模型序列化脚本
保存Phase 2最终模型工件为Phase 3推理API做准备

功能:
1. 训练最终基线模型
2. 保存XGBoost模型为JSON格式
3. 保存LabelEncoder用于预测解码
4. 保存特征列表确保输入顺序一致

作者: Chief Architect
创建时间: 2025-12-10
版本: 1.0.0 - Production Model v1
"""

import json
import pickle
from datetime import datetime
import logging
from pathlib import Path

# 导入基线训练器
import sys

sys.path.append(str(Path(__file__).parent))
from train_baseline import BaselineTrainer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionModelSaver(BaselineTrainer):
    """生产模型保存器"""

    def __init__(self):
        super().__init__()
        self.model_version = "v1.0.0"
        self.model_name = "football_xgboost_baseline"

    def train_production_model(self, data_path: str) -> dict:
        """训练生产模型"""
        logger.info(f"🏭 开始训练生产模型 {self.model_name} {self.model_version}")

        # 加载和准备数据
        df = self.load_and_prepare_data(data_path)

        # 选择特征
        X, y, feature_columns = self.select_features(df)

        # 时序分割
        X_train, X_test, y_train_enc, y_test_enc, y_train_orig, y_test_orig = (
            self.split_data_chronological(X, y)
        )

        # 保存特征列表
        self.feature_columns = feature_columns

        # 训练模型
        self.train_xgboost(X_train, y_train_enc)

        # 评估模型
        results = self.evaluate_model(X_test, y_test_enc, y_test_orig)

        # 保存模型工件
        self.save_model_artifacts(results)

        logger.info("🎉 生产模型训练完成!")
        return results

    def save_model_artifacts(self, results: dict):
        """保存所有模型工件"""
        logger.info("💾 保存生产模型工件...")

        # 创建models目录
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)

        # 1. 保存XGBoost模型 (JSON格式 - 生产推荐)
        model_json_path = models_dir / f"{self.model_name}.json"
        self.model.save_model(str(model_json_path))
        logger.info(f"   ✅ XGBoost模型已保存: {model_json_path}")

        # 2. 保存XGBoost模型 (pickle格式 - 备份)
        model_pkl_path = models_dir / f"{self.model_name}.pkl"
        with open(model_pkl_path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"   ✅ XGBoost模型备份已保存: {model_pkl_path}")

        # 3. 保存LabelEncoder
        encoder_path = models_dir / f"{self.model_name}_label_encoder.pkl"
        with open(encoder_path, "wb") as f:
            pickle.dump(self.label_encoder, f)
        logger.info(f"   ✅ LabelEncoder已保存: {encoder_path}")

        # 4. 保存特征列表
        features_path = models_dir / f"{self.model_name}_features.json"
        features_data = {
            "feature_columns": self.feature_columns,
            "feature_count": len(self.feature_columns),
            "model_version": self.model_version,
        }
        with open(features_path, "w") as f:
            json.dump(features_data, f, indent=2)
        logger.info(f"   ✅ 特征列表已保存: {features_path}")

        # 5. 保存模型元数据
        metadata = {
            "model_name": self.model_name,
            "version": self.model_version,
            "training_date": datetime.now().isoformat(),
            "performance": {
                "accuracy": results["accuracy"],
                "log_loss": results["log_loss"],
                "classification_report": results["classification_report"],
            },
            "model_params": {
                "n_estimators": self.model.n_estimators,
                "max_depth": self.model.max_depth,
                "learning_rate": self.model.learning_rate,
                "objective": self.model.objective,
                "eval_metric": self.model.eval_metric,
            },
            "dataset_info": {
                "training_samples": len(self.feature_columns),
                "feature_count": len(self.feature_columns),
                "target_classes": list(self.label_encoder.classes_),
            },
            "data_leakage_safe": True,
            "feature_engineering": "rolling_features_time_series_safe",
        }

        metadata_path = models_dir / f"{self.model_name}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"   ✅ 模型元数据已保存: {metadata_path}")

        # 6. 保存部署配置
        deployment_config = {
            "model_files": {
                "model_json": str(model_json_path.name),
                "model_pkl": str(model_pkl_path.name),
                "label_encoder": str(encoder_path.name),
                "features": str(features_path.name),
                "metadata": str(metadata_path.name),
            },
            "input_schema": {
                "type": "DataFrame",
                "features_required": self.feature_columns,
                "feature_order": "must_match_features_json",
            },
            "output_schema": {
                "prediction": "encoded_class",
                "prediction_label": "H/D/A",
                "probabilities": "dict_class_to_probability",
            },
            "inference": {
                "preprocessing_steps": [
                    "ensure_feature_order",
                    "fill_missing_values_0",
                    "encode_prediction",
                ]
            },
        }

        config_path = models_dir / f"{self.model_name}_deployment_config.json"
        with open(config_path, "w") as f:
            json.dump(deployment_config, f, indent=2)
        logger.info(f"   ✅ 部署配置已保存: {config_path}")

    def print_production_summary(self, results: dict):
        """打印生产模型摘要"""
        print("\n" + "=" * 80)
        print("🏆 PRODUCTION MODEL SUMMARY")
        print("=" * 80)

        print("\n📋 模型信息:")
        print(f"   名称: {self.model_name}")
        print(f"   版本: {self.model_version}")
        print(f"   训练时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n📊 性能指标:")
        print(f"   🎯 准确率: {results['accuracy']:.4f}")
        print(f"   📉 Log Loss: {results['log_loss']:.4f}")

        print("\n🔧 模型配置:")
        print("   算法: XGBoost Classifier")
        print(f"   树数量: {self.model.n_estimators}")
        print(f"   最大深度: {self.model.max_depth}")
        print(f"   学习率: {self.model.learning_rate}")

        print("\n📁 已保存文件:")
        models_dir = Path("models")
        for file_path in models_dir.glob(f"{self.model_name}*"):
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"   📄 {file_path.name} ({size_mb:.2f} MB)")

        print("\n🚀 Phase 2 完成状态:")
        print("   ✅ 数据泄露修复完成")
        print("   ✅ 滚动特征工程完成")
        print("   ✅ 时序安全模型训练完成")
        print("   ✅ 模型工件序列化完成")
        print("   ✅ 准备就绪: Phase 3 推理API")

        print("=" * 80)


def main():
    """主函数"""
    print("🏭 生产模型序列化开始")
    print("Phase 2: Feature Engineering → Production Model")
    print("=" * 60)

    # 初始化生产模型保存器
    saver = ProductionModelSaver()

    try:
        # 训练并保存生产模型
        results = saver.train_production_model(
            data_path="data/processed/features_v2_rolling.csv"
        )

        # 打印摘要
        saver.print_production_summary(results)

    except Exception as e:
        logger.error(f"❌ 生产模型保存失败: {e}")
        raise


if __name__ == "__main__":
    main()
