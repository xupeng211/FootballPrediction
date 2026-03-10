#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN V4.46.7 核心逻辑断言测试                                              ║
# ║   First Line of Defense - Unit Tests                                         ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 测试覆盖:
# 1. H2HEstimator - H2H 补位计算正确性
# 2. MV-Scout - 身价回溯与默认值逻辑
# 3. 除零防御 - 极端情况下的安全处理
#
# @module tests.test_core_logic
# @version V4.46.7
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
import math
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# H2HEstimator 测试类 (从 predict_pipeline.py 提取核心逻辑)
# ============================================================================

class H2HEstimator:
    """测试用 H2HEstimator 副本 (与 predict_pipeline.py 保持同步)"""

    ELO_TO_GOAL_COEFF = 0.005
    HOME_WIN_SMOOTH_FACTOR = 0.85

    LEAGUE_HOME_WIN_BASELINE = {
        'Premier League': 0.42, 'La Liga': 0.45, 'Serie A': 0.44,
        'Bundesliga': 0.43, 'Ligue 1': 0.41, 'default': 0.40,
    }

    LEAGUE_DRAW_BASELINE = {
        'Premier League': 0.24, 'La Liga': 0.25, 'Serie A': 0.26,
        'Bundesliga': 0.23, 'Ligue 1': 0.25, 'default': 0.25,
    }

    @classmethod
    def estimate_from_elo(cls, elo_diff, expected_home_win, league_name=None):
        """基于 Elo 估算 H2H"""
        h2h_avg_goal_diff = elo_diff * cls.ELO_TO_GOAL_COEFF

        league_baseline = cls._get_league_home_win_baseline(league_name)
        h2h_home_win_ratio = (
            expected_home_win * cls.HOME_WIN_SMOOTH_FACTOR +
            league_baseline * (1 - cls.HOME_WIN_SMOOTH_FACTOR)
        )

        h2h_draw_ratio = cls._get_league_draw_baseline(league_name)

        return {
            'h2h_avg_goal_diff': round(h2h_avg_goal_diff, 3),
            'h2h_home_win_ratio': round(h2h_home_win_ratio, 3),
            'h2h_draw_ratio': round(h2h_draw_ratio, 3),
        }

    @classmethod
    def _get_league_home_win_baseline(cls, league_name):
        if not league_name:
            return cls.LEAGUE_HOME_WIN_BASELINE['default']
        for key, value in cls.LEAGUE_HOME_WIN_BASELINE.items():
            if key.lower() in league_name.lower():
                return value
        return cls.LEAGUE_HOME_WIN_BASELINE['default']

    @classmethod
    def _get_league_draw_baseline(cls, league_name):
        if not league_name:
            return cls.LEAGUE_DRAW_BASELINE['default']
        for key, value in cls.LEAGUE_DRAW_BASELINE.items():
            if key.lower() in league_name.lower():
                return value
        return cls.LEAGUE_DRAW_BASELINE['default']

    @classmethod
    def needs_estimation(cls, h2h_data):
        if not h2h_data:
            return True
        avg_gd = h2h_data.get('h2h_avg_goal_diff', h2h_data.get('avg_goal_diff', 0))
        win_ratio = h2h_data.get('h2h_home_win_ratio', h2h_data.get('home_win_ratio', 0))
        return (avg_gd == 0 and win_ratio == 0)


# ============================================================================
# 工具函数测试副本
# ============================================================================

def safe_float(v, d=0.0):
    try:
        return float(v) if v is not None else d
    except:
        return d

def safe_log10(v, d=18.0):
    try:
        return math.log10(v) if v and v > 0 else d
    except:
        return d

def calculate_mv_share(home_mv, away_mv):
    """计算身价占比 (带除零防御)"""
    total_mv = home_mv + away_mv
    if total_mv <= 0:
        return 0.5  # 防御性默认值
    return home_mv / total_mv


# ============================================================================
# 测试类: H2HEstimator 测试
# ============================================================================

