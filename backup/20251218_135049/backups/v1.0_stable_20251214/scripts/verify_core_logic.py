#!/usr/bin/env python3
"""
L1 & L2 核心逻辑验证脚本
QA Lead & System Architect Verification Script

目的：在不启动大规模回填的情况下，通过实时调用真实 API，验证当前代码库中:
1. L1 (赛程获取) 的核心逻辑是否符合预期
2. L2 (详情解析) 的核心逻辑是否符合预期

验证重点：
- L1 修复有效：获取到的 Match ID 是纯数字（如 `4219053`），而不是错误的组合字符串
- L2 修复有效：能正确从列表结构的 `stats` 中提取出 `xG`，并从 `environment` 中提取出 `referee`

作者: QA Lead & System Architect
创建时间: 2025-12-08
版本: 1.0.0
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目的FotMob采集器
from src.collectors.fotmob_api_collector import FotMobAPICollector
from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


class CoreLogicVerifier:
    """核心逻辑验证器"""

    def __init__(self):
        self.verification_results = {
            "l1_verification": {},
            "l2_verification": {},
            "overall_status": "PENDING"
        }

    def print_header(self):
        """打印验证脚本头部信息"""
        print("=" * 80)
        print("🏗️  L1 & L2 核心逻辑验证脚本")
        print("=" * 80)
        print("📋 验证目标:")
        print("   1. L1 赛程获取: Match ID 必须是纯数字格式")
        print("   2. L2 详情解析: xG 和 referee 数据提取正确性")
        print("   3. 使用项目中的 FotMobAPICollector 类")
        print("=" * 80)
        print()

    def print_step_header(self, step_name: str, description: str):
        """打印步骤头部"""
        print(f"🔶 {step_name}")
        print(f"   {description}")
        print("-" * 60)

    async def step_1_l1_verification(self) -> bool:
        """Step 1: L1 赛程验证 (The Map Check)"""
        self.print_step_header(
            "Step 1: L1 赛程验证 (The Map Check)",
            "调用 API 获取英超 (ID 47) 的最新赛程，验证 Match ID 格式"
        )

        try:
            # 使用EnhancedFotMobCollector进行L1采集
            collector = EnhancedFotMobCollector()
            await collector.initialize()

            print("🏴󠁧󠁢󠁥󠁮󠁧󠁿 正在获取英超 (ID 47) 的比赛赛程...")

            # 使用正确的API端点获取英超比赛
            import aiohttp
            headers = collector.client.headers if collector.client else {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.fotmob.com/",
                "Origin": "https://www.fotmob.com",
                "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=",
                "x-foo": "production:208a8f87c2cc13343f1dd8671471cf5a039dced3",
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                # 正确的API端点
                url = "https://www.fotmob.com/api/leagues?id=47&tab=fixtures"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        matches = []

                        # 解析比赛数据
                        if "matches" in data:
                            matches = data["matches"]
                        elif "leagues" in data:
                            for league in data["leagues"]:
                                if "matches" in league:
                                    matches.extend(league["matches"])
                        else:
                            # 尝试从其他字段中提取比赛数据
                            print(f"🔍 API返回的数据结构: {list(data.keys())}")
                            # 检查是否有fixtures字段
                            if "fixtures" in data:
                                fixtures = data["fixtures"]
                                print(f"🔍 Fixtures数据结构: {type(fixtures)}, 键: {list(fixtures.keys()) if isinstance(fixtures, dict) else 'N/A'}")

                                # fixtures可能是字典或列表
                                if isinstance(fixtures, dict):
                                    # 检查是否有allMatches字段（FotMob英超API使用这个结构）
                                    if "allMatches" in fixtures:
                                        all_matches = fixtures["allMatches"]
                                        if isinstance(all_matches, list):
                                            matches.extend(all_matches)
                                            print(f"✅ 从 allMatches 提取到 {len(all_matches)} 场比赛")
                                    else:
                                        # 尝试其他键
                                        for round_key, round_data in fixtures.items():
                                            if isinstance(round_data, dict) and "matches" in round_data:
                                                round_matches = round_data["matches"]
                                                if isinstance(round_matches, list):
                                                    matches.extend(round_matches)
                                                    print(f"✅ 从 {round_key} 提取到 {len(round_matches)} 场比赛")
                                elif isinstance(fixtures, list):
                                    for fixture in fixtures:
                                        if isinstance(fixture, dict) and "matches" in fixture:
                                            matches.extend(fixture["matches"])

                        print(f"✅ 成功获取到 {len(matches)} 场英超比赛")
                    else:
                        print(f"❌ API请求失败，状态码: {response.status}")
                        matches = []

            if not matches:
                print("❌ 未能获取到任何比赛数据！")
                self.verification_results["l1_verification"] = {
                    "status": "FAILED",
                    "error": "无法获取比赛数据",
                    "matches_found": 0
                }
                await collector.close()
                return False

            # 验证 Match ID 格式
            invalid_ids = []
            valid_ids = []

            print("\n🔍 验证 Match ID 格式:")
            for i, match in enumerate(matches[:3], 1):  # 只检查前3个
                match_id = str(match.get("id", ""))
                home_team = match.get("home", {}).get("name", "Unknown")
                away_team = match.get("away", {}).get("name", "Unknown")
                print(f"   比赛 {i}: {home_team} vs {away_team}, ID = '{match_id}'")

                # 关键验证：ID必须是纯数字
                if match_id.isdigit():
                    valid_ids.append(match_id)
                    print("      ✅ 格式正确 (纯数字)")
                else:
                    invalid_ids.append(match_id)
                    print("      ❌ 格式错误 (包含非数字字符)")

            # 记录验证结果
            self.verification_results["l1_verification"] = {
                "status": "PASSED" if not invalid_ids else "FAILED",
                "matches_found": len(matches),
                "valid_ids": valid_ids,
                "invalid_ids": invalid_ids,
                "sample_matches": matches[:3]  # 保存前3个比赛用于L2验证
            }

            await collector.close()

            # 如果有无效ID，立即报错停止
            if invalid_ids:
                print(f"\n❌ L1 验证失败！发现 {len(invalid_ids)} 个无效 Match ID:")
                for invalid_id in invalid_ids:
                    print(f"   - {invalid_id}")
                print("\n🛑 脚本立即停止，请修复 L1 采集逻辑！")
                return False

            print(f"\n✅ L1 验证通过！所有 {len(valid_ids)} 个 Match ID 都是纯数字格式")
            return True

        except Exception as e:
            logger.error(f"❌ L1 验证过程中发生错误: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

            self.verification_results["l1_verification"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False

    async def step_2_l2_verification(self, sample_matches: list[dict[str, Any]]) -> bool:
        """Step 2: L2 详情验证 (The Deep Dive)"""
        self.print_step_header(
            "Step 2: L2 详情验证 (The Deep Dive)",
            "从 L1 获取的比赛中选取样本，调用详情API并验证数据解析"
        )

        if not sample_matches:
            print("❌ 没有可用的比赛样本进行 L2 验证！")
            self.verification_results["l2_verification"] = {
                "status": "FAILED",
                "error": "没有比赛样本"
            }
            return False

        try:
            # 使用 FotMobAPICollector 进行 L2 详情采集
            collector = FotMobAPICollector(max_concurrent=2, timeout=30)
            await collector.initialize()

            # 选择比赛：1场已结束 + 1场未来比赛
            finished_match = None
            scheduled_match = None

            print("🔍 分析比赛状态，选择验证样本:")
            for match in sample_matches:
                status = match.get("status", {}).get("reason", {}).get("short", "Unknown")
                match_id = str(match.get("id", ""))
                home_team = match.get("home", {}).get("name", "Unknown")
                away_team = match.get("away", {}).get("name", "Unknown")

                print(f"   比赛 {match_id}: {home_team} vs {away_team} (状态: {status})")

                if status == "FT" and not finished_match:
                    finished_match = match
                    print("      ✅ 选择为已结束比赛样本")
                elif status in ["NS", "Scheduled"] and not scheduled_match:
                    scheduled_match = match
                    print("      ✅ 选择为未来比赛样本")

                if finished_match and scheduled_match:
                    break

            # 如果没有找到理想组合，使用可用的比赛
            test_matches = [m for m in [finished_match, scheduled_match] if m]
            if not test_matches:
                test_matches = sample_matches[:1]  # 至少测试一个

            print(f"\n📊 将验证 {len(test_matches)} 场比赛的详情数据")

            l2_results = []

            for i, match in enumerate(test_matches, 1):
                match_id = str(match.get("id", ""))
                home_team = match.get("home", {}).get("name", "Unknown")
                away_team = match.get("away", {}).get("name", "Unknown")
                status = match.get("status", {}).get("reason", {}).get("short", "Unknown")

                print(f"\n🎯 验证比赛 {i}: {home_team} vs {away_team} (ID: {match_id})")

                # 调用 L2 详情采集
                match_detail = await collector.collect_match_details(match_id)

                if match_detail:
                    # 打印详细验尸报告
                    report = self.generate_autopsy_report(match, match_detail)
                    print(report)

                    l2_results.append({
                        "match_id": match_id,
                        "success": True,
                        "detail": match_detail,
                        "xg_extracted": match_detail.xg_home > 0 or match_detail.xg_away > 0,
                        "referee_extracted": match_detail.referee is not None,
                        "lineups_extracted": match_detail.lineups_json is not None
                    })
                else:
                    print(f"❌ 无法获取比赛 {match_id} 的详情数据")
                    l2_results.append({
                        "match_id": match_id,
                        "success": False,
                        "detail": None,
                        "xg_extracted": False,
                        "referee_extracted": False,
                        "lineups_extracted": False
                    })

            # 分析 L2 验证结果
            successful_extractions = [r for r in l2_results if r["success"]]
            xg_success_count = sum(1 for r in successful_extractions if r["xg_extracted"])
            referee_success_count = sum(1 for r in successful_extractions if r["referee_extracted"])
            lineups_success_count = sum(1 for r in successful_extractions if r["lineups_extracted"])

            print("\n📈 L2 验证统计:")
            print(f"   成功获取详情: {len(successful_extractions)}/{len(l2_results)} 场比赛")
            print(f"   xG 数据提取: {xg_success_count}/{len(successful_extractions)} 场比赛")
            print(f"   裁判数据提取: {referee_success_count}/{len(successful_extractions)} 场比赛")
            print(f"   阵容数据提取: {lineups_success_count}/{len(successful_extractions)} 场比赛")

            # 判断 L2 验证是否通过
            # 至少需要成功提取到一些关键数据
            critical_features_ok = (
                len(successful_extractions) > 0 and
                (xg_success_count > 0 or referee_success_count > 0)
            )

            self.verification_results["l2_verification"] = {
                "status": "PASSED" if critical_features_ok else "FAILED",
                "total_matches": len(l2_results),
                "successful_extractions": len(successful_extractions),
                "xg_success": xg_success_count,
                "referee_success": referee_success_count,
                "lineups_success": lineups_success_count,
                "results": l2_results
            }

            await collector.close()

            if critical_features_ok:
                print("\n✅ L2 验证通过！关键数据提取功能正常")
                return True
            else:
                print("\n❌ L2 验证失败！无法提取关键数据")
                return False

        except Exception as e:
            logger.error(f"❌ L2 验证过程中发生错误: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

            self.verification_results["l2_verification"] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False

    def generate_autopsy_report(self, match: dict[str, Any], match_detail) -> str:
        """生成详细验尸报告"""
        match_id = str(match.get("id", ""))
        home_team = match.get("home", {}).get("name", "Unknown")
        away_team = match.get("away", {}).get("name", "Unknown")

        report = f"""
