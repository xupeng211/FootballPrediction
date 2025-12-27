"""
V20.0 数据验证器 - 金融量化级清洗准则
========================================

核心升级：
1. 特征熔断机制 - 自动剔除异常比赛
2. 离群值检测 - xG vs Score 偏差检测
3. 时间旅行防护 - 数据泄露检测

作者: Feature Engineering Team
日期: 2025-12-24
版本: V20.0
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MatchStatus(Enum):
    """比赛状态分类"""

    READY = "ready"  # 可以处理
    OUTLIER = "outlier"  # 离群值，标记审查
    INVALID = "invalid"  # 无效数据，拒绝处理
    MISSING_FEATURES = "missing"  # 缺失关键特征


class ValidationSeverity(Enum):
    """验证严重程度"""

    ERROR = "error"  # 阻止处理的严重错误
    WARNING = "warning"  # 可以继续但需警告
    INFO = "info"  # 信息性提示


@dataclass
class ValidationIssue:
    """验证问题"""

    severity: ValidationSeverity
    field: str
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    issues: list[ValidationIssue]
    quality_score: float  # 0-100

    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    def get_error_messages(self) -> list[str]:
        """获取错误消息列表"""
        return [
            f"[{i.severity.value.upper()}] {i.field}: {i.message}"
            for i in self.issues
            if i.severity == ValidationSeverity.ERROR
        ]

    def get_warning_messages(self) -> list[str]:
        """获取警告消息列表"""
        return [
            f"[{i.severity.value.upper()}] {i.field}: {i.message}"
            for i in self.issues
            if i.severity == ValidationSeverity.WARNING
        ]


class SanitizationProtocol:
    """
    V20.0 特征熔断与清洗准则

    金融量化级硬标准：
    1. total_shots < 2 → 立即剔除
    2. possession == 0 → 立即剔除
    3. xG vs Score 偏差超过5倍且样本极端偏离 → 标记 OUTLIER
    """

    # 硬标准阈值
    MIN_TOTAL_SHOTS = 2
    MIN_POSSESSION = 1  # 至少1%
    MAX_POSSESSION = 99  # 最多99%

    # xG 离群值检测参数
    XG_OUTLIER_THRESHOLD = 5.0  # 偏差倍数
    XG_DEVIATION_STD = 3.0  # 标准差倍数

    @classmethod
    def check_basic_validity(cls, features: dict[str, Any]) -> tuple[bool, str, MatchStatus]:
        """
        检查基本有效性

        Args:
            features: 特征字典

        Returns:
            (是否有效, 原因说明, 状态)
        """
        # 检1: total_shots 熔断
        total_shots = cls._get_numeric(features, "shots_total")
        if total_shots is not None and total_shots < cls.MIN_TOTAL_SHOTS:
            return False, f"total_shots={total_shots} < {cls.MIN_TOTAL_SHOTS}", MatchStatus.INVALID

        # 检2: possession 熔断
        home_poss = cls._get_numeric(features, "possession")
        if home_poss is not None and (home_poss < cls.MIN_POSSESSION or home_poss > cls.MAX_POSSESSION):
            return False, f"possession={home_poss} 超出范围", MatchStatus.INVALID

        return True, "", MatchStatus.READY

    @classmethod
    def check_outlier(cls, features: dict[str, Any], league_context: dict | None = None) -> tuple[bool, str]:
        """
        检查离群值

        Args:
            features: 特征字典
            league_context: 联赛统计上下文（用于计算均值和标准差）

        Returns:
            (是否离群, 原因说明)
        """
        home_score = cls._get_numeric(features, "home_score")
        away_score = cls._get_numeric(features, "away_score")
        home_xg = cls._get_numeric(features, "xg")
        away_xg = cls._get_numeric(features, "xg_away")

        # 需要比分和xG数据
        if None in [home_score, away_score, home_xg, away_xg]:
            return False, ""

        # 计算实际进球 vs xG 的偏差
        actual_goals = home_score + away_score
        expected_goals = home_xg + away_xg

        if expected_goals < 0.1:  # 避免除零
            return False, ""

        deviation_ratio = abs(actual_goals - expected_goals) / expected_goals

        # 偏差超过5倍
        if deviation_ratio > cls.XG_OUTLIER_THRESHOLD:
            # 检查是否在联赛统计的极端
            is_extreme = False
            if league_context:
                league_mean_xg = league_context.get("mean_total_xg", 2.5)
                league_std_xg = league_context.get("std_total_xg", 1.0)

                # xG 极端偏离均值
                if abs(expected_goals - league_mean_xg) > cls.XG_DEVIATION_STD * league_std_xg:
                    is_extreme = True

            if is_extreme:
                return True, (
                    f"xG偏差: 实际={actual_goals}, 预期={expected_goals:.2f}, 偏差比={deviation_ratio:.1f}x, 极端偏离"
                )

        return False, ""

    @classmethod
    def _get_numeric(cls, data: dict, key: str, default: float | None = None) -> float | None:
        """安全获取数值"""
        if key in data:
            try:
                return float(data[key])
            except (ValueError, TypeError):
                pass
        # 尝试嵌套键
        for nested_key in [f"home_{key}", f"away_{key}"]:
            if nested_key in data:
                try:
                    return float(data[nested_key])
                except (ValueError, TypeError):
                    pass
        return default


class DataValidator:
    """V20.0 数据验证器 - 金融量化级"""

    # 定义数据质量规则
    REQUIRED_FIELDS = [
        "external_id",
        "home_team",
        "away_team",
        "match_time",
    ]

    REQUIRED_SCORE_FIELDS = [
        "home_score",
        "away_score",
    ]

    NUMERIC_FIELDS = [
        "expected_goals",
        "shots_on_target",
        "possession",
        "shots",
        "corners",
        "home_expected_goals",
        "away_expected_goals",
        "home_shots_on_target",
        "away_shots_on_target",
        "home_possession",
        "away_possession",
    ]

    VALUE_RANGES = {
        "expected_goals": (0, 15),
        "possession": (0, 100),
        "shots": (0, 50),
        "shots_on_target": (0, 20),
        "corners": (0, 25),
        "home_score": (0, 20),
        "away_score": (0, 20),
    }

    SUPPORTED_FORMATS = ["technical_features", "home_stats_away_stats", "normalized"]
    SUPPORTED_LEAGUES = [47, 48, 8, 54, 23, 34, 13, 61, 57, 55]  # 扩展的联赛支持

    def __init__(self, strict_mode: bool = False, enable_sanitization: bool = True):
        """初始化数据验证器

        Args:
            strict_mode: 严格模式，如果有警告也会视为失败
            enable_sanitization: 启用金融量化级清洗准则
        """
        self.strict_mode = strict_mode
        self.enable_sanitization = enable_sanitization
        self.sanitization = SanitizationProtocol()

        # 统计信息（用于离群值检测）
        self.league_statistics: dict[int, dict] = defaultdict(
            lambda: {"total_xg": [], "total_shots": [], "match_count": 0}
        )

    def validate_match_data(self, match_data: dict) -> ValidationResult:
        """验证单场比赛数据

        Args:
            match_data: 比赛数据字典

        Returns:
            ValidationResult: 验证结果
        """
        issues = []

        # 1. 检查必需字段
        for field in self.REQUIRED_FIELDS:
            if field not in match_data or match_data[field] is None:
                issues.append(
                    ValidationIssue(severity=ValidationSeverity.ERROR, field=field, message=f"缺少必需字段: {field}")
                )

        # 2. 检查比分字段（如果比赛已完成）
        if match_data.get("is_finished", True):
            for field in self.REQUIRED_SCORE_FIELDS:
                if field not in match_data or match_data[field] is None:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR, field=field, message=f"已完成的比赛缺少比分字段: {field}"
                        )
                    )

        # 3. 检查数值范围
        for field, (min_val, max_val) in self.VALUE_RANGES.items():
            if field in match_data:
                value = match_data[field]
                try:
                    num_val = float(value)
                    if not (min_val <= num_val <= max_val):
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                field=field,
                                message=f"值超出正常范围: {field}={num_val} (期望: {min_val}-{max_val})",
                                value=num_val,
                            )
                        )
                except (ValueError, TypeError):
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            field=field,
                            message=f"数值类型错误: {field}={value}",
                            value=value,
                        )
                    )

        # 4. 检查联赛ID
        if "league_id" in match_data:
            league_id = match_data["league_id"]
            try:
                league_id_int = int(league_id)
                if league_id_int not in self.SUPPORTED_LEAGUES:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            field="league_id",
                            message=f"未经验证的联赛ID: {league_id_int}",
                            value=league_id_int,
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        field="league_id",
                        message=f"联赛ID类型错误: {league_id}",
                        value=league_id,
                    )
                )

        # 5. 计算质量分数
        quality_score = self._calculate_quality_score(issues, match_data)

        # 严格模式下，警告也会导致验证失败
        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        if self.strict_mode:
            is_valid = is_valid and not any(i.severity == ValidationSeverity.WARNING for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues, quality_score=quality_score)

    def validate_feature_matrix(self, feature_df: pd.DataFrame) -> ValidationResult:
        """验证特征矩阵质量

        Args:
            feature_df: 特征矩阵 DataFrame

        Returns:
            ValidationResult: 验证结果
        """
        issues = []

        if feature_df.empty:
            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(severity=ValidationSeverity.ERROR, field="feature_matrix", message="特征矩阵为空")
                ],
                quality_score=0,
            )

        # 1. 检查 NaN 值（仅限数值列）
        numeric_cols = feature_df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            nan_counts = feature_df[numeric_cols].isnull().sum()
            for col, count in nan_counts[nan_counts > 0].items():
                pct = count / len(feature_df) * 100
                severity = ValidationSeverity.ERROR if pct > 50 else ValidationSeverity.WARNING
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        field=col,
                        message=f"NaN 值占比 {pct:.1f}%: {col} ({count}/{len(feature_df)})",
                        value=count,
                    )
                )

        # 2. 检查无穷值
        for col in numeric_cols:
            try:
                if (feature_df[col] == float("inf")).any() or (feature_df[col] == float("-inf")).any():
                    issues.append(
                        ValidationIssue(severity=ValidationSeverity.ERROR, field=col, message=f"发现无穷值: {col}")
                    )
            except (TypeError, ValueError):
                # 跳过无法比较的列
                pass

        # 3. 检查常数列（没有变化）
        for col in feature_df.columns:
            try:
                if feature_df[col].nunique() == 1:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            field=col,
                            message=f"常数列（无变化）: {col} = {feature_df[col].iloc[0]}",
                        )
                    )
            except (TypeError, ValueError):
                # 跳过无法比较的列（如 dict/object 列）
                pass

        # 4. 计算质量分数
        quality_score = self._calculate_quality_score(issues, feature_df)

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues, quality_score=quality_score)

    def detect_data_format(self, raw_data: dict) -> str | None:
        """检测数据格式类型

        Args:
            raw_data: 原始数据字典

        Returns:
            格式类型：'technical_features', 'home_stats_away_stats', 或 None
        """
        if "technical_features" in raw_data:
            return "technical_features"
        elif "home_stats" in raw_data and "away_stats" in raw_data:
            return "home_stats_away_stats"
        elif all(k in raw_data for k in ["home_expected_goals", "away_expected_goals"]):
            return "normalized"
        return None

    def _calculate_quality_score(self, issues: list[ValidationIssue], data_context: Any) -> float:
        """计算数据质量分数 (0-100)

        Args:
            issues: 问题列表
            data_context: 数据上下文（用于计算字段数量等）

        Returns:
            质量分数 (0-100)
        """
        if not issues:
            return 100.0

        # 计算字段数量（用于权重）
        if isinstance(data_context, dict):
            field_count = len(data_context)
        elif isinstance(data_context, pd.DataFrame):
            field_count = len(data_context.columns)
        else:
            field_count = 10

        error_penalty = sum(25 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_penalty = sum(5 for i in issues if i.severity == ValidationSeverity.WARNING)

        # 根据字段数量调整惩罚
        total_penalty = error_penalty + warning_penalty
        max_penalty = min(100, field_count * 2)

        score = max(0, 100 - min(total_penalty, max_penalty))
        return score

    def get_validation_summary(self, result: ValidationResult) -> str:
        """获取验证结果摘要

        Args:
            result: 验证结果

        Returns:
            摘要字符串
        """
        lines = [
            f"验证状态: {'✅ 通过' if result.is_valid else '❌ 失败'}",
            f"质量分数: {result.quality_score:.1f}/100",
            f"问题数量: {len(result.issues)} ({len([i for i in result.issues if i.severity == ValidationSeverity.ERROR])} 严重)",
        ]

        if result.issues:
            lines.append("\n问题详情:")
            for issue in result.issues:
                lines.append(f"  - [{issue.severity.value.upper()}] {issue.field}: {issue.message}")

        return "\n".join(lines)


def validate_batch(match_data_list: list[dict], validator: DataValidator | None = None) -> dict[str, Any]:
    """批量验证多场比赛数据

    Args:
        match_data_list: 比赛数据列表
        validator: 数据验证器（可选，默认创建新实例）

    Returns:
        验证结果摘要
    """
    if validator is None:
        validator = DataValidator()

    results = {
        "total": len(match_data_list),
        "valid": 0,
        "invalid": 0,
        "issues": [],
        "average_quality_score": 0.0,
    }

    total_score = 0.0

    for match_data in match_data_list:
        result = validator.validate_match_data(match_data)
        total_score += result.quality_score

        if result.is_valid:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            results["issues"].extend(result.get_error_messages())

    results["average_quality_score"] = total_score / len(match_data_list) if match_data_list else 0

    return results


# ============================================
# V20.0 新增方法
# ============================================


class FeatureForgeValidator(DataValidator):
    """
    V20.0 特征加工厂专用验证器

    继承 DataValidator 并添加金融量化级功能：
    1. 特征熔断检测
    2. 离群值标记
    3. 时间旅行防护
    4. 跨赛季特征对齐
    """

    def __init__(self, strict_mode: bool = False, enable_sanitization: bool = True):
        super().__init__(strict_mode, enable_sanitization)

        # 被熔断的比赛记录
        self.filtered_matches: dict[MatchStatus, list[int]] = {
            MatchStatus.INVALID: [],
            MatchStatus.OUTLIER: [],
            MatchStatus.MISSING_FEATURES: [],
        }

        # 联赛统计上下文
        self.league_contexts: dict[int, dict] = {}

    def apply_sanitization(
        self, match_id: int, features: dict[str, Any], league_id: int
    ) -> tuple[bool, str, MatchStatus]:
        """
        应用金融量化级清洗准则

        Args:
            match_id: 比赛 ID
            features: 特征字典
            league_id: 联赛 ID

        Returns:
            (是否通过, 原因, 状态)
        """
        # 1. 基本有效性检查（熔断）
        is_valid, reason, status = self.sanitization.check_basic_validity(features)
        if not is_valid:
            self.filtered_matches[status].append(match_id)
            return False, f"熔断: {reason}", status

        # 2. 离群值检测
        league_context = self.league_contexts.get(league_id)
        is_outlier, outlier_reason = self.sanitization.check_outlier(features, league_context)

        if is_outlier:
            self.filtered_matches[MatchStatus.OUTLIER].append(match_id)
            # 离群值不立即拒绝，而是标记审查
            return True, f"离群值: {outlier_reason}", MatchStatus.OUTLIER

        return True, "", MatchStatus.READY

    def update_league_context(self, league_id: int, features_list: list[dict[str, Any]]):
        """
        更新联赛统计上下文（用于离群值检测）

        Args:
            league_id: 联赛 ID
            features_list: 特征列表
        """
        total_xg_list = []
        total_shots_list = []

        for features in features_list:
            home_xg = self.sanitization._get_numeric(features, "xg")
            away_xg = self.sanitization._get_numeric(features, "xg_away")
            total_shots = self.sanitization._get_numeric(features, "shots_total")

            if home_xg is not None and away_xg is not None:
                total_xg_list.append(home_xg + away_xg)

            if total_shots is not None:
                total_shots_list.append(total_shots)

        if total_xg_list:
            xg_array = np.array(total_xg_list)
            self.league_contexts[league_id] = {
                "mean_total_xg": float(np.mean(xg_array)),
                "std_total_xg": float(np.std(xg_array)),
                "median_total_xg": float(np.median(xg_array)),
            }

        if total_shots_list:
            shots_array = np.array(total_shots_list)
            self.league_contexts[league_id]["mean_total_shots"] = float(np.mean(shots_array))
            self.league_contexts[league_id]["std_total_shots"] = float(np.std(shots_array))

    def check_leakage(
        self, match_id: int, features: dict[str, Any], match_time: datetime, historical_matches: list[dict]
    ) -> tuple[bool, str]:
        """
        时间旅行防护 - 检测数据泄露

        Args:
            match_id: 当前比赛 ID
            features: 特征字典
            match_time: 当前比赛时间
            historical_matches: 历史比赛列表（按时间排序）

        Returns:
            (是否泄露, 泄露说明)
        """
        # 检查是否有未来数据混入
        for hist_match in historical_matches:
            hist_time = hist_match.get("match_time")
            if hist_time and hist_time > match_time:
                return True, (
                    f"时间旅行: Match {match_id} 的特征包含 "
                    f"来自未来比赛 {hist_match.get('id')} 的数据 "
                    f"(历史时间: {hist_time} > 当前时间: {match_time})"
                )

        return False, ""

    def get_filtering_report(self) -> dict[str, Any]:
        """获取过滤报告"""
        return {
            "invalid_count": len(self.filtered_matches[MatchStatus.INVALID]),
            "outlier_count": len(self.filtered_matches[MatchStatus.OUTLIER]),
            "missing_count": len(self.filtered_matches[MatchStatus.MISSING_FEATURES]),
            "invalid_ids": self.filtered_matches[MatchStatus.INVALID][:10],  # 样本
            "outlier_ids": self.filtered_matches[MatchStatus.OUTLIER][:10],
        }

    def estimate_missing_xg(self, match_data: dict) -> float | None:
        """
        智能补齐 - 估算缺失的 xG

        策略：
        1. 根据比分推算保守 xG
        2. 使用联赛平均值

        Args:
            match_data: 比赛数据

        Returns:
            估算的总 xG
        """
        home_score = match_data.get("home_score")
        away_score = match_data.get("away_score")
        league_id = match_data.get("league_id")

        if home_score is None or away_score is None:
            return None

        # 策略1: 基于比分的保守估算 (进球 * 0.12)
        total_goals = home_score + away_score
        estimated_xg = total_goals * 0.12  # 保守系数

        # 策略2: 如果有联赛统计，使用均值调整
        if league_id in self.league_contexts:
            league_mean = self.league_contexts[league_id].get("mean_total_xg", 2.5)
            # 混合估算值和联赛均值
            estimated_xg = (estimated_xg * 0.6) + (league_mean * 0.4)

        return max(0.5, estimated_xg)  # 最小值 0.5
