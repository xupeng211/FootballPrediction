#!/usr/bin/env python3
"""
OddsPortal 解析器测试脚本
Test script for OddsPortal parser

使用生成的样本文件测试解析器功能。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from fetchers.parsers.odds_parser import OddsParser


def test_odds_parser():
    """测试赔率解析器"""

    # 读取样本文件
    sample_file = Path(__file__).parent / "oddsportal_sample.html"
    with open(sample_file, encoding='utf-8') as f:
        html_content = f.read()

    # 创建解析器实例
    parser = OddsParser()

    # 解析HTML内容
    print("🔍 开始解析HTML内容...")
    parsed_odds = parser.parse_match_page(html_content)

    print(f"📊 解析结果: 找到 {len(parsed_odds)} 条赔率记录")

    # 显示解析结果
    for i, odds in enumerate(parsed_odds[:5], 1):  # 显示前5条
        print(f"\n记录 {i}:")
        print(f"  博彩公司: {odds['bookmaker']}")
        print(f"  市场类型: {odds['market']}")
        print(f"  投注选择: {odds['selection']}")
        print(f"  赔率值: {odds['odds']}")

    # 验证数据
    print("\n🔍 验证数据...")
    validated_odds = parser.validate_odds_data(parsed_odds)
    print(f"✅ 验证通过: {len(validated_odds)} 条记录")

    return validated_odds


if __name__ == "__main__":
    try:
        test_odds_parser()
        print("\n🎉 测试完成！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
