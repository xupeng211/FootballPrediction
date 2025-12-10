#!/usr/bin/env python3
"""
全历史数据回填脚本 - 安全加固版
Full Historical Data Backfill Script - Security Hardened Edition

# Strategy: Newest -> Oldest | Concurrency: 4 (Safe Mode)
使用 Super Greedy 采集器对过去 5 年 (2020-2025) 的全球核心赛事进行地毯式采集。
具备断点续传、智能风控、429避障等企业级安全特性。

Security Features:
- 🛡️ 智能风控降级 (4并发 + 1-3秒延迟)
- 🔄 倒序回填策略 (优先近期高价值数据)
- 🚨 智能429避障 (自动冷却+重试)
- ⏯️ 断点续传机制 (支持随时中断/继续)
- 📊 实时进度监控
- 🔧 硬编码补丁机制

Author: DevOps & Security Engineer
Version: 2.1.0 Security Hardened Edition
Date: 2025-01-08
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from random import uniform

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backfill_full_history.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入进度条
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    logger.warning("⚠️ tqdm未安装，将使用简单进度显示")

# 导入项目模块
try:
    from collectors.fotmob_api_collector import FotMobAPICollector
    from database.async_manager import get_db_session, initialize_database
    from database.models.match import Match
    from sqlalchemy import text  # 🔧 修复: 导入 text 函数
    COLLECTOR_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ 无法导入采集器模块: {e}")
    COLLECTOR_AVAILABLE = False

# 配置常量
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/football_prediction"
)

# 🏗️ 硬编码补丁 - 高价值联赛 ID
HARDCODED_PATCHES = {
    "Championship": 48,      # 英冠 - 关键次级联赛
    "Liga Portugal": 61,     # 葡超 - 葡萄牙顶级联赛
}

# 时间机器配置 - 倒序回填策略 (优先近期高价值数据)
YEARS_TO_BACKFILL = [2025, 2024, 2023, 2022, 2021, 2020]  # 新 -> 旧
CONCURRENT_LIMIT = 4  # 风控降级：安全并发数
MIN_DELAY = 1.0  # 风控降级：最小延迟
MAX_DELAY = 3.0  # 风控降级：最大延迟
RATE_LIMIT_COOLDOWN = 60  # 429 触发时的冷却时间(秒)

# 洲际联赛配置 (用于赛季格式判断)
EUROPEAN_COUNTRIES = {
    "England", "Spain", "Germany", "Italy", "France",
    "Netherlands", "Portugal", "Belgium", "Scotland",
    "Turkey", "Russia", "Ukraine", "Poland", "Czech Republic",
    "Austria", "Switzerland", "Denmark", "Norway", "Sweden"
}

AMERICAN_COUNTRIES = {
    "USA", "Brazil", "Argentina", "Mexico", "Chile", "Colombia",
    "Peru", "Uruguay", "Paraguay", "Ecuador", "Bolivia", "Venezuela"
}

ASIAN_COUNTRIES = {
    "Japan", "South Korea", "China", "Australia", "Saudi Arabia",
    "UAE", "Qatar", "Iran", "Iraq", "Jordan"
}

@dataclass
class BackfillStats:
    """回填统计信息"""
    total_matches: int = 0
    processed_matches: int = 0
    skipped_matches: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    start_time: datetime = None
    errors_by_type: dict[str, int] = None

    def __post_init__(self):
        if self.errors_by_type is None:
            self.errors_by_type = {}
        if self.start_time is None:
            self.start_time = datetime.now()

    @property
    def progress_percentage(self) -> float:
        """计算进度百分比"""
        if self.total_matches == 0:
            return 0.0
        return (self.processed_matches / self.total_matches) * 100

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.processed_matches == 0:
            return 0.0
        return (self.successful_matches / self.processed_matches) * 100

    @property
    def elapsed_time(self) -> timedelta:
        """计算已用时间"""
        return datetime.now() - self.start_time

    def log_progress(self):
        """记录进度日志"""
        logger.info(
            f"📊 进度: {self.processed_matches}/{self.total_matches} "
            f"({self.progress_percentage:.1f}%) | "
            f"✅ 成功: {self.successful_matches} | "
            f"⏭️ 跳过: {self.skipped_matches} | "
            f"❌ 失败: {self.failed_matches} | "
            f"📈 成功率: {self.success_rate:.1f}% | "
            f"⏱️ 已用: {self.elapsed_time}"
        )

class SeasonFormatGenerator:
    """赛季格式生成器 - 智能处理不同联赛的赛季格式，避免重复抓取"""

    def __init__(self):
        # 根据联赛ID精确分类，避免重复格式
        self.crossover_leagues = {
            # 欧洲主要跨年制联赛 (8月-5月)
            47,    # Premier League (英格兰)
            42,    # Championship (英格兰)
            54,    # La Liga (西班牙)
            82,    # Serie A (意大利)
            100,   # Bundesliga (德国)
            354,   # Ligue 1 (法国)
            127,   # Eredivisie (荷兰)
            5,     # Champions League (欧洲冠军联赛)
            61,    # Europa League (欧洲联赛)
            57,    # Conference League (欧洲协会联赛)
            364,   # Primeira Liga (葡萄牙)
            381,   # Scottish Premiership (苏格兰)
            # 其他欧洲联赛
            144, 196, 312, 125, 399, 155, 406, 345, 71, 2, 59, 116, 419
        }

        self.single_year_leagues = {
            # 南美单年制联赛 (通常在年内进行)
            268,   # Brasileirão (巴西)
            326,   # Argentine Primera División (阿根廷)
            377,   # Colombian Liga (哥伦比亚)
            313,   # Chilean Primera División (智利)
            # 中北美联赛
            34,    # MLS (美国职业大联盟)
            194,   # Liga MX (墨西哥)
            # 亚洲联赛
            372,   # J1 League (日本)
            70,    # K League 1 (韩国)
            # 其他单年制联赛
            126, 210, 96, 408, 311, 398, 310, 306, 348, 421, 338, 433, 392, 103, 171
        }

    def generate_season_string(self, year: int, league_info: dict[str, Any]) -> list[str]:
        """
        根据联赛信息智能生成唯一的赛季格式，避免重复抓取

        Args:
            year: 赛季年份
            league_info: 联赛信息字典

        Returns:
            List[str]: 包含唯一赛季格式的列表（不再是多个格式）
        """
        league_id = league_info.get("id", 0)
        country = league_info.get("country", "")
        league_type = league_info.get("type", "league")

        # 1. 优先根据精确的联赛ID分类
        if league_id in self.crossover_leagues:
            return [f"{year}/{year + 1}"]  # 跨年制：2023/2024
        elif league_id in self.single_year_leagues:
            return [str(year)]  # 单年制：2023

        # 2. 根据国家分类（备用逻辑）
        if country in EUROPEAN_COUNTRIES:
            if league_type == "league":
                return [f"{year}/{year + 1}"]  # 欧洲联赛多为跨年制
            else:  # 杯赛
                return [str(year)]  # 杯赛多为单年制

        elif country in AMERICAN_COUNTRIES:
            return [str(year)]  # 美洲多为单年制

        elif country in ASIAN_COUNTRIES:
            if country in ["Japan", "South Korea"]:
                return [f"{year}/{year + 1}"]  # 日韩跨年制
            else:
                return [str(year)]  # 其他亚洲单年制

        # 3. 默认策略：优先使用跨年制（欧洲联赛较多）
        logger.debug(f"未分类联赛 {league_id} ({country})，默认使用跨年制格式")
        return [f"{year}/{year + 1}"]

class IndustrialBackfillEngine:
    """工业级回填引擎"""

    def __init__(self):
        self.stats = BackfillStats()
        self.semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
        self.collector = None
        self.processed_match_ids: set[str] = set()
        self.league_cache: dict[int, dict[str, Any]] = {}

    async def initialize(self):
        """初始化回填引擎"""
        logger.info("🚀 初始化工业级回填引擎...")

        if not COLLECTOR_AVAILABLE:
            raise RuntimeError("❌ 采集器模块不可用，无法继续")

        # 初始化数据库
        initialize_database()

        # 初始化采集器
        self.collector = FotMobAPICollector(
            max_concurrent=CONCURRENT_LIMIT,
            timeout=60,
            max_retries=3,
            base_delay=1.0,
            enable_proxy=False,  # 回填时禁用代理以提高速度
            enable_jitter=True
        )

        await self.collector.initialize()

        # 预加载已处理过的比赛ID
        await self._preload_processed_matches()

        logger.info("✅ 工业级回填引擎初始化完成")

    async def _preload_processed_matches(self):
        """预加载已处理的比赛ID"""
        logger.info("📋 预加载已处理的比赛ID...")

        try:
            async with get_db_session() as session:
                result = await session.execute(
                    text("SELECT id FROM matches WHERE status = 'finished'")
                )
                matches = result.fetchall()
                self.processed_match_ids = {match[0] for match in matches}
                logger.info(f"✅ 已加载 {len(self.processed_match_ids)} 个已处理比赛ID")

        except Exception as e:
            logger.warning(f"⚠️ 预加载比赛ID失败，将跳过断点续传: {e}")
            self.processed_match_ids = set()

    async def load_league_config(self) -> list[dict[str, Any]]:
        """加载联赛配置并应用硬编码补丁"""
        logger.info("📋 加载联赛配置...")

        config_path = project_root / "config" / "target_leagues.json"

        if not config_path.exists():
            logger.error(f"❌ 配置文件不存在: {config_path}")
            return []

        try:
            with open(config_path, encoding='utf-8') as f:
                config = json.load(f)

            leagues = config.get("leagues", [])
            logger.info(f"✅ 从配置文件加载了 {len(leagues)} 个联赛")

            # 🏗️ 应用硬编码补丁
            patched_leagues = self._apply_hardcoded_patches(leagues)
            logger.info(f"🔧 应用硬编码补丁后: {len(patched_leagues)} 个联赛")

            return patched_leagues

        except Exception as e:
            logger.error(f"❌ 加载联赛配置失败: {e}")
            return []

    def _apply_hardcoded_patches(self, leagues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """应用硬编码补丁"""
        logger.info("🔧 应用硬编码补丁...")

        existing_names = {league.get("name") for league in leagues}
        existing_ids = {league.get("id") for league in leagues}

        for league_name, league_id in HARDCODED_PATCHES.items():
            if league_name not in existing_names and league_id not in existing_ids:
                # 添加硬编码的联赛
                patch_league = {
                    "name": league_name,
                    "id": league_id,
                    "tier": 2,  # 默认为二级联赛
                    "country": "England" if league_name == "Championship" else "Portugal",
                    "type": "league",
                    "source": "hardcoded_patch"
                }
                leagues.append(patch_league)
                logger.info(f"🔧 添加硬编码补丁联赛: {league_name} (ID: {league_id})")
            else:
                logger.debug(f"ℹ️ 联赛已存在，跳过补丁: {league_name}")

        return leagues

    async def fetch_league_matches(self, league_id: int, season: str) -> list[str]:
        """获取联赛指定赛季的比赛ID列表 - 使用FotMob fixtures API"""
        try:
            logger.debug(f"🔍 获取联赛 {league_id} 赛季 {season} 的比赛列表...")

            # 使用FotMob fixtures API
            league_url = f"https://www.fotmob.com/api/leagues?id={league_id}&timezone=Europe/London"

            # 使用采集器发送请求
            data, status = await self.collector._make_request(league_url, f"league_{league_id}")

            if status.name != "SUCCESS" or not data:
                logger.warning(f"⚠️ 联赛 {league_id} API请求失败: {status}")
                return []

            # 从fixtures.allMatches提取比赛数据
            matches_data = []
            if "fixtures" in data:
                matches_data = data["fixtures"].get("allMatches", [])
                logger.info(f"✅ 从fixtures.allMatches找到: {len(matches_data)}场比赛")

            if not matches_data:
                logger.warning(f"⚠️ 联赛 {league_id} 赛季 {season}: 未找到比赛数据")
                return []

            # 提取纯数字比赛ID
            match_ids = []
            for match in matches_data:
                if not isinstance(match, dict):
                    continue

                match_id = match.get("id")
                if not match_id:
                    match_id = match.get("matchId") or match.get("match_id")

                if match_id:
                    clean_id = str(match_id).strip()
                    if clean_id.isdigit():
                        match_ids.append(clean_id)
                    else:
                        logger.warning(f"⚠️ 跳过非数字ID: {clean_id}")

            await asyncio.sleep(uniform(0.1, 0.3))  # 网络延迟

            if match_ids:
                logger.info(f"✅ 联赛 {league_id} 赛季 {season}: 找到 {len(match_ids)} 场比赛")
                return match_ids
            else:
                logger.warning(f"⚠️ 联赛 {league_id} 赛季 {season}: 未找到有效比赛ID")
                return []

        except Exception as e:
            logger.error(f"❌ 获取联赛 {league_id} 赛季 {season} 比赛列表失败: {e}")
            return []

    async def process_match(self, match_id: str, league_info: dict[str, Any]) -> bool:
        """处理单个比赛 - 智能429避障版"""
        async with self.semaphore:  # 控制并发
            try:
                # 断点续传检查
                if match_id in self.processed_match_ids:
                    logger.debug(f"⏭️ 跳过已存在比赛: {match_id}")
                    self.stats.skipped_matches += 1
                    return True

                # 智能采集比赛数据 (含429避障)
                logger.debug(f"🔄 正在采集: {match_id}")
                match_data = await self._collect_with_429_protection(match_id)

                if match_data:
                    # 保存到数据库
                    await self._save_match_data(match_data, league_info)
                    self.stats.successful_matches += 1
                    logger.debug(f"✅ 成功处理: {match_id}")
                    return True
                else:
                    self.stats.failed_matches += 1
                    self.stats.errors_by_type["collection_failed"] = self.stats.errors_by_type.get("collection_failed", 0) + 1
                    return False

            except Exception as e:
                self.stats.failed_matches += 1
                error_type = type(e).__name__
                self.stats.errors_by_type[error_type] = self.stats.errors_by_type.get(error_type, 0) + 1
                logger.error(f"❌ 处理比赛 {match_id} 失败: {e}")
                return False

            finally:
                # 安全流量控制
                await asyncio.sleep(uniform(MIN_DELAY, MAX_DELAY))

    async def _collect_with_429_protection(self, match_id: str):
        """智能429避障的数据采集方法"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 尝试采集数据
                return await self.collector.collect_match_details(match_id)

            except Exception as e:
                error_str = str(e).lower()

                # 检查是否为429错误
                if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
                    logger.warning(f"⚠️ Rate Limit Hit! Cooling down for {RATE_LIMIT_COOLDOWN}s... (Attempt {attempt + 1}/{max_retries})")
                    self.stats.errors_by_type["rate_limit_429"] = self.stats.errors_by_type.get("rate_limit_429", 0) + 1

                    # 强制冷却
                    await asyncio.sleep(RATE_LIMIT_COOLDOWN)

                    # 如果不是最后一次尝试，继续重试
                    if attempt < max_retries - 1:
                        logger.info("🔄 Retrying after cooldown...")
                        continue
                    else:
                        logger.error(f"❌ Max retries exceeded for {match_id} after 429 errors")
                        return None

                else:
                    # 其他错误直接抛出
                    logger.debug(f"🔄 Non-429 error, will be handled by caller: {e}")
                    raise

        return None

    async def _save_match_data(self, match_data, league_info: dict[str, Any]):
        """保存比赛数据到数据库"""
        try:
            async with get_db_session() as session:
                # 检查是否已存在（按 fotmob_id 查询）
                existing = await session.execute(
                    text("SELECT id FROM matches WHERE fotmob_id = :fotmob_id"),
                    {"fotmob_id": match_data.fotmob_id}
                )
                if existing.fetchone():
                    # 更新现有记录（按 fotmob_id 更新）
                    update_query = text("""
                    UPDATE matches SET
                        home_score = :home_score,
                        away_score = :away_score,
                        status = :status,
                        home_xg = :home_xg,
                        away_xg = :away_xg,
                        stats_json = :stats_json,
                        lineups_json = :lineups_json,
                        odds_snapshot_json = :odds_snapshot_json,
                        match_info = :match_info,
                        environment_json = :environment_json,
                        data_completeness = :data_completeness,
                        collection_time = NOW(),
                        updated_at = NOW()
                    WHERE fotmob_id = :fotmob_id
                    """)
                    await session.execute(update_query, {
                        "home_score": match_data.home_score,
                        "away_score": match_data.away_score,
                        "status": match_data.status,
                        "home_xg": match_data.xg_home,
                        "away_xg": match_data.xg_away,
                        "stats_json": json.dumps(match_data.stats_json) if match_data.stats_json else None,
                        "lineups_json": json.dumps(match_data.lineups_json) if match_data.lineups_json else None,
                        "odds_snapshot_json": json.dumps(match_data.odds_snapshot_json) if match_data.odds_snapshot_json else None,
                        "match_info": json.dumps(match_data.match_info) if match_data.match_info else None,
                        "environment_json": json.dumps(match_data.environment_json) if match_data.environment_json else None,
                        "data_completeness": "partial",
                        "fotmob_id": match_data.fotmob_id
                    })
                    logger.info(f"📝 更新比赛数据: {match_data.fotmob_id}")
                else:
                    # 插入新记录（不设置 id，让它自增）
                    insert_query = text("""
                    INSERT INTO matches (
                        fotmob_id, home_team_name, away_team_name,
                        home_score, away_score, status,
                        home_xg, away_xg,
                        match_time, match_date,
                        data_source, data_completeness, collection_time,
                        stats_json, lineups_json, odds_snapshot_json,
                        match_info, environment_json
                    ) VALUES (
                        :fotmob_id, :home_team_name, :away_team_name,
                        :home_score, :away_score, :status,
                        :home_xg, :away_xg,
                        :match_time, :match_date,
                        :data_source, :data_completeness, NOW(),
                        :stats_json, :lineups_json, :odds_snapshot_json,
                        :match_info, :environment_json
                    )
                    """)
                    await session.execute(insert_query, {
                        "fotmob_id": match_data.fotmob_id,
                        "home_team_name": getattr(match_data, 'home_team_name', 'Home Team'),
                        "away_team_name": getattr(match_data, 'away_team_name', 'Away Team'),
                        "home_score": match_data.home_score,
                        "away_score": match_data.away_score,
                        "status": match_data.status,
                        "home_xg": match_data.xg_home,
                        "away_xg": match_data.xg_away,
                        "match_time": match_data.match_time,
                        "match_date": match_data.match_time,
                        "data_source": "fotmob_v2",
                        "data_completeness": "partial",
                        "stats_json": json.dumps(match_data.stats_json) if match_data.stats_json else None,
                        "lineups_json": json.dumps(match_data.lineups_json) if match_data.lineups_json else None,
                        "odds_snapshot_json": json.dumps(match_data.odds_snapshot_json) if match_data.odds_snapshot_json else None,
                        "match_info": json.dumps(match_data.match_info) if match_data.match_info else None,
                        "environment_json": json.dumps(match_data.environment_json) if match_data.environment_json else None,
                    })
                    logger.info(f"💾 新增比赛数据: {match_data.fotmob_id}")

                await session.commit()
                self.processed_match_ids.add(match_data.fotmob_id)

        except Exception as e:
            logger.error(f"❌ 保存比赛数据失败 {match_data.fotmob_id}: {e}")
            raise

    async def run_backfill(self):
        """运行完整回填流程"""
        logger.info("🚀 启动全历史数据回填...")

        try:
            # 加载联赛配置
            leagues = await self.load_league_config()
            if not leagues:
                logger.error("❌ 没有可用的联赛配置，退出")
                return False

            # 生成回填任务
            backfill_tasks = await self._generate_backfill_tasks(leagues)
            if not backfill_tasks:
                logger.error("❌ 没有生成回填任务，退出")
                return False

            self.stats.total_matches = len(backfill_tasks)
            logger.info(f"📊 总计需要处理 {self.stats.total_matches} 场比赛")

            # 执行回填任务
            await self._execute_backfill_tasks(backfill_tasks)

            # 输出最终统计
            await self._print_final_stats()

            return True

        except Exception as e:
            logger.error(f"❌ 回填流程执行失败: {e}")
            return False

    async def _generate_backfill_tasks(self, leagues: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
        """生成回填任务列表 - 智能赛季格式，避免重复抓取"""
        logger.info("📋 生成回填任务...")

        tasks = []
        season_generator = SeasonFormatGenerator()  # 创建智能赛季生成器实例

        for league in leagues:
            league_id = league.get("id")
            league_name = league.get("name", "Unknown")

            logger.info(f"🔍 处理联赛: {league_name} (ID: {league_id})")

            for year in YEARS_TO_BACKFILL:
                # 生成唯一的赛季格式（不再重复）
                season_formats = season_generator.generate_season_string(year, league)

                # 由于现在每个联赛只生成一种赛季格式，我们可以简化逻辑
                season = season_formats[0]  # 取第一个（也是唯一的）赛季格式

                try:
                    # 获取该赛季的比赛列表
                    match_ids = await self.fetch_league_matches(league_id, season)

                    for match_id in match_ids:
                        tasks.append((match_id, league))

                    logger.info(f"✅ 联赛 {league_name} {season} 赛季: {len(match_ids)} 场比赛")

                except Exception as e:
                    logger.warning(f"⚠️ 获取联赛 {league_name} 赛季 {season} 失败: {e}")
                    continue

        logger.info(f"✅ 生成回填任务: {len(tasks)} 个")
        return tasks

    async def _execute_backfill_tasks(self, tasks: list[tuple[str, dict[str, Any]]]):
        """执行回填任务"""
        logger.info("🚀 开始执行回填任务...")

        # 创建进度条
        if TQDM_AVAILABLE:
            pbar = tqdm(total=len(tasks), desc="回填进度", unit="比赛")

        # 批量处理任务
        batch_size = 50
        processed_count = 0

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]

            # 创建并发任务
            batch_tasks = [
                self.process_match(match_id, league_info)
                for match_id, league_info in batch
            ]

            # 执行并发任务
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # 统计结果
            for result in results:
                self.stats.processed_matches += 1
                processed_count += 1

                if isinstance(result, Exception):
                    logger.error(f"❌ 任务执行异常: {result}")
                    self.stats.failed_matches += 1

                # 更新进度条
                if TQDM_AVAILABLE:
                    pbar.update(1)

            # 每50个比赛打印一次进度
            if processed_count % 50 == 0:
                self.stats.log_progress()

        # 关闭进度条
        if TQDM_AVAILABLE:
            pbar.close()

    async def _print_final_stats(self):
        """打印最终统计信息"""
        logger.info("\n" + "="*60)
        logger.info("🏁 全历史数据回填完成")
        logger.info("="*60)
        logger.info(f"📊 总比赛数: {self.stats.total_matches}")
        logger.info(f"✅ 成功处理: {self.stats.successful_matches}")
        logger.info(f"⏭️ 跳过已存在: {self.stats.skipped_matches}")
        logger.info(f"❌ 处理失败: {self.stats.failed_matches}")
        logger.info(f"📈 成功率: {self.stats.success_rate:.1f}%")
        logger.info(f"⏱️ 总用时: {self.stats.elapsed_time}")

        if self.stats.errors_by_type:
            logger.info("\n🚨 错误统计:")
            for error_type, count in self.stats.errors_by_type.items():
                # 特别高亮429错误
                if "rate_limit_429" in error_type:
                    logger.info(f"  🚨 {error_type}: {count} (触发了智能冷却)")
                else:
                    logger.info(f"  📊 {error_type}: {count}")

            # 风控状态报告
            rate_429_count = self.stats.errors_by_type.get("rate_limit_429", 0)
            if rate_429_count > 0:
                total_429_cooldown = rate_429_count * RATE_LIMIT_COOLDOWN
                logger.info("\n🛡️ 风控报告:")
                logger.info(f"  429触发次数: {rate_429_count}")
                logger.info(f"  总冷却时间: {total_429_cooldown//60}分{total_429_cooldown%60}秒")
                logger.info(f"  平均处理速度: ~{self.stats.successful_matches / max(1, (self.stats.elapsed_time.total_seconds() - total_429_cooldown) / 3600):.0f}场/小时 (不含冷却时间)")
            else:
                logger.info("\n🛡️ 风控报告: 未触发429限制，安全运行")

        logger.info("="*60)
        logger.info("🎉 全历史数据回填任务完成!")

    async def cleanup(self):
        """清理资源"""
        if self.collector:
            await self.collector.close()
        logger.info("🧹 资源清理完成")

async def main():
    """主函数"""
    logger.info("🛡️ 启动安全加固版全历史数据回填脚本")
    logger.info(f"📊 策略配置: 倒序回填 ({YEARS_TO_BACKFILL[0]} -> {YEARS_TO_BACKFILL[-1]})")
    logger.info(f"🔒 风控设置: {CONCURRENT_LIMIT}并发 + {MIN_DELAY}-{MAX_DELAY}秒延迟")
    logger.info(f"🚨 429避障: {RATE_LIMIT_COOLDOWN}秒自动冷却 + 3次重试")

    # 设置环境变量
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = DATABASE_URL

    # 创建回填引擎
    engine = IndustrialBackfillEngine()

    try:
        # 初始化
        await engine.initialize()

        # 执行回填
        success = await engine.run_backfill()

        if success:
            logger.info("✅ 安全加固版全历史数据回填任务成功完成!")
            sys.exit(0)
        else:
            logger.error("❌ 安全加固版全历史数据回填任务失败!")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断，正在保存进度...")
        engine.stats.log_progress()
        sys.exit(130)

    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}")
        sys.exit(1)

    finally:
        await engine.cleanup()

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
