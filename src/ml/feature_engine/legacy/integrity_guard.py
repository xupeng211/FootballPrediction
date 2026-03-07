"""
V41.350 Integrity Guard - Golden Shield Production Module
=========================================================

Migrated from V41.287 Golden Shield Audit - Production-grade feature integrity validation.

Core capabilities:
- Feature richness calculation (recursive nested dimension counting)
- Core metrics validation (xG, shots, possession, attacks)
- Quality rating (EXCELLENT/GOOD/FAIR/POOR)
- Golden Shield compliance check (configurable threshold)

Usage:
    from src.ml.feature_engine.legacy import IntegrityGuard, GoldenShieldConfig

    # Use default config (threshold: 30)
    guard = IntegrityGuard()

    # Custom config
    config = GoldenShieldConfig(
        feature_richness_threshold=50,
        require_xg=True,
        require_shots=True,
    )
    guard = IntegrityGuard(config)

    # Validate technical features
    result = guard.validate(technical_features)
    if result.is_compliant:
        logger.info("PASS: Golden Shield compliant")
    else:
        logger.info(f"FAIL: {result.violation_reason}")

Author: V41.350 SRE Team
Version: V41.350 "The Great Consolidation"
Migrated from: V41.287 "The Golden Shield"
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from src.config_unified import get_config

logger = logging.getLogger("IntegrityGuard")


# =============================================================================
# Configuration Models
# =============================================================================


@dataclass
class GoldenShieldConfig:
    """
    V41.350: Golden Shield Configuration

    Compliance thresholds for technical_features validation.

    Attributes:
        feature_richness_threshold: Minimum dimension count (default: 30)
        require_xg: Require xG/expected_goals data (default: True)
        require_shots: Require shots data (default: True)
        require_possession: Require possession data (default: True)
        require_attack_data: Require attack statistics (default: True)
        excellent_threshold: Dimensions for EXCELLENT rating (default: 100)
        good_threshold: Dimensions for GOOD rating (default: 80)
        fair_threshold: Dimensions for FAIR rating (default: 50)
    """

    feature_richness_threshold: int = 30
    require_xg: bool = True
    require_shots: bool = True
    require_possession: bool = True
    require_attack_data: bool = True

    excellent_threshold: int = 100
    good_threshold: int = 80
    fair_threshold: int = 50

    @classmethod
    def from_settings(cls) -> GoldenShieldConfig:
        """Load config from harvester_settings.json"""
        get_config()
        # TODO: Load from config/harvester_settings.json when ready
        return cls()


@dataclass
class ValidationResult:
    """
    V41.350: Validation Result

    Attributes:
        is_compliant: Whether the sample passes Golden Shield validation
        quality_rating: Quality rating (EXCELLENT/GOOD/FAIR/POOR)
        feature_richness: Total dimension count
        core_metrics: Core metric presence check results
        violation_reason: Reason for non-compliance (if any)
        warnings: List of warnings (non-blocking issues)
    """

    is_compliant: bool
    quality_rating: str
    feature_richness: int
    core_metrics: dict[str, bool]
    violation_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "is_compliant": self.is_compliant,
            "quality_rating": self.quality_rating,
            "feature_richness": self.feature_richness,
            "core_metrics": self.core_metrics,
            "violation_reason": self.violation_reason,
            "warnings": self.warnings,
        }


# =============================================================================
# V41.350 Integrity Guard (Golden Shield)
# =============================================================================


class IntegrityGuard:
    """
    V41.350: Integrity Guard - Golden Shield Production Module

    Validates technical_features integrity for harvested match data.

    Core validation steps:
    1. Feature richness calculation (recursive nested dimension counting)
    2. Core metrics validation (xG, shots, possession, attacks)
    3. Quality rating assignment
    4. Golden Shield compliance check

    Configuration loaded from config/harvester_settings.json:
    - golden_shield.threshold: Minimum feature richness (default: 30)
    - golden_shield.require_xg: Require xG data (default: true)
    """

    def __init__(self, config: GoldenShieldConfig | None = None):
        self.config = config or GoldenShieldConfig.from_settings()
        logger.info("V41.350: Integrity Guard initialized")
        logger.info(f"  - Feature richness threshold: {self.config.feature_richness_threshold}")
        logger.info(
            f"  - Quality thresholds: EXCELLENT≥{self.config.excellent_threshold}, "
            f"GOOD≥{self.config.good_threshold}, FAIR≥{self.config.fair_threshold}"
        )

    def validate(self, technical_features: dict[str, Any] | None) -> ValidationResult:
        """
        Validate technical_features against Golden Shield standards

        Args:
            technical_features: Match technical features (JSONB from database)

        Returns:
            ValidationResult: Validation result with compliance status
        """
        if technical_features is None:
            return ValidationResult(
                is_compliant=False,
                quality_rating="POOR",
                feature_richness=0,
                core_metrics={
                    "has_xg": False,
                    "has_shots": False,
                    "has_possession": False,
                    "has_attack_data": False,
                },
                violation_reason="technical_features is NULL",
            )

        # Step 1: Calculate feature richness
        richness = self._calculate_feature_richness(technical_features)

        # Step 2: Check core metrics
        core_metrics = self._check_core_metrics(technical_features)

        # Step 3: Determine quality rating
        quality = self._get_quality_rating(richness, core_metrics)

        # Step 4: Check Golden Shield compliance
        is_compliant, violation_reason = self._check_compliance(richness, core_metrics)

        # Collect warnings
        warnings = self._collect_warnings(richness, core_metrics)

        return ValidationResult(
            is_compliant=is_compliant,
            quality_rating=quality,
            feature_richness=richness,
            core_metrics=core_metrics,
            violation_reason=violation_reason,
            warnings=warnings,
        )

    def _calculate_feature_richness(self, technical_features: dict[str, Any]) -> int:
        """
        Calculate feature richness (recursive nested dimension counting)

        V41.287: Recursively counts all nested fields in the JSON structure.
        """

        def count_dict_keys(d: dict[str, Any]) -> int:
            count = 0
            for value in d.values():
                if isinstance(value, dict):
                    count += count_dict_keys(value)
                elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    for item in value:
                        count += count_dict_keys(item)
                else:
                    count += 1
            return count

        return count_dict_keys(technical_features)

    def _check_core_metrics(self, technical_features: dict[str, Any]) -> dict[str, bool]:
        """
        Check if core metrics are present

        V41.287: Recursively searches for xG, shots, possession, and attack data.
        """
        checks = {
            "has_xg": False,
            "has_shots": False,
            "has_possession": False,
            "has_attack_data": False,
        }

        def search_recursive(data: Any, target_keywords: list) -> bool:
            """Recursively search for target keywords"""
            if isinstance(data, dict):
                for key, value in data.items():
                    for keyword in target_keywords:
                        if keyword.lower() in key.lower():
                            return True
                    if search_recursive(value, target_keywords):
                        return True
            elif isinstance(data, list):
                for item in data:
                    if search_recursive(item, target_keywords):
                        return True
            return False

        checks["has_xg"] = search_recursive(
            technical_features, ["xg", "expected_goals", "expected-goals"]
        )
        checks["has_shots"] = search_recursive(technical_features, ["shots", "shot", "total_shots"])
        checks["has_possession"] = search_recursive(technical_features, ["possession", "pos"])
        checks["has_attack_data"] = search_recursive(
            technical_features, ["attack", "attacks", "dangerous_attacks", "counter_attacks"]
        )

        return checks

    def _get_quality_rating(self, feature_richness: int, core_checks: dict[str, bool]) -> str:
        """
        Calculate data quality rating

        V41.287: Quality thresholds:
        - EXCELLENT: ≥100 dimensions AND 4 core metrics
        - GOOD: ≥80 dimensions AND 3 core metrics
        - FAIR: ≥50 dimensions AND 2 core metrics
        - POOR: Below FAIR threshold
        """
        core_score = sum(core_checks.values())

        if feature_richness >= self.config.excellent_threshold and core_score >= 4:
            return "EXCELLENT"
        if feature_richness >= self.config.good_threshold and core_score >= 3:
            return "GOOD"
        if feature_richness >= self.config.fair_threshold and core_score >= 2:
            return "FAIR"
        return "POOR"

    def _check_compliance(
        self, feature_richness: int, core_checks: dict[str, bool]
    ) -> tuple[bool, str | None]:
        """
        Check Golden Shield compliance

        V41.287: Compliance requires:
        1. Feature richness >= threshold (default: 30)
        2. All required core metrics present (based on config)
        """
        # Check feature richness
        if feature_richness < self.config.feature_richness_threshold:
            return (
                False,
                f"Feature richness ({feature_richness}) below threshold ({self.config.feature_richness_threshold})",
            )

        # Check required core metrics
        if self.config.require_xg and not core_checks["has_xg"]:
            return False, "Missing required xG data"

        if self.config.require_shots and not core_checks["has_shots"]:
            return False, "Missing required shots data"

        if self.config.require_possession and not core_checks["has_possession"]:
            return False, "Missing required possession data"

        if self.config.require_attack_data and not core_checks["has_attack_data"]:
            return False, "Missing required attack data"

        return True, None

    def _collect_warnings(self, feature_richness: int, core_checks: dict[str, bool]) -> list[str]:
        """Collect non-blocking warnings"""
        warnings = []

        if feature_richness < self.config.good_threshold:
            warnings.append(
                f"Feature richness ({feature_richness}) below GOOD threshold ({self.config.good_threshold})"
            )

        if not core_checks["has_xg"]:
            warnings.append("Missing xG data (quality may be degraded)")

        if not core_checks["has_shots"]:
            warnings.append("Missing shots data")

        return warnings


# =============================================================================
# V41.350 Batch Auditor (Database Level)
# =============================================================================


class BatchAuditor:
    """
    V41.350: Batch Auditor for Database-Level Validation

    Validates multiple samples from the database and generates audit report.

    Usage:
        auditor = BatchAuditor()
        report = auditor.audit_database(limit=100)
        logger.info(report)
    """

    def __init__(self, config: GoldenShieldConfig | None = None):
        self.guard = IntegrityGuard(config)

    def audit_database(self, limit: int = 100) -> dict:
        """
        Run audit on database samples

        Returns:
            dict: Audit report with statistics
        """
        import psycopg2

        from src.config_unified import get_config

        config = get_config()
        conn = psycopg2.connect(
            host=config.database.host,
            database=config.database.name,
            user=config.database.user,
            password=config.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        try:
            # Get samples with odds and lineups (three-in-one)
            cursor.execute(
                """
                SELECT DISTINCT m.match_id, m.technical_features, m.home_team, m.away_team, m.match_date
                FROM matches m
                INNER JOIN match_odds_intelligence modi ON m.match_id = modi.match_id
                INNER JOIN match_lineups ml ON m.match_id = ml.match_id
                ORDER BY m.match_date DESC
                LIMIT %s
            """,
                (limit,),
            )

            samples = cursor.fetchall()

            stats = {
                "total": len(samples),
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0,
                "compliant": 0,
                "non_compliant": 0,
            }

            problem_samples = []

            for match_id, tech_features, home_team, away_team, _match_date in samples:
                result = self.guard.validate(tech_features)

                stats[result.quality_rating.lower()] += 1
                if result.is_compliant:
                    stats["compliant"] += 1
                else:
                    stats["non_compliant"] += 1
                    problem_samples.append(
                        {
                            "match_id": match_id,
                            "home_team": home_team,
                            "away_team": away_team,
                            "violation": result.violation_reason,
                        }
                    )

            return {
                "stats": stats,
                "problem_samples": problem_samples,
                "compliance_rate": stats["compliant"] / stats["total"] * 100
                if stats["total"] > 0
                else 0,
            }

        finally:
            cursor.close()
            conn.close()
