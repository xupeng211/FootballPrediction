#!/usr/bin/env python3
"""
全能采集器 (Master Collector) - 企业级自动化数据采集流水线
FootballPrediction Master Collector - Enterprise-grade Automated Pipeline

功能说明:
1. L1数据采集: 获取赛程索引底座数据
2. L2数据采集: 并发采集详细JSON数据
3. 自动特征提取: 完成后立即触发特征提取
4. 自愈机制: 自动重试和错误恢复
5. 幂等性: 支持断点续传

作者: FootballPrediction Team
版本: v3.0.0
日期: 2024-12-20
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime

import aiohttp
import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """流水线配置"""

    league_id: int = 47
    season: str = "2024/25"
    concurrent_limit: int = 3
    request_delay: float = 2.0
    retry_attempts: int = 3
    batch_size: int = 50
    auto_extract_features: bool = True


@dataclass
class PipelineStats:
    """流水线统计"""

    l1_matches_found: int = 0
    l1_matches_saved: int = 0
    l2_attempts: int = 0
    l2_successful: int = 0
    l2_failed: int = 0
    features_extracted: int = 0
    start_time: float = 0
    total_requests: int = 0


class MasterCollector:
    """全能采集器 - 企业级自动化数据采集流水线"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.stats = PipelineStats()
        self.semaphore = asyncio.Semaphore(config.concurrent_limit)

        # FotMob API Headers (最新版本)
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.fotmob.com/",
            "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "x-mas": "Q29udGVudC1UeXBlOiBhcHBsaWNhdGlvbi9qc29uOyBjaGFyc2V0PXV0Zi04",
            "x-foo": "aHR0cHM6Ly93d3cuZm90bW9iLmNvbS8=",
        }

        # 数据库连接池
        self.db_pool = None

    async def initialize(self):
        """初始化连接池"""
        self.db_pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            database="football_db",
            user="football_user",
            password="football_pass",
            min_size=2,
            max_size=10,
        )
        logger.info("✅ 数据库连接池初始化完成")

    async def cleanup(self):
        """清理资源"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("✅ 数据库连接池已关闭")

    async def get_database_connection(self) -> asyncpg.Connection:
        """获取数据库连接，支持重试"""
        for attempt in range(self.config.retry_attempts):
            try:
                if self.db_pool:
                    return await self.db_pool.acquire()
                else:
                    return await asyncpg.connect(
                        host="localhost",
                        port=5432,
                        database="football_db",
                        user="football_user",
                        password="football_pass",
                    )
            except Exception as e:
                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{self.config.retry_attempts}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(5**attempt)  # 指数退避
                else:
                    raise

    async def release_database_connection(self, conn: asyncpg.Connection):
        """释放数据库连接"""
        if self.db_pool:
            await self.db_pool.release(conn)

    async def collect_l1_data(self) -> bool:
        """L1数据采集: 获取赛程索引底座数据"""
        logger.info("🚀 开始L1数据采集...")

        url = f"https://www.fotmob.com/api/leagues?id={self.config.league_id}&type=league&season={self.config.season}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self.process_l1_data(data)
                    else:
                        logger.error(f"❌ L1数据采集失败: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ L1数据采集异常: {e}")
            return False

    async def process_l1_data(self, data: dict) -> bool:
        """处理L1数据并保存到数据库"""
        try:
            # FotMob API返回的数据结构: data.fixtures.allMatches
            fixtures = data.get("fixtures", {})
            matches = fixtures.get("allMatches", [])
            self.stats.l1_matches_found = len(matches)

            logger.info(f"📊 找到 {len(matches)} 场比赛")

            conn = await self.get_database_connection()
            try:
                saved_count = 0
                for match in matches:
                    # 提取比赛信息 (FotMob API结构)
                    external_id = str(match.get("id", ""))
                    home_team = match.get("home", {}).get("name", "")
                    away_team = match.get("away", {}).get("name", "")
                    match_time = match.get("status", {}).get("utcTime", "")
                    status = match.get("status", {}).get("reason", {}).get("short", "Fixture")
                    round_info = match.get("round", "")

                    if not all([external_id, home_team, away_team]):
                        continue

                    # 解析时间 (FotMob格式: 2023-08-11T19:00:00Z)
                    match_time_parsed = None
                    if match_time:
                        try:
                            # 直接解析ISO 8601格式
                            match_time_parsed = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
                        except Exception:
                            logger.warning(f"时间解析失败: {match_time}")

                    # 检查是否已存在
                    existing = await conn.fetchval("SELECT id FROM matches WHERE external_id = $1", external_id)

                    if existing:
                        logger.debug(f"⏭️ 比赛已存在: {external_id}")
                        continue

                    # 插入新记录
                    await conn.execute(
                        """
                        INSERT INTO matches (
                            external_id, league_name, season, match_time, status,
                            home_team, away_team, league_id, round_info,
                            collection_status, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending', NOW(), NOW())
                    """,
                        external_id,
                        "Premier League",
                        self.config.season,
                        match_time_parsed,
                        status,
                        home_team,
                        away_team,
                        str(self.config.league_id),
                        round_info,
                    )

                    saved_count += 1
                    self.stats.l1_matches_saved = saved_count

                logger.info(f"✅ L1数据保存完成: {saved_count}/{len(matches)} 场")
                return True

            finally:
                await self.release_database_connection(conn)

        except Exception as e:
            logger.error(f"❌ L1数据处理异常: {e}")
            return False

    async def get_pending_matches(self) -> list[dict]:
        """获取待采集L2数据的比赛"""
        conn = await self.get_database_connection()
        try:
            matches = await conn.fetch(
                """
                SELECT id, external_id, home_team, away_team, match_time
                FROM matches
                WHERE collection_status = 'pending'
                ORDER BY match_time
                LIMIT $1
            """,
                self.config.batch_size,
            )

            return [dict(match) for match in matches]
        finally:
            await self.release_database_connection(conn)

    async def collect_l2_batch(self) -> tuple[int, int]:
        """批量采集L2数据"""
        pending_matches = await self.get_pending_matches()

        if not pending_matches:
            return 0, 0

        logger.info(f"🎯 开始L2批量采集: {len(pending_matches)} 场比赛")

        tasks = []
        for match in pending_matches:
            task = self.process_single_l2_match(match)
            tasks.append(task)

        # 并发处理
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)

        return successful, failed

    async def process_single_l2_match(self, match: dict) -> bool:
        """处理单场比赛的L2采集"""
        async with self.semaphore:
            external_id = match["external_id"]
            home_team = match["home_team"]
            away_team = match["away_team"]

            self.stats.l2_attempts += 1

            try:
                # 采集L2数据
                l2_data = await self.fetch_l2_data(external_id)
                if not l2_data:
                    self.stats.l2_failed += 1
                    return False

                # 保存数据
                success = await self.save_l2_data(external_id, l2_data)

                if success:
                    self.stats.l2_successful += 1
                    logger.info(f"✅ {home_team} vs {away_team} (ID: {external_id}) - L2采集成功")
                else:
                    self.stats.l2_failed += 1

                return success

            except Exception as e:
                logger.error(f"❌ 处理比赛 {external_id} 异常: {e}")
                self.stats.l2_failed += 1
                return False

    async def fetch_l2_data(self, match_id: str) -> dict | None:
        """采集单场比赛的L2数据"""
        url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"

        try:
            await asyncio.sleep(self.config.request_delay)
            self.stats.total_requests += 1

            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"✅ 成功采集比赛 {match_id}")
                        return data
                    elif response.status == 404:
                        logger.warning(f"⚠️ 比赛 {match_id} 数据不存在 (404)")
                        return None
                    elif response.status == 429:
                        logger.warning("⚠️ 触发速率限制，等待10秒...")
                        await asyncio.sleep(10)
                        return await self.fetch_l2_data(match_id)
                    else:
                        logger.error(f"❌ 比赛 {match_id} 采集失败: HTTP {response.status}")
                        return None

        except TimeoutError:
            logger.error(f"❌ 比赛 {match_id} 请求超时")
            return None
        except Exception as e:
            logger.error(f"❌ 比赛 {match_id} 采集异常: {e}")
            return None

    async def save_l2_data(self, external_id: str, l2_data: dict) -> bool:
        """保存L2数据到数据库"""
        conn = await self.get_database_connection()
        try:
            l2_json = json.dumps(l2_data, ensure_ascii=False)

            # 使用事务确保数据一致性
            async with conn.transaction():
                # 检查并更新raw_match_data表
                existing = await conn.fetchval("SELECT id FROM raw_match_data WHERE external_id = $1", external_id)

                if existing:
                    await conn.execute(
                        """
                        UPDATE raw_match_data
                        SET raw_match_data = $1, updated_at = CURRENT_TIMESTAMP
                        WHERE external_id = $2
                    """,
                        l2_json,
                        external_id,
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO raw_match_data (external_id, raw_match_data, created_at, updated_at)
                        VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        external_id,
                        l2_json,
                    )

                # 更新matches表状态
                await conn.execute(
                    """
                    UPDATE matches
                    SET collection_status = 'completed',
                        l2_collected_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE external_id = $1
                """,
                    external_id,
                )

            return True

        except Exception as e:
            logger.error(f"❌ 保存L2数据失败 {external_id}: {e}")
            return False
        finally:
            await self.release_database_connection(conn)

    async def collect_l3_odds(self, match_id: str) -> bool:
        """采集L3赔率数据"""
        logger.debug(f"🎯 开始采集L3赔率数据: {match_id}")

        # 构建L3赔率API URL
        url = f"https://www.fotmob.com/api/data/matchOdds?matchId={match_id}&ccode3=SGP"

        try:
            await asyncio.sleep(self.config.request_delay)
            self.stats.total_requests += 1

            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        odds_data = await response.json()
                        logger.debug(f"✅ 成功采集赔率数据 {match_id}")
                        return await self.save_l3_odds_data(match_id, odds_data)
                    elif response.status == 404:
                        logger.warning(f"⚠️ 比赛 {match_id} 赔率数据不存在 (404)")
                        return False
                    elif response.status == 429:
                        logger.warning("⚠️ 触发速率限制，等待10秒...")
                        await asyncio.sleep(10)
                        return await self.collect_l3_odds(match_id)
                    else:
                        logger.error(f"❌ 比赛 {match_id} 赔率采集失败: HTTP {response.status}")
                        return False

        except TimeoutError:
            logger.error(f"❌ 比赛 {match_id} 赔率请求超时")
            return False
        except Exception as e:
            logger.error(f"❌ 比赛 {match_id} 赔率采集异常: {e}")
            return False

    async def save_l3_odds_data(self, external_id: str, odds_data: dict) -> bool:
        """保存L3赔率数据到数据库"""
        conn = await self.get_database_connection()
        try:
            odds_json = json.dumps(odds_data, ensure_ascii=False)

            # 使用事务确保数据一致性
            async with conn.transaction():
                # 更新raw_match_data表，添加L3赔率数据
                await conn.execute(
                    """
                    UPDATE raw_match_data
                    SET raw_odds_data = $1,
                        odds_data_source = 'fotmob_matchodds',
                        odds_collected_at = CURRENT_TIMESTAMP,
                        odds_parse_status = 'completed',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE external_id = $2
                """,
                    odds_json,
                    external_id,
                )

                # 更新matches表状态
                await conn.execute(
                    """
                    UPDATE matches
                    SET l2_collected_at = l2_collected_at,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE external_id = $1
                """,
                    external_id,
                )

            logger.info(f"✅ 成功保存赔率数据: {external_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存L3赔率数据失败 {external_id}: {e}")
            return False
        finally:
            await self.release_database_connection(conn)

    async def get_pending_l3_matches(self) -> list[dict]:
        """获取待采集L3赔率的比赛"""
        conn = await self.get_database_connection()
        try:
            matches = await conn.fetch(
                """
                SELECT id, external_id, home_team, away_team
                FROM matches
                WHERE collection_status = 'completed'
                AND EXISTS (
                    SELECT 1 FROM raw_match_data
                    WHERE external_id = matches.external_id
                    AND raw_match_data IS NOT NULL
                )
                AND NOT EXISTS (
                    SELECT 1 FROM raw_match_data
                    WHERE external_id = matches.external_id
                    AND raw_odds_data IS NOT NULL
                )
                ORDER BY match_time
                LIMIT $1
            """,
                self.config.batch_size,
            )

            return [dict(match) for match in matches]
        finally:
            await self.release_database_connection(conn)

    async def collect_l3_odds_batch(self) -> tuple[int, int]:
        """批量采集L3赔率数据"""
        pending_matches = await self.get_pending_l3_matches()

        if not pending_matches:
            return 0, 0

        logger.info(f"🎯 开始L3赔率批量采集: {len(pending_matches)} 场比赛")

        tasks = []
        for match in pending_matches:
            task = self.process_single_l3_match(match)
            tasks.append(task)

        # 并发处理
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)

        return successful, failed

    async def process_single_l3_match(self, match: dict) -> bool:
        """处理单场比赛的L3赔率采集"""
        async with self.semaphore:
            external_id = match["external_id"]
            home_team = match["home_team"]
            away_team = match["away_team"]

            try:
                # 采集L3赔率数据
                success = await self.collect_l3_odds(external_id)

                if success:
                    logger.info(f"✅ {home_team} vs {away_team} (ID: {external_id}) - L3赔率采集成功")
                else:
                    logger.warning(f"⚠️ {home_team} vs {away_team} (ID: {external_id}) - L3赔率采集失败")

                return success

            except Exception as e:
                logger.error(f"❌ 处理L3赔率比赛 {external_id} 异常: {e}")
                return False

    async def trigger_feature_extraction(self) -> bool:
        """触发特征提取"""
        if not self.config.auto_extract_features:
            logger.info("⏭️ 跳过自动特征提取")
            return True

        logger.info("🔄 触发特征提取...")

        try:
            # 调用最终收割特征提取器
            result = subprocess.run(
                [sys.executable, "scripts/final_harvest_extractor.py"], capture_output=True, text=True, timeout=1800
            )  # 30分钟超时

            if result.returncode == 0:
                logger.info("✅ 特征提取完成!")
                self.stats.features_extracted = 1
                return True
            else:
                logger.error(f"❌ 特征提取失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("⚠️ 特征提取超时")
            return False
        except Exception as e:
            logger.error(f"⚠️ 触发特征提取异常: {e}")
            return False

    async def run_automatic_pipeline(self) -> bool:
        """运行全自动流水线"""
        self.stats.start_time = time.time()

        logger.info("🚀 启动全能采集器自动化流水线")
        logger.info(f"⚙️ 配置: 联赛{self.config.league_id}, 赛季{self.config.season}")
        logger.info(f"🔧 并发数: {self.config.concurrent_limit}, 请求间隔: {self.config.request_delay}s")
        logger.info("=" * 80)

        try:
            # 步骤1: L1数据采集
            logger.info("📋 步骤1/4: L1索引数据采集...")
            l1_success = await self.collect_l1_data()
            if not l1_success:
                logger.error("❌ L1数据采集失败，流水线终止")
                return False

            # 步骤2: L2数据批量采集
            logger.info("📦 步骤2/4: L2详情数据批量采集...")

            total_l2_successful = 0
            total_l2_failed = 0
            batch_count = 0

            while True:
                successful, failed = await self.collect_l2_batch()

                if successful == 0 and failed == 0:
                    # 没有待处理的比赛
                    break

                total_l2_successful += successful
                total_l2_failed += failed
                batch_count += 1

                # 更新统计
                self.stats.l2_successful = total_l2_successful
                self.stats.l2_failed = total_l2_failed

                logger.info(f"📊 批次{batch_count}完成: ✅{successful} ❌{failed}")

                # 每10个批次报告进度
                if batch_count % 10 == 0:
                    await self.report_progress()

                # 批次间短暂休息
                await asyncio.sleep(1)

            # 步骤3: L3赔率数据批量采集
            logger.info("💰 步骤3/5: L3赔率数据批量采集...")

            total_l3_successful = 0
            total_l3_failed = 0
            batch_count = 0

            while True:
                successful, failed = await self.collect_l3_odds_batch()

                if successful == 0 and failed == 0:
                    # 没有待处理的比赛
                    break

                total_l3_successful += successful
                total_l3_failed += failed
                batch_count += 1

                logger.info(f"📊 L3批次{batch_count}完成: ✅{successful} ❌{failed}")

                # 每5个批次报告进度
                if batch_count % 5 == 0:
                    await self.report_progress()

                # 批次间短暂休息
                await asyncio.sleep(2)

            # 步骤4: 特征提取
            logger.info("🎯 步骤4/5: 自动特征提取...")
            feature_success = await self.trigger_feature_extraction()

            # 步骤5: 最终报告
            logger.info("📈 步骤5/5: 生成最终报告...")
            await self.generate_final_report()

            success = l1_success and (total_l2_successful > 0) and (total_l3_successful > 0) and feature_success

            if success:
                logger.info("🎉 全能采集器流水线执行成功!")
            else:
                logger.warning("⚠️ 流水线部分完成，请检查日志")

            return success

        except Exception as e:
            logger.error(f"❌ 流水线执行异常: {e}")
            return False

    async def report_progress(self):
        """汇报进度"""
        elapsed = time.time() - self.stats.start_time
        rate = self.stats.l2_attempts / elapsed if elapsed > 0 else 0

        print("\n" + "=" * 80)
        print(f"📊 全能采集器进度报告 - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        print(
            f"🏃 L2采集: {self.stats.l2_attempts} | ✅ 成功: {self.stats.l2_successful} | ❌ 失败: {self.stats.l2_failed}"
        )
        print(
            f"📈 成功率: {(self.stats.l2_successful / self.stats.l2_attempts * 100):.1f}%"
            if self.stats.l2_attempts > 0
            else "📈 成功率: 0%"
        )
        print(f"⚡ 采集速率: {rate:.2f} 场/秒")
        print(f"🔢 总请求次数: {self.stats.total_requests}")
        print("=" * 80)

    async def generate_final_report(self):
        """生成最终报告"""
        elapsed = time.time() - self.stats.start_time

        # 获取数据库统计
        conn = await self.get_database_connection()
        try:
            total_matches = await conn.fetchval("SELECT COUNT(*) FROM matches")
            completed_matches = await conn.fetchval(
                "SELECT COUNT(*) FROM matches WHERE collection_status = 'completed'"
            )
            raw_data_count = await conn.fetchval("SELECT COUNT(*) FROM raw_match_data WHERE raw_match_data IS NOT NULL")
            feature_count = await conn.fetchval("SELECT COUNT(*) FROM match_features_training")

        finally:
            await self.release_database_connection(conn)

        print("\n" + "🎉" * 20)
        print("🏆 全能采集器最终报告")
        print(f"📊 L1数据: 找到{self.stats.l1_matches_found}, 保存{self.stats.l1_matches_saved}")
        print(f"📦 L2采集: 尝试{self.stats.l2_attempts}, 成功{self.stats.l2_successful}, 失败{self.stats.l2_failed}")
        print(f"💰 L3赔率: 成功{total_l3_successful}, 失败{total_l3_failed}")
        print(f"🎯 特征提取: {'✅ 成功' if self.stats.features_extracted > 0 else '❌ 失败/跳过'}")
        print(f"⏱️ 总耗时: {elapsed:.1f}秒")
        print(
            f"📈 数据库状态: 总比赛{total_matches}, 已完成{completed_matches}, L2数据{raw_data_count}, 特征{feature_count}"
        )
        print("🎉" * 20)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="全能采集器 - 自动化数据采集流水线")
    parser.add_argument("--league", type=int, default=47, help="联赛ID (默认: 47)")
    parser.add_argument("--season", type=str, default="2024/25", help="赛季 (默认: 2024/25)")
    parser.add_argument("--concurrent", type=int, default=3, help="并发数 (默认: 3)")
    parser.add_argument("--delay", type=float, default=2.0, help="请求间隔秒数 (默认: 2.0)")
    parser.add_argument("--batch-size", type=int, default=50, help="批处理大小 (默认: 50)")
    parser.add_argument("--no-features", action="store_true", help="跳过特征提取")

    args = parser.parse_args()

    # 创建配置
    config = PipelineConfig(
        league_id=args.league,
        season=args.season,
        concurrent_limit=args.concurrent,
        request_delay=args.delay,
        batch_size=args.batch_size,
        auto_extract_features=not args.no_features,
    )

    # 创建并运行全能采集器
    collector = MasterCollector(config)

    try:
        await collector.initialize()
        success = await collector.run_automatic_pipeline()

        if success:
            print("🎉 全能采集器执行成功!")
            sys.exit(0)
        else:
            print("❌ 全能采集器执行失败!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断执行")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        sys.exit(1)
    finally:
        await collector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
