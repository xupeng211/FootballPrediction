'use strict';

/* eslint-disable max-lines -- version binding, engine invocation, and lineage projection are one boundary. */
/* eslint-disable complexity -- projection validation is intentionally fail-closed. */

// lifecycle: permanent
// GD-A03 V-next standings integration。它只调用已合并的
// PointInTimeStandingsEngine；V1 GdA03PriorStateAssembler 与 V1 artifact
// contract 不在此模块内被改写，也不会被这个模块隐式激活。

const {
    buildHistoricalStandingsEvidenceInputs,
    FrozenEvidenceAdapterError,
} = require('../standings/PremierLeagueFrozenEvidenceAdapter');
const { APPROVED_REAL_MASTER_V1_IDENTITY_PROJECTION_HASH } = require('../canonical/CanonicalInventoryContract');
const { STANDINGS_CONTRACT_ID, STANDINGS_CONTRACT_VERSION } = require('../standings/StandingsContractBinding');
const { computeStandingsSnapshots } = require('../standings/PointInTimeStandingsEngine');
const { sha256Text, stableStringify } = require('../canonical/StableValue');

const VNEXT_CONTRACT_ID = 'canonical_prematch/vnext-v1';
const VNEXT_FEATURE_COUNT = 17;
const STANDINGS_FEATURES = Object.freeze(['home_table_position', 'away_table_position', 'table_position_diff']);
const FEATURE_STATUS_FIELDS = new Set([
    'feature_name',
    'v_next_status',
    'semantic_definition_status',
    'historical_source_status',
    'runtime_source_status',
    'training_eligibility',
    'reason_code',
]);

class GdA03StandingsIntegrationError extends Error {
    constructor(message, code = 'DEPENDENCY_UNAVAILABLE') {
        super(message);
        this.name = 'GdA03StandingsIntegrationError';
        this.code = code;
        this.reasonCode = code;
    }
}

