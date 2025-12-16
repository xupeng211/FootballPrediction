#!/usr/bin/env python3
"""
全量离线特征提取脚本 (Full-Scale Offline Feature Extraction)

从raw_match_data表中批量提取高级球员特征并更新matches表
使用高性能asyncpg进行批量操作，带进度条显示
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "FootballPrediction"))

import asyncpg
import urllib.parse
from tqdm import tqdm


@dataclass
class TeamFeatures:
    """球队特征数据结构"""

    team_name: str
    team_id: int
    starting_xi_avg_rating: float
    bench_avg_rating: float
    star_player_name: str
    star_player_rating: float
    star_player_id: int
    total_players: int


@dataclass
class MatchFeatures:
    """比赛特征数据结构"""

    external_id: str
    match_id: Optional[int]  # matches表的主键ID
    home_team: TeamFeatures
    away_team: TeamFeatures
    total_players_analyzed: int


class HighPerformanceFeatureExtractor:
    """高性能特征提取器"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None

    async def initialize(self):
        """初始化数据库连接"""
        print("🔧 初始化高性能特征提取器...")

        # 解析数据库URL
        parsed = urllib.parse.urlparse(
            self.db_url.replace("postgresql+asyncpg://", "postgresql://")
        )

        self.conn = await asyncpg.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=parsed.password or "postgres",
            database=parsed.path.lstrip("/") or "football_prediction",
        )

        print("✅ 高性能特征提取器初始化完成")

    async def get_all_raw_records(self) -> List[Dict[str, Any]]:
        """获取所有原始数据记录"""
        print("📊 获取所有原始数据记录...")

        query = """
            SELECT external_id, match_data
            FROM raw_match_data
            ORDER BY external_id
        """

        rows = await self.conn.fetch(query)
        print(f"✅ 找到 {len(rows)} 条原始数据记录")

        # asyncpg返回的记录已经包含正确的数据类型，不需要额外转换
        return rows

    async def get_match_id_mapping(self) -> Dict[str, int]:
        """获取external_id到match_id的映射"""
        print("🔗 获取比赛ID映射关系...")

        query = """
            SELECT m.fotmob_id as external_id, m.id as match_id
            FROM matches m
            WHERE m.fotmob_id IS NOT NULL
        """

        rows = await self.conn.fetch(query)
        mapping = {row["external_id"]: row["match_id"] for row in rows}
        print(f"✅ 找到 {len(mapping)} 个ID映射关系")

        return mapping

    def extract_features_from_raw(self, raw_record) -> Optional[MatchFeatures]:
        """从原始数据中提取特征"""
        # 处理asyncpg返回的Record对象
        if hasattr(raw_record, "external_id"):
            external_id = raw_record["external_id"]
            match_data = raw_record["match_data"]
        else:
            external_id = raw_record["external_id"]
            match_data = raw_record["match_data"]

        # 确保match_data是字典
        if not isinstance(match_data, dict):
            # asyncpg返回的JSONB数据可能需要特殊处理
            import json

            if isinstance(match_data, str):
                try:
                    match_data = json.loads(match_data)
                except json.JSONDecodeError:
                    print(f"⚠️ 记录 {external_id}: 无法解析JSON字符串")
                    return None
            else:
                print(f"⚠️ 记录 {external_id}: match_data 类型为 {type(match_data)}")
                return None

        content = match_data.get("content", {})

        # 获取球队信息
        header = match_data.get("header", {})
        teams = header.get("teams", [])

        if len(teams) < 2:
            return None

        home_team_info = teams[0]
        away_team_info = teams[1]

        # 提取球员数据
        player_stats = content.get("playerStats", {})

        if not player_stats:
            return None

        # 分别处理主客队球员
        home_players = {}
        away_players = {}

        for player_id, player_data in player_stats.items():
            if isinstance(player_data, dict):
                team_id = player_data.get("teamId")
                if team_id == home_team_info.get("id"):
                    home_players[player_id] = player_data
                elif team_id == away_team_info.get("id"):
                    away_players[player_id] = player_data

        # 如果没有找到球员数据，跳过
        if not home_players and not away_players:
            print(f"⚠️ 跳过记录 {external_id}: 没有找到球员数据")
            return None

        # 提取球队特征
        home_features = self._extract_team_features(
            home_players,
            home_team_info.get("name", "Unknown"),
            home_team_info.get("id", 0),
        )

        away_features = self._extract_team_features(
            away_players,
            away_team_info.get("name", "Unknown"),
            away_team_info.get("id", 0),
        )

        return MatchFeatures(
            external_id=external_id,
            match_id=None,  # 稍后填充
            home_team=home_features,
            away_team=away_features,
            total_players_analyzed=len(home_players) + len(away_players),
        )

    def _extract_team_features(
        self, players: Dict[str, Any], team_name: str, team_id: int
    ) -> TeamFeatures:
        """提取单个球队的特征"""

        # 提取球员评分和位置信息
        player_ratings = []
        bench_players = []
        starting_xi_players = []

        for player_id, player_data in players.items():
            if not isinstance(player_data, dict):
                continue

            # 提取评分
            rating = self._extract_player_rating(player_data)
            if rating is None:
                continue

            player_name = player_data.get("name", "Unknown")
            is_goalkeeper = player_data.get("isGoalkeeper", False)

            # 简单判断是否为首发（通过评分数据的存在和完整性）
            is_starting = self._is_starting_player(player_data)

            player_info = {
                "id": player_id,
                "name": player_name,
                "rating": rating,
                "is_goalkeeper": is_goalkeeper,
                "is_starting": is_starting,
            }

            player_ratings.append(player_info)

            if is_starting:
                starting_xi_players.append(player_info)
            else:
                bench_players.append(player_info)

        # 计算平均评分
        starting_xi_avg = (
            sum(p["rating"] for p in starting_xi_players) / len(starting_xi_players)
            if starting_xi_players
            else 0.0
        )
        bench_avg = (
            sum(p["rating"] for p in bench_players) / len(bench_players)
            if bench_players
            else 0.0
        )

        # 找到最佳球员
        all_players_sorted = sorted(
            player_ratings, key=lambda x: x["rating"], reverse=True
        )
        star_player = (
            all_players_sorted[0]
            if all_players_sorted
            else {"name": "N/A", "rating": 0.0, "id": 0}
        )

        return TeamFeatures(
            team_name=team_name,
            team_id=team_id,
            starting_xi_avg_rating=round(starting_xi_avg, 2),
            bench_avg_rating=round(bench_avg, 2),
            star_player_name=star_player["name"],
            star_player_rating=round(star_player["rating"], 2),
            star_player_id=star_player["id"],
            total_players=len(player_ratings),
        )

    def _extract_player_rating(self, player_data: Dict[str, Any]) -> Optional[float]:
        """提取球员评分"""
        # 方法1: 从stats中查找rating
        stats = player_data.get("stats", [])
        for stat_section in stats:
            if isinstance(stat_section, dict) and "stats" in stat_section:
                section_stats = stat_section["stats"]
                for key, value in section_stats.items():
                    if isinstance(value, dict) and "stat" in value:
                        stat_value = value["stat"]
                        if key == "FotMob rating" or key == "rating":
                            try:
                                return float(stat_value.get("value", 0))
                            except (ValueError, TypeError):
                                continue

        # 方法2: 直接查找rating字段
        for key, value in player_data.items():
            if "rating" in key.lower() and isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, dict) and "value" in value:
                try:
                    return float(value["value"])
                except (ValueError, TypeError):
                    continue

        return None

    def _is_starting_player(self, player_data: Dict[str, Any]) -> bool:
        """判断是否为首发球员"""
        # 简单的启发式方法：有完整统计数据且评分较高的通常是首发
        rating = self._extract_player_rating(player_data)

        # 门将通常是首发
        if player_data.get("isGoalkeeper", False):
            return True

        # 评分较高的球员更可能是首发
        if rating and rating > 6.5:
            return True

        # 如果有minutes played字段，大于60分钟的通常是首发
        stats = player_data.get("stats", [])
        for stat_section in stats:
            if isinstance(stat_section, dict) and "stats" in stat_section:
                section_stats = stat_section["stats"]
                for key, value in section_stats.items():
                    if "minutes" in key.lower() and isinstance(value, dict):
                        minutes = value.get("stat", {}).get("value", 0)
                        if minutes and minutes > 60:
                            return True

        return False

    async def batch_update_matches(
        self, features_list: List[MatchFeatures], id_mapping: Dict[str, int]
    ):
        """批量更新matches表"""
        print("💾 开始批量更新matches表...")

        successful_updates = 0
        failed_updates = 0

        # 准备批量更新语句
        for features in tqdm(features_list, desc="批量更新比赛特征"):
            try:
                # 查找对应的match_id
                match_id = id_mapping.get(features.external_id)
                if not match_id:
                    continue

                # 构建更新语句
                update_query = """
                    UPDATE matches
                    SET home_xi_rating = $1,
                        away_xi_rating = $2,
                        home_star_rating = $3,
                        away_star_rating = $4,
                        home_bench_rating = $5,
                        away_bench_rating = $6,
                        updated_at = NOW()
                    WHERE id = $7
                """

                await self.conn.execute(
                    update_query,
                    features.home_team.starting_xi_avg_rating,
                    features.away_team.starting_xi_avg_rating,
                    features.home_team.star_player_rating,
                    features.away_team.star_player_rating,
                    features.home_team.bench_avg_rating,
                    features.away_team.bench_avg_rating,
                    match_id,
                )

                successful_updates += 1

            except Exception as e:
                failed_updates += 1
                print(f"❌ 更新失败 {features.external_id}: {e}")
                continue

        print(f"\n✅ 批量更新完成:")
        print(f"   成功: {successful_updates} 条记录")
        print(f"   失败: {failed_updates} 条记录")

    async def process_all_records(self, batch_size: int = 50):
        """处理所有记录"""
        print("🚀 开始全量特征提取...")

        # 获取所有原始记录
        raw_records = await self.get_all_raw_records()

        # 获取ID映射
        id_mapping = await self.get_match_id_mapping()

        # 提取特征
        all_features = []
        processed_count = 0
        skipped_count = 0

        print("\n🧠 开始特征提取...")
        for record in tqdm(raw_records, desc="提取球员特征"):
            features = self.extract_features_from_raw(record)
            if features:
                # 填充match_id
                features.match_id = id_mapping.get(features.external_id)
                all_features.append(features)
                processed_count += 1
            else:
                skipped_count += 1

        print(f"\n📊 特征提取统计:")
        print(f"   成功提取: {processed_count} 条记录")
        print(f"   跳过: {skipped_count} 条记录")
        print(f"   总计特征: {len(all_features)} 条")

        if not all_features:
            print("❌ 没有可处理的特征数据")
            return

        # 批量更新数据库
        await self.batch_update_matches(all_features, id_mapping)

    async def verify_results(self, limit: int = 5):
        """验证更新结果"""
        print(f"\n🔍 验证更新结果 (显示前 {limit} 条)...")

        query = f"""
            SELECT
                fotmob_id,
                home_team_name,
                away_team_name,
                home_xi_rating,
                away_xi_rating,
                home_star_rating,
                away_star_rating,
                home_bench_rating,
                away_bench_rating
            FROM matches
            WHERE home_xi_rating IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT {limit}
        """

        rows = await self.conn.fetch(query)

        print("\n📋 验证结果:")
        for i, row in enumerate(rows, 1):
            print(f"{i}. {row['home_team_name']} vs {row['away_team_name']}")
            print(
                f"   首发均分: 主队 {row['home_xi_rating']}, 客队 {row['away_xi_rating']}"
            )
            print(
                f"   球星评分: 主队 {row['home_star_rating']}, 客队 {row['away_star_rating']}"
            )
            print(
                f"   板凳均分: 主队 {row['home_bench_rating']}, 客队 {row['away_bench_rating']}"
            )
            print(f"   FotMob ID: {row['fotmob_id']}")
            print()

    async def close(self):
        """关闭连接"""
        if self.conn:
            await self.conn.close()
        print("🔐 高性能特征提取器已关闭")


async def main():
    """主函数"""
    print("🚀 启动全量离线特征提取")
    print("=" * 60)

    # 数据库配置
    db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction"

    extractor = HighPerformanceFeatureExtractor(db_url)

    try:
        # 初始化
        await extractor.initialize()

        # 开始时间
        start_time = time.time()

        # 处理所有记录
        await extractor.process_all_records()

        # 计算耗时
        elapsed_time = time.time() - start_time
        print(f"\n⏱️ 总耗时: {elapsed_time:.2f} 秒")

        # 验证结果
        await extractor.verify_results()

        print("\n🎉 全量离线特征提取完成！")
        print("✨ 球员级高级特征已成功集成到数据湖系统")

    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理资源
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())
