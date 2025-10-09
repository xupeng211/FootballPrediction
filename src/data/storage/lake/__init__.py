"""
数据湖存储模块
Data Lake Storage Module

提供高性能的数据湖存储功能，支持本地和S3存储。
"""


from .local_storage import DataLakeStorage
from .local_storage import LocalDataLakeStorage
from .metadata import MetadataManager
from .partition import PartitionManager
from .s3_storage import S3DataLakeStorage
from .utils import LakeStorageUtils

# 导出主要接口
__all__ = [
    "LocalDataLakeStorage",
    "S3DataLakeStorage",
    "MetadataManager",
    "PartitionManager",
    "LakeStorageUtils",
    "DataLakeStorage",  # 向后兼容
]

# 为了向后兼容
