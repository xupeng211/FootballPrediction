from typing import Union

class Calculator:
    """增强版计算器"""

    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相加

        Args:
            a: 第一个数
            b: 第二个数

        Returns:
            相加结果
        """
        return a + b

    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相减"""
        return a - b

    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相乘"""
        return a * b
