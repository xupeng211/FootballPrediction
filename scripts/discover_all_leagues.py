#!/usr/bin/env python3
"""
FBref 赛事发现者 (League Discovery)
首席数据架构师专用工具

Purpose: 从FBref自动发现所有可用赛事，实现"地毯式覆盖"
目标: 发现并采集FBref上存在的每一场比赛

Strategy:
1. 访问 https://fbref.com/en/comps/ 获取赛事总索引
2. 解析所有表格 (Big 5, Domestic, International, Cups)
3. 提取赛事名称和链接
4. 存入数据库leagues表
"""

import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from bs4 import BeautifulSoup
import requests
from curl_cffi import requests as curl_requests
from sqlalchemy import create_engine, text

# 数据库连接
DB_URL = (
    "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
)
engine = create_engine(DB_URL)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FBrefLeagueDiscovery:
    """FBref赛事发现器"""

    BASE_URL = "https://fbref.com"
    COMP_INDEX_URL = "https://fbref.com/en/comps/"

    def __init__(self):
        self.session = curl_requests.Session(impersonate="chrome")
        self.discovered_leagues = []
        self.existing_leagues = set()

    def load_existing_leagues(self):
        """加载数据库中已存在的联赛"""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT fbref_url, name FROM leagues
                WHERE fbref_url IS NOT NULL
            """
                )
            )
            self.existing_leagues = {row[0] for row in result.fetchall() if row[0]}

        logger.info(f"已加载 {len(self.existing_leagues)} 个已存在联赛")

    def fetch_comp_index_page(self) -> Optional[BeautifulSoup]:
        """获取FBref赛事索引页面"""
        logger.info(f"🔍 访问FBref赛事总索引: {self.COMP_INDEX_URL}")

        try:
            response = self.session.get(self.COMP_INDEX_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            logger.info(f"✅ 成功获取页面，内容长度: {len(response.text):,} 字符")

            return soup

        except Exception as e:
            logger.error(f"❌ 获取页面失败: {e}")
            return None

    def parse_league_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """解析所有联赛表格"""
        logger.info("🏆 开始解析联赛表格...")

        discovered = []

        # 查找所有表格
        tables = soup.find_all("table")

        # 每个表格对应一个分类
        table_categories = [
            "Big 5 European Leagues",
            "Domestic Leagues",
            "International Leagues",
            "Club Cups",
            "Youth Leagues",
            "Other Competitions",
        ]

        for idx, table in enumerate(tables):
            # 获取表格标题
            category = "Unknown"
            try:
                # 查找表格前面的标题
                prev_header = table.find_previous(["h2", "h3", "h4"])
                if prev_header:
                    category = prev_header.get_text(strip=True)
                elif idx < len(table_categories):
                    category = table_categories[idx]
            except:
                pass

            logger.info(f"📊 解析表格 {idx + 1}/{len(tables)}: {category}")

            # 解析表格行
            try:
                rows = table.find_all("tr")[1:]  # 跳过表头

                for row in rows:
                    cells = row.find_all(["td", "th"])

                    if len(cells) < 2:
                        continue

                    # 提取联赛名称和链接
                    link_cell = cells[0]
                    link_tag = link_cell.find("a")

                    if not link_tag or not link_tag.get("href"):
                        continue

                    league_name = link_tag.get_text(strip=True)
                    league_path = link_tag.get("href")

                    # 提取国家/地区 - 尝试多个位置
                    country = ""
                    if len(cells) > 1:
                        # 国家可能在前几列
                        for i in range(1, min(len(cells), 4)):
                            cell_text = cells[i].get_text(strip=True)
                            if cell_text and len(cell_text) > 1 and len(cell_text) < 30:
                                # 过滤掉数字和非国家信息
                                if not cell_text.replace(".", "").isdigit():
                                    country = cell_text
                                    break

                    # 判断级别
                    tier = self._determine_tier(league_name, country)

                    # 使用正确的URL - 导航到当前赛季页面而不是历史页面
                    if "/history/" in league_path:
                        # 从历史页面URL提取comp ID，构建正确的URL
                        # 例如: /en/comps/9/history/Premier-League-Seasons
                        # 提取comp ID (9) 和路径 (Premier-League)
                        match = re.search(
                            r"/comps/(\d+)/history/([^/]+)-Seasons", league_path
                        )
                        if match:
                            comp_id = match.group(1)
                            comp_name = match.group(2)
                            league_path = f"/en/comps/{comp_id}/schedule/{comp_name}-Scores-and-Fixtures"
                    else:
                        # 如果不是历史页面，检查是否需要转换
                        if league_path.endswith("-Stats"):
                            league_path = league_path.replace(
                                "-Stats", "-Scores-and-Fixtures"
                            )

                    # 生成FBref URL
                    fbref_url = urljoin(self.BASE_URL, league_path)

                    # 去重检查
                    if fbref_url in self.existing_leagues:
                        logger.debug(f"⏭️ 跳过已存在联赛: {league_name}")
                        continue

                    # 存储发现结果
                    league_info = {
                        "name": league_name,
                        "country": country,
                        "category": category,
                        "tier": tier,
                        "fbref_url": fbref_url,
                        "fbref_path": league_path,
                    }

                    discovered.append(league_info)
                    self.existing_leagues.add(fbref_url)

            except Exception as e:
                logger.error(f"❌ 解析表格失败: {e}")
                continue

        logger.info(f"✅ 发现 {len(discovered)} 个新联赛")
        return discovered

    def _determine_tier(self, league_name: str, country: str) -> str:
        """判断联赛级别"""
        name_lower = league_name.lower()

        # 一级联赛（顶级联赛）
        if any(
            keyword in name_lower
            for keyword in [
                "premier",
                "la liga",
                "bundesliga",
                "serie a",
                "ligue 1",
                "championship",
                "laLiga",
                "primera division",
                "primeira liga",
                "eredivisie",
                "súperliga",
                "superliga",
            ]
        ):
            return "1st"

        # 二级联赛
        if any(
            keyword in name_lower
            for keyword in [
                "championship",
                "segunda",
                "2.",
                "2nd",
                "tier 2",
                "bundesliga 2",
                "serie b",
                "ligue 2",
            ]
        ):
            return "2nd"

        # 三级联赛
        if any(
            keyword in name_lower
            for keyword in ["3.", "tier 3", "third division", "tercera", "serie c"]
        ):
            return "3rd"

        # 杯赛
        if any(
            keyword in name_lower
            for keyword in ["cup", "fa cup", "copa", "dfb", "coppa", "taça"]
        ):
            return "Cup"

        # 洲际赛事
        if any(
            keyword in name_lower
            for keyword in [
                "champions",
                "europa",
                "conference",
                "copa Libertadores",
                "afc",
                "caf",
                "concacaf",
            ]
        ):
            return "International"

        return "Other"

    def save_to_database(self, leagues: List[Dict]) -> int:
        """将发现的联赛存入数据库"""
        if not leagues:
            logger.warning("⚠️ 没有联赛需要保存")
            return 0

        logger.info(f"💾 保存 {len(leagues)} 个联赛到数据库...")

        saved_count = 0

        with engine.begin() as conn:
            for league in leagues:
                try:
                    # 尝试插入新联赛
                    conn.execute(
                        text(
                            """
                        INSERT INTO leagues (
                            name, country, category, tier,
                            fbref_url, is_active, created_at, updated_at
                        ) VALUES (
                            :name, :country, :category, :tier,
                            :fbref_url, true, NOW(), NOW()
                        )
                    """
                        ),
                        {
                            "name": league["name"],
                            "country": league["country"],
                            "category": league["category"],
                            "tier": league["tier"],
                            "fbref_url": league["fbref_url"],
                        },
                    )

                    saved_count += 1

                except Exception as e:
                    # 如果已存在（并发情况），跳过
                    if "duplicate key" not in str(e).lower():
                        logger.warning(f"⚠️ 保存联赛失败 {league['name']}: {e}")

        logger.info(f"✅ 成功保存 {saved_count} 个联赛")
        return saved_count

    def get_statistics(self) -> Dict:
        """获取联赛统计信息"""
        with engine.connect() as conn:
            # 总数
            result = conn.execute(
                text("SELECT COUNT(*) FROM leagues WHERE fbref_url IS NOT NULL")
            )
            total = result.fetchone()[0]

            # 按分类统计
            result = conn.execute(
                text(
                    """
                SELECT category, COUNT(*) as count
                FROM leagues
                WHERE fbref_url IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """
                )
            )
            category_stats = {row[0]: row[1] for row in result.fetchall()}

            # 按国家统计
            result = conn.execute(
                text(
                    """
                SELECT country, COUNT(*) as count
                FROM leagues
                WHERE fbref_url IS NOT NULL
                  AND country != ''
                GROUP BY country
                ORDER BY count DESC
                LIMIT 10
            """
                )
            )
            country_stats = {row[0]: row[1] for row in result.fetchall()}

        return {
            "total_leagues": total,
            "category_distribution": category_stats,
            "top_countries": country_stats,
        }

    def run_discovery(self) -> Dict:
        """运行完整的联赛发现流程"""
        logger.info("🚀 启动FBref赛事发现器")
        logger.info("=" * 80)

        # Step 1: 加载已存在联赛
        self.load_existing_leagues()

        # Step 2: 获取索引页面
        soup = self.fetch_comp_index_page()
        if not soup:
            return {"error": "Failed to fetch page"}

        # Step 3: 解析联赛表格
        discovered = self.parse_league_tables(soup)

        # Step 4: 保存到数据库
        saved_count = self.save_to_database(discovered)

        # Step 5: 获取统计信息
        stats = self.get_statistics()

        logger.info("\n" + "=" * 80)
        logger.info("🎉 赛事发现完成!")
        logger.info("=" * 80)

        logger.info(f"\n📊 统计信息:")
        logger.info(f"  总联赛数: {stats['total_leagues']:,}")
        logger.info(f"  新增联赛: {saved_count}")

        logger.info(f"\n🏆 分类分布:")
        for category, count in stats["category_distribution"].items():
            logger.info(f"  {category:30s}: {count:3d}")

        logger.info(f"\n🌍 Top 10 国家:")
        for country, count in stats["top_countries"].items():
            logger.info(f"  {country:20s}: {count:3d}")

        logger.info("=" * 80)

        return {
            "discovered": len(discovered),
            "saved": saved_count,
            "statistics": stats,
        }


async def main():
    """主函数"""
    discovery = FBrefLeagueDiscovery()
    result = discovery.run_discovery()

    logger.info(f"\n✅ 程序执行完成")
    logger.info(f"   发现: {result.get('discovered', 0)} 个联赛")
    logger.info(f"   保存: {result.get('saved', 0)} 个联赛")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
