"""
审计上下文
Audit Context

管理审计过程中的上下文信息。
"""

from typing import Any, Dict, Optional


class AuditContext:
    """
    审计上下文管理器 / Audit Context Manager

    存储和管理审计操作所需的上下文信息。
    Stores and manages context information needed for audit operations.

    Attributes:
        user_id (str): 用户ID / User ID
        username (Optional[str]): 用户名 / Username
        user_role (Optional[str]): 用户角色 / User role
        session_id (Optional[str]): 会话ID / Session ID
        ip_address (Optional[str]): IP地址 / IP address
        user_agent (Optional[str]): 用户代理 / User agent
        request_id (Optional[str]): 请求ID / Request ID
        correlation_id (Optional[str]): 关联ID / Correlation ID
    """

    def __init__(
        self,
        user_id: str,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """
        初始化审计上下文 / Initialize Audit Context

        Args:
            user_id (str): 用户ID / User ID
            username (Optional[str]): 用户名 / Username
            user_role (Optional[str]): 用户角色 / User role
            session_id (Optional[str]): 会话ID / Session ID
            ip_address (Optional[str]): IP地址 / IP address
            user_agent (Optional[str]): 用户代理 / User agent
            request_id (Optional[str]): 请求ID / Request ID
            correlation_id (Optional[str]): 关联ID / Correlation ID
        """
        self.user_id = user_id
        self.username = username
        self.user_role = user_role
        self.session_id = session_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id
        self.correlation_id = correlation_id

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典 / Convert to Dictionary

        Returns:
            Dict[str, Any]: 上下文字典 / Context dictionary
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "user_role": self.user_role,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_request(cls, request, user_info: Optional[Dict[str, Any]] = None):
        """
        从请求创建上下文 / Create Context from Request

        Args:
            request: FastAPI请求对象 / FastAPI request object
            user_info: 用户信息字典 / User info dictionary

        Returns:
            AuditContext: 审计上下文 / Audit context
        """
        # 从请求头获取信息
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        request_id = request.headers.get("x-request-id")
        correlation_id = request.headers.get("x-correlation-id")

        # 从用户信息获取数据
        user_id = None
        username = None
        user_role = None
        session_id = None

        if user_info:
            user_id = user_info.get("user_id")
            username = user_info.get("username")
            user_role = user_info.get("role")
            session_id = user_info.get("session_id")

        return cls(
            user_id=user_id,
            username=username,
            user_role=user_role,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            correlation_id=correlation_id,
        )

    def update(self, **kwargs):
        """
        更新上下文信息 / Update Context Information

        Args:
            **kwargs: 要更新的字段 / Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def merge(self, other_context: "AuditContext") -> "AuditContext":
        """
        合并另一个上下文 / Merge Another Context

        Args:
            other_context: 另一个上下文 / Another context

        Returns:
            AuditContext: 合并后的新上下文 / Merged new context
        """
        merged = self.to_dict()

        # 使用非空值更新
        for key, value in other_context.to_dict().items():
            if value is not None:
                merged[key] = value

        return AuditContext(**merged)

    def clone(self) -> "AuditContext":
        """
        克隆上下文 / Clone Context

        Returns:
            AuditContext: 克隆的上下文 / Cloned context
        """
        return AuditContext(**self.to_dict())

    def is_valid(self) -> bool:
        """
        检查上下文是否有效 / Check if Context is Valid

        Returns:
            bool: 是否有效 / Whether valid
        """
        return bool(self.user_id)

    def get_trace_id(self) -> str:
        """
        获取跟踪ID / Get Trace ID

        Returns:
            str: 跟踪ID / Trace ID
        """
        return self.correlation_id or self.request_id or self.session_id or "unknown"

    def to_log_string(self) -> str:
        """
        转换为日志字符串 / Convert to Log String

        Returns:
            str: 日志字符串 / Log string
        """
        return f"user_id={self.user_id}, username={self.username}, ip={self.ip_address}, session={self.session_id}"