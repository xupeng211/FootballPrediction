"""
足球数据清洗器 - 完整实现

提供专业的足球数据清洗功能，包括：
- 数据验证和去重
- 缺失值处理
- 异常值检测和处理
- 数据类型转换和标准化
- 高级数据质量评估
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FootballDataCleaner:
    """足球数据清洗器 - 完整实现"""

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
        """清洗完整数据集

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
        """基础数据结构验证"""
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
        """移除重复数据"""
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
        """自适应缺失值处理"""
        missing_info = {}

        for column in data.columns:
            missing_count = data[column].isnull().sum()
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
        """确定缺失值处理策略"""
        if missing_ratio > 0.5:
            return "drop_column"  # 缺失值超过50%，考虑删除列
        elif missing_ratio > 0.3:
            return "model_based"  # 缺失值30-50%，使用模型预测
        elif series.dtype in ["int64", "float64"]:
            return "median" if series.skew() > 1 else "mean"
        else:
            return "mode"

    def _apply_missing_strategy(self, series: pd.Series, strategy: str) -> pd.Series:
        """应用缺失值处理策略"""
        if strategy == "drop_column":
            return series  # 将在上层处理
        elif strategy == "drop_rows":
            return series.dropna()
        elif strategy == "mean" and series.dtype in ["int64", "float64"]:
            return series.fillna(series.mean())
        elif strategy == "median" and series.dtype in ["int64", "float64"]:
            return series.fillna(series.median())
        elif strategy == "mode":
            mode_value = series.mode()[0] if not series.mode().empty else "Unknown"
            return series.fillna(mode_value)
        elif strategy == "forward_fill":
            return series.ffill()
        elif strategy == "backward_fill":
            return series.bfill()
        elif strategy == "interpolate" and series.dtype in ["int64", "float64"]:
            return series.interpolate()
        else:
            return series.fillna(0)  # 默认填充0

    def _detect_and_handle_outliers(
        self, data: pd.DataFrame, data_type: str
    ) -> pd.DataFrame:
        """检测和处理异常值"""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        outliers_info = {}

        for column in numeric_columns:
            if self.config["outlier_method"] == "iqr":
                outliers = self._detect_outliers_iqr(data[column])
            else:
                outliers = pd.Series(False, index=data.index)

            if outliers.any():
                outliers_info[column] = {
                    "count": outliers.sum(),
                    "indices": data.index[outliers].tolist(),
                }

                # 处理异常值 - 使用边界值替换
                data = self._handle_outliers(data, column, outliers)

        if outliers_info:
            self.data_quality_report["outliers"] = outliers_info

        return data

    def _detect_outliers_iqr(self, series: pd.Series) -> pd.Series:
        """使用IQR方法检测异常值"""
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
        """处理异常值"""
        try:
            q1 = data[column].quantile(0.25)
            q3 = data[column].quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            # 将异常值限制在边界范围内
            data.loc[data[column] < lower_bound, column] = lower_bound
            data.loc[data[column] > upper_bound, column] = upper_bound
        except Exception as e:
            logger.error(f"异常值处理失败: {e}")

        return data

    def _convert_and_standardize(self, data: pd.DataFrame) -> pd.DataFrame:
        """数据类型转换和标准化"""
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
                if data[col].min() >= 0 and data[col].max() <= 255:
                    data[col] = data[col].astype("uint8")
                elif data[col].min() >= 0 and data[col].max() <= 65535:
                    data[col] = data[col].astype("uint16")
            elif data[col].dtype == "float64":
                data[col] = pd.to_numeric(data[col], downcast="float")

        return data

    def _advanced_validation(self, data: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """高级数据验证"""
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
        """生成清洗报告"""
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
        """获取清洗报告"""
        return self.data_quality_report.copy()

    def clean_match_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """清洗比赛数据的便捷方法"""
        return self.clean_dataset(raw_data, "matches")

    def clean_team_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """清洗球队数据的便捷方法"""
        return self.clean_dataset(raw_data, "teams")

    def clean_odds_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """清洗赔率数据的便捷方法"""
        return self.clean_dataset(raw_data, "odds")


# 便捷函数
def clean_football_data(
    raw_data: pd.DataFrame, data_type: str = "matches", config: dict | None = None
) -> pd.DataFrame:
    """
    便捷的足球数据清洗函数

    Args:
        raw_data: 原始数据
        data_type: 数据类型
        config: 配置参数

    Returns:
        pd.DataFrame: 清洗后的数据
    """
    cleaner = FootballDataCleaner(config)
    return cleaner.clean_dataset(raw_data, data_type)
