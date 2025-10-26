from typing import Any, Dict, Optional
from datetime import datetime
from datetime import timedelta
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, func

"""
权限审计日志模型

实现全面的数据库操作审计功能，记录所有敏感数据的访问和修改操作。
支持合规要求和安全审计。

基于 DATA_DESIGN.md 中的权限控制设计。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func
from ..base import BaseModel
from ..types import SQLiteCompatibleJSONB
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

class AuditAction(str, Enum):
    """审计操作类型枚举"""

    # 数据操作
    CREATE = "CREATE"  # 创建记录
    READ = "READ"  # 读取记录
    UPDATE = "UPDATE"  # 更新记录
    DELETE = "DELETE"  # 删除记录

    # 权限操作
    GRANT = "GRANT"  # 授予权限
    REVOKE = "REVOKE"  # 撤销权限

    # 系统操作
    LOGIN = "LOGIN"  # 用户登录
    LOGOUT = "LOGOUT"  # 用户登出
    BACKUP = "BACKUP"  # 数据备份
    RESTORE = "RESTORE"  # 数据恢复

    # 配置操作
    CONFIG_CHANGE = "CONFIG_CHANGE"  # 配置变更
    SCHEMA_CHANGE = "SCHEMA_CHANGE"  # 架构变更

class AuditSeverity(str, Enum):
    """审计事件严重级别"""

    INFO = "INFO"  # 信息级：一般性成功事件
    LOW = "LOW"  # 低风险：普通读操作
    MEDIUM = "MEDIUM"  # 中风险：普通写操作
    HIGH = "HIGH"  # 高风险：删除、权限变更
    CRITICAL = "CRITICAL"  # 极高风险：系统级操作

class AuditLog(BaseModel):
    __table_args__ = {'extend_existing': True}
    __tablename__ = "audit_logs"