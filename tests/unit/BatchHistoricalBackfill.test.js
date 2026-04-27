'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    DEFAULT_SEASONS,
    EXPANSION_TARGETS,
    buildPlan,
    normalizeSeasonInput,
    parseArgs,
    resolveTargets,
} = require('../../scripts/ops/batch_historical_backfill');

test('batch_historical_backfill 默认覆盖三季和 12 个扩军目标', () => {
    const options = parseArgs([]);
    const plan = buildPlan(options);

    assert.deepEqual(plan.seasons, DEFAULT_SEASONS);
    assert.equal(plan.targets.length, 12);
    assert.equal(plan.expectedMatches, 13332);
    assert.equal(new Set(plan.targets.map(target => target.id)).size, plan.targets.length);
});

test('batch_historical_backfill 应支持按 football-data 代码缩小目标', () => {
    const options = parseArgs(['--commit', '--leagues', 'E1,D2,SP2,I2,F2,N1,P1', '--season', '2022/2023']);
    const plan = buildPlan(options);

    assert.equal(options.commit, true);
    assert.equal(options.dryRun, false);
    assert.deepEqual(plan.seasons, ['2022/2023']);
    assert.deepEqual(
        plan.targets.map(target => target.code),
        ['E1', 'D2', 'SP2', 'I2', 'F2', 'N1', 'P1']
    );
    assert.equal(plan.expectedMatches, 2692);
});

test('batch_historical_backfill 应规范化赛季并拒绝未规划赛季', () => {
    assert.equal(normalizeSeasonInput('20222023'), '2022/2023');
    assert.throws(() => normalizeSeasonInput('2021/2022'), /未支持的扩军赛季/);
});

test('batch_historical_backfill 扩军目标应包含真实 FotMob 二级联赛 ID', () => {
    const targets = resolveTargets(['D2', 'SP2', 'I2', 'F2']);

    assert.deepEqual(
        targets.map(target => target.id),
        [146, 140, 86, 110]
    );
    assert.equal(
        EXPANSION_TARGETS.some(target => target.id === 77 && target.code === 'D2'),
        false
    );
});
