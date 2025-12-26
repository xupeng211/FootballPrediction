#!/usr/bin/env python3
"""
V50.0 自治型赛季发现器 (Autonomous Season Discoverer)
====================================================
核心功能：
1. 废弃硬编码的 seasonId，通过 API 自动嗅探联赛赛季
2. 支持过去 5 年的历史赛季回溯
3. 处理 FotMob 内部的 5 位数整型季标映射
4. 智能缓存机制，减少 API 调用

架构原则：
- 单一职责：仅负责赛季发现和映射
- 无状态设计：所有配置通过参数传入
- 容错优先：API 失败时返回可用数据
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


@dataclass
class SeasonInfo:
    """赛季信息数据类"""
    season_id: int                    # FotMob 内部赛季 ID (如 23032)
    season_name: str                  # 显示名称 (如 "24/25")
    season_code: str                  # API 代码 (如 "2425")
    is_current: bool = False          # 是否为当前赛季
    start_year: int = 0               # 赛季开始年份
    end_year: int = 0                 # 赛季结束年份


@dataclass
class LeagueSeasonManifest:
    """联赛赛季清单"""
    league_id: int
    league_name: str
    seasons: list[SeasonInfo] = field(default_factory=list)

    def get_season_by_code(self, code: str) -> SeasonInfo | None:
        """通过赛季代码获取赛季信息"""
        for season in self.seasons:
            if season.season_code == code:
                return season
        return None

    def get_current_season(self) -> SeasonInfo | None:
        """获取当前赛季"""
        for season in self.seasons:
            if season.is_current:
                return season
        return None


class AutonomousSeasonDiscoverer:
    """
    自治型赛季发现器
    
    核心功能：
    1. 从 FotMob API 自动发现联赛的所有可用赛季
    2. 生成过去 5 年的赛季映射表
    3. 智能缓存和容错处理
    """

    # V50.0: 拟人化反爬盔甲 - UA 池
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    # 赛季代码映射规则 (FotMob API 格式)
    SEASON_CODE_PATTERNS = {
        # 标准格式: 2425 -> "24/25"
        "standard": lambda year: f"{year[-2:]}/{str(int(year[-2:]) + 1).zfill(2)}",
        # 早期格式: 2021 -> "20/21"
        "early": lambda year: f"{year[:2]}{year[-2:]}/{str(int(year[-2:]) + 1).zfill(2)}",
    }

    def __init__(
        self,
        base_url: str = "https://www.fotmob.com/api",
        cache_ttl: int = 86400,  # 24 小时缓存
        request_timeout: int = 30,
        retry_count: int = 3,
        backoff_factor: float = 0.5
    ):
        """
        初始化赛季发现器
        
        Args:
            base_url: FotMob API 基础 URL
            cache_ttl: 缓存生存时间（秒）
            request_timeout: 请求超时时间
            retry_count: 重试次数
            backoff_factor: 退避因子
        """
        self.base_url = base_url
        self.cache_ttl = cache_ttl
        self.request_timeout = request_timeout
        self.retry_count = retry_count
        self.backoff_factor = backoff_factor

        # 缓存存储 {league_id: (timestamp, LeagueSeasonManifest)}
        self._cache: dict[int, tuple[float, LeagueSeasonManifest]] = {}

        # 会话管理
        self.session = requests.Session()
        self._refresh_headers()

        logger.info("🔍 V50.0 自治型赛季发现器已初始化")

    def _refresh_headers(self) -> None:
        """刷新请求头（隐身模式）"""
        import random
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,en-GB;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Referer': 'https://www.fotmob.com/',
        })

    def _make_request(self, url: str) -> dict | None:
        """
        发起 HTTP 请求（带重试机制）
        
        Args:
            url: 请求 URL
            
        Returns:
            响应 JSON 数据，失败返回 None
        """
        for attempt in range(self.retry_count):
            try:
                # 随机 Jitter 防止被检测
                import random
                jitter = random.uniform(0.1, 0.5)
                time.sleep(jitter)

                response = self.session.get(
                    url,
                    timeout=self.request_timeout
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"API 返回 404: {url}")
                    return None
                else:
                    logger.warning(
                        f"请求失败 (尝试 {attempt + 1}/{self.retry_count}): "
                        f"状态码 {response.status_code}"
                    )

            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.retry_count}): {url}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求异常 (尝试 {attempt + 1}/{self.retry_count}): {e}")

            # 指数退避
            if attempt < self.retry_count - 1:
                sleep_time = self.backoff_factor * (2 ** attempt)
                time.sleep(sleep_time)

        logger.error(f"请求最终失败: {url}")
        return None

    def discover_league_seasons(
        self,
        league_id: int,
        league_name: str = ""
    ) -> LeagueSeasonManifest:
        """
        发现联赛的所有可用赛季
        
        Args:
            league_id: FotMob 联赛 ID
            league_name: 联赛名称（可选）
            
        Returns:
            LeagueSeasonManifest 对象
        """
        # 检查缓存
        cached = self._get_from_cache(league_id)
        if cached:
            logger.debug(f"从缓存获取联赛 {league_id} 的赛季信息")
            return cached

        # 从 API 获取
        url = f"{self.base_url}/leagues?id={league_id}"
        data = self._make_request(url)

        if not data:
            logger.warning(f"无法获取联赛 {league_id} 的信息，返回空清单")
            return LeagueSeasonManifest(league_id=league_id, league_name=league_name)

        # 解析赛季信息
        manifest = self._parse_seasons_data(data, league_id, league_name)

        # 缓存结果
        self._save_to_cache(league_id, manifest)

        logger.info(
            f"✓ 发现联赛 {league_id} ({manifest.league_name}) "
            f"共 {len(manifest.seasons)} 个赛季"
        )

        return manifest

    def _parse_seasons_data(
        self,
        data: dict,
        league_id: int,
        league_name: str
    ) -> LeagueSeasonManifest:
        """
        解析 API 响应中的赛季数据
        
        Args:
            data: FotMob API 响应
            league_id: 联赛 ID
            league_name: 联赛名称
            
        Returns:
            LeagueSeasonManifest 对象
        """
        seasons = []

        # 提取联赛名称
        if not league_name:
            league_name = data.get('name', f"League_{league_id}")

        # 解析赛季列表
        # FotMob API 格式: seasons.availableSeasons[]
        all_leagues_data = data.get('allLeagues', [])
        if not all_leagues_data:
            logger.warning(f"联赛 {league_id} 缺少 allLeagues 数据")
            return LeagueSeasonManifest(league_id=league_id, league_name=league_name)

        # 找到当前联赛的数据
        current_league = None
        for league_data in all_leagues_data:
            if league_data.get('id') == league_id:
                current_league = league_data
                break

        if not current_league:
            logger.warning(f"在 allLeagues 中未找到联赛 {league_id}")
            return LeagueSeasonManifest(league_id=league_id, league_name=league_name)

        # 解析赛季
        raw_seasons = current_league.get('seasons', [])
        current_season_id = current_league.get('currentSeasonId')

        for season_data in raw_seasons:
            season_id = season_data.get('id')
            season_name = season_data.get('name', '')

            if not season_id or not season_name:
                continue

            # 解析赛季代码
            # "24/25" -> "2425"
            # "2021" -> "2021"
            season_code = self._extract_season_code(season_name)

            # 解析年份
            years = self._extract_years(season_name)

            season_info = SeasonInfo(
                season_id=season_id,
                season_name=season_name,
                season_code=season_code,
                is_current=(season_id == current_season_id),
                start_year=years[0] if years else 0,
                end_year=years[1] if years else 0
            )
            seasons.append(season_info)

        # 按年份排序（新到旧）
        seasons.sort(key=lambda s: (s.start_year, s.end_year), reverse=True)

        return LeagueSeasonManifest(
            league_id=league_id,
            league_name=league_name,
            seasons=seasons
        )

    def _extract_season_code(self, season_name: str) -> str:
        """
        从赛季名称提取 API 代码
        
        Args:
            season_name: 赛季名称 (如 "24/25", "2021")
            
        Returns:
            赛季代码 (如 "2425", "2021")
        """
        # 移除空格
        season_name = season_name.replace(' ', '')

        # 检查是否为标准格式 "24/25"
        if '/' in season_name:
            parts = season_name.split('/')
            if len(parts) == 2:
                # "24/25" -> "2425"
                return parts[0] + parts[1]

        # 检查是否为早期格式 "2021"
        if season_name.isdigit() and len(season_name) == 4:
            return season_name

        # 回退：直接返回原字符串
        return season_name

    def _extract_years(self, season_name: str) -> tuple[int, int]:
        """
        从赛季名称提取起止年份

        Args:
            season_name: 赛季名称 (如 "24/25", "2021")

        Returns:
            (start_year, end_year) 元组
        """
        import re

        # 移除空格
        season_name = season_name.replace(' ', '')

        # 检查格式 "24/25"
        if '/' in season_name:
            parts = season_name.split('/')
            if len(parts) == 2:
                start = int(parts[0])
                end = int(parts[1])
                # 处理跨世纪情况
                base_year = 2000 if start < 50 else 1900
                # 当 end < start 时，表示跨世纪（如 99/00 = 1999/2000）
                if end < start:
                    end += 100
                return (base_year + start, base_year + end)

        # 检查格式 "2021"
        if season_name.isdigit() and len(season_name) == 4:
            year = int(season_name)
            return (year, year + 1)

        # 使用正则提取数字
        numbers = re.findall(r'\d+', season_name)
        if len(numbers) >= 2:
            return (int(numbers[0]), int(numbers[1]))
        elif len(numbers) == 1:
            year = int(numbers[0])
            return (year, year + 1)

        return (0, 0)

    def get_historical_seasons(
        self,
        league_id: int,
        league_name: str = "",
        years_back: int = 5
    ) -> list[SeasonInfo]:
        """
        获取过去 N 年的赛季列表
        
        Args:
            league_id: 联赛 ID
            league_name: 联赛名称
            years_back: 回溯年数
            
        Returns:
            赛季信息列表
        """
        manifest = self.discover_league_seasons(league_id, league_name)

        current_year = datetime.now().year
        cutoff_year = current_year - years_back

        # 筛选最近 N 年的赛季
        historical = [
            s for s in manifest.seasons
            if s.start_year >= cutoff_year
        ]

        logger.info(
            f"✓ 联赛 {league_id} 过去 {years_back} 年 "
            f"共 {len(historical)} 个赛季"
        )

        return historical

    def _get_from_cache(self, league_id: int) -> LeagueSeasonManifest | None:
        """从缓存获取数据"""
        if league_id in self._cache:
            timestamp, manifest = self._cache[league_id]
            age = time.time() - timestamp
            if age < self.cache_ttl:
                return manifest
            else:
                # 过期，删除缓存
                del self._cache[league_id]
        return None

    def _save_to_cache(self, league_id: int, manifest: LeagueSeasonManifest) -> None:
        """保存数据到缓存"""
        self._cache[league_id] = (time.time(), manifest)

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("缓存已清空")

    def close(self) -> None:
        """关闭会话"""
        self.session.close()
        logger.info("赛季发现器会话已关闭")


# 便捷函数
def discover_seasons_for_leagues(
    league_ids: list[int],
    league_names: dict[int, str] = None,
    years_back: int = 5
) -> dict[int, list[SeasonInfo]]:
    """
    批量发现多个联赛的赛季
    
    Args:
        league_ids: 联赛 ID 列表
        league_names: 联赛名称映射 {league_id: name}
        years_back: 回溯年数
        
    Returns:
        {league_id: [SeasonInfo]} 映射
    """
    if league_names is None:
        league_names = {}

    discoverer = AutonomousSeasonDiscoverer()
    results = {}

    try:
        for league_id in league_ids:
            league_name = league_names.get(league_id, "")
            seasons = discoverer.get_historical_seasons(
                league_id, league_name, years_back
            )
            results[league_id] = seasons
    finally:
        discoverer.close()

    return results


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试单个联赛
    discoverer = AutonomousSeasonDiscoverer()

    # 测试英超
    print("\n" + "=" * 60)
    print("测试：英超联赛 (ID=47)")
    print("=" * 60)

    epl_manifest = discoverer.discover_league_seasons(47, "Premier League")

    print(f"\n发现 {len(epl_manifest.seasons)} 个赛季:")
    for season in epl_manifest.seasons:
        current = " [当前]" if season.is_current else ""
        print(f"  - {season.season_name} (ID: {season.season_id}, "
              f"代码: {season.season_code}){current}")

    print(f"\n当前赛季: {epl_manifest.get_current_season().season_name}")

    # 测试过去 5 年
    print("\n" + "-" * 60)
    print("过去 5 年的赛季:")
    print("-" * 60)

    historical = discoverer.get_historical_seasons(47, "Premier League", 5)
    for season in historical:
        print(f"  - {season.season_name} ({season.start_year}/{season.end_year})")

    discoverer.close()
    print("\n✅ 测试完成!")
