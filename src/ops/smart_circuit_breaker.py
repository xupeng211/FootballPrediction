#!/usr/bin/env python3
"""
V20.0 智能断点续传与坏账核销器
==============================

核心功能：
- 跟踪每个 match ID 的失败次数
- 自动标记坏账（连续3次失败）并移出队列
- 断点续传支持（记录已处理和待处理队列）
- 持久化状态，支持进程重启后恢复

作者: Data Architecture Team
日期: 2025-12-24
版本: V20.0
"""

import json
import logging
import time
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MatchStatus:
    """比赛处理状态"""
    match_id: int
    attempts: int = 0           # 尝试次数
    consecutive_failures: int = 0  # 连续失败次数
    last_attempt: Optional[str] = None
    last_error: Optional[str] = None
    status: str = "pending"      # pending, success, failed, bad_debt

    def record_attempt(self, success: bool, error: str = None):
        """记录一次尝试"""
        self.attempts += 1
        self.last_attempt = datetime.now().isoformat()

        if success:
            self.consecutive_failures = 0
            self.status = "success"
            self.last_error = None
        else:
            self.consecutive_failures += 1
            self.last_error = error

            # 连续3次失败标记为坏账
            if self.consecutive_failures >= 3:
                self.status = "bad_debt"

    def to_dict(self) -> Dict:
        return {
            'match_id': self.match_id,
            'attempts': self.attempts,
            'consecutive_failures': self.consecutive_failures,
            'last_attempt': self.last_attempt,
            'last_error': self.last_error,
            'status': self.status
        }


@dataclass
class ProcessingState:
    """处理状态快照"""
    total_queued: int = 0
    processed: int = 0
    successful: int = 0
    bad_debt: int = 0
    pending: int = 0

    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return self.successful / self.processed


