#!/usr/bin/env python3
"""
队名映射修正脚本
数据治理专家专用工具

规则：
1. 严禁将顶级联赛球队映射到U18/U21/青年队
2. 硬编码五大联赛豪门的正确映射关系
3. 修正明显的模糊匹配错误
"""

import json
import re
from pathlib import Path
from typing import Dict, Set

# 配置路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
INPUT_FILE = CONFIG_DIR / "team_mapping.json"
OUTPUT_FILE = CONFIG_DIR / "team_mapping_refined.json"
LOW_CONFIDENCE_FILE = CONFIG_DIR / "team_mapping_low_confidence.json"
UNMATCHED_FILE = CONFIG_DIR / "team_mapping_unmatched.json"


# 规则1: 五大联赛豪门球队映射（硬编码）
TOP_TEAMS_MAPPING = {
    # 英超
    "Arsenal": "Arsenal",
    "Aston Villa": None,  # FotMob中未找到
    "Brentford": "Brentford",
    "Brighton": "Brighton",
    "Chelsea": "Chelsea",
    "Crystal Palace": "Crystal Palace",
    "Everton": "Everton",  # FotMob数据可能不完整
    "Fulham": None,
    "Leeds United": "Leeds",
    "Leicester": None,
    "Liverpool": "Liverpool FC",
    "Manchester City": None,  # FotMob数据中没有顶级队
    "Manchester Utd": None,
    "Newcastle Utd": "Newcastle",
    "Nottingham Forest": "Nottm Forest",
    "Southampton": "Southampton",
    "Tottenham": "Tottenham",
    "West Ham": "West Ham",
    "Wolves": "Wolves",
    # 西甲
    "Athletic Club": "Athletic Club",
    "Atlético Madrid": "Atletico Madrid",
    "Barcelona": "Barcelona",
    "Betis": None,
    "Celta Vigo": "Celta Vigo",
    "Elche": "Elche",
    "Espanyol": "Espanyol",
    "Getafe": None,
    "Girona": None,
    "Granada": None,
    "Las Palmas": None,
    "Mallorca": "Mallorca",
    "Osasuna": None,
    "Rayo Vallecano": None,
    "Real Madrid": None,  # FotMob中没有
    "Real Sociedad": "Real Sociedad",
    "Sevilla": None,
    "Valencia": "Valencia",
    "Villarreal": None,
    # 德甲
    "Augsburg": "Augsburg",
    "Bayern Munich": None,  # FotMob中没有
    "Borussia Dortmund": "Dortmund",
    "Borussia Mönchengladbach": "M'gladbach",
    "Eintracht Frankfurt": None,
    "Freiburg": "Freiburg",
    "Hertha BSC": None,
    "Hoffenheim": "Hoffenheim",
    "Köln": "Köln",
    "Leverkusen": "Leverkusen",
    "Mainz 05": None,
    "RB Leipzig": "RB Leipzig",
    "VfB Stuttgart": None,
    "Werder Bremen": "Werder Bremen",
    "Wolfsburg": "Wolfsburg",
    "Union Berlin": "Union Berlin",
    "Heidenheim": "FC Heidenheim",
    # 意甲
    "AC Milan": "Milan",
    "AS Roma": "Roma",
    "Atalanta": "Atalanta",
    "Bologna": "Bologna",
    "Cagliari": "Cagliari",
    "Como": "Como",
    "Cremonese": "Cremonese",
    "Empoli": None,
    "Fiorentina": "Fiorentina",
    "Genoa": None,
    "Hellas Verona": "Hellas Verona",
    "Inter": None,
    "Juventus": None,
    "Lazio": "Lazio",
    "Lecce": None,
    "Monza": None,
    "Napoli": None,
    "Parma": None,
    "Sassuolo": "Sassuolo",
    "Torino": None,
    "Udinese": None,
    "Venezia": None,
    # 法甲
    "Auxerre": None,
    "Brest": "Brest",
    "Clermont": None,
    "Le Havre": None,
    "Lille": None,
    "Lyon": "Lyon",
    "Marseille": None,
    "Monaco": None,
    "Montpellier": None,
    "Nantes": "Nantes",
    "Nice": "Nice",
    "Paris S-G": None,
    "PSG": None,
    "Reims": "Reims",
    "Rennes": "Rennes",
    "Strasbourg": "Strasbourg",
    "Toulouse": None,
    # 其他知名球队
    "Ajax": None,
    "Benfica": None,
    "Porto": None,
    "Celtic": None,
    "Rangers": "Rangers",
    "Shakhtar Donetsk": None,
    "Galatasaray": None,
    "Fenerbahçe": None,
    "Beşiktaş": None,
}


