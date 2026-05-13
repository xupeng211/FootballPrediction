#!/usr/bin/env node
/* eslint-disable complexity */
'use strict';

const PHASE = 'PHASE5_13L2_RAW_MATCH_DATA_INGEST_PLANNING';
const NEXT_REQUIRED_PHASE = 'Phase 5.14L2 raw_match_data ingest authorization';
const TARGET = Object.freeze({
    source: 'fotmob',
    route: 'html_hydration',
    matchId: '53_20252026_4830746',
    externalId: '4830746',
    homeTeam: 'Angers',
    awayTeam: 'Strasbourg',
});

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

function parsePositiveInteger(value, fallback = null) {
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
        route: null,
        matchId: null,
        externalId: null,
        homeTeam: null,
        awayTeam: null,
        previewBodySha256: null,
        previewBodyByteLength: null,
        hydrationParseOk: null,
        looksLikeValidMatchDetail: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
        allowTraining: null,
        allowPrediction: null,
        commit: false,
        execute: false,
        networkAuthorization: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        route: 'route',
        'match-id': 'matchId',
        match_id: 'matchId',
        'external-id': 'externalId',
        external_id: 'externalId',
        'home-team': 'homeTeam',
        home_team: 'homeTeam',
        'away-team': 'awayTeam',
        away_team: 'awayTeam',
        'preview-body-sha256': 'previewBodySha256',
        preview_body_sha256: 'previewBodySha256',
        'preview-body-byte-length': 'previewBodyByteLength',
        preview_body_byte_length: 'previewBodyByteLength',
        'hydration-parse-ok': 'hydrationParseOk',
        hydration_parse_ok: 'hydrationParseOk',
        'looks-like-valid-match-detail': 'looksLikeValidMatchDetail',
        looks_like_valid_match_detail: 'looksLikeValidMatchDetail',
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
        commit: 'commit',
        execute: 'execute',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'hydrationParseOk',
        'looksLikeValidMatchDetail',
        'allowDbWrite',
        'allowRawMatchDataWrite',
        'allowMatchesWrite',
        'allowTraining',
        'allowPrediction',
        'commit',
        'execute',
        'networkAuthorization',
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

function includesText(value, expected) {
    return normalizeText(value).toLowerCase().includes(normalizeText(expected).toLowerCase());
}

function pushRequiredFalseError(errors, value, flagName) {
    if (value === false) {
        return;
    }
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.13L2`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function normalizePlanningInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        route: normalizeText(input.route).toLowerCase(),
        matchId: normalizeText(input.matchId),
        externalId: normalizeText(input.externalId),
        homeTeam: normalizeText(input.homeTeam),
        awayTeam: normalizeText(input.awayTeam),
        previewBodySha256: normalizeText(input.previewBodySha256).toLowerCase(),
        previewBodyByteLength: parsePositiveInteger(input.previewBodyByteLength, null),
        hydrationParseOk: normalizeBooleanFlag(input.hydrationParseOk, undefined),
        looksLikeValidMatchDetail: normalizeBooleanFlag(input.looksLikeValidMatchDetail, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, false),
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
    } else if (value.source !== TARGET.source) {
        errors.push('unsupported source: only fotmob is allowed');
    }
    if (!value.route) {
        errors.push('missing route: provide --route=html_hydration');
    } else if (value.route !== TARGET.route) {
        errors.push('unsupported route: Phase 5.13L2 only plans html_hydration raw_data ingest');
    }
    if (!value.matchId) {
        errors.push('missing match-id');
    } else if (value.matchId !== TARGET.matchId) {
        errors.push(`match-id must be ${TARGET.matchId} in Phase 5.13L2`);
    }
    if (!value.externalId) {
        errors.push('missing external-id');
    } else if (value.externalId !== TARGET.externalId) {
        errors.push(`external-id must be ${TARGET.externalId} in Phase 5.13L2`);
    }
    if (!value.homeTeam) {
        errors.push('missing home-team');
    } else if (!includesText(value.homeTeam, TARGET.homeTeam)) {
        errors.push(`home-team must contain ${TARGET.homeTeam}`);
    }
    if (!value.awayTeam) {
        errors.push('missing away-team');
    } else if (!includesText(value.awayTeam, TARGET.awayTeam)) {
        errors.push(`away-team must contain ${TARGET.awayTeam}`);
    }
    if (!value.previewBodySha256) {
        errors.push('missing preview-body-sha256');
    } else if (!/^[a-f0-9]{64}$/.test(value.previewBodySha256)) {
        errors.push('preview-body-sha256 must be a 64-character SHA-256 hex digest');
    }
    if (!Number.isFinite(value.previewBodyByteLength) || value.previewBodyByteLength <= 0) {
        errors.push('preview-body-byte-length must be > 0');
    }
    if (value.hydrationParseOk !== true) {
        errors.push('hydration-parse-ok=yes is required');
    }
    if (value.looksLikeValidMatchDetail !== true) {
        errors.push('looks-like-valid-match-detail=yes is required');
    }

    pushRequiredFalseError(errors, value.allowDbWrite, 'allow-db-write');
    pushRequiredFalseError(errors, value.allowRawMatchDataWrite, 'allow-raw-match-data-write');
    pushRequiredFalseError(errors, value.allowMatchesWrite, 'allow-matches-write');
    pushRequiredFalseError(errors, value.allowTraining, 'allow-training');
    pushRequiredFalseError(errors, value.allowPrediction, 'allow-prediction');

    if (value.commit === true) {
        errors.push('commit=yes is blocked in Phase 5.13L2');
    }
    if (value.execute === true) {
        errors.push('execute=yes is blocked in Phase 5.13L2');
    }
    if (value.networkAuthorization === true) {
        errors.push('network-authorization=yes is blocked: this phase is planning-only and no-network');
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function buildRawDataPolicy(input = {}) {
    return {
        storage_shape: 'canonical_transformed_detail_payload',
        recommended_source: 'FotMobDetailRouteSelector html_hydration transformed_api_format object',
        required_top_level_keys: ['_meta', 'content', 'general', 'header', 'matchId'],
        include_meta: true,
        exclude_full_html_body: true,
        exclude_full_http_response_string: true,
        exclude_screenshot_or_file_path: true,
        raw_data_must_not_be_page_html: true,
        raw_data_meta_fields: {
            source: TARGET.source,
            route: TARGET.route,
            request_url: 'https://www.fotmob.com/match/4830746',
            final_url: 'https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och',
            fetch_body_sha256: input.previewBodySha256 || null,
            fetch_body_byte_length: input.previewBodyByteLength || null,
            hydration_parse_ok: true,
            parser: 'NextDataParser / FotMobDetailRouteSelector',
            collected_at: 'write_phase_utc_timestamp',
        },
        preserve_paths: [
            'content.matchFacts',
            'content.lineup',
            'content.liveticker.teams',
            'content.playerStats.*.shotmap',
            'content.playerStats.*.stats',
            'general',
            'header',
            'matchId',
        ],
    };
}

function buildHashPolicy() {
    return {
        data_hash_algorithm: 'sha256',
        data_hash_input: 'canonical_json(raw_data)',
        canonical_json_requires_stable_key_ordering: true,
        html_body_hash_is_data_hash: false,
        body_sha256_metadata_field: 'raw_data._meta.fetch_body_sha256',
        future_write_phase_must_recompute_hash_from_exact_raw_data: true,
    };
}

function buildDataVersionPolicy() {
    return {
        data_version: 'fotmob_html_hyd_v1',
        semantic_label: 'fotmob_html_hydration_v1',
        rationale: 'raw_data comes from FotMob page HTML hydration transformed into API-compatible payload shape',
        schema_column_limit_note:
            'raw_match_data.data_version is varchar(20), so the DB value uses the shortened fotmob_html_hyd_v1 form while preserving the full semantic label in planning metadata',
    };
}

function buildCollectedAtPolicy() {
    return {
        collected_at_source: 'write_phase_utc_timestamp',
        collected_at_generated_by: 'future controlled write script',
        timezone: 'UTC',
        preview_time_handling:
            'preview time may be recorded as raw_data._meta.preview_at, but DB collected_at must represent actual raw payload capture/write time',
    };
}

function buildUpsertPolicy() {
    return {
        conflict_key: 'match_id',
        unique_constraint: 'raw_match_data_match_id_key',
        foreign_key: 'match_id -> matches(match_id) ON DELETE CASCADE',
        no_existing_row: 'would_insert',
        existing_same_data_hash: 'would_skip',
        existing_different_data_hash: 'would_update_only_after_explicit_authorization',
        delete_allowed: false,
        truncate_allowed: false,
        overwrite_without_preflight_allowed: false,
        first_write_max_rows: 1,
        later_batch_max_rows: 8,
        transaction_required: true,
    };
}

function buildProtectedTablesPolicy() {
    return {
        future_write_allowed_table: 'raw_match_data',
        raw_match_data_write_allowed_this_phase: false,
        protected_tables: {
            matches: 'read_only',
            bookmaker_odds_history: 'unchanged',
            l3_features: 'unchanged',
            match_features_training: 'unchanged',
            predictions: 'unchanged',
        },
        parser_features_training_prediction_allowed_in_raw_ingest_phase: false,
    };
}

function buildPreflightRequirements() {
    return [
        'SELECT target match and verify FK row exists',
        'SELECT existing raw_match_data by match_id/external_id',
        'Build exact raw_data object from already authorized route selector result without full HTML body',
        'Compute SHA-256 over canonical JSON raw_data',
        'Compare computed hash with existing row if present',
        'Preview insert/skip/update decision with rows <= 1',
        'Confirm transaction plan touches only raw_match_data',
        'Confirm matches/features/training/predictions row counts remain unchanged',
    ];
}

function buildAuthorizationRequirements() {
    return [
        'Phase 5.14L2 user authorization for raw_match_data write only',
        'Target locked to 53_20252026_4830746 / external_id 4830746',
        'No matches write',
        'No bookmaker_odds_history write',
        'No l3_features write',
        'No match_features_training write',
        'No predictions write',
        'No parser/features/training/prediction execution',
        'No external FotMob request unless separately authorized in a future acquisition phase',
    ];
}

function buildRawMatchDataIngestPlan(input = {}) {
    const validation = validatePlanningInput(input);
    const normalized = validation.value;
    const base = {
        phase: PHASE,
        planning_only: true,
        ok: validation.ok,
        source: TARGET.source,
        route: TARGET.route,
        match_id: TARGET.matchId,
        external_id: TARGET.externalId,
        home_team: TARGET.homeTeam,
        away_team: TARGET.awayTeam,
        target_table: 'raw_match_data',
        raw_match_data_write_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_write_matches: false,
        would_train: false,
        would_predict: false,
        external_network_used: false,
        live_match_detail_request_used: false,
        browser_used: false,
        proxy_used: false,
        full_body_saved: false,
        full_body_printed: false,
        commit_requested: normalized.commit === true,
        execute_requested: normalized.execute === true,
        network_authorization_requested: normalized.networkAuthorization === true,
        preview_input: {
            preview_body_sha256: normalized.previewBodySha256 || null,
            preview_body_byte_length: normalized.previewBodyByteLength,
            hydration_parse_ok: normalized.hydrationParseOk === true,
            looks_like_valid_match_detail: normalized.looksLikeValidMatchDetail === true,
        },
        raw_data_policy: buildRawDataPolicy(normalized),
        hash_policy: buildHashPolicy(),
        data_version_policy: buildDataVersionPolicy(),
        collected_at_policy: buildCollectedAtPolicy(),
        upsert_policy: buildUpsertPolicy(),
        protected_tables_policy: buildProtectedTablesPolicy(),
        preflight_requirements: buildPreflightRequirements(),
        authorization_requirements: buildAuthorizationRequirements(),
        next_required_phase: NEXT_REQUIRED_PHASE,
    };

    if (!validation.ok) {
        return {
            ...base,
            controlled_error: `INVALID_INGEST_PLAN_INPUT:${validation.errors.join('; ')}`,
            errors: validation.errors,
        };
    }

    return {
        ...base,
        controlled_error: null,
        errors: [],
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_raw_match_data_ingest_plan.js --source=fotmob --route=html_hydration --match-id=53_20252026_4830746 --external-id=4830746 --home-team=Angers --away-team=Strasbourg --preview-body-sha256=<sha256> --preview-body-byte-length=<bytes> --hydration-parse-ok=yes --looks-like-valid-match-detail=yes --allow-db-write=no --allow-raw-match-data-write=no --allow-matches-write=no --allow-training=no --allow-prediction=no',
        '',
        'Safety:',
        '  Phase 5.13L2 is planning-only: no network, no DB write, no raw_match_data write.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const plan = buildRawMatchDataIngestPlan(args);
    stdout(`${JSON.stringify(plan, null, 2)}\n`);
    return plan.ok ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(
                `${JSON.stringify(
                    {
                        phase: PHASE,
                        planning_only: true,
                        ok: false,
                        controlled_error: String(error.message || error),
                        raw_match_data_write_allowed_this_phase: false,
                        db_write_allowed_this_phase: false,
                        would_write_raw_match_data: false,
                        would_write_db: false,
                    },
                    null,
                    2
                )}\n`
            );
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validatePlanningInput,
    buildRawDataPolicy,
    buildHashPolicy,
    buildDataVersionPolicy,
    buildCollectedAtPolicy,
    buildUpsertPolicy,
    buildProtectedTablesPolicy,
    buildPreflightRequirements,
    buildAuthorizationRequirements,
    buildRawMatchDataIngestPlan,
    runCli,
};
