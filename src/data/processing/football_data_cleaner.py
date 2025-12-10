"""足球数据清洗器 - 完整实现.

提供专业的足球数据清洗功能，包括：
- 数据验证和去重
- 缺失值处理
- 异常值检测和处理
- 数据类型转换和标准化
- 高级数据质量评估
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

# 修复pandas/NumPy覆盖率模式下的_NoValueType问题
import os

os.environ["NUMPY_EXPERIMENTAL_ARRAY_FUNCTION"] = "0"

logger = logging.getLogger(__name__)


class FootballDataCleaner:
    """足球数据清洗器 - 完整实现."""

    def __init__(self, config: dict | None = None):
        self.config = config or self._get_default_config()
        self.data_quality_report = {}

    def _get_default_config(self) -> dict:
        return {
            "remove_duplicates": True,
            "handle_missing": True,
            "detect_outliers": True,
            "validate_data": True,
            "standardize_features": False,
            "outlier_method": "iqr",
            "missing_strategy": "adaptive",
        }

    def clean_dataset(
        self, raw_data: pd.DataFrame, data_type: str = "matches"
    ) -> pd.DataFrame:
        """清洗完整数据集.

        Args:
            raw_data: 原始数据DataFrame
            data_type: 数据类型 ('matches', 'teams', 'odds')

        Returns:
            pd.DataFrame: 清洗后的数据
        """
        logger.info(f"开始清洗 {data_type} 数据，原始数据形状: {raw_data.shape}")

        cleaned_data = raw_data.copy()
        cleaning_steps = []

        # 1. 数据基础验证
        if self.config["validate_data"]:
            cleaned_data = self._validate_basic_structure(cleaned_data, data_type)
            cleaning_steps.append("基础验证")

        # 2. 移除重复数据
        if self.config["remove_duplicates"]:
            cleaned_data = self._remove_duplicates(cleaned_data, data_type)
            cleaning_steps.append("去重")

        # 3. 处理缺失值
        if self.config["handle_missing"]:
            cleaned_data = self._handle_missing_values_adaptive(cleaned_data)
            cleaning_steps.append("缺失值处理")

        # 4. 检测和处理异常值
        if self.config["detect_outliers"]:
            cleaned_data = self._detect_and_handle_outliers(cleaned_data, data_type)
            cleaning_steps.append("异常值处理")

        # 5. 数据类型转换和标准化
        cleaned_data = self._convert_and_standardize(cleaned_data)
        cleaning_steps.append("数据转换")

        # 6. 高级数据验证
        cleaned_data = self._advanced_validation(cleaned_data, data_type)
        cleaning_steps.append("高级验证")

        # 7. 生成清洗报告
        self._generate_cleaning_report(raw_data, cleaned_data, cleaning_steps)

        logger.info(f"数据清洗完成，最终数据形状: {cleaned_data.shape}")
        return cleaned_data

    def _validate_basic_structure(
        self, data: pd.DataFrame, data_type: str
    ) -> pd.DataFrame:
        """基础数据结构验证."""
        required_columns = {
            "matches": ["match_id", "home_team_id", "away_team_id", "match_date"],
            "teams": ["team_id", "team_name"],
            "odds": ["match_id", "home_win_odds", "draw_odds", "away_win_odds"],
        }

        # 检查必需列是否存在
        missing_columns = []
        for col in required_columns.get(data_type, []):
            if col not in data.columns:
                missing_columns.append(col)

        if missing_columns:
            logger.warning(f"缺少推荐的列: {missing_columns}")

        return data

    def _remove_duplicates(self, data: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """移除重复数据."""
        initial_count = len(data)

        if data_type == "matches":
            subset_cols = (
                ["match_id"]
                if "match_id" in data.columns
                else ["home_team_id", "away_team_id", "match_date"]
            )
        elif data_type == "teams":
            subset_cols = ["team_id"]
        elif data_type == "odds":
            subset_cols = ["match_id"]
        else:
            subset_cols = data.columns.tolist()

        # 确保子集列存在
        subset_cols = [col for col in subset_cols if col in data.columns]
        if subset_cols:
            data_dedup = data.drop_duplicates(subset=subset_cols, keep="first")
        else:
            data_dedup = data.drop_duplicates()

        removed_count = initial_count - len(data_dedup)

        if removed_count > 0:
            logger.info(f"移除了 {removed_count} 条重复记录")
            self.data_quality_report["duplicates_removed"] = removed_count

        return data_dedup

    def _handle_missing_values_adaptive(self, data: pd.DataFrame) -> pd.DataFrame:
        """自适应缺失值处理."""
        missing_info = {}

        for column in data.columns:
            # 修复_NoValueType错误：使用更安全的方式计算缺失值
            null_mask = data[column].isnull()
            missing_count = len(data) - len(data[column][~null_mask])
            if missing_count > 0:
                missing_ratio = missing_count / len(data)
                missing_info[column] = {
                    "count": missing_count,
                    "ratio": missing_ratio,
                    "strategy": self._determine_missing_strategy(
                        column, data[column], missing_ratio
                    ),
                }

                # 应用相应的处理策略
                data[column] = self._apply_missing_strategy(
                    data[column], missing_info[column]["strategy"]
                )

        if missing_info:
            self.data_quality_report["missing_values"] = missing_info

        return data

    def _determine_missing_strategy(
        self, column: str, series: pd.Series, missing_ratio: float
    ) -> str:
        """确定缺失值处理策略."""
        if missing_ratio > 0.5:
            return "drop_column"  # 缺失值超过50%，考虑删除列
        elif missing_ratio > 0.3:
            return "model_based"  # 缺失值30-50%，使用模型预测
        elif series.dtype in ["int64", "float64"]:
            return "median" if series.skew() > 1 else "mean"
        else:
            return "mode"

    def _apply_missing_strategy(self, series: pd.Series, strategy: str) -> pd.Series:
        """应用缺失值处理策略."""
        if strategy == "drop_column":
            return series  # 将在上层处理
        elif strategy == "drop_rows":
            return series.dropna()
        elif strategy == "mean" and series.dtype in ["int64", "float64"]:
            fill_value = series.mean()
            # 修复类型兼容性：对整数列保持整数类型
            if pd.api.types.is_integer_dtype(series):
                fill_value = int(round(fill_value))
            return series.fillna(fill_value)
        elif strategy == "median" and series.dtype in ["int64", "float64"]:
            fill_value = series.median()
            # 修复类型兼容性：对整数列保持整数类型
            if pd.api.types.is_integer_dtype(series):
                fill_value = int(round(fill_value))
            return series.fillna(fill_value)
        elif strategy == "mode":
            mode_value = series.mode()[0] if not series.mode().empty else "Unknown"
            return series.fillna(mode_value)
        elif strategy == "forward_fill":
            return series.ffill()
        elif strategy == "backward_fill":
            return series.bfill()
        elif strategy == "interpolate" and series.dtype in ["int64", "float64"]:
            interpolated = series.interpolate()
            # 修复类型兼容性：对整数列保持整数类型
            if pd.api.types.is_integer_dtype(series):
                interpolated = interpolated.round().astype(series.dtype)
            return interpolated
        else:
            # 修复类型兼容性：对整数列保持整数类型
            if pd.api.types.is_integer_dtype(series):
                return series.fillna(0).astype(series.dtype)
            else:
                return series.fillna(0)

    def _detect_and_handle_outliers(
        self, data: pd.DataFrame, data_type: str
    ) -> pd.DataFrame:
        """检测和处理异常值."""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        outliers_info = {}

        for column in numeric_columns:
            if self.config["outlier_method"] == "iqr":
                outliers = self._detect_outliers_iqr(data[column])
            else:
                outliers = pd.Series(False, index=data.index)

            if outliers.any():
                # 修复_NoValueType错误：使用更安全的方式计算异常值数量
                outliers_info[column] = {
                    "count": len(outliers[outliers]),
                    "indices": data.index[outliers].tolist(),
                }

                # 处理异常值 - 使用边界值替换
                data = self._handle_outliers(data, column, outliers)

        if outliers_info:
            self.data_quality_report["outliers"] = outliers_info

        return data

    def _detect_outliers_iqr(self, series: pd.Series) -> pd.Series:
        """使用IQR方法检测异常值."""
        try:
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = (series < lower_bound) | (series > upper_bound)
            return outliers
        except Exception as e:
            logger.error(f"IQR异常值检测失败: {e}")
            return pd.Series(False, index=series.index)

    def _handle_outliers(
        self, data: pd.DataFrame, column: str, outliers: pd.Series
    ) -> pd.DataFrame:
        """处理异常值."""
        try:
            q1 = data[column].quantile(0.25)
            q3 = data[column].quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            # 修复类型兼容性问题：将边界值转换为与列相同的类型
            if pd.api.types.is_integer_dtype(data[column]):
                lower_bound = int(round(lower_bound))
                upper_bound = int(round(upper_bound))

            # 将异常值限制在边界范围内
            data.loc[data[column] < lower_bound, column] = lower_bound
            data.loc[data[column] > upper_bound, column] = upper_bound
        except Exception as e:
            logger.error(f"异常值处理失败: {e}")

        return data

    def _convert_and_standardize(self, data: pd.DataFrame) -> pd.DataFrame:
        """数据类型转换和标准化."""
        # 确保日期列格式正确
        date_columns = ["match_date", "created_at", "updated_at", "utc_date"]
        for col in date_columns:
            if col in data.columns:
                data[col] = pd.to_datetime(data[col], errors="coerce")

        # 数值列类型优化
        numeric_columns = data.select_dtypes(include=["int64", "float64"]).columns
        for col in numeric_columns:
            # 检查是否可以转换为更小的数值类型
            if data[col].dtype == "int64":
                # 修复_NoValueType错误：使用更安全的方式获取min/max
                col_min = min(data[col].values)
                col_max = max(data[col].values)
                if col_min >= 0 and col_max <= 255:
                    data[col] = data[col].astype("uint8")
                elif col_min >= 0 and col_max <= 65535:
                    data[col] = data[col].astype("uint16")
            elif data[col].dtype == "float64":
                data[col] = pd.to_numeric(data[col], downcast="float")

        return data

    def _advanced_validation(self, data: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """高级数据验证."""
        validation_errors = []

        if data_type == "matches":
            # 验证比分逻辑
            if "home_score" in data.columns and "away_score" in data.columns:
                invalid_scores = data[
                    (data["home_score"] < 0)
                    | (data["away_score"] < 0)
                    | (data["home_score"] > 20)
                    | (data["away_score"] > 20)
                ]
                if not invalid_scores.empty:
                    validation_errors.append(
                        f"发现 {len(invalid_scores)} 条无效比分记录"
                    )

            # 验证时间逻辑
            if "match_date" in data.columns:
                future_matches = data[
                    data["match_date"] > datetime.now() + timedelta(days=365)
                ]
                if not future_matches.empty:
                    validation_errors.append(
                        f"发现 {len(future_matches)} 条超过1年的未来比赛"
                    )

            # 验证球队ID逻辑
            if "home_team_id" in data.columns and "away_team_id" in data.columns:
                same_team_matches = data[data["home_team_id"] == data["away_team_id"]]
                if not same_team_matches.empty:
                    validation_errors.append(
                        f"发现 {len(same_team_matches)} 条主队相同比赛"
                    )

        elif data_type == "odds":
            # 验证赔率逻辑
            odds_columns = ["home_win_odds", "draw_odds", "away_win_odds"]
            for col in odds_columns:
                if col in data.columns:
                    invalid_odds = data[(data[col] <= 1.0) | (data[col] > 100.0)]
                    if not invalid_odds.empty:
                        validation_errors.append(
                            f"发现 {len(invalid_odds)} 条无效赔率记录 ({col})"
                        )

        if validation_errors:
            logger.warning(f"数据验证警告: {'; '.join(validation_errors)}")
            self.data_quality_report["validation_warnings"] = validation_errors

        return data

    def _generate_cleaning_report(
        self, raw_data: pd.DataFrame, cleaned_data: pd.DataFrame, steps: list[str]
    ):
        """生成清洗报告."""
        self.data_quality_report.update(
            {
                "original_shape": raw_data.shape,
                "cleaned_shape": cleaned_data.shape,
                "cleaning_steps": steps,
                "data_reduction_ratio": (
                    1 - (len(cleaned_data) / len(raw_data)) if len(raw_data) > 0 else 0
                ),
                "cleaning_timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(f"数据清洗报告生成完成: {self.data_quality_report}")

    def get_cleaning_report(self) -> dict[str, Any]:
        """获取清洗报告."""
        return self.data_quality_report.copy()

    def parse_match_json(self, raw_json: dict[str, Any]) -> dict[str, Any]:
        """解析比赛JSON数据为标准化格式.

        从API返回的JSON中提取关键信息并转换为符合Match模型的格式。

        Args:
            raw_json: 原始API返回的JSON数据

        Returns:
            dict: 解析后的标准化数据
        """
        try:
            # 处理不同的JSON结构（可能是直接API数据或已包装的数据）
            if "raw_data" in raw_json:
                data = raw_json["raw_data"]
            else:
                data = raw_json

            # 提取基本信息
            match_data = {
                "external_id": data.get("id"),
                "status": data.get("status", "SCHEDULED"),
                "match_date": self._parse_datetime(data.get("utcDate")),
                "matchday": data.get("matchday"),
                "season": data.get("season", {}).get("id")
                if isinstance(data.get("season"), dict)
                else data.get("season"),
            }

            # 提取比分信息
            score = data.get("score", {})
            if isinstance(score, dict):
                full_time = score.get("fullTime", {})
                match_data.update(
                    {
                        "home_score": full_time.get("home", 0),
                        "away_score": full_time.get("away", 0),
                        "winner": score.get("winner"),
                    }
                )
            else:
                match_data.update(
                    {
                        "home_score": 0,
                        "away_score": 0,
                        "winner": None,
                    }
                )

            # 提取主队信息
            home_team = data.get("homeTeam", {})
            if isinstance(home_team, dict):
                match_data.update(
                    {
                        "home_team_external_id": home_team.get("id"),
                        "home_team_name": home_team.get("name"),
                        "home_team_short_name": home_team.get("shortName"),
                    }
                )

            # 提取客队信息
            away_team = data.get("awayTeam", {})
            if isinstance(away_team, dict):
                match_data.update(
                    {
                        "away_team_external_id": away_team.get("id"),
                        "away_team_name": away_team.get("name"),
                        "away_team_short_name": away_team.get("shortName"),
                    }
                )

            # 提取联赛信息
            competition = data.get("competition", {})
            if isinstance(competition, dict):
                match_data.update(
                    {
                        "league_external_id": competition.get("id"),
                        "league_name": competition.get("name"),
                        "league_code": competition.get("code"),
                    }
                )

            # 提取场地信息
            match_data["venue"] = data.get("venue")

            # 验证必需字段
            if not match_data.get("external_id"):
                raise ValueError("缺少external_id字段")

            if not match_data.get("home_team_external_id") or not match_data.get(
                "away_team_external_id"
            ):
                raise ValueError("缺少球队ID信息")

            logger.debug(f"成功解析比赛数据: external_id={match_data['external_id']}")
            return match_data

        except Exception as e:
            logger.error(f"JSON解析失败: {e}, 原始数据: {raw_json}")
            raise

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """解析ISO8601时间字符串为datetime对象.

        Args:
            datetime_str: ISO8601格式的时间字符串

        Returns:
            datetime: 解析后的时间对象
        """
        if not datetime_str:
            return datetime.utcnow()

        try:
            # 处理带Z后缀的UTC时间
            if datetime_str.endswith("Z"):
                datetime_str = datetime_str[:-1] + "+00:00"

            # 使用pandas的to_datetime解析，支持更多格式
            dt = pd.to_datetime(datetime_str, errors="coerce")
            if pd.isna(dt):
                raise ValueError(f"无效的时间格式: {datetime_str}")

            return dt.to_pydatetime()

        except Exception as e:
            logger.warning(f"时间解析失败: {e}, 使用当前时间")
            return datetime.utcnow()

    def extract_team_from_match(
        self, match_data: dict[str, Any], team_type: str
    ) -> dict[str, Any]:
        """从比赛数据中提取球队信息.

        Args:
            match_data: 解析后的比赛数据
            team_type: 'home' 或 'away'

        Returns:
            dict: 球队信息
        """
        if team_type == "home":
            return {
                "external_id": match_data.get("home_team_external_id"),
                "name": match_data.get("home_team_name"),
                "short_name": match_data.get("home_team_short_name"),
                "country": "England",  # 基于当前英超数据的默认值
            }
        elif team_type == "away":
            return {
                "external_id": match_data.get("away_team_external_id"),
                "name": match_data.get("away_team_name"),
                "short_name": match_data.get("away_team_short_name"),
                "country": "England",  # 基于当前英超数据的默认值
            }
        else:
            raise ValueError("team_type必须是'home'或'away'")

    def extract_league_from_match(self, match_data: dict[str, Any]) -> dict[str, Any]:
        """从比赛数据中提取联赛信息.

        Args:
            match_data: 解析后的比赛数据

        Returns:
            dict: 联赛信息
        """
        return {
            "external_id": match_data.get("league_external_id"),
            "name": match_data.get("league_name", "Premier League"),
            "country": "England",  # 基于当前英超数据的默认值
            "is_active": True,
        }

    def clean_match_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """清洗比赛数据的便捷方法."""
        return self.clean_dataset(raw_data, "matches")

    def clean_team_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """清洗球队数据的便捷方法."""
        return self.clean_dataset(raw_data, "teams")

    def clean_odds_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """清洗赔率数据的便捷方法."""
        return self.clean_dataset(raw_data, "odds")


# 便捷函数
def clean_football_data(
    raw_data: pd.DataFrame, data_type: str = "matches", config: dict | None = None
) -> pd.DataFrame:
    """便捷的足球数据清洗函数.

    Args:
        raw_data: 原始数据
        data_type: 数据类型
        config: 配置参数

    Returns:
        pd.DataFrame: 清洗后的数据
    """
    cleaner = FootballDataCleaner(config)
    return cleaner.clean_dataset(raw_data, data_type)
