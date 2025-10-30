"""
数据采集器抽象基类

定义足球数据采集的统一接口和基础功能。
实现了采集日志记录、错误处理、防重复等通用功能。
集成新的重试机制以提高外部API调用的可靠性。

基于 DATA_DESIGN.md 第1.2节设计。
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from src.database.connection import DatabaseManager
from src.utils.retry import RetryConfig, retry

# 外部API重试配置 / External API retry configuration
EXTERNAL_API_RETRY_CONFIG = RetryConfig(
    max_attempts=int(os.getenv("EXTERNAL_API_RETRY_MAX_ATTEMPTS", "3")),
    base_delay=float(os.getenv("EXTERNAL_API_RETRY_BASE_DELAY", "2.0")),
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(aiohttp.ClientError, asyncio.TimeoutError, ConnectionError),
)


@dataclass
class CollectionResult:
    """采集结果数据结构"""

    data_source: str
    collection_type: str
    records_collected: int
    success_count: int
    error_count: int
    status: str  # success/failed/partial
    error_message: Optional[str] = None
    collected_data: Optional[List[Dict[str, Any]]] = None


class DataCollector(ABC):
    """
    数据采集器抽象基类

    定义了数据采集的标准接口和通用功能：
    - 采集日志记录
    - 防重复机制
    - 防丢失策略
    - 错误处理和重试
    """

    def __init__(
        self,
        data_source: str,
        max_retries: int = 3,
        retry_delay: int = 5,
        timeout: int = 30,
    ):
        """
        初始化采集器

        Args:
            data_source: 数据源标识
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 请求超时时间（秒）
        """
        self.data_source = data_source
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"collector.{self.__class__.__name__}")

    @abstractmethod
    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        """
        采集赛程数据

        实现防重复、防丢失策略：
        - 基于match_id + league_id去重
        - 增量同步 + 全量校验

        Returns:
            CollectionResult: 采集结果
        """

    @abstractmethod
    async def collect_odds(self, **kwargs) -> CollectionResult:
        """
        采集赔率数据

        高频采集策略：
        - 每5分钟更新
        - 基于时间戳窗口去重
        - 只保存变化的赔率

        Returns:
            CollectionResult: 采集结果
        """

    @abstractmethod
    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        """
        采集实时比分数据

        实时采集策略：
        - WebSocket连接或轮询
        - 比赛状态管理（开始/进行/结束）
        - 关键事件记录

        Returns:
            CollectionResult: 采集结果
        """

    @retry(EXTERNAL_API_RETRY_CONFIG)
    async def _make_request_with_retry(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发起HTTP请求（带重试机制） / Make HTTP Request (with Retry Mechanism)

        使用新的重试装饰器发起HTTP请求，包含指数退避和抖动。
        Make HTTP request using the new retry decorator with exponential backoff and jitter.

        Args:
            url (str): 请求URL / Request URL
            method (str): HTTP方法 / HTTP method
                Defaults to "GET"
            headers (Optional[Dict[str, str]]): 请求头 / Request headers
                Defaults to None
            params (Optional[Dict[str, Any]]): URL参数 / URL parameters
                Defaults to None
            json_data (Optional[Dict[str, Any]]): JSON数据 / JSON data
                Defaults to None

        Returns:
            Dict[str, Any]: 响应JSON数据 / Response JSON data

        Raises:
            Exception: 请求失败或达到最大重试次数 / Request failed or max retry attempts reached

        Example:
            ```python
            collector = DataCollector("api_source")
            response = await collector._make_request_with_retry(
                "https://api.example.com/data",
                method="GET",
                headers={"Authorization": "Bearer token"}
            )
            ```

        Note:
            该方法包含自动重试机制，使用指数退避和抖动。
            This method includes an automatic retry mechanism with exponential backoff and jitter.
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method=method, url=url, headers=headers, params=params, json=json_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status} for {url}",
                    )

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发起HTTP请求（带重试机制） / Make HTTP Request (with Retry Mechanism)

        Args:
            url (str): 请求URL / Request URL
            method (str): HTTP方法 / HTTP method
                Defaults to "GET"
            headers (Optional[Dict[str, str]]): 请求头 / Request headers
                Defaults to None
            params (Optional[Dict[str, Any]]): URL参数 / URL parameters
                Defaults to None
            json_data (Optional[Dict[str, Any]]): JSON数据 / JSON data
                Defaults to None

        Returns:
            Dict[str, Any]: 响应JSON数据 / Response JSON data

        Raises:
            Exception: 请求失败或达到最大重试次数 / Request failed or max retry attempts reached

        Example:
            ```python
            collector = DataCollector("api_source")
            response = await collector._make_request(
                "https://api.example.com/data",
                method="GET",
                headers={"Authorization": "Bearer token"}
            )
            ```

        Note:
            该方法包含自动重试机制，最大尝试3次。
            This method includes an automatic retry mechanism with up to 3 attempts.
        """
        for attempt in range(self.max_retries):
            try:
                # 使用新的带重试机制的方法
                return await self._make_request_with_retry(
                    url=url,
                    method=method,
                    headers=headers,
                    params=params,
                    json_data=json_data,
                )
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                self.logger.error(f"Request failed for {url}, attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise e

    async def _save_to_bronze_layer(self, table_name: str, raw_data: List[Dict[str, Any]]) -> None:
        """
        保存原始数据到Bronze层

        Args:
            table_name: 目标表名（raw_match_data、raw_odds_data、raw_scores_data）
            raw_data: 原始数据列表
        """
        if not raw_data:
            self.logger.info(f"No data to save to {table_name}")
            return

        try:
            # 导入相应的Bronze层模型

            from .models.raw_data import RawMatchData, RawOddsData, RawScoresData

            # 映射表名到模型类
            model_mapping = {
                "raw_match_data": RawMatchData,
                "raw_odds_data": RawOddsData,
                "raw_scores_data": RawScoresData,
            }

            if table_name not in model_mapping:
                raise ValueError(f"Unsupported table name: {table_name}")

            model_class = model_mapping[table_name]

            async with self.db_manager.get_async_session() as session:
                saved_count = 0
                current_time = datetime.utcnow()

                for data in raw_data:
                    try:
                        # 提取标准字段
                        raw_json = data.get(str("raw_data"), data)

                        # 创建Bronze层记录
                        bronze_record = model_class(
                            data_source=self.data_source,
                            raw_data=raw_json,
                            collected_at=current_time,
                            processed=False,
                        )

                        # 根据表类型设置特定字段
                        if table_name == "raw_match_data":
                            bronze_record.external_match_id = data.get("external_match_id")
                            bronze_record.external_league_id = data.get("external_league_id")
                            if "match_time" in data:
                                try:
                                    match_time_str = data["match_time"]
                                    if isinstance(match_time_str, ((((str):
                                        bronze_record.match_time = datetime.fromisoformat(
                                            match_time_str.replace("Z", "+00:00")))
                                        )
                                except (ValueError)) as e:
                                    self.logger.warning(f"Invalid match_time format: {e}")

                        elif table_name == "raw_odds_data":
                            bronze_record.external_match_id = data.get("external_match_id")
                            bronze_record.bookmaker = data.get("bookmaker")
                            bronze_record.market_type = data.get("market_type")

                        elif table_name == "raw_scores_data":
                            bronze_record.external_match_id = data.get("external_match_id")
                            bronze_record.match_status = data.get("match_status")
                            bronze_record.home_score = data.get("home_score")
                            bronze_record.away_score = data.get("away_score")
                            bronze_record.match_minute = data.get("match_minute")

                        session.add(bronze_record)
                        saved_count += 1

                    except (
                        ValueError)) as e:
                        self.logger.error(f"Failed to create Bronze record: {str(e)}")
                        continue

                # 批量提交
                await session.commit()

                self.logger.info(
                    f"Successfully saved {saved_count}/{len(raw_data)} records to {table_name}"
                )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"{e}")
            return None

    def _is_duplicate_record(
        self,
        new_record: Dict[str, Any],
        existing_records: List[Dict[str, Any]],
        key_fields: List[str],
    ) -> bool:
        """
        检查是否为重复记录

        Args:
            new_record: 新记录
            existing_records: 已有记录列表
            key_fields: 用于去重的关键字段

        Returns:
            bool: 是否重复
        """
        for existing in existing_records:
            if all(
                new_record.get(field) == existing.get(field)
                for field in key_fields
                if field in new_record and field in existing
            ):
                return True
        return False

    async def _create_collection_log(self, collection_type: str) -> int:
        """
        创建采集日志记录（开始时调用）

        Args:
            collection_type: 采集类型

        Returns:
            int: 日志记录ID
        """
        try:
            from .models.data_collection_log import DataCollectionLog

            log_entry = DataCollectionLog(
                data_source=self.data_source, collection_type=collection_type
            )
            log_entry.mark_started()

            async with self.db_manager.get_async_session() as session:
                session.add(log_entry)
                await session.commit()
                await session.refresh(log_entry)
                return log_entry.id

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to create collection log: {str(e)}")
            return 0

    async def _update_collection_log(self, log_id: int, result: CollectionResult) -> None:
        """
        更新采集日志记录（结束时调用）

        Args:
            log_id: 日志记录ID
            result: 采集结果
        """
        try:
            from .models.data_collection_log import CollectionStatus, DataCollectionLog

            if log_id == 0:
                self.logger.warning("Invalid log_id (0), cannot update collection log.")
                return

            async with self.db_manager.get_async_session() as session:
                log_entry = await session.get(str(DataCollectionLog), log_id)
                if log_entry:
                    # 根据结果状态确定最终状态
                    if result.status == "success":
                        status = CollectionStatus.SUCCESS
                    elif result.status == "failed":
                        status = CollectionStatus.FAILED
                    elif result.status == "partial":
                        status = CollectionStatus.PARTIAL
                    else:
                        status = CollectionStatus.FAILED

                    log_entry.mark_completed(
                        status=status,
                        records_collected=result.records_collected,
                        success_count=result.success_count,
                        error_count=result.error_count,
                        error_message=result.error_message,
                    )
                    await session.commit()

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Failed to update collection log: {str(e)}")

    async def collect_all_data(self) -> Dict[str, CollectionResult]:
        """
        执行完整的数据采集流程

        Returns:
            Dict[str, CollectionResult]: 各类型数据的采集结果
        """
        results = {}

        # 按顺序采集各类型数据
        collection_tasks = [
            ("fixtures", self.collect_fixtures),
            ("odds", self.collect_odds),
            ("live_scores", self.collect_live_scores),
        ]

        for data_type, collect_method in collection_tasks:
            log_id = 0
            try:
                self.logger.info(f"Starting {data_type} collection...")

                # 创建采集日志记录
                log_id = await self._create_collection_log(data_type)

                # 执行采集
                result = await collect_method()
                results[data_type] = result

                # 更新采集日志
                await self._update_collection_log(log_id, result)

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                self.logger.error(f"Failed to collect {data_type}: {str(e)}")
                error_result = CollectionResult(
                    data_source=self.data_source,
                    collection_type=data_type,
                    records_collected=0,
                    success_count=0,
                    error_count=1,
                    status="failed",
                    error_message=str(e),
                )
                results[data_type] = error_result

                # 更新采集日志（失败状态）
                await self._update_collection_log(log_id, error_result)

        return results
