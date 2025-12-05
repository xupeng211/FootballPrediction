#!/usr/bin/env python3
"""
首席数据治理专家专用 - 球队实体合并计划生成器
识别重复球队并生成标准化合并计划
"""

import subprocess
import json
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TeamMergePlanner:
    """球队合并计划生成器"""

    def __init__(self):
        self.teams = []
        self.merge_plan = []
        self.similarity_threshold = 0.85

    def load_teams_from_db(self) -> list[dict]:
        """从数据库加载所有球队"""
        try:
            cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-tAc",
                "SELECT id, name FROM teams ORDER BY id;",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                teams = []
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split("|")
                        if len(parts) >= 2:
                            teams.append(
                                {"id": int(parts[0].strip()), "name": parts[1].strip()}
                            )

                self.teams = teams
                logger.info(f"📊 加载了 {len(teams)} 个球队")
                return teams
            else:
                logger.error(f"❌ 数据库查询失败: {result.stderr}")
                return []

        except Exception as e:
            logger.error(f"❌ 加载球队数据异常: {e}")
            return []

    def normalize_team_name(self, name: str) -> str:
        """标准化球队名称用于比较"""
        if not name:
            return ""

        # 移除国家代码前缀/后缀 (如 "es Barcelona", "Barcelona es")
        parts = name.split()
        if len(parts) >= 2:
            # 移除2字母国家代码
            if len(parts[0]) == 2 and parts[0].islower():
                normalized = " ".join(parts[1:])
                logger.debug(f"🔧 标准化: '{name}' -> '{normalized}'")
                return normalized
            elif len(parts[-1]) == 2 and parts[-1].islower():
                normalized = " ".join(parts[:-1])
                logger.debug(f"🔧 标准化: '{name}' -> '{normalized}'")
                return normalized

        # 移除常见的后缀
        suffixes = ["FC", "CF", "SC", "AC", "CD", "UD", "SD"]
        normalized = name
        for suffix in suffixes:
            if normalized.endswith(f" {suffix}"):
                normalized = normalized[: -len(f" {suffix}")]
                break

        return normalized.strip()

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """计算两个球队名的相似度"""
        # 先标准化名称
        norm1 = self.normalize_team_name(name1.lower())
        norm2 = self.normalize_team_name(name2.lower())

        # 使用SequenceMatcher计算相似度
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity

    def find_duplicate_teams(self) -> list[tuple]:
        """找出重复的球队"""
        duplicates = []
        processed_ids = set()

        logger.info(f"🔍 开始分析 {len(self.teams)} 个球队的相似度...")

        for i, team1 in enumerate(self.teams):
            if team1["id"] in processed_ids:
                continue

            similar_teams = [team1]

            for j, team2 in enumerate(self.teams[i + 1 :], i + 1):
                if team2["id"] in processed_ids:
                    continue

                similarity = self.calculate_similarity(team1["name"], team2["name"])

                if similarity >= self.similarity_threshold:
                    similar_teams.append(team2)
                    processed_ids.add(team2["id"])
                    logger.info(
                        f"🎯 发现相似球队: '{team1['name']}' vs '{team2['name']}' (相似度: {similarity:.3f})"
                    )

            if len(similar_teams) > 1:
                # 选择master球队（名字最短最干净的）
                master = min(similar_teams, key=lambda x: len(x["name"]))

                for team in similar_teams:
                    if team["id"] != master["id"]:
                        duplicates.append((master, team))
                        processed_ids.add(team["id"])

                logger.info(
                    f"👑 选择Master球队: '{master['name']}' (ID: {master['id']})"
                )

        return duplicates

    def generate_merge_plan(self, duplicates: list[tuple]) -> dict:
        """生成合并计划"""
        merge_plan = {
            "generated_at": datetime.now().isoformat(),
            "similarity_threshold": self.similarity_threshold,
            "total_merges": len(duplicates),
            "merges": [],
        }

        for master, duplicate in duplicates:
            merge_plan["merges"].append(
                {
                    "master": {"id": master["id"], "name": master["name"]},
                    "duplicate": {"id": duplicate["id"], "name": duplicate["name"]},
                    "similarity": self.calculate_similarity(
                        master["name"], duplicate["name"]
                    ),
                }
            )

        return merge_plan

    def save_merge_plan(self, merge_plan: dict, filename: str = "merge_plan.json"):
        """保存合并计划到文件"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(merge_plan, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 合并计划已保存到 {filename}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存合并计划失败: {e}")
            return False

    def run(self):
        """执行完整的合并计划生成流程"""
        logger.info("🚀 启动球队实体合并计划生成器")

        # 加载球队数据
        teams = self.load_teams_from_db()
        if not teams:
            return False

        # 找出重复球队
        duplicates = self.find_duplicate_teams()
        logger.info(f"🔍 发现 {len(duplicates)} 组重复球队")

        # 生成合并计划
        merge_plan = self.generate_merge_plan(duplicates)

        # 保存计划
        success = self.save_merge_plan(merge_plan)

        if success:
            logger.info("=" * 60)
            logger.info("🎉 球队合并计划生成完成！")
            logger.info("=" * 60)
            logger.info(f"📊 总球队数: {len(teams)}")
            logger.info(f"🔄 合并对数: {len(duplicates)}")
            logger.info("💾 计划文件: merge_plan.json")
            logger.info("⏱️  下一步: python scripts/execute_team_merges.py")

        return success


def main():
    """主函数"""
    try:
        planner = TeamMergePlanner()
        success = planner.run()

        if success:
            logger.info("✅ 合并计划生成成功")
            return 0
        else:
            logger.error("❌ 合并计划生成失败")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
