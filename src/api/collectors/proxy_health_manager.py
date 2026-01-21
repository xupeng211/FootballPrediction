#!/usr/bin/env python3
"""
V26.5 代理健康评分管理器 - 智能代理轮换系统
==============================================

核心功能：
    1. 代理健康评分（0-100 分）
    2. 403/429 错误触发"黑屋子"冷却（12 小时）
    3. Timeout 错误降低评分
    4. 加权随机选择（健康评分越高，选中概率越大）
    5. 冷却期过期后恢复可用

设计原则：
    - 容错优先：即使所有代理都失败也不中断流程
    - 透明切换：上层调用者无需关心代理轮换
    - 日志完整：记录每次代理选择和失败事件

Author: TDD Expert & Performance Architect
Version: V26.5
Date: 2026-01-06
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# 代理健康状态数据结构
# ============================================================================


@dataclass
class ProxyHealthStatus:
    """单个代理的健康状态"""

    url: str
    score: int = 100  # 健康评分 (0-100)
    success_count: int = 0  # 成功次数
    failure_count: int = 0  # 失败次数
    last_error: str | None = None  # 最后错误类型
    last_error_time: str | None = None  # 最后错误时间
    cooling_until: str | None = None  # 冷却期截止时间

    def is_cooled(self) -> bool:
        """检查代理是否在冷却期"""
        if not self.cooling_until:
            return False

        try:
            cooling_time = datetime.fromisoformat(self.cooling_until)
            return datetime.now() < cooling_time
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "score": self.score,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "cooling_until": self.cooling_until,
        }


# ============================================================================
# 代理健康评分管理器
# ============================================================================


class ProxyHealthManager:
    """
    V26.5 代理健康评分管理器

    功能：
        1. 管理多个代理的健康状态
        2. 记录每次采集的成功/失败
        3. 自动处理冷却期（403/429 错误）
        4. 加权随机选择代理
        5. 评分恢复机制

    使用示例：
        >>> manager = ProxyHealthManager(proxy_list=["http://proxy1:8080", ...])
        >>> proxy = manager.select_proxy()
        >>> manager.record_success(proxy)
        >>> manager.record_failure(proxy, error_type="403")
    """

    def __init__(
        self,
        proxy_list: list[str] | None = None,
        cooling_duration_hours: int = 12,
        score_penalty_timeout: int = 40,
        score_penalty_banned: int = 100,
        score_recovery_increment: int = 10,
    ):
        """
        初始化代理健康评分管理器

        Args:
            proxy_list: 代理 URL 列表
            cooling_duration_hours: 冷却期时长（小时）
            score_penalty_timeout: 超时扣分
            score_penalty_banned: 被封禁扣分
            score_recovery_increment: 每次成功恢复加分
        """
        self.proxy_list = proxy_list or []
        self.cooling_duration = timedelta(hours=cooling_duration_hours)
        self.score_penalty_timeout = score_penalty_timeout
        self.score_penalty_banned = score_penalty_banned
        self.score_recovery_increment = score_recovery_increment

        # 初始化所有代理的健康状态
        self.proxy_status: dict[str, ProxyHealthStatus] = {}
        for proxy_url in self.proxy_list:
            self.proxy_status[proxy_url] = ProxyHealthStatus(url=proxy_url)

    # ========================================
    # 代理选择逻辑
    # ========================================

    def select_proxy(self) -> str | None:
        """
        加权随机选择代理

        选择逻辑：
            1. 过滤掉冷却中的代理
            2. 根据健康评分计算权重
            3. 加权随机选择

        Returns:
            选中的代理 URL，如果无可用代理则返回 None
        """
        # Step 1: 过滤可用代理
        available_proxies = {
            url: status for url, status in self.proxy_status.items() if not status.is_cooled()
        }

        if not available_proxies:
            logger.warning("⚠️ 所有代理都在冷却期，无法选择代理")
            return None

        # Step 2: 计算权重
        total_score = sum(status.score for status in available_proxies.values())

        if total_score == 0:
            # 所有评分都为 0，随机选择
            return random.choice(list(available_proxies.keys()))

        # Step 3: 加权随机选择
        rand = random.uniform(0, total_score)
        cumulative = 0

        for url, status in available_proxies.items():
            cumulative += status.score
            if rand <= cumulative:
                logger.debug(f"🎯 选择代理: {url} (评分: {status.score})")
                return url

        # 兜底：返回第一个可用代理
        return next(iter(available_proxies.keys()))

    # ========================================
    # 成功/失败记录
    # ========================================

    def record_success(self, proxy_url: str) -> None:
        """
        记录成功请求，恢复评分

        Args:
            proxy_url: 代理 URL
        """
        if proxy_url not in self.proxy_status:
            logger.warning(f"⚠️ 未知代理: {proxy_url}")
            return

        status = self.proxy_status[proxy_url]
        status.success_count += 1

        # 逐步恢复评分
        old_score = status.score
        status.score = min(100, status.score + self.score_recovery_increment)

        logger.info(f"✅ 代理成功: {proxy_url} | 评分: {old_score} → {status.score}")

    def record_failure(
        self,
        proxy_url: str,
        error_type: str,
    ) -> None:
        """
        记录失败请求，更新评分或触发冷却

        Args:
            proxy_url: 代理 URL
            error_type: 错误类型 ('403', '429', 'timeout', 'other')
        """
        if proxy_url not in self.proxy_status:
            logger.warning(f"⚠️ 未知代理: {proxy_url}")
            return

        status = self.proxy_status[proxy_url]
        status.failure_count += 1
        status.last_error = error_type
        status.last_error_time = datetime.now().isoformat()

        # 处理不同错误类型
        if error_type in ("403", "429"):
            # 被封禁：触发冷却期
            status.cooling_until = (datetime.now() + self.cooling_duration).isoformat()
            status.score = 0  # 冷却期间评分为 0
            logger.warning(f"🔒 代理被封禁: {proxy_url} | 冷却期至: {status.cooling_until}")
        elif error_type == "timeout":
            # 超时：降低评分
            old_score = status.score
            status.score = max(0, status.score - self.score_penalty_timeout)
            logger.warning(f"⏱️  代理超时: {proxy_url} | 评分: {old_score} → {status.score}")
        else:
            # 其他错误：轻微扣分
            old_score = status.score
            status.score = max(0, status.score - 10)
            logger.warning(
                f"❌ 代理错误: {proxy_url} | "
                f"类型: {error_type} | 评分: {old_score} → {status.score}"
            )

    # ========================================
    # 统计与查询
    # ========================================

    def get_health_summary(self) -> dict[str, Any]:
        """
        获取代理健康统计摘要

        Returns:
            统计摘要字典
        """
        total_proxies = len(self.proxy_status)
        cooled_proxies = sum(1 for status in self.proxy_status.values() if status.is_cooled())
        available_proxies = total_proxies - cooled_proxies

        avg_score = (
            sum(status.score for status in self.proxy_status.values()) / total_proxies
            if total_proxies > 0
            else 0
        )

        return {
            "total_proxies": total_proxies,
            "available_proxies": available_proxies,
            "cooled_proxies": cooled_proxies,
            "average_score": round(avg_score, 1),
            "proxy_details": [status.to_dict() for status in self.proxy_status.values()],
        }

    def get_proxy_status(self, proxy_url: str) -> ProxyHealthStatus | None:
        """
        获取单个代理的健康状态

        Args:
            proxy_url: 代理 URL

        Returns:
            代理健康状态，如果不存在则返回 None
        """
        return self.proxy_status.get(proxy_url)

    def reset_all_scores(self) -> None:
        """重置所有代理评分（用于新批次）"""
        for status in self.proxy_status.values():
            status.score = 100
            status.success_count = 0
            status.failure_count = 0
            status.last_error = None
            status.last_error_time = None
            status.cooling_until = None

        logger.info("🔄 所有代理评分已重置")

    def add_proxy(self, proxy_url: str) -> None:
        """
        添加新代理

        Args:
            proxy_url: 代理 URL
        """
        if proxy_url not in self.proxy_status:
            self.proxy_status[proxy_url] = ProxyHealthStatus(url=proxy_url)
            self.proxy_list.append(proxy_url)
            logger.info(f"➕ 新增代理: {proxy_url}")

    def remove_proxy(self, proxy_url: str) -> None:
        """
        移除代理

        Args:
            proxy_url: 代理 URL
        """
        if proxy_url in self.proxy_status:
            del self.proxy_status[proxy_url]
            self.proxy_list.remove(proxy_url)
            logger.info(f"➖ 移除代理: {proxy_url}")


# ============================================================================
# 便捷函数
# ============================================================================


def create_proxy_health_manager(
    proxy_list: list[str],
    cooling_duration_hours: int = 12,
) -> ProxyHealthManager:
    """
    创建代理健康评分管理器（工厂函数）

    Args:
        proxy_list: 代理 URL 列表
        cooling_duration_hours: 冷却期时长（小时）

    Returns:
        ProxyHealthManager 实例
    """
    return ProxyHealthManager(
        proxy_list=proxy_list,
        cooling_duration_hours=cooling_duration_hours,
    )
