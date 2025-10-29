#!/usr/bin/env python3
"""
真实数据模型训练脚本
Real Data Model Training Script

集成了特征工程、高级模型训练和AutoML管道的完整训练流程
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pathlib import Path

from src.core.logging_system import get_logger
from src.features.features.feature_calculator_calculators import (
    FeatureCalculator,
    MatchResult,
)
from src.ml.advanced_model_trainer import (
    AdvancedModelTrainer,
    EnsembleTrainer,
    ModelType,
)
from src.ml.automl_pipeline import AutoMLPipeline

logger = get_logger(__name__)


class RealModelTrainingPipeline:
    """真实数据模型训练管道"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化训练管道

        Args:
            config: 训练配置
        """
        self.config = config or {}
        self.feature_calculator = FeatureCalculator()
        self.models = {}
        self.training_history = []
        self.logger = get_logger(self.__class__.__name__)

        # 训练结果保存路径
        self.models_dir = Path(self.config.get("models_dir", "models/trained"))
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("RealModelTrainingPipeline initialized")

    def create_sample_match_data(self, num_matches: int = 500) -> List[MatchResult]:
        """
        创建示例比赛数据（用于测试）

        Args:
            num_matches: 比赛数量

        Returns:
            比赛结果列表
        """
        self.logger.info(f"Creating {num_matches} sample match data...")

        teams = [
            "Manchester United",
            "Manchester City",
            "Liverpool",
            "Chelsea",
            "Arsenal",
            "Tottenham",
            "Leicester City",
            "West Ham",
            "Aston Villa",
            "Leeds United",
            "Everton",
            "Newcastle",
            "Wolverhampton",
            "Crystal Palace",
            "Southampton",
            "Brighton",
            "Burnley",
            "Fulham",
            "West Brom",
            "Sheffield United",
        ]

        leagues = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]

        matches = []
        base_date = datetime.now() - timedelta(days=365)

        for i in range(num_matches):
            # 随机选择主客队
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])
            league = np.random.choice(leagues)

            # 生成比分（基于随机概率，但保持一定的合理性）
            home_strength = np.random.uniform(0.3, 0.8)
            away_strength = np.random.uniform(0.3, 0.8)

            # 主场优势
            home_advantage = 0.1

            # 计算期望进球数
            home_exp_goals = (home_strength + home_advantage) * 2.5
            away_exp_goals = away_strength * 2.0

            # 使用泊松分布生成实际进球数
            home_score = np.random.poisson(home_exp_goals)
            away_score = np.random.poisson(away_exp_goals)

            # 确保比分不会太大
            home_score = min(home_score, 7)
            away_score = min(away_score, 7)

            match_date = base_date + timedelta(days=i)

            match = MatchResult(
                match_id=f"match_{i:04d}",
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                match_date=match_date,
                league=league,
                home_win=home_score > away_score,
                draw=home_score == away_score,
                away_win=home_score < away_score,
                home_goals=home_score,
                away_goals=away_score,
                total_goals=home_score + away_score,
                goal_difference=home_score - away_score,
            )

            matches.append(match)

        self.logger.info(f"Created {len(matches)} sample matches")
        return matches

    def create_sample_league_table(self, teams: List[str]) -> List[Dict[str, Any]]:
        """
        创建示例积分榜

        Args:
            teams: 球队列表

        Returns:
            积分榜数据
        """
        league_table = []

        # 为每个球队生成随机积分
        for i, team in enumerate(teams):
            points = np.random.randint(20, 80)  # 随机积分
            goal_diff = np.random.randint(-20, 40)  # 随机净胜球

            league_table.append(
                {
                    "position": i + 1,
                    "team": team,
                    "played": np.random.randint(25, 38),
                    "won": np.random.randint(5, 25),
                    "drawn": np.random.randint(3, 15),
                    "lost": np.random.randint(3, 20),
                    "goals_for": np.random.randint(20, 80),
                    "goals_against": np.random.randint(20, 70),
                    "goal_difference": goal_diff,
                    "points": points,
                }
            )

        # 按积分排序
        league_table.sort(key=lambda x: x["points"], reverse=True)

        # 更新排名
        for i, club in enumerate(league_table):
            club["position"] = i + 1

        return league_table

    async def prepare_training_data(
        self,
        matches: List[MatchResult],
        league_table: Optional[List[Dict]] = None,
        league: str = "Premier League",
    ) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """
        准备训练数据

        Args:
            matches: 比赛数据
            league_table: 积分榜数据
            league: 联赛名称

        Returns:
            特征DataFrame、标签Series和特征列名
        """
        self.logger.info("Preparing training data...")

        # 为所有比赛计算特征
        all_features = []
        targets = []

        for match in matches:
            try:
                # 计算比赛特征
                features = self.feature_calculator.calculate_all_features(
                    match.home_team, match.away_team, matches, league_table, league
                )

                # 添加基本信息
                features["match_id"] = match.match_id
                features["home_team"] = match.home_team
                features["away_team"] = match.away_team
                features["match_date"] = match.match_date

                # 确定目标变量
                if match.home_win:
                    target = 2  # 主队胜
                elif match.draw:
                    target = 1  # 平局
                else:
                    target = 0  # 主队负

                all_features.append(features)
                targets.append(target)

            except Exception as e:
                self.logger.warning(f"Failed to process match {match.match_id}: {e}")
                continue

        if not all_features:
            raise ValueError("No valid features generated")

        # 创建DataFrame
        df = pd.DataFrame(all_features)
        y = pd.Series(targets)

        # 移除非特征列
        feature_columns = [
            col
            for col in df.columns
            if col not in ["match_id", "home_team", "away_team", "match_date"]
        ]

        X = df[feature_columns]

        self.logger.info(
            f"Training data prepared: {len(X)} samples, {len(feature_columns)} features"
        )
        return X, y, feature_columns

    async def train_single_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_type: str = "xgboost_classifier",
        hyperparameter_tuning: bool = True,
    ) -> Dict[str, Any]:
        """
        训练单个模型

        Args:
            X: 特征数据
            y: 标签数据
            model_type: 模型类型
            hyperparameter_tuning: 是否进行超参数调优

        Returns:
            训练结果
        """
        self.logger.info(f"Training single model: {model_type}")

        trainer = AdvancedModelTrainer(self.config)
        result = await trainer.train_model(
            X, y, model_type, hyperparameter_tuning, validation_split=0.2
        )

        if result["success"]:
            # 保存模型
            model_path = (
                self.models_dir / f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            )
            trainer.save_model(str(model_path))

            # 保存到模型字典
            self.models[model_type] = {
                "trainer": trainer,
                "result": result,
                "path": str(model_path),
            }

            self.logger.info(f"Model {model_type} trained and saved successfully")
        else:
            self.logger.error(f"Model {model_type} training failed: {result.get('error')}")

        return result

    async def train_ensemble_models(
        self, X: pd.DataFrame, y: pd.Series, model_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        训练集成模型

        Args:
            X: 特征数据
            y: 标签数据
            model_types: 模型类型列表

        Returns:
            训练结果
        """
        self.logger.info("Training ensemble models")

        if model_types is None:
            model_types = [
                ModelType.XGBOOST_CLASSIFIER.value,
                ModelType.LIGHTGBM_CLASSIFIER.value,
                ModelType.RANDOM_FOREST.value,
            ]

        trainer = EnsembleTrainer(self.config)
        result = await trainer.train_ensemble(
            X, y, model_types, validation_split=0.2, hyperparameter_tuning=True
        )

        if result["success"]:
            # 保存集成模型
            ensemble_path = (
                self.models_dir / f"ensemble_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            )
            trainer.save_ensemble(str(ensemble_path))

            # 保存到模型字典
            self.models["ensemble"] = {
                "trainer": trainer,
                "result": result,
                "path": str(ensemble_path),
            }

            self.logger.info("Ensemble model trained and saved successfully")
        else:
            self.logger.error(f"Ensemble model training failed: {result.get('error')}")

        return result

    async def run_automl(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        运行AutoML流程

        Args:
            X: 特征数据
            y: 标签数据

        Returns:
            AutoML结果
        """
        self.logger.info("Running AutoML pipeline")

        automl = AutoMLPipeline(self.config)

        # 测试多种模型类型
        model_types_to_test = ["random_forest", "gradient_boosting"]

        best_result = None
        best_score = 0
        best_model_type = None

        for model_type in model_types_to_test:
            try:
                result = await automl.train_model(X, y, model_type, hyperparameter_tuning=True)

                if result["success"]:
                    score = result.get("metric_value", 0)
                    if score > best_score:
                        best_score = score
                        best_result = result
                        best_model_type = model_type

                        self.logger.info(
                            f"New best AutoML model: {model_type} with score {score:.4f}"
                        )

            except Exception as e:
                self.logger.warning(f"AutoML failed for {model_type}: {e}")
                continue

        if best_result:
            # 保存最佳AutoML模型
            automl_path = (
                self.models_dir
                / f"automl_{best_model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            )
            automl.save_model(str(automl_path))

            # 保存到模型字典
            self.models[f"automl_{best_model_type}"] = {
                "trainer": automl,
                "result": best_result,
                "path": str(automl_path),
            }

            best_result["best_model_type"] = best_model_type
            best_result["best_score"] = best_score

        return best_result or {"success": False, "error": "All AutoML models failed"}

    async def compare_models(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        比较所有训练好的模型

        Args:
            X_test: 测试特征
            y_test: 测试标签

        Returns:
            模型比较结果
        """
        self.logger.info("Comparing all trained models")

        comparison_results = {}

        for model_name, model_info in self.models.items():
            try:
                trainer = model_info["trainer"]

                if hasattr(trainer, "predict"):
                    if isinstance(trainer, EnsembleTrainer):
                        result = await trainer.predict_ensemble(X_test)
                    else:
                        result = await trainer.predict(X_test)

                    if result["success"]:
                        predictions = result["predictions"]

                        # 计算指标
                        from sklearn.metrics import (
                            accuracy_score,
                            precision_score,
                            recall_score,
                            f1_score,
                        )

                        metrics = {
                            "accuracy": accuracy_score(y_test, predictions),
                            "precision": precision_score(
                                y_test, predictions, average="weighted", zero_division=0
                            ),
                            "recall": recall_score(
                                y_test, predictions, average="weighted", zero_division=0
                            ),
                            "f1_score": f1_score(
                                y_test, predictions, average="weighted", zero_division=0
                            ),
                        }

                        comparison_results[model_name] = {
                            "metrics": metrics,
                            "training_result": model_info["result"],
                        }

                        self.logger.info(
                            f"Model {model_name} test accuracy: {metrics['accuracy']:.4f}"
                        )

            except Exception as e:
                self.logger.error(f"Failed to evaluate model {model_name}: {e}")
                comparison_results[model_name] = {"error": str(e)}

        # 找出最佳模型
        if comparison_results:
            best_model = max(
                comparison_results.items(),
                key=lambda x: x[1].get("metrics", {}).get("accuracy", 0),
            )

            comparison_results["best_model"] = {
                "name": best_model[0],
                "accuracy": best_model[1].get("metrics", {}).get("accuracy", 0),
            }

        return comparison_results

    async def run_complete_training_pipeline(
        self,
        matches: Optional[List[MatchResult]] = None,
        league_table: Optional[List[Dict]] = None,
        use_sample_data: bool = True,
    ) -> Dict[str, Any]:
        """
        运行完整的训练管道

        Args:
            matches: 比赛数据
            league_table: 积分榜数据
            use_sample_data: 是否使用示例数据

        Returns:
            完整的训练结果
        """
        self.logger.info("Starting complete training pipeline...")
        start_time = datetime.now()

        try:
            # 1. 准备数据
            if use_sample_data or matches is None:
                matches = self.create_sample_match_data(500)

                # 创建积分榜
                teams = list(set([m.home_team for m in matches] + [m.away_team for m in matches]))
                league_table = self.create_sample_league_table(teams)

            # 2. 准备训练数据
            X, y, feature_columns = await self.prepare_training_data(matches, league_table)

            # 3. 数据分割
            from sklearn.model_selection import train_test_split

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # 4. 训练单个模型
            single_model_results = {}
            for model_type in [
                ModelType.XGBOOST_CLASSIFIER.value,
                ModelType.LIGHTGBM_CLASSIFIER.value,
            ]:
                try:
                    result = await self.train_single_model(X_train, y_train, model_type)
                    single_model_results[model_type] = result
                except Exception as e:
                    self.logger.warning(f"Failed to train {model_type}: {e}")
                    single_model_results[model_type] = {
                        "success": False,
                        "error": str(e),
                    }

            # 5. 训练集成模型
            try:
                ensemble_result = await self.train_ensemble_models(X_train, y_train)
            except Exception as e:
                self.logger.warning(f"Failed to train ensemble model: {e}")
                ensemble_result = {"success": False, "error": str(e)}

            # 6. 运行AutoML
            try:
                automl_result = await self.run_automl(X_train, y_train)
            except Exception as e:
                self.logger.warning(f"AutoML failed: {e}")
                automl_result = {"success": False, "error": str(e)}

            # 7. 模型比较
            comparison_result = await self.compare_models(X_test, y_test)

            # 8. 保存训练历史
            training_record = {
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
                "data_info": {
                    "total_matches": len(matches),
                    "features_count": len(feature_columns),
                    "training_samples": len(X_train),
                    "test_samples": len(X_test),
                },
                "single_models": single_model_results,
                "ensemble_model": ensemble_result,
                "automl_result": automl_result,
                "comparison": comparison_result,
                "feature_columns": feature_columns,
            }

            self.training_history.append(training_record)

            # 保存训练历史
            history_path = (
                self.models_dir
                / f"training_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(history_path, "w") as f:
                json.dump(training_record, f, indent=2, default=str)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "success": True,
                "pipeline_completed": True,
                "duration": duration,
                "models_trained": list(self.models.keys()),
                "best_model": comparison_result.get("best_model", {}).get("name"),
                "best_accuracy": comparison_result.get("best_model", {}).get("accuracy"),
                "training_record": training_record,
                "models_directory": str(self.models_dir),
            }

            self.logger.info(f"Complete training pipeline finished in {duration:.2f} seconds")
            self.logger.info(
                f"Best model: {result['best_model']} with accuracy {result['best_accuracy']:.4f}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Training pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

    def get_training_summary(self) -> Dict[str, Any]:
        """获取训练摘要"""
        if not self.training_history:
            return {"status": "No training history available"}

        latest_training = self.training_history[-1]

        return {
            "total_training_runs": len(self.training_history),
            "latest_training": latest_training,
            "available_models": list(self.models.keys()),
            "models_directory": str(self.models_dir),
        }


# 便捷函数
async def train_football_prediction_model(
    matches: Optional[List[MatchResult]] = None,
    config: Dict[str, Any] = None,
    use_sample_data: bool = True,
) -> Dict[str, Any]:
    """
    训练足球预测模型的便捷函数

    Args:
        matches: 比赛数据
        config: 训练配置
        use_sample_data: 是否使用示例数据

    Returns:
        训练结果
    """
    pipeline = RealModelTrainingPipeline(config)
    return await pipeline.run_complete_training_pipeline(matches, use_sample_data=use_sample_data)


# 主函数示例
async def main():
    """主函数示例"""
    logger.info("Starting real model training example...")

    # 运行训练管道
    result = await train_football_prediction_model(use_sample_data=True)

    if result["success"]:
        logger.info("Training completed successfully!")
        logger.info(f"Best model: {result['best_model']}")
        logger.info(f"Best accuracy: {result['best_accuracy']:.4f}")
        logger.info(f"Models saved to: {result['models_directory']}")
    else:
        logger.error(f"Training failed: {result['error']}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