class SmartCircuitBreaker:
    """
    V20.0 智能熔断器

    核心改进：
    1. 按比赛 ID 级别跟踪，而非全局计数
    2. 自动标记坏账并移出队列
    3. 断点续传支持
    4. 持久化状态
    """

    # 配置常量
    MAX_CONSECUTIVE_FAILURES = 3      # 连续失败次数后标记坏账
    BAD_DEBT_COOLDOWN = 3600         # 坏账冷却时间（秒）
    STATE_FILE = "data/processing_state.json"

    def __init__(self):
        self.match_status: Dict[int, MatchStatus] = {}
        self.bad_debt_registry: Set[int] = set()
        self.success_registry: Set[int] = set()

        self.state_file = Path(self.STATE_FILE)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载持久化状态
        self._load_state()

        logger.info("=== V20.0 智能熔断器初始化 ===")
        logger.info(f"坏账数量: {len(self.bad_debt_registry)}")
        logger.info(f"成功数量: {len(self.success_registry)}")

    def should_process(self, match_id: int) -> Tuple[bool, str]:
        """
        判断是否应该处理该比赛

        Args:
            match_id: 比赛 ID

        Returns:
            (是否应该处理, 原因说明)
        """
        # 检查是否已成功
        if match_id in self.success_registry:
            return False, "已成功采集"

        # 检查是否是坏账
        if match_id in self.bad_debt_registry:
            status = self.match_status.get(match_id)
            if status:
                # 检查是否在冷却期外（允许重试）
                if self._is_cooldown_over(status):
                    return True, "坏账冷却期结束，允许重试"
                else:
                    return False, f"坏账冷却中 (连续失败 {status.consecutive_failures} 次)"
            return False, "已标记为坏账"

        return True, "待处理"

    def record_success(self, match_id: int):
        """记录成功"""
        self.match_status.setdefault(match_id, MatchStatus(match_id)).record_attempt(True)
        self.success_registry.add(match_id)
        self.bad_debt_registry.discard(match_id)

        # 定期持久化
        if len(self.success_registry) % 50 == 0:
            self._save_state()

    def record_failure(self, match_id: int, error: str):
        """记录失败"""
        status = self.match_status.setdefault(match_id, MatchStatus(match_id))
        status.record_attempt(False, error)

        # 检查是否标记为坏账
        if status.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            self.bad_debt_registry.add(match_id)
            logger.warning(f"⚠️  Match {match_id} 标记为坏账 (连续失败 {status.consecutive_failures} 次): {error}")

        # 定期持久化
        if len(self.bad_debt_registry) % 10 == 0:
            self._save_state()

    def get_processing_state(self) -> ProcessingState:
        """获取当前处理状态"""
        status = ProcessingState()

        for match_id, match_status in self.match_status.items():
            status.total_queued += 1

            if match_status.status == "success":
                status.processed += 1
                status.successful += 1
            elif match_status.status == "bad_debt":
                status.bad_debt += 1
                status.processed += 1
            elif match_status.status == "pending":
                status.pending += 1

        return status

    def get_bad_debt_list(self) -> List[Dict]:
        """获取坏账列表"""
        return [
            {
                'match_id': match_id,
                'attempts': self.match_status[match_id].attempts,
                'last_error': self.match_status[match_id].last_error
            }
            for match_id in sorted(self.bad_debt_registry)
        ]

    def purge_old_bad_debt(self, max_age_hours: int = 24):
        """
        清理旧的坏账记录

        Args:
            max_age_hours: 最大保留时间（小时）
        """
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_remove = []

        for match_id in self.bad_debt_registry:
            status = self.match_status.get(match_id)
            if status and status.last_attempt:
                try:
                    attempt_time = datetime.fromisoformat(status.last_attempt).timestamp()
                    if attempt_time < cutoff:
                        to_remove.append(match_id)
                except:
                    pass

        for match_id in to_remove:
            self.bad_debt_registry.discard(match_id)
            del self.match_status[match_id]

        if to_remove:
            logger.info(f"🧹 清理 {len(to_remove)} 个过期坏账记录")
            self._save_state()

    def reset_match(self, match_id: int):
        """重置特定比赛的状态（允许重新处理）"""
        if match_id in self.match_status:
            del self.match_status[match_id]

        self.bad_debt_registry.discard(match_id)
        self.success_registry.discard(match_id)

        logger.info(f"🔄 重置 Match {match_id} 状态")

    def print_summary(self):
        """打印摘要"""
        state = self.get_processing_state()

        logger.info("\n=== 智能熔断器状态 ===")
        logger.info(f"待处理: {state.pending}")
        logger.info(f"已处理: {state.processed}")
        logger.info(f"成功: {state.successful}")
        logger.info(f"坏账: {state.bad_debt}")
        logger.info(f"成功率: {state.success_rate:.1%}")

    def _is_cooldown_over(self, status: MatchStatus) -> bool:
        """检查冷却期是否结束"""
        if not status.last_attempt:
            return True

        try:
            attempt_time = datetime.fromisoformat(status.last_attempt)
            elapsed = (datetime.now() - attempt_time).total_seconds()
            return elapsed >= self.BAD_DEBT_COOLDOWN
        except:
            return True

    def _save_state(self):
        """持久化状态"""
        state_data = {
            'last_updated': datetime.now().isoformat(),
            'bad_debt_count': len(self.bad_debt_registry),
            'success_count': len(self.success_registry),
            'match_status': {
                str(match_id): status.to_dict()
                for match_id, status in self.match_status.items()
            },
            'bad_debt_registry': list(self.bad_debt_registry),
            'success_registry': list(self.success_registry)
        }

        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.error(f"保存状态失败: {e}")

    def _load_state(self):
        """加载持久化状态"""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            # 恢复 match_status
            for match_id_str, status_dict in state_data.get('match_status', {}).items():
                match_id = int(match_id_str)
                status = MatchStatus(
                    match_id=match_id,
                    attempts=status_dict['attempts'],
                    consecutive_failures=status_dict['consecutive_failures'],
                    last_attempt=status_dict['last_attempt'],
                    last_error=status_dict['last_error'],
                    status=status_dict['status']
                )
                self.match_status[match_id] = status

            # 恢复注册表
            self.bad_debt_registry = set(int(x) for x in state_data.get('bad_debt_registry', []))
            self.success_registry = set(int(x) for x in state_data.get('success_registry', []))

            logger.info(f"✅ 加载持久化状态: {len(self.match_status)} 条记录")

        except Exception as e:
            logger.warning(f"加载状态失败: {e}")


# 单例实例
_circuit_breaker_instance: Optional[SmartCircuitBreaker] = None


def get_circuit_breaker() -> SmartCircuitBreaker:
    """获取智能熔断器单例"""
    global _circuit_breaker_instance
    if _circuit_breaker_instance is None:
        _circuit_breaker_instance = SmartCircuitBreaker()
    return _circuit_breaker_instance


# ============================================
# 核心代码片段（输出要求）
# ============================================

def smart_recheck_logic(match_id: int) -> Tuple[bool, str]:
    """
    V20.0 智能重试逻辑

    替代原有的全局熔断机制：

    传统方式：
        if consecutive_failures >= 5:
            time.sleep(1800)  # 全局休眠30分钟

    V20.0 方式：
        if match_id in bad_debt_registry:
            skip_this_match()
            continue_with_next()
    """
    cb = get_circuit_breaker()
    should_process, reason = cb.should_process(match_id)

    if not should_process:
        if "坏账" in reason:
            # 自动跳过，不阻塞队列
            return False, f"SKIP: {reason}"
        else:
            # 已成功，跳过
            return False, f"DONE: {reason}"

    return True, "PROCESS"


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    cb = get_circuit_breaker()

    # 模拟处理
    test_match_ids = [4813551, 4813552, 4813553, 4813554, 4813555]

    for match_id in test_match_ids:
        should_process, reason = smart_recheck_logic(match_id)
        print(f"Match {match_id}: {should_process} - {reason}")

        if should_process:
            # 模拟失败
            cb.record_failure(match_id, "响应过小")

    cb.print_summary()
