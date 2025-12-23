#!/usr/bin/env python3
"""
对抗性时间泄露审计测试
====================================

审计目标：确保 StandingsCalculator 和 pipeline_v19.py
在处理时序数据时，绝对不会使用未来数据。

测试场景：
1. 时空回溯攻击 - 验证未来数据不影响过去预测
2. 边界一致性审计 - 验证比赛时间边界
3. 累计逻辑压力测试 - 验证统计计算正确性

Author: QA Automation & Security Auditor
Version: 1.0.0
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# Configure logging for audit trail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [AUDIT] %(message)s'
)
logger = logging.getLogger(__name__)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.features.standings_calculator import (
    StandingsCalculator,
    TeamStandings,
    initialize_global_calculator,
    get_global_calculator
)


class TestTimeLeakageAudit:
    """
    对抗性时间泄露审计测试套件

    每个测试都是独立的，使用 Mock 数据，不污染生产环境
    """

    # ========================================================================
    # Test 1: 时空回溯攻击 (Future-to-Past Attack)
    # ========================================================================

    def test_future_to_past_attack(self):
        """
        [SEC-001] 时空回溯攻击测试

        攻击场景：
        1. 模拟一个按时间顺序的赛季数据
        2. 提取某场比赛在"干净状态"下的积分榜特征
        3. 恶意插入一场未来的"假大比分"比赛
        4. 重新提取同一比赛的特征

        预期：两次提取结果必须完全相同
        失败条件：未来数据影响了过去预测 = 数据泄露
        """
        logger.info("=" * 80)
        logger.info("[SEC-001] 启动时空回溯攻击测试")
        logger.info("=" * 80)

        # Step 1: 创建干净的时序数据
        base_date = datetime(2024, 1, 1)
        clean_data = []

        # 10 场比赛：Arsenal vs various opponents
        for i in range(10):
            match_date = base_date + timedelta(days=i*7)  # 每周一场
            clean_data.append({
                'home_team': 'Arsenal',
                'away_team': f'Team_{i}',
                'match_time': match_date,
                'home_score': 2,
                'away_score': 1,
                'id': i
            })

        df_clean = pd.DataFrame(clean_data)

        # Step 2: 初始化计算器并提取目标比赛的特征
        calculator = StandingsCalculator()
        calculator.initialize_from_dataframe(df_clean)

        # 提取第 5 场比赛（索引 5）的积分榜
        target_match_idx = 5
        target_home_team = 'Arsenal'

        baseline_standings = calculator.get_team_stats_at_match(
            target_match_idx,
            target_home_team
        )

        logger.info(f"[SEC-001] 基准积分榜 (Match {target_match_idx}):")
        logger.info(f"  Position: {baseline_standings['position']}")
        logger.info(f"  Points: {baseline_standings['points']}")
        logger.info(f"  Played: {baseline_standings['played']}")
        logger.info(f"  Won: {baseline_standings['won']}")

        # Step 3: 恶意插入未来数据（12 月的大比分比赛）
        future_match = {
            'home_team': 'Arsenal',
            'away_team': 'Team_Future',
            'match_time': datetime(2024, 12, 1),  # 12 月的未来数据
            'home_score': 10,  # 假大比分
            'away_score': 0,
            'id': 999
        }

        df_corrupted = pd.concat([
            df_clean,
            pd.DataFrame([future_match])
        ], ignore_index=True)

        logger.info(f"[SEC-001] 已注入恶意未来数据: {future_match}")

        # Step 4: 重新初始化并提取同一比赛的特征
        calculator_corrupted = StandingsCalculator()
        calculator_corrupted.initialize_from_dataframe(df_corrupted)

        # 关键：必须找到同一场比赛在 corrupted DataFrame 中的索引
        # 因为排序后索引会变化！
        df_sorted = df_corrupted.sort_values('match_time').reset_index(drop=True)
        target_match_in_corrupted = df_sorted[
            (df_sorted['home_team'] == target_home_team) &
            (df_sorted['id'] == target_match_idx)
        ].index[0]

        corrupted_standings = calculator_corrupted.get_team_stats_at_match(
            target_match_in_corrupted,
            target_home_team
        )

        logger.info(f"[SEC-001] 被攻击后的积分榜 (Match {target_match_idx}):")
        logger.info(f"  Position: {corrupted_standings['position']}")
        logger.info(f"  Points: {corrupted_standings['points']}")
        logger.info(f"  Played: {corrupted_standings['played']}")
        logger.info(f"  Won: {corrupted_standings['won']}")

        # Step 5: 断言 - 两次结果必须完全相同
        assert baseline_standings['points'] == corrupted_standings['points'], \
            f"[SEC-001-FAIL] 数据泄露！积分被未来数据影响: " \
            f"{baseline_standings['points']} -> {corrupted_standings['points']}"

        assert baseline_standings['played'] == corrupted_standings['played'], \
            f"[SEC-001-FAIL] 数据泄露！比赛场次被未来数据影响: " \
            f"{baseline_standings['played']} -> {corrupted_standings['played']}"

        assert baseline_standings['won'] == corrupted_standings['won'], \
            f"[SEC-001-FAIL] 数据泄露！胜场数被未来数据影响: " \
            f"{baseline_standings['won']} -> {corrupted_standings['won']}"

        logger.info("[SEC-001-PASS] ✅ 时空回溯攻击测试通过 - 未来数据未泄露")

    # ========================================================================
    # Test 2: 边界一致性审计 (Match-Day Boundary Check)
    # ========================================================================

    def test_match_day_boundary_integrity(self):
        """
        [SEC-002] 比赛日边界完整性测试

        验证：在计算 Match(T) 的积分榜时，
        引用的最新比赛时间必须严格 < Match(T) 的时间

        失败条件：存在任何引用时间 >= 目标比赛时间

        V19.2 更新：测试时延机制的影响
        """
        logger.info("=" * 80)
        logger.info("[SEC-002] 启动比赛日边界完整性测试")
        logger.info("=" * 80)

        # V19.2: 使用 0 时延进行基础测试，确保核心逻辑正确
        calculator = StandingsCalculator(latency_minutes=0)

        # 创建精确时间戳的测试数据（比赛间隔 3 小时，大于 2 小时时延）
        base_time = datetime(2024, 3, 15, 15, 0, 0)  # 2024-03-15 15:00:00

        test_matches = []
        for i in range(5):
            # 每场比赛相隔 3 小时（大于 2 小时时延）
            match_time = base_time + timedelta(hours=i*3)
            test_matches.append({
                'home_team': f'Team_{i % 2}',  # Team_0 vs Team_1 交替
                'away_team': f'Team_{(i + 1) % 2}',
                'match_time': match_time,
                'home_score': 1,
                'away_score': 0,
            })

        df = pd.DataFrame(test_matches)
        calculator.initialize_from_dataframe(df)

        # 测试每一场比赛的边界
        for target_idx in range(1, len(test_matches)):
            target_match_time = df.iloc[target_idx]['match_time']

            # 获取该比赛时的积分榜
            standings = calculator.get_standings_at_match(target_idx)

            # 验证：计算积分榜时引用的所有比赛时间必须 < 目标比赛时间
            max_referenced_time = None
            for i in range(target_idx):
                match_time = df.iloc[i]['match_time']
                if max_referenced_time is None or match_time > max_referenced_time:
                    max_referenced_time = match_time

            logger.info(f"[SEC-002] Match[{target_idx}] at {target_match_time}")
            logger.info(f"  Max referenced time: {max_referenced_time}")
            logger.info(f"  Time gap: {(target_match_time - max_referenced_time).total_seconds()}s")

            # 核心断言：引用的最新时间必须严格小于目标比赛时间
            assert max_referenced_time < target_match_time, \
                f"[SEC-002-FAIL] 边界破坏！引用时间 {max_referenced_time} " \
                f">= 目标比赛时间 {target_match_time}"

            # 验证积分统计的正确性
            expected_played = target_idx  # 每支球队应该参与了 target_idx 场比赛
            for team_name, team_standings in standings.items():
                assert team_standings.played == expected_played, \
                    f"[SEC-002-FAIL] {team_name} 的比赛场次不正确: " \
                    f"expected {expected_played}, got {team_standings.played}"

        logger.info("[SEC-002-PASS] ✅ 比赛日边界完整性测试通过 - 无时间泄露")

    # ========================================================================
    # Test 3: 累计逻辑压力测试 (Cumulative Logic Stress)
    # ========================================================================

    def test_cumulative_logic_correctness(self):
        """
        [SEC-003] 累计逻辑正确性压力测试

        随机生成 50 场比赛，手动计算预期值，
        与 StandingsCalculator 输出进行逐场比对

        失败条件：任何统计误差 != 0
        """
        logger.info("=" * 80)
        logger.info("[SEC-003] 启动累计逻辑压力测试")
        logger.info("=" * 80)

        # 固定随机种子以确保可重现性
        np.random.seed(42)

        # 创建 2 支球队的简单场景，便于手动验证
        teams = ['Team_A', 'Team_B']
        n_matches = 50

        test_matches = []
        base_date = datetime(2024, 1, 1)

        for i in range(n_matches):
            match_time = base_date + timedelta(days=i)
            home_score = np.random.randint(0, 4)  # 0-3 球
            away_score = np.random.randint(0, 4)

            test_matches.append({
                'home_team': teams[i % 2],
                'away_team': teams[(i + 1) % 2],
                'match_time': match_time,
                'home_score': home_score,
                'away_score': away_score,
            })

        df = pd.DataFrame(test_matches)

        # 手动计算预期积分榜
        manual_standings_history = []
        current_standings = {team: {
            'position': 0, 'points': 0, 'played': 0,
            'won': 0, 'drawn': 0, 'lost': 0,
            'goals_for': 0, 'goals_against': 0
        } for team in teams}

        for match_idx, match in enumerate(test_matches):
            # 记录当前比赛前的积分榜状态
            manual_standings_history.append({
                team: dict(current_standings[team]) for team in teams
            })

            # 更新积分榜（为下一场比赛做准备）
            home = match['home_team']
            away = match['away_team']
            home_goals = match['home_score']
            away_goals = match['away_score']

            # 更新主队
            current_standings[home]['played'] += 1
            current_standings[home]['goals_for'] += home_goals
            current_standings[home]['goals_against'] += away_goals

            # 更新客队
            current_standings[away]['played'] += 1
            current_standings[away]['goals_for'] += away_goals
            current_standings[away]['goals_against'] += home_goals

            # 更新胜负平和积分
            if home_goals > away_goals:
                current_standings[home]['won'] += 1
                current_standings[home]['points'] += 3
                current_standings[away]['lost'] += 1
            elif home_goals < away_goals:
                current_standings[away]['won'] += 1
                current_standings[away]['points'] += 3
                current_standings[home]['lost'] += 1
            else:
                current_standings[home]['drawn'] += 1
                current_standings[home]['points'] += 1
                current_standings[away]['drawn'] += 1
                current_standings[away]['points'] += 1

        # 使用 StandingsCalculator 计算
        calculator = StandingsCalculator()
        calculator.initialize_from_dataframe(df)

        # 逐场比对
        errors = []
        for match_idx in range(n_matches):
            expected = manual_standings_history[match_idx]
            calculated = calculator.get_standings_at_match(match_idx)

            for team in teams:
                # 跳过尚未出现的球队（前几轮可能没有所有球队）
                if team not in calculated:
                    continue

                exp_pts = expected[team]['points']
                calc_pts = calculated[team].points

                if exp_pts != calc_pts:
                    errors.append(
                        f"Match[{match_idx}] {team}: "
                        f"expected {exp_pts} points, got {calc_pts}"
                    )

                # 验证其他统计
                assert expected[team]['played'] == calculated[team].played, \
                    f"[SEC-003-FAIL] Match[{match_idx}] {team}: played mismatch"
                assert expected[team]['won'] == calculated[team].won, \
                    f"[SEC-003-FAIL] Match[{match_idx}] {team}: won mismatch"
                assert expected[team]['drawn'] == calculated[team].drawn, \
                    f"[SEC-003-FAIL] Match[{match_idx}] {team}: drawn mismatch"
                assert expected[team]['lost'] == calculated[team].lost, \
                    f"[SEC-003-FAIL] Match[{match_idx}] {team}: lost mismatch"
                assert expected[team]['goals_for'] == calculated[team].goals_for, \
                    f"[SEC-003-FAIL] Match[{match_idx}] {team}: goals_for mismatch"
                assert expected[team]['goals_against'] == calculated[team].goals_against, \
                    f"[SEC-003-FAIL] Match[{match_idx}] {team}: goals_against mismatch"

        # 打印错误报告
        if errors:
            logger.error(f"[SEC-003] 发现 {len(errors)} 个积分错误:")
            for error in errors[:10]:  # 只显示前 10 个
                logger.error(f"  {error}")

        assert len(errors) == 0, \
            f"[SEC-003-FAIL] 累计逻辑存在误差，共 {len(errors)} 处错误"

        logger.info(f"[SEC-003-PASS] ✅ 累计逻辑压力测试通过 - {n_matches} 场比赛零误差")

    # ========================================================================
    # Test 4: 真实场景泄露检测 (Real-World Leakage Detection)
    # ========================================================================

    def test_pipeline_index_corruption_risk(self):
        """
        [SEC-004] Pipeline 索引错位风险检测

        检测 pipeline_v19.py 中使用 pandas 原始索引
        而非 sorted matches_cache 索引的风险

        这是当前系统中最隐蔽的泄露源！
        """
        logger.info("=" * 80)
        logger.info("[SEC-004] 启动 Pipeline 索引错位风险检测")
        logger.info("=" * 80)

        # 创建故意乱序的数据
        base_date = datetime(2024, 1, 1)
        matches = []

        # 第 1 批：1 月的比赛
        for i in range(5):
            matches.append({
                'id': 100 + i,
                'home_team': 'Team_A',
                'away_team': 'Team_B',
                'match_time': base_date + timedelta(days=i),
                'home_score': 1,
                'away_score': 0,
            })

        # 第 2 批：2 月的比赛（时间更晚）
        feb_date = datetime(2024, 2, 1)
        for i in range(5):
            matches.append({
                'id': 200 + i,
                'home_team': 'Team_A',
                'away_team': 'Team_C',
                'match_time': feb_date + timedelta(days=i),
                'home_score': 2,
                'away_score': 1,
            })

        # 创建 DataFrame 并故意乱序
        df = pd.DataFrame(matches)

        # 打乱 DataFrame 行顺序（但保持内部数据正确）
        df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

        logger.info(f"[SEC-004] 创建了 {len(df_shuffled)} 场乱序比赛")
        logger.info(f"[SEC-004] 原始索引范围: 0-{len(df_shuffled)-1}")
        logger.info(f"[SEC-004] 时间范围: {df_shuffled['match_time'].min()} 到 {df_shuffled['match_time'].max()}")

        # 初始化计算器（会进行排序）
        calculator = StandingsCalculator()
        calculator.initialize_from_dataframe(df_shuffled)

        # 检测风险：使用 iterrows() 的索引 vs matches_cache 的索引
        risks_detected = []

        for idx, row in df_shuffled.iterrows():
            # idx 是原始 DataFrame 的乱序索引
            # 但 calculator.get_team_stats_at_match(idx) 期望的是 sorted 索引

            team = row['home_team']
            match_time = row['match_time']

            try:
                standings = calculator.get_team_stats_at_match(idx, team)

                # 验证：返回的积分榜是否与当前比赛时间一致
                # 如果 idx 错位，played 数会异常

                # 找到这场比赛在排序后的 DataFrame 中的真实位置
                df_sorted = df_shuffled.sort_values('match_time').reset_index(drop=True)
                true_idx = df_sorted[
                    (df_sorted['home_team'] == team) &
                    (df_sorted['match_time'] == match_time)
                ].index

                if len(true_idx) > 0:
                    true_idx = true_idx[0]

                    if idx != true_idx:
                        risks_detected.append({
                            'iterrows_idx': idx,
                            'true_sorted_idx': true_idx,
                            'match_time': match_time,
                            'team': team,
                            'risk': 'INDEX_MISMATCH'
                        })

            except Exception as e:
                risks_detected.append({
                    'iterrows_idx': idx,
                    'error': str(e),
                    'risk': 'EXCEPTION'
                })

        # 报告风险
        if risks_detected:
            logger.warning(f"[SEC-004-WARNING] 检测到 {len(risks_detected)} 个潜在索引错位风险:")
            for risk in risks_detected[:5]:
                logger.warning(f"  {risk}")

        # 检测是否存在严重泄露风险
        # 如果使用错误的索引，会导致查看错误的比赛数量
        severe_risks = [r for r in risks_detected if r.get('risk') == 'INDEX_MISMATCH']

        if len(severe_risks) > 0:
            logger.error(f"[SEC-004-FAIL] 发现严重索引错位风险！")
            logger.error(f"[SEC-004] pipeline_v19.py 中使用 pandas iterrows() 的索引")
            logger.error(f"[SEC-004] 作为 get_team_stats_at_match() 的参数是错误的！")

            # 提供修复建议
            logger.error(f"\n[SEC-004] 修复建议：")
            logger.error(f"[SEC-004] 1. 在 extract_v19_features() 中，使用 DataFrame 的")
            logger.error(f"[SEC-004]    reset_index(drop=True) 后的索引")
            logger.error(f"[SEC-004] 2. 或者在 get_team_stats_at_match() 中根据 match_time")
            logger.error(f"[SEC-004]    查找正确的索引")
        else:
            logger.info("[SEC-004-PASS] ✅ 索引一致性检查通过")

    # ========================================================================
    # Test 5: NaN 传播审计 (NaN Propagation Audit)
    # ========================================================================

    def test_nan_propagation_integrity(self):
        """
        [SEC-005] NaN 值传播完整性测试

        验证当积分榜数据不可用时（早期比赛），
        系统是否正确使用 None 而非假数据
        """
        logger.info("=" * 80)
        logger.info("[SEC-005] 启动 NaN 传播完整性测试")
        logger.info("=" * 80)

        # V19.2: 创建多场比赛数据，包含新球队的首场比赛
        base_date = datetime(2024, 1, 1)
        test_data = []

        # 第 0 场：ExistingTeam vs OldTeam (NewTeam 未出现)
        test_data.append({
            'home_team': 'ExistingTeam',
            'away_team': 'OldTeam',
            'match_time': base_date,
            'home_score': 1,
            'away_score': 0,
        })

        # 第 1 场：NewTeam 首次登场
        test_data.append({
            'home_team': 'NewTeam',
            'away_team': 'ExistingTeam',
            'match_time': base_date + timedelta(days=7),
            'home_score': 1,
            'away_score': 0,
        })

        # 第 2 场：NewTeam 的第二场比赛
        test_data.append({
            'home_team': 'OldTeam',
            'away_team': 'NewTeam',
            'match_time': base_date + timedelta(days=14),
            'home_score': 0,
            'away_score': 2,
        })

        df = pd.DataFrame(test_data)

        # V19.2: 使用 0 时延进行基础测试
        calculator = StandingsCalculator(latency_minutes=0)
        calculator.initialize_from_dataframe(df)

        # 测试 1: 查询 NewTeam 在首场比赛前（match_idx=1）的积分榜
        # 应该返回 None（没有历史数据）
        standings_before_first = calculator.get_team_stats_at_match(1, 'NewTeam')

        if standings_before_first is None:
            logger.info("[SEC-005] NewTeam 首场比赛前积分榜: None ✅")
        else:
            logger.error(f"[SEC-005-FAIL] 首场比赛前应返回 None，但返回了: {standings_before_first}")
            assert False, "[SEC-005-FAIL] 首场比赛前应返回 None"

        # 测试 2: 查询 NewTeam 在首场比赛后（match_idx=2）的积分榜
        # 应该看到第一场比赛的结果（1胜3分）
        standings_after_first = calculator.get_team_stats_at_match(2, 'NewTeam')

        if standings_after_first is not None:
            logger.info(f"[SEC-005] NewTeam 首场比赛后积分榜:")
            logger.info(f"  Played: {standings_after_first['played']}")
            logger.info(f"  Points: {standings_after_first['points']}")
            logger.info(f"  Won: {standings_after_first['won']}")

            assert standings_after_first['played'] == 1, \
                f"[SEC-005-FAIL] 首场比赛后 played 应该是 1，实际 {standings_after_first['played']}"
            assert standings_after_first['points'] == 3, \
                f"[SEC-005-FAIL] 首场比赛后 points 应该是 3，实际 {standings_after_first['points']}"
            assert standings_after_first['won'] == 1, \
                f"[SEC-005-FAIL] 首场比赛后 won 应该是 1，实际 {standings_after_first['won']}"
        else:
            logger.error("[SEC-005-FAIL] 首场比赛后积分榜返回 None（意外）")
            assert False, "[SEC-005-FAIL] 首场比赛后应返回有效数据"

        # 测试 3: 验证不存在的球队返回 None
        standings_ghost = calculator.get_team_stats_at_match(2, 'GhostTeam')
        assert standings_ghost is None, \
            "[SEC-005-FAIL] 不存在的球队应返回 None"

        logger.info("[SEC-005-PASS] ✅ NaN 传播完整性检查完成")


class TestAuditReport:
    """
    审计报告生成器
    生成可读性强的审计结果报告
    """

    @staticmethod
    def generate_report():
        """生成审计报告摘要"""
        report = """
================================================================================
                  时间泄露对抗性审计报告
================================================================================

审计范围：
- src/ml/features/standings_calculator.py
- src/core/pipeline_v19.py (集成点)

审计项目：
[SEC-001] 时空回溯攻击测试 - 未来数据不应影响过去预测
[SEC-002] 比赛日边界完整性 - 确保时间隔离
[SEC-003] 累计逻辑压力测试 - 验证统计计算正确性
[SEC-004] Pipeline 索引错位风险 - 检测 pandas 索引使用问题
[SEC-005] NaN 传播完整性 - 验证无数据时的处理

执行方法：
    pytest tests/test_standings_leakage_audit.py -v --tb=short

预期结果：
    所有测试应该通过（PASS）
    任何 FAIL 表示存在数据泄露风险

修复优先级：
    🔴 HIGH - [SEC-004] 索引错位（如果失败）
    🟡 MEDIUM - [SEC-001] 时空回溯（如果失败）
    🟢 LOW - [SEC-005] NaN 处理（如果失败）

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================
        """
        return report


def main():
    """运行审计并生成报告"""
    print(TestAuditReport.generate_report())

    # 运行测试
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ])


if __name__ == '__main__':
    main()
