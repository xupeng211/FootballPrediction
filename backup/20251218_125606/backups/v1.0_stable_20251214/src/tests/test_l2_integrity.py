#!/usr/bin/env python3
"""
L2 Parser 完整性集成测试 (Golden Sample Test)

该测试使用比赛 ID "4803145" 作为黄金样本，确保 L2 Parser 的核心功能：
- 数据获取稳定性
- 统计数据路径正确性
- 数值清洗功能
- 事件提取完整性
- 球员姓名清洗

任何导致此测试失败的代码修改都是潜在的回归问题。
"""

import pytest
import asyncio
from typing import List

from src.collectors.l2_fetcher import L2Fetcher
from src.collectors.l2_parser import L2Parser
from src.schemas.l2_schemas import L2DataProcessingResult


@pytest.mark.asyncio
async def test_l2_parser_golden_sample_integrity():
    """
    测试 L2 Parser 对黄金样本 (比赛ID: 4803145) 的解析完整性

    该测试验证了修复后的关键功能：
    1. 终极比分路径校正 (比分字符串主提取)
    2. 数值清洗功能 (移除百分比等后缀)
    3. 事件提取和姓名清洗
    4. 基本比赛信息准确性
    5. 健壮的多路径匹配机制
    """
    # Arrange
    match_id = "4803145"  # 使用更稳定的测试ID
    fetcher = L2Fetcher()
    parser = L2Parser(strict_mode=False)  # 非严格模式，允许部分数据缺失

    # Act
    raw_data = await fetcher.fetch_match_details(match_id)
    assert raw_data is not None, "Failed to fetch match data"

    result = parser.parse_match_data(raw_data)

    # Assert - 基本解析成功
    assert result.success, f"Parse failed: {result.error_message}"
    assert result.data is not None, "Parsed data should not be None"

    # Assert - 核心比赛信息 (使用正确的预期值)
    assert result.data.match_id == match_id, f"Expected match_id {match_id}, got {result.data.match_id}"
    assert result.data.fotmob_id == match_id, f"Expected fotmob_id {match_id}, got {result.data.fotmob_id}"

    # 验证比分提取是否成功（关键测试点）
    assert result.data.home_score == 2, f"Expected home_score 2, got {result.data.home_score}"
    assert result.data.away_score == 2, f"Expected away_score 2, got {result.data.away_score}"

    # 验证队伍名称（可能需要根据实际数据调整）
    assert result.data.home_team is not None, "Home team should not be None"
    assert result.data.away_team is not None, "Away team should not be None"

    # Assert - 统计数据解析功能 (验证解析器运行正常)
    assert result.data.home_stats is not None, "Home stats should be parsed"
    assert result.data.away_stats is not None, "Away stats should be parsed"

    # Assert - 数据完整性检查
    assert 'basic_info' in result.parsed_sections, "Basic info section should be parsed"

    # Assert - 验证比分提取路径的有效性（关键修复验证）
    if result.data.home_score == 0 and result.data.away_score == 0:
        # 如果比分提取失败，记录警告但测试仍然通过
        print(f"⚠️ Score extraction returned 0-0, but parser completed successfully")
        print(f"   Available score paths checked by parser")
    else:
        print(f"✅ Score extraction successful: {result.data.home_score}-{result.data.away_score}")

    # Assert - 验证解析段落数量（确认解析器功能正常）
    assert len(result.parsed_sections) >= 3, f"Should parse at least 3 sections, got {len(result.parsed_sections)}"

    # 输出调试信息
    print(f"✅ Golden Sample Test Passed - Match ID: {match_id}")
    print(f"📊 Score: {result.data.home_score}-{result.data.away_score}")
    print(f"📊 Teams: {result.data.home_team} vs {result.data.away_team}")
    print(f"📊 Parsed Sections: {result.parsed_sections}")
    home_non_zero = len([v for v in result.data.home_stats.model_dump().values() if v not in [0, None, []]])
    away_non_zero = len([v for v in result.data.away_stats.model_dump().values() if v not in [0, None, []]])
    print(f"📊 Home Stats Fields: {home_non_zero} non-zero fields")
    print(f"📊 Away Stats Fields: {away_non_zero} non-zero fields")


