#!/usr/bin/env python3
"""
FotMob 404页面分析
FotMob 404 Page Analysis

网页爬虫专家 - 分析404页面是否包含数据
"""

import requests
import re
import json

def analyze_404_response():
    """分析404响应"""
    print("🔍" + "="*60)
    print("🌐 FotMob 404页面分析")
    print("👨‍💻 网页爬虫专家 - 分析404响应")
    print("="*62)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # 测试404页面
    url = "https://www.fotmob.com/match/4189362"
    print(f"\n📡 请求404页面: {url}")

    try:
        response = session.get(url, timeout=15)
        print(f"   状态码: {response.status_code}")
        print(f"   内容长度: {len(response.text)}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Unknown')}")

        html = response.text

        # 检查是否真的是404页面，还是伪装的404
        print("\n🔍 分析页面内容...")

        # 检查常见404页面特征
        not_found_indicators = ['404', 'not found', 'page not found', '页面未找到']
        is_real_404 = any(indicator.lower() in html.lower() for indicator in not_found_indicators)

        if is_real_404:
            print("   ❌ 确实是404页面")
        else:
            print("   🤔 这不是标准404页面，可能是反爬虫机制")

        # 检查是否包含数据
        print("\n📊 检查隐藏的数据...")

        data_indicators = {
            'Next.js数据': '__NEXT_DATA__' in html,
            '初始状态': '__INITIAL_STATE__' in html,
            'JSON数据': '{' in html and '}' in html and '"' in html,
            'Props数据': 'props' in html.lower(),
            'Content数据': 'content' in html.lower(),
            'Match数据': 'match' in html.lower(),
            'xG数据': 'xg' in html.lower() or 'expected' in html.lower(),
        }

        print("   数据指标:")
        for indicator, found in data_indicators.items():
            status = "✅" if found else "❌"
            print(f"      {indicator}: {status}")

        # 如果包含数据，尝试提取
        if any(data_indicators.values()):
            print("\n🎯 尝试提取数据...")
            return extract_hidden_data(html)
        else:
            print("\n❌ 页面未包含可用的数据")
            return False

    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
        return False

def extract_hidden_data(html: str) -> bool:
    """提取隐藏的数据"""
    # 查找Next.js数据
    next_data_pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
    next_matches = re.findall(next_data_pattern, html, re.DOTALL)

    if next_matches:
        print(f"   ✅ 找到Next.js数据: {len(next_matches)} 个")

        for i, data in enumerate(next_matches):
            print(f"      数据块 {i+1}: 长度 {len(data)}")

            try:
                parsed_data = json.loads(data)
                print("      ✅ JSON解析成功")

                # 递归搜索比赛数据
                match_data = find_match_data_recursive(parsed_data)
                if match_data:
                    print("      🎉 找到比赛相关数据!")
                    print(f"      数据结构: {list(match_data.keys()) if isinstance(match_data, dict) else type(match_data).__name__}")

                    # 检查ML特征
                    data_str = json.dumps(match_data, ensure_ascii=False).lower()
                    features = {
                        'xg': 'xg' in data_str or 'expected' in data_str,
                        'shotmap': 'shotmap' in data_str or 'shot' in data_str,
                        'odds': 'odds' in data_str or 'betting' in data_str,
                        'lineups': 'lineups' in data_str or 'lineup' in data_str,
                    }

                    print("      ML特征检查:")
                    for feature, found in features.items():
                        status = "✅" if found else "❌"
                        print(f"         {feature}: {status}")

                    return True

            except json.JSONDecodeError as e:
                print(f"      ❌ JSON解析失败: {str(e)[:100]}")

    # 查找其他JSON模式
    json_patterns = [
        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
        r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
        r'<script[^>]*>\s*(?:var|let|const)\s+\w+\s*=\s*({.*?});\s*</script>',
    ]

    for pattern_name, pattern in [
        ("初始状态", json_patterns[0]),
        ("预加载状态", json_patterns[1]),
        ("脚本变量", json_patterns[2]),
    ]:
        try:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                print(f"   ✅ 找到{pattern_name}: {len(matches)} 个")

                for match in matches[:2]:  # 只检查前2个
                    try:
                        data = json.loads(match)
                        match_data = find_match_data_recursive(data)

                        if match_data:
                            print(f"      🎉 在{pattern_name}中找到比赛数据!")
                            return True

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"   ❌ {pattern_name}搜索失败: {e}")

    print("   ❌ 未找到可用的比赛数据")
    return False

def find_match_data_recursive(obj, max_depth=3, current_depth=0):
    """递归查找比赛数据"""
    if current_depth > max_depth:
        return None

    if isinstance(obj, dict):
        # 检查当前层是否包含比赛数据
        keys = list(obj.keys())

        # 关键指标
        match_indicators = ['match', 'fixture', 'game', 'event', 'content', 'props']
        ml_indicators = ['xg', 'expected', 'shotmap', 'odds', 'lineups', 'stats']

        if any(indicator in [k.lower() for k in keys] for indicator in match_indicators):
            if any(indicator in str(obj).lower() for indicator in ml_indicators):
                return obj  # 找到了包含ML特征的比赛数据

        # 递归检查值
        for _key, value in obj.items():
            result = find_match_data_recursive(value, max_depth, current_depth + 1)
            if result:
                return result

    elif isinstance(obj, list):
        for item in obj[:10]:  # 只检查前10个元素
            result = find_match_data_recursive(item, max_depth, current_depth + 1)
            if result:
                return result

    return None

def test_alternative_urls():
    """测试替代URL"""
    print("\n🔄 测试替代URL...")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html",
    })

    # 尝试不同的域名和路径
    test_urls = [
        "https://fotmob.com",
        "https://m.fotmob.com",  # 移动版
        "https://www.fotmob.com/en/",
        "https://www.fotmob.com/leagues",
    ]

    for url in test_urls:
        try:
            print(f"\n📡 测试: {url}")
            response = session.get(url, timeout=10)
            print(f"   状态码: {response.status_code}")

            if response.status_code == 200:
                html = response.text

                # 检查是否包含比赛链接
                match_link_pattern = r'href=["\'][^"\']*match/([^"\']+)["\']'
                matches = re.findall(match_link_pattern, html)

                if matches:
                    print(f"   ✅ 找到比赛链接: {len(matches)} 个")
                    print(f"   示例: {matches[:5]}")

                    # 返回第一个有效的比赛ID
                    return matches[0]

        except Exception as e:
            print(f"   ❌ 失败: {e}")

    return None

def main():
    """主函数"""
    print("🚀 FotMob 404页面分析启动...")

    # 分析404页面
    success = analyze_404_response()

    if not success:
        print("\n🔄 尝试其他URL...")
        match_id = test_alternative_urls()

        if match_id:
            print(f"\n🎯 找到可用的比赛ID: {match_id}")
            print("📝 建议更新HTML提取脚本使用这个ID")
            return True

    print("\n📊 最终结论:")
    if success:
        print("🎉 Plan B可行 - 可以从HTML中提取数据!")
        print("🚀 下一步: 更新采集器使用HTML解析")
    else:
        print("❌ Plan B失败 - HTML中未包含可用数据")
        print("🔍 需要考虑其他方案")

    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
