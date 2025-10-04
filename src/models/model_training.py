"""
import asyncio
基准模型训练器

使用XGBoost实现足球比赛结果预测的基准模型，支持：
- 从特征仓库获取训练数据
- 模型训练和验证
- MLflow实验跟踪
- 模型注册和版本管理
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd

# from sklearn.ensemble import RandomForestClassifier  # 备用分类器
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import xgboost as xgb  # type: ignore

    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    xgb = None  # type: ignore

# 处理可选依赖
try:
    import mlflow.sklearn

    import mlflow
    from mlflow import MlflowClient

    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    # 创建一个模拟的 mlflow 对象

    class MockMLflow:
        def start_run(self, **kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def log_metric(self, *args, **kwargs):
            pass

        def log_param(self, *args, **kwargs):
            pass

        def log_artifacts(self, *args, **kwargs):
            pass

        class sklearn:
            @staticmethod
            def log_model(*args, **kwargs):
                pass

    mlflow = MockMLflow()  # type: ignore
    mlflow.sklearn = MockMLflow.sklearn()  # type: ignore

    class MockMlflowClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_latest_versions(self, *args, **kwargs):
            return []

    # 将模拟类赋值给原名称，保持向后兼容
    MlflowClient = MockMlflowClient

from src.database.connection import DatabaseManager
from src.database.models import Match
from src.features.feature_store import FootballFeatureStore

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
        self.db_manager = DatabaseManager()
        self.feature_store = FootballFeatureStore()
        self.mlflow_tracking_uri = mlflow_tracking_uri

        # 设置MLflow跟踪URI
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)

        # XGBoost模型参数
        self.model_params = {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": -1,
            "eval_metric": "mlogloss",  # 多分类对数损失
        }

        # 特征配置
        self.feature_refs = [
            # 球队近期表现特征
            "team_recent_performance:recent_5_wins",
            "team_recent_performance:recent_5_draws",
            "team_recent_performance:recent_5_losses",
            "team_recent_performance:recent_5_goals_for",
            "team_recent_performance:recent_5_goals_against",
            "team_recent_performance:recent_5_points",
            "team_recent_performance:recent_5_home_wins",
            "team_recent_performance:recent_5_away_wins",
            # 历史对战特征
            "historical_matchup:h2h_total_matches",
            "historical_matchup:h2h_home_wins",
            "historical_matchup:h2h_away_wins",
            "historical_matchup:h2h_draws",
            "historical_matchup:h2h_recent_5_home_wins",
            "historical_matchup:h2h_recent_5_away_wins",
            # 赔率特征
            "odds_features:home_odds_avg",
            "odds_features:draw_odds_avg",
            "odds_features:away_odds_avg",
            "odds_features:home_implied_probability",
            "odds_features:draw_implied_probability",
            "odds_features:away_implied_probability",
            "odds_features:bookmaker_count",
        ]

    async def prepare_training_data(
        self, start_date: datetime, end_date: datetime, min_samples: int = 1000
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        从特征仓库获取训练数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            min_samples: 最小样本数量

        Returns:
            特征DataFrame和目标变量Series
        """
        logger.info(f"开始准备训练数据，时间范围：{start_date} 到 {end_date}")

        # 获取历史比赛数据
        matches_df = await self._get_historical_matches(start_date, end_date)
        logger.info(f"获取到 {len(matches_df)} 场历史比赛")

        if len(matches_df) < min_samples:
            raise ValueError(
                f"训练数据不足，需要至少 {min_samples} 条记录，实际获取 {len(matches_df)} 条"
            )

        # 准备实体DataFrame用于特征获取
        entity_df = pd.DataFrame(
            {
                "match_id": matches_df["id"],
                "team_id": matches_df["home_team_id"],  # Feast需要团队ID作为实体
                "event_timestamp": matches_df["match_time"],
            }
        )

        # 从Feast特征存储获取特征
        logger.info("从特征仓库获取特征数据...")
        try:
            features_df = await self.feature_store.get_historical_features(
                entity_df=entity_df,
                feature_refs=self.feature_refs,
                full_feature_names=True,
            )
            logger.info(f"获取到 {len(features_df)} 条特征记录")
        except Exception as e:
            logger.error(f"从特征仓库获取特征失败: {e}")
            # 如果特征仓库失败，使用简化特征
            features_df = await self._get_simplified_features(matches_df)
            logger.info(f"使用简化特征，获取到 {len(features_df)} 条记录")

        # 合并比赛结果作为目标变量
        features_df = features_df.merge(
            matches_df[["id", "result"]], left_on="match_id", right_on="id", how="inner"
        )

        # 分离特征和目标变量
        target_col = "result"
        feature_cols = [
            col
            for col in features_df.columns
            if col not in ["match_id", "team_id", "event_timestamp", "id", target_col]
        ]

        X = features_df[feature_cols].fillna(0)  # 填充缺失值
        y = features_df[target_col]

        logger.info(f"训练数据准备完成：{len(X)} 条样本，{len(feature_cols)} 个特征")
        return X, y

    async def _get_historical_matches(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """获取历史比赛数据"""
        async with self.db_manager.get_async_session() as session:
            # 查询已完成的比赛
            query = (
                select(
                    Match.id,
                    Match.home_team_id,
                    Match.away_team_id,
                    Match.league_id,
                    Match.match_time,
                    Match.home_score,
                    Match.away_score,
                    Match.season,
                )
                .where(
                    and_(
                        Match.match_time >= start_date,
                        Match.match_time <= end_date,
                        Match.match_status == "completed",
                        Match.home_score.isnot(None),
                        Match.away_score.isnot(None),
                    )
                )
                .order_by(Match.match_time)
            )

            result = await session.execute(query)
            matches = result.fetchall()

            # 转换为DataFrame
            df = pd.DataFrame(
                [
                    {
                        "id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "league_id": match.league_id,
                        "match_time": match.match_time,
                        "home_score": match.home_score,
                        "away_score": match.away_score,
                        "season": match.season,
                    }
                    for match in matches
                ]
            )

            if not df.empty:
                # 计算比赛结果
                df["result"] = df.apply(self._calculate_match_result, axis=1)

            return df

    def _calculate_match_result(self, row) -> str:
        """计算比赛结果"""
        home_score = row["home_score"]
        away_score = row["away_score"]

        if home_score is not None and away_score is not None and home_score > away_score:
            return "home"
        elif home_score < away_score:
            return "away"
        else:
            return "draw"

    async def _get_simplified_features(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """获取简化特征（当特征仓库不可用时）"""
        features_list = []

        async with self.db_manager.get_async_session() as session:
            for _, match in matches_df.iterrows():
                # 计算简化特征
                home_features = await self._calculate_team_simple_features(
                    session, match["home_team_id"], match["match_time"]
                )
                away_features = await self._calculate_team_simple_features(
                    session, match["away_team_id"], match["match_time"]
                )

                # 组合特征
                match_features = {
                    "match_id": match["id"],
                    "team_id": match["home_team_id"],
                    "event_timestamp": match["match_time"],
                    # 主队特征
                    "home_recent_wins": home_features["recent_wins"],
                    "home_recent_goals_for": home_features["recent_goals_for"],
                    "home_recent_goals_against": home_features["recent_goals_against"],
                    # 客队特征
                    "away_recent_wins": away_features["recent_wins"],
                    "away_recent_goals_for": away_features["recent_goals_for"],
                    "away_recent_goals_against": away_features["recent_goals_against"],
                    # 对战特征
                    "h2h_home_advantage": 0.5,  # 默认值
                }

                features_list.append(match_features)

        return pd.DataFrame(features_list)

    async def _calculate_team_simple_features(
        self, session: AsyncSession, team_id: int, match_time: datetime
    ) -> Dict[str, Any]:
        """计算球队简化特征"""
        # 查询最近5场比赛
        recent_matches_query = (
            select(Match)
            .where(
                and_(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.match_time < match_time,
                    Match.match_status == "completed",
                )
            )
            .order_by(desc(Match.match_time))
            .limit(5)
        )

        result = await session.execute(recent_matches_query)
        recent_matches = result.scalars().all()

        # 计算统计指标
        wins = 0
        goals_for = 0
        goals_against = 0

        for match in recent_matches:
            if match.home_team_id == team_id:
                # 主场比赛
                if match.home_score > match.away_score:
                    wins += 1
                goals_for += match.home_score or 0
                goals_against += match.away_score or 0
            else:
                # 客场比赛
                if match.away_score > match.home_score:
                    wins += 1
                goals_for += match.away_score or 0
                goals_against += match.home_score or 0

        return {
            "recent_wins": wins,
            "recent_goals_for": goals_for,
            "recent_goals_against": goals_against,
        }

    async def train_baseline_model(
        self,
        experiment_name: str = "football_prediction_baseline",
        model_name: str = "football_baseline_model",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        训练基准模型并注册到MLflow

        Args:
            experiment_name: 实验名称
            model_name: 模型名称
            start_date: 训练数据开始日期
            end_date: 训练数据结束日期

        Returns:
            MLflow运行ID
        """
        # 设置默认日期范围（过去1年）
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        logger.info(f"开始训练基准模型：{model_name}")
        logger.info(f"实验名称：{experiment_name}")
        logger.info(f"训练数据时间范围：{start_date} 到 {end_date}")

        # 设置或创建实验
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
            else:
                experiment_id = experiment.experiment_id
        except Exception as e:
            logger.error(f"设置MLflow实验失败: {e}")
            # 使用默认实验
            experiment_id = "0"

        mlflow.set_experiment(experiment_name)

        # 开始MLflow运行
        with mlflow.start_run(experiment_id=experiment_id) as run:
            try:
                # 准备训练数据
                X, y = await self.prepare_training_data(start_date, end_date)

                # 记录数据信息
                mlflow.log_params(
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
                mlflow.log_params(self.model_params)

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

                # 计算训练集指标
                train_accuracy = accuracy_score(y_train, y_train_pred)
                train_precision = precision_score(
                    y_train, y_train_pred, average="weighted"
                )
                train_recall = recall_score(y_train, y_train_pred, average="weighted")
                train_f1 = f1_score(y_train, y_train_pred, average="weighted")

                # 计算测试集指标
                test_accuracy = accuracy_score(y_test, y_test_pred)
                test_precision = precision_score(
                    y_test, y_test_pred, average="weighted"
                )
                test_recall = recall_score(y_test, y_test_pred, average="weighted")
                test_f1 = f1_score(y_test, y_test_pred, average="weighted")

                # 记录指标
                mlflow.log_metrics(
                    {
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
                )

                # 记录分类报告
                classification_rep = classification_report(
                    y_test, y_test_pred, output_dict=True
                )
                for class_name, metrics in classification_rep.items():
                    if isinstance(metrics, dict):
                        for metric_name, value in metrics.items():
                            mlflow.log_metric(f"{class_name}_{metric_name}", value)

                # 记录特征重要性
                if hasattr(model, "feature_importances_"):
                    feature_importance = dict(
                        zip(X.columns, model.feature_importances_)
                    )
                    # 记录前10个最重要的特征
                    top_features = sorted(
                        feature_importance.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                    for i, (feature, importance) in enumerate(top_features):
                        mlflow.log_metric(
                            f"feature_importance_{i+1}_{feature}", importance
                        )

                # 注册模型到MLflow
                logger.info(f"注册模型：{model_name}")
                mlflow.sklearn.log_model(
                    model,
                    "model",
                    registered_model_name=model_name,
                    signature=mlflow.models.infer_signature(X_train, y_train_pred),
                )

                # 记录模型元数据
                mlflow.set_tags(
                    {
                        "model_type": "XGBoost",
                        "framework": "sklearn",
                        "purpose": "football_match_prediction",
                        "features": ",".join(X.columns.tolist()),
                        "training_date": datetime.now().isoformat(),
                    }
                )

                logger.info("模型训练完成！")
                logger.info(f"测试集准确率: {test_accuracy:.4f}")
                logger.info(f"MLflow运行ID: {run.info.run_id}")

                return {
                    "run_id": run.info.run_id,
                    "metrics": {
                        "accuracy": test_accuracy,
                        "precision": test_precision,
                        "recall": test_recall,
                        "f1_score": test_f1,
                    },
                }

            except Exception as e:
                logger.error(f"模型训练失败: {e}")
                mlflow.log_param("training_status", "failed")
                mlflow.log_param("error_message", str(e))
                raise

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
        try:
            # Use existing client if available (for testing), otherwise create new one
            client = getattr(self, "mlflow_client", None) or MlflowClient(
                tracking_uri=self.mlflow_tracking_uri
            )

            if version is None:
                # 获取最新版本
                latest_versions = client.get_latest_versions(
                    name=model_name, stages=["Staging"]
                )
                if not latest_versions:
                    logger.error(f"模型 {model_name} 在Staging阶段没有版本")
                    return False
                version = latest_versions[0].version

            # 推广到生产环境
            client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage="Production",
                archive_existing_versions=True,  # 归档现有生产版本
            )

            logger.info(f"模型 {model_name} 版本 {version} 已推广到生产环境")
            return True

        except Exception as e:
            logger.error(f"模型推广失败: {e}")
            return False

    def get_model_performance_summary(self, run_id: str) -> Dict[str, Any]:
        """
        获取模型性能摘要

        Args:
            run_id: MLflow运行ID

        Returns:
            性能摘要字典
        """
        try:
            # Use existing client if available (for testing), otherwise create new one
            client = getattr(self, "mlflow_client", None) or MlflowClient(
                tracking_uri=self.mlflow_tracking_uri
            )
            run = client.get_run(run_id)

            return {
                "run_id": run_id,
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "metrics": run.data.metrics,
                "parameters": run.data.params,  # Changed from "params" to "parameters"
                "tags": run.data.tags,
            }

        except Exception as e:
            logger.error(f"获取模型性能摘要失败: {e}")
            return {}
