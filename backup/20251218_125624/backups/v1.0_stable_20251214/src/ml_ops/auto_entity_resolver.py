#!/usr/bin/env python3
"""
MLOps首席架构师专用 - 自动化实体解析器
处理新球队的自动映射和插入，无需人工干预
"""

import subprocess
import logging
import json
from typing import Optional
from datetime import datetime
from difflib import SequenceMatcher
import asyncio
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AutoEntityResolver:
    """自动化实体解析器"""

    def __init__(self):
        self.existing_teams = {}
        self.team_mapping = {}
        self.stats = {
            "new_teams_detected": 0,
            "high_confidence_matches": 0,
            "low_confidence_matches": 0,
            "new_teams_inserted": 0,
            "processing_time": 0,
        }

    async def load_existing_teams(self) -> bool:
        """加载数据库中现有的球队"""
        try:
            logger.info("📊 加载现有球队数据...")

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
            if result.returncode != 0:
                logger.error(f"❌ 加载球队数据失败: {result.stderr}")
                return False

            teams = {}
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split("|")
                    if len(parts) >= 2:
                        try:
                            team_id = int(parts[0].strip())
                            team_name = parts[1].strip()
                            teams[team_name] = team_id
                        except ValueError:
                            continue

            self.existing_teams = teams
            logger.info(f"✅ 加载了 {len(teams)} 个现有球队")
            return True

        except Exception as e:
            logger.error(f"❌ 加载球队数据异常: {e}")
            return False

    def normalize_team_name(self, name: str) -> str:
        """标准化球队名称用于匹配"""
        if not name:
            return ""

        name = name.strip()

        # 移除常见后缀
        suffixes = ["FC", "CF", "SC", "AC", "CD", "UD", "SD"]
        for suffix in suffixes:
            if name.endswith(f" {suffix}"):
                name = name[: -len(f" {suffix}")]
                break

        # 移除常见前缀
        prefixes = ["FC ", "CD ", "SD "]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break

        # 标准化空格和大小写
        name = " ".join(name.split())
        return name.title()  # 使用title()方法将首字母大写

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """计算两个球队名的相似度"""
        norm1 = self.normalize_team_name(name1.lower())
        norm2 = self.normalize_team_name(name2.lower())

        return SequenceMatcher(None, norm1, norm2).ratio()

    async def resolve_team_entity(self, team_name: str) -> dict:
        """解析单个球队实体"""
        result = {
            "input_name": team_name,
            "resolution_type": None,  # 'high_confidence_match', 'low_confidence_match', 'new_team'
            "matched_team_id": None,
            "matched_team_name": None,
            "similarity_score": 0.0,
            "action_taken": None,
        }

        try:
            # 1. 精确匹配
            if team_name in self.existing_teams:
                result["resolution_type"] = "exact_match"
                result["matched_team_id"] = self.existing_teams[team_name]
                result["matched_team_name"] = team_name
                result["similarity_score"] = 1.0
                result["action_taken"] = "used_existing"
                return result

            # 2. 高置信度模糊匹配 (>95%)
            best_match = None
            best_similarity = 0.0
            best_team_id = None

            for existing_name, team_id in self.existing_teams.items():
                similarity = self.calculate_similarity(team_name, existing_name)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = existing_name
                    best_team_id = team_id

            if best_similarity >= 0.95:
                result["resolution_type"] = "high_confidence_match"
                result["matched_team_id"] = best_team_id
                result["matched_team_name"] = best_match
                result["similarity_score"] = best_similarity
                result["action_taken"] = "auto_mapped"
                self.stats["high_confidence_matches"] += 1
                return result

            # 3. 低置信度匹配 (>85% < 95%)
            elif best_similarity >= 0.85:
                result["resolution_type"] = "low_confidence_match"
                result["matched_team_id"] = best_team_id
                result["matched_team_name"] = best_match
                result["similarity_score"] = best_similarity
                result["action_taken"] = "auto_mapped_caution"
                self.stats["low_confidence_matches"] += 1
                return result

            # 4. 新球队 - 自动插入
            else:
                result["resolution_type"] = "new_team"
                result["action_taken"] = "inserted_new"
                self.stats["new_teams_inserted"] += 1

                # 插入新球队到数据库
                new_team_id = await self.insert_new_team(team_name)
                if new_team_id:
                    result["matched_team_id"] = new_team_id
                    # 更新现有球队列表
                    self.existing_teams[team_name] = new_team_id

                logger.info(f"🆕 检测到新球队: '{team_name}' (ID: {new_team_id})")
                return result

        except Exception as e:
            logger.error(f"❌ 解析球队实体失败 '{team_name}': {e}")
            result["action_taken"] = "error"
            return result

    async def insert_new_team(self, team_name: str) -> Optional[int]:
        """插入新球队到数据库"""
        try:
            # 验证和清理team_name输入，防止SQL注入
            # 确保team_name不包含危险字符
            if not team_name or len(team_name) > 100:
                logger.error(f"❌ 无效的球队名称: {team_name}")
                return None

            # 检查是否包含危险字符
            dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
            for char in dangerous_chars:
                if char in team_name.lower():
                    logger.error(f"❌ 球队名称包含危险字符: {team_name}")
                    return None

            # 使用双引号包围team_name以转义特殊字符（PostgreSQL风格）
            safe_team_name = team_name.replace("'", "''")  # 转义单引号

            cmd = [
                "docker-compose",
                "exec",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-c",
                f"INSERT INTO teams (name, country, created_at, updated_at) VALUES ('{safe_team_name}', 'Unknown', NOW(), NOW()) RETURNING id;",  # noqa: B608  # Input validated and escaped above
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # 解析返回的ID
                try:
                    # PostgreSQL返回格式: "id\n--------\n 123\n(1 row)\n"
                    lines = result.stdout.strip().split("\n")
                    if len(lines) >= 3:
                        id_line = lines[2].strip()
                        new_id = int(id_line)
                    else:
                        # 备用解析方法
                        import re

                        match = re.search(r"\d+", result.stdout)
                        if match:
                            new_id = int(match.group())
                        else:
                            raise ValueError("无法解析返回的ID")
                except (ValueError, IndexError) as parse_error:
                    logger.error(
                        f"❌ 解析新球队ID失败: {result.stdout} - {parse_error}"
                    )
                    return None

                logger.info(f"✅ 成功插入新球队: {team_name} (ID: {new_id})")
                return new_id
            else:
                logger.error(f"❌ 插入新球队失败: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ 插入新球队异常: {e}")
            return None

    async def resolve_team_list(self, team_names: list[str]) -> dict:
        """解析球队列表"""
        start_time = datetime.now()
        results = []

        logger.info(f"🔄 开始解析 {len(team_names)} 个球队...")

        for i, team_name in enumerate(team_names, 1):
            logger.info(f"🔍 [{i}/{len(team_names)}] 解析: {team_name}")
            result = await self.resolve_team_entity(team_name)
            results.append(result)

            # 统计新检测到的球队
            if result["resolution_type"] == "new_team":
                self.stats["new_teams_detected"] += 1

        # 计算处理时间
        self.stats["processing_time"] = (datetime.now() - start_time).total_seconds()

        # 生成解析报告
        self.generate_resolution_report(results)

        return {
            "results": results,
            "team_mapping": {
                r["input_name"]: r["matched_team_id"]
                for r in results
                if r["matched_team_id"]
            },
            "stats": self.stats,
        }

    def generate_resolution_report(self, results: list[dict]):
        """生成解析报告"""
        resolution_counts = {}
        for result in results:
            resolution_type = result["resolution_type"]
            resolution_counts[resolution_type] = (
                resolution_counts.get(resolution_type, 0) + 1
            )

        logger.info("=" * 60)
        logger.info("🎯 自动实体解析报告")
        logger.info("=" * 60)
        logger.info(f"📊 处理球队总数: {len(results)}")
        logger.info(f"🆕 新球队检测: {self.stats['new_teams_detected']}")
        logger.info(f"✅ 高置信度匹配: {self.stats['high_confidence_matches']}")
        logger.info(f"⚠️  低置信度匹配: {self.stats['low_confidence_matches']}")
        logger.info(f"➕ 新球队插入: {self.stats['new_teams_inserted']}")
        logger.info(f"⏱️  处理耗时: {self.stats['processing_time']:.1f}秒")

        logger.info("📋 解析类型分布:")
        for resolution_type, count in resolution_counts.items():
            logger.info(f"   {resolution_type}: {count}")

        # 保存详细报告
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "resolution_counts": resolution_counts,
            "details": results,
        }

        report_path = Path("logs/entity_resolution_report.json")
        report_path.parent.mkdir(exist_ok=True)

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 详细报告已保存: {report_path}")
        except Exception as e:
            logger.warning(f"⚠️ 保存报告失败: {e}")


async def main():
    """主函数 - 测试用"""
    resolver = AutoEntityResolver()

    # 加载现有球队
    await resolver.load_existing_teams()

    # 测试一些球队名称
    test_teams = [
        "Manchester City",  # 现有球队
        "Real Madrid FC",  # 模糊匹配
        "New Team Example",  # 新球队
        "Barcelona es",  # 国家代码变体
        "Chelsea FC",  # FC后缀变体
    ]

    results = await resolver.resolve_team_list(test_teams)
    logger.info(f"✅ 测试完成，结果: {len(results['results'])} 个球队")


if __name__ == "__main__":
    asyncio.run(main())
