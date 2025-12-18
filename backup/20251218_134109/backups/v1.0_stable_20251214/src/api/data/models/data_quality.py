"""数据质量报告工具
Data Quality Reporting Tools.

提供统一的数据质量评估和报告功能.
"""


class DataQualityConfig:
    """数据质量配置."""

    def __init__(
        self,
        min_success_rate: float = 0.95,
        min_quality_score: float = 70.0,
        max_error_sample: int = 10,
        enable_warnings: bool = True,
        strict_mode: bool = False
    ):
        self.min_success_rate = min_success_rate
        self.min_quality_score = min_quality_score
        self.max_error_sample = max_error_sample
        self.enable_warnings = enable_warnings
        self.strict_mode = strict_mode


class DataQualityReport:
    """综合数据质量报告."""

    def __init__(self, config: DataQualityConfig = None):
        self.config = config or DataQualityConfig()
        self.reports = {
            'matches': [],
            'odds': [],
            'teams': []
        }
        self.validation_errors = []
        self.validation_warnings = []

    def add_match_result(self, validation_result):
        """添加比赛验证结果."""
        self.reports['matches'].append(validation_result)

        if not validation_result.is_valid:
            self.validation_errors.extend(validation_result.errors)

        if self.config.enable_warnings:
            self.validation_warnings.extend(validation_result.warnings)

    def add_odds_result(self, validation_result, market_type: str = None):
        """添加赔率验证结果."""
        self.reports['odds'].append((validation_result, market_type))

    def add_team_result(self, validation_result, country: str = None):
        """添加球队验证结果."""
        self.reports['teams'].append((validation_result, country))

        if not validation_result.is_valid:
            self.validation_errors.extend(validation_result.errors)

        if self.config.enable_warnings:
            self.validation_warnings.extend(validation_result.warnings)

    def get_summary(self) -> dict[str, Any]:
        """获取综合质量报告摘要."""
        # 计算整体健康状况
        scores = []
        for report in self.reports.values():
            if hasattr(report, 'total_records') and report.total_records > 0:
                success_rate = report.valid_records / report.total_records
                scores.append(success_rate)

        if not scores:
            return {'score': 100.0, 'status': 'excellent'}

        avg_score = sum(scores) / len(scores)
        avg_score *= 100  # 转换为百分制

        if avg_score >= 95:
            status = 'excellent'
        elif avg_score >= 90:
            status = 'good'
        elif avg_score >= 80:
            status = 'fair'
        elif avg_score >= 70:
            status = 'poor'
        else:
            status = 'critical'

        return {
            'score': round(avg_score, 2),
            'status': status
        }

    def _get_common_errors(self) -> list[dict[str, Any]]:
        """获取常见错误."""
        """获取改进建议."""
        recommendations = []

        for module_name, report in self.reports.items():
            if report.total_records > 0:
                success_rate = report.valid_records / report.total_records

                if success_rate < self.config.min_success_rate:
                    recommendations.append(
                        f"{module_name.title()}模块成功率过低 ({success_rate:.1%})，建议检查数据清洗流程"
                    )

        if len(self.validation_errors) > len(self.validation_warnings) * 2:
            recommendations.append("错误数量过多，建议启用更严格的数据验证规则")

        if any('格式' in error or '无效' in error for error in self.validation_errors):
            recommendations.append("发现多个格式错误，建议增加数据格式标准化步骤")

        return recommendations

    def export_to_json(self, filepath: str = None) -> str:
        """导出报告为JSON."""
        """导出错误详情为CSV."""
        import csv
        from io import StringIO

        # 创建CSV数据
        csv_data = []
        for error in self.validation_errors[:self.config.max_error_sample]:
            csv_data.append({
                'timestamp': datetime.now().isoformat(),
                'error_type': 'validation_error',
                'error_message': error
            })

        if not csv_data:
            return ""

        # 生成CSV内容
        output = StringIO()
        if csv_data:
            fieldnames = list(csv_data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        csv_content = output.getvalue()

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(csv_content)

        return csv_content

    def is_healthy(self) -> bool:
        """判断整体数据质量是否健康."""
        """获取快速统计信息."""
        return {
            'total_records': sum(report.total_records for report in self.reports.values()),
            'success_rate': sum(report.valid_records for report in self.reports.values()) / max(
                sum(report.total_records for report in self.reports.values()), 1
            ) * 100,
            'is_healthy': self.is_healthy(),
            'config': {
                'min_success_rate': self.config.min_success_rate,
                'min_quality_score': self.config.min_quality_score,
                'strict_mode': self.config.strict_mode
            }
        }


# 便捷函数
def create_quality_report(
    min_success_rate: float = 0.95,
    min_quality_score: float = 70.0,
    strict_mode: bool = False
) -> DataQualityReport:
    """创建数据质量报告实例."""
    """验证数据集的便捷函数."""
    report = create_quality_report(min_success_rate=min_success_rate)

    result = report.validate_batch_data(dataset_name, data_list, validator_class)

    return {
        'dataset_name': dataset_name,
        'report_summary': report.get_summary(),
        'validation_result': result
    }


# 标准库导入
import json
from collections import Counter
from datetime import datetime
from pydantic import BaseModel, ValidationError

# 本地导入
from .enhanced_match_models import MatchDataQualityReport
from .enhanced_odds_models import OddsDataQualityReport
from .enhanced_team_models import TeamDataQualityReport

class DataQualityConfig:
    def __init__(self, config: DataQualityConfig = None):
        self.config = config or DataQualityConfig()
        self.reports = {
            'matches': MatchDataQualityReport(),
            'odds': OddsDataQualityReport(),
            'teams': TeamDataQualityReport()
        }
        self.validation_errors = []
        self.validation_warnings = []
        self.start_time = datetime.now()
        self.end_time = None
    def add_match_result(self, validation_result):
        self.reports['odds'].add_record_result(validation_result, market_type)
        if not validation_result.is_valid:
            self.validation_errors.extend(validation_result.errors)
        if self.config.enable_warnings:
            self.validation_warnings.extend(validation_result.warnings)
    def add_team_result(self, validation_result, country: str = None):
        if self.end_time is None:
            self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        # 收集各模块报告摘要
        summaries = {}
        for key, report in self.reports.items():
            summaries[key] = report.get_summary()
        # 计算总体统计
        total_records = sum(report['total_records'] for report in self.reports.values())
        total_valid = sum(report['valid_records'] for report in self.reports.values())
        total_invalid = total_records - total_valid
        overall_health = self._calculate_overall_health()
        return {
            'summary': {
                'total_records': total_records,
                'valid_records': total_valid,
                'invalid_records': total_invalid,
                'overall_success_rate': total_valid / max(total_records, 1),
                'overall_health_score': overall_health['score'],
                'overall_health_status': overall_health['status'],
                'validation_duration': duration,
                'strict_mode': self.config.strict_mode
            },
            'modules': summaries,
            'common_errors': self._get_common_errors(),
            'recommendations': self._get_recommendations()
        }
    def _calculate_overall_health(self) -> dict[str, Any]:
        error_counter = Counter(self.validation_errors)
        return [
            {
                'error': error,
                'count': count,
                'percentage': f"{(count / max(len(self.validation_errors), 1)):.1f}%"
            }
            for error, count in error_counter.most_common(self.config.max_error_sample)
        ]
    def _get_recommendations(self) -> list[str]:
        report_data = self.get_summary()
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        return json.dumps(report_data, indent=2, ensure_ascii=False, default=str)
    def export_to_csv(self, filepath: str = None) -> str:
        overall_health = self._calculate_overall_health()
        return (
            overall_health['score'] >= self.config.min_quality_score and
            overall_health['status'] in ['excellent', 'good']
        )
    def get_quick_stats(self) -> dict[str, Any]:
        """获取快速统计信息."""
        return {
            'total_reports': len(self.reports),
            'validation_errors': len(self.validation_errors),
            'validation_warnings': len(self.validation_warnings),
            'health_score': self._calculate_overall_health()['score']
        }


def create_data_quality_config(
    min_success_rate: float = 0.95,
    min_quality_score: float = 70.0,
    strict_mode: bool = False
) -> DataQualityConfig:
    """创建数据质量配置."""
    config = DataQualityConfig(
        min_success_rate=min_success_rate,
        min_quality_score=min_quality_score,
        strict_mode=strict_mode
    )
    return config


def validate_dataset(
    dataset_name: str,
    data_list: list[[BaseModel, dict[str, Any]]],
    validator_class: type[BaseModel],
    min_success_rate: float = 0.95
) -> dict[str, Any]: