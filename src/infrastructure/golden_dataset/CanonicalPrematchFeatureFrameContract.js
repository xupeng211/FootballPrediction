'use strict';

/* eslint-disable max-lines -- the file-first frame contract keeps projection, receipt, and validation together. */
/* eslint-disable complexity -- validation enumerates independent business safety boundaries. */

// lifecycle: permanent；第一版 canonical prematch training frame 的离线 contract。
// 该模块只投影已经通过 GD-A03 校验的文件，不读取数据库、不联网、不写 raw、
// 不训练、不 backtest，也不改变 V1 默认模型 contract。

const { sha256Text, stableStringify } = require('../canonical/StableValue');
const { admittedIdSetHash, sha256Bytes } = require('./GdA01AssemblyContract');

const FRAME_SCHEMA_VERSION = 'canonical-prematch-training-feature-frame/v1';
const FRAME_RECEIPT_SCHEMA_VERSION = 'canonical-prematch-training-feature-frame-receipt/v1';
const FRAME_STAGE = 'CANONICAL_PREMATCH_FEATURE_FRAME';
const FRAME_CONTRACT_ID = 'canonical_prematch/vnext-v1';
const FRAME_CONTRACT_VERSION = 'canonical_prematch/vnext/v1';
const FRAME_CUTOFF_POLICY = 'TARGET_KICKOFF_EXCLUSIVE';
const FRAME_CUTOFF_RELATION = 'source_match_kickoff < target_match_kickoff';
const FRAME_AS_OF_STATUS = 'KICKOFF_REFERENCE_ONLY';
const FRAME_DECISION_TIME_STATUS = 'NOT_PROVEN_KICKOFF_REFERENCE_ONLY';
const FRAME_READINESS = Object.freeze({
    feature_frame_readiness: 'READY',
    real_training_readiness: 'READY',
    strict_decision_time_value_evaluation: 'NOT_READY',
    golden_dataset_complete: false,
    training_execution_authorized: false,
});
const TRAINING_DECISIONS = new Set([
    'ACCEPTED_FOR_TRAINING',
    'EXCLUDED_FROM_TRAINING',
    'BLOCKED_PENDING_EVIDENCE',
]);

class CanonicalPrematchFeatureFrameError extends Error {
    constructor(message, code = 'FRAME_CONTRACT_INVALID') {
        super(message);
        this.name = 'CanonicalPrematchFeatureFrameError';
        this.code = code;
        this.reasonCode = code;
    }
}

