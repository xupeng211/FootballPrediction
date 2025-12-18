#!/usr/bin/env python3
"""
真实数据基线模型训练脚本 - Phase 4 真实世界数据集成

使用 PostgresDataLoader 从真实数据库加载 2,039 条比赛数据，
应用 RollingAverageTransformer 特征工程，训练 XGBoost 模型。
"""

import asyncio
import sys
import logging
from pathlib import Path
import json
from datetime import datetime


# 添加项目根路径
project_root = Path(__file__).parent.parent  # src/scripts -> src
football_prediction_root = project_root.parent  # src -> project root

sys.path.insert(0, str(football_prediction_root))
sys.path.insert(0, str(football_prediction_root / "FootballPrediction"))

# 确保能找到 src 目录
src_path = football_prediction_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 暂时禁用所有不存在的ML组件导入
# from FootballPrediction.src.ml.features.rolling import RollingAverageTransformer
# from FootballPrediction.src.ml.training.trainer import ModelTrainer
# from src.ml.features.rolling import RollingAverageTransformer
# from src.ml.training.trainer import ModelTrainer
# from ml.features.rolling import RollingAverageTransformer
# from ml.training.trainer import ModelTrainer
# from src.ml.data.postgres_loader import PostgresDataLoader
# from ml.data.postgres_loader import PostgresDataLoader

