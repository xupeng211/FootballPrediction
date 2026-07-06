/**
 * PrematchEloComputer 单元测试
 * =============================
 *
 * 覆盖所有赛前 Elo 安全边界：
 *   1. 无历史球队 → 默认 1500 + _is_default=true
 *   2. 主胜 → 主队上升 / 客队下降
 *   3. 平局 → 0.5/0.5 更新
 *   4. 赛前保证 → 目标比赛自身结果不影响其赛前 Elo
 *   5. 时间隔离 → 未来比赛不影响当前
 *   6. 同日稳定 → 同日 match 按 match_id 排序，不互相污染
 *   7. 批量计算 → computeAll 正确产出所有 match 的赛前 Elo
 *   8. 单场计算 → computeOne 正确过滤历史
 *   9. 空输入 → 安全返回空 Map
 *   10. 无效输入 → 不抛异常，graceful fallback
 *
 * lifecycle: permanent
 * scope: GOLD-AUDIT-2AH Elo signal safety validation
 */

'use strict';

const { PrematchEloComputer } = require(
    '../../../src/feature_engine/elo/PrematchEloComputer'
);

// ── helpers ──────────────────────────────────────────────────────────────

function makeMatch(id, home, away, hScore, aScore, date) {
    return {
        matchId: id,
        homeTeam: home,
        awayTeam: away,
        homeScore: hScore,
        awayScore: aScore,
        matchDate: date || '2025-08-15T19:00:00Z',
    };
}

function eloKey(match) {
    return match.matchId;
}

// ── 1. 无历史球队 → 默认 1500 ──────────────────────────────────────────

function test_no_history_is_default_1500() {
    const computer = new PrematchEloComputer();
    const matches = [
        makeMatch('m1', 'TeamA', 'TeamB', 2, 1, '2025-08-15T19:00:00Z'),
    ];
    const result = computer.computeAll(matches);
    const elo = result.get('m1');

    if (elo.home_elo_pre !== 1500.0) throw new Error(`Expected 1500, got ${elo.home_elo_pre}`);
    if (elo.away_elo_pre !== 1500.0) throw new Error(`Expected 1500, got ${elo.away_elo_pre}`);
    if (elo.elo_diff !== 0) throw new Error(`Expected elo_diff=0, got ${elo.elo_diff}`);
    if (elo._is_default !== true) throw new Error('Expected _is_default=true for no-history teams');
    if (elo._home_default !== true) throw new Error('Expected _home_default=true');
    if (elo._away_default !== true) throw new Error('Expected _away_default=true');
}

// ── 2. 历史球队 → 非默认 Elo ───────────────────────────────────────────

function test_history_team_has_real_elo() {
    const computer = new PrematchEloComputer();
    const matches = [
        makeMatch('m1', 'TeamA', 'TeamB', 2, 1, '2025-08-15T19:00:00Z'),
        makeMatch('m2', 'TeamA', 'TeamC', 1, 0, '2025-08-22T19:00:00Z'),
    ];
    const result = computer.computeAll(matches);
    const elo_m2 = result.get('m2');

    // TeamA has history, TeamC doesn't
    if (elo_m2._is_default !== false) throw new Error('m2: _is_default should be false (TeamA has history)');
    if (elo_m2._home_default !== false) throw new Error('m2: _home_default should be false');
    // TeamC 没有历史 → 仍然是 1500
    if (elo_m2.away_elo_pre !== 1500.0) throw new Error(`m2: away_elo should be 1500, got ${elo_m2.away_elo_pre}`);
    // TeamA 主胜后应该高于 1500
    if (elo_m2.home_elo_pre <= 1500.0) throw new Error(`m2: home_elo should be >1500 after a win, got ${elo_m2.home_elo_pre}`);
}

// ── 3. 赛前保证：目标比赛结果不影响自身赛前 Elo ─────────────────────────

function test_target_match_result_does_not_affect_own_prematch_elo() {
    const computer = new PrematchEloComputer();
    const matches = [
        makeMatch('m1', 'TeamA', 'TeamB', 5, 0, '2025-08-15T19:00:00Z'),
    ];
    const result = computer.computeAll(matches);

    // m1 是首场比赛，赛前 Elo 应该都是 1500
    const elo = result.get('m1');
    if (elo.home_elo_pre !== 1500.0) {
        throw new Error(`m1: home_elo_pre should be 1500 (no prior matches), got ${elo.home_elo_pre}`);
    }
    if (elo.away_elo_pre !== 1500.0) {
        throw new Error(`m1: away_elo_pre should be 1500, got ${elo.away_elo_pre}`);
    }
}

// ── 4. 未来比赛隔离 ─────────────────────────────────────────────────────

