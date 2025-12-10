"""
Data Quality Monitor - 数据质量监控器

与 P0-2 FeatureStore 完全集成的现代化数据质量监控器。
支持基于协议的可插拔规则系统，提供异步批量数据质量检查能力。

核心功能：
- 与 FeatureStoreProtocol 完全集成
- 支持多种数据质量规则
- 异步批量处理能力
- JSON-safe 错误报告
- 重试机制和错误处理
- 统计信息和健康检查

重构版本: P0-3
重构时间: 2025-12-05
重构原因: 原实现只有pass语句，与FeatureStore脱节
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, dict, list, Optional
from dataclasses import dataclass, field

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# 导入P0-2修复的FeatureStore
from src.features.feature_store_interface import FeatureStoreProtocol
from src.quality.quality_protocol import (
    DataQualityRule,
    DataQualityResult,
    RuleSeverity,
)

logger = logging.getLogger(__name__)


@dataclass
class DataQualityStats:
    """数据质量统计信息。

    跟踪数据质量检查的历史记录和统计指标。
    支持序列化和持久化存储。
    """

    total_checks: int = field(default=0)
    passed_checks: int = field(default=0)
    failed_checks: int = field(default=0)
    high_severity_errors: int = field(default=0)
    medium_severity_errors: int = field(default=0)
    low_severity_errors: int = field(default=0)
    last_check_time: Optional[datetime] = field(default=None)
    rule_execution_stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为JSON-safe字典格式。"""
        return {
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "high_severity_errors": self.high_severity_errors,
            "medium_severity_errors": self.medium_severity_errors,
            "low_severity_errors": self.low_severity_errors,
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
            "rule_execution_stats": self.rule_execution_stats,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
        }

    @property
    def success_rate(self) -> float:
        """计算成功率。"""
        if self.total_checks == 0:
            return 0.0
        return (self.passed_checks / self.total_checks) * 100.0

    @property
    def error_rate(self) -> float:
        """计算错误率。"""
        if self.total_checks == 0:
            return 0.0
        return (self.failed_checks / self.total_checks) * 100.0


