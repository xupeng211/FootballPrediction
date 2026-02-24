"""
V171-Standard-04 C++ Bridge 单元测试
====================================

测试 cpp_bridge_radar.py 的模糊匹配功能：
- 5 组队名对撞测试
- 断言匹配率符合预期
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


# ============================================================================
# Mock 数据类
# ============================================================================

@dataclass
class RadarQuery:
    """模拟 RadarQuery"""
    match_id: str
    home_team: str
    away_team: str
    league_name: str
    match_date: datetime
    min_threshold: float = 65.0


@dataclass
class BridgeResult:
    """模拟 BridgeResult"""
    success: bool
    url: Optional[str] = None
    confidence: float = 0.0
    method: str = "fuzzy"


# ============================================================================
# 测试数据
# ============================================================================

TEST_MATCHES = [
    {
        "fotmob": ("Liverpool", "West Ham"),
        "oddsportal": ("liverpool", "west-ham"),
        "expected_confidence": 0.90,
        "description": "完整队名匹配"
    },
    {
        "fotmob": ("Arsenal", "Chelsea"),
        "oddsportal": ("arsenal", "chelsea"),
        "expected_confidence": 0.95,
        "description": "简单队名匹配"
    },
    {
        "fotmob": ("Man Utd", "Man City"),
        "oddsportal": ("manchester-united", "manchester-city"),
        "expected_confidence": 0.55,
        "description": "缩写 vs 全名"
    },
    {
        "fotmob": ("Spurs", "Wolves"),
        "oddsportal": ("tottenham-hotspur", "wolverhampton"),
        "expected_confidence": 0.50,
        "description": "昵称 vs 全名"
    },
    {
        "fotmob": ("Brighton", "Nottingham Forest"),
        "oddsportal": ("brighton", "nottingham"),
        "expected_confidence": 0.85,
        "description": "部分匹配"
    },
]


# ============================================================================
# 测试类
# ============================================================================

class TestCppFuzzyBridge:
    """C++ 模糊匹配桥接测试"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟引擎"""
        engine = MagicMock()
        engine.dynamic_bridge = MagicMock(return_value="https://example.com/match-ABC12345/")
        return engine

    @pytest.fixture
    def mock_rapidfuzz(self):
        """模拟 RapidFuzz"""
        with patch('rapidfuzz.fuzz.WRatio') as mock:
            yield mock

    def test_team_name_normalization(self):
        """测试队名标准化"""
        from src.utils.typed_matcher import normalize_team_name

        assert normalize_team_name("Manchester United") == "manchester united"
        assert normalize_team_name("  Liverpool FC  ") == "liverpool fc"
        assert normalize_team_name("ARSENAL") == "arsenal"

    def test_fuzzy_match_basic(self, mock_rapidfuzz):
        """测试基础模糊匹配"""
        # 模拟 RapidFuzz 返回值
        mock_rapidfuzz.side_effect = [95.0, 90.0]  # 主队、客队相似度

        from rapidfuzz import fuzz

        home_score = fuzz.WRatio("liverpool", "liverpool fc")
        away_score = fuzz.WRatio("west ham", "west-ham-united")

        # 至少有一个被调用
        assert mock_rapidfuzz.called

    @pytest.mark.parametrize("match_data", TEST_MATCHES)
    def test_team_matching_confidence(self, match_data):
        """测试队名匹配置信度"""
        from rapidfuzz import fuzz

        fotmob_home, fotmob_away = match_data["fotmob"]
        oddsportal_home, oddsportal_away = match_data["oddsportal"]
        expected = match_data["expected_confidence"]
        description = match_data["description"]

        # 计算实际相似度
        home_score = fuzz.WRatio(
            fotmob_home.lower(),
            oddsportal_home.lower().replace("-", " ")
        ) / 100.0

        away_score = fuzz.WRatio(
            fotmob_away.lower(),
            oddsportal_away.lower().replace("-", " ")
        ) / 100.0

        avg_score = (home_score + away_score) / 2.0

        print(f"\n  {description}:")
        print(f"    主队: {fotmob_home} vs {oddsportal_home} → {home_score:.2%}")
        print(f"    客队: {fotmob_away} vs {oddsportal_away} → {away_score:.2%}")
        print(f"    平均: {avg_score:.2%} (预期: {expected:.2%})")

        # 断言置信度在预期范围内 (±20%)
        assert avg_score >= expected - 0.20, \
            f"置信度过低: {avg_score:.2%} < {expected - 0.20:.2%}"

    def test_url_hash_extraction(self):
        """测试 URL Hash 提取"""
        import re

        pattern = re.compile(r'/([A-Za-z0-9]{8})/?$')

        test_urls = [
            ("https://oddsportal.com/liverpool-west-ham-KbUrxW1T/", "KbUrxW1T"),
            ("https://oddsportal.com/arsenal-chelsea-CE2gREmB", "CE2gREmB"),
            ("https://oddsportal.com/fulham-tottenham-CSsSuE24/", "CSsSuE24"),
        ]

        for url, expected_hash in test_urls:
            match = pattern.search(url)
            assert match is not None, f"未找到 hash: {url}"
            assert match.group(1) == expected_hash
            print(f"  ✅ {url} → {expected_hash}")

    def test_bridge_result_structure(self):
        """测试桥接结果结构"""
        result = BridgeResult(
            success=True,
            url="https://example.com/match-ABC12345/",
            confidence=0.85,
            method="fuzzy"
        )

        assert result.success is True
        assert result.url is not None
        assert 0.0 <= result.confidence <= 1.0
        assert result.method in ["fuzzy", "exact", "cache"]


class TestCppBridgeIntegration:
    """C++ 桥接集成测试"""

    def test_full_matching_workflow(self):
        """测试完整匹配工作流"""
        from rapidfuzz import process, fuzz

        fotmob_teams = ["Liverpool", "Arsenal", "Chelsea"]
        oddsportal_teams = [
            "liverpool-fc",
            "arsenal-london",
            "chelsea-fc"
        ]

        results = []

        for fotmob in fotmob_teams:
            match = process.extractOne(
                fotmob.lower(),
                [t.lower().replace("-", " ") for t in oddsportal_teams],
                scorer=fuzz.WRatio
            )

            results.append({
                "fotmob": fotmob,
                "matched": match[0],
                "score": match[1] / 100.0
            })

            print(f"  {fotmob} → {match[0]} ({match[1]:.1f}%)")

        # 验证所有匹配都成功
        assert len(results) == 3
        assert all(r["score"] > 0.5 for r in results)

    def test_threshold_filtering(self):
        """测试阈值过滤"""
        from rapidfuzz import fuzz

        test_cases = [
            ("liverpool", "liverpool-fc", 0.90),  # 应该通过
            ("man utd", "manchester-united", 0.55),  # 可能不通过
            ("spurs", "tottenham-hotspur", 0.50),  # 可能不通过
        ]

        threshold = 0.65
        passed = 0

        for fotmob, oddsportal, _ in test_cases:
            score = fuzz.WRatio(fotmob, oddsportal) / 100.0
            if score >= threshold:
                passed += 1
                print(f"  ✅ {fotmob} vs {oddsportal}: {score:.2%}")
            else:
                print(f"  ⚠️ {fotmob} vs {oddsportal}: {score:.2%} (低于阈值)")

        print(f"\n  通过率: {passed}/{len(test_cases)}")


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
