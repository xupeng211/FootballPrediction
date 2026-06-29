#!/usr/bin/env python3
"""
V4.45 核心算力中心 - 安全表达式求值模块
=========================================

从 src/utils/safe_eval.py 迁移
提供安全的数学表达式求值功能

Author: V4.45 Grand Unification Team
Date: 2026-03-08
"""

import ast
from collections.abc import Callable
import operator
from typing import Any

# 允许的操作符
ALLOWED_OPERATORS: dict[type[ast.operator] | type[ast.unaryop], Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

# 允许的函数
ALLOWED_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "max": max,
    "min": min,
    "sum": sum,
    "round": round,
}


def safe_eval(expression: str, variables: dict[str, Any] | None = None) -> Any:
    """
    安全地求值数学表达式

    Args:
        expression: 数学表达式字符串 (如 "2 + 3 * 4")
        variables: 变量字典 (如 {"x": 10, "y": 20})

    Returns:
        表达式计算结果

    Raises:
        ValueError: 表达式不安全或语法错误
    """
    if variables is None:
        variables = {}

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"语法错误: {e}") from e

    return _eval_node(tree.body, variables)


def _eval_node(node: ast.AST, variables: dict[str, Any]) -> Any:  # noqa: C901, PLR0911
    """递归求值 AST 节点"""
    if isinstance(node, ast.Constant):  # Python 3.8+
        return node.value
    # ast.Num removed in Python 3.12+; guard with hasattr for compat.
    if hasattr(ast, "Num") and isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        if node.id in ALLOWED_FUNCTIONS:
            return ALLOWED_FUNCTIONS[node.id]
        raise ValueError(f"未定义的变量: {node.id}")
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        bin_op_type = type(node.op)
        if bin_op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"不允许的操作符: {bin_op_type.__name__}")
        return ALLOWED_OPERATORS[bin_op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, variables)
        unary_op_type = type(node.op)
        if unary_op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"不允许的一元操作符: {unary_op_type.__name__}")
        return ALLOWED_OPERATORS[unary_op_type](operand)
    if isinstance(node, ast.Call):
        func = _eval_node(node.func, variables)
        args = [_eval_node(arg, variables) for arg in node.args]
        return func(*args)
    raise ValueError(f"不支持的表达式类型: {type(node).__name__}")


# 向后兼容导出
__all__ = ["safe_eval"]
