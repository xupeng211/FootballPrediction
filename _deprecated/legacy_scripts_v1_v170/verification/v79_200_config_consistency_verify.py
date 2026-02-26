#!/usr/bin/env python3
"""
V79.200 Configuration Consistency Verification (Python Side)
============================================================

This script verifies that Python's YAML loader produces consistent types
with JavaScript's YAML/JSON loader.

Author: V79.200 Engineering Team
Version: V79.200
Date: 2026-01-25
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config_loader import (
    get_hyper_parameters_config,
    get_team_aliases_config,
)


def format_type(value: Any) -> str:
    """Get the type name of a value"""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return type(value).__name__


def verify_hyper_parameters() -> dict[str, Any]:
    """Verify hyper-parameters configuration"""
    config = get_hyper_parameters_config()

    result = {
        "timestamp": datetime.now().isoformat(),
        "language": "python",
        "loader": "yaml.safe_load (PyYAML)",
        "config_file": "src/config/hyper_parameters.yaml",
        "sections": {}
    }

    # Fatigue section
    result["sections"]["fatigue"] = {
        "busy_week_threshold": {
            "value": config.busy_week_threshold,
            "type": format_type(config.busy_week_threshold),
            "expected_type": "integer"
        },
        "default_rest_days": {
            "value": config.default_rest_days,
            "type": format_type(config.default_rest_days),
            "expected_type": "integer"
        }
    }

    # Unavailable section
    result["sections"]["unavailable"] = {
        "star_market_value": {
            "value": config.star_market_value,
            "type": format_type(config.star_market_value),
            "expected_type": "float"
        }
    }

    # Feature extraction section
    result["sections"]["feature_extraction"] = {
        "core_player_threshold": {
            "value": config.core_player_threshold,
            "type": format_type(config.core_player_threshold),
            "expected_type": "float"
        },
        "sparsity_threshold": {
            "value": config.sparsity_threshold,
            "type": format_type(config.sparsity_threshold),
            "expected_type": "float"
        },
        "excellent_threshold": {
            "value": config.excellent_threshold,
            "type": format_type(config.excellent_threshold),
            "expected_type": "integer"
        },
        "good_threshold": {
            "value": config.good_threshold,
            "type": format_type(config.good_threshold),
            "expected_type": "integer"
        },
        "fair_threshold": {
            "value": config.fair_threshold,
            "type": format_type(config.fair_threshold),
            "expected_type": "integer"
        },
        "minimum_threshold": {
            "value": config.minimum_threshold,
            "type": format_type(config.minimum_threshold),
            "expected_type": "integer"
        }
    }

    # Similarity section
    result["sections"]["similarity"] = {
        "team_match_threshold": {
            "value": config.team_match_threshold,
            "type": format_type(config.team_match_threshold),
            "expected_type": "float"
        },
        "excellent_confidence_min": {
            "value": config.excellent_confidence_min,
            "type": format_type(config.excellent_confidence_min),
            "expected_type": "integer"
        },
        "good_confidence_min": {
            "value": config.good_confidence_min,
            "type": format_type(config.good_confidence_min),
            "expected_type": "integer"
        },
        "fair_confidence_min": {
            "value": config.fair_confidence_min,
            "type": format_type(config.fair_confidence_min),
            "expected_type": "integer"
        },
        "reject_confidence_below": {
            "value": config.reject_confidence_below,
            "type": format_type(config.reject_confidence_below),
            "expected_type": "integer"
        },
        "youth_penalty_ratio": {
            "value": config.youth_penalty_ratio,
            "type": format_type(config.youth_penalty_ratio),
            "expected_type": "float"
        }
    }

    # Odds integrity section
    result["sections"]["odds_integrity"] = {
        "min_payout": {
            "value": config.min_payout,
            "type": format_type(config.min_payout),
            "expected_type": "float"
        },
        "max_payout": {
            "value": config.max_payout,
            "type": format_type(config.max_payout),
            "expected_type": "float"
        },
        "min_odds_value": {
            "value": config.min_odds_value,
            "type": format_type(config.min_odds_value),
            "expected_type": "float"
        }
    }

    # Database section
    result["sections"]["database"] = {
        "pool_size": {
            "value": config.pool_size,
            "type": format_type(config.pool_size),
            "expected_type": "integer"
        },
        "pool_max_overflow": {
            "value": config.pool_max_overflow,
            "type": format_type(config.pool_max_overflow),
            "expected_type": "integer"
        },
        "pool_timeout": {
            "value": config.pool_timeout,
            "type": format_type(config.pool_timeout),
            "expected_type": "integer"
        },
        "pool_recycle": {
            "value": config.pool_recycle,
            "type": format_type(config.pool_recycle),
            "expected_type": "integer"
        },
        "query_timeout": {
            "value": config.query_timeout,
            "type": format_type(config.query_timeout),
            "expected_type": "integer"
        },
        "connection_timeout": {
            "value": config.connection_timeout,
            "type": format_type(config.connection_timeout),
            "expected_type": "integer"
        }
    }

    # Crawler section
    result["sections"]["crawler"] = {
        "default_delay": {
            "value": config.default_delay,
            "type": format_type(config.default_delay),
            "expected_type": "float"
        },
        "min_delay": {
            "value": config.min_delay,
            "type": format_type(config.min_delay),
            "expected_type": "float"
        },
        "max_delay": {
            "value": config.max_delay,
            "type": format_type(config.max_delay),
            "expected_type": "float"
        },
        "max_retries": {
            "value": config.max_retries,
            "type": format_type(config.max_retries),
            "expected_type": "integer"
        },
        "retry_backoff_multiplier": {
            "value": config.retry_backoff_multiplier,
            "type": format_type(config.retry_backoff_multiplier),
            "expected_type": "float"
        },
        "retry_max_delay": {
            "value": config.retry_max_delay,
            "type": format_type(config.retry_max_delay),
            "expected_type": "integer"
        },
        "retry_jitter_range": {
            "value": config.retry_jitter_range,
            "type": format_type(config.retry_jitter_range),
            "expected_type": "float"
        }
    }

    # Cache section
    result["sections"]["cache"] = {
        "cache_enable": {
            "value": config.cache_enable,
            "type": format_type(config.cache_enable),
            "expected_type": "boolean"
        },
        "cache_size": {
            "value": config.cache_size,
            "type": format_type(config.cache_size),
            "expected_type": "integer"
        },
        "cache_ttl_seconds": {
            "value": config.cache_ttl_seconds,
            "type": format_type(config.cache_ttl_seconds),
            "expected_type": "integer"
        }
    }

    # Performance section
    result["sections"]["performance"] = {
        "target_inference_latency_ms": {
            "value": config.target_inference_latency_ms,
            "type": format_type(config.target_inference_latency_ms),
            "expected_type": "integer"
        },
        "target_fotmob_api_latency_s": {
            "value": config.target_fotmob_api_latency_s,
            "type": format_type(config.target_fotmob_api_latency_s),
            "expected_type": "float"
        },
        "max_memory_mb": {
            "value": config.max_memory_mb,
            "type": format_type(config.max_memory_mb),
            "expected_type": "integer"
        },
        "min_data_completeness": {
            "value": config.min_data_completeness,
            "type": format_type(config.min_data_completeness),
            "expected_type": "float"
        },
        "min_mapping_success_rate": {
            "value": config.min_mapping_success_rate,
            "type": format_type(config.min_mapping_success_rate),
            "expected_type": "float"
        }
    }

    # Leagues section
    result["sections"]["leagues"] = {
        "top_5_leagues": {
            "value": config.top_5_leagues,
            "type": format_type(config.top_5_leagues),
            "expected_type": "array"
        }
    }

    return result


def verify_team_aliases() -> dict[str, Any]:
    """Verify team aliases configuration"""
    config = get_team_aliases_config()

    result = {
        "timestamp": datetime.now().isoformat(),
        "language": "python",
        "loader": "json.load (stdlib)",
        "config_file": "config/team_aliases.json",
        "sections": {}
    }

    result["sections"]["team_aliases"] = {
        "team_name_mappings": {
            "value": config.team_name_mappings,
            "type": format_type(config.team_name_mappings),
            "expected_type": "object"
        },
        "suffixes_to_strip": {
            "value": config.suffixes_to_strip,
            "type": format_type(config.suffixes_to_strip),
            "expected_type": "array"
        },
        "prefixes_to_strip": {
            "value": config.prefixes_to_strip,
            "type": format_type(config.prefixes_to_strip),
            "expected_type": "array"
        },
        "youth_keywords": {
            "value": config.youth_keywords,
            "type": format_type(config.youth_keywords),
            "expected_type": "object"
        },
        "youth_patterns": {
            "value": config.youth_patterns,
            "type": format_type(config.youth_patterns),
            "expected_type": "array"
        },
        "common_suffixes": {
            "value": config.common_suffixes,
            "type": format_type(config.common_suffixes),
            "expected_type": "object"
        }
    }

    return result


def main() -> int:
    """Main entry point"""
    print("=" * 70)
    print("V79.200 Configuration Consistency Verification (Python Side)")
    print("=" * 70)
    print()

    # Verify hyper-parameters
    print("Verifying hyper_parameters.yaml...")
    hyper_params = verify_hyper_parameters()

    # Verify team aliases
    print("Verifying team_aliases.json...")
    team_aliases = verify_team_aliases()

    # Output JSON result
    result = {
        "hyper_parameters": hyper_params,
        "team_aliases": team_aliases
    }

    # Write to file
    output_file = Path(__file__).parent / "v79_200_python_config_snapshot.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Python configuration snapshot saved to: {output_file}")
    print()

    # Print summary
    print("Summary:")
    print(f"  - Fatigue parameters: {len(hyper_params['sections']['fatigue'])} keys")
    print(f"  - Feature extraction: {len(hyper_params['sections']['feature_extraction'])} keys")
    print(f"  - Similarity: {len(hyper_params['sections']['similarity'])} keys")
    print(f"  - Database: {len(hyper_params['sections']['database'])} keys")
    print(f"  - Crawler: {len(hyper_params['sections']['crawler'])} keys")
    print(f"  - Cache: {len(hyper_params['sections']['cache'])} keys")
    print(f"  - Performance: {len(hyper_params['sections']['performance'])} keys")
    print(f"  - Leagues: {len(hyper_params['sections']['leagues'])} keys")
    print(f"  - Team aliases: {len(team_aliases['sections']['team_aliases'])} keys")

    print("\n⏳ Next: Run JavaScript verification to compare results.")
    print("   Command: node scripts/verification/v79_200_config_consistency_verify.js")

    return 0


if __name__ == "__main__":
    sys.exit(main())
