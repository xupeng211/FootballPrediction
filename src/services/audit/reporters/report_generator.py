"""
审计报告生成器

生成各种格式的审计报告。
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from src.database.models.audit_log import AuditLog, AuditLogSummary


class AuditReportGenerator:
    """审计报告生成器"""

    def __init__(self):
        """初始化报告生成器"""
        self.logger = logging.getLogger(f"audit.{self.__class__.__name__}")

    def generate_summary_report(
        self,
        summary: AuditLogSummary,
        format: str = "json",
    ) -> Union[str, bytes]:
        """
        生成摘要报告

        Args:
            summary: 审计日志摘要
            format: 报告格式 (json, csv, txt)

        Returns:
            Union[str, bytes]: 报告内容
        """
        try:
            if format.lower() == "json":
                return self._generate_json_summary(summary)
            elif format.lower() == "csv":
                return self._generate_csv_summary(summary)
            elif format.lower() == "txt":
                return self._generate_text_summary(summary)
            else:
                raise ValueError(f"不支持的格式: {format}")

        except Exception as e:
            self.logger.error(f"生成摘要报告失败: {e}", exc_info=True)
            return ""

    def _generate_json_summary(self, summary: AuditLogSummary) -> str:
        """生成JSON格式摘要"""
        data = {
            "report_type": "audit_summary",
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start_date": summary.start_date.isoformat(),
                "end_date": summary.end_date.isoformat(),
            },
            "statistics": {
                "total_operations": summary.total_operations,
                "unique_users": summary.unique_users,
                "unique_tables": summary.unique_tables,
                "high_risk_operations": summary.high_risk_operations,
                "failed_operations": summary.failed_operations,
                "success_rate": (
                    (summary.total_operations - summary.failed_operations)
                    / max(summary.total_operations, 1)
                    * 100
                ),
                "avg_execution_time_ms": summary.avg_execution_time_ms,
            },
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _generate_csv_summary(self, summary: AuditLogSummary) -> str:
        """生成CSV格式摘要"""
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入标题
        writer.writerow(["审计摘要报告"])
        writer.writerow(["生成时间", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # 写入统计信息
        writer.writerow(["统计项", "数值"])
        writer.writerow(["总操作数", summary.total_operations])
        writer.writerow(["独立用户数", summary.unique_users])
        writer.writerow(["独立表数", summary.unique_tables])
        writer.writerow(["高风险操作数", summary.high_risk_operations])
        writer.writerow(["失败操作数", summary.failed_operations])
        writer.writerow(["平均执行时间(ms)", f"{summary.avg_execution_time_ms:.2f}"])

        return output.getvalue()

    def _generate_text_summary(self, summary: AuditLogSummary) -> str:
        """生成文本格式摘要"""
        report = f"""
========================================
审计摘要报告
========================================

生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
统计周期: {summary.start_date.strftime('%Y-%m-%d')} 至 {summary.end_date.strftime('%Y-%m-%d')}

----------------------------------------
统计信息
----------------------------------------
总操作数: {summary.total_operations:,}
独立用户数: {summary.unique_users:,}
独立表数: {summary.unique_tables:,}
高风险操作数: {summary.high_risk_operations:,}
失败操作数: {summary.failed_operations:,}
成功率: {((summary.total_operations - summary.failed_operations) / max(summary.total_operations, 1) * 100):.2f}%
平均执行时间: {summary.avg_execution_time_ms:.2f} ms

========================================
        """.strip()
        return report

    def generate_detailed_report(
        self,
        audit_logs: List[AuditLog],
        format: str = "json",
    ) -> Union[str, bytes]:
        """
        生成详细报告

        Args:
            audit_logs: 审计日志列表
            format: 报告格式

        Returns:
            Union[str, bytes]: 报告内容
        """
        try:
            if format.lower() == "json":
                return self._generate_json_detailed(audit_logs)
            elif format.lower() == "csv":
                return self._generate_csv_detailed(audit_logs)
            elif format.lower() == "txt":
                return self._generate_text_detailed(audit_logs)
            else:
                raise ValueError(f"不支持的格式: {format}")

        except Exception as e:
            self.logger.error(f"生成详细报告失败: {e}", exc_info=True)
            return ""

    def _generate_json_detailed(self, audit_logs: List[AuditLog]) -> str:
        """生成JSON格式详细报告"""
        data = {
            "report_type": "audit_detailed",
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": len(audit_logs),
            "records": [
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "user_id": log.user_id,
                    "username": log.username,
                    "action": log.action.value if log.action else None,
                    "table_name": log.table_name,
                    "record_id": log.record_id,
                    "status": log.status.value if log.status else None,
                    "severity": log.severity.value if log.severity else None,
                    "is_high_risk": log.is_high_risk,
                    "is_sensitive": log.is_sensitive,
                    "execution_time_ms": log.execution_time_ms,
                    "error_message": log.error_message,
                }
                for log in audit_logs
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _generate_csv_detailed(self, audit_logs: List[AuditLog]) -> str:
        """生成CSV格式详细报告"""
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入标题行
        writer.writerow(
            [
                "ID",
                "时间",
                "用户ID",
                "用户名",
                "操作",
                "表名",
                "记录ID",
                "状态",
                "严重程度",
                "高风险",
                "敏感",
                "执行时间(ms)",
                "错误信息",
            ]
        )

        # 写入数据行
        for log in audit_logs:
            writer.writerow(
                [
                    log.id,
                    log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    log.user_id,
                    log.username,
                    log.action.value if log.action else "",
                    log.table_name or "",
                    log.record_id or "",
                    log.status.value if log.status else "",
                    log.severity.value if log.severity else "",
                    "是" if log.is_high_risk else "否",
                    "是" if log.is_sensitive else "否",
                    log.execution_time_ms or "",
                    log.error_message or "",
                ]
            )

        return output.getvalue()

    def _generate_text_detailed(self, audit_logs: List[AuditLog]) -> str:
        """生成文本格式详细报告"""
        output = io.StringIO()
        output.write(f"{'ID':<8} {'时间':<20} {'用户':<15} {'操作':<15} {'表':<20} {'状态':<10}\n")
        output.write("-" * 100 + "\n")

        for log in audit_logs[:100]:  # 限制100条记录
            output.write(
                f"{log.id:<8} "
                f"{log.timestamp.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                f"{log.username or log.user_id or '':<15} "
                f"{log.action.value if log.action else '':<15} "
                f"{log.table_name or '':<20} "
                f"{log.status.value if log.status else '':<10}\n"
            )

        if len(audit_logs) > 100:
            output.write(f"\n... 还有 {len(audit_logs) - 100} 条记录\n")

        return output.getvalue()

    def generate_anomaly_report(
        self,
        anomalies: List[Dict[str, Any]],
        format: str = "json",
    ) -> Union[str, bytes]:
        """
        生成异常报告

        Args:
            anomalies: 异常列表
            format: 报告格式

        Returns:
            Union[str, bytes]: 报告内容
        """
        try:
            if format.lower() == "json":
                return json.dumps(
                    {
                        "report_type": "audit_anomalies",
                        "generated_at": datetime.utcnow().isoformat(),
                        "total_anomalies": len(anomalies),
                        "anomalies": anomalies,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            else:
                # 其他格式简化实现
                return str(anomalies)

        except Exception as e:
            self.logger.error(f"生成异常报告失败: {e}", exc_info=True)
            return ""