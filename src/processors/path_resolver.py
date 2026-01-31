"""
V41.500 Path Resolver - Schema-Agnostic 路径解析器
===================================================

功能：
1. 从 schema_map.yaml 读取路径配置
2. 提供安全的路径访问（带默认值）
3. 支持 Schema 变化时无需修改代码

Author: V41.500 Pipeline Team
Version: V41.500 "The Automated Pipeline"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


# =============================================================================
# Schema Map Configuration
# =============================================================================

class SchemaMapConfig:
    """Schema Map 配置管理器"""

    _config_cache: dict[str, Any] | None

    def __init__(self, config_path: str | Path | None = None) -> None:
        """
        初始化 Schema Map 配置

        Args:
            config_path: schema_map.yaml 文件路径
        """
        if config_path is None:
            # 默认路径：项目根目录/config/schema_map.yaml
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "schema_map.yaml"

        self.config_path: Path = Path(config_path) if isinstance(config_path, str) else config_path
        self._config_cache = None

    def load_config(self) -> dict[str, Any]:
        """加载 YAML 配置文件"""
        if self._config_cache is not None:
            return self._config_cache

        if not self.config_path.exists():
            logger.warning("Schema map config not found: %s", self.config_path)
            self._config_cache = {}
            return {}

        try:
            with self.config_path.open(encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                self._config_cache = loaded if isinstance(loaded, dict) else {}
            logger.info("Loaded schema map from: %s", self.config_path)
            return self._config_cache
        except Exception as e:
            logger.exception("Failed to load schema map: %s", e)
            self._config_cache = {}
            return {}

    @property
    def fotmob(self) -> dict:
        """FotMob 路径配置"""
        return self.load_config().get("fotmob", {})

    @property
    def database(self) -> dict:
        """数据库表路径配置"""
        return self.load_config().get("database", {})

    @property
    def feature_params(self) -> dict:
        """特征计算参数配置"""
        return self.load_config().get("feature_params", {})

    @property
    def defaults(self) -> dict:
        """默认值配置"""
        return self.load_config().get("defaults", {})

    @property
    def feature_output(self) -> dict:
        """特征输出映射配置"""
        return self.load_config().get("feature_output", {})

    def get_param(self, category: str, key: str, default: Any = None) -> Any:
        """
        获取特征计算参数

        Args:
            category: 参数类别（如 fatigue, unavailability）
            key: 参数键
            default: 默认值

        Returns:
            参数值
        """
        return self.feature_params.get(category, {}).get(key, default)

    def get_default(self, key: str, default: Any = None) -> Any:
        """
        获取默认值

        Args:
            key: 默认值键（如 market_value, rating）
            default: 备用默认值

        Returns:
            默认值
        """
        missing_defaults = self.defaults.get("missing_values", {})
        return missing_defaults.get(key, default)


# =============================================================================
# Path Resolver
# =============================================================================

class PathResolver:
    """
    Schema-Agnostic 路径解析器

    功能：
    1. 安全的嵌套路径访问
    2. 带默认值的容错读取
    3. 支持 JSON 字符串自动解析
    """

    def __init__(self, schema_config: SchemaMapConfig | None = None):
        """
        初始化路径解析器

        Args:
            schema_config: Schema Map 配置对象
        """
        self.schema = schema_config or SchemaMapConfig()

    def resolve_path(
        self,
        data: dict[str, Any] | str | None,
        path: str,
        default: Any = None
    ) -> Any:
        """
        安全地解析嵌套路径

        Args:
            data: 数据字典或 JSON 字符串
            path: 点分隔的路径，如 "content.lineup.homeTeam.unavailable"
            default: 找不到时的默认值

        Returns:
            路径对应的值，或默认值

        Examples:
            >>> resolver.resolve_path(data, "content.lineup.homeTeam.unavailable", [])
            >>> resolver.resolve_path(data, "user.profile.name", "Unknown")
        """
        if data is None:
            return default

        # 解析 JSON 字符串
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return default

        if not isinstance(data, dict):
            return default

        # 分割路径
        keys = path.split(".")
        current = data

        try:
            for key in keys:
                # 处理数组索引（如 unavailable[0]）
                if "[" in key and key.endswith("]"):
                    base_key = key[:key.index("[")]
                    index_str = key[key.index("[") + 1:key.index("]")]
                    try:
                        index = int(index_str)
                    except ValueError:
                        return default

                    current = current.get(base_key, {})
                    if isinstance(current, list) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return default
                else:
                    current = current.get(key)
                    if current is None:
                        return default

            return current

        except (KeyError, TypeError, AttributeError):
            return default

    def get_unavailable_players(
        self,
        l2_raw_json: dict[str, Any] | str | None,
        team: str = "home"  # "home" or "away"
    ) -> list[dict[str, Any]]:
        """
        获取缺阵球员列表

        Args:
            l2_raw_json: FotMob L2 原始 JSON
            team: "home" 或 "away"

        Returns:
            缺阵球员列表
        """
        path = f"content.lineup.{team}Team.unavailable"
        result = self.resolve_path(l2_raw_json, path, [])
        return result if isinstance(result, list) else []

    def get_starters(
        self,
        l2_raw_json: dict[str, Any] | str | None,
        team: str = "home"  # "home" or "away"
    ) -> list[dict[str, Any]]:
        """
        获取首发球员列表

        Args:
            l2_raw_json: FotMob L2 原始 JSON
            team: "home" 或 "away"

        Returns:
            首发球员列表
        """
        path = f"content.lineup.{team}Team.starters"
        result = self.resolve_path(l2_raw_json, path, [])
        return result if isinstance(result, list) else []

    def get_team_rating(
        self,
        l2_raw_json: dict[str, Any] | str | None,
        team: str = "home"  # "home" or "away"
    ) -> float:
        """
        获取球队评分

        Args:
            l2_raw_json: FotMob L2 原始 JSON
            team: "home" 或 "away"

        Returns:
            球队评分（或默认值 6.0）
        """
        path = f"content.lineup.{team}Team.rating"
        result = self.resolve_path(l2_raw_json, path, 6.0)
        try:
            return float(result)
        except (TypeError, ValueError):
            return 6.0

    def get_player_market_value(
        self,
        player: dict[str, Any],
        default: float = 0.0
    ) -> float:
        """
        获取球员身价（带容错）

        Args:
            player: 球员数据字典
            default: 默认值

        Returns:
            球员身价（欧元）
        """
        mv = player.get("marketValue") or player.get("market_value") or default
        try:
            return float(mv)
        except (TypeError, ValueError):
            return default

    def get_player_rating(
        self,
        player: dict[str, Any],
        default: float = 6.0
    ) -> float:
        """
        获取球员评分（带容错）

        Args:
            player: 球员数据字典
            default: 默认值

        Returns:
            球员评分
        """
        # 从 performance 字典中获取评分
        performance = player.get("performance", {})
        if isinstance(performance, dict):
            rating = performance.get("rating")
        else:
            rating = player.get("rating")

        try:
            return float(rating) if rating is not None else default
        except (TypeError, ValueError):
            return default

    def get_unavailability_type(
        self,
        player: dict[str, Any]
    ) -> str:
        """
        获取缺阵类型（伤病/禁赛/其他）

        Args:
            player: 球员数据字典

        Returns:
            "injury", "suspension", 或 "unknown"
        """
        unavailability = player.get("unavailability", {})
        if isinstance(unavailability, dict):
            unavail_type = unavailability.get("type", "unknown")
        else:
            unavail_type = "unknown"

        unavail_type = str(unavail_type).lower()

        # 根据 schema_map.yaml 中的分类
        injury_types = self.schema.get_param("unavailability", "injury_types", ["injury"])
        suspension_types = self.schema.get_param("unavailability", "suspension_types", ["suspension", "suspended"])

        if any(t in unavail_type for t in injury_types):
            return "injury"
        if any(t in unavail_type for t in suspension_types):
            return "suspension"
        return "unknown"


# =============================================================================
# Singleton Instance
# =============================================================================

_path_resolver_instance = None


def get_path_resolver() -> PathResolver:
    """获取路径解析器单例"""
    global _path_resolver_instance
    if _path_resolver_instance is None:
        _path_resolver_instance = PathResolver()
    return _path_resolver_instance


def get_schema_config() -> SchemaMapConfig:
    """获取 Schema Map 配置单例"""
    global _path_resolver_instance
    if _path_resolver_instance is None:
        _path_resolver_instance = PathResolver()
    return _path_resolver_instance.schema
