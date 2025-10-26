"""
Helper functions
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Optional

def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())

def generate_hash(data: str) -> str:
    """Generate SHA256 hash"""
    return hashlib.sha256(data.encode()).hexdigest()

def safe_get(data: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    """Safely get value from dict"""
    if data is None:
        return default
    return data.get(key, default)

def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp to ISO format"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat()

def sanitize_string(s: str) -> str:
    """Sanitize string input"""
    return s.strip().lower() if s else ""
