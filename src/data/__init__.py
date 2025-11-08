from . import collectors, features, processing

"""
数据管道模块

包含足球预测系统的数据采集、存储、清洗和处理组件。
基于 DATA_DESIGN.md 的设计实现完整的数据管道架构.

子模块:
- collectors: 数据采集器（赛程、赔率、比分）
- storage: 数据存储（数据湖、分层存储）
- processing: 数据处理（清洗,标准化,缺失值处理）
- quality: 数据质量监控和异常检测
- features: 特征仓库和特征工程
"""

__all__ = ["collectors", "storage", "processing", "quality", "features"]
