#!/usr/bin/env python3
"""
V20.5 故障容错系统 - 防崩塌机制
================================

核心功能:
1. CircuitBreaker: 熔断器 - 连续失败自动关机
2. CheckpointTracker: 断点续传 - 基于 JSON 的进度追踪
3. FaultTolerantProcessor: 容错处理器 - 全局异常捕获

作者: SRE Team
日期: 2025-12-24
版本: V20.5
"""

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"           # 正常运行
    OPEN = "open"               # 熔断开启（拒绝请求）
    HALF_OPEN = "half_open"     # 半开（试探性恢复）


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 20        # 失败阈值（连续失败次数）
    success_threshold: int = 5         # 成功阈值（半开状态下连续成功次数）
    timeout_seconds: int = 300         # 熔断超时（秒）
    error_codes: Set[int] = field(default_factory=lambda: {403, 429, 500, 502, 503})
    monitored_exceptions: tuple = field(default_factory=lambda: (Exception,))


@dataclass
class ProgressSnapshot:
    """进度快照"""
    total_matches: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    successful_ids: List[int] = field(default_factory=list)
    failed_ids: List[int] = field(default_factory=list)
    skipped_ids: List[int] = field(default_factory=list)
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())
    circuit_breaker_trips: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProgressSnapshot':
        return cls(**data)


class CircuitBreaker:
    """
    熔断器 - 防止级联故障

    功能:
    - 连续失败达到阈值时自动熔断
    - 支持半开状态试探性恢复
    - 记录熔断历史
    """

    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._trip_count = 0
        self._lock = threading.Lock()

        logger.info(
            f"熔断器初始化: threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout_seconds}s, "
            f"monitored_errors={self.config.error_codes}"
        )

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self._state

    @property
    def failure_count(self) -> int:
        """获取当前失败计数"""
        return self._failure_count

    @property
    def trip_count(self) -> int:
        """获取熔断次数"""
        return self._trip_count

    def record_success(self):
        """记录成功"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.info(f"熔断器半开状态: 成功计数 {self._success_count}/{self.config.success_threshold}")

                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            else:
                # CLOSED 状态下重置失败计数
                self._failure_count = 0

    def record_failure(self, error_code: Optional[int] = None, exception: Optional[Exception] = None):
        """
        记录失败

        Args:
            error_code: HTTP 错误码
            exception: 异常对象
        """
        with self._lock:
            # 检查是否为监控的错误
            if error_code and error_code not in self.config.error_codes:
                logger.debug(f"错误码 {error_code} 不在熔断监控范围内")
                return

            if exception and not isinstance(exception, self.config.monitored_exceptions):
                logger.debug(f"异常类型 {type(exception)} 不在熔断监控范围内")
                return

            self._failure_count += 1
            self._last_failure_time = time.time()

            logger.warning(
                f"熔断器: 失败计数 {self._failure_count}/{self.config.failure_threshold}, "
                f"error_code={error_code}, state={self._state.value}"
            )

            # 检查是否需要熔断
            if self._state == CircuitState.CLOSED and self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()
            elif self._state == CircuitState.HALF_OPEN:
                # 半开状态下失败，重新熔断
                self._transition_to_open()

    def _transition_to_open(self):
        """转换到开启状态"""
        self._state = CircuitState.OPEN
        self._trip_count += 1
        logger.error(
            f"🔴 熔断器已触发！连续失败 {self._failure_count} 次。"
            f"系统将在 {self.config.timeout_seconds} 秒后尝试恢复。"
        )

    def _transition_to_closed(self):
        """转换到关闭状态"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("🟢 熔断器已恢复，系统正常运行")

    def _transition_to_half_open(self):
        """转换到半开状态"""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        logger.info("🟡 熔断器进入半开状态，试探性恢复")

    def can_execute(self) -> bool:
        """
        检查是否可以执行请求

        Returns:
            True 如果可以执行，False 如果熔断
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # 检查是否超时，可以尝试半开
                if self._last_failure_time and (time.time() - self._last_failure_time) >= self.config.timeout_seconds:
                    self._transition_to_half_open()
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                return True

            return False

    def is_open(self) -> bool:
        """
        检查熔断器是否已开启（熔断状态）

        Returns:
            True 如果熔断器开启（拒绝请求），False 如果正常运行
        """
        with self._lock:
            # 如果是 OPEN 状态且未超时，则认为是熔断开启
            if self._state == CircuitState.OPEN:
                # 检查是否超时
                if self._last_failure_time and (time.time() - self._last_failure_time) >= self.config.timeout_seconds:
                    return False  # 已超时，可以恢复
                return True  # 仍在熔断中
            return False  # CLOSED 或 HALF_OPEN 状态

    def reset(self):
        """重置熔断器"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info("熔断器已手动重置")


