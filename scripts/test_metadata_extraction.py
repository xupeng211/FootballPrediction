#!/usr/bin/env python3
"""
测试新增的元数据提取功能

专门测试裁判、球场、观众、阵型等新元数据的提取功能
"""

import json
from pathlib import Path

def extract_match_metadata(content):
    """提取比赛元数据 - 裁判、球场、观众等"""
    metadata = {
        "referee": None,
        "stadium": None,
        "attendance": None,
        "city": None,
        "country": None
    }

    try:
        # 检查matchFacts中的infoBox数据
        if "matchFacts" in content:
            match_facts = content["matchFacts"]

            if "infoBox" in match_facts:
                info_box = match_facts["infoBox"]

                # 提取裁判信息
                if "Referee" in info_box:
                    referee_info = info_box["Referee"]
                    if isinstance(referee_info, dict) and "text" in referee_info:
                        metadata["referee"] = referee_info["text"]

                # 提取球场信息
                if "Stadium" in info_box:
                    stadium_info = info_box["Stadium"]
                    if isinstance(stadium_info, dict):
                        metadata["stadium"] = stadium_info.get("name")
                        metadata["city"] = stadium_info.get("city")
                        metadata["country"] = stadium_info.get("country")

                # 提取观众人数
                if "Attendance" in info_box:
                    attendance_info = info_box["Attendance"]
                    if isinstance(attendance_info, dict) and "value" in attendance_info:
                        try:
                            metadata["attendance"] = int(attendance_info["value"])
                        except (ValueError, TypeError):
                            metadata["attendance"] = None
                    elif isinstance(attendance_info, (int, str)):
                        # 处理直接是数字或字符串的情况
                        try:
                            metadata["attendance"] = int(attendance_info)
                        except (ValueError, TypeError):
                            metadata["attendance"] = None

        # 打印详细提取结果
        print("🔍 元数据提取详情:")
        for key, value in metadata.items():
            print(f"   {key}: {value}")

        return metadata

    except Exception as e:
        print(f"❌ 元数据提取失败: {e}")
        return metadata


def extract_tactical_data(content):
    """提取战术数据 - 阵型等"""
    tactical_data = {
        "home_formation": None,
        "away_formation": None,
        "lineups_available": False
    }

    try:
        # 检查阵容数据
        if "lineups" in content:
            lineups = content["lineups"]
            tactical_data["lineups_available"] = True

            # 尝试从阵容中提取阵型信息
            if isinstance(lineups, dict):
                # 检查主队阵型
                if "home" in lineups:
                    home_lineup = lineups["home"]
                    if isinstance(home_lineup, dict):
                        # 查找阵型信息，可能在不同字段中
                        formation = home_lineup.get("formation") or home_lineup.get("lineup")
                        if formation:
                            tactical_data["home_formation"] = formation

                # 检查客队阵型
                if "away" in lineups:
                    away_lineup = lineups["away"]
                    if isinstance(away_lineup, dict):
                        formation = away_lineup.get("formation") or away_lineup.get("lineup")
                        if formation:
                            tactical_data["away_formation"] = formation

        # 如果在lineups中没找到，尝试其他位置
        if not tactical_data["home_formation"] or not tactical_data["away_formation"]:
            # 可以在这里添加更多的阵型查找逻辑
            pass

        print("🛡️ 战术数据提取详情:")
        print(f"   主队阵型: {tactical_data['home_formation']}")
        print(f"   客队阵型: {tactical_data['away_formation']}")
        print(f"   阵容数据可用: {tactical_data['lineups_available']}")

        return tactical_data

    except Exception as e:
        print(f"❌ 战术数据提取失败: {e}")
        return tactical_data


def test_metadata_extraction():
    """测试元数据提取功能"""
    print("🏆 测试比赛元数据提取功能...")
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

    # 1. 测试比赛元数据提取
    print("\n📋 测试比赛元数据提取...")
    metadata = extract_match_metadata(content)

    # 验证元数据提取结果
    metadata_success_count = sum([
        1 for v in metadata.values()
        if v is not None and v != ""
    ])

    print(f"\n📊 元数据提取结果: {metadata_success_count}/5 项成功提取")

    # 2. 测试战术数据提取
    print("\n⚔️ 测试战术数据提取...")
    tactical_data = extract_tactical_data(content)

    # 验证战术数据提取结果
    tactical_success_count = sum([
        1 for v in [tactical_data["home_formation"], tactical_data["away_formation"]]
        if v is not None and v != ""
    ])

    print(f"\n📊 战术数据提取结果: {tactical_success_count}/2 项阵型成功提取")

    # 3. 生成集成报告
    print("\n" + "=" * 80)
    print("📋 Total Data Extraction 综合报告:")
    print("=" * 80)

    # 比赛元数据报告
    print("\n🏆 比赛元数据 (Match Metadata):")
    print(f"   裁判: {'✅' if metadata['referee'] else '❌'} {metadata['referee']}")
    print(f"   球场: {'✅' if metadata['stadium'] else '❌'} {metadata['stadium']}")
    print(f"   观众: {'✅' if metadata['attendance'] else '❌'} {metadata['attendance']}")
    print(f"   城市: {'✅' if metadata['city'] else '❌'} {metadata['city']}")
    print(f"   国家: {'✅' if metadata['country'] else '❌'} {metadata['country']}")

    # 战术数据报告
    print("\n⚔️ 战术数据 (Tactical Data):")
    print(f"   主队阵型: {'✅' if tactical_data['home_formation'] else '❌'} {tactical_data['home_formation']}")
    print(f"   客队阵型: {'✅' if tactical_data['away_formation'] else '❌'} {tactical_data['away_formation']}")
    print(f"   阵容数据: {'✅' if tactical_data['lineups_available'] else '❌'}")

    # 总体评估
    total_features = metadata_success_count + tactical_success_count
    max_features = 7  # 5个元数据 + 2个阵型数据
    success_rate = total_features / max_features

    print(f"\n📈 总体提取成功率: {success_rate:.1%} ({total_features}/{max_features})")

    # 数据质量评估
    if success_rate >= 0.8:
        print("🎉 Total Data Extraction 功能优秀！")
        print("📈 新功能可以用于:")
        print("   - 比赛环境分析: 球场、观众、裁判因素")
        print("   - 战术分析: 阵型对比和战术预测")
        print("   - 数据增强: 丰富ML模型特征维度")
        print("   - 比赛报告: 完整的比赛信息展示")
        return True
    elif success_rate >= 0.5:
        print("✅ Total Data Extraction 功能良好")
        print("⚠️ 部分元数据需要进一步优化")
        return True
    else:
        print("⚠️ Total Data Extraction 需要改进")
        print("🔧 建议检查JSON数据结构或调整提取逻辑")
        return False


def main():
    """主函数"""
    print("🚀 Total Data Extraction 测试启动")
    print("🎯 目标: 彻底'榨干' L2 数据源 - 提取所有元数据")
    print()

    success = test_metadata_extraction()

    print("\n" + "=" * 80)
    if success:
        print("🏆 Total Data Extraction 测试通过！")
        print("✨ 新增功能为足球预测系统提供了丰富的元数据支持")
    else:
        print("❌ Total Data Extraction 测试失败")
        print("🔧 需要进一步调试和优化")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)