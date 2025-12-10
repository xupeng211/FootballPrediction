#!/usr/bin/env python3
"""
快速L1数据修复 - 使用已验证的数据
Quick L1 Data Fix - Using verified data
"""

import httpx
import json
import re
import psycopg2
from datetime import datetime

def extract_nextjs_data(html):
    """从HTML中提取Next.js数据"""
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
                return json.loads(nextjs_data_str)
            except json.JSONDecodeError:
                continue
    return None

def extract_matches_from_fixtures(fixtures_data):
    """从fixtures数据中提取比赛列表"""
    try:
        matches = []

        if isinstance(fixtures_data, dict):
            if "matches" in fixtures_data:
                direct_matches = fixtures_data["matches"]
                if isinstance(direct_matches, list):
                    matches.extend(direct_matches)

        return matches

    except Exception as e:
        print(f"❌ fixtures比赛提取异常: {e}")
        return []

def is_valid_match(match):
    """验证是否是有效的比赛数据"""
    required_fields = ["home", "away"]
    has_home_away = any(field in match for field in required_fields)
    has_id = "id" in match
    return has_home_away or has_id

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
                    print(f"🔍 在 {path}.{key} 找到matches: {len(value)} 场比赛")
                    for match in value:
                        if isinstance(match, dict) and is_valid_match(match):
                            matches.append(match)

                elif isinstance(value, (dict, list)):
                    new_path = f"{path}.{key}" if path else key
                    matches.extend(
                        recursive_search_matches(value, new_path, depth + 1, max_depth)
                    )

        elif isinstance(data, list) and len(data) > 0:
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    matches.extend(
                        recursive_search_matches(item, new_path, depth + 1, max_depth)
                    )

    except Exception as e:
        print(f"递归搜索异常 (路径: {path}): {e}")

    return matches

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
                print(f"📅 从fixtures提取到 {len(extracted_matches)} 场比赛")

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
                        print(f"📅 从overview.allMatches提取到 {len(valid_matches)} 场比赛")

        # 路径3: 页面级深度搜索
        if not matches:
            print("🔍 在页面数据中深度搜索比赛...")
            page_matches = recursive_search_matches(page_props, "pageProps")
            matches.extend(page_matches)
            if page_matches:
                print(f"📅 深度搜索找到 {len(page_matches)} 场比赛")

        # 过滤有效比赛
        valid_matches = []
        for match in matches:
            if isinstance(match, dict) and is_valid_match(match):
                if "leagueId" not in match:
                    match["leagueId"] = 47  # Premier League
                if "leagueName" not in match:
                    match["leagueName"] = "Premier League"
                valid_matches.append(match)

        return valid_matches

    except Exception as e:
        print(f"❌ fixtures数据提取异常: {e}")
        return []

def save_teams_to_db(teams_data):
    """保存球队数据到数据库"""
    try:
        # 使用正确的数据库连接
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="football_prediction",
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor()

        saved_count = 0
        for team in teams_data:
            try:
                team_id = team.get("id")
                team_name = team.get("name")
                if not team_name:
                    continue

                # 简单插入
                cur.execute(
                    """
                    INSERT INTO teams (name, country, external_id, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                """,
                    (team_name, "England", team_id),
                )

                if cur.rowcount > 0:
                    saved_count += 1
                    print(f"💾 新增球队: {team_name} (ID: {team_id})")

            except Exception as e:
                print(f"⚠️ 保存球队失败: {team.get('id', 'unknown')} - {e}")

        conn.commit()
        conn.close()
        print(f"✅ 成功保存 {saved_count} 支新球队")
        return saved_count

    except Exception as e:
        print(f"❌ 保存球队数据失败: {e}")
        return 0

