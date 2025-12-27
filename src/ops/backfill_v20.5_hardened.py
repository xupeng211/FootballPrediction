#!/usr/bin/env python3
"""
V20.5 工业级硬化回填执行器
============================

特性:
- 熔断器保护 (连续 20 个 403 自动关机)
- 断点续传 (基于 JSON 进度文件)
- 数据验证卫士 (Schema 验证)
- 分级日志系统
- 实时统计面板

作者: SRE Team
日期: 2025-12-24
版本: V20.5
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# 只在没有环境变量时加载 .env，否则使用传入的环境变量
if os.getenv("DB_HOST"):
    load_dotenv(override=False)  # 尊重已设置的环境变量
else:
    load_dotenv(override=True)  # 使用 .env 文件的配置

import psycopg2
from psycopg2.extras import RealDictCursor

from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.config_unified import get_settings
from src.ml.data_guard import DataGuard
from src.ml.fault_tolerance import CheckpointTracker, CircuitBreaker, CircuitBreakerConfig, ProcessingResult
from src.ml.feature_forge_v20 import FeatureExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/backfill_v20.5.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ==================== 全局状态 ====================
GRACEFUL_SHUTDOWN = False


def signal_handler(signum, frame):
    """优雅关闭信号处理"""
    global GRACEFUL_SHUTDOWN
    logger.info(f"收到信号 {signum}，准备优雅关闭...")
    GRACEFUL_SHUTDOWN = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class BackfillConfig:
    """回填配置"""

    # 五大联赛配置
    LEAGUES = {47: "Premier_League", 53: "Serie_A", 54: "Bundesliga", 55: "Ligue_1", 87: "LaLiga"}

    SEASONS = ["2122", "2223", "2324", "2425"]

    # API 限速
    DELAY_SECONDS = 2.0
    BATCH_SIZE = 100

    # 数据库配置
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 10


class BackfillOrchestrator:
    """回填编排器"""

    def __init__(self):
        self.settings = get_settings()
        self.config = BackfillConfig()

        # 初始化组件
        cb_config = CircuitBreakerConfig(
            failure_threshold=20, timeout_seconds=300, error_codes={403, 429, 500, 502, 503}
        )
        self.circuit_breaker = CircuitBreaker(cb_config)
        self.checkpoint_tracker = CheckpointTracker("data/backfill_progress_v20.5.json")
        self.data_guard = DataGuard()
        self.feature_extractor = FeatureExtractor()
        # V20.5.2 HOTFIX: 集成真实数据采集器
        self.fotmob_collector = FotMobCoreCollector()

        # 数据库连接
        self.db_conn = None

        # V20.5.3 HOTFIX: 设置数据库同步并修复伪失败
        self.checkpoint_tracker.set_db_connection_getter(self._get_db_connection)
        self.checkpoint_tracker.sync_with_database()

        logger.info("=" * 60)
        logger.info("V20.5 工业级硬化回填执行器初始化完成")
        logger.info("熔断器阈值: 20 次连续失败")
        logger.info("断点文件: data/backfill_progress_v20.5.json")
        logger.info(f"API 限速: {self.config.DELAY_SECONDS} 秒/请求")
        logger.info("=" * 60)

    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db_conn is None or self.db_conn.closed:
            # V20.5: 智能数据库主机检测
            # 1. 优先使用显式设置的环境变量
            db_host = os.getenv("DB_HOST", os.getenv("FOOTBALL_DB_HOST", self.settings.database.host))

            # 2. 如果配置的是 "db" 但无法解析，则使用 localhost
            if db_host == "db":
                try:
                    import socket

                    socket.gethostbyname("db")
                    logger.debug("Docker 环境检测: 'db' 主机可解析")
                except socket.gaierror:
                    logger.info("检测到非 Docker 环境，自动切换到 localhost")
                    db_host = "localhost"

            logger.debug(f"连接数据库: {db_host}:{self.settings.database.port}/{self.settings.database.name}")

            self.db_conn = psycopg2.connect(
                host=db_host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self.db_conn

    def _load_manifest(self, league_id: int, season: str) -> list[dict]:
        """加载 manifest 文件"""
        manifest_file = Path(f"data/production/manifest_{league_id}_{season}.csv")

        if not manifest_file.exists():
            logger.warning(f"Manifest 文件不存在: {manifest_file}")
            return []

        matches = []
        with open(manifest_file) as f:
            lines = f.readlines()
            headers = lines[0].strip().split(",")

            for line in lines[1:]:
                values = line.strip().split(",")
                if len(values) >= 6:
                    match = {
                        "match_id": int(values[0].strip('"')),
                        "league_id": int(values[1]),
                        "league_name": values[2].strip('"'),
                        "season_id": values[3].strip('"'),
                        "home_team": values[4].strip('"'),
                        "away_team": values[5].strip('"') if len(values) > 5 else "",
                        "status": values[6].strip('"') if len(values) > 6 else "unknown",
                    }
                    matches.append(match)

        logger.info(f"加载 Manifest: {len(matches)} 场比赛 ({league_id}/{season})")
        return matches

    def _get_db_total_count(self) -> int:
        """获取数据库 match_features_training 表总记录数"""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM match_features_training")
            count = cur.fetchone()["count"]
            cur.close()
            return count
        except Exception as e:
            logger.warning(f"无法获取数据库记录总数: {e}")
            return 0

    def _process_single_match(self, match: dict) -> ProcessingResult:
        """
        V20.5.2 HOTFIX: 处理单场比赛 - 集成真实特征提取器

        流程:
        1. 从 FotMob API 获取比赛详情
        2. 使用 FeatureExtractor 提取 660+ 维特征
        3. 强制校验特征维度 > 300
        4. 保存到数据库
        """
        match_id = match["match_id"]

        # 检查熔断器
        if not self.circuit_breaker.can_execute():
            return ProcessingResult(match_id=match_id, success=False, error="Circuit breaker is OPEN", error_code=503)

        try:
            logger.debug(f"处理 Match {match_id}: {match['home_team']} vs {match['away_team']}")

            # 检查是否已存在于数据库
            conn = self._get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT match_id FROM match_features_training
                WHERE match_id = %s
            """,
                (match_id,),
            )

            if cur.fetchone():
                cur.close()
                logger.debug(f"Match {match_id} 已存在，跳过")
                self.checkpoint_tracker.record_skip(match_id)
                return ProcessingResult(match_id=match_id, success=True, error="Already exists")

            cur.close()

            # V20.5.2 HOTFIX: 步骤 1 - 从 FotMob API 获取比赛详情
            logger.debug(f"正在获取 Match {match_id} 的 FotMob 数据...")
            match_data = self.fotmob_collector.fetch_match_details(match_id)

            if not match_data:
                logger.warning(f"Match {match_id}: FotMob API 无数据返回")
                return ProcessingResult(match_id=match_id, success=False, error="API returned no data", error_code=404)

            # V20.5.3 HOTFIX: 步骤 2 - 使用真实特征提取器
            logger.debug(f"正在提取 Match {match_id} 的特征...")

            # V20.5.3 CRITICAL FIX: 正确套娃 l2_json 结构
            # FeatureExtractor.extract_features() 期望:
            # match_data['player_stats']['l2_json'] = 原始 FotMob API 响应
            match_data_wrapped = {
                "match_id": match_id,
                "league_id": match["league_id"],
                "season_id": match["season_id"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_score": None,
                "away_score": None,
                "player_stats": {
                    "l2_json": match_data  # 关键: 套娃 l2_json 层
                },
            }

            extracted = self.feature_extractor.extract_features(match_data_wrapped)

            # V20.5.3 HOTFIX: 步骤 3 - 强制校验特征维度
            enriched_features = extracted.get("enriched", {})
            core_features = extracted.get("core", {})
            player_assets = extracted.get("player_assets", [])

            enriched_count = len(enriched_features)
            player_assets_count = len(player_assets) if isinstance(player_assets, list) else 0

            logger.debug(f"Match {match_id}: 提取到 {enriched_count} 维特征, {player_assets_count} 名球员数据")

            # V20.5.3 HOTFIX: 动态阈值 - 根据可用周期调整最小特征数
            # 检查 API 返回的 Periods 数量
            periods_data = match_data.get("content", {}).get("stats", {}).get("Periods", {})
            has_first_half = "FirstHalf" in periods_data
            has_second_half = "SecondHalf" in periods_data

            # 动态阈值设定
            if has_first_half and has_second_half:
                # 全息模式: 有 All + FirstHalf + SecondHalf
                MIN_FEATURES = 600
                mode_desc = "holographic (3 periods)"
            else:
                # 兼容模式: 只有 All 周期 (历史比赛)
                MIN_FEATURES = 250
                mode_desc = "compatibility (1 period)"

            if enriched_count < MIN_FEATURES:
                error_msg = f"Feature extraction degraded: only {enriched_count} features extracted (minimum {MIN_FEATURES} required for {mode_desc})"
                logger.error(f"Match {match_id}: {error_msg}")
                self.circuit_breaker.record_failure()
                return ProcessingResult(match_id=match_id, success=False, error=error_msg, error_code=500)

            logger.debug(f"Match {match_id}: 模式={mode_desc}, 特征数={enriched_count}/{MIN_FEATURES} ✅")

            # 构建最终保存的特征字典
            final_features = {
                **core_features,
                **enriched_features,
                "_meta": {
                    "extraction_version": "V20.5.2",
                    "feature_count": enriched_count,
                    "player_assets_count": player_assets_count,
                    "extracted_at": datetime.now().isoformat(),
                },
            }

            # 数据验证
            allowed, validation_result = self.data_guard.verify_before_save(match, final_features)

            if not allowed:
                logger.error(f"Match {match_id} 数据验证失败: {len(validation_result.errors)} errors")
                return ProcessingResult(
                    match_id=match_id, success=False, error=f"Validation failed: {len(validation_result.errors)} errors"
                )

            # 保存到数据库
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO match_features_training (match_id, league_id, season_id, home_team, away_team, enriched_features, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO UPDATE SET
                    enriched_features = EXCLUDED.enriched_features,
                    updated_at = NOW()
            """,
                (
                    match_id,
                    match["league_id"],
                    match["season_id"],
                    match["home_team"],
                    match["away_team"],
                    json.dumps(final_features),
                    datetime.now(),
                ),
            )

            conn.commit()
            cur.close()

            logger.info(f"✅ Match {match_id}: 成功提取 {enriched_count} 维特征")

            return ProcessingResult(match_id=match_id, success=True, duration=0.01)

        except Exception as e:
            logger.error(f"处理 Match {match_id} 失败: {e}")
            self.circuit_breaker.record_failure(exception=e)
            return ProcessingResult(match_id=match_id, success=False, error=str(e))

    def run_backfill(self):
        """执行回填"""
        logger.info("=" * 60)
        logger.info("V20.5 流式回填启动")
        logger.info("=" * 60)

        total_matches = 0

        # 统计每个联赛的场次
        for league_id in self.config.LEAGUES.keys():
            for season in self.config.SEASONS:
                matches = self._load_manifest(league_id, season)
                total_matches += len(matches)

        logger.info(f"总场次: {total_matches}")
        logger.info(f"预计耗时: ~{total_matches * self.config.DELAY_SECONDS / 3600:.1f} 小时")
        logger.info("")

        self.checkpoint_tracker.set_total(total_matches)

        # V20.5.1 FIX: 会话级计数器 (本次启动的增量统计)
        session_processed = 0
        session_success = 0
        session_failed = 0
        session_skipped = 0

        processed = 0
        start_time = time.time()

        # 按联赛顺序处理
        for league_id, league_name in self.config.LEAGUES.items():
            if GRACEFUL_SHUTDOWN:
                logger.info("检测到关闭信号，停止处理")
                break

            for season in self.config.SEASONS:
                if GRACEFUL_SHUTDOWN:
                    break

                matches = self._load_manifest(league_id, season)

                if not matches:
                    continue

                logger.info("")
                logger.info(f"开始处理: {league_name} {season} ({len(matches)} 场)")

                for match in matches:
                    if GRACEFUL_SHUTDOWN:
                        logger.info("检测到关闭信号，停止处理")
                        break

                    result = self._process_single_match(match)

                    # V20.5.1 FIX: 区分会话统计和全局统计
                    session_processed += 1
                    processed += 1

                    if result.success:
                        if result.error == "Already exists":
                            # 已存在于数据库，记录为跳过
                            session_skipped += 1
                        else:
                            # 真正处理成功
                            session_success += 1
                            self.circuit_breaker.record_success()
                        self.checkpoint_tracker.record_success(match["match_id"])
                    else:
                        session_failed += 1
                        self.checkpoint_tracker.record_failure(match["match_id"])
                        if result.error_code:
                            self.circuit_breaker.record_failure(result.error_code)

                    # 每批打印统计
                    if processed % self.config.BATCH_SIZE == 0:
                        progress = self.checkpoint_tracker.get_progress()
                        elapsed = time.time() - start_time
                        rate = processed / elapsed if elapsed > 0 else 0
                        session_rate = session_success / elapsed if elapsed > 0 else 0

                        logger.info("")
                        logger.info(
                            f"批次 #{processed // self.config.BATCH_SIZE}: 已处理 {processed}/{total_matches} 场"
                        )
                        # V20.5.1 FIX: 区分 [Session] 和 [Global DB]
                        logger.info(
                            f"  [Session] 本次运行: 成功 {session_success}, 跳过 {session_skipped}, 失败 {session_failed}"
                        )
                        logger.info(
                            f"  [Global DB] 累积总计: 成功 {progress['successful']}, 跳过 {progress['skipped']}, 失败 {progress['failed']}"
                        )
                        logger.info(
                            f"  会话速率: {session_rate:.2f} 场/秒 | 熔断状态: {self.circuit_breaker.state.value}, 失败计数: {self.circuit_breaker.failure_count}"
                        )

                    # API 限速
                    time.sleep(self.config.DELAY_SECONDS)

        # 最终统计
        elapsed = time.time() - start_time
        progress = self.checkpoint_tracker.get_progress()
        db_total = self._get_db_total_count()

        logger.info("")
        logger.info("=" * 60)
        logger.info("V20.5 流式回填完成")
        logger.info("=" * 60)
        logger.info(f"总耗时: {elapsed / 3600:.2f} 小时")
        # V20.5.1 FIX: 区分 [Session] 和 [Global DB]
        logger.info("")
        logger.info("[Session] 本次运行统计:")
        logger.info(f"  已处理: {session_processed} 场")
        logger.info(f"  成功: {session_success}, 跳过: {session_skipped}, 失败: {session_failed}")
        logger.info(
            f"  会话成功率: {session_success / session_processed * 100:.1f}%"
            if session_processed > 0
            else "  会话成功率: N/A"
        )
        logger.info("")
        logger.info("[Global DB] 累积统计:")
        logger.info(f"  Checkpoint: {progress['processed']}/{progress['total_matches']} 场")
        logger.info(
            f"  累积成功: {progress['successful']}, 累积跳过: {progress['skipped']}, 累积失败: {progress['failed']}"
        )
        logger.info(f"  数据库记录总数: {db_total}")
        logger.info("")
        logger.info(f"熔断次数: {self.circuit_breaker.trip_count}")
        logger.info("=" * 60)

        # 关闭数据库连接
        if self.db_conn:
            self.db_conn.close()


def main():
    """主入口"""
    orchestrator = BackfillOrchestrator()

    try:
        orchestrator.run_backfill()
    except KeyboardInterrupt:
        logger.info("用户中断，正在保存进度...")
    except Exception as e:
        logger.error(f"回填异常: {e}")
        raise
    finally:
        logger.info("程序退出")


if __name__ == "__main__":
    main()