class CheckpointTracker:
    """
    断点续传追踪器

    功能:
    - 持久化进度到 JSON 文件
    - 支持从中断点恢复
    - 记录成功/失败/跳过的 Match ID
    """

    def __init__(self, checkpoint_file: str = "data/backfill_progress.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot = self._load_snapshot()
        self._lock = threading.Lock()
        self._db_conn_getter = None  # 延迟初始化数据库连接getter

        logger.info(f"断点追踪器初始化: {self.checkpoint_file}")
        logger.info(f"已加载快照: processed={self._snapshot.processed}/{self._snapshot.total_matches}")

    def set_db_connection_getter(self, conn_getter):
        """
        设置数据库连接获取函数
        Args:
            conn_getter: 返回数据库连接的函数
        """
        self._db_conn_getter = conn_getter

    def sync_with_database(self):
        """
        V20.5.3 HOTFIX: 与数据库同步，修复伪失败Bug

        逻辑:
        1. 查询数据库中实际存在的记录
        2. 将存在于数据库但标记为failed的记录移到successful
        """
        if not self._db_conn_getter:
            logger.warning("数据库连接getter未设置，跳过数据库同步")
            return

        try:
            conn = self._db_conn_getter()
            cur = conn.cursor()

            # 查询数据库中所有记录
            cur.execute("""
                SELECT match_id FROM match_features_training
            """)
            db_match_ids = set(row[0] for row in cur.fetchall())
            cur.close()

            with self._lock:
                # 修复伪失败: 将存在于数据库但标记为failed的记录移到successful
                false_failures = []
                for match_id in self._snapshot.failed_ids[:]:
                    if match_id in db_match_ids:
                        self._snapshot.failed_ids.remove(match_id)
                        if match_id not in self._snapshot.successful_ids:
                            self._snapshot.successful_ids.append(match_id)
                        false_failures.append(match_id)

                if false_failures:
                    # 修正计数器
                    self._snapshot.successful += len(false_failures)
                    self._snapshot.failed -= len(false_failures)
                    self._save_snapshot()
                    logger.info(f"✅ 修复伪失败: {len(false_failures)} 场比赛已从failed移到successful")

        except Exception as e:
            logger.warning(f"数据库同步失败: {e}")

    def _load_snapshot(self) -> ProgressSnapshot:
        """加载快照"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                snapshot = ProgressSnapshot.from_dict(data)
                logger.info(f"从快照恢复: {snapshot.processed} 场已处理")
                return snapshot
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"快照文件损坏，创建新快照: {e}")
                return ProgressSnapshot()
        return ProgressSnapshot()

    def _save_snapshot(self):
        """保存快照"""
        self._snapshot.last_update = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self._snapshot.to_dict(), f, indent=2, ensure_ascii=False)

    def set_total(self, total: int):
        """设置总场次"""
        with self._lock:
            self._snapshot.total_matches = total
            self._save_snapshot()

    def record_success(self, match_id: int):
        """记录成功"""
        with self._lock:
            if match_id not in self._snapshot.successful_ids:
                self._snapshot.successful_ids.append(match_id)
            self._snapshot.processed += 1
            self._snapshot.successful += 1
            self._save_snapshot()

    def record_failure(self, match_id: int):
        """记录失败"""
        with self._lock:
            if match_id not in self._snapshot.failed_ids:
                self._snapshot.failed_ids.append(match_id)
            self._snapshot.processed += 1
            self._snapshot.failed += 1
            self._save_snapshot()

    def record_skip(self, match_id: int):
        """记录跳过"""
        with self._lock:
            if match_id not in self._snapshot.skipped_ids:
                self._snapshot.skipped_ids.append(match_id)
            self._snapshot.skipped += 1
            self._save_snapshot()

    def is_processed(self, match_id: int) -> bool:
        """检查是否已处理"""
        return match_id in self._snapshot.successful_ids

    def get_failed_ids(self) -> List[int]:
        """获取失败的 Match ID 列表"""
        return self._snapshot.failed_ids.copy()

    def get_successful_ids(self) -> List[int]:
        """获取成功的 Match ID 列表"""
        return self._snapshot.successful_ids.copy()

    def get_progress(self) -> Dict[str, Any]:
        """获取进度摘要"""
        with self._lock:
            return {
                'total_matches': self._snapshot.total_matches,
                'processed': self._snapshot.processed,
                'successful': self._snapshot.successful,
                'failed': self._snapshot.failed,
                'skipped': self._snapshot.skipped,
                'remaining': self._snapshot.total_matches - self._snapshot.processed,
                'success_rate': self._snapshot.successful / self._snapshot.processed if self._snapshot.processed > 0 else 0,
                'last_update': self._snapshot.last_update,
            }

    def create_backup(self):
        """创建备份"""
        backup_file = self.checkpoint_file.with_suffix(f'.bak.{int(time.time())}')
        import shutil
        shutil.copy2(self.checkpoint_file, backup_file)
        logger.info(f"创建快照备份: {backup_file}")

    def reset(self):
        """重置快照"""
        with self._lock:
            self._snapshot = ProgressSnapshot()
            self._save_snapshot()
            logger.info("断点追踪器已重置")


@dataclass
class ProcessingResult:
    """处理结果"""
    match_id: int
    success: bool
    error: Optional[str] = None
    duration: float = 0.0
    error_code: Optional[int] = None


class FaultTolerantProcessor:
    """
    容错处理器

    结合熔断器和断点追踪，提供完整的容错处理能力
    """

    def __init__(
        self,
        circuit_breaker: CircuitBreaker = None,
        checkpoint_tracker: CheckpointTracker = None,
        max_retries: int = 2
    ):
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.checkpoint_tracker = checkpoint_tracker or CheckpointTracker()
        self.max_retries = max_retries
        logger.info("容错处理器初始化完成")

    def process_with_retry(
        self,
        match_id: int,
        processor_func: Callable[[int], ProcessingResult],
        skip_if_processed: bool = True
    ) -> ProcessingResult:
        """
        带重试和容错的处理函数

        Args:
            match_id: 比赛 ID
            processor_func: 处理函数，接受 match_id，返回 ProcessingResult
            skip_if_processed: 如果已处理是否跳过

        Returns:
            ProcessingResult
        """
        # 检查是否已处理
        if skip_if_processed and self.checkpoint_tracker.is_processed(match_id):
            logger.debug(f"Match {match_id} 已处理，跳过")
            self.checkpoint_tracker.record_skip(match_id)
            return ProcessingResult(match_id=match_id, success=True, error="Already processed")

        # 检查熔断器
        if not self.circuit_breaker.can_execute():
            logger.error(f"熔断器已开启，拒绝处理 Match {match_id}")
            return ProcessingResult(
                match_id=match_id,
                success=False,
                error="Circuit breaker is OPEN",
                error_code=503
            )

        # 执行处理（带重试）
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                result = processor_func(match_id)
                result.duration = time.time() - start_time

                if result.success:
                    self.circuit_breaker.record_success()
                    self.checkpoint_tracker.record_success(match_id)
                    logger.info(f"✓ Match {match_id} 处理成功 (耗时: {result.duration:.2f}s)")
                    return result
                else:
                    last_error = result.error
                    if result.error_code:
                        self.circuit_breaker.record_failure(result.error_code)
                    else:
                        self.circuit_breaker.record_failure()

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Match {match_id} 处理异常 (attempt {attempt + 1}/{self.max_retries + 1}): {e}")

                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    # 最后一次尝试失败
                    self.circuit_breaker.record_failure(exception=e)

        # 所有尝试都失败
        self.checkpoint_tracker.record_failure(match_id)
        logger.error(f"✗ Match {match_id} 处理失败: {last_error}")

        return ProcessingResult(
            match_id=match_id,
            success=False,
            error=last_error
        )

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'circuit_breaker': {
                'state': self.circuit_breaker.state.value,
                'failure_count': self.circuit_breaker.failure_count,
                'trip_count': self.circuit_breaker.trip_count,
            },
            'progress': self.checkpoint_tracker.get_progress(),
        }
