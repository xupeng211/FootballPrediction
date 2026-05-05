#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const REGISTRY_PATH = path.resolve(__dirname, '../../config/acquisition_engines.phase454.json');
const REQUIRED_ENGINE_FIELDS = [
    'id',
    'category',
    'entrypoint',
    'commands',
    'accesses_network',
    'writes_db',
    'writes_files',
    'supports_dry_run',
    'dry_run_trust_level',
    'supports_commit',
    'bulk_risk',
    'tos_license_risk',
    'provenance_required',
    'safe_for_ai_default',
    'requires_user_authorization',
    'phase454_policy',
    'notes',
];
const REQUIRED_GOVERNANCE_FIELDS = [
    'owner',
    'status',
    'intended_layer',
    'replacement_plan',
    'deprecation_status',
    'canonical_entrypoint',
    'allowed_next_phase',
    'test_coverage',
];
const ALLOWED_STATUS_VALUES = new Set([
    'canonical',
    'gate_only',
    'quarantine',
    'deprecation_candidate',
    'adapter_candidate',
    'legacy_blocked',
]);
const ALLOWED_INTENDED_LAYER_VALUES = new Set([
    'layer_0_registry_policy',
    'layer_1_source_manifest',
    'layer_2_discovery',
    'layer_3_single_target_acquisition',
    'layer_4_local_staging_normalization',
    'layer_5_local_staging_dry_run',
    'layer_6_small_db_write',
    'layer_7_feature_dry_run',
    'layer_8_training_prediction',
    'legacy_bulk_pipeline',
    'legacy_production_path',
    'unknown',
]);
const ALLOWED_DEPRECATION_STATUS_VALUES = new Set([
    'not_deprecated',
    'watch',
    'quarantine',
    'deprecation_candidate',
    'deprecated_do_not_use',
]);
const ALLOWED_NEXT_PHASE_VALUES = new Set([
    'allowed_read_only',
    'requires_user_authorization',
    'requires_future_network_dry_run_authorization',
    'requires_future_db_write_authorization',
    'blocked',
    'blocked_legacy',
]);
const ALLOWED_TEST_COVERAGE_VALUES = new Set([
    'unit_covered',
    'gate_covered',
    'needs_unit_tests',
    'needs_integration_tests',
    'not_covered',
]);

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/acquisition_engine_gate.js --list',
        '  node scripts/ops/acquisition_engine_gate.js --audit',
        '  node scripts/ops/acquisition_engine_gate.js --engine <id> --target-match-id <id> --source-manifest <path>',
        '  node scripts/ops/acquisition_engine_gate.js --engine <id> --target-match-id <id> --source-manifest <path> --commit',
        '',
        'Safety:',
        '  Phase 4.54 is scaffold-only. No engine execution, no DB writes, no external network, no staging writes.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        list: false,
        audit: false,
        engine: '',
        targetMatchId: '',
        sourceManifest: '',
        commit: false,
        json: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--list') {
            args.list = true;
        } else if (token === '--audit') {
            args.audit = true;
        } else if (token === '--engine') {
            args.engine = String(argv[index + 1] || '');
            index += 1;
        } else if (token === '--target-match-id') {
            args.targetMatchId = String(argv[index + 1] || '');
            index += 1;
        } else if (token === '--source-manifest') {
            args.sourceManifest = String(argv[index + 1] || '');
            index += 1;
        } else if (token === '--commit') {
            args.commit = true;
        } else if (token === '--json') {
            args.json = true;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
    }

    return args;
}

function boolToText(value) {
    return value ? 'true' : 'false';
}

function listToText(values) {
    if (!Array.isArray(values) || values.length === 0) {
        return 'none';
    }
    return values.join(',');
}

function resolveLocalFile(rawPath) {
    if (!rawPath) {
        return '';
    }
    return path.isAbsolute(rawPath) ? path.resolve(rawPath) : path.resolve(process.cwd(), rawPath);
}

function buildNonExecutionConfirmations() {
    return [
        'no_db_writes',
        'no_external_network',
        'no_engine_execution',
        'no_staging_writes',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
    ];
}

function loadRegistry() {
    const payload = {
        registry_found: fs.existsSync(REGISTRY_PATH),
        registry_path: path.relative(process.cwd(), REGISTRY_PATH),
        registry_valid: false,
        errors: [],
        registry: null,
    };

    if (!payload.registry_found) {
        payload.errors.push(`registry file not found: ${payload.registry_path}`);
        return payload;
    }

    try {
        payload.registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    } catch (error) {
        payload.errors.push(`registry parse error: ${error.message}`);
        return payload;
    }

    const validation = validateRegistry(payload.registry);
    payload.registry_valid = validation.valid;
    payload.errors.push(...validation.errors);
    return payload;
}

