#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { once } = require('events');
const { Readable, Writable } = require('stream');
const { pipeline } = require('stream/promises');
const csv = require('csv-parser');
const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const { EntityMapper, WARNING_LOW_QUALITY_SOURCE } = require('../../src/infrastructure/etl/EntityMapper');
const { REPO_ROOT, buildDbConnectionConfig } = require('./helpers/dbBlueprint');

const MATCH_REUSE_WINDOW_MS = 2 * 60 * 60 * 1000;
const FOOTBALL_DATA_LEAGUES = {
    E0: 'Premier League',
    SP1: 'La Liga',
    D1: 'Bundesliga',
    I1: 'Serie A',
    F1: 'Ligue 1',
};
const SEASON_CANDIDATES = [
    {
        seasonCode: '2425',
        season: '2024-2025',
    },
    {
        seasonCode: '2324',
        season: '2023-2024',
    },
    {
        seasonCode: '2223',
        season: '2022-2023',
    },
    {
        seasonCode: '2122',
        season: '2021-2022',
    },
    {
        seasonCode: '2021',
        season: '2020-2021',
    },
];
const OUTPUT_PATH = path.join(REPO_ROOT, 'data', 'mock', 'real_euro_league_adapted.csv');
const OUTPUT_HEADERS = [
    'match_id',
    'external_id',
    'league_name',
    'season',
    'home_team',
    'away_team',
    'match_date',
    'status',
    'bookmaker_name',
    'market_type',
    'open_line',
    'open_home',
    'open_draw',
    'open_away',
    'close_line',
    'close_home',
    'close_draw',
    'close_away',
    'home_score',
    'away_score',
    'quality_flags',
];
const MARKET_CONFIGS = [
    {
        bookmakerName: 'Bet365',
        marketType: '1x2',
        openColumns: { home: 'B365H', draw: 'B365D', away: 'B365A' },
        closeColumns: { home: 'B365CH', draw: 'B365CD', away: 'B365CA' },
    },
    {
        bookmakerName: 'Pinnacle',
        marketType: '1x2',
        openColumns: { home: 'PSH', draw: 'PSD', away: 'PSA' },
        closeColumns: { home: 'PSCH', draw: 'PSCD', away: 'PSCA' },
    },
    {
        bookmakerName: 'William Hill',
        marketType: '1x2',
        openColumns: { home: 'WHH', draw: 'WHD', away: 'WHA' },
        closeColumns: { home: 'WHCH', draw: 'WHCD', away: 'WHCA' },
    },
    {
        bookmakerName: 'Ladbrokes',
        marketType: '1x2',
        openColumns: { home: 'LBH', draw: 'LBD', away: 'LBA' },
        closeColumns: { home: 'LBCH', draw: 'LBCD', away: 'LBCA' },
    },
    {
        bookmakerName: 'Bwin',
        marketType: '1x2',
        openColumns: { home: 'BWH', draw: 'BWD', away: 'BWA' },
        closeColumns: { home: 'BWCH', draw: 'BWCD', away: 'BWCA' },
    },
    {
        bookmakerName: 'Betfair',
        marketType: '1x2',
        openColumns: { home: 'BFH', draw: 'BFD', away: 'BFA' },
        closeColumns: { home: 'BFCH', draw: 'BFCD', away: 'BFCA' },
    },
    {
        bookmakerName: 'Bet365',
        marketType: 'Asian Handicap',
        openColumns: { home: 'B365AHH', away: 'B365AHA' },
        closeColumns: { home: 'B365CAHH', away: 'B365CAHA' },
        openLineColumn: 'AHh',
        closeLineColumn: 'AHCh',
    },
    {
        bookmakerName: 'Pinnacle',
        marketType: 'Asian Handicap',
        openColumns: { home: 'PAHH', away: 'PAHA' },
        closeColumns: { home: 'PCAHH', away: 'PCAHA' },
        openLineColumn: 'AHh',
        closeLineColumn: 'AHCh',
    },
    {
        bookmakerName: 'Betfair Exchange',
        marketType: 'Asian Handicap',
        openColumns: { home: 'BFEAHH', away: 'BFEAHA' },
        closeColumns: { home: 'BFECAHH', away: 'BFECAHA' },
        openLineColumn: 'AHh',
        closeLineColumn: 'AHCh',
    },
    {
        bookmakerName: 'Bet365',
        marketType: 'Over/Under',
        openColumns: { over: 'B365>2.5', under: 'B365<2.5' },
        closeColumns: { over: 'B365C>2.5', under: 'B365C<2.5' },
        openLineValue: '2.5',
        closeLineValue: '2.5',
    },
    {
        bookmakerName: 'Pinnacle',
        marketType: 'Over/Under',
        openColumns: { over: 'P>2.5', under: 'P<2.5' },
        closeColumns: { over: 'PC>2.5', under: 'PC<2.5' },
        openLineValue: '2.5',
        closeLineValue: '2.5',
    },
    {
        bookmakerName: 'Betfair Exchange',
        marketType: 'Over/Under',
        openColumns: { over: 'BFE>2.5', under: 'BFE<2.5' },
        closeColumns: { over: 'BFEC>2.5', under: 'BFEC<2.5' },
        openLineValue: '2.5',
        closeLineValue: '2.5',
    },
];

