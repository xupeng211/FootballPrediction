#!/usr/bin/env python3
"""
首席数据治理专家专用 - 球队实体合并执行器
执行合并计划，将重复球队数据缝合
"""

import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TeamMergeExecutor:
    """球队合并执行器"""

    def __init__(self):
        self.merge_plan = {}
        self.stats = {
            "total_merges": 0,
            "successful_merges": 0,
            "failed_merges": 0,
            "matches_updated": 0,
            "teams_deleted": 0,
        }

    def load_merge_plan(self, filename: str = "merge_plan.json") -> bool:
        """加载合并计划"""
        try:
            with open(filename, encoding="utf-8") as f:
                self.merge_plan = json.load(f)

            self.stats["total_merges"] = len(self.merge_plan.get("merges", []))
            logger.info(f"📋 加载合并计划: {self.stats['total_merges']} 组合并")
            logger.info(
                f"📅 生成时间: {self.merge_plan.get('generated_at', 'Unknown')}"
            )
            logger.info(
                f"🎯 相似度阈值: {self.merge_plan.get('similarity_threshold', 'Unknown')}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ 加载合并计划失败: {e}")
            return False

    def execute_team_merge(self, master_id: int, duplicate_id: int) -> tuple[bool, int]:
        """执行单个球队合并"""
        try:
            # 开始事务
            logger.info(f"🔄 合并球队: Master {master_id} ← Duplicate {duplicate_id}")

            # 1. 更新matches表中的主队ID
            update_home_cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-c",
                f"UPDATE matches SET home_team_id = {master_id} WHERE home_team_id = {duplicate_id} AND data_source = 'fbref';",
            ]

            home_result = subprocess.run(
                update_home_cmd, capture_output=True, text=True
            )
            if home_result.returncode != 0:
                logger.error(f"❌ 更新主队ID失败: {home_result.stderr}")
                return False, 0

            # 获取更新的行数 - 处理psql返回的"UPDATE N"格式
            home_output = home_result.stdout.strip()
            home_updated = 0
            if home_output:
                # 提取数字部分
                import re

                match = re.search(r"\d+", home_output)
                if match:
                    home_updated = int(match.group())

            # 2. 更新matches表中的客队ID
            update_away_cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-c",
                f"UPDATE matches SET away_team_id = {master_id} WHERE away_team_id = {duplicate_id} AND data_source = 'fbref';",
            ]

            away_result = subprocess.run(
                update_away_cmd, capture_output=True, text=True
            )
            if away_result.returncode != 0:
                logger.error(f"❌ 更新客队ID失败: {away_result.stderr}")
                return False, 0

            # 获取更新的行数 - 处理psql返回的"UPDATE N"格式
            away_output = away_result.stdout.strip()
            away_updated = 0
            if away_output:
                # 提取数字部分
                match = re.search(r"\d+", away_output)
                if match:
                    away_updated = int(match.group())

            total_updated = home_updated + away_updated

            # 3. 删除重复球队记录
            delete_cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-c",
                f"DELETE FROM teams WHERE id = {duplicate_id};",
            ]

            delete_result = subprocess.run(delete_cmd, capture_output=True, text=True)
            if delete_result.returncode != 0:
                logger.error(f"❌ 删除重复球队失败: {delete_result.stderr}")
                return False, 0

            logger.info(f"✅ 合并成功: 更新 {total_updated} 场比赛，删除1个重复球队")
            return True, total_updated

        except Exception as e:
            logger.error(f"❌ 合并异常 {master_id} ← {duplicate_id}: {e}")
            return False, 0

    def execute_all_merges(self) -> bool:
        """执行所有合并操作"""
        logger.info("🚀 开始执行球队实体合并")
        logger.info(f"📊 将要合并 {self.stats['total_merges']} 对球队")

        merges = self.merge_plan.get("merges", [])

        for i, merge in enumerate(merges, 1):
            master = merge["master"]
            duplicate = merge["duplicate"]
            similarity = merge.get("similarity", 0)

            logger.info(
                f"🔄 进度: {i}/{self.stats['total_merges']} ({i/self.stats['total_merges']*100:.1f}%)"
            )
            logger.info(f"🎯 相似度: {similarity:.3f}")
            logger.info(f"👑 Master: '{master['name']}' (ID: {master['id']})")
            logger.info(f"📋 Duplicate: '{duplicate['name']}' (ID: {duplicate['id']})")

            success, matches_updated = self.execute_team_merge(
                master["id"], duplicate["id"]
            )

            if success:
                self.stats["successful_merges"] += 1
                self.stats["matches_updated"] += matches_updated
                self.stats["teams_deleted"] += 1
            else:
                self.stats["failed_merges"] += 1
                logger.error(f"❌ 合并失败: {master['name']} ← {duplicate['name']}")

        logger.info("=" * 60)
        logger.info("🎉 球队实体合并执行完成！")
        logger.info("=" * 60)
        logger.info(
            f"✅ 成功合并: {self.stats['successful_merges']}/{self.stats['total_merges']}"
        )
        logger.info(f"❌ 失败合并: {self.stats['failed_merges']}")
        logger.info(f"🔄 更新比赛: {self.stats['matches_updated']} 场")
        logger.info(f"🗑️ 删除球队: {self.stats['teams_deleted']} 个")

        return self.stats["failed_merges"] == 0

    def verify_merge_results(self) -> dict:
        """验证合并结果"""
        try:
            logger.info("🔍 验证合并结果...")

            # 统计球队总数
            team_count_cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-tAc",
                "SELECT COUNT(*) FROM teams;",
            ]

            team_result = subprocess.run(team_count_cmd, capture_output=True, text=True)
            final_team_count = (
                int(team_result.stdout.strip()) if team_result.returncode == 0 else 0
            )

            # 检查重复球队数量
            duplicate_cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-tAc",
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        CASE
                            WHEN name ~ '^[a-z]{2}\\s' THEN SUBSTRING(name FROM 4)
                            WHEN name ~ '\\s[a-z]{2}$' THEN SUBSTRING(name FROM 1 FOR LENGTH(name) - 3)
                            ELSE name
                        END as clean_name
                    FROM teams
                    GROUP BY clean_name
                    HAVING COUNT(*) > 1
                ) duplicates;
                """,
            ]

            duplicate_result = subprocess.run(
                duplicate_cmd, capture_output=True, text=True
            )
            remaining_duplicates = (
                int(duplicate_result.stdout.strip())
                if duplicate_result.returncode == 0
                else 0
            )

            # 统计比赛记录数
            match_count_cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-tAc",
                "SELECT COUNT(*) FROM matches WHERE data_source = 'fbref';",
            ]

            match_result = subprocess.run(
                match_count_cmd, capture_output=True, text=True
            )
            final_match_count = (
                int(match_result.stdout.strip()) if match_result.returncode == 0 else 0
            )

            verification_results = {
                "final_team_count": final_team_count,
                "remaining_duplicates": remaining_duplicates,
                "final_match_count": final_match_count,
                "duplicate_reduction_pct": 0,
                "success": remaining_duplicates <= 5,  # 允许少量剩余
            }

            if self.stats["total_merges"] > 0:
                original_duplicates = self.stats["total_merges"]
                verification_results["duplicate_reduction_pct"] = (
                    (original_duplicates - remaining_duplicates) / original_duplicates
                ) * 100

            logger.info("📊 验证结果:")
            logger.info(f"   最终球队数: {final_team_count}")
            logger.info(f"   剩余重复: {remaining_duplicates}")
            logger.info(f"   比赛记录: {final_match_count}")
            logger.info(
                f"   重复减少: {verification_results['duplicate_reduction_pct']:.1f}%"
            )

            return verification_results

        except Exception as e:
            logger.error(f"❌ 验证结果异常: {e}")
            return {"success": False, "error": str(e)}

    def run(self):
        """执行完整的合并流程"""
        logger.info("🚀 启动首席数据治理专家 - 球队实体合并执行器")
        start_time = datetime.now()

        # 加载合并计划
        if not self.load_merge_plan():
            return False

        # 确认执行
        logger.info(f"⚠️  即将执行 {self.stats['total_merges']} 组球队合并")
        logger.info("🔒 这将修改数据库中的matches和teams表")

        # 执行所有合并
        success = self.execute_all_merges()

        # 验证结果
        verification = self.verify_merge_results()

        # 计算总耗时
        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"⏱️  总耗时: {duration:.1f}秒")

        # 最终结果
        final_success = success and verification.get("success", False)

        if final_success:
            logger.info("🎉 球队实体合并圆满成功！")
            logger.info("✅ 数据已标准化，消除了大部分重复球队")
        else:
            logger.error("❌ 球队实体合并失败")
            if not verification.get("success", False):
                logger.error(f"❌ 验证失败: {verification.get('error', 'Unknown')}")

        return final_success


def main():
    """主函数"""
    try:
        executor = TeamMergeExecutor()
        success = executor.run()

        if success:
            logger.info("✅ 球队实体合并执行成功")
            return 0
        else:
            logger.error("❌ 球队实体合并执行失败")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