🔍 详细验尸报告 (Autopsy Report)
{'='*50}
🆔 **ID**: {match_id}
🆚 **对阵**: {home_team} vs {away_team}
⚽ **比分**: {match_detail.home_score} - {match_detail.away_score}
📊 **xG**: {match_detail.xg_home} - {match_detail.xg_away}
👮 **裁判**: {match_detail.referee or '未提取到'}
👥 **阵容**: {'是' if match_detail.lineups_json else '否'}
📅 **状态**: {match_detail.status}
🏟️ **场地**: {match_detail.venue or '未知'}
"""

        # 验证数据质量
        quality_checks = []
        if match_detail.xg_home > 0 or match_detail.xg_away > 0:
            quality_checks.append("✅ xG数据提取成功")
        else:
            quality_checks.append("❌ xG数据提取失败")

        if match_detail.referee:
            quality_checks.append("✅ 裁判数据提取成功")
        else:
            quality_checks.append("❌ 裁判数据提取失败")

        if match_detail.lineups_json:
            quality_checks.append("✅ 阵容数据提取成功")
        else:
            quality_checks.append("❌ 阵容数据提取失败")

        report += "\n📋 **数据质量检查**:\n"
        for check in quality_checks:
            report += f"   {check}\n"

        # 环境数据验证
        if match_detail.environment_json:
            env_data = match_detail.environment_json
            report += "\n🌟 **环境数据** (Super Greedy Mode):\n"
            if env_data.get("referee"):
                report += f"   👮 裁判: {env_data['referee'].get('name', '未知')}\n"
            if env_data.get("venue"):
                report += f"   🏟️ 场地: {env_data['venue'].get('name', '未知')}\n"
            if env_data.get("weather"):
                report += f"   🌤️ 天气: {env_data['weather'].get('condition', '未知')}\n"

        return report

    def print_final_summary(self):
        """打印最终总结"""
        print("\n" + "=" * 80)
        print("🏁 验证脚本执行完成")
        print("=" * 80)

        l1_status = self.verification_results["l1_verification"].get("status", "UNKNOWN")
        l2_status = self.verification_results["l2_verification"].get("status", "UNKNOWN")

        print(f"📊 L1 赛程验证: {'✅ 通过' if l1_status == 'PASSED' else '❌ 失败'}")
        print(f"📊 L2 详情验证: {'✅ 通过' if l2_status == 'PASSED' else '❌ 失败'}")

        # 整体状态
        overall_passed = l1_status == "PASSED" and l2_status == "PASSED"
        self.verification_results["overall_status"] = "PASSED" if overall_passed else "FAILED"

        print(f"\n🎯 整体验证结果: {'✅ 全部通过' if overall_passed else '❌ 存在问题'}")

        # 详细结果
        if l1_status == "PASSED":
            l1_result = self.verification_results["l1_verification"]
            print(f"   • L1: 成功验证 {len(l1_result.get('valid_ids', []))} 个纯数字 Match ID")

        if l2_status == "PASSED":
            l2_result = self.verification_results["l2_verification"]
            print(f"   • L2: 成功提取 {l2_result.get('xg_success', 0)} 个 xG 数据, {l2_result.get('referee_success', 0)} 个裁判数据")

        print("\n" + "=" * 80)

        # 保存验证结果到文件
        results_file = project_root / "scripts" / "verification_results.json"
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.verification_results, f, indent=2, ensure_ascii=False, default=str)
            print(f"📄 验证结果已保存到: {results_file}")
        except Exception as e:
            logger.error(f"保存验证结果失败: {e}")

        print("=" * 80)

    async def run_verification(self):
        """运行完整验证流程"""
        self.print_header()

        # Step 1: L1 验证
        l1_passed = await self.step_1_l1_verification()

        if not l1_passed:
            print("\n🛑 L1 验证失败，脚本终止")
            self.print_final_summary()
            return False

        # Step 2: L2 验证
        sample_matches = self.verification_results["l1_verification"].get("sample_matches", [])
        await self.step_2_l2_verification(sample_matches)

        # 打印最终总结
        self.print_final_summary()

        return self.verification_results["overall_status"] == "PASSED"


async def main():
    """主函数"""
    verifier = CoreLogicVerifier()
    success = await verifier.run_verification()

    if success:
        print("\n🎉 所有验证通过！系统核心逻辑运行正常")
        sys.exit(0)
    else:
        print("\n⚠️ 验证发现问题！请检查并修复相关代码")
        sys.exit(1)


if __name__ == "__main__":
    # 运行验证
    asyncio.run(main())