function fail(message, code = 'DEPENDENCY_UNAVAILABLE') {
    throw new GdA03StandingsIntegrationError(message, code);
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function assertObject(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (!isPlainObject(value)) fail(`${label} must be an object`, code);
    return value;
}

function assertArray(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (!Array.isArray(value)) fail(`${label} must be an array`, code);
    return value;
}

function assertText(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (typeof value !== 'string' || value.trim() === '') fail(`${label} must be non-empty text`, code);
    return value;
}

function assertSha(value, label) {
    if (typeof value !== 'string' || !/^[0-9a-f]{64}$/.test(value)) fail(`${label} must be a lowercase SHA-256`);
    return value;
}

function assertKnownKeys(value, allowed, label, code = 'DEPENDENCY_UNAVAILABLE') {
    for (const key of Object.keys(value)) {
        if (!allowed.has(key)) fail(`${label} contains unsupported field ${key}`, code);
    }
}

function assertRequiredKeys(value, required, label, code = 'DEPENDENCY_UNAVAILABLE') {
    for (const key of required) {
        if (!Object.hasOwn(value, key)) fail(`${label}.${key} is required`, code);
    }
}

function bindVNextFeatureContract(registry) {
    const value = assertObject(registry, 'feature contract registry', 'RULE_VERSION_UNPROVEN');
    if (value.schema_version !== 'model-feature-contract-registry/v2' || value.lifecycle !== 'permanent') {
        fail('feature contract registry boundary is malformed', 'RULE_VERSION_UNPROVEN');
    }
    const contracts = assertArray(value.contracts, 'feature contract registry.contracts', 'RULE_VERSION_UNPROVEN');
    const contract = contracts.find(candidate => candidate?.contract_id === VNEXT_CONTRACT_ID);
    if (!contract) fail('V-next feature contract is missing from the canonical registry', 'RULE_VERSION_UNPROVEN');
    if (
        contract.contract_role !== 'VERSIONED_NEXT' ||
        contract.activation_status !== 'DEFINED_NOT_ACTIVATED' ||
        contract.feature_count !== VNEXT_FEATURE_COUNT ||
        contract.feature_contract_version !== 'canonical_prematch/vnext/v1'
    ) {
        fail('V-next feature contract activation or version boundary is invalid', 'RULE_VERSION_UNPROVEN');
    }
    const orderedFeatures = assertArray(contract.ordered_features, 'V-next ordered_features', 'RULE_VERSION_UNPROVEN');
    if (orderedFeatures.length !== VNEXT_FEATURE_COUNT || new Set(orderedFeatures).size !== VNEXT_FEATURE_COUNT) {
        fail('V-next feature order/count is malformed', 'RULE_VERSION_UNPROVEN');
    }
    const statuses = assertArray(contract.feature_statuses, 'V-next feature_statuses', 'RULE_VERSION_UNPROVEN');
    if (statuses.length !== VNEXT_FEATURE_COUNT) {
        fail('V-next feature status count is malformed', 'RULE_VERSION_UNPROVEN');
    }
    const statusByName = new Map();
    statuses.forEach((status, index) => {
        const label = `V-next feature_statuses[${index}]`;
        assertObject(status, label, 'RULE_VERSION_UNPROVEN');
        assertKnownKeys(status, FEATURE_STATUS_FIELDS, label, 'RULE_VERSION_UNPROVEN');
        assertRequiredKeys(status, FEATURE_STATUS_FIELDS, label, 'RULE_VERSION_UNPROVEN');
        if (status.feature_name !== orderedFeatures[index] || statusByName.has(status.feature_name)) {
            fail('V-next feature status order does not bind ordered_features', 'RULE_VERSION_UNPROVEN');
        }
        statusByName.set(status.feature_name, { ...status });
    });
    for (const featureName of STANDINGS_FEATURES) {
        const status = statusByName.get(featureName);
        if (
            !status ||
            status.v_next_status !== 'RETAINED_PROVEN' ||
            status.semantic_definition_status !== 'SEMANTICS_FROZEN' ||
            status.historical_source_status !== 'PROVEN_FOR_FROZEN_SCOPE' ||
            status.runtime_source_status !== 'NOT_PROVEN' ||
            status.training_eligibility !== 'NOT_READY_RUNTIME_PARITY'
        ) {
            fail(`${featureName} V-next status is not bound to the frozen authority`, 'RULE_VERSION_UNPROVEN');
        }
    }
    return Object.freeze({
        contract_id: contract.contract_id,
        feature_contract_version: contract.feature_contract_version,
        feature_count: contract.feature_count,
        ordered_features: [...orderedFeatures],
        contract_role: contract.contract_role,
        activation_status: contract.activation_status,
        registry_schema_version: value.schema_version,
        registry_sha256: sha256Text(stableStringify(value)),
        standings_feature_statuses: Object.fromEntries(
            STANDINGS_FEATURES.map(featureName => [featureName, statusByName.get(featureName)])
        ),
    });
}

function assertScheduleClosure(scheduleClosure) {
    const value = assertObject(scheduleClosure, 'standings schedule closure', 'DEPENDENCY_UNAVAILABLE');
    if (
        value.status !== 'PROVEN' ||
        value.canonical_schedule_count !== 1140 ||
        value.canonical_schedule_business_sha256 !== APPROVED_REAL_MASTER_V1_IDENTITY_PROJECTION_HASH
    ) {
        fail('GD-A03 standings integration requires proven 1,140-fixture schedule closure', 'DEPENDENCY_UNAVAILABLE');
    }
    assertSha(value.canonical_schedule_sha256, 'standings schedule closure.canonical_schedule_sha256');
    assertSha(value.canonical_required_set_sha256, 'standings schedule closure.canonical_required_set_sha256');
    assertObject(value.source_binding, 'standings schedule closure.source_binding');
    assertSha(value.source_binding.sha256, 'standings schedule closure.source_binding.sha256');
    return value;
}

function assertEngineImplementation(engineImplementation) {
    const value = assertObject(engineImplementation, 'standings engine implementation binding');
    assertText(value.implementation_id, 'standings engine implementation_binding.implementation_id');
    if (value.implementation_id !== 'PointInTimeStandingsEngine') {
        fail('GD-A03 standings integration is bound to an unexpected engine', 'DEPENDENCY_UNAVAILABLE');
    }
    assertText(value.source_commit, 'standings engine implementation_binding.source_commit');
    return { ...value };
}

function assertEngineOutput(output) {
    const value = assertObject(output, 'standings engine output');
    assertRequiredKeys(
        value,
        [
            'snapshot_status',
            'target_match_id',
            'target_kickoff_utc',
            'season',
            'contract_id',
            'contract_version',
            'home_table_position',
            'away_table_position',
            'table_position_diff',
            'unavailable_reason_codes',
            'source_event_ids_used',
            'administrative_adjustment_ids_considered',
            'administrative_adjustment_ids_applied',
            'input_digest',
            'provenance_digest',
        ],
        'standings engine output'
    );
    if (!['AVAILABLE', 'UNAVAILABLE'].includes(value.snapshot_status)) fail('standings engine status is invalid');
    if (value.contract_id !== STANDINGS_CONTRACT_ID || value.contract_version !== STANDINGS_CONTRACT_VERSION) {
        fail('standings engine output contract binding differs', 'RULE_VERSION_UNPROVEN');
    }
    assertText(value.target_match_id, 'standings engine output.target_match_id');
    assertText(value.season, 'standings engine output.season');
    assertText(value.target_kickoff_utc, 'standings engine output.target_kickoff_utc');
    assertArray(value.unavailable_reason_codes, 'standings engine output.unavailable_reason_codes');
    assertArray(value.source_event_ids_used, 'standings engine output.source_event_ids_used');
    assertArray(
        value.administrative_adjustment_ids_considered,
        'standings engine output.administrative_adjustment_ids_considered'
    );
    assertArray(
        value.administrative_adjustment_ids_applied,
        'standings engine output.administrative_adjustment_ids_applied'
    );
    assertSha(value.input_digest, 'standings engine output.input_digest');
    assertSha(value.provenance_digest, 'standings engine output.provenance_digest');
    if (value.snapshot_status === 'AVAILABLE') {
        for (const field of ['home_table_position', 'away_table_position']) {
            if (!Number.isSafeInteger(value[field]) || value[field] < 1 || value[field] > 20) {
                fail(`available standings output.${field} is outside 1..20`, 'STANDINGS_POSITION_UNAVAILABLE');
            }
        }
        if (
            !Number.isSafeInteger(value.table_position_diff) ||
            value.table_position_diff !== value.home_table_position - value.away_table_position ||
            value.table_position_diff < -19 ||
            value.table_position_diff > 19
        ) {
            fail('available standings table_position_diff has the wrong orientation', 'STANDINGS_POSITION_UNAVAILABLE');
        }
        if (value.unavailable_reason_codes.length !== 0) {
            fail('available output contains unavailable reasons', 'DEPENDENCY_UNAVAILABLE');
        }
    } else {
        if (
            value.home_table_position !== null ||
            value.away_table_position !== null ||
            value.table_position_diff !== null
        ) {
            fail(
                'unavailable standings output contains fabricated numeric positions',
                'STANDINGS_POSITION_UNAVAILABLE'
            );
        }
        if (value.unavailable_reason_codes.length === 0) {
            fail('unavailable standings output has no reason code', 'DEPENDENCY_UNAVAILABLE');
        }
    }
    return value;
}

function makeEvidenceIds(output, context) {
    const resultById = context.lineage.resultByMatchId;
    const adjustmentById = context.lineage.adjustmentById;
    const sourceEventIds = [...output.source_event_ids_used].sort((left, right) => left.localeCompare(right));
    const eventLineage = sourceEventIds.map(matchId => {
        const lineage = resultById[matchId];
        if (!lineage) fail(`engine source event ${matchId} has no adapter lineage`, 'DEPENDENCY_UNAVAILABLE');
        return {
            canonical_match_id: matchId,
            source_record_sha256: lineage.source_record_sha256,
            actual_event_time_utc: lineage.actual_event_time_utc,
        };
    });
    const adjustmentIds = [...output.administrative_adjustment_ids_considered].sort((left, right) =>
        left.localeCompare(right)
    );
    const adjustmentLineage = adjustmentIds.map(adjustmentId => {
        const lineage = adjustmentById[adjustmentId];
        if (!lineage) fail(`engine adjustment ${adjustmentId} has no adapter lineage`, 'ADMIN_ADJUSTMENT_CONFLICT');
        return { adjustment_id: adjustmentId, ...lineage };
    });
    return {
        source_event_ids_used: sourceEventIds,
        actual_event_time_evidence: eventLineage,
        administrative_adjustment_ids_considered: adjustmentIds,
        administrative_adjustment_ids_applied: [...output.administrative_adjustment_ids_applied].sort((left, right) =>
            left.localeCompare(right)
        ),
        administrative_adjustment_evidence: adjustmentLineage,
        exception_disposition_evidence: {
            evidence_file: 'exception-status-audit.json',
            evidence_sha256: context.sourceBindings.exception_status_audit.sha256,
        },
        postponed_event_time_evidence: {
            evidence_file: 'postponed-rescheduled-audit.json',
            evidence_sha256: context.sourceBindings.postponed_rescheduled_audit.sha256,
        },
    };
}

function makeFeatureLine(featureName, output, sharedLineage, scheduleClosure, engineImplementation) {
    const value = output.snapshot_status === 'AVAILABLE' ? output[featureName] : null;
    const lineageDigest = sha256Text(stableStringify(sharedLineage));
    return {
        feature_name: featureName,
        value,
        availability: output.snapshot_status,
        unavailable_reason_codes: [...output.unavailable_reason_codes],
        contract_id: STANDINGS_CONTRACT_ID,
        contract_version: STANDINGS_CONTRACT_VERSION,
        v_next_contract_id: VNEXT_CONTRACT_ID,
        cutoff_rule: 'SOURCE_EVENT_TIME_LT_TARGET_KICKOFF',
        target_kickoff_utc: output.target_kickoff_utc,
        lineage_ref: 'row.standings_lineage',
        lineage_digest: lineageDigest,
        source_event_count: sharedLineage.source_event_ids_used.length,
        administrative_adjustment_count: sharedLineage.administrative_adjustment_ids_considered.length,
        canonical_schedule_authority: {
            evidence_file: 'derived/official-fixture-projection.json',
            evidence_sha256: scheduleClosure.source_binding.sha256,
            canonical_schedule_sha256: scheduleClosure.canonical_schedule_sha256,
            canonical_schedule_business_sha256: scheduleClosure.canonical_schedule_business_sha256,
            closure_status: scheduleClosure.status,
        },
        engine_implementation: engineImplementation,
        engine_input_digest: output.input_digest,
        engine_provenance_digest: output.provenance_digest,
    };
}

function projectStandingsSnapshot({ output, vNextContractBinding, context, scheduleClosure, engineImplementation }) {
    const value = assertEngineOutput(output);
    const targetLineage = context.lineage.targetByMatchId[value.target_match_id];
    if (!targetLineage) fail(`target ${value.target_match_id} has no adapter lineage`, 'DEPENDENCY_UNAVAILABLE');
    const sharedLineage = makeEvidenceIds(value, context);
    const lineageDigest = sha256Text(stableStringify(sharedLineage));
    const featureLines = Object.fromEntries(
        STANDINGS_FEATURES.map(featureName => [
            featureName,
            makeFeatureLine(featureName, value, sharedLineage, scheduleClosure, engineImplementation),
        ])
    );
    const row = {
        target_match_id: value.target_match_id,
        season: value.season,
        target_kickoff_utc: value.target_kickoff_utc,
        snapshot_status: value.snapshot_status,
        contract_id: STANDINGS_CONTRACT_ID,
        contract_version: STANDINGS_CONTRACT_VERSION,
        v_next_contract_id: vNextContractBinding.contract_id,
        v_next_feature_contract_version: vNextContractBinding.feature_contract_version,
        v_next_activation_status: vNextContractBinding.activation_status,
        home_table_position: value.snapshot_status === 'AVAILABLE' ? value.home_table_position : null,
        away_table_position: value.snapshot_status === 'AVAILABLE' ? value.away_table_position : null,
        table_position_diff: value.snapshot_status === 'AVAILABLE' ? value.table_position_diff : null,
        unavailable_reason_codes: [...value.unavailable_reason_codes],
        feature_lines: featureLines,
        target_lineage: targetLineage,
        standings_lineage: sharedLineage,
        standings_lineage_digest: lineageDigest,
        engine_input_digest: value.input_digest,
        engine_provenance_digest: value.provenance_digest,
    };
    row.provenance_digest = sha256Text(
        stableStringify({
            target_match_id: row.target_match_id,
            snapshot_status: row.snapshot_status,
            values: [row.home_table_position, row.away_table_position, row.table_position_diff],
            unavailable_reason_codes: row.unavailable_reason_codes,
            standings_lineage: row.standings_lineage,
            engine_input_digest: row.engine_input_digest,
            engine_provenance_digest: row.engine_provenance_digest,
        })
    );
    return row;
}

function businessProjectionRow(row) {
    return {
        target_match_id: row.target_match_id,
        season: row.season,
        snapshot_status: row.snapshot_status,
        home_table_position: row.home_table_position,
        away_table_position: row.away_table_position,
        table_position_diff: row.table_position_diff,
        unavailable_reason_codes: [...row.unavailable_reason_codes].sort((left, right) => left.localeCompare(right)),
    };
}

function computeBusinessProjectionHash(rows) {
    const normalized = [...rows]
        .map(businessProjectionRow)
        .sort((left, right) => left.target_match_id.localeCompare(right.target_match_id));
    return sha256Text(stableStringify(normalized));
}

function buildGdA03StandingsProjection({
    registry,
    officialFixtureProjection,
    normalizedPriorResultLedger,
    missingPriorFixtureLedger,
    postponedRescheduledAudit,
    exceptionStatusAudit,
    administrativeAdjustmentLedger,
    targetClosureAudit,
    seasonRuleMatrix,
    sourceBindings,
    engineImplementation,
}) {
    const context = buildHistoricalStandingsEvidenceInputs({
        registry,
        officialFixtureProjection,
        normalizedPriorResultLedger,
        missingPriorFixtureLedger,
        postponedRescheduledAudit,
        exceptionStatusAudit,
        administrativeAdjustmentLedger,
        targetClosureAudit,
        seasonRuleMatrix,
        sourceBindings,
    });
    const vNextContractBinding = bindVNextFeatureContract(registry);
    const scheduleClosure = assertScheduleClosure(context.scheduleClosure);
    const implementation = assertEngineImplementation(engineImplementation);
    const outputs = computeStandingsSnapshots(context.inputs);
    if (outputs.length !== context.inputs.length) {
        fail('engine output population differs from adapter target population');
    }
    const rows = outputs.map(output =>
        projectStandingsSnapshot({
            output,
            vNextContractBinding,
            context,
            scheduleClosure,
            engineImplementation: implementation,
        })
    );
    return Object.freeze({
        integration_status: 'IMPLEMENTED_HISTORICAL_PROJECTION_ONLY',
        standings_contract_id: STANDINGS_CONTRACT_ID,
        standings_contract_version: STANDINGS_CONTRACT_VERSION,
        v_next_contract: vNextContractBinding,
        schedule_closure: {
            status: scheduleClosure.status,
            canonical_schedule_count: scheduleClosure.canonical_schedule_count,
            canonical_schedule_sha256: scheduleClosure.canonical_schedule_sha256,
            canonical_schedule_business_sha256: scheduleClosure.canonical_schedule_business_sha256,
            canonical_required_set_sha256: scheduleClosure.canonical_required_set_sha256,
            per_season: scheduleClosure.per_season,
            source_binding: scheduleClosure.source_binding,
        },
        reconciliation: context.reconciliation,
        source_bindings: context.sourceBindings,
        rows,
        target_population: rows.length,
        business_projection_hash: computeBusinessProjectionHash(rows),
    });
}

module.exports = {
    FrozenEvidenceAdapterError,
    GdA03StandingsIntegrationError,
    STANDINGS_FEATURES,
    VNEXT_CONTRACT_ID,
    VNEXT_FEATURE_COUNT,
    bindVNextFeatureContract,
    buildGdA03StandingsProjection,
    businessProjectionRow,
    computeBusinessProjectionHash,
    projectStandingsSnapshot,
};
