#!/usr/bin/env python3
"""
全量L1采集脚本 - 2023-24英超完整赛季版本 (标准化入口)
Full Season L1 Collection Script - Complete 2023-24 Premier League Version (Standard Entry Point)
"""

import asyncio
import sys
import os
from datetime import datetime
import logging
from pathlib import Path

# 关键修正：添加项目根路径到sys.path，确保能正确导入src模块
# 当前文件位置：src/jobs/run_season_fixtures.py
# 项目根目录：src/jobs/的上一级
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.html_fotmob_collector import HTMLFotMobCollector
import psycopg2
import requests
import json
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"


def save_teams_to_db(teams_data):
    """直接使用SQL保存球队数据"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        saved_count = 0
        for team in teams_data:
            try:
                team_id = team.get("id")
                team_name = team.get("name")
                if not team_name:
                    continue

                # 简单插入，跳过重复
                cur.execute("""
                    INSERT INTO teams (name, country, fotmob_external_id, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT (fotmob_external_id) DO NOTHING
                """, (team_name, "England", team_id))

                if cur.rowcount > 0:
                    saved_count += 1
                    logger.info(f"💾 新增球队: {team_name} (ID: {team_id})")

            except Exception as e:
                logger.warning(f"⚠️ 保存球队失败: {team.get('id', 'unknown')} - {e}")

        conn.commit()
        conn.close()
        logger.info(f"✅ 成功保存 {saved_count} 支新球队")
        return saved_count

    except Exception as e:
        logger.error(f"❌ 保存球队数据失败: {e}")
        return 0


def save_matches_to_db(match_data):
    """直接使用SQL保存比赛数据"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 获取球队映射
        cur.execute("SELECT fotmob_external_id, id FROM teams WHERE fotmob_external_id IS NOT NULL")
        team_mapping = {row[0]: row[1] for row in cur.fetchall()}

        saved_count = 0
        for match in match_data:
            try:
                fotmob_id = str(match.get("id", ""))
                home_team = match.get("home", {}).get("name", "")
                away_team = match.get("away", {}).get("name", "")

                # 获取球队ID
                home_fotmob_id = match.get("home", {}).get("id")
                away_fotmob_id = match.get("away", {}).get("id")

                home_team_id = team_mapping.get(home_fotmob_id)
                away_team_id = team_mapping.get(away_fotmob_id)

                if not home_team_id or not away_team_id:
                    logger.warning(f"⚠️ 跳过比赛（找不到球队）: {fotmob_id} - {home_team} vs {away_team}")
                    continue

                # 插入比赛
                cur.execute("""
                    INSERT INTO matches (
                        home_team_id, away_team_id,
                        home_score, away_score, status, match_date,
                        fotmob_id, data_source, data_completeness, created_at, updated_at
                    ) VALUES (
                        %s, %s, 0, 0, 'pending', NOW(),
                        %s, 'fotmob_v2', 'partial', NOW(), NOW()
                    )
                    ON CONFLICT (fotmob_id) DO NOTHING
                """, (home_team_id, away_team_id, fotmob_id))

                if cur.rowcount > 0:
                    saved_count += 1
                    logger.info(f"💾 保存比赛: {fotmob_id} - {home_team} vs {away_team}")

            except Exception as e:
                logger.warning(f"⚠️ 保存比赛失败: {match.get('id', 'unknown')} - {e}")

        conn.commit()
        conn.close()
        logger.info(f"✅ 成功保存 {saved_count} 场比赛")
        return saved_count

    except Exception as e:
        logger.error(f"❌ 保存比赛数据失败: {e}")
        return 0


def extract_nextjs_data(html):
    """从HTML中提取Next.js数据"""
    patterns = [
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        r'window\.__NEXT_DATA__\s*=\s*(\{.*?\});?\s*<\/script>'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        if matches:
            nextjs_data_str = matches[0].strip()
            if nextjs_data_str.startswith('window.__NEXT_DATA__'):
                nextjs_data_str = nextjs_data_str.replace('window.__NEXT_DATA__', '').replace('=', '').strip()
                if nextjs_data_str.endswith(';'):
                    nextjs_data_str = nextjs_data_str[:-1]
            try:
                return json.loads(nextjs_data_str)
            except json.JSONDecodeError:
                continue
    return None


def extract_fixtures_data(nextjs_data):
    """从Next.js数据中提取比赛数据"""
    try:
        matches = []
        props = nextjs_data.get("props", {})
        page_props = props.get("pageProps", {})

        # 路径1: fixtures
        fixtures = page_props.get("fixtures", {})
        if fixtures:
            extracted_matches = extract_matches_from_fixtures(fixtures)
            matches.extend(extracted_matches)
            if extracted_matches:
                logger.info(f"📅 从fixtures提取到 {len(extracted_matches)} 场比赛")

        # 路径2: overview.allMatches (主要数据源)
        if not matches:
            overview = page_props.get("overview", {})
            if overview:
                matches_data = overview.get("matches", {})
                if "allMatches" in matches_data:
                    all_matches = matches_data["allMatches"]
                    if isinstance(all_matches, list):
                        valid_matches = [m for m in all_matches if is_valid_match(m)]
                        matches.extend(valid_matches)
                        logger.info(f"📅 从overview.allMatches提取到 {len(valid_matches)} 场比赛")

        # 路径3: 页面级深度搜索
        if not matches:
            logger.info("🔍 在页面数据中深度搜索比赛...")
            page_matches = recursive_search_matches(page_props, "pageProps")
            matches.extend(page_matches)
            if page_matches:
                logger.info(f"📅 深度搜索找到 {len(page_matches)} 场比赛")

        # 过滤有效比赛 - 全量处理，无切片限制
        valid_matches = []
        for match in matches:
            if isinstance(match, dict) and is_valid_match(match):
                # 确保比赛有联赛ID
                if "leagueId" not in match:
                    match["leagueId"] = 47  # Premier League
                if "leagueName" not in match:
                    match["leagueName"] = "Premier League"
                valid_matches.append(match)

        return valid_matches

    except Exception as e:
        logger.error(f"❌ fixtures数据提取异常: {e}")
        return []


def extract_matches_from_fixtures(fixtures_data):
    """从fixtures数据中提取比赛列表"""
    try:
        matches = []

        if isinstance(fixtures_data, dict):
            if "matches" in fixtures_data:
                direct_matches = fixtures_data["matches"]
                if isinstance(direct_matches, list):
                    matches.extend(direct_matches)

            # 递归搜索matches
            if not matches:
                matches.extend(recursive_search_matches(fixtures_data))

        return matches

    except Exception as e:
        logger.error(f"❌ fixtures比赛提取异常: {e}")
        return []


def recursive_search_matches(data, path="", depth=0, max_depth=6):
    """递归搜索matches数据"""
    matches = []

    if depth > max_depth:
        return matches

    try:
        if isinstance(data, dict):
            for key, value in data.items():
                key_lower = str(key).lower()

                if key_lower == "matches" and isinstance(value, list):
                    logger.debug(f"🔍 在 {path}.{key} 找到matches: {len(value)} 场比赛")
                    for match in value:
                        if isinstance(match, dict) and is_valid_match(match):
                            matches.append(match)

                elif isinstance(value, (dict, list)):
                    new_path = f"{path}.{key}" if path else key
                    matches.extend(recursive_search_matches(value, new_path, depth + 1, max_depth))

        elif isinstance(data, list) and len(data) > 0:
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    matches.extend(recursive_search_matches(item, new_path, depth + 1, max_depth))

    except Exception as e:
        logger.debug(f"递归搜索异常 (路径: {path}): {e}")

    return matches


def is_valid_match(match):
    """验证是否是有效的比赛数据"""
    required_fields = ["home", "away"]
    has_home_away = any(field in match for field in required_fields)
    has_id = "id" in match
    return has_home_away or has_id


def print_help():
    """打印帮助信息"""
    print("""
🏆 英超赛季数据采集工具
==========================

用法:
  python3 src/jobs/run_season_fixtures.py [选项]

选项:
  --help, -h    显示此帮助信息
  --dry-run     仅测试网络连接和数据提取，不写入数据库
  --league-id   指定联赛ID (默认: 47 = Premier League)
  --verbose     详细日志输出

示例:
  python3 src/jobs/run_season_fixtures.py                    # 标准模式
  python3 src/jobs/run_season_fixtures.py --dry-run         # 测试模式
  python3 src/jobs/run_season_fixtures.py --verbose         # 详细模式

注意:
  - 此脚本会采集完整的赛季数据并保存到数据库
  - 确保数据库服务正在运行
  - 首次运行会创建球队和比赛记录
    """)


async def main():
    """主函数 - 全赛季采集"""
    import argparse

    parser = argparse.ArgumentParser(description='英超赛季数据采集工具')
    parser.add_argument('--dry-run', action='store_true', help='仅测试，不写入数据库')
    parser.add_argument('--league-id', type=int, default=47, help='联赛ID (默认: 47)')
    parser.add_argument('--verbose', action='store_true', help='详细日志')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("🚀 启动2023-24英超全赛季L1数据采集")
    logger.info("🎯 目标：完整380场英超比赛 + 数据库存储")

    if args.dry_run:
        logger.info("🧪 运行在测试模式 - 不会写入数据库")

    # 初始化采集器
    collector = HTMLFotMobCollector(
        max_retries=3,
        timeout=(10, 30),
        enable_stealth=True
    )
    await collector.initialize()

    try:
        # 联赛页面URL
        test_url = f"https://www.fotmob.com/leagues/{args.league_id}/overview/premier-league"
        logger.info(f"🕷️ 访问英超联赛页面: {test_url}")

        # 发起请求
        response = requests.get(
            test_url,
            headers=collector._get_current_headers(),
            timeout=collector.timeout,
            allow_redirects=True,
            verify=False
        )

        logger.info(f"📊 响应状态: {response.status_code}, 大小: {len(response.text):,} 字符")

        if response.status_code != 200:
            logger.error(f"❌ HTTP请求失败: {response.status_code}")
            return 1

        # 提取Next.js数据
        if '__NEXT_DATA__' not in response.text:
            logger.error("❌ 页面无Next.js数据")
            return 1

        nextjs_data = extract_nextjs_data(response.text)
        if not nextjs_data:
            logger.error("❌ Next.js数据解析失败")
            return 1

        logger.info("✅ Next.js数据解析成功")

        # 提取比赛数据 - 全量无限制
        matches = extract_fixtures_data(nextjs_data)
        if matches:
            logger.info(f"🎉 成功找到 {len(matches)} 场比赛数据!")

            # 显示前几场比赛信息
            logger.info("⚽ 比赛列表预览:")
            for j, match in enumerate(matches[:10], 1):
                home = match.get("home", {}).get("name", "Unknown")
                away = match.get("away", {}).get("name", "Unknown")
                match_id = match.get("id", "N/A")
                logger.info(f"   {j:2d}. {home:<25} vs {away:<25} (ID: {match_id})")

            if len(matches) > 10:
                logger.info(f"   ... 还有 {len(matches) - 10} 场比赛")

            if not args.dry_run:
                # 提取所有球队数据 - 全量处理
                teams_data = [
                    {"id": team.get("id"), "name": team.get("name")}
                    for match in matches  # 全部比赛，无切片
                    for team in [match.get("home", {}), match.get("away", {})]
                ]
                unique_teams = {team["id"]: team for team in teams_data if team.get("id")}
                unique_team_list = list(unique_teams.values())

                logger.info(f"🏆 发现 {len(unique_team_list)} 支独特球队")

                # 保存球队数据
                if unique_team_list:
                    logger.info("💾 开始保存球队数据...")
                    teams_saved = save_teams_to_db(unique_team_list)
                    if teams_saved > 0:
                        logger.info(f"✅ 球队数据保存成功: {teams_saved} 支新球队")

                # 保存比赛数据 - 全量处理
                logger.info("💾 开始保存比赛数据到数据库...")
                matches_saved = save_matches_to_db(matches)
                if matches_saved > 0:
                    logger.info(f"✅ 比赛数据保存成功: {matches_saved} 场比赛")

                    # 最终统计
                    logger.info("🎊 **2023-24英超全赛季L1采集完成！**")
                    logger.info(f"   📊 总比赛数: {len(matches)}")
                    logger.info(f"   💾 入库比赛: {matches_saved}")
                    logger.info(f"   🏆 参赛球队: {len(unique_team_list)}")

                    return 0
                else:
                    logger.warning("⚠️ 比赛数据保存失败")
                    return 1
            else:
                logger.info("🧪 测试模式完成 - 未写入数据库")
                return 0
        else:
            logger.error("❌ 未找到比赛数据")
            return 1

    except Exception as e:
        logger.error(f"❌ 全赛季采集异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await collector.close()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}")
        sys.exit(1)
