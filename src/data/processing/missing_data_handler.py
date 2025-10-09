"""
缺失数据处理器

实现处理数据缺失的逻辑，包括填充、插值、删除等策略。

填充策略：
- 球队统计：使用历史平均值
- 球员统计：使用位置中位数
- 天气数据：使用季节正常值
- 赔率数据：使用市场共识

基于 DATA_DESIGN.md 第4.3节设计。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import get_settings
from src.database.connection import DatabaseManager
from src.database.models.features import Features


class MissingDataHandler:
    """
    缺失数据处理器

    提供多种策略来处理数据集中的缺失值，
    确保数据完整性，为模型训练做准备。
    """

    FILL_STRATEGIES = {
        "team_stats": "historical_average",  # 历史平均值
        "player_stats": "position_median",  # 位置中位数
        "weather": "seasonal_normal",  # 季节正常值
        "odds": "market_consensus",  # 市场共识
    }

    _DEFAULT_FALLBACK_AVERAGES: Dict[str, float] = {
        "avg_possession": 50.0,
        "avg_shots_per_game": 12.5,
        "avg_goals_per_game": 1.5,
        "league_position": 10.0,
    }

    def __init__(self):
        """初始化缺失数据处理器"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"handler.{self.__class__.__name__}")
        self._feature_average_cache: Dict[str, float] = {}
        self._settings = get_settings()
        self._fallback_defaults = self._load_fallback_defaults()

    async def handle_missing_match_data(
        self, match_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理比赛数据中的缺失值

        Args:
            match_data: 清洗后的比赛数据

        Returns:
            Dict[str, Any]: 处理缺失值后的数据
        """
        # 示例：填充缺失的比分
        if match_data.get("home_score") is None:
            match_data["home_score"] = 0
            self.logger.debug(
                "Filled missing home_score for match %s",
                match_data.get("external_match_id") or match_data.get("id"),
            )

        if match_data.get("away_score") is None:
            match_data["away_score"] = 0
            self.logger.debug(
                "Filled missing away_score for match %s",
                match_data.get("external_match_id") or match_data.get("id"),
            )

        # 示例：填充缺失的场地和裁判
        if not match_data.get("venue"):
            match_data["venue"] = "Unknown"

        if not match_data.get("referee"):
            match_data["referee"] = "Unknown"

        return match_data

    async def handle_missing_features(
        self, match_id: int, features_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        处理特征数据中的缺失值

        Args:
            match_id: 比赛ID
            features_df: 特征数据DataFrame

        Returns:
            pd.DataFrame: 处理缺失值后的特征数据
        """
        try:
            # 遍历所有特征列
            for col in features_df.columns:
                if features_df[col].isnull().any():
                    fill_strategy = self.FILL_STRATEGIES.get(str("team_stats"), "zero")

                    if fill_strategy == "historical_average":
                        # 使用历史平均值填充
                        historical_avg = await self._get_historical_average(col)
                        features_df[col].fillna(historical_avg, inplace=True)
                        self.logger.info(
                            f"Filled missing {col} with historical average ({historical_avg})"
                        )

                    elif fill_strategy == "median":
                        # 使用中位数填充
                        median_val = features_df[col].median()
                        features_df[col].fillna(median_val, inplace=True)

                    else:
                        # 默认使用0填充
                        features_df[col].fillna(0, inplace=True)

            return features_df

        except Exception as e:
            self.logger.error(
                f"Failed to handle missing features for match {match_id}: {str(e)}"
            )
            # 出错时返回原始数据
            return features_df

    async def _get_historical_average(self, feature_name: str) -> float:
        """
        获取特征的历史平均值

        Args:
            feature_name: 特征名称

        Returns:
            float: 历史平均值
        """
        if feature_name in self._feature_average_cache:
            return self._feature_average_cache[feature_name]

        column = getattr(Features, feature_name, None)
        if column is None:
            self.logger.warning(
                "Feature column %s does not exist on Features model; using default fallback.",
                feature_name,
            )
            return self._fallback_average(feature_name)

        try:
            async with self.db_manager.get_async_session() as session:
                stmt = select(func.avg(column))
                result = await session.execute(stmt)
                avg_value: Optional[float] = result.scalar()

                if avg_value is None:
                    avg_value = self._fallback_average(feature_name)
                else:
                    avg_value = float(avg_value)

                self._feature_average_cache[feature_name] = avg_value
                return avg_value

        except (RuntimeError, SQLAlchemyError) as exc:
            self.logger.warning(
                "Unable to query historical average for %s, fallback will be used. Error: %s",
                feature_name,
                exc,
            )
            return self._fallback_average(feature_name)

    def _fallback_average(self, feature_name: str) -> float:
        """提供默认平均值作为数据库不可用时的回退策略"""
        return self._fallback_defaults.get(str(feature_name), 0.0)

    def register_fallback_average(self, feature_name: str, value: float) -> None:
        """在运行时注册或覆盖指定特征的默认均值。"""

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            self.logger.warning("忽略无效的默认均值: %s=%s", feature_name, value)
            return

        self._fallback_defaults[feature_name] = numeric_value

    def _load_fallback_defaults(self) -> Dict[str, float]:
        """加载缺失值默认均值配置，支持环境变量或JSON配置文件。"""

        defaults = self._DEFAULT_FALLBACK_AVERAGES.copy()

        settings_json = getattr(self._settings, "missing_data_defaults_json", None)
        if settings_json:
            self._merge_default_source(defaults, settings_json, source="settings")

        candidate_paths: List[Path] = []
        settings_path = getattr(self._settings, "missing_data_defaults_path", None)
        if settings_path:
            candidate_paths.append(Path(settings_path))

        legacy_env_path = os.getenv("MISSING_DATA_DEFAULTS_PATH")
        if legacy_env_path:
            candidate_paths.append(Path(legacy_env_path))

        candidate_paths.append(Path("config/missing_data_defaults.json"))

        for path in candidate_paths:
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    self._merge_default_source(defaults, content, source=str(path))
                except Exception as exc:
                    self.logger.warning("读取缺失值默认配置失败: %s (%s)", path, exc)

                # 找到第一个有效文件即可
                break

        legacy_json = os.getenv("MISSING_DATA_DEFAULTS")
        if legacy_json:
            self._merge_default_source(defaults, legacy_json, source="env")

        return defaults

    def _merge_default_source(
        self, defaults: Dict[str, float], raw_json: str, *, source: str
    ) -> None:
        """将来自字符串的 JSON 数据合并到默认映射。"""

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            self.logger.warning("解析默认均值 JSON 失败（来源: %s）: %s", source, exc)
            return

        if not isinstance(payload, dict):
            self.logger.warning("默认均值配置必须是对象（来源: %s）", source)
            return

        for key, value in payload.items():
            try:
                defaults[key] = float(value)
            except (TypeError, ValueError):
                self.logger.warning(
                    "忽略无效的默认均值（来源: %s）: %s=%s", source, key, value
                )

    def interpolate_time_series_data(self, data: pd.Series) -> pd.Series:
        """
        使用插值法填充时间序列数据

        Args:
            data: 时间序列数据

        Returns:
            pd.Series: 填充后的数据
        """
        try:
            # 使用线性插值
            return data.interpolate(method="linear")
        except Exception as e:
            self.logger.error(f"Failed to interpolate time series data: {str(e)}")
            return data

    def remove_rows_with_missing_critical_data(
        self, df: pd.DataFrame, critical_columns: List[str]
    ) -> pd.DataFrame:
        """
        删除包含关键数据缺失的行

        Args:
            df: 数据集
            critical_columns: 关键列列表

        Returns:
            pd.DataFrame: 清理后的数据集
        """
        try:
            original_rows = len(df)
            cleaned_df = df.dropna(subset=critical_columns)
            removed_rows = original_rows - len(cleaned_df)

            if removed_rows > 0:
                self.logger.warning(
                    f"Removed {removed_rows} rows due to missing critical data in columns: {critical_columns}"
                )

            return cleaned_df

        except Exception as e:
            self.logger.error(f"Failed to remove rows with missing data: {str(e)}")
            return df

    def reload_fallback_defaults(self) -> None:
        """重新加载缺省均值配置并清除缓存，支持运行时热更新。"""

        self._fallback_defaults = self._load_fallback_defaults()
        self._feature_average_cache.clear()

    def clear_cached_averages(self) -> None:
        """清理历史均值缓存。"""

        self._feature_average_cache.clear()
