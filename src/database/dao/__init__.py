"""
数据访问对象模块
Data Access Object Module

提供统一的数据库访问接口。
"""

from .exceptions import *
from .base_dao import BaseDAO
from .schemas import MatchCreate, MatchUpdate, MatchResponse
from .match_dao import MatchDAO

__all__ = [
    'BaseDAO',
    'MatchDAO',
    'MatchCreate',
    'MatchUpdate',
    'MatchResponse',
    'DAOException',
    'RecordNotFoundError',
    'DatabaseConnectionError',
    'ValidationError'
]