class DataQualityMonitor:
    """
    数据质量监控器主实现。

    与 P0-2 FeatureStore 完全集成，提供现代化的数据质量检查能力。
    支持基于协议的可插拔规则系统和异步批量处理。

    主要特性：
    - 异步处理能力，支持大规模数据检查
    - 与 FeatureStoreProtocol 完全集成
    - 支持多种数据质量规则
    - 内置重试机制和错误处理
    - 提供详细的统计信息和健康检查
    """

    def __init__(
        self,
        rules: list[DataQualityRule],
        feature_store: FeatureStoreProtocol,
        enable_stats: bool = True,
        max_concurrent_checks: int = 10,
    ):
        """
        初始化数据质量监控器。

        Args:
            rules: 数据质量规则列表
            feature_store: FeatureStore协议实例
            enable_stats: 是否启用统计信息收集
            max_concurrent_checks: 最大并发检查数量
        """
        self.rules = rules
        self.feature_store = feature_store
        self.enable_stats = enable_stats
        self.max_concurrent_checks = max_concurrent_checks

        # 统计信息
        self.stats = DataQualityStats() if enable_stats else None

        # 日志记录器
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 验证规则
        self._validate_rules()

        self.logger.info(f"DataQualityMonitor 初始化完成，加载了 {len(rules)} 个规则")

    def _validate_rules(self) -> None:
        """验证规则配置的有效性。"""
        if not self.rules:
            raise ValueError("至少需要提供一个数据质量规则")

        rule_names = [rule.rule_name for rule in self.rules]
        if len(rule_names) != len(set(rule_names)):
            raise ValueError("规则名称必须唯一")

        for rule in self.rules:
            if not hasattr(rule, "check") or not callable(rule.check):
                raise ValueError(f"规则 {rule.rule_name} 必须实现 check 方法")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def check_match(self, match_id: int) -> dict[str, Any]:
        """
        检查单个比赛的数据质量。

        Args:
            match_id: 比赛ID

        Returns:
            dict[str, Any]: 包含检查结果的字典
                {
                    "match_id": int,
                    "passed": bool,
                    "results": list[dict],  # 各规则的检查结果
                    "summary": dict,       # 检查摘要
                    "timestamp": str       # 检查时间
                }
        """
        start_time = datetime.now(timezone.utc)

        try:
            self.logger.debug(f"开始检查比赛 {match_id} 的数据质量")

            # 从 FeatureStore 加载特征数据
            feature_data = await self.feature_store.load_features(match_id)

            if feature_data is None:
                result = {
                    "match_id": match_id,
                    "passed": False,
                    "results": [],
                    "summary": {
                        "error": "比赛特征数据未找到",
                        "total_rules": len(self.rules),
                        "passed_rules": 0,
                        "failed_rules": len(self.rules),
                    },
                    "timestamp": start_time.isoformat(),
                    "check_duration_ms": (
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds()
                    * 1000,
                }

                if self.stats:
                    self.stats.total_checks += 1
                    self.stats.failed_checks += 1

                return result

            # 提取特征数据字典
            if isinstance(feature_data, dict):
                features = feature_data.get("features", feature_data)
            else:
                # FeatureData 对象，取 features 字段
                features = getattr(feature_data, "features", {})

            # 执行所有规则的检查
            rule_results = await self._execute_rules(features)

            # 分析结果
            passed_count = sum(1 for r in rule_results if r.passed)
            failed_count = len(rule_results) - passed_count

            # 生成检查摘要
            summary = self._generate_summary(rule_results)

            # 更新统计信息
            if self.stats:
                self.stats.total_checks += 1
                if failed_count == 0:
                    self.stats.passed_checks += 1
                else:
                    self.stats.failed_checks += 1

                # 更新错误统计
                for result in rule_results:
                    if result.severity == RuleSeverity.HIGH:
                        self.stats.high_severity_errors += len(result.errors)
                    elif result.severity == RuleSeverity.MEDIUM:
                        self.stats.medium_severity_errors += len(result.errors)
                    elif result.severity == RuleSeverity.LOW:
                        self.stats.low_severity_errors += len(result.errors)

                self.stats.last_check_time = datetime.now(timezone.utc)

            check_duration = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            result = {
                "match_id": match_id,
                "passed": failed_count == 0,
                "results": [r.to_dict() for r in rule_results],
                "summary": summary,
                "timestamp": start_time.isoformat(),
                "check_duration_ms": round(check_duration, 2),
            }

            self.logger.debug(
                f"比赛 {match_id} 数据质量检查完成: "
                f"通过 {passed_count}/{len(self.rules)} 个规则, "
                f"耗时 {check_duration:.2f}ms"
            )

            return result

        except Exception as e:
            error_msg = f"检查比赛 {match_id} 数据质量时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            # 更新错误统计
            if self.stats:
                self.stats.total_checks += 1
                self.stats.failed_checks += 1
                self.stats.last_check_time = datetime.now(timezone.utc)

            return {
                "match_id": match_id,
                "passed": False,
                "results": [],
                "summary": {
                    "error": error_msg,
                    "total_rules": len(self.rules),
                    "passed_rules": 0,
                    "failed_rules": len(self.rules),
                },
                "timestamp": start_time.isoformat(),
                "check_duration_ms": (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds()
                * 1000,
            }

    async def check_batch(self, match_ids: list[int]) -> list[dict[str, Any]]:
        """
        批量检查多个比赛的数据质量。

        Args:
            match_ids: 比赛ID列表

        Returns:
            list[dict]: 每个比赛的检查结果列表
        """
        if not match_ids:
            return []

        self.logger.info(f"开始批量检查 {len(match_ids)} 个比赛的数据质量")

        # 控制并发数量
        semaphore = asyncio.Semaphore(self.max_concurrent_checks)

        async def check_single_match(match_id: int) -> dict[str, Any]:
            async with semaphore:
                return await self.check_match(match_id)

        # 并发执行检查
        tasks = [check_single_match(mid) for mid in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                match_id = match_ids[i]
                processed_results.append(
                    {
                        "match_id": match_id,
                        "passed": False,
                        "results": [],
                        "summary": {
                            "error": f"批量检查异常: {str(result)}",
                            "total_rules": len(self.rules),
                            "passed_rules": 0,
                            "failed_rules": len(self.rules),
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "check_duration_ms": 0,
                    }
                )
            else:
                processed_results.append(result)

        passed_count = sum(1 for r in processed_results if r.get("passed", False))
        self.logger.info(
            f"批量检查完成: {passed_count}/{len(match_ids)} 个比赛通过检查"
        )

        return processed_results

    async def _execute_rules(self, features: dict[str, Any]) -> list[DataQualityResult]:
        """
        执行所有规则的数据质量检查。

        Args:
            features: 特征数据字典

        Returns:
            list[DataQualityResult]: 规则检查结果列表
        """
        results = []

        # 并发执行规则检查
        async def check_single_rule(rule: DataQualityRule) -> DataQualityResult:
            try:
                errors = await rule.check(features)
                passed = len(errors) == 0
                severity = self._determine_severity(errors)

                return DataQualityResult(
                    rule_name=rule.rule_name,
                    passed=passed,
                    errors=errors,
                    severity=severity,
                    metadata={
                        "check_time": datetime.now(timezone.utc).isoformat(),
                        "feature_count": len(features),
                    },
                )
            except Exception as e:
                self.logger.error(f"规则 {rule.rule_name} 执行失败: {str(e)}")
                return DataQualityResult(
                    rule_name=rule.rule_name,
                    passed=False,
                    errors=[f"规则执行异常: {str(e)}"],
                    severity=RuleSeverity.HIGH,
                    metadata={
                        "error": str(e),
                        "check_time": datetime.now(timezone.utc).isoformat(),
                    },
                )

        tasks = [check_single_rule(rule) for rule in self.rules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(
                    DataQualityResult(
                        rule_name="unknown_rule",
                        passed=False,
                        errors=[f"规则检查异常: {str(result)}"],
                        severity=RuleSeverity.HIGH,
                        metadata={"error": str(result)},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _determine_severity(self, errors: list[str]) -> str:
        """
        根据错误信息确定严重程度。

        Args:
            errors: 错误信息列表

        Returns:
            str: 严重程度 (LOW/MEDIUM/HIGH)
        """
        if not errors:
            return RuleSeverity.LOW

        # 基于错误关键词判断严重程度
        error_text = " ".join(errors).lower()

        if any(
            keyword in error_text for keyword in ["缺失", "null", "missing", "critical"]
        ):
            return RuleSeverity.HIGH
        elif any(
            keyword in error_text for keyword in ["超出", "异常", "错误", "invalid"]
        ):
            return RuleSeverity.MEDIUM
        else:
            return RuleSeverity.LOW

    def _generate_summary(self, results: list[DataQualityResult]) -> dict[str, Any]:
        """
        生成检查结果摘要。

        Args:
            results: 规则检查结果列表

        Returns:
            dict[str, Any]: 检查摘要
        """
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        # 按严重程度统计错误
        severity_counts = {
            RuleSeverity.HIGH: 0,
            RuleSeverity.MEDIUM: 0,
            RuleSeverity.LOW: 0,
        }

        total_errors = 0
        for result in results:
            severity_counts[result.severity] += len(result.errors)
            total_errors += len(result.errors)

        return {
            "total_rules": len(results),
            "passed_rules": passed_count,
            "failed_rules": failed_count,
            "pass_rate": (passed_count / len(results)) * 100 if results else 0,
            "total_errors": total_errors,
            "error_severity_distribution": {
                "high": severity_counts[RuleSeverity.HIGH],
                "medium": severity_counts[RuleSeverity.MEDIUM],
                "low": severity_counts[RuleSeverity.LOW],
            },
            "failed_rule_names": [r.rule_name for r in results if not r.passed],
        }

    async def get_stats(self) -> dict[str, Any]:
        """
        获取数据质量监控的统计信息。

        Returns:
            dict[str, Any]: 统计信息字典
        """
        if not self.stats:
            return {"stats_enabled": False, "message": "统计信息收集未启用"}

        return self.stats.to_dict()

    async def health_check(self) -> dict[str, Any]:
        """
        健康检查，评估DataQualityMonitor的状态。

        Returns:
            dict[str, Any]: 健康状态信息
        """
        try:
            # 检查基本配置
            if not self.rules:
                return {"status": "unhealthy", "reason": "没有配置数据质量规则"}

            if not self.feature_store:
                return {"status": "unhealthy", "reason": "FeatureStore未配置"}

            # 测试FeatureStore连接
            try:
                # 尝试加载一个测试用的特征数据
                test_match_id = 1  # 使用一个可能存在的ID
                await self.feature_store.load_features(test_match_id)
                feature_store_status = "healthy"
            except Exception:
                feature_store_status = "warning"

            # 获取统计信息
            stats = await self.get_stats()

            # 计算整体健康状态
            if stats.get("success_rate", 0) >= 80 and feature_store_status == "healthy":
                overall_status = "healthy"
            elif stats.get("success_rate", 0) >= 50:
                overall_status = "warning"
            else:
                overall_status = "unhealthy"

            return {
                "status": overall_status,
                "feature_store_status": feature_store_status,
                "rules_count": len(self.rules),
                "stats": stats,
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"健康检查失败: {str(e)}")
            return {
                "status": "error",
                "reason": f"健康检查异常: {str(e)}",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    def add_rule(self, rule: DataQualityRule) -> None:
        """
        添加新的数据质量规则。

        Args:
            rule: 要添加的规则实例
        """
        if not hasattr(rule, "check") or not callable(rule.check):
            raise ValueError("规则必须实现 check 方法")

        # 检查规则名称唯一性
        existing_names = [r.rule_name for r in self.rules]
        if rule.rule_name in existing_names:
            raise ValueError(f"规则名称 '{rule.rule_name}' 已存在")

        self.rules.append(rule)
        self.logger.info(f"添加新规则: {rule.rule_name}")

    def remove_rule(self, rule_name: str) -> bool:
        """
        移除指定名称的数据质量规则。

        Args:
            rule_name: 要移除的规则名称

        Returns:
            bool: 是否成功移除
        """
        for i, rule in enumerate(self.rules):
            if rule.rule_name == rule_name:
                self.rules.pop(i)
                self.logger.info(f"移除规则: {rule_name}")
                return True

        self.logger.warning(f"未找到要移除的规则: {rule_name}")
        return False

    def get_rule_names(self) -> list[str]:
        """
        获取所有已配置的规则名称。

        Returns:
            list[str]: 规则名称列表
        """
        return [rule.rule_name for rule in self.rules]