class TestH2HEstimator:
    """H2H 补位引擎核心逻辑测试"""

    def test_elo_to_goal_conversion(self):
        """
        测试: Elo 差值到净胜球的线性转换
        公式: h2h_avg_goal_diff = elo_diff * 0.005
        """
        # Case 1: elo_diff = 200 → h2h_gd = 1.0
        result = H2HEstimator.estimate_from_elo(elo_diff=200, expected_home_win=0.6)
        assert result['h2h_avg_goal_diff'] == 1.0, f"期望 1.0, 实际 {result['h2h_avg_goal_diff']}"

        # Case 2: elo_diff = 100 → h2h_gd = 0.5
        result = H2HEstimator.estimate_from_elo(elo_diff=100, expected_home_win=0.55)
        assert result['h2h_avg_goal_diff'] == 0.5, f"期望 0.5, 实际 {result['h2h_avg_goal_diff']}"

        # Case 3: elo_diff = -150 → h2h_gd = -0.75 (客队优势)
        result = H2HEstimator.estimate_from_elo(elo_diff=-150, expected_home_win=0.35)
        assert result['h2h_avg_goal_diff'] == -0.75, f"期望 -0.75, 实际 {result['h2h_avg_goal_diff']}"

        # Case 4: elo_diff = 0 → h2h_gd = 0 (均势)
        result = H2HEstimator.estimate_from_elo(elo_diff=0, expected_home_win=0.45)
        assert result['h2h_avg_goal_diff'] == 0.0, f"期望 0.0, 实际 {result['h2h_avg_goal_diff']}"

    def test_home_win_ratio_smoothing(self):
        """
        测试: 主胜率平滑计算
        公式: h2h_win = exp_home * 0.85 + league_baseline * 0.15
        """
        # 英超: baseline = 0.42
        result = H2HEstimator.estimate_from_elo(
            elo_diff=100, expected_home_win=0.60, league_name='Premier League'
        )
        expected = 0.60 * 0.85 + 0.42 * 0.15  # = 0.543
        assert abs(result['h2h_home_win_ratio'] - expected) < 0.01

        # 西甲: baseline = 0.45
        result = H2HEstimator.estimate_from_elo(
            elo_diff=150, expected_home_win=0.65, league_name='La Liga'
        )
        expected = 0.65 * 0.85 + 0.45 * 0.15  # = 0.605
        assert abs(result['h2h_home_win_ratio'] - expected) < 0.01

    def test_league_baseline_fallback(self):
        """测试: 未知联赛使用默认基准"""
        result = H2HEstimator.estimate_from_elo(
            elo_diff=100, expected_home_win=0.50, league_name='中超'
        )
        # 应使用 default = 0.40
        expected = 0.50 * 0.85 + 0.40 * 0.15  # = 0.485
        assert abs(result['h2h_home_win_ratio'] - expected) < 0.01

    def test_needs_estimation_detection(self):
        """测试: H2H 缺失检测逻辑"""
        # Case 1: 空数据 → 需要补位
        assert H2HEstimator.needs_estimation({}) == True
        assert H2HEstimator.needs_estimation(None) == True

        # Case 2: 全 0 数据 → 需要补位
        assert H2HEstimator.needs_estimation({'h2h_avg_goal_diff': 0, 'h2h_home_win_ratio': 0}) == True

        # Case 3: 有效数据 → 不需要补位
        assert H2HEstimator.needs_estimation({'h2h_avg_goal_diff': 0.5, 'h2h_home_win_ratio': 0.45}) == False

        # Case 4: 只有一个非零 → 不需要补位
        assert H2HEstimator.needs_estimation({'h2h_avg_goal_diff': 0, 'h2h_home_win_ratio': 0.4}) == False


# ============================================================================
# 测试类: MV-Scout 测试
# ============================================================================

class TestMVScout:
    """身价侦察兵逻辑测试"""

    def test_mv_share_normal_case(self):
        """测试: 正常身价占比计算"""
        # 主队 3.5 亿 vs 客队 2.5 亿 → 占比 58.3%
        share = calculate_mv_share(350_000_000, 250_000_000)
        expected = 350_000_000 / 600_000_000  # = 0.5833
        assert abs(share - expected) < 0.001

    def test_mv_share_extreme_dominance(self):
        """测试: 极端身价优势"""
        # 主队 10 亿 vs 客队 5000 万 → 占比 95.2%
        share = calculate_mv_share(1_000_000_000, 50_000_000)
        expected = 1_000_000_000 / 1_050_000_000  # = 0.952
        assert abs(share - expected) < 0.001

    def test_mv_share_zero_defense(self):
        """测试: 除零防御 - 两队身价均为 0"""
        # 两队身价均为 0 → 必须返回 0.5，不能崩溃
        share = calculate_mv_share(0, 0)
        assert share == 0.5, f"期望 0.5, 实际 {share}"

    def test_mv_share_one_side_zero(self):
        """测试: 单侧身价为 0"""
        # 主队 3 亿 vs 客队 0 → 占比 100%
        share = calculate_mv_share(300_000_000, 0)
        assert share == 1.0

        # 主队 0 vs 客队 3 亿 → 占比 0%
        share = calculate_mv_share(0, 300_000_000)
        assert share == 0.0

    def test_safe_log10_edge_cases(self):
        """测试: 对数计算边缘情况"""
        # 正常值
        assert safe_log10(1_000_000_000) == 9.0  # log10(10亿) = 9

        # 零值 → 返回默认
        assert safe_log10(0) == 18.0

        # 负值 → 返回默认
        assert safe_log10(-100) == 18.0

        # None → 返回默认
        assert safe_log10(None) == 18.0


# ============================================================================
# 测试类: 工具函数测试
# ============================================================================

class TestUtilityFunctions:
    """工具函数测试"""

    def test_safe_float_normal(self):
        assert safe_float(3.14) == 3.14
        assert safe_float("2.5") == 2.5
        assert safe_float(100) == 100.0

    def test_safe_float_edge_cases(self):
        assert safe_float(None) == 0.0
        assert safe_float("invalid") == 0.0
        # 注意: safe_float 签名是 safe_float(v, d=0.0)，d 是位置参数
        assert safe_float(None, 5.0) == 5.0

    def test_result_mapping_consistency(self):
        """测试: 结果映射一致性"""
        RESULT_MAP = {"H": 2, "D": 1, "A": 0}
        RESULT_NAMES = ["AWAY", "DRAW", "HOME"]

        # 验证映射可逆
        for key, val in RESULT_MAP.items():
            assert RESULT_NAMES[val] == {"H": "HOME", "D": "DRAW", "A": "AWAY"}[key]


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
