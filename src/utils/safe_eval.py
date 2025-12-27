#!/usr/bin/env python3
"""
安全表达式求值器 - V11.0

替换不安全的 eval()，使用 AST 解析实现安全的数学表达式计算。
支持 NaN 处理，避免代码注入风险。

Author: V11.0 Security Team
Version: 1.0.0
"""

import ast
import logging
import operator
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SafeExpressionEvaluator:
    """
    安全表达式求值器

    核心功能:
    1. 使用 AST 解析代替 eval()，避免代码注入
    2. 支持 NaN 安全的数学运算
    3. 支持变量替换和简单表达式

    支持的表达式格式:
    - "home.xg + away.xg"
    - "(home.shots - away.shots) / (home.shots + away.shots)"
    - "xg / (shots + 1e-6)"
    """

    # 支持的运算符映射
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # 支持的比较运算符
    COMPARATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    # 支持的函数
    FUNCTIONS = {
        "abs": abs,
        "min": min,
        "max": max,
        "round": round,
        "float": float,
        "int": int,
        "pow": pow,
    }

    def __init__(self, allow_nan_propagation: bool = True):
        """
        初始化安全求值器

        Args:
            allow_nan_propagation: 是否允许 NaN 传播（默认 True）
                - True: NaN 会在计算中传播（推荐用于机器学习）
                - False: NaN 会被替换为 0
        """
        self.allow_nan_propagation = allow_nan_propagation

    def evaluate(self, expr: str, context: dict[str, Any]) -> float:
        """
        安全计算表达式

        Args:
            expr: 数学表达式字符串
                支持格式: "home.xg + away.xg", "(a - b) / (a + b)"
            context: 变量上下文
                例如: {"home": {"xg": 1.5}, "away": {"xg": 0.8}}

        Returns:
            float: 计算结果（NaN 表示缺失值）

        Raises:
            ValueError: 表达式语法错误或不支持的运算
        """
        try:
            tree = ast.parse(expr, mode="eval")
            result = self._eval_node(tree.body, context)

            # 确保返回浮点数或 NaN
            if isinstance(result, (int, float)):
                return float(result)
            elif np.isnan(result):
                return np.nan
            else:
                logger.warning(f"表达式结果类型异常: {type(result)}")
                return float(result) if result is not None else np.nan

        except (SyntaxError, ValueError) as e:
            logger.error(f"表达式解析失败: {expr}, 错误: {e}")
            return np.nan
        except Exception as e:
            logger.error(f"表达式计算失败: {expr}, 错误: {e}")
            return np.nan

    def _eval_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """
        递归求值 AST 节点

        Args:
            node: AST 节点
            context: 变量上下文

        Returns:
            求值结果

        Raises:
            ValueError: 不支持的节点类型或运算
        """
        # 常量节点
        if isinstance(node, ast.Constant):
            return node.value

        # 数字节点 (Python < 3.8)
        elif isinstance(node, ast.Num):
            return node.n

        # 二元运算
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)

            op_type = type(node.op)

            # NaN 安全检查
            if self.allow_nan_propagation:
                if self._is_nan(left) or self._is_nan(right):
                    return np.nan

            # 应用运算符
            if op_type in self.OPERATORS:
                return self.OPERATORS[op_type](left, right)
            else:
                raise ValueError(f"不支持的运算符: {op_type}")

        # 一元运算
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)

            # NaN 安全检查
            if self.allow_nan_propagation and self._is_nan(operand):
                return np.nan

            op_type = type(node.op)
            if op_type in self.OPERATORS:
                return self.OPERATORS[op_type](operand)
            else:
                raise ValueError(f"不支持的一元运算符: {op_type}")

        # 比较运算
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)

            for op, comparator_node in zip(node.ops, node.comparators):
                right = self._eval_node(comparator_node, context)

                # NaN 安全检查
                if self._is_nan(left) or self._is_nan(right):
                    return False  # NaN 比较返回 False

                op_type = type(op)
                if op_type in self.COMPARATORS:
                    if not self.COMPARATORS[op_type](left, right):
                        return False
                    left = right  # 链式比较
                else:
                    raise ValueError(f"不支持的比较运算符: {op_type}")

            return True

        # 变量名
        elif isinstance(node, ast.Name):
            return context.get(node.id, np.nan)

        # 属性访问 (如 home.xg)
        elif isinstance(node, ast.Attribute):
            obj = self._eval_node(node.value, context)

            # 处理字典访问
            if isinstance(obj, dict):
                return obj.get(node.attr, np.nan)
            # 处理对象属性
            else:
                return getattr(obj, node.attr, np.nan)

        # 下标访问 (如 array[0])
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value, context)
            slice_val = self._eval_node(node.slice, context) if hasattr(node.slice, "value") else None

            if isinstance(value, dict):
                return value.get(slice_val, np.nan) if slice_val is not None else value
            elif isinstance(value, (list, tuple)):
                try:
                    index = int(self._eval_node(node.slice, context))
                    return value[index]
                except (IndexError, ValueError, TypeError):
                    return np.nan
            else:
                return np.nan

        # 列表/元组
        elif isinstance(node, (ast.List, ast.Tuple)):
            return [self._eval_node(elt, context) for elt in node.elts]

        # 函数调用
        elif isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name and func_name in self.FUNCTIONS:
                args = [self._eval_node(arg, context) for arg in node.args]
                # 检查参数中的 NaN
                if self.allow_nan_propagation:
                    if any(self._is_nan(arg) for arg in args):
                        return np.nan
                return self.FUNCTIONS[func_name](*args)
            else:
                raise ValueError(f"不支持的函数: {func_name}")

        # 表达式列表
        elif isinstance(node, ast.Expr):
            return self._eval_node(node.value, context)

        else:
            raise ValueError(f"不支持的节点类型: {type(node).__name__}")

    @staticmethod
    def _is_nan(value: Any) -> bool:
        """检查值是否为 NaN 或 None"""
        if value is None:
            return True
        if isinstance(value, float):
            return np.isnan(value)
        return False