def save_matches_to_db(match_data):
    """保存比赛数据到数据库"""
    try:
        # 使用正确的数据库连接
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="football_prediction",
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor()

        # 获取球队映射
        cur.execute(
            "SELECT external_id, id FROM teams WHERE external_id IS NOT NULL"
        )
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
                    print(
                        f"⚠️ 跳过比赛（找不到球队）: {fotmob_id} - {home_team} vs {away_team}"
                    )
                    continue

                # 插入比赛
                cur.execute(
                    """
                    INSERT INTO matches (
                        home_team_id, away_team_id,
                        home_score, away_score, status, match_date,
                        fotmob_id, data_source, data_completeness, created_at, updated_at
                    ) VALUES (
                        %s, %s, 0, 0, 'pending', NOW(),
                        %s, 'fotmob_v2', 'partial', NOW(), NOW()
                    )
                """,
                    (home_team_id, away_team_id, fotmob_id),
                )

                if cur.rowcount > 0:
                    saved_count += 1
                    print(
                        f"💾 保存比赛: {fotmob_id} - {home_team} vs {away_team}"
                    )

            except Exception as e:
                print(f"⚠️ 保存比赛失败: {match.get('id', 'unknown')} - {e}")

        conn.commit()
        conn.close()
        print(f"✅ 成功保存 {saved_count} 场比赛")
        return saved_count

    except Exception as e:
        print(f"❌ 保存比赛数据失败: {e}")
        return 0

def main():
    """主函数"""
    print("🚀 快速L1数据修复开始")
    print("="*50)

    # 访问英超联赛页面
    league_id = 47
    test_url = f"https://www.fotmob.com/leagues/{league_id}/overview/premier-league"

    print(f"🕷️ 访问联赛页面: {test_url}")

    try:
        # 使用httpx直接请求
        with httpx.Client(timeout=30) as client:
            response = client.get(
                test_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-GB,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )

        print(f"📊 响应状态: {response.status_code}, 大小: {len(response.text):,} 字符")

        if response.status_code != 200:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return 1

        # 提取Next.js数据
        if "__NEXT_DATA__" not in response.text:
            print("❌ 页面无Next.js数据")
            return 1

        nextjs_data = extract_nextjs_data(response.text)
        if not nextjs_data:
            print("❌ Next.js数据解析失败")
            return 1

        print("✅ Next.js数据解析成功")

        # 提取比赛数据
        matches = extract_fixtures_data(nextjs_data)
        if matches:
            print(f"🎉 成功找到 {len(matches)} 场比赛数据!")

            # 显示前几场比赛信息
            print("⚽ 比赛列表预览:")
            for j, match in enumerate(matches[:5], 1):
                home = match.get("home", {}).get("name", "Unknown")
                away = match.get("away", {}).get("name", "Unknown")
                match_id = match.get("id", "N/A")
                print(f"   {j}. {match_id:<10} {home:<25} vs {away:<25}")

            # 提取所有球队数据
            teams_data = [
                {"id": team.get("id"), "name": team.get("name")}
                for match in matches
                for team in [match.get("home", {}), match.get("away", {})]
            ]
            unique_teams = {
                team["id"]: team for team in teams_data if team.get("id")
            }
            unique_team_list = list(unique_teams.values())

            print(f"🏆 发现 {len(unique_team_list)} 支独特球队")

            # 保存球队数据
            if unique_team_list:
                print("💾 开始保存球队数据...")
                teams_saved = save_teams_to_db(unique_team_list)
                if teams_saved > 0:
                    print(f"✅ 球队数据保存成功: {teams_saved} 支新球队")

            # 保存比赛数据
            print("💾 开始保存比赛数据到数据库...")
            matches_saved = save_matches_to_db(matches)
            if matches_saved > 0:
                print(f"✅ 比赛数据保存成功: {matches_saved} 场比赛")

                # 最终统计
                print("🎊 **快速L1数据修复完成！**")
                print(f"   📊 总比赛数: {len(matches)}")
                print(f"   💾 入库比赛: {matches_saved}")
                print(f"   🏆 参赛球队: {len(unique_team_list)}")

                return 0
            else:
                print("⚠️ 比赛数据保存失败")
                return 1
        else:
            print("❌ 未找到比赛数据")
            return 1

    except Exception as e:
        print(f"❌ 数据修复异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
