"""
异常摘要生成器
Anomaly Summary Generator

生成异常检测结果的统计摘要。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from .models import AnomalyResult, AnomalySeverity

logger = logging.getLogger(__name__)


class AnomalySummarizer:
    """异常摘要生成器"""

    def __init__(self):
        """初始化摘要生成器"""
        pass

    async def generate_summary(self, anomalies: List[AnomalyResult]) -> Dict[str, Any]:
        """
        生成异常摘要

        Args:
            anomalies: 异常结果列表

        Returns:
            Dict[str, Any]: 异常摘要
        """
        if not anomalies:
            return {
                "total_anomalies": 0,
                "by_severity": {},
                "by_type": {},
                "by_table": {},
                "summary_time": datetime.now().isoformat(),
            }

        # 按严重程度统计
        by_severity: Dict[str, int] = {}
        for anomaly in anomalies:
            severity = anomaly.severity.value
            by_severity[severity] = by_severity.get(str(severity), 0) + 1

        # 按类型统计
        by_type: Dict[str, int] = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.anomaly_type.value
            by_type[anomaly_type] = by_type.get(str(anomaly_type), 0) + 1

        # 按表统计
        by_table: Dict[str, int] = {}
        for anomaly in anomalies:
            table = anomaly.table_name
            by_table[table] = by_table.get(str(table), 0) + 1

        # 按列统计
        by_column: Dict[str, int] = {}
        for anomaly in anomalies:
            column_key = f"{anomaly.table_name}.{anomaly.column_name}"
            by_column[column_key] = by_column.get(str(column_key), 0) + 1

        # 按检测方法统计
        by_method: Dict[str, int] = {}
        for anomaly in anomalies:
            method = anomaly.detection_method
            by_method[method] = by_method.get(str(method), 0) + 1

        # 计算关键指标
        critical_anomalies = len(
            [a for a in anomalies if a.severity == AnomalySeverity.CRITICAL]
        )
        high_priority_anomalies = len(
            [
                a
                for a in anomalies
                if a.severity in [AnomalySeverity.CRITICAL, AnomalySeverity.HIGH]
            ]
        )

        # 找出最严重的异常
        most_critical = max(
            anomalies,
            key=lambda x: (x.severity.value, x.anomaly_score),
            default=None,
        )

        # 找出影响最严重的表
        most_affected_table = (
            max(by_table.items(), key=lambda x: x[1])[0] if by_table else None
        )

        # 找出影响最严重的列
        most_affected_column = (
            max(by_column.items(), key=lambda x: x[1])[0] if by_column else None
        )

        # 计算平均异常得分
        avg_anomaly_score = sum(a.anomaly_score for a in anomalies) / len(anomalies)

        return {
            # 基本统计
            "total_anomalies": len(anomalies),
            "summary_time": datetime.now().isoformat(),

            # 按维度统计
            "by_severity": by_severity,
            "by_type": by_type,
            "by_table": by_table,
            "by_column": by_column,
            "by_method": by_method,

            # 关键指标
            "critical_anomalies": critical_anomalies,
            "high_priority_anomalies": high_priority_anomalies,
            "most_affected_table": most_affected_table,
            "most_affected_column": most_affected_column,

            # 统计信息
            "avg_anomaly_score": round(avg_anomaly_score, 4),
            "max_anomaly_score": max(a.anomaly_score for a in anomalies),

            # 最严重的异常
            "most_critical_anomaly": most_critical.to_dict() if most_critical else None,

            # 严重程度分布百分比
            "severity_distribution": {
                severity: round(count / len(anomalies) * 100, 2)
                for severity, count in by_severity.items()
            },

            # 健康评分（0-100，100表示无异常）
            "health_score": max(0, 100 - len(anomalies)),

            # 建议措施
            "recommendations": self._generate_recommendations(by_severity, by_type, by_table),
        }

    def _generate_recommendations(
        self,
        by_severity: Dict[str, int],
        by_type: Dict[str, int],
        by_table: Dict[str, int],
    ) -> List[str]:
        """
        根据异常统计生成建议措施

        Args:
            by_severity: 按严重程度统计
            by_type: 按类型统计
            by_table: 按表统计

        Returns:
            List[str]: 建议措施列表
        """
        recommendations = []

        # 基于严重程度的建议
        if by_severity.get("critical", 0) > 0:
            recommendations.append(
                f"发现 {by_severity['critical']} 个严重异常，需要立即处理"
            )

        if by_severity.get("high", 0) > 5:
            recommendations.append(
                f"高风险异常数量较多({by_severity['high']}个)，建议优先处理"
            )

        # 基于异常类型的建议
        if by_type.get("outlier", 0) > 10:
            recommendations.append(
                "离群值异常较多，建议检查数据采集过程是否存在问题"
            )

        if by_type.get("frequency", 0) > 0:
            recommendations.append(
                "发现频率异常，建议检查数据分布是否发生变化"
            )

        if by_type.get("value_range", 0) > 0:
            recommendations.append(
                "发现数值范围异常，建议验证数据约束规则"
            )

        # 基于表影响的建议
        if by_table:
            most_affected = max(by_table.items(), key=lambda x: x[1])
            if most_affected[1] > 5:
                recommendations.append(
                    f"表 {most_affected[0]} 异常较多({most_affected[1]}个)，建议重点检查"
                )

        # 通用建议
        if not recommendations:
            recommendations.append("数据质量良好，继续监控")

        return recommendations