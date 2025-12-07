#!/usr/bin/env python3
"""
OddsPortal HTML 样本文件生成器
OddsPortal Sample HTML File Generator

生成最小化的 OddsPortal HTML 样本文件，用于离线测试和开发。

使用方法:
    python scripts/generate_oddsportal_sample.py

输出文件:
    tests/fixtures/oddsportal_sample.html

作者: Senior Backend Architect
创建时间: 2025-12-07
版本: 1.0.0
"""

import os
from datetime import datetime
from pathlib import Path

def generate_oddsportal_sample():
    """生成 OddsPortal HTML 样本文件"""

    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    fixtures_dir = project_root / "tests" / "fixtures"

    # 确保目录存在
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # 生成样本 HTML 内容
    sample_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OddsPortal - Match Odds</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .match-header {{ background: #f5f5f5; padding: 15px; margin-bottom: 20px; }}
        .odds-section {{ margin: 20px 0; }}
        .odds-table {{ border: 1px solid #ddd; border-collapse: collapse; width: 100%; }}
        .odds-table th, .odds-table td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        .odds-table th {{ background: #f2f2f2; font-weight: bold; }}
        .bookmaker {{ font-weight: bold; color: #333; }}
        .home-odds {{ color: #d32f2f; }}
        .draw-odds {{ color: #f57c00; }}
        .away-odds {{ color: #1976d2; }}
        .timestamp {{ font-size: 0.8em; color: #666; }}
    </style>
</head>
<body>
    <div class="match-header">
        <h1>Match: Manchester United vs Liverpool</h1>
        <p>Premier League • {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        <p>Match ID: TEST_MATCH_001</p>
    </div>

    <!-- 1X2 赔率表格 -->
    <div class="odds-section">
        <h2>1X2 Odds</h2>
        <table id="odds-data-table" class="odds-table">
            <thead>
                <tr>
                    <th>Bookmaker</th>
                    <th>Market</th>
                    <th>Selection</th>
                    <th>Odds</th>
                    <th>Last Updated</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="bookmaker">Bet365</td>
                    <td>1X2</td>
                    <td class="home-odds">Home</td>
                    <td class="home-odds">2.15</td>
                    <td class="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>
                <tr>
                    <td class="bookmaker">Bet365</td>
                    <td>1X2</td>
                    <td class="draw-odds">Draw</td>
                    <td class="draw-odds">3.40</td>
                    <td class="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>
                <tr>
                    <td class="bookmaker">Bet365</td>
                    <td>1X2</td>
                    <td class="away-odds">Away</td>
                    <td class="away-odds">3.20</td>
                    <td class="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>
                <tr>
                    <td class="bookmaker">William Hill</td>
                    <td>1X2</td>
                    <td class="home-odds">Home</td>
                    <td class="home-odds">2.10</td>
                    <td class="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>
                <tr>
                    <td class="bookmaker">William Hill</td>
                    <td>1X2</td>
                    <td class="draw-odds">Draw</td>
                    <td class="draw-odds">3.50</td>
                    <td class="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>
                <tr>
                    <td class="bookmaker">William Hill</td>
                    <td>1X2</td>
                    <td class="away-odds">Away</td>
                    <td class="away-odds">3.30</td>
                    <td class="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 亚洲让分盘赔率 -->
    <div class="odds-section">
        <h2>Asian Handicap Odds</h2>
        <table class="odds-table">
            <thead>
                <tr>
                    <th>Bookmaker</th>
                    <th>Market</th>
                    <th>Selection</th>
                    <th>Odds</th>
                    <th>Line</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="bookmaker">Betfair</td>
                    <td>Asian Handicap</td>
                    <td>Home</td>
                    <td>1.95</td>
                    <td>-0.5</td>
                </tr>
                <tr>
                    <td class="bookmaker">Betfair</td>
                    <td>Asian Handicap</td>
                    <td>Away</td>
                    <td>1.85</td>
                    <td>+0.5</td>
                </tr>
                <tr>
                    <td class="bookmaker">Paddy Power</td>
                    <td>Asian Handicap</td>
                    <td>Home</td>
                    <td>2.05</td>
                    <td>-1.0</td>
                </tr>
                <tr>
                    <td class="bookmaker">Paddy Power</td>
                    <td>Asian Handicap</td>
                    <td>Away</td>
                    <td>1.75</td>
                    <td>+1.0</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 大小球赔率 -->
    <div class="odds-section">
        <h2>Over/Under Odds</h2>
        <table class="odds-table">
            <thead>
                <tr>
                    <th>Bookmaker</th>
                    <th>Market</th>
                    <th>Selection</th>
                    <th>Odds</th>
                    <th>Line</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="bookmaker">888Sport</td>
                    <td>Over/Under</td>
                    <td>Over</td>
                    <td>1.90</td>
                    <td>2.5</td>
                </tr>
                <tr>
                    <td class="bookmaker">888Sport</td>
                    <td>Over/Under</td>
                    <td>Under</td>
                    <td>1.95</td>
                    <td>2.5</td>
                </tr>
                <tr>
                    <td class="bookmaker">Unibet</td>
                    <td>Over/Under</td>
                    <td>Over</td>
                    <td>1.85</td>
                    <td>2.0</td>
                </tr>
                <tr>
                    <td class="bookmaker">Unibet</td>
                    <td>Over/Under</td>
                    <td>Under</td>
                    <td>2.00</td>
                    <td>2.0</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 双方进球赔率 -->
    <div class="odds-section">
        <h2>Both Teams to Score Odds</h2>
        <table class="odds-table">
            <thead>
                <tr>
                    <th>Bookmaker</th>
                    <th>Market</th>
                    <th>Selection</th>
                    <th>Odds</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="bookmaker">Ladbrokes</td>
                    <td>Both Teams to Score</td>
                    <td>Yes</td>
                    <td>1.65</td>
                </tr>
                <tr>
                    <td class="bookmaker">Ladbrokes</td>
                    <td>Both Teams to Score</td>
                    <td>No</td>
                    <td>2.20</td>
                </tr>
                <tr>
                    <td class="bookmaker">Betway</td>
                    <td>Both Teams to Score</td>
                    <td>Yes</td>
                    <td>1.70</td>
                </tr>
                <tr>
                    <td class="bookmaker">Betway</td>
                    <td>Both Teams to Score</td>
                    <td>No</td>
                    <td>2.10</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 正确比分赔率 -->
    <div class="odds-section">
        <h2>Correct Score Odds</h2>
        <table class="odds-table">
            <thead>
                <tr>
                    <th>Bookmaker</th>
                    <th>Market</th>
                    <th>Selection</th>
                    <th>Odds</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="bookmaker">Bet365</td>
                    <td>Correct Score</td>
                    <td>1-0</td>
                    <td>8.50</td>
                </tr>
                <tr>
                    <td class="bookmaker">Bet365</td>
                    <td>Correct Score</td>
                    <td>1-1</td>
                    <td>6.80</td>
                </tr>
                <tr>
                    <td class="bookmaker">Bet365</td>
                    <td>Correct Score</td>
                    <td>2-1</td>
                    <td>9.00</td>
                </tr>
                <tr>
                    <td class="bookmaker">Bet365</td>
                    <td>Correct Score</td>
                    <td>0-0</td>
                    <td>10.00</td>
                </tr>
                <tr>
                    <td class="bookmaker">William Hill</td>
                    <td>Correct Score</td>
                    <td>1-0</td>
                    <td>8.00</td>
                </tr>
                <tr>
                    <td class="bookmaker">William Hill</td>
                    <td>Correct Score</td>
                    <td>2-0</td>
                    <td>12.00</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div id="odds-container">
        <div class="betting-offers">
            <div data-bookmaker="Bet365" data-market="1X2" data-selection="Home" class="odds-value">2.15</div>
            <div data-bookmaker="Bet365" data-market="1X2" data-selection="Draw" class="odds-value">3.40</div>
            <div data-bookmaker="Bet365" data-market="1X2" data-selection="Away" class="odds-value">3.20</div>
            <div data-bookmaker="William Hill" data-market="Asian Handicap" data-selection="Home" class="odds-value">1.95</div>
            <div data-bookmaker="William Hill" data-market="Asian Handicap" data-selection="Away" class="odds-value">1.85</div>
            <div data-bookmaker="Betfair" data-market="Over/Under" data-selection="Over" class="odds-value">1.90</div>
            <div data-bookmaker="Betfair" data-market="Over/Under" data-selection="Under" class="odds-value">1.95</div>
        </div>
    </div>

    <div class="match-info">
        <h3>Additional Information</h3>
        <p>Stadium: Old Trafford</p>
        <p>Weather: Clear</p>
        <p>Attendance: 74,000</p>
        <p>Referee: Michael Oliver</p>
    </div>

    <footer>
        <p><small>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} for testing purposes</small></p>
        <p><small>This is a sample HTML file for OddsPortal parser testing</small></p>
    </footer>
</body>
</html>"""

    # 写入文件
    output_file = fixtures_dir / "oddsportal_sample.html"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sample_html)

    print(f"✅ OddsPortal HTML 样本文件已生成: {output_file}")
    print(f"📄 文件大小: {output_file.stat().st_size} bytes")
    print(f"🎯 文件用途: 用于离线测试 OddsPortalFetcher 和 OddsParser")

    return output_file


def generate_parser_test_script():
    """生成解析器测试脚本"""

    project_root = Path(__file__).parent.parent
    test_script = project_root / "tests" / "fixtures" / "test_odds_parser.py"

    test_content = '''#!/usr/bin/env python3
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
    with open(sample_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 创建解析器实例
    parser = OddsParser()

    # 解析HTML内容
    print("🔍 开始解析HTML内容...")
    parsed_odds = parser.parse_match_page(html_content)

    print(f"📊 解析结果: 找到 {len(parsed_odds)} 条赔率记录")

    # 显示解析结果
    for i, odds in enumerate(parsed_odds[:5], 1):  # 显示前5条
        print(f"\\n记录 {i}:")
        print(f"  博彩公司: {odds['bookmaker']}")
        print(f"  市场类型: {odds['market']}")
        print(f"  投注选择: {odds['selection']}")
        print(f"  赔率值: {odds['odds']}")

    # 验证数据
    print("\\n🔍 验证数据...")
    validated_odds = parser.validate_odds_data(parsed_odds)
    print(f"✅ 验证通过: {len(validated_odds)} 条记录")

    return validated_odds


if __name__ == "__main__":
    try:
        test_odds_parser()
        print("\\n🎉 测试完成！")
    except Exception as e:
        print(f"\\n❌ 测试失败: {e}")
        sys.exit(1)
'''

    with open(test_script, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print(f"✅ 解析器测试脚本已生成: {test_script}")
    return test_script


if __name__ == "__main__":
    print("🚀 开始生成 OddsPortal 测试文件...")

    # 生成 HTML 样本文件
    html_file = generate_oddsportal_sample()

    # 生成测试脚本
    test_script = generate_parser_test_script()

    print("\\n📋 生成的文件:")
    print(f"  1. HTML 样本: {html_file}")
    print(f"  2. 测试脚本: {test_script}")

    print("\\n🔧 使用方法:")
    print(f"  python {test_script}")

    print("\\n✅ 所有文件生成完成！")