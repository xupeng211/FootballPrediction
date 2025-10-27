"""
足球数据清理器（兼容版本）
Football Data Cleaner (Compatibility Version)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FootballDataCleaner:
    """足球数据清理器"""

    def __init__(self):
        self.cleaning_stats = {}

    def clean_match_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理比赛数据"""
        # 去除重复记录
        initial_count = len(df)
        df = df.drop_duplicates()
        duplicates_removed = initial_count - len(df)

        # 处理缺失值
        df = self._handle_missing_values(df)

        # 标准化列名
        df = self._standardize_column_names(df)

        # 验证数据完整性
        df = self._validate_data(df)

        self.cleaning_stats = {
            "initial_records": initial_count,
            "duplicates_removed": duplicates_removed,
            "final_records": len(df),
            "cleaned_at": datetime.utcnow(),
        }

        logger.info(f"Cleaned match data: {initial_count} -> {len(df)} records")
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 数值列：用中位数填充
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)

        # 分类列：用众数填充
        categorical_cols = df.select_dtypes(include=["object"]).columns
        for col in categorical_cols:
            if df[col].isnull().any():
                mode_val = df[col].mode()[0] if not df[col].mode().empty else "unknown"
                df[col] = df[col].fillna(mode_val)

        return df

    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 转换为小写并替换空格
        df.columns = df.columns.str.lower().str.replace(" ", "_")
        return df

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证数据完整性"""
        # 移除无效的行（例如：全为空值的行）
        df = df.dropna(how="all")
        return df

    def clean_team_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理球队数据"""
        return self.clean_match_data(df)

    def clean_player_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理球员数据"""
        return self.clean_match_data(df)


class DataValidator:
    """数据验证器"""

    @staticmethod
    def validate_scores(df: pd.DataFrame, home_col: str, away_col: str) -> bool:
        """验证比分数据"""
        invalid = df[(df[home_col] < 0) | (df[away_col] < 0)]
        return len(invalid) == 0

    @staticmethod
    def validate_dates(df: pd.DataFrame, date_col: str) -> bool:
        """验证日期数据"""
        try:
            pd.to_datetime(df[date_col])
            return True
        except Exception:
            return False

    @staticmethod
    def validate_odds(df: pd.DataFrame, odds_cols: List[str]) -> Dict[str, Any]:
        """验证赔率数据"""
        results = {}
        for col in odds_cols:
            if col in df.columns:
                invalid = df[(df[col] <= 1) | (df[col] > 100)]
                results[col] = {"invalid_count": len(invalid), "total_count": len(df)}
        return results
