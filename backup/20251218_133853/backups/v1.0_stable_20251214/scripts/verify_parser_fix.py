#!/usr/bin/env python3
"""
FotMobAPI 解析器修复验证脚本
Verify Parser Fix Script

验证修复后的 _extract_full_match_stats 方法能否正确解析真实的API响应结构
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 直接导入修复后的采集器，避免通过__init__.py的循环导入
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'collectors'))

from fotmob_api_collector import FotMobAPICollector

class ParserFixVerifier:
    """解析器修复验证器"""

    def __init__(self):
        self.collector = FotMobAPICollector()
        self.test_results = {
            "mock_data_test": False,
            "real_api_test": False,
            "xg_extraction": False,
            "possession_extraction": False,
            "shots_extraction": False,
        }

    def run_verification(self) -> bool:
        """运行完整的验证测试"""
        logger.info("🚀 启动FotMobAPI解析器修复验证")
        logger.info("=" * 60)

        try:
            # 测试1: 使用模拟的API数据结构
            logger.info("\n📋 测试1: 模拟API数据结构验证")
            logger.info("-" * 40)
            self._test_mock_api_data()

            # 测试2: 使用真实API调用
            logger.info("\n📋 测试2: 真实API调用验证")
            logger.info("-" * 40)
            self._test_real_api_call()

            # 打印最终结果
            logger.info("\n📋 验证结果汇总")
            logger.info("=" * 60)
            self._print_verification_summary()

            # 计算总体通过率
            passed_tests = sum(self.test_results.values())
            total_tests = len(self.test_results)
            success_rate = passed_tests / total_tests * 100

            logger.info(f"📊 总体通过率: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

            return success_rate >= 80  # 80%以上通过率视为修复成功

        except Exception as e:
            logger.error(f"💥 验证过程异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _test_mock_api_data(self):
        """测试模拟的API数据结构"""
        try:
            # 🔥 模拟真实的API响应结构（基于审计发现的列表结构）
            mock_content = {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {
                                    "key": "expected_goals",
                                    "stats": [
                                        {
                                            "key": "xg",
                                            "stats": [2.21, 1.85]  # 🔍 xG: 2.21
                                        }
                                    ]
                                },
                                {
                                    "key": "ball_possession_shared",
                                    "stats": [
                                        {
                                            "key": "possession",
                                            "stats": [58, 42]  # 控球率: 58% vs 42%
                                        }
                                    ]
                                },
                                {
                                    "key": "total_shots",
                                    "stats": [
                                        {
                                            "key": "shots_total",
                                            "stats": [15, 8]  # 射门: 15 vs 8
                                        }
                                    ]
                                },
                                {
                                    "key": "passes",
                                    "stats": [
                                        {
                                            "key": "total_passes",
                                            "stats": [420, 380]  # 传球: 420 vs 380
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            }

            logger.info("🔍 使用模拟API数据测试修复后的解析器...")

            # 调用修复后的解析方法
            result = self.collector._extract_full_match_stats(mock_content)

            if result and isinstance(result, dict):
                logger.info("✅ 解析器返回有效的字典结构")
                self.test_results["mock_data_test"] = True

                # 验证xG提取
                xg_data = result.get("xg", {})
                if xg_data and "xg" in xg_data:
                    xg_values = xg_data["xg"]
                    if len(xg_values) >= 2:
                        home_xg, away_xg = xg_values[0], xg_values[1]
                        logger.info(f"✅ xG数据提取成功: 主队={home_xg}, 客队={away_xg}")

                        # 验证关键值2.21是否被正确提取
                        if abs(home_xg - 2.21) < 0.01:
                            logger.info("🎯 关键xG值2.21提取成功!")
                            self.test_results["xg_extraction"] = True
                        else:
                            logger.warning(f"⚠️ xG值不匹配: 期望2.21, 实际{home_xg}")

                # 验证控球率提取
                possession_data = result.get("possession", {})
                if possession_data and "possession" in possession_data:
                    possession_values = possession_data["possession"]
                    if len(possession_values) >= 2:
                        home_possession, away_possession = possession_values[0], possession_values[1]
                        logger.info(f"✅ 控球率数据提取成功: 主队={home_possession}%, 客队={away_possession}%")
                        self.test_results["possession_extraction"] = True

                # 验证射门数据提取
                shots_data = result.get("shots", {})
                if shots_data and "shots_total" in shots_data:
                    shots_values = shots_data["shots_total"]
                    if len(shots_values) >= 2:
                        home_shots, away_shots = shots_values[0], shots_values[1]
                        logger.info(f"✅ 射门数据提取成功: 主队={home_shots}, 客队={away_shots}")
                        self.test_results["shots_extraction"] = True

                # 显示完整解析结果
                logger.info(f"📊 解析结果概览: {list(result.keys())}")
                for category, stats in result.items():
                    if stats:
                        logger.info(f"   {category}: {len(stats)} 项统计")

            else:
                logger.error("❌ 解析器返回无效结果")
                self.test_results["mock_data_test"] = False

        except Exception as e:
            logger.error(f"❌ 模拟数据测试异常: {e}")
            self.test_results["mock_data_test"] = False

    async def _test_real_api_call(self):
        """测试真实API调用"""
        try:
            import asyncio

            logger.info("🌐 测试真实API调用...")

            # 初始化采集器
            await self.collector.initialize()

            # 使用一个测试比赛ID
            test_match_id = "4189362"  # 推荐的测试比赛

            logger.info(f"📡 请求比赛数据: {test_match_id}")

            # 调用真实API
            match_data = await self.collector.collect_match_details(test_match_id)

            if match_data:
                logger.info("✅ 真实API调用成功")

                # 检查stats_json字段
                if match_data.stats_json:
                    stats_json = match_data.stats_json
                    logger.info(f"✅ stats_json包含数据，字段数: {len(stats_json)}")

                    # 验证关键字段
                    key_fields = ["xg", "possession", "shots"]
                    found_fields = []

                    for field in key_fields:
                        if field in stats_json and stats_json[field]:
                            found_fields.append(field)
                            logger.info(f"✅ 找到{field}数据: {stats_json[field]}")
                        else:
                            logger.warning(f"⚠️ 未找到{field}数据")

                    if found_fields:
                        logger.info(f"🎯 成功提取关键字段: {found_fields}")
                        self.test_results["real_api_test"] = True
                    else:
                        logger.warning("⚠️ 未提取到任何关键字段")
                else:
                    logger.warning("⚠️ stats_json为空")
            else:
                logger.warning("⚠️ 未获取到比赛数据")

            # 清理资源
            await self.collector.close()

        except Exception as e:
            logger.error(f"❌ 真实API测试异常: {e}")
            self.test_results["real_api_test"] = False

    def _print_verification_summary(self):
        """打印验证摘要"""
        logger.info("📋 详细验证结果:")

        status_map = {True: "✅ 通过", False: "❌ 失败"}

        for test_name, result in self.test_results.items():
            status = status_map[result]
            logger.info(f"   {test_name}: {status}")

        # 关键修复验证
        logger.info("\n🎯 关键修复验证:")

        if self.test_results["xg_extraction"]:
            logger.info("   ✅ xG数据解析: 修复成功 - 正确处理列表结构")
        else:
            logger.error("   ❌ xG数据解析: 仍有问题 - 可能需要进一步修复")

        if self.test_results["mock_data_test"]:
            logger.info("   ✅ 列表结构处理: 修复成功 - 不再误认为字典")
        else:
            logger.error("   ❌ 列表结构处理: 仍有问题")

def main():
    """主函数"""
    logger.info("🔧 FotMobAPI 解析器修复验证工具")

    verifier = ParserFixVerifier()

    # 对于真实API测试，需要异步执行
    import asyncio
    asyncio.run(verifier._test_real_api_call()) if hasattr(verifier, '_test_real_api_call') else False

    # 运行完整验证
    overall_success = verifier.run_verification()

    if overall_success:
        logger.info("\n🎉 ✅ 解析器修复验证通过!")
        logger.info("🚀 修复后的解析器已准备投入生产使用")
        sys.exit(0)
    else:
        logger.error("\n💥 ❌ 解析器修复验证失败!")
        logger.error("🚨 需要进一步调试和修复")
        sys.exit(1)

if __name__ == "__main__":
    main()
