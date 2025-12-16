#!/usr/bin/env python3
"""
简化的L2特征提取测试

直接测试我们新增的赔率和球员评分提取方法，不依赖复杂的导入路径。
"""

import json
from pathlib import Path

def extract_odds(content):
    """提取赔率数据 - 支持多种赔率数据源"""
    odds_data = {
        "pre_match_home_odds": None,
        "pre_match_draw_odds": None,
        "pre_match_away_odds": None,
        "home_win_probability": None,
        "draw_probability": None,
        "away_win_probability": None
    }

    try:
        # 1. 检查superlive中的赔率数据
        if "superlive" in content:
            superlive = content["superlive"]
            if "odds" in superlive:
                odds = superlive["odds"]
                if isinstance(odds, dict) and "home" in odds:
                    odds_data["pre_match_home_odds"] = odds.get("home")
                    odds_data["pre_match_draw_odds"] = odds.get("draw")
                    odds_data["pre_match_away_odds"] = odds.get("away")

        # 2. 检查betting模块
        if "betting" in content:
            betting = content["betting"]

            # 检查preMatchOdds
            if "preMatchOdds" in betting:
                pre_odds = betting["preMatchOdds"]
                if isinstance(pre_odds, dict):
                    odds_data["pre_match_home_odds"] = pre_odds.get("home") or odds_data["pre_match_home_odds"]
                    odds_data["pre_match_draw_odds"] = pre_odds.get("draw") or odds_data["pre_match_draw_odds"]
                    odds_data["pre_match_away_odds"] = pre_odds.get("away") or odds_data["pre_match_away_odds"]

            # 检查matchOdds
            if "matchOdds" in betting and not odds_data["pre_match_home_odds"]:
                match_odds = betting["matchOdds"]
                if isinstance(match_odds, dict):
                    odds_data["pre_match_home_odds"] = match_odds.get("home")
                    odds_data["pre_match_draw_odds"] = match_odds.get("draw")
                    odds_data["pre_match_away_odds"] = match_odds.get("away")

        # 3. 检查general.bettingOdds
        if "general" in content and isinstance(content["general"], dict):
            general = content["general"]
            if "bettingOdds" in general and not odds_data["pre_match_home_odds"]:
                betting_odds = general["bettingOdds"]
                if isinstance(betting_odds, dict):
                    # 尝试多个可能的字段名
                    home_odds = betting_odds.get("homeWin") or betting_odds.get("home") or betting_odds.get("1")
                    draw_odds = betting_odds.get("draw") or betting_odds.get("X")
                    away_odds = betting_odds.get("awayWin") or betting_odds.get("away") or betting_odds.get("2")

                    odds_data["pre_match_home_odds"] = home_odds or odds_data["pre_match_home_odds"]
                    odds_data["pre_match_draw_odds"] = draw_odds or odds_data["pre_match_draw_odds"]
                    odds_data["pre_match_away_odds"] = away_odds or odds_data["pre_match_away_odds"]

        # 4. 计算隐含概率 (如果有赔率数据)
        if odds_data["pre_match_home_odds"]:
            try:
                home_odds = float(odds_data["pre_match_home_odds"])
                draw_odds = float(odds_data["pre_match_draw_odds"]) if odds_data["pre_match_draw_odds"] else None
                away_odds = float(odds_data["pre_match_away_odds"])

                # 转换为隐含概率 (考虑bookmaker margin)
                if home_odds > 0 and away_odds > 0:
                    odds_data["home_win_probability"] = round(1.0 / home_odds * 100, 2)
                    odds_data["away_win_probability"] = round(1.0 / away_odds * 100, 2)
                    if draw_odds and draw_odds > 0:
                        odds_data["draw_probability"] = round(1.0 / draw_odds * 100, 2)
            except (ValueError, TypeError) as e:
                print(f"赔率数据转换失败: {e}")

        # 5. 数据质量验证
        valid_odds_count = sum([
            1 for v in [odds_data["pre_match_home_odds"], odds_data["pre_match_draw_odds"], odds_data["pre_match_away_odds"]]
            if v is not None and isinstance(v, (int, float)) and v > 1.0
        ])

        if valid_odds_count > 0:
            print(f"✅ 成功提取 {valid_odds_count}/3 项赔率数据")
            return odds_data
        else:
            print("⚠️ 未找到有效赔率数据")
            return odds_data

    except Exception as e:
        print(f"❌ 赔率数据提取失败: {e}")
        return odds_data


