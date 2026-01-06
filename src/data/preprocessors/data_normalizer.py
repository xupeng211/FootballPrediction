"""
数据格式标准化器 - 统一处理不同格式的比赛数据

支持多种数据格式的标准化处理，确保特征提取器能够接收一致的数据格式。
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class DataFormatNormalizer:
    """数据格式标准化器

    将不同来源和格式的比赛数据统一转换为标准格式，供特征提取器使用。

    支持的输入格式:
    - technical_features: FotMob API 的 technical_features 格式
    - home_stats_away_stats: 主客队统计分离格式
    - normalized: 已经标准化的扁平格式

    输出格式: 标准化的扁平字典，包含所有必需字段
    """

    # 字段映射表 - 不同格式到标准格式的映射
    FIELD_MAPPINGS = {
        "technical_features": {
            "home_team": ["homeTeam", "home_team", "team"],
            "away_team": ["awayTeam", "away_team", "team"],
            "expected_goals": ["expectedGoals", "xg", "expected_goals"],
            "shots_on_target": ["shotsOnTarget", "shots_on_target", "sot"],
            "possession": ["possession", "ballPossession", "possession%"],
            "shots": ["totalShots", "shots", "total_shots"],
            "corners": ["corners", "corner_kicks"],
        },
        "home_stats_away_stats": {
            "expected_goals": ["xg", "expectedGoals", "expected_goals"],
            "shots_on_target": ["shotsOnTarget", "shots_on_target", "sot"],
            "possession": ["possession", "ballPossession"],
            "shots": ["totalShots", "shots"],
            "corners": ["corners"],
        },
    }

    # 标准字段名（输出格式）
    STANDARD_FIELDS = [
        # 基础信息
        "external_id",
        "home_team",
        "away_team",
        "match_time",
        "home_score",
        "away_score",
        "actual_result",
        "league_id",
        "league_name",
        "season",
        # 主队统计
        "home_expected_goals",
        "home_shots_on_target",
        "home_possession",
        "home_shots",
        "home_corners",
        # 客队统计
        "away_expected_goals",
        "away_shots_on_target",
        "away_possession",
        "away_shots",
        "away_corners",
        # 合并统计（用于向后兼容）
        "expected_goals",
        "shots_on_target",
        "possession",
        "shots",
        "corners",
    ]

    def __init__(self, strict_mode: bool = False):
        """初始化数据格式标准化器

        Args:
            strict_mode: 严格模式，如果为 True 则遇到无法标准化的字段时抛出异常
        """
        self.strict_mode = strict_mode
        self._normalization_stats = {
            "total_processed": 0,
            "format_counts": {},
            "field_errors": 0,
        }

    def detect_format(self, raw_data: dict[str, Any]) -> str | None:
        """检测数据格式类型

        Args:
            raw_data: 原始数据字典

        Returns:
            格式类型：'technical_features', 'home_stats_away_stats', 'normalized', 或 None
        """
        if not raw_data:
            return None

        # 检查 technical_features 格式
        if "technical_features" in raw_data:
            return "technical_features"

        # 检查 home_stats_away_stats 格式
        if "home_stats" in raw_data and "away_stats" in raw_data:
            return "home_stats_away_stats"

        # 检查是否已经是标准化格式
        has_home_prefix = any(k.startswith("home_") for k in raw_data)
        has_away_prefix = any(k.startswith("away_") for k in raw_data)

        if has_home_prefix and has_away_prefix:
            return "normalized"

        # 默认视为简化格式
        return "simple"

    def normalize(self, raw_data: dict[str, Any], format_hint: str | None = None) -> dict[str, Any]:
        """标准化数据格式

        Args:
            raw_data: 原始数据字典
            format_hint: 可选的格式提示（跳过自动检测）

        Returns:
            标准化的扁平字典
        """
        self._normalization_stats["total_processed"] += 1

        # 检测或使用提示的格式
        data_format = format_hint or self.detect_format(raw_data)

        if not data_format:
            logger.warning("无法检测数据格式，使用原始数据")
            return raw_data

        # 更新统计
        self._normalization_stats["format_counts"][data_format] = (
            self._normalization_stats["format_counts"].get(data_format, 0) + 1
        )

        # 根据格式调用相应的标准化方法
        if data_format == "technical_features":
            normalized = self._normalize_technical_features(raw_data)
        elif data_format == "home_stats_away_stats":
            normalized = self._normalize_stats_format(raw_data)
        elif data_format == "normalized":
            normalized = self._normalize_already_normalized(raw_data)
        elif data_format == "simple":
            normalized = self._normalize_simple_format(raw_data)
        else:
            logger.warning(f"未知数据格式: {data_format}，使用原始数据")
            normalized = raw_data

        return normalized

    def _normalize_technical_features(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """标准化 technical_features 格式

        FotMob API 返回的格式示例:
        {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "technical_features": {
                "stats": {
                    "expected_goals": {"home": 1.2, "away": 0.8},
                    ...
                }
            }
        }
        """
        normalized = {}
        tech = raw_data.get("technical_features", {})

        # 基础信息
        normalized["home_team"] = raw_data.get("home_team") or tech.get("homeTeam")
        normalized["away_team"] = raw_data.get("away_team") or tech.get("awayTeam")
        normalized["match_time"] = raw_data.get("match_time")
        normalized["external_id"] = raw_data.get("external_id")
        normalized["league_id"] = raw_data.get("league_id", 47)  # 默认英超
        normalized["season"] = raw_data.get("season", "2324")
        normalized["home_score"] = raw_data.get("home_score")
        normalized["away_score"] = raw_data.get("away_score")

        # 从 stats 中提取统计数据
        stats = tech.get("stats", {})

        # 处理每个统计字段
        stat_mappings = {
            "expected_goals": "expected_goals",
            "shots_on_target": "shots_on_target",
            "possession": "possession",
            "shots": "shots",
            "corners": "corners",
        }

        for standard_field, stat_key in stat_mappings.items():
            stat_data = stats.get(stat_key, {})

            # 检查是否有 home/away 分离的数据
            if isinstance(stat_data, dict):
                home_val = stat_data.get("home")
                away_val = stat_data.get("away")

                # 主队统计
                if home_val is not None:
                    normalized[f"home_{standard_field}"] = self._safe_float_convert(home_val)

                # 客队统计
                if away_val is not None:
                    normalized[f"away_{standard_field}"] = self._safe_float_convert(away_val)

                # 合并统计（用于向后兼容）
                if home_val is not None and away_val is not None:
                    normalized[standard_field] = self._safe_float_convert(home_val)  # 默认使用主队

            # 检查是否有 value 字段（单值格式）
            elif "value" in stat_data:
                normalized[standard_field] = self._safe_float_convert(stat_data["value"])

        return normalized

    def _normalize_stats_format(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """标准化 home_stats/away_stats 格式

        示例:
        {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_stats": {"xg": 1.2, "possession": 55},
            "away_stats": {"xg": 0.8, "possession": 45}
        }
        """
        normalized = {}

        # 基础信息
        normalized["home_team"] = raw_data.get("home_team")
        normalized["away_team"] = raw_data.get("away_team")
        normalized["match_time"] = raw_data.get("match_time")
        normalized["external_id"] = raw_data.get("external_id")
        normalized["league_id"] = raw_data.get("league_id", 47)
        normalized["season"] = raw_data.get("season", "2324")
        normalized["home_score"] = raw_data.get("home_score")
        normalized["away_score"] = raw_data.get("away_score")

        # 主队统计
        home_stats = raw_data.get("home_stats", {})
        normalized["home_expected_goals"] = self._extract_field(home_stats, ["xg", "expectedGoals", "expected_goals"])
        normalized["home_shots_on_target"] = self._extract_field(
            home_stats, ["shotsOnTarget", "shots_on_target", "sot"]
        )
        normalized["home_possession"] = self._extract_field(home_stats, ["possession", "ballPossession"])
        normalized["home_shots"] = self._extract_field(home_stats, ["totalShots", "shots"])
        normalized["home_corners"] = self._extract_field(home_stats, ["corners"])

        # 客队统计
        away_stats = raw_data.get("away_stats", {})
        normalized["away_expected_goals"] = self._extract_field(away_stats, ["xg", "expectedGoals", "expected_goals"])
        normalized["away_shots_on_target"] = self._extract_field(
            away_stats, ["shotsOnTarget", "shots_on_target", "sot"]
        )
        normalized["away_possession"] = self._extract_field(away_stats, ["possession", "ballPossession"])
        normalized["away_shots"] = self._extract_field(away_stats, ["totalShots", "shots"])
        normalized["away_corners"] = self._extract_field(away_stats, ["corners"])

        # 合并统计（用于向后兼容）
        normalized["expected_goals"] = normalized.get("home_expected_goals")
        normalized["shots_on_target"] = normalized.get("home_shots_on_target")
        normalized["possession"] = normalized.get("home_possession")
        normalized["shots"] = normalized.get("home_shots")
        normalized["corners"] = normalized.get("home_corners")

        return normalized

    def _normalize_already_normalized(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """处理已经是标准化格式的数据

        只需确保所有必需字段存在，并填充默认值
        """
        normalized = raw_data.copy()

        # 确保基础字段存在
        if "league_id" not in normalized:
            normalized["league_id"] = 47
        if "season" not in normalized:
            normalized["season"] = "2324"

        return normalized

    def _normalize_simple_format(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """处理简化格式数据

        简化格式可能只有部分字段，尝试智能推断
        """
        normalized = {}

        # 基础信息
        normalized["home_team"] = raw_data.get("home_team")
        normalized["away_team"] = raw_data.get("away_team")
        normalized["match_time"] = raw_data.get("match_time")
        normalized["external_id"] = raw_data.get("external_id")
        normalized["league_id"] = raw_data.get("league_id", 47)
        normalized["season"] = raw_data.get("season", "2324")
        normalized["home_score"] = raw_data.get("home_score")
        normalized["away_score"] = raw_data.get("away_score")

        # 尝试推断主客队统计
        # 如果只有 expected_goals，默认分配给主队
        if "expected_goals" in raw_data and "home_expected_goals" not in raw_data:
            normalized["home_expected_goals"] = self._safe_float_convert(raw_data["expected_goals"])

        # 如果有 xg，转换为 expected_goals
        if "xg" in raw_data and "expected_goals" not in raw_data:
            normalized["expected_goals"] = self._safe_float_convert(raw_data["xg"])

        # 其他统计字段
        stat_fields = {
            "shots_on_target": ["shotsOnTarget", "sot"],
            "possession": ["possession", "ballPossession"],
            "shots": ["totalShots"],
            "corners": ["corners"],
        }

        for standard_field, alt_names in stat_fields.items():
            value = self._extract_field(raw_data, alt_names)
            if value is not None:
                normalized[standard_field] = value
                normalized[f"home_{standard_field}"] = value

        return normalized

    def _extract_field(self, data: dict[str, Any], possible_names: list) -> float | None:
        """从字典中提取字段（尝试多个可能的名称）

        Args:
            data: 数据字典
            possible_names: 可能的字段名列表（按优先级排序）

        Returns:
            字段值（转换为 float）或 None
        """
        for name in possible_names:
            if name in data and data[name] is not None:
                return self._safe_float_convert(data[name])
        return None

    def _safe_float_convert(self, value: Any) -> float | None:
        """安全地将值转换为 float

        Args:
            value: 要转换的值

        Returns:
            转换后的 float 值，如果转换失败则返回 None
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            if self.strict_mode:
                raise ValueError(f"无法将值转换为 float: {value}")
            self._normalization_stats["field_errors"] += 1
            return None

    def normalize_batch(self, data_list: list) -> list:
        """批量标准化数据

        Args:
            data_list: 原始数据列表

        Returns:
            标准化后的数据列表
        """
        return [self.normalize(data) for data in data_list]

    def normalize_dataframe(self, df: pd.DataFrame, format_hint: str | None = None) -> pd.DataFrame:
        """标准化 DataFrame 格式

        Args:
            df: 原始 DataFrame
            format_hint: 可选的格式提示

        Returns:
            标准化后的 DataFrame
        """
        # 将每一行转换为字典，标准化后重新组合
        normalized_dicts = []

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            normalized = self.normalize(row_dict, format_hint)
            normalized_dicts.append(normalized)

        return pd.DataFrame(normalized_dicts)

    def get_statistics(self) -> dict[str, Any]:
        """获取标准化统计信息

        Returns:
            统计信息字典
        """
        return self._normalization_stats.copy()

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._normalization_stats = {
            "total_processed": 0,
            "format_counts": {},
            "field_errors": 0,
        }


# 便捷函数
def normalize_match_data(raw_data: dict[str, Any], strict_mode: bool = False) -> dict[str, Any]:
    """标准化单场比赛数据（便捷函数）

    Args:
        raw_data: 原始数据字典
        strict_mode: 严格模式

    Returns:
        标准化后的数据字典
    """
    normalizer = DataFormatNormalizer(strict_mode=strict_mode)
    return normalizer.normalize(raw_data)


def detect_data_format(raw_data: dict[str, Any]) -> str | None:
    """检测数据格式（便捷函数）

    Args:
        raw_data: 原始数据字典

    Returns:
        格式类型字符串
    """
    normalizer = DataFormatNormalizer()
    return normalizer.detect_format(raw_data)
