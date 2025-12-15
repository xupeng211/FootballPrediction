#!/usr/bin/env python3
"""
最终就绪验证脚本
Final Readiness Verification Script

验证修复后的系统是否能正确采集真实数据，不再产生"空壳数据"
验收标准：主队名、xG、裁判信息均为真实数据（非None）
"""

import asyncio
import sys
import json
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入项目模块
from database.async_manager import initialize_database, get_async_db_session
from sqlalchemy import text


class FinalReadinessVerifier:
    """最终就绪验证器"""

    def __init__(self):
        self.verification_results = {
            "database_connection": False,
            "test_match_collection": False,
            "home_team_name_real": False,
            "away_team_name_real": False,
            "xg_data_real": False,
            "referee_data_real": False,
            "venue_data_real": False,
            "stats_data_complete": False,
        }
        self.test_match_id = "4189362"  # 推荐的测试比赛ID（近期英超比赛）

    async def run_full_verification(self) -> bool:
        """运行完整的就绪验证"""
        logger.info("🚀 启动最终就绪验证")
        logger.info("🎯 验证目标：系统不再产生'空壳数据'")
        logger.info("=" * 70)

        try:
            # 步骤1: 数据库连接验证
            logger.info("\n📋 步骤1: 数据库连接验证")
            logger.info("-" * 50)
            await self._verify_database_connection()

            # 步骤2: 清理之前的测试数据
            logger.info("\n📋 步骤2: 清理之前的测试数据")
            logger.info("-" * 50)
            await self._cleanup_previous_test_data()

            # 步骤3: 测试真实比赛数据采集
            logger.info("\n📋 步骤3: 测试真实比赛数据采集")
            logger.info("-" * 50)
            await self._test_real_match_collection()

            # 步骤4: 验证数据库中的数据质量
            logger.info("\n📋 步骤4: 验证数据库中的数据质量")
            logger.info("-" * 50)
            await self._verify_data_quality()

            # 步骤5: 打印最终验证结果
            logger.info("\n📋 步骤5: 最终验证结果")
            logger.info("-" * 50)
            self._print_final_verification()

            # 计算总体通过率
            passed_tests = sum(self.verification_results.values())
            total_tests = len(self.verification_results)
            success_rate = passed_tests / total_tests * 100

            logger.info(
                f"\n📊 总体通过率: {passed_tests}/{total_tests} ({success_rate:.1f}%)"
            )

            # 关键验收标准：必须全部通过
            critical_tests = [
                "home_team_name_real",
                "away_team_name_real",
                "xg_data_real",
                "referee_data_real",
            ]

            critical_passed = all(
                self.verification_results[test] for test in critical_tests
            )

            if critical_passed:
                logger.info("\n🎉 ✅ 关键验收标准全部通过!")
                logger.info("✅ 主队名、xG、裁判信息均为真实数据")
                logger.info("🚀 系统已准备就绪，可以启动大规模数据回填")
                return True
            else:
                logger.error("\n💥 ❌ 关键验收标准未通过!")
                failed_critical = [
                    test
                    for test in critical_tests
                    if not self.verification_results[test]
                ]
                logger.error(f"❌ 失败的关键测试: {failed_critical}")
                logger.error("🚨 系统仍存在'空壳数据'问题，需要进一步修复")
                return False

        except Exception as e:
            logger.error(f"💥 验证过程异常: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _verify_database_connection(self):
        """验证数据库连接"""
        try:
            initialize_database()
            logger.info("✅ 数据库连接成功")
            self.verification_results["database_connection"] = True
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            self.verification_results["database_connection"] = False

    async def _cleanup_previous_test_data(self):
        """清理之前的测试数据"""
        try:
            async for session in get_async_db_session():
                # 删除测试比赛的数据（如果存在）
                delete_query = text(
                    """
                    DELETE FROM matches
                    WHERE fotmob_id = :test_match_id
                """
                )

                result = await session.execute(
                    delete_query, {"test_match_id": self.test_match_id}
                )
                deleted_count = result.rowcount

                if deleted_count > 0:
                    logger.info(f"🧹 清理了 {deleted_count} 条之前的测试数据")
                else:
                    logger.info("🧹 没有找到需要清理的测试数据")

                await session.commit()
                await session.close()
                break

        except Exception as e:
            logger.warning(f"⚠️ 清理测试数据时出错: {e}")

    async def _test_real_match_collection(self):
        """测试真实比赛数据采集"""
        try:
            # 使用Docker执行数据采集测试
            import subprocess

            logger.info(f"📡 开始采集测试比赛: {self.test_match_id}")

            # 在Docker容器中执行Python脚本进行数据采集
            cmd = [
                "docker-compose",
                "exec",
                "app",
                "python",
                "-c",
                f"""
import sys
sys.path.append("/app/src")
from collectors.fotmob_api_collector import FotMobAPICollector
import asyncio

async def test_collection():
    collector = FotMobAPICollector(max_concurrent=1, timeout=30, max_retries=3)
    await collector.initialize()

    try:
        match_data = await collector.collect_match_details("{self.test_match_id}")
        if match_data:
            print("✅ 数据采集成功")
            print(f"主队名: {{match_data.match_info.get('home_team_name', 'NOT_FOUND')}}")
            print(f"客队名: {{match_data.match_info.get('away_team_name', 'NOT_FOUND')}}")
            print(f"xG数据: {{match_data.stats_json.get('xg', 'NOT_FOUND')}}")
            print(f"裁判信息: {{match_data.referee or 'NOT_FOUND'}}")
            return True
        else:
            print("❌ 数据采集失败")
            return False
    except Exception as e:
        print(f"❌ 数据采集异常: {{e}}")
        return False
    finally:
        await collector.close()

result = asyncio.run(test_collection())
sys.exit(0 if result else 1)
                """,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                logger.info("✅ 真实比赛数据采集成功")
                logger.info(f"采集结果: {result.stdout.strip()}")
                self.verification_results["test_match_collection"] = True
            else:
                logger.error("❌ 真实比赛数据采集失败")
                logger.error(f"错误信息: {result.stderr}")
                self.verification_results["test_match_collection"] = False

        except subprocess.TimeoutExpired:
            logger.error("❌ 数据采集超时")
            self.verification_results["test_match_collection"] = False
        except Exception as e:
            logger.error(f"❌ 数据采集测试异常: {e}")
            self.verification_results["test_match_collection"] = False

    async def _verify_data_quality(self):
        """验证数据库中的数据质量"""
        try:
            async for session in get_async_db_session():
                # 查询刚采集的测试数据
                query = text(
                    """
                    SELECT
                        fotmob_id,
                        home_team_name,
                        away_team_name,
                        home_xg,
                        away_xg,
                        venue,
                        referee,
                        match_info,
                        stats_json,
                        collection_time,
                        data_completeness
                    FROM matches
                    WHERE fotmob_id = :test_match_id
                    ORDER BY collection_time DESC
                    LIMIT 1
                """
                )

                result = await session.execute(
                    query, {"test_match_id": self.test_match_id}
                )
                match_record = result.fetchone()

                await session.close()

                if not match_record:
                    logger.error("❌ 数据库中未找到测试比赛数据")
                    return

                logger.info(
                    f"✅ 找到测试比赛数据，采集时间: {match_record.collection_time}"
                )

                # 验证主客队名是否为真实数据
                home_team = match_record.home_team_name
                away_team = match_record.away_team_name

                logger.info("🔍 验证主客队名:")
                logger.info(f"   主队: {home_team}")
                logger.info(f"   客队: {away_team}")

                if home_team and home_team != "NOT_FOUND" and home_team.strip():
                    logger.info("✅ 主队名为真实数据")
                    self.verification_results["home_team_name_real"] = True
                else:
                    logger.error("❌ 主队名为空或默认值")

                if away_team and away_team != "NOT_FOUND" and away_team.strip():
                    logger.info("✅ 客队名为真实数据")
                    self.verification_results["away_team_name_real"] = True
                else:
                    logger.error("❌ 客队名为空或默认值")

                # 验证xG数据
                home_xg = match_record.home_xg
                away_xg = match_record.away_xg

                logger.info("🔍 验证xG数据:")
                logger.info(f"   主队xG: {home_xg}")
                logger.info(f"   客队xG: {away_xg}")

                if (
                    home_xg is not None
                    and home_xg > 0
                    and away_xg is not None
                    and away_xg >= 0
                ):
                    logger.info("✅ xG数据为真实数值")
                    self.verification_results["xg_data_real"] = True
                else:
                    logger.error("❌ xG数据为空或无效")

                    # 检查stats_json中的xG数据
                    if match_record.stats_json:
                        try:
                            stats = (
                                json.loads(match_record.stats_json)
                                if isinstance(match_record.stats_json, str)
                                else match_record.stats_json
                            )
                            if stats.get("xg"):
                                logger.info("✅ 在stats_json中找到xG数据")
                                self.verification_results["xg_data_real"] = True
                        except:
                            pass

                # 验证裁判信息
                referee = match_record.referee
                logger.info(f"🔍 验证裁判信息: {referee}")

                if referee and referee.strip() and referee != "NOT_FOUND":
                    logger.info("✅ 裁判信息为真实数据")
                    self.verification_results["referee_data_real"] = True
                else:
                    logger.error("❌ 裁判信息为空或默认值")

                    # 检查environment_json中的裁判信息
                    if match_record.match_info:
                        try:
                            (
                                json.loads(match_record.match_info)
                                if isinstance(match_record.match_info, str)
                                else match_record.match_info
                            )
                            # 这里我们暂时跳过检查，因为environment_json需要单独查询
                        except:
                            pass

                # 验证场地信息
                venue = match_record.venue
                logger.info(f"🔍 验证场地信息: {venue}")

                if venue and venue.strip() and venue != "NOT_FOUND":
                    logger.info("✅ 场地信息为真实数据")
                    self.verification_results["venue_data_real"] = True
                else:
                    logger.warning("⚠️ 场地信息为空")

                # 验证统计数据完整性
                if match_record.stats_json:
                    try:
                        stats = (
                            json.loads(match_record.stats_json)
                            if isinstance(match_record.stats_json, str)
                            else match_record.stats_json
                        )
                        if isinstance(stats, dict) and len(stats) > 0:
                            logger.info(f"✅ 统计数据完整，包含 {len(stats)} 个类别")
                            logger.info(f"   类别: {list(stats.keys())}")
                            self.verification_results["stats_data_complete"] = True
                        else:
                            logger.error("❌ 统计数据为空或格式错误")
                    except Exception as e:
                        logger.error(f"❌ 统计数据解析失败: {e}")
                else:
                    logger.error("❌ 统计数据为空")

        except Exception as e:
            logger.error(f"❌ 数据质量验证异常: {e}")

    def _print_final_verification(self):
        """打印最终验证结果"""
        logger.info("📊 最终验证结果详情:")

        status_map = {True: "✅ 通过", False: "❌ 失败"}

        for test_name, result in self.verification_results.items():
            status = status_map[result]
            logger.info(f"   {test_name}: {status}")

        # 关键测试摘要
        logger.info("\n🎯 关键验收标准:")
        critical_tests = [
            ("主队名真实", "home_team_name_real"),
            ("客队名真实", "away_team_name_real"),
            ("xG数据真实", "xg_data_real"),
            ("裁判信息真实", "referee_data_real"),
        ]

        for display_name, test_key in critical_tests:
            status = "✅ 通过" if self.verification_results[test_key] else "❌ 失败"
            logger.info(f"   {display_name}: {status}")


async def main():
    """主函数"""
    logger.info("🔧 最终就绪验证工具")
    logger.info("🎯 验证系统是否不再产生'空壳数据'")

    verifier = FinalReadinessVerifier()
    success = await verifier.run_full_verification()

    if success:
        logger.info("\n🎉 ✅ 系统就绪验证通过!")
        logger.info("🚀 可以安全启动大规模数据回填作业")
        sys.exit(0)
    else:
        logger.error("\n💥 ❌ 系统就绪验证失败!")
        logger.error("🚨 仍存在数据质量问题，请检查上述失败的测试")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