def extract_player_ratings(content):
    """提取球员评分数据 - 从playerStats中提取FotMob评分"""
    ratings_data = {
        "home_team_ratings": [],
        "away_team_ratings": [],
        "avg_home_rating": None,
        "avg_away_rating": None,
        "best_home_player": None,
        "best_away_player": None,
        "total_players_rated": 0,
        "team_ratings": {}  # 按teamId分组
    }

    try:
        # 检查playerStats数据
        if "playerStats" not in content:
            print("⚠️ 未找到playerStats数据")
            return ratings_data

        player_stats = content["playerStats"]
        if not isinstance(player_stats, dict):
            print("⚠️ playerStats不是对象格式")
            return ratings_data

        # 遍历球员统计，提取评分
        for player_id, player_info in player_stats.items():
            if not isinstance(player_info, dict):
                continue

            team_id = player_info.get("teamId")
            player_name = player_info.get("name", "Unknown")

            # 检查stats数组
            stats = player_info.get("stats", [])
            if not isinstance(stats, list) or len(stats) == 0:
                continue

            player_rating = None

            # 遍历stats数组，查找评分
            for stat_group in stats:
                if not isinstance(stat_group, dict) or "stats" not in stat_group:
                    continue

                stat_details = stat_group["stats"]
                if isinstance(stat_details, dict):
                    # 查找FotMob评分
                    if "FotMob rating" in stat_details:
                        rating_info = stat_details["FotMob rating"]
                        if isinstance(rating_info, dict) and "stat" in rating_info:
                            stat_value = rating_info["stat"]
                            if isinstance(stat_value, dict) and "value" in stat_value:
                                player_rating = float(stat_value["value"])
                                break

            if player_rating and player_rating > 0:
                player_data = {
                    "player_id": int(player_id),
                    "player_name": player_name,
                    "team_id": team_id,
                    "rating": player_rating
                }

                # 按球队分组
                if team_id not in ratings_data["team_ratings"]:
                    ratings_data["team_ratings"][team_id] = []
                ratings_data["team_ratings"][team_id].append(player_data)

        # 处理球队评分数据
        team_ids = list(ratings_data["team_ratings"].keys())

        if len(team_ids) >= 2:
            # 取前两个球队作为主客队
            home_team_id = team_ids[0]
            away_team_id = team_ids[1]

            ratings_data["home_team_ratings"] = ratings_data["team_ratings"][home_team_id]
            ratings_data["away_team_ratings"] = ratings_data["team_ratings"][away_team_id]

            # 计算主队统计
            home_ratings = [p["rating"] for p in ratings_data["home_team_ratings"]]
            if home_ratings:
                ratings_data["avg_home_rating"] = round(sum(home_ratings) / len(home_ratings), 2)
                best_home = max(ratings_data["home_team_ratings"], key=lambda x: x["rating"])
                ratings_data["best_home_player"] = {
                    "name": best_home["player_name"],
                    "rating": best_home["rating"]
                }

            # 计算客队统计
            away_ratings = [p["rating"] for p in ratings_data["away_team_ratings"]]
            if away_ratings:
                ratings_data["avg_away_rating"] = round(sum(away_ratings) / len(away_ratings), 2)
                best_away = max(ratings_data["away_team_ratings"], key=lambda x: x["rating"])
                ratings_data["best_away_player"] = {
                    "name": best_away["player_name"],
                    "rating": best_away["rating"]
                }

        # 计算总评分球员数
        ratings_data["total_players_rated"] = (
            len(ratings_data["home_team_ratings"]) + len(ratings_data["away_team_ratings"])
        )

        if ratings_data["total_players_rated"] > 0:
            print(f"✅ 成功提取 {ratings_data['total_players_rated']} 名球员评分")
            print(f"   主队平均评分: {ratings_data['avg_home_rating']}")
            print(f"   客队平均评分: {ratings_data['avg_away_rating']}")

            # 显示评分前5名的球员
            all_players = ratings_data["home_team_ratings"] + ratings_data["away_team_ratings"]
            top_players = sorted(all_players, key=lambda x: x["rating"], reverse=True)[:5]
            print("   评分前5名球员:")
            for i, player in enumerate(top_players, 1):
                print(f"     {i}. {player['player_name']}: {player['rating']}")
        else:
            print("⚠️ 未找到有效球员评分数据")

        return ratings_data

    except Exception as e:
        print(f"❌ 球员评分提取失败: {e}")
        import traceback
        traceback.print_exc()
        return ratings_data


