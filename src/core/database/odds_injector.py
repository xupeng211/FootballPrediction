"""
Odds Injector Module - Database Batch Injection

This module provides production-grade batch injection functionality for odds data.
It handles database connections, data validation, quality scoring, and UPSERT operations.

Core Features:
    - Stream-based JSONL processing (low memory)
    - Quality score calculation (1/H + 1/D + 1/A)
    - Duplicate protection (UPSERT based on quality)
    - Batch optimization with execute_values
    - Full type annotations and logging

Usage:
    from src.core.database.odds_injector import OddsInjector, InjectionStats

    injector = OddsInjector()
    stats = injector.inject_from_jsonl("data.jsonl")
    print(f"Injected: {stats.injected}, Skipped: {stats.skipped}")

Authors: V41.143 -> V41.153 Migration
Version: 1.0.0 (Production)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values
from pydantic import BaseModel, Field, field_validator, model_validator

from src.config_unified import get_settings

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class InjectionStats:
    """Statistics for injection operation.

    Attributes:
        total: Total records processed.
        injected: Records successfully injected.
        skipped: Records skipped (lower quality).
        failed: Records that failed injection.
        start_time: Operation start timestamp.
        end_time: Operation end timestamp.
    """

    total: int = 0
    injected: int = 0
    skipped: int = 0
    failed: int = 0
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    end_time: float | None = None

    @property
    def duration(self) -> float:
        """Calculate operation duration in seconds."""
        end = self.end_time or datetime.utcnow().timestamp()
        return end - self.start_time

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.injected / self.total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total": self.total,
            "injected": self.injected,
            "skipped": self.skipped,
            "failed": self.failed,
            "duration_seconds": round(self.duration, 2),
            "success_rate": round(self.success_rate, 2),
        }


class OddsRecord(BaseModel):
    """Odds data record for validation.

    Attributes:
        match_id: Unique match identifier.
        values: Odds values [home, draw, away].
        source_alias: Data source identifier.
        timestamp: ISO format timestamp.
    """

    match_id: str
    values: list[float] = Field(min_length=3, max_length=3)
    source_alias: str = "Provider_Alpha"
    timestamp: str | None = None

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: list[float]) -> list[float]:
        """Validate odds values are positive."""
        if not all(val > 0 for val in v):
            raise ValueError("All odds values must be positive")
        return v

    @model_validator(mode="after")
    def validate_timestamp(self) -> OddsRecord:
        """Set default timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        return self


class InjectionPayload(BaseModel):
    """Database injection payload.

    Attributes:
        match_id: Match identifier.
        source: Source identifier.
        values: Odds values.
        quality_score: Computed quality score.
        timestamp: Injection timestamp.
    """

    match_id: str
    source: str
    values: list[float]
    quality_score: float
    timestamp: str

    @classmethod
    def from_record(cls, record: OddsRecord) -> InjectionPayload:
        """Create payload from odds record.

        Args:
            record: Validated odds record.

        Returns:
            InjectionPayload instance.
        """
        quality_score = cls._calculate_quality_score(record.values)

        return cls(
            match_id=record.match_id,
            source=record.source_alias,
            values=record.values,
            quality_score=quality_score,
            timestamp=record.timestamp or datetime.utcnow().isoformat() + "Z",
        )

    @staticmethod
    def _calculate_quality_score(values: list[float]) -> float:
        """Calculate quality score (sum of reciprocals).

        Args:
            values: Odds values [home, draw, away].

        Returns:
            Quality score (higher is better).
        """
        try:
            if len(values) != 3 or any(v <= 0 for v in values):
                return 0.0
            return round(sum(1.0 / v for v in values), 6)
        except (ZeroDivisionError, TypeError):
            return 0.0


# ============================================================================
# Logger Configuration
# ============================================================================

