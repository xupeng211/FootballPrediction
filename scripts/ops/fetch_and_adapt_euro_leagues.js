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
const {
    normalizeText,
    resolveCsvField,
    toCsvCell,
    formatCsvLine,
    parseFootballDataDateTime,
    MIN_CONFIDENCE_SCORE,
    MIN_ALIGNMENT_SCORE_GAP,
    selectBestAlignmentCandidate,
    extractOddsValues,
    hasAnyOddsValue,
    hasCompleteOddsTriplet,
    resolveLineValue,
    mapOutcomeColumns,
    buildExpandedOddsRows,
} = require('./helpers/euroLeagueAdapters');

const MATCH_REUSE_WINDOW_MS = 6 * 60 * 60 * 1000;
const FOOTBALL_DATA_LEAGUES = {
    E0: 'Premier League',
    SP1: 'La Liga',
    D1: 'Bundesliga',
    I1: 'Serie A',
    F1: 'Ligue 1',
};
const SEASON_CANDIDATES = [
    {
        seasonCode: '2526',
        season: '2025-2026',
    },
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
    'home_corners',
    'away_corners',
    'home_yellow_cards',
    'away_yellow_cards',
    'home_red_cards',
    'away_red_cards',
    'referee',
    'alignment_meta',
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

function buildOddsConfig(configs = []) {
    return configs.reduce((accumulator, config) => {
        const bookmakerBucket = accumulator[config.bookmakerName] || {};
        bookmakerBucket[config.marketType] = {
            open: { ...(config.openColumns || {}) },
            close: { ...(config.closeColumns || {}) },
            open_line: config.openLineColumn || '',
            close_line: config.closeLineColumn || '',
            open_line_value: config.openLineValue || '',
            close_line_value: config.closeLineValue || '',
        };
        accumulator[config.bookmakerName] = bookmakerBucket;
        return accumulator;
    }, {});
}

const ODDS_CONFIG = buildOddsConfig(MARKET_CONFIGS);
const TACTICAL_FIELD_ALIASES = {
    homeCorners: ['HC', 'HomeCorners', 'H_Corners'],
    awayCorners: ['AC', 'AwayCorners', 'A_Corners'],
    homeYellowCards: ['HY', 'HomeYellowCards', 'H_YellowCards'],
    awayYellowCards: ['AY', 'AwayYellowCards', 'A_YellowCards'],
    homeRedCards: ['HR', 'HomeRedCards', 'H_RedCards'],
    awayRedCards: ['AR', 'AwayRedCards', 'A_RedCards'],
    referee: ['Referee', 'RefereeName', 'OfficialsReferee']
};

function resolveRawReferee(match = {}) {
    return normalizeText(match.raw_referee || '');
}

function resolveTacticalValues(row, existingMatch = {}) {
    const refereeFromCsv = resolveCsvField(row, TACTICAL_FIELD_ALIASES.referee);
    const refereeFromRaw = resolveRawReferee(existingMatch);

    return {
        home_corners: resolveCsvField(row, TACTICAL_FIELD_ALIASES.homeCorners),
        away_corners: resolveCsvField(row, TACTICAL_FIELD_ALIASES.awayCorners),
        home_yellow_cards: resolveCsvField(row, TACTICAL_FIELD_ALIASES.homeYellowCards),
        away_yellow_cards: resolveCsvField(row, TACTICAL_FIELD_ALIASES.awayYellowCards),
        home_red_cards: resolveCsvField(row, TACTICAL_FIELD_ALIASES.homeRedCards),
        away_red_cards: resolveCsvField(row, TACTICAL_FIELD_ALIASES.awayRedCards),
        referee: refereeFromCsv || refereeFromRaw,
        referee_source: refereeFromCsv ? 'csv' : (refereeFromRaw ? 'fotmob_raw' : 'missing')
    };
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
        '用法: node scripts/ops/fetch_and_adapt_euro_leagues.js [--league-code E0|SP1|D1|I1|F1] [--season-code 2526|2425]'
    );
    console.log('说明: 默认抓取英超最新可用赛季；传入 --season-code 时只处理指定赛季。');
}

