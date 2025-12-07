"""
Flows - Prefect工作流模块

提供模型训练和评估的自动化工作流。
"""

from .train_flow import train_flow
from .eval_flow import eval_flow

__all__ = [
    "train_flow",
    "eval_flow",
]
