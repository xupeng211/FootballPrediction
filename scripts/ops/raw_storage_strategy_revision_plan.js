#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2C_RAW_STORAGE_STRATEGY_REVISION_PLANNING';
const EXPECTED = Object.freeze({
    source: 'fotmob',
    currentVersion: 'fotmob_html_hyd_v1',
    recommendedVersion: 'fotmob_pageprops_v2',
    recommendedHashStrategy: 'stable_pageprops_payload_v1',
});
const REQUIRED_NO_FLAGS = Object.freeze([
    'allow-network',
    'allow-db-write',
    'allow-migration',
    'allow-parser-features',
    'allow-training',
    'allow-prediction',
]);
const BLOCKED_YES_FLAGS = Object.freeze(['execute', 'commit', 'rewrite-existing', 'drop-v1']);
const PROFILE_MODULES = Object.freeze([
    'content.lineup',
    'content.playerStats',
    'content.shotmap',
    'content.stats',
    'content.liveticker',
    'content.matchFacts',
    'content.momentum',
    'content.h2h',
    'content.table',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function toKebabKey(key) {
    return normalizeText(key)
        .replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        .replace(/^--+/, '');
}

function parseArgs(argv = []) {
    const args = {};
    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (!token.startsWith('--')) continue;
        const raw = token.slice(2);
        const eqIndex = raw.indexOf('=');
        if (eqIndex >= 0) {
            args[toKebabKey(raw.slice(0, eqIndex))] = raw.slice(eqIndex + 1);
            continue;
        }
        const next = argv[index + 1];
        if (next && !next.startsWith('--')) {
            args[toKebabKey(raw)] = next;
            index += 1;
        } else {
            args[toKebabKey(raw)] = 'yes';
        }
    }
    return args;
}

function normalizeBooleanFlag(value) {
    const normalized = normalizeText(value).toLowerCase();
    if (['yes', 'true', '1', 'y'].includes(normalized)) return true;
    if (['no', 'false', '0', 'n'].includes(normalized)) return false;
    return null;
}

function requireExact(input, key, expected, errors) {
    const actual = normalizeText(input[key]);
    if (!actual) {
        errors.push(`${key}=${expected} is required`);
    } else if (actual !== expected) {
        errors.push(`${key} must be ${expected}`);
    }
    return actual;
}

function requireNo(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value !== false) {
        errors.push(`${key}=no is required`);
    }
    return value;
}

function blockYes(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value === true) {
        errors.push(`${key}=yes is blocked in Phase 5.21L2C`);
    }
    return value;
}

function validatePlanInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    if (!source) {
        errors.push('source=fotmob is required');
    } else if (source !== EXPECTED.source) {
        errors.push('source must be fotmob');
    }

    const currentVersion = requireExact(input, 'current-version', EXPECTED.currentVersion, errors);
    const recommendedVersion = requireExact(input, 'recommended-version', EXPECTED.recommendedVersion, errors);
    const recommendedHashStrategy = requireExact(
        input,
        'recommended-hash-strategy',
        EXPECTED.recommendedHashStrategy,
        errors
    );

    const noFlags = {};
    for (const flag of REQUIRED_NO_FLAGS) {
        noFlags[flag] = requireNo(input, flag, errors);
    }
    for (const flag of BLOCKED_YES_FLAGS) {
        blockYes(input, flag, errors);
    }

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source: EXPECTED.source,
            currentVersion,
            recommendedVersion,
            recommendedHashStrategy,
            allowNetwork: noFlags['allow-network'],
            allowDbWrite: noFlags['allow-db-write'],
            allowMigration: noFlags['allow-migration'],
            allowParserFeatures: noFlags['allow-parser-features'],
            allowTraining: noFlags['allow-training'],
            allowPrediction: noFlags['allow-prediction'],
        },
    };
}