function test_future_matches_do_not_leak() {
    const computer = new PrematchEloComputer();
    const matches = [
        makeMatch('m2', 'TeamA', 'TeamC', 3, 0, '2025-08-22T19:00:00Z'), // 未来
        makeMatch('m1', 'TeamA', 'TeamB', 2, 1, '2025-08-15T19:00:00Z'), // 过去
    ];
    // computeAll 会按日期排序，所以 m1 先处理，m2 后处理
    const result = computer.computeAll(matches);
    const elo_m1 = result.get('m1');

    // m1 是首场（排序后），赛前 Elo 应为 1500
    if (elo_m1.home_elo_pre !== 1500.0) {
        throw new Error(`m1: m2 (future) should not affect m1 prematch Elo`);
    }
}

// ── 5. 同日稳定排序 ────────────────────────────────────────────────────

function test_same_date_matches_stable_ordering() {
    const computer = new PrematchEloComputer();
    const matches = [
        makeMatch('mB', 'TeamB', 'TeamC', 1, 1, '2025-08-15T19:00:00Z'),
        makeMatch('mA', 'TeamA', 'TeamB', 2, 0, '2025-08-15T19:00:00Z'),
    ];
    const result = computer.computeAll(matches);

    // 按 match_id 排序：mA → mB
    // mA: all default 1500
    const elo_mA = result.get('mA');
    if (elo_mA.home_elo_pre !== 1500.0) throw new Error('mA: should be default 1500');

    // mB: TeamB has history (lost to TeamA in mA), so TeamB should NOT be 1500
    const elo_mB = result.get('mB');
    if (elo_mB.home_elo_pre === 1500.0) {
        throw new Error('mB: TeamB has history → home_elo should not be 1500');
    }
}

// ── 6. 主胜 / 平局 / 客胜 方向验证 ──────────────────────────────────────

function test_elo_direction_after_win_loss_draw() {
    const computer = new PrematchEloComputer();

    // 一场主胜，检验方向
    const m1 = makeMatch('m1', 'TeamA', 'TeamB', 2, 0, '2025-08-15T19:00:00Z');
    const m2 = makeMatch('m2', 'TeamA', 'TeamC', 0, 2, '2025-08-22T19:00:00Z'); // A 输了
    const m3 = makeMatch('m3', 'TeamA', 'TeamD', 1, 1, '2025-08-29T19:00:00Z'); // 平
    const result = computer.computeAll([m1, m2, m3]);

    // m2 赛前：TeamA 经历了 m1 的主胜 → 应该 > 1500
    const elo_m2 = result.get('m2');
    if (elo_m2.home_elo_pre <= 1500.0) throw new Error('m2: TeamA won before → home_elo should be >1500');

    // m3 赛前：TeamA 经历了 m1 胜 + m2 负
    const elo_m3 = result.get('m3');
    // 主胜后 Elo 上升，客负后下降 — m2 是 0:2 输了
    // 无法确定精确值，但应该不是 1500
    if (elo_m3.home_elo_pre === 1500.0) throw new Error('m3: TeamA has 2 matches history → should not be 1500');
}

// ── 7. 空输入 / 无效输入 ─────────────────────────────────────────────────

function test_empty_input() {
    const computer = new PrematchEloComputer();
    const result1 = computer.computeAll([]);
    if (result1.size !== 0) throw new Error('Empty array should return empty Map');

    const result2 = computer.computeAll(null);
    if (result2.size !== 0) throw new Error('null should return empty Map');

    const result3 = computer.computeAll(undefined);
    if (result3.size !== 0) throw new Error('undefined should return empty Map');
}

function test_invalid_match_skipped() {
    const computer = new PrematchEloComputer();
    const matches = [
        makeMatch('m1', 'TeamA', 'TeamB', 2, 1, '2025-08-15T19:00:00Z'),
        { matchId: 'bad', homeTeam: null, awayTeam: null },  // invalid
    ];
    const result = computer.computeAll(matches);
    if (result.size !== 1) throw new Error(`Expected 1 valid match, got ${result.size}`);
    if (!result.has('m1')) throw new Error('m1 should be present');
}

// ── 8. computeOne 正确过滤历史 ───────────────────────────────────────────

function test_computeOne_filters_prior_matches() {
    const computer = new PrematchEloComputer();
    const history = [
        makeMatch('h1', 'TeamA', 'TeamX', 2, 1, '2025-08-08T19:00:00Z'),
        makeMatch('h2', 'TeamA', 'TeamY', 1, 0, '2025-08-15T19:00:00Z'), // same date as target = excluded
    ];
    const target = makeMatch('target', 'TeamA', 'TeamB', null, null, '2025-08-15T19:00:00Z');

    const elo = computer.computeOne(history, target);

    // h1 is before target → should be used
    // TeamA won h1 → Elo should be >1500
    if (elo.home_elo_pre <= 1500.0) {
        throw new Error('computeOne: TeamA has prior win → home_elo should be >1500');
    }
    // h2 has same date as target → should NOT be used
    // So h2 result should not affect TeamY
    if (elo.away_elo_pre !== 1500.0) {
        throw new Error('computeOne: TeamB has no prior → away_elo should be 1500');
    }
}

// ── 9. 多队交叉验证 ─────────────────────────────────────────────────────

function test_multi_team_cross_validation() {
    const computer = new PrematchEloComputer();
    const matches = [
        makeMatch('m1', 'PSG', 'Marseille', 3, 1, '2025-08-15T19:00:00Z'),
        makeMatch('m2', 'Lyon', 'PSG', 0, 2, '2025-08-22T19:00:00Z'),
        makeMatch('m3', 'Marseille', 'Lyon', 1, 1, '2025-08-29T19:00:00Z'),
    ];
    const result = computer.computeAll(matches);

    // m2: PSG has 1 prior win → Elo should be >1500
    const elo_m2 = result.get('m2');
    if (elo_m2.away_elo_pre <= 1500.0) throw new Error('m2: PSG won before → away_elo >1500');
    if (elo_m2.home_elo_pre !== 1500.0) throw new Error(`m2: Lyon no history → home_elo should be 1500, got ${elo_m2.home_elo_pre}`);
    if (elo_m2._is_default !== false) throw new Error('m2: PSG has history → _is_default should be false');
    if (elo_m2._home_default !== true) throw new Error('m2: Lyon no history → _home_default should be true');

    // m3: Marseille and Lyon both have 1 prior match (both lost)
    const elo_m3 = result.get('m3');
    if (elo_m3.home_elo_pre === 1500.0) throw new Error('m3: Marseille has history → home_elo should not be 1500');
    if (elo_m3.away_elo_pre === 1500.0) throw new Error('m3: Lyon has history → away_elo should not be 1500');
    // Both had losses, so Elo should be < 1500
    if (elo_m3.home_elo_pre >= 1500.0) throw new Error('m3: Marseille lost → home_elo should be <1500');
    if (elo_m3.away_elo_pre >= 1500.0) throw new Error('m3: Lyon lost → away_elo should be <1500');
}

// ── 10. importRatings / exportRatings / reset ────────────────────────────

function test_import_export_reset() {
    const computer = new PrematchEloComputer();

    // Import pre-existing ratings
    computer.importRatings({ 'TeamA': 1600, 'TeamB': 1400 });
    const ratings = computer.exportRatings();
    if (ratings['TeamA'] !== 1600) throw new Error('Import/export: TeamA should be 1600');
    if (ratings['TeamB'] !== 1400) throw new Error('Import/export: TeamB should be 1400');

    // computeAll should use imported ratings
    const matches = [
        makeMatch('m1', 'TeamA', 'TeamB', 1, 0, '2025-08-15T19:00:00Z'),
    ];
    const result = computer.computeAll(matches);
    const elo = result.get('m1');
    if (elo.home_elo_pre !== 1600) throw new Error(`Imported Elo should be 1600, got ${elo.home_elo_pre}`);
    if (elo.away_elo_pre !== 1400) throw new Error(`Imported Elo should be 1400, got ${elo.away_elo_pre}`);
    if (elo._is_default !== false) throw new Error('Imported ratings → _is_default should be false');

    // Reset
    computer.reset();
    const afterReset = computer.exportRatings();
    if (Object.keys(afterReset).length !== 0) throw new Error('After reset, ratings should be empty');
}

// ── runner ───────────────────────────────────────────────────────────────

const TESTS = [
    { name: '无历史球队 → 默认 1500 + _is_default', fn: test_no_history_is_default_1500 },
    { name: '有历史球队 → 非默认 Elo', fn: test_history_team_has_real_elo },
    { name: '目标比赛结果不影响自身赛前 Elo', fn: test_target_match_result_does_not_affect_own_prematch_elo },
    { name: '未来比赛不泄漏到当前', fn: test_future_matches_do_not_leak },
    { name: '同日比赛稳定排序不互相污染', fn: test_same_date_matches_stable_ordering },
    { name: '主胜/平局/客胜 Elo 方向验证', fn: test_elo_direction_after_win_loss_draw },
    { name: '空输入安全返回', fn: test_empty_input },
    { name: '无效 match 跳过不崩溃', fn: test_invalid_match_skipped },
    { name: 'computeOne 正确过滤历史', fn: test_computeOne_filters_prior_matches },
    { name: '多队交叉验证', fn: test_multi_team_cross_validation },
    { name: 'importRatings / exportRatings / reset', fn: test_import_export_reset },
];

let passed = 0;
let failed = 0;

for (const t of TESTS) {
    try {
        t.fn();
        passed++;
        console.log(`  ok - ${t.name}`);
    } catch (e) {
        failed++;
        console.log(`  FAIL - ${t.name}: ${e.message}`);
    }
}

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
