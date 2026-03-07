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
import operator
from typing import Any


# 允许的操作符
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

# 允许的函数
ALLOWED_FUNCTIONS = {
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


def _eval_node(node: ast.AST, variables: dict[str, Any]) -> Any:
    """递归求值 AST 节点"""
    if isinstance(node, ast.Num):  # Python 3.7
        return node.n
    elif isinstance(node, ast.Constant):  # Python 3.8+
        return node.value
    elif isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        elif node.id in ALLOWED_FUNCTIONS:
            return ALLOWED_FUNCTIONS[node.id]
        else:
            raise ValueError(f"未定义的变量: {node.id}")
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"不允许的操作符: {op_type.__name__}")
        return ALLOWED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, variables)
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"不允许的一元操作符: {op_type.__name__}")
        return ALLOWED_OPERATORS[op_type](operand)
    elif isinstance(node, ast.Call):
        func = _eval_node(node.func, variables)
        args = [_eval_node(arg, variables) for arg in node.args]
        return func(*args)
    else:
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")


# 向后兼容导出
__all__ = ["safe_eval"]
