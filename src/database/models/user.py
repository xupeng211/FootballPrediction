from __future__ import annotations


from ..base import BaseModel

"""用户数据模型。"""


from src.database.base import BaseModel


class User(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "users"
