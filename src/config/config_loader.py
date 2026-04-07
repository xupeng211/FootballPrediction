#!/usr/bin/env python3
"""
V79.100 Configuration Loader - Legacy 兼容层
=============================================

⚠️ V4.15 声明: 此模块仅被 legacy 代码使用。
新代码请使用 src/config/__init__.py 作为配置源。

提供从外部化配置文件加载配置的功能：
1. team_aliases.json - 队名映射
2. hyper_parameters.yaml - 超参数阈值

Author: V79.100 Engineering Team
Version: V79.100-legacy
Date: 2026-01-25
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
import logging
from pathlib import Path

import yaml  # type: ignore[import-untyped]

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
    def from_json(cls, json_path: Path = TEAM_ALIASES_PATH) -> TeamAliasesConfig:
        """从 JSON 文件加载配置"""
        if not json_path.exists():
            logger.warning("Team aliases file not found: %s, using defaults", json_path)
            return cls()

        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        team_data = data.get("team_name_mappings", {})
        suffixes = data.get("suffixes_to_strip", [])
        prefixes = data.get("prefixes_to_strip", [])
        youth_data = data.get("youth_keywords", {})
        patterns = data.get("youth_patterns", [])
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

    @classmethod
    def from_yaml(cls, yaml_path: Path = HYPER_PARAMETERS_PATH) -> HyperParametersConfig:
        """从 YAML 文件加载配置"""
        if not yaml_path.exists():
            logger.warning("Hyper parameters file not found: %s, using defaults", yaml_path)
            return cls()

        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        fatigue_data = data.get("fatigue", {})
        unavailable_data = data.get("unavailable", {})
        feature_data = data.get("feature_extraction", {})
        similarity_data = data.get("similarity", {})
        odds_data = data.get("odds_integrity", {})

        bridge_conf = similarity_data.get("bridge_confidence", {})
        richness_data = feature_data.get("feature_richness", {})

        return cls(
            busy_week_threshold=fatigue_data.get("busy_week_threshold", 4),
            default_rest_days=fatigue_data.get("default_rest_days", 14),
            star_market_value=unavailable_data.get("star_market_value", 30000000),
            core_player_threshold=feature_data.get("core_player_threshold", 0.7),
            sparsity_threshold=feature_data.get("sparsity_threshold", 0.90),
            excellent_threshold=richness_data.get("excellent_threshold", 100),
            good_threshold=richness_data.get("good_threshold", 80),
            fair_threshold=richness_data.get("fair_threshold", 50),
            minimum_threshold=richness_data.get("minimum_threshold", 30),
            team_match_threshold=similarity_data.get("team_match_threshold", 85.0),
            excellent_confidence_min=bridge_conf.get("excellent_min", 95),
            good_confidence_min=bridge_conf.get("good_min", 85),
            fair_confidence_min=bridge_conf.get("fair_min", 70),
            reject_confidence_below=bridge_conf.get("reject_below", 70),
            youth_penalty_ratio=similarity_data.get("youth_penalty_ratio", 0.5),
            min_payout=odds_data.get("min_payout", 1.02),
            max_payout=odds_data.get("max_payout", 1.08),
            min_odds_value=odds_data.get("min_odds_value", 0.01),
        )


@lru_cache(maxsize=1)
def get_team_aliases_config() -> TeamAliasesConfig:
    """获取队名映射配置单例"""
    return TeamAliasesConfig.from_json()


@lru_cache(maxsize=1)
def get_hyper_parameters_config() -> HyperParametersConfig:
    """获取超参数配置单例"""
    return HyperParametersConfig.from_yaml()


# 版本标识
__version__ = "V79.100-legacy"
