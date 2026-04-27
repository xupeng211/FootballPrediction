#!/usr/bin/env node
'use strict';

/**
 * 横向大扩军 - 历史 CSV / FotMob / ELO / L3 批量编排入口。
 *
 * 该脚本只编排仓库已有真实入口，不生成模拟数据：
 * - scripts/ops/titan_discovery.js
 * - scripts/ops/fetch_and_adapt_euro_leagues.js
 * - scripts/ops/csv_bulk_loader.js
 * - scripts/ops/run_production.js
 * - scripts/maintenance/recalculate_elo.js
 * - scripts/ops/smelt_all.js
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const { Normalizer } = require('../../src/utils/Normalizer');

const REPO_ROOT = path.resolve(__dirname, '../..');
const DEFAULT_SEASONS = ['2022/2023', '2023/2024', '2024/2025'];
const DEFAULT_OUTPUT_DIR = path.join(REPO_ROOT, 'data', 'historical_csv', 'adapted');
const DEFAULT_ERROR_LOG = path.join(REPO_ROOT, 'logs', 'batch_historical_backfill_csv_errors.jsonl');
const DEFAULT_HARVEST_LIMIT = 25;

const SEASON_CODE_BY_SEASON = {
    '2022/2023': '2223',
    '2023/2024': '2324',
    '2024/2025': '2425',
};

const EXPANSION_TARGETS = [
    { id: 47, code: 'E0', name: 'Premier League', expectedMatches: 380, group: 'core' },
    { id: 87, code: 'SP1', name: 'La Liga', expectedMatches: 380, group: 'core' },
    { id: 54, code: 'D1', name: 'Bundesliga', expectedMatches: 306, group: 'core' },
    { id: 55, code: 'I1', name: 'Serie A', expectedMatches: 380, group: 'core' },
    { id: 53, code: 'F1', name: 'Ligue 1', expectedMatches: 306, group: 'core' },
    { id: 48, code: 'E1', name: 'Championship', expectedMatches: 552, group: 'expansion' },
    { id: 146, code: 'D2', name: '2. Bundesliga', expectedMatches: 306, group: 'expansion' },
    { id: 140, code: 'SP2', name: 'Segunda División', expectedMatches: 462, group: 'expansion' },
    { id: 86, code: 'I2', name: 'Serie B', expectedMatches: 380, group: 'expansion' },
    { id: 110, code: 'F2', name: 'Ligue 2', expectedMatches: 380, group: 'expansion' },
    { id: 57, code: 'N1', name: 'Eredivisie', expectedMatches: 306, group: 'expansion' },
    { id: 61, code: 'P1', name: 'Liga Portugal', expectedMatches: 306, group: 'expansion' },
];

const TARGETS_BY_ID = new Map(EXPANSION_TARGETS.map(target => [String(target.id), target]));
const TARGETS_BY_CODE = new Map(EXPANSION_TARGETS.map(target => [target.code, target]));

function printUsage() {
    console.log(`
横向大扩军历史回填编排

用法:
  node scripts/ops/batch_historical_backfill.js --commit --fotmob-compliance
  node scripts/ops/batch_historical_backfill.js --dry-run --leagues E1,D2,SP2,I2,F2,N1,P1 --seasons 2022/2023,2023/2024,2024/2025

选项:
  --commit                 实际写入数据库；默认只做 dry-run
  --dry-run                显式预览，不写数据库
  --fotmob-compliance      在 FOTMOB_COMPLIANCE_MODE=true 下低频补齐 L1/L2
  --leagues <list>         联赛 ID 或 football-data 代码，逗号分隔；默认 12 项扩军清单
  --seasons <list>         赛季列表，逗号分隔；默认 2022/2023,2023/2024,2024/2025
  --output-dir <path>      适配后 CSV 输出目录
  --harvest-limit <n>      合规 L2 每个联赛/赛季最多收割条数，默认 ${DEFAULT_HARVEST_LIMIT}
  --skip-discovery         跳过 L1 播种
  --skip-csv               跳过 football-data CSV 适配与导入
  --skip-elo               跳过 Elo 全量重算
  --skip-l3                跳过 L3 熔炼
`);
}

function readOptionValue(argv, index, flag) {
    const value = argv[index + 1];
    if (!value || String(value).startsWith('--')) {
        throw new Error(`参数 ${flag} 缺少值`);
    }
    return value;
}

function parseList(rawValue) {
    return String(rawValue || '')
        .split(',')
        .map(value => value.trim())
        .filter(Boolean);
}

function parsePositiveInteger(rawValue, flag) {
    const parsed = Number.parseInt(rawValue, 10);
    if (!Number.isInteger(parsed) || parsed <= 0) {
        throw new Error(`参数 ${flag} 必须是正整数`);
    }
    return parsed;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        commit: false,
        dryRun: false,
        fotmobCompliance: false,
        leagueTokens: [],
        seasons: DEFAULT_SEASONS,
        outputDir: DEFAULT_OUTPUT_DIR,
        harvestLimit: DEFAULT_HARVEST_LIMIT,
        skipDiscovery: false,
        skipCsv: false,
        skipElo: false,
        skipL3: false,
    };

    for (let index = 0; index < argv.length; index++) {
        const token = String(argv[index] || '').trim();
        if (!token) {
            continue;
        }
        index = applyArgToken(options, argv, index, token);
    }

    if (!options.commit) {
        options.dryRun = true;
    }
    options.outputDir = path.isAbsolute(options.outputDir)
        ? options.outputDir
        : path.resolve(REPO_ROOT, options.outputDir);

    return options;
}

function applyArgToken(options, argv, index, token) {
    if (token === '--help' || token === '-h') {
        options.help = true;
        return index;
    }
    if (token === '--commit') {
        options.commit = true;
        options.dryRun = false;
        return index;
    }
    if (token === '--dry-run') {
        options.dryRun = true;
        options.commit = false;
        return index;
    }
    if (token === '--fotmob-compliance') {
        options.fotmobCompliance = true;
        return index;
    }
    if (token === '--skip-discovery') {
        options.skipDiscovery = true;
        return index;
    }
    if (token === '--skip-csv') {
        options.skipCsv = true;
        return index;
    }
    if (token === '--skip-elo') {
        options.skipElo = true;
        return index;
    }
    if (token === '--skip-l3') {
        options.skipL3 = true;
        return index;
    }
    return applyValueArgToken(options, argv, index, token);
}

function applyValueArgToken(options, argv, index, token) {
    if (token === '--leagues') {
        options.leagueTokens = parseList(readOptionValue(argv, index, token));
        return index + 1;
    }
    if (token === '--seasons' || token === '--season') {
        options.seasons = parseList(readOptionValue(argv, index, token));
        return index + 1;
    }
    if (token === '--output-dir') {
        options.outputDir = readOptionValue(argv, index, token);
        return index + 1;
    }
    if (token === '--harvest-limit') {
        options.harvestLimit = parsePositiveInteger(readOptionValue(argv, index, token), token);
        return index + 1;
    }
    throw new Error(`未知参数: ${token}`);
}

function normalizeSeasonInput(season) {
    const normalized = Normalizer.normalizeSeason(String(season || '').trim());
    if (!SEASON_CODE_BY_SEASON[normalized]) {
        throw new Error(`未支持的扩军赛季: ${season}`);
    }
    return normalized;
}

function resolveTargets(leagueTokens = []) {
    if (!leagueTokens.length) {
        return [...EXPANSION_TARGETS];
    }

    const targets = leagueTokens.map(token => {
        const normalized = String(token).trim().toUpperCase();
        const target = TARGETS_BY_ID.get(normalized) || TARGETS_BY_CODE.get(normalized);
        if (!target) {
            throw new Error(`未支持的扩军联赛: ${token}`);
        }
        return target;
    });

    return [...new Map(targets.map(target => [target.id, target])).values()];
}

function buildPlan(options) {
    const seasons = [...new Set(options.seasons.map(normalizeSeasonInput))];
    const targets = resolveTargets(options.leagueTokens);
    return {
        seasons,
        targets,
        expectedMatches: seasons.length * targets.reduce((sum, target) => sum + target.expectedMatches, 0),
    };
}

function runCommand(label, command, args, options = {}) {
    const printable = [command, ...args].join(' ');
    console.log(`\n[EXPANSION] ${label}`);
    console.log(`[EXPANSION] $ ${printable}`);

    const result = spawnSync(command, args, {
        cwd: REPO_ROOT,
        stdio: 'inherit',
        env: {
            ...process.env,
            ...(options.env || {}),
        },
    });

    if (result.status !== 0) {
        throw new Error(`${label} 失败: exit=${result.status}`);
    }
}

function buildAdaptedCsvPath(outputDir, target, season) {
    const seasonCode = SEASON_CODE_BY_SEASON[season];
    return path.join(outputDir, `${target.code}_${seasonCode}_adapted.csv`);
}

function runDiscovery(target, season, options) {
    if (options.skipDiscovery || !options.fotmobCompliance) {
        return;
    }

    const commandRunner = options.commandRunner || runCommand;
    const args = [
        'scripts/ops/titan_discovery.js',
        `--league=${target.id}`,
        `--season=${season}`,
        '--full-sync',
        '--concurrency=1',
        '--lookback=2000',
        '--lookahead=2000',
    ];
    if (options.dryRun) {
        args.push('--dry-run');
    }

    commandRunner(`L1 低频播种 ${target.name} ${season}`, 'node', args, {
        env: { FOTMOB_COMPLIANCE_MODE: 'true' },
    });
}

function runCsvFlow(target, season, options) {
    if (options.skipCsv) {
        return null;
    }

    const outputPath = buildAdaptedCsvPath(options.outputDir, target, season);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    const commandRunner = options.commandRunner || runCommand;

    commandRunner(`下载并适配 CSV ${target.code} ${season}`, 'node', [
        'scripts/ops/fetch_and_adapt_euro_leagues.js',
        '--league-code',
        target.code,
        '--season-code',
        SEASON_CODE_BY_SEASON[season],
        '--output',
        outputPath,
    ]);

    const loaderArgs = [
        'scripts/ops/csv_bulk_loader.js',
        '--file',
        outputPath,
        '--batch-size',
        '500',
        '--error-log',
        DEFAULT_ERROR_LOG,
    ];
    if (options.commit) {
        loaderArgs.push('--commit');
    }

    commandRunner(`导入 matches / bookmaker_odds_history ${target.name} ${season}`, 'node', loaderArgs);
    return outputPath;
}

function runComplianceHarvest(target, season, options) {
    if (!options.fotmobCompliance || options.dryRun) {
        return;
    }

    const commandRunner = options.commandRunner || runCommand;
    commandRunner(
        `FOTMOB 合规低频 L2 ${target.name} ${season}`,
        'node',
        [
            'scripts/ops/run_production.js',
            '--league-ids',
            String(target.id),
            '--season',
            season,
            '--finished-only',
            '--workers',
            '1',
            '--limit',
            String(options.harvestLimit),
            '--progress-every',
            '10',
        ],
        {
            env: {
                FOTMOB_COMPLIANCE_MODE: 'true',
                MAX_WORKERS: '1',
            },
        }
    );
}

function runPostProcessing(options) {
    const commandRunner = options.commandRunner || runCommand;
    if (!options.skipElo) {
        commandRunner('ELO 全量重算', 'node', [
            'scripts/maintenance/recalculate_elo.js',
            ...(options.dryRun ? ['--dry-run'] : []),
        ]);
    }

    if (!options.skipL3) {
        commandRunner('L3 特征熔炼', 'node', ['scripts/ops/smelt_all.js', ...(options.dryRun ? ['--dry-run'] : [])]);
    }
}

function writeReport(report) {
    try {
        fs.mkdirSync(path.join(REPO_ROOT, 'logs'), { recursive: true });
        const reportPath = path.join(REPO_ROOT, 'logs', `batch_historical_backfill_${Date.now()}.json`);
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        console.log(`\n[EXPANSION] 报告已写入 ${path.relative(REPO_ROOT, reportPath)}`);
        return reportPath;
    } catch (error) {
        console.warn(`[EXPANSION] WARN: 报告写入失败，主流程已完成: ${error.message}`);
        return null;
    }
}

async function main(argv = process.argv.slice(2)) {
    const options = parseArgs(argv);
    if (options.help) {
        printUsage();
        return null;
    }

    const plan = buildPlan(options);
    const report = {
        startedAt: new Date().toISOString(),
        mode: options.commit ? 'commit' : 'dry-run',
        fotmobCompliance: options.fotmobCompliance,
        seasons: plan.seasons,
        targets: plan.targets.map(({ id, code, name, expectedMatches, group }) => ({
            id,
            code,
            name,
            expectedMatches,
            group,
        })),
        expectedMatches: plan.expectedMatches,
        csvFiles: [],
    };

    console.log('[EXPANSION] 横向大扩军计划启动');
    console.log(
        `[EXPANSION] seasons=${plan.seasons.join(',')} targets=${plan.targets.length} expected_matches=${plan.expectedMatches}`
    );

    for (const season of plan.seasons) {
        for (const target of plan.targets) {
            runDiscovery(target, season, options);
            const csvPath = runCsvFlow(target, season, options);
            if (csvPath) {
                report.csvFiles.push(path.relative(REPO_ROOT, csvPath));
            }
            runComplianceHarvest(target, season, options);
        }
    }

    runPostProcessing(options);

    report.finishedAt = new Date().toISOString();
    writeReport(report);
    console.log('[EXPANSION] 横向大扩军计划完成');
    return report;
}

/* node:coverage ignore next 6 */
if (require.main === module) {
    main().catch(error => {
        console.error(`[EXPANSION] 失败: ${error.message}`);
        process.exit(1);
    });
}

module.exports = {
    DEFAULT_SEASONS,
    EXPANSION_TARGETS,
    SEASON_CODE_BY_SEASON,
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
};
