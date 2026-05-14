#!/usr/bin/env node
/* eslint-disable complexity */
'use strict';

const PHASE = 'PHASE5_17L2_REMAINING_RAW_MATCH_DATA_ACQUISITION_PLANNING';
const NEXT_REQUIRED_PHASE = 'Phase 5.18L2 remaining raw_match_data acquisition authorization';
const EXPECTED_SCOPE = Object.freeze({
    source: 'fotmob',
    leagueId: '53',
    season: '2025/2026',
    date: '2026-05-10',
    expectedSeededCount: 8,
    expectedExistingRawCount: 1,
    expectedMissingRawCount: 7,
    rawRoute: 'html_hydration',
});
const EXPECTED_SEEDED_MATCHES = Object.freeze([
    Object.freeze({
        match_id: '53_20252026_4830746',
        external_id: '4830746',
        home_team: 'Angers',
        away_team: 'Strasbourg',
    }),
    Object.freeze({
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        home_team: 'Auxerre',
        away_team: 'Nice',
    }),
    Object.freeze({
        match_id: '53_20252026_4830748',
        external_id: '4830748',
        home_team: 'Le Havre',
        away_team: 'Marseille',
    }),
    Object.freeze({
        match_id: '53_20252026_4830750',
        external_id: '4830750',
        home_team: 'Metz',
        away_team: 'Lorient',
    }),
    Object.freeze({
        match_id: '53_20252026_4830751',
        external_id: '4830751',
        home_team: 'Monaco',
        away_team: 'Lille',
    }),
    Object.freeze({
        match_id: '53_20252026_4830752',
        external_id: '4830752',
        home_team: 'Paris Saint-Germain',
        away_team: 'Brest',
    }),
    Object.freeze({
        match_id: '53_20252026_4830753',
        external_id: '4830753',
        home_team: 'Rennes',
        away_team: 'Paris FC',
    }),
    Object.freeze({
        match_id: '53_20252026_4830754',
        external_id: '4830754',
        home_team: 'Toulouse',
        away_team: 'Lyon',
    }),
]);
const EXPECTED_INGESTED_MATCH_ID = '53_20252026_4830746';
const EXPECTED_REMAINING_MATCH_IDS = Object.freeze(
    EXPECTED_SEEDED_MATCHES.filter(match => match.match_id !== EXPECTED_INGESTED_MATCH_ID).map(match => match.match_id)
);