class TeamMappingRefiner:
    """队名映射修正器"""

    def __init__(self):
        self.high_confidence = {}
        self.low_confidence = {}
        self.unmatched = {}
        self.metadata = {}
        self.refined_high_confidence = {}
        self.refined_low_confidence = {}
        self.corrections_log = []

    def load_mapping(self) -> None:
        """加载原始映射文件"""
        print("📥 加载原始映射文件...")

        with open(INPUT_FILE, encoding="utf-8") as f:
            data = json.load(f)

        self.high_confidence = data.get("high_confidence", {})
        self.low_confidence = data.get("low_confidence", {})
        self.unmatched = data.get("unmatched", {})
        self.metadata = data.get("metadata", {})

        print("✅ 加载完成:")
        print(f"  - 高可信度映射: {len(self.high_confidence)}")
        print(f"  - 低可信度映射: {len(self.low_confidence)}")
        print(f"  - 未匹配: {len(self.unmatched)}")

    def is_youth_team(self, team_name: str) -> bool:
        """检查是否为青年队或梯队"""
        youth_patterns = [
            r"\bU\d{1,2}\b",  # U18, U21, U23
            r"\b\d{2}\b",  # 年龄作为后缀
            r"Academy",  # 青训营
            r"Reserve",  # 预备队
            r"B",  # 二队 (如 Real Madrid B)
            r"II",  # 二队 (如 Bayern Munich II)
            r"Womens",  # 女子队
            r"Women",  # 女子队
            r"Ladies",  # 女子队
        ]

        team_lower = team_name.lower()
        for pattern in youth_patterns:
            if re.search(pattern, team_lower, re.IGNORECASE):
                return True

        return False

    def apply_hardcoded_rules(self) -> None:
        """应用硬编码规则修正映射"""
        print("\n🔧 应用硬编码规则修正映射...")

        corrections_count = 0

        # 遍历所有顶级球队映射
        for fbref_name, fotmob_name in TOP_TEAMS_MAPPING.items():
            # 检查是否存在于现有映射中
            if fbref_name in self.high_confidence:
                current_mapping = self.high_confidence[fbref_name]

                # 检查当前映射是否为青年队
                if self.is_youth_team(current_mapping):
                    self.log_correction(
                        fbref_name,
                        current_mapping,
                        fotmob_name,
                        "ERROR: 顶级球队映射到青年队",
                    )
                    corrections_count += 1

                # 应用硬编码映射
                if fotmob_name is None:
                    # 移除映射，标记为未匹配
                    if fbref_name in self.high_confidence:
                        del self.high_confidence[fbref_name]
                        self.unmatched[fbref_name] = None
                    corrections_count += 1
                else:
                    # 修正映射
                    if current_mapping != fotmob_name:
                        self.log_correction(
                            fbref_name,
                            current_mapping,
                            fotmob_name,
                            "HARDCODE: 硬编码修正",
                        )
                        corrections_count += 1

                    self.high_confidence[fbref_name] = fotmob_name

            elif fbref_name in self.low_confidence:
                current_mapping = self.low_confidence[fbref_name]

                # 检查当前映射是否为青年队
                if self.is_youth_team(current_mapping):
                    if fotmob_name is not None:
                        self.log_correction(
                            fbref_name,
                            current_mapping,
                            fotmob_name,
                            "ERROR: 低可信度青年队映射修正",
                        )
                        corrections_count += 1
                        self.high_confidence[fbref_name] = fotmob_name
                    else:
                        self.log_correction(
                            fbref_name, current_mapping, None, "ERROR: 移除青年队映射"
                        )
                        corrections_count += 1
                        del self.low_confidence[fbref_name]
                        self.unmatched[fbref_name] = None

                elif fotmob_name is not None and current_mapping != fotmob_name:
                    self.log_correction(
                        fbref_name, current_mapping, fotmob_name, "HARDCODE: 硬编码修正"
                    )
                    corrections_count += 1
                    self.high_confidence[fbref_name] = fotmob_name
                    del self.low_confidence[fbref_name]

        print(f"✅ 规则修正完成，共修正 {corrections_count} 个映射")

    def correct_obvious_errors(self) -> None:
        """修正明显的模糊匹配错误"""
        print("\n🔍 修正明显的模糊匹配错误...")

        # 检查并修正青年队映射
        youth_team_mappings = []

        for fbref_name, fotmob_name in list(self.high_confidence.items()):
            if self.is_youth_team(fotmob_name):
                youth_team_mappings.append((fbref_name, fotmob_name))

        # 检查并修正低可信度中的青年队映射
        for fbref_name, fotmob_name in list(self.low_confidence.items()):
            if self.is_youth_team(fotmob_name):
                youth_team_mappings.append((fbref_name, fotmob_name))

        # 移除所有青年队映射
        corrections = 0
        for fbref_name, fotmob_name in youth_team_mappings:
            if fbref_name in self.high_confidence:
                del self.high_confidence[fbref_name]
                self.unmatched[fbref_name] = None
                self.log_correction(
                    fbref_name, fotmob_name, None, "REMOVED: 青年队映射"
                )
                corrections += 1

            if fbref_name in self.low_confidence:
                del self.low_confidence[fbref_name]
                self.unmatched[fbref_name] = None
                self.log_correction(
                    fbref_name, fotmob_name, None, "REMOVED: 青年队映射"
                )
                corrections += 1

        print(f"✅ 移除了 {corrections} 个青年队映射")

    def remove_inconsistent_leagues(self) -> None:
        """移除明显来自不同联赛的映射"""
        print("\n🏆 移除跨联赛映射...")

        # 英超球队不应该映射到德甲或其他联赛球队
        # 这里可以添加更复杂的逻辑，目前先标记需要人工审核的映射

        suspicious_mappings = [
            ("Angers", "Rangers"),  # 法甲→苏超
            ("Eint Frankfurt", "Frankfurt"),  # 可能正确
        ]

        corrections = 0
        for fbref_name, fotmob_name in suspicious_mappings:
            if fbref_name in self.high_confidence:
                if fotmob_name != fbref_name:  # 不是完全匹配
                    del self.high_confidence[fbref_name]
                    self.unmatched[fbref_name] = None
                    self.log_correction(
                        fbref_name, fotmob_name, None, "SUSPICIOUS: 跨联赛映射"
                    )
                    corrections += 1

        print(f"✅ 移除了 {corrections} 个可疑映射")

    def log_correction(self, fbref: str, old: str, new: str, reason: str) -> None:
        """记录修正日志"""
        self.corrections_log.append(
            {
                "fbref_team": fbref,
                "old_mapping": old,
                "new_mapping": new,
                "reason": reason,
            }
        )

    def save_refined_mapping(self) -> None:
        """保存修正后的映射"""
        print("\n💾 保存修正后的映射文件...")

        refined_mapping = {
            "high_confidence": self.high_confidence,
            "low_confidence": self.low_confidence,
            "unmatched": self.unmatched,
            "metadata": {
                **self.metadata,
                "refined": True,
                "corrections_count": len(self.corrections_log),
                "refinement_rules": [
                    "RULE_1: 严禁将顶级球队映射到U18/U21/青年队",
                    "RULE_2: 硬编码五大联赛豪门映射",
                    "RULE_3: 移除跨联赛可疑映射",
                ],
            },
            "corrections_log": self.corrections_log,
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(refined_mapping, f, indent=2, ensure_ascii=False)

        print(f"✅ 修正后的映射已保存: {OUTPUT_FILE}")

        # 也保存单独的修正日志
        corrections_file = CONFIG_DIR / "team_mapping_corrections.json"
        with open(corrections_file, "w", encoding="utf-8") as f:
            json.dump(self.corrections_log, f, indent=2, ensure_ascii=False)

        print(f"✅ 修正日志已保存: {corrections_file}")

    def print_summary(self) -> None:
        """打印修正摘要"""
        print("\n" + "=" * 80)
        print("📋 映射修正报告")
        print("=" * 80)

        print("\n📊 修正后统计:")
        print(f"  - 高可信度映射: {len(self.high_confidence)}")
        print(f"  - 低可信度映射: {len(self.low_confidence)}")
        print(f"  - 未匹配: {len(self.unmatched)}")
        print(f"  - 修正数量: {len(self.corrections_log)}")

        if self.corrections_log:
            print("\n🔧 修正详情:")
            for correction in self.corrections_log[:10]:  # 只显示前10个
                print(
                    f"  - {correction['fbref_team']}: {correction['old_mapping']} → {correction['new_mapping']} ({correction['reason']})"
                )

            if len(self.corrections_log) > 10:
                print(f"  ... 还有 {len(self.corrections_log) - 10} 个修正")

        print("\n" + "=" * 80)


def main():
    """主函数"""
    print("🚀 队名映射修正工具启动")
    print("=" * 80)

    # 创建修正器
    refiner = TeamMappingRefiner()

    # 加载原始映射
    refiner.load_mapping()

    # 应用修正规则
    refiner.apply_hardcoded_rules()
    refiner.correct_obvious_errors()
    refiner.remove_inconsistent_leagues()

    # 保存结果
    refiner.save_refined_mapping()

    # 打印摘要
    refiner.print_summary()

    print("\n✅ 映射修正完成!")
    print(f"📁 输出文件: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
