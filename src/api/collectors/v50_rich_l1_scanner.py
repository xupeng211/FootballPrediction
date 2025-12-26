#!/usr/bin/env python3
"""
V50.0 Rich L1 多维扫描引擎 (Rich L1 Multi-Dimensional Scanner)
================================================================
核心功能：
1. 扫描比赛 ID 的同时，带回比分、状态、UTC 时间
2. 实现全自动赛季路由，无需硬编码
3. 维持拟人化反爬盔甲（UA 池、随机 Jitter）
4. 智能去重和断点续传

产出结构 (Rich L1 Tuple):
{
    'match_id': int,
    'home_score': Optional[int],
    'away_score': Optional[int],
    'status': str,  # 'finished' | 'ongoing' | 'scheduled'
    'match_time_utc': str,
    'league_id': int,
    'season_id': int,
    'season_name': str,
    'home_team': str,
    'away_team': str,
    'home_team_id': int,
    'away_team_id': int,
}

架构原则：
- 身首合一：比分和状态第一时间进入数据库
- 容错优先：API 失败时返回部分数据
- 性能优化：并发扫描 + 智能缓存
"""

import asyncio
import json
import logging
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import aiohttp

from .v50_autonomous_season_discoverer import AutonomousSeasonDiscoverer, SeasonInfo

logger = logging.getLogger(__name__)


@dataclass
class RichL1Match:
    """Rich L1 比赛数据结构"""
    match_id: int
    league_id: int
    season_id: int
    season_name: str

    # 基础信息
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int

    # 状态和时间
    status: str  # 'finished' | 'ongoing' | 'scheduled'
    match_time_utc: str

    # 比分（可能为 None）
    home_score: int | None = None
    away_score: int | None = None

    # 元数据
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    def is_finished(self) -> bool:
        """是否已完赛"""
        return self.status == 'finished'

    def has_score(self) -> bool:
        """是否有比分数据"""
        return self.home_score is not None and self.away_score is not None

    def get_result_code(self) -> str | None:
        """获取结果代码 (H/D/A)"""
        if not self.has_score():
            return None
        if self.home_score > self.away_score:
            return 'H'
        elif self.home_score < self.away_score:
            return 'A'
        else:
            return 'D'


@dataclass
class ScanStatistics:
    """扫描统计"""
    total_matches: int = 0
    finished_matches: int = 0
    ongoing_matches: int = 0
    scheduled_matches: int = 0

    # 比分统计
    matches_with_score: int = 0
    matches_without_score: int = 0

    # 按联赛统计
    by_league: dict[str, int] = field(default_factory=dict)

    # 按赛季统计
    by_season: dict[str, int] = field(default_factory=dict)

    # API 请求统计
    api_requests: int = 0
    api_failures: int = 0
    api_successes: int = 0

    def update_with_match(self, match: RichL1Match, league_name: str) -> None:
        """更新统计数据"""
        self.total_matches += 1

        # 状态统计
        if match.is_finished():
            self.finished_matches += 1
        elif match.status == 'scheduled':
            self.scheduled_matches += 1
        else:
            self.ongoing_matches += 1

        # 比分统计
        if match.has_score():
            self.matches_with_score += 1
        else:
            self.matches_without_score += 1

        # 按联赛统计
        if league_name not in self.by_league:
            self.by_league[league_name] = 0
        self.by_league[league_name] += 1

        # 按赛季统计
        if match.season_name not in self.by_season:
            self.by_season[match.season_name] = 0
        self.by_season[match.season_name] += 1

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