function validateRegistry(registry) {
    const errors = [];
    if (!registry || typeof registry !== 'object') {
        errors.push('registry root must be an object');
        return { valid: false, errors };
    }

    if (!Array.isArray(registry.engines) || registry.engines.length === 0) {
        errors.push('registry.engines must be a non-empty array');
        return { valid: false, errors };
    }

    const seenIds = new Set();
    registry.engines.forEach((engine, index) => {
        validateEngine(engine, index, seenIds, errors);
    });

    return {
        valid: errors.length === 0,
        errors,
    };
}

function validateMissingFields(engine, index, fields, errorPrefix, errors) {
    fields.forEach(field => {
        if (!(field in engine)) {
            errors.push(`engine[${index}] ${errorPrefix}: ${field}`);
        }
    });
}

function validateEngineId(engine, index, seenIds, errors) {
    if (typeof engine.id !== 'string' || engine.id.trim() === '') {
        errors.push(`engine[${index}] id must be a non-empty string`);
        return;
    }
    if (seenIds.has(engine.id)) {
        errors.push(`duplicate engine id: ${engine.id}`);
        return;
    }
    seenIds.add(engine.id);
}

function validateEnumField(engine, index, fieldName, allowedValues, errors) {
    if (fieldName in engine && !allowedValues.has(engine[fieldName])) {
        errors.push(`engine[${index}] invalid ${fieldName}: ${engine[fieldName]}`);
    }
}

function validateEngine(engine, index, seenIds, errors) {
    validateMissingFields(engine, index, REQUIRED_ENGINE_FIELDS, 'missing field', errors);
    validateMissingFields(engine, index, REQUIRED_GOVERNANCE_FIELDS, 'missing governance field', errors);
    validateEngineId(engine, index, seenIds, errors);

    if (!Array.isArray(engine.commands) || engine.commands.length === 0) {
        errors.push(`engine[${index}] commands must be a non-empty array`);
    }

    validateEnumField(engine, index, 'status', ALLOWED_STATUS_VALUES, errors);
    validateEnumField(engine, index, 'intended_layer', ALLOWED_INTENDED_LAYER_VALUES, errors);
    validateEnumField(engine, index, 'deprecation_status', ALLOWED_DEPRECATION_STATUS_VALUES, errors);
    validateEnumField(engine, index, 'allowed_next_phase', ALLOWED_NEXT_PHASE_VALUES, errors);
    validateEnumField(engine, index, 'test_coverage', ALLOWED_TEST_COVERAGE_VALUES, errors);

    if ('canonical_entrypoint' in engine && typeof engine.canonical_entrypoint !== 'boolean') {
        errors.push(`engine[${index}] canonical_entrypoint must be boolean`);
    }
}

function getEngines(registry) {
    return Array.isArray(registry?.engines) ? registry.engines : [];
}

function collectGovernanceFieldGaps(engines) {
    return engines
        .map(engine => ({
            id: engine.id,
            missing_fields: REQUIRED_GOVERNANCE_FIELDS.filter(field => !(field in engine)),
        }))
        .filter(entry => entry.missing_fields.length > 0);
}

function collectEnginesByStatus(engines, status) {
    return engines.filter(engine => engine.status === status).map(engine => engine.id);
}

function collectEnginesByNextPhase(engines, allowedNextPhase) {
    return engines.filter(engine => engine.allowed_next_phase === allowedNextPhase).map(engine => engine.id);
}

function collectEnginesByTestCoverage(engines, testCoverage) {
    return engines.filter(engine => engine.test_coverage === testCoverage).map(engine => engine.id);
}

function buildListPayload(loaded) {
    const engines = getEngines(loaded.registry);
    const safeCount = engines.filter(engine => engine.safe_for_ai_default === true).length;
    const blockedCount = engines.filter(engine => engine.phase454_policy === 'blocked').length;

    return {
        mode: 'acquisition-engine-list',
        registry_found: loaded.registry_found,
        registry_valid: loaded.registry_valid,
        registry_path: loaded.registry_path,
        total_engines: engines.length,
        safe_for_ai_default_count: safeCount,
        blocked_count: blockedCount,
        engines: engines.map(engine => ({
            id: engine.id,
            category: engine.category,
            phase454_policy: engine.phase454_policy,
            safe_for_ai_default: engine.safe_for_ai_default,
        })),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: loaded.errors,
    };
}

