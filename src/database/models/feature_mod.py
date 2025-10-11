"""特征模块 - 简化版本，用于向后兼容"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class FeatureEntity(Base):
    """特征实体 - 简化版本"""
    __tablename__ = "feature_entities"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    value = Column(Float)
    created_at = Column(DateTime)


class FeatureMetadata(Base):
    """特征元数据 - 简化版本"""
    __tablename__ = "feature_metadata"

    id = Column(Integer, primary_key=True)
    feature_name = Column(String(100))
    description = Column(Text)


# 简化的导出
feature_entity = FeatureEntity
feature_metadata = FeatureMetadata

# 空的模块字典，用于兼容性
feature_types = {}
models = {}