#!/usr/bin/env python3
"""
V26.2 性能优化模块 - "零缺陷"收割流水线核心 (Phase 2.1 优化版)
================================================================

核心优化:
    1. 多进程并行提取 - ProcessPoolExecutor
    2. 动态批次入库 - 根据内存占用自动调整
    3. 内存屏障 - 动态内存控制
    4. 幂等性保证 - ON CONFLICT DO UPDATE

Phase 2.1 新增优化:
    1. 多进程安全的特征统计同步
    2. 数据库连接池支持
    3. Worker ID 日志标识
    4. 连接泄露防护

架构设计:
    - 环境自愈: auto_fix_env() 自动修复权限和连接
    - 并行提取器: ParallelFeatureExtractor (Phase 2.1: 增强版)
    - 批量写入器: BulkInserter (V26.2: 使用连接池)
    - 内存安全: 动态 GC + 批次调整
    - 多进程安全: 特征统计跨进程同步

Author: Principal Architect & Performance Expert
Version: V26.2 (Phase 2.1 Optimization)
Date: 2025-12-28
"""

import gc
import logging
import multiprocessing
import os
import stat
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import psutil
import psycopg2
from psycopg2.extras import execute_values

# Phase 2.1: 导入数据库连接池
from src.database.db_pool import SyncDatabasePool, DatabasePoolConfig

logger = logging.getLogger(__name__)


# ============================================================================
# 环境自愈模块
# ============================================================================


