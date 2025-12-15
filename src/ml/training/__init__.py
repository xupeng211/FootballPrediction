"""
Training Module - 训练管道模块

Phase 2.3: Training Pipeline - 模型训练管道

提供企业级的模型训练管道，支持时间序列切分和防数据泄露机制。
"""

from .trainer import ModelTrainer

__all__ = [
    'ModelTrainer',
]