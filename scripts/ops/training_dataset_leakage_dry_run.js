#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only training dataset construction & feature leakage policy dry-run

const PHASE = 'TRAINING_DATASET_LEAKAGE_DRY_RUN';
const TARGET_LEAGUE = 'Ligue 1';
const TARGET_SEASON = '2025/2026';
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const VALID_LABELS = new Set(['home_win', 'draw', 'away_win']);

// Feature classification taxonomy
// label — prediction target
// safe_pre_match — known before kickoff, safe for training
// leakage_post_match — only known after the match, must NOT be used as feature
// administrative — metadata / governance, not a feature
// uncertain — needs human review before classification

const FIELD_CLASSIFICATION = Object.freeze({
    // === Label ===
    actual_result: {
        category: 'label',
        reason: 'Prediction target. Encoded as home_win / draw / away_win.',
        usable_as_feature: false,
    },

    // === Safe pre-match features ===
    league_name: {
        category: 'safe_pre_match',
        reason: 'League identifier. Known before season starts.',
        usable_as_feature: true,
        encoding_note: 'One-hot or label encode',
    },
    season: {
        category: 'safe_pre_match',
        reason: 'Season identifier. Known before any match.',
        usable_as_feature: true,
        encoding_note: 'Can derive season phase / round number',
    },
    home_team: {
        category: 'safe_pre_match',
        reason: 'Home team identity. Known when fixture is published.',
        usable_as_feature: true,
        encoding_note: 'Team strength features (historical form, ELO, etc.) must be time-gated',
    },
    away_team: {
        category: 'safe_pre_match',
        reason: 'Away team identity. Known when fixture is published.',
        usable_as_feature: true,
        encoding_note: 'Same time-gating requirement as home_team',
    },
    match_date: {
        category: 'safe_pre_match',
        reason: 'Scheduled match datetime. Known before kickoff.',
        usable_as_feature: true,
        encoding_note: 'Can derive: day of week, month, time of day, days since season start',
    },
    venue: {
        category: 'safe_pre_match',
        reason: 'Match venue. Known when fixture is published.',
        usable_as_feature: true,
        encoding_note: 'Home/away/neutral indicator. Home advantage feature.',
    },
    referee: {
        category: 'safe_pre_match',
        reason: 'Match referee appointment. Typically published days before match.',
        usable_as_feature: true,
        encoding_note: 'Referee strictness metrics must be time-gated. Marginal feature.',
    },
    external_id: {
        category: 'administrative',
        reason: 'FotMob match identifier. Not a feature.',
        usable_as_feature: false,
    },

    // === Leakage (post-match — MUST NOT be features) ===
    home_score: {
        category: 'leakage_post_match',
        reason: 'Final home score. Known only after match ends. DIRECT LEAKAGE of label.',
        usable_as_feature: false,
    },
    away_score: {
        category: 'leakage_post_match',
        reason: 'Final away score. Known only after match ends. DIRECT LEAKAGE of label.',
        usable_as_feature: false,
    },
    home_corners: {
        category: 'leakage_post_match',
        reason: 'Home corner count. Match statistic known only after match.',
        usable_as_feature: false,
    },
    away_corners: {
        category: 'leakage_post_match',
        reason: 'Away corner count. Match statistic known only after match.',
        usable_as_feature: false,
    },
    home_yellow_cards: {
        category: 'leakage_post_match',
        reason: 'Home yellow cards. Match discipline record known only after match.',
        usable_as_feature: false,
    },
    away_yellow_cards: {
        category: 'leakage_post_match',
        reason: 'Away yellow cards. Match discipline record known only after match.',
        usable_as_feature: false,
    },
    home_red_cards: {
        category: 'leakage_post_match',
        reason: 'Home red cards. Match discipline record known only after match.',
        usable_as_feature: false,
    },
    away_red_cards: {
        category: 'leakage_post_match',
        reason: 'Away red cards. Match discipline record known only after match.',
        usable_as_feature: false,
    },
    status: {
        category: 'leakage_post_match',
        reason: 'Match status (finished). Knowing match is finished leaks that the game occurred.',
        usable_as_feature: false,
    },
    is_finished: {
        category: 'leakage_post_match',
        reason: 'Boolean match completion flag. Same as status.',
        usable_as_feature: false,
    },

    // === Administrative / governance (not features) ===
    match_id: {
        category: 'administrative',
        reason: 'Primary key. Not a feature.',
        usable_as_feature: false,
    },
    collection_date: {
        category: 'administrative',
        reason: 'Data collection timestamp. Indicates when raw data was fetched, not match time.',
        usable_as_feature: false,
        note: 'Could leak data pipeline timing if used naively',
    },
    created_at: {
        category: 'administrative',
        reason: 'Database record creation timestamp. Not a feature.',
        usable_as_feature: false,
    },
    updated_at: {
        category: 'administrative',
        reason: 'Database record update timestamp. Not a feature.',
        usable_as_feature: false,
    },
    data_version: {
        category: 'administrative',
        reason: 'Data version tag. Governance metadata.',
        usable_as_feature: false,
    },
    data_source: {
        category: 'administrative',
        reason: 'Data provenance tag. Governance metadata.',
        usable_as_feature: false,
    },
    pipeline_status: {
        category: 'administrative',
        reason: 'Pipeline processing state. Governance metadata.',
        usable_as_feature: false,
    },
    source_type: {
        category: 'administrative',
        reason: 'Provenance class. Governance metadata.',
        usable_as_feature: false,
    },
    evidence_level: {
        category: 'administrative',
        reason: 'Evidence strength. Governance metadata.',
        usable_as_feature: false,
    },
    is_production_scope: {
        category: 'administrative',
        reason: 'Production scope flag. Governance metadata.',
        usable_as_feature: false,
    },
    is_reconciliation_eligible: {
        category: 'administrative',
        reason: 'Reconciliation eligibility flag. Governance metadata.',
        usable_as_feature: false,
    },
    is_training_eligible: {
        category: 'administrative',
        reason: 'Training eligibility flag. Governance metadata.',
        usable_as_feature: false,
    },
    pipeline_status_reason: {
        category: 'administrative',
        reason: 'Pipeline status reason code. Governance metadata.',
        usable_as_feature: false,
    },
});

