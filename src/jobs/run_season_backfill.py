#!/usr/bin/env python3
"""
2023-2024 赛季英超联赛数据批量采集 - 联赛页面策略
Premier League 2023-2024 Season Batch Collection - League Page Strategy

生产高质量黄金数据集 - 直接访问联赛页面获取完整赛季数据
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import json
import re

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.async_manager import get_db_session
from collectors.html_fotmob_collector import HTMLFotMobCollector
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SeasonBackfillJob:
    """赛季数据批量采集任务 - 联赛页面策略"""

    def __init__(self):
        self.logger = logger
        # 使用 HTML 采集器（与 L2 相同的技术栈）
        self.html_collector = HTMLFotMobCollector(
            max_retries=3, timeout=(10, 30), enable_stealth=True
        )

        # 2023-2024 赛季英超配置 - 正式生产模式
        self.premier_league_id = 47
        self.season_start_date = datetime(2023, 8, 11)  # 2023-08-11 赛季开始
        self.season_end_date = datetime(2024, 5, 19)  # 2024-05-19 赛季结束

        # 联赛页面URL - 经过验证的成功URL
        self.league_urls = [
            "https://www.fotmob.com/leagues/47/overview/premier-league",
            "https://www.fotmob.com/leagues/47/matches/premier-league",
            "https://www.fotmob.com/leagues/47",
        ]

        # 统计信息
        self.stats = {
            "total_matches": 0,
            "premier_matches": 0,
            "saved_matches": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
            "teams_found": 0,
            "fixtures_extracted": 0,
        }

    async def initialize(self):
        """初始化任务"""
        await self.html_collector.initialize()
        self.stats["start_time"] = datetime.now()
        self.logger.info("✅ 赛季采集任务初始化完成 - 联赛页面策略")
        self.logger.info(f"📊 目标联赛: Premier League (ID: {self.premier_league_id})")
        self.logger.info("🎯 采集策略: 直接访问联赛页面获取完整赛季数据")

    async def collect_league_season_data(self) -> dict[str, Any]:
        """
        采集整个赛季的联赛数据 - 联赛页面策略

        Returns:
            联赛数据结构，包含球队、比赛、赛季信息等
        """
        try:
            self.logger.info("🎯 开始采集联赛页面数据...")

            # 尝试每个URL直到成功
            for i, url in enumerate(self.league_urls, 1):
                self.logger.info(f"🕷️ [{i}/{len(self.league_urls)}] 尝试URL: {url}")

                try:
                    # 发起请求
                    response = requests.get(
                        url,
                        headers=self.html_collector._get_current_headers(),
                        timeout=self.html_collector.timeout,
                        allow_redirects=True,
                        verify=True,  # 启用 SSL 证书验证
                    )

                    self.logger.info(
                        f"📊 响应状态: {response.status_code}, 大小: {len(response.text):,} 字符"
                    )

                    if response.status_code != 200:
                        self.logger.warning(
                            f"   ❌ HTTP状态码错误: {response.status_code}"
                        )
                        continue

                    # 优先使用 response.text (requests已自动处理GZIP解压)
                    # 只在 response.text 为空且检测到GZIP时才使用手动解压
                    if response.text and len(response.text) > 1000:
                        html_content = response.text
                        self.logger.debug(
                            "   🔧 使用response.text (requests已自动解压)"
                        )
                    elif response.content and response.content[:2] == b"\x1f\x8b":
                        self.logger.info("   🔧 检测到GZIP压缩，使用手动解压...")
                        html_content = self.html_collector._manual_decompress_response(
                            response
                        )
                    else:
                        self.logger.warning("   ⚠️ 响应内容异常，尝试使用response.text")
                        html_content = response.text

                    # 解析Next.js数据
                    if "__NEXT_DATA__" not in html_content:
                        self.logger.warning("   ❌ 页面无Next.js数据")
                        continue

                    # 提取Next.js数据
                    nextjs_data = self._extract_nextjs_data(
                        html_content, f"league_page_{i}"
                    )
                    if not nextjs_data:
                        self.logger.warning("   ❌ Next.js数据解析失败")
                        continue

                    self.logger.info("   ✅ Next.js数据解析成功")

                    # 提取赛季数据
                    season_data = self._extract_season_data(nextjs_data, url)
                    if season_data:
                        self.logger.info(
                            f"   🎉 成功提取赛季数据: {len(season_data.get('teams', []))} 支球队, {len(season_data.get('matches', []))} 场比赛"
                        )
                        return season_data

                except Exception as e:
                    self.logger.error(f"   ❌ URL访问异常: {e}")
                    self.stats["errors"] += 1
                    continue

            self.logger.error("❌ 所有联赛页面URL都访问失败")
            return {}

        except Exception as e:
            self.logger.error(f"❌ 联赛赛季数据采集失败: {e}")
            self.stats["errors"] += 1
            return {}

    def _extract_season_data(
        self, nextjs_data: dict[str, Any], source_url: str
    ) -> dict[str, Any]:
        """
        从Next.js数据中提取完整的赛季数据

        Args:
            nextjs_data: Next.js数据
            source_url: 数据源URL

        Returns:
            赛季数据结构
        """
        try:
            season_data = {
                "source_url": source_url,
                "extracted_at": datetime.now().isoformat(),
                "teams": [],
                "matches": [],
                "season_info": {},
                "leagues": [],
                "overview": {},
            }

            # 解析主要数据结构
            props = nextjs_data.get("props", {})
            page_props = props.get("pageProps", {})

            # 1. 提取overview数据（包含球队信息）
            overview = page_props.get("overview", {})
            if overview:
                season_data["overview"] = overview

                # 提取球队信息
                matches_data = overview.get("matches", {})
                fixture_info = matches_data.get("fixtureInfo", {})

                if isinstance(fixture_info, dict):
                    # 检查fixtureInfo字典中的teams字段
                    teams_data = fixture_info.get("teams", [])
                    if isinstance(teams_data, list):
                        season_data["teams"] = teams_data
                        self.logger.info(
                            f"   📊 从overview提取到 {len(teams_data)} 支球队"
                        )

                        # 显示球队列表
                        for team in teams_data[:5]:  # 显示前5支球队
                            team_name = team.get("name", "Unknown")
                            team_id = team.get("id", "N/A")
                            self.logger.info(f"      ⚽ {team_name} (ID: {team_id})")

                        if len(teams_data) > 5:
                            self.logger.info(
                                f"      ... 还有 {len(teams_data) - 5} 支球队"
                            )
                    else:
                        self.logger.warning(
                            f"   ⚠️ fixtureInfo.teams不是数组: {type(teams_data)}"
                        )
                elif isinstance(fixture_info, list):
                    # 备选方案：如果fixtureInfo是列表
                    season_data["teams"] = fixture_info
                    self.logger.info(
                        f"   📊 从overview提取到 {len(fixture_info)} 支球队 (列表格式)"
                    )
                else:
                    self.logger.warning(
                        f"   ⚠️ fixtureInfo类型异常: {type(fixture_info)}"
                    )

                # 提取当前赛季信息
                season_info = matches_data.get("seasons", [])
                if (
                    season_info
                    and isinstance(season_info, list)
                    and len(season_info) > 0
                ):
                    current_season = season_info[0]  # 通常是当前赛季
                    season_data["season_info"] = current_season
                    self.logger.info(
                        f"   📅 赛季信息: {current_season.get('name', 'Unknown')}"
                    )

            # 2. 提取fixtures数据（比赛赛程）
            fixtures = page_props.get("fixtures", {})
            if fixtures:
                # 提取比赛列表
                matches = self._extract_matches_from_fixtures(fixtures)
                if matches:
                    season_data["matches"] = matches
                    self.logger.info(f"   📅 从fixtures提取到 {len(matches)} 场比赛")

                    # 显示比赛概览
                    for i, match in enumerate(matches[:3]):  # 显示前3场比赛
                        home_team = match.get("home", {}).get("name", "Unknown")
                        away_team = match.get("away", {}).get("name", "Unknown")
                        status = match.get("status", {}).get("finished", False)
                        status_text = "已结束" if status else "未结束"
                        self.logger.info(
                            f"      {i+1}. {home_team} vs {away_team} ({status_text})"
                        )

                    if len(matches) > 3:
                        self.logger.info(f"      ... 还有 {len(matches) - 3} 场比赛")

            # 3. 提取所有可用赛季信息
            all_seasons = page_props.get("allAvailableSeasons", [])
            if all_seasons:
                season_data["all_seasons"] = all_seasons
                self.logger.info(f"   📊 可用赛季: {len(all_seasons)} 个")

            # 4. 提取联赛详情
            details = page_props.get("details", {})
            if details:
                season_data["league_details"] = details
                league_name = details.get("name", "Unknown League")
                self.logger.info(f"   🏆 联赛详情: {league_name}")

            return season_data

        except Exception as e:
            self.logger.error(f"❌ 赛季数据提取异常: {e}")
            return {}

    def _extract_matches_from_fixtures(
        self, fixtures_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        从fixtures数据中提取比赛列表

        Args:
            fixtures_data: fixtures数据结构

        Returns:
            比赛列表
        """
        try:
            matches = []

            # fixtures数据可能有多种结构，尝试不同的提取路径
            if isinstance(fixtures_data, dict):
                # 路径1: 直接的matches字段
                if "matches" in fixtures_data:
                    direct_matches = fixtures_data["matches"]
                    if isinstance(direct_matches, list):
                        matches.extend(direct_matches)

                # 路径2: tournaments/leagues结构
                for key in ["tournaments", "leagues", "rounds", "stages"]:
                    if key in fixtures_data:
                        structure = fixtures_data[key]
                        if isinstance(structure, list):
                            for item in structure:
                                if isinstance(item, dict) and "matches" in item:
                                    item_matches = item["matches"]
                                    if isinstance(item_matches, list):
                                        matches.extend(item_matches)

                # 路径3: 递归搜索matches
                if not matches:
                    matches.extend(self._recursive_search_matches(fixtures_data))

            elif isinstance(fixtures_data, list):
                # 如果是列表，递归搜索每个元素
                for item in fixtures_data:
                    if isinstance(item, dict):
                        matches.extend(self._recursive_search_matches(item))

            # 过滤有效比赛
            valid_matches = []
            for match in matches:
                if isinstance(match, dict) and self._is_valid_match(match):
                    # 确保比赛有联赛ID
                    if "leagueId" not in match:
                        match["leagueId"] = self.premier_league_id
                    if "leagueName" not in match:
                        match["leagueName"] = "Premier League"
                    valid_matches.append(match)

            return valid_matches

        except Exception as e:
            self.logger.error(f"❌ fixtures比赛提取异常: {e}")
            return []

    def _recursive_search_matches(
        self, data: Any, path: str = "", depth: int = 0, max_depth: int = 6
    ) -> list[dict[str, Any]]:
        """递归搜索matches数据"""
        matches = []

        if depth > max_depth:
            return matches

        try:
            if isinstance(data, dict):
                # 检查当前层级的matches
                for key, value in data.items():
                    key_lower = str(key).lower()

                    # 如果是matches字段
                    if key_lower == "matches" and isinstance(value, list):
                        self.logger.debug(
                            f"   🔍 在 {path}.{key} 找到matches: {len(value)} 场比赛"
                        )
                        for match in value:
                            if isinstance(match, dict) and self._is_valid_match(match):
                                matches.append(match)

                    # 继续递归搜索
                    elif isinstance(value, (dict, list)):
                        new_path = f"{path}.{key}" if path else key
                        matches.extend(
                            self._recursive_search_matches(
                                value, new_path, depth + 1, max_depth
                            )
                        )

            elif isinstance(data, list) and len(data) > 0:
                for i, item in enumerate(data):
                    if isinstance(item, (dict, list)):
                        new_path = f"{path}[{i}]" if path else f"[{i}]"
                        matches.extend(
                            self._recursive_search_matches(
                                item, new_path, depth + 1, max_depth
                            )
                        )

        except Exception as e:
            self.logger.debug(f"递归搜索异常 (路径: {path}): {e}")

        return matches

    def _extract_nextjs_data(self, html: str, context: str) -> Optional[dict[str, Any]]:
        """从HTML中提取Next.js数据"""
        try:
            patterns = [
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                r"window\.__NEXT_DATA__\s*=\s*(\{.*?\});?\s*<\/script>",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    nextjs_data_str = matches[0].strip()

                    if nextjs_data_str.startswith("window.__NEXT_DATA__"):
                        nextjs_data_str = (
                            nextjs_data_str.replace("window.__NEXT_DATA__", "")
                            .replace("=", "")
                            .strip()
                        )
                        if nextjs_data_str.endswith(";"):
                            nextjs_data_str = nextjs_data_str[:-1]

                    try:
                        nextjs_data = json.loads(nextjs_data_str)
                        self.logger.info(f"✅ Next.js数据解析成功: {context}")
                        return nextjs_data
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"⚠️ JSON解析失败 {context}: {e}")
                        continue

            return None

        except Exception as e:
            self.logger.error(f"❌ Next.js提取异常 {context}: {e}")
            return None

    def _is_valid_match(self, match: dict[str, Any]) -> bool:
        """验证是否是有效的比赛数据"""
        # 检查是否包含基本的比赛字段
        required_fields = ["home", "away"]  # 至少要有主客队

        # 如果包含主客队信息，认为是有效比赛
        has_home_away = any(field in match for field in required_fields)

        # 如果有比赛ID，也认为是有效比赛
        has_id = "id" in match

        return has_home_away or has_id

    async def save_season_data_to_db(self, season_data: dict[str, Any]) -> int:
        """
        保存赛季数据到数据库

        Args:
            season_data: 赛季数据结构

        Returns:
            保存的比赛数量
        """
        if not season_data:
            return 0

        try:
            saved_count = 0
            async with get_db_session() as session:
                from sqlalchemy import text

                # 保存球队信息
                teams = season_data.get("teams", [])
                if teams:
                    self.logger.info(f"💾 开始保存 {len(teams)} 支球队信息...")
                    for team in teams:
                        try:
                            team_id = team.get("id")
                            team_name = team.get("name")
                            if not team_name:
                                continue

                            # 插入或更新球队信息
                            insert_team_sql = text(
                                """
                                INSERT INTO teams (fotmob_id, name, created_at, updated_at)
                                VALUES (:fotmob_id, :name, NOW(), NOW())
                                ON CONFLICT (fotmob_id) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    updated_at = NOW()
                            """
                            )

                            await session.execute(
                                insert_team_sql,
                                {"fotmob_id": team_id, "name": team_name},
                            )

                            saved_count += 1

                        except Exception as e:
                            self.logger.warning(
                                f"   ⚠️ 保存球队失败: {team.get('name', 'unknown')} - {e}"
                            )

                # 保存比赛信息
                matches = season_data.get("matches", [])
                if matches:
                    self.logger.info(f"💾 开始保存 {len(matches)} 场比赛信息...")
                    for match in matches:
                        try:
                            fotmob_id = str(match.get("id", ""))
                            home_team = match.get("home", {}).get("name", "")
                            away_team = match.get("away", {}).get("name", "")
                            home_score = match.get("home", {}).get("score", 0)
                            away_score = match.get("away", {}).get("score", 0)
                            status = (
                                "completed"
                                if match.get("status", {}).get("finished", False)
                                else "pending"
                            )

                            # 提取比赛时间（如果有）
                            match_time = (
                                match.get("time") or match.get("date") or datetime.now()
                            )

                            # 插入比赛信息
                            insert_match_sql = text(
                                """
                                INSERT INTO matches (
                                    fotmob_id, home_team_id, away_team_id,
                                    home_score, away_score, status, match_date,
                                    created_at, updated_at, data_source
                                ) VALUES (
                                    :fotmob_id,
                                    (SELECT COALESCE((SELECT id FROM teams WHERE name ILIKE :home_team LIMIT 1), 0)),
                                    (SELECT COALESCE((SELECT id FROM teams WHERE name ILIKE :away_team LIMIT 1), 1)),
                                    :home_score, :away_score, :status, :match_time,
                                    NOW(), NOW(), 'fotmob_season_backfill'
                                )
                                ON CONFLICT (fotmob_id) DO NOTHING
                            """
                            )

                            await session.execute(
                                insert_match_sql,
                                {
                                    "fotmob_id": fotmob_id,
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "home_score": home_score,
                                    "away_score": away_score,
                                    "status": status,
                                    "match_time": match_time,
                                },
                            )

                            saved_count += 1
                            self.logger.debug(
                                f"      💾 保存比赛: {fotmob_id} - {home_team} vs {away_team}"
                            )

                        except Exception as e:
                            self.logger.warning(
                                f"   ⚠️ 保存比赛失败: {match.get('id', 'unknown')} - {e}"
                            )
                            self.stats["errors"] += 1

                await session.commit()

            self.logger.info(f"   ✅ 成功保存数据，总计: {saved_count} 条记录")
            return saved_count

        except Exception as e:
            self.logger.error(f"❌ 保存赛季数据失败: {e}")
            self.stats["errors"] += 1
            return 0

    def print_summary(self):
        """打印采集总结"""
        self.stats["end_time"] = datetime.now()
        duration = self.stats["end_time"] - self.stats["start_time"]

        self.logger.info("=" * 60)
        self.logger.info("📊 联赛页面赛季采集任务完成总结")
        self.logger.info("=" * 60)
        self.logger.info(f"⏱️  总耗时: {duration}")
        self.logger.info(f"⚽ 发现球队: {self.stats['teams_found']}")
        self.logger.info(f"📅 提取比赛: {self.stats['fixtures_extracted']}")
        self.logger.info(f"💾 已保存数据: {self.stats['saved_matches']} 条")
        self.logger.info(f"❌ 错误次数: {self.stats['errors']}")

        if self.stats["errors"] == 0:
            self.logger.info("🎉 采集任务完美完成！")
        else:
            self.logger.warning(f"⚠️ 采集完成，但有 {self.stats['errors']} 个错误")

    async def run(self):
        """运行赛季采集任务 - 联赛页面策略"""
        try:
            await self.initialize()

            self.logger.info("🚀 开始采集 2023-2024 赛季英超数据 - 联赛页面策略")
            self.logger.info("=" * 60)

            # 采集联赛赛季数据
            season_data = await self.collect_league_season_data()

            if season_data:
                # 更新统计信息
                teams = season_data.get("teams", [])
                matches = season_data.get("matches", [])
                self.stats["teams_found"] = len(teams)
                self.stats["fixtures_extracted"] = len(matches)

                self.logger.info("✅ 联赛数据采集完成:")
                self.logger.info(f"   📊 球队: {len(teams)} 支")
                self.logger.info(f"   📅 比赛: {len(matches)} 场")

                # 保存到数据库
                self.logger.info("💾 开始保存赛季数据到数据库...")
                saved_count = await self.save_season_data_to_db(season_data)
                self.stats["saved_matches"] = saved_count

                if saved_count > 0:
                    self.logger.info(f"🎉 数据保存成功: {saved_count} 条记录")
                else:
                    self.logger.warning("⚠️ 没有数据被保存到数据库")

            else:
                self.logger.error("❌ 联赛赛季数据采集失败")
                self.stats["errors"] += 1

            # 打印最终总结
            self.print_summary()

        except KeyboardInterrupt:
            self.logger.info("⚠️ 用户中断任务")
            self.print_summary()
        except Exception as e:
            self.logger.error(f"❌ 赛季采集任务失败: {e}")
            self.stats["errors"] += 1
            raise
        finally:
            # 清理 HTML 采集器
            if hasattr(self, "html_collector"):
                await self.html_collector.close()


async def main():
    """主函数"""
    logger.info("🚀 启动 2023-2024 赛季英超数据批量采集 - 联赛页面策略")
    logger.info("📋 目标: 生产高质量黄金数据集")

    job = SeasonBackfillJob()
    await job.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断")
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}")
        sys.exit(1)
