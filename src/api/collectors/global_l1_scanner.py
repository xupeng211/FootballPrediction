#!/usr/bin/env python3
"""
V35.2 全球广域 L1 扫描器 (The Big List Scanner - FIX)
========================================================
跨 5 年、6 大联赛的完整比赛索引生成器

V35.2 修复:
- 修正 FotMob API league ID 错误 (ID 42/87 互换问题)
- 移除数据不完整的联赛 (Champions League 只有 144 场)
- 西甲使用正确 ID: 87

目标: 10,000+ 场比赛的核心索引清单
范围: 2021-2025 赛季 × 6 大联赛
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import sys

import aiohttp

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


@dataclass
class LeagueConfig:
    """联赛配置"""

    league_id: int
    league_name: str
    fotmob_code: str  # FotMob API 中的赛季代码格式


# 7 大联赛配置 (V35.3 最终版: 恢复欧冠)
# V35.3 修正: 欧冠每赛季 ~144 场是正常的（小组赛+淘汰赛）
LEAGUE_CONFIGS = [
    LeagueConfig(47, "Premier League", ""),  # 380 场/赛季
    LeagueConfig(87, "La Liga", ""),  # 380 场/赛季
    LeagueConfig(54, "Serie A", ""),  # 306 场/赛季
    LeagueConfig(53, "Bundesliga", ""),  # 306 场/赛季
    LeagueConfig(61, "Ligue 1", ""),  # 306 场/赛季
    LeagueConfig(12, "Eredivisie", ""),  # 荷甲 (数据量待验证)
    LeagueConfig(42, "Champions League", ""),  # 144 场/赛季 (V35.3 恢复)
]

# 赛季映射 (FotMob 格式) - V36.0 修复
# FotMob API 使用 YYYY/YYYY 格式（如 "2020/2021"）
SEASONS = {
    "20/21": "2020/2021",
    "21/22": "2021/2022",
    "22/23": "2022/2023",
    "23/24": "2023/2024",
    "24/25": "2024/2025",
}


class GlobalL1Scanner:
    """
    全球广域 L1 扫描器

    核心功能:
    1. 跨赛季扫描: 2021-2025 (4 完整 + 1 当前)
    2. 多联赛并行: 5 大联赛同时抓取
    3. 智能去重: 避免重复索引
    4. 实时统计: 进度追踪和报告
    """

    def __init__(self):
        """初始化扫描器"""
        self.session: aiohttp.ClientSession | None = None
        self.scan_stats = {
            "total_matches": 0,
            "by_league": {},
            "by_season": {},
            "finished_matches": 0,
            "scheduled_matches": 0,
        }
        self.match_index: list[dict] = []

    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=10)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()

    async def fetch_league_matches(
        self, league_id: int, season_code: str, season_name: str
    ) -> list[dict]:
        """
        获取指定联赛和赛季的所有比赛

        Args:
            league_id: 联赛 ID
            season_code: FotMob 赛季代码 (如 "2122")
            season_name: 显示名称 (如 "21/22")

        Returns:
            比赛列表
        """
        url = f"https://www.fotmob.com/api/leagues?id={league_id}&season={season_code}"

        try:
            if not self.session:
                raise RuntimeError("Session not initialized")

            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(
                        f"获取联赛 {league_id} 赛季 {season_name} 失败: {response.status}"
                    )
                    return []

                data = await response.json()

                # 解析比赛数据
                matches = self._parse_league_matches(data, league_id, season_name)
                logger.info(f"✓ {league_id} - {season_name}: {len(matches)} 场比赛")

                return matches

        except Exception as e:
            logger.exception(f"获取联赛 {league_id} 赛季 {season_name} 失败: {e}")
            return []

    def _parse_league_matches(self, data: dict, league_id: int, season_name: str) -> list[dict]:
        """
        解析联赛比赛数据

        Args:
            data: FotMob API 响应
            league_id: 联赛 ID
            season_name: 赛季名称

        Returns:
            解析后的比赛列表
        """
        matches = []

        try:
            # 导航到 matches 数据 - fixtures.allMatches 路径
            fixtures = data.get("fixtures", {})
            all_matches = fixtures.get("allMatches", [])

            for match_data in all_matches:
                # 提取基础信息
                match_id = match_data.get("id")
                if not match_id:
                    continue

                home_team = match_data.get("home", {})
                away_team = match_data.get("away", {})
                status_obj = match_data.get("status", {})
                match_time = status_obj.get("utcTime", "")

                # 判断比赛状态 - API 使用布尔值
                is_finished = status_obj.get("finished", False)
                is_started = status_obj.get("started", False)
                is_scheduled = not is_started and not is_finished

                match_info = {
                    "match_id": match_id,
                    "league_id": league_id,
                    "season": season_name,
                    "home_team": home_team.get("name", "Unknown"),
                    "home_team_id": int(home_team.get("id", 0)),
                    "away_team": away_team.get("name", "Unknown"),
                    "away_team_id": int(away_team.get("id", 0)),
                    "status": "finished"
                    if is_finished
                    else ("scheduled" if is_scheduled else "ongoing"),
                    "is_finished": is_finished,
                    "is_scheduled": is_scheduled,
                    "match_time": match_time,
                    "home_score": status_obj.get("homeScore"),
                    "away_score": status_obj.get("awayScore"),
                }

                matches.append(match_info)

                # 更新统计
                self.scan_stats["total_matches"] += 1
                league_name = next(
                    (lc.league_name for lc in LEAGUE_CONFIGS if lc.league_id == league_id),
                    str(league_id),
                )
                if league_name not in self.scan_stats["by_league"]:
                    self.scan_stats["by_league"][league_name] = 0
                self.scan_stats["by_league"][league_name] += 1

                if season_name not in self.scan_stats["by_season"]:
                    self.scan_stats["by_season"][season_name] = 0
                self.scan_stats["by_season"][season_name] += 1

                if is_finished:
                    self.scan_stats["finished_matches"] += 1
                if is_scheduled:
                    self.scan_stats["scheduled_matches"] += 1

        except Exception as e:
            logger.exception(f"解析比赛数据失败: {e}")

        return matches

    async def scan_all(self) -> list[dict]:
        """
        执行全量扫描

        Returns:
            所有比赛索引列表
        """
        tasks = []
        task_info = []

        logger.info("🌍 开始全球广域 L1 扫描...")
        logger.info(f"📊 目标: {len(LEAGUE_CONFIGS)} 大联赛 × {len(SEASONS)} 赛季")

        # 为每个联赛-赛季组合创建任务
        for league_config in LEAGUE_CONFIGS:
            for season_name, season_code in SEASONS.items():
                task = self.fetch_league_matches(league_config.league_id, season_code, season_name)
                tasks.append(task)
                task_info.append(
                    {
                        "league": league_config.league_name,
                        "season": season_name,
                    }
                )

        # 并发执行所有任务
        logger.info(f"🚀 启动 {len(tasks)} 个并发扫描任务...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        self.match_index = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"任务 {task_info[i]} 失败: {result}")
                continue
            if result:
                self.match_index.extend(result)

        # V35.1 修复: 使用复合唯一键去重 (league_id + season + match_id)
        # 这确保跨赛季的相同 match_id 不会被错误去重
        unique_matches = {}
        for match in self.match_index:
            # 复合唯一键: league_id + season + match_id
            unique_key = f"{match['league_id']}_{match['season']}_{match['match_id']}"
            if unique_key not in unique_matches:
                unique_matches[unique_key] = match

        self.match_index = list(unique_matches.values())
        self.scan_stats["total_matches"] = len(self.match_index)

        # 修正统计: 重新计算按赛季和按联赛的分布
        self._recalculate_stats()

        logger.info(f"✅ 扫描完成! 去重后总计: {len(self.match_index)} 场比赛")

        return self.match_index

    def _recalculate_stats(self):
        """重新计算统计信息 (去重后)"""
        # 重置统计
        self.scan_stats["by_league"] = {}
        self.scan_stats["by_season"] = {}
        self.scan_stats["finished_matches"] = 0
        self.scan_stats["scheduled_matches"] = 0

        for match in self.match_index:
            league_name = next(
                (lc.league_name for lc in LEAGUE_CONFIGS if lc.league_id == match["league_id"]),
                f"League_{match['league_id']}",
            )
            season = match["season"]

            # 按联赛统计
            if league_name not in self.scan_stats["by_league"]:
                self.scan_stats["by_league"][league_name] = 0
            self.scan_stats["by_league"][league_name] += 1

            # 按赛季统计
            if season not in self.scan_stats["by_season"]:
                self.scan_stats["by_season"][season] = 0
            self.scan_stats["by_season"][season] += 1

            # 按状态统计
            if match.get("is_finished"):
                self.scan_stats["finished_matches"] += 1
            if match.get("is_scheduled"):
                self.scan_stats["scheduled_matches"] += 1

    def save_index(self, output_dir: Path) -> Path:
        """
        保存比赛索引到文件

        Args:
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"global_match_index_v35.1_{timestamp}.json"

        index_data = {
            "scan_metadata": {
                "scan_version": "V35.1-FIXED",
                "scan_timestamp": datetime.now().isoformat(),
                "total_matches": len(self.match_index),
                "leagues_covered": len(LEAGUE_CONFIGS),
                "seasons_covered": len(SEASONS),
                "dedup_method": "composite_key (league_id + season + match_id)",
            },
            "scan_stats": self.scan_stats,
            "match_index": self.match_index,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 比赛索引已保存: {output_file}")
        logger.info(f"   文件大小: {output_file.stat().st_size:,} 字节")

        return output_file

    def print_summary(self):
        """打印扫描摘要"""


        for _league, count in sorted(self.scan_stats["by_league"].items()):
            (
                (count / self.scan_stats["total_matches"] * 100)
                if self.scan_stats["total_matches"] > 0
                else 0
            )

        for _season, count in sorted(self.scan_stats["by_season"].items()):
            (
                (count / self.scan_stats["total_matches"] * 100)
                if self.scan_stats["total_matches"] > 0
                else 0
            )

        # 目标达成分析
        target = 5000
        achieved = len(self.match_index)
        (achieved / target * 100) if target > 0 else 0


        if achieved >= target:
            pass
        else:
            target - achieved



async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    async with GlobalL1Scanner() as scanner:
        # 执行全量扫描
        await scanner.scan_all()

        # 打印摘要
        scanner.print_summary()

        # 保存索引
        output_dir = Path("data/production/global_manifest_v34")
        scanner.save_index(output_dir)



if __name__ == "__main__":
    asyncio.run(main())
