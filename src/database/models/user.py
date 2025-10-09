
"""用户数据模型。"""






class User(BaseModel):
    """平台用户表，满足测试所需的基本字段。"""

    __tablename__ = "users"

    username = Column(String(64), unique=True, nullable=False, comment="用户名")
    email = Column(String(128), unique=True, nullable=False, comment="邮箱")
    full_name = Column(String(128), nullable=True, comment="全名")
    password_hash = Column(String(128), nullable=True, comment="密码哈希")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_verified = Column(Boolean, default=False, nullable=False, comment="是否验证")
    is_admin = Column(Boolean, default=False, nullable=False, comment="管理员标记")
    is_analyst = Column(Boolean, default=False, nullable=False, comment="分析师标记")
    is_premium = Column(Boolean, default=False, nullable=False, comment="高级订阅标记")
    is_professional_bettor = Column(
        Boolean, default=False, nullable=False, comment="职业投注者"
    )
    is_casual_bettor = Column(
        Boolean, default=False, nullable=False, comment="休闲投注者"
    )
    last_login = Column(DateTime, nullable=True, comment="最近登录时间")
    subscription_plan = Column(String(32), nullable=True, comment="订阅计划")
    subscription_expires_at = Column(DateTime, nullable=True, comment="订阅过期时间")
    bankroll = Column(Integer, nullable=True, comment="资金池")
    risk_preference = Column(String(16), nullable=True, comment="风险偏好")
    favorite_leagues = Column(JSON, nullable=True, comment="偏好联赛列表")
    timezone = Column(String(64), nullable=True, comment="时区")
    avatar_url = Column(String(256), nullable=True, comment="头像地址")
    specialization = Column(String(128), nullable=True, comment="分析师专长")
    experience_years = Column(Integer, nullable=True, comment="相关经验年限")

    def touch_login(self) -> None:
        """更新最近登录时间。"""
        self.last_login = datetime.utcnow()  # type: ignore[assignment]

    def __repr__(self) -> str:  # pragma: no cover - 调试友好
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
from datetime import datetime

from __future__ import annotations
