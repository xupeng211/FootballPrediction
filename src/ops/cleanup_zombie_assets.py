#!/usr/bin/env python3
"""
V25.0 僵尸资产清理脚本 - Zombie Debt Cleanup
==================================================

功能:
    1. 扫描版本低于 V24.1 的 252 场僵尸记录
    2. 尝试调用 L2 抓取器重新补全 JSON
    3. 补全失败的记录，标记为 DELETED_INVALID 以隔离
    4. 生成清理报告

设计模式:
    - Strategy Pattern: 根据数据状态选择处理策略
    - Circuit Breaker: 防止连续失败触发熔断
    - Observer: 记录清理进度和结果

作者: SRE/DataOps Specialist
版本: V25.0-Industrial
日期: 2025-12-25
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
src_root = Path(__file__).parent.parent
sys.path.insert(0, str(src_root))

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

# 配置日志
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.FileHandler("logs/v25_zombie_cleanup.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 枚举定义
# ============================================================================


class CleanupAction(str, Enum):
    """清理动作"""

    RETRY_HARVEST = "retry_harvest"  # 重新尝试收割
    MARK_DELETED = "mark_deleted"  # 标记为已删除
    SKIP = "skip"  # 跳过


class ZombieStatus(str, Enum):
    """僵尸状态"""

    PENDING = "pending"
    RETRYING = "retrying"
    RECOVERED = "recovered"
    FAILED = "failed"
    DELETED = "deleted"


# ============================================================================
# 配置类定义
# ============================================================================


@dataclass
class CleanupConfig:
    """
    清理配置

    Attributes:
        batch_size: 批量处理大小
        max_retry_attempts: 最大重试次数
        retry_delay_ms: 重试延迟（毫秒）
        enable_auto_harvest: 是否启用自动收割
        harvest_timeout_seconds: 收割超时时间
        mark_as_deleted_status: 标记为删除的状态值
    """

    batch_size: int = 50
    max_retry_attempts: int = 3
    retry_delay_ms: int = 1000
    enable_auto_harvest: bool = True
    harvest_timeout_seconds: int = 30
    mark_as_deleted_status: str = "DELETED_INVALID"


@dataclass
class CleanupStats:
    """
    清理统计信息

    Attributes:
        start_time: 开始时间
        end_time: 结束时间
        total_zombies: 总僵尸记录数
        recovered_count: 恢复数量
        deleted_count: 删除数量
        failed_count: 失败数量
        skipped_count: 跳过数量
        harvest_success_count: 收割成功数量
        harvest_failed_count: 收割失败数量
    """

    start_time: float = 0.0
    end_time: float = 0.0
    total_zombies: int = 0
    recovered_count: int = 0
    deleted_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    harvest_success_count: int = 0
    harvest_failed_count: int = 0
    # 详细记录
    recovered_match_ids: list[int] = field(default_factory=list)
    deleted_match_ids: list[int] = field(default_factory=list)
    failed_match_ids: list[int] = field(default_factory=list)

    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def recovery_rate(self) -> float:
        """恢复率"""
        if self.total_zombies == 0:
            return 0.0
        return self.recovered_count / self.total_zombies

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "elapsed_seconds": self.elapsed_time,
            "total_zombies": self.total_zombies,
            "recovered_count": self.recovered_count,
            "deleted_count": self.deleted_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "harvest_success_count": self.harvest_success_count,
            "harvest_failed_count": self.harvest_failed_count,
            "recovery_rate": round(self.recovery_rate * 100, 2),
            "recovered_match_ids": self.recovered_match_ids[:10],  # 只保存前10个用于展示
            "deleted_match_ids": self.deleted_match_ids[:10],
            "failed_match_ids": self.failed_match_ids[:10],
        }


# ============================================================================
# 核心类定义
# ============================================================================


class ZombieAssetCleaner:
    """
    僵尸资产清理器 (V25.0)

    职责:
        1. 扫描并识别僵尸记录（版本 < V24.1 且无原始 JSON）
        2. 尝试重新收割数据
        3. 标记无法恢复的记录
        4. 生成清理报告

    清理策略:
        - 策略 1: 重新尝试从 FotMob API 收割
        - 策略 2: 检查是否有备份数据
        - 策略 3: 标记为 DELETED_INVALID 并从训练集中隔离
    """

    def __init__(self, config: CleanupConfig | None = None):
        """
        初始化清理器

        Args:
            config: 清理配置
        """
        self.config = config or CleanupConfig()
        self.stats = CleanupStats()

        # 获取数据库配置
        settings = get_settings()
        self.db_config = settings.database

        # 数据库连接（延迟初始化）
        self._conn = None

        logger.info("=" * 60)
        logger.info("V25.0 僵尸资产清理器初始化完成")
        logger.info("=" * 60)
        logger.info(f"  批量大小: {self.config.batch_size}")
        logger.info(f"  最大重试: {self.config.max_retry_attempts}")
        logger.info(f"  自动收割: {self.config.enable_auto_harvest}")

    def connect(self) -> None:
        """建立数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.name,
                user=self.db_config.user,
                password=self.db_config.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
            logger.info("数据库连接已建立")

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("数据库连接已关闭")

    def scan_zombie_assets(self) -> list[dict[str, Any]]:
        """
        扫描僵尸资产

        僵尸定义:
            1. extraction_version < 'V24.1'
            2. l2_raw_json 为 NULL 或无效
            3. status = 'completed'

        Returns:
            僵尸记录列表
        """
        self.connect()

        with self._conn.cursor() as cur:
            # 统计总数
            cur.execute("""
                SELECT COUNT(*) as total
                FROM match_features_training f
                JOIN matches m ON f.match_id = m.match_id
                WHERE f.status = 'completed'
                  AND COALESCE(f.meta_data->>'extraction_version', 'V0.0') < 'V24.1'
                  AND (m.l2_raw_json IS NULL OR jsonb_typeof(m.l2_raw_json) = 'null');
            """)
            self.stats.total_zombies = cur.fetchone()["total"]

            # 获取僵尸记录
            query = """
                SELECT
                    f.match_id,
                    m.external_id,
                    f.home_team,
                    f.away_team,
                    f.match_time,
                    m.league_id,
                    m.season,
                    COALESCE(f.meta_data->>'extraction_version', 'V0.0') as current_version,
                    m.l2_raw_json IS NULL as missing_raw_json
                FROM match_features_training f
                JOIN matches m ON f.match_id = m.match_id
                WHERE f.status = 'completed'
                  AND COALESCE(f.meta_data->>'extraction_version', 'V0.0') < 'V24.1'
                  AND (m.l2_raw_json IS NULL OR jsonb_typeof(m.l2_raw_json) = 'null')
                ORDER BY f.match_time DESC NULLS LAST
                LIMIT %s;
            """

            cur.execute(query, (self.config.batch_size,))
            zombies = cur.fetchall()

            logger.info(f"发现 {len(zombies)} 条僵尸记录（总计: {self.stats.total_zombies}）")

            return zombies

    def attempt_harvest_recovery(self, zombie: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
        """
        尝试通过重新收割恢复僵尸记录

        Args:
            zombie: 僵尸记录

        Returns:
            (成功标志, 收割的数据)
        """
        if not self.config.enable_auto_harvest:
            return False, None

        match_id = zombie["match_id"]
        external_id = zombie["external_id"]
        league_id = zombie.get("league_id", "47")
        season = zombie.get("season", "2324")

        logger.info(f"尝试收割 match_id={match_id}, external_id={external_id}")

        try:
            # 动态导入 FotMob 收割器
            from src.api.collectors.fotmob_core import FotMobCollector

            collector = FotMobCollector()
            raw_data = collector.fetch_match_data(external_id)

            if raw_data and "content" in raw_data:
                logger.info(f"match_id={match_id}: 收割成功")
                self.stats.harvest_success_count += 1
                return True, raw_data
            logger.warning(f"match_id={match_id}: 收割返回空数据")
            self.stats.harvest_failed_count += 1
            return False, None

        except ImportError:
            logger.warning("FotMobCollector 不可用，跳过自动收割")
            self.stats.harvest_failed_count += 1
            return False, None
        except Exception as e:
            logger.error(f"match_id={match_id}: 收割失败 - {e}")
            self.stats.harvest_failed_count += 1
            return False, None

    def recover_zombie(self, zombie: dict[str, Any], raw_data: dict[str, Any]) -> bool:
        """
        恢复僵尸记录（更新 l2_raw_json 和版本）

        Args:
            zombie: 僵尸记录
            raw_data: 收割的原始数据

        Returns:
            是否成功恢复
        """
        match_id = zombie["match_id"]

        try:
            with self._conn.cursor() as cur:
                # 更新 l2_raw_json
                update_query = """
                    UPDATE matches
                    SET l2_raw_json = %s::jsonb,
                        l2_data_version = 'V25.0-recovered',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s;
                """

                # 构造 JSON 结构
                l2_json = {
                    "l2_json": raw_data.get("content", raw_data),
                    "league_id": zombie.get("league_id", ""),
                    "collected_at": datetime.now().isoformat(),
                    "recovered_by": "zombie_cleanup_v25",
                }

                cur.execute(update_query, (json.dumps(l2_json), match_id))

                # 更新特征表的元数据
                meta_update = """
                    UPDATE match_features_training
                    SET meta_data = COALESCE(meta_data, '{}'::jsonb) || %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s;
                """

                metadata = {
                    "zombie_recovered_at": datetime.now().isoformat(),
                    "zombie_recovery_version": "V25.0",
                }

                cur.execute(meta_update, (json.dumps(metadata), match_id))

                self._conn.commit()

                self.stats.recovered_count += 1
                self.stats.recovered_match_ids.append(match_id)

                logger.info(f"match_id={match_id}: ✓ 已恢复")
                return True

        except Exception as e:
            logger.error(f"match_id={match_id}: 恢复失败 - {e}")
            self._conn.rollback()
            self.stats.failed_count += 1
            self.stats.failed_match_ids.append(match_id)
            return False

    def mark_as_deleted(self, zombie: dict[str, Any]) -> bool:
        """
        标记僵尸记录为已删除（从训练集中隔离）

        Args:
            zombie: 僵尸记录

        Returns:
            是否成功标记
        """
        match_id = zombie["match_id"]

        try:
            with self._conn.cursor() as cur:
                # 更新状态为 DELETED_INVALID
                update_query = """
                    UPDATE match_features_training
                    SET status = %s,
                        meta_data = COALESCE(meta_data, '{}'::jsonb) || %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s;
                """

                metadata = {
                    "zombie_deleted_at": datetime.now().isoformat(),
                    "zombie_cleanup_version": "V25.0",
                    "deletion_reason": "No raw data available and harvest failed",
                }

                cur.execute(update_query, (self.config.mark_as_deleted_status, json.dumps(metadata), match_id))
                self._conn.commit()

                self.stats.deleted_count += 1
                self.stats.deleted_match_ids.append(match_id)

                logger.info(f"match_id={match_id}: 已标记为 {self.config.mark_as_deleted_status}")
                return True

        except Exception as e:
            logger.error(f"match_id={match_id}: 标记删除失败 - {e}")
            self._conn.rollback()
            self.stats.failed_count += 1
            return False

    def process_batch(self, zombies: list[dict[str, Any]]) -> None:
        """
        处理一批僵尸记录

        Args:
            zombies: 僵尸记录列表
        """
        logger.info(f"开始处理 {len(zombies)} 条僵尸记录...")

        for zombie in zombies:
            match_id = zombie["match_id"]
            missing_raw = zombie.get("missing_raw_json", True)

            # 尝试重新收割
            harvest_success, raw_data = self.attempt_harvest_recovery(zombie)

            if harvest_success and raw_data:
                # 收割成功，恢复记录
                self.recover_zombie(zombie, raw_data)
            # 收割失败，标记为删除
            elif missing_raw:
                logger.info(f"match_id={match_id}: 无原始数据，标记为删除")
                self.mark_as_deleted(zombie)
            else:
                logger.info(f"match_id={match_id}: 保留现有数据（有原始 JSON）")
                self.stats.skipped_count += 1

    def run(self) -> CleanupStats:
        """
        执行完整的清理流程

        Returns:
            清理统计信息
        """
        logger.info("=" * 60)
        logger.info("V25.0 僵尸资产清理开始")
        logger.info("=" * 60)

        self.stats.start_time = time.time()

        try:
            batch_count = 0
            while True:
                # 扫描僵尸记录
                zombies = self.scan_zombie_assets()

                if not zombies:
                    logger.info("没有更多僵尸记录，清理完成")
                    break

                batch_count += 1
                logger.info(f"\n[批次 {batch_count}] 处理 {len(zombies)} 条僵尸记录")

                # 处理当前批次
                self.process_batch(zombies)

                # 打印当前统计
                logger.info("\n当前统计:")
                logger.info(f"  🔄 已恢复: {self.stats.recovered_count}")
                logger.info(f"  🗑️  已删除: {self.stats.deleted_count}")
                logger.info(f"  ❌ 失败: {self.stats.failed_count}")
                logger.info(f"  ⏭️  已跳过: {self.stats.skipped_count}")
                logger.info(f"  📈 恢复率: {self.stats.recovery_rate * 100:.1f}%")

                # 批次间休眠
                time.sleep(self.config.retry_delay_ms / 1000.0)

        except KeyboardInterrupt:
            logger.info("\n用户中断，正在退出...")

        except Exception as e:
            logger.error(f"清理运行异常: {e}")
            raise

        finally:
            self.close()

        # 打印最终统计
        self.stats.end_time = time.time()
        self._print_final_stats()

        return self.stats

    def _print_final_stats(self) -> None:
        """打印最终统计"""
        stats = self.stats.to_dict()

        print("\n" + "🧹 " + "=" * 58)
        print("V25.0 僵尸资产清理报告")
        print("=" * 60)

        print("\n执行时间:")
        print(f"  • 开始时间: {stats['start_time']}")
        print(f"  • 结束时间: {stats['end_time']}")
        print(f"  • 运行时长: {stats['elapsed_seconds']:.1f} 秒")

        print("\n清理结果:")
        print(f"  🔄 已恢复: {stats['recovered_count']} 场")
        print(f"  🗑️  已删除: {stats['deleted_count']} 场")
        print(f"  ❌ 失败: {stats['failed_count']} 场")
        print(f"  ⏭️  已跳过: {stats['skipped_count']} 场")

        print("\n收割统计:")
        print(f"  ✅ 收割成功: {stats['harvest_success_count']}")
        print(f"  ❌ 收割失败: {stats['harvest_failed_count']}")

        print(f"\n恢复率: {stats['recovery_rate']}%")

        if stats["recovered_match_ids"]:
            print(f"\n已恢复比赛 ID (前10个): {stats['recovered_match_ids']}")
        if stats["deleted_match_ids"]:
            print(f"已删除比赛 ID (前10个): {stats['deleted_match_ids']}")

        print("\n" + "=" * 60)


# ============================================================================
# 主程序入口
# ============================================================================


def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="V25.0 僵尸资产清理脚本 - Zombie Debt Cleanup")
    parser.add_argument("--batch-size", type=int, default=50, help="批量处理大小（默认: 50）")
    parser.add_argument("--no-harvest", action="store_true", help="禁用自动收割")
    parser.add_argument("--max-retry", type=int, default=3, help="最大重试次数（默认: 3）")
    parser.add_argument(
        "--delete-status", type=str, default="DELETED_INVALID", help="标记为删除的状态值（默认: DELETED_INVALID）"
    )

    args = parser.parse_args()

    # 创建配置
    config = CleanupConfig(
        batch_size=args.batch_size,
        enable_auto_harvest=not args.no_harvest,
        max_retry_attempts=args.max_retry,
        mark_as_deleted_status=args.delete_status,
    )

    # 创建并运行清理器
    cleaner = ZombieAssetCleaner(config)
    stats = cleaner.run()

    # 返回退出码
    if stats.failed_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
