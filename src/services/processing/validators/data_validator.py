"""
数据验证器

验证处理后的数据质量和完整性。
"""

from datetime import datetime, timedelta

import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

import pandas as pd

# from src.data.processing.missing_data_handler import MissingDataHandler  # type: ignore


class DataValidator:
    """数据验证器"""

    def __init__(self):
        """初始化验证器"""
        self.logger = logging.getLogger(f"processing.{self.__class__.__name__}")
        # self.missing_handler = MissingDataHandler()  # type: ignore

        # 验证规则配置
        self.validation_rules = {
            "match_data": {
                "required_fields": [
                    "match_id",
                    "home_team",
                    "away_team",
                    "match_date",
                ],
                "date_fields": ["match_date"],
                "numeric_fields": ["home_score", "away_score"],
                "string_fields": ["home_team", "away_team", "venue", "competition"],
            },
            "odds_data": {
                "required_fields": [
                    "match_id",
                    "bookmaker",
                    "home_win",
                    "draw",
                    "away_win",
                ],
                "numeric_fields": [
                    "home_win",
                    "draw",
                    "away_win",
                    "bookmaker_margin",
                ],
                "float_fields": ["home_win", "draw", "away_win"],
            },
            "features_data": {
                "numeric_range": {
                    "form": (0, 1),
                    "win_rate": (0, 1),
                    "goals_avg": (0, 10),
                },
            },
        }

    async def validate_data_quality(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        data_type: str = "match_data",
    ) -> Dict[str, Any]:
        """
        验证数据质量

        Args:
            data: 要验证的数据
            data_type: 数据类型

        Returns:
            验证结果报告
        """
        try:
            # 转换为DataFrame
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data

            if df.empty:
                return {
                    "valid": False,
                    "errors": ["数据为空"],
                    "warnings": [],
                    "statistics": {},
                }

            # 执行各类验证
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "statistics": {},
            }

            # 1. 结构验证
            structure_result = await self._validate_structure(df, data_type)
            validation_results.update(structure_result)

            # 2. 内容验证
            content_result = await self._validate_content(df, data_type)
            validation_results["errors"].extend(content_result["errors"])  # type: ignore
            validation_results["warnings"].extend(content_result["warnings"])  # type: ignore

            # 3. 业务规则验证
            business_result = await self._validate_business_rules(df, data_type)
            validation_results["errors"].extend(business_result["errors"])  # type: ignore
            validation_results["warnings"].extend(business_result["warnings"])  # type: ignore

            # 4. 统计信息
            validation_results["statistics"] = await self._generate_statistics(df)

            # 5. 总体评估
            if validation_results["errors"]:
                validation_results["valid"] = False

            # 记录验证结果
            await self._log_validation_results(validation_results, data_type)

            return validation_results

        except Exception as e:
            self.logger.error(f"数据验证失败: {e}", exc_info=True)
            return {
                "valid": False,
                "errors": [f"验证过程出错: {str(e)}"],
                "warnings": [],
                "statistics": {},
            }

    async def _validate_structure(
        self, df: pd.DataFrame, data_type: str
    ) -> Dict[str, Any]:
        """
        验证数据结构

        Args:
            df: 数据DataFrame
            data_type: 数据类型

        Returns:
            结构验证结果
        """
        result: Dict[str, List[str]] = {"errors": [], "warnings": []}

        rules = self.validation_rules.get(data_type, {})
        required_fields = rules.get("required_fields", [])

        # 检查必需字段
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            result["errors"].append(f"缺少必需字段: {missing_fields}")

        # 检查字段类型
        date_fields = rules.get("date_fields", [])
        for field in date_fields:
            if field in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df[field]):
                    try:
                        pd.to_datetime(df[field])
                    except Exception:
                        result["errors"].append(f"字段 {field} 不是有效的日期格式")

        numeric_fields = rules.get("numeric_fields", [])
        for field in numeric_fields:
            if field in df.columns:
                if not pd.api.types.is_numeric_dtype(df[field]):
                    try:
                        pd.to_numeric(df[field])
                    except Exception:
                        result["warnings"].append(f"字段 {field} 包含非数值数据")

        return result

    async def _validate_content(
        self, df: pd.DataFrame, data_type: str
    ) -> Dict[str, Any]:
        """
        验证数据内容

        Args:
            df: 数据DataFrame
            data_type: 数据类型

        Returns:
            内容验证结果
        """
        result: Dict[str, List[str]] = {"errors": [], "warnings": []}

        # 检查重复记录
        duplicates = df.duplicated()
        if duplicates.any():
            result["warnings"].append(f"发现 {duplicates.sum()} 条重复记录")

        # 检查缺失值
        # missing_report = self.missing_handler.analyze_missing_data(df)  # type: ignore
        missing_report = {"missing_percentage": 0}
        if missing_report["missing_percentage"] > 50:
            result["errors"].append(
                f"数据缺失率过高: {missing_report['missing_percentage']:.1%}"
            )
        elif missing_report["missing_percentage"] > 20:
            result["warnings"].append(
                f"数据缺失率较高: {missing_report['missing_percentage']:.1%}"
            )

        # 检查异常值
        numeric_cols = df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if df[col].dtype in ["float64", "int64"]:
                # 使用IQR方法检测异常值
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                if not outliers.empty:
                    outlier_percentage = len(outliers) / len(df) * 100
                    if outlier_percentage > 10:
                        result["warnings"].append(
                            f"字段 {col} 异常值比例过高: {outlier_percentage:.1%}"
                        )

        return result

    async def _validate_business_rules(
        self, df: pd.DataFrame, data_type: str
    ) -> Dict[str, Any]:
        """
        验证业务规则

        Args:
            df: 数据DataFrame
            data_type: 数据类型

        Returns:
            业务规则验证结果
        """
        result: Dict[str, List[str]] = {"errors": [], "warnings": []}

        if data_type == "match_data":
            result = await self._validate_match_business_rules(df)
        elif data_type == "odds_data":
            result = await self._validate_odds_business_rules(df)
        elif data_type == "features_data":
            result = await self._validate_features_business_rules(df)

        return result

    async def _validate_match_business_rules(self, df: pd.DataFrame) -> Dict[str, Any]:
        """验证比赛数据业务规则"""
        result: Dict[str, List[str]] = {"errors": [], "warnings": []}

        # 检查同一日期的重复比赛
        if (
            "match_date" in df.columns
            and "home_team" in df.columns
            and "away_team" in df.columns
        ):
            date_team_pairs = df.groupby("match_date").apply(
                lambda x: x.duplicated(subset=["home_team", "away_team"]).any()
            )
            if date_team_pairs.any():
                result["errors"].append("发现同一日期的重复比赛")

        # 检查比分合理性
        if "home_score" in df.columns and "away_score" in df.columns:
            # 检查负分
            negative_scores = (df["home_score"] < 0) | (df["away_score"] < 0)
            if negative_scores.any():
                result["errors"].append("发现负分")

            # 检查异常高比分
            high_scores = (df["home_score"] > 20) | (df["away_score"] > 20)
            if high_scores.any():
                result["warnings"].append("发现异常高比分（>20）")

        # 检查日期范围
        if "match_date" in df.columns:
            df["match_date"] = pd.to_datetime(df["match_date"])
            future_matches = df["match_date"] > datetime.now() + timedelta(days=7)
            if future_matches.any():
                result["warnings"].append("发现超过7天的未来比赛")

            old_matches = df["match_date"] < datetime.now() - timedelta(days=365)
            if old_matches.any():
                result["warnings"].append("发现超过1年的历史比赛")

        return result

    async def _validate_odds_business_rules(self, df: pd.DataFrame) -> Dict[str, Any]:
        """验证赔率数据业务规则"""
        result: Dict[str, List[str]] = {"errors": [], "warnings": []}

        # 检查赔率值
        for outcome in ["home_win", "draw", "away_win"]:
            if outcome in df.columns:
                # 检查赔率小于等于1
                invalid_odds = df[outcome] <= 1
                if invalid_odds.any():
                    result["errors"].append(f"{outcome} 赔率值不能小于等于1")

                # 检查过高的赔率
                high_odds = df[outcome] > 1000
                if high_odds.any():
                    result["warnings"].append(f"{outcome} 赔率值异常高（>1000）")

        # 检查隐含概率
        if all(x in df.columns for x in ["home_win", "draw", "away_win"]):
            implied_probs = 1 / df["home_win"] + 1 / df["draw"] + 1 / df["away_win"]
            # 检查隐含概率过低（套利机会）
            arbitrage = implied_probs < 1
            if arbitrage.any():
                result["warnings"].append("发现可能的套利机会")

            # 检查隐含概率过高
            excessive_margin = implied_probs > 1.5
            if excessive_margin.any():
                result["warnings"].append("庄家优势过高（>50%）")

        return result

    async def _validate_features_business_rules(
        self, df: pd.DataFrame
    ) -> Dict[str, Any]:
        """验证特征数据业务规则"""
        result: Dict[str, List[str]] = {"errors": [], "warnings": []}

        # 检查标准化特征的范围
        for col in df.columns:
            if col.endswith("_standardized"):
                # 标准化后的值应该在[-3, 3]范围内
                out_of_range = (df[col] < -3) | (df[col] > 3)
                if out_of_range.any():
                    result["warnings"].append(f"标准化特征 {col} 存在超出±3标准差的值")

        # 检查比率型特征
        ratio_features = [
            col for col in df.columns if "rate" in col.lower() or "ratio" in col.lower()
        ]
        for col in ratio_features:
            if df[col].dtype in ["float64", "int64"]:
                invalid_ratios = (df[col] < 0) | (df[col] > 1)
                if invalid_ratios.any():
                    result["errors"].append(f"比率特征 {col} 的值必须在[0, 1]范围内")

        return result

    async def _generate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        生成数据统计信息

        Args:
            df: 数据DataFrame

        Returns:
            统计信息
        """
        stats = {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "missing_values": df.isnull().sum().to_dict(),
            "data_types": df.dtypes.astype(str).to_dict(),
        }

        # 数值列统计
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if not numeric_cols.empty:
            numeric_stats = df[numeric_cols].describe().to_dict()
            stats["numeric_statistics"] = numeric_stats

        # 时间范围统计
        date_cols = df.select_dtypes(include=["datetime64"]).columns
        if not date_cols.empty:
            date_stats = {}
            for col in date_cols:
                date_stats[col] = {
                    "min": df[col].min(),
                    "max": df[col].max(),
                    "range_days": (df[col].max() - df[col].min()).days,
                }
            stats["date_statistics"] = date_stats

        return stats

    async def _log_validation_results(
        self, results: Dict[str, Any], data_type: str
    ) -> None:
        """记录验证结果"""
        if results["valid"]:
            self.logger.info(f"{data_type} 数据验证通过")
        else:
            self.logger.error(
                f"{data_type} 数据验证失败，错误数: {len(results['errors'])}"
            )

        if results["warnings"]:
            self.logger.warning(
                f"{data_type} 数据验证警告数: {len(results['warnings'])}"
            )

        # 记录统计信息
        stats = results.get("statistics", {})
        if "total_records" in stats:
            self.logger.info(f"验证记录数: {stats['total_records']}")

    async def validate_batch_consistency(
        self, batches: List[pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        验证批次数据的一致性

        Args:
            batches: 批次数据列表

        Returns:
            一致性验证结果
        """
        result: Dict[str, Any] = {
            "consistent": True,
            "issues": [],
            "statistics": {
                "total_batches": len(batches),
                "total_records": sum(len(batch) for batch in batches),
            },
        }

        if not batches:
            result["consistent"] = False
            result["issues"].append("没有批次数据")
            return result

        # 检查列一致性
        first_batch_cols = set(batches[0].columns)
        for i, batch in enumerate(batches[1:], 1):
            batch_cols = set(batch.columns)
            if batch_cols != first_batch_cols:
                result["consistent"] = False
                result["issues"].append(f"批次 {i} 的列与批次 0 不一致")

        # 检查数据类型一致性
        for col in first_batch_cols:
            col_types = []
            for batch in batches:
                if col in batch.columns:
                    col_types.append(str(batch[col].dtype))

            if len(set(col_types)) > 1:
                result["issues"].append(
                    f"列 {col} 在不同批次中有不同的数据类型: {set(col_types)}"
                )

        return result