function buildAuditPayload(loaded) {
    const engines = getEngines(loaded.registry);
    const highRisk = engines
        .filter(engine => engine.accesses_network || engine.writes_db || engine.bulk_risk === 'high')
        .map(engine => engine.id);
    const allowedReadOnly = engines
        .filter(engine => engine.phase454_policy === 'allowed_read_only')
        .map(engine => engine.id);
    const blocked = engines.filter(engine => engine.phase454_policy === 'blocked').map(engine => engine.id);
    const missingProvenance = engines.filter(engine => engine.provenance_required !== true).map(engine => engine.id);
    const missingGovernanceFields = collectGovernanceFieldGaps(engines);

    return {
        mode: 'acquisition-engine-audit',
        registry_found: loaded.registry_found,
        registry_valid: loaded.registry_valid,
        registry_path: loaded.registry_path,
        total_engines: engines.length,
        governance_fields_required: REQUIRED_GOVERNANCE_FIELDS,
        governance_fields_complete: missingGovernanceFields.length === 0,
        missing_governance_fields: missingGovernanceFields,
        high_risk_engines: highRisk,
        allowed_read_only_engines: allowedReadOnly,
        blocked_engines: blocked,
        canonical_engines: collectEnginesByStatus(engines, 'canonical'),
        gate_only_engines: collectEnginesByStatus(engines, 'gate_only'),
        quarantine_engines: collectEnginesByStatus(engines, 'quarantine'),
        deprecation_candidate_engines: collectEnginesByStatus(engines, 'deprecation_candidate'),
        adapter_candidate_engines: collectEnginesByStatus(engines, 'adapter_candidate'),
        legacy_blocked_engines: collectEnginesByStatus(engines, 'legacy_blocked'),
        engines_requiring_user_authorization: collectEnginesByNextPhase(engines, 'requires_user_authorization'),
        engines_requiring_future_network_authorization: collectEnginesByNextPhase(
            engines,
            'requires_future_network_dry_run_authorization'
        ),
        engines_requiring_future_db_write_authorization: collectEnginesByNextPhase(
            engines,
            'requires_future_db_write_authorization'
        ),
        engines_needing_unit_tests: collectEnginesByTestCoverage(engines, 'needs_unit_tests'),
        engines_missing_provenance_requirement: missingProvenance,
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: loaded.errors,
    };
}

function buildBlockedCommitPayload(args, loaded) {
    return {
        mode: 'blocked-commit',
        registry_found: loaded.registry_found,
        registry_valid: loaded.registry_valid,
        registry_path: loaded.registry_path,
        engine_id: args.engine || '',
        target_match_id: args.targetMatchId || '',
        source_manifest: args.sourceManifest || '',
        blocked_reason: 'BLOCKED: acquisition network commit is not wired in Phase 4.54.',
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: loaded.errors,
    };
}

function resolveEngineRequirements(engine) {
    return {
        sourceManifestRequired: engine ? engine.source_manifest_required !== false : true,
        targetScopeRequired: engine ? engine.target_scope_required !== false : true,
    };
}

function resolveManifestState(sourceManifest, sourceManifestRequired) {
    const resolvedManifestPath = resolveLocalFile(sourceManifest);
    return {
        resolvedManifestPath,
        sourceManifestFound: resolvedManifestPath ? fs.existsSync(resolvedManifestPath) : false,
        missingSourceManifest: sourceManifestRequired && !sourceManifest,
    };
}

function resolveBlockedReason({ args, engine, sourceManifestFound, missingSourceManifest, missingTargetScope }) {
    if (!engine) {
        return `BLOCKED: unknown engine id: ${args.engine}`;
    }

    if (missingSourceManifest) {
        return 'BLOCKED: missing SOURCE_MANIFEST. Phase 4.54 does not create manifests or access network.';
    }

    if (!sourceManifestFound) {
        return `BLOCKED: source manifest not found: ${args.sourceManifest}`;
    }

    if (missingTargetScope) {
        return 'BLOCKED: missing TARGET_MATCH_ID. Phase 4.54 requires explicit single-target scope.';
    }

    if (engine.phase454_policy === 'blocked') {
        return 'BLOCKED: Phase 4.54 is scaffold-only. This engine must not be executed without a future explicit single-target network dry-run authorization.';
    }

    return 'BLOCKED: Phase 4.54 network gate is scaffold-only. Use dedicated local read-only gates for this engine until a future phase authorizes network execution.';
}