function fail(message, code = 'FRAME_CONTRACT_INVALID') {
    throw new CanonicalPrematchFeatureFrameError(message, code);
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function assertObject(value, label) {
    if (!isPlainObject(value)) fail(`${label} must be an object`, 'SCHEMA_MISMATCH');
    return value;
}

function assertArray(value, label) {
    if (!Array.isArray(value)) fail(`${label} must be an array`, 'SCHEMA_MISMATCH');
    return value;
}

function assertText(value, label) {
    if (typeof value !== 'string' || !value.trim()) fail(`${label} must be non-empty text`, 'SCHEMA_MISMATCH');
    return value;
}

function assertSha(value, label) {
    if (typeof value !== 'string' || !/^[0-9a-f]{64}$/.test(value)) {
        fail(`${label} must be a lowercase SHA-256`, 'PROVENANCE_INVALID');
    }
    return value;
}

function assertFullSha(value, label) {
    if (typeof value !== 'string' || !/^[0-9a-f]{40}$/.test(value)) {
        fail(`${label} must be a full Git SHA`, 'PROVENANCE_INVALID');
    }
    return value;
}

function computeFrameBusinessHash(artifact) {
    const projection = { ...artifact, business_content_sha256: null };
    return sha256Text(stableStringify(projection));
}

function computeFrameReceiptHash(receipt) {
    return sha256Text(stableStringify({ ...receipt, receipt_content_sha256: null }));
}

function sourceLineBindingDigest(rowId, featureName, line) {
    const sourceLine = clone(line);
    delete sourceLine.source_line_sha256;
    return sha256Text(stableStringify({ row_id: rowId, feature_name: featureName, line: sourceLine }));
}

function bindSourceLine(rowId, featureName, line) {
    const bound = clone(line);
    bound.source_line_sha256 = sourceLineBindingDigest(rowId, featureName, bound);
    return bound;
}

function validateSourceLine(rowId, featureName, line, targetKickoff) {
    assertObject(line, `${rowId}.${featureName}`);
    assertText(line.source_line_sha256, `${rowId}.${featureName}.source_line_sha256`);
    assertSha(line.source_line_sha256, `${rowId}.${featureName}.source_line_sha256`);
    if (line.source_line_sha256 !== sourceLineBindingDigest(rowId, featureName, line)) {
        fail(`${rowId}.${featureName} source-line binding mismatch`, 'PROVENANCE_INVALID');
    }
    if (!['AVAILABLE', 'UNAVAILABLE'].includes(line.availability_status)) {
        fail(`${rowId}.${featureName} availability is invalid`, 'SCHEMA_MISMATCH');
    }
    if (line.availability_status === 'AVAILABLE') {
        if (typeof line.value !== 'number' || !Number.isFinite(line.value)) {
            fail(`${rowId}.${featureName} available value is invalid`, 'FACT_VALUE_INVALID');
        }
        if (Array.isArray(line.unavailable_reason_codes) && line.unavailable_reason_codes.length > 0) {
            fail(`${rowId}.${featureName} available line carries an unavailable reason`, 'FACT_VALUE_INVALID');
        }
    } else if (line.value !== null || !Array.isArray(line.unavailable_reason_codes) || line.unavailable_reason_codes.length === 0) {
        fail(`${rowId}.${featureName} unavailable line is not fail-closed`, 'FACT_VALUE_INVALID');
    }
    assertArray(line.source_match_ids, `${rowId}.${featureName}.source_match_ids`);
    assertArray(line.source_identities, `${rowId}.${featureName}.source_identities`);
    assertArray(line.source_fields, `${rowId}.${featureName}.source_fields`);
    assertSha(line.provenance_digest, `${rowId}.${featureName}.provenance_digest`);
    assertObject(line.cutoff_proof, `${rowId}.${featureName}.cutoff_proof`);
    if (
        line.cutoff_proof.passed !== true ||
        line.cutoff_proof.relation !== FRAME_CUTOFF_RELATION ||
        line.cutoff_proof.target_cutoff !== targetKickoff
    ) {
        fail(`${rowId}.${featureName} cutoff proof is invalid`, 'CUTOFF_VIOLATION');
    }
    const identityIds = line.source_identities.map(identity => identity.canonical_match_id);
    if (stableStringify(identityIds) !== stableStringify(line.source_match_ids)) {
        fail(`${rowId}.${featureName} source identity binding mismatch`, 'PROVENANCE_INVALID');
    }
    if (new Set(line.source_match_ids).size !== line.source_match_ids.length) {
        fail(`${rowId}.${featureName} contains duplicate source IDs`, 'PROVENANCE_INVALID');
    }
    for (const identity of line.source_identities) {
        assertObject(identity, `${rowId}.${featureName}.source_identity`);
        assertText(identity.canonical_match_id, `${rowId}.${featureName}.source_identity.canonical_match_id`);
        assertText(identity.kickoff_at, `${rowId}.${featureName}.source_identity.kickoff_at`);
        if (!(Date.parse(identity.kickoff_at) < Date.parse(targetKickoff))) {
            fail(`${rowId}.${featureName} has future source identity`, 'CUTOFF_VIOLATION');
        }
    }
    if (line.source_match_ids.includes(rowId)) {
        fail(`${rowId}.${featureName} depends on target match`, 'TARGET_MATCH_DEPENDENCY');
    }
}

function validateTargetLabel(label, rowId) {
    assertObject(label, `${rowId}.target_label`);
    if (label.role !== 'TRAINING_LABEL_POSTMATCH' || label.timing_class !== 'POSTMATCH_ONLY') {
        fail(`${rowId}.target_label timing is invalid`, 'TEMPORAL_SEMANTICS_UNPROVEN');
    }
    if (label.canonical_match_id !== rowId || !['AVAILABLE', 'UNAVAILABLE'].includes(label.status)) {
        fail(`${rowId}.target_label identity/status is invalid`, 'PROVENANCE_INVALID');
    }
    assertSha(label.provenance_digest, `${rowId}.target_label.provenance_digest`);
    assertObject(label.source_fact_binding, `${rowId}.target_label.source_fact_binding`);
}

function validateFeatureDecisions(decisions, orderedFeatures, acceptedFeatures) {
    assertArray(decisions, 'feature_decisions');
    if (decisions.length !== orderedFeatures.length) fail('feature decision coverage is incomplete', 'SCHEMA_MISMATCH');
    const seen = new Set();
    const accepted = [];
    for (const [index, decision] of decisions.entries()) {
        assertObject(decision, `feature_decisions[${index}]`);
        assertText(decision.feature_name, `feature_decisions[${index}].feature_name`);
        if (decision.feature_name !== orderedFeatures[index] || seen.has(decision.feature_name)) {
            fail('feature decision order does not match contract', 'SCHEMA_MISMATCH');
        }
        if (!TRAINING_DECISIONS.has(decision.final_decision)) {
            fail(`feature decision ${decision.feature_name} is not classified`, 'SCHEMA_MISMATCH');
        }
        if (decision.final_decision === 'ACCEPTED_FOR_TRAINING') accepted.push(decision.feature_name);
        seen.add(decision.feature_name);
    }
    if (stableStringify(accepted) !== stableStringify(acceptedFeatures)) {
        fail('accepted feature order does not match feature decisions', 'SCHEMA_MISMATCH');
    }
}

function projectFrameArtifact({
    priorStateArtifact,
    priorStateArtifactSha256,
    priorStateReceipt,
    priorStateReceiptSha256,
    featureContractBinding,
    vNextContract,
    runtimeSemanticEngineBinding,
}) {
    assertObject(priorStateArtifact, 'GD-A03 artifact');
    assertObject(priorStateReceipt, 'GD-A03 receipt');
    assertObject(featureContractBinding, 'feature contract binding');
    assertObject(vNextContract, 'V-next feature contract');
    assertObject(runtimeSemanticEngineBinding, 'runtime semantic engine binding');
    assertSha(priorStateArtifactSha256, 'GD-A03 artifact SHA');
    assertSha(priorStateReceiptSha256, 'GD-A03 receipt SHA');
    assertSha(featureContractBinding.sha256, 'feature contract SHA');
    assertSha(runtimeSemanticEngineBinding.sha256, 'runtime semantic engine SHA');
    if (
        vNextContract.contract_id !== FRAME_CONTRACT_ID ||
        vNextContract.feature_contract_version !== FRAME_CONTRACT_VERSION ||
        vNextContract.activation_status !== 'DEFINED_NOT_ACTIVATED'
    ) {
        fail('V-next contract identity or activation boundary is invalid', 'CONTRACT_MISMATCH');
    }
    const orderedFeatures = [...vNextContract.ordered_features];
    const statusByName = new Map(vNextContract.feature_statuses.map(status => [status.feature_name, status]));
    if (statusByName.size !== orderedFeatures.length) fail('V-next status matrix is incomplete', 'SCHEMA_MISMATCH');
    const acceptedFeatures = vNextContract.feature_statuses
        .filter(status => status.training_decision === 'ACCEPTED_FOR_TRAINING')
        .map(status => status.feature_name);
    if (acceptedFeatures.length === 0) fail('V-next has no accepted feature', 'CONTRACT_MISMATCH');
    if (acceptedFeatures.some(featureName => !priorStateArtifact.feature_contract.ordered_features.includes(featureName))) {
        fail('accepted V-next feature is absent from GD-A03 source artifact', 'CONTRACT_MISMATCH');
    }
    const semanticsByName = new Map(
        priorStateArtifact.feature_semantics.map(definition => [definition.feature_name, definition])
    );
    const featureDecisions = vNextContract.feature_statuses.map(status => {
        const semantic = semanticsByName.get(status.feature_name);
        return {
            feature_name: status.feature_name,
            intended_semantics: semantic?.intended_semantics || 'V-next semantic definition is pending source closure.',
            historical_source_proven: status.historical_source_status,
            runtime_value_proven: status.runtime_source_status,
            point_in_time_safe: 'KICKOFF_EXCLUSIVE_PROVEN_FOR_FRAME',
            train_runtime_parity:
                status.training_decision === 'ACCEPTED_FOR_TRAINING'
                    ? 'PROVEN_TYPED_CONTEXT_ENGINE_FIXTURE'
                    : 'NOT_PROVEN',
            missing_policy: semantic?.missing_history_policy || status.reason_code,
            final_decision: status.training_decision,
            reason_code: status.reason_code,
        };
    });
    validateFeatureDecisions(featureDecisions, orderedFeatures, acceptedFeatures);

    const rows = priorStateArtifact.rows.map(sourceRow => {
        const acceptedLineSource = sourceRow.features;
        const features = Object.fromEntries(
            acceptedFeatures.map(featureName => [
                featureName,
                bindSourceLine(sourceRow.canonical_match_id, featureName, acceptedLineSource[featureName]),
            ])
        );
        const label = clone(sourceRow.target_label);
        const labelAvailable = label.status === 'AVAILABLE';
        const allFeaturesAvailable = acceptedFeatures.every(
            featureName =>
                features[featureName].availability_status === 'AVAILABLE' &&
                Number.isFinite(features[featureName].value)
        );
        const eligibility = allFeaturesAvailable && labelAvailable;
        return {
            canonical_match_id: sourceRow.canonical_match_id,
            target_match_identity: {
                canonical_match_id: sourceRow.canonical_match_id,
                home_team: sourceRow.home_team,
                away_team: sourceRow.away_team,
            },
            target_kickoff_utc: sourceRow.target_kickoff,
            feature_as_of_utc: sourceRow.target_kickoff,
            feature_as_of_status: FRAME_AS_OF_STATUS,
            model_decision_time_utc: null,
            model_decision_time_status: FRAME_DECISION_TIME_STATUS,
            feature_cutoff_policy: FRAME_CUTOFF_POLICY,
            feature_cutoff_relation: FRAME_CUTOFF_RELATION,
            features,
            target_label: label,
            training_eligibility: {
                status: eligibility ? 'ELIGIBLE' : 'INELIGIBLE',
                reason_codes: eligibility
                    ? []
                    : [
                          ...acceptedFeatures
                              .filter(featureName => features[featureName].availability_status !== 'AVAILABLE')
                              .map(featureName => `FEATURE_UNAVAILABLE:${featureName}`),
                          ...(labelAvailable ? [] : ['TARGET_LABEL_UNAVAILABLE']),
                      ],
            },
        };
    });
    const trainingEligible = rows.filter(row => row.training_eligibility.status === 'ELIGIBLE').length;
    const trainingIneligible = rows.length - trainingEligible;
    const rowIds = rows.map(row => row.canonical_match_id);
    const targetIdHash = admittedIdSetHash(rowIds);
    const targetMatchFactDependencyCount = rows.reduce(
        (count, row) =>
            count + acceptedFeatures.filter(featureName => row.features[featureName].source_match_ids.includes(row.canonical_match_id)).length,
        0
    );
    const futureDependencyCount = rows.reduce(
        (count, row) =>
            count +
                acceptedFeatures.reduce(
                    (featureCount, featureName) =>
                        featureCount +
                        row.features[featureName].source_identities.filter(
                            identity => Date.parse(identity.kickoff_at) >= Date.parse(row.feature_as_of_utc)
                        ).length,
                    0
                ),
        0
    );
    const fabricatedValueCount = rows.reduce(
        (count, row) =>
            count +
                acceptedFeatures.filter(
                    featureName =>
                        !['AVAILABLE', 'UNAVAILABLE'].includes(row.features[featureName].availability_status) ||
                        (row.features[featureName].availability_status === 'AVAILABLE' &&
                            !Number.isFinite(row.features[featureName].value)) ||
                        (row.features[featureName].availability_status === 'UNAVAILABLE' &&
                            row.features[featureName].value !== null)
                ).length,
        0
    );
    const featureAvailability = acceptedFeatures.map(featureName => ({
        feature_name: featureName,
        available_count: rows.filter(row => row.features[featureName].availability_status === 'AVAILABLE').length,
        unavailable_count: rows.filter(row => row.features[featureName].availability_status === 'UNAVAILABLE').length,
    }));
    const artifact = {
        schema_version: FRAME_SCHEMA_VERSION,
        stage: FRAME_STAGE,
        artifact_kind: 'canonical_prematch_training_feature_frame',
        feature_contract: {
            contract_id: FRAME_CONTRACT_ID,
            feature_contract_version: FRAME_CONTRACT_VERSION,
            registry_feature_count: orderedFeatures.length,
            training_feature_count: acceptedFeatures.length,
            ordered_features: orderedFeatures,
            training_feature_order: acceptedFeatures,
        },
        feature_decisions: featureDecisions,
        feature_cutoff_policy: FRAME_CUTOFF_POLICY,
        feature_cutoff_relation: FRAME_CUTOFF_RELATION,
        feature_as_of_status: FRAME_AS_OF_STATUS,
        model_decision_time_status: FRAME_DECISION_TIME_STATUS,
        point_in_time_policy: 'KICKOFF_EXCLUSIVE_HISTORICAL_REFERENCE_ONLY; NO_T-24H_OR_T-1H_AVAILABILITY_CLAIM',
        feature_availability: featureAvailability,
        population_authority: {
            schema_version: 'canonical-prematch-frame-population/v1',
            source_binding: 'gd_a03_artifact.population_authority',
            target_id_set_sha256: targetIdHash,
            target_population_count: rows.length,
        },
        population_accounting: {
            target_population: rows.length,
            rows_accounted: rows.length,
            training_eligible: trainingEligible,
            training_ineligible: trainingIneligible,
            unaccounted: 0,
            duplicate: 0,
            extra: 0,
            target_id_set_sha256: targetIdHash,
            accounted_id_set_sha256: targetIdHash,
        },
        source_bindings: {
            gd_a03_artifact: {
                sha256: priorStateArtifactSha256,
                business_hash: priorStateArtifact.business_content_sha256,
                schema_version: priorStateArtifact.schema_version,
            },
            gd_a03_receipt: {
                sha256: priorStateReceiptSha256,
                business_hash: priorStateReceipt.output_business_sha256,
                schema_version: priorStateReceipt.schema_version,
            },
            feature_contract: {
                sha256: featureContractBinding.sha256,
                schema_version: featureContractBinding.registrySchemaVersion,
                contract_id: FRAME_CONTRACT_ID,
                feature_contract_version: FRAME_CONTRACT_VERSION,
            },
            runtime_semantic_engine: {
                sha256: runtimeSemanticEngineBinding.sha256,
                implementation_id: 'canonical-prematch-feature-engine',
                implementation_version: 'v1',
                source_path: 'src/ml/inference/canonical_prematch_feature_engine.py',
            },
        },
        runtime_parity: {
            status: 'PROVEN_TYPED_CONTEXT_ENGINE_FIXTURE',
            historical_producer: 'GD-A03 prior-state feature lines under kickoff-exclusive policy',
            runtime_producer: 'canonical-prematch-feature-engine/v1',
            numeric_parity_test: 'REPOSITORY_TEST_REQUIRED_AND_SCOPED_TO_TYPED_CONTEXT',
            features: acceptedFeatures,
            failures: [],
        },
        validation_counters: {
            target_match_fact_dependency_count: targetMatchFactDependencyCount,
            future_match_dependency_count: futureDependencyCount,
            cutoff_violation_count: futureDependencyCount,
            fabricated_value_count: fabricatedValueCount,
            label_feature_dependency_count: 0,
        },
        feature_frame_readiness: FRAME_READINESS.feature_frame_readiness,
        real_training_readiness: FRAME_READINESS.real_training_readiness,
        strict_decision_time_value_evaluation: FRAME_READINESS.strict_decision_time_value_evaluation,
        golden_dataset_complete: FRAME_READINESS.golden_dataset_complete,
        training_execution_authorized: FRAME_READINESS.training_execution_authorized,
        rows,
        business_content_sha256: null,
    };
    artifact.business_content_sha256 = computeFrameBusinessHash(artifact);
    return artifact;
}

function validateFrameArtifact(artifact) {
    assertObject(artifact, 'canonical prematch frame artifact');
    if (
        artifact.schema_version !== FRAME_SCHEMA_VERSION ||
        artifact.stage !== FRAME_STAGE ||
        artifact.artifact_kind !== 'canonical_prematch_training_feature_frame'
    ) {
        fail('canonical prematch frame identity is invalid', 'SCHEMA_MISMATCH');
    }
    if (
        artifact.feature_cutoff_policy !== FRAME_CUTOFF_POLICY ||
        artifact.feature_cutoff_relation !== FRAME_CUTOFF_RELATION ||
        artifact.feature_as_of_status !== FRAME_AS_OF_STATUS ||
        artifact.model_decision_time_status !== FRAME_DECISION_TIME_STATUS
    ) {
        fail('canonical prematch frame temporal boundary is invalid', 'TEMPORAL_SEMANTICS_UNPROVEN');
    }
    if (artifact.feature_frame_readiness !== 'READY' || artifact.real_training_readiness !== 'READY') {
        fail('canonical prematch frame readiness is not READY', 'READINESS_BOUNDARY');
    }
    if (
        artifact.strict_decision_time_value_evaluation !== 'NOT_READY' ||
        artifact.golden_dataset_complete !== false ||
        artifact.training_execution_authorized !== false
    ) {
        fail('canonical prematch frame readiness boundary was widened', 'READINESS_BOUNDARY');
    }
    assertObject(artifact.feature_contract, 'feature_contract');
    if (
        artifact.feature_contract.contract_id !== FRAME_CONTRACT_ID ||
        artifact.feature_contract.feature_contract_version !== FRAME_CONTRACT_VERSION ||
        artifact.feature_contract.training_feature_count !== artifact.feature_contract.training_feature_order.length ||
        artifact.feature_contract.registry_feature_count !== artifact.feature_contract.ordered_features.length
    ) {
        fail('canonical prematch frame contract binding is invalid', 'CONTRACT_MISMATCH');
    }
    const orderedFeatures = artifact.feature_contract.ordered_features;
    const acceptedFeatures = artifact.feature_contract.training_feature_order;
    validateFeatureDecisions(artifact.feature_decisions, orderedFeatures, acceptedFeatures);
    assertArray(artifact.rows, 'rows');
    const ids = new Set();
    let eligible = 0;
    let targetMatchDependencies = 0;
    let futureDependencies = 0;
    let fabricated = 0;
    for (const row of artifact.rows) {
        assertObject(row, 'frame row');
        const rowId = assertText(row.canonical_match_id, 'frame row.canonical_match_id');
        if (ids.has(rowId)) fail(`duplicate frame row ${rowId}`, 'POPULATION_MISMATCH');
        ids.add(rowId);
        assertObject(row.target_match_identity, `${rowId}.target_match_identity`);
        if (
            row.target_match_identity.canonical_match_id !== rowId ||
            !assertText(row.target_match_identity.home_team, `${rowId}.target_match_identity.home_team`) ||
            !assertText(row.target_match_identity.away_team, `${rowId}.target_match_identity.away_team`)
        ) {
            fail(`${rowId} target identity is invalid`, 'PROVENANCE_INVALID');
        }
        assertText(row.target_kickoff_utc, `${rowId}.target_kickoff_utc`);
        if (row.feature_as_of_utc !== row.target_kickoff_utc || row.model_decision_time_utc !== null) {
            fail(`${rowId} as-of boundary is invalid`, 'TEMPORAL_SEMANTICS_UNPROVEN');
        }
        if (
            row.feature_as_of_status !== FRAME_AS_OF_STATUS ||
            row.model_decision_time_status !== FRAME_DECISION_TIME_STATUS ||
            row.feature_cutoff_policy !== FRAME_CUTOFF_POLICY ||
            row.feature_cutoff_relation !== FRAME_CUTOFF_RELATION
        ) {
            fail(`${rowId} temporal metadata is invalid`, 'TEMPORAL_SEMANTICS_UNPROVEN');
        }
        assertObject(row.features, `${rowId}.features`);
        if (stableStringify(Object.keys(row.features)) !== stableStringify(acceptedFeatures)) {
            fail(`${rowId} feature order does not match training contract`, 'SCHEMA_MISMATCH');
        }
        for (const featureName of acceptedFeatures) {
            validateSourceLine(rowId, featureName, row.features[featureName], row.target_kickoff_utc);
            if (row.features[featureName].source_match_ids.includes(rowId)) targetMatchDependencies += 1;
            if (
                row.features[featureName].source_identities.some(
                    identity => Date.parse(identity.kickoff_at) >= Date.parse(row.feature_as_of_utc)
                )
            ) {
                futureDependencies += 1;
            }
            if (
                row.features[featureName].availability_status === 'AVAILABLE' &&
                !Number.isFinite(row.features[featureName].value)
            ) fabricated += 1;
            if (
                row.features[featureName].availability_status === 'UNAVAILABLE' &&
                row.features[featureName].value !== null
            ) fabricated += 1;
        }
        validateTargetLabel(row.target_label, rowId);
        assertObject(row.training_eligibility, `${rowId}.training_eligibility`);
        const expectedEligible =
            row.target_label.status === 'AVAILABLE' &&
            acceptedFeatures.every(
                featureName =>
                    row.features[featureName].availability_status === 'AVAILABLE' &&
                    Number.isFinite(row.features[featureName].value)
            );
        if ((row.training_eligibility.status === 'ELIGIBLE') !== expectedEligible) {
            fail(`${rowId} training eligibility disagrees with values`, 'POPULATION_MISMATCH');
        }
        if (expectedEligible) eligible += 1;
    }
    const population = artifact.population_accounting;
    assertObject(population, 'population_accounting');
    if (
        population.target_population !== artifact.rows.length ||
        population.rows_accounted !== artifact.rows.length ||
        population.training_eligible !== eligible ||
        population.training_ineligible !== artifact.rows.length - eligible ||
        population.unaccounted !== 0 ||
        population.duplicate !== 0 ||
        population.extra !== 0
    ) {
        fail('frame population accounting does not reconcile', 'POPULATION_MISMATCH');
    }
    assertSha(population.target_id_set_sha256, 'population target ID hash');
    assertSha(population.accounted_id_set_sha256, 'population accounted ID hash');
    const idHash = admittedIdSetHash([...ids]);
    if (population.target_id_set_sha256 !== idHash || population.accounted_id_set_sha256 !== idHash) {
        fail('frame population ID hash mismatch', 'POPULATION_MISMATCH');
    }
    assertObject(artifact.population_authority, 'population_authority');
    if (
        artifact.population_authority.target_id_set_sha256 !== idHash ||
        artifact.population_authority.target_population_count !== artifact.rows.length
    ) {
        fail('frame population authority mismatch', 'POPULATION_MISMATCH');
    }
    assertObject(artifact.validation_counters, 'validation_counters');
    if (
        artifact.validation_counters.target_match_fact_dependency_count !== targetMatchDependencies ||
        artifact.validation_counters.future_match_dependency_count !== futureDependencies ||
        artifact.validation_counters.cutoff_violation_count !== futureDependencies ||
        artifact.validation_counters.fabricated_value_count !== fabricated ||
        artifact.validation_counters.label_feature_dependency_count !== 0
    ) {
        fail('frame validation counters do not reconcile', 'SCHEMA_MISMATCH');
    }
    if (targetMatchDependencies !== 0 || futureDependencies !== 0 || fabricated !== 0) {
        fail('frame contains leakage or fabricated values', 'LEAKAGE_BOUNDARY');
    }
    assertSha(artifact.business_content_sha256, 'frame business hash');
    if (artifact.business_content_sha256 !== computeFrameBusinessHash(artifact)) {
        fail('frame business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    return artifact;
}

function validateFrameReceipt(receipt, artifactBytes, artifact) {
    assertObject(receipt, 'canonical prematch frame receipt');
    if (receipt.schema_version !== FRAME_RECEIPT_SCHEMA_VERSION || receipt.stage !== FRAME_STAGE) {
        fail('frame receipt identity is invalid', 'SCHEMA_MISMATCH');
    }
    assertFullSha(receipt.code_revision, 'frame receipt code_revision');
    if (receipt.artifact_sha256 !== sha256Bytes(artifactBytes)) {
        fail('frame receipt artifact hash mismatch', 'ARTIFACT_HASH_MISMATCH');
    }
    if (receipt.output_business_sha256 !== artifact.business_content_sha256) {
        fail('frame receipt business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    assertSha(receipt.receipt_content_sha256, 'frame receipt content hash');
    if (receipt.receipt_content_sha256 !== computeFrameReceiptHash(receipt)) {
        fail('frame receipt content hash mismatch', 'RECEIPT_HASH_MISMATCH');
    }
    for (const field of Object.keys(FRAME_READINESS)) {
        if (receipt[field] !== artifact[field] || receipt[field] !== FRAME_READINESS[field]) {
            fail(`frame receipt readiness ${field} mismatch`, 'READINESS_BOUNDARY');
        }
    }
    if (
        receipt.offline !== true ||
        receipt.file_first !== true ||
        receipt.live_fetch !== 0 ||
        receipt.db_writes !== 0 ||
        receipt.raw_writes !== 0 ||
        receipt.training_runs !== 0 ||
        receipt.backtest_runs !== 0 ||
        receipt.model_activations !== 0
    ) {
        fail('frame receipt side-effect boundary was widened', 'SAFETY_BOUNDARY');
    }
    if (
        receipt.target_population !== artifact.population_accounting.target_population ||
        receipt.rows_accounted !== artifact.population_accounting.rows_accounted ||
        receipt.training_eligible !== artifact.population_accounting.training_eligible ||
        receipt.training_ineligible !== artifact.population_accounting.training_ineligible ||
        receipt.unaccounted !== artifact.population_accounting.unaccounted ||
        receipt.duplicate !== artifact.population_accounting.duplicate ||
        receipt.extra !== artifact.population_accounting.extra
    ) {
        fail('frame receipt population mismatch', 'POPULATION_MISMATCH');
    }
    if (stableStringify(receipt.source_bindings) !== stableStringify(artifact.source_bindings)) {
        fail('frame receipt source binding mismatch', 'PROVENANCE_INVALID');
    }
    if (stableStringify(receipt.population_authority) !== stableStringify(artifact.population_authority)) {
        fail('frame receipt population authority mismatch', 'POPULATION_MISMATCH');
    }
    return receipt;
}

function buildFrameOutput({
    priorStateArtifact,
    priorStateArtifactBytes,
    priorStateReceipt,
    priorStateReceiptBytes,
    featureContractBinding,
    vNextContract,
    runtimeSemanticEngineBinding,
    codeRevision,
}) {
    const artifact = projectFrameArtifact({
        priorStateArtifact,
        priorStateArtifactSha256: sha256Bytes(priorStateArtifactBytes),
        priorStateReceipt,
        priorStateReceiptSha256: sha256Bytes(priorStateReceiptBytes),
        featureContractBinding,
        vNextContract,
        runtimeSemanticEngineBinding,
    });
    const artifactBytes = Buffer.from(`${JSON.stringify(artifact, null, 2)}\n`, 'utf8');
    const receipt = {
        schema_version: FRAME_RECEIPT_SCHEMA_VERSION,
        stage: FRAME_STAGE,
        code_revision: codeRevision,
        artifact_sha256: sha256Bytes(artifactBytes),
        output_business_sha256: artifact.business_content_sha256,
        receipt_content_sha256: null,
        target_population: artifact.population_accounting.target_population,
        rows_accounted: artifact.population_accounting.rows_accounted,
        training_eligible: artifact.population_accounting.training_eligible,
        training_ineligible: artifact.population_accounting.training_ineligible,
        unaccounted: artifact.population_accounting.unaccounted,
        duplicate: artifact.population_accounting.duplicate,
        extra: artifact.population_accounting.extra,
        feature_frame_readiness: artifact.feature_frame_readiness,
        real_training_readiness: artifact.real_training_readiness,
        strict_decision_time_value_evaluation: artifact.strict_decision_time_value_evaluation,
        golden_dataset_complete: artifact.golden_dataset_complete,
        training_execution_authorized: artifact.training_execution_authorized,
        offline: true,
        file_first: true,
        live_fetch: 0,
        db_writes: 0,
        raw_writes: 0,
        training_runs: 0,
        backtest_runs: 0,
        model_activations: 0,
        source_bindings: artifact.source_bindings,
        population_authority: artifact.population_authority,
    };
    receipt.receipt_content_sha256 = computeFrameReceiptHash(receipt);
    const receiptBytes = Buffer.from(`${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
    validateFrameOutputFiles(artifactBytes, receiptBytes);
    return { artifact, receipt, artifactBytes, receiptBytes };
}

function validateFrameOutputFiles(artifactBytes, receiptBytes) {
    let artifact;
    let receipt;
    try {
        artifact = JSON.parse(Buffer.from(artifactBytes).toString('utf8'));
        receipt = JSON.parse(Buffer.from(receiptBytes).toString('utf8'));
    } catch (error) {
        fail(`frame output is not valid JSON: ${error.message}`, 'SCHEMA_MISMATCH');
    }
    validateFrameArtifact(artifact);
    validateFrameReceipt(receipt, artifactBytes, artifact);
    return { artifact, receipt };
}

module.exports = {
    FRAME_CONTRACT_ID,
    FRAME_CONTRACT_VERSION,
    FRAME_CUTOFF_POLICY,
    FRAME_CUTOFF_RELATION,
    FRAME_DECISION_TIME_STATUS,
    FRAME_RECEIPT_SCHEMA_VERSION,
    FRAME_SCHEMA_VERSION,
    FRAME_STAGE,
    CanonicalPrematchFeatureFrameError,
    buildFrameOutput,
    computeFrameBusinessHash,
    computeFrameReceiptHash,
    projectFrameArtifact,
    sourceLineBindingDigest,
    validateFrameArtifact,
    validateFrameOutputFiles,
};
