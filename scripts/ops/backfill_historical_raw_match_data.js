#!/usr/bin/env node
'use strict';

require('dotenv').config();

const zlib = require('zlib');
const { Pool } = require('pg');
const { Normalizer } = require('../../src/utils/Normalizer');

const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_WORKERS = 8;
const DEFAULT_LIMIT = 0;
const DATA_VERSION = 'FOTMOB_GSM_L2_V1';
const SOURCE_URL_TEMPLATE = 'http://data.fotmob.com/webcl/ltc/gsm/%s_en_gen.json.gz';
const SHOT_INCIDENT_CODES = new Set(['goal', 'attempt blocked', 'attempt saved', 'attempt missed']);
const INCIDENT_STAT_KEYS = {
    corner: 'corners',
    offside: 'offsides',
    yc: 'yellowCards',
    rc: 'redCards',
    'free kick lost': 'fouls',
    foul: 'fouls'
};
const MOMENTUM_WEIGHTS = {
    goal: 5,
    'attempt saved': 2,
    'attempt blocked': 1.5,
    'attempt missed': 1,
    corner: 0.6,
    yc: -0.5,
    rc: -1.5,
    offside: -0.2
};

const pool = new Pool({
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number.parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || '',
    max: Math.max(DEFAULT_WORKERS + 2, 12)
});

function parseArgs(argv = process.argv.slice(2)) {
    const args = {
        season: '2024/2025',
        leagueIds: [],
        workers: DEFAULT_WORKERS,
        limit: DEFAULT_LIMIT,
        commit: false,
        verbose: false
    };

    for (const arg of argv) {
        if (arg === '--commit') {
            args.commit = true;
            continue;
        }
        if (arg === '--verbose' || arg === '-v') {
            args.verbose = true;
            continue;
        }
        if (arg.startsWith('--season=')) {
            args.season = arg.split('=')[1] || args.season;
            continue;
        }
        if (arg.startsWith('--workers=')) {
            args.workers = Number.parseInt(arg.split('=')[1], 10) || DEFAULT_WORKERS;
            continue;
        }
        if (arg.startsWith('--limit=')) {
            args.limit = Number.parseInt(arg.split('=')[1], 10) || DEFAULT_LIMIT;
            continue;
        }
        if (arg.startsWith('--league=')) {
            const raw = arg.split('=')[1] || '';
            const leagueIds = raw
                .split(',')
                .map(value => Number.parseInt(value.trim(), 10))
                .filter(Number.isFinite);
            args.leagueIds.push(...leagueIds);
        }
    }

    args.leagueIds = Array.from(new Set(args.leagueIds));

    if (args.leagueIds.length === 0) {
        args.leagueIds = [87, 55, 54, 53];
    }

    return args;
}

function createLimiter(concurrency) {
    let activeCount = 0;
    const queue = [];

    const next = () => {
        if (activeCount >= concurrency || queue.length === 0) {
            return;
        }

        activeCount += 1;
        const item = queue.shift();
        item.fn()
            .then(item.resolve, item.reject)
            .finally(() => {
                activeCount -= 1;
                next();
            });
    };

    return (fn) => new Promise((resolve, reject) => {
        queue.push({ fn, resolve, reject });
        next();
    });
}

function normalizeText(value) {
    return String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]+/gi, '')
        .toLowerCase();
}

function createStatLine(title, home, away) {
    return {
        title,
        stats: [home, away]
    };
}

function getEventMinute(event) {
    const minute = Number.parseInt(event?.Elapsed, 10);
    if (!Number.isFinite(minute) || minute < 0) {
        return null;
    }

    return minute;
}

function getEventAddedMinute(event) {
    const minute = Number.parseInt(event?.ElapsedPlus, 10);
    if (!Number.isFinite(minute) || minute < 0) {
        return null;
    }

    return minute;
}

function describeMatch(match) {
    return `${match.match_id} ${match.home_team} vs ${match.away_team}`;
}

