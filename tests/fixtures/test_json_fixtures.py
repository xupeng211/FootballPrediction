"""JSON格式测试fixtures"""

import json
from pathlib import Path


def load_json_fixture(filename):
    """加载JSON fixture"""
    fixture_path = Path(__file__).parent / "json" / filename
    if fixture_path.exists():
        with open(fixture_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# 预定义的JSON响应
API_RESPONSES = {
    "health_check": {
        "status": "healthy",
        "timestamp": "2025-10-04T10:00:00Z",
        "version": "1.0.0",
        "database": "connected",
        "cache": "connected",
    },
    "error_response": {
        "detail": "Validation error",
        "errors": [{"field": "email", "message": "Invalid email format"}],
    },
    "prediction_created": {
        "id": 1,
        "status": "pending",
        "created_at": "2025-10-04T10:00:00Z",
    },
}
