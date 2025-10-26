from typing import Any, Dict, Optional
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.exc import SQLAlchemyError, DatabaseError
from sqlalchemy.orm import validates
from ..base import BaseModel
from ..types import JsonbType

class RawData(BaseModel):
    __table_args__ = {'extend_existing': True}