function normalizeText(value) {
    return String(value || '')
        .replace(/\s+/g, ' ')
        .trim();
}

function toCsvCell(value) {
    const normalized = value === null || value === undefined ? '' : String(value);
    if (!/[",\n]/.test(normalized)) {
        return normalized;
    }

    return `"${normalized.replace(/"/g, '""')}"`;
}

function formatCsvLine(row) {
    return `${OUTPUT_HEADERS.map(header => toCsvCell(row[header] ?? '')).join(',')}\n`;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        seasonCode: null,
        leagueCode: 'E0',
    };

    for (let index = 0; index < argv.length; index++) {
        const token = String(argv[index] || '').trim();
        if (!token) {
            continue;
        }

        if (token === '--season-code') {
            const value = argv[index + 1];
            if (!value || String(value).startsWith('--')) {
                throw new Error('参数 --season-code 缺少值');
            }
            options.seasonCode = normalizeText(value);
            index += 1;
            continue;
        }

        if (token === '--league-code') {
            const value = argv[index + 1];
            if (!value || String(value).startsWith('--')) {
                throw new Error('参数 --league-code 缺少值');
            }
            options.leagueCode = normalizeText(value).toUpperCase();
            index += 1;
            continue;
        }

        if (token === '--help' || token === '-h') {
            options.help = true;
            continue;
        }

        throw new Error(`未知参数: ${token}`);
    }

    return options;
}

function printUsage() {
    console.log(
        '用法: node scripts/ops/fetch_and_adapt_euro_leagues.js [--league-code E0|SP1|D1|I1|F1] [--season-code 2425]'
    );
    console.log('说明: 默认抓取英超最新可用赛季；传入 --season-code 时只处理指定赛季。');
}

function parseFootballDataDateTime(dateValue, timeValue) {
    const dateText = normalizeText(dateValue);
    if (!dateText) {
        throw new Error('Date 缺失');
    }

    const match = dateText.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
    if (!match) {
        throw new Error(`无法识别的 Date: ${dateValue}`);
    }

    const day = Number.parseInt(match[1], 10);
    const month = Number.parseInt(match[2], 10);
    let year = Number.parseInt(match[3], 10);
    if (year < 100) {
        year += 2000;
    }

    const timeText = normalizeText(timeValue) || '15:00';
    const timeMatch = timeText.match(/^(\d{1,2}):(\d{2})$/);
    const hour = timeMatch ? Number.parseInt(timeMatch[1], 10) : 15;
    const minute = timeMatch ? Number.parseInt(timeMatch[2], 10) : 0;

    return new Date(Date.UTC(year, month - 1, day, hour, minute, 0)).toISOString();
}

