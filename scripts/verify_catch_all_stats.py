#!/usr/bin/env python3
"""
直接验证Catch-All统计数据提取功能

直接使用代码复制的方式验证match_detailed_stats字段提取
"""

import json
from pathlib import Path
from typing import Any, Dict

def extract_deep_stats(content: dict[str, Any]) -> dict[str, Any]:
    """提取深度统计数据 - 射图谱、势头、教练、板凳评分等"""
    deep_stats = {
        "match_shotmap": [],      # 射图谱数据
        "match_momentum": [],     # 比赛势头数据
        "home_coach": None,       # 主队教练
        "away_coach": None,       # 客队教练
        "home_bench_rating": None,# 主队板凳评分
        "away_bench_rating": None,# 客队板凳评分
        "match_detailed_stats": {},  # 🆕 抓取所有详细统计数据 (Catch-All)
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

        # 🆕 6. 提取完整统计数据 (Catch-All Statistics)
        detailed_stats = {}

        # 定义潜在的统计数据源
        stats_sources = [
            ("stats", "stats"),                    # 主要统计数据
            ("matchStats", "matchStats"),          # 比赛统计数据
            ("content", "stats"),                  # 根内容结构中的统计
            ("matchFacts", "stats"),               # 比赛详情中的统计
            ("statistics", "statistics")           # 备用统计字段
        ]

        # 足球关键统计指标关键词
        football_keywords = [
            "Big Chances", "Passes", "Passes Accuracy", "Tackles",
            "Possession", "Shots", "Shots on Target", "xG", "Goals",
            "Assists", "Yellow Cards", "Red Cards", "Fouls", "Corners",
            "Offsides", "Saves", "Crosses", "Interceptions", "Aerials",
            "Dribbles", "Duels", "Dispossessed", "Turnovers"
        ]

        # 按优先级提取统计数据
        for source_key, nested_key in stats_sources:
            stats_data = None

            # 从根级别查找
            if source_key in content:
                source = content[source_key]
                if isinstance(source, dict) and nested_key in source:
                    stats_data = source[nested_key]

            # 从content内部查找
            elif source_key == "content" and "content" in content:
                content_root = content["content"]
                if isinstance(content_root, dict) and nested_key in content_root:
                    stats_data = content_root[nested_key]

            # 如果找到了统计数据
            if stats_data is not None:
                # 验证是否包含足球相关统计数据
                is_football_stats = False

                if isinstance(stats_data, dict):
                    # 检查键名是否包含足球关键词
                    for key in stats_data.keys():
                        if any(keyword.lower() in key.lower() for keyword in football_keywords):
                            is_football_stats = True
                            break
                elif isinstance(stats_data, list) and len(stats_data) > 0:
                    # 如果是列表，检查第一个元素
                    first_item = stats_data[0]
                    if isinstance(first_item, dict):
                        for key in first_item.keys():
                            if any(keyword.lower() in key.lower() for keyword in football_keywords):
                                is_football_stats = True
                                break

                if is_football_stats:
                    detailed_stats = stats_data
                    print(f"📊 找到足球统计数据: 来源={source_key}.{nested_key}")
                    print(f"   数据类型: {type(stats_data)}")
                    if isinstance(stats_data, dict):
                        print(f"   统计字段数量: {len(stats_data)}")
                    break

        # 如果没有找到专门的统计数据，尝试收集所有可能的数值型数据
        if not detailed_stats:
            print("🔍 未找到专门的统计数据，尝试收集数值型数据...")
            collected_data = {}

            # 遍历content寻找可能的数值型统计
            def collect_numeric_data(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key

                        # 检查是否是足球相关字段
                        is_football_field = any(
                            keyword.lower() in key.lower() or keyword.lower() in path.lower()
                            for keyword in football_keywords
                        )

                        if is_football_field:
                            if isinstance(value, (int, float, str)):
                                collected_data[current_path] = value
                            elif isinstance(value, (dict, list)):
                                collect_numeric_data(value, current_path)

                elif isinstance(obj, list) and len(obj) > 0:
                    # 处理列表中的第一个元素
                    collect_numeric_data(obj[0], f"{path}[0]")

            if "content" in content:
                collect_numeric_data(content["content"])

            detailed_stats = collected_data
            if detailed_stats:
                print(f"📈 收集到 {len(detailed_stats)} 个数值型统计字段")

        deep_stats["match_detailed_stats"] = detailed_stats

        # 统计提取结果
        extracted_count = sum([
            1 for v in deep_stats.values()
            if v is not None and v != [] and v != ""
        ])

        print(f"📊 深度统计提取完成: {extracted_count}/7 项数据成功提取")

        # 详细日志
        if deep_stats["home_coach"]:
            print(f"👨‍💼 主队教练: {deep_stats['home_coach']}")
        if deep_stats["away_coach"]:
            print(f"👨‍💼 客队教练: {deep_stats['away_coach']}")
        if deep_stats["match_shotmap"]:
            print(f"🎯 射图谱数据: {len(deep_stats['match_shotmap'])} 个射门")
        if deep_stats["match_momentum"]:
            print(f"📈 势头数据: {len(deep_stats['match_momentum'])} 个数据点")
        if deep_stats["match_detailed_stats"]:
            print(f"📊 详细统计数据: {len(deep_stats['match_detailed_stats'])} 个字段")

        return deep_stats

    except Exception as e:
        print(f"❌ 深度统计提取失败: {e}")
        import traceback
        traceback.print_exc()
        return deep_stats


def test_catch_all_stats_extraction():
    """测试Catch-All统计数据提取"""
    print("🚀 开始测试Catch-All统计数据提取")
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

    print("\n🔬 开始Catch-All统计提取测试...")
    deep_stats = extract_deep_stats(content)

    print("\n📊 Catch-All统计提取结果:")
    print(f"   射图谱数据: {len(deep_stats['match_shotmap'])} 个射门")
    print(f"   势头数据: {len(deep_stats['match_momentum'])} 个数据点")
    print(f"   主队教练: {deep_stats['home_coach']}")
    print(f"   客队教练: {deep_stats['away_coach']}")
    print(f"   主队板凳评分: {deep_stats['home_bench_rating']}")
    print(f"   客队板凳评分: {deep_stats['away_bench_rating']}")
    print(f"   详细统计数据: {len(deep_stats['match_detailed_stats'])} 个字段")

    # 详细分析详细统计数据
    detailed_stats = deep_stats['match_detailed_stats']
    if detailed_stats:
        print(f"\n🎯 详细统计数据内容分析:")
        print(f"   数据源结构: {type(detailed_stats)}")

        if isinstance(detailed_stats, dict):
            print(f"   统计字段数量: {len(detailed_stats)}")

            # 查找关键统计指标
            key_stats = [
                "Big Chances", "Passes", "Passes Accuracy", "Tackles",
                "Possession", "Shots", "Shots on Target", "xG", "Goals",
                "Assists", "Yellow Cards", "Red Cards", "Fouls", "Corners",
                "Offsides", "Saves", "Crosses", "Interceptions", "Aerials"
            ]

            found_stats = []
            for stat in key_stats:
                # 模糊匹配统计字段名
                matching_keys = [k for k in detailed_stats.keys()
                               if stat.lower() in k.lower() or k.lower() in stat.lower()]
                if matching_keys:
                    found_stats.extend(matching_keys)
                    print(f"   ✅ 找到相关统计: {stat} -> {matching_keys}")

            # 显示所有可用的统计字段
            if len(detailed_stats) <= 20:
                print(f"\n📋 所有可用统计字段 ({len(detailed_stats)}个):")
                for i, (key, value) in enumerate(detailed_stats.items(), 1):
                    value_preview = str(value)[:50] if value is not None else "None"
                    print(f"   {i:2d}. {key}: {value_preview}")
            else:
                print(f"\n📋 前20个可用统计字段 (共{len(detailed_stats)}个):")
                for i, (key, value) in enumerate(list(detailed_stats.items())[:20], 1):
                    value_preview = str(value)[:50] if value is not None else "None"
                    print(f"   {i:2d}. {key}: {value_preview}")

            # 检查是否包含关键统计
            success_indicators = [
                any("big chance" in str(k).lower() for k in detailed_stats.keys()),
                any("pass" in str(k).lower() for k in detailed_stats.keys()),
                any("tackle" in str(k).lower() for k in detailed_stats.keys()),
                any("shot" in str(k).lower() for k in detailed_stats.keys()),
                any("possess" in str(k).lower() for k in detailed_stats.keys()),
                any("goal" in str(k).lower() for k in detailed_stats.keys()),
                any("card" in str(k).lower() for k in detailed_stats.keys()),
                any("corner" in str(k).lower() for k in detailed_stats.keys()),
            ]

            catch_all_success = any(success_indicators)

            print(f"\n🎯 Catch-All提取成功指标:")
            print(f"   包含Big Chances: {'✅' if success_indicators[0] else '❌'}")
            print(f"   包含Passes相关: {'✅' if success_indicators[1] else '❌'}")
            print(f"   包含Tackles相关: {'✅' if success_indicators[2] else '❌'}")
            print(f"   包含Shots相关: {'✅' if success_indicators[3] else '❌'}")
            print(f"   包含Possession相关: {'✅' if success_indicators[4] else '❌'}")
            print(f"   包含Goals相关: {'✅' if success_indicators[5] else '❌'}")
            print(f"   包含Cards相关: {'✅' if success_indicators[6] else '❌'}")
            print(f"   包含Corners相关: {'✅' if success_indicators[7] else '❌'}")

            if catch_all_success:
                print(f"\n🎉 Catch-All统计数据提取成功！")
                print(f"✨ 成功捕获到 {len(found_stats)} 个详细足球统计")
                return True
            else:
                print(f"\n⚠️ Catch-All统计数据提取部分成功")
                print(f"🔧 提取到 {len(detailed_stats)} 个字段，但可能不是足球统计")
                return False
        else:
            print(f"   ❌ 详细统计数据格式异常: {type(detailed_stats)}")
            return False
    else:
        print(f"   ❌ 没有提取到详细统计数据")
        return False


def main():
    """主函数"""
    print("🚀 Catch-All统计数据提取验证启动")
    print("🎯 目标: 验证match_detailed_stats字段成功提取Big Chances、Passes等详细统计")
    print()

    success = test_catch_all_stats_extraction()

    print("\n" + "=" * 80)
    if success:
        print("🏆 Catch-All统计数据提取验证通过！")
        print("✨ match_detailed_stats字段成功捕获详细足球统计")
    else:
        print("❌ Catch-All统计数据提取验证失败")
        print("🔧 需要进一步调试数据提取逻辑")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)