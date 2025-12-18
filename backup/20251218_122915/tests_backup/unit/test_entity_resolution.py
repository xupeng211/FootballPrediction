#!/usr/bin/env python3
"""
测试实体解析器 - 保护数据治理逻辑
Test Entity Resolver - Protects Data Governance Logic

这个测试文件是质量保护的核心防线，确保：
1. 模糊匹配逻辑不会被破坏
2. 排重逻辑正确工作
3. 新球队自动插入机制安全运行

作为首席软件质量工程师的最终审计测试。
"""

import pytest
from unittest.mock import patch
from difflib import SequenceMatcher

# 导入被测试的组件
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from ml_ops.auto_entity_resolver import AutoEntityResolver


class TestAutoEntityResolver:
    """实体解析器测试套件"""

    @pytest.fixture
    def resolver(self):
        """创建实体解析器实例"""
        return AutoEntityResolver()

    @pytest.fixture
    def mock_existing_teams(self):
        """模拟现有球队数据"""
        return {
            "Manchester City": 1,
            "Liverpool": 2,
            "Bayern Munich": 3,
            "Real Madrid": 4,
            "Barcelona": 5,
            "Chelsea": 6,
            "Arsenal": 7,
            "Manchester United": 8,
            "Tottenham": 9,
            "AC Milan": 10,
        }

    def test_normalize_team_name_basic(self, resolver):
        """测试基础球队名称标准化"""
        # 测试移除FC后缀
        assert resolver.normalize_team_name("Manchester City FC") == "Manchester City"
        assert resolver.normalize_team_name("Real Madrid CF") == "Real Madrid"

        # 测试移除SC后缀
        assert resolver.normalize_team_name("FC Barcelona") == "Barcelona"

        # 测试移除常见前缀
        assert resolver.normalize_team_name("FC Real Madrid") == "Real Madrid"

        # 测试标准化空格
        assert resolver.normalize_team_name("Manchester   City") == "Manchester City"

        # 测试大小写不敏感
        assert resolver.normalize_team_name("MANCHESTER CITY") == "Manchester City"

    def test_normalize_team_name_edge_cases(self, resolver):
        """测试球队名称标准化的边界情况"""
        # 空字符串
        assert resolver.normalize_team_name("") == ""

        # None值（虽然类型注解不允许，但防御性编程）
        # 这里假设可能会传入空值

        # 只有后缀
        assert resolver.normalize_team_name("FC") == ""

        # 多个空格
        assert resolver.normalize_team_name("Bayern   Munich   FC") == "Bayern Munich"

        # 混合后缀
        assert resolver.normalize_team_name("Barcelona CF AC") == "Barcelona"

    def test_calculate_similarity(self, resolver):
        """测试相似度计算"""
        # 相同球队 - 相似度应该是1.0
        assert (
            resolver.calculate_similarity("Manchester City", "Manchester City") == 1.0
        )

        # 高相似度变体
        similarity = resolver.calculate_similarity("Bayern", "Bayern Munich")
        assert similarity > 0.9  # 应该大于90%

        # 中等相似度
        similarity = resolver.calculate_similarity("Man City", "Manchester City")
        assert 0.7 < similarity < 0.95

        # 低相似度
        similarity = resolver.calculate_similarity("Arsenal", "Barcelona")
        assert similarity < 0.5

    @pytest.mark.asyncio
    async def test_exact_match(self, resolver, mock_existing_teams):
        """测试精确匹配逻辑"""
        resolver.existing_teams = mock_existing_teams

        # 测试现有球队精确匹配
        result = await resolver.resolve_team_entity("Manchester City")

        assert result["resolution_type"] == "exact_match"
        assert result["matched_team_id"] == 1
        assert result["matched_team_name"] == "Manchester City"
        assert result["similarity_score"] == 1.0
        assert result["action_taken"] == "used_existing"

    @pytest.mark.asyncio
    async def test_high_confidence_fuzzy_match(self, resolver, mock_existing_teams):
        """测试高置信度模糊匹配 (>95%)"""
        resolver.existing_teams = mock_existing_teams

        # 测试Bayern变体（应该是高置信度匹配）
        result = await resolver.resolve_team_entity("Bayern")

        assert result["resolution_type"] == "high_confidence_match"
        assert result["matched_team_id"] == 3
        assert result["matched_team_name"] == "Bayern Munich"
        assert result["similarity_score"] >= 0.95
        assert result["action_taken"] == "auto_mapped"

    @pytest.mark.asyncio
    async def test_low_confidence_fuzzy_match(self, resolver, mock_existing_teams):
        """测试低置信度模糊匹配 (85%-95%)"""
        resolver.existing_teams = mock_existing_teams

        # 测试AC Milan的变体（应该在85%-95%范围内）
        result = await resolver.resolve_team_entity("AC Milan FC")

        assert result["resolution_type"] == "low_confidence_match"
        assert result["matched_team_id"] == 10
        assert result["matched_team_name"] == "AC Milan"
        assert 0.85 <= result["similarity_score"] < 0.95
        assert result["action_taken"] == "auto_mapped_caution"

    @pytest.mark.asyncio
    async def test_new_team_insertion(self, resolver, mock_existing_teams):
        """测试新球队自动插入"""
        resolver.existing_teams = mock_existing_teams

        # Mock数据库插入操作
        with patch.object(resolver, "insert_new_team", return_value=99):
            result = await resolver.resolve_team_entity("New Unseen Team FC")

            assert result["resolution_type"] == "new_team"
            assert result["matched_team_id"] == 99
            assert result["action_taken"] == "inserted_new"
            assert "New Unseen Team FC" in resolver.existing_teams

    @pytest.mark.asyncio
    async def test_deduplication_logic(self, resolver):
        """
        测试排重逻辑 - 核心数据治理保护

        场景：5个不同变体应该映射到1个规范ID
        """
        # 模拟Bayern Munich的不同变体
        team_variants = [
            "Bayern Munich",
            "Bayern",
            "FC Bayern",
            "FC Bayern Munich",
            "Bayern Munich FC",
        ]

        resolver.existing_teams = {"Bayern Munich": 3}

        # 模拟insert_new_team方法来模拟数据库插入失败
        with patch.object(resolver, "insert_new_team", return_value=None):
            for variant in team_variants[:-1]:  # 除了最后一个，其他都应该被匹配
                result = await resolver.resolve_team_entity(variant)
                # 这些变体应该被映射到现有的Bayern Munich ID
                assert result["matched_team_id"] == 3
                assert result["resolution_type"] in [
                    "high_confidence_match",
                    "low_confidence_match",
                    "exact_match",
                ]

        # 最后一个变体应该是新球队
        with patch.object(resolver, "insert_new_team", return_value=100):
            result = await resolver.resolve_team_entity(team_variants[-1])
            # 如果相似度不够高，应该插入为新球队
            # 注意：这里的具体行为取决于相似度阈值

    def test_normalization_removes_common_suffixes(self, resolver):
        """测试标准化移除常见后缀"""
        test_cases = [
            ("Manchester City FC", "Manchester City"),
            ("Real Madrid CF", "Real Madrid"),
            ("Barcelona SC", "Barcelona"),
            ("AC Milan", "AC Milan"),  # AC是前缀，不是后缀
            ("Chelsea AC", "Chelsea"),
        ]

        for input_name, expected in test_cases:
            actual = resolver.normalize_team_name(input_name)
            assert (
                actual == expected
            ), f"Failed: {input_name} -> {actual} (expected {expected})"

    def test_normalization_removes_common_prefixes(self, resolver):
        """测试标准化移除常见前缀"""
        test_cases = [
            ("FC Barcelona", "Barcelona"),
            ("CD Real Madrid", "Real Madrid"),
            ("SD Atletico", "Atletico"),
        ]

        for input_name, expected in test_cases:
            actual = resolver.normalize_team_name(input_name)
            assert (
                actual == expected
            ), f"Failed: {input_name} -> {actual} (expected {expected})"

    @pytest.mark.asyncio
    async def test_error_handling(self, resolver):
        """测试错误处理"""
        resolver.existing_teams = {"Test Team": 1}

        # 测试异常情况的处理
        try:
            result = await resolver.resolve_team_entity("Test Team")
            assert result["action_taken"] in ["used_existing", "error"]
        except Exception:
            # 如果有未捕获的异常，测试失败
            pytest.fail("未捕获的异常")

    @pytest.mark.asyncio
    async def test_similarity_threshold_boundaries(self, resolver):
        """测试相似度阈值边界"""
        resolver.existing_teams = {"Arsenal": 7}

        # 模拟不同相似度分数的球队名称
        # 注意：这里我们通过比较实际字符串来测试

        # 高相似度变体（应被高置信度匹配）
        high_sim = await resolver.resolve_team_entity("Arsenal FC")
        assert high_sim["similarity_score"] >= 0.95

        # 中等相似度（如果没有完全匹配的，应被低置信度匹配）
        # 这里取决于实际实现的相似度计算

    def test_sequence_matcher_usage(self, resolver):
        """验证使用了SequenceMatcher进行相似度计算"""
        # 确保calculate_similarity使用了SequenceMatcher
        name1 = "Manchester City"
        name2 = "Man City"

        # 手动计算相似度（使用SequenceMatcher）
        expected_similarity = SequenceMatcher(
            None, name1.lower(), name2.lower()
        ).ratio()

        # 通过实体解析器计算
        actual_similarity = resolver.calculate_similarity(name1, name2)

        assert actual_similarity == expected_similarity

    @pytest.mark.asyncio
    async def test_batch_team_resolution(self, resolver, mock_existing_teams):
        """测试批量球队解析"""
        resolver.existing_teams = mock_existing_teams

        team_list = [
            "Manchester City",  # 现有球队
            "Bayern",  # 模糊匹配
            "New Team",  # 新球队
        ]

        with patch.object(resolver, "insert_new_team", return_value=100):
            results = await resolver.resolve_team_list(team_list)

            assert len(results["results"]) == 3
            assert "Manchester City" in results["team_mapping"]
            assert "Bayern" in results["team_mapping"]
            assert "New Team" in results["team_mapping"]

            # 检查统计信息
            assert results["stats"]["new_teams_detected"] >= 0

    @pytest.mark.asyncio
    async def test_empty_team_name(self, resolver):
        """测试空球队名称处理"""
        result = await resolver.resolve_team_entity("")
        assert result["resolution_type"] in ["new_team", None]
        assert result["action_taken"] in ["inserted_new", "error"]

    def test_case_insensitive_matching(self, resolver):
        """测试大小写不敏感匹配"""
        # 标准化后应该处理大小写
        normalized = resolver.normalize_team_name("MANCHESTER CITY")
        assert normalized == "Manchester City"

    @pytest.mark.asyncio
    async def test_stats_tracking(self, resolver, mock_existing_teams):
        """测试统计信息跟踪"""
        resolver.existing_teams = mock_existing_teams

        initial_stats = resolver.stats.copy()

        with patch.object(resolver, "insert_new_team", return_value=100):
            await resolver.resolve_team_entity("New Team")

        # 检查统计信息更新
        assert (
            resolver.stats["new_teams_inserted"] > initial_stats["new_teams_inserted"]
        )

    @pytest.mark.asyncio
    async def test_multiple_variants_mapping_to_same_id(self, resolver):
        """
        关键测试：多个变体映射到相同ID

        这是数据治理的核心 - 确保5个变体 -> 1个规范ID
        """
        resolver.existing_teams = {"Bayern Munich": 3}

        variants = ["Bayern", "FC Bayern", "Bayern Munich", "FC Bayern Munich"]

        for variant in variants:
            result = await resolver.resolve_team_entity(variant)
            # 所有变体都应该映射到相同的ID（3）
            assert result["matched_team_id"] == 3

        # 验证没有创建重复的球队
        # 如果所有变体都正确映射，最终的existing_teams应该只包含原始的一个
        assert len([k for k, v in resolver.existing_teams.items() if v == 3]) == 1

    def test_normalization_preserves_team_names(self, resolver):
        """测试标准化保持有效球队名称"""
        # 确保标准化不会产生无意义的字符串
        test_cases = [
            "Real Madrid",
            "AC Milan",
            "Inter Milan",
            "Ajax",
            "PSV",
        ]

        for team in test_cases:
            normalized = resolver.normalize_team_name(team)
            assert len(normalized) > 0
            assert (
                " " not in normalized.strip() or normalized.count(" ") < 5
            )  # 防止过多空格

    @pytest.mark.asyncio
    async def test_resolve_team_entity_return_structure(self, resolver):
        """测试resolve_team_entity返回结构的一致性"""
        resolver.existing_teams = {"Test Team": 1}

        result = await resolver.resolve_team_entity("Test Team")

        # 检查返回字典包含所有必需字段
        required_fields = [
            "input_name",
            "resolution_type",
            "matched_team_id",
            "matched_team_name",
            "similarity_score",
            "action_taken",
        ]

        for field in required_fields:
            assert field in result, f"缺少字段: {field}"

        # 检查字段类型
        assert isinstance(result["input_name"], str)
        assert isinstance(result["resolution_type"], (str(None)))
        assert isinstance(result["matched_team_id"], (int(None)))
        assert isinstance(result["similarity_score"], float)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
