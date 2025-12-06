"""
Prefect Flow Scheduler for Celery Beat Integration.

This module provides a custom Celery Beat scheduler that can trigger
Prefect flows, enabling seamless integration between Celery's robust
scheduling capabilities and Prefect's advanced flow orchestration.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from celery import schedules
from celery.schedules import crontab
from celery.beat import Scheduler

from prefect.client.orchestration import PrefectClient
from prefect.deployments import run_deployment
from prefect.flows import load_flow_from_script
from prefect.exceptions import ObjectNotFound

from src.orchestration.flows.daily_data_collection_flow import daily_data_collection_flow, manual_data_collection_flow
from src.orchestration.flows.weekly_model_retraining_flow import weekly_model_retraining_flow, emergency_model_retraining_flow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PrefectFlowScheduler(Scheduler):
    """
    Custom Celery Beat scheduler that triggers Prefect flows.

    This scheduler extends Celery Beat to orchestrate Prefect flows,
    combining Celery's reliable scheduling with Prefect's advanced
    flow management, retry logic, and monitoring capabilities.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefect_client = None
        self._prefect_client_initialized = False

    async def _get_prefect_client(self) -> PrefectClient:
        """Get or create Prefect client."""
        if not self._prefect_client_initialized or self.prefect_client is None:
            try:
                self.prefect_client = PrefectClient()
                await self.prefect_client.__aenter__()
                self._prefect_client_initialized = True
                logger.info("Prefect client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Prefect client: {e}")
                raise
        return self.prefect_client

    def setup_schedule(self):
        """Setup the schedule with Prefect flow triggers."""
        logger.info("Setting up Prefect Flow Scheduler")

        # Daily data collection flow - runs every day at 2 AM UTC
        self.schedule['daily-data-collection'] = {
            'task': 'src.tasks.scheduler_prefect.trigger_prefect_flow',
            'schedule': crontab(minute=0, hour=2),  # 2 AM UTC daily
            'args': ('daily_data_collection_flow',),
            'kwargs': {},
            'options': {
                'queue': 'scheduler',
                'priority': 5,
                'expires': 3600  # 1 hour expiration
            }
        }

        # Weekly model retraining flow - runs every Monday at 3 AM UTC
        self.schedule['weekly-model-retraining'] = {
            'task': 'src.tasks.scheduler_prefect.trigger_prefect_flow',
            'schedule': crontab(minute=0, hour=3, day_of_week=1),  # Monday 3 AM UTC
            'args': ('weekly_model_retraining_flow',),
            'kwargs': {
                'lookback_days': 30,
                'experiment_name': 'weekly_retraining',
                'force_retrain': False
            },
            'options': {
                'queue': 'scheduler',
                'priority': 8,
                'expires': 7200  # 2 hour expiration
            }
        }

        # Emergency retraining check - runs every 6 hours
        self.schedule['emergency-retraining-check'] = {
            'task': 'src.tasks.scheduler_prefect.check_model_performance',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
            'args': (),
            'kwargs': {},
            'options': {
                'queue': 'scheduler',
                'priority': 9,
                'expires': 1800  # 30 minute expiration
            }
        }

        # Data quality monitoring - runs every 4 hours
        self.schedule['data-quality-monitoring'] = {
            'task': 'src.tasks.scheduler_prefect.monitor_data_quality',
            'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
            'args': (),
            'kwargs': {},
            'options': {
                'queue': 'scheduler',
                'priority': 6,
                'expires': 1200  # 20 minute expiration
            }
        }

        logger.info(f"Scheduler setup complete with {len(self.schedule)} scheduled tasks")

    async def trigger_prefect_flow(
        self,
        flow_name: str,
        flow_args: tuple = (),
        flow_kwargs: dict = None,
        deployment_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger a Prefect flow execution.

        Args:
            flow_name: Name of the flow to trigger
            flow_args: Positional arguments for the flow
            flow_kwargs: Keyword arguments for the flow
            deployment_name: Optional deployment name to use

        Returns:
            Dict with trigger results
        """
        logger.info(f"Triggering Prefect flow: {flow_name}")

        if flow_kwargs is None:
            flow_kwargs = {}

        try:
            client = await self._get_prefect_client()

            # Try to run via deployment first (preferred method)
            if deployment_name:
                try:
                    flow_run_id = await run_deployment(
                        name=deployment_name,
                        parameters=flow_kwargs,
                        timeout=30
                    )
                    logger.info(f"Flow triggered via deployment: {deployment_name}, run_id: {flow_run_id}")
                    return {
                        "status": "success",
                        "flow_name": flow_name,
                        "deployment_name": deployment_name,
                        "flow_run_id": flow_run_id,
                        "trigger_method": "deployment"
                    }
                except ObjectNotFound:
                    logger.warning(f"Deployment {deployment_name} not found, falling back to direct flow execution")

            # Fallback to direct flow execution
            flow_module_map = {
                "daily_data_collection_flow": "src.orchestration.flows.daily_data_collection_flow:daily_data_collection_flow",
                "weekly_model_retraining_flow": "src.orchestration.flows.weekly_model_retraining_flow:weekly_model_retraining_flow",
                "manual_data_collection_flow": "src.orchestration.flows.daily_data_collection_flow:manual_data_collection_flow",
                "emergency_model_retraining_flow": "src.orchestration.flows.weekly_model_retraining_flow:emergency_model_retraining_flow"
            }

            if flow_name not in flow_module_map:
                raise ValueError(f"Unknown flow: {flow_name}")

            flow_path = flow_module_map[flow_name]
            flow = await load_flow_from_script(flow_path)

            # Create flow run
            flow_run = await client.create_flow_run_from_flow(
                flow=flow,
                parameters=flow_kwargs,
                name=f"scheduled-{flow_name}-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )

            logger.info(f"Flow triggered directly: {flow_name}, run_id: {flow_run.id}")

            return {
                "status": "success",
                "flow_name": flow_name,
                "flow_run_id": str(flow_run.id),
                "trigger_method": "direct",
                "flow_url": f"http://localhost:4200/flow-run/{flow_run.id}"
            }

        except Exception as e:
            logger.error(f"Failed to trigger Prefect flow {flow_name}: {e}")
            return {
                "status": "error",
                "flow_name": flow_name,
                "error": str(e),
                "trigger_method": "failed"
            }

    async def check_model_performance(self) -> Dict[str, Any]:
        """
        Check model performance and trigger emergency retraining if needed.

        This task monitors model performance metrics and can trigger
        emergency retraining if performance degrades below thresholds.

        Returns:
            Dict with performance check results
        """
        logger.info("Checking model performance for emergency retraining")

        try:
            from src.services.inference_service import get_inference_service
            from src.ml.model_performance_monitor import ModelPerformanceMonitor

            # Get current model performance
            inference_service = await get_inference_service()
            performance_monitor = ModelPerformanceMonitor()

            # Check recent performance
            performance_data = await performance_monitor.check_recent_performance(
                lookback_hours=6
            )

            # Determine if emergency retraining is needed
            accuracy_threshold = 0.6  # Minimum acceptable accuracy
            current_accuracy = performance_data.get("accuracy", 1.0)

            needs_retraining = current_accuracy < accuracy_threshold
            reason = f"Accuracy {current_accuracy:.3f} below threshold {accuracy_threshold}" if needs_retraining else "Performance acceptable"

            if needs_retraining:
                logger.warning(f"Triggering emergency retraining: {reason}")
                result = await self.trigger_prefect_flow(
                    "emergency_model_retraining_flow",
                    flow_kwargs={
                        "reason": "performance_degradation",
                        "lookback_days": 14
                    }
                )
                result["retraining_triggered"] = True
                result["retraining_reason"] = reason
            else:
                logger.info(f"Model performance acceptable: {reason}")
                result = {
                    "status": "success",
                    "retraining_triggered": False,
                    "current_accuracy": current_accuracy,
                    "reason": reason
                }

            return result

        except Exception as e:
            logger.error(f"Model performance check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "retraining_triggered": False
            }

    async def monitor_data_quality(self) -> Dict[str, Any]:
        """
        Monitor data quality and trigger data collection if needed.

        This task monitors data quality metrics and can trigger
        additional data collection if quality degrades.

        Returns:
            Dict with quality monitoring results
        """
        logger.info("Monitoring data quality")

        try:
            from src.quality.data_quality_monitor import DataQualityMonitor

            quality_monitor = DataQualityMonitor()

            # Run quality checks on recent data
            quality_report = await quality_monitor.run_quality_checks(
                data_sources=["fotmob", "fbref"],
                time_window_hours=4
            )

            # Determine if additional data collection is needed
            quality_threshold = 0.8  # Minimum acceptable quality score
            current_score = quality_report.overall_score

            needs_collection = current_score < quality_threshold
            reason = f"Quality score {current_score:.3f} below threshold {quality_threshold}" if needs_collection else "Data quality acceptable"

            if needs_collection:
                logger.warning(f"Triggering additional data collection: {reason}")
                result = await self.trigger_prefect_flow(
                    "manual_data_collection_flow",
                    flow_kwargs={
                        "sources": ["fotmob_fixtures", "fotmob_details", "fbref"]
                    }
                )
                result["collection_triggered"] = True
                result["collection_reason"] = reason
            else:
                logger.info(f"Data quality acceptable: {reason}")
                result = {
                    "status": "success",
                    "collection_triggered": False,
                    "quality_score": current_score,
                    "reason": reason
                }

            return result

        except Exception as e:
            logger.error(f"Data quality monitoring failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "collection_triggered": False
            }

    def close(self):
        """Clean up resources."""
        if self._prefect_client_initialized and self.prefect_client:
            try:
                asyncio.create_task(self.prefect_client.__aexit__(None, None, None))
                logger.info("Prefect client closed")
            except Exception as e:
                logger.error(f"Error closing Prefect client: {e}")

        super().close()


# Celery task for triggering Prefect flows
def trigger_prefect_flow_task(flow_name: str, **kwargs) -> Dict[str, Any]:
    """
    Celery task to trigger a Prefect flow.

    This task provides the bridge between Celery Beat scheduling
    and Prefect flow execution.

    Args:
        flow_name: Name of the Prefect flow to trigger
        **kwargs: Additional arguments for the flow

    Returns:
        Dict with execution results
    """
    logger.info(f"Celery task triggering Prefect flow: {flow_name}")

    try:
        # Create scheduler instance
        scheduler = PrefectFlowScheduler()

        # Run async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                scheduler.trigger_prefect_flow(flow_name, flow_kwargs=kwargs)
            )
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Failed to trigger flow {flow_name}: {e}")
        return {
            "status": "error",
            "flow_name": flow_name,
            "error": str(e)
        }


def check_model_performance_task() -> Dict[str, Any]:
    """
    Celery task for model performance monitoring.

    Returns:
        Dict with performance check results
    """
    logger.info("Celery task checking model performance")

    try:
        scheduler = PrefectFlowScheduler()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                scheduler.check_model_performance()
            )
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Model performance check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def monitor_data_quality_task() -> Dict[str, Any]:
    """
    Celery task for data quality monitoring.

    Returns:
        Dict with quality monitoring results
    """
    logger.info("Celery task monitoring data quality")

    try:
        scheduler = PrefectFlowScheduler()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                scheduler.monitor_data_quality()
            )
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Data quality monitoring failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }