#!/usr/bin/env python3
"""
分析Next.js数据结构
Analyze Next.js Data Structure

专门用于分析FotMob页面的实际Next.js数据结构
"""

import asyncio
import sys
import json
import re
from pathlib import Path

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

from src.collectors.html_fotmob_collector import HTMLFotMobCollector

def extract_nextjs_data_from_html(html: str) -> dict:
    """从HTML中提取Next.js数据"""
    try:
        pattern = r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL)

        if not matches:
            return {"error": "No __NEXT_DATA__ found"}

        nextjs_data_str = matches[0].strip()
        try:
            nextjs_data = json.loads(nextjs_data_str)
            return {"success": True, "data": nextjs_data}
        except json.JSONDecodeError as e:
            return {"error": f"JSON decode error: {e}", "preview": nextjs_data_str[:500]}

    except Exception as e:
        return {"error": f"Extraction error: {e}"}

def analyze_data_structure(data: dict, path: str = "") -> None:
    """递归分析数据结构"""
    if isinstance(data, dict):
        print(f"{'  ' * len(path.split('.'))}📁 Dictionary: {path or 'root'} ({len(data)} keys)")
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            # 检查是否包含比赛相关关键字段
            if any(keyword in key.lower() for keyword in ['match', 'content', 'data', 'props', 'state']):
                print(f"{'  ' * (len(path.split('.')) + 1)}🔑 Key: {key} (type: {type(value).__name__})")

                if isinstance(value, dict):
                    if len(value) <= 10:  # 小字典直接显示
                        print(f"{'  ' * (len(path.split('.')) + 2)}📋 Content: {list(value.keys())}")
                    else:
                        print(f"{'  ' * (len(path.split('.')) + 2)}📋 Content: {len(value)} keys")
                        # 显示前5个键
                        first_keys = list(value.keys())[:5]
                        print(f"{'  ' * (len(path.split('.')) + 2)}📋 First 5 keys: {first_keys}...")

                    # 递归分析重要的数据结构
                    if key.lower() in ['content', 'data', 'state', 'matchfacts', 'stats', 'lineups']:
                        analyze_data_structure(value, current_path)

                elif isinstance(value, list):
                    print(f"{'  ' * (len(path.split('.')) + 2)}📋 Array: {len(value)} items")
                    if value and isinstance(value[0], dict):
                        print(f"{'  ' * (len(path.split('.')) + 2)}📋 First item keys: {list(value[0].keys())[:5]}...")

            else:
                # 对于非关键字段，只显示基本信息
                if isinstance(value, dict):
                    print(f"{'  ' * (len(path.split('.')) + 1)}📁 {key}: Dictionary ({len(value)} keys)")
                elif isinstance(value, list):
                    print(f"{'  ' * (len(path.split('.')) + 1)}📄 {key}: Array ({len(value)} items)")
                else:
                    print(f"{'  ' * (len(path.split('.')) + 1)}💎 {key}: {type(value).__name__}")

    elif isinstance(data, list):
        print(f"{'  ' * len(path.split('.'))}📄 Array: {path} ({len(data)} items)")
        if data:
            print(f"{'  ' * (len(path.split('.')) + 1)}📋 First item type: {type(data[0]).__name__}")
            if isinstance(data[0], dict):
                print(f"{'  ' * (len(path.split('.')) + 1)}📋 First item keys: {list(data[0].keys())[:5]}...")
    else:
        print(f"{'  ' * len(path.split('.'))}💎 {path}: {type(data).__name__} = {str(data)[:100]}")

def search_for_match_data(data: dict, search_path: str = "") -> list:
    """搜索包含比赛数据的路径"""
    results = []

    # 比赛数据的关键字段
    match_keywords = [
        'matchfacts', 'stats', 'lineups', 'odds', 'shotmap', 'xg', 'expected_goals',
        'hometeam', 'awayteam', 'score', 'minute', 'possession', 'shots'
    ]

    def recursive_search(obj, current_path: str):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{current_path}.{key}" if current_path else key

                # 检查当前键是否包含比赛数据关键字
                if any(keyword in key.lower() for keyword in match_keywords):
                    results.append({
                        "path": new_path,
                        "key": key,
                        "type": type(value).__name__,
                        "size": len(str(value)) if not isinstance(value, (list, dict)) else
                                len(value) if isinstance(value, (list, dict)) else 0,
                        "preview": str(value)[:200] if not isinstance(value, (list, dict)) else None
                    })

                # 递归搜索
                recursive_search(value, new_path)

        elif isinstance(obj, list) and obj:
            # 搜索数组中的对象
            for i, item in enumerate(obj):
                if isinstance(item, dict):
                    recursive_search(item, f"{current_path}[{i}]")

    recursive_search(data, search_path)
    return results

