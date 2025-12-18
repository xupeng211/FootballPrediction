"""
Weekly model retraining flow for automated ML pipeline execution.

This module implements the weekly model retraining using P2-5 train_flow,
integrating with the existing ML infrastructure for continuous model improvement.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Any

from prefect import flow, task
from prefect.tasks import task_input_hash
from prefect.runtime import flow_run

# Import P2-5 training infrastructure
from src.ml.enhanced_xgboost_trainer import EnhancedXGBoostTrainer
from src.ml.football_prediction_pipeline import FootballPredictionPipeline
from src.ml.enhanced_feature_engineering import EnhancedFeatureEngineering
from src.features.feature_store import FeatureStore
from src.services.inference_service import get_inference_service
from src.database.async_manager import get_db_session
from src.quality.data_quality_monitor import DataQualityMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@task(
    name="Validate Training Data Quality",
    retries=2,
    retry_delay_seconds=300,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=6),
)
async def validate_training_data_quality(lookback_days: int = 30) -> dict[str, Any]:
    """
    Validate the quality of training data before model retraining.

    This task ensures that the data meets quality thresholds for
    reliable model training using the modern quality monitor.

    Args:
        lookback_days: Number of days to look back for training data

    Returns:
        dict with validation results and quality metrics
    """
    logger.info(
        f"Starting training data quality validation (last {lookback_days} days)"
    )

    try:
        # Initialize quality monitor
        quality_monitor = DataQualityMonitor()

        # Run comprehensive quality checks on training data
        quality_report = await quality_monitor.run_training_data_validation(
            lookback_days=lookback_days
        )

        # Determine if data quality is sufficient for training
        min_quality_score = 0.85  # Minimum quality threshold
        is_suitable = quality_report.overall_score >= min_quality_score

        logger.info("Training data validation completed:")
        logger.info(f"  Overall quality score: {quality_report.overall_score:.3f}")
        logger.info(f"  Records validated: {quality_report.total_records}")
        logger.info(f"  Issues found: {len(quality_report.issues)}")
        logger.info(f"  Suitable for training: {is_suitable}")

        return {
            "status": "success",
            "validation_time": datetime.utcnow().isoformat(),
            "quality_score": quality_report.overall_score,
            "min_quality_threshold": min_quality_score,
            "records_validated": quality_report.total_records,
            "issues_found": len(quality_report.issues),
            "is_suitable_for_training": is_suitable,
            "quality_issues": [issue.to_dict() for issue in quality_report.issues],
            "report": quality_report.to_dict(),
        }

    except Exception as e:
        logger.error(f"Training data quality validation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "validation_time": datetime.utcnow().isoformat(),
            "is_suitable_for_training": False,
        }


@task(name="Prepare Training Features", retries=2, retry_delay_seconds=300)
async def prepare_training_features(
    lookback_days: int = 30, feature_version: str = "latest"
) -> dict[str, Any]:
    """
    Prepare training features from the feature store.

    This task extracts and prepares features for model training,
    ensuring consistency between training and inference.

    Args:
        lookback_days: Number of days to look back for training data
        feature_version: Version of features to use

    Returns:
        dict with feature preparation results
    """
    logger.info(f"Preparing training features (last {lookback_days} days)")

    try:
        # Initialize feature store and feature engineering
        feature_store = FeatureStore()
        feature_engineering = EnhancedFeatureEngineering()

        # Extract training data from feature store
        async with get_db_session() as session:
            training_data = await feature_store.extract_training_data(
                session=session,
                lookback_days=lookback_days,
                feature_version=feature_version,
            )

        # Apply advanced feature engineering
        engineered_features = await feature_engineering.engineer_training_features(
            raw_data=training_data
        )

        # Split into features and target
        X = engineered_features["features"]
        y = engineered_features["target"]

        logger.info("Feature preparation completed:")
        logger.info(f"  Training samples: {len(X)}")
        logger.info(
            f"  Feature count: {X.shape[1] if hasattr(X, 'shape') else len(X[0])}"
        )
        logger.info(
            f"  Target distribution: {y.value_counts().to_dict() if hasattr(y, 'value_counts') else 'N/A'}"
        )

        return {
            "status": "success",
            "preparation_time": datetime.utcnow().isoformat(),
            "training_samples": len(X),
            "feature_count": (
                X.shape[1] if hasattr(X, "shape") else len(X[0]) if X else 0
            ),
            "feature_version": feature_version,
            "lookback_days": lookback_days,
            "feature_names": list(X.columns) if hasattr(X, "columns") else [],
            "data": {
                "features": X,
                "target": y,
                "metadata": engineered_features.get("metadata", {}),
            },
        }

    except Exception as e:
        logger.error(f"Feature preparation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "preparation_time": datetime.utcnow().isoformat(),
        }


@task(name="Train XGBoost Model", retries=1, retry_delay_seconds=600)
async def train_xgboost_model(
    training_data: dict[str, Any],
    model_params: Optional[dict[str, Any]] = None,
    experiment_name: str = "weekly_retraining",
) -> dict[str, Any]:
    """
    Train XGBoost model using P2-5 training infrastructure.

    This task leverages the enhanced XGBoost trainer from P2-5
    with hyperparameter optimization and MLflow tracking.

    Args:
        training_data: Dictionary with features and target
        model_params: Optional model hyperparameters
        experiment_name: MLflow experiment name

    Returns:
        dict with training results and model information
    """
    logger.info("Starting XGBoost model training")

    try:
        # Initialize enhanced XGBoost trainer
        trainer = EnhancedXGBoostTrainer(
            experiment_name=experiment_name, use_hyperparameter_optimization=True
        )

        # Extract features and target
        X = training_data["data"]["features"]
        y = training_data["data"]["target"]
        metadata = training_data["data"].get("metadata", {})

        # Train the model with automatic hyperparameter optimization
        training_result = await trainer.train_with_optimization(
            X=X, y=y, cv_folds=5, n_trials=50, timeout_hours=2
        )

        # Save the trained model
        model_path = await trainer.save_model(
            model_version=f"weekly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        logger.info("XGBoost training completed:")
        logger.info(f"  Best score: {training_result.best_score:.4f}")
        logger.info(f"  Best params: {training_result.best_params}")
        logger.info(f"  Model saved to: {model_path}")

        return {
            "status": "success",
            "training_time": datetime.utcnow().isoformat(),
            "experiment_name": experiment_name,
            "best_score": training_result.best_score,
            "best_params": training_result.best_params,
            "model_path": model_path,
            "training_samples": len(X),
            "feature_count": (
                X.shape[1] if hasattr(X, "shape") else len(X[0]) if X else 0
            ),
            "cv_folds": 5,
            "optimization_trials": training_result.n_trials,
            "mlflow_run_id": training_result.run_id,
            "model_metadata": metadata,
        }

    except Exception as e:
        logger.error(f"XGBoost model training failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "training_time": datetime.utcnow().isoformat(),
        }


@task(name="Evaluate Model Performance", retries=1, retry_delay_seconds=300)
async def evaluate_model_performance(
    model_path: str, test_data_lookback_days: int = 7
) -> dict[str, Any]:
    """
    Evaluate the trained model performance on recent test data.

    This task validates model performance against recent data
    to ensure the model generalizes well.

    Args:
        model_path: Path to the trained model file
        test_data_lookback_days: Number of days to use for test data

    Returns:
        dict with evaluation results and performance metrics
    """
    logger.info(
        f"Evaluating model performance (test data: last {test_data_lookback_days} days)"
    )

    try:
        # Initialize prediction pipeline for evaluation
        pipeline = FootballPredictionPipeline()

        # Load the trained model
        model_loaded = await pipeline.load_model(model_path)
        if not model_loaded:
            raise ValueError(f"Failed to load model from {model_path}")

        # Prepare test data
        async with get_db_session() as session:
            test_data = await pipeline.prepare_test_data(
                session=session, lookback_days=test_data_lookback_days
            )

        # Evaluate model performance
        evaluation_results = await pipeline.evaluate_model(
            test_data=test_data,
            metrics=["accuracy", "precision", "recall", "f1", "roc_auc"],
        )

        logger.info("Model evaluation completed:")
        for metric, value in evaluation_results["metrics"].items():
            logger.info(f"  {metric}: {value:.4f}")

        return {
            "status": "success",
            "evaluation_time": datetime.utcnow().isoformat(),
            "model_path": model_path,
            "test_samples": evaluation_results.get("test_samples", 0),
            "metrics": evaluation_results["metrics"],
            "confusion_matrix": evaluation_results.get("confusion_matrix"),
            "classification_report": evaluation_results.get("classification_report"),
            "passes_performance_threshold": evaluation_results.get("accuracy", 0) > 0.6,
        }

    except Exception as e:
        logger.error(f"Model evaluation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "evaluation_time": datetime.utcnow().isoformat(),
        }


@task(name="Update Inference Service")
async def update_inference_service(
    model_path: str, model_version: str, performance_metrics: dict[str, float]
) -> dict[str, Any]:
    """
    Update the inference service with the new model.

    This task updates the production inference service to use
    the newly trained model if it meets performance criteria.

    Args:
        model_path: Path to the trained model file
        model_version: Version identifier for the model
        performance_metrics: Model performance metrics

    Returns:
        dict with service update results
    """
    logger.info(f"Updating inference service with model: {model_version}")

    try:
        # Get inference service instance
        inference_service = await get_inference_service()

        # Check if model meets performance criteria
        min_accuracy = 0.6  # Minimum accuracy threshold
        model_accuracy = performance_metrics.get("accuracy", 0)

        if model_accuracy < min_accuracy:
            logger.warning(
                f"Model accuracy {model_accuracy:.3f} below threshold {min_accuracy}"
            )
            return {
                "status": "skipped",
                "reason": f"Model accuracy {model_accuracy:.3f} below threshold {min_accuracy}",
                "update_time": datetime.utcnow().isoformat(),
            }

        # Update inference service with new model
        await inference_service.update_model(
            model_path=model_path,
            model_version=model_version,
            performance_metrics=performance_metrics,
        )

        logger.info("Inference service updated successfully:")
        logger.info(f"  Model version: {model_version}")
        logger.info(f"  Update time: {datetime.utcnow().isoformat()}")

        return {
            "status": "success",
            "update_time": datetime.utcnow().isoformat(),
            "model_version": model_version,
            "model_path": model_path,
            "performance_metrics": performance_metrics,
            "service_health": inference_service.health_check(),
        }

    except Exception as e:
        logger.error(f"Inference service update failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "update_time": datetime.utcnow().isoformat(),
        }


@flow(
    name="Weekly Model Retraining Flow",
    log_prints=True,
    flow_run_name="weekly-model-retraining-{flow_run.expected_start_time}",
)
async def weekly_model_retraining_flow(
    lookback_days: int = 30,
    experiment_name: str = "weekly_retraining",
    force_retrain: bool = False,
) -> dict[str, Any]:
    """
    Weekly automated model retraining using P2-5 training infrastructure.

    This flow orchestrates the complete ML pipeline:
    1. Data quality validation
    2. Feature preparation
    3. Model training with hyperparameter optimization
    4. Model evaluation
    5. Production service update

    The flow integrates with P2-5 training infrastructure and maintains
    consistency between training and inference.

    Args:
        lookback_days: Number of days to look back for training data
        experiment_name: MLflow experiment name
        force_retrain: Force retraining even if data quality is marginal

    Returns:
        dict with flow execution summary and results
    """
    logger.info("=" * 60)
    logger.info("🧠 Starting Weekly Model Retraining Flow")
    logger.info("=" * 60)

    flow_start_time = datetime.utcnow()
    results = {
        "flow_name": "weekly_model_retraining_flow",
        "flow_run_id": flow_run.id,
        "start_time": flow_start_time.isoformat(),
        "parameters": {
            "lookback_days": lookback_days,
            "experiment_name": experiment_name,
            "force_retrain": force_retrain,
        },
        "tasks": {},
    }

    try:
        # Step 1: Validate training data quality
        logger.info("🔍 Step 1: Validating training data quality")

        quality_result = await validate_training_data_quality(
            lookback_days=lookback_days
        )
        results["tasks"]["data_quality_validation"] = quality_result

        if not quality_result.get("is_suitable_for_training") and not force_retrain:
            logger.warning("Training data quality insufficient, skipping retraining")
            results["overall_status"] = "skipped"
            results["reason"] = "Training data quality below threshold"
            return results

        # Step 2: Prepare training features
        logger.info("⚡ Step 2: Preparing training features")

        feature_result = await prepare_training_features(lookback_days=lookback_days)
        results["tasks"]["feature_preparation"] = feature_result

        if feature_result.get("status") != "success":
            raise ValueError("Feature preparation failed")

        # Step 3: Train XGBoost model
        logger.info("🎯 Step 3: Training XGBoost model")

        training_result = await train_xgboost_model(
            training_data=feature_result, experiment_name=experiment_name
        )
        results["tasks"]["model_training"] = training_result

        if training_result.get("status") != "success":
            raise ValueError("Model training failed")

        model_path = training_result["model_path"]
        model_version = f"weekly_{flow_start_time.strftime('%Y%m%d_%H%M%S')}"

        # Step 4: Evaluate model performance
        logger.info("📊 Step 4: Evaluating model performance")

        evaluation_result = await evaluate_model_performance(
            model_path=model_path, test_data_lookback_days=7
        )
        results["tasks"]["model_evaluation"] = evaluation_result

        if evaluation_result.get("status") != "success":
            logger.warning(
                "Model evaluation failed, but continuing with service update"
            )

        # Step 5: Update inference service
        logger.info("🚀 Step 5: Updating inference service")

        performance_metrics = evaluation_result.get("metrics", {})
        service_result = await update_inference_service(
            model_path=model_path,
            model_version=model_version,
            performance_metrics=performance_metrics,
        )
        results["tasks"]["service_update"] = service_result

        # Calculate flow statistics
        flow_end_time = datetime.utcnow()
        flow_duration = (flow_end_time - flow_start_time).total_seconds()

        results.update(
            {
                "end_time": flow_end_time.isoformat(),
                "duration_seconds": flow_duration,
                "overall_status": "success",
                "summary": {
                    "data_quality_score": quality_result.get("quality_score", 0),
                    "training_samples": feature_result.get("training_samples", 0),
                    "feature_count": feature_result.get("feature_count", 0),
                    "model_accuracy": performance_metrics.get("accuracy", 0),
                    "best_cv_score": training_result.get("best_score", 0),
                    "service_updated": service_result.get("status") == "success",
                    "model_version": model_version,
                },
            }
        )

        logger.info("=" * 60)
        logger.info("✅ Weekly Model Retraining Flow completed successfully")
        logger.info(f"Duration: {flow_duration:.2f} seconds")
        logger.info(f"Model accuracy: {performance_metrics.get('accuracy', 0):.3f}")
        logger.info(f"Model version: {model_version}")
        logger.info("=" * 60)

        return results

    except Exception as e:
        # Handle flow-level errors
        flow_end_time = datetime.utcnow()
        flow_duration = (flow_end_time - flow_start_time).total_seconds()

        logger.error(f"Weekly Model Retraining Flow failed: {e}")

        results.update(
            {
                "end_time": flow_end_time.isoformat(),
                "duration_seconds": flow_duration,
                "overall_status": "error",
                "error": str(e),
            }
        )

        return results


# Schedule configuration for weekly execution
weekly_schedule = {
    "cron": "0 3 * * 1",  # Run weekly on Monday at 3 AM UTC
    "timezone": "UTC",
    "active": True,
}


@flow(name="Emergency Model Retraining Flow", log_prints=True)
async def emergency_model_retraining_flow(
    reason: str = "performance_degradation", lookback_days: int = 14
) -> dict[str, Any]:
    """
    Emergency model retraining for urgent situations.

    This flow is designed for rapid model retraining in response
    to performance degradation or data drift issues.

    Args:
        reason: Reason for emergency retraining
        lookback_days: Reduced lookback period for faster training

    Returns:
        dict with emergency retraining results
    """
    logger.info(f"🚨 Starting Emergency Model Retraining Flow - Reason: {reason}")

    return await weekly_model_retraining_flow(
        lookback_days=lookback_days,
        experiment_name=f"emergency_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        force_retrain=True,
    )