def main():
    """主函数 - 测试L2特征提取"""
    print("🚀 开始测试L2增强数据提取功能")
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

    # 1. 测试赔率提取
    print("\n💰 测试赔率数据提取功能...")
    odds_data = extract_odds(content)
    print("📊 赔率提取结果:")
    for key, value in odds_data.items():
        print(f"   {key}: {value}")

    # 2. 测试球员评分提取
    print("\n⭐ 测试球员评分提取功能...")
    ratings_data = extract_player_ratings(content)
    print("📊 球员评分提取结果:")
    print(f"   总评分球员数: {ratings_data['total_players_rated']}")
    print(f"   主队平均评分: {ratings_data['avg_home_rating']}")
    print(f"   客队平均评分: {ratings_data['avg_away_rating']}")

    if ratings_data["best_home_player"]:
        print(f"   主队最佳球员: {ratings_data['best_home_player']['name']} ({ratings_data['best_home_player']['rating']})")

    if ratings_data["best_away_player"]:
        print(f"   客队最佳球员: {ratings_data['best_away_player']['name']} ({ratings_data['best_away_player']['rating']})")

    # 3. 验证数据质量
    print("\n🔍 数据质量评估...")
    has_odds = any(odds_data.values())
    has_ratings = ratings_data["total_players_rated"] > 0

    print(f"   赔率数据: {'✅ 可用' if has_odds else '❌ 不可用'}")
    print(f"   球员评分: {'✅ 可用' if has_ratings else '❌ 不可用'}")

    # 4. 生成ML特征向量示例
    ml_features = {
        "has_odds_data": has_odds,
        "has_ratings_data": has_ratings,
        "total_players": ratings_data["total_players_rated"],
        "home_rating_avg": ratings_data["avg_home_rating"] or 0,
        "away_rating_avg": ratings_data["avg_away_rating"] or 0,
        "rating_advantage": (ratings_data["avg_home_rating"] or 0) - (ratings_data["avg_away_rating"] or 0)
    }

    print("\n🎯 ML特征向量示例:")
    for feature, value in ml_features.items():
        print(f"   {feature}: {value}")

    # 5. 最终评估
    enhanced_features_count = sum([has_odds, has_ratings])

    print("\n" + "=" * 80)
    print(f"📊 L2增强数据评估总结:")
    print(f"   赔率特征: {'✅' if has_odds else '❌'}")
    print(f"   评分特征: {'✅' if has_ratings else '❌'}")
    print(f"   增强特征总数: {enhanced_features_count}/2")

    if enhanced_features_count >= 1:
        print("🎉 L2增强数据提取功能测试成功！")
        print("📈 新功能可以用于:")
        print("   - 赔率转概率: 市场预期分析")
        print("   - 球员评分: 个人表现量化")
        print("   - 评分差异: 球队实力对比")
        print("   - ML特征工程: 丰富预测特征")
        return True
    else:
        print("⚠️ L2增强数据提取功能需要进一步优化")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)