#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2E_PAGEPROPS_V2_CONTROLLED_WRITE_PLANNING';
const EXPECTED = Object.freeze({
    source: 'fotmob',
    currentVersion: 'fotmob_html_hyd_v1',
    targetVersion: 'fotmob_pageprops_v2',
    hashStrategy: 'stable_pageprops_payload_v1',
    targetMatchId: '53_20252026_4830747',
    targetExternalId: '4830747',
});
const REQUIRED_NO_FLAGS = Object.freeze([
    'allow-network',
    'allow-db-write',
    'allow-migration',
    'allow-raw-match-data-write',
    'allow-parser-features',
    'allow-training',
    'allow-prediction',
]);
const BLOCKED_YES_FLAGS = Object.freeze(['execute', 'commit', 'rewrite-existing', 'drop-v1', 'alter-table']);

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
        errors.push(`${key}=yes is blocked in Phase 5.21L2E`);
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
    const targetVersion = requireExact(input, 'target-version', EXPECTED.targetVersion, errors);
    const hashStrategy = requireExact(input, 'hash-strategy', EXPECTED.hashStrategy, errors);
    const targetMatchId = requireExact(input, 'target-match-id', EXPECTED.targetMatchId, errors);
    const targetExternalId = requireExact(input, 'target-external-id', EXPECTED.targetExternalId, errors);

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
            targetVersion,
            hashStrategy,
            targetMatchId,
            targetExternalId,
            allowNetwork: noFlags['allow-network'],
            allowDbWrite: noFlags['allow-db-write'],
            allowMigration: noFlags['allow-migration'],
            allowRawMatchDataWrite: noFlags['allow-raw-match-data-write'],
            allowParserFeatures: noFlags['allow-parser-features'],
            allowTraining: noFlags['allow-training'],
            allowPrediction: noFlags['allow-prediction'],
        },
    };
}

function normalizeSchemaDefinitions(items = []) {
    if (!Array.isArray(items)) return [];
    return items
        .map(item => {
            if (typeof item === 'string') return item;
            return [item.conname, item.indexname, item.definition, item.indexdef].filter(Boolean).join(' ');
        })
        .map(value => normalizeText(value).replace(/\s+/g, ' ').toLowerCase())
        .filter(Boolean);
}

function hasUniqueMatchIdDefinition(definitions = []) {
    return definitions.some(definition => {
        const compact = definition.replace(/\s+/g, '');
        return (
            compact.includes('unique(match_id)') ||
            (compact.includes('uniqueindex') && compact.includes('btree(match_id)')) ||
            (compact.includes('uniqueconstraint') && compact.includes('btree(match_id)'))
        );
    });
}

function hasUniqueMatchIdDataVersionDefinition(definitions = []) {
    return definitions.some(definition => {
        const compact = definition.replace(/\s+/g, '');
        return (
            compact.includes('unique(match_id,data_version)') ||
            compact.includes('unique(data_version,match_id)') ||
            (compact.includes('uniqueindex') &&
                (compact.includes('btree(match_id,data_version)') || compact.includes('btree(data_version,match_id)')))
        );
    });
}

function detectConflictPolicy(policies = []) {
    const normalized = Array.isArray(policies)
        ? policies.map(policy => normalizeText(policy).replace(/\s+/g, ' ').toLowerCase())
        : [];
    if (normalized.some(policy => policy.includes('on conflict (match_id, data_version)'))) {
        return 'ON CONFLICT (match_id, data_version)';
    }
    if (normalized.some(policy => policy.includes('on conflict (match_id)'))) {
        return 'ON CONFLICT (match_id)';
    }
    return normalized.length > 0 ? 'other' : 'unknown';
}

function boolToFinding(value) {
    return value === undefined ? 'unknown' : String(Boolean(value));
}

function buildSchemaFindings(schema = {}) {
    const definitions = normalizeSchemaDefinitions([...(schema.constraints || []), ...(schema.indexes || [])]);
    const hasDefinitions = definitions.length > 0;
    const hasUniqueMatchId = hasDefinitions ? hasUniqueMatchIdDefinition(definitions) : undefined;
    const hasVersionedUnique = hasDefinitions ? hasUniqueMatchIdDataVersionDefinition(definitions) : undefined;
    const allowsMultiVersion =
        hasVersionedUnique === true ? true : hasUniqueMatchId === true ? false : hasDefinitions ? undefined : undefined;

    return {
        raw_match_data_has_unique_match_id: boolToFinding(hasUniqueMatchId),
        raw_match_data_has_unique_match_id_data_version: boolToFinding(hasVersionedUnique),
        raw_match_data_allows_multi_version_per_match: boolToFinding(allowsMultiVersion),
        current_on_conflict_policy: detectConflictPolicy(schema.onConflictPolicies || []),
        duplicate_match_id_count:
            Number.isInteger(schema.duplicateMatchIdCount) && schema.duplicateMatchIdCount >= 0
                ? schema.duplicateMatchIdCount
                : null,
    };
}

