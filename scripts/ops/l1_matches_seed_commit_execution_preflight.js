#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
'use strict';

const PHASE = 'PHASE5_08L1_CONTROLLED_MATCHES_SEED_COMMIT_EXECUTION_PREFLIGHT';
const SAFE_SOURCE = 'fotmob';
const SAFE_SCOPES = new Set(['league_season_date', 'controlled_candidates_preview']);
const MAX_SEED_ROWS_LIMIT = 10;
const DEFAULT_MAX_SEED_ROWS = 10;
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: L1 matches seed commit execution remains preflight-only in Phase 5.08L1.';
const NEXT_REQUIRED_PHASE = 'Phase 5.09L1 controlled matches seed commit execution';
const PREVIEW_SCOPE = 'controlled_candidates_preview';
const SAFE_NETWORK_CONCURRENCY = 1;
const SAFE_NETWORK_MAX_TARGETS = 10;
const SAFE_NETWORK_TIMEOUT_MS = 15000;
const CONTROLLED_FIELD_NAMES = [
    'external_id',
    'league_name',
    'season',
    'home_team',
    'away_team',
    'match_date',
    'status',
    'data_source',
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
        commit: false,
        execute: false,
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
        commit: 'commit',
        execute: 'execute',
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
        'commit',
        'execute',
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

function normalizeExecutionPreflightInput(input = {}) {
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
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        candidatesJson: typeof input.candidatesJson === 'string' ? input.candidatesJson : null,
        existingMatchesJson: typeof input.existingMatchesJson === 'string' ? input.existingMatchesJson : null,
    };
}

function validateSourceScope(value, errors) {
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
}

function validateRequiredFields(value, errors) {
    if (!value.leagueId) {
        errors.push('missing league-id');
    }
    if (!value.season) {
        errors.push('missing season');
    }
    if (!value.date) {
        errors.push('missing date');
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(value.date)) {
        errors.push('invalid date: provide YYYY-MM-DD');
    }
    if (!value.containsTargetMatchId) {
        errors.push('missing contains-target-match-id');
    }
    if (!value.containsTargetLabel) {
        errors.push('missing contains-target-label');
    }
}

function validateLimits(value, errors) {
    if (!Number.isInteger(value.candidateCount) || value.candidateCount < 0) {
        errors.push('invalid candidate-count: provide a non-negative integer');
    }
    if (!Number.isInteger(value.maxSeedRows) || value.maxSeedRows < 1) {
        errors.push('invalid max-seed-rows: provide a positive integer');
    } else if (value.maxSeedRows > MAX_SEED_ROWS_LIMIT) {
        errors.push(`max-seed-rows > ${MAX_SEED_ROWS_LIMIT} is blocked in Phase 5.08L1`);
    }
    if (
        Number.isInteger(value.candidateCount) &&
        Number.isInteger(value.maxSeedRows) &&
        value.candidateCount > value.maxSeedRows
    ) {
        errors.push('candidate-count must be <= max-seed-rows');
    }
}

function validateBlockedFlags(value, errors) {
    if (value.finalDbWriteConfirmation === true) {
        errors.push('final-db-write-confirmation=yes is blocked in Phase 5.08L1');
    }
    if (value.allowDbWriteNow === true) {
        errors.push('allow-db-write-now=yes is blocked in Phase 5.08L1');
    }
    if (value.allowMatchesWriteNow === true) {
        errors.push('allow-matches-write-now=yes is blocked in Phase 5.08L1');
    }
    if (value.allowRawMatchDataWrite === true) {
        errors.push('allow-raw-match-data-write=yes is blocked in Phase 5.08L1');
    }
    if (value.allowTraining === true) {
        errors.push('allow-training=yes is blocked in Phase 5.08L1');
    }
    if (value.allowPrediction === true) {
        errors.push('allow-prediction=yes is blocked in Phase 5.08L1');
    }
    if (value.commit === true) {
        errors.push(BLOCKED_COMMIT_MESSAGE);
    }
    if (value.execute === true) {
        errors.push('execute=yes is blocked in Phase 5.08L1');
    }
}

function validateExecutionPreflightInput(input = {}) {
    const value = normalizeExecutionPreflightInput(input);
    const errors = [];

    validateSourceScope(value, errors);
    validateRequiredFields(value, errors);
    validateLimits(value, errors);
    validateBlockedFlags(value, errors);

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
        data_source: normalizeDataSource(row?.data_source ?? row?.dataSource),
    }));
}

