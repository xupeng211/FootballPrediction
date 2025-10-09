"""
失败分类器
Failure Classifier

负责分析错误消息并分类失败类型。
"""

import logging
from typing import Dict, List

from .models import FailureType

logger = logging.getLogger(__name__)


class FailureClassifier:
    """失败分类器"""

    def __init__(self):
        """初始化分类器"""
        # 定义关键词映射
        self.keyword_mappings = {
            FailureType.TIMEOUT: [
                "timeout",
                "time out",
                "超时",
                "timed out",
                "deadline",
            ],
            FailureType.CONNECTION_ERROR: [
                "connection",
                "connect",
                "network",
                "socket",
                "连接",
                "网络",
                "unreachable",
                "refused",
                "connection refused",
                "network unreachable",
                "no route",
            ],
            FailureType.DATA_ERROR: [
                "data",
                "parse",
                "format",
                "json",
                "xml",
                "数据",
                "格式",
                "解析",
                "invalid",
                "malformed",
                "decoding",
                "encoding",
            ],
            FailureType.RESOURCE_ERROR: [
                "memory",
                "disk",
                "space",
                "resource",
                "内存",
                "磁盘",
                "空间",
                "资源",
                "out of memory",
                "no space left",
                "quota exceeded",
                "limit exceeded",
            ],
            FailureType.PERMISSION_ERROR: [
                "permission",
                "access",
                "auth",
                "forbidden",
                "权限",
                "访问",
                "认证",
                "禁止",
                "unauthorized",
                "access denied",
                "permission denied",
                "not allowed",
            ],
        }

    def classify_failure(self, error_message: str) -> FailureType:
        """
        分类失败类型

        Args:
            error_message: 错误消息

        Returns:
            FailureType: 失败类型
        """
        if not error_message:
            return FailureType.UNKNOWN_ERROR

        error_lower = error_message.lower()

        # 按优先级检查各种失败类型
        for failure_type, keywords in self.keyword_mappings.items():
            if any(keyword in error_lower for keyword in keywords):
                logger.debug(f"错误分类: {error_message[:50]}... -> {failure_type.value}")
                return failure_type

        # 未匹配到任何已知类型
        logger.debug(f"未知错误类型: {error_message[:50]}...")
        return FailureType.UNKNOWN_ERROR

    def add_custom_keywords(
        self, failure_type: FailureType, keywords: List[str]
    ) -> None:
        """
        添加自定义关键词

        Args:
            failure_type: 失败类型
            keywords: 关键词列表
        """
        if failure_type not in self.keyword_mappings:
            self.keyword_mappings[failure_type] = []

        self.keyword_mappings[failure_type].extend(keywords)
        logger.info(f"已添加自定义关键词到 {failure_type.value}: {keywords}")

    def get_classification_stats(
        self, error_messages: List[str]
    ) -> Dict[str, int]:
        """
        获取分类统计

        Args:
            error_messages: 错误消息列表

        Returns:
            Dict[str, int]: 各类型失败的数量
        """
        stats = {}
        for message in error_messages:
            failure_type = self.classify_failure(message)
            type_name = failure_type.value
            stats[type_name] = stats.get(type_name, 0) + 1

        return stats