#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
'use strict';

const PHASE = 'PHASE5_09L1_CONTROLLED_MATCHES_SEED_COMMIT_EXECUTION';
const SAFE_SOURCE = 'fotmob';
const SAFE_SCOPES = new Set(['league_season_date', 'controlled_candidates_preview']);
const EXACT_LEAGUE_ID = '53';
const EXACT_SEASON = '2025/2026';
const EXACT_DATE = '2026-05-10';
const EXACT_CANDIDATE_COUNT = 8;
const EXACT_TARGET_MATCH_ID = '4830746';
const MAX_SEED_ROWS_LIMIT = 10;
const DEFAULT_MAX_SEED_ROWS = 10;
const PREVIEW_SCOPE = 'controlled_candidates_preview';
const SAFE_NETWORK_CONCURRENCY = 1;
const SAFE_NETWORK_MAX_TARGETS = 10;
const SAFE_NETWORK_TIMEOUT_MS = 15000;
const NEXT_REQUIRED_PHASE = 'Phase 5.10L2 controlled raw JSON acquisition planning';
const ALLOWED_INSERT_COLUMNS = [
    'match_id',
    'external_id',
    'league_name',
    'season',
    'home_team',
    'away_team',
    'match_date',
    'status',
    'is_finished',
    'data_source',
];
const COUNT_TABLES = [
    'matches',
    'bookmaker_odds_history',
    'raw_match_data',
    'l3_features',
    'match_features_training',
    'predictions',
];

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') {
        return value;
    }
    if (value === null || value === undefined || value === '') {
        return fallback;
    }

    const normalized = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) {
        return true;
    }
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) {
        return false;
    }
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    const normalized = String(value).trim();
    if (!/^\d+$/.test(normalized)) {
        return Number.NaN;
    }
    const parsed = Number.parseInt(normalized, 10);
    return Number.isInteger(parsed) ? parsed : Number.NaN;
}

function normalizeOptionalText(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    return String(value).trim();
}

function normalizeTargetLabel(value) {
    return String(value || '')
        .trim()
        .toLowerCase();
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) {
        return {
            value: arg.slice(arg.indexOf('=') + 1),
            consumedNext: false,
        };
    }

    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return { value: nextArg, consumedNext: true };
    }

    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        scope: null,
        leagueId: null,
        season: null,
        date: null,
        candidateCount: null,
        containsTargetMatchId: null,
        containsTargetLabel: null,
        maxSeedRows: null,
        finalDbWriteConfirmation: false,
        allowDbWriteNow: false,
        allowMatchesWriteNow: false,
        allowRawMatchDataWrite: false,
        allowTraining: false,
        allowPrediction: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        bulk: false,
        candidatesJson: null,
        existingMatchesJson: null,
        help: false,
    };

    const keyMap = {
        source: 'source',
        scope: 'scope',
        'league-id': 'leagueId',
        league_id: 'leagueId',
        season: 'season',
        date: 'date',
        'candidate-count': 'candidateCount',
        candidate_count: 'candidateCount',
        'contains-target-match-id': 'containsTargetMatchId',
        contains_target_match_id: 'containsTargetMatchId',
        'contains-target-label': 'containsTargetLabel',
        contains_target_label: 'containsTargetLabel',
        'max-seed-rows': 'maxSeedRows',
        max_seed_rows: 'maxSeedRows',
        'final-db-write-confirmation': 'finalDbWriteConfirmation',
        final_db_write_confirmation: 'finalDbWriteConfirmation',
        'allow-db-write-now': 'allowDbWriteNow',
        allow_db_write_now: 'allowDbWriteNow',
        'allow-matches-write-now': 'allowMatchesWriteNow',
        allow_matches_write_now: 'allowMatchesWriteNow',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        prediction: 'allowPrediction',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        bulk: 'bulk',
        'candidates-json': 'candidatesJson',
        candidates_json: 'candidatesJson',
        'existing-matches-json': 'existingMatchesJson',
        existing_matches_json: 'existingMatchesJson',
        help: 'help',
        h: 'help',
    };

    const booleanOptions = new Set([
        'finalDbWriteConfirmation',
        'allowDbWriteNow',
        'allowMatchesWriteNow',
        'allowRawMatchDataWrite',
        'allowTraining',
        'allowPrediction',
        'allowBrowserRuntime',
        'allowProxyRuntime',
        'bulk',
        'help',
    ]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index];
        if (!arg.startsWith('--')) {
            continue;
        }

        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        if (!optionKey) {
            continue;
        }

        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) {
            index += 1;
        }

        if (booleanOptions.has(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function normalizeExecutionInput(input = {}) {
    return {
        source: typeof input.source === 'string' ? input.source.trim().toLowerCase() : '',
        scope: typeof input.scope === 'string' ? input.scope.trim() : '',
        leagueId: normalizeOptionalText(input.leagueId),
        season: typeof input.season === 'string' ? input.season.trim() : null,
        date: typeof input.date === 'string' ? input.date.trim() : null,
        candidateCount: parseInteger(input.candidateCount, null),
        containsTargetMatchId: normalizeOptionalText(input.containsTargetMatchId),
        containsTargetLabel: normalizeOptionalText(input.containsTargetLabel),
        maxSeedRows: parseInteger(input.maxSeedRows, DEFAULT_MAX_SEED_ROWS),
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, false),
        allowDbWriteNow: normalizeBooleanFlag(input.allowDbWriteNow, false),
        allowMatchesWriteNow: normalizeBooleanFlag(input.allowMatchesWriteNow, false),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, false),
        allowTraining: normalizeBooleanFlag(input.allowTraining, false),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, false),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, false),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, false),
        bulk: normalizeBooleanFlag(input.bulk, false),
        candidatesJson: typeof input.candidatesJson === 'string' ? input.candidatesJson : null,
        existingMatchesJson: typeof input.existingMatchesJson === 'string' ? input.existingMatchesJson : null,
    };
}

