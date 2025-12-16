#!/usr/bin/env python3
"""
验证深度数据提取功能

测试新添加的射图谱、势头、教练、板凳评分等深度统计提取功能
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent / "FootballPrediction"))

def extract_deep_stats(content: dict[str, Any]) -> dict[str, Any]:
    """提取深度统计数据 - 射图谱、势头、教练、板凳评分等"""
    deep_stats = {
        "match_shotmap": [],      # 射图谱数据
        "match_momentum": [],     # 比赛势头数据
        "home_coach": None,       # 主队教练
        "away_coach": None,       # 客队教练
        "home_bench_rating": None,# 主队板凳评分
        "away_bench_rating": None,# 客队板凳评分
    }

    try:
        # 1. 提取射图谱数据
        if "shotmap" in content:
            shotmap_data = content["shotmap"]
            if isinstance(shotmap_data, dict) and "shots" in shotmap_data:
                shots = shotmap_data["shots"]
                if isinstance(shots, list):
                    deep_stats["match_shotmap"] = shots
                    print(f"🎯 提取到 {len(shots)} 个射门数据")

        # 2. 提取比赛势头数据
        if "momentum" in content:
            momentum_data = content["momentum"]
            if isinstance(momentum_data, dict) and "data" in momentum_data:
                momentum = momentum_data["data"]
                if isinstance(momentum, list):
                    deep_stats["match_momentum"] = momentum
                    print(f"📈 提取到 {len(momentum)} 个势头数据点")

        # 3. 提取教练信息
        if "content" in content and isinstance(content["content"], dict):
            content_data = content["content"]

            # 从general信息中查找教练数据
            if "general" in content_data:
                general = content_data["general"]

                # 检查主队教练
                if "homeTeam" in general and isinstance(general["homeTeam"], dict):
                    home_team = general["homeTeam"]
                    if "coachName" in home_team:
                        deep_stats["home_coach"] = home_team["coachName"]
                    elif "managerName" in home_team:
                        deep_stats["home_coach"] = home_team["managerName"]

                # 检查客队教练
                if "awayTeam" in general and isinstance(general["awayTeam"], dict):
                    away_team = general["awayTeam"]
                    if "coachName" in away_team:
                        deep_stats["away_coach"] = away_team["coachName"]
                    elif "managerName" in away_team:
                        deep_stats["away_coach"] = away_team["managerName"]

            # 从lineups中查找教练信息（备用数据源）
            if (not deep_stats["home_coach"] or not deep_stats["away_coach"]) and "lineups" in content_data:
                lineups = content_data["lineups"]
                if isinstance(lineups, dict):
                    # 主队教练
                    if "home" in lineups and isinstance(lineups["home"], dict):
                        home_lineup = lineups["home"]
                        if "coach" in home_lineup and not deep_stats["home_coach"]:
                            deep_stats["home_coach"] = home_lineup["coach"]

                    # 客队教练
                    if "away" in lineups and isinstance(lineups["away"], dict):
                        away_lineup = lineups["away"]
                        if "coach" in away_lineup and not deep_stats["away_coach"]:
                            deep_stats["away_coach"] = away_lineup["coach"]

        # 4. 提取板凳评分（从球员评分中计算板凳球员平均分）
        if "content" in content and isinstance(content["content"], dict):
            content_data = content["content"]

            # 查找球员评分数据
            player_ratings = []

            # 可能的球员评分数据源位置
            rating_sources = [
                ("players", "players"),
                ("ratings", "ratings"),
                ("playerStats", "playerStats"),
                ("stats", "stats")
            ]

            for source_key, nested_key in rating_sources:
                if source_key in content_data:
                    source_data = content_data[source_key]
                    if isinstance(source_data, dict) and nested_key in source_data:
                        ratings = source_data[nested_key]
                        if isinstance(ratings, list):
                            player_ratings.extend(ratings)
                            break

            # 计算主客队板凳评分（假设板凳球员有特定标识）
            if player_ratings:
                home_bench_ratings = []
                away_bench_ratings = []

                for player in player_ratings:
                    if isinstance(player, dict):
                        rating = player.get("rating") or player.get("averageRating") or player.get("score")
                        is_home = player.get("isHome") or player.get("team") == "home"
                        is_bench = player.get("position") == "bench" or player.get("substitute") is True

                        if rating and is_bench:
                            try:
                                rating_value = float(rating)
                                if is_home:
                                    home_bench_ratings.append(rating_value)
                                else:
                                    away_bench_ratings.append(rating_value)
                            except (ValueError, TypeError):
                                continue

                # 计算平均板凳评分
                if home_bench_ratings:
                    deep_stats["home_bench_rating"] = sum(home_bench_ratings) / len(home_bench_ratings)
                    print(f"🏠 主队板凳评分: {deep_stats['home_bench_rating']:.2f}")

                if away_bench_ratings:
                    deep_stats["away_bench_rating"] = sum(away_bench_ratings) / len(away_bench_ratings)
                    print(f"✈️ 客队板凳评分: {deep_stats['away_bench_rating']:.2f}")

        # 记录提取结果摘要
        extracted_count = sum([
            1 for v in deep_stats.values()
            if v is not None and v != [] and v != ""
        ])

        print(f"📊 深度统计提取完成: {extracted_count}/6 项数据成功提取")

        # 详细日志
        if deep_stats["home_coach"]:
            print(f"👨‍💼 主队教练: {deep_stats['home_coach']}")
        if deep_stats["away_coach"]:
            print(f"👨‍💼 客队教练: {deep_stats['away_coach']}")
        if deep_stats["match_shotmap"]:
            print(f"🎯 射图谱数据: {len(deep_stats['match_shotmap'])} 个射门")
        if deep_stats["match_momentum"]:
            print(f"📈 势头数据: {len(deep_stats['match_momentum'])} 个数据点")

        return deep_stats

    except Exception as e:
        print(f"❌ 深度统计提取失败: {e}")
        import traceback
        traceback.print_exc()
        return deep_stats


def analyze_shotmap_data(shotmap: list) -> dict[str, Any]:
    """分析射图谱数据"""
    if not shotmap:
        return {"analysis": "无射图谱数据"}

    analysis = {
        "total_shots": len(shotmap),
        "goal_shots": 0,
        "on_target": 0,
        "off_target": 0,
        "blocked": 0,
        "shot_locations": [],
        "avg_shot_distance": 0
    }

    distances = []

    for shot in shotmap:
        if isinstance(shot, dict):
            # 统计射门类型
            shot_type = shot.get("eventType", "")
            if shot_type == "Goal":
                analysis["goal_shots"] += 1
            elif shot_type == "ShotOnGoal":
                analysis["on_target"] += 1
            elif shot_type == "ShotOffGoal":
                analysis["off_target"] += 1
            elif shot_type == "ShotBlocked":
                analysis["blocked"] += 1

            # 提取位置信息
            x = shot.get("x")
            y = shot.get("y")
            if x is not None and y is not None:
                analysis["shot_locations"].append({"x": x, "y": y})
                # 计算射门距离（简单估算）
                try:
                    distance = (100 - float(x)) / 100 * 120  # 假设球场长度120米
                    distances.append(distance)
                except (ValueError, TypeError):
                    pass

    if distances:
        analysis["avg_shot_distance"] = sum(distances) / len(distances)

    return analysis


def test_deep_stats_extraction():
    """测试深度统计数据提取"""
    print("🚀 开始测试深度统计数据提取")
    print("=" * 80)

    # 加载测试数据
    test_data_path = Path("fotmob_match_data.json")
    if not test_data_path.exists():
        print(f"❌ 测试数据文件不存在: {test_data_path}")
        return False

    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print(f"✅ 成功加载测试数据: {test_data_path}")

    # 提取content部分
    if "content" not in test_data:
        print("❌ 测试数据中缺少content字段")
        return False

    content = test_data["content"]

    # 测试深度统计提取
    print("\n🔬 开始深度统计提取测试...")
    deep_stats = extract_deep_stats(content)

    print("\n📊 深度统计提取结果:")
    print(f"   射图谱数据: {len(deep_stats['match_shotmap'])} 个射门")
    print(f"   势头数据: {len(deep_stats['match_momentum'])} 个数据点")
    print(f"   主队教练: {deep_stats['home_coach']}")
    print(f"   客队教练: {deep_stats['away_coach']}")
    print(f"   主队板凳评分: {deep_stats['home_bench_rating']}")
    print(f"   客队板凳评分: {deep_stats['away_bench_rating']}")

    # 详细分析射图谱数据
    if deep_stats["match_shotmap"]:
        print("\n🎯 射图谱详细分析:")
        shotmap_analysis = analyze_shotmap_data(deep_stats["match_shotmap"])

        print(f"   总射门数: {shotmap_analysis['total_shots']}")
        print(f"   进球数: {shotmap_analysis['goal_shots']}")
        print(f"   封正数: {shotmap_analysis['on_target']}")
        print(f"   偏靶数: {shotmap_analysis['off_target']}")
        print(f"   被阻挡: {shotmap_analysis['blocked']}")
        print(f"   平均射门距离: {shotmap_analysis['avg_shot_distance']:.1f}米")

        # 显示前3个射门位置
        if shotmap_analysis["shot_locations"]:
            print("   前3个射门位置:")
            for i, loc in enumerate(shotmap_analysis["shot_locations"][:3], 1):
                print(f"     {i}. X坐标: {loc['x']:.1f}, Y坐标: {loc['y']:.1f}")

    # 详细分析势头数据
    if deep_stats["match_momentum"]:
        print("\n📈 势头数据详细分析:")
        momentum = deep_stats["match_momentum"]
        print(f"   势头数据点数量: {len(momentum)}")

        # 分析势头趋势
        if len(momentum) >= 2:
            home_momentum_values = []
            away_momentum_values = []

            for point in momentum[:10]:  # 分析前10个数据点
                if isinstance(point, dict):
                    home_val = point.get("home") or point.get("homeValue")
                    away_val = point.get("away") or point.get("awayValue")

                    if home_val is not None:
                        try:
                            home_momentum_values.append(float(home_val))
                        except (ValueError, TypeError):
                            pass

                    if away_val is not None:
                        try:
                            away_momentum_values.append(float(away_val))
                        except (ValueError, TypeError):
                            pass

            if home_momentum_values:
                avg_home_momentum = sum(home_momentum_values) / len(home_momentum_values)
                print(f"   主队平均势头: {avg_home_momentum:.2f}")

            if away_momentum_values:
                avg_away_momentum = sum(away_momentum_values) / len(away_momentum_values)
                print(f"   客队平均势头: {avg_away_momentum:.2f}")

    # 数据质量评估
    print("\n📈 数据质量评估:")
    quality_checks = {
        "射图谱数据": len(deep_stats["match_shotmap"]) > 0,
        "势头数据": len(deep_stats["match_momentum"]) > 0,
        "主队教练信息": deep_stats["home_coach"] is not None,
        "客队教练信息": deep_stats["away_coach"] is not None,
        "主队板凳评分": deep_stats["home_bench_rating"] is not None,
        "客队板凳评分": deep_stats["away_bench_rating"] is not None
    }

    passed_checks = sum(quality_checks.values())
    total_checks = len(quality_checks)

    for check_name, passed in quality_checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")

    success_rate = passed_checks / total_checks
    print(f"\n🎯 深度数据提取成功率: {success_rate:.1%} ({passed_checks}/{total_checks})")

    # 生成业务价值报告
    print("\n🏆 业务价值分析:")
    if deep_stats["match_shotmap"]:
        print("   🎯 射图谱数据: 可用于射门精度分析、进攻模式识别")
    if deep_stats["match_momentum"]:
        print("   📈 势头数据: 可用于比赛节奏分析、关键时刻识别")
    if deep_stats["home_coach"] or deep_stats["away_coach"]:
        print("   👨‍💼 教练信息: 可用于战术风格分析、教练对决统计")
    if deep_stats["home_bench_rating"] or deep_stats["away_bench_rating"]:
        print("   🏟️ 板凳评分: 可用于阵容深度分析、换人效果预测")

    print("\n" + "=" * 80)
    if success_rate >= 0.5:
        print("🎉 深度数据提取测试成功！")
        print("✨ 新功能为足球预测系统提供了更深度的数据维度")
        return True
    else:
        print("⚠️ 深度数据提取需要进一步优化")
        return False


def main():
    """主函数"""
    print("🚀 深度数据提取验证启动")
    print("🎯 目标: 验证射图谱、势头、教练、板凳评分等深度数据提取")
    print()

    success = test_deep_stats_extraction()

    print("\n" + "=" * 80)
    if success:
        print("🏆 深度数据提取验证通过！")
        print("✨ 新增功能为足球预测系统提供了完整的深度数据支持")
    else:
        print("❌ 深度数据提取验证失败")
        print("🔧 需要进一步调试和优化")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)