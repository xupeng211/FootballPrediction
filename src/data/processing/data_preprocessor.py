"""
数据预处理器

提供完整的数据预处理流水线，整合数据清洗和缺失值处理功能
"""

import logging
from typing import Any

import pandas as pd

from .football_data_cleaner import FootballDataCleaner
from .missing_data_handler import MissingDataHandler

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """数据预处理器 - 整合清洗和缺失值处理功能"""

    def __init__(self, config: dict | None = None):
        """
        初始化数据预处理器

        Args:
            config: 配置参数
        """
        self.config = config or self._get_default_config()
        self.cleaner = FootballDataCleaner(self.config.get("cleaning", {}))
        self.missing_handler = MissingDataHandler()
        self.processing_history = []

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "cleaning": {
                "remove_duplicates": True,
                "handle_missing": True,
                "detect_outliers": True,
                "validate_data": True,
                "outlier_method": "iqr",
                "missing_strategy": "adaptive",
            },
            "missing_data": {"strategy": "adaptive", "drop_threshold": 0.5},
            "validation": {"enable_quality_check": True, "quality_threshold": 0.8},
        }

    def preprocess_dataset(
        self, raw_data: pd.DataFrame, data_type: str = "matches"
    ) -> dict[str, Any]:
        """
        预处理完整数据集

        Args:
            raw_data: 原始数据
            data_type: 数据类型 ('matches', 'teams', 'odds')

        Returns:
            Dict: 预处理结果，包含清洗后的数据和处理报告
        """
        logger.info(f"开始预处理 {data_type} 数据，形状: {raw_data.shape}")

        processing_result = {
            "original_data": raw_data,
            "cleaned_data": None,
            "final_data": None,
            "processing_steps": [],
            "reports": {},
        }

        try:
            # Step 1: 数据清洗
            logger.info("Step 1: 执行数据清洗")
            cleaned_data = self.cleaner.clean_dataset(raw_data, data_type)
            processing_result["cleaned_data"] = cleaned_data
            processing_result["processing_steps"].append("数据清洗")
            processing_result["reports"][
                "cleaning"
            ] = self.cleaner.get_cleaning_report()

            # Step 2: 缺失值分析和处理
            if self.config["cleaning"]["handle_missing"]:
                logger.info("Step 2: 分析和处理缺失值")

                # 分析缺失模式
                missing_analysis = self.missing_handler.analyze_missing_patterns(
                    cleaned_data
                )
                processing_result["reports"]["missing_analysis"] = missing_analysis

                # 处理缺失值过多的列
                drop_threshold = self.config["missing_data"]["drop_threshold"]
                data_after_dropping = (
                    self.missing_handler.handle_columns_with_excessive_missing(
                        cleaned_data, drop_threshold
                    )
                )
                processing_result["processing_steps"].append("缺失值过多列处理")

                # 插补剩余缺失值
                missing_strategy = self.config["missing_data"]["strategy"]
                final_data = self.missing_handler.impute_missing_data(
                    data_after_dropping, missing_strategy
                )
                processing_result["final_data"] = final_data
                processing_result["processing_steps"].append("缺失值插补")

                # 验证插补质量
                imputation_validation = (
                    self.missing_handler.validate_imputation_quality(
                        cleaned_data, final_data
                    )
                )
                processing_result["reports"][
                    "imputation_validation"
                ] = imputation_validation
                processing_result["reports"][
                    "missing_report"
                ] = self.missing_handler.get_missing_data_report()
            else:
                final_data = cleaned_data
                processing_result["final_data"] = final_data

            # Step 3: 数据质量评估
            if self.config["validation"]["enable_quality_check"]:
                logger.info("Step 3: 执行数据质量评估")
                quality_assessment = self._assess_data_quality(
                    raw_data, final_data, data_type
                )
                processing_result["reports"]["quality_assessment"] = quality_assessment
                processing_result["processing_steps"].append("数据质量评估")

            # 记录处理历史
            self.processing_history.append(
                {
                    "timestamp": pd.Timestamp.now().isoformat(),
                    "data_type": data_type,
                    "original_shape": raw_data.shape,
                    "final_shape": final_data.shape,
                    "processing_steps": processing_result["processing_steps"],
                    "success": True,
                }
            )

            logger.info(f"数据预处理完成，最终形状: {final_data.shape}")
            processing_result["success"] = True

        except Exception as e:
            logger.error(f"数据预处理失败: {e}")
            processing_result["success"] = False
            processing_result["error"] = str(e)

        return processing_result

    def _assess_data_quality(
        self, original_data: pd.DataFrame, processed_data: pd.DataFrame, data_type: str
    ) -> dict[str, Any]:
        """评估数据质量

        Args:
            original_data: 原始数据
            processed_data: 处理后数据
            data_type: 数据类型

        Returns:
            Dict: 数据质量评估结果
        """
        assessment = {
            "completeness_score": 0.0,
            "consistency_score": 0.0,
            "validity_score": 0.0,
            "overall_score": 0.0,
            "quality_issues": [],
            "improvements": [],
        }

        # 1. 完整性评估
        total_cells = processed_data.shape[0] * processed_data.shape[1]
        missing_cells = processed_data.isnull().sum().sum()
        completeness_score = (
            (total_cells - missing_cells) / total_cells if total_cells > 0 else 0
        )
        assessment["completeness_score"] = completeness_score

        if completeness_score < 0.95:
            assessment["quality_issues"].append(
                f"数据完整性较低: {completeness_score:.2%}"
            )

        # 2. 一致性评估
        if data_type == "matches":
            consistency_issues = self._check_match_consistency(processed_data)
            assessment["consistency_score"] = (
                1.0 - len(consistency_issues) / 10.0
            )  # 假设最多10个问题
            assessment["quality_issues"].extend(consistency_issues)

        # 3. 有效性评估
        validity_issues = self._check_data_validity(processed_data, data_type)
        assessment["validity_score"] = (
            1.0 - len(validity_issues) / 20.0
        )  # 假设最多20个问题
        assessment["quality_issues"].extend(validity_issues)

        # 4. 计算总体质量分数
        assessment["overall_score"] = (
            assessment["completeness_score"] * 0.4
            + assessment["consistency_score"] * 0.3
            + assessment["validity_score"] * 0.3
        )

        # 5. 生成改进建议
        assessment["improvements"] = self._generate_improvement_suggestions(
            assessment, data_type
        )

        return assessment

    def _check_match_consistency(self, data: pd.DataFrame) -> list[str]:
        """检查比赛数据一致性"""
        issues = []

        if "home_team_id" in data.columns and "away_team_id" in data.columns:
            same_team_matches = data[data["home_team_id"] == data["away_team_id"]]
            if not same_team_matches.empty:
                issues.append(f"发现 {len(same_team_matches)} 条主客队相同的比赛")

        if "match_date" in data.columns and "status" in data.columns:
            future_finished = data[
                (data["match_date"] > pd.Timestamp.now())
                & (data["status"] == "FINISHED")
            ]
            if not future_finished.empty:
                issues.append(f"发现 {len(future_finished)} 条未来的已完成比赛")

        return issues

    def _check_data_validity(self, data: pd.DataFrame, data_type: str) -> list[str]:
        """检查数据有效性"""
        issues = []

        # 检查负值
        numeric_columns = data.select_dtypes(include=["number"]).columns
        for col in numeric_columns:
            if "score" in col.lower() or "odds" in col.lower():
                negative_values = data[data[col] < 0]
                if not negative_values.empty:
                    issues.append(f"列 {col} 包含 {len(negative_values)} 个负值")

        # 检查极端值
        if (
            data_type == "matches"
            and "home_score" in data.columns
            and "away_score" in data.columns
        ):
            extreme_scores = data[(data["home_score"] > 15) | (data["away_score"] > 15)]
            if not extreme_scores.empty:
                issues.append(f"发现 {len(extreme_scores)} 条极端比分记录")

        if data_type == "odds":
            odds_columns = [col for col in data.columns if "odds" in col.lower()]
            for col in odds_columns:
                invalid_odds = data[(data[col] <= 1.0) | (data[col] > 1000.0)]
                if not invalid_odds.empty:
                    issues.append(f"赔率列 {col} 包含 {len(invalid_odds)} 个无效值")

        return issues

    def _generate_improvement_suggestions(
        self, assessment: dict[str, Any], data_type: str
    ) -> list[str]:
        """生成数据改进建议"""
        suggestions = []

        if assessment["completeness_score"] < 0.9:
            suggestions.append("建议进一步处理缺失值以提高数据完整性")

        if assessment["consistency_score"] < 0.8:
            suggestions.append("建议检查数据源以提高数据一致性")

        if assessment["validity_score"] < 0.8:
            suggestions.append("建议增加数据验证规则以提高数据有效性")

        # 基于数据类型的特定建议
        if data_type == "matches":
            if "match_date" not in assessment.get("quality_issues", []):
                suggestions.append("建议添加比赛时区信息")

        if assessment["overall_score"] < self.config["validation"]["quality_threshold"]:
            suggestions.append("数据质量低于阈值，建议进行人工审核")

        return suggestions

    def preprocess_matches(self, raw_data: pd.DataFrame) -> dict[str, Any]:
        """预处理比赛数据的便捷方法"""
        return self.preprocess_dataset(raw_data, "matches")

    def preprocess_teams(self, raw_data: pd.DataFrame) -> dict[str, Any]:
        """预处理球队数据的便捷方法"""
        return self.preprocess_dataset(raw_data, "teams")

    def preprocess_odds(self, raw_data: pd.DataFrame) -> dict[str, Any]:
        """预处理赔率数据的便捷方法"""
        return self.preprocess_dataset(raw_data, "odds")

    def get_processing_summary(self) -> dict[str, Any]:
        """获取处理摘要"""
        if not self.processing_history:
            return {"message": "还没有处理历史记录"}

        total_processed = len(self.processing_history)
        successful_processed = sum(
            1 for record in self.processing_history if record["success"]
        )

        return {
            "total_processing_jobs": total_processed,
            "successful_jobs": successful_processed,
            "success_rate": (
                successful_processed / total_processed if total_processed > 0 else 0
            ),
            "latest_jobs": self.processing_history[-5:],  # 最近5个任务
            "processing_statistics": self._calculate_processing_stats(),
        }

    def _calculate_processing_stats(self) -> dict[str, Any]:
        """计算处理统计信息"""
        if not self.processing_history:
            return {}

        data_types = {}
        for record in self.processing_history:
            data_type = record["data_type"]
            if data_type not in data_types:
                data_types[data_type] = {"count": 0, "total_rows_processed": 0}

            data_types[data_type]["count"] += 1
            if "final_shape" in record:
                data_types[data_type]["total_rows_processed"] += record["final_shape"][
                    0
                ]

        return {
            "by_data_type": data_types,
            "average_rows_per_job": (
                sum(
                    stat["total_rows_processed"] / stat["count"]
                    for stat in data_types.values()
                    if stat["count"] > 0
                )
                / len(data_types)
                if data_types
                else 0
            ),
        }


# 便捷函数
def preprocess_football_data(
    raw_data: pd.DataFrame, data_type: str = "matches", config: dict | None = None
) -> dict[str, Any]:
    """
    便捷的足球数据预处理函数

    Args:
        raw_data: 原始数据
        data_type: 数据类型
        config: 配置参数

    Returns:
        Dict: 预处理结果
    """
    preprocessor = DataPreprocessor(config)
    return preprocessor.preprocess_dataset(raw_data, data_type)
