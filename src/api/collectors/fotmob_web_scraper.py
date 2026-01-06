#!/usr/bin/env python3
"""
V19.4 FotMob 网页抓取器 - 绕过 API 限制

功能:
1. 直接从 FotMob 网页抓取比赛数据
2. 解析 HTML 提取 Match ID 和比赛信息
3. 作为 API 失效时的备用方案

作者: V19.4 数据采集专家
日期: 2025-12-23
"""

from dataclasses import dataclass
import json
import logging
import time

try:
    from bs4 import BeautifulSoup
    import requests

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

logger = logging.getLogger(__name__)


@dataclass
class ScrapedMatch:
    """抓取的比赛数据"""

    match_id: str
    home_team: str
    away_team: str
    league_id: int
    league_name: str
    match_time: str
    status: str


class FotMobWebScraper:
    """
    FotMob 网页抓取器

    当官方 API 失效时，直接从网页获取数据
    """

    def __init__(self):
        self.base_url = "https://www.fotmob.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # 联赛映射 (使用 URL 简化名称)
        self.league_urls = {
            47: "premier-league",  # 英超
            48: "championship",  # 英冠
            55: "serie-a",  # 意甲
            56: "serie-b",  # 意乙
            87: "la-liga",  # 西甲
            94: "bundesliga",  # 德甲
        }

        logger.info("FotMob 网页抓取器初始化完成")

    def scrape_league_fixtures(self, league_id: int, date_str: str = None) -> list[ScrapedMatch]:
        """
        抓取指定联赛的 fixtures

        Args:
            league_id: 联赛 ID
            date_str: 日期字符串 (YYYYMMDD)，可选

        Returns:
            List[ScrapedMatch]: 抓取的比赛列表
        """
        if not HAS_DEPS:
            logger.error("缺少依赖: 请安装 beautifulsoup4")
            logger.error("  pip install beautifulsoup4 requests")
            return []

        if league_id not in self.league_urls:
            logger.warning(f"不支持的联赛 ID: {league_id}")
            return []

        league_url_name = self.league_urls[league_id]
        # FotMob URL 格式: /leagues/{id}/overview/{name}
        url = f"{self.base_url}/leagues/{league_id}/overview/{league_url_name}"

        logger.info(f"抓取 URL: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # 解析 HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # FotMob 将数据存储在 __NEXT_DATA__ script 标签中
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})

            if not script_tag:
                logger.warning("未找到 __NEXT_DATA__ 标签")
                return []

            # 解析 JSON 数据
            json_text = script_tag.string.strip()
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError:
                logger.error("无法解析 JSON 数据")
                return []

            # 提取比赛数据
            matches = self._extract_matches_from_data(data, league_id)

            logger.info(f"✅ 成功抓取 {len(matches)} 场比赛")

            return matches

        except requests.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"抓取失败: {e}")
            return []

    def _extract_matches_from_data(self, data: dict, league_id: int) -> list[ScrapedMatch]:
        """从 JSON 数据中提取比赛信息"""
        matches = []

        try:
            # 导航到 pageProps.fixtures.allMatches
            page_props = data.get("props", {}).get("pageProps", {})
            fixtures = page_props.get("fixtures", {})
            matches_data = fixtures.get("allMatches", [])

            if not matches_data:
                logger.warning("未在数据中找到 allMatches 数组")
                return matches

            logger.info(f"找到 {len(matches_data)} 场比赛，开始解析...")

            # 解析每场比赛
            for match in matches_data:
                if not isinstance(match, dict):
                    continue

                # 提取比赛信息
                match_id = str(match.get("id", ""))
                if not match_id:
                    continue

                home = match.get("home", {})
                away = match.get("away", {})
                status = match.get("status", {})

                # 获取比赛时间
                utc_time = status.get("utcTime", "")
                start_time = status.get("startTime", {})
                uts_time = start_time.get("uts", "") if isinstance(start_time, dict) else ""

                # 获取比赛状态
                stage = (
                    status.get("stage", {}).get("id", "")
                    if isinstance(status.get("stage"), dict)
                    else status.get("stage", "")
                )
                stage_str = str(stage).lower() if stage else ""

                # 只返回未完成的比赛（未来和进行中的）
                # 跳过已完成的比赛（我们只关心未来的）
                if stage_str in ["finished", "ft", "played", "postponed"]:
                    continue

                matches.append(
                    ScrapedMatch(
                        match_id=match_id,
                        home_team=home.get("name", "Unknown"),
                        away_team=away.get("name", "Unknown"),
                        league_id=league_id,
                        league_name=self._get_league_name(league_id),
                        match_time=utc_time or uts_time,
                        status=stage_str,
                    )
                )

        except Exception as e:
            logger.error(f"解析比赛数据失败: {e}")

        return matches

    def _get_league_name(self, league_id: int) -> str:
        """获取联赛名称"""
        names = {
            47: "Premier League",
            48: "Championship",
            55: "Serie A",
            56: "Serie B",
            87: "La Liga",
            94: "Bundesliga",
        }
        return names.get(league_id, f"League {league_id}")

    def scrape_multiple_leagues(self, league_ids: list[int], max_matches: int = 50) -> list[ScrapedMatch]:
        """
        抓取多个联赛的比赛

        Args:
            league_ids: 联赛 ID 列表
            max_matches: 最大返回比赛数

        Returns:
            List[ScrapedMatch]: 所有抓取的比赛
        """
        all_matches = []

        for league_id in league_ids:
            logger.info(f"抓取联赛 {league_id}...")
            matches = self.scrape_league_fixtures(league_id)
            all_matches.extend(matches)

            # 避免请求过于频繁
            time.sleep(2)

            if len(all_matches) >= max_matches:
                break

        logger.info(f"总计抓取 {len(all_matches)} 场比赛")
        return all_matches


# ============================================
# 测试脚本
# ============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=" * 70)
    print("FotMob 网页抓取器测试")
    print("=" * 70)

    scraper = FotMobWebScraper()

    # 测试英超抓取
    print("\n测试抓取英超 fixtures...")
    matches = scraper.scrape_league_fixtures(47)

    print(f"\n抓取到 {len(matches)} 场比赛:")
    print("-" * 70)

    for i, match in enumerate(matches[:10], 1):
        print(f"{i}. {match.home_team} vs {match.away_team}")
        print(f"   Match ID: {match.match_id}")
        print(f"   Time: {match.match_time}")
        print(f"   Status: {match.status}")
        print()

    if len(matches) > 10:
        print(f"... 还有 {len(matches) - 10} 场比赛")

    print("=" * 70)