function compareSchemaStrategies() {
    return [
        {
            strategy: 'unique_match_id_data_version',
            rank: 1,
            summary: 'change raw_match_data uniqueness to the versioned identity',
            pros: [
                'minimal table surface change',
                'keeps raw_match_data as the raw warehouse',
                'allows v1 and v2 rows to coexist',
            ],
            cons: ['requires schema migration', 'writers/readers using match_id identity need compatibility review'],
        },
        {
            strategy: 'new_versions_table',
            rank: 2,
            summary: 'add a dedicated raw_match_data_versions table',
            pros: ['clear version history', 'does not change current raw_match_data uniqueness immediately'],
            cons: ['more tables and query routing', 'future parser/readers must know which table to use'],
        },
        {
            strategy: 'raw_match_data_v2_table',
            rank: 3,
            summary: 'add a v2-only sibling table',
            pros: ['isolates v2 writes', 'keeps v1 rows untouched'],
            cons: ['duplicates raw table semantics', 'increases long-term reader complexity'],
        },
        {
            strategy: 'overwrite_v1',
            rank: 4,
            summary: 'overwrite current fotmob_html_hyd_v1 rows',
            pros: ['smallest immediate schema change'],
            cons: ['destroys v1 provenance', 'not reversible without backups', 'not recommended'],
            recommended: false,
        },
    ];
}

function buildRecommendedSchemaStrategy(schemaFindings = buildSchemaFindings()) {
    const hasVersionedUnique = schemaFindings.raw_match_data_has_unique_match_id_data_version === 'true';
    const hasUniqueMatchId = schemaFindings.raw_match_data_has_unique_match_id === 'true';
    return {
        strategy: 'unique_match_id_data_version',
        reason: hasVersionedUnique
            ? 'raw_match_data already appears to support versioned uniqueness; keep v1/v2 coexistence on the main raw table'
            : hasUniqueMatchId
              ? 'current unique(match_id) blocks v1/v2 coexistence, and changing identity to (match_id, data_version) is the smallest coherent schema evolution'
              : 'versioned uniqueness keeps raw_match_data as the canonical raw table while preserving existing v1 rows',
        migration_required: !hasVersionedUnique,
        migration_execute_this_phase: false,
        overwrite_v1_recommended: false,
    };
}

function buildVersionedWritePolicy() {
    return {
        write_v2_as_new_version: true,
        do_not_rewrite_v1: true,
        do_not_overwrite_existing: true,
        upsert_conflict_target: ['match_id', 'data_version'],
        expected_rows_for_initial_sample: 1,
        first_target: {
            match_id: EXPECTED.targetMatchId,
            external_id: EXPECTED.targetExternalId,
        },
    };
}

function buildCompatibilityPolicy() {
    return {
        readers_must_filter_data_version: true,
        parser_must_branch_by_data_version: true,
        synthetic_unknown_excluded_by_default: true,
        canonical_selector_recommended: true,
        recommended_canonical_selector_order: ['fotmob_pageprops_v2', 'fotmob_html_hyd_v1'],
    };
}

function buildRollbackPolicy() {
    return {
        pre_migration_backup_required: true,
        rollback_plan_required: true,
        no_execution_this_phase: true,
        verify_existing_row_counts_before_and_after: true,
    };
}

function buildPagePropsV2ControlledWritePlan(input = {}, schema = {}) {
    const source = input.source || EXPECTED.source;
    const currentVersion = input.currentVersion || EXPECTED.currentVersion;
    const targetVersion = input.targetVersion || EXPECTED.targetVersion;
    const hashStrategy = input.hashStrategy || EXPECTED.hashStrategy;
    const targetMatchId = input.targetMatchId || EXPECTED.targetMatchId;
    const targetExternalId = input.targetExternalId || EXPECTED.targetExternalId;
    const schemaFindings = buildSchemaFindings(schema);

    return {
        phase: PHASE,
        planning_only: true,
        source,
        current_version: currentVersion,
        target_version: targetVersion,
        hash_strategy: hashStrategy,
        target: {
            match_id: targetMatchId,
            external_id: targetExternalId,
        },
        schema_findings: schemaFindings,
        strategy_comparison: compareSchemaStrategies(),
        recommended_schema_strategy: buildRecommendedSchemaStrategy(schemaFindings),
        write_policy: buildVersionedWritePolicy(),
        compatibility_policy: buildCompatibilityPolicy(),
        rollback_policy: buildRollbackPolicy(),
        next_phases: [
            'Phase 5.21L2F: raw_match_data versioned schema migration planning/preflight',
            'Phase 5.21L2G: controlled schema migration execution',
            'Phase 5.21L2H: pageProps v2 single-target write preflight',
            'Phase 5.21L2I: pageProps v2 single-target controlled write',
        ],
        network_access_executed: false,
        db_write_executed: false,
        migration_executed: false,
        raw_match_data_write_executed: false,
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
            network_access_executed: false,
            db_write_executed: false,
            migration_executed: false,
            raw_match_data_write_executed: false,
            parser_features_executed: false,
            training_executed: false,
            prediction_executed: false,
        };
        output(payload);
        return { status: 1, payload };
    }

    const payload = {
        ok: true,
        ...buildPagePropsV2ControlledWritePlan(validation.value, dependencies.schema || {}),
    };
    output(payload);
    return { status: 0, payload };
}

module.exports = {
    PHASE,
    EXPECTED,
    parseArgs,
    normalizeBooleanFlag,
    validatePlanInput,
    buildSchemaFindings,
    compareSchemaStrategies,
    buildRecommendedSchemaStrategy,
    buildVersionedWritePolicy,
    buildCompatibilityPolicy,
    buildRollbackPolicy,
    buildPagePropsV2ControlledWritePlan,
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
