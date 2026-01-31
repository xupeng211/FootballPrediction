#!/usr/bin/env python3
"""
V37.0【全量洗髓】收割器 - Legacy数据重炼版
==============================================
核心任务:
1. 历史赛季Deep Sweep - 收割五大联赛+荷甲所有缺失场次
2. 遗留数据重炼 - 将959条V35.1-LEGACY升级为V37.0-HOLOGRAPHIC
3. 数据均匀度保证 - 确保各联赛数据平衡
4. 慢速稳健模式 - 并发度3，避免触发API封禁

目标:
- 总记录数突破 5,500 场
- 全息化率 100%
"""

import asyncio
import csv
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor

# Add src to path
project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))

from src.ml.miners_v34.greedy_miner import GreedyMiner

logger = logging.getLogger(__name__)


# ============================================================
# V35.2 继承: 深度反爬盔甲
# ============================================================

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

LANGUAGE_POOL = [
    "en-US,en;q=0.9,en-GB;q=0.8",
    "en-GB,en;q=0.9",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
]

# 联赛ID映射
LEAGUE_NAMES = {
    47: "Premier League",
    87: "La Liga",
    54: "Bundesliga",
    55: "Serie A",
    53: "Ligue 1",
    42: "Eredivisie",  # 荷甲
    61: "Serie A",  # 意甲另一ID
}


@dataclass
class V37Stats:
    """V37.0 洗髓统计"""

    phase: str = "INIT"

    # 收割统计
    total_targets: int = 0
    processed: int = 0
    successful_harvests: int = 0
    failed_harvests: int = 0
    rejected_dirty: int = 0
    skipped_existing: int = 0

    # 重炼统计
    legacy_targets: int = 0
    legacy_reprocessed: int = 0
    legacy_upgraded: int = 0
    legacy_failed: int = 0

    # 数据质量
    holographic_data: int = 0
    legacy_data: int = 0

    retry_count: int = 0
    start_time: float = field(default_factory=time.time)

    def get_elapsed(self) -> float:
        return time.time() - self.start_time

    def get_rate(self) -> float:
        elapsed = self.get_elapsed()
        if elapsed > 0:
            return self.successful_harvests / elapsed * 60
        return 0


