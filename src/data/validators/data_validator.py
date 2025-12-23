"""
数据验证器 - 特征提取前的数据质量验证

提供比赛数据和特征矩阵的验证功能，确保数据质量符合要求。
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """验证严重程度"""
    ERROR = "error"      # 阻止处理的严重错误
    WARNING = "warning"  # 可以继续但需警告
    INFO = "info"        # 信息性提示


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
    issues: List[ValidationIssue]
    quality_score: float  # 0-100

    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    def get_error_messages(self) -> List[str]:
        """获取错误消息列表"""
        return [f"[{i.severity.value.upper()}] {i.field}: {i.message}" for i in self.issues if i.severity == ValidationSeverity.ERROR]

    def get_warning_messages(self) -> List[str]:
        """获取警告消息列表"""
        return [f"[{i.severity.value.upper()}] {i.field}: {i.message}" for i in self.issues if i.severity == ValidationSeverity.WARNING]


class DataValidator:
    """数据验证器 - 特征提取前验证数据质量"""

    # 定义数据质量规则
    REQUIRED_FIELDS = [
        'external_id',
        'home_team',
        'away_team',
        'match_time',
    ]

    REQUIRED_SCORE_FIELDS = [
        'home_score',
        'away_score',
    ]

    NUMERIC_FIELDS = [
        'expected_goals',
        'shots_on_target',
        'possession',
        'shots',
        'corners',
        'home_expected_goals',
        'away_expected_goals',
        'home_shots_on_target',
        'away_shots_on_target',
        'home_possession',
        'away_possession',
    ]

    VALUE_RANGES = {
        'expected_goals': (0, 15),
        'possession': (0, 100),
        'shots': (0, 50),
        'shots_on_target': (0, 20),
        'corners': (0, 25),
        'home_score': (0, 20),
        'away_score': (0, 20),
    }

    SUPPORTED_FORMATS = ['technical_features', 'home_stats_away_stats', 'normalized']
    SUPPORTED_LEAGUES = [47, 48, 8, 54, 23, 34, 13, 61, 57, 55]  # 扩展的联赛支持

    def __init__(self, strict_mode: bool = False):
        """初始化数据验证器

        Args:
            strict_mode: 严格模式，如果有警告也会视为失败
        """
        self.strict_mode = strict_mode

    def validate_match_data(self, match_data: Dict) -> ValidationResult:
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
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field=field,
                    message=f"缺少必需字段: {field}"
                ))

        # 2. 检查比分字段（如果比赛已完成）
        if match_data.get('is_finished', True):
            for field in self.REQUIRED_SCORE_FIELDS:
                if field not in match_data or match_data[field] is None:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=field,
                        message=f"已完成的比赛缺少比分字段: {field}"
                    ))

        # 3. 检查数值范围
        for field, (min_val, max_val) in self.VALUE_RANGES.items():
            if field in match_data:
                value = match_data[field]
                try:
                    num_val = float(value)
                    if not (min_val <= num_val <= max_val):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            field=field,
                            message=f"值超出正常范围: {field}={num_val} (期望: {min_val}-{max_val})",
                            value=num_val
                        ))
                except (ValueError, TypeError):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=field,
                        message=f"数值类型错误: {field}={value}",
                        value=value
                    ))

        # 4. 检查联赛ID
        if 'league_id' in match_data:
            league_id = match_data['league_id']
            try:
                league_id_int = int(league_id)
                if league_id_int not in self.SUPPORTED_LEAGUES:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        field='league_id',
                        message=f"未经验证的联赛ID: {league_id_int}",
                        value=league_id_int
                    ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field='league_id',
                    message=f"联赛ID类型错误: {league_id}",
                    value=league_id
                ))

        # 5. 计算质量分数
        quality_score = self._calculate_quality_score(issues, match_data)

        # 严格模式下，警告也会导致验证失败
        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        if self.strict_mode:
            is_valid = is_valid and not any(i.severity == ValidationSeverity.WARNING for i in issues)

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            quality_score=quality_score
        )

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
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="feature_matrix",
                    message="特征矩阵为空"
                )],
                quality_score=0
            )

        # 1. 检查 NaN 值（仅限数值列）
        numeric_cols = feature_df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            nan_counts = feature_df[numeric_cols].isnull().sum()
            for col, count in nan_counts[nan_counts > 0].items():
                pct = count / len(feature_df) * 100
                severity = ValidationSeverity.ERROR if pct > 50 else ValidationSeverity.WARNING
                issues.append(ValidationIssue(
                    severity=severity,
                    field=col,
                    message=f"NaN 值占比 {pct:.1f}%: {col} ({count}/{len(feature_df)})",
                    value=count
                ))

        # 2. 检查无穷值
        for col in numeric_cols:
            try:
                if (feature_df[col] == float('inf')).any() or (feature_df[col] == float('-inf')).any():
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field=col,
                        message=f"发现无穷值: {col}"
                    ))
            except (TypeError, ValueError):
                # 跳过无法比较的列
                pass

        # 3. 检查常数列（没有变化）
        for col in feature_df.columns:
            try:
                if feature_df[col].nunique() == 1:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        field=col,
                        message=f"常数列（无变化）: {col} = {feature_df[col].iloc[0]}"
                    ))
            except (TypeError, ValueError):
                # 跳过无法比较的列（如 dict/object 列）
                pass

        # 4. 计算质量分数
        quality_score = self._calculate_quality_score(issues, feature_df)

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            quality_score=quality_score
        )

    def detect_data_format(self, raw_data: Dict) -> Optional[str]:
        """检测数据格式类型

        Args:
            raw_data: 原始数据字典

        Returns:
            格式类型：'technical_features', 'home_stats_away_stats', 或 None
        """
        if 'technical_features' in raw_data:
            return 'technical_features'
        elif 'home_stats' in raw_data and 'away_stats' in raw_data:
            return 'home_stats_away_stats'
        elif all(k in raw_data for k in ['home_expected_goals', 'away_expected_goals']):
            return 'normalized'
        return None

    def _calculate_quality_score(self, issues: List[ValidationIssue], data_context: Any) -> float:
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


def validate_batch(match_data_list: List[Dict], validator: Optional[DataValidator] = None) -> Dict[str, Any]:
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
        'total': len(match_data_list),
        'valid': 0,
        'invalid': 0,
        'issues': [],
        'average_quality_score': 0.0,
    }

    total_score = 0.0

    for match_data in match_data_list:
        result = validator.validate_match_data(match_data)
        total_score += result.quality_score

        if result.is_valid:
            results['valid'] += 1
        else:
            results['invalid'] += 1
            results['issues'].extend(result.get_error_messages())

    results['average_quality_score'] = total_score / len(match_data_list) if match_data_list else 0

    return results