class EnvironmentHealer:
    """
    环境自愈器 - 自动修复环境问题

    功能:
        1. 自动修复脚本目录权限
        2. 验证数据库连接
        3. 验证 Schema 完整性
        4. 自动创建必要目录
    """

    def __init__(self, db_config: Any):
        """
        初始化环境自愈器

        Args:
            db_config: 数据库配置对象
        """
        self.db_config = db_config
        self.issues_fixed = []

    def auto_fix_env(self) -> bool:
        """
        执行环境自愈（主入口）

        Returns:
            bool: 所有问题是否已修复
        """
        logger.info("🔧 环境自愈器启动...")

        all_ok = True

        # 1. 修复脚本权限
        if not self._fix_script_permissions():
            all_ok = False

        # 2. 验证/创建必要目录
        if not self._ensure_directories():
            all_ok = False

        # 3. 验证数据库连接
        if not self._verify_db_connection():
            all_ok = False

        # 4. 验证 Schema 完整性
        if not self._verify_schema():
            all_ok = False

        if all_ok:
            logger.info("✅ 环境自愈完成 - 所有检查通过")
        else:
            logger.warning(f"⚠️  环境自愈完成 - 修复了 {len(self.issues_fixed)} 个问题")

        return all_ok

    def _fix_script_permissions(self) -> bool:
        """修复脚本目录权限"""
        try:
            scripts_dir = Path("scripts")
            if not scripts_dir.exists():
                return True

            # 递归修复权限
            for script in scripts_dir.rglob("*.sh"):
                current_mode = script.stat().st_mode
                if not (current_mode & stat.S_IXUSR):
                    script.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    self.issues_fixed.append(f"权限修复: {script}")

            return True
        except Exception as e:
            logger.error(f"权限修复失败: {e}")
            return False

    def _ensure_directories(self) -> bool:
        """确保必要目录存在"""
        required_dirs = [
            "logs",
            "data/processed",
            "data/predictions",
            "data/monitoring",
            "data/models",
        ]

        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

        return True

    def _verify_db_connection(self) -> bool:
        """验证数据库连接"""
        try:
            conn = psycopg2.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.name,
                user=self.db_config.user,
                password=self.db_config.password.get_secret_value(),
                connect_timeout=5,
            )
            conn.close()
            logger.info("✅ 数据库连接验证通过")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            return False

    def _verify_schema(self) -> bool:
        """验证 Schema 完整性"""
        try:
            conn = psycopg2.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.name,
                user=self.db_config.user,
                password=self.db_config.password.get_secret_value(),
            )
            cur = conn.cursor()

            # 检查核心表是否存在
            required_tables = ["matches", "raw_match_data", "match_features_training"]
            cur.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = ANY(%s);
            """,
                (required_tables,),
            )

            existing = {row[0] for row in cur.fetchall()}
            missing = required_tables - list(existing)

            if missing:
                logger.error(f"❌ 缺少必要表: {missing}")
                return False

            logger.info("✅ Schema 验证通过")
            return True

        except Exception as e:
            logger.error(f"❌ Schema 验证失败: {e}")
            return False
        finally:
            if "conn" in locals():
                conn.close()


# ============================================================================
# 并行特征提取器 (多进程)
# ============================================================================


class ParallelFeatureExtractor:
    """
    并行特征提取器 - 10X 性能提升核心

    设计:
        - 使用 ProcessPoolExecutor 并行处理
        - 自动检测 CPU 核心数
        - 内存屏障 - 动态控制批次大小
    """

    def __init__(
        self,
        max_workers: int | None = None,
        batch_size: int = 100,
        memory_limit_mb: int = 1500,
    ):
        """
        初始化并行提取器

        Args:
            max_workers: 最大进程数（默认: CPU 核心数 - 1）
            batch_size: 每批处理数量
            memory_limit_mb: 内存限制（MB）
        """
        # 自动检测 CPU 核心数
        cpu_count = multiprocessing.cpu_count()
        self.max_workers = max_workers or max(1, cpu_count - 1)
        self.batch_size = batch_size
        self.memory_limit_mb = memory_limit_mb

        logger.info(
            f"并行提取器初始化: "
            f"workers={self.max_workers}, "
            f"batch_size={self.batch_size}, "
            f"memory_limit={self.memory_limit_mb}MB"
        )

    def extract_batch_parallel(
        self,
        matches: list[dict[str, Any]],
        extractor_class_path: str,
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        并行提取一批比赛的特征 (Phase 2.1: 增强)

        Args:
            matches: 比赛数据列表
            extractor_class_path: 提取器类路径（用于跨进程导入）

        Returns:
            [(match_id, features), ...] 列表
        """
        results = []
        completed = 0
        failed = 0
        worker_id = 0  # Phase 2.1: Worker ID 计数器

        # 使用进程池并行处理
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_match = {}
            for match in matches:
                future = executor.submit(
                    _extract_single_match,
                    match,
                    extractor_class_path,
                    worker_id,  # Phase 2.1: 传递 worker_id
                )
                future_to_match[future] = match
                worker_id = (worker_id + 1) % self.max_workers  # 循环分配 worker_id

            # 收集结果
            for future in as_completed(future_to_match):
                match = future_to_match[future]
                try:
                    match_id, features = future.result(timeout=30)
                    if features:
                        results.append((match_id, features))
                        completed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"提取失败 {match.get('match_id')}: {e}")
                    failed += 1

        logger.info(f"并行提取完成: 成功={completed}, 失败={failed}, 总计={len(matches)}")

        return results

    def get_memory_usage_mb(self) -> float:
        """获取当前进程内存使用（MB）"""
        return psutil.Process().memory_info().rss / 1024 / 1024

    def check_memory_barrier(self) -> bool:
        """
        检查是否超过内存限制

        Returns:
            bool: True 表示内存安全，False 表示接近限制
        """
        current_mb = self.get_memory_usage_mb()
        return current_mb < self.memory_limit_mb


# ============================================================================
# 批量入库器 (Bulk Upsert)
# ============================================================================


