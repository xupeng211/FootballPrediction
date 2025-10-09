"""
审计上下文管理

管理用户会话信息和请求上下文。
"""


# 上下文变量，用于在请求处理过程中传递审计信息
audit_context: ContextVar[Dict[str, Any]] = ContextVar("audit_context", default={})


class AuditContext:
    """审计上下文管理器"""

    def __init__(
        self,
        user_id: str,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        初始化审计上下文

        Args:
            user_id: 用户ID
            username: 用户名
            user_role: 用户角色
            session_id: 会话ID
            ip_address: IP地址
            user_agent: 用户代理
        """
        self.user_id = user_id
        self.username = username
        self.user_role = user_role
        self.session_id = session_id
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "user_role": self.user_role,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_request(cls, request, user_id: str) -> "AuditContext":
        """从FastAPI请求创建审计上下文"""
        return cls(
            user_id=user_id,
            username=getattr(request.state, "username", None),
            user_role=getattr(request.state, "user_role", None),
            session_id=getattr(request.state, "session_id", None),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    def __enter__(self):
        """进入上下文管理器"""
        audit_context.set(self.to_dict())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        audit_context.set({})


