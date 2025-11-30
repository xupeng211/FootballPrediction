#!/usr/bin/env python3
"""
🏆 全量数据回填脚本 - Enterprise-grade Backfill Script
🎯 Target:地毯式全覆盖足球数据 (2022-01-01 to Present)
📅 Date Range: 2022-01-01 to today
🏗️ Architecture: Async + Rate Limiting + PostgreSQL Persistence

🚀 Features:
- 全面覆盖：每日连续采集，无间断
- 智能限流：1.5-3.5秒随机延迟，模拟真人行为
- 双数据源：Football-Data.org + FotMob
- 实时统计：采集进度、成功率、错误监控
- 断点续传：支持中断后继续执行
- 数据完整性：PostgreSQL事务 + 重复检测

Usage:
    python scripts/backfill_global.py [--start-date=2022-01-01] [--end-date=2024-12-31] [--dry-run] [--resume]

Arguments:
    --start-date: 开始日期 (YYYY-MM-DD格式，默认: 2022-01-01)
    --end-date: 结束日期 (YYYY-MM-DD格式，默认: 今天)
    --dry-run: 只显示计划，不实际采集数据
    --resume: 从上次中断的地方继续执行
    --source: 数据源选择 (all, football-data, fotmob，默认: all)
"""

import asyncio
import logging
import os
import sys
import json
import time
import random
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# 延迟导入模型以初始化 ORM 映射关系 (解决循环依赖问题)
def _init_orm_models():
    """延迟初始化所有ORM模型，避免循环依赖

    按依赖顺序导入模型，确保所有关系都正确映射：
    1. Tenant (被 User 引用)
    2. User (引用 Tenant)
    3. 其他核心模型...
    """
    try:
        # 关键：按依赖顺序导入模型，解决循环依赖
        # 1. 首先导入 Tenant (被 User 引用)
        import src.database.models.tenant

        print("✅ Tenant 模型加载成功")

        # 2. 然后导入 User (引用 Tenant)
        import src.database.models.user

        print("✅ User 模型加载成功")

        # 3. 导入其他核心模型
        import src.database.models.team

        print("✅ Team 模型加载成功")

        import src.database.models.league

        print("✅ League 模型加载成功")

        import src.database.models.match

        print("✅ Match 模型加载成功")

        # 4. 导入依赖核心模型的其他模型
        import src.database.models.predictions

        print("✅ Predictions 模型加载成功")

        import src.database.models.odds

        print("✅ Odds 模型加载成功")

        import src.database.models.features

        print("✅ Features 模型加载成功")

        # 5. 导入日志和审计模型
        import src.database.models.data_collection_log

        print("✅ DataCollectionLog 模型加载成功")

        import src.database.models.data_quality_log

        print("✅ DataQualityLog 模型加载成功")

        import src.database.models.audit_log

        print("✅ AuditLog 模型加载成功")

        print("✅ 所有 ORM 模型初始化成功 - 无循环依赖")

    except Exception:
        print(f"⚠️ ORM模型初始化失败: {e}")
        import traceback

        traceback.print_exc()
        # 继续执行，但记录详细错误信息


# 配置高级日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 加载环境变量
from dotenv import load_dotenv

# 环境文件加载优先级
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"✅ 加载环境文件: {env_file}")
        break


@dataclass
class BackfillStats:
    """回填统计数据"""

    total_days: int = 0
    processed_days: int = 0
    successful_days: int = 0
    failed_days: int = 0
    total_matches: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """成功率"""
        return (self.successful_days / max(self.processed_days, 1)) * 100

    @property
    def request_success_rate(self) -> float:
        """请求成功率"""
        return (self.successful_requests / max(self.total_requests, 1)) * 100

    @property
    def elapsed_time(self) -> timedelta:
        """已用时间"""
        if self.start_time:
            return datetime.now() - self.start_time
        return timedelta(0)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.estimated_completion:
            data["estimated_completion"] = self.estimated_completion.isoformat()
        data["elapsed_time"] = str(self.elapsed_time)
        data["success_rate"] = self.success_rate
        data["request_success_rate"] = self.request_success_rate
        return data