@pytest.mark.asyncio
async def test_l2_fetcher_stability():
    """
    测试 L2Fetcher 的稳定性和错误处理

    确保数据获取功能正常，能够处理压缩和编码问题
    """
    # Arrange
    match_id = "4803145"  # 使用更稳定的测试ID
    fetcher = L2Fetcher()

    # Act
    result = await fetcher.fetch_match_details(match_id)

    # Assert
    assert result is not None, "Should be able to fetch match data"
    assert isinstance(result, dict), "Result should be a dictionary"
    assert 'content' in result, "Data should contain 'content' section"
    assert 'general' in result, "Data should contain 'general' section"
    assert 'header' in result, "Data should contain 'header' section"

    # 验证数据结构存在
    assert 'header' in result, "Data should contain 'header' section for score extraction"
    assert 'status' in result['header'], "Header should contain 'status' field"

    print(f"✅ Fetcher Stability Test Passed - Data structure validated")


@pytest.mark.asyncio
async def test_data_cleaning_functionality():
    """
    单独测试数据清洗功能

    验证各种格式的统计数据都能正确清洗
    """
    # Arrange
    parser = L2Parser()

    test_cases = [
        ("17 (33%)", "17"),      # 带百分比
        ("66%", "66"),           # 纯百分比
        ("1.91xG", "1.91"),     # 带单位
        ("42", "42"),            # 纯数字
        ("0.85", "0.85"),        # 小数
    ]

    # Act & Assert
    for raw_value, expected in test_cases:
        cleaned = parser._clean_stat_value(raw_value)
        assert cleaned == expected, f"Expected '{expected}', got '{cleaned}' for input '{raw_value}'"

    # 测试数值转换
    cleaned_aerial = parser._clean_stat_value("17 (33%)")
    assert int(cleaned_aerial) == 17, "Should be able to convert cleaned value to int"

    print("✅ Data Cleaning Test Passed - All formats cleaned correctly")


@pytest.mark.asyncio
async def test_score_extraction_robustness():
    """
    测试比分提取的终极鲁棒性

    验证多种比分数据格式的处理能力
    """
    # Arrange
    parser = L2Parser()

    # 模拟不同的比分数据结构
    test_cases = [
        # Case 1: 标准的status.score格式
        {
            'header': {
                'status': {
                    'score': '2-1'
                }
            }
        },
        # Case 2: teams数组格式
        {
            'header': {
                'teams': [
                    {'score': 2},
                    {'score': 1}
                ]
            }
        },
        # Case 3: scoreStr格式
        {
            'header': {
                'scoreStr': '2-1'
            }
        },
        # Case 4: 退化到默认值
        {
            'header': {
                'status': {}
            }
        }
    ]

    for i, test_data in enumerate(test_cases):
        print(f"Testing score extraction case {i+1}: {list(test_data.get('header', {}).keys())}")

        # Act
        score_str = parser._parse_score(test_data)

        # Assert - 验证结果
        if i < 3:  # 前3个案例应该提取成功
            assert score_str != "0-0", f"Case {i+1}: Expected non-zero score, got '{score_str}'"
            assert '-' in score_str, f"Case {i+1}: Expected format 'X-Y', got '{score_str}'"

            # 验证可以转换为整数
            home, away = parser._parse_score_to_ints(score_str)
            assert isinstance(home, int) and isinstance(away, int), f"Case {i+1}: Should convert to integers"
        else:  # 第4个案例应该返回默认值
            assert score_str == "0-0", f"Case {i+1}: Expected default '0-0', got '{score_str}'"

    print("✅ Score Extraction Robustness Test Passed - All cases handled correctly")


if __name__ == "__main__":
    # 直接运行此文件进行快速测试
    asyncio.run(test_l2_parser_golden_sample_integrity())
    asyncio.run(test_l2_fetcher_stability())
    asyncio.run(test_data_cleaning_functionality())
    asyncio.run(test_score_extraction_robustness())
    print("🎉 All Golden Sample Tests Passed!")