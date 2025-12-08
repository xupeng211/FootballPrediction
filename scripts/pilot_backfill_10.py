#!/usr/bin/env python3
"""
10场试跑脚本 - Pilot Run 10 Matches
验证修复后的数据采集完整性和深度
"""

import asyncio
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy import text

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入修复后的模块
from database.async_manager import initialize_database, get_async_db_session
from collectors.fotmob_api_collector import FotMobAPICollector
from database.models.match import Match

class PilotBackfill10:
    """10场试跑数据采集器"""

    def __init__(self, max_matches: int = 10):
        self.max_matches = max_matches
        self.success_count = 0
        self.fail_count = 0
        self.collected_matches = []

        # 🔥 使用一些较近期的英超比赛ID进行测试
        self.test_match_ids = [
            "4329053",  # 曼城 vs 阿森纳
            "4329067",  # 利物浦 vs 切尔西
            "4329078",  # 热刺 vs 曼联
            "4329089",  # 纽卡斯尔 vs 莱斯特城
            "4329090",  # 布莱顿 vs 西汉姆
            "4329091",  # 维拉 vs 埃弗顿
            "4329092",  # 富勒姆 vs 水晶宫
            "4329093",  # 伯恩利 vs 诺丁汉森林
            "4329094",  # 谢菲联 vs 卢顿
            "4329095",  # 狼队 vs 伯恩茅斯
        ]

    async def run_pilot(self):
        """执行10场试跑"""
        logger.info("🚀 启动10场试跑数据采集")
        logger.info(f"🎯 目标: 成功采集 {self.max_matches} 场比赛")
        logger.info("=" * 60)

        try:
            # 初始化数据库
            initialize_database()
            logger.info("✅ 数据库连接成功")

            # 初始化采集器
            collector = FotMobAPICollector(
                max_concurrent=3,
                timeout=30,
                max_retries=3
            )
            await collector.initialize()
            logger.info("✅ 采集器初始化成功")

            # 开始采集
            logger.info(f"📡 开始采集，总计 {len(self.test_match_ids)} 场比赛...")

            for i, match_id in enumerate(self.test_match_ids, 1):
                if self.success_count >= self.max_matches:
                    logger.info(f"🎯 已达到目标数量 {self.max_matches}，停止采集")
                    break

                logger.info(f"\n📋 进度: {i}/{len(self.test_match_ids)} | 已成功: {self.success_count} | 当前: {match_id}")

                # 采集单场比赛
                success = await self._collect_single_match(collector, match_id)

                if success:
                    self.success_count += 1
                    self.collected_matches.append(match_id)
                    logger.info(f"✅ 成功采集第 {self.success_count} 场比赛: {match_id}")
                else:
                    self.fail_count += 1
                    logger.warning(f"❌ 采集失败: {match_id}")

                # 避免API限流
                await asyncio.sleep(1.0)

            # 清理采集器
            await collector.close()
            logger.info("🔒 采集器已关闭")

            # 生成详细验货报告
            logger.info(f"\n🎯 采集完成: 成功 {self.success_count} 场, 失败 {self.fail_count} 场")
            await self._generate_quality_report()

        except Exception as e:
            logger.error(f"💥 试跑过程异常: {e}")
            import traceback
            traceback.print_exc()

    async def _collect_single_match(self, collector: FotMobAPICollector, match_id: str) -> bool:
        """采集单场比赛数据"""
        try:
            # 采集数据
            match_data = await collector.collect_match_details(match_id)

            if not match_data:
                logger.warning(f"⚠️ 未获取到比赛数据: {match_id}")
                return False

            # 检查数据质量
            if not self._validate_match_data_quality(match_data):
                logger.warning(f"⚠️ 数据质量不达标: {match_id}")
                return False

            # 保存到数据库
            success = await self._save_to_database(match_data)

            if success:
                logger.info(f"💾 数据保存成功: {match_id}")
                return True
            else:
                logger.warning(f"❌ 数据保存失败: {match_id}")
                return False

        except Exception as e:
            logger.error(f"💥 采集比赛异常 {match_id}: {e}")
            return False

    def _validate_match_data_quality(self, match_data) -> bool:
        """验证比赛数据质量"""
        try:
            # 基础信息验证
            if not match_data.fotmob_id:
                logger.warning("❌ 缺少fotmob_id")
                return False

            # 主客队信息验证
            match_info = match_data.match_info or {}
            home_team = match_info.get("home_team_name")
            away_team = match_info.get("away_team_name")

            if not home_team or not away_team:
                logger.warning(f"❌ 缺少主客队信息: 主队={home_team}, 客队={away_team}")
                return False

            # 至少要有一些统计数据
            if not match_data.stats_json:
                logger.warning("❌ 缺少统计数据")
                return False

            # 基础验证通过
            return True

        except Exception as e:
            logger.warning(f"❌ 数据质量验证异常: {e}")
            return False

    async def _save_to_database(self, match_data) -> bool:
        """保存比赛数据到数据库"""
        try:
            async for session in get_async_db_session():
                # 检查是否已存在
                check_query = text("""
                    SELECT id FROM matches
                    WHERE fotmob_id = :fotmob_id
                    LIMIT 1
                """)

                result = await session.execute(check_query, {"fotmob_id": match_data.fotmob_id})
                existing = result.fetchone()

                if existing:
                    logger.debug(f"⚠️ 比赛已存在: {match_data.fotmob_id}")
                    await session.close()
                    return True  # 认为成功，因为数据已存在

                # 插入新数据
                insert_query = text("""
                    INSERT INTO matches (
                        fotmob_id, home_team_name, away_team_name, home_score, away_score,
                        status, match_time, venue, league_id, season,
                        home_xg, away_xg, home_possession, away_possession,
                        match_info, lineups_json, stats_json, environment_json,
                        odds_snapshot_json, collection_time, data_completeness,
                        created_at, updated_at
                    ) VALUES (
                        :fotmob_id, :home_team_name, :away_team_name, :home_score, :away_score,
                        :status, :match_time, :venue, :league_id, :season,
                        :home_xg, :away_xg, :home_possession, :away_possession,
                        :match_info, :lineups_json, :stats_json, :environment_json,
                        :odds_snapshot_json, :collection_time, :data_completeness,
                        NOW(), NOW()
                    )
                """)

                # 提取数据
                match_info = match_data.match_info or {}
                stats_json = match_data.stats_json or {}
                environment_json = match_data.environment_json or {}

                # 从统计中提取xG和控球率
                home_xg, away_xg = self._extract_xg_values(stats_json)
                home_possession, away_possession = self._extract_possession_values(stats_json)

                # 执行插入
                await session.execute(insert_query, {
                    "fotmob_id": match_data.fotmob_id,
                    "home_team_name": match_info.get("home_team_name"),
                    "away_team_name": match_info.get("away_team_name"),
                    "home_score": match_data.home_score,
                    "away_score": match_data.away_score,
                    "status": match_data.status,
                    "match_time": match_data.match_time,
                    "venue": match_data.venue,
                    "league_id": match_info.get("league_context", {}).get("league_id"),
                    "season": match_info.get("league_context", {}).get("season"),
                    "home_xg": home_xg,
                    "away_xg": away_xg,
                    "home_possession": home_possession,
                    "away_possession": away_possession,
                    "match_info": json.dumps(match_info, ensure_ascii=False) if match_info else None,
                    "lineups_json": json.dumps(match_data.lineups_json, ensure_ascii=False) if match_data.lineups_json else None,
                    "stats_json": json.dumps(stats_json, ensure_ascii=False) if stats_json else None,
                    "environment_json": json.dumps(environment_json, ensure_ascii=False) if environment_json else None,
                    "odds_snapshot_json": json.dumps(match_data.odds_snapshot_json, ensure_ascii=False) if match_data.odds_snapshot_json else None,
                    "collection_time": datetime.now(),
                    "data_completeness": "full"
                })

                await session.commit()
                await session.close()
                return True

        except Exception as e:
            logger.error(f"❌ 保存数据异常: {e}")
            return False

    def _extract_xg_values(self, stats_json: dict) -> tuple[float, float]:
        """从统计数据中提取xG值"""
        try:
            xg_data = stats_json.get("xg", {})
            if xg_data and "xg" in xg_data:
                xg_values = xg_data["xg"]
                if len(xg_values) >= 2:
                    return float(xg_values[0]), float(xg_values[1])
            return None, None
        except:
            return None, None

    def _extract_possession_values(self, stats_json: dict) -> tuple[float, float]:
        """从统计数据中提取控球率值"""
        try:
            possession_data = stats_json.get("possession", {})
            if possession_data and "possession" in possession_data:
                possession_values = possession_data["possession"]
                if len(possession_values) >= 2:
                    return float(possession_values[0]), float(possession_values[1])
            return None, None
        except:
            return None, None

    async def _generate_quality_report(self):
        """生成详细的验货报告"""
        logger.info("\n" + "="*80)
        logger.info("📊 详细验货报告")
        logger.info("="*80)

        try:
            async for session in get_async_db_session():
                # 查询最近采集的比赛
                query = text("""
                    SELECT
                        fotmob_id,
                        home_team_name,
                        away_team_name,
                        home_score,
                        away_score,
                        status,
                        venue,
                        match_time,
                        home_xg,
                        away_xg,
                        home_possession,
                        away_possession,
                        match_info,
                        stats_json,
                        environment_json,
                        odds_snapshot_json,
                        collection_time,
                        data_completeness
                    FROM matches
                    WHERE fotmob_id = ANY(:match_ids)
                    ORDER BY collection_time DESC
                """)

                result = await session.execute(query, {"match_ids": self.collected_matches})
                matches = result.fetchall()

                await session.close()

                if not matches:
                    logger.error("❌ 未找到采集的比赛数据")
                    return

                logger.info(f"📋 共找到 {len(matches)} 场比赛数据")

                # 逐场比赛详细报告
                for i, match in enumerate(matches, 1):
                    logger.info(f"\n🎯 比赛 {i}: {match.home_team_name} vs {match.away_team_name}")
                    logger.info("   " + "-"*70)

                    # 基础信息
                    logger.info(f"   🆔 Match ID: {match.fotmob_id}")
                    logger.info(f"   ⚽ 比分: {match.home_score}-{match.away_score}")
                    logger.info(f"   🏟️ 场地: {match.venue or '❌ Unknown'}")
                    logger.info(f"   📅 时间: {match.match_time or '❌ Unknown'}")
                    logger.info(f"   ✅ 状态: {match.status}")

                    # xG数据
                    if match.home_xg is not None and match.away_xg is not None:
                        logger.info(f"   📊 xG: 主队 {match.home_xg:.2f} - 客队 {match.away_xg:.2f} ✅")
                    else:
                        logger.info("   📊 xG: ❌ 未找到")

                    # 控球率数据
                    if match.home_possession is not None and match.away_possession is not None:
                        logger.info(f"   📊 控球率: 主队 {match.home_possession}% - 客队 {match.away_possession}% ✅")
                    else:
                        logger.info("   📊 控球率: ❌ 未找到")

                    # 统计数据详细检查
                    if match.stats_json:
                        try:
                            stats = json.loads(match.stats_json) if isinstance(match.stats_json, str) else match.stats_json
                            if isinstance(stats, dict):
                                xg_from_stats = stats.get("xg", {})
                                possession_from_stats = stats.get("possession", {})
                                shots_from_stats = stats.get("shots", {})

                                if xg_from_stats:
                                    logger.info(f"   📈 Stats.xG: {xg_from_stats} ✅")
                                if possession_from_stats:
                                    logger.info(f"   📈 Stats.Possession: {possession_from_stats} ✅")
                                if shots_from_stats:
                                    logger.info(f"   📈 Stats.Shots: {shots_from_stats} ✅")

                                logger.info(f"   📈 Stats类别数: {len([k for k, v in stats.items() if v])} ✅")
                            else:
                                logger.info("   📈 统计数据: ❌ 格式错误")
                        except Exception as e:
                            logger.info(f"   📈 统计数据: ❌ 解析失败 ({e})")
                    else:
                        logger.info("   📈 统计数据: ❌ 空数据")

                    # 环境数据详细检查
                    if match.environment_json:
                        try:
                            env = json.loads(match.environment_json) if isinstance(match.environment_json, str) else match.environment_json
                            if isinstance(env, dict):
                                referee = env.get("referee", {})
                                weather = env.get("weather", {})
                                managers = env.get("managers", {})
                                venue_info = env.get("venue", {})

                                if referee and referee.get("name"):
                                    logger.info(f"   🌍 裁判: {referee.get('name')} ({referee.get('country')}) ✅")
                                else:
                                    logger.info("   🌍 裁判: ❌ 未找到")

                                if weather and weather.get("condition"):
                                    logger.info(f"   🌍 天气: {weather.get('condition')} {weather.get('temp', '')}°C ✅")
                                else:
                                    logger.info("   🌍 天气: ❌ 未找到")

                                if managers and isinstance(managers, dict):
                                    home_mgr = managers.get("home_team", {}).get("name")
                                    away_mgr = managers.get("away_team", {}).get("name")
                                    if home_mgr or away_mgr:
                                        logger.info(f"   🌍 主教练: 主队{home_mgr} vs 客队{away_mgr} ✅")
                                    else:
                                        logger.info("   🌍 主教练: ❌ 未找到")
                            else:
                                logger.info("   🌍 环境数据: ❌ 格式错误")
                        except Exception as e:
                            logger.info(f"   🌍 环境数据: ❌ 解析失败 ({e})")
                    else:
                        logger.info("   🌍 环境数据: ❌ 空数据")

                    # 赔率数据重点检查
                    if match.odds_snapshot_json:
                        try:
                            odds = json.loads(match.odds_snapshot_json) if isinstance(match.odds_snapshot_json, str) else match.odds_snapshot_json
                            if isinstance(odds, dict) and odds:
                                logger.info(f"   💰 赔率数据: ✅ 找到 {len(odds)} 个数据源")
                                for key, value in odds.items():
                                    if key != "snapshot_time":
                                        logger.info(f"      - {key}: {type(value).__name__} (长度: {len(str(value))})")
                            else:
                                logger.info("   💰 赔率数据: ⚠️ Empty")
                        except Exception as e:
                            logger.info(f"   💰 赔率数据: ❌ 解析失败 ({e})")
                    else:
                        logger.info("   💰 赔率数据: ❌ 未找到")

                    # 战意上下文检查
                    if match.match_info:
                        try:
                            info = json.loads(match.match_info) if isinstance(match.match_info, str) else match.match_info
                            if isinstance(info, dict):
                                league_table = info.get("league_table", {})
                                round_info = info.get("round_info", {})

                                if league_table:
                                    logger.info(f"   🎯 战意信息: ✅ 联赛排名数据")
                                if round_info:
                                    logger.info(f"   🎯 战意信息: ✅ 轮次信息 ({round_info.get('round_name')})")
                            else:
                                logger.info("   🎯 战意信息: ❌ 格式错误")
                        except Exception as e:
                            logger.info(f"   🎯 战意信息: ❌ 解析失败 ({e})")
                    else:
                        logger.info("   🎯 战意信息: ❌ 空数据")

        except Exception as e:
            logger.error(f"❌ 生成验货报告异常: {e}")

        # 最终总结
        logger.info("\n" + "="*80)
        logger.info("🎯 试跑总结")
        logger.info("="*80)
        logger.info(f"📊 目标: {self.max_matches} 场比赛")
        logger.info(f"✅ 成功: {self.success_count} 场")
        logger.info(f"❌ 失败: {self.fail_count} 场")
        logger.info(f"📈 成功率: {(self.success_count/(self.success_count+self.fail_count)*100):.1f}%")
        logger.info(f"🕐 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """主函数"""
    logger.info("🚀 启动10场试跑数据采集器")

    pilot = PilotBackfill10(max_matches=10)
    await pilot.run_pilot()

if __name__ == "__main__":
    asyncio.run(main())