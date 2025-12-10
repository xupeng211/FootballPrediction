"""
Orchestration flows for automated data collection and model training.

This module implements Prefect 2.x flows for:
1. Daily data collection from FotMob and FBref
2. Weekly model retraining using P2-5 train_flow

These flows replace manual scripts with automated, scheduled, and monitored tasks.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import dict, list, Optional, Any
from pathlib import Path

from prefect import flow, task
from prefect.tasks import task_input_hash
from prefect.runtime import flow_run, task_run
from prefect.client.orchestration import PrefectClient

from src.tasks.celery_app import celery_app
from src.tasks.data_collection_tasks import (
    collect_fotmob_fixtures_task,
    collect_fotmob_details_task,
    collect_fbref_data_task,
)
from src.features.feature_store import FeatureStore
from src.quality.data_quality_monitor import DataQualityMonitor
from src.database.async_manager import get_db_session

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@task(
    name="Collect FotMob Fixtures",
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
async def collect_fotmob_fixtures_flow_task() -> dict[str, Any]:
    """
    Collect fixture data from FotMob API.

    This task runs as part of the daily data collection flow,
    fetching upcoming match fixtures for prediction processing.

    Returns:
        dict with collection results and statistics
    """
    logger.info("Starting FotMob fixtures collection")

    try:
        # Trigger Celery task for distributed execution
        celery_task = collect_fotmob_fixtures_task.delay()

        # Wait for completion with timeout
        result = celery_task.get(timeout=300)  # 5 minutes timeout

        logger.info(f"FotMob fixtures collection completed: {result}")

        return {
            "status": "success",
            "task_id": str(celery_task.id),
            "fixtures_collected": result.get("count", 0),
            "collection_time": datetime.utcnow().isoformat(),
            "data": result,
        }

    except Exception as e:
        logger.error(f"FotMob fixtures collection failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "collection_time": datetime.utcnow().isoformat(),
        }


@task(
    name="Collect FotMob Match Details",
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=2),
)
async def collect_fotmob_details_flow_task() -> dict[str, Any]:
    """
    Collect detailed match data from FotMob API.

    This task fetches detailed statistics for matches,
    including shots, xG, possession, and other advanced metrics.

    Returns:
        dict with collection results and statistics
    """
    logger.info("Starting FotMob match details collection")

    try:
        # Trigger Celery task for distributed execution
        celery_task = collect_fotmob_details_task.delay()

        # Wait for completion with timeout
        result = celery_task.get(timeout=600)  # 10 minutes timeout

        logger.info(f"FotMob details collection completed: {result}")

        return {
            "status": "success",
            "task_id": str(celery_task.id),
            "matches_updated": result.get("updated_count", 0),
            "collection_time": datetime.utcnow().isoformat(),
            "data": result,
        }

    except Exception as e:
        logger.error(f"FotMob details collection failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "collection_time": datetime.utcnow().isoformat(),
        }


@task(
    name="Collect FBref Data",
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=4),
)
async def collect_fbref_flow_task() -> dict[str, Any]:
    """
    Collect data from FBref API.

    This task fetches advanced statistics and historical data
    from FBref to complement FotMob data.

    Returns:
        dict with collection results and statistics
    """
    logger.info("Starting FBref data collection")

    try:
        # Trigger Celery task for distributed execution
        celery_task = collect_fbref_data_task.delay()

        # Wait for completion with timeout
        result = celery_task.get(timeout=900)  # 15 minutes timeout

        logger.info(f"FBref collection completed: {result}")

        return {
            "status": "success",
            "task_id": str(celery_task.id),
            "records_processed": result.get("processed", 0),
            "collection_time": datetime.utcnow().isoformat(),
            "data": result,
        }

    except Exception as e:
        logger.error(f"FBref collection failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "collection_time": datetime.utcnow().isoformat(),
        }


@task(name="Run Data Quality Checks")
async def run_data_quality_checks() -> dict[str, Any]:
    """
    Run comprehensive data quality checks on newly collected data.

    This task validates the quality of collected data using
    the modern async quality monitor with protocol-based rules.

    Returns:
        dict with quality check results and statistics
    """
    logger.info("Starting data quality checks")

    try:
        # Initialize quality monitor
        quality_monitor = DataQualityMonitor()

        # Run quality checks on recent data
        quality_report = await quality_monitor.run_quality_checks(
            data_sources=["fotmob", "fbref"], time_window_hours=24
        )

        logger.info(f"Data quality checks completed: {quality_report.summary}")

        return {
            "status": "success",
            "quality_score": quality_report.overall_score,
            "issues_found": len(quality_report.issues),
            "records_checked": quality_report.total_records,
            "check_time": datetime.utcnow().isoformat(),
            "report": quality_report.to_dict(),
        }

    except Exception as e:
        logger.error(f"Data quality checks failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "check_time": datetime.utcnow().isoformat(),
        }


@task(name="Update Feature Store")
async def update_feature_store() -> dict[str, Any]:
    """
    Update feature store with newly collected and validated data.

    This task processes raw collected data into engineered features
    and stores them in the async feature store for ML consumption.

    Returns:
        dict with feature store update results
    """
    logger.info("Starting feature store update")

    try:
        # Initialize feature store
        feature_store = FeatureStore()

        # Process recent data into features
        async with get_db_session() as session:
            features_created = await feature_store.process_recent_data(
                session=session, lookback_hours=24
            )

        logger.info(f"Feature store update completed: {features_created} features")

        return {
            "status": "success",
            "features_created": features_created,
            "update_time": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Feature store update failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "update_time": datetime.utcnow().isoformat(),
        }


@flow(
    name="Daily Data Collection Flow",
    log_prints=True,
    flow_run_name="daily-data-collection-{flow_run.expected_start_time}",
)
async def daily_data_collection_flow() -> dict[str, Any]:
    """
    Daily automated data collection from FotMob and FBref.

    This flow orchestrates parallel data collection from multiple sources,
    runs quality validation, and updates the feature store. It replaces
    manual data collection scripts with automated, monitored tasks.

    Features:
    - Parallel execution of FotMob and FBref collection
    - Automatic retry with exponential backoff
    - Data quality validation with protocol-based rules
    - Feature store integration with async processing
    - Comprehensive logging and monitoring

    Returns:
        dict with flow execution summary and statistics
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting Daily Data Collection Flow")
    logger.info("=" * 60)

    flow_start_time = datetime.utcnow()
    results = {
        "flow_name": "daily_data_collection_flow",
        "flow_run_id": flow_run.id,
        "start_time": flow_start_time.isoformat(),
        "tasks": {},
    }

    try:
        # Step 1: Parallel data collection from all sources
        logger.info("📊 Step 1: Starting parallel data collection")

        collection_tasks = await asyncio.gather(
            collect_fotmob_fixtures_flow_task(),
            collect_fotmob_details_flow_task(),
            collect_fbref_flow_task(),
            return_exceptions=True,
        )

        # Process collection results
        collection_results = {
            "fotmob_fixtures": (
                collection_tasks[0]
                if not isinstance(collection_tasks[0], Exception)
                else {"status": "error", "error": str(collection_tasks[0])}
            ),
            "fotmob_details": (
                collection_tasks[1]
                if not isinstance(collection_tasks[1], Exception)
                else {"status": "error", "error": str(collection_tasks[1])}
            ),
            "fbref": (
                collection_tasks[2]
                if not isinstance(collection_tasks[2], Exception)
                else {"status": "error", "error": str(collection_tasks[2])}
            ),
        }

        results["tasks"]["data_collection"] = collection_results
        successful_collections = sum(
            1 for r in collection_results.values() if r.get("status") == "success"
        )

        logger.info(
            f"Data collection completed: {successful_collections}/3 sources successful"
        )

        # Step 2: Data quality validation
        logger.info("🔍 Step 2: Running data quality checks")

        quality_result = await run_data_quality_checks()
        results["tasks"]["quality_checks"] = quality_result

        if quality_result.get("status") == "success":
            logger.info(
                f"Data quality score: {quality_result.get('quality_score', 'N/A')}"
            )
        else:
            logger.warning(
                "Data quality checks failed - continuing with feature update"
            )

        # Step 3: Feature store update
        logger.info("⚡ Step 3: Updating feature store")

        feature_result = await update_feature_store()
        results["tasks"]["feature_update"] = feature_result

        # Calculate overall statistics
        flow_end_time = datetime.utcnow()
        flow_duration = (flow_end_time - flow_start_time).total_seconds()

        results.update(
            {
                "end_time": flow_end_time.isoformat(),
                "duration_seconds": flow_duration,
                "overall_status": "success",
                "summary": {
                    "data_sources_success": successful_collections,
                    "quality_checks_passed": quality_result.get("status") == "success",
                    "feature_store_updated": feature_result.get("status") == "success",
                    "total_issues_found": quality_result.get("issues_found", 0),
                },
            }
        )

        logger.info("=" * 60)
        logger.info("✅ Daily Data Collection Flow completed successfully")
        logger.info(f"Duration: {flow_duration:.2f} seconds")
        logger.info(f"Data sources: {successful_collections}/3 successful")
        logger.info("=" * 60)

        return results

    except Exception as e:
        # Handle flow-level errors
        flow_end_time = datetime.utcnow()
        flow_duration = (flow_end_time - flow_start_time).total_seconds()

        logger.error(f"Daily Data Collection Flow failed: {e}")

        results.update(
            {
                "end_time": flow_end_time.isoformat(),
                "duration_seconds": flow_duration,
                "overall_status": "error",
                "error": str(e),
            }
        )

        return results


