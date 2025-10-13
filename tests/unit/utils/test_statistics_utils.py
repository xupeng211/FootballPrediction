"""
统计工具测试
"""

import pytest
import math
from typing import List, Tuple, Optional, Dict, Any


class StatisticsUtils:
    """统计工具类"""

    @staticmethod
    def mean(data: List[float]) -> float:
        """计算平均值"""
        if not data:
            return 0.0
        return sum(data) / len(data)

    @staticmethod
    def median(data: List[float]) -> float:
        """计算中位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        n = len(sorted_data)
        mid = n // 2

        if n % 2 == 0:
            return (sorted_data[mid - 1] + sorted_data[mid]) / 2
        else:
            return sorted_data[mid]

    @staticmethod
    def mode(data: List[float]) -> List[float]:
        """计算众数"""
        if not data:
            return []

        counts = {}
        for item in data:
            counts[item] = counts.get(item, 0) + 1

        max_count = max(counts.values())
        return [item for item, count in counts.items() if count == max_count]

    @staticmethod
    def variance(data: List[float], sample: bool = False) -> float:
        """计算方差"""
        if not data:
            return 0.0

        avg = StatisticsUtils.mean(data)
        n = len(data)
        divisor = n - 1 if sample else n

        return sum((x - avg) ** 2 for x in data) / divisor

    @staticmethod
    def standard_deviation(data: List[float], sample: bool = False) -> float:
        """计算标准差"""
        return math.sqrt(StatisticsUtils.variance(data, sample))

    @staticmethod
    def percentile(data: List[float], p: float) -> float:
        """计算百分位数"""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        n = len(sorted_data)
        index = (p / 100) * (n - 1)

        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = int(math.floor(index))
            upper = int(math.ceil(index))
            weight = index - lower
            return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    @staticmethod
    def quartiles(data: List[float]) -> Tuple[float, float, float]:
        """计算四分位数 (Q1, Q2, Q3)"""
        if not data:
            return (0.0, 0.0, 0.0)

        sorted_data = sorted(data)
        n = len(sorted_data)

        Q2 = StatisticsUtils.median(sorted_data)

        if n % 2 == 0:
            lower_half = sorted_data[: n // 2]
            upper_half = sorted_data[n // 2 :]
        else:
            lower_half = sorted_data[: n // 2]
            upper_half = sorted_data[n // 2 + 1 :]

        Q1 = StatisticsUtils.median(lower_half)
        Q3 = StatisticsUtils.median(upper_half)

        return (Q1, Q2, Q3)

    @staticmethod
    def interquartile_range(data: List[float]) -> float:
        """计算四分位距"""
        Q1, _, Q3 = StatisticsUtils.quartiles(data)
        return Q3 - Q1

    @staticmethod
    def outliers_iqr(data: List[float]) -> List[float]:
        """使用IQR方法检测异常值"""
        if not data:
            return []

        Q1, _, Q3 = StatisticsUtils.quartiles(data)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        return [x for x in data if x < lower_bound or x > upper_bound]

    @staticmethod
    def z_score(value: float, data: List[float]) -> float:
        """计算Z分数"""
        if not data:
            return 0.0

        mean = StatisticsUtils.mean(data)
        std = StatisticsUtils.standard_deviation(data)
        return (value - mean) / std if std != 0 else 0.0

    @staticmethod
    def outliers_zscore(data: List[float], threshold: float = 2.0) -> List[float]:
        """使用Z分数方法检测异常值"""
        if not data:
            return []

        return [x for x in data if abs(StatisticsUtils.z_score(x, data)) > threshold]

    @staticmethod
    def correlation(x: List[float], y: List[float]) -> float:
        """计算皮尔逊相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(a * b for a, b in zip(x, y))
        sum_x2 = sum(a**2 for a in x)
        sum_y2 = sum(b**2 for b in y)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))

        return numerator / denominator if denominator != 0 else 0.0

    @staticmethod
    def covariance(x: List[float], y: List[float], sample: bool = True) -> float:
        """计算协方差"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = StatisticsUtils.mean(x)
        mean_y = StatisticsUtils.mean(y)
        divisor = n - 1 if sample else n

        return sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y)) / divisor

    @staticmethod
    def skewness(data: List[float]) -> float:
        """计算偏度"""
        if not data or len(data) < 3:
            return 0.0

        n = len(data)
        mean = StatisticsUtils.mean(data)
        std = StatisticsUtils.standard_deviation(data, sample=True)

        if std == 0:
            return 0.0

        m3 = sum((x - mean) ** 3 for x in data) / n
        return m3 / (std**3)

    @staticmethod
    def kurtosis(data: List[float]) -> float:
        """计算峰度"""
        if not data or len(data) < 4:
            return 0.0

        n = len(data)
        mean = StatisticsUtils.mean(data)
        std = StatisticsUtils.standard_deviation(data, sample=True)

        if std == 0:
            return 0.0

        m4 = sum((x - mean) ** 4 for x in data) / n
        return m4 / (std**4) - 3  # 减去3得到超额峰度

    @staticmethod
    def summary_statistics(data: List[float]) -> Dict[str, float]:
        """生成汇总统计"""
        if not data:
            return {}

        sorted(data)
        n = len(data)

        return {
            "count": n,
            "mean": StatisticsUtils.mean(data),
            "median": StatisticsUtils.median(data),
            "mode": StatisticsUtils.mode(data)[0]
            if StatisticsUtils.mode(data)
            else None,
            "std": StatisticsUtils.standard_deviation(data, sample=True),
            "variance": StatisticsUtils.variance(data, sample=True),
            "min": min(data),
            "max": max(data),
            "range": max(data) - min(data),
            "q1": StatisticsUtils.quartiles(data)[0],
            "q3": StatisticsUtils.quartiles(data)[2],
            "iqr": StatisticsUtils.interquartile_range(data),
            "skewness": StatisticsUtils.skewness(data),
            "kurtosis": StatisticsUtils.kurtosis(data),
        }

    @staticmethod
    def moving_average(data: List[float], window: int) -> List[float]:
        """计算移动平均"""
        if not data or window <= 0:
            return []

        _result = []
        for i in range(len(data) - window + 1):
            window_data = data[i : i + window]
            result.append(StatisticsUtils.mean(window_data))
        return result

    @staticmethod
    def exponential_smoothing(data: List[float], alpha: float = 0.3) -> List[float]:
        """指数平滑"""
        if not data or not (0 < alpha <= 1):
            return []

        smoothed = [data[0]]
        for i in range(1, len(data)):
            value = alpha * data[i] + (1 - alpha) * smoothed[i - 1]
            smoothed.append(value)
        return smoothed

    @staticmethod
    def linear_regression(x: List[float], y: List[float]) -> Tuple[float, float]:
        """简单线性回归 y = mx + b"""
        if len(x) != len(y) or len(x) < 2:
            return (0.0, 0.0)

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(a * b for a, b in zip(x, y))
        sum_x2 = sum(a**2 for a in x)

        m = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        b = (sum_y - m * sum_x) / n

        return (m, b)

    @staticmethod
    def r_squared(x: List[float], y: List[float]) -> float:
        """计算R平方值"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        m, b = StatisticsUtils.linear_regression(x, y)
        y_mean = StatisticsUtils.mean(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        ss_res = sum((yi - (m * xi + b)) ** 2 for xi, yi in zip(x, y))

        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0


class TestStatisticsUtils:
    """测试统计工具类"""

    def test_mean(self):
        """测试平均值"""
        assert StatisticsUtils.mean([1, 2, 3, 4, 5]) == 3
        assert StatisticsUtils.mean([2, 4, 6, 8]) == 5
        assert StatisticsUtils.mean([1]) == 1
        assert StatisticsUtils.mean([]) == 0.0

    def test_median_odd(self):
        """测试中位数-奇数个元素"""
        assert StatisticsUtils.median([1, 3, 5]) == 3
        assert StatisticsUtils.median([1, 2, 3, 4, 5]) == 3

    def test_median_even(self):
        """测试中位数-偶数个元素"""
        assert StatisticsUtils.median([1, 2, 3, 4]) == 2.5
        assert StatisticsUtils.median([2, 4, 6, 8, 10, 12]) == 7

    def test_median_empty(self):
        """测试中位数-空列表"""
        assert StatisticsUtils.median([]) == 0.0

    def test_mode_single(self):
        """测试众数-单个众数"""
        assert StatisticsUtils.mode([1, 2, 2, 3, 4]) == [2]
        assert StatisticsUtils.mode([10, 10, 10, 5, 6]) == [10]

    def test_mode_multiple(self):
        """测试众数-多个众数"""
        _result = StatisticsUtils.mode([1, 1, 2, 2, 3])
        assert set(result) == {1, 2}

    def test_mode_empty(self):
        """测试众数-空列表"""
        assert StatisticsUtils.mode([]) == []

    def test_variance_population(self):
        """测试方差-总体方差"""
        _data = [2, 4, 4, 4, 5, 5, 7, 9]
        _result = StatisticsUtils.variance(data, sample=False)
        assert abs(result - 4) < 0.001

    def test_variance_sample(self):
        """测试方差-样本方差"""
        _data = [2, 4, 4, 4, 5, 5, 7, 9]
        _result = StatisticsUtils.variance(data, sample=True)
        assert abs(result - 4.571) < 0.001

    def test_standard_deviation(self):
        """测试标准差"""
        _data = [2, 4, 4, 4, 5, 5, 7, 9]
        _result = StatisticsUtils.standard_deviation(data, sample=True)
        assert abs(result - 2.138) < 0.001

    def test_percentile(self):
        """测试百分位数"""
        _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert StatisticsUtils.percentile(data, 25) == 3.25
        assert StatisticsUtils.percentile(data, 50) == 5.5
        assert StatisticsUtils.percentile(data, 75) == 7.75
        assert StatisticsUtils.percentile(data, 100) == 10

    def test_quartiles(self):
        """测试四分位数"""
        _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        Q1, Q2, Q3 = StatisticsUtils.quartiles(data)
        assert Q1 == 3.5
        assert Q2 == 6.5
        assert Q3 == 9.5

    def test_interquartile_range(self):
        """测试四分位距"""
        _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        _result = StatisticsUtils.interquartile_range(data)
        assert _result == 5  # Q3=7.5, Q1=2.5

    def test_outliers_iqr(self):
        """测试IQR异常值检测"""
        _data = [1, 2, 2, 3, 4, 5, 5, 6, 100]  # 100是异常值
        outliers = StatisticsUtils.outliers_iqr(data)
        assert 100 in outliers
        assert len(outliers) == 1

    def test_z_score(self):
        """测试Z分数"""
        _data = [10, 12, 14, 16, 18]
        # 10的Z分数应该是-1.264
        z = StatisticsUtils.z_score(10, data)
        assert abs(z + 1.264) < 0.001

    def test_outliers_zscore(self):
        """测试Z分数异常值检测"""
        _data = [10, 12, 14, 16, 18, 100]  # 100是异常值
        outliers = StatisticsUtils.outliers_zscore(data, threshold=2.0)
        assert 100 in outliers

    def test_correlation(self):
        """测试相关系数"""
        # 完全正相关
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        assert abs(StatisticsUtils.correlation(x, y) - 1) < 0.001

        # 完全负相关
        y2 = [10, 8, 6, 4, 2]
        assert abs(StatisticsUtils.correlation(x, y2) + 1) < 0.001

        # 无相关
        y3 = [3, 1, 4, 1, 5]
        assert abs(StatisticsUtils.correlation(x, y3)) < 0.1

    def test_covariance(self):
        """测试协方差"""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        cov = StatisticsUtils.covariance(x, y)
        assert abs(cov - 5) < 0.001

    def test_skewness(self):
        """测试偏度"""
        # 右偏（正偏）
        _data = [1, 2, 3, 4, 100]
        skew = StatisticsUtils.skewness(data)
        assert skew > 0

        # 左偏（负偏）
        data2 = [1, 97, 98, 99, 100]
        skew2 = StatisticsUtils.skewness(data2)
        assert skew2 < 0

        # 对称
        data3 = [1, 2, 3, 4, 5]
        skew3 = StatisticsUtils.skewness(data3)
        assert abs(skew3) < 0.1

    def test_kurtosis(self):
        """测试峰度"""
        # 正态分布的峰度接近0
        normal_data = [3, 4, 5, 5, 6, 7]
        kurt = StatisticsUtils.kurtosis(normal_data)
        assert abs(kurt) < 1

    def test_summary_statistics(self):
        """测试汇总统计"""
        _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        summary = StatisticsUtils.summary_statistics(data)

        assert summary["count"] == 10
        assert summary["mean"] == 5.5
        assert summary["median"] == 5.5
        assert summary["min"] == 1
        assert summary["max"] == 10
        assert summary["range"] == 9
        assert "std" in summary
        assert "variance" in summary
        assert "skewness" in summary
        assert "kurtosis" in summary

    def test_moving_average(self):
        """测试移动平均"""
        _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        _result = StatisticsUtils.moving_average(data, 3)
        expected = [2, 3, 4, 5, 6, 7, 8, 9]
        assert _result == expected

        # 窗口大于数据长度
        assert StatisticsUtils.moving_average(data, 20) == []

    def test_exponential_smoothing(self):
        """测试指数平滑"""
        _data = [10, 20, 30, 40, 50]
        _result = StatisticsUtils.exponential_smoothing(data, alpha=0.5)
        assert len(result) == 5
        assert result[0] == 10  # 第一个值不变
        assert result[1] == 15  # 0.5*20 + 0.5*10
        assert result[2] == 22.5  # 0.5*30 + 0.5*15

    def test_linear_regression(self):
        """测试线性回归"""
        # y = 2x + 1
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]
        m, b = StatisticsUtils.linear_regression(x, y)
        assert abs(m - 2) < 0.001
        assert abs(b - 1) < 0.001

    def test_r_squared(self):
        """测试R平方值"""
        # 完美拟合
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]  # y = 2x + 1
        r2 = StatisticsUtils.r_squared(x, y)
        assert abs(r2 - 1) < 0.001

    def test_empty_data_handling(self):
        """测试空数据处理"""
        assert StatisticsUtils.mean([]) == 0.0
        assert StatisticsUtils.median([]) == 0.0
        assert StatisticsUtils.mode([]) == []
        assert StatisticsUtils.variance([]) == 0.0
        assert StatisticsUtils.standard_deviation([]) == 0.0
        assert StatisticsUtils.percentile([], 50) == 0.0
        assert StatisticsUtils.quartiles([]) == (0.0, 0.0, 0.0)
        assert StatisticsUtils.correlation([], []) == 0.0
        assert StatisticsUtils.moving_average([], 3) == []
        assert StatisticsUtils.exponential_smoothing([]) == []

    def test_single_value(self):
        """测试单个值"""
        _data = [5]
        assert StatisticsUtils.mean(data) == 5
        assert StatisticsUtils.median(data) == 5
        assert StatisticsUtils.mode(data) == [5]
        assert StatisticsUtils.variance(data) == 0.0
        assert StatisticsUtils.standard_deviation(data) == 0.0
