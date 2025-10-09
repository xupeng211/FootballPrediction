"""
数据质量监控结果类 / Data Quality Monitoring Result Classes

定义数据质量检查的各种结果数据结构。
"""



class DataFreshnessResult:
    """数据新鲜度检查结果"""

    def __init__(
        self,
        table_name: str,
        last_update_time: Optional[datetime],
        records_count: int,
        freshness_hours: float,
        is_fresh: bool,
        threshold_hours: float,
    ):
        """
        初始化数据新鲜度结果

        Args:
            table_name: 表名
            last_update_time: 最后更新时间
            records_count: 记录数量
            freshness_hours: 数据新鲜度（小时）
            is_fresh: 是否新鲜
            threshold_hours: 新鲜度阈值（小时）
        """
        self.table_name = table_name
        self.last_update_time = last_update_time
        self.records_count = records_count
        self.freshness_hours = freshness_hours
        self.is_fresh = is_fresh
        self.threshold_hours = threshold_hours

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "last_update_time": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "records_count": self.records_count,
            "freshness_hours": round(self.freshness_hours, 2),
            "is_fresh": self.is_fresh,
            "threshold_hours": self.threshold_hours,
        }


class DataCompletenessResult:
    """数据完整性检查结果"""

    def __init__(
        self,
        table_name: str,
        total_records: int,
        missing_critical_fields: Dict[str, int],
        missing_rate: float,
        completeness_score: float,
    ):
        """
        初始化数据完整性结果

        Args:
            table_name: 表名
            total_records: 总记录数
            missing_critical_fields: 关键字段缺失统计
            missing_rate: 缺失率
            completeness_score: 完整性评分
        """
        self.table_name = table_name
        self.total_records = total_records
        self.missing_critical_fields = missing_critical_fields
        self.missing_rate = missing_rate
        self.completeness_score = completeness_score

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name, Dict, Optional

            "total_records": self.total_records,
            "missing_critical_fields": self.missing_critical_fields,
            "missing_rate": round(self.missing_rate, 4),
            "completeness_score": round(self.completeness_score, 2),
        }