function validateExecutionInput(input = {}) {
    const value = normalizeExecutionInput(input);
    const errors = [];

    if (!value.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (value.source !== SAFE_SOURCE) {
        errors.push('unsupported source: only fotmob is allowed');
    }

    if (!value.scope) {
        errors.push('missing scope: provide --scope=league_season_date or --scope=controlled_candidates_preview');
    } else if (!SAFE_SCOPES.has(value.scope)) {
        errors.push(`unsupported scope: ${value.scope}`);
    }

    if (!value.leagueId) {
        errors.push('missing league-id');
    } else if (value.leagueId !== EXACT_LEAGUE_ID) {
        errors.push(`league-id must be ${EXACT_LEAGUE_ID} in Phase 5.09L1`);
    }

    if (!value.season) {
        errors.push('missing season');
    } else if (value.season !== EXACT_SEASON) {
        errors.push(`season must be ${EXACT_SEASON} in Phase 5.09L1`);
    }

    if (!value.date) {
        errors.push('missing date');
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(value.date)) {
        errors.push('invalid date: provide YYYY-MM-DD');
    } else if (value.date !== EXACT_DATE) {
        errors.push(`date must be ${EXACT_DATE} in Phase 5.09L1`);
    }

    if (!Number.isInteger(value.candidateCount)) {
        errors.push('invalid candidate-count: provide an integer');
    } else if (value.candidateCount !== EXACT_CANDIDATE_COUNT) {
        errors.push(`candidate-count must be exactly ${EXACT_CANDIDATE_COUNT}`);
    }

    if (!Number.isInteger(value.maxSeedRows) || value.maxSeedRows < 1) {
        errors.push('invalid max-seed-rows: provide a positive integer');
    } else if (value.maxSeedRows > MAX_SEED_ROWS_LIMIT) {
        errors.push(`max-seed-rows > ${MAX_SEED_ROWS_LIMIT} is blocked in Phase 5.09L1`);
    }

    if (
        Number.isInteger(value.candidateCount) &&
        Number.isInteger(value.maxSeedRows) &&
        value.candidateCount > value.maxSeedRows
    ) {
        errors.push('candidate-count must be <= max-seed-rows');
    }

    if (!value.containsTargetMatchId) {
        errors.push('missing contains-target-match-id');
    } else if (value.containsTargetMatchId !== EXACT_TARGET_MATCH_ID) {
        errors.push(`contains-target-match-id must be ${EXACT_TARGET_MATCH_ID}`);
    }

    const normalizedLabel = normalizeTargetLabel(value.containsTargetLabel);
    if (!value.containsTargetLabel) {
        errors.push('missing contains-target-label');
    } else {
        if (!normalizedLabel.includes('angers')) {
            errors.push('contains-target-label must contain Angers');
        }
        if (!normalizedLabel.includes('strasbourg')) {
            errors.push('contains-target-label must contain Strasbourg');
        }
    }

    if (value.finalDbWriteConfirmation !== true) {
        errors.push('final-db-write-confirmation must be yes');
    }
    if (value.allowDbWriteNow !== true) {
        errors.push('allow-db-write-now must be yes');
    }
    if (value.allowMatchesWriteNow !== true) {
        errors.push('allow-matches-write-now must be yes');
    }
    if (value.allowRawMatchDataWrite !== false) {
        errors.push('allow-raw-match-data-write=yes is blocked in Phase 5.09L1');
    }
    if (value.allowTraining !== false) {
        errors.push('allow-training=yes is blocked in Phase 5.09L1');
    }
    if (value.allowPrediction !== false) {
        errors.push('allow-prediction=yes is blocked in Phase 5.09L1');
    }
    if (value.allowBrowserRuntime !== false) {
        errors.push('allow-browser-runtime=yes is blocked in Phase 5.09L1');
    }
    if (value.allowProxyRuntime !== false) {
        errors.push('allow-proxy-runtime=yes is blocked in Phase 5.09L1');
    }
    if (value.bulk !== false) {
        errors.push('bulk=yes is blocked in Phase 5.09L1');
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function parseJsonText(text, label) {
    try {
        return JSON.parse(text);
    } catch (error) {
        throw new Error(`${label} is not valid JSON: ${error.message}`);
    }
}

function normalizeDateText(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    if (value instanceof Date) {
        return Number.isNaN(value.getTime()) ? null : value.toISOString();
    }

    const text = String(value).trim();
    if (!text) {
        return null;
    }
    const parsed = new Date(text);
    return Number.isNaN(parsed.getTime()) ? text : parsed.toISOString();
}

function normalizeStatus(value) {
    const text = String(value || '')
        .trim()
        .toLowerCase();
    return text || 'scheduled';
}

function normalizeDataSource(value) {
    const text = String(value || '').trim();
    return text || 'FotMob';
}

function normalizeCandidates(input) {
    const candidates = Array.isArray(input)
        ? input
        : Array.isArray(input?.candidates)
          ? input.candidates
          : input?.candidates_preview;
    if (!Array.isArray(candidates)) {
        throw new Error('candidate payload must be an array or expose candidates/candidates_preview');
    }

    return candidates.map((candidate, index) => {
        const matchId = normalizeOptionalText(candidate?.match_id ?? candidate?.matchId);
        const externalId = normalizeOptionalText(
            candidate?.external_id ?? candidate?.externalId ?? candidate?.id ?? matchId
        );
        const leagueName = normalizeOptionalText(candidate?.league_name ?? candidate?.league);
        const season = normalizeOptionalText(candidate?.season);
        const homeTeam = normalizeOptionalText(candidate?.home_team ?? candidate?.home);
        const awayTeam = normalizeOptionalText(candidate?.away_team ?? candidate?.away);
        const matchDate = normalizeDateText(candidate?.match_date ?? candidate?.matchDate);
        const status = normalizeStatus(candidate?.status);
        const dataSource = normalizeDataSource(candidate?.data_source ?? candidate?.dataSource);
        const isFinished = candidate?.is_finished === true || candidate?.isFinished === true || status === 'finished';

        const missing = [];
        if (!matchId) missing.push('match_id');
        if (!externalId) missing.push('external_id');
        if (!leagueName) missing.push('league_name');
        if (!season) missing.push('season');
        if (!homeTeam) missing.push('home_team');
        if (!awayTeam) missing.push('away_team');
        if (!matchDate) missing.push('match_date');
        if (missing.length > 0) {
            throw new Error(`candidate[${index}] missing required fields: ${missing.join(', ')}`);
        }

        return {
            match_id: matchId,
            external_id: externalId,
            league_name: leagueName,
            season,
            home_team: homeTeam,
            away_team: awayTeam,
            match_date: matchDate,
            status,
            is_finished: isFinished,
            data_source: dataSource,
        };
    });
}

function normalizeExistingMatches(rows) {
    const list = Array.isArray(rows)
        ? rows
        : Array.isArray(rows?.rows)
          ? rows.rows
          : Array.isArray(rows?.existing_matches)
            ? rows.existing_matches
            : [];

    return list.map(row => ({
        match_id: normalizeOptionalText(row?.match_id ?? row?.matchId),
        external_id: normalizeOptionalText(row?.external_id ?? row?.externalId),
        league_name: normalizeOptionalText(row?.league_name ?? row?.leagueName),
        season: normalizeOptionalText(row?.season),
        home_team: normalizeOptionalText(row?.home_team ?? row?.homeTeam),
        away_team: normalizeOptionalText(row?.away_team ?? row?.awayTeam),
        match_date: normalizeDateText(row?.match_date ?? row?.matchDate),
        status: normalizeStatus(row?.status),
        is_finished:
            row?.is_finished === true || row?.isFinished === true || normalizeStatus(row?.status) === 'finished',
        data_source: normalizeDataSource(row?.data_source ?? row?.dataSource),
    }));
}

function normalizeTeamToken(value) {
    return String(value || '')
        .toLowerCase()
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]+/g, '');
}

function candidateMatchesTargetId(candidates, targetId) {
    return normalizeCandidates(candidates).some(candidate =>
        [candidate.match_id, candidate.external_id].some(value => String(value || '').includes(String(targetId || '')))
    );
}

function candidateMatchesTargetLabel(candidates, targetLabel) {
    const expectedHome = normalizeTargetLabel(targetLabel).includes('angers');
    const expectedAway = normalizeTargetLabel(targetLabel).includes('strasbourg');
    if (!expectedHome || !expectedAway) {
        return false;
    }

    return normalizeCandidates(candidates).some(candidate => {
        const home = normalizeTeamToken(candidate.home_team);
        const away = normalizeTeamToken(candidate.away_team);
        return (
            (home.includes('angers') && away.includes('strasbourg')) ||
            (home.includes('strasbourg') && away.includes('angers'))
        );
    });
}

function buildAffectedMatchIds(candidates) {
    return [...new Set(normalizeCandidates(candidates).map(candidate => candidate.match_id))];
}

function buildInsertRows(candidates) {
    return normalizeCandidates(candidates).map(candidate => ({
        match_id: candidate.match_id,
        external_id: candidate.external_id,
        league_name: candidate.league_name,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        match_date: candidate.match_date,
        status: candidate.status,
        is_finished: candidate.is_finished === true,
        data_source: candidate.data_source,
    }));
}

function buildUpsertSqlPlan(rows) {
    if (!Array.isArray(rows) || rows.length === 0) {
        throw new Error('rows are required for buildUpsertSqlPlan');
    }

    const values = [];
    const placeholders = rows.map((row, index) => {
        const offset = index * ALLOWED_INSERT_COLUMNS.length;
        ALLOWED_INSERT_COLUMNS.forEach(column => {
            values.push(row[column]);
        });
        return `(${ALLOWED_INSERT_COLUMNS.map((_, columnIndex) => `$${offset + columnIndex + 1}`).join(', ')})`;
    });

    return {
        table: 'matches',
        columns: [...ALLOWED_INSERT_COLUMNS],
        rowCount: rows.length,
        values,
        text: `
            INSERT INTO matches (
                ${ALLOWED_INSERT_COLUMNS.join(', ')}
            )
            VALUES ${placeholders.join(', ')}
            ON CONFLICT (match_id) DO UPDATE SET
                external_id = EXCLUDED.external_id,
                league_name = EXCLUDED.league_name,
                season = EXCLUDED.season,
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                match_date = EXCLUDED.match_date,
                status = EXCLUDED.status,
                is_finished = EXCLUDED.is_finished,
                data_source = EXCLUDED.data_source,
                updated_at = NOW()
            RETURNING match_id, (xmax = 0) AS inserted;
        `,
    };
}

function buildSelectExistingMatchesQuery(matchIds) {
    return {
        text: `
            SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status, is_finished, data_source
            FROM matches
            WHERE match_id = ANY($1::text[])
            ORDER BY match_date, match_id;
        `,
        values: [matchIds],
    };
}

function buildCountQuery() {
    return {
        text: `
            SELECT 'matches' AS table_name, COUNT(*)::int AS rows FROM matches
            UNION ALL
            SELECT 'bookmaker_odds_history', COUNT(*)::int FROM bookmaker_odds_history
            UNION ALL
            SELECT 'raw_match_data', COUNT(*)::int FROM raw_match_data
            UNION ALL
            SELECT 'l3_features', COUNT(*)::int FROM l3_features
            UNION ALL
            SELECT 'match_features_training', COUNT(*)::int FROM match_features_training
            UNION ALL
            SELECT 'predictions', COUNT(*)::int FROM predictions;
        `,
        values: [],
    };
}

function mapCountRows(rows) {
    const counts = Object.fromEntries(COUNT_TABLES.map(tableName => [tableName, null]));
    (rows || []).forEach(row => {
        counts[String(row.table_name)] = Number(row.rows);
    });
    return counts;
}

function diffControlledFields(candidate, existingRow) {
    return [
        'external_id',
        'league_name',
        'season',
        'home_team',
        'away_team',
        'match_date',
        'status',
        'is_finished',
        'data_source',
    ].filter(field => {
        const left = candidate[field] ?? null;
        const right = existingRow[field] ?? null;
        return left !== right;
    });
}

function buildAffectedPreview(candidates, existingMatches) {
    const existingMap = new Map(
        normalizeExistingMatches(existingMatches)
            .filter(row => row.match_id)
            .map(row => [row.match_id, row])
    );

    return normalizeCandidates(candidates).map(candidate => {
        const existingRow = existingMap.get(candidate.match_id) || null;
        if (!existingRow) {
            return {
                match_id: candidate.match_id,
                external_id: candidate.external_id,
                home_team: candidate.home_team,
                away_team: candidate.away_team,
                match_date: candidate.match_date,
                league_name: candidate.league_name,
                season: candidate.season,
                status: candidate.status,
                existing_row_found: false,
                decision: 'would_insert',
                reason: 'match_id not found in matches',
            };
        }

        const differingFields = diffControlledFields(candidate, existingRow);
        if (differingFields.length === 0) {
            return {
                match_id: candidate.match_id,
                external_id: candidate.external_id,
                home_team: candidate.home_team,
                away_team: candidate.away_team,
                match_date: candidate.match_date,
                league_name: candidate.league_name,
                season: candidate.season,
                status: candidate.status,
                existing_row_found: true,
                decision: 'would_skip',
                reason: 'existing matches row already matches controlled seed fields',
            };
        }

        return {
            match_id: candidate.match_id,
            external_id: candidate.external_id,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            match_date: candidate.match_date,
            league_name: candidate.league_name,
            season: candidate.season,
            status: candidate.status,
            existing_row_found: true,
            decision: 'would_update',
            reason: `existing matches row differs on: ${differingFields.join(', ')}`,
        };
    });
}

function countDecisions(affectedPreview, decision) {
    return affectedPreview.filter(item => item.decision === decision).length;
}

async function readStdinText(io = {}, dependencies = {}) {
    if (typeof dependencies.stdinText === 'string') {
        return dependencies.stdinText;
    }

    const stdin = io.stdin || process.stdin;
    if (!stdin || typeof stdin.on !== 'function') {
        return '';
    }

    return new Promise(resolve => {
        let buffer = '';
        stdin.setEncoding?.('utf8');
        stdin.on('data', chunk => {
            buffer += chunk;
        });
        stdin.on('end', () => resolve(buffer));
        stdin.on('error', () => resolve(''));
        if (stdin.readableEnded === true) {
            resolve(buffer);
        }
    });
}

async function resolveCandidatesFromSafePreview(input, dependencies = {}) {
    const safePreview = dependencies.safePreviewModule || require('./l1_discovery_safe_preview');
    const payload = await safePreview.buildL1DiscoveryPlanPreview(
        {
            source: input.source,
            scope: PREVIEW_SCOPE,
            leagueId: input.leagueId,
            season: input.season,
            date: input.date,
            concurrency: SAFE_NETWORK_CONCURRENCY,
            maxTargets: SAFE_NETWORK_MAX_TARGETS,
            dryRun: true,
            networkPreview: true,
            networkAuthorization: true,
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
            allowDbWrite: false,
        },
        {
            fetch: dependencies.fetch,
            timeoutMs: dependencies.timeoutMs || SAFE_NETWORK_TIMEOUT_MS,
        }
    );

    return {
        candidates: payload.candidates_preview || payload.candidates || [],
        exactCandidateSetSource: 'safe_controlled_network_preview',
        sourceUrlUsed: payload.source_url_used || null,
        networkUsed: payload.external_network_used === true,
    };
}

async function resolveCandidates(input, stdinText, dependencies = {}) {
    if (Array.isArray(dependencies.candidates)) {
        return {
            candidates: dependencies.candidates,
            exactCandidateSetSource: 'dependency_candidates',
            sourceUrlUsed: dependencies.sourceUrlUsed || null,
            networkUsed: false,
        };
    }

    if (typeof dependencies.resolveCandidates === 'function') {
        return dependencies.resolveCandidates({ input, stdinText });
    }

    if (input.candidatesJson) {
        return {
            candidates: parseJsonText(input.candidatesJson, 'candidates-json'),
            exactCandidateSetSource: 'candidates_json_argument',
            sourceUrlUsed: null,
            networkUsed: false,
        };
    }

    const trimmedStdin = String(stdinText || '').trim();
    if (trimmedStdin) {
        return {
            candidates: parseJsonText(trimmedStdin, 'stdin candidates payload'),
            exactCandidateSetSource: 'stdin_candidates_payload',
            sourceUrlUsed: null,
            networkUsed: false,
        };
    }

    return resolveCandidatesFromSafePreview(input, dependencies);
}

async function resolveExistingMatches(input, affectedMatchIds, dependencies = {}) {
    if (Array.isArray(dependencies.existingMatches)) {
        return dependencies.existingMatches;
    }

    if (typeof dependencies.selectExistingMatches === 'function') {
        return dependencies.selectExistingMatches({ input, matchIds: affectedMatchIds });
    }

    if (input.existingMatchesJson) {
        return parseJsonText(input.existingMatchesJson, 'existing-matches-json');
    }

    return null;
}

function createPgPool() {
    const { Pool } = require('pg');
    return new Pool({
        host: process.env.DB_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || '5432', 10),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        application_name: 'l1_matches_seed_commit_execute',
        max: 2,
        idleTimeoutMillis: 5000,
        connectionTimeoutMillis: 5000,
    });
}

