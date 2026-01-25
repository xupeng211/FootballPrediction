#!/usr/bin/env python3
"""
V79.100 Configuration Loader - 统一配置加载器
=============================================

提供从外部化配置文件加载配置的功能：
1. team_aliases.json - 队名映射
2. hyper_parameters.yaml - 超参数阈值

Author: V79.100 Engineering Team
Version: V79.100
Date: 2026-01-25
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration Paths
# =============================================================================

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
TEAM_ALIASES_PATH = CONFIG_DIR / "team_aliases.json"
HYPER_PARAMETERS_PATH = Path(__file__).parent / "hyper_parameters.yaml"


# =============================================================================
# Team Aliases Configuration
# =============================================================================

@dataclass
class TeamAliasesConfig:
    """队名映射配置"""

    team_name_mappings: dict[str, str] = field(default_factory=dict)
    suffixes_to_strip: list[str] = field(default_factory=list)
    prefixes_to_strip: list[str] = field(default_factory=list)
    youth_keywords: dict[str, list[str]] = field(default_factory=dict)
    youth_patterns: list[str] = field(default_factory=list)
    common_suffixes: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_json(cls, json_path: Path = TEAM_ALIASES_PATH) -> "TeamAliasesConfig":
        """从 JSON 文件加载配置"""
        if not json_path.exists():
            logger.warning(f"Team aliases file not found: {json_path}, using defaults")
            return cls()

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract team mappings
        team_data = data.get("team_name_mappings", {})

        # Extract suffixes and prefixes
        suffixes = data.get("suffixes_to_strip", [])
        prefixes = data.get("prefixes_to_strip", [])

        # Extract youth keywords
        youth_data = data.get("youth_keywords", {})

        # Extract youth patterns
        patterns = data.get("youth_patterns", [])

        # Extract common suffixes
        suffix_data = data.get("common_suffixes", {})

        return cls(
            team_name_mappings=team_data,
            suffixes_to_strip=suffixes,
            prefixes_to_strip=prefixes,
            youth_keywords=youth_data,
            youth_patterns=patterns,
            common_suffixes=suffix_data,
        )


# =============================================================================
# Hyper-Parameters Configuration
# =============================================================================

@dataclass
class HyperParametersConfig:
    """超参数配置"""

    # Fatigue Index Parameters
    busy_week_threshold: int = 4
    default_rest_days: int = 14

    # Unavailable Parameters
    star_market_value: float = 30000000  # 30M

    # Feature Extraction Parameters
    core_player_threshold: float = 0.7
    sparsity_threshold: float = 0.90
    excellent_threshold: int = 100
    good_threshold: int = 80
    fair_threshold: int = 50
    minimum_threshold: int = 30

    # Similarity Thresholds
    team_match_threshold: float = 85.0
    excellent_confidence_min: int = 95
    good_confidence_min: int = 85
    fair_confidence_min: int = 70
    reject_confidence_below: int = 70
    youth_penalty_ratio: float = 0.5

    # Odds Integrity Parameters
    min_payout: float = 1.02
    max_payout: float = 1.08
    min_odds_value: float = 0.01

    # Database Parameters
    pool_size: int = 15
    pool_max_overflow: int = 20
    pool_timeout: int = 10
    pool_recycle: int = 600
    query_timeout: int = 30000
    connection_timeout: int = 10000

    # Crawler Parameters
    default_delay: float = 5.0
    min_delay: float = 3.0
    max_delay: float = 15.0
    max_retries: int = 3
    retry_backoff_multiplier: float = 2.0
    retry_max_delay: int = 10000
    retry_jitter_range: float = 0.1
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: int = 60
    circuit_success_threshold: int = 2
    browser_pool_size: int = 5

    # League Classification
    top_5_leagues: list[str] = field(default_factory=lambda: [
        "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"
    ])

    # Performance Benchmarks
    target_inference_latency_ms: int = 100
    target_fotmob_api_latency_s: float = 3.0
    target_oddsportal_rpa_latency_s: float = 8.0
    max_memory_mb: int = 8192
    max_cpu_cores: int = 4
    min_data_completeness: float = 0.95
    min_mapping_success_rate: float = 0.90

    # Cache Configuration
    cache_enable: bool = True
    cache_size: int = 1000
    cache_ttl_seconds: int = 3600

    # Logging Configuration
    logging_level: str = "INFO"

    @classmethod
    def from_yaml(cls, yaml_path: Path = HYPER_PARAMETERS_PATH) -> "HyperParametersConfig":
        """从 YAML 文件加载配置"""
        if not yaml_path.exists():
            logger.warning(f"Hyper parameters file not found: {yaml_path}, using defaults")
            return cls()

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Extract sections
        fatigue_data = data.get("fatigue", {})
        unavailable_data = data.get("unavailable", {})
        feature_data = data.get("feature_extraction", {})
        similarity_data = data.get("similarity", {})
        odds_data = data.get("odds_integrity", {})
        db_data = data.get("database", {})
        crawler_data = data.get("crawler", {})
        leagues_data = data.get("leagues", {})
        performance_data = data.get("performance", {})
        cache_data = data.get("cache", {})
        logging_data = data.get("logging", {})

        # Extract bridge confidence
        bridge_conf = similarity_data.get("bridge_confidence", {})
        excellent_min = bridge_conf.get("excellent_min", 95)
        good_min = bridge_conf.get("good_min", 85)
        fair_min = bridge_conf.get("fair_min", 70)
        reject_below = similarity_data.get("bridge_confidence", {}).get("reject_below", 70)

        # Extract feature richness thresholds
        richness_data = feature_data.get("feature_richness", {})

        # Extract circuit breaker
        circuit_data = crawler_data.get("circuit_breaker", {})

        # Extract ghost settings
        ghost_data = crawler_data.get("ghost", {})

        return cls(
            # Fatigue
            busy_week_threshold=fatigue_data.get("busy_week_threshold", 4),
            default_rest_days=fatigue_data.get("default_rest_days", 14),
            # Unavailable
            star_market_value=unavailable_data.get("star_market_value", 30000000),
            # Feature Extraction
            core_player_threshold=feature_data.get("core_player_threshold", 0.7),
            sparsity_threshold=feature_data.get("sparsity_threshold", 0.90),
            excellent_threshold=richness_data.get("excellent_threshold", 100),
            good_threshold=richness_data.get("good_threshold", 80),
            fair_threshold=richness_data.get("fair_threshold", 50),
            minimum_threshold=richness_data.get("minimum_threshold", 30),
            # Similarity
            team_match_threshold=similarity_data.get("team_match_threshold", 85.0),
            excellent_confidence_min=excellent_min,
            good_confidence_min=good_min,
            fair_confidence_min=fair_min,
            reject_confidence_below=reject_below,
            youth_penalty_ratio=similarity_data.get("youth_penalty_ratio", 0.5),
            # Odds Integrity
            min_payout=odds_data.get("min_payout", 1.02),
            max_payout=odds_data.get("max_payout", 1.08),
            min_odds_value=odds_data.get("min_odds_value", 0.01),
            # Database
            pool_size=db_data.get("pool_size", 15),
            pool_max_overflow=db_data.get("pool_max_overflow", 20),
            pool_timeout=db_data.get("pool_timeout", 10),
            pool_recycle=db_data.get("pool_recycle", 600),
            query_timeout=db_data.get("query_timeout", 30000),
            connection_timeout=db_data.get("connection_timeout", 10000),
            # Crawler
            default_delay=crawler_data.get("default_delay", 5.0),
            min_delay=crawler_data.get("min_delay", 3.0),
            max_delay=crawler_data.get("max_delay", 15.0),
            max_retries=crawler_data.get("max_retries", 3),
            retry_backoff_multiplier=crawler_data.get("retry_backoff_multiplier", 2.0),
            retry_max_delay=crawler_data.get("retry_max_delay", 10000),
            retry_jitter_range=crawler_data.get("retry_jitter_range", 0.1),
            circuit_failure_threshold=circuit_data.get("failure_threshold", 5),
            circuit_recovery_timeout=circuit_data.get("recovery_timeout", 60),
            circuit_success_threshold=circuit_data.get("success_threshold", 2),
            browser_pool_size=ghost_data.get("browser_pool_size", 5),
            # Leagues
            top_5_leagues=leagues_data.get("top_5_leagues", [
                "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"
            ]),
            # Performance
            target_inference_latency_ms=performance_data.get("target_inference_latency_ms", 100),
            target_fotmob_api_latency_s=performance_data.get("target_fotmob_api_latency_s", 3.0),
            target_oddsportal_rpa_latency_s=performance_data.get("target_oddsportal_rpa_latency_s", 8.0),
            max_memory_mb=performance_data.get("max_memory_mb", 8192),
            max_cpu_cores=performance_data.get("max_cpu_cores", 4),
            min_data_completeness=performance_data.get("min_data_completeness", 0.95),
            min_mapping_success_rate=performance_data.get("min_mapping_success_rate", 0.90),
            # Cache
            cache_enable=cache_data.get("enable", True),
            cache_size=cache_data.get("size", 1000),
            cache_ttl_seconds=cache_data.get("ttl_seconds", 3600),
            # Logging
            logging_level=logging_data.get("level", "INFO"),
        )


# =============================================================================
# Singleton Instances
# =============================================================================

_team_aliases_config: Optional[TeamAliasesConfig] = None
_hyper_parameters_config: Optional[HyperParametersConfig] = None


def get_team_aliases_config() -> TeamAliasesConfig:
    """获取队名映射配置单例"""
    global _team_aliases_config
    if _team_aliases_config is None:
        _team_aliases_config = TeamAliasesConfig.from_json()
    return _team_aliases_config


def get_hyper_parameters_config() -> HyperParametersConfig:
    """获取超参数配置单例"""
    global _hyper_parameters_config
    if _hyper_parameters_config is None:
        _hyper_parameters_config = HyperParametersConfig.from_yaml()
    return _hyper_parameters_config


# =============================================================================
# Type Aliases
# =============================================================================

# 常用类型别名
TeamMapping = dict[str, str]
SuffixList = list[str]
PatternList = list[str]
