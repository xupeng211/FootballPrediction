"""

"""




    """指标聚合器

    """

        """

        """

        """

        """



        """


        """

        """

        """







        """


        """

        """

        """





        """


        """



        """


        """




        """

        """




        """

        """



from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Deque
import statistics
from .metric_types import MetricPoint, MetricSummary

指标聚合器 / Metrics Aggregator
负责收集、聚合和存储时序指标数据。
class MetricsAggregator:
    提供时序指标的收集、聚合和查询功能。
    支持滑动窗口聚合和百分位数计算。
    def __init__(self, window_size: int = 300):
        初始化聚合器
        Args:
            window_size: 窗口大小（秒），默认5分钟
        self.window_size = window_size
        self.metrics: Dict[str, Deque[MetricPoint]] = defaultdict(
            lambda: deque(maxlen=window_size * 10)  # 保留足够的数据点
        )
        self.aggregates: Dict[str, MetricSummary] = {}
        self.last_update: Dict[str, datetime] = {}
    def add_metric(self, metric: MetricPoint):
        添加指标点
        Args:
            metric: 指标数据点
        key = self._make_key(metric.name, metric.labels)
        # 添加到时间序列
        self.metrics[key].append(metric)
        # 更新聚合
        self._update_aggregates(key)
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        生成指标键
        Args:
            name: 指标名称
            labels: 标签字典
        Returns:
            唯一的指标键
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    def _update_aggregates(self, key: str):
        更新聚合统计
        Args:
            key: 指标键
        metrics = self.metrics[key]
        if not metrics:
            return
        # 清理过期数据
        cutoff_time = datetime.now() - timedelta(seconds=self.window_size)
        while metrics and metrics[0].timestamp < cutoff_time:
            metrics.popleft()
        if not metrics:
            return
        # 提取数值
        values = [m.value for m in metrics]
        # 计算基础统计
        self.aggregates[key] = MetricSummary(
            count=len(values),
            sum=sum(values),
            avg=statistics.mean(values),
            min=min(values),
            max=max(values),
            last=values[-1],
        )
        # 计算百分位数（如果数据量足够）
        if len(values) >= 10:
            sorted_values = sorted(values)
            n = len(sorted_values)
            self.aggregates[key].p50 = sorted_values[int(n * 0.5)]
            self.aggregates[key].p95 = sorted_values[int(n * 0.95)]
            self.aggregates[key].p99 = sorted_values[int(n * 0.99)]
        self.last_update[key] = datetime.now()
    def get_metric(
        self, name: str, labels: Dict[str, str] = None
    ) -> Optional[MetricSummary]:
        获取指标聚合
        Args:
            name: 指标名称
            labels: 标签字典
        Returns:
            指标摘要，如果不存在返回None
        key = self._make_key(name, labels or {})
        return self.aggregates.get(key)
    def get_all_metrics(self) -> Dict[str, Dict[str, MetricSummary]]:
        获取所有指标
        Returns:
            按名称和标签组织的指标字典
        result: Dict[str, Dict[str, MetricSummary]] = {}
        for key, summary in self.aggregates.items():
            # 解析指标键
            name, labels = self._parse_key(key)
            if name not in result:
                result[name] = {}
            result[name][str(labels)] = summary
        return result
    def _parse_key(self, key: str) -> Tuple[str, Dict[str, str]]:
        解析指标键
        Args:
            key: 指标键
        Returns:
            (指标名称, 标签字典)
        if "[" in key:
            name, label_str = key.split("[", 1)
            labels = {}
            # 解析标签字符串
            label_part = label_str.rstrip("]")
            for pair in label_part.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    labels[k] = v
        else:
            name = key
            labels = {}
        return name, labels
    def get_metric_history(
        self, name: str, labels: Dict[str, str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricPoint]:
        获取指标历史数据
        Args:
            name: 指标名称
            labels: 标签字典
            start_time: 开始时间
            end_time: 结束时间
        Returns:
            指标数据点列表
        key = self._make_key(name, labels or {})
        metrics = self.metrics.get(key, [])
        if not metrics:
            return []
        # 过滤时间范围
        if start_time or end_time:
            filtered = []
            for m in metrics:
                if start_time and m.timestamp < start_time:
                    continue
                if end_time and m.timestamp > end_time:
                    continue
                filtered.append(m)
            return filtered
        return list(metrics)
    def clear_expired_metrics(self, max_age: int = 3600):
        清理过期的指标数据
        Args:
            max_age: 最大保留时间（秒）
        cutoff_time = datetime.now() - timedelta(seconds=max_age)
        expired_keys = []
        for key, metrics in self.metrics.items():
            # 清理过期的数据点
            while metrics and metrics[0].timestamp < cutoff_time:
                metrics.popleft()
            # 如果整个指标过期，标记为删除
            if not metrics and key in self.last_update:
                if self.last_update[key] < cutoff_time:
                    expired_keys.append(key)
        # 删除过期的指标
        for key in expired_keys:
            del self.metrics[key]
            if key in self.aggregates:
                del self.aggregates[key]
            if key in self.last_update:
                del self.last_update[key]
    def get_metrics_count(self) -> Dict[str, int]:
        获取指标统计信息
        Returns:
            指标数量统计
        return {
            "total_metrics": len(self.metrics),
            "total_points": sum(len(m) for m in self.metrics.values()),
            "active_aggregates": len(self.aggregates),
        }