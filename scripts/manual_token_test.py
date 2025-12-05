#!/usr/bin/env python3
"""
手动Token测试
Manual Token Testing

尝试不同的token组合和API端点
"""

import requests
import json

# 多种可能的token组合
TOKEN_COMBINATIONS = [
    {
        "name": "原始tokens",
        "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=",
        "x-foo": "production:208a8f87c2cc13343f1dd8671471cf5a039dced3"
    },
    {
        "name": "简化tokens",
        "x-mas": "",
        "x-foo": ""
    }
]

# 多种可能的API端点
API_ENDPOINTS = [
    "https://www.fotmob.com/api/leagues",
    "https://www.fotmob.com/api/matches?date=20241205",
    "https://www.fotmob.com/api/matchDetails?matchId=4189362",
    "https://www.fotmob.com/api/translations",
    "https://fotmob.com/api/leagues",  # 尝试无www
]

def test_combination(tokens, endpoint):
    """测试单个组合"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.fotmob.com/",
        "Origin": "https://www.fotmob.com",
    }

    # 只在tokens存在时添加
    if tokens["x-mas"]:
        headers["x-mas"] = tokens["x-mas"]
    if tokens["x-foo"]:
        headers["x-foo"] = tokens["x-foo"]

    try:
        response = requests.get(endpoint, headers=headers, timeout=15)

        result = {
            "status_code": response.status_code,
            "content_type": response.headers.get('content-type', 'unknown'),
            "content_length": response.headers.get('content-length', '0'),
            "success": response.status_code == 200
        }

        if response.status_code == 200:
            try:
                data = response.json()
                result["data_type"] = type(data).__name__
                result["data_keys"] = list(data.keys()) if isinstance(data, dict) else []
            except:
                result["data_type"] = "text"
                result["data_preview"] = response.text[:200]

        return result

    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

def main():
    """主函数"""
    print("🔧" + "="*60)
    print("🔐 手动Token测试")
    print("👨‍💻 运维工程师 - 组合测试")
    print("="*62)

    successful_combinations = []

    for i, tokens in enumerate(TOKEN_COMBINATIONS, 1):
        print(f"\n🎯 测试Token组合 {i}: {tokens['name']}")
        print(f"   x-mas: {'有' if tokens['x-mas'] else '无'}")
        print(f"   x-foo: {'有' if tokens['x-foo'] else '无'}")

        for j, endpoint in enumerate(API_ENDPOINTS, 1):
            print(f"\n   📡 测试端点 {j}: {endpoint}")

            result = test_combination(tokens, endpoint)

            if result.get("success"):
                print(f"      🎉 SUCCESS! 状态码: {result['status_code']}")
                print(f"      数据类型: {result.get('data_type', 'unknown')}")
                print(f"      数据键: {result.get('data_keys', [])}")

                successful_combinations.append({
                    'tokens': tokens['name'],
                    'endpoint': endpoint,
                    'result': result
                })
            else:
                status = result.get('status_code', 'ERROR')
                error = result.get('error', '')
                print(f"      ❌ 失败: {status} {error}")

    # 总结结果
    print("\n" + "="*62)
    print("📊 测试总结")
    print("="*62)

    if successful_combinations:
        print(f"✅ 找到 {len(successful_combinations)} 个可用组合:")

        for i, combo in enumerate(successful_combinations, 1):
            print(f"\n{i}. {combo['tokens']} + {combo['endpoint']}")
            print(f"   状态码: {combo['result']['status_code']}")
            print(f"   数据类型: {combo['result'].get('data_type', 'unknown')}")

            # 如果找到可用的组合，生成更新代码
            if i == 1:  # 使用第一个成功的组合
                tokens_obj = next(t for t in TOKEN_COMBINATIONS if t['name'] == combo['tokens'])

                print("\n🔧 更新代码:")
                print("headers = {")
                print("    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'")
                print("    'Accept': 'application/json, text/plain, */*'")
                print("    'Referer': 'https://www.fotmob.com/'")
                print("    'Origin': 'https://www.fotmob.com'")

                if tokens_obj["x-mas"]:
                    print(f"    'x-mas': '{tokens_obj['x-mas']}',")
                if tokens_obj["x-foo"]:
                    print(f"    'x-foo': '{tokens_obj['x-foo']}',")

                print("}")

        return True
    else:
        print("❌ 没有找到可用的组合")
        print("\n🔍 可能的解决方案:")
        print("1. FotMob API结构已完全变更")
        print("2. 需要完全不同的认证方式")
        print("3. API服务暂时不可用")
        print("4. 需要更新的token获取方式")

        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