function compareCandidatePriority(left, right) {
    const leftPriority = left.data_source === 'CSV_BULK_LOADER' ? 1 : 0;
    const rightPriority = right.data_source === 'CSV_BULK_LOADER' ? 1 : 0;
    if (leftPriority !== rightPriority) {
        return leftPriority - rightPriority;
    }

    return String(left.match_id).localeCompare(String(right.match_id));
}

function extractOddsValues(row, columns = {}) {
    return Object.fromEntries(
        Object.entries(columns).map(([key, columnName]) => [key, normalizeText(row[columnName])])
    );
}

function hasAnyOddsValue(oddsValues) {
    return Object.values(oddsValues).some(value => value !== '');
}

function hasCompleteOddsTriplet(oddsValues) {
    return Object.values(oddsValues).every(value => value !== '');
}

function resolveLineValue(row, config, phase) {
    if (phase === 'open' && config.openLineValue) {
        return normalizeText(config.openLineValue);
    }
    if (phase === 'close' && config.closeLineValue) {
        return normalizeText(config.closeLineValue);
    }

    const columnName = phase === 'open' ? config.openLineColumn : config.closeLineColumn;
    if (!columnName) {
        return '';
    }

    return normalizeText(row[columnName]);
}

function mapOutcomeColumns(config, values) {
    if (config.marketType === 'Over/Under') {
        return {
            primary: values.over || '',
            middle: '',
            secondary: values.under || '',
        };
    }

    return {
        primary: values.home || '',
        middle: values.draw || '',
        secondary: values.away || '',
    };
}

function buildExpandedOddsRows(row, context, matchCore) {
    const rows = [];

    for (const config of MARKET_CONFIGS) {
        const openValues = extractOddsValues(row, config.openColumns);
        const closeValues = extractOddsValues(row, config.closeColumns);
        const openLine = resolveLineValue(row, config, 'open');
        const closeLine = resolveLineValue(row, config, 'close') || openLine;
        const hasOpenOdds = hasCompleteOddsTriplet(openValues);
        const hasCloseOdds = hasCompleteOddsTriplet(closeValues);

        if (!hasAnyOddsValue(openValues) && !hasAnyOddsValue(closeValues)) {
            continue;
        }

        const openColumns = mapOutcomeColumns(config, openValues);
        const closeColumns = mapOutcomeColumns(config, closeValues);
        const qualityFlags = context.mapper.buildSourceQualityFlags({ hasOpenOdds });

        rows.push({
            ...matchCore,
            bookmaker_name: config.bookmakerName,
            market_type: config.marketType,
            open_line: openLine,
            open_home: openColumns.primary,
            open_draw: openColumns.middle,
            open_away: openColumns.secondary,
            close_line: closeLine,
            close_home: closeColumns.primary,
            close_draw: closeColumns.middle,
            close_away: closeColumns.secondary,
            quality_flags: qualityFlags.join(';'),
        });
    }

    return rows;
}

class ExistingMatchResolver {
    constructor(options = {}) {
        this.mapper = options.mapper || new EntityMapper();
        this.leagueName = options.leagueName || '';
        this.season = Normalizer.normalizeSeason(options.season || '');
        this.pool = options.pool || new Pool(buildDbConnectionConfig());
        this.ownsPool = !options.pool;
        this.matchesByKey = new Map();
        this.candidateCount = 0;
        this.loaded = false;
    }

    async load() {
        if (this.loaded) {
            return this;
        }

        const client = await this.pool.connect();
        try {
            const leagueName = this.mapper.normalizeLeagueName(this.leagueName);
            const result = await client.query(
                `
        SELECT
          match_id,
          external_id,
          home_team,
          away_team,
          match_date,
          data_source,
          data_version
        FROM matches
        WHERE season = $1
          AND league_name = $2
          AND COALESCE(data_source, '') <> 'CSV_BULK_LOADER'
          AND match_date IS NOT NULL
      `,
                [this.season, leagueName]
            );

            for (const row of result.rows) {
                const key = this.mapper.buildMatchLookupKey(row.home_team, row.away_team);
                const bucket = this.matchesByKey.get(key) || [];
                bucket.push(row);
                this.matchesByKey.set(key, bucket);
            }

            this.candidateCount = result.rows.length;
            this.loaded = true;
            return this;
        } finally {
            client.release();
        }
    }

