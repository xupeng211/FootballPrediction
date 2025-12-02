#!/usr/bin/env python3
"""
队名映射生成器 - Entity Resolution快速解决方案
数据清洗工程师专用工具

功能：
1. 从数据库提取FBref队名
2. 从FotMob JSON文件提取队名
3. 使用模糊匹配生成映射
4. 输出映射文件和未匹配名单
"""

import json
import os
import sys
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import pandas as pd
from sqlalchemy import create_engine, text

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置
DATABASE_URL = (
    "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
)
FOTMOB_DATA_DIR = project_root / "data" / "fotmob" / "historical"
OUTPUT_DIR = project_root / "config"
MAPPING_FILE = OUTPUT_DIR / "team_mapping.json"
LOW_CONFIDENCE_FILE = OUTPUT_DIR / "team_mapping_low_confidence.json"
UNMATCHED_FILE = OUTPUT_DIR / "team_mapping_unmatched.json"


class TeamMappingGenerator:
    """队名映射生成器"""

    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.fbref_teams: Set[str] = set()
        self.fotmob_teams: Set[str] = set()
        self.mapping: Dict[str, str] = {}
        self.low_confidence: Dict[str, str] = {}
        self.unmatched: Dict[str, str] = {}

    def similarity(self, a: str, b: str) -> float:
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def clean_team_name(self, name: str) -> str:
        """清理队名，移除常见的后缀"""
        # 移除常见后缀
        suffixes = [" FC", " CF", " AC", " SC", " United", " City", " Town"]
        cleaned = name
        for suffix in suffixes:
            if cleaned.endswith(suffix):
                # 保留特殊情况，如 "Manchester City" 不能简化为 "Man"
                if suffix == " City" and "Manchester" in cleaned:
                    continue
                if suffix == " United" and "Newcastle" in cleaned:
                    continue
                cleaned = cleaned[: -len(suffix)]

        # 移除特殊字符
        cleaned = cleaned.replace(".", "").replace("-", " ")

        return cleaned.strip()

    def extract_fbref_teams(self) -> None:
        """从数据库提取FBref队名"""
        print("🔄 提取FBref队名...")

        with self.engine.connect() as conn:
            df = pd.read_sql(
                text(
                    """
                SELECT DISTINCT t.name
                FROM matches m
                JOIN teams t ON m.home_team_id = t.id
                WHERE m.data_source = 'fbref'
                ORDER BY t.name
            """
                ),
                conn,
            )

            self.fbref_teams = set(df["name"].tolist())

        print(f"✅ 发现 {len(self.fbref_teams)} 个FBref队名")

    def extract_fotmob_teams(self) -> None:
        """从FotMob JSON文件提取队名"""
        print("🔄 提取FotMob队名...")

        json_files = list(FOTMOB_DATA_DIR.glob("fotmob_matches_*.json"))

        if not json_files:
            print(f"❌ 未找到FotMob数据文件: {FOTMOB_DATA_DIR}")
            return

        teams_set = set()

        for json_file in json_files:
            print(f"  📖 读取: {json_file.name}")
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

                for match in data.get("matches", []):
                    teams_set.add(match["home_team_name"])
                    teams_set.add(match["away_team_name"])

        self.fotmob_teams = teams_set

        print(f"✅ 发现 {len(self.fotmob_teams)} 个FotMob队名")

    def generate_mapping(self, threshold: float = 0.85) -> None:
        """生成模糊匹配映射"""
        print(f"\n🔍 开始模糊匹配 (相似度阈值: {threshold:.0%})...")

        fotmob_list = list(self.fotmob_teams)
        fotmob_list.sort()

        matched_fotmob = set()

        for fbref_team in sorted(self.fbref_teams):
            best_match = None
            best_score = 0.0

            # 寻找最佳匹配
            for fotmob_team in fotmob_list:
                if fotmob_team in matched_fotmob:
                    continue

                # 直接匹配
                if fbref_team.lower() == fotmob_team.lower():
                    best_match = fotmob_team
                    best_score = 1.0
                    break

                # 清理后匹配
                cleaned_fbref = self.clean_team_name(fbref_team)
                cleaned_fotmob = self.clean_team_name(fotmob_team)

                if cleaned_fbref.lower() == cleaned_fotmob.lower():
                    best_match = fotmob_team
                    best_score = 0.95
                    break

                # 模糊匹配
                score = self.similarity(fbref_team, fotmob_team)
                if score > best_score:
                    best_score = score
                    best_match = fotmob_team

            # 根据匹配度分类
            if best_match and best_score >= threshold:
                self.mapping[fbref_team] = best_match
                matched_fotmob.add(best_match)
                print(f"  ✅ {fbref_team} → {best_match} (相似度: {best_score:.2%})")

            elif best_match and best_score >= 0.7:
                self.low_confidence[fbref_team] = best_match
                matched_fotmob.add(best_match)
                print(f"  ⚠️  {fbref_team} → {best_match} (低相似度: {best_score:.2%})")

        # 标记未匹配的FBref队名
        for fbref_team in self.fbref_teams:
            if fbref_team not in self.mapping and fbref_team not in self.low_confidence:
                self.unmatched[fbref_team] = None

        # 标记未匹配的FotMob队名
        unmatched_fotmob = self.fotmob_teams - matched_fotmob
        for fotmob_team in sorted(unmatched_fotmob):
            self.unmatched[f"__FOTMOB_ONLY__{fotmob_team}"] = fotmob_team

        print(f"\n📊 匹配统计:")
        print(f"  ✅ 高可信度映射: {len(self.mapping)}")
        print(f"  ⚠️  低可信度映射: {len(self.low_confidence)}")
        print(f"  ❌ 未匹配: {len(self.unmatched)}")

    def save_mapping(self) -> None:
        """保存映射文件"""
        print(f"\n💾 保存映射文件...")

        # 确保输出目录存在
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 保存完整映射
        full_mapping = {
            "high_confidence": self.mapping,
            "low_confidence": self.low_confidence,
            "unmatched": self.unmatched,
            "metadata": {
                "total_fbref_teams": len(self.fbref_teams),
                "total_fotmob_teams": len(self.fotmob_teams),
                "high_confidence_matches": len(self.mapping),
                "low_confidence_matches": len(self.low_confidence),
                "unmatched_teams": len(self.unmatched),
            },
        }

        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(full_mapping, f, indent=2, ensure_ascii=False)

        print(f"✅ 完整映射已保存: {MAPPING_FILE}")

        # 保存低可信度映射
        with open(LOW_CONFIDENCE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.low_confidence, f, indent=2, ensure_ascii=False)

        # 保存未匹配名单
        with open(UNMATCHED_FILE, "w", encoding="utf-8") as f:
            json.dump(self.unmatched, f, indent=2, ensure_ascii=False)

        print(f"✅ 低可信度映射: {LOW_CONFIDENCE_FILE}")
        print(f"✅ 未匹配名单: {UNMATCHED_FILE}")

    def print_summary(self) -> None:
        """打印详细报告"""
        print("\n" + "=" * 80)
        print("📋 队名映射生成报告")
        print("=" * 80)

        if self.mapping:
            print(f"\n✅ 高可信度映射 ({len(self.mapping)} 个):")
            for fbref, fotmob in sorted(self.mapping.items()):
                print(f"  {fbref:30s} → {fotmob}")

        if self.low_confidence:
            print(f"\n⚠️  低可信度映射 ({len(self.low_confidence)} 个) - 需要人工检查:")
            for fbref, fotmob in sorted(self.low_confidence.items()):
                print(f"  {fbref:30s} → {fotmob}")

        if self.unmatched:
            print(f"\n❌ 未匹配队名 ({len(self.unmatched)} 个):")
            for team, _ in sorted(self.unmatched.items()):
                print(f"  {team}")

        print("\n" + "=" * 80)

    def generate_sql_updates(self) -> None:
        """生成SQL更新语句（可选功能）"""
        print("\n🔧 生成SQL更新语句...")

        sql_statements = []

        # 为每个高可信度映射生成SQL
        for fbref_name, fotmob_name in sorted(self.mapping.items()):
            sql = f"""
-- 映射: {fbref_name} → {fotmob_name}
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = '{fotmob_name.replace("'", "''")}'
    LIMIT 1
)
WHERE name = '{fbref_name.replace("'", "''")}';
"""
            sql_statements.append(sql)

        # 保存SQL文件
        sql_file = OUTPUT_DIR / "team_mapping_updates.sql"
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write("-- 队名映射SQL更新语句\n")
            f.write("-- ⚠️  请仔细检查后再执行!\n\n")
            for sql in sql_statements:
                f.write(sql + "\n")

        print(f"✅ SQL更新语句已保存: {sql_file}")
        print("⚠️  请仔细检查SQL语句后再执行!")


def main():
    """主函数"""
    print("🚀 队名映射生成器启动")
    print("=" * 80)

    # 创建映射生成器
    generator = TeamMappingGenerator()

    # Step 1: 提取数据
    print("\n📥 Step 1: 数据提取")
    generator.extract_fbref_teams()
    generator.extract_fotmob_teams()

    # Step 2: 生成映射
    print("\n🔍 Step 2: 模糊匹配")
    generator.generate_mapping(threshold=0.85)

    # Step 3: 保存结果
    print("\n💾 Step 3: 保存映射文件")
    generator.save_mapping()

    # Step 4: 打印报告
    print("\n📊 Step 4: 生成报告")
    generator.print_summary()

    # Step 5: SQL更新语句（可选）
    print("\n🔧 Step 5: SQL更新语句生成")
    generator.generate_sql_updates()

    print("\n🎉 完成! 请检查生成的文件:")
    print(f"  - {MAPPING_FILE}")
    print(f"  - {LOW_CONFIDENCE_FILE}")
    print(f"  - {UNMATCHED_FILE}")
    print(f"  - {OUTPUT_DIR / 'team_mapping_updates.sql'}")


if __name__ == "__main__":
    main()