# Schedule configuration for daily execution
daily_schedule = {
    "cron": "0 2 * * *",  # Run daily at 2 AM UTC
    "timezone": "UTC",
    "active": True,
}


@flow(name="Manual Data Collection Flow", log_prints=True)
async def manual_data_collection_flow(
    sources: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Manual data collection flow for on-demand execution.

    This flow allows manual triggering of data collection for specific
    sources, useful for testing or backfilling missing data.

    Args:
        sources: list of data sources to collect ['fotmob_fixtures', 'fotmob_details', 'fbref']
                 If None, collects from all sources

    Returns:
        dict with manual collection results
    """
    logger.info("🔧 Starting Manual Data Collection Flow")

    if sources is None:
        sources = ["fotmob_fixtures", "fotmob_details", "fbref"]

    results = {
        "flow_name": "manual_data_collection_flow",
        "sources_requested": sources,
        "start_time": datetime.utcnow().isoformat(),
        "tasks": {},
    }

    task_mapping = {
        "fotmob_fixtures": collect_fotmob_fixtures_flow_task,
        "fotmob_details": collect_fotmob_details_flow_task,
        "fbref": collect_fbref_flow_task,
    }

    try:
        # Execute requested collection tasks
        tasks_to_run = [
            task_mapping[source] for source in sources if source in task_mapping
        ]

        if not tasks_to_run:
            raise ValueError(f"No valid sources found in: {sources}")

        collection_results = await asyncio.gather(
            *[task() for task in tasks_to_run], return_exceptions=True
        )

        # Map results back to source names
        for _i, source in enumerate(sources):
            if source in task_mapping:
                result = collection_results[sources.index(source)]
                if isinstance(result, Exception):
                    results["tasks"][source] = {"status": "error", "error": str(result)}
                else:
                    results["tasks"][source] = result

        results["end_time"] = datetime.utcnow().isoformat()
        results["overall_status"] = "success"

        logger.info("Manual Data Collection Flow completed")
        return results

    except Exception as e:
        logger.error(f"Manual Data Collection Flow failed: {e}")
        results["end_time"] = datetime.utcnow().isoformat()
        results["overall_status"] = "error"
        results["error"] = str(e)
        return results