function diffControlledFields(candidate, existingRow) {
    return CONTROLLED_FIELD_NAMES.filter(field => {
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

function buildTransactionPlan(input) {
    return {
        begin: 'BEGIN',
        row_limit: `rows <= ${input.maxSeedRows}`,
        row_limit_enforced: true,
        allowed_table: 'matches',
        forbidden_tables: ['raw_match_data', 'l3_features', 'match_features_training', 'predictions'],
        upsert_strategy: 'upsert by match_id',
        raw_match_data_write_allowed: false,
        feature_write_allowed: false,
        prediction_write_allowed: false,
        rollback_on_error: 'ROLLBACK on error',
        commit_condition: 'COMMIT only after final confirmation in next phase',
        steps: [
            'BEGIN',
            `validate rows <= ${input.maxSeedRows}`,
            'operate on matches only',
            'upsert by match_id',
            'ROLLBACK on error',
            'COMMIT only after final confirmation in next phase',
        ],
    };
}

function buildBackupPlan() {
    return {
        execute_backup_this_phase: false,
        select_existing_affected_rows_before_commit: true,
        include_baseline_counts: true,
        baseline_count_tables: ['matches', 'raw_match_data', 'l3_features', 'match_features_training', 'predictions'],
        pg_dump_allowed_this_phase: false,
        backup_file_write_allowed_this_phase: false,
        future_backup_artifact_requires_separate_user_authorization: true,
    };
}

function buildRollbackPlan() {
    return {
        execute_rollback_this_phase: false,
        transaction_rollback_on_failure: true,
        affected_rows_snapshot_required_for_later_compensation: true,
        later_restore_requires_authorization: true,
        delete_allowed_this_phase: false,
        rollback_file_write_allowed_this_phase: false,
    };
}

function buildPostCommitVerificationPlan() {
    return {
        matches_row_count_delta_expected: true,
        affected_match_ids_exist: true,
        raw_match_data_unchanged: true,
        l3_features_unchanged: true,
        match_features_training_unchanged: true,
        predictions_unchanged: true,
        no_training_prediction_executed: true,
    };
}

function candidateMatchesTargetId(candidates, targetId) {
    return normalizeCandidates(candidates).some(candidate =>
        [candidate.match_id, candidate.external_id].some(value => String(value || '').includes(String(targetId || '')))
    );
}

function candidateMatchesTargetLabel(candidates, targetLabel) {
    const label = String(targetLabel || '')
        .trim()
        .toLowerCase();
    if (!label) {
        return false;
    }

    return normalizeCandidates(candidates).some(candidate => {
        const pair = `${candidate.home_team} vs ${candidate.away_team}`.toLowerCase();
        const reversePair = `${candidate.away_team} vs ${candidate.home_team}`.toLowerCase();
        return pair === label || reversePair === label;
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
        exact_candidate_set_source: 'safe_controlled_network_preview',
        source_url_used: payload.source_url_used || null,
        network_used: payload.external_network_used === true,
        contains_target_match_id_candidate: payload.contains_target_match_id_candidate === true,
        contains_angers_strasbourg_candidate:
            payload.contains_angers_strasbourg_candidate === true ||
            payload.contains_anglers_strasbourg_candidate === true,
    };
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

async function resolveCandidates(input, stdinText, dependencies = {}) {
    if (Array.isArray(dependencies.candidates)) {
        return {
            candidates: dependencies.candidates,
            exact_candidate_set_source: 'dependency_candidates',
            source_url_used: dependencies.sourceUrlUsed || null,
            network_used: false,
        };
    }

    if (typeof dependencies.resolveCandidates === 'function') {
        return dependencies.resolveCandidates({ input, stdinText });
    }

    if (input.candidatesJson) {
        return {
            candidates: parseJsonText(input.candidatesJson, 'candidates-json'),
            exact_candidate_set_source: 'candidates_json_argument',
            source_url_used: null,
            network_used: false,
        };
    }

    const trimmedStdin = String(stdinText || '').trim();
    if (trimmedStdin) {
        return {
            candidates: parseJsonText(trimmedStdin, 'stdin candidates payload'),
            exact_candidate_set_source: 'stdin_candidates_payload',
            source_url_used: null,
            network_used: false,
        };
    }

    return resolveCandidatesFromSafePreview(input, dependencies);
}

function buildSelectExistingMatchesQuery(matchIds) {
    return {
        text: `
            SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status, data_source
            FROM matches
            WHERE match_id = ANY($1::text[])
            ORDER BY match_date, match_id;
        `,
        values: [matchIds],
    };
}

async function defaultSelectExistingMatches(matchIds) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
        return [];
    }

    const { Pool } = require('pg');
    const pool = new Pool({
        host: process.env.DB_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || '5432', 10),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        application_name: 'l1_matches_seed_execution_preflight',
        max: 2,
        idleTimeoutMillis: 5000,
        connectionTimeoutMillis: 5000,
    });

    try {
        const query = buildSelectExistingMatchesQuery(matchIds);
        const result = await pool.query(query.text, query.values);
        return result.rows || [];
    } finally {
        await pool.end();
    }
}

async function resolveExistingMatches(input, candidates, dependencies = {}) {
    if (Array.isArray(dependencies.existingMatches)) {
        return dependencies.existingMatches;
    }

    if (typeof dependencies.selectExistingMatches === 'function') {
        return dependencies.selectExistingMatches({
            input,
            matchIds: normalizeCandidates(candidates).map(candidate => candidate.match_id),
        });
    }

    if (input.existingMatchesJson) {
        return parseJsonText(input.existingMatchesJson, 'existing-matches-json');
    }

    return defaultSelectExistingMatches(normalizeCandidates(candidates).map(candidate => candidate.match_id));
}

function countDecisions(affectedPreview, decision) {
    return affectedPreview.filter(item => item.decision === decision).length;
}

async function buildMatchesSeedExecutionPreflight(input = {}, dependencies = {}) {
    const validation = validateExecutionPreflightInput(input);
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

    const existingMatches = normalizeExistingMatches(await resolveExistingMatches(value, candidates, dependencies));
    const affectedPreview = buildAffectedPreview(candidates, existingMatches);

    return {
        phase: PHASE,
        execution_preflight_only: true,
        source: value.source,
        scope: value.scope,
        league_id: value.leagueId,
        season: value.season,
        date: value.date,
        candidate_count: value.candidateCount,
        max_seed_rows: value.maxSeedRows,
        contains_target_match_id: value.containsTargetMatchId,
        contains_target_label: value.containsTargetLabel,
        exact_candidate_set_captured: true,
        exact_candidate_set_source: candidateResolution.exact_candidate_set_source || 'unknown',
        source_url_used: candidateResolution.source_url_used || null,
        candidate_match_ids: candidates.map(candidate => candidate.match_id),
        contains_target_match_id_candidate:
            candidateResolution.contains_target_match_id_candidate === true ||
            candidateMatchesTargetId(candidates, value.containsTargetMatchId),
        contains_angers_strasbourg_candidate:
            candidateResolution.contains_angers_strasbourg_candidate === true ||
            candidateMatchesTargetLabel(candidates, value.containsTargetLabel),
        affected_matches_selected: true,
        existing_affected_matches_count: existingMatches.length,
        would_insert_count: countDecisions(affectedPreview, 'would_insert'),
        would_update_count: countDecisions(affectedPreview, 'would_update'),
        would_skip_count: countDecisions(affectedPreview, 'would_skip'),
        affected_preview: affectedPreview,
        transaction_plan: buildTransactionPlan(value),
        backup_plan: buildBackupPlan(),
        rollback_plan: buildRollbackPlan(),
        post_commit_verification_plan: buildPostCommitVerificationPlan(),
        final_db_write_confirmation_required: true,
        commit_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed_this_phase: false,
        raw_match_data_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        would_write_matches: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_call_fixture_repository_persist: false,
        would_call_discovery_service_discover: false,
        would_run_titan_discovery: false,
        would_train: false,
        would_predict: false,
        commit_gate: 'blocked_this_phase',
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildErrorPayload(options, errors) {
    const value = normalizeExecutionPreflightInput(options);
    return {
        phase: PHASE,
        execution_preflight_only: true,
        ok: false,
        errors: Array.isArray(errors) ? errors : [String(errors)],
        source: value.source || null,
        scope: value.scope || null,
        league_id: value.leagueId,
        season: value.season,
        date: value.date,
        candidate_count: value.candidateCount,
        max_seed_rows: value.maxSeedRows,
        contains_target_match_id: value.containsTargetMatchId,
        contains_target_label: value.containsTargetLabel,
        exact_candidate_set_captured: false,
        affected_matches_selected: false,
        would_insert_count: 0,
        would_update_count: 0,
        would_skip_count: 0,
        affected_preview: [],
        transaction_plan: buildTransactionPlan(value),
        backup_plan: buildBackupPlan(),
        rollback_plan: buildRollbackPlan(),
        post_commit_verification_plan: buildPostCommitVerificationPlan(),
        final_db_write_confirmation_required: true,
        commit_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed_this_phase: false,
        raw_match_data_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        would_write_matches: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_call_fixture_repository_persist: false,
        would_call_discovery_service_discover: false,
        would_run_titan_discovery: false,
        would_train: false,
        would_predict: false,
        commit_gate: 'blocked_this_phase',
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function showHelp(io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    stdout(
        [
            'Usage:',
            '  node scripts/ops/l1_matches_seed_commit_execution_preflight.js --source=fotmob --scope=league_season_date --league-id=53 --season=2025/2026 --date=2026-05-10 --candidate-count=8 --contains-target-match-id=4830746 --contains-target-label="Angers vs Strasbourg" --max-seed-rows=10 --final-db-write-confirmation=no --allow-db-write-now=no --allow-matches-write-now=no --allow-raw-match-data-write=no --allow-training=no --allow-prediction=no',
            '',
            'Optional:',
            "  --candidates-json='[...]'",
            "  --existing-matches-json='[...]'",
            '  stdin JSON array/object for candidates',
            '',
            'Phase 5.08L1: execution preflight only, SELECT-only, no DB writes, no matches/raw writes.',
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
        const payload = await buildMatchesSeedExecutionPreflight(
            options,
            Object.prototype.hasOwnProperty.call(dependencies, 'stdinText')
                ? dependencies
                : { ...dependencies, stdinText }
        );
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 0;
    } catch (error) {
        const payload = buildErrorPayload(options, error.validationErrors || [error.message]);
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
    validateExecutionPreflightInput,
    normalizeCandidates,
    normalizeExistingMatches,
    buildAffectedPreview,
    buildTransactionPlan,
    buildBackupPlan,
    buildRollbackPlan,
    buildPostCommitVerificationPlan,
    buildMatchesSeedExecutionPreflight,
    runCli,
};