class RichL1Scanner:
    """
    Rich L1 多维扫描引擎
    
    核心功能：
    1. 扫描比赛 ID + 比分 + 状态 + UTC 时间
    2. 全自动赛季路由
    3. 拟人化反爬盔甲
    4. 智能去重和断点续传
    """

    # V50.0: 拟人化反爬盔甲
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]

    ACCEPT_LANGUAGES = [
        'en-US,en;q=0.9,en-GB;q=0.8',
        'en-GB,en;q=0.9',
        'fr-FR,fr;q=0.9,en;q=0.8',
        'de-DE,de;q=0.9,en;q=0.8',
    ]

    def __init__(
        self,
        base_url: str = "https://www.fotmob.com/api",
        max_concurrent: int = 5,
        request_timeout: int = 30,
        jitter_range: tuple[float, float] = (0.1, 0.5),
        retry_count: int = 3
    ):
        """
        初始化 Rich L1 扫描器
        
        Args:
            base_url: FotMob API 基础 URL
            max_concurrent: 最大并发数
            request_timeout: 请求超时时间
            jitter_range: 随机 Jitter 范围（秒）
            retry_count: 重试次数
        """
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.request_timeout = request_timeout
        self.jitter_range = jitter_range
        self.retry_count = retry_count

        # 赛季发现器
        self.season_discoverer = AutonomousSeasonDiscoverer()

        # 统计数据
        self.stats = ScanStatistics()

        # 去重集合
        self.seen_match_ids: set[tuple[int, int, str]] = set()  # (match_id, league_id, season)

        # 会话管理
        self.session: aiohttp.ClientSession | None = None

        logger.info("🎯 V50.0 Rich L1 多维扫描引擎已初始化")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        # 关闭会话
        if self.session:
            await self.session.close()

        # 关闭赛季发现器
        self.season_discoverer.close()

    def _get_random_headers(self) -> dict[str, str]:
        """生成随机请求头（隐身模式）"""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': random.choice(self.ACCEPT_LANGUAGES),
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Referer': 'https://www.fotmob.com/',
            'Origin': 'https://www.fotmob.com',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }

    async def _fetch_with_retry(
        self,
        url: str,
        method: str = "GET"
    ) -> dict | None:
        """
        带重试机制的 HTTP 请求
        
        Args:
            url: 请求 URL
            method: HTTP 方法
            
        Returns:
            响应 JSON 数据，失败返回 None
        """
        for attempt in range(self.retry_count):
            try:
                # 随机 Jitter
                await asyncio.sleep(random.uniform(*self.jitter_range))

                async with self.session.request(
                    method,
                    url,
                    headers=self._get_random_headers()
                ) as response:
                    self.stats.api_requests += 1

                    if response.status == 200:
                        self.stats.api_successes += 1
                        return await response.json()
                    elif response.status == 404:
                        logger.warning(f"API 返回 404: {url}")
                        return None
                    else:
                        logger.warning(
                            f"请求失败 (尝试 {attempt + 1}/{self.retry_count}): "
                            f"状态码 {response.status}"
                        )

            except TimeoutError:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.retry_count}): {url}")
            except Exception as e:
                logger.warning(f"请求异常 (尝试 {attempt + 1}/{self.retry_count}): {e}")

            self.stats.api_failures += 1

            # 指数退避
            if attempt < self.retry_count - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))

        logger.error(f"请求最终失败: {url}")
        return None

    async def fetch_league_matches(
        self,
        league_id: int,
        league_name: str,
        season_info: SeasonInfo
    ) -> list[RichL1Match]:
        """
        获取指定联赛和赛季的所有比赛（Rich L1 数据）
        
        Args:
            league_id: 联赛 ID
            league_name: 联赛名称
            season_info: 赛季信息
            
        Returns:
            Rich L1 比赛列表
        """
        url = f"{self.base_url}/leagues?id={league_id}&season={season_info.season_code}"

        logger.info(
            f"🔍 扫描 {league_name} - {season_info.season_name} "
            f"(赛季代码: {season_info.season_code})"
        )

        data = await self._fetch_with_retry(url)
        if not data:
            logger.warning(f"无法获取联赛 {league_id} 赛季 {season_info.season_name} 的数据")
            return []

        # 解析比赛数据
        matches = self._parse_league_matches(
            data, league_id, league_name, season_info
        )

        logger.info(f"✓ {league_name} - {season_info.season_name}: {len(matches)} 场比赛")

        return matches

    def _parse_league_matches(
        self,
        data: dict,
        league_id: int,
        league_name: str,
        season_info: SeasonInfo
    ) -> list[RichL1Match]:
        """
        解析联赛比赛数据（Rich L1）
        
        Args:
            data: FotMob API 响应
            league_id: 联赛 ID
            league_name: 联赛名称
            season_info: 赛季信息
            
        Returns:
            Rich L1 比赛列表
        """
        matches = []

        try:
            # 导航到 matches 数据
            fixtures = data.get('fixtures', {})
            all_matches = fixtures.get('allMatches', [])

            for match_data in all_matches:
                # 提取基础信息
                match_id = match_data.get('id')
                if not match_id:
                    continue

                # 去重检查
                unique_key = (match_id, league_id, season_info.season_name)
                if unique_key in self.seen_match_ids:
                    continue
                self.seen_match_ids.add(unique_key)

                # 提取球队信息
                home_team = match_data.get('home', {})
                away_team = match_data.get('away', {})

                # 提取状态和时间
                status_obj = match_data.get('status', {})
                is_finished = status_obj.get('finished', False)
                is_started = status_obj.get('started', False)

                # 判定状态
                if is_finished:
                    status = 'finished'
                elif is_started:
                    status = 'ongoing'
                else:
                    status = 'scheduled'

                # 提取 UTC 时间
                match_time_utc = status_obj.get('utcTime', '')

                # 提取比分（Rich L1 核心功能）
                home_score = status_obj.get('homeScore')
                away_score = status_obj.get('awayScore')

                # 创建 Rich L1 比赛对象
                rich_match = RichL1Match(
                    match_id=match_id,
                    league_id=league_id,
                    season_id=season_info.season_id,
                    season_name=season_info.season_name,
                    home_team=home_team.get('name', 'Unknown'),
                    away_team=away_team.get('name', 'Unknown'),
                    home_team_id=int(home_team.get('id', 0)),
                    away_team_id=int(away_team.get('id', 0)),
                    status=status,
                    match_time_utc=match_time_utc,
                    home_score=home_score,
                    away_score=away_score,
                )

                matches.append(rich_match)

                # 更新统计
                self.stats.update_with_match(rich_match, league_name)

        except Exception as e:
            logger.error(f"解析比赛数据失败: {e}")

        return matches

    async def scan_league_historical(
        self,
        league_id: int,
        league_name: str = "",
        years_back: int = 5
    ) -> list[RichL1Match]:
        """
        扫描联赛的历史赛季数据
        
        Args:
            league_id: 联赛 ID
            league_name: 联赛名称
            years_back: 回溯年数
            
        Returns:
            Rich L1 比赛列表
        """
        # 获取历史赛季
        seasons = self.season_discoverer.get_historical_seasons(
            league_id, league_name, years_back
        )

        if not seasons:
            logger.warning(f"联赛 {league_id} 没有可用赛季")
            return []

        logger.info(
            f"🏆 开始扫描 {league_name} 过去 {years_back} 年 "
            f"共 {len(seasons)} 个赛季"
        )

        # 并发扫描所有赛季
        tasks = []
        for season in seasons:
            task = self.fetch_league_matches(league_id, league_name, season)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_matches = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"扫描任务失败: {result}")
                continue
            if result:
                all_matches.extend(result)

        logger.info(
            f"✅ {league_name} 扫描完成: {len(all_matches)} 场比赛"
        )

        return all_matches

    async def scan_multiple_leagues(
        self,
        league_configs: list[tuple[int, str]],  # [(league_id, league_name), ...]
        years_back: int = 5
    ) -> list[RichL1Match]:
        """
        扫描多个联赛的历史数据
        
        Args:
            league_configs: 联赛配置列表 [(league_id, league_name), ...]
            years_back: 回溯年数
            
        Returns:
            Rich L1 比赛列表
        """
        logger.info(
            f"🌍 开始全球广域扫描: {len(league_configs)} 个联赛 × 过去 {years_back} 年"
        )

        # 并发扫描所有联赛
        tasks = []
        for league_id, league_name in league_configs:
            task = self.scan_league_historical(league_id, league_name, years_back)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_matches = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"联赛扫描失败: {result}")
                continue
            if result:
                all_matches.extend(result)

        logger.info(f"✅ 全球扫描完成: {len(all_matches)} 场比赛")

        return all_matches

    def get_statistics(self) -> ScanStatistics:
        """获取扫描统计"""
        return self.stats

    def print_summary(self) -> None:
        """打印扫描摘要"""
        print("\n" + "=" * 70)
        print("V50.0 Rich L1 扫描摘要")
        print("=" * 70)

        print("\n📊 总体统计:")
        print(f"   总比赛数: {self.stats.total_matches:,}")
        print(f"   已完成: {self.stats.finished_matches:,}")
        print(f"   进行中: {self.stats.ongoing_matches:,}")
        print(f"   未开始: {self.stats.scheduled_matches:,}")

        print("\n🎯 比分统计 (Rich L1 核心指标):")
        print(f"   带比分: {self.stats.matches_with_score:,}")
        print(f"   缺比分: {self.stats.matches_without_score:,}")
        if self.stats.total_matches > 0:
            score_coverage = (self.stats.matches_with_score / self.stats.total_matches * 100)
            print(f"   覆盖率: {score_coverage:.1f}%")

        print("\n📡 API 统计:")
        print(f"   总请求: {self.stats.api_requests:,}")
        print(f"   成功: {self.stats.api_successes:,}")
        print(f"   失败: {self.stats.api_failures:,}")
        if self.stats.api_requests > 0:
            success_rate = (self.stats.api_successes / self.stats.api_requests * 100)
            print(f"   成功率: {success_rate:.1f}%")

        if self.stats.by_league:
            print("\n🏆 按联赛分布:")
            for league, count in sorted(self.stats.by_league.items()):
                percentage = (count / self.stats.total_matches * 100) if self.stats.total_matches > 0 else 0
                print(f"   {league:20s}: {count:5d} 场 ({percentage:5.1f}%)")

        if self.stats.by_season:
            print("\n📅 按赛季分布:")
            for season, count in sorted(self.stats.by_season.items()):
                percentage = (count / self.stats.total_matches * 100) if self.stats.total_matches > 0 else 0
                print(f"   {season:6s}: {count:5d} 场 ({percentage:5.1f}%)")

        print("=" * 70)

    def save_results(self, output_path: Path) -> None:
        """
        保存扫描结果到文件
        
        Args:
            output_path: 输出文件路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化的格式
        matches_data = [m.to_dict() for m in self.get_all_matches()]

        output_data = {
            'scan_metadata': {
                'scan_version': 'V50.0-Rich-L1',
                'scan_timestamp': datetime.now().isoformat(),
                'total_matches': len(matches_data),
                'finished_matches': self.stats.finished_matches,
                'matches_with_score': self.stats.matches_with_score,
                'score_coverage': (
                    self.stats.matches_with_score / self.stats.total_matches * 100
                    if self.stats.total_matches > 0 else 0
                ),
            },
            'statistics': self.stats.to_dict(),
            'matches': matches_data,
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 扫描结果已保存: {output_path}")
        logger.info(f"   文件大小: {output_path.stat().st_size:,} 字节")

    def get_all_matches(self) -> list[RichL1Match]:
        """
        获取所有扫描到的比赛
        
        Note: 当前版本需要在扫描过程中缓存比赛，
        后续版本可以添加内存存储优化
        """
        # TODO: 添加比赛缓存
        logger.warning("get_all_matches 需要在扫描过程中缓存比赛数据")
        return []


# 便捷函数
async def quick_scan_league(
    league_id: int,
    league_name: str = "",
    years_back: int = 5
) -> list[dict]:
    """
    快速扫描单个联赛
    
    Args:
        league_id: 联赛 ID
        league_name: 联赛名称
        years_back: 回溯年数
        
    Returns:
        比赛数据字典列表
    """
    async with RichL1Scanner() as scanner:
        matches = await scanner.scan_league_historical(
            league_id, league_name, years_back
        )
        scanner.print_summary()
        return [m.to_dict() for m in matches]


async def quick_scan_multiple_leagues(
    league_configs: list[tuple[int, str]],
    years_back: int = 5
) -> list[dict]:
    """
    快速扫描多个联赛
    
    Args:
        league_configs: 联赛配置列表 [(league_id, league_name), ...]
        years_back: 回溯年数
        
    Returns:
        比赛数据字典列表
    """
    async with RichL1Scanner() as scanner:
        matches = await scanner.scan_multiple_leagues(
            league_configs, years_back
        )
        scanner.print_summary()
        return [m.to_dict() for m in matches]


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test():
        """测试函数"""
        # 测试单个联赛
        print("\n" + "=" * 60)
        print("测试：荷甲联赛 (ID=12)")
        print("=" * 60)

        matches = await quick_scan_league(12, "Eredivisie", 3)

        print(f"\n✅ 测试完成! 共 {len(matches)} 场比赛")

    asyncio.run(test())
