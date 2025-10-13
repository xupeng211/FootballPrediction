"""
数学工具测试
"""

import pytest
import math
import random
from typing import List, Tuple, Optional, Union


class MathUtils:
    """数学工具类"""

    @staticmethod
    def clamp(
        value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]
    ) -> Union[int, float]:
        """将值限制在指定范围内"""
        return max(min_val, min(max_val, value))

    @staticmethod
    def lerp(a: float, b: float, t: float) -> float:
        """线性插值"""
        return a + (b - a) * t

    @staticmethod
    def normalize_angle(angle: float) -> float:
        """将角度归一化到 [0, 360) 范围"""
        return angle % 360

    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        """角度转弧度"""
        return degrees * math.pi / 180

    @staticmethod
    def radians_to_degrees(radians: float) -> float:
        """弧度转角度"""
        return radians * 180 / math.pi

    @staticmethod
    def distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """计算两点间距离"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
    def is_point_in_circle(
        px: float, py: float, cx: float, cy: float, radius: float
    ) -> bool:
        """判断点是否在圆内"""
        return MathUtils.distance(px, py, cx, cy) <= radius

    @staticmethod
    def average(numbers: List[Union[int, float]]) -> float:
        """计算平均值"""
        if not numbers:
            return 0.0
        return sum(numbers) / len(numbers)

    @staticmethod
    def median(numbers: List[Union[int, float]]) -> float:
        """计算中位数"""
        if not numbers:
            return 0.0

        sorted_nums = sorted(numbers)
        n = len(sorted_nums)

        if n % 2 == 0:
            return (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
        else:
            return sorted_nums[n // 2]

    @staticmethod
    def standard_deviation(numbers: List[Union[int, float]]) -> float:
        """计算标准差"""
        if not numbers:
            return 0.0

        avg = MathUtils.average(numbers)
        variance = sum((x - avg) ** 2 for x in numbers) / len(numbers)
        return math.sqrt(variance)

    @staticmethod
    def factorial(n: int) -> int:
        """计算阶乘"""
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers")
        if n == 0 or n == 1:
            return 1
        return n * MathUtils.factorial(n - 1)

    @staticmethod
    def fibonacci(n: int) -> int:
        """计算斐波那契数列第n项"""
        if n < 0:
            raise ValueError("Fibonacci is not defined for negative numbers")
        if n == 0:
            return 0
        if n == 1:
            return 1

        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    @staticmethod
    def gcd(a: int, b: int) -> int:
        """计算最大公约数"""
        while b:
            a, b = b, a % b
        return abs(a)

    @staticmethod
    def lcm(a: int, b: int) -> int:
        """计算最小公倍数"""
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // MathUtils.gcd(a, b)

    @staticmethod
    def is_prime(n: int) -> bool:
        """判断是否为素数"""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False

        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return False
        return True

    @staticmethod
    def round_to_places(value: float, places: int) -> float:
        """四舍五入到指定小数位"""
        multiplier = 10**places
        return round(value * multiplier) / multiplier

    @staticmethod
    def percentage(part: Union[int, float], total: Union[int, float]) -> float:
        """计算百分比"""
        if total == 0:
            return 0.0
        return (part / total) * 100

    @staticmethod
    def is_power_of_two(n: int) -> bool:
        """判断是否为2的幂"""
        return n > 0 and (n & (n - 1)) == 0

    @staticmethod
    def sum_of_digits(n: int) -> int:
        """计算数字各位之和"""
        return sum(int(digit) for digit in str(abs(n)))

    @staticmethod
    def reverse_number(n: int) -> int:
        """反转数字"""
        sign = -1 if n < 0 else 1
        reversed_str = str(abs(n))[::-1]
        return sign * int(reversed_str)

    @staticmethod
    def moving_average(numbers: List[float], window_size: int) -> List[float]:
        """计算移动平均"""
        if window_size <= 0 or window_size > len(numbers):
            return []

        _result = []
        for i in range(len(numbers) - window_size + 1):
            window = numbers[i : i + window_size]
            result.append(MathUtils.average(window))
        return result

    @staticmethod
    def find_min_max(
        numbers: List[Union[int, float]],
    ) -> Tuple[Optional[Union[int, float]], Optional[Union[int, float]]]:
        """查找最小值和最大值"""
        if not numbers:
            return None, None
        return min(numbers), max(numbers)

    @staticmethod
    def geometric_mean(numbers: List[Union[int, float]]) -> float:
        """计算几何平均数"""
        if not numbers:
            return 0.0
        if any(x <= 0 for x in numbers):
            return 0.0

        product = 1
        for x in numbers:
            product *= x
        return product ** (1 / len(numbers))

    @staticmethod
    def harmonic_mean(numbers: List[Union[int, float]]) -> float:
        """计算调和平均数"""
        if not numbers:
            return 0.0
        if any(x == 0 for x in numbers):
            return 0.0

        return len(numbers) / sum(1 / x for x in numbers)


class TestMathUtils:
    """测试数学工具类"""

    def test_clamp(self):
        """测试值限制"""
        assert MathUtils.clamp(5, 0, 10) == 5
        assert MathUtils.clamp(-5, 0, 10) == 0
        assert MathUtils.clamp(15, 0, 10) == 10
        assert MathUtils.clamp(5.5, 0.0, 10.0) == 5.5

    def test_lerp(self):
        """测试线性插值"""
        assert MathUtils.lerp(0, 10, 0.5) == 5
        assert MathUtils.lerp(0, 10, 0) == 0
        assert MathUtils.lerp(0, 10, 1) == 10
        assert MathUtils.lerp(10, 20, 0.25) == 12.5

    def test_normalize_angle(self):
        """测试角度归一化"""
        assert MathUtils.normalize_angle(0) == 0
        assert MathUtils.normalize_angle(360) == 0
        assert MathUtils.normalize_angle(450) == 90
        assert MathUtils.normalize_angle(-90) == 270

    def test_degrees_to_radians(self):
        """测试角度转弧度"""
        assert MathUtils.degrees_to_radians(0) == 0
        assert MathUtils.degrees_to_radians(180) == math.pi
        assert abs(MathUtils.degrees_to_radians(90) - math.pi / 2) < 0.0001

    def test_radians_to_degrees(self):
        """测试弧度转角度"""
        assert MathUtils.radians_to_degrees(0) == 0
        assert MathUtils.radians_to_degrees(math.pi) == 180
        assert abs(MathUtils.radians_to_degrees(math.pi / 2) - 90) < 0.0001

    def test_distance(self):
        """测试距离计算"""
        assert MathUtils.distance(0, 0, 3, 4) == 5
        assert MathUtils.distance(1, 1, 1, 1) == 0
        assert abs(MathUtils.distance(0, 0, 1, 1) - 1.414) < 0.001

    def test_is_point_in_circle(self):
        """测试点是否在圆内"""
        assert MathUtils.is_point_in_circle(3, 4, 0, 0, 5) is True
        assert MathUtils.is_point_in_circle(6, 0, 0, 0, 5) is False
        assert MathUtils.is_point_in_circle(0, 0, 0, 0, 0) is True

    def test_average(self):
        """测试平均值"""
        assert MathUtils.average([1, 2, 3, 4, 5]) == 3
        assert MathUtils.average([10, 20]) == 15
        assert MathUtils.average([]) == 0.0

    def test_median(self):
        """测试中位数"""
        assert MathUtils.median([1, 2, 3, 4, 5]) == 3
        assert MathUtils.median([1, 2, 3, 4]) == 2.5
        assert MathUtils.median([5]) == 5
        assert MathUtils.median([]) == 0.0

    def test_standard_deviation(self):
        """测试标准差"""
        _data = [2, 4, 4, 4, 5, 5, 7, 9]
        _result = MathUtils.standard_deviation(data)
        assert abs(result - 2) < 0.001
        assert MathUtils.standard_deviation([]) == 0.0

    def test_factorial(self):
        """测试阶乘"""
        assert MathUtils.factorial(0) == 1
        assert MathUtils.factorial(1) == 1
        assert MathUtils.factorial(5) == 120
        assert MathUtils.factorial(6) == 720

    def test_factorial_negative(self):
        """测试负数阶乘"""
        with pytest.raises(ValueError):
            MathUtils.factorial(-1)

    def test_fibonacci(self):
        """测试斐波那契数列"""
        assert MathUtils.fibonacci(0) == 0
        assert MathUtils.fibonacci(1) == 1
        assert MathUtils.fibonacci(2) == 1
        assert MathUtils.fibonacci(5) == 5
        assert MathUtils.fibonacci(10) == 55

    def test_gcd(self):
        """测试最大公约数"""
        assert MathUtils.gcd(48, 18) == 6
        assert MathUtils.gcd(17, 13) == 1
        assert MathUtils.gcd(100, 0) == 100
        assert MathUtils.gcd(-24, 18) == 6

    def test_lcm(self):
        """测试最小公倍数"""
        assert MathUtils.lcm(4, 6) == 12
        assert MathUtils.lcm(17, 13) == 221
        assert MathUtils.lcm(0, 5) == 0

    def test_is_prime(self):
        """测试素数判断"""
        assert MathUtils.is_prime(2) is True
        assert MathUtils.is_prime(3) is True
        assert MathUtils.is_prime(17) is True
        assert MathUtils.is_prime(4) is False
        assert MathUtils.is_prime(9) is False
        assert MathUtils.is_prime(1) is False
        assert MathUtils.is_prime(0) is False

    def test_round_to_places(self):
        """测试四舍五入到指定小数位"""
        assert MathUtils.round_to_places(3.14159, 2) == 3.14
        assert MathUtils.round_to_places(3.145, 2) == 3.15
        assert MathUtils.round_to_places(3.1, 0) == 3.0

    def test_percentage(self):
        """测试百分比计算"""
        assert MathUtils.percentage(25, 100) == 25.0
        assert MathUtils.percentage(50, 200) == 25.0
        assert MathUtils.percentage(10, 0) == 0.0

    def test_is_power_of_two(self):
        """测试是否为2的幂"""
        assert MathUtils.is_power_of_two(1) is True
        assert MathUtils.is_power_of_two(2) is True
        assert MathUtils.is_power_of_two(8) is True
        assert MathUtils.is_power_of_two(16) is True
        assert MathUtils.is_power_of_two(3) is False
        assert MathUtils.is_power_of_two(0) is False
        assert MathUtils.is_power_of_two(-2) is False

    def test_sum_of_digits(self):
        """测试数字各位之和"""
        assert MathUtils.sum_of_digits(123) == 6
        assert MathUtils.sum_of_digits(4567) == 22
        assert MathUtils.sum_of_digits(0) == 0
        assert MathUtils.sum_of_digits(-123) == 6

    def test_reverse_number(self):
        """测试反转数字"""
        assert MathUtils.reverse_number(123) == 321
        assert MathUtils.reverse_number(4567) == 7654
        assert MathUtils.reverse_number(-123) == -321
        assert MathUtils.reverse_number(120) == 21

    def test_moving_average(self):
        """测试移动平均"""
        _data = [1, 2, 3, 4, 5]
        _result = MathUtils.moving_average(data, 3)
        assert _result == [2.0, 3.0, 4.0]

        _result = MathUtils.moving_average(data, 2)
        assert _result == [1.5, 2.5, 3.5, 4.5]

        assert MathUtils.moving_average(data, 6) == []

    def test_find_min_max(self):
        """测试查找最小值和最大值"""
        _data = [3, 1, 4, 1, 5, 9, 2, 6]
        min_val, max_val = MathUtils.find_min_max(data)
        assert min_val == 1
        assert max_val == 9

        assert MathUtils.find_min_max([]) == (None, None)

    def test_geometric_mean(self):
        """测试几何平均数"""
        _data = [2, 8]
        _result = MathUtils.geometric_mean(data)
        assert abs(result - 4) < 0.001

        # 包含0的情况
        assert MathUtils.geometric_mean([2, 0, 8]) == 0.0
        assert MathUtils.geometric_mean([]) == 0.0

    def test_harmonic_mean(self):
        """测试调和平均数"""
        _data = [1, 2, 4]
        _result = MathUtils.harmonic_mean(data)
        assert abs(result - 1.714) < 0.001

        # 包含0的情况
        assert MathUtils.harmonic_mean([1, 0, 2]) == 0.0
        assert MathUtils.harmonic_mean([]) == 0.0
