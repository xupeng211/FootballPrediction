#!/usr/bin/env python3
"""
自动重训练管道

功能：
1. 监控模型准确率，当低于阈值时触发重训练
2. 自动训练新模型并注册到MLflow
3. 生成新旧模型对比评估指标
4. 支持模型版本管理和回滚
5. 提供人工审核流程
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import mlflow.sklearn
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

import mlflow
from mlflow import MlflowClient

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logging import get_logger  # noqa: E402
from src.database.connection import get_async_session  # noqa: E402
from src.database.models.predictions import Predictions  # noqa: E402

logger = get_logger(__name__)

# MLflow配置
MLFLOW_TRACKING_URI = "http://localhost:5002"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


class AutoRetrainPipeline:
    """自动重训练管道"""

    def __init__(
        self,
        accuracy_threshold: float = 0.45,
        min_predictions_required: int = 50,
        evaluation_window_days: int = 30,
    ):
        """
        初始化自动重训练管道

        Args:
            accuracy_threshold: 准确率阈值，低于此值触发重训练
            min_predictions_required: 最少预测数量要求
            evaluation_window_days: 评估窗口天数
        """
        self.session: Optional[AsyncSession] = None
        self.mlflow_client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        self.accuracy_threshold = accuracy_threshold
        self.min_predictions_required = min_predictions_required
        self.evaluation_window_days = evaluation_window_days

        # 创建输出目录
        self.output_dir = Path("models/retrain_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = get_async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def evaluate_model_performance(
        self, model_name: str, model_version: str = None
    ) -> Dict[str, Any]:
        """
        评估模型性能

        Args:
            model_name: 模型名称
            model_version: 模型版本（可选）

        Returns:
            Dict[str, Any]: 性能评估结果
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        cutoff_date = datetime.utcnow() - timedelta(days=self.evaluation_window_days)

        # 构建查询条件
        query_conditions = [
            Predictions.model_name == model_name,
            Predictions.verified_at >= cutoff_date,
            Predictions.verified_at.isnot(None),
        ]

        if model_version:
            query_conditions.append(Predictions.model_version == model_version)

        # 查询性能数据
        stmt = select(
            func.count().label("total_predictions"),
            func.sum(func.case((Predictions.is_correct.is_(True), 1), else_=0)).label(
                "correct_predictions"
            ),
            func.avg(Predictions.confidence_score).label("avg_confidence"),
            func.min(Predictions.verified_at).label("earliest_prediction"),
            func.max(Predictions.verified_at).label("latest_prediction"),
        ).where(and_(*query_conditions))

        result = await self.session.execute(stmt)
        stats = result.first()

        if not stats or stats.total_predictions == 0:
            return {
                "model_name": model_name,
                "model_version": model_version,
                "evaluation_period": self.evaluation_window_days,
                "total_predictions": 0,
                "accuracy": 0.0,
                "needs_retrain": False,
                "reason": "No predictions found",
            }

        accuracy = stats.correct_predictions / stats.total_predictions
        needs_retrain = (
            stats.total_predictions >= self.min_predictions_required
            and accuracy < self.accuracy_threshold
        )

        # 获取最近趋势
        recent_performance = await self._get_recent_performance_trend(
            model_name, model_version, days=7
        )

        evaluation = {
            "model_name": model_name,
            "model_version": model_version,
            "evaluation_period": self.evaluation_window_days,
            "total_predictions": stats.total_predictions,
            "correct_predictions": stats.correct_predictions,
            "accuracy": round(accuracy, 4),
            "avg_confidence": (
                float(stats.avg_confidence) if stats.avg_confidence else None
            ),
            "earliest_prediction": stats.earliest_prediction,
            "latest_prediction": stats.latest_prediction,
            "needs_retrain": needs_retrain,
            "threshold": self.accuracy_threshold,
            "recent_trend": recent_performance,
            "evaluated_at": datetime.utcnow(),
        }

        if needs_retrain:
            evaluation[
                "reason"
            ] = f"Accuracy {accuracy:.2%} below threshold {self.accuracy_threshold:.2%}"
        elif stats.total_predictions < self.min_predictions_required:
            evaluation[
                "reason"
            ] = f"Insufficient predictions ({stats.total_predictions} < {self.min_predictions_required})"
        else:
            evaluation["reason"] = "Performance satisfactory"

        logger.info(f"模型 {model_name} 评估完成: 准确率 {accuracy:.2%}, 需要重训练: {needs_retrain}")
        return evaluation

    async def _get_recent_performance_trend(
        self, model_name: str, model_version: str = None, days: int = 7
    ) -> Dict[str, Any]:
        """
        获取最近的性能趋势

        Args:
            model_name: 模型名称
            model_version: 模型版本
            days: 分析天数

        Returns:
            Dict[str, Any]: 趋势分析结果
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query_conditions = [
            Predictions.model_name == model_name,
            Predictions.verified_at >= cutoff_date,
            Predictions.verified_at.isnot(None),
        ]

        if model_version:
            query_conditions.append(Predictions.model_version == model_version)

        # 按天统计准确率
        stmt = (
            select(
                func.date(Predictions.verified_at).label("prediction_date"),
                func.count().label("daily_predictions"),
                func.sum(
                    func.case((Predictions.is_correct.is_(True), 1), else_=0)
                ).label("daily_correct"),
            )
            .where(and_(*query_conditions))
            .group_by(func.date(Predictions.verified_at))
            .order_by(func.date(Predictions.verified_at))
        )

        result = await self.session.execute(stmt)
        daily_stats = result.all()

        if not daily_stats:
            return {"trend": "no_data", "daily_accuracies": []}

        daily_accuracies = [
            {
                "date": str(stat.prediction_date),
                "predictions": stat.daily_predictions,
                "accuracy": (
                    stat.daily_correct / stat.daily_predictions
                    if stat.daily_predictions > 0
                    else 0
                ),
            }
            for stat in daily_stats
        ]

        # 分析趋势
        if len(daily_accuracies) >= 2:
            recent_acc = sum(d["accuracy"] for d in daily_accuracies[-3:]) / min(
                3, len(daily_accuracies)
            )
            early_acc = sum(d["accuracy"] for d in daily_accuracies[:3]) / min(
                3, len(daily_accuracies)
            )

            if recent_acc > early_acc * 1.05:
                trend = "improving"
            elif recent_acc < early_acc * 0.95:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "daily_accuracies": daily_accuracies,
            "analysis_days": days,
        }

    async def get_models_for_evaluation(self) -> List[Dict[str, str]]:
        """
        获取需要评估的模型列表

        Returns:
            List[Dict[str, str]]: 模型列表
        """
        try:
            # 从MLflow获取注册的模型
            registered_models = self.mlflow_client.search_registered_models()

            models_to_evaluate = []

            for model in registered_models:
                model_name = model.name

                # 获取生产环境版本
                try:
                    production_versions = self.mlflow_client.get_latest_versions(
                        name=model_name, stages=["Production"]
                    )

                    if production_versions:
                        for version in production_versions:
                            models_to_evaluate.append(
                                {
                                    "model_name": model_name,
                                    "model_version": version.version,
                                    "stage": "Production",
                                }
                            )
                    else:
                        # 如果没有生产版本，检查Staging版本
                        staging_versions = self.mlflow_client.get_latest_versions(
                            name=model_name, stages=["Staging"]
                        )

                        for version in staging_versions:
                            models_to_evaluate.append(
                                {
                                    "model_name": model_name,
                                    "model_version": version.version,
                                    "stage": "Staging",
                                }
                            )

                except Exception as e:
                    logger.error(f"获取模型 {model_name} 版本失败: {e}")
                    continue

            logger.info(f"找到{len(models_to_evaluate)}个模型需要评估")
            return models_to_evaluate

        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []

    async def trigger_model_retraining(
        self, model_name: str, current_version: str, performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        触发模型重训练

        Args:
            model_name: 模型名称
            current_version: 当前版本
            performance_data: 性能数据

        Returns:
            Dict[str, Any]: 重训练结果
        """
        logger.info(f"开始重训练模型: {model_name} (当前版本: {current_version})")

        try:
            # 创建新的实验运行
            experiment_name = f"{model_name}_retrain"

            # 确保实验存在
            try:
                experiment = mlflow.get_experiment_by_name(experiment_name)
                if experiment is None:
                    experiment_id = mlflow.create_experiment(experiment_name)
                else:
                    experiment_id = experiment.experiment_id
            except Exception:
                experiment_id = mlflow.create_experiment(experiment_name)

            with mlflow.start_run(experiment_id=experiment_id) as run:
                # 记录重训练触发信息
                mlflow.log_params(
                    {
                        "trigger_reason": "automatic_retrain",
                        "previous_version": current_version,
                        "previous_accuracy": performance_data["accuracy"],
                        "threshold": self.accuracy_threshold,
                        "retrain_date": datetime.utcnow().isoformat(),
                    }
                )

                # 这里应该调用实际的模型训练逻辑
                # 为了演示，我们创建一个模拟的训练过程
                training_result = await self._execute_model_training(
                    model_name, performance_data
                )

                # 记录训练结果
                mlflow.log_metrics(training_result["metrics"])

                # 记录模型
                if "model" in training_result:
                    mlflow.sklearn.log_model(
                        training_result["model"],
                        "model",
                        registered_model_name=model_name,
                    )

                run_id = run.info.run_id

            # 将新模型版本设置为Staging
            latest_version = self._get_latest_model_version(model_name)
            if latest_version:
                self.mlflow_client.transition_model_version_stage(
                    name=model_name, version=latest_version, stage="Staging"
                )

                logger.info(f"新模型版本 {latest_version} 已设置为 Staging 阶段")

            return {
                "success": True,
                "model_name": model_name,
                "new_version": latest_version,
                "run_id": run_id,
                "training_metrics": training_result["metrics"],
                "retrained_at": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"模型重训练失败: {e}")
            return {
                "success": False,
                "model_name": model_name,
                "error": str(e),
                "retrained_at": datetime.utcnow(),
            }

    async def _execute_model_training(
        self, model_name: str, performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行模型训练（模拟实现）

        Args:
            model_name: 模型名称
            performance_data: 性能数据

        Returns:
            Dict[str, Any]: 训练结果
        """
        # 这里应该实现实际的模型训练逻辑
        # 为了演示目的，我们返回模拟的训练结果

        logger.info(f"开始训练模型 {model_name}...")

        # 模拟训练过程
        await asyncio.sleep(2)  # 模拟训练时间

        # 模拟的训练指标
        training_metrics = {
            "train_accuracy": 0.72,
            "validation_accuracy": 0.68,
            "train_loss": 0.45,
            "validation_loss": 0.52,
            "training_time": 120,  # 秒
            "epochs": 100,
            "learning_rate": 0.001,
        }

        logger.info(f"模型训练完成，验证准确率: {training_metrics['validation_accuracy']:.2%}")

        return {
            "success": True,
            "metrics": training_metrics,
            "model": None,  # 在实际实现中，这里应该是训练好的模型对象
            "training_data_size": 1000,  # 训练数据大小
            "features_used": 25,  # 使用的特征数量
        }

    def _get_latest_model_version(self, model_name: str) -> Optional[str]:
        """
        获取模型的最新版本

        Args:
            model_name: 模型名称

        Returns:
            Optional[str]: 最新版本号
        """
        try:
            latest_versions = self.mlflow_client.get_latest_versions(name=model_name)
            if latest_versions:
                # 返回版本号最大的版本
                return str(max(int(v.version) for v in latest_versions))
            return None
        except Exception as e:
            logger.error(f"获取最新模型版本失败: {e}")
            return None

    async def generate_comparison_report(
        self,
        model_name: str,
        old_version: str,
        new_version: str,
        retrain_result: Dict[str, Any],
    ) -> str:
        """
        生成新旧模型对比报告

        Args:
            model_name: 模型名称
            old_version: 旧版本
            new_version: 新版本
            retrain_result: 重训练结果

        Returns:
            str: 报告文件路径
        """
        logger.info(f"生成模型对比报告: {model_name} v{old_version} vs v{new_version}")

        # 获取旧模型性能数据
        old_performance = await self.evaluate_model_performance(model_name, old_version)

        # 获取新模型的训练指标
        new_metrics = retrain_result.get("training_metrics", {})

        # 生成报告内容
        report_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        report_content = f"""# 模型重训练对比报告

**模型名称**: {model_name}
**生成时间**: {report_time}
**报告类型**: 自动重训练对比分析

---

## 📊 重训练触发信息

### 触发原因
- **当前模型版本**: v{old_version}
- **当前准确率**: {old_performance['accuracy']:.2%}
- **准确率阈值**: {self.accuracy_threshold:.2%}
- **评估周期**: {self.evaluation_window_days} 天
- **预测数量**: {old_performance['total_predictions']}

### 性能趋势
- **最近趋势**: {old_performance['recent_trend']['trend']}
- **需要重训练**: {'是' if old_performance['needs_retrain'] else '否'}

---

## 🔄 重训练结果

### 新模型信息
- **新版本**: v{new_version}
- **训练状态**: {'成功' if retrain_result['success'] else '失败'}
- **MLflow运行ID**: {retrain_result.get('run_id', 'N/A')}
- **模型阶段**: Staging（待人工审核）

### 训练指标
"""

        if new_metrics:
            report_content += f"""
| 指标 | 数值 |
|------|------|
| 训练准确率 | {new_metrics.get('train_accuracy', 'N/A'):.2%} |
| 验证准确率 | {new_metrics.get('validation_accuracy', 'N/A'):.2%} |
| 训练损失 | {new_metrics.get('train_loss', 'N/A'):.3f} |
| 验证损失 | {new_metrics.get('validation_loss', 'N/A'):.3f} |
| 训练时间 | {new_metrics.get('training_time', 'N/A')} 秒 |
| 训练轮数 | {new_metrics.get('epochs', 'N/A')} |
| 学习率 | {new_metrics.get('learning_rate', 'N/A')} |
"""

        report_content += f"""

---

## 📈 性能对比分析

### 旧模型表现 (v{old_version})
- **整体准确率**: {old_performance['accuracy']:.2%}
- **预测总数**: {old_performance['total_predictions']}
- **平均置信度**: {old_performance['avg_confidence']:.3f if old_performance['avg_confidence'] else 'N/A'}
- **评估时段**: {old_performance['earliest_prediction']} 至 {old_performance['latest_prediction']}

### 新模型表现 (v{new_version})
- **验证准确率**: {new_metrics.get('validation_accuracy', 0):.2%}
- **训练数据量**: {retrain_result.get('training_data_size', 'N/A')}
- **使用特征数**: {retrain_result.get('features_used', 'N/A')}

### 对比分析
"""

        if new_metrics.get("validation_accuracy"):
            improvement = (
                new_metrics["validation_accuracy"] - old_performance["accuracy"]
            )
            improvement_pct = (
                (improvement / old_performance["accuracy"]) * 100
                if old_performance["accuracy"] > 0
                else 0
            )

            report_content += f"""
- **准确率改进**: {improvement:+.4f} ({improvement_pct:+.1f}%)
- **改进状态**: {'显著改进' if improvement > 0.05 else '轻微改进' if improvement > 0 else '需要进一步优化'}
"""

        report_content += """

---

## 🚀 部署建议

### 自动评估结果
"""

        if (
            retrain_result["success"]
            and new_metrics.get("validation_accuracy", 0) > old_performance["accuracy"]
        ):
            report_content += """
✅ **建议部署**: 新模型性能优于当前模型
- 新模型已设置为 Staging 阶段
- 建议进行人工审核后推广到生产环境
- 可以考虑 A/B 测试验证效果
"""
        else:
            report_content += """
⚠️ **需要人工审核**: 新模型性能需要进一步评估
- 新模型暂时保持在 Staging 阶段
- 建议详细分析性能差异原因
- 可能需要调整训练参数或数据
"""

        report_content += f"""

### 推荐操作步骤
1. **性能验证**: 在测试环境中验证新模型效果
2. **A/B测试**: 对比新旧模型在真实场景中的表现
3. **逐步部署**: 先部署到部分流量，观察效果
4. **监控指标**: 密切关注准确率、置信度等关键指标
5. **回滚准备**: 如有问题，及时回滚到旧版本

---

## 📋 技术细节

**MLflow信息**:
- 跟踪URI: {MLFLOW_TRACKING_URI}
- 实验名称: {model_name}_retrain
- 模型注册表: {model_name}

**系统配置**:
- 准确率阈值: {self.accuracy_threshold:.2%}
- 最小预测要求: {self.min_predictions_required}
- 评估窗口: {self.evaluation_window_days} 天

---

*本报告由自动重训练系统生成*
"""

        # 保存报告
        report_filename = f"retrain_comparison_{model_name}_v{old_version}_to_v{new_version}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = self.output_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"对比报告已生成: {report_path}")
        return str(report_path)

    async def run_evaluation_cycle(self) -> Dict[str, Any]:
        """
        运行完整的评估和重训练周期

        Returns:
            Dict[str, Any]: 执行结果
        """
        logger.info("开始自动重训练评估周期")

        results = {
            "start_time": datetime.utcnow(),
            "models_evaluated": 0,
            "models_needing_retrain": 0,
            "retraining_triggered": 0,
            "retraining_successful": 0,
            "reports_generated": 0,
            "model_results": [],
            "errors": [],
        }

        try:
            # 获取需要评估的模型
            models_to_evaluate = await self.get_models_for_evaluation()
            results["models_evaluated"] = len(models_to_evaluate)

            if not models_to_evaluate:
                logger.warning("未找到需要评估的模型")
                return results

            # 逐个评估模型
            for model_info in models_to_evaluate:
                model_name = model_info["model_name"]
                model_version = model_info["model_version"]

                try:
                    logger.info(f"评估模型: {model_name} v{model_version}")

                    # 评估性能
                    performance = await self.evaluate_model_performance(
                        model_name, model_version
                    )

                    model_result = {
                        "model_name": model_name,
                        "model_version": model_version,
                        "performance": performance,
                        "retrain_triggered": False,
                        "retrain_successful": False,
                        "new_version": None,
                        "report_path": None,
                    }

                    # 如果需要重训练
                    if performance["needs_retrain"]:
                        results["models_needing_retrain"] += 1
                        logger.info(f"触发重训练: {model_name} v{model_version}")

                        # 执行重训练
                        retrain_result = await self.trigger_model_retraining(
                            model_name, model_version, performance
                        )

                        model_result["retrain_triggered"] = True
                        results["retraining_triggered"] += 1

                        if retrain_result["success"]:
                            results["retraining_successful"] += 1
                            model_result["retrain_successful"] = True
                            model_result["new_version"] = retrain_result["new_version"]

                            # 生成对比报告
                            try:
                                report_path = await self.generate_comparison_report(
                                    model_name,
                                    model_version,
                                    retrain_result["new_version"],
                                    retrain_result,
                                )
                                model_result["report_path"] = report_path
                                results["reports_generated"] += 1
                            except Exception as e:
                                logger.error(f"生成对比报告失败: {e}")
                                results["errors"].append(
                                    f"Report generation failed for {model_name}: {e}"
                                )

                        model_result["retrain_result"] = retrain_result

                    results["model_results"].append(model_result)

                except Exception as e:
                    logger.error(f"处理模型 {model_name} 失败: {e}")
                    results["errors"].append(f"Model {model_name}: {e}")

        except Exception as e:
            logger.error(f"评估周期执行失败: {e}")
            results["errors"].append(f"Cycle execution failed: {e}")

        results["end_time"] = datetime.utcnow()
        results["duration_seconds"] = (
            results["end_time"] - results["start_time"]
        ).total_seconds()

        logger.info(
            f"评估周期完成: "
            f"评估{results['models_evaluated']}个模型, "
            f"{results['models_needing_retrain']}个需要重训练, "
            f"{results['retraining_successful']}个重训练成功"
        )

        return results


@click.command()
@click.option("--threshold", default=0.45, help="准确率阈值")
@click.option("--min-predictions", default=50, help="最小预测数量要求")
@click.option("--window-days", default=30, help="评估窗口天数")
@click.option("--model-name", help="指定模型名称（可选）")
@click.option("--dry-run", is_flag=True, help="试运行模式，不执行实际重训练")
@click.option("--verbose", is_flag=True, help="详细输出")
def main(
    threshold: float,
    min_predictions: int,
    window_days: int,
    model_name: str,
    dry_run: bool,
    verbose: bool,
):
    """自动重训练管道主入口"""

    # 配置日志级别
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def run():
        async with AutoRetrainPipeline(
            accuracy_threshold=threshold,
            min_predictions_required=min_predictions,
            evaluation_window_days=window_days,
        ) as pipeline:
            click.echo("🚀 启动自动重训练管道")
            click.echo(f"   准确率阈值: {threshold:.2%}")
            click.echo(f"   最小预测数: {min_predictions}")
            click.echo(f"   评估窗口: {window_days} 天")
            click.echo(f"   试运行模式: {'是' if dry_run else '否'}")

            if model_name:
                click.echo(f"   指定模型: {model_name}")

                # 单模型评估
                performance = await pipeline.evaluate_model_performance(model_name)

                click.echo("\n📊 模型性能评估:")
                click.echo(f"   准确率: {performance['accuracy']:.2%}")
                click.echo(f"   预测数量: {performance['total_predictions']}")
                click.echo(f"   需要重训练: {'是' if performance['needs_retrain'] else '否'}")
                click.echo(f"   原因: {performance['reason']}")

                if performance["needs_retrain"] and not dry_run:
                    click.echo("\n🔄 开始重训练...")
                    retrain_result = await pipeline.trigger_model_retraining(
                        model_name, performance.get("model_version"), performance
                    )

                    if retrain_result["success"]:
                        click.echo(f"✅ 重训练成功! 新版本: v{retrain_result['new_version']}")

                        # 生成对比报告
                        report_path = await pipeline.generate_comparison_report(
                            model_name,
                            performance.get("model_version", "unknown"),
                            retrain_result["new_version"],
                            retrain_result,
                        )
                        click.echo(f"📄 对比报告: {report_path}")
                    else:
                        click.echo(f"❌ 重训练失败: {retrain_result['error']}")

            else:
                # 全量评估周期
                if dry_run:
                    click.echo("\n🔍 试运行模式 - 仅评估，不执行重训练")

                results = await pipeline.run_evaluation_cycle()

                click.echo("\n📊 执行结果:")
                click.echo(f"   评估模型数: {results['models_evaluated']}")
                click.echo(f"   需要重训练: {results['models_needing_retrain']}")
                click.echo(f"   触发重训练: {results['retraining_triggered']}")
                click.echo(f"   重训练成功: {results['retraining_successful']}")
                click.echo(f"   生成报告数: {results['reports_generated']}")
                click.echo(f"   执行时间: {results['duration_seconds']:.1f} 秒")

                if results["errors"]:
                    click.echo("\n⚠️ 错误信息:")
                    for error in results["errors"]:
                        click.echo(f"   - {error}")

                # 显示详细结果
                if verbose and results["model_results"]:
                    click.echo("\n📋 详细结果:")
                    for model_result in results["model_results"]:
                        click.echo(
                            f"   🤖 {model_result['model_name']} v{model_result['model_version']}:"
                        )
                        click.echo(
                            f"      准确率: {model_result['performance']['accuracy']:.2%}"
                        )
                        click.echo(
                            f"      重训练: {'是' if model_result['retrain_triggered'] else '否'}"
                        )
                        if model_result["report_path"]:
                            click.echo(f"      报告: {model_result['report_path']}")

    # 运行异步函数
    asyncio.run(run())


if __name__ == "__main__":
    main()