function inferTeamSide(description, match, event) {
    const normalizedDescription = normalizeText(description);
    const homeTeam = normalizeText(match.home_team);
    const awayTeam = normalizeText(match.away_team);

    if (homeTeam && normalizedDescription.includes(homeTeam)) {
        return 'home';
    }
    if (awayTeam && normalizedDescription.includes(awayTeam)) {
        return 'away';
    }

    if (event?.Players?.[0]?.TeamId && match.fotmob_home_team_id && match.fotmob_away_team_id) {
        if (Number(event.Players[0].TeamId) === Number(match.fotmob_home_team_id)) {
            return 'home';
        }
        if (Number(event.Players[0].TeamId) === Number(match.fotmob_away_team_id)) {
            return 'away';
        }
    }

    if (typeof event?.HometeamEvent === 'boolean') {
        return event.HometeamEvent ? 'home' : 'away';
    }

    return null;
}

function addStat(stats, side, key, amount = 1) {
    if (!side || !stats[side]) {
        return;
    }
    stats[side][key] = Number(stats[side][key] || 0) + amount;
}

function classifyShotEvent(code) {
    if (!SHOT_INCIDENT_CODES.has(code)) {
        return null;
    }

    return {
        isGoal: code === 'goal',
        isBlocked: code === 'attempt blocked',
        isSaved: code === 'attempt saved'
    };
}

function buildShotEvent(event, side, match) {
    const code = String(event?.IncidentCode || '').toLowerCase();
    const shotType = classifyShotEvent(code);
    if (!shotType) {
        return null;
    }

    const minute = getEventMinute(event);
    const addedMinute = getEventAddedMinute(event);
    const isHome = side === 'home';
    return {
        id: `${event?.Elapsed || '0'}-${event?.ElapsedPlus || '0'}-${event?.IncidentCode || 'shot'}-${event?.Description || ''}`.slice(0, 120),
        min: minute,
        minAdded: addedMinute,
        teamId: isHome ? match.fotmob_home_team_id : match.fotmob_away_team_id,
        teamName: isHome ? match.home_team : match.away_team,
        eventType: shotType.isGoal ? 'Goal' : 'Shot',
        shotType: null,
        isBlocked: shotType.isBlocked,
        isOnTarget: shotType.isGoal || shotType.isSaved,
        isOwnGoal: false,
        playerName: event?.Players?.[0]?.Name || null,
        description: event?.Description || ''
    };
}

function buildApproxMomentum(momentumBuckets) {
    const minutes = Object.keys(momentumBuckets)
        .map(value => Number.parseInt(value, 10))
        .filter(Number.isFinite)
        .sort((left, right) => left - right);

    return minutes.map((minute) => ({
        minute,
        value: Math.max(-100, Math.min(100, Math.round(momentumBuckets[minute] * 20)))
    }));
}

function buildEmptyStats() {
    return {
        shots: 0,
        shotsOnTarget: 0,
        shotsOffTarget: 0,
        blockedShots: 0,
        corners: 0,
        offsides: 0,
        yellowCards: 0,
        redCards: 0,
        fouls: 0
    };
}

function normalizeGsmEvent(event, side, minute, addedMinute, code, description) {
    return {
        minute,
        addedMinute,
        code: event?.IncidentCode || null,
        side,
        description,
        players: Array.isArray(event?.Players)
            ? event.Players.map(player => ({
                id: player?.Id || null,
                name: player?.Name || null,
                teamId: player?.TeamId || null
            }))
            : []
    };
}

function applyShotStats(stats, shotEvent, side) {
    if (!shotEvent) {
        return;
    }

    addStat(stats, side, 'shots', 1);
    addStat(stats, side, shotEvent.isOnTarget ? 'shotsOnTarget' : 'shotsOffTarget', 1);
    if (shotEvent.isBlocked) {
        addStat(stats, side, 'blockedShots', 1);
    }
}

function applyIncidentStats(stats, code, side) {
    const statKey = INCIDENT_STAT_KEYS[code];
    if (statKey) {
        addStat(stats, side, statKey, 1);
    }
}

function applyMomentum(momentumBuckets, code, side, minute) {
    if (!Number.isFinite(minute) || !side) {
        return;
    }

    const weight = MOMENTUM_WEIGHTS[code] || 0;
    if (weight === 0) {
        return;
    }

    const sign = side === 'home' ? 1 : -1;
    momentumBuckets[minute] = Number(momentumBuckets[minute] || 0) + (sign * weight);
}