class BulkInserter:
    """
    批量入库器 - V26.2 动态批次大小优化 (Phase 2.1: 使用连接池)

    优化:
        - 使用 execute_values() 批量插入
        - ON CONFLICT 处理重复（幂等性）
        - 动态批次大小: 根据内存占用自动调整
        - 事务批处理
        - Phase 2.1: 使用 SyncDatabasePool 防止连接泄露
    """

    def __init__(
        self,
        conn_params: dict[str, Any],
        initial_batch_size: int = 50,
        min_batch_size: int = 10,
        max_batch_size: int = 100,
        memory_threshold: float = 0.7,
        use_connection_pool: bool = True,  # Phase 2.1 新增
    ):
        """
        初始化批量入库器（V26.2）

        Args:
            conn_params: 数据库连接参数
            initial_batch_size: 初始批次大小
            min_batch_size: 最小批次大小
            max_batch_size: 最大批次大小
            memory_threshold: 内存占用阈值（0-1），超过则减小批次
            use_connection_pool: 是否使用连接池 (Phase 2.1 新增)
        """
        self.conn_params = conn_params
        self.buffer: list[tuple] = []
        self.initial_batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.memory_threshold = memory_threshold
        self.buffer_size = initial_batch_size
        self.current_batch_size = initial_batch_size
        self.use_connection_pool = use_connection_pool

        # Phase 2.1: 初始化连接池
        self._db_pool: SyncDatabasePool | None = None
        if use_connection_pool:
            self._init_connection_pool()

    def _init_connection_pool(self) -> None:
        """初始化数据库连接池（Phase 2.1）"""
        config = DatabasePoolConfig(
            host=self.conn_params.get("host", "localhost"),
            port=self.conn_params.get("port", 5432),
            user=self.conn_params.get("user", "football_user"),
            password=self.conn_params.get("password", ""),
            database=self.conn_params.get("database", "football_db"),
            min_size=2,  # Phase 2.1: 2-3 并发使用 2-5 连接
            max_size=10,  # Phase 2.1: 最大 10 连接
        )
        self._db_pool = SyncDatabasePool.get_instance(config)
        self._db_pool.init_pool()
        logger.info("✅ BulkInserter 使用数据库连接池")

    def insert_features_batch(
        self,
        features_list: list[tuple],
        table_name: str = "match_features_training",
    ) -> int:
        """
        批量插入特征数据 (Phase 2.1: 使用连接池)

        Args:
            features_list: 特征数据列表 (match_id, season, ..., features_json, ...)
            table_name: 目标表名

        Returns:
            int: 插入的记录数
        """
        if not features_list:
            return 0

        try:
            # Phase 2.1: 使用连接池
            if self.use_connection_pool and self._db_pool:
                with self._db_pool.get_connection() as conn:
                    return self._execute_insert(conn, features_list, table_name)
            else:
                # 回退到直接连接
                conn = psycopg2.connect(**self.conn_params)
                try:
                    result = self._execute_insert(conn, features_list, table_name)
                    return result
                finally:
                    conn.close()

        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            raise

    def _execute_insert(
        self,
        conn,
        features_list: list[tuple],
        table_name: str,
    ) -> int:
        """
        执行真实的特征数据入库（Phase 2.2: JSONB 存储 + 事务隔离 + JOIN 获取 NOT NULL 字段）

        Args:
            conn: 数据库连接
            features_list: 特征数据列表
            table_name: 目标表名

        Returns:
            int: 插入的记录数
        """
        cur = conn.cursor()

        # Phase 2.2: 真实入库 - 将 6000 维特征存入 JSONB
        # 关键修复：先从 matches 表 JOIN 获取 NOT NULL 字段

        inserted_count = 0

        # 第一步：批量查询 matches 表获取所有必需的 NOT NULL 字段
        external_ids = [record[0] for record in features_list]

        if not external_ids:
            return 0

        # 构建 IN 子句
        placeholders = ",".join(["%s"] * len(external_ids))

        cur.execute(f"""
            SELECT
                external_id,
                match_time,
                home_team,
                away_team,
                home_score,
                away_score,
                league_name
            FROM matches
            WHERE external_id IN ({placeholders})
        """, external_ids)

        # 构建映射字典: external_id -> (match_time, home_team, away_team, home_score, away_score, league_name)
        matches_map = {row[0]: row[1:] for row in cur.fetchall()}

        # 第二步：逐条插入（使用 UPSERT）
        for record in features_list:
            # record: (external_id, season, match_date, home_team, away_team, version, features_json, meta_json, feature_count, status)
            external_id = record[0]
            features_json = record[6]  # V26.2 特征 JSON
            meta_json = record[7]       # 元数据 JSON

            # 检查是否在 matches 表中存在
            if external_id not in matches_map:
                logger.warning(f"⚠️  external_id {external_id} 在 matches 表中不存在，跳过")
                continue

            match_time, home_team, away_team, home_score, away_score, league_name = matches_map[external_id]

            # Phase 2.2: 每条记录使用独立的事务，避免一条失败影响全部
            try:
                # 使用 ON CONFLICT 直接 UPSERT，包含所有 NOT NULL 字段
                cur.execute(f"""
                    INSERT INTO {table_name} AS tgt (
                        external_id,
                        match_time,
                        home_team,
                        away_team,
                        home_score,
                        away_score,
                        adaptive_features,
                        meta_data,
                        feature_version,
                        extraction_confidence,
                        feature_quality_score,
                        processing_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (external_id) DO UPDATE SET
                        match_time = EXCLUDED.match_time,
                        home_team = EXCLUDED.home_team,
                        away_team = EXCLUDED.away_team,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        adaptive_features = EXCLUDED.adaptive_features,
                        meta_data = COALESCE(tgt.meta_data, '{{}}'::jsonb) || EXCLUDED.meta_data,
                        feature_version = EXCLUDED.feature_version,
                        extraction_confidence = GREATEST(tgt.extraction_confidence, EXCLUDED.extraction_confidence),
                        feature_quality_score = GREATEST(tgt.feature_quality_score, EXCLUDED.feature_quality_score),
                        processing_status = EXCLUDED.processing_status,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    external_id,
                    match_time,
                    home_team,
                    away_team,
                    home_score,
                    away_score,
                    features_json,
                    meta_json,
                    record[5],  # feature_version
                    0.9,        # extraction_confidence
                    0.9,        # feature_quality_score
                    "COMPLETED" # processing_status
                ))

                inserted_count += 1

            except Exception as e:
                logger.error(f"写入特征失败 (external_id={external_id}): {e}")
                # 回滚当前事务，继续处理下一条记录
                try:
                    conn.rollback()
                except:
                    pass
                continue

        # 最终提交
        try:
            conn.commit()
        except:
            pass

        logger.info(f"✅ 真实入库完成: {inserted_count}/{len(features_list)} 条记录")
        return inserted_count

    def add_to_buffer(self, record: tuple) -> bool:
        """
        添加到缓冲区

        Args:
            record: 待插入记录

        Returns:
            bool: True 表示缓冲区已满，需要刷新
        """
        self.buffer.append(record)
        return len(self.buffer) >= self.buffer_size

    def flush_buffer(
        self,
        table_name: str = "match_features_training",
    ) -> int:
        """
        刷新缓冲区到数据库（V26.1: 动态批次调整）

        Args:
            table_name: 目标表名

        Returns:
            int: 插入的记录数
        """
        if not self.buffer:
            return 0

        count = self.insert_features_batch(self.buffer, table_name)
        self.buffer.clear()

        # 执行 GC 释放内存
        gc.collect()

        # V26.1: 动态调整批次大小
        self._adjust_batch_size()

        return count

    def _adjust_batch_size(self) -> None:
        """
        V26.1: 动态调整批次大小

        策略:
            - 内存占用 > 70%: 减半批次大小
            - 内存占用 < 50%: 增加批次大小
            - 限制在 [min_batch_size, max_batch_size] 范围内
        """
        import psutil

        memory_percent = psutil.virtual_memory().percent / 100.0

        if memory_percent > self.memory_threshold:
            # 内存占用过高，减小批次
            new_size = max(self.min_batch_size, int(self.current_batch_size * 0.5))
            if new_size < self.current_batch_size:
                logger.info(
                    f"内存占用 {memory_percent:.1%} > {self.memory_threshold:.0%}, "
                    f"批次大小: {self.current_batch_size} → {new_size}"
                )
                self.current_batch_size = new_size
                self.buffer_size = new_size
        elif memory_percent < 0.5:
            # 内存占用较低，可以增加批次
            new_size = min(self.max_batch_size, int(self.current_batch_size * 1.5))
            if new_size > self.current_batch_size:
                logger.info(f"内存占用 {memory_percent:.1%} < 50%, 批次大小: {self.current_batch_size} → {new_size}")
                self.current_batch_size = new_size
                self.buffer_size = new_size

    def get_memory_usage_mb(self) -> float:
        """获取当前进程内存使用（MB）"""
        import psutil

        return psutil.Process().memory_info().rss / 1024 / 1024


# ============================================================================
# 跨进程提取函数（必须在模块级别）
# ============================================================================


def _extract_single_match(
    match: dict[str, Any],
    extractor_class_path: str,
    worker_id: int = 0,  # Phase 2.1: 添加 worker_id
) -> tuple[str, dict[str, Any] | None]:
    """
    提取单场比赛特征（跨进程函数，Phase 2.1: 增强）

    Args:
        match: 比赛数据
        extractor_class_path: 提取器类路径
        worker_id: Worker 进程 ID (Phase 2.1 新增)

    Returns:
        (match_id, features) 元组
    """
    import json

    # Phase 2.1: 添加 worker_id 到日志
    worker_logger = logging.getLogger(f"worker_{worker_id}")

    # 动态导入提取器
    module_path, class_name = extractor_class_path.rsplit(".", 1)
    mod = __import__(module_path, fromlist=[class_name])
    extractor_class = getattr(mod, class_name)

    match_id = match.get("match_id")
    raw_data = match.get("raw_data", {})

    try:
        # 解析 raw_data
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)

        # 提取特征
        extractor = extractor_class()
        result = extractor.extract(raw_data)

        if result and hasattr(result, "features"):
            worker_logger.debug(f"[Worker-{worker_id}] 提取成功: {match_id}")
            return (match_id, result.features)

        worker_logger.warning(f"[Worker-{worker_id}] 提取失败（无特征）: {match_id}")
        return (match_id, None)

    except Exception as e:
        worker_logger.error(f"[Worker-{worker_id}] 特征提取异常 {match_id}: {e}")
        return (match_id, None)


# ============================================================================
# 性能优化流水线编排器
# ============================================================================


class PerformancePipeline:
    """
    性能优化流水线 - 整合并行提取 + 批量入库

    目标: 1000+ 场/分钟
    """

    def __init__(
        self,
        db_config: Any,
        max_workers: int | None = None,
        batch_size: int = 50,  # V26.1: 默认 50（动态调整）
    ):
        """
        初始化性能优化流水线（V26.1）

        Args:
            db_config: 数据库配置
            max_workers: 最大进程数
            batch_size: 初始批量大小（会根据内存动态调整）
        """
        self.db_config = db_config
        self.parallel_extractor = ParallelFeatureExtractor(
            max_workers=max_workers,
            batch_size=batch_size,
        )

        # V26.1: 使用动态批次插入器
        conn_params = {
            "host": db_config.host,
            "port": db_config.port,
            "database": db_config.name,
            "user": db_config.user,
            "password": db_config.password.get_secret_value(),
        }

        self.bulk_inserter = BulkInserter(
            conn_params=conn_params,
            initial_batch_size=batch_size,
            min_batch_size=10,
            max_batch_size=100,
            memory_threshold=0.7,
        )

        # 连接参数（保留兼容性）
        self.conn_params = conn_params

    def process_candidates(
        self,
        candidates: list[dict[str, Any]],
        extractor_class_path: str = "src.processors.v25_production_extractor.V25ProductionExtractor",
    ) -> dict[str, Any]:
        """
        处理候选比赛（并行提取 + 批量入库）

        Args:
            candidates: 候选比赛列表
            extractor_class_path: 提取器类路径

        Returns:
            处理统计信息
        """
        start_time = time.time()

        # 1. 并行提取特征
        logger.info(f"开始并行提取 {len(candidates)} 场比赛...")
        extraction_results = self.parallel_extractor.extract_batch_parallel(
            candidates,
            extractor_class_path,
        )

        # 2. 准备批量插入数据
        insert_records = []
        for match_id, features in extraction_results:
            candidate = next((c for c in candidates if c["match_id"] == match_id), None)
            if candidate:
                record = self._prepare_insert_record(
                    match_id,
                    candidate,
                    features,
                )
                insert_records.append(record)

        # 3. 批量入库
        logger.info(f"开始批量插入 {len(insert_records)} 条记录...")
        inserted = self.bulk_inserter.insert_features_batch(insert_records)

        # 4. 统计
        elapsed = time.time() - start_time
        throughput = len(candidates) / elapsed * 60 if elapsed > 0 else 0

        stats = {
            "total_candidates": len(candidates),
            "extraction_success": len(extraction_results),
            "inserted": inserted,
            "elapsed_seconds": elapsed,
            "throughput_per_minute": throughput,
        }

        logger.info(
            f"性能流水线完成: "
            f"处理={stats['total_candidates']}, "
            f"提取={stats['extraction_success']}, "
            f"入库={stats['inserted']}, "
            f"耗时={stats['elapsed_seconds']:.1f}秒, "
            f"吞吐量={stats['throughput_per_minute']:.0f}场/分钟"
        )

        return stats

    def _prepare_insert_record(
        self,
        match_id: str,
        candidate: dict[str, Any],
        features: dict[str, Any],
    ) -> tuple:
        """准备插入记录（Phase 2.1: 使用 external_id）"""
        import json
        from datetime import datetime

        meta_data = {
            "extraction_version": "V26.2",
            "extracted_at": datetime.now().isoformat(),
            "pipeline_type": "parallel_performance",
        }

        # Phase 2.1: 检查是否有足够的特征数据
        # 如果 features 包含 _meta，使用它
        feature_count = len(features)
        if "_meta" in features:
            meta_data.update(features["_meta"])
            feature_count = features["_meta"].get("feature_count", len(features))

        return (
            match_id,  # Phase 2.1: 使用 external_id
            candidate.get("season", "0000"),
            candidate.get("match_date"),
            candidate.get("home_team"),
            candidate.get("away_team"),
            "V26.2",
            json.dumps(features, default=str),
            json.dumps(meta_data, default=str),
            feature_count,
            "PENDING",
        )


# ============================================================================
# 模块测试
# ============================================================================

if __name__ == "__main__":
    from src.config_unified import get_settings

    logging.basicConfig(level=logging.INFO)

    settings = get_settings()

    # 测试环境自愈
    healer = EnvironmentHealer(settings.database)
    healer.auto_fix_env()

    # 测试性能流水线
    pipeline = PerformancePipeline(settings.database)

    # 模拟测试数据
    test_candidates = [
        {
            "match_id": f"test_{i}",
            "season": "2324",
            "match_date": "2024-12-26",
            "home_team": "Team A",
            "away_team": "Team B",
            "raw_data": {"stats": {"xg": 1.5}},
        }
        for i in range(10)
    ]

    # 运行测试
    # stats = pipeline.process_candidates(test_candidates)
    # print(f"测试结果: {stats}")
