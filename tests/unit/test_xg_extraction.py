#!/usr/bin/env python3
"""
V41.91 xG 提取测试 - 红线测试
==============================

目标: 验证 FotMob API 返回的 JSON 中能够正确提取 xG 数据
"""

import json
from pathlib import Path


def test_xg_extraction_from_fotmob_json():
    """V41.91: 测试从 FotMob JSON 提取 xG 数据"""

    # 加载测试样本
    fixture_path = Path(__file__).parent.parent / "fixtures" / "premium_match_sample.json"

    with open(fixture_path, 'r') as f:
        data = json.load(f)

    # 验证 JSON 结构
    assert 'l2_raw_json' in data, "缺少 l2_raw_json 字段"
    l2_data = data['l2_raw_json']

    assert 'content' in l2_data, "l2_raw_json 缺少 content 字段"
    content = l2_data['content']

    assert 'stats' in content, "content 缺少 stats 字段"
    stats = content['stats']

    assert 'Periods' in stats, "stats 缺少 Periods 字段"
    periods = stats['Periods']

    # 验证 All 阶段存在
    assert 'All' in periods, "Periods 缺少 All 阶段"
    all_period = periods['All']

    assert 'stats' in all_period, "All 阶段缺少 stats 字段"
    all_stats = all_period['stats']

    # 查找 xG 数据
    xg_found = False
    xg_home = None
    xg_away = None

    for stat in all_stats:
        if stat.get('key') == 'expected_goals':
            stats_data = stat.get('stats', [])
            # stats_data 是一个数组，包含多个字典
            # 找到 type="text" 的元素（实际数据，第一个元素是标题）
            for item in stats_data:
                if isinstance(item, dict) and item.get('type') == 'text':
                    values = item.get('stats', [])
                    if len(values) >= 2:
                        xg_home = float(values[0])
                        xg_away = float(values[1])
                        xg_found = True
                        break
            if xg_found:
                break

    # 验证 xG 提取
    assert xg_found, "未找到 Expected goals (xG) 数据"
    assert xg_home is not None, "主队 xG 为 None"
    assert xg_away is not None, "客队 xG 为 None"

    print(f"✅ xG 提取成功!")
    print(f"   主队 xG: {xg_home}")
    print(f"   客队 xG: {xg_away}")
    print(f"   总 xG: {xg_home + xg_away}")

    # 验证 xG 值合理
    assert xg_home >= 0, f"主队 xG 为负数: {xg_home}"
    assert xg_away >= 0, f"客队 xG 为负数: {xg_away}"
    assert xg_home + xg_away < 10, f"总 xG 异常高: {xg_home + xg_away}"


def test_coverage_level():
    """V41.91: 测试 coverageLevel 字段"""

    fixture_path = Path(__file__).parent.parent / "fixtures" / "premium_match_sample.json"

    with open(fixture_path, 'r') as f:
        data = json.load(f)

    l2_data = data['l2_raw_json']
    general = l2_data['general']

    # 验证 coverageLevel
    assert 'coverageLevel' in general, "缺少 coverageLevel 字段"
    coverage = general['coverageLevel']

    print(f"✅ coverageLevel: {coverage}")
    assert coverage == 'xG', f"coverageLevel 不是 'xG': {coverage}"


if __name__ == "__main__":
    print("=" * 60)
    print("V41.91 xG 提取测试")
    print("=" * 60)
    print()

    try:
        test_xg_extraction_from_fotmob_json()
        print()
        test_coverage_level()
        print()
        print("=" * 60)
        print("🎉 所有测试通过!")
        print("=" * 60)
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        raise
