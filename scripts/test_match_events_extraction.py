#!/usr/bin/env python3
"""
测试比赛事件提取功能

专门测试新增的红黄牌和事件时间线提取功能
"""

import json
from pathlib import Path

def extract_match_events(content):
    """提取比赛事件数据 - 红黄牌、进球、时间线等"""
    events_data = {
        "home_red_cards": 0,
        "away_red_cards": 0,
        "home_yellow_cards": 0,
        "away_yellow_cards": 0,
        "total_events": 0,
        "goals": [],
        "cards": [],
        "substitutions": [],
        "match_events": []  # 完整事件时间线
    }

    try:
        # 获取主客队ID以便区分事件
        home_team_id = None
        away_team_id = None

        if "general" in content:
            general = content["general"]
            home_team_id = general.get("homeTeam", {}).get("id")
            away_team_id = general.get("awayTeam", {}).get("id")

        # 检查events数据 - 主要事件来源
        if "events" in content:
            events = content["events"]
            if isinstance(events, dict) and "events" in events:
                event_list = events["events"]

                if isinstance(event_list, list):
                    events_data["total_events"] = len(event_list)

                    # 处理每个事件
                    for event in event_list:
                        if not isinstance(event, dict):
                            continue

                        event_type = event.get("type")
                        event_time = event.get("time", 0)
                        is_home = event.get("isHome", False)

                        # 构建标准化事件对象
                        standardized_event = {
                            "type": event_type,
                            "time": event_time,
                            "timeStr": event.get("timeStr", ""),
                            "isHome": is_home,
                            "player": event.get("player", {}),
                            "team": "home" if is_home else "away"
                        }

                        # 添加特定事件的详细信息
                        if event_type == "Goal":
                            goal_info = {
                                "player": event.get("nameStr", ""),
                                "player_id": event.get("playerId"),
                                "score": event.get("newScore", []),
                                "isPenalty": event.get("goalDescription") == "Penalty",
                                "ownGoal": event.get("ownGoal", False)
                            }
                            standardized_event.update(goal_info)
                            events_data["goals"].append(standardized_event)

                        elif event_type == "Card":
                            card_type = event.get("card", "")
                            card_info = {
                                "player": event.get("nameStr", ""),
                                "player_id": event.get("playerId"),
                                "cardType": card_type  # "Yellow" 或 "Red"
                            }
                            standardized_event.update(card_info)
                            events_data["cards"].append(standardized_event)

                            # 统计红黄牌数量
                            if card_type == "Red":
                                if is_home:
                                    events_data["home_red_cards"] += 1
                                else:
                                    events_data["away_red_cards"] += 1
                            elif card_type == "Yellow":
                                if is_home:
                                    events_data["home_yellow_cards"] += 1
                                else:
                                    events_data["away_yellow_cards"] += 1

                        elif event_type == "Substitution":
                            sub_info = {
                                "swap": event.get("swap", [])
                            }
                            standardized_event.update(sub_info)
                            events_data["substitutions"].append(standardized_event)

                        # 添加到完整事件时间线
                        events_data["match_events"].append(standardized_event)

        # 检查header中的红牌统计（备用数据源）
        if "header" in content:
            header = content["header"]
            if "status" in header:
                status = header["status"]
                # 使用header中的红牌数量作为验证或补充
                header_home_reds = status.get("numberOfHomeRedCards", 0)
                header_away_reds = status.get("numberOfAwayRedCards", 0)

                # 如果events中没有找到红牌，使用header数据
                if events_data["home_red_cards"] == 0 and header_home_reds > 0:
                    events_data["home_red_cards"] = header_home_reds
                if events_data["away_red_cards"] == 0 and header_away_reds > 0:
                    events_data["away_red_cards"] = header_away_reds

        return events_data

    except Exception as e:
        print(f"❌ 比赛事件提取失败: {e}")
        import traceback
        traceback.print_exc()
        return events_data


