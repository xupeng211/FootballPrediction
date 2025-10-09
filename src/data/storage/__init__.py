
"""
数据存储模块

包含数据湖存储、分层数据管理等功能。
支持Parquet文件存储、数据分区、历史数据归档等。

基于 DATA_DESIGN.md 第2节数据存储设计。
"""


from typing import cast, Any, Optional, Union

from .data_lake_storage import DataLakeStorage

__all__ = ["DataLakeStorage"]
