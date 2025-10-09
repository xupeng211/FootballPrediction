"""
统计工具模块

提供各种统计计算的工具函数。
"""

import statistics
from typing import Any, Dict, List, Optional


class StatisticsUtils:
    """统计工具类"""

    @staticmethod
    def calculate_mean(data: Any) -> Optional[float]:
        """
        计算均值

        Args:
            data: 数据列表或Series

        Returns:
            均值，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            return float(statistics.mean(data))
        except (TypeError, ValueError, statistics.StatisticsError):
            return None

    @staticmethod
    def calculate_std(data: Any) -> Optional[float]:
        """
        计算标准差

        Args:
            data: 数据列表或Series

        Returns:
            标准差，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) <= 1:
                return None
            return float(statistics.stdev(data))
        except (TypeError, ValueError, statistics.StatisticsError):
            return None

    @staticmethod
    def calculate_min(data: Any) -> Optional[float]:
        """
        计算最小值

        Args:
            data: 数据列表或Series

        Returns:
            最小值，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            return float(min(data))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def calculate_max(data: Any) -> Optional[float]:
        """
        计算最大值

        Args:
            data: 数据列表或Series

        Returns:
            最大值，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            return float(max(data))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def calculate_median(data: Any) -> Optional[float]:
        """
        计算中位数

        Args:
            data: 数据列表或Series

        Returns:
            中位数，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            return float(statistics.median(data))
        except (TypeError, ValueError, statistics.StatisticsError):
            return None

    @staticmethod
    def calculate_percentile(data: Any, percentile: float) -> Optional[float]:
        """
        计算百分位数

        Args:
            data: 数据列表或Series
            percentile: 百分位数（0-100）

        Returns:
            百分位数，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            import numpy as np

            return float(np.percentile(data, percentile))
        except (TypeError, ValueError, ImportError):
            return None

    @staticmethod
    def calculate_skewness(data: Any) -> Optional[float]:
        """
        计算偏度

        Args:
            data: 数据列表或Series

        Returns:
            偏度，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) < 3:
                return None
            import scipy.stats as stats

            return float(stats.skew(data))
        except (TypeError, ValueError, ImportError):
            return None

    @staticmethod
    def calculate_kurtosis(data: Any) -> Optional[float]:
        """
        计算峰度

        Args:
            data: 数据列表或Series

        Returns:
            峰度，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) < 4:
                return None
            import scipy.stats as stats

            return float(stats.kurtosis(data))
        except (TypeError, ValueError, ImportError):
            return None

    @staticmethod
    def calculate_correlation(x: Any, y: Any) -> Optional[float]:
        """
        计算相关系数

        Args:
            x: 数据列表或Series
            y: 数据列表或Series

        Returns:
            相关系数，如果数据无效则返回None
        """
        try:
            if x is None or y is None or len(x) != len(y) or len(x) < 2:
                return None
            import numpy as np

            return float(np.corrcoef(x, y)[0, 1])
        except (TypeError, ValueError, ImportError):
            return None

    @staticmethod
    def calculate_rolling_mean(data: Any, window: int = 3):
        """
        计算滚动均值

        Args:
            data: 数据Series或列表
            window: 窗口大小

        Returns:
            滚动均值Series
        """
        try:
            import pandas as pd

            if hasattr(data, "rolling"):
                # 如果是pandas Series
                return data.rolling(window=window, min_periods=1).mean()
            else:
                # 如果是列表，转换为Series
                series = pd.Series(data)
                return series.rolling(window=window, min_periods=1).mean()
        except Exception:
            import pandas as pd

            return pd.Series([None] * len(data))

    @staticmethod
    def calculate_rolling_std(data: Any, window: int = 3):
        """
        计算滚动标准差

        Args:
            data: 数据Series或列表
            window: 窗口大小

        Returns:
            滚动标准差Series
        """
        try:
            import pandas as pd

            if hasattr(data, "rolling"):
                return data.rolling(window=window, min_periods=1).std()
            else:
                series = pd.Series(data)
                return series.rolling(window=window, min_periods=1).std()
        except Exception:
            import pandas as pd

            return pd.Series([None] * len(data))

    @staticmethod
    def calculate_moving_average(data: Any, periods: List[int] = None):
        """
        计算多个周期的移动平均

        Args:
            data: 数据列表
            periods: 周期列表，如 [3, 5, 10]

        Returns:
            Dict[int, List[float]]: 周期到移动平均值的映射
        """
        if periods is None:
            periods = [3, 5, 10]

        results = {}
        for period in periods:
            if len(data) >= period:
                moving_avg = []
                for i in range(period - 1, len(data)):
                    window = data[i - period + 1 : i + 1]
                    avg = StatisticsUtils.calculate_mean(window)
                    moving_avg.append(avg)
                results[period] = moving_avg

        return results

    @staticmethod
    def detect_outliers(data: Any, method: str = "iqr", multiplier: float = 1.5):
        """
        检测异常值

        Args:
            data: 数据列表
            method: 检测方法 ('iqr' 或 'zscore')
            multiplier: 乘数

        Returns:
            Dict[str, Any]: 异常值检测结果
        """
        if data is None or len(data) == 0:
            return {"outliers": [], "indices": [], "method": method}

        data_list = list(data)
        outlier_indices = []

        if method == "iqr":
            q1 = StatisticsUtils.calculate_percentile(data_list, 25)
            q3 = StatisticsUtils.calculate_percentile(data_list, 75)
            iqr = q3 - q1 if q1 and q3 else 0

            if iqr > 0:
                lower_bound = q1 - multiplier * iqr
                upper_bound = q3 + multiplier * iqr

                for i, value in enumerate(data_list):
                    if value < lower_bound or value > upper_bound:
                        outlier_indices.append(i)

        elif method == "zscore":
            mean = StatisticsUtils.calculate_mean(data_list)
            std = StatisticsUtils.calculate_std(data_list)

            if mean and std and std > 0:
                for i, value in enumerate(data_list):
                    zscore = abs((value - mean) / std)
                    if zscore > multiplier:
                        outlier_indices.append(i)

        outliers = [data_list[i] for i in outlier_indices]

        return {
            "outliers": outliers,
            "indices": outlier_indices,
            "count": len(outliers),
            "percentage": len(outliers) / len(data_list) * 100,
            "method": method,
            "multiplier": multiplier,
        }

    @staticmethod
    def calculate_distribution_stats(data: Any) -> Dict[str, Any]:
        """
        计算分布统计信息

        Args:
            data: 数据列表

        Returns:
            Dict[str, Any]: 分布统计信息
        """
        if data is None or len(data) == 0:
            return {}

        stats = {
            "count": len(data),
            "mean": StatisticsUtils.calculate_mean(data),
            "median": StatisticsUtils.calculate_median(data),
            "std": StatisticsUtils.calculate_std(data),
            "min": StatisticsUtils.calculate_min(data),
            "max": StatisticsUtils.calculate_max(data),
            "skewness": StatisticsUtils.calculate_skewness(data),
            "kurtosis": StatisticsUtils.calculate_kurtosis(data),
            "q25": StatisticsUtils.calculate_percentile(data, 25),
            "q75": StatisticsUtils.calculate_percentile(data, 75),
            "range": None,
            "iqr": None,
        }

        if stats["min"] is not None and stats["max"] is not None:
            stats["range"] = stats["max"] - stats["min"]

        if stats["q25"] is not None and stats["q75"] is not None:
            stats["iqr"] = stats["q75"] - stats["q25"]

        return stats