    findMatch(options = {}) {
        const matchDate = new Date(options.matchDate);
        if (Number.isNaN(matchDate.getTime())) {
            return null;
        }

        const key = this.mapper.buildMatchLookupKey(options.homeTeam, options.awayTeam);
        const candidates = (this.matchesByKey.get(key) || [])
            .map(candidate => {
                const candidateDate = new Date(candidate.match_date);
                return {
                    ...candidate,
                    diffMs: Math.abs(matchDate.getTime() - candidateDate.getTime()),
                };
            })
            .filter(candidate => candidate.diffMs <= MATCH_REUSE_WINDOW_MS)
            .sort((left, right) => left.diffMs - right.diffMs || compareCandidatePriority(left, right));

        return candidates[0] || null;
    }

    async close() {
        if (!this.ownsPool) {
            return;
        }
        await this.pool.end();
    }
}

function buildMatchId(options = {}) {
    const existingMatch = options.resolver?.findMatch({
        homeTeam: options.homeTeam,
        awayTeam: options.awayTeam,
        matchDate: options.matchDate,
    });

    if (!existingMatch) {
        throw new Error(
            `未找到对应 FotMob 比赛: league=${options.leagueName} season=${Normalizer.normalizeSeason(options.season)} ` +
                `home=${options.homeTeam} away=${options.awayTeam} match_date=${options.matchDate}`
        );
    }

    const identity = options.mapper.bindFotMobIdentity(existingMatch);
    return {
        matchId: identity.matchId,
        externalId: identity.externalId,
        reusedExisting: true,
        matchedSource: existingMatch.data_source || '',
        matchedDate: existingMatch.match_date,
    };
}

function resolveLeagueMeta(options = {}, mapper = new EntityMapper()) {
    const leagueCode = normalizeText(options.leagueCode || 'E0').toUpperCase();
    const rawLeagueName = FOOTBALL_DATA_LEAGUES[leagueCode];
    if (!rawLeagueName) {
        throw new Error(`未支持的联赛代码: ${leagueCode}`);
    }

    const leagueName = mapper.normalizeLeagueName(rawLeagueName);
    const matchedLeague = (mapper.activeLeagues || []).find(
        league => normalizeText(league?.name) === normalizeText(leagueName)
    );
    const leagueId = Number(matchedLeague?.id || 0);
    if (!Number.isFinite(leagueId) || leagueId <= 0) {
        throw new Error(`未在 Atlas 配置中找到联赛: ${leagueName}`);
    }

    return {
        leagueCode,
        leagueName,
        leagueId,
    };
}

function adaptSourceRow(row, context) {
    const rawHomeTeam = normalizeText(row.HomeTeam);
    const rawAwayTeam = normalizeText(row.AwayTeam);
    if (!rawHomeTeam || !rawAwayTeam) {
        throw new Error('HomeTeam / AwayTeam 缺失');
    }

    const homeTeam = context.mapper.normalizeTeamName(rawHomeTeam);
    const awayTeam = context.mapper.normalizeTeamName(rawAwayTeam);
    const matchDate = parseFootballDataDateTime(row.Date, row.Time);
    const matchIdResolution = buildMatchId({
        leagueName: context.leagueMeta.leagueName,
        season: context.sourceMeta.season,
        matchDate,
        homeTeam,
        awayTeam,
        mapper: context.mapper,
        resolver: context.resolver,
    });
    const matchCore = {
        match_id: matchIdResolution.matchId,
        external_id: matchIdResolution.externalId,
        league_name: context.leagueMeta.leagueName,
        season: Normalizer.normalizeSeason(context.sourceMeta.season),
        home_team: homeTeam,
        away_team: awayTeam,
        match_date: matchDate,
        status: hasFinalScore(row) ? 'finished' : 'scheduled',
        home_score: normalizeText(row.FTHG),
        away_score: normalizeText(row.FTAG),
    };
    const expandedRows = buildExpandedOddsRows(row, context, matchCore);
    if (expandedRows.length === 0) {
        throw new Error('未提取到任何支持的赔率记录');
    }

    return {
        rows: expandedRows,
        diagnostics: {
            qualityFlags: [
                ...new Set(
                    expandedRows.flatMap(record => normalizeText(record.quality_flags).split(';').filter(Boolean))
                ),
            ],
            reusedExisting: matchIdResolution.reusedExisting,
            matchedSource: matchIdResolution.matchedSource,
            matchedDate: matchIdResolution.matchedDate,
        },
    };
}

