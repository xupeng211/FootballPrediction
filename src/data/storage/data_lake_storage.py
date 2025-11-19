from typing import Optional

"""数据湖存储模块
Data Lake Storage Module.

提供高性能的数据湖存储功能,支持本地和S3存储.
"""

import logging

from .lake import (
    LakeStorageUtils,
    LocalDataLakeStorage,  # 导入拆分后的模块
    MetadataManager,
    PartitionManager,
    S3DataLakeStorage,
)

logger = logging.getLogger(__name__)

# 为了向后兼容,导出DataLakeStorage类
DataLakeStorage = LocalDataLakeStorage

# 导出所有主要类
__all__ = [
    "DataLakeStorage",
    "LocalDataLakeStorage",
    "S3DataLakeStorage",
    "MetadataManager",
    "PartitionManager",
    "LakeStorageUtils",
]