# 全局单例
_global_evaluator: SafeExpressionEvaluator | None = None


def get_global_evaluator() -> SafeExpressionEvaluator:
    """获取全局安全求值器"""
    global _global_evaluator
    if _global_evaluator is None:
        _global_evaluator = SafeExpressionEvaluator()
    return _global_evaluator


def safe_eval(expr: str, context: dict[str, Any]) -> float:
    """
    安全表达式求值的便捷函数

    Args:
        expr: 表达式字符串
        context: 变量上下文

    Returns:
        float: 计算结果

    Examples:
        >>> safe_eval("home.xg + away.xg", {"home": {"xg": 1.5}, "away": {"xg": 0.8}})
        2.3
        >>> safe_eval("a / (b + 1e-6)", {"a": 1.0, "b": 0.0})
        1000000.0
        >>> safe_eval("missing + 1", {"other": 2})
        nan
    """
    return get_global_evaluator().evaluate(expr, context)


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    evaluator = SafeExpressionEvaluator()

    # 测试用例
    test_cases = [
        ("1 + 1", {}, 2.0),
        ("home.xg + away.xg", {"home": {"xg": 1.5}, "away": {"xg": 0.8}}, 2.3),
        ("(a - b) / (a + b)", {"a": 10.0, "b": 5.0}, 0.3333333333333333),
        ("x / (y + 1e-6)", {"x": 1.0, "y": 0.0}, 999999.999999),
        ("missing + 1", {"other": 2}, np.nan),
        ("abs(-5)", {}, 5.0),
        ("max(1, 2, 3)", {}, 3.0),
    ]

    print("=" * 60)
    print("安全表达式求值器测试")
    print("=" * 60)

    all_passed = True
    for expr, ctx, expected in test_cases:
        result = evaluator.evaluate(expr, ctx)
        if np.isnan(expected):
            passed = np.isnan(result)
        else:
            passed = abs(result - expected) < 1e-6

        status = "✅" if passed else "❌"
        print(f"{status} {expr} = {result} (预期: {expected})")

        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✅ 所有测试通过")
    else:
        print("❌ 部分测试失败")