function hasFinalScore(row) {
    return normalizeText(row.FTHG) !== '' && normalizeText(row.FTAG) !== '';
}

async function downloadToTempFile(sourceMeta) {
    const response = await fetch(sourceMeta.url, {
        headers: {
            'user-agent': 'FootballPrediction/TEP-001 CSV Adapter',
        },
    });

    if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status} ${response.statusText}`.trim());
    }

    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'football-data-euro-'));
    const tempFile = path.join(tempDir, `${sourceMeta.seasonCode}-${sourceMeta.leagueCode}.csv`);
    await pipeline(Readable.fromWeb(response.body), fs.createWriteStream(tempFile));

    return {
        ...sourceMeta,
        tempDir,
        tempFile,
    };
}

function resolveCandidateList(options = {}) {
    const leagueMeta = options.leagueMeta || resolveLeagueMeta(options);
    if (!options.seasonCode) {
        return SEASON_CANDIDATES.map(candidate => ({
            ...candidate,
            ...leagueMeta,
            url: `https://www.football-data.co.uk/mmz4281/${candidate.seasonCode}/${leagueMeta.leagueCode}.csv`,
        }));
    }

    const matched = SEASON_CANDIDATES.find(candidate => candidate.seasonCode === options.seasonCode);
    if (!matched) {
        throw new Error(`未配置的 seasonCode: ${options.seasonCode}`);
    }

    return [
        {
            ...matched,
            ...leagueMeta,
            url: `https://www.football-data.co.uk/mmz4281/${matched.seasonCode}/${leagueMeta.leagueCode}.csv`,
        },
    ];
}

async function resolveDownloadSource(options = {}) {
    const errors = [];
    for (const candidate of resolveCandidateList(options)) {
        try {
            const resolved = await downloadToTempFile(candidate);
            return resolved;
        } catch (error) {
            errors.push(`${candidate.seasonCode}: ${error.message}`);
        }
    }

    throw new Error(`所有联赛下载源都失败了: ${errors.join(' | ')}`);
}

class CollectingWriter extends Writable {
    constructor(sourceMeta, options = {}) {
        super({ objectMode: true });
        this.sourceMeta = sourceMeta;
        this.mapper = options.mapper || new EntityMapper();
        this.resolver = options.resolver || null;
        this.rows = [];
        this.skipped = 0;
        this.errors = [];
        this.stats = {
            reusedExisting: 0,
            unmatchedRows: 0,
            lowQualityRows: 0,
        };
        this.sourceQualityFlags = new Set();
    }

    _write(row, _encoding, callback) {
        try {
            const adapted = adaptSourceRow(row, {
                sourceMeta: this.sourceMeta,
                mapper: this.mapper,
                resolver: this.resolver,
                leagueMeta: this.sourceMeta,
            });
            this.rows.push(...adapted.rows);
            if (adapted.diagnostics.reusedExisting) {
                this.stats.reusedExisting += 1;
            }
            if (adapted.diagnostics.qualityFlags.length > 0) {
                this.stats.lowQualityRows += 1;
            }
            adapted.diagnostics.qualityFlags.forEach(flag => this.sourceQualityFlags.add(flag));
            callback();
        } catch (error) {
            this.skipped += 1;
            this.stats.unmatchedRows += 1;
            this.errors.push(error.message);
            callback();
        }
    }
}

