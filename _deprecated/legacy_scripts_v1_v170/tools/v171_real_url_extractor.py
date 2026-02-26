#!/usr/bin/env python3
"""
V171.002 Real URL Hash Extractor
=================================

从 OddsPortal 网站抓取真实的 URL hash 值，替换数据库中的假 URL。

使用 crawler_service.py 中的核心逻辑：
- 正则表达式: /[A-Za-z0-9]{8}/
- Playwright DOM 提取

Usage:
    python scripts/ops/v171_real_url_extractor.py --limit 20
"""

import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 添加项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright, Page

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger('V171_URL_Extractor')


@dataclass
class RealMatch:
    """真实比赛数据"""
    home_team: str
    away_team: str
    url_hash: str
    full_url: str
    league: str


class RealUrlExtractor:
    """真实 URL Hash 提取器"""

    # OddsPortal 联赛 URL 模板
    LEAGUE_URLS = {
        'Premier League': 'https://www.oddsportal.com/football/england/premier-league/',
        'La Liga': 'https://www.oddsportal.com/football/spain/laliga/',
        'Bundesliga': 'https://www.oddsportal.com/football/germany/bundesliga/',
        'Serie A': 'https://www.oddsportal.com/football/italy/serie-a/',
        'Ligue 1': 'https://www.oddsportal.com/football/france/ligue-1/',
    }

    # 8 字符 hash 正则表达式 (来自 crawler_service.py)
    HASH_PATTERN = re.compile(r'/([A-Za-z0-9]{8})/?$')

    def __init__(self):
        self.matches: list[RealMatch] = []

    async def extract_from_league(self, page: Page, league: str, url: str) -> list[RealMatch]:
        """从联赛页面提取真实 URL"""
        matches = []

        logger.info(f"🌐 访问: {url}")
        await page.goto(url, timeout=30000, wait_until='networkidle')

        # 等待页面加载
        await page.wait_for_timeout(3000)

        # 使用 crawler_service.py 的核心逻辑提取链接
        links = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    if (href && href.match(/[A-Za-z0-9]{8}\\/?$/)) {
                        results.push({ href: href, text: link.innerText });
                    }
                });

                return results;
            }
        """)

        logger.info(f"   找到 {len(links)} 个带 hash 的链接")

        for link in links:
            href = link.get('href', '')
            text = link.get('text', '')

            # 提取 hash
            match = self.HASH_PATTERN.search(href)
            if match:
                url_hash = match.group(1)

                # 从 URL 或文本解析队名
                teams = self._parse_teams_from_url(href, text)
                if teams:
                    full_url = f"https://www.oddsportal.com{href}" if not href.startswith('http') else href

                    real_match = RealMatch(
                        home_team=teams[0],
                        away_team=teams[1],
                        url_hash=url_hash,
                        full_url=full_url,
                        league=league
                    )
                    matches.append(real_match)

                    logger.info(f"   ✅ {teams[0]} vs {teams[1]} → {url_hash}")

        return matches

    def _parse_teams_from_url(self, url: str, text: str) -> tuple | None:
        """从 URL 解析队名"""
        # URL 格式: /football/england/premier-league/home-team-away-team-HASH/
        # 提取联赛后的部分
        match = re.search(r'/premier-league/([^/]+)/?$', url)
        if not match:
            # 尝试其他联赛
            match = re.search(r'/[a-z-]+/([^/]+)/?$', url)

        if not match:
            return None

        teams_part = match.group(1)

        # 分割并找到 hash
        parts = teams_part.split('-')

        # 找到 hash 位置（8字符，包含大写字母或数字）
        hash_idx = None
        for i, part in enumerate(parts):
            if len(part) == 8 and (any(c.isupper() for c in part) or any(c.isdigit() for c in part)):
                hash_idx = i
                break

        if hash_idx is None or hash_idx < 2:
            return None

        # 提取队名部分
        team_parts = parts[:hash_idx]

        if len(team_parts) < 2:
            return None

        # 简单分割：尝试找到合理的分界点
        # 常见模式: manchester-united-chelsea-ABC12345
        # 需要智能分割

        # 使用已知队名列表辅助分割
        known_teams = [
            'manchester-united', 'manchester-city', 'liverpool', 'chelsea', 'arsenal',
            'tottenham', 'hotspur', 'newcastle', 'united', 'brighton', 'west-ham',
            'wolves', 'wolverhampton', 'aston-villa', 'everton', 'fulham',
            'crystal-palace', 'brentford', 'nottingham-forest', 'bournemouth',
            'southampton', 'leeds', 'leicester', 'city'
        ]

        # 尝试找到最佳分割点
        for i in range(1, len(team_parts)):
            home_parts = team_parts[:i]
            away_parts = team_parts[i:]

            home = ' '.join(p.title() for p in home_parts)
            away = ' '.join(p.title() for p in away_parts)

            # 检查是否合理
            if len(home_parts) >= 1 and len(away_parts) >= 1:
                # 简单验证：队名不要太长
                if len(home) < 30 and len(away) < 30:
                    return (home, away)

        # 默认返回首尾
        if len(team_parts) >= 2:
            return (team_parts[0].title(), ' '.join(p.title() for p in team_parts[1:]))

        return None

    async def run(self, leagues: list[str] = None, limit: int = 20) -> list[RealMatch]:
        """执行 URL 提取"""
        all_matches = []

        if leagues is None:
            leagues = list(self.LEAGUE_URLS.keys())

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for league in leagues:
                if league not in self.LEAGUE_URLS:
                    logger.warning(f"未知联赛: {league}")
                    continue

                url = self.LEAGUE_URLS[league]

                try:
                    matches = await self.extract_from_league(page, league, url)
                    all_matches.extend(matches)

                    if len(all_matches) >= limit:
                        break

                except Exception as e:
                    logger.error(f"提取失败 {league}: {e}")

            await browser.close()

        self.matches = all_matches[:limit]
        return self.matches


async def update_database(matches: list[RealMatch]) -> int:
    """更新数据库中的 URL"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        # 从环境变量获取数据库连接信息
        import os
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'football_db'),
            user=os.getenv('DB_USER', 'football_user'),
            password=os.getenv('DB_PASSWORD', 'your_secure_password_here')
        )

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        updated = 0

        for match in matches:
            # 查找匹配的比赛
            cursor.execute("""
                SELECT match_id FROM matches
                WHERE (home_team ILIKE %s AND away_team ILIKE %s)
                   OR (home_team ILIKE %s AND away_team ILIKE %s)
                LIMIT 1
            """, (f'%{match.home_team}%', f'%{match.away_team}%',
                  f'%{match.away_team}%', f'%{match.home_team}%'))

            row = cursor.fetchone()

            if row:
                match_id = row['match_id']

                # 更新 URL
                cursor.execute("""
                    UPDATE matches
                    SET external_id = %s, updated_at = NOW()
                    WHERE match_id = %s
                """, (match.full_url, match_id))

                logger.info(f"   💾 更新: {match_id} → {match.url_hash}")
                updated += 1

        conn.commit()
        cursor.close()
        conn.close()

        return updated

    except Exception as e:
        logger.error(f"数据库更新失败: {e}")
        return 0


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='V171 真实 URL Hash 提取器')
    parser.add_argument('--limit', type=int, default=20, help='提取数量限制')
    parser.add_argument('--league', type=str, default='Premier League', help='联赛名称')
    parser.add_argument('--update-db', action='store_true', help='更新数据库')
    args = parser.parse_args()

    print("")
    print("═" * 65)
    print("  V171.002 真实 URL Hash 提取器")
    print("═" * 65)
    print("")

    # 提取 URL
    extractor = RealUrlExtractor()
    matches = await extractor.run(
        leagues=[args.league],
        limit=args.limit
    )

    print("")
    print(f"📋 共提取 {len(matches)} 个真实 URL:")
    print("─" * 65)

    for i, m in enumerate(matches, 1):
        print(f"   {i}. {m.home_team} vs {m.away_team}")
        print(f"      Hash: {m.url_hash}")
        print(f"      URL:  {m.full_url}")
        print("")

    # 更新数据库
    if args.update_db and matches:
        print("─" * 65)
        print("💾 更新数据库...")
        updated = await update_database(matches)
        print(f"   更新了 {updated} 条记录")

    print("")
    print("═" * 65)
    print("  提取完成!")
    print("═" * 65)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