async def analyze_match_nextjs(match_id: str) -> None:
    """分析特定比赛的Next.js数据结构"""
    print(f"🔍 分析比赛 {match_id} 的Next.js数据结构")
    print("=" * 80)

    collector = HTMLFotMobCollector(enable_stealth=True, enable_proxy=False)

    try:
        await collector.initialize()

        # 获取HTML
        url = f"https://www.fotmob.com/match/{match_id}"
        session = collector.session_manager.session
        headers = collector.session_manager.current_headers or {}

        print(f"🔄 获取页面: {url}")
        response = session.get(url, headers=headers, timeout=30)

        print(f"✅ 响应状态: {response.status_code}")
        print(f"✅ 响应大小: {len(response.text):,} 字符")

        # 提取Next.js数据
        print("\n🔍 提取Next.js数据...")
        extraction_result = extract_nextjs_data_from_html(response.text)

        if "error" in extraction_result:
            print(f"❌ 数据提取失败: {extraction_result['error']}")
            if "preview" in extraction_result:
                print(f"📋 数据预览: {extraction_result['preview']}")
            return

        nextjs_data = extraction_result["data"]
        print("✅ Next.js数据提取成功!")

        # 分析整体数据结构
        print("\n📊 Next.js数据结构分析:")
        print("-" * 60)
        analyze_data_structure(nextjs_data)

        # 搜索比赛数据
        print("\n🎯 比赛数据搜索结果:")
        print("-" * 60)
        match_data_paths = search_for_match_data(nextjs_data)

        if match_data_paths:
            print(f"✅ 找到 {len(match_data_paths)} 个可能包含比赛数据的路径:")
            for i, result in enumerate(match_data_paths[:10]):  # 只显示前10个
                print(f"\n{i+1}. 📍 路径: {result['path']}")
                print(f"   🔑 键名: {result['key']}")
                print(f"   📝 类型: {result['type']}")
                print(f"   📏 大小: {result['size']}")
                if result['preview']:
                    print(f"   👁️ 预览: {result['preview']}...")
        else:
            print("❌ 未找到明显的比赛数据字段")

        # 特别检查props.pageProps结构
        print("\n🔍 详细检查props.pageProps结构:")
        print("-" * 60)
        props = nextjs_data.get('props', {})
        page_props = props.get('pageProps', {})

        if page_props:
            print(f"✅ pageProps包含 {len(page_props)} 个键: {list(page_props.keys())}")

            # 检查每个键的详细信息
            for key, value in page_props.items():
                print(f"\n📋 键: {key}")
                if isinstance(value, dict):
                    print(f"   类型: Dictionary ({len(value)} 键)")
                    print(f"   内容: {list(value.keys())[:10]}...")
                elif isinstance(value, list):
                    print(f"   类型: Array ({len(value)} 项)")
                    if value and isinstance(value[0], dict):
                        print(f"   首项键: {list(value[0].keys())[:5]}...")
                else:
                    print(f"   类型: {type(value).__name__}")
                    print(f"   值: {str(value)[:100]}...")
        else:
            print("❌ pageProps为空或不存在")

        # 保存完整的Next.js数据用于进一步分析
        timestamp = asyncio.get_event_loop().time()
        filename = f"logs/nextjs_data_{match_id}_{int(timestamp)}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(nextjs_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 完整Next.js数据已保存: {filename}")

    except Exception as e:
        print(f"❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await collector.close()

async def main():
    """主函数"""
    print("🔍 Next.js数据结构分析工具")
    print("=" * 80)

    # 从日志中提取的失败比赛ID
    failed_match_ids = [
        "4000125",  # 404页面
        "4193904",  # 200页面
    ]

    for match_id in failed_match_ids:
        await analyze_match_nextjs(match_id)
        print("\n" + "="*80)
        print("\n")

if __name__ == "__main__":
    asyncio.run(main())
