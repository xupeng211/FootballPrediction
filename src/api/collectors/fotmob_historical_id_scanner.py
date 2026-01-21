#!/usr/bin/env python3
"""
V36.0 纯净破冰 - FotMob 历史赛季 ID 挖掘器
============================================
通过【球队路径】绕过联赛接口限制，强制挖掘 22/23、23/24 赛季 Match IDs

核心策略:
1. 避开 /leagues?id=X&season=Y 受限端点
2. 使用 /teams?id=X&tab=matches 自由访问
3. 从球队历史赛程聚合联赛比赛 ID

单一数据源: FotMob (纯净架构)
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path
import random
import time

import aiohttp

logger = logging.getLogger(__name__)


# ============================================================
# V35.2 继承: 深度反爬盔甲
# ============================================================

# UA 池 - 模拟真实浏览器
UA_POOL = [
    # Chrome 120 (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Chrome 119 (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome 120 (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox 121 (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox 120 (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Safari 17 (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge 120 (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# Accept-Language 池
LANGUAGE_POOL = [
    "en-US,en;q=0.9,en-GB;q=0.8",
    "en-GB,en;q=0.9",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en;q=0.8",
]


# ============================================================
# V36.0: 种子球队池 (按联赛分类)
# ============================================================

SEED_TEAMS_BY_LEAGUE = {
    # 英超 Premier League (47)
    47: {
        "name": "Premier League",
        "teams": [
            {"id": 8456, "name": "Manchester City"},  # 当前冠军
            {"id": 8650, "name": "Arsenal"},  # 传统豪门
            {"id": 8586, "name": "Liverpool"},  # 传统豪门
            {"id": 10260, "name": "Tottenham"},  # 传统豪门
            {"id": 8630, "name": "Manchester United"},  # 传统豪门
            {"id": 8455, "name": "Chelsea"},  # 传统豪门
            {"id": 9825, "name": "Newcastle"},  # 新晋势力
            {"id": 8488, "name": "Aston Villa"},  # 历史劲旅
        ],
    },
    # 西甲 La Liga (87)
    87: {
        "name": "La Liga",
        "teams": [
            {"id": 8631, "name": "Real Madrid"},  # 传统豪门
            {"id": 3785, "name": "Barcelona"},  # 传统豪门
            {"id": 8633, "name": "Atletico Madrid"},  # 传统豪门
            {"id": 8636, "name": "Sevilla"},  # 传统豪门
            {"id": 4484, "name": "Athletic Bilbao"},  # 传统劲旅
            {"id": 4025, "name": "Real Sociedad"},  # 新晋势力
            {"id": 8629, "name": "Villarreal"},  # 传统劲旅
            {"id": 3787, "name": "Real Betis"},  # 传统劲旅
        ],
    },
    # 德甲 Bundesliga (54)
    54: {
        "name": "Bundesliga",
        "teams": [
            {"id": 9823, "name": "Bayern Munich"},  # 传统豪门
            {"id": 9810, "name": "Borussia Dortmund"},  # 传统豪门
            {"id": 8019, "name": "Bayer Leverkusen"},  # 新晋势力
            {"id": 8035, "name": "Eintracht Frankfurt"},  # 传统劲旅
            {"id": 9845, "name": "Wolfsburg"},  # 传统劲旅
            {"id": 8178, "name": "RB Leipzig"},  # 新晋势力
            {"id": 9870, "name": "Borussia Monchengladbach"},
            {"id": 8021, "name": "Union Berlin"},  # 新晋势力
        ],
    },
    # 意甲 Serie A (55)
    55: {
        "name": "Serie A",
        "teams": [
            {"id": 9857, "name": "Inter Milan"},  # 传统豪门
            {"id": 8628, "name": "AC Milan"},  # 传统豪门
            {"id": 8636, "name": "Juventus"},  # 传统豪门
            {"id": 4023, "name": "AS Roma"},  # 传统豪门
            {"id": 4031, "name": "Lazio"},  # 传统劲旅
            {"id": 8524, "name": "Napoli"},  # 传统豪门
            {"id": 4024, "name": "Atalanta"},  # 新晋势力
            {"id": 8600, "name": "Fiorentina"},  # 传统劲旅
        ],
    },
    # 法甲 Ligue 1 (53)
    53: {
        "name": "Ligue 1",
        "teams": [
            {"id": 9825, "name": "PSG"},  # 传统豪门
            {"id": 4199, "name": "Marseille"},  # 传统豪门
            {"id": 4019, "name": "Lyon"},  # 传统豪门
            {"id": 4504, "name": "Monaco"},  # 传统豪门
            {"id": 4475, "name": "Lille"},  # 传统劲旅
            {"id": 4521, "name": "Nice"},  # 传统劲旅
            {"id": 5061, "name": "Rennes"},  # 新晋势力
            {"id": 5035, "name": "Lens"},  # 新晋势力
        ],
    },
}


# 目标赛季配置
TARGET_SEASONS = ["2223", "2324"]  # 22/23, 23/24


@dataclass
class DiscoveryStats:
    """发现统计"""

    total_teams_queried: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    matches_discovered: int = 0
    unique_match_ids: int = 0
    leagues_covered: set[int] = field(default_factory=set)
    seasons_covered: set[str] = field(default_factory=set)
    validation_rejected: int = 0
    start_time: float = field(default_factory=time.time)

    def get_elapsed(self) -> float:
        return time.time() - self.start_time

    def get_rate(self) -> float:
        elapsed = self.get_elapsed()
        if elapsed > 0:
            return self.successful_queries / elapsed * 60
        return 0


class FotMobHistoricalIDScanner:
    """
    V36.0 纯净破冰 - FotMob 历史赛季 ID 挖掘器

    核心特性:
    1. 【球队路径】: 通过 /teams 端点绕过 /leagues 限制
    2. 【深度反爬】: UA 轮换 + 随机延迟 + 自然模拟
    3. 【零容忍校验】: 严格验证返回数据完整性
    4. 【纯净架构】: 单一数据源，无第三方依赖
    """

    def __init__(self, concurrency: int = 2):
        """
        初始化挖掘器

        Args:
            concurrency: 并发度 (默认 2，保持低调)
        """
        self.concurrency = concurrency
        self.session: aiohttp.ClientSession | None = None
        self.stats = DiscoveryStats()

        # 按联赛-赛季组织发现的比赛
        self.discovered_matches: dict[tuple[int, str], list[dict]] = defaultdict(list)

        # 数据指纹日志
        self.fingerprint_log = Path("data/logs/v36_discovery_fingerprints.log")
        self.fingerprint_log.parent.mkdir(parents=True, exist_ok=True)

    def _get_random_headers(self) -> dict[str, str]:
        """生成随机请求头 (V35.2 继承)"""
        return {
            "User-Agent": random.choice(UA_POOL),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": random.choice(LANGUAGE_POOL),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

    def validate_payload(self, data: dict, team_id: int) -> tuple[bool, str]:
        """
        V36.0 零容忍数据校验

        规则:
        1. 必须包含 fixtures.allMatches 数组
        2. 每场比赛必须有 id 字段 (Match ID)
        3. 每场比赛必须有 leagueId 字段 (用于过滤)
        4. 每场比赛必须有 status.finished 或 status 字段

        Args:
            data: API 返回的 JSON 数据
            team_id: 球队 ID (用于日志)

        Returns:
            (is_valid, reason): 是否通过校验及原因
        """
        # 检查 1: fixtures 结构
        if "fixtures" not in data:
            return False, "Missing 'fixtures' field"

        fixtures = data["fixtures"]

        if not isinstance(fixtures, dict):
            return False, "Invalid 'fixtures' format (not a dict)"

        # 检查 2: allMatches 数组
        if "allMatches" not in fixtures:
            return False, "Missing 'allMatches' field"

        all_matches = fixtures["allMatches"]

        if not isinstance(all_matches, list):
            return False, "Invalid 'allMatches' format (not a list)"

        # 检查 3: 至少有一些比赛
        if len(all_matches) == 0:
            return False, "Empty 'allMatches' array (0 matches)"

        # 检查 4: 抽样验证比赛数据完整性
        sample_size = min(10, len(all_matches))
        for i, match in enumerate(all_matches[:sample_size]):
            if not isinstance(match, dict):
                return False, f"Match at index {i} is not a dict"

            # 必须有 id
            if "id" not in match:
                return False, f"Match at index {i} missing 'id' field"

            # 必须有 leagueId
            if "leagueId" not in match:
                return False, f"Match at index {i} missing 'leagueId' field"

            # 检查 status
            if "status" not in match:
                return False, f"Match at index {i} missing 'status' field"

        return True, f"OK ({len(all_matches)} matches validated)"

    def _log_discovery_fingerprint(
        self, team_id: int, team_name: str, match_count: int, seasons_found: list[str]
    ):
        """记录发现指纹"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "team_id": team_id,
            "team_name": team_name,
            "matches_total": match_count,
            "seasons_discovered": seasons_found,
        }

        with open(self.fingerprint_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    async def fetch_team_matches(
        self, team_id: int, team_name: str, max_retries: int = 3
    ) -> list[dict] | None:
        """
        获取球队历史赛程 (带重试机制)

        Args:
            team_id: 球队 ID
            team_name: 球队名称
            max_retries: 最大重试次数

        Returns:
            比赛列表或 None
        """
        url = f"https://www.fotmob.com/api/teams?id={team_id}&tab=matches"

        for attempt in range(max_retries):
            try:
                # V36.0: 随机延迟 (模拟人类浏览)
                if attempt > 0:
                    # 指数退避 + 随机抖动
                    base_delay = 2.0 * (2**attempt)
                    delay = base_delay + random.uniform(0.5, 2.0)
                    logger.info(
                        f"⏳ 重试 {attempt + 1}/{max_retries}: Team {team_name} ({team_id}), 延迟 {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    # 首次请求: 自然随机延迟 (1-3 秒)
                    await asyncio.sleep(random.uniform(1.0, 3.0))

                # V36.0: 随机 UA
                headers = self._get_random_headers()

                async with self.session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status}: Team {team_name} ({team_id})")
                        continue

                    data = await response.json()

                    # V36.0: 零容忍校验
                    is_valid, reason = self.validate_payload(data, team_id)
                    if not is_valid:
                        logger.error(f"🚫 校验失败: Team {team_name} ({team_id}) - {reason}")
                        self.stats.validation_rejected += 1
                        return None

                    # 提取比赛列表
                    all_matches = data["fixtures"]["allMatches"]
                    self.stats.successful_queries += 1

                    logger.info(
                        f"✅ 成功: Team {team_name} ({team_id}) - {len(all_matches)} 场比赛"
                    )

                    return all_matches

            except TimeoutError:
                logger.warning(
                    f"⏰ 超时: Team {team_name} ({team_id}) (尝试 {attempt + 1}/{max_retries})"
                )
            except aiohttp.ClientError as e:
                logger.warning(f"🌐 网络错误: Team {team_name} ({team_id}) - {e}")
            except Exception as e:
                logger.exception(f"❌ 未知错误: Team {team_name} ({team_id}) - {e}")

        self.stats.failed_queries += 1
        logger.error(f"❌ 达到最大重试次数: Team {team_name} ({team_id})")
        return None

    def extract_target_matches(
        self, all_matches: list[dict], target_league_id: int, target_seasons: list[str]
    ) -> list[dict]:
        """
        从球队赛程中提取目标联赛和赛季的比赛

        Args:
            all_matches: 所有比赛列表
            target_league_id: 目标联赛 ID
            target_seasons: 目标赛季列表 (如 ['2223', '2324'])

        Returns:
            过滤后的比赛列表
        """
        extracted = []

        for match in all_matches:
            # 提取联赛 ID
            league_id = match.get("leagueId")
            if league_id != target_league_id:
                continue

            # 提取赛季
            season = match.get("season")
            if season not in target_seasons:
                continue

            # 提取核心字段
            match_id = match.get("id")
            if not match_id:
                continue

            # 构建精简的比赛信息
            extracted.append(
                {
                    "match_id": match_id,
                    "league_id": league_id,
                    "season": season,
                    "home_team": match.get("home", {}).get("name", "Unknown"),
                    "away_team": match.get("away", {}).get("name", "Unknown"),
                    "status": match.get("status", {}),
                    "utc_time": match.get("time", {}).get("utcTime", ""),
                    "home_score": match.get("status", {}).get("scoreStr", ""),
                }
            )

        return extracted

    async def discover_league_season(
        self, league_id: int, season: str, seed_teams: list[dict]
    ) -> list[dict]:
        """
        发现指定联赛-赛季的所有比赛 ID

        Args:
            league_id: 联赛 ID
            season: 赛季代码 (如 '2223')
            seed_teams: 种子球队列表

        Returns:
            唯一比赛列表
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"🔍 开始挖掘: League {league_id} - Season {season}")
        logger.info(f"{'=' * 70}")

        all_discovered = []

        for i, team in enumerate(seed_teams, 1):
            team_id = team["id"]
            team_name = team["name"]

            logger.info(f"\n[{i}/{len(seed_teams)}] 查询球队: {team_name} ({team_id})")

            # 获取球队赛程
            matches = await self.fetch_team_matches(team_id, team_name)
            if not matches:
                continue

            # 提取目标联赛-赛季的比赛
            target_matches = self.extract_target_matches(matches, league_id, [season])

            if target_matches:
                logger.info(f"  → 发现 {len(target_matches)} 场目标比赛")
                all_discovered.extend(target_matches)

            # 记录指纹
            seasons_found = list({m.get("season") for m in matches})
            self._log_discovery_fingerprint(team_id, team_name, len(matches), seasons_found)

            # 短暂休眠，避免过于频繁
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # 去重
        unique_ids = set()
        unique_matches = []
        for match in all_discovered:
            if match["match_id"] not in unique_ids:
                unique_ids.add(match["match_id"])
                unique_matches.append(match)

        logger.info(f"\n✅ League {league_id} - Season {season} 挖掘完成:")
        logger.info(f"   原始发现: {len(all_discovered)} 场")
        logger.info(f"   去重后: {len(unique_matches)} 场")

        return unique_matches

    async def discover_all_target_seasons(
        self, league_ids: list[int] | None = None, seasons: list[str] | None = None
    ) -> dict[tuple[int, str], list[dict]]:
        """
        发现所有目标联赛-赛季的比赛

        Args:
            league_ids: 联赛 ID 列表 (默认五大联赛)
            seasons: 赛季列表 (默认 2223, 2324)

        Returns:
            {(league_id, season): [matches]} 字典
        """
        if league_ids is None:
            league_ids = list(SEED_TEAMS_BY_LEAGUE.keys())

        if seasons is None:
            seasons = TARGET_SEASONS

        results = {}

        for league_id in league_ids:
            league_info = SEED_TEAMS_BY_LEAGUE[league_id]
            seed_teams = league_info["teams"]

            for season in seasons:
                matches = await self.discover_league_season(league_id, season, seed_teams)

                key = (league_id, season)
                results[key] = matches

                # 更新统计
                self.stats.leagues_covered.add(league_id)
                self.stats.seasons_covered.add(season)
                self.stats.matches_discovered += len(matches)

                # 保存到实例变量
                self.discovered_matches[key] = matches

        return results

    def save_manifest(self, output_dir: Path | None = None):
        """
        保存发现结果到 manifest 文件

        Args:
            output_dir: 输出目录 (默认 data/production)
        """
        if output_dir is None:
            output_dir = Path("data/production")

        output_dir.mkdir(parents=True, exist_ok=True)

        for (league_id, season), matches in self.discovered_matches.items():
            if not matches:
                continue

            # 构建文件名
            filename = f"v36_discovered_{league_id}_{season}.csv"
            filepath = output_dir / filename

            # 写入 CSV
            import csv

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                if matches:
                    writer = csv.DictWriter(f, fieldnames=matches[0].keys())
                    writer.writeheader()
                    writer.writerows(matches)

            logger.info(f"💾 保存 manifest: {filepath} ({len(matches)} 场)")

    def print_summary(self):
        """打印发现摘要"""
        self.stats.get_elapsed()


        # 按联赛-赛季分组统计
        for (league_id, _season), _matches in sorted(self.discovered_matches.items()):
            SEED_TEAMS_BY_LEAGUE.get(league_id, {}).get("name", f"League {league_id}")


    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=3)  # 低并发度
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()


# ============================================================
# V36.0 主程序
# ============================================================


async def main():
    """主函数"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


    # 目标配置
    target_leagues = [47, 87, 54, 55, 53]  # 五大联赛
    target_seasons = ["2223", "2324"]  # 22/23, 23/24

    async with FotMobHistoricalIDScanner(concurrency=2) as scanner:
        # 执行发现
        await scanner.discover_all_target_seasons(
            league_ids=target_leagues, seasons=target_seasons
        )

        # 保存 manifest
        scanner.save_manifest()

        # 打印摘要
        scanner.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