def get_injection_logger(name: str = "OddsInjector") -> logging.Logger:
    """Get configured logger for injection operations.

    Args:
        name: Logger name.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(
            log_dir / "injection_audit.log",
            mode="a",
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


# ============================================================================
# Main Injector Class
# ============================================================================

class OddsInjector:
    """Production-grade odds data injector.

    This class handles the complete injection workflow:
    1. Stream-read JSONL files
    2. Validate records
    3. Check existing data quality
    4. Perform UPSERT operations
    5. Track statistics

    Attributes:
        settings: Application settings.
        logger: Configured logger instance.
        quality_threshold_min: Minimum quality score.
    """

    DEFAULT_QUALITY_MIN = 0.95
    DEFAULT_QUALITY_MAX = 1.08

    def __init__(
        self,
        quality_threshold_min: float = DEFAULT_QUALITY_MIN,
        quality_threshold_max: float = DEFAULT_QUALITY_MAX,
        logger: logging.Logger | None = None,
    ):
        """Initialize odds injector.

        Args:
            quality_threshold_min: Minimum acceptable quality score.
            quality_threshold_max: Maximum quality score (prevents outliers).
            logger: Custom logger instance.
        """
        self.settings = get_settings()
        self.logger = logger or get_injection_logger()
        self.quality_threshold_min = quality_threshold_min
        self.quality_threshold_max = quality_threshold_max

    def inject_from_jsonl(
        self,
        file_path: str | Path,
        batch_size: int = 500,
        dry_run: bool = False,
    ) -> InjectionStats:
        """Inject odds data from JSONL file.

        Args:
            file_path: Path to JSONL file.
            batch_size: Number of records per batch.
            dry_run: If True, validate but don't inject.

        Returns:
            Injection statistics.

        Raises:
            FileNotFoundError: If file doesn't exist.
            IOError: If file cannot be read.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stats = InjectionStats()

        self.logger.info(f"[INJECT] Starting injection from: {file_path}")

        # Stream read and validate
        records = self._stream_read_jsonl(path, stats)

        if not records:
            self.logger.warning("[INJECT] No valid records found")
            stats.end_time = datetime.utcnow().timestamp()
            return stats

        # Inject records
        if not dry_run:
            self._inject_records(records, stats, batch_size)
        else:
            self.logger.info(f"[INJECT] Dry run: {len(records)} records validated")

        stats.end_time = datetime.utcnow().timestamp()

        self.logger.info(
            f"[INJECT] Complete - "
            f"Total: {stats.total}, "
            f"Injected: {stats.injected}, "
            f"Skipped: {stats.skipped}, "
            f"Success: {stats.success_rate:.1f}%"
        )

        return stats

    def _stream_read_jsonl(
        self,
        file_path: Path,
        stats: InjectionStats,
    ) -> list[OddsRecord]:
        """Stream read JSONL file and validate records.

        Args:
            file_path: Path to JSONL file.
            stats: Statistics object to update.

        Returns:
            List of validated records.
        """
        valid_records: list[OddsRecord] = []

        with open(file_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    record = OddsRecord(**data)

                    # Additional quality validation
                    if self._validate_quality(record):
                        valid_records.append(record)
                    else:
                        self.logger.debug(
                            f"[INJECT] Quality check failed (line {line_num})"
                        )

                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.warning(
                        f"[INJECT] Validation failed (line {line_num}): {e}"
                    )
                    stats.failed += 1

        stats.total = len(valid_records)
        return valid_records

    def _validate_quality(self, record: OddsRecord) -> bool:
        """Validate record quality.

        Args:
            record: Record to validate.

        Returns:
            True if quality is acceptable.
        """
        quality = InjectionPayload._calculate_quality_score(record.values)
        return self.quality_threshold_min <= quality <= self.quality_threshold_max

    def _inject_records(
        self,
        records: list[OddsRecord],
        stats: InjectionStats,
        batch_size: int,
    ) -> None:
        """Inject records into database.

        Args:
            records: Validated records to inject.
            stats: Statistics object to update.
            batch_size: Batch size for database operations.
        """
        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        try:
            # Prepare update data
            update_data: list[tuple[str, str, float]] = []

            for record in records:
                payload = InjectionPayload.from_record(record)

                # Check existing quality
                should_update = self._should_update_record(cursor, payload)

                if should_update:
                    update_data.append((
                        json.dumps(payload.model_dump()),
                        payload.match_id,
                        payload.quality_score,
                    ))

            # Batch update
            if update_data:
                execute_values(
                    cursor,
                    """
                    UPDATE matches
                    SET l3_odds_data = data.v::jsonb,
                        updated_at = NOW()
                    FROM (VALUES %s) AS data(v, mid, quality)
                    WHERE matches.match_id = data.mid
                      AND (matches.l3_odds_data IS NULL
                           OR (matches.l3_odds_data->>'quality_score')::float < data.quality)
                    """,
                    update_data,
                )

                stats.injected = len(update_data)
                conn.commit()

                self.logger.info(f"[INJECT] Batch update complete: {stats.injected} records")
            else:
                stats.skipped = len(records)

        except psycopg2.Error as e:
            conn.rollback()
            self.logger.exception(f"[INJECT] Database error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _should_update_record(
        self,
        cursor,
        payload: InjectionPayload,
    ) -> bool:
        """Check if record should be updated based on quality.

        Args:
            cursor: Database cursor.
            payload: Injection payload.

        Returns:
            True if record should be updated.
        """
        cursor.execute(
            "SELECT l3_odds_data FROM matches WHERE match_id = %s",
            (payload.match_id,)
        )
        row = cursor.fetchone()

        if not row or not row[0]:
            return True

        try:
            existing_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            existing_quality = existing_data.get("quality_score", 0.0)

            return payload.quality_score > existing_quality
        except (json.JSONDecodeError, TypeError):
            return True


# ============================================================================
# Convenience Functions
# ============================================================================

def inject_odds_data(
    file_path: str | Path,
    quality_min: float = 0.95,
    dry_run: bool = False,
) -> InjectionStats:
    """Convenience function for odds injection.

    Args:
        file_path: Path to JSONL file.
        quality_min: Minimum quality score.
        dry_run: If True, validate only.

    Returns:
        Injection statistics.
    """
    injector = OddsInjector(quality_threshold_min=quality_min)
    return injector.inject_from_jsonl(file_path, dry_run=dry_run)


# Convenience exports
__all__ = [
    "InjectionPayload",
    "InjectionStats",
    "OddsInjector",
    "OddsRecord",
    "get_injection_logger",
    "inject_odds_data",
]
