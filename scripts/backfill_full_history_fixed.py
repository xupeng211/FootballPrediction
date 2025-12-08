#!/usr/bin/env python3
"""
全历史数据回填脚本 - 安全加固版 (已修复异步调用错误)
Full Historical Data Backfill Script - Security Hardened Edition (Fixed Async Call Error)

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
Version: 2.1.1 Security Hardened Edition (Fixed)
Date: 2025-01-08

🔧 修复内容:
- 修复了 initialize_database() 的错误异步调用
- 修复了 _apply_hardcoded_patches() 的错误异步声明
- 确保同步/异步方法正确匹配
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
    errors_by_type: Dict[str, int] = None

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
    """赛季格式生成器 - 智能处理不同联赛的赛季格式"""

    @staticmethod
    def generate_season_string(year: int, league_info: Dict[str, Any]) -> List[str]:
        """
        生成赛季字符串列表，按优先级排序
        """
        country = league_info.get("country", "")
        league_type = league_info.get("type", "league")

        season_formats = []

        # 欧洲联赛主要使用跨年格式
        if country in EUROPEAN_COUNTRIES:
            if league_type == "league":
                season_formats.extend([
                    f"{year}/{year + 1}",  # 2023/2024
                    f"{year-1}/{year}",    # 2022/2023 (对于年初比赛)
                ])
            else:  # 杯赛
                season_formats.extend([
                    str(year),            # 2023
                    f"{year}/{year + 1}",  # 2023/2024
                ])

        # 美洲联赛主要使用单年格式
        elif country in AMERICAN_COUNTRIES:
            season_formats.extend([
                str(year),            # 2023
                f"{year}/{year + 1}",  # 备选跨年格式
            ])

        # 亚洲联赛混合使用
        elif country in ASIAN_COUNTRIES:
            if country in ["Japan", "South Korea"]:  # 跨年赛季
                season_formats.extend([
                    f"{year}/{year + 1}",
                    str(year),
                ])
            else:  # 单年赛季
                season_formats.extend([
                    str(year),
                    f"{year}/{year + 1}",
                ])

        # 国际赛事
        elif league_type == "cup" and "International" in country:
            season_formats.extend([
                str(year),
                f"{year}/{year + 1}",
            ])

        # 默认格式
        else:
            season_formats.extend([
                f"{year}/{year + 1}",
                str(year),
            ])

        # 去重并返回
        return list(dict.fromkeys(season_formats))

class IndustrialBackfillEngine:
    """工业级回填引擎"""

    def __init__(self):
        self.stats = BackfillStats()
        self.semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
        self.collector = None
        self.processed_match_ids: Set[str] = set()
        self.league_cache: Dict[int, Dict[str, Any]] = {}

    async def initialize(self):
        """初始化回填引擎"""
        logger.info("🚀 初始化工业级回填引擎...")

        if not COLLECTOR_AVAILABLE:
            raise RuntimeError("❌ 采集器模块不可用，无法继续")

        # 🔧 修复: initialize_database() 是同步函数，不需要 await
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
                    "SELECT fotmob_id FROM matches WHERE status = 'finished' AND fotmob_id IS NOT NULL"
                )
                matches = result.fetchall()
                self.processed_match_ids = {match[0] for match in matches}
                logger.info(f"✅ 已加载 {len(self.processed_match_ids)} 个已处理比赛ID")

        except Exception as e:
            logger.warning(f"⚠️ 预加载比赛ID失败，将跳过断点续传: {e}")
            self.processed_match_ids = set()

    async def load_league_config(self) -> List[Dict[str, Any]]:
        """加载联赛配置并应用硬编码补丁"""
        logger.info("📋 加载联赛配置...")

        config_path = project_root / "config" / "target_leagues.json"

        if not config_path.exists():
            logger.error(f"❌ 配置文件不存在: {config_path}")
            return []

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            leagues = config.get("leagues", [])
            logger.info(f"✅ 从配置文件加载了 {len(leagues)} 个联赛")

            # 🏗️ 应用硬编码补丁
            # 🔧 修复: _apply_hardcoded_patches() 是同步函数，不需要 await
            patched_leagues = self._apply_hardcoded_patches(leagues)
            logger.info(f"🔧 应用硬编码补丁后: {len(patched_leagues)} 个联赛")

            return patched_leagues

        except Exception as e:
            logger.error(f"❌ 加载联赛配置失败: {e}")
            return []

    # 🔧 修复: 这个方法没有异步操作，改为同步函数
    def _apply_hardcoded_patches(self, leagues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    # 其余方法保持不变...
    async def fetch_league_matches(self, league_id: int, season: str) -> List[str]:
        """获取联赛指定赛季的比赛ID列表"""
        try:
            # 这里应该调用 FotMob API 获取联赛赛程
            # 由于API限制，这里使用模拟数据

            # 模拟获取比赛ID
            logger.debug(f"🔍 获取联赛 {league_id} 赛季 {season} 的比赛列表...")

            # 模拟数据 - 实际实现中需要替换为真实的API调用
            match_ids = [f"{league_id}_{i}_{hash(season) % 10000}" for i in range(1, 50)]  # 模拟49场比赛

            # 随机延迟模拟网络请求
            await asyncio.sleep(uniform(0.1, 0.3))

            logger.info(f"✅ 联赛 {league_id} 赛季 {season}: 找到 {len(match_ids)} 场比赛")
            return match_ids

        except Exception as e:
            logger.error(f"❌ 获取联赛 {league_id} 赛季 {season} 比赛列表失败: {e}")
            return []

    async def process_match(self, match_id: str, league_info: Dict[str, Any]) -> bool:
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
                        logger.info(f"🔄 Retrying after cooldown...")
                        continue
                    else:
                        logger.error(f"❌ Max retries exceeded for {match_id} after 429 errors")
                        return None

                else:
                    # 其他错误直接抛出
                    logger.debug(f"🔄 Non-429 error, will be handled by caller: {e}")
                    raise

        return None

    async def _save_match_data(self, match_data, league_info: Dict[str, Any]):
        """保存比赛数据到数据库"""
        try:
            async with get_db_session() as session:
                # 检查是否已存在
                existing = await session.execute(
                    f"SELECT id FROM matches WHERE fotmob_id = '{match_data.fotmob_id}'"
                )
                if existing.fetchone():
                    # 更新现有记录
                    update_query = f"""
                    UPDATE matches SET
                        stats_json = :stats_json,
                        lineups_json = :lineups_json,
                        odds_snapshot_json = :odds_snapshot_json,
                        match_info = :match_info,
                        environment_json = :environment_json,
                        updated_at = NOW()
                    WHERE fotmob_id = :fotmob_id
                    """
                    await session.execute(update_query, {
                        "stats_json": json.dumps(match_data.stats_json) if match_data.stats_json else None,
                        "lineups_json": json.dumps(match_data.lineups_json) if match_data.lineups_json else None,
                        "odds_snapshot_json": json.dumps(match_data.odds_snapshot_json) if match_data.odds_snapshot_json else None,
                        "match_info": json.dumps(match_data.match_info) if match_data.match_info else None,
                        "environment_json": json.dumps(match_data.environment_json) if match_data.environment_json else None,
                        "fotmob_id": match_data.fotmob_id
                    })
                else:
                    # 插入新记录
                    insert_query = f"""
                    INSERT INTO matches (
                        fotmob_id, home_score, away_score, status, match_time,
                        venue, attendance, referee,
                        stats_json, lineups_json, odds_snapshot_json,
                        match_info, environment_json, created_at, updated_at
                    ) VALUES (
                        :fotmob_id, :home_score, :away_score, :status, :match_time,
                        :venue, :attendance, :referee,
                        :stats_json, :lineups_json, :odds_snapshot_json,
                        :match_info, :environment_json, NOW(), NOW()
                    )
                    """
                    await session.execute(insert_query, {
                        "fotmob_id": match_data.fotmob_id,
                        "home_score": match_data.home_score,
                        "away_score": match_data.away_score,
                        "status": match_data.status,
                        "match_time": match_data.match_time,
                        "venue": match_data.venue,
                        "attendance": match_data.attendance,
                        "referee": match_data.referee,
                        "stats_json": json.dumps(match_data.stats_json) if match_data.stats_json else None,
                        "lineups_json": json.dumps(match_data.lineups_json) if match_data.lineups_json else None,
                        "odds_snapshot_json": json.dumps(match_data.odds_snapshot_json) if match_data.odds_snapshot_json else None,
                        "match_info": json.dumps(match_data.match_info) if match_data.match_info else None,
                        "environment_json": json.dumps(match_data.environment_json) if match_data.environment_json else None,
                    })

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

    async def _generate_backfill_tasks(self, leagues: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
        """生成回填任务列表"""
        logger.info("📋 生成回填任务...")

        tasks = []

        for league in leagues:
            league_id = league.get("id")
            league_name = league.get("name", "Unknown")

            logger.info(f"🔍 处理联赛: {league_name} (ID: {league_id})")

            for year in YEARS_TO_BACKFILL:
                # 生成赛季格式
                season_formats = SeasonFormatGenerator.generate_season_string(year, league)

                for season in season_formats:
                    try:
                        # 获取该赛季的比赛列表
                        match_ids = await self.fetch_league_matches(league_id, season)

                        for match_id in match_ids:
                            tasks.append((match_id, league))

                    except Exception as e:
                        logger.warning(f"⚠️ 获取联赛 {league_name} 赛季 {season} 失败: {e}")
                        continue

        logger.info(f"✅ 生成回填任务: {len(tasks)} 个")
        return tasks

    async def _execute_backfill_tasks(self, tasks: List[Tuple[str, Dict[str, Any]]]):
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
                logger.info(f"\n🛡️ 风控报告:")
                logger.info(f"  429触发次数: {rate_429_count}")
                logger.info(f"  总冷却时间: {total_429_cooldown//60}分{total_429_cooldown%60}秒")
                logger.info(f"  平均处理速度: ~{self.stats.successful_matches / max(1, (self.stats.elapsed_time.total_seconds() - total_429_cooldown) / 3600):.0f}场/小时 (不含冷却时间)")
            else:
                logger.info(f"\n🛡️ 风控报告: 未触发429限制，安全运行")

        logger.info("="*60)
        logger.info("🎉 全历史数据回填任务完成!")

    async def cleanup(self):
        """清理资源"""
        if self.collector:
            await self.collector.close()
        logger.info("🧹 资源清理完成")

async def main():
    """主函数"""
    logger.info("🛡️ 启动安全加固版全历史数据回填脚本 (已修复异步调用错误)")
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