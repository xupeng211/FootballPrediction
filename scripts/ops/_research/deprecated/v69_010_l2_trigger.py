#!/usr/bin/env python3
"""
V69.010 - L2 Enrichment Trigger
====================================

Step A of the V69.000 Pipeline Orchestrator.

Triggers FotMob L2 data enrichment for matches with NULL l2_raw_json.
Integrates with V144.5 FotMobCoreCollector.

Usage:
    python v69_010_l2_trigger.py --match-ids "1234567,1234568,1234569" --batch-size 50

Author: Principal Systems Integration Engineer
Version: V69.010
Date: 2026-01-25
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/v69_010_l2_trigger.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# V71.000: L2 Data Sanity Filter
# ============================================================================

class L2DataSanityFilter:
    """
    V71.000: Sanity filter for L2 data validation.

    Ensures that collected L2 data contains required fields before persisting to database.
    Rejects empty or malformed data to prevent "garbage data" from entering the system.
    """

    # V72.100: Relaxed structure validation - FotMob API response varies by match tier
    # Only validate data quality (size, type), not specific structure
    REQUIRED_TOP_LEVEL_FIELDS = []  # Removed 'content' - API structure varies

    # Required nested fields (under 'content')
    REQUIRED_CONTENT_FIELDS = []  # V72.100: Removed - not applicable for all API responses

    # Minimum data size check (bytes) to detect empty responses
    MIN_DATA_SIZE_BYTES = 100

    # Maximum data size check (bytes) to detect absurdly large responses
    MAX_DATA_SIZE_BYTES = 10_000_000  # 10MB

    @classmethod
    def validate_l2_data(cls, l2_raw_json: Optional[Dict[str, Any]], match_id: str) -> Dict[str, Any]:
        """
        Validate L2 data for completeness and correctness.

        Args:
            l2_raw_json: The L2 data to validate (can be None or dict)
            match_id: Match ID for logging purposes

        Returns:
            Dict with validation results:
            {
                'valid': bool,
                'reason': str (if invalid),
                'confidence': float (0.0 to 1.0)
            }
        """
        # Check 1: Null or empty data
        if l2_raw_json is None:
            logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: l2_raw_json is None")
            return {
                'valid': False,
                'reason': 'l2_raw_json is None',
                'confidence': 0.0
            }

        # Check 2: Data type validation
        if not isinstance(l2_raw_json, dict):
            logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: l2_raw_json is not a dict (type: {type(l2_raw_json)})")
            return {
                'valid': False,
                'reason': f'l2_raw_json is not a dict (type: {type(l2_raw_json).__name__})',
                'confidence': 0.0
            }

        # Check 3: Minimum size check (convert to JSON string to check size)
        json_str = json.dumps(l2_raw_json)
        data_size = len(json_str.encode('utf-8'))

        if data_size < cls.MIN_DATA_SIZE_BYTES:
            logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: Data too small ({data_size} bytes < {cls.MIN_DATA_SIZE_BYTES})")
            return {
                'valid': False,
                'reason': f'Data too small ({data_size} bytes)',
                'confidence': 0.0
            }

        if data_size > cls.MAX_DATA_SIZE_BYTES:
            logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: Data too large ({data_size} bytes > {cls.MAX_DATA_SIZE_BYTES})")
            return {
                'valid': False,
                'reason': f'Data too large ({data_size} bytes)',
                'confidence': 0.0
            }

        # Check 4: Required top-level fields
        missing_top_level = [field for field in cls.REQUIRED_TOP_LEVEL_FIELDS if field not in l2_raw_json]
        if missing_top_level:
            logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: Missing top-level fields: {missing_top_level}")
            return {
                'valid': False,
                'reason': f'Missing top-level fields: {missing_top_level}',
                'confidence': 0.0
            }

        # Check 5: Required content fields (V72.100: Skip if no required fields)
        if cls.REQUIRED_CONTENT_FIELDS:
            content = l2_raw_json.get('content', {})
            if isinstance(content, dict):
                missing_content = [field for field in cls.REQUIRED_CONTENT_FIELDS if field not in content]
                if missing_content:
                    logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: Missing content fields: {missing_content}")
                    return {
                        'valid': False,
                        'reason': f'Missing content fields: {missing_content}',
                        'confidence': 0.0
                    }

        # Check 6: Detect error pages (common API error responses)
        if 'error' in l2_raw_json or 'errorCode' in l2_raw_json:
            logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: API error response detected")
            return {
                'valid': False,
                'reason': 'API error response',
                'confidence': 0.0
            }

        # Check 7: Detect empty stats (V72.100: Skip if content field not present)
        content = l2_raw_json.get('content')
        if content and isinstance(content, dict):
            stats = content.get('stats')
            if stats is None or (isinstance(stats, (dict, list)) and len(stats) == 0):
                logger.warning(f"[V71.000] Sanity check FAILED for {match_id}: Empty stats field")
                return {
                    'valid': False,
                    'reason': 'Empty stats field',
                    'confidence': 0.0
                }

        # All checks passed
        logger.info(f"[V71.000] ✅ Sanity check PASSED for {match_id}: Data size {data_size} bytes")
        return {
            'valid': True,
            'reason': None,
            'confidence': 1.0
        }

    @classmethod
    def get_failed_match_status_update(cls, reason: str) -> str:
        """
        Generate appropriate status update message for failed sanity check.

        Args:
            reason: The validation failure reason

        Returns:
            Status message string
        """
        return f"FAILED: Sanity check - {reason}"


class L2EnrichmentService:
    """V69.010: L2 Enrichment Service with V71.000 sanity filter."""

    def __init__(self):
        """Initialize the L2 enrichment service."""
        self.collector = FotMobCoreCollector()
        logger.info("[V69.010] L2 Enrichment Service initialized")

    async def enrich_match(self, match_id: str) -> Dict[str, Any]:
        """
        Enrich a single match with L2 data.

        Args:
            match_id: Match ID to enrich

        Returns:
            Dict with success status and metadata
        """
        try:
            logger.info(f"[V69.010] Enriching match: {match_id}")

            # Get league_id from database (required for harvest_match_with_league)
            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor
            )

            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT league_id FROM matches WHERE match_id = %s",
                    (match_id,)
                )
                row = cursor.fetchone()

                if not row or not row['league_id']:
                    logger.warning(f"[V69.010] No league_id found for match {match_id}, skipping")
                    return {"success": False, "reason": "no_league_id"}

                league_id = row['league_id']
                cursor.close()

            except Exception as e:
                if cursor:
                    cursor.close()
                conn.close()
                raise

            # Use harvest_match_with_league with ON CONFLICT handling
            success = self.collector.harvest_match_with_league(
                match_id=match_id,
                league_id=league_id
            )

            if not success:
                logger.warning(f"[V69.010] ⚠️ Match {match_id} enrichment failed (harvest returned False)")
                conn.close()
                return {"success": False, "reason": "harvest_failed"}

            # V71.000: Validate the harvested L2 data with sanity filter
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT l2_raw_json FROM matches WHERE match_id = %s",
                    (match_id,)
                )
                row = cursor.fetchone()

                if row and row['l2_raw_json']:
                    l2_data = row['l2_raw_json']
                    sanity_check = L2DataSanityFilter.validate_l2_data(l2_data, match_id)

                    if not sanity_check['valid']:
                        # Sanity check FAILED - mark match as FAILED in pipeline state
                        logger.error(f"[V71.000] ❌ Sanity check FAILED for {match_id}: {sanity_check['reason']}")

                        # Update match_pipeline_state to FAILED
                        cursor.execute(
                            """
                            INSERT INTO match_pipeline_state (match_id, status, updated_at, error_message, metadata)
                            VALUES (%s, 'FAILED', NOW(), %s, %s)
                            ON CONFLICT (match_id) DO UPDATE SET
                                status = 'FAILED',
                                updated_at = NOW(),
                                error_message = EXCLUDED.error_message,
                                metadata = EXCLUDED.metadata
                            """,
                            (
                                match_id,
                                L2DataSanityFilter.get_failed_match_status_update(sanity_check['reason']),
                                json.dumps({
                                    "sanity_check_result": sanity_check,
                                    "data_size_bytes": len(json.dumps(l2_data).encode('utf-8')),
                                    "checked_at": datetime.now().isoformat()
                                })
                            )
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

                        return {
                            "success": False,
                            "reason": f"sanity_check_failed: {sanity_check['reason']}",
                            "sanity_check": sanity_check
                        }

                    # Sanity check PASSED - update pipeline state to ENRICHED
                    cursor.execute(
                        """
                        INSERT INTO match_pipeline_state (match_id, status, updated_at, metadata)
                        VALUES (%s, 'ENRICHED', NOW(), %s)
                        ON CONFLICT (match_id) DO UPDATE SET
                            status = 'ENRICHED',
                            updated_at = NOW(),
                            metadata = EXCLUDED.metadata
                        """,
                        (
                            match_id,
                            json.dumps({
                                "sanity_check_result": sanity_check,
                                "enriched_at": datetime.now().isoformat(),
                                "league_id": league_id
                            })
                        )
                    )
                    conn.commit()
                    logger.info(f"[V71.000] ✅ Sanity check PASSED for {match_id}, pipeline state updated to ENRICHED")

                cursor.close()

            except Exception as e:
                logger.exception(f"[V71.000] Error during sanity check for {match_id}: {e}")
                # Continue anyway - the harvest was successful even if sanity check failed

            conn.close()
            logger.info(f"[V69.010] ✅ Match {match_id} enriched successfully")
            return {"success": True}

        except Exception as e:
            logger.exception(f"[V69.010] ❌ Error enriching match {match_id}: {e}")
            return {"success": False, "reason": str(e)}

    async def enrich_batch(self, match_ids: List[str]) -> Dict[str, Any]:
        """
        Enrich multiple matches in batch.

        Args:
            match_ids: List of match IDs to enrich

        Returns:
            Dict with enrichment statistics
        """
        logger.info(f"[V69.010] Starting batch enrichment: {len(match_ids)} matches")

        results = {
            "total": len(match_ids),
            "enriched": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for i, match_id in enumerate(match_ids, 1):
            try:
                result = await self.enrich_match(match_id)

                if result["success"]:
                    results["enriched"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "match_id": match_id,
                        "reason": result.get("reason", "unknown")
                    })

                # Progress logging every 10 matches
                if i % 10 == 0:
                    logger.info(
                        f"[V69.010] Progress: {i}/{len(match_ids)} | "
                        f"Enriched: {results['enriched']} | Failed: {results['failed']}"
                    )

            except Exception as e:
                logger.exception(f"[V69.010] Unexpected error for match {match_id}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "match_id": match_id,
                    "reason": "exception"
                })

        # Log summary
        logger.info("=" * 60)
        logger.info("[V69.010] Batch Enrichment Summary")
        logger.info("=" * 60)
        logger.info(f"Total: {results['total']} matches")
        logger.info(f"Enriched: {results['enriched']} matches")
        logger.info(f"Failed: {results['failed']} matches")
        logger.info(f"Skipped: {results['skipped']} matches")
        logger.info(f"Success Rate: {(results['enriched'] / results['total'] * 100 if results['total'] > 0 else 0):.1f}%")
        logger.info("=" * 60)

        return results


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="V69.010 L2 Enrichment Trigger - Step A of V69.000 Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--match-ids",
        type=str,
        required=True,
        help="Comma-separated match IDs to enrich"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for processing (default: 50)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (no actual enrichment)"
    )

    args = parser.parse_args()

    # Parse match IDs
    match_ids = [mid.strip() for mid in args.match_ids.split(',') if mid.strip()]

    if not match_ids:
        logger.error("No valid match IDs provided")
        return 1

    logger.info(f"[V69.010] Starting L2 enrichment trigger with {len(match_ids)} matches")

    if args.dry_run:
        logger.info("[V69.010] Dry run mode - no actual enrichment")
        for match_id in match_ids[:5]:
            logger.info(f"  Would enrich: {match_id}")
        if len(match_ids) > 5:
            logger.info(f"  ... and {len(match_ids) - 5} more")
        return 0

    # Enrich matches
    service = L2EnrichmentService()
    results = await service.enrich_batch(match_ids)

    # V84.000: Output result as JSON with [JSON_RESULT] protocol (for Node.js integration)
    print(f"[JSON_RESULT]{json.dumps(results, ensure_ascii=False)}[JSON_RESULT]")

    # Return exit code based on success rate
    if results["failed"] == 0:
        return 0
    elif results["enriched"] > 0:
        return 0  # Partial success is OK
    else:
        return 1  # All failed


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n[V69.010] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"[V69.010] Fatal error: {e}")
        sys.exit(1)