function deriveGsmStats(gsmData, match) {
    const stats = {
        home: buildEmptyStats(),
        away: buildEmptyStats()
    };

    const shotmapShots = [];
    const momentumBuckets = {};
    const normalizedEvents = [];
    const events = Array.isArray(gsmData?.Events) ? gsmData.Events : [];

    for (const event of events) {
        const description = String(event?.Description || '');
        const code = String(event?.IncidentCode || '').toLowerCase();
        const side = inferTeamSide(description, match, event);
        const minute = getEventMinute(event);
        const addedMinute = getEventAddedMinute(event);

        normalizedEvents.push(normalizeGsmEvent(event, side, minute, addedMinute, code, description));

        const shotEvent = buildShotEvent(event, side, match);
        if (shotEvent) {
            shotmapShots.push(shotEvent);
        }
        applyShotStats(stats, shotEvent, side);
        applyIncidentStats(stats, code, side);
        applyMomentum(momentumBuckets, code, side, minute);
    }

    return {
        stats,
        shotmapShots,
        normalizedEvents,
        momentum: buildApproxMomentum(momentumBuckets)
    };
}

function buildStatsPayload(derivedStats) {
    const { home, away } = derivedStats;
    return [
        createStatLine('Total shots', home.shots, away.shots),
        createStatLine('Shots on target', home.shotsOnTarget, away.shotsOnTarget),
        createStatLine('Shots off target', home.shotsOffTarget, away.shotsOffTarget),
        createStatLine('Blocked shots', home.blockedShots, away.blockedShots),
        createStatLine('Corner kicks', home.corners, away.corners),
        createStatLine('Offsides', home.offsides, away.offsides),
        createStatLine('Yellow cards', home.yellowCards, away.yellowCards),
        createStatLine('Red cards', home.redCards, away.redCards),
        createStatLine('Fouls', home.fouls, away.fouls)
    ];
}

function resolveTeamId(match, gsmData, side) {
    return side === 'home'
        ? match.fotmob_home_team_id || gsmData?.HometeamId || null
        : match.fotmob_away_team_id || gsmData?.AwayteamId || null;
}

function buildTeamSummary(match, gsmData, side) {
    return {
        id: resolveTeamId(match, gsmData, side),
        name: side === 'home' ? match.home_team : match.away_team
    };
}

function buildHeaderTeam(match, gsmData, side) {
    return {
        ...buildTeamSummary(match, gsmData, side),
        score: side === 'home' ? match.home_score : match.away_score
    };
}

function buildLineupPlaceholder(match, gsmData, side) {
    return {
        ...buildTeamSummary(match, gsmData, side),
        starters: [],
        subs: [],
        coach: null,
        rating: null,
        formation: null,
        unavailable: [],
        averageStarterAge: null,
        totalStarterMarketValue: 0
    };
}

function buildPseudoFotMobPayload(match, gsmData) {
    const derived = deriveGsmStats(gsmData, match);
    const matchTime = match.match_date instanceof Date
        ? match.match_date.toISOString()
        : new Date(match.match_date).toISOString();
    const isFinished = match.home_score !== null && match.away_score !== null;
    const scoreStr = `${match.home_score ?? '-'} - ${match.away_score ?? '-'}`;

    return {
        general: {
            matchId: String(match.external_id),
            matchName: `${match.home_team}-vs-${match.away_team}`,
            leagueId: Number(match.league_id),
            leagueName: match.league_name,
            parentLeagueName: match.league_name,
            matchTimeUTCDateTime: matchTime,
            matchTimeUTCDate: matchTime,
            finished: isFinished,
            started: true,
            coverageLevel: 'historical_gsm',
            source: 'data.fotmob.com',
            homeTeam: buildTeamSummary(match, gsmData, 'home'),
            awayTeam: buildTeamSummary(match, gsmData, 'away')
        },
        header: {
            teams: [
                buildHeaderTeam(match, gsmData, 'home'),
                buildHeaderTeam(match, gsmData, 'away')
            ],
            status: {
                started: true,
                finished: isFinished,
                utcTime: matchTime,
                timezone: 'UTC',
                scoreStr
            }
        },
        content: {
            stats: buildStatsPayload(derived.stats),
            lineup: {
                homeTeam: buildLineupPlaceholder(match, gsmData, 'home'),
                awayTeam: buildLineupPlaceholder(match, gsmData, 'away')
            },
            shotmap: {
                shots: derived.shotmapShots
            },
            momentum: {
                data: derived.momentum
            },
            matchFacts: {
                matchId: String(match.external_id),
                source: 'historical_gsm',
                infoBox: {
                    note: {
                        key: 'historical_gsm_backfill',
                        text: 'Derived from data.fotmob.com/webcl/ltc/gsm historical event feed'
                    }
                }
            },
            liveticker: {
                events: derived.normalizedEvents
            }
        },
        _meta: {
            source: 'historical_gsm_backfill',
            dataVersion: DATA_VERSION,
            sourceUrl: SOURCE_URL_TEMPLATE.replace('%s', String(match.external_id)),
            derivedSignals: {
                hasLineup: true,
                lineupIsPlaceholder: true,
                hasShotmap: true,
                shotCount: derived.shotmapShots.length,
                hasMomentum: derived.momentum.length > 0,
                hasStats: true,
                statsAreEventDerived: true,
                hasExpectedGoals: false,
                hasMarketValue: false
            }
        }
    };
}

