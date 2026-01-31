#!/usr/bin/env python3
"""
[Genesis.OfflineHarvest] production_harvest_batch.py
========================================================

独立运行的生产级赛季刷新与收割脚本。

核心功能：
A. 赛季 ID 刷新模块 - 获取 2025/2026 赛季最新比赛列表
B. 生产级收割流水线 - 5 并发 Worker 全链路穿透
C. 离线优化 - 静默模式 + 断点续传

Usage:
    python production_harvest_batch.py

Author: Genesis.OfflineHarvest Team
Version: V1.0
Date: 2026-01-30
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# 配置与常量
# ============================================================================

# 五大联赛配置 (2025/2026 赛季)
TOP_5_LEAGUES = {
    47: "Premier League",
    87: "La Liga",
    78: "Bundesliga",
    126: "Serie A",
    53: "Ligue 1",
}

TARGET_SEASON = "2526"  # 2025/2026 赛季

# 并发配置
MAX_WORKERS = 5
BATCH_SIZE = 50  # 每 50 场打印一次进度

# 日志配置
LOG_DIR = Path("logs/ops")
LOG_DIR.mkdir(parents=True, exist_ok=True)
DETAILED_LOG = LOG_DIR / "harvest_detailed.log"
PROGRESS_LOG = LOG_DIR / "harvest_progress.log"

# FotMob API 配置
FOTMOB_API_BASE = "https://www.fotmob.com/api"
FOTMOB_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ============================================================================
# 日志设置
# ============================================================================


def setup_logging() -> logging.Logger:
    """配置日志系统"""
    logger = logging.getLogger("OfflineHarvest")
    logger.setLevel(logging.INFO)

    # 清空处理器
    logger.handlers.clear()

    # 详细日志 (文件)
    file_handler = logging.FileHandler(DETAILED_LOG, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 进度日志 (文件 + 控制台)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 进度日志文件
    progress_handler = logging.FileHandler(PROGRESS_LOG, encoding="utf-8")
    progress_handler.setLevel(logging.INFO)
    progress_handler.setFormatter(console_formatter)
    logger.addHandler(progress_handler)

    return logger


logger = setup_logging()


# ============================================================================
# 数据类定义
# ============================================================================


@dataclass
class MatchInfo:
    """比赛信息"""
    match_id: str
    league_id: int
    league_name: str
    season: str
    home_team: str
    away_team: str
    match_date: datetime | None = None
    status: str = "UNKNOWN"

    def __hash__(self) -> int:
        return hash(self.match_id)


@dataclass
class HarvestResult:
    """收割结果"""
    match_id: str
    success: bool
    data_collected: bool = False
    features_extracted: bool = False
    prediction_made: bool = False
    error_message: str = ""
    provider_count: int = 0
    processing_time_ms: float = 0


@dataclass
class BatchStats:
    """批处理统计"""
    total_matches: int = 0
    processed_matches: int = 0
    successful_harvests: int = 0
    successful_features: int = 0
    successful_predictions: int = 0
    failed_matches: int = 0
    skipped_matches: int = 0
    start_time: float = field(default_factory=time.time)

    def get_elapsed(self) -> float:
        return time.time() - self.start_time

    def get_rate(self) -> float:
        elapsed = self.get_elapsed()
        if elapsed > 0:
            return self.processed_matches / elapsed * 60
        return 0


# ============================================================================
# 数据库连接
# ============================================================================


def get_db_connection():
    """获取数据库连接"""
    from src.config_unified import get_settings

    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


# ============================================================================
# A. 赛季 ID 刷新模块
# ============================================================================


class SeasonIDRefresher:
    """
    赛季 ID 刷新器

    获取 2025/2026 赛季五大联赛的最新比赛列表。
    """

    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": random.choice(FOTMOB_USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Referer": "https://www.fotmob.com/",
        }

    def fetch_league_matches(self, league_id: int) -> list[dict]:
        """
        获取联赛比赛列表

        使用 FotMob API: /leagues?id={league_id}
        """
        url = f"{FOTMOB_API_BASE}/leagues?id={league_id}"

        try:
            import requests

            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 提取比赛列表
            matches = []
            league_data = data.get("leagues", [{}])[0] if data.get("leagues") else {}

            # 获取当前赛季比赛
            if "matches" in league_data:
                for match in league_data["matches"].get("allMatches", []):
                    match_id = match.get("id")
                    if not match_id:
                        continue

                    # 过滤 2025/2026 赛季
                    season = match.get("season", "")
                    if TARGET_SEASON not in season:
                        continue

                    matches.append({
                        "match_id": str(match_id),
                        "league_id": league_id,
                        "league_name": TOP_5_LEAGUES.get(league_id, f"League {league_id}"),
                        "season": TARGET_SEASON,
                        "home_team": match.get("home", {}).get("name", "Unknown"),
                        "away_team": match.get("away", {}).get("name", "Unknown"),
                        "status": match.get("status", {}).get("state", "UNKNOWN"),
                        "utc_time": match.get("time", {}).get("utcTime", ""),
                    })

            logger.info(f"[IDRefresher] League {league_id}: 发现 {len(matches)} 场 {TARGET_SEASON} 赛季比赛")
            return matches

        except Exception as e:
            logger.error(f"[IDRefresher] 获取联赛 {league_id} 比赛失败: {e}")
            return []

    def refresh_season_ids(self) -> list[MatchInfo]:
        """
        刷新所有五大联赛的赛季 ID

        Returns:
            MatchInfo 列表
        """
        all_matches = []

        logger.info(f"[IDRefresher] 开始刷新 {TARGET_SEASON} 赛季 ID...")

        for league_id, league_name in TOP_5_LEAGUES.items():
            matches = self.fetch_league_matches(league_id)

            for m in matches:
                try:
                    match_date = None
                    if m.get("utc_time"):
                        try:
                            match_date = datetime.fromisoformat(m["utc_time"].replace("Z", "+00:00"))
                        except:
                            pass

                    all_matches.append(MatchInfo(
                        match_id=m["match_id"],
                        league_id=m["league_id"],
                        league_name=m["league_name"],
                        season=m["season"],
                        home_team=m["home_team"],
                        away_team=m["away_team"],
                        match_date=match_date,
                        status=m["status"],
                    ))
                except Exception as e:
                    logger.debug(f"[IDRefresher] 跳过无效比赛: {e}")

        logger.info(f"[IDRefresher] 总共发现 {len(all_matches)} 场比赛")
        return all_matches

    def upsert_matches_to_db(self, matches: list[MatchInfo]) -> int:
        """
        将比赛信息插入/更新到数据库

        Returns:
            插入/更新的记录数
        """
        if not matches:
            return 0

        updated_count = 0

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            for match in matches:
                try:
                    cursor.execute("""
                        INSERT INTO matches (match_id, league_name, season, home_team, away_team, match_time)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (match_id)
                        DO UPDATE SET
                            league_name = EXCLUDED.league_name,
                            season = EXCLUDED.season,
                            home_team = EXCLUDED.home_team,
                            away_team = EXCLUDED.away_team,
                            match_time = COALESCE(EXCLUDED.match_time, matches.match_time)
                    """, (
                        match.match_id,
                        match.league_name,
                        match.season,
                        match.home_team,
                        match.away_team,
                        match.match_date,
                    ))
                    updated_count += 1

                except Exception as e:
                    logger.debug(f"[IDRefresher] 插入比赛 {match.match_id} 失败: {e}")

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"[IDRefresher] 数据库更新完成: {updated_count} 条记录")
            return updated_count

        except Exception as e:
            logger.error(f"[IDRefresher] 数据库操作失败: {e}")
            return updated_count


# ============================================================================
# B. 生产级收割流水线
# ============================================================================


class ProductionHarvestPipeline:
    """
    生产级收割流水线

    全链路穿透：
    1. JS Executor (QuantHarvester) 抓取赔率数据
    2. GoldenExtractor 提炼特征
    3. ModelDispatcher 进行预测
    4. 数据库同步
    """

    def __init__(self):
        self.stats = BatchStats()
        self.stats_lock = Lock()

        # 延迟导入模块 (避免初始化错误)
        self.js_executor = None
        self.golden_extractor = None
        self.model_dispatcher = None

    def initialize_components(self):
        """初始化组件"""
        try:
            # 导入 JS 执行器
            from src.bridge.adapters.js_executor import JSExecutor
            from src.bridge.schemas.harvest import HarvestRequest

            self.js_executor = JSExecutor()
            self.HarvestRequest = HarvestRequest

            logger.info("[Pipeline] JS Executor initialized")

            # 导入特征提取器
            from src.processors.v41_380_golden_extractor import GoldenFeatureExtractor

            self.golden_extractor = GoldenFeatureExtractor()
            logger.info("[Pipeline] Golden Extractor initialized")

            # 导入模型分发器
            from src.ml.inference.model_dispatcher import ModelDispatcher

            self.model_dispatcher = ModelDispatcher()
            logger.info("[Pipeline] Model Dispatcher initialized")

        except Exception as e:
            logger.error(f"[Pipeline] 组件初始化失败: {e}")
            raise

    def check_match_processed(self, match_id: str) -> bool:
        """
        检查比赛是否已处理 (断点续传)

        Returns:
            True 如果已处理 (有有效 L2 数据)
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT l2_raw_json IS NOT NULL AND l2_raw_json != ''::jsonb AS has_data
                FROM matches
                WHERE match_id = %s
            """, (match_id,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result and result.get("has_data"):
                return True

            return False

        except Exception as e:
            logger.debug(f"[Pipeline] 检查比赛 {match_id} 状态失败: {e}")
            return False

    def fetch_l2_data(self, match_id: str) -> dict | None:
        """
        获取 L2 数据 (FotMob API)

        Returns:
            L2 数据字典或 None
        """
        try:
            from src.collectors.fotmob_core import FotMobCoreCollector

            collector = FotMobCoreCollector()
            result = collector.fetch_match_details(int(match_id))

            if result.get("success") and result.get("data"):
                return result["data"]

            return None

        except Exception as e:
            logger.debug(f"[Pipeline] 获取 L2 数据失败 (match_id={match_id}): {e}")
            return None

    def extract_golden_features(self, l2_data: dict, match_date: datetime | None) -> dict:
        """
        提炼黄金特征
        """
        if not self.golden_extractor:
            self.initialize_components()

        try:
            features = self.golden_extractor.extract_all_golden_features(l2_data, match_date)
            return features
        except Exception as e:
            logger.debug(f"[Pipeline] 特征提取失败: {e}")
            return {}

    def make_prediction(self, match_data: dict) -> dict | None:
        """
        执行预测
        """
        if not self.model_dispatcher:
            self.initialize_components()

        try:
            result = self.model_dispatcher.predict(match_data)
            return result
        except Exception as e:
            logger.debug(f"[Pipeline] 预测失败: {e}")
            return None

    def save_prediction_to_db(self, match_id: str, prediction: dict):
        """
        保存预测结果到数据库
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 保存到 metrics_multi_source_data (作为预测数据源)
            cursor.execute("""
                INSERT INTO metrics_multi_source_data (
                    match_id, source_name, init_h, init_d, init_a,
                    final_h, final_d, final_a, integrity_score
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id, source_name)
                DO UPDATE SET
                    init_h = EXCLUDED.init_h,
                    init_d = EXCLUDED.init_d,
                    init_a = EXCLUDED.init_a,
                    final_h = EXCLUDED.final_h,
                    final_d = EXCLUDED.final_d,
                    final_a = EXCLUDED.final_a
            """, (
                match_id,
                "ModelPrediction",
                prediction.get("probabilities", {}).get("Away", 0),
                prediction.get("probabilities", {}).get("Draw", 0),
                prediction.get("probabilities", {}).get("Home", 0),
                prediction.get("probabilities", {}).get("Away", 0),
                prediction.get("probabilities", {}).get("Draw", 0),
                prediction.get("probabilities", {}).get("Home", 0),
                1.0,  # integrity_score
            ))

            # 保存到 prediction_logs
            cursor.execute("""
                INSERT INTO prediction_logs (
                    match_id, model_type, prediction, confidence,
                    home_prob, draw_prob, away_prob, predicted_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match_id,
                prediction.get("model_source", "unknown"),
                prediction.get("prediction", ""),
                prediction.get("confidence", 0),
                prediction.get("probabilities", {}).get("Home", 0),
                prediction.get("probabilities", {}).get("Draw", 0),
                prediction.get("probabilities", {}).get("Away", 0),
                datetime.now(),
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            logger.debug(f"[Pipeline] 保存预测失败 (match_id={match_id}): {e}")

    def process_single_match(self, match: MatchInfo) -> HarvestResult:
        """
        处理单场比赛 (全链路)

        Returns:
            HarvestResult
        """
        start_time = time.time()
        result = HarvestResult(match_id=match.match_id, success=False)

        try:
            # 1. 检查断点续传
            if self.check_match_processed(match.match_id):
                result.error_message = "Already processed (skip)"
                with self.stats_lock:
                    self.stats.skipped_matches += 1
                return result

            # 2. 获取 L2 数据
            l2_data = self.fetch_l2_data(match.match_id)
            if not l2_data:
                result.error_message = "Failed to fetch L2 data"
                return result

            result.data_collected = True

            # 3. 提炼特征
            features = self.extract_golden_features(
                {"l2_json": l2_data},
                match.match_date
            )
            if not features:
                result.error_message = "Feature extraction failed"
                return result

            result.features_extracted = True

            # 4. 构建预测输入
            match_data = {
                "match_id": match.match_id,
                "league_id": match.league_id,
                "league_name": match.league_name,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "season": match.season,
                **features,  # 合并特征
            }

            # 5. 执行预测
            prediction = self.make_prediction(match_data)
            if not prediction:
                result.error_message = "Prediction failed"
                return result

            result.prediction_made = True
            result.provider_count = len(prediction.get("probabilities", {}))

            # 6. 保存到数据库
            self.save_prediction_to_db(match.match_id, prediction)

            result.success = True

            with self.stats_lock:
                self.stats.successful_harvests += 1
                self.stats.successful_features += 1
                self.stats.successful_predictions += 1

        except Exception as e:
            result.error_message = str(e)
            logger.debug(f"[Pipeline] 处理比赛 {match.match_id} 失败: {e}")

            with self.stats_lock:
                self.stats.failed_matches += 1

        result.processing_time_ms = (time.time() - start_time) * 1000

        with self.stats_lock:
            self.stats.processed_matches += 1

        return result

    def process_batch(self, matches: list[MatchInfo]) -> BatchStats:
        """
        批量处理比赛 (并发)

        Args:
            matches: 比赛列表

        Returns:
            BatchStats
        """
        self.stats = BatchStats()
        self.stats.total_matches = len(matches)

        logger.info(f"[Pipeline] 开始处理 {len(matches)} 场比赛 (并发={MAX_WORKERS})...")

        # 初始化组件
        self.initialize_components()

        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self.process_single_match, match): match
                for match in matches
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1

                # 每 BATCH_SIZE 场打印一次进度
                if completed % BATCH_SIZE == 0:
                    logger.info(
                        f"[Pipeline] 进度: {completed}/{len(matches)} "
                        f"({completed * 100 // len(matches)}%) | "
                        f"成功: {self.stats.successful_predictions} | "
                        f"失败: {self.stats.failed_matches} | "
                        f"跳过: {self.stats.skipped_matches}"
                    )

                try:
                    result = future.result()
                    # 详细日志写入文件
                    if result.success:
                        logger.debug(
                            f"[SUCCESS] {result.match_id} | "
                            f"Providers: {result.provider_count} | "
                            f"Time: {result.processing_time_ms:.0f}ms"
                        )
                    elif result.error_message != "Already processed (skip)":
                        logger.debug(
                            f"[FAILED] {result.match_id} | {result.error_message}"
                        )
                except Exception as e:
                    logger.debug(f"[Pipeline] Future 异常: {e}")

        # 最终统计
        elapsed = self.stats.get_elapsed()
        logger.info(f"[Pipeline] 批处理完成!")
        logger.info(f"  总场次: {self.stats.total_matches}")
        logger.info(f"  已处理: {self.stats.processed_matches}")
        logger.info(f"  成功收割: {self.stats.successful_harvests}")
        logger.info(f"  成功预测: {self.stats.successful_predictions}")
        logger.info(f"  失败: {self.stats.failed_matches}")
        logger.info(f"  跳过: {self.stats.skipped_matches}")
        logger.info(f"  耗时: {elapsed:.1f}秒")
        logger.info(f"  速率: {self.stats.get_rate():.1f} 场/分钟")

        return self.stats


# ============================================================================
# C. 主程序
# ============================================================================


def main():
    """主函数"""
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║     [Genesis.OfflineHarvest] production_harvest_batch.py   ║
    ║                                                            ║
    ║  A. 赛季 ID 刷新 - 2025/2026 五大联赛                      ║
    ║  B. 生产级收割 - 5 并发全链路穿透                          ║
    ║  C. 离线优化 - 静默模式 + 断点续传                         ║
    ╚════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("=" * 60)
    logger.info("[Genesis.OfflineHarvest] 脚本启动")
    logger.info("=" * 60)
    logger.info(f"目标赛季: {TARGET_SEASON}")
    logger.info(f"目标联赛: {', '.join(TOP_5_LEAGUES.values())}")
    logger.info(f"并发度: {MAX_WORKERS}")
    logger.info(f"详细日志: {DETAILED_LOG}")
    logger.info("-" * 60)

    total_start = time.time()

    try:
        # ====================================================================
        # Step A: 赛季 ID 刷新
        # ====================================================================
        logger.info("\n[Step A] 赛季 ID 刷新...")
        logger.info("-" * 40)

        refresher = SeasonIDRefresher()
        matches = refresher.refresh_season_ids()

        if not matches:
            logger.warning("[Step A] 未发现任何比赛，请检查网络或 API 状态")
            return

        # 插入/更新数据库
        updated = refresher.upsert_matches_to_db(matches)
        logger.info(f"[Step A] 完成! 更新 {updated} 条记录\n")

        # ====================================================================
        # Step B: 生产级收割流水线
        # ====================================================================
        logger.info("[Step B] 生产级收割流水线...")
        logger.info("-" * 40)

        pipeline = ProductionHarvestPipeline()
        stats = pipeline.process_batch(matches)

        # ====================================================================
        # 最终报告
        # ====================================================================
        total_elapsed = time.time() - total_start

        logger.info("\n" + "=" * 60)
        logger.info("[Genesis.OfflineHarvest] 执行完成")
        logger.info("=" * 60)
        logger.info(f"总耗时: {total_elapsed:.1f}秒 ({total_elapsed/60:.1f}分钟)")
        logger.info(f"处理成功率: {stats.successful_predictions * 100 / max(stats.processed_matches, 1):.1f}%")
        logger.info(f"详细日志: {DETAILED_LOG}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("\n[Genesis.OfflineHarvest] 用户中断执行")
    except Exception as e:
        logger.error(f"\n[Genesis.OfflineHarvest] 执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