function buildRawV2ShapePolicy() {
    return {
        raw_data: 'pageProps',
        meta: '_meta',
        data_hash_basis: 'canonical_json(pageProps_without_volatile_meta)',
        not_stored: ['full HTML body'],
        not_default: ['full __NEXT_DATA__'],
        rationale: [
            'preserves match content and pageProps siblings',
            'keeps source payload cleaner than the full Next.js wrapper',
            'retains future unknown factors before parser design',
        ],
    };
}

function buildDerivedPayloadPolicy() {
    return {
        transformed_payload: 'derived/helper',
        not_canonical_raw: true,
        can_be_recomputed_from_pageprops_v2: true,
        intended_use:
            'normalization convenience, compatibility helpers, and parser scaffolding after raw policy is settled',
    };
}

function buildExistingV1Policy() {
    return {
        keep_existing_rows: true,
        do_not_rewrite_now: true,
        current_version_shape: 'transformed_hydration_payload',
        parser_must_branch_by_data_version: true,
        migration_requires_separate_authorization: true,
    };
}

function buildMixedProvenancePolicy() {
    return {
        synthetic_and_unknown_excluded_from_fotmob_parser_training: true,
        requires_data_version_filtering: true,
        requires_source_provenance_filtering: true,
        no_one_bucket_training_dataset: true,
    };
}

function buildLeagueExpansionCompletenessPolicy() {
    return {
        requires_completeness_profile_before_parser_training: true,
        profile_dimensions: ['league', 'season', 'match_status', 'data_version', 'source'],
        profile_modules: [...PROFILE_MODULES],
        coverage_tiers_required: true,
        do_not_assume_low_tier_module_coverage: true,
    };
}

function buildRawStorageStrategyRevisionPlan(input = {}) {
    const source = input.source || EXPECTED.source;
    const currentVersion = input.currentVersion || EXPECTED.currentVersion;
    const recommendedVersion = input.recommendedVersion || EXPECTED.recommendedVersion;
    const recommendedHashStrategy = input.recommendedHashStrategy || EXPECTED.recommendedHashStrategy;

    return {
        phase: PHASE,
        planning_only: true,
        source,
        current_canonical_raw_version: currentVersion,
        recommended_canonical_raw_version: recommendedVersion,
        recommended_hash_strategy: recommendedHashStrategy,
        raw_v2_shape: buildRawV2ShapePolicy(),
        derived_payload_policy: buildDerivedPayloadPolicy(),
        existing_v1_policy: buildExistingV1Policy(),
        mixed_provenance_policy: buildMixedProvenancePolicy(),
        league_expansion_policy: buildLeagueExpansionCompletenessPolicy(),
        next_phases: [
            'Phase 5.21L2D: single-target pageProps v2 no-write preview',
            'Phase 5.21L2E: pageProps v2 write planning',
            'Phase 5.21L2F: controlled pageProps v2 write for small sample',
        ],
        db_write_executed: false,
        raw_match_data_write_executed: false,
        migration_executed: false,
        network_access_executed: false,
        parser_features_executed: false,
        training_executed: false,
        prediction_executed: false,
    };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsedArgs = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validatePlanInput(parsedArgs);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));

    if (!validation.ok) {
        const payload = {
            phase: PHASE,
            planning_only: true,
            ok: false,
            blocked: true,
            errors: validation.errors,
            db_write_executed: false,
            raw_match_data_write_executed: false,
            migration_executed: false,
            network_access_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
        };
        output(payload);
        return { status: 1, payload };
    }

    const payload = {
        ok: true,
        ...buildRawStorageStrategyRevisionPlan(validation.value),
    };
    output(payload);
    return { status: 0, payload };
}

module.exports = {
    PHASE,
    EXPECTED,
    PROFILE_MODULES,
    parseArgs,
    normalizeBooleanFlag,
    validatePlanInput,
    buildRawV2ShapePolicy,
    buildDerivedPayloadPolicy,
    buildExistingV1Policy,
    buildMixedProvenancePolicy,
    buildLeagueExpansionCompletenessPolicy,
    buildRawStorageStrategyRevisionPlan,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