function buildEnginePayload(args, loaded) {
    const engines = getEngines(loaded.registry);
    const engine = engines.find(entry => entry.id === args.engine) || null;
    const { sourceManifestRequired, targetScopeRequired } = resolveEngineRequirements(engine);
    const { sourceManifestFound, missingSourceManifest } = resolveManifestState(
        args.sourceManifest,
        sourceManifestRequired
    );
    const missingTargetScope = targetScopeRequired && !args.targetMatchId;
    const blockedReason = resolveBlockedReason({
        args,
        engine,
        sourceManifestFound,
        missingSourceManifest,
        missingTargetScope,
    });

    return {
        mode: 'single-target-network-scaffold',
        registry_found: loaded.registry_found,
        registry_valid: loaded.registry_valid,
        registry_path: loaded.registry_path,
        engine_found: Boolean(engine),
        engine_id: engine ? engine.id : args.engine || '',
        phase454_policy: engine ? engine.phase454_policy : 'not_found',
        accesses_network: engine ? engine.accesses_network : false,
        writes_db: engine ? engine.writes_db : false,
        bulk_risk: engine ? engine.bulk_risk : 'unknown',
        dry_run_trust_level: engine ? engine.dry_run_trust_level : 'unknown',
        source_manifest_required: sourceManifestRequired,
        target_scope_required: targetScopeRequired,
        target_match_id: args.targetMatchId || '',
        source_manifest: args.sourceManifest || '',
        source_manifest_found: sourceManifestFound,
        missing_source_manifest: missingSourceManifest,
        missing_target_scope: missingTargetScope,
        would_access_network: false,
        would_write_db: false,
        would_execute_engine: false,
        blocked_reason: blockedReason,
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: loaded.errors,
    };
}

function formatListText(payload) {
    const lines = [
        `mode=${payload.mode}`,
        `registry_found=${boolToText(payload.registry_found)}`,
        `registry_valid=${boolToText(payload.registry_valid)}`,
        `registry_path=${payload.registry_path}`,
        `total_engines=${payload.total_engines}`,
        `safe_for_ai_default_count=${payload.safe_for_ai_default_count}`,
        `blocked_count=${payload.blocked_count}`,
        'no_db_writes',
        'no_external_network',
        'engines:',
    ];

    payload.engines.forEach(engine => {
        lines.push(
            `  id=${engine.id} category=${engine.category} phase454_policy=${engine.phase454_policy} safe_for_ai_default=${boolToText(
                engine.safe_for_ai_default
            )}`
        );
    });

    return lines.join('\n');
}

function formatAuditText(payload) {
    return [
        `mode=${payload.mode}`,
        `registry_found=${boolToText(payload.registry_found)}`,
        `registry_valid=${boolToText(payload.registry_valid)}`,
        `registry_path=${payload.registry_path}`,
        `total_engines=${payload.total_engines}`,
        `governance_fields_required=${listToText(payload.governance_fields_required)}`,
        `governance_fields_complete=${boolToText(payload.governance_fields_complete)}`,
        `missing_governance_fields=${payload.missing_governance_fields.length === 0 ? 'none' : JSON.stringify(payload.missing_governance_fields)}`,
        `high_risk_engines=${listToText(payload.high_risk_engines)}`,
        `allowed_read_only_engines=${listToText(payload.allowed_read_only_engines)}`,
        `blocked_engines=${listToText(payload.blocked_engines)}`,
        `canonical_engines=${listToText(payload.canonical_engines)}`,
        `gate_only_engines=${listToText(payload.gate_only_engines)}`,
        `quarantine_engines=${listToText(payload.quarantine_engines)}`,
        `deprecation_candidate_engines=${listToText(payload.deprecation_candidate_engines)}`,
        `adapter_candidate_engines=${listToText(payload.adapter_candidate_engines)}`,
        `legacy_blocked_engines=${listToText(payload.legacy_blocked_engines)}`,
        `engines_requiring_user_authorization=${listToText(payload.engines_requiring_user_authorization)}`,
        `engines_requiring_future_network_authorization=${listToText(payload.engines_requiring_future_network_authorization)}`,
        `engines_requiring_future_db_write_authorization=${listToText(payload.engines_requiring_future_db_write_authorization)}`,
        `engines_needing_unit_tests=${listToText(payload.engines_needing_unit_tests)}`,
        `engines_missing_provenance_requirement=${listToText(payload.engines_missing_provenance_requirement)}`,
        'no_db_writes',
        'no_external_network',
    ].join('\n');
}