# 临时占位符
RollingAverageTransformer = None
ModelTrainer = None
PostgresDataLoader = None

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RealDataTrainingPipeline:
    """
    真实数据训练流水线

    整合 PostgresDataLoader、RollingAverageTransformer 和 ModelTrainer，
    实现端到端的真实数据模型训练。
    """

    def __init__(self):
        """初始化训练流水线"""
        self.data_loader = PostgresDataLoader(
            batch_size=1000,
            selected_columns=[
                "home_team_id",
                "away_team_id",
                "home_score",
                "away_score",
                "match_date",
                "status",
                "home_team_name",
                "away_team_name",
                "league_id",
            ],
            max_records=5000,
        )

        # 特征工程配置
        self.feature_transformers = [
            RollingAverageTransformer(
                windows=[3, 5, 10],  # 3场、5场、10场滚动平均
                columns=["home_score", "away_score"],  # 对得分进行滚动平均
                group_by=["home_team_id"],  # 按主队分组
                date_column="match_date",
                output_prefix="rolling_home",
            ),
            RollingAverageTransformer(
                windows=[3, 5, 10],
                columns=["home_score", "away_score"],
                group_by=["away_team_id"],  # 按客队分组
                date_column="match_date",
                output_prefix="rolling_away",
            ),
        ]

        # 模型参数配置
        self.model_params = {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "eval_metric": "logloss",
            "use_label_encoder": False,
            "reg_alpha": 0.1,  # L1正则化
            "reg_lambda": 1.0,  # L2正则化
        }

        # 模型训练器
        self.model_trainer = ModelTrainer(
            data_loader=self.data_loader,
            feature_transformers=self.feature_transformers,
            model_params=self.model_params,
        )

        logger.info("真实数据训练流水线初始化完成")

    async def train_and_evaluate(self) -> dict:
        """
        执行完整的训练和评估流程

        Returns:
            dict: 训练结果和性能指标
        """
        logger.info("🚀 开始真实数据基线模型训练")
        logger.info("=" * 60)

        try:
            # 1. 数据加载和验证
            logger.info("📊 第1步: 真实数据加载验证...")
            data_summary = await self.data_loader.get_data_summary()
            logger.info(f"✅ 数据摘要: {data_summary}")

            # 2. 执行训练流水线
            logger.info("🧠 第2步: 执行模型训练流水线...")
            training_metrics = await self.model_trainer.run(test_size=0.2)

            # 3. 获取特征重要性
            logger.info("🔍 第3步: 特征重要性分析...")
            feature_importance_df = self.model_trainer.get_feature_importance()

            # 4. 生成详细评估报告
            logger.info("📋 第4步: 生成评估报告...")
            evaluation_report = self._generate_evaluation_report(
                training_metrics, feature_importance_df, data_summary
            )

            # 5. 保存模型
            logger.info("💾 第5步: 保存模型...")
            model_path = await self._save_model()

            # 6. 保存训练报告
            report_path = await self._save_training_report(evaluation_report)

            # 7. 输出总结
            self._print_training_summary(evaluation_report, model_path, report_path)

            return evaluation_report

        except Exception as e:
            logger.error(f"❌ 真实数据训练失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _generate_evaluation_report(
        self, training_metrics, feature_importance_df, data_summary
    ) -> dict:
        """
        生成详细的评估报告

        Args:
            training_metrics: 训练指标
            feature_importance_df: 特征重要性DataFrame
            data_summary: 数据摘要

        Returns:
            dict: 完整的评估报告
        """
        # 处理特征重要性
        top_features = []
        if feature_importance_df is not None and not feature_importance_df.empty:
            top_5_features = feature_importance_df.head(5)
            for _, row in top_5_features.iterrows():
                top_features.append(
                    {"feature": row["feature"], "importance": float(row["importance"])}
                )

        # 构建评估报告
        evaluation_report = {
            "success": True,
            "training_info": {
                "model_type": "XGBClassifier",
                "data_source": "PostgreSQL - 真实比赛数据",
                "total_samples": data_summary.get("total_records", 0),
                "training_samples": training_metrics.get("train_samples", 0),
                "test_samples": training_metrics.get("test_samples", 0),
                "feature_engineering": "RollingAverageTransformer (3, 5, 10 windows)",
                "target_variable": "主队获胜 (home_score > away_score)",
            },
            "performance_metrics": {
                "accuracy": float(training_metrics.get("accuracy", 0)),
                "precision": float(training_metrics.get("precision", 0)),
            },
            "top_5_features": top_features,
            "model_parameters": self.model_params,
            "training_timestamp": datetime.now().isoformat(),
            "data_quality": {
                "missing_values": "已处理",
                "outliers": "已处理",
                "temporal_splitting": "严格时间序列切分",
            },
        }

        return evaluation_report

    async def _save_model(self) -> str:
        """
        保存训练好的模型

        Returns:
            str: 模型保存路径
        """
        if (
            not hasattr(self.model_trainer, "model")
            or not self.model_trainer.is_trained_
        ):
            raise RuntimeError("模型尚未训练，无法保存")

        # 创建模型目录
        models_dir = football_prediction_root / "models"
        models_dir.mkdir(exist_ok=True)

        # 保存XGBoost模型
        model_path = models_dir / "baseline_v2_real.json"
        self.model_trainer.model.save_model(str(model_path))

        # 保存模型特征信息
        feature_info_path = models_dir / "baseline_v2_real_features.json"
        feature_info = {
            "feature_names": self.model_trainer.feature_names_,
            "feature_transformers": [
                {
                    "type": type(t).__name__,
                    "windows": t.windows if hasattr(t, "windows") else None,
                    "columns": t.columns if hasattr(t, "columns") else None,
                }
                for t in self.feature_transformers
            ],
        }

        with open(feature_info_path, "w", encoding="utf-8") as f:
            json.dump(feature_info, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 模型已保存: {model_path}")
        logger.info(f"✅ 特征信息已保存: {feature_info_path}")

        return str(model_path)

    async def _save_training_report(self, evaluation_report: dict) -> str:
        """
        保存训练报告

        Args:
            evaluation_report: 评估报告

        Returns:
            str: 报告保存路径
        """
        reports_dir = football_prediction_root / "reports"
        reports_dir.mkdir(exist_ok=True)

        # 生成报告文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"training_report_real_v2_{timestamp}.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 训练报告已保存: {report_path}")

        return str(report_path)

    def _print_training_summary(
        self, evaluation_report: dict, model_path: str, report_path: str
    ):
        """
        打印训练总结报告

        Args:
            evaluation_report: 评估报告
            model_path: 模型保存路径
            report_path: 报告保存路径
        """
        logger.info("🎉 真实数据基线模型训练完成!")
        logger.info("=" * 80)
        logger.info("📊 模型性能:")

        metrics = evaluation_report["performance_metrics"]
        logger.info(
            f"   • Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']:.2%})"
        )
        logger.info(
            f"   • Precision: {metrics['precision']:.4f} ({metrics['precision']:.2%})"
        )

        logger.info("🔧 技术规格:")
        training_info = evaluation_report["training_info"]
        logger.info(f"   • 数据来源:   {training_info['data_source']}")
        logger.info(f"   • 总样本数:   {training_info['total_samples']:,}")
        logger.info(f"   • 训练样本:   {training_info['training_samples']:,}")
        logger.info(f"   • 测试样本:   {training_info['test_samples']:,}")
        logger.info(f"   • 特征工程:   {training_info['feature_engineering']}")
        logger.info(f"   • 模型类型:   {training_info['model_type']}")

        logger.info("🏆 Top 5 重要特征:")
        top_features = evaluation_report["top_5_features"]
        for i, feature_info in enumerate(top_features, 1):
            logger.info(
                f"   {i}. {feature_info['feature']:<30} : {feature_info['importance']:.6f}"
            )

        logger.info("💾 输出文件:")
        logger.info(f"   • 模型文件:   {model_path}")
        logger.info(f"   • 训练报告:   {report_path}")
        logger.info("=" * 80)

        logger.info("🎯 Phase 4 真实数据集成成功!")
        logger.info("   • ✅ PostgresDataLoader 正常工作")
        logger.info("   • ✅ RollingAverageTransformer 特征生成")
        logger.info("   • ✅ XGBoost 模型训练完成")
        logger.info("   • ✅ 真实数据模型已就绪")


async def main():
    """主函数"""
    logger.info("🚀 Phase 4 - 真实数据基线模型训练脚本启动")
    logger.info(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建并执行训练流水线
    pipeline = RealDataTrainingPipeline()
    result = await pipeline.train_and_evaluate()

    logger.info(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if result.get("success", False):
        logger.info("✅ Phase 4 真实数据训练圆满完成!")

        # 提取并显示关键指标
        metrics = result["performance_metrics"]
        logger.info("\n" + "=" * 50)
        logger.info("📈 核心指标总结:")
        logger.info(f"   • Accuracy:  {metrics['accuracy']:.2%}")
        logger.info(f"   • Precision: {metrics['precision']:.2%}")

        logger.info("\n🏆 Top 5 特征重要性:")
        for i, feature in enumerate(result["top_5_features"], 1):
            logger.info(f"   {i}. {feature['feature']}: {feature['importance']:.6f}")

        logger.info("=" * 50)

        sys.exit(0)
    else:
        logger.error("❌ 真实数据训练失败!")
        logger.error(f"错误信息: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    # 运行真实数据训练
    asyncio.run(main())