const SCAN_SQL = `
SELECT
    m.match_id, m.external_id, m.league_name, m.season,
    m.home_team, m.away_team,
    m.home_score, m.away_score, m.actual_result,
    m.match_date, m.venue, m.status, m.is_finished,
    m.home_corners, m.away_corners,
    m.home_yellow_cards, m.away_yellow_cards,
    m.home_red_cards, m.away_red_cards,
    m.referee,
    m.is_training_eligible,
    m.collection_date, m.created_at, m.updated_at
FROM matches m
WHERE m.is_training_eligible = true
  AND m.league_name = $1
  AND m.season = $2
ORDER BY m.match_id
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/training_dataset_leakage_dry_run.js [--json]',
        '',
        'Safety:',
        '  Dry-run only. No migration, no schema change, no DB write, no model training,',
        '  no live fetch, no raw payload output.',
    ].join('\n');
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { json: false, help: false };
    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (arg === '--json') { options.json = true; }
        else if (arg === '--help' || arg === '-h') { options.help = true; }
        else { throw new Error(`Unknown argument: ${arg}`); }
    }
    return options;
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    };
}

async function openReadOnlyClient(dependencies = {}) {
    if (dependencies.client) {
        return { client: dependencies.client, close: async () => {} };
    }
    const { Pool } = require('pg');
    const pool = new Pool(buildDbConfig());
    const client = await pool.connect();
    return {
        client,
        close: async () => {
            if (typeof client.release === 'function') { client.release(); }
            await pool.end();
        },
    };
}

function assertSelectOnlySql(sql) {
    const normalized = String(sql || '').replace(/\s+/g, ' ').trim().toUpperCase();
    const allowed =
        normalized === READ_ONLY_BEGIN_SQL ||
        normalized === READ_ONLY_ROLLBACK_SQL ||
        normalized.startsWith('SELECT ') ||
        normalized.startsWith('WITH ');
    if (!allowed) {
        throw new Error(`Unsafe SQL rejected by ${PHASE}: ${normalized.slice(0, 80)}`);
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

async function scanTrainingEligibleMatches(dependencies = {}) {
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;
    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);
        const result = await querySelectOnly(connection.client, SCAN_SQL, [TARGET_LEAGUE, TARGET_SEASON]);
        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;
        return result.rows || [];
    } finally {
        if (!rolledBack) {
            try { await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL); } catch { /* preserve */ }
        }
        await connection.close();
    }
}

function countDistribution(rows, keyFn) {
    const dist = {};
    for (const row of rows) {
        const key = keyFn(row);
        if (key === null || key === undefined || key === '') { continue; }
        dist[key] = (dist[key] || 0) + 1;
    }
    return dist;
}

function buildFieldSummary() {
    const byCategory = {
        label: [],
        safe_pre_match: [],
        leakage_post_match: [],
        administrative: [],
        uncertain: [],
    };

    for (const [fieldName, classification] of Object.entries(FIELD_CLASSIFICATION)) {
        byCategory[classification.category].push({
            field: fieldName,
            reason: classification.reason,
            usable_as_feature: classification.usable_as_feature,
            encoding_note: classification.encoding_note || null,
            note: classification.note || null,
        });
    }

    return byCategory;
}

function buildDryRunPayload(rows) {
    const labelDistribution = countDistribution(rows, r => r.actual_result);
    const labelValidCount = rows.filter(r => VALID_LABELS.has(r.actual_result || '')).length;
    const labelNonNullCount = rows.filter(r => r.actual_result !== null).length;

    const fieldSummary = buildFieldSummary();

    const safeFeatureCount = fieldSummary.safe_pre_match.length;
    const leakageFeatureCount = fieldSummary.leakage_post_match.length;
    const uncertainCount = fieldSummary.uncertain.length;

    const riskFlags = [
        'dry_run_only_no_model_training',
        'real_training_pipeline_requires_explicit_user_authorization',
        `sample_size=${rows.length}: suitable only for smoke/integration dataset, NOT for production model training`,
        'all_safe_pre_match_features_require_time_gating: team form/ELO/historical stats must use only data before match_date',
        'potential_raw_match_data_features_not_audited: xG, shots, possession, other FotMob stats are in raw_match_data.raw_data JSONB and are ALL post-match leakage',
        'collection_date IS post-creation timestamp — safe features like team form must be derived from historical matches with match_date < current match_date',
        'cross-league generalization not tested',
    ];

    const recommendations = [
        'This 58-sample dataset is a SMOKE / INTEGRATION dataset only.',
        'Do NOT train a production model on 58 samples.',
        'Safe features (7): league_name, season, home_team, away_team, match_date, venue, referee.',
        'ALL match statistics (corners, cards, scores) are post-match leakage — NEVER use as features.',
        'Team strength features (ELO, form, etc.) must be computed from historical data with strict time-gating: only use matches with match_date < current match_date.',
        'raw_match_data.raw_data contains FotMob JSONB with xG, shots, possession, etc. ALL of these are post-match leakage.',
        'For production: expand dataset to 500+ matches across multiple leagues and seasons.',
        'Define an explicit temporal cutoff: features at time T must only use data available before match_date[T].',
    ];

    // Sample rows for illustration (anonymized for safety)
    const sampleRows = rows.slice(0, 3).map(r => ({
        match_id: r.match_id,
        league_name: r.league_name,
        season: r.season,
        home_team: r.home_team,
        away_team: r.away_team,
        actual_result: r.actual_result,
        match_date: r.match_date,
        venue: r.venue,
    }));

    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: 'scripts/ops/training_dataset_leakage_dry_run.js',
        generated_at: new Date().toISOString(),
        target_scope: {
            league_name: TARGET_LEAGUE,
            season: TARGET_SEASON,
            description: 'Training dataset construction & feature leakage audit',
        },
        training_eligible_count: rows.length,
        label_distribution: labelDistribution,
        label_validation: {
            non_null_count: labelNonNullCount,
            valid_count: labelValidCount,
            total_count: rows.length,
            all_label_valid: labelValidCount === rows.length,
        },
        field_classification_summary: {
            total_fields_classified: Object.keys(FIELD_CLASSIFICATION).length,
            label_count: fieldSummary.label.length,
            safe_pre_match_count: safeFeatureCount,
            leakage_post_match_count: leakageFeatureCount,
            administrative_count: fieldSummary.administrative.length,
            uncertain_count: uncertainCount,
        },
        safe_feature_candidates: fieldSummary.safe_pre_match,
        leakage_feature_candidates: fieldSummary.leakage_post_match,
        uncertain_feature_candidates: fieldSummary.uncertain,
        label_field: fieldSummary.label,
        administrative_fields_summary: `${
            fieldSummary.administrative.length} fields: ${
            fieldSummary.administrative.map(f => f.field).join(', ')}`,
        sample_rows: sampleRows,
        sample_rows_count: rows.length,
        risk_flags: riskFlags,
        recommendations,
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            model_training_performed: false,
            model_output_generated: false,
            live_fetch_allowed: false,
            raw_payload_output_allowed: false,
            read_only_transaction_used: true,
        },
    };
}

async function runDryRun(options = {}, dependencies = {}) {
    const rows = await scanTrainingEligibleMatches(dependencies);
    return buildDryRunPayload(rows);
}

function payloadToText(payload) {
    const labelDist = Object.entries(payload.label_distribution || {})
        .map(([k, v]) => `  ${k}: ${v}`).join('\n') || '  none';
    const safeFeatures = payload.safe_feature_candidates
        .map(f => `  - ${f.field}: ${f.reason}`).join('\n') || '  - none';
    const leakageFeatures = payload.leakage_feature_candidates
        .map(f => `  - ${f.field}: ${f.reason}`).join('\n') || '  - none';
    const riskFlags = (payload.risk_flags || []).map(f => `  - ${f}`).join('\n') || '  - none';
    const recs = (payload.recommendations || []).map(r => `  - ${r}`).join('\n') || '  - none';

    return [
        '[DRY-RUN] Training dataset construction & feature leakage audit',
        `Phase: ${payload.phase}`,
        `Mode: ${payload.mode}`,
        `Training eligible count: ${payload.training_eligible_count}`,
        'Label distribution:',
        labelDist,
        `Label valid: ${payload.label_validation.all_label_valid} (${payload.label_validation.valid_count}/${payload.label_validation.total_count})`,
        '',
        `Safe pre-match features (${payload.field_classification_summary.safe_pre_match_count}):`,
        safeFeatures,
        '',
        `Leakage post-match fields (${payload.field_classification_summary.leakage_post_match_count}) — MUST NOT be features:`,
        leakageFeatures,
        '',
        `Uncertain fields (${payload.field_classification_summary.uncertain_count}):`,
        (payload.uncertain_feature_candidates || []).map(f => `  - ${f.field}: ${f.reason}`).join('\n') || '  - none',
        '',
        'Risk flags:',
        riskFlags,
        '',
        'Recommendations:',
        recs,
    ].join('\n');
}

function writePayload(payload, json, io) {
    const output = json
        ? `${JSON.stringify(payload, null, 2)}\n`
        : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function buildFailurePayload(error, options = {}) {
    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: 'scripts/ops/training_dataset_leakage_dry_run.js',
        target_scope: { league_name: TARGET_LEAGUE, season: TARGET_SEASON },
        errors: [error.message],
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            model_training_performed: false,
            model_output_generated: false,
            live_fetch_allowed: false,
            raw_payload_output_allowed: false,
            read_only_transaction_used: true,
        },
    };
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };
    let options = { json: false, help: false };
    try {
        options = parseArgs(argv);
        if (options.help) { output.stdout(`${usage()}\n`); return 0; }
        const payload = await runDryRun(options);
        writePayload(payload, options.json, output);
        return 0;
    } catch (error) {
        const payload = buildFailurePayload(error, options);
        writePayload(payload, options.json === true, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(status => { process.exitCode = status; });
}

module.exports = {
    PHASE,
    TARGET_LEAGUE,
    TARGET_SEASON,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    FIELD_CLASSIFICATION,
    SCAN_SQL,
    parseArgs,
    buildDbConfig,
    openReadOnlyClient,
    assertSelectOnlySql,
    querySelectOnly,
    scanTrainingEligibleMatches,
    countDistribution,
    buildFieldSummary,
    buildDryRunPayload,
    runDryRun,
    payloadToText,
    buildFailurePayload,
    main,
};