function formatBlockedCommitText(payload) {
    return [
        `mode=${payload.mode}`,
        `registry_found=${boolToText(payload.registry_found)}`,
        `registry_valid=${boolToText(payload.registry_valid)}`,
        `registry_path=${payload.registry_path}`,
        `engine_id=${payload.engine_id}`,
        `target_match_id=${payload.target_match_id}`,
        `source_manifest=${payload.source_manifest}`,
        payload.blocked_reason,
        'no_db_writes',
        'no_external_network',
    ].join('\n');
}

function formatEngineText(payload) {
    return [
        `mode=${payload.mode}`,
        `registry_found=${boolToText(payload.registry_found)}`,
        `registry_valid=${boolToText(payload.registry_valid)}`,
        `registry_path=${payload.registry_path}`,
        `engine_found=${boolToText(payload.engine_found)}`,
        `engine_id=${payload.engine_id}`,
        `phase454_policy=${payload.phase454_policy}`,
        `accesses_network=${boolToText(payload.accesses_network)}`,
        `writes_db=${boolToText(payload.writes_db)}`,
        `bulk_risk=${payload.bulk_risk}`,
        `dry_run_trust_level=${payload.dry_run_trust_level}`,
        `source_manifest_required=${boolToText(payload.source_manifest_required)}`,
        `target_scope_required=${boolToText(payload.target_scope_required)}`,
        `source_manifest=${payload.source_manifest}`,
        `source_manifest_found=${boolToText(payload.source_manifest_found)}`,
        `target_match_id=${payload.target_match_id}`,
        `missing_source_manifest=${boolToText(payload.missing_source_manifest)}`,
        `missing_target_scope=${boolToText(payload.missing_target_scope)}`,
        `would_access_network=${boolToText(payload.would_access_network)}`,
        `would_write_db=${boolToText(payload.would_write_db)}`,
        `would_execute_engine=${boolToText(payload.would_execute_engine)}`,
        `blocked_reason=${payload.blocked_reason}`,
        'no_db_writes',
        'no_external_network',
        'no_engine_execution',
    ].join('\n');
}

function emit(payload, asJson, formatter) {
    if (asJson) {
        console.log(JSON.stringify(payload, null, 2));
        return;
    }
    console.log(formatter(payload));
}

function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }

    const loaded = loadRegistry();
    if (args.commit) {
        const payload = buildBlockedCommitPayload(args, loaded);
        emit(payload, args.json, formatBlockedCommitText);
        process.exitCode = 1;
        return;
    }

    if (args.list) {
        const payload = buildListPayload(loaded);
        emit(payload, args.json, formatListText);
        if (!loaded.registry_valid) {
            process.exitCode = 1;
        }
        return;
    }

    if (args.audit) {
        const payload = buildAuditPayload(loaded);
        emit(payload, args.json, formatAuditText);
        if (!loaded.registry_valid) {
            process.exitCode = 1;
        }
        return;
    }

    if (!args.engine) {
        console.error('ERROR: provide --list, --audit, or --engine <id>');
        console.error(usage());
        process.exitCode = 1;
        return;
    }

    const payload = buildEnginePayload(args, loaded);
    emit(payload, args.json, formatEngineText);
    process.exitCode = 1;
}

if (require.main === module) {
    try {
        main();
    } catch (error) {
        console.error(
            JSON.stringify(
                {
                    mode: 'acquisition-engine-gate',
                    ok: false,
                    error: error.message,
                    non_execution_confirmations: buildNonExecutionConfirmations(),
                },
                null,
                2
            )
        );
        process.exitCode = 1;
    }
}

module.exports = {
    REGISTRY_PATH,
    buildAuditPayload,
    buildBlockedCommitPayload,
    buildEnginePayload,
    buildListPayload,
    buildNonExecutionConfirmations,
    formatAuditText,
    formatBlockedCommitText,
    formatEngineText,
    formatListText,
    loadRegistry,
    parseArgs,
    resolveBlockedReason,
    resolveEngineRequirements,
    resolveManifestState,
    validateRegistry,
    REQUIRED_GOVERNANCE_FIELDS,
    ALLOWED_STATUS_VALUES,
    ALLOWED_INTENDED_LAYER_VALUES,
    ALLOWED_DEPRECATION_STATUS_VALUES,
    ALLOWED_NEXT_PHASE_VALUES,
    ALLOWED_TEST_COVERAGE_VALUES,
};
