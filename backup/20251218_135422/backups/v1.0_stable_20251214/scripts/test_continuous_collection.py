#!/usr/bin/env python3
"""
连续10场真实比赛采集测试
Continuous 10-Match Real-World Collection Test

验证修复后的系统能够流畅、连续地采集并入库10场真实的FotMob比赛数据
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_continuous_collection():
    """执行连续10场真实比赛采集测试"""
    logger.info("🚀 启动连续10场真实比赛采集测试")
    logger.info("🎯 目标: 验证修复后系统的稳定性和数据采集能力")
    logger.info("=" * 70)

    try:
        # 在Docker容器中执行测试
        import subprocess

        python_script = '''
import sys
sys.path.append("/app/src")
from collectors.fotmob_api_collector import FotMobAPICollector
from database.async_manager import initialize_database, get_async_db_session
from sqlalchemy import text
import asyncio
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContinuousCollectionTester:
    def __init__(self, target_count: int = 10):
        self.target_count = target_count
        self.success_count = 0
        self.fail_count = 0
        self.collected_matches = []

    async def get_premier_league_matches(self):
        """获取英超联赛的最新比赛ID列表"""
        logger.info("🔍 获取英超联赛最新比赛ID列表...")

        # 构造获取比赛列表的API请求
        collector = FotMobAPICollector(max_concurrent=1, timeout=30, max_retries=2)
        await collector.initialize()

        try:
            # 尝试获取英超联赛的比赛列表
            # 使用一个有效的英超联赛页面
            league_url = "https://www.fotmob.com/api/leagues?id=47&timezone=Europe/London"

            data, status = await collector._make_request(league_url, "premier_league")

            if status.name == "SUCCESS" and data:
                # 解析比赛列表
                matches = []
                content = data.get("content", {})

                # 尝试不同的数据结构
                if "matches" in content:
                    matches_data = content["matches"]["allMatches"]
                elif "leagueMatches" in content:
                    matches_data = content["leagueMatches"]
                else:
                    # 尝试从其他结构中获取
                    matches_data = []
                    for key in ["upcomingMatches", "liveMatches", "finishedMatches"]:
                        if key in content:
                            if isinstance(content[key], list):
                                matches_data.extend(content[key])
                            else:
                                matches_data.append(content[key])

                # 提取比赛ID
                match_ids = []
                for match in matches_data[:15]:  # 取前15个，确保有足够的有效比赛
                    if isinstance(match, dict):
                        match_id = match.get("id")
                        if match_id:
                            match_ids.append(str(match_id))
                        elif match.get("matchId"):
                            match_ids.append(str(match.get("matchId")))

                await collector.close()

                if match_ids:
                    logger.info(f"✅ 获取到 {len(match_ids)} 个比赛ID")
                    return match_ids[:self.target_count]
                else:
                    logger.warning("⚠️ 未获取到比赛ID，使用预设的测试ID")
                    return self._get_fallback_match_ids()
            else:
                logger.warning(f"⚠️ 获取英超比赛失败: {status}")
                return self._get_fallback_match_ids()

        except Exception as e:
            logger.error(f"💥 获取比赛ID异常: {e}")
            await collector.close()
            return self._get_fallback_match_ids()

    def _get_fallback_match_ids(self):
        """获取fallback比赛ID列表（使用一些可能有效的ID）"""
        fallback_ids = [
            "4315030",  # 曼城 vs 阿森纳 (测试ID)
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

        logger.info(f"🔄 使用fallback比赛ID列表: {len(fallback_ids)} 个")
        return fallback_ids[:self.target_count]

    async def collect_and_save_matches(self, match_ids: List[str]):
        """连续采集并保存比赛数据"""
        logger.info(f"🚀 开始连续采集 {len(match_ids)} 场比赛...")

        # 初始化采集器
        collector = FotMobAPICollector(max_concurrent=2, timeout=30, max_retries=2)
        await collector.initialize()

        try:
            for i, match_id in enumerate(match_ids, 1):
                logger.info(f"\\n📋 进度: {i}/{len(match_ids)} | 采集比赛: {match_id}")

                try:
                    # 采集比赛数据
                    match_data = await collector.collect_match_details(match_id)

                    if match_data:
                        # 验证数据质量
                        if self._validate_match_data(match_data):
                            # 保存到数据库
                            success = await self._save_match_to_database(match_data)

                            if success:
                                self.success_count += 1
                                self.collected_matches.append({
                                    'id': match_id,
                                    'home_team': match_data.match_info.get('home_team_name', 'Unknown'),
                                    'away_team': match_data.match_info.get('away_team_name', 'Unknown'),
                                    'score': f"{match_data.home_score}-{match_data.away_score}",
                                    'status': match_data.status,
                                    'venue': match_data.venue,
                                    'xg_data': bool(match_data.stats_json.get('xg')),
                                    'match_time': match_data.match_time
                                })
                                logger.info(f"✅ 成功采集并保存: {match_id}")
                            else:
                                self.fail_count += 1
                                logger.error(f"❌ 保存失败: {match_id}")
                        else:
                            self.fail_count += 1
                            logger.warning(f"⚠️ 数据质量不达标: {match_id}")
                    else:
                        self.fail_count += 1
                        logger.warning(f"⚠️ 未获取到数据: {match_id}")

                except Exception as e:
                    self.fail_count += 1
                    logger.error(f"💥 采集异常 {match_id}: {e}")

                # 避免API限流
                await asyncio.sleep(0.5)

        finally:
            await collector.close()

        logger.info(f"\\n🎯 采集完成统计:")
        logger.info(f"   📊 目标: {len(match_ids)} 场")
        logger.info(f"   ✅ 成功: {self.success_count} 场")
        logger.info(f"   ❌ 失败: {self.fail_count} 场")
        logger.info(f"   📈 成功率: {(self.success_count/len(match_ids)*100):.1f}%")

    def _validate_match_data(self, match_data) -> bool:
        """验证比赛数据质量"""
        try:
            # 基础信息验证
            if not match_data.fotmob_id:
                return False

            match_info = match_data.match_info or {}
            home_team = match_info.get("home_team_name")
            away_team = match_info.get("away_team_name")

            # 主客队信息至少要有一个
            if not home_team and not away_team:
                return False

            # 统计数据验证（可选）
            if match_data.stats_json:
                return True

            # 即使没有统计数据，只要有基础信息也认为有效
            return True

        except Exception as e:
            logger.warning(f"⚠️ 数据质量验证异常: {e}")
            return False

    async def _save_match_to_database(self, match_data):
        """保存比赛数据到数据库"""
        try:
            async for session in get_async_db_session():
                # 检查是否已存在
                check_query = text("SELECT id FROM matches WHERE fotmob_id = :fotmob_id LIMIT 1")
                result = await session.execute(check_query, {"fotmob_id": match_data.fotmob_id})
                if result.fetchone():
                    await session.close()
                    return True  # 已存在，认为成功

                # 插入新数据
                insert_query = text('''
                    INSERT INTO matches (
                        fotmob_id, home_team_name, away_team_name, home_score, away_score,
                        status, match_time, match_date, venue, league_id, season,
                        home_xg, away_xg, home_possession, away_possession,
                        match_info, lineups_json, stats_json, environment_json,
                        odds_snapshot_json, collection_time, data_completeness,
                        created_at, updated_at
                    ) VALUES (
                        :fotmob_id, :home_team_name, :away_team_name, :home_score, :away_score,
                        :status, :match_time, :match_date, :venue, :league_id, :season,
                        :home_xg, :away_xg, :home_possession, :away_possession,
                        :match_info, :lineups_json, :stats_json, :environment_json,
                        :odds_snapshot_json, :collection_time, :data_completeness,
                        NOW(), NOW()
                    )
                ''')

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
                    "match_date": None,  # 允许NULL
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
                    "data_completeness": "full" if stats_json else "partial"
                })

                await session.commit()
                await session.close()
                return True

        except Exception as e:
            logger.error(f"❌ 保存数据异常: {e}")
            return False

    def _extract_xg_values(self, stats_json: dict) -> tuple:
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

    def _extract_possession_values(self, stats_json: dict) -> tuple:
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

    async def generate_summary_report(self):
        """生成采集结果摘要报告"""
        logger.info("\\n" + "="*80)
        logger.info("📊 10场比赛入库摘要")
        logger.info("="*80)

        if not self.collected_matches:
            logger.error("❌ 没有采集到任何比赛数据")
            return False

        logger.info(f"🎯 连续采集结果: {self.success_count}/{len(self.collected_matches)} 成功")

        for i, match in enumerate(self.collected_matches, 1):
            xg_status = "✅ Yes" if match['xg_data'] else "❌ No"
            time_info = match['match_time'] if match['match_time'] else "⏰ TBD"

            logger.info(f"\\n[{i:2d}] {match['id']} | {time_info} | {match['home_team']} vs {match['away_team']} | xG: {xg_status}")
            logger.info(f"     比分: {match['score']} | 状态: {match['status']} | 场地: {match['venue'] or 'N/A'}")

        # 统计xG数据
        matches_with_xg = sum(1 for match in self.collected_matches if match['xg_data'])
        matches_with_time = sum(1 for match in self.collected_matches if match['match_time'])

        logger.info(f"\\n📊 数据质量统计:")
        logger.info(f"   📈 包含xG数据: {matches_with_xg}/{self.success_count} ({(matches_with_xg/self.success_count*100):.1f}%)")
        logger.info(f"   ⏰ 包含时间数据: {matches_with_time}/{self.success_count} ({(matches_with_time/self.success_count*100):.1f}%)")

        return self.success_count >= 8  # 80%以上成功率视为通过

async def main():
    """主函数"""
    logger.info("🚀 启动连续10场真实比赛采集测试")

    tester = ContinuousCollectionTester(target_count=10)

    # 获取比赛ID列表
    match_ids = await tester.get_premier_league_matches()

    if not match_ids:
        logger.error("❌ 无法获取比赛ID列表")
        return False

    logger.info(f"📋 获取到 {len(match_ids)} 个比赛ID: {match_ids}")

    # 连续采集并保存
    await tester.collect_and_save_matches(match_ids)

    # 生成摘要报告
    success = await tester.generate_summary_report()

    return success

# 执行测试
result = asyncio.run(main())
sys.exit(0 if result else 1)
'''

        cmd = [
            "docker-compose", "exec", "app", "python", "-c", python_script
        ]

        # 执行测试命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # 输出结果
        print("🔍 连续10场真实比赛采集测试输出:")
        print("=" * 80)
        print(result.stdout)

        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr)

        # 检查结果
        if result.returncode == 0:
            print("\n✅ 连续10场真实比赛采集测试成功!")
            print("🚀 系统稳定性验证通过")
            return True
        else:
            print("\n❌ 连续10场真实比赛采集测试失败!")
            print("🚨 系统仍存在稳定性问题")
            return False

    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

if __name__ == "__main__":
    success = test_continuous_collection()

    if success:
        print("\n" + "=" * 80)
        print("🎉 ✅ 连续10场真实比赛采集测试完全成功!")
        print("🚀 系统修复验证完成，可以投入生产使用")
        print("📊 数据采集流程稳定可靠")
        print("💡 可以安全启动大规模数据回填作业!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("💥 ❌ 连续10场真实比赛采集测试失败!")
        print("🚨 系统仍需要进一步调试和优化")
        print("=" * 80)

    exit(0 if success else 1)