async function fetchBuffer(url, redirectsLeft = 3) {
    if (typeof fetch !== 'function') {
        throw new Error('FETCH_UNAVAILABLE: Node runtime does not provide native fetch');
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
    let response;

    try {
        response = await fetch(url, {
            redirect: 'manual',
            signal: controller.signal,
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; FootballPrediction/1.0; +historical-l2-backfill)',
                'Accept': 'application/json,text/plain,*/*',
                'Accept-Encoding': 'gzip'
            }
        });
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error(`TIMEOUT_${DEFAULT_TIMEOUT_MS}ms`);
        }
        throw error;
    } finally {
        clearTimeout(timeout);
    }

    if (response.status >= 300 && response.status < 400 && response.headers.get('location') && redirectsLeft > 0) {
        const redirected = new URL(response.headers.get('location'), url).toString();
        return fetchBuffer(redirected, redirectsLeft - 1);
    }

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP_${response.status}: ${errorText.slice(0, 200)}`);
    }

    const buffer = Buffer.from(await response.arrayBuffer());
    const looksGzipped = buffer[0] === 0x1f && buffer[1] === 0x8b;
    if (looksGzipped) {
        return zlib.gunzipSync(buffer);
    }
    return buffer;
}

async function fetchGsmPayload(externalId) {
    const url = SOURCE_URL_TEMPLATE.replace('%s', String(externalId));
    const buffer = await fetchBuffer(url);
    const text = buffer.toString('utf8');
    return {
        url,
        data: JSON.parse(text)
    };
}

async function loadPendingMatches(options) {
    const patterns = options.leagueIds.map(id => `${id}_%`);
    const values = [options.season, patterns];
    const limitClause = options.limit > 0 ? `LIMIT $${values.push(options.limit)}` : '';

    const query = `
        SELECT
            m.match_id,
            m.external_id,
            m.league_name,
            split_part(m.match_id, '_', 1)::int AS league_id,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score,
            m.match_date
        FROM matches m
        LEFT JOIN raw_match_data r ON r.match_id = m.match_id
        WHERE m.season = $1
          AND m.match_id LIKE ANY($2::text[])
          AND m.external_id IS NOT NULL
          AND m.external_id NOT LIKE 'csv%'
          AND r.match_id IS NULL
        ORDER BY m.match_date ASC, m.match_id ASC
        ${limitClause}
    `;

    const result = await pool.query(query, values);
    return result.rows;
}

async function persistRawMatchData(client, match, rawData) {
    await client.query(
        `
            INSERT INTO raw_match_data (
                match_id,
                external_id,
                raw_data,
                collected_at,
                data_version,
                data_hash
            ) VALUES (
                $1, $2, $3::jsonb, NOW(), $4, md5($3::text)
            )
            ON CONFLICT (match_id) DO UPDATE SET
                external_id = EXCLUDED.external_id,
                raw_data = EXCLUDED.raw_data,
                collected_at = NOW(),
                data_version = EXCLUDED.data_version,
                data_hash = EXCLUDED.data_hash
        `,
        [
            match.match_id,
            match.external_id,
            JSON.stringify(rawData),
            DATA_VERSION
        ]
    );

    await client.query(
        `
            UPDATE matches
            SET pipeline_status = 'harvested',
                updated_at = NOW()
            WHERE match_id = $1
        `,
        [match.match_id]
    );
}

async function processMatch(match, options) {
    const startedAt = Date.now();
    const { url, data } = await fetchGsmPayload(match.external_id);
    const enrichedMatch = {
        ...match,
        fotmob_home_team_id: data?.HometeamId || null,
        fotmob_away_team_id: data?.AwayteamId || null
    };
    const rawData = buildPseudoFotMobPayload(enrichedMatch, data);

    const result = {
        matchId: match.match_id,
        externalId: match.external_id,
        leagueName: match.league_name,
        url,
        shotCount: Number(rawData?.content?.shotmap?.shots?.length || 0),
        momentumSamples: Number(rawData?.content?.momentum?.data?.length || 0),
        durationMs: Date.now() - startedAt,
        committed: false
    };

    if (!options.commit) {
        result.preview = {
            contentKeys: Object.keys(rawData.content || {}),
            hasLineup: !!rawData?.content?.lineup,
            hasShotmap: !!rawData?.content?.shotmap,
            hasStats: Array.isArray(rawData?.content?.stats),
            statsRows: Array.isArray(rawData?.content?.stats) ? rawData.content.stats.length : 0
        };
        return result;
    }

    const client = await pool.connect();
    try {
        await client.query('BEGIN');
        await persistRawMatchData(client, match, rawData);
        await client.query('COMMIT');
        result.committed = true;
        return result;
    } catch (error) {
        await client.query('ROLLBACK').catch(() => {});
        throw error;
    } finally {
        client.release();
    }
}

async function queryCoverageByLeague(season, leagueIds) {
    const patterns = leagueIds.map(id => `${id}_%`);
    const result = await pool.query(
        `
            SELECT
                m.league_name,
                COUNT(*) FILTER (
                    WHERE m.external_id IS NOT NULL
                      AND m.external_id NOT LIKE 'csv%'
                ) AS total_real_matches,
                COUNT(r.match_id) AS has_raw_data,
                COUNT(*) FILTER (
                    WHERE m.external_id IS NOT NULL
                      AND m.external_id NOT LIKE 'csv%'
                      AND r.match_id IS NULL
                ) AS missing_raw_data
            FROM matches m
            LEFT JOIN raw_match_data r ON r.match_id = m.match_id
            WHERE m.season = $1
              AND m.match_id LIKE ANY($2::text[])
            GROUP BY 1
            ORDER BY 1
        `,
        [season, patterns]
    );
    return result.rows;
}

async function main() {
    const options = parseArgs();
    const normalizedSeason = Normalizer.normalizeSeason(options.season);
    console.log(`[HIST-L2] season=${options.season} normalized=${normalizedSeason} leagues=${options.leagueIds.join(',')} commit=${options.commit} workers=${options.workers} limit=${options.limit || 'ALL'}`);

    const pendingMatches = await loadPendingMatches(options);
    console.log(`[HIST-L2] pending_matches=${pendingMatches.length}`);

    if (pendingMatches.length === 0) {
        const coverage = await queryCoverageByLeague(options.season, options.leagueIds);
        console.table(coverage);
        return;
    }

    const limit = createLimiter(Math.max(1, options.workers));
    const stats = {
        success: 0,
        failed: 0,
        rows: []
    };

    await Promise.all(pendingMatches.map(match => limit(async () => {
        try {
            const result = await processMatch(match, options);
            stats.success += 1;
            stats.rows.push(result);
            if (options.verbose) {
                console.log(`[HIST-L2] OK ${describeMatch(match)} shots=${result.shotCount} momentum=${result.momentumSamples} ${result.committed ? 'committed' : 'preview'}`);
            }
        } catch (error) {
            stats.failed += 1;
            console.error(`[HIST-L2] FAIL ${describeMatch(match)} reason=${error.message}`);
        }
    })));

    console.log(`[HIST-L2] success=${stats.success} failed=${stats.failed}`);

    if (!options.commit) {
        console.table(
            stats.rows.slice(0, 5).map(row => ({
                matchId: row.matchId,
                league: row.leagueName,
                shots: row.shotCount,
                momentum: row.momentumSamples,
                statsRows: row.preview?.statsRows || 0
            }))
        );
    }

    const coverage = await queryCoverageByLeague(options.season, options.leagueIds);
    console.table(coverage);

    if (stats.failed > 0) {
        process.exitCode = 2;
    }
}

main()
    .catch(error => {
        console.error(`[HIST-L2] fatal=${error.message}`);
        console.error(error.stack);
        process.exitCode = 1;
    })
    .finally(async () => {
        await pool.end().catch(() => {});
    });
