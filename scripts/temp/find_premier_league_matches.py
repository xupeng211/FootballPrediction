#!/usr/bin/env python3
"""
寻找真正的英超比赛ID
基于FotMob的实际数据结构来寻找英超比赛
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from curl_cffi.requests import AsyncSession


class PremierLeagueMatchFinder:
    """英超比赛寻找器"""

    def __init__(self):
        self.session = None
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
        }

    async def init_session(self):
        """初始化会话"""
        if not self.session:
            self.session = AsyncSession(impersonate="chrome120")
            await self.session.get("https://www.fotmob.com/")

    async def get_league_matches(self, league_id="47"):  # 47 是英超的FotMob ID
        """获取英超比赛列表"""
        await self.init_session()

        # 尝试不同的英超接口
        endpoints = [
            f"/api/leagues?id={league_id}",
            "/api/leagues?name=Premier%20League",
            f"/api/leagues/{league_id}",
            f"/api/matches?leagueId={league_id}",
            f"/api/fixtures?leagueId={league_id}",
        ]

        for endpoint in endpoints:
            print(f"🔍 测试英超接口: {endpoint}")

            try:
                url = f"https://www.fotmob.com{endpoint}"
                response = await self.session.get(url, headers=self.base_headers, timeout=10)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ 成功获取英超数据! 数据类型: {type(data).__name__}")

                        if isinstance(data, dict):
                            print(f"📋 顶级键: {list(data.keys())}")

                            # 查找比赛列表
                            for key in ['matches', 'games', 'fixtures', 'data']:
                                if key in data and isinstance(data[key], list):
                                    matches = data[key]
                                    print(f"📊 在 '{key}' 中找到 {len(matches)} 场比赛")

                                    # 寻找已完场且包含详细数据的比赛
                                    finished_matches = []
                                    for i, match in enumerate(matches[:10]):  # 只检查前10场
                                        if isinstance(match, dict):
                                            match_id = match.get('id')
                                            status = match.get('status', {})
                                            is_finished = status.get('finished', False)

                                            if match_id and is_finished:
                                                home = match.get('home', {})
                                                away = match.get('away', {})
                                                home_name = home.get('name', 'Unknown')
                                                away_name = away.get('name', 'Unknown')

                                                finished_matches.append({
                                                    'id': str(match_id),
                                                    'home': home_name,
                                                    'away': away_name,
                                                    'status': status,
                                                    'raw_match': match
                                                })

                                                print(f"   🎯 找到已完场: {home_name} vs {away_name} (ID: {match_id})")

                                    return finished_matches[:3]  # 返回前3场已完场比赛

                        elif isinstance(data, list) and data:
                            print(f"📊 比赛列表，长度: {len(data)}")

                            # 查找已完场比赛
                            finished_matches = []
                            for i, match in enumerate(data[:10]):
                                if isinstance(match, dict):
                                    match_id = match.get('id')
                                    status = match.get('status', {})
                                    is_finished = status.get('finished', False)

                                    if match_id and is_finished:
                                        home = match.get('home', {})
                                        away = match.get('away', {})
                                        home_name = home.get('name', 'Unknown')
                                        away_name = away.get('name', 'Unknown')

                                        finished_matches.append({
                                            'id': str(match_id),
                                            'home': home_name,
                                            'away': away_name,
                                            'status': status,
                                            'raw_match': match
                                        })

                                        print(f"   🎯 找到已完场: {home_name} vs {away_name} (ID: {match_id})")

                            return finished_matches[:3]

                    except Exception as e:
                        print(f"❌ JSON解析错误: {e}")

                elif response.status_code == 401:
                    print(f"❌ 需要认证: {endpoint}")
                elif response.status_code == 404:
                    print(f"❌ 接口不存在: {endpoint}")
                else:
                    print(f"❌ 请求失败，状态码: {response.status_code}")

            except Exception as e:
                print(f"❌ 请求异常: {e}")

        return []

    async def test_premier_league_match_ids(self):
        """测试一些可能的英超比赛ID范围"""
        # 英超比赛ID通常在特定范围内
        # 这里我们测试一些可能的ID范围
        test_ids = [
            # 基于我们之前探测的ID格式
            "4017263", "4017264", "4017265", "4017266", "4017267", "4017268",
            # 另一些可能的ID格式
            "3785121", "3785122", "3785123", "3785124", "3785125",
            # 更大的数字，可能是较新的比赛
            "4050000", "4050001", "4050002", "4050003", "4050004",
        ]

        await self.init_session()
        valid_matches = []

        print("🔍 测试潜在的英超比赛ID...")

        for match_id in test_ids:
            try:
                url = f"https://www.fotmob.com/api/match?id={match_id}"
                response = await self.session.get(url, headers=self.base_headers, timeout=5)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            home = data.get('home', {})
                            away = data.get('away', {})
                            status = data.get('status', {})

                            if home and away:
                                home_name = home.get('name', '')
                                away_name = away.get('name', '')
                                is_finished = status.get('finished', False)

                                # 简单检查是否可能是英超比赛（基于球队名称）
                                premier_league_teams = [
                                    'Manchester United', 'Manchester City', 'Chelsea', 'Arsenal', 'Liverpool',
                                    'Tottenham', 'Leicester', 'Everton', 'West Ham', 'Newcastle',
                                    'Aston Villa', 'Crystal Palace', 'Wolves', 'Leeds', 'Southampton',
                                    'Brighton', 'Burnley', 'Brentford', 'Fulham', 'Nottingham Forest'
                                ]

                                is_premier = (any(team.lower() in home_name.lower() for team in premier_league_teams) or
                                             any(team.lower() in away_name.lower() for team in premier_league_teams))

                                if is_premier or is_finished:  # 如果是英超球队或已完场
                                    valid_matches.append({
                                        'id': match_id,
                                        'home': home_name,
                                        'away': away_name,
                                        'is_premier': is_premier,
                                        'is_finished': is_finished,
                                        'data_size': len(str(data))
                                    })

                                    status_text = "英超" if is_premier else "其他"
                                    finished_text = "已完场" if is_finished else "未完场"
                                    print(f"✅ 找到比赛: {home_name} vs {away_name} ({status_text}, {finished_text}) (ID: {match_id})")

                                    if is_premier and is_finished and len(valid_matches) >= 3:
                                        break

                    except Exception:
                        pass

                elif response.status_code == 502:
                    print(f"❌ 服务器错误: {match_id}")
                else:
                    print(f"❌ 其他错误: {match_id} - {response.status_code}")

            except Exception as e:
                print(f"❌ 请求异常: {match_id} - {e}")

        return valid_matches


async def main():
    """主函数"""
    print("🚀 开始寻找英超比赛...\n")

    finder = PremierLeagueMatchFinder()

    try:
        # 方法1: 通过联赛接口获取
        print("📊 方法1: 通过英超联赛接口")
        print("-" * 50)
        league_matches = await finder.get_league_matches()

        if league_matches:
            print(f"\n✅ 找到 {len(league_matches)} 场英超比赛!")
            for i, match in enumerate(league_matches, 1):
                print(f"   {i}. {match['home']} vs {match['away']} (ID: {match['id']})")
        else:
            print("\n❌ 方法1失败，尝试方法2...")

            # 方法2: 测试可能的比赛ID
            print("\n🔍 方法2: 测试可能的比赛ID")
            print("-" * 50)
            test_matches = await finder.test_premier_league_match_ids()

            if test_matches:
                print(f"\n✅ 找到 {len(test_matches)} 场有效比赛!")
                for i, match in enumerate(test_matches, 1):
                    status = []
                    if match['is_premier']:
                        status.append("英超")
                    if match['is_finished']:
                        status.append("已完场")
                    status_text = ", ".join(status) if status else "其他"

                    print(f"   {i}. {match['home']} vs {match['away']} ({status_text}) (ID: {match['id']})")

                # 优先选择已完场的英超比赛
                finished_premier = [m for m in test_matches if m['is_premier'] and m['is_finished']]
                if finished_premier:
                    print(f"\n🎯 推荐测试比赛: {finished_premier[0]['home']} vs {finished_premier[0]['away']} (ID: {finished_premier[0]['id']})")
                    return finished_premier[0]['id']
                elif test_matches:
                    print(f"\n🎯 推荐测试比赛: {test_matches[0]['home']} vs {test_matches[0]['away']} (ID: {test_matches[0]['id']})")
                    return test_matches[0]['id']

        print("\n❌ 未能找到合适的英超比赛")
        return None

    except Exception as e:
        print(f"\n❌ 搜索过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    match_id = asyncio.run(main())
    if match_id:
        print(f"\n🎉 找到比赛ID: {match_id}")
    else:
        print("\n⚠️ 未找到合适的比赛ID")
