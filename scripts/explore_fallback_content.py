#!/usr/bin/env python3
"""
深度探索fallback内容
Deep exploration of fallback content
"""

import sys
import os
import asyncio
import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from collectors.html_fotmob_collector import HTMLFotMobCollector


class FallbackExplorer:
    """Fallback数据深度探索器"""

    def __init__(self):
        self.collector = HTMLFotMobCollector(
            max_retries=3, timeout=(10, 30), enable_stealth=True
        )
        self.target_url = "https://www.fotmob.com/matches?date=20240225"
        self.premier_league_id = 47

    async def initialize(self):
        """初始化采集器"""
        await self.collector.initialize()
        print("✅ HTML采集器初始化完成")

    def get_headers(self) -> dict[str, str]:
        """获取请求头"""
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def fetch_page(self) -> Optional[str]:
        """获取页面内容"""
        try:
            print(f"🕷️ 请求赛程页面: {self.target_url}")

            response = requests.get(
                self.target_url,
                headers=self.get_headers(),
                timeout=(10, 30),
                allow_redirects=True,
                verify=False,
            )

            print(f"📊 HTTP状态码: {response.status_code}")
            print(f"📊 响应大小: {len(response.text):,} 字符")

            if response.status_code != 200:
                print(f"❌ 页面请求失败，状态码: {response.status_code}")
                return None

            return response.text

        except Exception as e:
            print(f"❌ 页面获取异常: {e}")
            return None

    def extract_nextjs_data(self, html: str) -> Optional[dict[str, Any]]:
        """提取 Next.js 数据"""
        try:
            if "__NEXT_DATA__" not in html:
                print("❌ 页面中未找到 __NEXT_DATA__")
                return None

            print("✅ 发现 __NEXT_DATA__ 标签")

            # 尝试不同的正则模式
            patterns = [
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
                r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                r"window\.__NEXT_DATA__\s*=\s*(\{.*?\});?\s*<\/script>",
            ]

            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, html, re.DOTALL)
                if matches:
                    print(f"✅ 使用模式 {i+1} 找到 Next.js 数据")
                    nextjs_data_str = matches[0].strip()

                    # 清理 JavaScript 包装
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
                        print(
                            f"✅ Next.js JSON 解析成功，大小: {len(str(nextjs_data)):,} 字符"
                        )
                        return nextjs_data
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 解析失败 (模式 {i+1}): {e}")
                        continue

            print("❌ 所有模式都未能解析出有效的 JSON")
            return None

        except Exception as e:
            print(f"❌ Next.js 数据提取异常: {e}")
            return None

    def explore_fallback_content(self, nextjs_data: dict[str, Any]):
        """深度探索fallback内容"""
        print("\n🔬 开始深度探索fallback内容...")

        fallback_data = (
            nextjs_data.get("props", {}).get("pageProps", {}).get("fallback", {})
        )

        if not fallback_data:
            print("❌ 未找到fallback数据")
            return

        print(f"✅ 找到fallback数据，包含 {len(fallback_data)} 个键")

        for key, value in fallback_data.items():
            print(f"\n📋 键: {key}")
            print(f"   类型: {type(value)}")

            if isinstance(value, dict):
                print(f"   包含字段: {list(value.keys())[:10]}")

                # 检查是否包含matches
                if "matches" in value:
                    matches = value.get("matches", [])
                    print(f"   ⚽ 包含matches: {len(matches)} 场比赛")

                    if matches:
                        # 检查英超比赛
                        premier_matches = []
                        for match in matches:
                            if isinstance(match, dict):
                                league_id = match.get("leagueId")
                                if league_id == self.premier_league_id:
                                    premier_matches.append(match)

                        if premier_matches:
                            print(f"      🎉 找到 {len(premier_matches)} 场英超比赛！")
                            for i, match in enumerate(premier_matches[:3], 1):
                                home = match.get("home", {}).get("name", "Unknown")
                                away = match.get("away", {}).get("name", "Unknown")
                                match_id = match.get("id", "unknown")
                                print(f"        {i}. {home} vs {away} (ID: {match_id})")
                        else:
                            print("      ⚠️ 该matches中无英超比赛")

                # 检查是否包含leagues
                if "leagues" in value:
                    leagues = value.get("leagues", [])
                    print(f"   🏆 包含leagues: {len(leagues)} 个联赛")

                    for i, league in enumerate(leagues[:3], 1):
                        if isinstance(league, dict):
                            league_id = league.get("id")
                            league_name = league.get("name")
                            matches_count = len(league.get("matches", []))
                            print(
                                f"      {i}. {league_name} (ID: {league_id}) - {matches_count} 场比赛"
                            )

                # 显示关键信息
                important_keys = ["id", "name", "leagueId", "primaryId"]
                for imp_key in important_keys:
                    if imp_key in value:
                        print(f"   {imp_key}: {value[imp_key]}")

            elif isinstance(value, list):
                print(f"   列表长度: {len(value)}")
                if len(value) > 0:
                    first_item = value[0]
                    if isinstance(first_item, dict):
                        print(f"   第一个元素字段: {list(first_item.keys())[:5]}")

    def find_all_leagues(self, nextjs_data: dict[str, Any]):
        """寻找所有联赛信息"""
        print("\n🏆 寻找所有联赛信息...")

        fallback_data = (
            nextjs_data.get("props", {}).get("pageProps", {}).get("fallback", {})
        )

        all_leagues = {}

        for key, value in fallback_data.items():
            if not isinstance(value, dict):
                continue

            # 直接在value中查找league信息
            if any(k in value for k in ["id", "name", "matches"]):
                league_id = (
                    value.get("id") or value.get("primaryId") or value.get("leagueId")
                )
                league_name = value.get("name")

                if league_id and league_name:
                    all_leagues[str(league_id)] = {
                        "id": league_id,
                        "name": league_name,
                        "source_key": key,
                        "matches_count": (
                            len(value.get("matches", []))
                            if isinstance(value.get("matches"), list)
                            else 0
                        ),
                    }

            # 在matches中查找league信息
            if "matches" in value:
                matches = value.get("matches", [])
                if isinstance(matches, list) and matches:
                    for match in matches:
                        if isinstance(match, dict):
                            league_id = match.get("leagueId")
                            if league_id and str(league_id) not in all_leagues:
                                all_leagues[str(league_id)] = {
                                    "id": league_id,
                                    "name": f"League-{league_id}",
                                    "source_key": key,
                                    "matches_count": 1,
                                }
                                if "leagueName" in match:
                                    all_leagues[str(league_id)]["name"] = match[
                                        "leagueName"
                                    ]

        print(f"📊 找到 {len(all_leagues)} 个联赛:")
        for league_id, info in sorted(
            all_leagues.items(),
            key=lambda x: x[1].get("matches_count", 0),
            reverse=True,
        ):
            print(
                f"  ID {league_id}: {info['name']} - {info['matches_count']} 场比赛 (来源: {info['source_key']})"
            )

        # 检查英超
        if str(self.premier_league_id) in all_leagues:
            premier_info = all_leagues[str(self.premier_league_id)]
            print(
                f"✅ 找到英超联赛: {premier_info['name']} - {premier_info['matches_count']} 场比赛"
            )
        else:
            print(f"⚠️ 未找到英超联赛 (ID: {self.premier_league_id})")

    async def run_exploration(self):
        """运行探索"""
        print("🚀 开始fallback内容深度探索")
        print("=" * 60)

        # 初始化
        await self.initialize()

        # 获取页面
        html = await self.fetch_page()
        if not html:
            print("❌ 无法获取页面内容，探索终止")
            return

        # 提取 Next.js 数据
        nextjs_data = self.extract_nextjs_data(html)
        if not nextjs_data:
            print("❌ 无法提取 Next.js 数据，探索终止")
            return

        # 探索fallback内容
        self.explore_fallback_content(nextjs_data)

        # 寻找所有联赛
        self.find_all_leagues(nextjs_data)

        print("\n" + "=" * 60)
        print("🔍 探索完成")


async def main():
    """主函数"""
    explorer = FallbackExplorer()
    await explorer.run_exploration()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback

        traceback.print_exc()
