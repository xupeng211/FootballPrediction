#!/usr/bin/env python3
"""
FotMob 高级详情接口探测
测试多种方法获取比赛详情数据
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from curl_cffi.requests import AsyncSession


class AdvancedFotMobDetailsProbe:
    """高级FotMob详情探测"""

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
            # 访问主页建立会话
            await self.session.get("https://www.fotmob.com/")

    async def test_match_details_direct(self, match_id):
        """直接测试 matchDetails 接口"""
        print(f"🔍 测试 /api/matchDetails?matchId={match_id}")

        await self.init_session()

        # 方法1: 不带任何特殊头的直接请求
        try:
            url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
            response = await self.session.get(url, headers=self.base_headers, timeout=10)

            print(f"   状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print("   ✅ 成功获取JSON数据!")
                    return data
                except json.JSONDecodeError:
                    print("   ❌ 响应不是有效的JSON")
                    print(f"   内容预览: {response.text[:200]}")
            else:
                print(f"   ❌ 请求失败，状态码: {response.status_code}")
                if response.text:
                    print(f"   错误信息: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ 请求异常: {e}")

        return None

    async def test_alternative_endpoints(self, match_id):
        """测试其他可能的端点"""
        endpoints = [
            f"/api/matchDetails?matchId={match_id}",
            f"/api/match/{match_id}",
            f"/api/match?id={match_id}",
            f"/api/gameDetails?matchId={match_id}",
            f"/api/eventDetails?matchId={match_id}",
            f"/api/data/matchDetails?matchId={match_id}",
        ]

        await self.init_session()

        for endpoint in endpoints:
            print(f"🔍 测试端点: {endpoint}")
            try:
                url = f"https://www.fotmob.com{endpoint}"
                response = await self.session.get(url, headers=self.base_headers, timeout=8)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   ✅ 成功! 数据键: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")

                        # 检查是否包含我们想要的数据
                        if isinstance(data, dict):
                            if 'content' in data:
                                content = data['content']
                                if isinstance(content, dict):
                                    if 'stats' in content:
                                        print("   🎯 发现统计数据!")
                                    if 'lineup' in content:
                                        print("   👥 发现阵容数据!")

                        return data
                    except json.JSONDecodeError:
                        print("   ❌ 非JSON响应")
                else:
                    print(f"   ❌ 状态码: {response.status_code}")

            except Exception as e:
                print(f"   ❌ 异常: {e}")

        return None

    async def test_with_known_matches(self):
        """测试一些已知的重要比赛ID"""
        # 一些可能的英超比赛ID（这些是示例，实际可能需要更新）
        known_matches = [
            "4721983",  # 从audio-matches获取的ID
            "4721984",
            "4721985",
            "4721986",
            "4721987",
            # 一些常见的英超比赛格式
            "4017263",  # 通常是英超比赛ID格式
            "4017264",
            "4000001",  # 测试格式
            "4000002",
        ]

        print("🏆 测试已知比赛ID...")

        for i, match_id in enumerate(known_matches):
            print(f"\n--- 测试比赛 {i+1}/{len(known_matches)} (ID: {match_id}) ---")

            # 先测试直接端点
            data = await self.test_match_details_direct(match_id)

            if not data:
                # 测试其他端点
                data = await self.test_alternative_endpoints(match_id)

            if data:
                print(f"✅ 比赛 {match_id} 成功获取数据!")

                # 分析数据结构
                if isinstance(data, dict):
                    print(f"📊 数据键: {list(data.keys())}")

                    # 寻找关键数据
                    content = data.get('content', {})
                    if isinstance(content, dict):
                        if 'stats' in content:
                            print("🎯 包含统计数据!")
                        if 'lineup' in content:
                            print("👥 包含阵容数据!")

                # 保存第一个成功的数据样本
                if i == 0:
                    with open(f"successful_match_details_{match_id}.json", 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"💾 数据已保存到 successful_match_details_{match_id}.json")

                return match_id, data
            else:
                print(f"❌ 比赛 {match_id} 无法获取数据")

        return None, None

    async def analyze_successful_data(self, data):
        """分析成功获取的数据"""
        print("\n🔬 分析数据结构...")

        if not isinstance(data, dict):
            print("❌ 数据不是字典格式")
            return

        print(f"📋 顶级键: {list(data.keys())}")

        # 递归分析寻找xG和阵容数据
        def find_key_recursive(obj, key_path=""):
            found = []

            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{key_path}.{key}" if key_path else key

                    # 检查关键键
                    if key.lower() in ['xg', 'expectedgoals', 'expected_goals', 'stats', 'lineup']:
                        found.append((current_path, type(value).__name__))

                    # 递归搜索
                    if isinstance(value, (dict, list)) and len(str(value)) < 10000:  # 限制递归深度
                        found.extend(find_key_recursive(value, current_path))

            elif isinstance(obj, list) and len(obj) > 0:
                # 检查列表中的前几个元素
                for i, item in enumerate(obj[:3]):  # 只检查前3个元素
                    if isinstance(item, (dict, list)):
                        found.extend(find_key_recursive(item, f"{key_path}[{i}]"))

            return found

        found_keys = find_key_recursive(data)
        if found_keys:
            print("🔍 发现相关键:")
            for path, type_name in found_keys:
                print(f"   {path} ({type_name})")

        # 特别检查content结构
        content = data.get('content', {})
        if isinstance(content, dict):
            print("\n📊 Content分析:")
            print(f"   键: {list(content.keys())}")

            # 统计数据
            stats = content.get('stats', {})
            if stats:
                print(f"   📈 Stats类型: {type(stats).__name__}")
                if isinstance(stats, dict):
                    print(f"   📈 Stats键: {list(stats.keys())}")
                    # 寻找xG相关
                    for key in stats.keys():
                        if 'xg' in key.lower() or 'expected' in key.lower():
                            print(f"      🔥 xG相关: {key}")

            # 阵容数据
            lineup = content.get('lineup', {})
            if lineup:
                print(f"   👥 Lineup类型: {type(lineup).__name__}")
                if isinstance(lineup, dict):
                    print(f"   👥 Lineup键: {list(lineup.keys())}")


async def main():
    """主函数"""
    print("🚀 开始高级FotMob详情接口探测...")

    probe = AdvancedFotMobDetailsProbe()

    # 测试已知比赛
    successful_match_id, successful_data = await probe.test_with_known_matches()

    if successful_data:
        print(f"\n🎉 成功! 比赛ID: {successful_match_id}")

        # 分析数据
        await probe.analyze_successful_data(successful_data)

        return successful_match_id, successful_data
    else:
        print("\n❌ 未能成功获取任何比赛详情")
        return None, None


if __name__ == "__main__":
    asyncio.run(main())