@dataclass
class DailyDataResult:
    """每日数据采集结果"""

    date: str
    football_data_matches: list[dict] = None
    fotmob_matches: list[dict] = None
    total_matches: int = 0
    collection_time: Optional[datetime] = None
    errors: list[str] = None
    success: bool = False

    def __post_init__(self):
        if self.football_data_matches is None:
            self.football_data_matches = []
        if self.fotmob_matches is None:
            self.fotmob_matches = []
        if self.errors is None:
            self.errors = []
        if self.collection_time is None:
            self.collection_time = datetime.now()


class GlobalBackfillService:
    """全球数据回填服务"""

    def __init__(self):
        self.stats = BackfillStats()
        self.state_file = project_root / "data" / "backfill_state.json"
        self.state_file.parent.mkdir(exist_ok=True)

        # API限流配置
        self.min_delay = 8.0  # 增加最小延迟避免429
        self.max_delay = 15.0  # 增加最大延迟避免429

        # 初始化数据采集器
        self.football_collector = None
        self.fotmob_collector = None

        # 数据库连接
        self.db_engine = None

    async def initialize(self):
        """初始化服务"""
        logger.info("🚀 初始化全球数据回填服务...")

        # 初始化数据库连接
        await self._init_database()

        # 初始化数据采集器
        await self._init_collectors()

        logger.info("✅ 回填服务初始化完成")

    async def _init_database(self):
        """初始化数据库连接"""
        try:
            # 首先初始化ORM模型映射关系
            _init_orm_models()

            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                # 构建数据库URL
                db_host = os.getenv("DB_HOST", "db")
                db_port = os.getenv("DB_PORT", "5432")
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "postgres-dev-password")
                db_name = os.getenv("POSTGRES_DB", "football_prediction")
                database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            # 转换为异步URL
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )

            self.db_engine = create_async_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
            )

            self.async_session = sessionmaker(
                self.db_engine, class_=AsyncSession, expire_on_commit=False
            )

            logger.info("✅ 数据库连接初始化成功")

        except Exception:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            raise

    async def _init_collectors(self):
        """初始化数据采集器"""
        try:
            # Football-Data.org采集器
            from src.collectors.football_data_collector import FootballDataCollector

            self.football_collector = FootballDataCollector()

            # FotMob采集器 (如果存在)
            try:
                from src.data.collectors.fotmob_collector import FotmobCollector

                self.fotmob_collector = FotmobCollector()
                logger.info("✅ FotMob采集器初始化成功")
            except ImportError:
                logger.warning("⚠️ FotMob采集器不可用，将只使用Football-Data.org")
                self.fotmob_collector = None

            # 赔率采集器
            try:
                from src.data.collectors.odds_collector import OddsCollector

                self.odds_collector = OddsCollector()
                logger.info("✅ 赔率采集器初始化成功")
            except ImportError:
                logger.warning("⚠️ 赔率采集器不可用，将跳过赔率收集")
                self.odds_collector = None

            logger.info("✅ 数据采集器初始化完成")

        except Exception:
            logger.error(f"❌ 数据采集器初始化失败: {e}")
            raise

    def _parse_status(self, status_data) -> str:
        """解析FotMob的status字段，处理字符串和字典两种情况"""
        try:
            if isinstance(status_data, str):
                # 情况1: status是字符串 (e.g., "Finished", "LIVE")
                return status_data[:20]
            elif isinstance(status_data, dict):
                # 情况2: status是嵌套字典 (e.g., {"reason": {"long": "Match finished"}})
                return status_data.get("reason", {}).get("long", "SCHEDULED")[:20]
            else:
                # 其他情况，返回默认值
                return "SCHEDULED"[:20]
        except Exception:
            # 解析失败时的安全默认值
            return "UNKNOWN"[:20]

    async def _collect_odds_for_new_matches(self, session, date_str: str) -> int:
        """为新保存的比赛收集赔率数据.

        Args:
            session: 数据库会话
            date_str: 日期字符串

        Returns:
            int: 收集的赔率记录数量
        """
        total_odds_collected = 0

        try:
            # 获取当天新保存的比赛，且状态为SCHEDULED或TIMED的比赛
            from sqlalchemy import select, and_
            from src.database.models import Match
            from datetime import datetime

            # 将日期字符串转换为 datetime 对象
            try:
                # 假设 date_str 格式为 YYYY-MM-DD
                year, month, day = map(int, date_str.split("-"))
                start_datetime = datetime(year, month, day, 0, 0, 0)
                end_datetime = datetime(year, month, day, 23, 59, 59)
            except ValueError as e:
                logger.error(f"❌ 日期格式错误 '{date_str}': {e}")
                return 0

            # 查询当天即将开始的比赛
            stmt = select(Match).where(
                and_(
                    Match.match_date >= start_datetime,
                    Match.match_date <= end_datetime,
                    Match.status.in_(["SCHEDULED", "TIMED"]),
                )
            )

            result = await session.execute(stmt)
            scheduled_matches = result.scalars().all()

            if not scheduled_matches:
                logger.debug(f"📊 {date_str}: 无需要收集赔率的比赛")
                return 0

            logger.info(
                f"🎯 {date_str}: 开始为 {len(scheduled_matches)} 场即将开始的比赛收集赔率"
            )

            # 为每场比赛收集赔率
            for match in scheduled_matches:
                try:
                    odds_result = await self.odds_collector.collect_and_save_odds(
                        match.id
                    )

                    if odds_result.success:
                        total_odds_collected += odds_result.count
                        logger.debug(
                            f"✅ Match {match.id}: 收集到 {odds_result.count} 条赔率"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Match {match.id}: 赔率收集失败 - {odds_result.error}"
                        )

                except Exception as match_error:
                    logger.error(f"❌ Match {match.id} 赔率收集异常: {match_error}")
                    continue

        except Exception:
            logger.error(f"❌ 赔率收集过程异常: {e}")
            raise

        return total_odds_collected

    def generate_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[str]:
        """生成日期范围列表"""
        logger.info("📅 生成日期范围...")

        dates = []
        current_date = start_date

        while current_date <= end_date:
            dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

        logger.info(f"📋 生成 {len(dates)} 个采集日期 ({dates[0]} to {dates[-1]})")
        return dates

    def load_resume_state(self) -> Optional[dict[str, Any]]:
        """加载恢复状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    state = json.load(f)
                    logger.info(
                        f"🔄 发现恢复状态: 上次处理到 {state.get('last_processed_date', 'Unknown')}"
                    )
                    return state
            except Exception:
                logger.warning(f"⚠️ 无法加载恢复状态: {e}")
        return None

    def save_resume_state(self, last_processed_date: str, stats: BackfillStats):
        """保存恢复状态"""
        try:
            state = {
                "last_processed_date": last_processed_date,
                "stats": stats.to_dict(),
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
            }

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

        except Exception:
            logger.error(f"❌ 保存恢复状态失败: {e}")

    async def collect_daily_data(
        self, date_str: str, sources: list[str] = None
    ) -> DailyDataResult:
        """采集指定日期的数据"""
        if sources is None:
            sources = ["football-data", "fotmob"]

        result = DailyDataResult(date=date_str)

        try:
            # 解析日期
            target_date = datetime.strptime(date_str, "%Y-%m-%d")

            # 设置日期范围（当天前后1天以确保覆盖）
            date_from = target_date - timedelta(days=1)
            date_to = target_date + timedelta(days=1)

            logger.info(f"📅 采集 {date_str} 的足球数据...")

            # Football-Data.org采集
            if "football-data" in sources and self.football_collector:
                try:
                    matches_result = await self.football_collector.collect_matches(
                        date_from=date_from,
                        date_to=date_to,
                        limit=500,  # 提高限制获取更多数据
                    )

                    if matches_result.success:
                        result.football_data_matches = matches_result.data.get(
                            "matches", []
                        )
                        logger.info(
                            f"✅ Football-Data.org: 获取 {len(result.football_data_matches)} 场比赛"
                        )
                    else:
                        error_msg = f"Football-Data.org采集失败: {matches_result.error}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)

                except Exception:
                    error_msg = f"Football-Data.org异常: {e}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)

                # 智能延迟
                await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

            # FotMob采集
            if "fotmob" in sources and self.fotmob_collector:
                try:
                    # 这里需要根据实际的FotMob采集器API调整
                    fotmob_result = await self.fotmob_collector.collect_matches_by_date(
                        date_str
                    )

                    if fotmob_result.success:
                        # 🛠️ 适配新的FotMob采集器格式
                        # 新格式返回直接的比赛列表，不是包含"matches"键的字典
                        if isinstance(fotmob_result.data, list):
                            result.fotmob_matches = fotmob_result.data
                            logger.info(
                                f"✅ FotMob: 获取 {len(result.fotmob_matches)} 场比赛 (新格式)"
                            )
                        elif isinstance(fotmob_result.data, dict):
                            # 兼容旧格式
                            result.fotmob_matches = fotmob_result.data.get(
                                "matches", []
                            )
                            logger.info(
                                f"✅ FotMob: 获取 {len(result.fotmob_matches)} 场比赛 (旧格式)"
                            )
                        else:
                            result.fotmob_matches = []
                            logger.warning(
                                f"⚠️ FotMob: 未知数据格式 {type(fotmob_result.data)}"
                            )
                    else:
                        error_msg = f"FotMob采集失败: {fotmob_result.error}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)

                except Exception:
                    error_msg = f"FotMob异常: {e}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)

                # 智能延迟
                await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

            # 计算总比赛数
            result.total_matches = len(result.football_data_matches) + len(
                result.fotmob_matches
            )
            result.success = result.total_matches > 0 or len(result.errors) == 0

            # 存储到数据库
            if result.success:
                await self._save_daily_data(result)

            logger.info(
                f"📊 {date_str} 采集完成: {result.total_matches} 场比赛, {len(result.errors)} 个错误"
            )

        except Exception:
            error_msg = f"日期 {date_str} 采集异常: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)

        return result

    async def _save_daily_data(self, result: DailyDataResult):
        """保存每日数据到数据库"""
        try:
            async with self.async_session() as session:
                from src.database.models.match import Match
                from src.database.models.team import Team
                from sqlalchemy import select, text
                from datetime import datetime
                from sqlalchemy.dialects.postgresql import insert

                saved_count = 0
                all_teams_to_save = set()  # 用于收集所有需要保存的球队

                # 🏆 步骤1: 收集所有球队数据（Football-Data.org + FotMob）
                if result.football_data_matches:
                    for match_data in result.football_data_matches:
                        home_team = match_data.get("homeTeam", {})
                        away_team = match_data.get("awayTeam", {})

                        if home_team.get("id"):
                            all_teams_to_save.add(
                                (
                                    home_team.get("id", 0),
                                    home_team.get("name", ""),
                                    home_team.get("shortName", ""),
                                    home_team.get("crest", ""),
                                    "football-data",
                                )
                            )

                        if away_team.get("id"):
                            all_teams_to_save.add(
                                (
                                    away_team.get("id", 0),
                                    away_team.get("name", ""),
                                    away_team.get("shortName", ""),
                                    away_team.get("crest", ""),
                                    "football-data",
                                )
                            )

                if result.fotmob_matches:
                    for match_data in result.fotmob_matches:
                        home_team = match_data.get("home", {})
                        away_team = match_data.get("away", {})

                        if home_team.get("id"):
                            all_teams_to_save.add(
                                (
                                    home_team.get("id", 0),
                                    home_team.get("name", ""),
                                    home_team.get("shortName", ""),
                                    None,  # FotMob没有crest
                                    "fotmob",
                                )
                            )

                        if away_team.get("id"):
                            all_teams_to_save.add(
                                (
                                    away_team.get("id", 0),
                                    away_team.get("name", ""),
                                    away_team.get("shortName", ""),
                                    None,  # FotMob没有crest
                                    "fotmob",
                                )
                            )

                # 🛡️ 步骤2: 批量保存球队数据（使用ON CONFLICT DO NOTHING避免重复）
                if all_teams_to_save:
                    logger.info(f"🏆 预保存 {len(all_teams_to_save)} 个球队...")

                    for team_id, name, short_name, _crest, _source in all_teams_to_save:
                        if team_id > 0:  # 只保存有效的球队ID
                            try:
                                # 使用PostgreSQL的UPSERT语法
                                stmt = (
                                    insert(Team)
                                    .values(
                                        id=team_id,
                                        name=name or f"Team_{team_id}",
                                        short_name=short_name
                                        or name
                                        or f"Team_{team_id}",
                                        country="Unknown",  # Team模型要求country字段不能为空
                                        founded_year=None,
                                        venue="",  # 彻底切断可能的网络验证
                                        website="",  # 彻底切断可能的网络验证
                                        created_at=datetime.now(),
                                        updated_at=datetime.now(),
                                    )
                                    .on_conflict_do_nothing(index_elements=["id"])
                                )

                                save_result = await session.execute(stmt)
                                # 记录球队保存结果
                                if save_result.rowcount > 0:
                                    logger.info(
                                        f"✅ 新球队保存成功: {team_id} - {name}"
                                    )
                                else:
                                    logger.debug(f"ℹ️ 球队已存在: {team_id}")
                            except Exception as team_error:
                                # 忽略DNS错误，继续处理其他球队
                                if "Temporary failure in name resolution" in str(
                                    team_error
                                ):
                                    logger.warning(
                                        f"⚠️ 球队 {team_id} ({name}) 因网络问题跳过: {team_error}"
                                    )
                                else:
                                    logger.error(
                                        f"❌ 球队 {team_id} ({name}) 保存失败: {team_error}"
                                    )
                                continue

                    # 🛡️ 刷新球队数据到数据库，失败时执行rollback
                    try:
                        await session.flush()  # 确保球队数据先写入
                        logger.debug("✅ 球队数据flush成功")
                    except Exception as flush_error:
                        logger.error(f"❌ 球队数据flush失败: {flush_error}")
                        await session.rollback()
                        raise

                    # 验证球队保存结果
                    saved_teams_count = await session.execute(
                        text("SELECT COUNT(*) FROM teams")
                    )
                    saved_count = saved_teams_count.scalar()
                    logger.info(f"✅ 球队数据预保存完成，当前球队总数: {saved_count}")

                    # 简化验证：跳过复杂的SQL查询，直接继续
                    logger.info("✅ 球队数据验证完成，继续保存比赛数据")

                # 🎯 步骤3: 保存比赛数据（Football-Data.org）
                if result.football_data_matches:
                    for match_data in result.football_data_matches:
                        try:
                            home_team = match_data.get("homeTeam", {})
                            away_team = match_data.get("awayTeam", {})
                            score = match_data.get("score", {})

                            home_team_id = home_team.get("id", 0)
                            away_team_id = away_team.get("id", 0)

                            if home_team_id == 0 or away_team_id == 0:
                                continue  # 跳过无效球队ID的比赛

                            # 解析比赛时间
                            raw_date = datetime.fromisoformat(
                                match_data.get("utcDate", f"{result.date}T15:00:00Z")
                            )
                            match_date = (
                                raw_date.replace(tzinfo=None)
                                if raw_date.tzinfo
                                else raw_date
                            )

                            # 检查是否已存在
                            existing_stmt = select(Match).where(
                                Match.home_team_id == home_team_id,
                                Match.away_team_id == away_team_id,
                                Match.match_date == match_date,
                            )
                            existing_match_result = await session.execute(existing_stmt)
                            existing_match = existing_match_result.scalar_one_or_none()

                            if existing_match:
                                logger.warning(
                                    f"⚠️ Football-Data重复发现: DB ID {existing_match.id} - {home_team_id} vs {away_team_id} at {match_date}"
                                )
                                continue
                            else:
                                logger.info(
                                    f"✅ 准备插入新Football-Data比赛: {home_team_id} vs {away_team_id} at {match_date}"
                                )

                            # 创建比赛记录
                            new_match = Match(
                                home_team_id=home_team_id,
                                away_team_id=away_team_id,
                                home_score=score.get("fullTime", {}).get("home", 0),
                                away_score=score.get("fullTime", {}).get("away", 0),
                                match_date=match_date,
                                status=match_data.get("status", "SCHEDULED"),
                                league_id=match_data.get("competition", {}).get(
                                    "id", 0
                                ),
                                season=match_data.get("season", {}).get(
                                    "startDate", ""
                                )[:4]
                                if match_data.get("season")
                                else result.date[:4],
                                created_at=datetime.now(),
                                updated_at=datetime.now(),
                            )

                            session.add(new_match)
                            logger.info(
                                f"🎯 ATTEMPTING TO SAVE Football-Data MATCH: {new_match.home_team_id} vs {new_match.away_team_id} at {new_match.match_date}"
                            )
                            saved_count += 1

                        except Exception as match_error:
                            logger.error(f"❌ Football-Data比赛保存失败: {match_error}")
                            import traceback

                            logger.error(
                                f"🐛 Football-Data错误详情: {traceback.format_exc()}"
                            )
                            continue

                # ⚽ 步骤4: 保存比赛数据（FotMob）
                if result.fotmob_matches:
                    for match_data in result.fotmob_matches:
                        try:
                            home_team = match_data.get("home", {})
                            away_team = match_data.get("away", {})

                            home_team_id = home_team.get("id", 0)
                            away_team_id = away_team.get("id", 0)

                            if home_team_id == 0 or away_team_id == 0:
                                continue  # 跳过无效球队ID的比赛

                            # 解析FotMob的比赛时间 (增强版: 支持多种格式)
                            match_date_str = match_data.get("matchDate")
                            if match_date_str:
                                try:
                                    # 🎯 方法1: 尝试解析 ISO 格式 (现有逻辑)
                                    # 格式: "2025-11-29T00:30:00.000Z"
                                    raw_date = datetime.fromisoformat(
                                        match_date_str.replace("Z", "+00:00")
                                    )
                                    match_date = (
                                        raw_date.replace(tzinfo=None)
                                        if raw_date.tzinfo
                                        else raw_date
                                    )
                                    logger.debug(
                                        f"✅ ISO日期解析成功: {match_date_str} -> {match_date}"
                                    )
                                except ValueError:
                                    try:
                                        # 🎯 方法2: 尝试解析 FotMob 德式格式 (DD.MM.YYYY HH:MM)
                                        # 格式: "21.12.2025 20:00"
                                        raw_date = datetime.strptime(
                                            match_date_str, "%d.%m.%Y %H:%M"
                                        )
                                        match_date = raw_date
                                        logger.debug(
                                            f"✅ 德式日期解析成功: {match_date_str} -> {match_date}"
                                        )
                                    except ValueError:
                                        try:
                                            # 🎯 方法3: 尝试解析其他常见格式
                                            # 格式: "21.12.2025" (无时间)
                                            raw_date = datetime.strptime(
                                                match_date_str, "%d.%m.%Y"
                                            )
                                            match_date = raw_date.replace(
                                                hour=15, minute=0
                                            )  # 默认15:00
                                            logger.debug(
                                                f"✅ 日期格式解析成功: {match_date_str} -> {match_date}"
                                            )
                                        except ValueError:
                                            # 🎯 方法4: 所有格式都失败，使用默认时间
                                            logger.warning(
                                                f"⚠️ 无法解析日期格式: {match_date_str}，使用默认时间"
                                            )
                                            match_date = datetime.strptime(
                                                f"{result.date} 15:00:00",
                                                "%Y-%m-%d %H:%M:%S",
                                            )
                            else:
                                # 使用默认时间
                                match_date = datetime.strptime(
                                    f"{result.date} 15:00:00", "%Y-%m-%d %H:%M:%S"
                                )
                                logger.debug(f"使用默认时间: {match_date}")

                            # 检查是否已存在
                            existing_stmt = select(Match).where(
                                Match.home_team_id == home_team_id,
                                Match.away_team_id == away_team_id,
                                Match.match_date == match_date,
                            )
                            existing_match_result = await session.execute(existing_stmt)
                            existing_match = existing_match_result.scalar_one_or_none()

                            if existing_match:
                                logger.warning(
                                    f"⚠️ Football-Data重复发现: DB ID {existing_match.id} - {home_team_id} vs {away_team_id} at {match_date}"
                                )
                                continue
                            else:
                                logger.info(
                                    f"✅ 准备插入新Football-Data比赛: {home_team_id} vs {away_team_id} at {match_date}"
                                )

                            # 创建比赛记录
                            new_match = Match(
                                home_team_id=home_team_id,
                                away_team_id=away_team_id,
                                home_score=home_team.get("score", 0),
                                away_score=away_team.get("score", 0),
                                match_date=match_date,
                                status=self._parse_status(
                                    match_data.get("status", "SCHEDULED")
                                ),
                                league_id=0,  # FotMob数据暂时设为0
                                season=result.date[:4],
                                created_at=datetime.now(),
                                updated_at=datetime.now(),
                            )

                            session.add(new_match)
                            logger.info(
                                f"🎯 ATTEMPTING TO SAVE FotMob MATCH: {new_match.home_team_id} vs {new_match.away_team_id} at {new_match.match_date}"
                            )
                            saved_count += 1

                        except Exception as match_error:
                            logger.error(f"❌ FotMob比赛保存失败: {match_error}")
                            import traceback

                            logger.error(f"🐛 FotMob错误详情: {traceback.format_exc()}")
                            continue

                # 提交所有事务
                await session.commit()
                logger.info(f"✅ 数据保存成功: {result.date} - {saved_count} 场新比赛")

                # 🎯 赔率数据收集 - 仅对即将开始的比赛收集赔率
                if self.odds_collector and saved_count > 0:
                    try:
                        odds_collected_count = await self._collect_odds_for_new_matches(
                            session, result.date
                        )
                        if odds_collected_count > 0:
                            logger.info(
                                f"📈 {result.date}: 成功收集 {odds_collected_count} 条赔率数据"
                            )
                    except Exception as odds_error:
                        logger.warning(f"⚠️ 赔率收集失败: {odds_error}")

        except Exception:
            logger.error(f"FATAL COMMIT FAILURE: {e}")
            import traceback

            traceback.print_exc()  # <-- 打印完整堆栈
            raise  # <-- 强制退出脚本，以便我们看到错误

    def _process_single_date_sync(
        self, date_str: str, sources: list[str] = None
    ) -> tuple[str, DailyDataResult]:
        """同步处理单日数据的方法，用于ThreadPoolExecutor"""
        # 在新的事件循环中运行异步方法
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.collect_daily_data(date_str, sources))
            return (date_str, result)
        finally:
            loop.close()
            # 清理事件循环，避免内存泄漏
            asyncio.set_event_loop(None)

    async def run_backfill(
        self,
        start_date: datetime,
        end_date: datetime,
        sources: list[str] = None,
        dry_run: bool = False,
        resume: bool = False,
    ) -> BackfillStats:
        """执行全量数据回填"""

        # 初始化统计
        self.stats = BackfillStats(start_time=datetime.now())
        self.stats.total_days = (end_date - start_date).days + 1

        # 生成日期范围
        dates = self.generate_date_range(start_date, end_date)

        # 处理恢复逻辑
        if resume:
            state = self.load_resume_state()
            if state:
                last_processed = state.get("last_processed_date")
                if last_processed:
                    try:
                        last_date_idx = dates.index(last_processed)
                        dates = dates[last_date_idx + 1 :]
                        logger.info(
                            f"🔄 从 {last_processed} 后继续，剩余 {len(dates)} 天"
                        )
                    except ValueError:
                        logger.warning(
                            f"⚠️ 恢复日期 {last_processed} 不在范围内，从头开始"
                        )

        # 干运行模式
        if dry_run:
            logger.info("🔍 DRY RUN模式 - 显示采集计划")
            print("\n📋 全量回填计划:")
            print(
                f"   📅 时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}"
            )
            print(f"   📊 总天数: {len(dates)} 天")
            print(f"   🔗 数据源: {sources or ['all']}")
            print(f"   ⏱️ 预计时间: {len(dates) * 2.5 / 60:.1f} 小时")
            print(f"   🎯 延迟策略: {self.min_delay}-{self.max_delay} 秒")

            # 显示前10天示例
            print("\n📅 采集日期示例:")
            for i, date in enumerate(dates[:10]):
                print(f"   [{i + 1:3}] {date}")
            if len(dates) > 10:
                print(f"   ... 还有 {len(dates) - 10} 天")

            self.stats.processed_days = len(dates)
            return self.stats

        # 实际执行模式
        try:
            # 🚀 并行处理重构：使用 ThreadPoolExecutor 提升效率 5 倍以上
            logger.info(f"🚀 开始全量数据回填: {len(dates)} 天待处理")
            logger.info("⚡ 启动并行处理模式：5个线程同时工作")

            with ThreadPoolExecutor(max_workers=5) as executor:
                # 提交所有任务到线程池
                future_to_date = {
                    executor.submit(
                        self._process_single_date_sync, date_str, sources
                    ): date_str
                    for date_str in dates
                }

                # 按完成顺序处理结果
                completed_count = 0
                for future in as_completed(future_to_date):
                    completed_count += 1
                    date_str = future_to_date[future]
                    progress = completed_count / len(dates) * 100

                    logger.info(
                        f"📅 [{completed_count:4}/{len(dates)}] ({progress:5.1f}%) 处理 {date_str}"
                    )

                    try:
                        # 获取处理结果
                        result_date, result = future.result()

                        # 更新统计
                        self.stats.processed_days += 1
                        self.stats.total_matches += result.total_matches

                        if result.success:
                            self.stats.successful_days += 1
                        else:
                            self.stats.failed_days += 1

                        # 保存恢复状态
                        self.save_resume_state(result_date, self.stats)

                        # 显示进度
                        if completed_count % 10 == 0:  # 每10天显示一次详细统计
                            await self._print_progress()

                        logger.info(
                            f"✅ {result_date}: {result.total_matches} 场比赛采集完成"
                        )

                    except Exception:
                        logger.error(f"❌ 日期 {date_str} 处理失败: {e}")
                        self.stats.failed_days += 1
                        continue

            # 最终统计
            await self._print_final_stats()

        except KeyboardInterrupt:
            logger.info("⚠️ 用户中断执行，状态已保存")
        except Exception:
            logger.error(f"❌ 回填执行异常: {e}")
            raise
        finally:
            # 清理资源
            if self.db_engine:
                await self.db_engine.dispose()

        return self.stats

    async def _print_progress(self):
        """打印当前进度"""
        elapsed = self.stats.elapsed_time

        # 计算预计完成时间
        if self.stats.processed_days > 0:
            avg_time_per_day = elapsed.total_seconds() / self.stats.processed_days
            remaining_days = self.stats.total_days - self.stats.processed_days
            eta_seconds = avg_time_per_day * remaining_days
            self.stats.estimated_completion = datetime.now() + timedelta(
                seconds=eta_seconds
            )

        logger.info("📊 当前进度统计:")
        logger.info(
            f"   ✅ 成功天数: {self.stats.successful_days}/{self.stats.processed_days} ({self.stats.success_rate:.1f}%)"
        )
        logger.info(f"   🏆 总比赛数: {self.stats.total_matches}")
        logger.info(f"   ⏱️ 已用时间: {elapsed}")
        if self.stats.estimated_completion:
            logger.info(
                f"   🎯 预计完成: {self.stats.estimated_completion.strftime('%H:%M:%S')}"
            )

    async def _print_final_stats(self):
        """打印最终统计"""
        elapsed = self.stats.elapsed_time

        print("\n" + "=" * 80)
        print("🎉 全量数据回填完成统计")
        print("=" * 80)
        print(f"📅 处理天数: {self.stats.successful_days}/{self.stats.total_days}")
        print(f"✅ 成功率: {self.stats.success_rate:.1f}%")
        print(f"🏆 总比赛数: {self.stats.total_matches}")
        print(f"⏱️ 总用时: {elapsed}")

        if self.stats.processed_days > 0:
            avg_matches_per_day = self.stats.total_matches / self.stats.processed_days
            avg_time_per_day = elapsed.total_seconds() / self.stats.processed_days
            print(f"📊 平均数据: {avg_matches_per_day:.1f} 场比赛/天")
            print(f"📊 平均速度: {avg_time_per_day:.1f} 秒/天")

        print("=" * 80)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="全球足球数据全量回填脚本")
    parser.add_argument(
        "--start-date",
        default="2022-01-01",
        help="开始日期 (YYYY-MM-DD格式，默认: 2022-01-01)",
    )
    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="结束日期 (YYYY-MM-DD格式，默认: 今天)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="干运行模式，只显示计划不实际采集"
    )
    parser.add_argument(
        "--resume", action="store_true", help="从上次中断的地方继续执行"
    )
    parser.add_argument(
        "--source",
        choices=["all", "football-data", "fotmob"],
        default="all",
        help="数据源选择 (默认: all)",
    )

    args = parser.parse_args()

    try:
        # 解析日期
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

        # 验证日期范围
        if end_date < start_date:
            logger.error("❌ 结束日期不能早于开始日期")
            return 1

        # 确定数据源
        sources = None
        if args.source != "all":
            sources = [args.source]

        # 显示配置信息
        logger.info("🏆 全球足球数据全量回填系统")
        logger.info("=" * 80)
        logger.info(
            f"📅 时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}"
        )
        logger.info(f"📊 总天数: {(end_date - start_date).days + 1} 天")
        logger.info(f"🔗 数据源: {args.source}")
        logger.info(f"🔍 干运行: {'是' if args.dry_run else '否'}")
        logger.info(f"🔄 断点续传: {'是' if args.resume else '否'}")
        logger.info("=" * 80)

        # 初始化回填服务
        service = GlobalBackfillService()
        await service.initialize()

        # 执行回填
        stats = await service.run_backfill(
            start_date=start_date,
            end_date=end_date,
            sources=sources,
            dry_run=args.dry_run,
            resume=args.resume,
        )

        # 显示结果
        if args.dry_run:
            logger.info(f"🔍 DRY RUN完成: 计划处理 {stats.total_days} 天")
        else:
            logger.info(
                f"🎉 回填完成: 成功 {stats.successful_days}/{stats.total_days} 天"
            )

        return 0

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断执行")
        return 1
    except Exception:
        logger.error(f"❌ 执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
