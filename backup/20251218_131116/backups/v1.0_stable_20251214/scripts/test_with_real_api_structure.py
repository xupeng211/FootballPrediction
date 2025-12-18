#!/usr/bin/env python3
"""
使用真实API结构测试解析器
Test Parser with Real API Structure

使用模拟的真实API响应数据结构来验证修复后的解析逻辑
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

# 直接导入修复后的采集器
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'collectors'))

from fotmob_api_collector import FotMobAPICollector

def test_with_real_api_structure():
    """使用真实API结构测试解析器"""
    logger.info("🚀 使用真实API结构测试解析器")
    logger.info("=" * 60)

    # 🔥 构造一个真实的API响应结构（基于FotMob MatchDetails API的实际格式）
    real_api_response = {
        "header": {
            "status": {
                "reason": {"short": "Finished"}
            },
            "teams": [
                {
                    "id": 8456,
                    "name": "Manchester City",
                    "score": 3,
                    "shortName": "Man City",
                    "img": "https://www.fotmob.com/_next/static/image/team/8456.png"
                },
                {
                    "id": 9825,
                    "name": "Arsenal",
                    "score": 1,
                    "shortName": "Arsenal",
                    "img": "https://www.fotmob.com/_next/static/image/team/9825.png"
                }
            ],
            "matchTimeUTCDate": "2025-12-08T20:00:00Z",
            "matchId": "4329053"
        },
        "general": {
            "matchTimeUTCDate": "2025-12-08T20:00:00Z",
            "venue": {
                "id": 1234,
                "name": "Etihad Stadium",
                "city": "Manchester",
                "country": "England",
                "capacity": 55097
            },
            "referee": {
                "id": 5678,
                "name": "Michael Oliver",
                "country": "England",
                "cardsThisSeason": {
                    "yellowCards": 45,
                    "redCards": 2
                }
            },
            "weather": {
                "temp": 12,
                "condition": "Cloudy",
                "wind": 8,
                "humidity": 75,
                "pitchCondition": "Good"
            },
            "attendance": 55097,
            "homeTeam": {
                "id": 8456,
                "name": "Manchester City"
            },
            "awayTeam": {
                "id": 9825,
                "name": "Arsenal"
            },
            "leagueId": 47,
            "leagueName": "Premier League",
            "season": "2024/2025",
            "round": {
                "roundName": "Matchweek 16",
                "roundNumber": 16
            }
        },
        "content": {
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [
                            {
                                "key": "expected_goals",
                                "stats": [
                                    {
                                        "key": "xg",
                                        "stats": [2.21, 1.85]  # 🔍 关键xG数据
                                    }
                                ]
                            },
                            {
                                "key": "ball_possession_shared",
                                "stats": [
                                    {
                                        "key": "possession",
                                        "stats": [58, 42]  # 控球率
                                    }
                                ]
                            },
                            {
                                "key": "total_shots",
                                "stats": [
                                    {
                                        "key": "shots_total",
                                        "stats": [15, 8]  # 射门数据
                                    },
                                    {
                                        "key": "shots_on_target",
                                        "stats": [7, 4]  # 射正数据
                                    }
                                ]
                            },
                            {
                                "key": "total_passes",
                                "stats": [
                                    {
                                        "key": "total_passes",
                                        "stats": [520, 380]  # 传球数据
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
            "lineup": {
                "homeTeam": {
                    "formation": "4-3-3",
                    "starters": [
                        {
                            "id": 1,
                            "name": "Ederson",
                            "position": "GK",
                            "rating": 7.2
                        },
                        {
                            "id": 2,
                            "name": "Walker",
                            "position": "RB",
                            "rating": 6.8
                        }
                    ],
                    "bench": [],
                    "manager": {
                        "id": 123,
                        "name": "Pep Guardiola",
                        "age": 53,
                        "nationality": "Spanish"
                    }
                },
                "awayTeam": {
                    "formation": "4-4-2",
                    "starters": [
                        {
                            "id": 1,
                            "name": "Raya",
                            "position": "GK",
                            "rating": 6.5
                        }
                    ],
                    "bench": [],
                    "manager": {
                        "id": 456,
                        "name": "Mikel Arteta",
                        "age": 42,
                        "nationality": "Spanish"
                    }
                }
            }
        }
    }

    try:
        # 创建采集器实例
        collector = FotMobAPICollector()

        logger.info("🔍 开始解析真实API结构数据...")

        # 调用修复后的解析方法
        match_data = collector._parse_match_data("4329053", real_api_response)

        # 验证解析结果
        verification_results = {
            "basic_info_parsed": False,
            "team_names_correct": False,
            "score_correct": False,
            "xg_data_parsed": False,
            "stats_json_complete": False,
            "referee_data_parsed": False,
            "venue_data_parsed": False,
            "lineup_data_parsed": False,
        }

        logger.info("📊 解析结果验证:")

        # 验证基础信息
        if match_data:
            verification_results["basic_info_parsed"] = True
            logger.info("✅ 基础信息解析成功")
            logger.info(f"   fotmob_id: {match_data.fotmob_id}")
            logger.info(f"   status: {match_data.status}")
            logger.info(f"   venue: {match_data.venue}")
            logger.info(f"   match_time: {match_data.match_time}")

        # 验证主客队信息
        match_info = match_data.match_info or {}
        home_team = match_info.get("home_team_name")
        away_team = match_info.get("away_team_name")

        if home_team == "Manchester City" and away_team == "Arsenal":
            verification_results["team_names_correct"] = True
            logger.info(f"✅ 主客队名解析正确: {home_team} vs {away_team}")
        else:
            logger.error(f"❌ 主客队名解析错误: {home_team} vs {away_team}")

        # 验证比分
        if match_data.home_score == 3 and match_data.away_score == 1:
            verification_results["score_correct"] = True
            logger.info(f"✅ 比分解析正确: {match_data.home_score}-{match_data.away_score}")
        else:
            logger.error(f"❌ 比分解析错误: {match_data.home_score}-{match_data.away_score}")

        # 验证xG数据
        stats_json = match_data.stats_json or {}
        xg_data = stats_json.get("xg", {})
        if xg_data and "xg" in xg_data:
            xg_values = xg_data["xg"]
            if len(xg_values) >= 2:
                home_xg, away_xg = xg_values[0], xg_values[1]
                if abs(home_xg - 2.21) < 0.01 and abs(away_xg - 1.85) < 0.01:
                    verification_results["xg_data_parsed"] = True
                    logger.info(f"✅ xG数据解析正确: {home_xg} vs {away_xg}")
                else:
                    logger.error(f"❌ xG数据解析错误: {home_xg} vs {away_xg}")

        # 验证统计数据完整性
        if stats_json and len(stats_json) > 0:
            expected_categories = ["xg", "possession", "shots", "passes"]
            found_categories = [cat for cat in expected_categories if cat in stats_json and stats_json[cat]]
            if len(found_categories) >= 3:
                verification_results["stats_json_complete"] = True
                logger.info(f"✅ 统计数据完整，找到类别: {found_categories}")

        # 验证裁判信息
        environment_json = match_data.environment_json or {}
        referee_info = environment_json.get("referee", {})
        if referee_info and referee_info.get("name") == "Michael Oliver":
            verification_results["referee_data_parsed"] = True
            logger.info(f"✅ 裁判信息解析正确: {referee_info.get('name')}")

        # 验证场地信息
        if match_data.venue == "Etihad Stadium":
            verification_results["venue_data_parsed"] = True
            logger.info(f"✅ 场地信息解析正确: {match_data.venue}")

        # 验证阵容数据
        lineup_json = match_data.lineups_json or {}
        home_lineup = lineup_json.get("home_team", {})
        away_lineup = lineup_json.get("away_team", {})
        if (home_lineup.get("formation") == "4-3-3" and
            away_lineup.get("formation") == "4-4-2"):
            verification_results["lineup_data_parsed"] = True
            logger.info("✅ 阵容数据解析正确")

        # 显示详细的解析结果
        logger.info("\n📋 详细解析结果:")
        logger.info(f"   MatchDetailData 对象: fotmob_id={match_data.fotmob_id}, home_score={match_data.home_score}, away_score={match_data.away_score}")
        logger.info(f"   match_info keys: {list(match_info.keys()) if match_info else []}")
        logger.info(f"   stats_json keys: {list(stats_json.keys()) if stats_json else []}")
        logger.info(f"   environment_json keys: {list(environment_json.keys()) if environment_json else []}")

        # 计算总体通过率
        passed_tests = sum(verification_results.values())
        total_tests = len(verification_results)
        success_rate = passed_tests / total_tests * 100

        logger.info(f"\n📊 总体验证通过率: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

        # 关键验收标准
        critical_tests = [
            ("主队名正确", "team_names_correct"),
            ("xG数据正确", "xg_data_parsed"),
            ("裁判信息正确", "referee_data_parsed"),
        ]

        logger.info("\n🎯 关键验收标准:")
        all_critical_passed = True
        for display_name, test_key in critical_tests:
            passed = verification_results[test_key]
            status = "✅ 通过" if passed else "❌ 失败"
            logger.info(f"   {display_name}: {status}")
            if not passed:
                all_critical_passed = False

        if all_critical_passed:
            logger.info("\n🎉 ✅ 关键验收标准全部通过!")
            logger.info("🚀 修复后的解析器能够正确处理真实API结构")
            return True
        else:
            logger.error("\n💥 ❌ 关键验收标准未通过!")
            failed_tests = [display_name for display_name, test_key in critical_tests if not verification_results[test_key]]
            logger.error(f"❌ 失败的测试: {failed_tests}")
            return False

    except Exception as e:
        logger.error(f"❌ 测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_with_real_api_structure()

    if success:
        print("\n" + "="*60)
        print("🎉 ✅ 解析器验证成功!")
        print("✅ 修复后的代码能够正确处理真实API数据结构")
        print("🚀 系统已准备好处理真实的比赛数据")
        exit(0)
    else:
        print("\n" + "="*60)
        print("💥 ❌ 解析器验证失败!")
        print("❌ 代码仍需要进一步修复")
        exit(1)