class ExistingMatchResolver {
    constructor(options = {}) {
        this.mapper = options.mapper || new EntityMapper();
        this.leagueName = options.leagueName || '';
        this.season = Normalizer.normalizeSeason(options.season || '');
        this.pool = options.pool || new Pool(buildDbConnectionConfig());
        this.ownsPool = !options.pool;
        this.matches = [];
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
          m.match_id,
          m.external_id,
          m.home_team,
          m.away_team,
          m.match_date,
          m.data_source,
          m.data_version,
          COALESCE(r.raw_data#>>'{content,matchFacts,infoBox,Referee,text}', '') AS raw_referee
        FROM matches m
        LEFT JOIN raw_match_data r ON r.match_id = m.match_id
        WHERE m.season = $1
          AND m.league_name = $2
          AND COALESCE(m.data_source, '') <> 'CSV_BULK_LOADER'
          AND COALESCE(m.data_version, '') <> 'CSV_BOOTSTRAP'
          AND COALESCE(m.external_id, '') NOT LIKE 'csv%'
          AND m.match_date IS NOT NULL
      `,
                [this.season, leagueName]
            );

            this.matches = result.rows;
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

        const outcome = selectBestAlignmentCandidate(this.matches, {
            homeTeam: options.homeTeam,
            awayTeam: options.awayTeam,
            matchDate
        }, {
            maxTimeWindowMs: MATCH_REUSE_WINDOW_MS,
            minConfidenceScore: MIN_CONFIDENCE_SCORE,
            minScoreGap: MIN_ALIGNMENT_SCORE_GAP
        });

        if (outcome.status === 'not_found') {
            return null;
        }
        if (outcome.status !== 'matched') {
            const best = outcome.ranked[0];
            const error = new Error(
                `对齐失败 status=${outcome.status} home=${options.homeTeam} away=${options.awayTeam} ` +
                `match_date=${matchDate.toISOString()} ` +
                `best_score=${best ? best.score.matchScore : 'n/a'}`
            );
            error.code = 'FOTMOB_MATCH_ALIGNMENT_FAILED';
            error.details = {
                homeTeam: options.homeTeam,
                awayTeam: options.awayTeam,
                matchDate: matchDate.toISOString(),
                status: outcome.status,
                bestScore: best?.score?.matchScore ?? null
            };
            throw error;
        }

        return {
            ...outcome.candidate,
            alignment_meta: outcome.alignmentMeta
        };
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
        const error = new Error(
            `未找到对应 FotMob 比赛: league=${options.leagueName} season=${Normalizer.normalizeSeason(options.season)} ` +
                `home=${options.homeTeam} away=${options.awayTeam} match_date=${options.matchDate}`
        );
        error.code = 'FOTMOB_MATCH_NOT_FOUND';
        error.details = {
            leagueName: options.leagueName,
            season: Normalizer.normalizeSeason(options.season),
            rawHomeTeam: options.rawHomeTeam || options.homeTeam,
            rawAwayTeam: options.rawAwayTeam || options.awayTeam,
            homeTeam: options.homeTeam,
            awayTeam: options.awayTeam,
            matchDate: options.matchDate
        };
        throw error;
    }

    const identity = options.mapper.bindFotMobIdentity(existingMatch);
    return {
        matchId: identity.matchId,
        externalId: identity.externalId,
        reusedExisting: true,
        matchedSource: existingMatch.data_source || '',
        matchedDate: existingMatch.match_date,
        alignmentMeta: existingMatch.alignment_meta || null,
        existingMatch,
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
    const matchDate = parseFootballDataDateTime(row.Date, row.Time, {
        leagueName: context.leagueMeta.leagueName
    });
    const matchIdResolution = buildMatchId({
        leagueName: context.leagueMeta.leagueName,
        season: context.sourceMeta.season,
        matchDate,
        rawHomeTeam,
        rawAwayTeam,
        homeTeam,
        awayTeam,
        mapper: context.mapper,
        resolver: context.resolver,
    });
    const tacticalValues = resolveTacticalValues(row, matchIdResolution.existingMatch);
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
        home_corners: tacticalValues.home_corners,
        away_corners: tacticalValues.away_corners,
        home_yellow_cards: tacticalValues.home_yellow_cards,
        away_yellow_cards: tacticalValues.away_yellow_cards,
        home_red_cards: tacticalValues.home_red_cards,
        away_red_cards: tacticalValues.away_red_cards,
        referee: tacticalValues.referee,
        alignment_meta: JSON.stringify(matchIdResolution.alignmentMeta || {}),
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
            tacticalCoverage: {
                hasCorners: Boolean(tacticalValues.home_corners && tacticalValues.away_corners),
                hasYellowCards: Boolean(tacticalValues.home_yellow_cards && tacticalValues.away_yellow_cards),
                hasRedCards: Boolean(tacticalValues.home_red_cards !== '' && tacticalValues.away_red_cards !== ''),
                refereeSource: tacticalValues.referee_source
            }
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
            tacticalRows: 0,
            cornersRows: 0,
            yellowCardRows: 0,
            redCardRows: 0,
            refereeFromCsv: 0,
            refereeFromFotmob: 0,
            refereeMissing: 0
        };
        this.sourceQualityFlags = new Set();
        this.unmatchedPairCounts = new Map();
        this.unmatchedTeamCounts = new Map();
    }

    _write(row, _encoding, callback) {
        try {
            const adapted = adaptSourceRow(row, {
                sourceMeta: this.sourceMeta,
                mapper: this.mapper,
                resolver: this.resolver,
                leagueMeta: this.sourceMeta,
                oddsConfig: ODDS_CONFIG,
                WARNING_LOW_QUALITY_SOURCE,
            });
            this.rows.push(...adapted.rows);
            if (adapted.diagnostics.reusedExisting) {
                this.stats.reusedExisting += 1;
            }
            if (adapted.diagnostics.qualityFlags.length > 0) {
                this.stats.lowQualityRows += 1;
            }
            this.stats.tacticalRows += 1;
            if (adapted.diagnostics.tacticalCoverage.hasCorners) {
                this.stats.cornersRows += 1;
            }
            if (adapted.diagnostics.tacticalCoverage.hasYellowCards) {
                this.stats.yellowCardRows += 1;
            }
            if (adapted.diagnostics.tacticalCoverage.hasRedCards) {
                this.stats.redCardRows += 1;
            }
            if (adapted.diagnostics.tacticalCoverage.refereeSource === 'csv') {
                this.stats.refereeFromCsv += 1;
            } else if (adapted.diagnostics.tacticalCoverage.refereeSource === 'fotmob_raw') {
                this.stats.refereeFromFotmob += 1;
            } else {
                this.stats.refereeMissing += 1;
            }
            adapted.diagnostics.qualityFlags.forEach(flag => this.sourceQualityFlags.add(flag));
            callback();
        } catch (error) {
            this.skipped += 1;
            this.stats.unmatchedRows += 1;
            this.errors.push(error.message);
            this._recordUnmatchedTeams(error);
            callback();
        }
    }

    _recordUnmatchedTeams(error) {
        if (error?.code !== 'FOTMOB_MATCH_NOT_FOUND' || !error.details) {
            return;
        }

        const {
            rawHomeTeam,
            rawAwayTeam,
            homeTeam,
            awayTeam
        } = error.details;
        const pairKey = `${rawHomeTeam} vs ${rawAwayTeam}`;
        this.unmatchedPairCounts.set(pairKey, (this.unmatchedPairCounts.get(pairKey) || 0) + 1);

        const teamPairs = [
            [rawHomeTeam, homeTeam],
            [rawAwayTeam, awayTeam]
        ];

        for (const [rawName, normalizedName] of teamPairs) {
            if (!rawName) {
                continue;
            }
            const teamKey = rawName === normalizedName
                ? rawName
                : `${rawName} => ${normalizedName}`;
            this.unmatchedTeamCounts.set(teamKey, (this.unmatchedTeamCounts.get(teamKey) || 0) + 1);
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
        unmatchedPairCounts: [...collector.unmatchedPairCounts.entries()]
            .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0])),
        unmatchedTeamCounts: [...collector.unmatchedTeamCounts.entries()]
            .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    };
}

async function writeAdaptedCsv(outputPath, rows) {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    const output = fs.createWriteStream(outputPath, { encoding: 'utf8' });
    output.write(`${OUTPUT_HEADERS.join(',')}\n`);
    for (const row of rows) {
        output.write(`${formatCsvLine(row, OUTPUT_HEADERS)}\n`);
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
        console.log(
            `[FETCH-EURO] 战术覆盖 corners=${adapted.stats.cornersRows}/${adapted.stats.tacticalRows} ` +
                `yellow_cards=${adapted.stats.yellowCardRows}/${adapted.stats.tacticalRows} ` +
                `red_cards=${adapted.stats.redCardRows}/${adapted.stats.tacticalRows} ` +
                `referee(csv=${adapted.stats.refereeFromCsv},fotmob=${adapted.stats.refereeFromFotmob},missing=${adapted.stats.refereeMissing})`
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
        if (adapted.unmatchedTeamCounts.length > 0) {
            console.log(`[FETCH-EURO] 未匹配球队名审计: ${adapted.unmatchedTeamCounts.slice(0, 12).map(([name, count]) => `${name} x${count}`).join(' | ')}`);
        }
        if (adapted.unmatchedPairCounts.length > 0) {
            console.log(`[FETCH-EURO] 未匹配对阵审计: ${adapted.unmatchedPairCounts.slice(0, 8).map(([name, count]) => `${name} x${count}`).join(' | ')}`);
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
    resolveCsvField,
    resolveLeagueMeta,
    resolveRawReferee,
    resolveTacticalValues,
};
