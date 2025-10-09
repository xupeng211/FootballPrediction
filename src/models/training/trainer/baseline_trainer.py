"""
基准模型训练器

使用XGBoost实现足球比赛结果预测的基准模型
"""


    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    xgb = None


logger = logging.getLogger(__name__)


class BaselineModelTrainer:
    """
    基准模型训练器

    使用XGBoost实现足球比赛结果预测的基准模型，支持：
    - 从特征仓库获取训练数据
    - 模型训练和验证
    - MLflow实验跟踪
    - 模型注册和版本管理
    """

    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5002"):
        """
        初始化训练器

        Args:
            mlflow_tracking_uri: MLflow跟踪服务器URI
        """
        self.feature_processor = FeatureProcessor()
        self.experiment_manager = ExperimentManager(mlflow_tracking_uri)

        # XGBoost模型参数
        self.model_params = {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": -1,
            "eval_metric": "mlogloss",
        }

    async def train_baseline_model(
        self,
        experiment_name: str = "football_prediction_baseline",
        model_name: str = "football_baseline_model",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        训练基准模型并注册到MLflow

        Args:
            experiment_name: 实验名称
            model_name: 模型名称
            start_date: 训练数据开始日期
            end_date: 训练数据结束日期

        Returns:
            训练结果字典
        """
        # 设置默认日期范围（过去1年）
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        logger.info(f"开始训练基准模型：{model_name}")
        logger.info(f"实验名称：{experiment_name}")
        logger.info(f"训练数据时间范围：{start_date} 到 {end_date}")

        # 创建或获取实验
        experiment_id = await self.experiment_manager.get_or_create_experiment(
            experiment_name
        )

        # 开始MLflow运行
        async with self.experiment_manager.start_run(experiment_id) as run:
            try:
                # 准备训练数据
                X, y = await self.feature_processor.prepare_training_data(
                    start_date, end_date
                )

                # 记录数据信息
                await self.experiment_manager.log_params(
                    {
                        "training_start_date": start_date.isoformat(),
                        "training_end_date": end_date.isoformat(),
                        "total_samples": len(X),
                        "feature_count": len(X.columns),
                        "class_distribution": y.value_counts().to_dict(),
                    }
                )

                # 分割训练和测试数据
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y
                )

                # 记录模型参数
                await self.experiment_manager.log_params(self.model_params)

                # 训练XGBoost模型
                logger.info("开始训练XGBoost模型...")
                if not HAS_XGB:
                    raise ImportError(
                        "XGBoost not available, install with: pip install xgboost"
                    )
                model = xgb.XGBClassifier(**self.model_params)
                model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

                # 模型预测
                y_train_pred = model.predict(X_train)
                y_test_pred = model.predict(X_test)

                # 计算指标
                metrics = self._calculate_metrics(
                    y_train, y_train_pred, y_test, y_test_pred
                )

                # 记录指标
                await self.experiment_manager.log_metrics(metrics)

                # 记录分类报告
                await self._log_classification_report(y_test, y_test_pred)

                # 记录特征重要性
                await self._log_feature_importance(model, X)

                # 注册模型到MLflow
                logger.info(f"注册模型：{model_name}")
                await self.experiment_manager.log_model(
                    model, model_name, X_train, y_train_pred
                )

                # 记录模型元数据
                await self.experiment_manager.set_tags(
                    {
                        "model_type": "XGBoost",
                        "framework": "sklearn",
                        "purpose": "football_match_prediction",
                        "features": ",".join(X.columns.tolist()),
                        "training_date": datetime.now().isoformat(),
                    }
                )

                logger.info("模型训练完成！")
                logger.info(f"测试集准确率: {metrics['test_accuracy']:.4f}")
                logger.info(f"MLflow运行ID: {run.info.run_id}")

                return {
                    "run_id": run.info.run_id,
                    "metrics": {
                        "accuracy": metrics["test_accuracy"],
                        "precision": metrics["test_precision"],
                        "recall": metrics["test_recall"],
                        "f1_score": metrics["test_f1"],
                    },
                }

            except Exception as e:
                logger.error(f"模型训练失败: {e}")
                await self.experiment_manager.log_param("training_status", "failed")
                await self.experiment_manager.log_param("error_message", str(e))
                raise

    def _calculate_metrics(
        self, y_train, y_train_pred, y_test, y_test_pred
    ) -> Dict[str, float]:
        """计算训练和测试集指标"""
        # 计算训练集指标
        train_accuracy = accuracy_score(y_train, y_train_pred)
        train_precision = precision_score(y_train, y_train_pred, average="weighted")
        train_recall = recall_score(y_train, y_train_pred, average="weighted")
        train_f1 = f1_score(y_train, y_train_pred, average="weighted")

        # 计算测试集指标
        test_accuracy = accuracy_score(y_test, y_test_pred)
        test_precision = precision_score(y_test, y_test_pred, average="weighted")
        test_recall = recall_score(y_test, y_test_pred, average="weighted")
        test_f1 = f1_score(y_test, y_test_pred, average="weighted")

        return {
            "train_accuracy": train_accuracy,
            "train_precision": train_precision,
            "train_recall": train_recall,
            "train_f1": train_f1,
            "test_accuracy": test_accuracy,
            "test_precision": test_precision,
            "test_recall": test_recall,
            "test_f1": test_f1,
            "overfitting_score": train_accuracy - test_accuracy,
        }

    async def _log_classification_report(self, y_test, y_test_pred) -> None:
        """记录分类报告"""
        classification_rep = classification_report(
            y_test, y_test_pred, output_dict=True
        )
        for class_name, metrics in classification_rep.items():
            if isinstance(metrics, dict):
                for metric_name, value in metrics.items():
                    await self.experiment_manager.log_metric(
                        f"{class_name}_{metric_name}", value
                    )

    async def _log_feature_importance(self, model, X) -> None:
        """记录特征重要性"""
        if hasattr(model, "feature_importances_"):
            feature_importance = dict(zip(X.columns, model.feature_importances_))
            # 记录前10个最重要的特征
            top_features = sorted(
                feature_importance.items(), key=lambda x: x[1], reverse=True
            )[:10]
            for i, (feature, importance) in enumerate(top_features):
                await self.experiment_manager.log_metric(
                    f"feature_importance_{i+1}_{feature}", importance
                )

    async def promote_model_to_production(
        self, model_name: str = "football_baseline_model", version: Optional[str] = None
    ) -> bool:
        """
        将模型推广到生产环境

        Args:
            model_name: 模型名称
            version: 模型版本，如果为None则使用最新版本

        Returns:
            是否成功推广
        """
        return await self.experiment_manager.promote_model_to_production(
            model_name, version
        )

    async def get_model_performance_summary(self, run_id: str) -> Dict[str, Any]:
        """
        获取模型性能摘要

        Args:
            run_id: MLflow运行ID

        Returns:
            性能摘要字典
        """
        return await self.experiment_manager.get_run_summary(run_id)