async function selectProtectedRowCounts(client, dependencies = {}) {
    if (typeof dependencies.selectProtectedRowCounts === 'function') {
        return dependencies.selectProtectedRowCounts(client);
    }

    const query = buildCountQuery();
    const result = await client.query(query.text, query.values);
    return mapCountRows(result.rows);
}

async function selectExistingMatchesWithinTransaction(client, affectedMatchIds, dependencies = {}) {
    if (typeof dependencies.selectExistingMatchesWithinTransaction === 'function') {
        return dependencies.selectExistingMatchesWithinTransaction(client, affectedMatchIds);
    }

    const query = buildSelectExistingMatchesQuery(affectedMatchIds);
    const result = await client.query(query.text, query.values);
    return result.rows || [];
}

function buildPostCommitVerification(beforeCounts = {}, afterCounts = {}) {
    const l3FeaturesUnchanged = beforeCounts.l3_features === afterCounts.l3_features;
    const trainingFeaturesUnchanged = beforeCounts.match_features_training === afterCounts.match_features_training;

    return {
        matches_row_count_before: beforeCounts.matches ?? null,
        matches_row_count_after: afterCounts.matches ?? null,
        bookmaker_odds_history_unchanged: beforeCounts.bookmaker_odds_history === afterCounts.bookmaker_odds_history,
        raw_match_data_unchanged: beforeCounts.raw_match_data === afterCounts.raw_match_data,
        l3_features_unchanged: l3FeaturesUnchanged,
        match_features_training_unchanged: trainingFeaturesUnchanged,
        features_unchanged: l3FeaturesUnchanged && trainingFeaturesUnchanged,
        predictions_unchanged: beforeCounts.predictions === afterCounts.predictions,
    };
}