async function parseAndAdaptCsv(sourceMeta, options = {}) {
    const collector = new CollectingWriter(sourceMeta, options);
    await pipeline(fs.createReadStream(sourceMeta.tempFile, { encoding: 'utf8' }), csv(), collector);

    return {
        rows: collector.rows,
        skipped: collector.skipped,
        errors: collector.errors,
        stats: collector.stats,
        sourceQualityFlags: [...collector.sourceQualityFlags],
    };
}

async function writeAdaptedCsv(outputPath, rows) {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    const output = fs.createWriteStream(outputPath, { encoding: 'utf8' });
    output.write(`${OUTPUT_HEADERS.join(',')}\n`);
    for (const row of rows) {
        output.write(formatCsvLine(row));
    }
    output.end();
    await once(output, 'finish');
}

function cleanupTempDir(tempDir) {
    if (!tempDir) {
        return;
    }

    fs.rmSync(tempDir, { recursive: true, force: true });
}

async function main() {
    const options = parseArgs();
    if (options.help) {
        printUsage();
        return;
    }

    const mapper = new EntityMapper();
    const leagueMeta = resolveLeagueMeta(options, mapper);
    const sourceMeta = await resolveDownloadSource({ ...options, leagueMeta });
    const resolver = new ExistingMatchResolver({
        mapper,
        leagueName: leagueMeta.leagueName,
        season: sourceMeta.season,
    });

    console.log(
        `[FETCH-EURO] 下载成功 league=${leagueMeta.leagueName} ` + `season=${sourceMeta.season} url=${sourceMeta.url}`
    );

    try {
        await resolver.load();
        console.log(
            `[FETCH-EURO] 现有候选加载 season=${Normalizer.normalizeSeason(sourceMeta.season)} ` +
                `league=${leagueMeta.leagueName} candidates=${resolver.candidateCount}`
        );

        const adapted = await parseAndAdaptCsv(sourceMeta, {
            mapper,
            resolver,
        });
        await writeAdaptedCsv(OUTPUT_PATH, adapted.rows);

        console.log(
            `[FETCH-EURO] 适配完成 output=${path.relative(REPO_ROOT, OUTPUT_PATH)} ` +
                `rows=${adapted.rows.length} skipped=${adapted.skipped} ` +
                `reused_existing=${adapted.stats.reusedExisting} unmatched_rows=${adapted.stats.unmatchedRows}`
        );

        if (adapted.sourceQualityFlags.includes(WARNING_LOW_QUALITY_SOURCE)) {
            console.log(
                `[FETCH-EURO] 数据源质量告警 flags=${adapted.sourceQualityFlags.join(',')} ` +
                    '原因=部分庄家/市场缺少开盘赔率，相关记录已带低质量标记'
            );
        } else {
            console.log('[FETCH-EURO] 数据源质量诊断: 已检测到 Bet365 开盘与收盘列');
        }

        if (adapted.rows[0]) {
            console.log('[FETCH-EURO] 首行样本:');
            console.log(JSON.stringify(adapted.rows[0], null, 2));
        }
        if (adapted.errors.length > 0) {
            console.log(`[FETCH-EURO] 跳过样本原因: ${adapted.errors.slice(0, 3).join(' | ')}`);
        }
    } finally {
        await resolver.close();
        cleanupTempDir(sourceMeta.tempDir);
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error(`[FETCH-EURO] 失败: ${error.message}`);
        process.exit(1);
    });
}

module.exports = {
    FOOTBALL_DATA_LEAGUES,
    ExistingMatchResolver,
    OUTPUT_PATH,
    SEASON_CANDIDATES,
    adaptSourceRow,
    buildMatchId,
    parseArgs,
    parseFootballDataDateTime,
    resolveLeagueMeta,
};
