"""
指标聚合器
Metrics Aggregator

提供指标数据的聚合功能，如计算平均值、总和等。
"""


logger = logging.getLogger(__name__)


class MetricsAggregator:
    """指标聚合器"""

    def __init__(self):
        """初始化聚合器"""
        self.metrics: Dict[str, List[float]] = {}

    def add(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        添加指标值

        Args:
            name: 指标名称
            value: 指标值
            tags: 指标标签
        """
        key = f"{name}:{hash(str(tags))}"
        if key not in self.metrics:
            self.metrics[key] = []
        self.metrics[key].append(value)
        logger.debug(f"添加指标: {key} = {value}")

    def get_average(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """
        获取平均值

        Args:
            name: 指标名称
            tags: 指标标签

        Returns:
            float: 平均值
        """
        key = f"{name}:{hash(str(tags))}"
        values = self.metrics.get(key, [])
        return sum(values) / len(values) if values else 0.0

    def get_sum(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """
        获取总和

        Args:
            name: 指标名称
            tags: 指标标签

        Returns:
            float: 总和
        """
        key = f"{name}:{hash(str(tags))}"
        values = self.metrics.get(key, [])
        return sum(values)

    def get_count(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """
        获取计数

        Args:
            name: 指标名称
            tags: 指标标签

        Returns:
            int: 计数
        """
        key = f"{name}:{hash(str(tags))}"
        values = self.metrics.get(key, [])
        return len(values)

    def get_min(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """
        获取最小值

        Args:
            name: 指标名称
            tags: 指标标签

        Returns:
            float: 最小值
        """
        key = f"{name}:{hash(str(tags))}"
        values = self.metrics.get(key, [])
        return min(values) if values else 0.0

    def get_max(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """
        获取最大值

        Args:
            name: 指标名称
            tags: 指标标签

        Returns:
            float: 最大值
        """
        key = f"{name}:{hash(str(tags))}"
        values = self.metrics.get(key, [])
        return max(values) if values else 0.0

    def get_percentile(
        self, name: str, percentile: float, tags: Optional[Dict[str, str]] = None
    ) -> float:
        """
        获取百分位数

        Args:
            name: 指标名称
            percentile: 百分位数 (0-100)
            tags: 指标标签

        Returns:
            float: 百分位数值
        """
        key = f"{name}:{hash(str(tags))}"
        values = self.metrics.get(key, [])
        if not values:
            return 0.0

        sorted_values = sorted(values)
        # 使用线性插值方法计算百分位数
        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]

        # 计算位置 (n-1) * p/100
        pos = (n - 1) * percentile / 100
        lower = int(pos)
        upper = min(lower + 1, n - 1)

        # 线性插值
        weight = pos - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    def clear(self, name: Optional[str] = None):
        """
        清除指标数据

        Args:
            name: 指标名称，如果为None则清除所有
        """
        if name is None:
            self.metrics.clear()
            logger.debug("清除所有指标数据")
        else:
            keys_to_remove = [k for k in self.metrics.keys() if k.startswith(name)]
            for key in keys_to_remove:
                del self.metrics[key]
            logger.debug(f"清除指标: {name}")

    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        获取所有聚合指标

        Returns:
            Dict[str, Dict[str, float]]: 所有指标的统计信息
        """
        result = {}
        for key, values in self.metrics.items():

            if values:
                name = key.split(":")[0]
                result[name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": self.get_percentile(name, 50),
                    "p95": self.get_percentile(name, 95),
                    "p99": self.get_percentile(name, 99),
                }
        return result