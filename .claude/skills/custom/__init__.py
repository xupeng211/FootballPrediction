"""
Claude Skills Package
专业级Claude技能集合
"""

# 导入所有技能
from .data_collection import (
    DataCollectionSkill,
    collect_matches,
    get_collection_status,
    test_api_headers,
    update_api_headers,
)

__all__ = ["DataCollectionSkill", "test_api_headers", "update_api_headers", "collect_matches", "get_collection_status"]