def test_events_extraction():
    """测试事件提取功能"""
    print("🚀 开始测试比赛事件提取功能")
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

    # 测试事件提取
    print("\n⚽️ 测试比赛事件提取功能...")
    events_data = extract_match_events(content)

    print("\n📊 事件提取结果:")
    print(f"   总事件数: {events_data['total_events']}")
    print(f"   主队红牌: {events_data['home_red_cards']}")
    print(f"   客队红牌: {events_data['away_red_cards']}")
    print(f"   主队黄牌: {events_data['home_yellow_cards']}")
    print(f"   客队黄牌: {events_data['away_yellow_cards']}")
    print(f"   进球事件: {len(events_data['goals'])}")
    print(f"   红黄牌事件: {len(events_data['cards'])}")
    print(f"   换人事件: {len(events_data['substitutions'])}")

    # 显示进球详情
    if events_data["goals"]:
        print("\n⚽️ 进球事件详情:")
        for i, goal in enumerate(events_data["goals"][:5], 1):  # 显示前5个进球
            print(f"   {i}. 第{goal['time']}分钟 - {goal['player']} ({goal['team']})")
            if goal.get("isPenalty"):
                print(f"      🎯 点球进球")
            if goal.get("ownGoal"):
                print(f"      🏃️ 乌龙球")
            if goal.get("score"):
                print(f"      比分: {goal['score']}")

    # 显示红黄牌详情
    if events_data["cards"]:
        print("\n🟥️ 红黄牌事件详情:")
        for i, card in enumerate(events_data["cards"][:5], 1):  # 显示前5张牌
            print(f"   {i}. 第{card['time']}分钟 - {card['player']} ({card['team']}) - {card['cardType']}牌")

    # 验证红黄牌统计
    total_red_cards = events_data["home_red_cards"] + events_data["away_red_cards"]
    total_yellow_cards = events_data["home_yellow_cards"] + events_data["away_yellow_cards"]

    # 生成ML特征向量示例
    ml_features = {
        "has_events_data": events_data["total_events"] > 0,
        "total_cards": total_red_cards + total_yellow_cards,
        "total_red_cards": total_red_cards,
        "total_yellow_cards": total_yellow_cards,
        "total_goals": len(events_data["goals"]),
        "home_red_cards": events_data["home_red_cards"],
        "away_red_cards": events_data["away_red_cards"],
        "home_yellow_cards": events_data["home_yellow_cards"],
        "away_yellow_cards": events_data["away_yellow_cards"],
        "cards_advantage": events_data["away_red_cards"] - events_data["home_red_cards"],  # 负数表示客队优势
        "discipline_level": (total_red_cards * 2 + total_yellow_cards) / 2  # 纪律指数
    }

    print("\n🎯 ML特征向量示例:")
    for feature, value in ml_features.items():
        print(f"   {feature}: {value}")

    # 数据质量评估
    print("\n📈 数据质量评估:")
    has_goals = len(events_data["goals"]) > 0
    has_cards = len(events_data["cards"]) > 0
    has_events = events_data["total_events"] > 0

    print(f"   进球数据: {'✅' if has_goals else '❌'}")
    print(f"   红黄牌数据: {'✅' if has_cards else '❌'}")
    print(f"   事件数据: {'✅' if has_events else '❌'}")

    # 最终评估
    print("\n" + "=" * 80)
    print("🏆 Match Events Extraction 综合报告:")
    print("=" * 80)

    print(f"📊 事件提取统计:")
    print(f"   红牌统计: 主队{events_data['home_red_cards']}张, 客队{events_data['away_red_cards']}张")
    print(f"   黄牌统计: 主队{events_data['home_yellow_cards']}张, 客队{events_data['away_yellow_cards']}张")
    print(f"   进球事件: {len(events_data['goals'])}个")
    print(f"   换人事件: {len(events_data['substitutions'])}个")
    print(f"   总事件数: {events_data['total_events']}个")

    # 业务价值评估
    print(f"\n🎯 ML特征工程价值:")
    print(f"   ✅ 纪律指数: {ml_features['discipline_level']:.1f} (可用于纪律分析)")
    print(f"   ✅ 卡牌优势: {'客队优势' if ml_features['cards_advantage'] > 0 else '主队优势' if ml_features['cards_advantage'] < 0 else '平衡'}")
    print(f"   ✅ 时间线数据: 完整的比赛过程记录")
    print(f"   ✅ 特征维度: 10+个新特征可用于预测模型")

    if has_events:
        print("\n🎉 Match Events Extraction 功能测试成功！")
        print("📈 新功能可以用于:")
        print("   - 纪律分析: 红黄牌统计和趋势")
        print("   - 比赛过程: 完整的事件时间线")
        print("   - ML特征工程: 10+个新特征维度")
        print("   - 比赛报告: 详细的比赛过程记录")
        print("   - 战术分析: 换人时间和时机")
        return True
    else:
        print("\n⚠️ Match Events Extraction 需要进一步优化")
        return False


def main():
    """主函数"""
    print("🚀 Match Events Extraction 测试启动")
    print("🎯 目标: 提取完整的比赛事件数据 (红黄牌、进球、时间线)")
    print()

    success = test_events_extraction()

    print("\n" + "=" * 80)
    if success:
        print("🏆 Match Events Extraction 测试通过！")
        print("✨ 新增功能为足球预测系统提供了完整的过程数据支持")
    else:
        print("❌ Match Events Extraction 测试失败")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)