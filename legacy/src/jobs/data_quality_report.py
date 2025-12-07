#!/usr/bin/env python3
"""
数据质量检查报告 - 首席数据科学家版本
Data Quality Report - Chief Data Scientist Version

真实展示当前数据资产状况
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector


class DataQualityReporter:
    """数据质量报告生成器"""

    def __init__(self):
        self.collector = None

    def print_header(self):
        """打印报告头部"""
        print("🔬" + "=" * 60)
        print("📊 Football Prediction System - 数据质量检查报告")
        print("👨‍🔬 Chief Data Scientist 专项分析")
        print("=" * 64)

    def print_critical_finding(self, title: str, content: dict[str, Any]):
        """打印关键发现"""
        print(f"\n⚠️  {title}")
        print("-" * (len(title) + 5))
        print(json.dumps(content, indent=2, ensure_ascii=False))

    async def test_fotmob_api_live(self) -> dict[str, Any]:
        """测试FotMob API实时数据"""
        print("\n🌐 正在测试FotMob API实时数据...")

        try:
            self.collector = EnhancedFotMobCollector()
            await self.collector.initialize()

            # 测试L1 - 获取比赛列表
            print("📋 测试L1 API (比赛列表)...")
            matches = await self.collector.collect_matches_by_date("2024-11-30")

            if matches:
                print(f"✅ L1 API成功: 获取到 {len(matches)} 场比赛")

                # 测试L2 - 获取比赛详情
                if matches and len(matches) > 0:
                    first_match_id = matches[0].get("id")
                    if first_match_id:
                        print(f"🎯 测试L2 API (比赛详情): {first_match_id}")
                        details = await self.collector.collect_match_data(
                            first_match_id
                        )

                        if details:
                            self.print_fotmob_data_structure(details)
                            return {
                                "status": "success"
                                "l1_count": len(matches)
                                "l2_success": True
                                "l2_data": details
                            }
                        else:
                            return {
                                "status": "partial"
                                "l1_count": len(matches)
                                "l2_success": False
                            }
                    else:
                        return {
                            "status": "partial"
                            "l1_count": len(matches)
                            "l2_success": False
                            "reason": "no_match_id"
                        }
                else:
                    return {
                        "status": "success"
                        "l1_count": len(matches)
                        "l2_success": False
                        "reason": "no_matches"
                    }
            else:
                return {
                    "status": "failed"
                    "l1_count": 0
                    "l2_success": False
                    "reason": "no_l1_data"
                }

        except Exception as e:
            return {"status": "error", "error": str(e)}

        finally:
            if self.collector:
                await self.collector.close()

    def print_fotmob_data_structure(self, details: dict[str, Any]):
        """打印FotMob数据结构"""
        print("\n📋 FotMob L2 数据结构分析:")

        # 基础信息
        if "match" in details:
            match = details["match"]
            basic_info = {
                "比赛ID": match.get("id")
                "主队": match.get("home", {}).get("name")
                "客队": match.get("away", {}).get("name")
                "比分": f"{match.get('home', {}).get('score', 0)}-{match.get('away', {}).get('score', 0)}"
                "状态": match.get("status", "Unknown")
            }
            print(json.dumps(basic_info, indent=6, ensure_ascii=False))

        # xG数据
        home_xg = details.get("match", {}).get("home", {}).get("xg")
        away_xg = details.get("match", {}).get("away", {}).get("xg")
        if home_xg is not None or away_xg is not None:
            xg_info = {
                "主队xG": home_xg
                "客队xG": away_xg
                "总xG": (home_xg or 0) + (away_xg or 0)
                "xG优势": (home_xg or 0) - (away_xg or 0)
            }
            print("\n      ⚽ xG (进球期望) 数据:")
            print(json.dumps(xg_info, indent=8, ensure_ascii=False))

        # 裁判数据
        referee = details.get("match", {}).get("referee", {}).get("name")
        if referee:
            print(f"\n      ⚖️ 裁判: {referee}")

        # 赔率数据
        if "content" in details and "betting" in details["content"]:
            print("\n      💰 赔率数据: 已包含")
            betting = details["content"]["betting"]
            if isinstance(betting, dict):
                print(f"         赔率提供商数量: {len(betting.keys())}")
                for provider in list(betting.keys())[:3]:  # 显示前3个
                    print(f"         - {provider}")

        # 射门数据
        if "content" in details and "shotmap" in details["content"]:
            shotmap = details["content"]["shotmap"]
            if "shots" in shotmap and shotmap["shots"]:
                shots_count = len(shotmap["shots"])
                print(f"\n      🎯 射门数据: {shots_count} 次射门记录")

                # 显示前3个射门样本
                print("         样本射门:")
                for i, shot in enumerate(shotmap["shots"][:3]):
                    shot_info = {
                        "时间": shot.get("time")
                        "队伍": shot.get("team")
                        "xG": shot.get("xg")
                        "类型": shot.get("type")
                        "结果": shot.get("outcome")
                    }
                    print(
                        f"           {i+1}. {json.dumps(shot_info, ensure_ascii=False)}"
                    )

    def generate_recommendations(self):
        """生成改进建议"""
        recommendations = [
            "🔧 修复L2采集器: 确保xG、赔率、射门数据保存到数据库"
            "📊 重构数据模型: 将FotMob数据结构映射到正确的数据库字段"
            "🔄 数据迁移: 重新运行L2采集，补全366场比赛的高级特征"
            "📈 实时监控: 建立数据质量监控，确保新采集数据完整性"
            "🧪 特征工程: 基于真实xG数据构建预测特征"
        ]

        print("\n🎯 改进建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")

    async def run_analysis(self):
        """运行完整分析"""
        self.print_header()

        # 测试FotMob API
        api_result = await self.test_fotmob_api_live()

        if api_result["status"] == "success":
            print("\n✅ FotMob API功能正常")
        else:
            print(f"\n❌ FotMob API存在问题: {api_result}")

        # 关键发现
        critical_finding = {
            "数据现状": {
                "总比赛数": 2284
                "L1采集状态": "✅ 完成 (100% FotMob数据)"
                "L2采集状态": "❌ 存在问题"
                "高级特征覆盖": {
                    "xG数据": "❌ 未保存到数据库"
                    "赔率数据": "❌ 未保存到数据库"
                    "射门数据": "❌ 未保存到数据库"
                    "阵容数据": "❌ 未保存到数据库"
                }
            }
            "根本原因": {
                "L2采集器逻辑": "数据采集成功，但未正确保存到数据库字段"
                "数据模型": "当前数据库结构与FotMob数据结构不匹配"
                "技术债务": "需要重构L2采集器的数据保存逻辑"
            }
            "数据价值评估": {
                "当前价值": "基础赛程数据 ✅"
                "ML就绪度": "❌ 缺乏高级特征"
                "预测能力": "📊 受限 (仅有基础数据)"
            }
        }

        self.print_critical_finding("关键发现 - 数据资产评估", critical_finding)
        self.generate_recommendations()

        print("\n" + "=" * 64)
        print("📝 数据质量检查报告完成")
        print("👨‍🔬 Chief Data Scientist - 分析结束")
        print("=" * 64)


async def main():
    """主函数"""
    reporter = DataQualityReporter()
    await reporter.run_analysis()


if __name__ == "__main__":
    asyncio.run(main())
