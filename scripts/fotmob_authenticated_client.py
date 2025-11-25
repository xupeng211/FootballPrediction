#!/usr/bin/env python3
"""
FotMob 认证客户端
基于破解的认证机制访问 FotMob API
"""

import asyncio
import json
import base64
import time
import hashlib
from datetime import datetime
from urllib.parse import quote

try:
    from curl_cffi.requests import AsyncSession
except ImportError:
    print("❌ 错误: curl_cffi 库未安装")
    print("请运行: docker-compose exec app pip install curl_cffi")
    exit(1)


class FotMobAuthenticatedClient:
    """FotMob 认证客户端"""

    def __init__(self):
        self.session = None
        self.client_version = "production:208a8f87c2cc13343f1dd8671471cf5a039dced3"

        # 基础 Headers
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
        }

    async def initialize_session(self):
        """初始化会话"""
        print("🔧 初始化会话...")
        self.session = AsyncSession(impersonate="chrome120")

        # 访问主页建立会话
        home_response = await self.session.get("https://www.fotmob.com/")
        print(f"主页状态码: {home_response.status_code}")

    def generate_x_mas_header(self, api_url):
        """
        生成 x-mas 认证头
        基于逆向分析的签名算法
        """
        # 生成当前时间戳
        timestamp = int(time.time() * 1000)

        # 构建请求体数据
        body_data = {
            "url": api_url,
            "code": timestamp,
            "foo": self.client_version
        }

        # 生成签名的几种尝试
        signature_candidates = self._generate_signatures(body_data, api_url)

        # 选择最可能的签名（这里先用第一个候选，实际中可能需要调整）
        signature = signature_candidates[0]

        # 构建完整的 x-mas 头
        x_mas_data = {
            "body": body_data,
            "signature": signature
        }

        # 编码为 Base64
        x_mas_str = json.dumps(x_mas_data, separators=(',', ':'))
        x_mas_encoded = base64.b64encode(x_mas_str.encode()).decode()

        return x_mas_encoded

    def _generate_signatures(self, body_data, api_url):
        """生成可能的签名候选"""
        signatures = []

        # 方法1: 使用已知的有效签名模式（基于逆向工程）
        # 这里我们使用从样本中观察到的模式
        base_str = f"{api_url}{body_data['code']}{self.client_version}"
        signature = hashlib.md5(base_str.encode()).hexdigest().upper()[:16]
        signatures.append(signature)

        # 方法2: JSON 字符串哈希
        json_str = json.dumps(body_data, separators=(',', ':'), sort_keys=True)
        signature2 = hashlib.sha1(json_str.encode()).hexdigest().upper()[:16]
        signatures.append(signature2)

        # 方法3: 时间戳哈希
        signature3 = hashlib.md5(str(body_data['code']).encode()).hexdigest().upper()[:16]
        signatures.append(signature3)

        return signatures

    async def make_authenticated_request(self, api_url, use_known_signature=False):
        """
        发送认证请求
        """
        if not self.session:
            await self.initialize_session()

        # 生成认证头
        if use_known_signature:
            # 使用已知的有效签名（从您的样本中）
            known_x_mas = "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0="
            headers = {**self.base_headers, "x-mas": known_x_mas}
        else:
            # 动态生成的签名
            x_mas = self.generate_x_mas_header(api_url)
            headers = {**self.base_headers, "x-mas": x_mas}

        print(f"📡 请求 URL: https://www.fotmob.com{api_url}")
        print(f"🔐 使用 x-mas: {x_mas if not use_known_signature else '已知有效签名'}")

        try:
            response = await self.session.get(
                f"https://www.fotmob.com{api_url}",
                headers=headers,
                timeout=15
            )

            print(f"📊 状态码: {response.status_code}")
            print(f"📋 响应头: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ 成功! 数据类型: {type(data).__name__}")

                    if isinstance(data, dict):
                        print("🏗️ 数据结构:")
                        for key, value in list(data.items())[:5]:
                            if isinstance(value, list):
                                print(f"  {key}: list[{len(value)}]")
                            elif isinstance(value, dict):
                                print(f"  {key}: dict[{len(value)}]")
                            else:
                                print(f"  {key}: {type(value).__name__}")

                    # 显示数据预览
                    json_str = json.dumps(data, ensure_ascii=False)
                    print(f"📄 数据长度: {len(json_str)} 字符")
                    print(f"📝 数据前100字符: {json_str[:100]}...")

                    return data

                except json.JSONDecodeError:
                    print("❌ JSON 解析失败")
                    print(f"📄 原始响应: {response.text[:200]}...")
                    return None

            elif response.status_code == 401:
                print("🚫 认证失败")
                print(f"📄 响应: {response.text[:100]}...")
                return None

            elif response.status_code == 404:
                print("❌ 端点不存在")
                return None

            else:
                print(f"⚠️ 其他状态码: {response.status_code}")
                print(f"📄 响应: {response.text[:100]}...")
                return None

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None

    async def get_audio_matches(self):
        """获取音频比赛数据，提取 matchId 列表"""
        print("\n🎵 获取音频比赛数据...")

        result = await self.make_authenticated_request("/api/data/audio-matches", use_known_signature=True)

        if result and isinstance(result, list):
            # 提取 matchId 列表
            match_ids = []
            for item in result:
                if isinstance(item, dict) and 'id' in item:
                    match_ids.append(item['id'])

            print(f"✅ 成功获取 {len(match_ids)} 个比赛 ID")
            print(f"📋 前 10 个 ID: {match_ids[:10]}")
            return match_ids

        print("❌ 无法获取音频比赛数据")
        return []

    async def fetch_match_details(self, match_id, use_signature=True):
        """获取单场比赛详情"""
        api_url = f"/api/matchDetails?matchId={match_id}"

        print(f"\n🏈 获取比赛详情 (ID: {match_id})")
        print(f"🔗 URL: https://www.fotmob.com{api_url}")

        # 先尝试带签名
        if use_signature:
            print("🔐 尝试带 x-mas 签名请求...")
            result = await self.make_authenticated_request(api_url, use_known_signature=False)
            if result:
                return result

        # 如果签名失败，尝试不带签名（仅 TLS 伪装）
        print("🔓 尝试不带签名请求（仅 TLS 伪装）...")

        if not self.session:
            await self.initialize_session()

        headers = self.base_headers.copy()

        try:
            response = await self.session.get(
                f"https://www.fotmob.com{api_url}",
                headers=headers,
                timeout=15
            )

            print(f"📊 无签名请求状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ 无签名请求成功!")

                    # 显示数据结构
                    if isinstance(data, dict):
                        print("🏗️ 详情数据结构:")
                        for key, value in data.items():
                            if isinstance(value, list):
                                print(f"  {key}: list[{len(value)}]")
                            elif isinstance(value, dict):
                                print(f"  {key}: dict[{len(value)}]")
                                # 显示子级的键
                                for subkey in list(value.keys())[:3]:
                                    print(f"    └─ {subkey}")
                            else:
                                print(f"  {key}: {type(value).__name__}")

                    return data

                except json.JSONDecodeError:
                    print("❌ JSON 解析失败")
                    print(f"📄 响应预览: {response.text[:100]}...")
                    return None
            else:
                print(f"⚠️ 无签名请求失败: {response.status_code}")
                if response.text:
                    print(f"📄 响应预览: {response.text[:100]}...")
                return None

        except Exception as e:
            print(f"❌ 无签名请求异常: {e}")
            return None

    async def test_id_traversal_strategy(self):
        """测试 ID 遍历策略"""
        print("\n🎯 执行 ID 遍历策略测试...")

        # Step 1: 获取 matchId 列表
        match_ids = await self.get_audio_matches()

        if not match_ids:
            print("❌ 无法获取 matchId，策略终止")
            return

        # Step 2: 测试前 3 个比赛的详情
        test_count = min(3, len(match_ids))
        successful_details = 0

        for i in range(test_count):
            match_id = match_ids[i]
            print(f"\n{'='*50}")
            print(f"📍 测试 {i+1}/{test_count}: 比赛 {match_id}")
            print(f"{'='*50}")

            # 尝试获取详情
            details = await self.fetch_match_details(match_id, use_signature=True)

            if details:
                successful_details += 1
                print(f"🎉 比赛 {match_id} 详情获取成功!")

                # 如果成功，尝试解析一些关键信息
                if isinstance(details, dict):
                    # 常见的比赛信息字段
                    for key in ['header', 'content', 'general', 'teams', 'match']:
                        if key in details:
                            print(f"  📊 找到关键字段: {key}")
                            if isinstance(details[key], dict):
                                for subkey, subvalue in details[key].items():
                                    if isinstance(subvalue, (str, int, float)):
                                        print(f"    └─ {subkey}: {subvalue}")
                                        if isinstance(subvalue, str) and len(subvalue) > 50:
                                            print(f"       (长度: {len(subvalue)})")
            else:
                print(f"❌ 比赛 {match_id} 详情获取失败")

        print(f"\n📈 策略执行总结:")
        print(f"  📋 总共测试: {test_count} 个比赛")
        print(f"  ✅ 成功获取: {successful_details} 个详情")
        print(f"  📊 成功率: {(successful_details/test_count*100):.1f}%")

        return successful_details > 0

    async def brute_force_endpoint_discovery(self, match_id):
        """广撒网式路径探测 - 寻找防护薄弱的遗留接口"""
        print(f"\n🎯 执行广撒网式路径探测 (Match ID: {match_id})")

        # 候选路径模板列表
        endpoint_templates = [
            # 标准变体
            "/api/match?id={id}",
            "/api/match/{id}",
            "/api/matches/{id}",
            "/api/matches/overview?matchId={id}",
            "/api/match/info?matchId={id}",
            "/api/match/data?matchId={id}",

            # 移动端/兼容性接口
            "/api/mobile/matchDetails?matchId={id}",
            "/api/mob/match?matchId={id}",
            "/api/app/matchDetails?matchId={id}",
            "/api/legacy/match?matchId={id}",

            # Web/特定平台接口
            "/api/web/match?matchId={id}",
            "/api/www/matchDetails?matchId={id}",
            "/api/tld/match?matchId={id}",
            "/api/desktop/match?matchId={id}",

            # 数据相关接口
            "/api/data/match?matchId={id}",
            "/api/data/matchDetails?matchId={id}",
            "/api/data/game?matchId={id}",

            # 比赛特定接口
            "/api/game?id={id}",
            "/api/gameDetails?matchId={id}",
            "/api/event?matchId={id}",
            "/api/fixture?id={id}",

            # 联赛/队伍相关 (可能包含比赛信息)
            "/api/leagues?id={id}",
            "/api/teams/match?matchId={id}",
            "/api/league/match?id={id}",

            # 直接路径 (无前缀)
            "/match/{id}",
            "/game/{id}",
            "/event/{id}",

            # 特殊格式
            "/matchDetails?matchId={id}",
            "/matchData?id={id}",
            "/api/match{id}",
            "/match{id}",
        ]

        print(f"📋 总计 {len(endpoint_templates)} 个候选端点")

        # 构造完整的 URL 列表
        urls = []
        for template in endpoint_templates:
            url = template.format(id=match_id)
            urls.append((template, url))

        print(f"🚀 开始并发探测...")

        # 分批并发探测以避免过载
        batch_size = 8
        successful_endpoints = []

        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            print(f"\n📦 测试批次 {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")

            # 并发执行 A/B 测试
            batch_results = await asyncio.gather(
                *[self._test_endpoint_ab(template, url) for template, url in batch],
                return_exceptions=True
            )

            for (template, url), result in zip(batch, batch_results):
                if isinstance(result, dict) and result.get('success'):
                    successful_endpoints.append({
                        'template': template,
                        'url': url,
                        'method': result['method'],
                        'data': result['data']
                    })
                    print(f"🎉 发现可用端点: {template} (方法: {result['method']})")

        return successful_endpoints

    async def _test_endpoint_ab(self, template, url):
        """对单个端点进行 A/B 测试"""
        result = {
            'template': template,
            'url': url,
            'success': False,
            'method': None,
            'data': None,
            'status_codes': []
        }

        # 确保 session 存在
        if not self.session:
            await self.initialize_session()

        full_url = f"https://www.fotmob.com{url}"

        # Scenario A: 带签名头
        try:
            x_mas = self.generate_x_mas_header(url)
            headers_with_sig = {**self.base_headers, "x-mas": x_mas}

            response_a = await self.session.get(full_url, headers=headers_with_sig, timeout=10)
            result['status_codes'].append(f"A:{response_a.status_code}")

            if response_a.status_code == 200:
                print(f"✅ [{template}] A测试成功 (带签名)")
                result.update({
                    'success': True,
                    'method': 'with_signature',
                    'data': await self._analyze_response(response_a, template)
                })
                return result

        except Exception as e:
            result['status_codes'].append(f"A:Error({str(e)[:20]})")

        # Scenario B: 无签名头 (仅 TLS 伪装)
        try:
            response_b = await self.session.get(full_url, headers=self.base_headers, timeout=10)
            result['status_codes'].append(f"B:{response_b.status_code}")

            if response_b.status_code == 200:
                print(f"✅ [{template}] B测试成功 (无签名)")
                result.update({
                    'success': True,
                    'method': 'no_signature',
                    'data': await self._analyze_response(response_b, template)
                })
                return result

        except Exception as e:
            result['status_codes'].append(f"B:Error({str(e)[:20]})")

        # 记录失败但有用的信息
        if any("200" in code for code in result['status_codes']):
            print(f"⚠️ [{template}] 部分成功: {result['status_codes']}")

        return result

    async def _analyze_response(self, response, template):
        """分析成功的响应"""
        try:
            content_type = response.headers.get('content-type', '').lower()

            if 'application/json' in content_type:
                data = response.json()
                return {
                    'type': 'json',
                    'preview': str(data)[:200],
                    'keys': list(data.keys()) if isinstance(data, dict) else None,
                    'structure': self._analyze_json_structure(data)
                }

            elif 'text/html' in content_type:
                text = response.text
                # 检查是否包含嵌入的 JSON 数据
                json_indicators = ['__NEXT_DATA__', 'window.__INITIAL_STATE__', 'var data']
                found_json = any(indicator in text for indicator in json_indicators)

                return {
                    'type': 'html',
                    'length': len(text),
                    'has_embedded_json': found_json,
                    'preview': text[:200]
                }

            else:
                return {
                    'type': content_type or 'unknown',
                    'length': len(response.content),
                    'preview': response.text[:100] if hasattr(response, 'text') else str(response.content)[:100]
                }

        except Exception as e:
            return {
                'type': 'error',
                'error': str(e)
            }

    def _analyze_json_structure(self, data, depth=0, max_depth=2):
        """递归分析 JSON 结构"""
        if depth >= max_depth:
            return "max_depth_reached"

        if isinstance(data, dict):
            structure = {}
            for key, value in list(data.items())[:5]:  # 只分析前5个键
                if isinstance(value, dict):
                    structure[key] = f"dict({len(value)})"
                elif isinstance(value, list):
                    structure[key] = f"list({len(value)})"
                elif isinstance(value, str):
                    structure[key] = f"str({len(value)})"
                else:
                    structure[key] = type(value).__name__
            return structure

        elif isinstance(data, list):
            if data:
                first_item = data[0]
                return f"list[{type(first_item).__name__} x {len(data)}]"
            else:
                return "list[empty]"

        else:
            return type(data).__name__

    async def run_comprehensive_discovery(self):
        """执行全面的端点发现"""
        print("\n🔍 启动全面端点发现...")

        # 获取测试用的 matchId
        match_ids = await self.get_audio_matches()

        if not match_ids:
            print("❌ 无法获取 matchId")
            return []

        # 使用第一个 matchId 进行探测
        test_match_id = match_ids[0]
        print(f"🎯 使用比赛 {test_match_id} 进行探测")

        # 执行广撒网探测
        successful_endpoints = await self.brute_force_endpoint_discovery(test_match_id)

        # 输出结果报告
        print(f"\n" + "="*80)
        print(f"📊 广撒网探测结果报告")
        print(f"="*80)

        if successful_endpoints:
            print(f"🎉 发现 {len(successful_endpoints)} 个可用端点:")

            for i, endpoint in enumerate(successful_endpoints, 1):
                print(f"\n{i}️⃣ 端点: {endpoint['template']}")
                print(f"   方法: {endpoint['method']}")
                print(f"   URL: https://www.fotmob.com{endpoint['url']}")

                data = endpoint['data']
                if data['type'] == 'json':
                    print(f"   类型: JSON 数据")
                    if data['keys']:
                        print(f"   主要字段: {data['keys'][:5]}")
                    print(f"   结构: {data['structure']}")
                    print(f"   预览: {data['preview']}...")

                elif data['type'] == 'html':
                    print(f"   类型: HTML 页面 ({data['length']} 字符)")
                    if data['has_embedded_json']:
                        print(f"   🔍 发现嵌入的 JSON 数据")
                    print(f"   预览: {data['preview']}...")

                else:
                    print(f"   类型: {data['type']}")
                    print(f"   预览: {data['preview']}...")

            return successful_endpoints

        else:
            print(f"❌ 未发现可用的端点")
            print(f"💡 建议：可能需要更高级的认证机制或不同的数据源")
            return []

    async def test_other_endpoints(self):
        """测试其他可能的 API 端点"""
        print("\n🔍 测试其他端点...")

        endpoints = [
            "/api/leagues",
            "/api/teams",
            "/api/matchesToday",
            "/api/liveMatches",
            "/api/fixtures",
            "/api/data/leagues",
            "/api/data/teams",
        ]

        for i, endpoint in enumerate(endpoints, 1):
            print(f"\n{i}️⃣ 测试端点: {endpoint}")
            await self.make_authenticated_request(endpoint)


async def main():
    """主函数"""
    print("🚀 FotMob 认证客户端 - 广撒网式端点发现")
    print("=" * 60)

    client = FotMobAuthenticatedClient()

    try:
        # 执行全面的端点发现
        successful_endpoints = await client.run_comprehensive_discovery()

        if successful_endpoints:
            print(f"\n🎉 广撒网策略成功! 发现 {len(successful_endpoints)} 个可用端点")
            print("💡 建议基于这些端点开发数据采集逻辑")
        else:
            print("\n❌ 广撒网策略失败")
            print("💡 建议：可能需要完全不同的数据源或更深入的逆向工程")

        print("\n" + "=" * 60)
        print("🎯 广撒网探测完成!")

    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n💥 程序异常: {e}")