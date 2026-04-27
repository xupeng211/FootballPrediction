'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
    DEFAULT_SEASONS,
    EXPANSION_TARGETS,
    buildAdaptedCsvPath,
    buildPlan,
    main,
    normalizeSeasonInput,
    parseArgs,
    resolveTargets,
    runCommand,
    runComplianceHarvest,
    runCsvFlow,
    runDiscovery,
    runPostProcessing,
    writeReport,
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

test('batch_historical_backfill CLI 应覆盖防御性参数分支', () => {
    const absoluteOutput = path.join(os.tmpdir(), 'expansion.csv');
    const options = parseArgs([
        '',
        '--dry-run',
        '--fotmob-compliance',
        '--skip-discovery',
        '--skip-csv',
        '--skip-elo',
        '--skip-l3',
        '--output-dir',
        absoluteOutput,
        '--harvest-limit',
        '7',
        '--leagues',
        'D2,146,D2',
        '--seasons',
        '2022/2023,20222023',
    ]);
    const plan = buildPlan(options);

    assert.equal(options.commit, false);
    assert.equal(options.dryRun, true);
    assert.equal(options.fotmobCompliance, true);
    assert.equal(options.skipDiscovery, true);
    assert.equal(options.skipCsv, true);
    assert.equal(options.skipElo, true);
    assert.equal(options.skipL3, true);
    assert.equal(options.outputDir, absoluteOutput);
    assert.equal(options.harvestLimit, 7);
    assert.deepEqual(plan.seasons, ['2022/2023']);
    assert.deepEqual(
        plan.targets.map(target => target.code),
        ['D2']
    );

    assert.throws(() => parseArgs(['--leagues']), /参数 --leagues 缺少值/);
    assert.throws(() => parseArgs(['--harvest-limit', '0']), /参数 --harvest-limit 必须是正整数/);
    assert.throws(() => parseArgs(['--unknown']), /未知参数/);
    assert.throws(() => resolveTargets(['NOPE']), /未支持的扩军联赛/);
});

test('batch_historical_backfill 编排辅助函数应支持安全短路与失败降级', async () => {
    const target = resolveTargets(['D2'])[0];
    const outputPath = buildAdaptedCsvPath('/tmp/expansion-output', target, '2022/2023');

    assert.equal(outputPath, '/tmp/expansion-output/D2_2223_adapted.csv');
    assert.equal(runCsvFlow(target, '2022/2023', { skipCsv: true }), null);
    assert.doesNotThrow(() => runDiscovery(target, '2022/2023', { skipDiscovery: true, fotmobCompliance: true }));
    assert.doesNotThrow(() => runDiscovery(target, '2022/2023', { skipDiscovery: false, fotmobCompliance: false }));
    assert.doesNotThrow(() => runComplianceHarvest(target, '2022/2023', { fotmobCompliance: false, dryRun: false }));
    assert.doesNotThrow(() => runComplianceHarvest(target, '2022/2023', { fotmobCompliance: true, dryRun: true }));
    assert.doesNotThrow(() => runPostProcessing({ skipElo: true, skipL3: true }));

    const originalLog = console.log;
    console.log = () => {};
    try {
        assert.equal(await main(['--help']), null);
    } finally {
        console.log = originalLog;
    }

    const originalMkdirSync = fs.mkdirSync;
    const originalWarn = console.warn;
    fs.mkdirSync = () => {
        throw new Error('locked');
    };
    console.warn = () => {};
    try {
        assert.equal(writeReport({ ok: true }), null);
    } finally {
        fs.mkdirSync = originalMkdirSync;
        console.warn = originalWarn;
    }

    assert.doesNotThrow(() => runCommand('成功命令', process.execPath, ['-e', 'process.exit(0)']));
    assert.throws(() => runCommand('失败命令', process.execPath, ['-e', 'process.exit(3)']), /失败命令 失败: exit=3/);
});

test('batch_historical_backfill 主流程 dry-run 应在全跳过模式下生成收口报告', async () => {
    const originalLog = console.log;
    console.log = () => {};
    try {
        const report = await main([
            '--dry-run',
            '--skip-discovery',
            '--skip-csv',
            '--skip-elo',
            '--skip-l3',
            '--leagues',
            'D2',
            '--season',
            '2022/2023',
        ]);

        assert.equal(report.mode, 'dry-run');
        assert.equal(report.expectedMatches, 306);
        assert.deepEqual(report.seasons, ['2022/2023']);
        assert.deepEqual(
            report.targets.map(target => target.code),
            ['D2']
        );
        assert.deepEqual(report.csvFiles, []);
        assert.match(report.startedAt, /^\d{4}-\d{2}-\d{2}T/);
        assert.match(report.finishedAt, /^\d{4}-\d{2}-\d{2}T/);
    } finally {
        console.log = originalLog;
    }
});

test('batch_historical_backfill 应按顺序编排真实入口但允许测试替换命令执行器', () => {
    const calls = [];
    const commandRunner = (label, command, args, options = {}) => {
        calls.push({ label, command, args, env: options.env || {} });
    };
    const target = resolveTargets(['D2'])[0];
    const outputDir = fs.mkdtempSync(path.join(os.tmpdir(), 'historical-backfill-'));

    runDiscovery(target, '2022/2023', {
        dryRun: true,
        fotmobCompliance: true,
        skipDiscovery: false,
        commandRunner,
    });
    const csvPath = runCsvFlow(target, '2022/2023', {
        commit: true,
        skipCsv: false,
        outputDir,
        commandRunner,
    });
    runComplianceHarvest(target, '2022/2023', {
        dryRun: false,
        fotmobCompliance: true,
        harvestLimit: 3,
        commandRunner,
    });
    runPostProcessing({ dryRun: true, skipElo: false, skipL3: false, commandRunner });

    assert.equal(csvPath, path.join(outputDir, 'D2_2223_adapted.csv'));
    assert.deepEqual(
        calls.map(call => call.label),
        [
            'L1 低频播种 2. Bundesliga 2022/2023',
            '下载并适配 CSV D2 2022/2023',
            '导入 matches / bookmaker_odds_history 2. Bundesliga 2022/2023',
            'FOTMOB 合规低频 L2 2. Bundesliga 2022/2023',
            'ELO 全量重算',
            'L3 特征熔炼',
        ]
    );
    assert.equal(calls[0].command, 'node');
    assert.ok(calls[0].args.includes('--dry-run'));
    assert.equal(calls[0].env.FOTMOB_COMPLIANCE_MODE, 'true');
    assert.deepEqual(calls[1].args.slice(0, 5), [
        'scripts/ops/fetch_and_adapt_euro_leagues.js',
        '--league-code',
        'D2',
        '--season-code',
        '2223',
    ]);
    assert.ok(calls[2].args.includes('--commit'));
    assert.ok(calls[3].args.includes('--limit'));
    assert.ok(calls[3].args.includes('3'));
    assert.equal(calls[3].env.MAX_WORKERS, '1');
    assert.ok(calls[4].args.includes('--dry-run'));
    assert.ok(calls[5].args.includes('--dry-run'));
});