function normalizeText(value) {
    return String(value || '').trim();
}

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
    return Number.parseInt(normalized, 10);
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
        return {
            value: nextArg,
            consumedNext: true,
        };
    }

    return {
        value: true,
        consumedNext: false,
    };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        leagueId: null,
        season: null,
        date: null,
        expectedSeededCount: null,
        expectedExistingRawCount: null,
        expectedMissingRawCount: null,
        seededMatchesJson: null,
        rawCoverageJson: null,
        allowNetwork: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
        allowTraining: null,
        allowPrediction: null,
        networkAuthorization: null,
        livePreviewAuthorization: null,
        commit: false,
        execute: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        'league-id': 'leagueId',
        league_id: 'leagueId',
        season: 'season',
        date: 'date',
        'expected-seeded-count': 'expectedSeededCount',
        expected_seeded_count: 'expectedSeededCount',
        'expected-existing-raw-count': 'expectedExistingRawCount',
        expected_existing_raw_count: 'expectedExistingRawCount',
        'expected-missing-raw-count': 'expectedMissingRawCount',
        expected_missing_raw_count: 'expectedMissingRawCount',
        'seeded-matches-json': 'seededMatchesJson',
        seeded_matches_json: 'seededMatchesJson',
        'raw-coverage-json': 'rawCoverageJson',
        raw_coverage_json: 'rawCoverageJson',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'live-preview-authorization': 'livePreviewAuthorization',
        live_preview_authorization: 'livePreviewAuthorization',
        commit: 'commit',
        execute: 'execute',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowNetwork',
        'allowDbWrite',
        'allowRawMatchDataWrite',
        'allowMatchesWrite',
        'allowTraining',
        'allowPrediction',
        'networkAuthorization',
        'livePreviewAuthorization',
        'commit',
        'execute',
        'help',
    ]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }

        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) {
            index += 1;
        }

        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }

        if (booleanKeys.has(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function pushRequiredFalseError(errors, value, flagName) {
    if (value === false) {
        return;
    }
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.17L2`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function normalizePlanningInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        leagueId: normalizeText(input.leagueId),
        season: normalizeText(input.season),
        date: normalizeText(input.date),
        expectedSeededCount: parseInteger(input.expectedSeededCount, null),
        expectedExistingRawCount: parseInteger(input.expectedExistingRawCount, null),
        expectedMissingRawCount: parseInteger(input.expectedMissingRawCount, null),
        seededMatchesJson: input.seededMatchesJson,
        rawCoverageJson: input.rawCoverageJson,
        allowNetwork: normalizeBooleanFlag(input.allowNetwork, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, false),
        livePreviewAuthorization: normalizeBooleanFlag(input.livePreviewAuthorization, false),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePlanningInput(input = {}) {
    const value = normalizePlanningInput(input);
    const errors = [];

    if (value.unknown.length > 0) {
        errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    }
    if (!value.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (value.source !== EXPECTED_SCOPE.source) {
        errors.push('unsupported source: only fotmob is allowed');
    }
    if (!value.leagueId) {
        errors.push('missing league-id');
    } else if (value.leagueId !== EXPECTED_SCOPE.leagueId) {
        errors.push(`league-id must be ${EXPECTED_SCOPE.leagueId} in Phase 5.17L2`);
    }
    if (!value.season) {
        errors.push('missing season');
    } else if (value.season !== EXPECTED_SCOPE.season) {
        errors.push(`season must be ${EXPECTED_SCOPE.season} in Phase 5.17L2`);
    }
    if (!value.date) {
        errors.push('missing date');
    } else if (value.date !== EXPECTED_SCOPE.date) {
        errors.push(`date must be ${EXPECTED_SCOPE.date} in Phase 5.17L2`);
    }
    if (value.expectedSeededCount !== EXPECTED_SCOPE.expectedSeededCount) {
        errors.push(`expected-seeded-count must be ${EXPECTED_SCOPE.expectedSeededCount}`);
    }
    if (value.expectedExistingRawCount !== EXPECTED_SCOPE.expectedExistingRawCount) {
        errors.push(`expected-existing-raw-count must be ${EXPECTED_SCOPE.expectedExistingRawCount}`);
    }
    if (value.expectedMissingRawCount !== EXPECTED_SCOPE.expectedMissingRawCount) {
        errors.push(`expected-missing-raw-count must be ${EXPECTED_SCOPE.expectedMissingRawCount}`);
    }

    pushRequiredFalseError(errors, value.allowNetwork, 'allow-network');
    pushRequiredFalseError(errors, value.allowDbWrite, 'allow-db-write');
    pushRequiredFalseError(errors, value.allowRawMatchDataWrite, 'allow-raw-match-data-write');
    pushRequiredFalseError(errors, value.allowMatchesWrite, 'allow-matches-write');
    pushRequiredFalseError(errors, value.allowTraining, 'allow-training');
    pushRequiredFalseError(errors, value.allowPrediction, 'allow-prediction');

    if (value.networkAuthorization === true) {
        errors.push('network-authorization=yes is blocked in Phase 5.17L2');
    }
    if (value.livePreviewAuthorization === true) {
        errors.push('live-preview-authorization=yes is blocked in Phase 5.17L2');
    }
    if (value.commit === true) {
        errors.push('commit=yes is blocked in Phase 5.17L2');
    }
    if (value.execute === true) {
        errors.push('execute=yes is blocked in Phase 5.17L2');
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function parseJsonArrayInput(value, label) {
    if (Array.isArray(value)) {
        return value;
    }
    if (value === null || value === undefined || value === '') {
        return null;
    }
    try {
        const parsed = JSON.parse(String(value));
        if (!Array.isArray(parsed)) {
            throw new Error(`${label} must be a JSON array`);
        }
        return parsed;
    } catch (error) {
        if (error.message.includes('must be a JSON array')) {
            throw error;
        }
        throw new Error(`${label} must be valid JSON array input`);
    }
}

function normalizeCoverageRow(row = {}) {
    return {
        match_id: normalizeText(row.match_id),
        external_id: normalizeText(row.external_id),
        home_team: normalizeText(row.home_team),
        away_team: normalizeText(row.away_team),
        match_date: row.match_date ?? null,
        status: normalizeText(row.status) || null,
        raw_id: row.raw_id ?? null,
        data_version: normalizeText(row.data_version) || null,
        data_hash: normalizeText(row.data_hash) || null,
        collected_at: row.collected_at ?? null,
        raw_status: normalizeText(row.raw_status).toLowerCase() || null,
    };
}

function buildSeededMatchCoverage(seededMatchesInput = [], rawCoverageInput = []) {
    const seededMatches = parseJsonArrayInput(seededMatchesInput, 'seeded-matches-json');
    const rawCoverageRows = parseJsonArrayInput(rawCoverageInput, 'raw-coverage-json');
    if (!seededMatches) {
        throw new Error('seeded-matches-json is required for deterministic Phase 5.17L2 planning');
    }
    if (!rawCoverageRows) {
        throw new Error('raw-coverage-json is required for deterministic Phase 5.17L2 planning');
    }

    const rawCoverageByMatchId = new Map(
        rawCoverageRows.map(row => {
            const normalized = normalizeCoverageRow(row);
            return [normalized.match_id, normalized];
        })
    );

    return seededMatches
        .map(row => {
            const seeded = normalizeCoverageRow(row);
            const coverage = rawCoverageByMatchId.get(seeded.match_id) || {};
            const hasRaw = coverage.raw_status === 'has_raw' || coverage.raw_id !== null;
            return {
                match_id: seeded.match_id,
                external_id: seeded.external_id || coverage.external_id || null,
                home_team: seeded.home_team || coverage.home_team || null,
                away_team: seeded.away_team || coverage.away_team || null,
                match_date: seeded.match_date || coverage.match_date || null,
                status: seeded.status || coverage.status || null,
                raw_id: coverage.raw_id ?? null,
                data_version: coverage.data_version || null,
                data_hash: coverage.data_hash || null,
                collected_at: coverage.collected_at ?? null,
                raw_status: coverage.raw_status || (hasRaw ? 'has_raw' : 'missing_raw'),
            };
        })
        .sort((left, right) => left.match_id.localeCompare(right.match_id));
}

function buildRemainingTargets(seededMatchCoverage = []) {
    return seededMatchCoverage
        .filter(row => row.raw_status === 'missing_raw')
        .map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            home_team: row.home_team,
            away_team: row.away_team,
            route: EXPECTED_SCOPE.rawRoute,
            status: 'planned_missing_raw',
        }));
}

function buildAlreadyIngestedTargets(seededMatchCoverage = []) {
    return seededMatchCoverage
        .filter(row => row.raw_status === 'has_raw')
        .map(row => ({
            match_id: row.match_id,
            external_id: row.external_id,
            home_team: row.home_team,
            away_team: row.away_team,
            raw_status: 'has_raw',
        }));
}

function buildRecommendedAcquisitionStrategy(maxTargets = EXPECTED_SCOPE.expectedMissingRawCount) {
    return {
        mode: 'controlled_small_batch',
        max_targets: Number(maxTargets),
        route: EXPECTED_SCOPE.rawRoute,
        concurrency: 1,
        retry: 0,
        browser: false,
        proxy: false,
        full_body_save: false,
        full_body_print: false,
        raw_match_data_only: true,
        parser: false,
        features: false,
        training: false,
        prediction: false,
    };
}

function buildNextPhaseOptions() {
    return [
        {
            phase: 'Phase 5.18L2',
            name: 'remaining raw_match_data acquisition authorization',
            purpose: 'authorize the remaining 7 seeded matches for controlled raw acquisition',
        },
        {
            phase: 'Phase 5.19L2',
            name: 'remaining raw_match_data acquisition preflight',
            purpose: 'recapture exact payloads, compute hashes, and show would_insert/update/skip',
        },
        {
            phase: 'Phase 5.20L2',
            name: 'controlled remaining raw_match_data write',
            purpose: 'transactionally insert missing raw rows after final confirmation',
        },
    ];
}

function buildProtectedTablesPolicy() {
    return {
        matches: 'read_only',
        bookmaker_odds_history: 'unchanged',
        l3_features: 'unchanged',
        match_features_training: 'unchanged',
        predictions: 'unchanged',
    };
}

function buildInvalidPlan(input = {}, errors = [], controlledError = null) {
    const value = normalizePlanningInput(input);
    return {
        phase: PHASE,
        planning_only: true,
        ok: false,
        source: value.source || null,
        league_id: value.leagueId || null,
        season: value.season || null,
        date: value.date || null,
        raw_first_parse_later: true,
        parser_deferred_until_training_design: true,
        remaining_targets: [],
        already_ingested_targets: [],
        recommended_acquisition_strategy: buildRecommendedAcquisitionStrategy(0),
        next_phase_options: buildNextPhaseOptions(),
        protected_tables_policy: buildProtectedTablesPolicy(),
        db_write_allowed_this_phase: false,
        raw_match_data_write_allowed_this_phase: false,
        network_allowed_this_phase: false,
        would_write_db: false,
        would_write_raw_match_data: false,
        would_train: false,
        would_predict: false,
        errors,
        controlled_error:
            controlledError || `INVALID_REMAINING_RAW_MATCH_DATA_ACQUISITION_PLAN_INPUT:${errors.join('; ')}`,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildExpectedMatchMap() {
    return new Map(EXPECTED_SEEDED_MATCHES.map(match => [match.match_id, match]));
}

function validateSeededMatchCoverage(coverage = [], input = {}) {
    const value = normalizePlanningInput(input);
    const errors = [];
    const expectedMatches = buildExpectedMatchMap();
    const actualMatchIds = coverage.map(row => row.match_id);
    const actualMatchIdSet = new Set(actualMatchIds);
    const expectedMatchIds = EXPECTED_SEEDED_MATCHES.map(match => match.match_id);

    if (coverage.length !== value.expectedSeededCount) {
        errors.push(`seeded match coverage expected ${value.expectedSeededCount} rows, got ${coverage.length}`);
    }

    for (const expectedId of expectedMatchIds) {
        if (!actualMatchIdSet.has(expectedId)) {
            errors.push(`missing expected seeded match ${expectedId}`);
        }
    }
    for (const actualId of actualMatchIdSet) {
        if (!expectedMatches.has(actualId)) {
            errors.push(`unexpected seeded match ${actualId}`);
        }
    }

    for (const row of coverage) {
        const expected = expectedMatches.get(row.match_id);
        if (!expected) {
            continue;
        }
        if (row.external_id !== expected.external_id) {
            errors.push(
                `seeded coverage external_id mismatch for ${row.match_id}: expected ${expected.external_id}, got ${row.external_id}`
            );
        }
        if (row.home_team !== expected.home_team) {
            errors.push(
                `seeded coverage home_team mismatch for ${row.match_id}: expected ${expected.home_team}, got ${row.home_team}`
            );
        }
        if (row.away_team !== expected.away_team) {
            errors.push(
                `seeded coverage away_team mismatch for ${row.match_id}: expected ${expected.away_team}, got ${row.away_team}`
            );
        }
        if (!['has_raw', 'missing_raw'].includes(row.raw_status)) {
            errors.push(`raw_status for ${row.match_id} must be has_raw or missing_raw`);
        }
    }

    const alreadyIngestedMatchIds = coverage
        .filter(row => row.raw_status === 'has_raw')
        .map(row => row.match_id)
        .sort();
    const remainingMatchIds = coverage
        .filter(row => row.raw_status === 'missing_raw')
        .map(row => row.match_id)
        .sort();

    if (alreadyIngestedMatchIds.length !== value.expectedExistingRawCount) {
        errors.push(
            `existing raw_match_data count expected ${value.expectedExistingRawCount}, got ${alreadyIngestedMatchIds.length}`
        );
    }
    if (remainingMatchIds.length !== value.expectedMissingRawCount) {
        errors.push(
            `missing raw_match_data count expected ${value.expectedMissingRawCount}, got ${remainingMatchIds.length}`
        );
    }
    if (alreadyIngestedMatchIds.length !== 1 || alreadyIngestedMatchIds[0] !== EXPECTED_INGESTED_MATCH_ID) {
        errors.push(
            `already ingested target must be exactly ${EXPECTED_INGESTED_MATCH_ID}, got ${alreadyIngestedMatchIds.join(', ') || 'none'}`
        );
    }

    const expectedRemaining = [...EXPECTED_REMAINING_MATCH_IDS].sort();
    if (remainingMatchIds.join(',') !== expectedRemaining.join(',')) {
        errors.push(
            `remaining targets mismatch: expected ${expectedRemaining.join(', ')}, got ${remainingMatchIds.join(', ')}`
        );
    }

    return errors;
}

function buildRemainingRawMatchDataAcquisitionPlan(input = {}) {
    const validation = validatePlanningInput(input);
    if (!validation.ok) {
        return buildInvalidPlan(input, validation.errors);
    }

    try {
        const coverage = buildSeededMatchCoverage(validation.value.seededMatchesJson, validation.value.rawCoverageJson);
        const coverageErrors = validateSeededMatchCoverage(coverage, validation.value);
        if (coverageErrors.length > 0) {
            return buildInvalidPlan(
                validation.value,
                coverageErrors,
                `COVERAGE_VALIDATION_FAILED:${coverageErrors.join('; ')}`
            );
        }

        const remainingTargets = buildRemainingTargets(coverage);
        const alreadyIngestedTargets = buildAlreadyIngestedTargets(coverage);

        return {
            phase: PHASE,
            planning_only: true,
            ok: true,
            source: EXPECTED_SCOPE.source,
            league_id: EXPECTED_SCOPE.leagueId,
            season: EXPECTED_SCOPE.season,
            date: EXPECTED_SCOPE.date,
            seeded_match_count: coverage.length,
            existing_raw_match_data_count: alreadyIngestedTargets.length,
            missing_raw_match_data_count: remainingTargets.length,
            raw_first_parse_later: true,
            parser_deferred_until_training_design: true,
            remaining_targets: remainingTargets,
            already_ingested_targets: alreadyIngestedTargets,
            recommended_acquisition_strategy: buildRecommendedAcquisitionStrategy(remainingTargets.length),
            next_phase_options: buildNextPhaseOptions(),
            protected_tables_policy: buildProtectedTablesPolicy(),
            db_write_allowed_this_phase: false,
            raw_match_data_write_allowed_this_phase: false,
            network_allowed_this_phase: false,
            would_write_db: false,
            would_write_raw_match_data: false,
            would_train: false,
            would_predict: false,
            next_required_phase: NEXT_REQUIRED_PHASE,
        };
    } catch (error) {
        return buildInvalidPlan(
            validation.value,
            [String(error.message || error)],
            `COVERAGE_INPUT_REQUIRED:${String(error.message || error)}`
        );
    }
}

function usage() {
    return [
        'Usage:',
        "  node scripts/ops/l2_remaining_raw_match_data_acquisition_plan.js --source=fotmob --league-id=53 --season=2025/2026 --date=2026-05-10 --expected-seeded-count=8 --expected-existing-raw-count=1 --expected-missing-raw-count=7 --allow-network=no --allow-db-write=no --allow-raw-match-data-write=no --allow-matches-write=no --allow-training=no --allow-prediction=no --seeded-matches-json='[...]' --raw-coverage-json='[...]'",
        '',
        'Safety:',
        '  Phase 5.17L2 is planning-only: no external FotMob access, no live preview, no DB write, no raw_match_data write, no parser/features, no training/prediction.',
        '  This script expects explicit coverage JSON for deterministic planning and fails closed when coverage input is missing.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), streams = {}) {
    const stdout = streams.stdout || (text => process.stdout.write(text));
    const args = parseArgs(argv);

    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const plan = buildRemainingRawMatchDataAcquisitionPlan(args);
    stdout(`${JSON.stringify(plan, null, 2)}\n`);
    return plan.ok ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            console.error(
                JSON.stringify(
                    buildInvalidPlan(
                        {},
                        [String(error.message || error)],
                        `UNHANDLED_PHASE5_17L2_ERROR:${error.message}`
                    ),
                    null,
                    2
                )
            );
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validatePlanningInput,
    buildSeededMatchCoverage,
    buildRemainingTargets,
    buildAlreadyIngestedTargets,
    buildRecommendedAcquisitionStrategy,
    buildNextPhaseOptions,
    buildProtectedTablesPolicy,
    buildRemainingRawMatchDataAcquisitionPlan,
    runCli,
};