class MarrowCleaningHarvester:
    """
    V37.0 全量洗髓收割器

    双引擎模式:
    1. Deep Sweep: 收割历史缺失场次
    2. Legacy Refining: 重炼LEGACY数据为HOLOGRAPHIC
    """

    def __init__(self, concurrency: int = 3):
        self.concurrency = concurrency
        self.session: aiohttp.ClientSession | None = None
        self.miner = GreedyMiner()
        self.stats = V37Stats()
        self.db_conn = None
        self.harvested_ids: set[int] = set()

        # 日志文件
        self.bad_matches_log = Path("data/logs/v37_bad_matches.log")
        self.bad_matches_log.parent.mkdir(parents=True, exist_ok=True)

        self.upgrade_log = Path("data/logs/v37_legacy_upgrades.log")
        self.upgrade_log.parent.mkdir(parents=True, exist_ok=True)

    def _get_random_headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(UA_POOL),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": random.choice(LANGUAGE_POOL),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

    def validate_payload(self, data: dict, match_id: int) -> tuple[bool, str]:
        """V37.0 零容忍数据校验"""
        content = data.get("content")
        if not content or not isinstance(content, dict):
            return False, "Missing or invalid 'content' field"

        # 关键检查: 必须有 stats 才能算全息数据
        has_stats = bool(content.get("stats"))
        has_shotmap = bool(content.get("shotmap"))

        if not (has_stats or has_shotmap):
            return False, "Missing both 'stats' and 'shotmap'"

        if "header" not in data:
            return False, "Missing 'header' field"

        return True, "OK"

    def _log_dirty_match(self, match_id: int, reason: str, l2_data: dict):
        """记录脏数据"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "phase": self.stats.phase,
            "match_id": match_id,
            "rejection_reason": reason,
        }

        with open(self.bad_matches_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _log_legacy_upgrade(self, match_id: int, was_legacy: bool, is_now_holographic: bool):
        """记录LEGACY升级"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "match_id": match_id,
            "was_legacy": was_legacy,
            "is_now_holographic": is_now_holographic,
        }

        with open(self.upgrade_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    async def fetch_match_details(self, match_id: int, max_retries: int = 3) -> dict | None:
        """V35.2: 带指数退避的数据获取"""
        url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"

        for attempt in range(max_retries):
            try:
                # V37.0: 更保守的延迟策略
                if attempt > 0:
                    delay = random.uniform(1.5, 2.5) * (1.5**attempt)
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(random.uniform(0.5, 1.0))

                headers = self._get_random_headers()

                async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status}: Match {match_id}")
                        continue

                    content_bytes = await response.read()
                    size = len(content_bytes)

                    # 哨兵检查: 50KB 最低阈值
                    if size < 50000:
                        logger.warning(f"⚠️ 响应过小: Match {match_id} ({size} bytes)")
                        self.stats.rejected_dirty += 1
                        return None

                    data = await response.json()

                    # 零容忍校验
                    is_valid, reason = self.validate_payload(data, match_id)
                    if not is_valid:
                        self._log_dirty_match(match_id, reason, data)
                        self.stats.rejected_dirty += 1
                        return None

                    # 判断数据版本
                    content = data.get("content", {})
                    is_legacy = not bool(content.get("stats"))

                    return {
                        "match_id": match_id,
                        "l2_json": data,
                        "is_legacy": is_legacy,
                        "size": size,
                    }

            except TimeoutError:
                logger.warning(f"⏰ 超时: Match {match_id}")
                self.stats.retry_count += 1
            except Exception as e:
                logger.warning(f"❌ 错误: Match {match_id} - {e}")
                self.stats.retry_count += 1

        self.stats.failed_harvests += 1
        return None

    def load_manifest(self, manifest_path: str) -> list[dict]:
        """加载 manifest 文件"""
        matches = []

        if not Path(manifest_path).exists():
            logger.warning(f"⚠️ Manifest不存在: {manifest_path}")
            return []

        with open(manifest_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_id = row.get("match_id") or row.get("id")
                if match_id:
                    matches.append(
                        {
                            "match_id": int(match_id),
                            "home_team": row.get("home_team") or row.get("home"),
                            "away_team": row.get("away_team") or row.get("away"),
                            "league_id": int(row.get("league_id", 47)),
                            "season": row.get("season", "2223"),
                        }
                    )

        logger.info(f"✓ 加载 manifest: {len(matches)} 场比赛")
        return matches

    def connect_db(self):
        """连接数据库"""
        import socket

        is_docker = os.getenv("DOCKER_ENV", "false").lower() == "true"
        db_host_env = os.getenv("DB_HOST", "db")
        db_port = int(os.getenv("DB_PORT", 5432))
        db_name = os.getenv("DB_NAME", "football_db")
        db_user = os.getenv("DB_USER", "football_user")
        db_pass = os.getenv("DB_PASSWORD", "football_pass")

        if not is_docker and db_host_env in ["db", "database", "postgres"]:
            try:
                socket.create_connection(("localhost", 5432), timeout=1)
                db_host = "localhost"
            except:
                db_host = db_host_env
        else:
            db_host = db_host_env

        self.db_conn = psycopg2.connect(host=db_host, port=db_port, database=db_name, user=db_user, password=db_pass)
        logger.info(f"✓ 数据库连接成功 (host={db_host})")

    def get_existing_records(self) -> dict[str, set[int]]:
        """获取现有记录 (用于跳过已收割)"""
        cursor = self.db_conn.cursor()

        cursor.execute("SELECT match_id FROM match_features_training")
        existing = {row[0] for row in cursor.fetchall()}
        cursor.close()

        return existing

    def get_legacy_records(self) -> list[dict]:
        """获取需要重炼的LEGACY记录"""
        cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT match_id, league_id, season_id, home_team, away_team, match_time
            FROM match_features_training
            WHERE extraction_version LIKE '%LEGACY%'
            ORDER BY league_id, season_id
        """)

        legacy_records = []
        for row in cursor.fetchall():
            # 解析赛季格式 (21/22 -> 2122)
            season_str = row["season_id"].replace("/", "")
            legacy_records.append(
                {
                    "match_id": row["match_id"],
                    "league_id": row["league_id"],
                    "season": season_str,
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                    "match_time": row["match_time"],
                }
            )

        cursor.close()
        return legacy_records

    def save_to_database(
        self, match_info: dict, holographic_features: dict, extraction_version: str, extraction_hash: str
    ):
        """保存到数据库"""
        cursor = self.db_conn.cursor()

        enriched_data = {
            "holographic_features": holographic_features,
            "raw_match_info": match_info,
        }

        match_time = match_info.get("match_time")
        if match_time:
            try:
                if isinstance(match_time, str):
                    match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
            except:
                match_time = datetime.now()
        else:
            match_time = datetime.now()

        cursor.execute(
            """
            INSERT INTO match_features_training (
                match_id, league_id, season_id, home_team, away_team,
                match_time, home_score, away_score, total_goals,
                enriched_features, extraction_version, extraction_logic_hash,
                extraction_timestamp, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id) DO UPDATE SET
                enriched_features = EXCLUDED.enriched_features,
                extraction_version = EXCLUDED.extraction_version,
                extraction_logic_hash = EXCLUDED.extraction_logic_hash,
                extraction_timestamp = EXCLUDED.extraction_timestamp,
                updated_at = CURRENT_TIMESTAMP
        """,
            (
                int(match_info["match_id"]),
                match_info.get("league_id"),
                match_info.get("season", ""),
                match_info["home_team"],
                match_info["away_team"],
                match_time,
                match_info.get("home_score"),
                match_info.get("away_score"),
                (match_info.get("home_score") or 0) + (match_info.get("away_score") or 0),
                json.dumps(enriched_data),
                extraction_version,
                extraction_hash,
                datetime.now(),
                datetime.now(),
                datetime.now(),
            ),
        )

        self.db_conn.commit()
        cursor.close()

    async def harvest_single_match(self, match_info: dict) -> bool:
        """收割单场比赛"""
        match_id = match_info["match_id"]

        # 跳过已收割 (Deep Sweep模式)
        if match_id in self.harvested_ids and self.stats.phase == "DEEP_SWEEP":
            self.stats.skipped_existing += 1
            return True

        try:
            # 获取 L2 数据
            l2_data = await self.fetch_match_details(match_id)
            if not l2_data:
                self.stats.failed_harvests += 1
                return False

            # 使用 GreedyMiner 提取全息特征
            holographic_features = self.miner.extract_all_features(l2_data["l2_json"], match_id=match_id)

            # 确定数据版本
            if l2_data["is_legacy"]:
                extraction_version = "V37.0-LEGACY"
                self.stats.legacy_data += 1
            else:
                extraction_version = "V37.0-HOLOGRAPHIC"
                self.stats.holographic_data += 1

            # 计算版本指纹
            extraction_hash = self.miner.get_extraction_hash(l2_data["l2_json"])

            # 存储到数据库
            self.save_to_database(match_info, holographic_features, extraction_version, extraction_hash)

            self.harvested_ids.add(match_id)
            self.stats.successful_harvests += 1
            self.stats.processed += 1

            return True

        except Exception as e:
            logger.error(f"收割失败: MatchID {match_id} - {e}")
            self.stats.failed_harvests += 1
            self.stats.processed += 1
            return False

    async def refine_legacy_match(self, match_info: dict) -> tuple[bool, bool]:
        """
        重炼LEGACY数据

        Returns:
            (success, upgraded): 是否成功，是否升级为全息
        """
        match_id = match_info["match_id"]

        try:
            # 获取 L2 数据
            l2_data = await self.fetch_match_details(match_id)
            if not l2_data:
                self.stats.legacy_failed += 1
                return False, False

            # 使用 GreedyMiner 提取全息特征
            holographic_features = self.miner.extract_all_features(l2_data["l2_json"], match_id=match_id)

            # 确定数据版本
            if l2_data["is_legacy"]:
                extraction_version = "V37.0-LEGACY-REPROCESSED"
                upgraded = False
            else:
                extraction_version = "V37.0-HOLOGRAPHIC"
                upgraded = True
                self.stats.legacy_upgraded += 1

            # 计算版本指纹
            extraction_hash = self.miner.get_extraction_hash(l2_data["l2_json"])

            # 存储到数据库
            self.save_to_database(match_info, holographic_features, extraction_version, extraction_hash)

            self.stats.legacy_reprocessed += 1
            self.stats.successful_harvests += 1

            # 记录升级
            self._log_legacy_upgrade(match_id, was_legacy=True, is_now_holographic=upgraded)

            return True, upgraded

        except Exception as e:
            logger.error(f"重炼失败: MatchID {match_id} - {e}")
            self.stats.legacy_failed += 1
            return False, False

    async def harvest_batch(self, matches: list[dict], batch_size: int = 50):
        """批量收割"""
        semaphore = asyncio.Semaphore(self.concurrency)

        async def harvest_with_semaphore(match_info: dict):
            async with semaphore:
                if self.stats.phase == "LEGACY_REFINING":
                    return await self.refine_legacy_match(match_info)
                else:
                    return await self.harvest_single_match(match_info)

        # 分批处理
        for i in range(0, len(matches), batch_size):
            batch = matches[i : i + batch_size]
            tasks = [harvest_with_semaphore(m) for m in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            # 打印进度
            remaining = len(matches) - i - batch_size
            self.print_progress(len(matches), remaining)

    def print_progress(self, total: int, remaining: int):
        """打印进度"""
        elapsed = self.stats.get_elapsed()
        rate = self.stats.get_rate()
        progress = (total - remaining) / total * 100

        if self.stats.phase == "LEGACY_REFINING":
            print(
                f"\r🔥 [{self.stats.phase}] {progress:.1f}% "
                f"| 重炼: {self.stats.legacy_reprocessed}/{self.stats.legacy_targets} "
                f"| 升级: {self.stats.legacy_upgraded} "
                f"| 失败: {self.stats.legacy_failed} "
                f"| 速度: {rate:.1f} 场/分",
                end="",
                flush=True,
            )
        else:
            print(
                f"\r💧 [{self.stats.phase}] {progress:.1f}% "
                f"| 成功: {self.stats.successful_harvests} "
                f"| 拒绝: {self.stats.rejected_dirty} "
                f"| 失败: {self.stats.failed_harvests} "
                f"| 全息: {self.stats.holographic_data} "
                f"| 速度: {rate:.1f} 场/分",
                end="",
                flush=True,
            )

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60), connector=aiohttp.TCPConnector(limit=5)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


async def main():
    """主函数"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    print("\n" + "=" * 70)
    print("🧬 V37.0【全量洗髓】收割器启动")
    print("=" * 70)
    print("目标: 全量 5,500+ 场，全员全息化 (100% HOLOGRAPHIC)")
    print("=" * 70 + "\n")

    async with MarrowCleaningHarvester(concurrency=3) as harvester:
        harvester.connect_db()

        # 获取现有记录
        existing_ids = harvester.get_existing_records()
        harvester.harvested_ids = existing_ids
        print(f"✓ 现有记录: {len(existing_ids):,} 场\n")

        # ============================================================
        # 阶段 1: Deep Sweep - 五大联赛 + 荷甲缺失场次
        # ============================================================
        print("🎯 阶段 1: Deep Sweep (五大联赛 + 荷甲)")
        print("-" * 70)

        # 目标manifest - 所有缺失的赛季
        target_manifests = [
            # 22/23 赛季 (缺失: 西甲、德甲、意甲、法甲)
            "data/production/manifest_87_2223.csv",  # 西甲 22/23
            "data/production/manifest_54_2223.csv",  # 德甲 22/23
            "data/production/manifest_55_2223.csv",  # 意甲 22/23
            "data/production/manifest_53_2223.csv",  # 法甲 22/23
            # 23/24 赛季 (缺失: 西甲、德甲、意甲、法甲)
            "data/production/manifest_87_2324.csv",  # 西甲 23/24
            "data/production/manifest_54_2324.csv",  # 德甲 23/24
            "data/production/manifest_55_2324.csv",  # 意甲 23/24
            "data/production/manifest_53_2324.csv",  # 法甲 23/24
            # 24/25 赛季 (缺失: 西甲、德甲、意甲、法甲)
            "data/production/manifest_87_2425.csv",  # 西甲 24/25
            "data/production/manifest_54_2425.csv",  # 德甲 24/25
            "data/production/manifest_55_2425.csv",  # 意甲 24/25
            "data/production/manifest_53_2425.csv",  # 法甲 24/25
            # 21/22 赛季 (补充英超)
            "data/production/manifest_47_2122.csv",  # 英超 21/22
        ]

        all_matches = []
        for manifest_path in target_manifests:
            matches = harvester.load_manifest(manifest_path)
            all_matches.extend(matches)

        # 过滤已收割
        pending_matches = [m for m in all_matches if m["match_id"] not in existing_ids]

        harvester.stats.phase = "DEEP_SWEEP"
        harvester.stats.total_targets = len(pending_matches)

        print(f"\n🚀 开始收割 {len(pending_matches):,} 场新比赛...\n")

        if pending_matches:
            await harvester.harvest_batch(pending_matches, batch_size=50)

        # 阶段 1 统计
        print(f"\n\n{'=' * 70}")
        print("阶段 1 完成: Deep Sweep")
        print(f"{'=' * 70}")
        print(f"目标: {len(pending_matches):,} 场")
        print(f"成功: {harvester.stats.successful_harvests:,} 场")
        print(f"拒绝: {harvester.stats.rejected_dirty:,} 场")
        print(f"失败: {harvester.stats.failed_harvests:,} 场")
        print(f"全息: {harvester.stats.holographic_data:,} 场")
        print(f"速度: {harvester.stats.get_rate():.1f} 场/分钟")
        print(f"用时: {harvester.stats.get_elapsed() / 60:.1f} 分钟")
        print(f"{'=' * 70}\n")

        # 检查是否达成 5,000 里程碑
        current_total = len(existing_ids) + harvester.stats.successful_harvests
        if current_total >= 5000:
            print("\n" + "🎉" * 30)
            print("🎯 达成 5,000 场里程碑！")
            print("🎉" * 30 + "\n")

            # 生成质量分布表
            print_quality_distribution_report(harvester)
            return

        # ============================================================
        # 阶段 2: Legacy Refining - 重炼 959 条 LEGACY 记录
        # ============================================================
        print("\n🔥 阶段 2: Legacy Refining (重炼遗留数据)")
        print("-" * 70)

        legacy_records = harvester.get_legacy_records()
        harvester.stats.phase = "LEGACY_REFINING"
        harvester.stats.legacy_targets = len(legacy_records)

        print(f"\n🚀 开始重炼 {len(legacy_records):,} 条 LEGACY 记录...\n")

        if legacy_records:
            await harvester.harvest_batch(legacy_records, batch_size=50)

        # 最终统计
        print(f"\n\n{'=' * 70}")
        print("V37.0【全量洗髓】完成统计")
        print(f"{'=' * 70}")
        print(f"总成功: {harvester.stats.successful_harvests:,} 场")
        print(f"总拒绝: {harvester.stats.rejected_dirty:,} 场")
        print(f"总失败: {harvester.stats.failed_harvests:,} 场")
        print(f"全息数据: {harvester.stats.holographic_data:,} 场")
        print(f"遗留重炼: {harvester.stats.legacy_reprocessed:,} 条")
        print(f"升级成功: {harvester.stats.legacy_upgraded:,} 条")
        print(f"总用时: {harvester.stats.get_elapsed() / 60:.1f} 分钟")
        print(f"平均速度: {harvester.stats.get_rate():.1f} 场/分钟")
        print(f"{'=' * 70}\n")

        # 最终质量分布
        print_quality_distribution_report(harvester)


def print_quality_distribution_report(harvester: MarrowCleaningHarvester):
    """打印质量分布表（外部函数）"""
    cursor = harvester.db_conn.cursor()

    # 总记录数
    cursor.execute("SELECT COUNT(*) FROM match_features_training")
    total = cursor.fetchone()[0]

    # 按联赛分布
    cursor.execute(
        """
        SELECT
            league_id,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / %s, 1) as percentage
        FROM match_features_training
        GROUP BY league_id
        ORDER BY count DESC
    """,
        (total,),
    )

    print("\n📊 【最终质量分布表】")
    print("-" * 70)
    print("联赛 ID | 联赛名称          | 记录数 | 占比")
    print("-" * 70)

    for row in cursor.fetchall():
        league_id, count, percentage = row
        league_name = LEAGUE_NAMES.get(league_id, f"League {league_id}")
        print(f"  {league_id:4d}   | {league_name:16s} | {count:5d}  | {percentage:5.1f}%")

    print("-" * 70)
    print(f"        | 总计            | {total:5d}  | 100.0%")
    print("-" * 70 + "\n")

    cursor.close()


if __name__ == "__main__":
    asyncio.run(main())