function buildControlledExecutionResult(details = {}) {
    const verification = buildPostCommitVerification(details.beforeCounts, details.afterCounts);
    return {
        phase: PHASE,
        execution_completed: true,
        source: details.input.source,
        scope: details.input.scope,
        league_id: details.input.leagueId,
        season: details.input.season,
        date: details.input.date,
        candidate_count: details.input.candidateCount,
        max_seed_rows: details.input.maxSeedRows,
        contains_target_match_id: details.input.containsTargetMatchId,
        contains_target_label: details.input.containsTargetLabel,
        final_db_write_confirmation: true,
        db_write_executed: true,
        matches_write_executed: true,
        raw_match_data_write_executed: false,
        inserted_count: details.insertedCount,
        updated_count: details.updatedCount,
        skipped_count: details.skippedCount,
        affected_match_ids: details.affectedMatchIds,
        exact_candidate_set_source: details.exactCandidateSetSource,
        source_url_used: details.sourceUrlUsed || null,
        existing_affected_matches_count: details.existingAffectedMatchesCount,
        affected_preview: details.affectedPreview,
        transaction: details.transaction,
        post_commit_verification: verification,
        safety_summary: {
            called_titan_discovery: false,
            called_discovery_service_discover: false,
            called_fixture_repository_persist: false,
            wrote_matches: true,
            wrote_raw_match_data: false,
            trained: false,
            predicted: false,
        },
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildControlledErrorPayload(input = {}, errors = [], details = {}) {
    const value = normalizeExecutionInput(input);
    const beforeCounts = details.beforeCounts || {};
    const afterCounts = details.afterCounts || beforeCounts;
    const transaction = details.transaction || {
        began: false,
        committed: false,
        rolled_back: false,
    };

    return {
        phase: PHASE,
        execution_completed: false,
        source: value.source || null,
        scope: value.scope || null,
        league_id: value.leagueId,
        season: value.season,
        date: value.date,
        candidate_count: value.candidateCount,
        max_seed_rows: value.maxSeedRows,
        contains_target_match_id: value.containsTargetMatchId,
        contains_target_label: value.containsTargetLabel,
        final_db_write_confirmation: value.finalDbWriteConfirmation === true,
        db_write_executed: false,
        matches_write_executed: false,
        raw_match_data_write_executed: false,
        inserted_count: 0,
        updated_count: 0,
        skipped_count: 0,
        affected_match_ids: details.affectedMatchIds || [],
        exact_candidate_set_source: details.exactCandidateSetSource || null,
        source_url_used: details.sourceUrlUsed || null,
        existing_affected_matches_count: details.existingAffectedMatchesCount ?? null,
        affected_preview: details.affectedPreview || [],
        transaction,
        post_commit_verification: buildPostCommitVerification(beforeCounts, afterCounts),
        safety_summary: {
            called_titan_discovery: false,
            called_discovery_service_discover: false,
            called_fixture_repository_persist: false,
            wrote_matches: false,
            wrote_raw_match_data: false,
            trained: false,
            predicted: false,
        },
        errors: Array.isArray(errors) ? errors : [String(errors)],
        next_required_phase: null,
    };
}

async function executeMatchesSeedTransaction(input = {}, dependencies = {}) {
    const validation = validateExecutionInput(input);
    if (!validation.ok) {
        const error = new Error(validation.errors[0]);
        error.validationErrors = validation.errors;
        throw error;
    }

    const value = validation.value;
    const stdinText = typeof dependencies.stdinText === 'string' ? dependencies.stdinText : '';
    const candidateResolution = await resolveCandidates(value, stdinText, dependencies);
    const candidates = normalizeCandidates(candidateResolution.candidates);

    if (candidates.length !== value.candidateCount) {
        throw new Error(
            `exact candidate set count mismatch: expected ${value.candidateCount}, got ${candidates.length}`
        );
    }
    if (candidates.length > value.maxSeedRows) {
        throw new Error(`exact candidate set exceeds max-seed-rows=${value.maxSeedRows}`);
    }
    if (!candidateMatchesTargetId(candidates, value.containsTargetMatchId)) {
        throw new Error(`target match id candidate not found: ${value.containsTargetMatchId}`);
    }
    if (!candidateMatchesTargetLabel(candidates, value.containsTargetLabel)) {
        throw new Error(`target label candidate not found: ${value.containsTargetLabel}`);
    }

    const affectedMatchIds = buildAffectedMatchIds(candidates);
    const externalExisting = normalizeExistingMatches(
        (await resolveExistingMatches(value, affectedMatchIds, dependencies)) || []
    );
    const externalPreview = buildAffectedPreview(candidates, externalExisting);
    const externalInsertCount = countDecisions(externalPreview, 'would_insert');
    const externalUpdateCount = countDecisions(externalPreview, 'would_update');
    const externalSkipCount = countDecisions(externalPreview, 'would_skip');

    if (
        externalInsertCount !== EXACT_CANDIDATE_COUNT ||
        externalUpdateCount !== 0 ||
        externalSkipCount !== 0 ||
        externalExisting.length !== 0
    ) {
        throw new Error(
            `preflight mismatch detected before transaction: existing=${externalExisting.length}, would_insert=${externalInsertCount}, would_update=${externalUpdateCount}, would_skip=${externalSkipCount}`
        );
    }

    const pool = dependencies.pool || createPgPool();
    const ownsPool = !dependencies.pool;
    const transaction = {
        began: false,
        committed: false,
        rolled_back: false,
    };

    let client = null;
    let beforeCounts = null;
    let afterCounts = null;
    let transactionPreview = externalPreview;
    let transactionExistingMatches = externalExisting;
    let insertedCount = 0;
    let updatedCount = 0;
    let skippedCount = 0;

    try {
        client = dependencies.client || (await pool.connect());
        transaction.began = true;
        await client.query('BEGIN');

        beforeCounts = await selectProtectedRowCounts(client, dependencies);
        transactionExistingMatches = normalizeExistingMatches(
            await selectExistingMatchesWithinTransaction(client, affectedMatchIds, dependencies)
        );
        transactionPreview = buildAffectedPreview(candidates, transactionExistingMatches);

        const wouldInsertCount = countDecisions(transactionPreview, 'would_insert');
        const wouldUpdateCount = countDecisions(transactionPreview, 'would_update');
        const wouldSkipCount = countDecisions(transactionPreview, 'would_skip');

        if (
            transactionExistingMatches.length !== 0 ||
            wouldInsertCount !== EXACT_CANDIDATE_COUNT ||
            wouldUpdateCount !== 0 ||
            wouldSkipCount !== 0
        ) {
            throw new Error(
                `execution preflight mismatch inside transaction: existing=${transactionExistingMatches.length}, would_insert=${wouldInsertCount}, would_update=${wouldUpdateCount}, would_skip=${wouldSkipCount}`
            );
        }

        const rows = buildInsertRows(candidates);
        const sqlPlan = buildUpsertSqlPlan(rows);
        const queryResult = await client.query(sqlPlan.text, sqlPlan.values);
        const resultRows = Array.isArray(queryResult.rows) ? queryResult.rows : [];
        insertedCount = resultRows.filter(row => row.inserted === true).length;
        updatedCount = resultRows.length - insertedCount;
        skippedCount = 0;

        if (insertedCount !== EXACT_CANDIDATE_COUNT || updatedCount !== 0 || skippedCount !== 0) {
            throw new Error(
                `transaction write result mismatch: inserted=${insertedCount}, updated=${updatedCount}, skipped=${skippedCount}`
            );
        }

        afterCounts = await selectProtectedRowCounts(client, dependencies);
        const verification = buildPostCommitVerification(beforeCounts, afterCounts);

        if (afterCounts.matches !== beforeCounts.matches + EXACT_CANDIDATE_COUNT) {
            throw new Error(
                `matches row count delta mismatch: before=${beforeCounts.matches}, after=${afterCounts.matches}`
            );
        }
        if (
            verification.bookmaker_odds_history_unchanged !== true ||
            verification.raw_match_data_unchanged !== true ||
            verification.features_unchanged !== true ||
            verification.predictions_unchanged !== true
        ) {
            throw new Error('post-commit verification failed: protected tables changed unexpectedly');
        }

        await client.query('COMMIT');
        transaction.committed = true;

        return buildControlledExecutionResult({
            input: value,
            exactCandidateSetSource: candidateResolution.exactCandidateSetSource,
            sourceUrlUsed: candidateResolution.sourceUrlUsed || null,
            existingAffectedMatchesCount: transactionExistingMatches.length,
            affectedPreview: transactionPreview,
            insertedCount,
            updatedCount,
            skippedCount,
            affectedMatchIds,
            transaction,
            beforeCounts,
            afterCounts,
        });
    } catch (error) {
        if (transaction.began && transaction.committed !== true && client) {
            try {
                await client.query('ROLLBACK');
                transaction.rolled_back = true;
            } catch (rollbackError) {
                error.rollbackError = rollbackError;
            }
        }

        if (client && beforeCounts) {
            try {
                afterCounts = await selectProtectedRowCounts(client, dependencies);
            } catch (countError) {
                error.afterCountError = countError;
            }
        }

        error.controlledPayload = buildControlledErrorPayload(value, error.validationErrors || [error.message], {
            transaction,
            beforeCounts: beforeCounts || {},
            afterCounts: afterCounts || beforeCounts || {},
            affectedMatchIds,
            affectedPreview: transactionPreview,
            exactCandidateSetSource: candidateResolution.exactCandidateSetSource,
            sourceUrlUsed: candidateResolution.sourceUrlUsed || null,
            existingAffectedMatchesCount: transactionExistingMatches.length,
        });
        throw error;
    } finally {
        if (!dependencies.client && client && typeof client.release === 'function') {
            client.release();
        }
        if (ownsPool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

function showHelp(io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    stdout(
        [
            'Usage:',
            '  node scripts/ops/l1_matches_seed_commit_execute.js --source=fotmob --scope=league_season_date --league-id=53 --season=2025/2026 --date=2026-05-10 --candidate-count=8 --contains-target-match-id=4830746 --contains-target-label="Angers vs Strasbourg" --max-seed-rows=10 --final-db-write-confirmation=yes --allow-db-write-now=yes --allow-matches-write-now=yes --allow-raw-match-data-write=no --allow-training=no --allow-prediction=no',
            '',
            'Optional:',
            "  --candidates-json='[...]'",
            "  --existing-matches-json='[...]'",
            '  stdin JSON array/object for candidates',
            '',
            'Phase 5.09L1: controlled execution only, exact 2026-05-10 FotMob Ligue 1 candidates, matches-only transaction.',
        ].join('\n')
    );
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const stderr = io.stderr || (text => process.stderr.write(text));
    const options = parseArgs(argv);
    const dependenciesProvideCandidates =
        Array.isArray(dependencies.candidates) || typeof dependencies.resolveCandidates === 'function';
    const shouldReadStdin =
        Object.prototype.hasOwnProperty.call(dependencies, 'stdinText') ||
        typeof io.stdin?.on === 'function' ||
        (!options.candidatesJson && !dependenciesProvideCandidates);

    if (options.help) {
        showHelp({ stdout });
        return 0;
    }

    try {
        const stdinText = shouldReadStdin ? await readStdinText(io, dependencies) : '';
        const payload = await executeMatchesSeedTransaction(
            options,
            Object.prototype.hasOwnProperty.call(dependencies, 'stdinText')
                ? dependencies
                : { ...dependencies, stdinText }
        );
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 0;
    } catch (error) {
        const payload =
            error.controlledPayload || buildControlledErrorPayload(options, error.validationErrors || [error.message]);
        stderr(`${payload.errors[0]}\n`);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 1;
    }
}

if (require.main === module) {
    runCli().then(code => {
        process.exitCode = code;
    });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validateExecutionInput,
    normalizeCandidates,
    normalizeExistingMatches,
    buildAffectedPreview,
    buildAffectedMatchIds,
    buildInsertRows,
    buildUpsertSqlPlan,
    executeMatchesSeedTransaction,
    buildPostCommitVerification,
    buildControlledExecutionResult,
    runCli,
};
