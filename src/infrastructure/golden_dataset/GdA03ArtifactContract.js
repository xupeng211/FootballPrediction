'use strict';

// lifecycle: permanent
// GD-A03 artifact/receipt verifier。它只验证已经构建的 file-first projection：
// schema、strict cutoff、lineage digest、population accounting、safety flags 与
// byte/business hashes。上游 GD-A01/GD-A02/source file 的绑定由 GD-A03 CLI 校验。

const {
    FEATURE_AVAILABILITY,
    FEATURE_CUTOFF_POLICY,
    FEATURE_CUTOFF_RELATION,
    GdA03ContractError,
    PRIOR_STATE_ARTIFACT_SCHEMA_VERSION,
    PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
    PRIOR_STATE_RECEIPT_SCHEMA_VERSION,
    PRIOR_STATE_STAGE,
    assertFiniteNumber,
    assertObject,
    assertSha,
    assertText,
    computeBusinessHash,
    computeProvenanceDigest,
    featureSemanticsInOrder,
    REQUIRED_ROLLING_HISTORY_COUNT,
    stableStringify,
    validateFeatureContract,
} = require('./GdA03PriorStateContract');
const { sha256Bytes } = require('./GdA01AssemblyContract');

const TRAINING_LABEL_ROLE = 'TRAINING_LABEL_POSTMATCH';
const FACT_TIMING_CLASS = 'POSTMATCH_ONLY';

function fail(message, code = 'GD_A03_CONTRACT_INVALID') {
    throw new GdA03ContractError(message, code);
}

function assertArray(value, label) {
    if (!Array.isArray(value)) fail(`${label} must be an array`, 'SCHEMA_MISMATCH');
    return value;
}

function validateSourceBindings(sourceBindings) {
    assertObject(sourceBindings, 'GD-A03 source_bindings');
    for (const [name, binding] of Object.entries(sourceBindings)) {
        assertObject(binding, `GD-A03 source_bindings.${name}`);
        if (binding.sha256 !== undefined) assertSha(binding.sha256, `GD-A03 source_bindings.${name}.sha256`);
        if (binding.business_hash !== undefined) {
            assertSha(binding.business_hash, `GD-A03 source_bindings.${name}.business_hash`);
        }
    }
    return sourceBindings;
}

// eslint-disable-next-line complexity -- fail-closed validation keeps all lineage invariants visible together.
function validateLineageLine(line, featureName, row) {
    assertObject(line, `${row.canonical_match_id}.${featureName}`);
    if (!Object.values(FEATURE_AVAILABILITY).includes(line.availability_status)) {
        fail(`${featureName} availability status is invalid`, 'SCHEMA_MISMATCH');
    }
    if (line.value !== null) assertFiniteNumber(line.value, `${featureName}.value`);
    if (line.availability_status === FEATURE_AVAILABILITY.AVAILABLE && line.value === null) {
        fail(`${featureName} available line is null`, 'FACT_VALUE_INVALID');
    }
    if (line.availability_status === FEATURE_AVAILABILITY.UNAVAILABLE && line.value !== null) {
        fail(`${featureName} unavailable line carries a value`, 'FACT_VALUE_INVALID');
    }
    assertArray(line.source_match_ids, `${featureName}.source_match_ids`);
    assertArray(line.source_identities, `${featureName}.source_identities`);
    assertArray(line.source_evidence_match_ids, `${featureName}.source_evidence_match_ids`);
    assertArray(line.provenance_inputs, `${featureName}.provenance_inputs`);
    if (line.latest_source_kickoff !== null) {
        assertText(line.latest_source_kickoff, `${featureName}.latest_source_kickoff`);
    }
    assertText(line.derivation_contract, `${featureName}.derivation_contract`);
    assertArray(line.source_fields, `${featureName}.source_fields`);
    assertObject(line.cutoff_proof, `${featureName}.cutoff_proof`);
    if (line.cutoff_proof.relation !== FEATURE_CUTOFF_RELATION || line.cutoff_proof.passed !== true) {
        fail(`${featureName} cutoff proof is not strict`, 'CUTOFF_VIOLATION');
    }
    if (line.cutoff_proof.target_cutoff !== row.feature_cutoff_time) {
        fail(`${featureName} cutoff target mismatch`, 'CUTOFF_VIOLATION');
    }
    if (line.cutoff_proof.max_source_time !== line.latest_source_kickoff) {
        fail(`${featureName} latest source mismatch`, 'CUTOFF_VIOLATION');
    }
    if (
        line.latest_source_kickoff !== null &&
        !(Date.parse(line.latest_source_kickoff) < Date.parse(row.feature_cutoff_time))
    ) {
        fail(`${featureName} source time is not strictly prior`, 'CUTOFF_VIOLATION');
    }
    assertSha(line.provenance_digest, `${featureName}.provenance_digest`);
    assertArray(line.unavailable_reason_codes, `${featureName}.unavailable_reason_codes`);
    if (line.availability_status === FEATURE_AVAILABILITY.UNAVAILABLE && line.unavailable_reason_codes.length === 0) {
        fail(`${featureName} unavailable line has no reason`, 'SCHEMA_MISMATCH');
    }
    const sourceIds = line.source_identities.map(identity => identity.canonical_match_id);
    if (stableStringify(sourceIds) !== stableStringify(line.source_match_ids)) {
        fail(`${featureName} source identity IDs mismatch`, 'PROVENANCE_INVALID');
    }
    if (line.source_match_ids.length !== new Set(line.source_match_ids).size) {
        fail(`${featureName} has duplicate source IDs`, 'PROVENANCE_INVALID');
    }
    if (line.source_evidence_match_ids.some(sourceId => !line.source_match_ids.includes(sourceId))) {
        fail(`${featureName} evidence ID is not in source ID set`, 'PROVENANCE_INVALID');
    }
    if (line.source_evidence_match_ids.length !== new Set(line.source_evidence_match_ids).size) {
        fail(`${featureName} has duplicate evidence IDs`, 'PROVENANCE_INVALID');
    }
    const derivation = line.derivation_contract.split(':').slice(1).join(':');
    const expectedProvenanceDigest = computeProvenanceDigest({
        lineage_contract_version: PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
        feature_name: featureName,
        target_match_id: row.canonical_match_id,
        target_cutoff: row.feature_cutoff_time,
        source_match_ids: line.source_match_ids,
        source_evidence_match_ids: line.source_evidence_match_ids,
        source_fields: line.source_fields,
        source_projections: line.provenance_inputs,
        derivation,
        unavailable_reason_codes: line.unavailable_reason_codes,
    });
    if (line.provenance_digest !== expectedProvenanceDigest) {
        fail(`${featureName} provenance digest mismatch`, 'PROVENANCE_INVALID');
    }
    let latest = null;
    for (const identity of line.source_identities) {
        assertText(identity.canonical_match_id, `${featureName}.source_identity.canonical_match_id`);
        assertText(identity.kickoff_at, `${featureName}.source_identity.kickoff_at`);
        if (!(Date.parse(identity.kickoff_at) < Date.parse(row.feature_cutoff_time))) {
            fail(`${featureName} source identity violates cutoff`, 'CUTOFF_VIOLATION');
        }
        if (latest === null || Date.parse(identity.kickoff_at) > Date.parse(latest)) latest = identity.kickoff_at;
    }
    if (latest !== line.latest_source_kickoff) {
        fail(`${featureName} latest source cannot be recomputed`, 'PROVENANCE_INVALID');
    }
}

// eslint-disable-next-line complexity -- counters intentionally enumerate each safety invariant.
function computeArtifactCounters(artifact) {
    let targetMatch = 0;
    let future = 0;
    let cutoff = 0;
    let fabricated = 0;
    let silentGap = 0;
    for (const row of artifact.rows) {
        for (const [featureName, line] of Object.entries(row.features)) {
            if (line.source_match_ids.includes(row.canonical_match_id)) targetMatch += 1;
            if (line.value !== null && !Number.isFinite(line.value)) fabricated += 1;
            if (line.value !== null && line.unavailable_reason_codes.length > 0) fabricated += 1;
            if (line.source_match_ids.length !== new Set(line.source_match_ids).size) silentGap += 1;
            for (const identity of line.source_identities) {
                if (!(Date.parse(identity.kickoff_at) < Date.parse(row.feature_cutoff_time))) {
                    future += 1;
                    cutoff += 1;
                }
            }
            if (line.cutoff_proof.passed !== true) cutoff += 1;
            if (featureName.startsWith('rolling_') && line.source_match_ids.length === REQUIRED_ROLLING_HISTORY_COUNT) {
                if (line.value !== null && line.source_evidence_match_ids.length !== REQUIRED_ROLLING_HISTORY_COUNT) {
                    silentGap += 1;
                }
            }
        }
    }
    return {
        target_match_fact_dependency_count: targetMatch,
        future_match_dependency_count: future,
        cutoff_violation_count: cutoff,
        fabricated_value_count: fabricated,
        silent_history_gap_count: silentGap,
    };
}

function validateFeatureAvailability(artifact, featureNames) {
    assertArray(artifact.feature_availability, 'GD-A03 feature_availability');
    if (artifact.feature_availability.length !== featureNames.length) {
        fail('GD-A03 feature_availability count mismatch', 'POPULATION_MISMATCH');
    }
    for (const [index, entry] of artifact.feature_availability.entries()) {
        assertObject(entry, `GD-A03 feature_availability[${index}]`);
        if (entry.feature_name !== featureNames[index]) {
            fail('GD-A03 feature_availability order mismatch', 'SCHEMA_MISMATCH');
        }
        const available = artifact.rows.filter(
            row => row.features[entry.feature_name].availability_status === FEATURE_AVAILABILITY.AVAILABLE
        ).length;
        if (entry.available_count !== available || entry.unavailable_count !== artifact.rows.length - available) {
            fail(`GD-A03 feature_availability mismatch for ${entry.feature_name}`, 'POPULATION_MISMATCH');
        }
    }
}

function computeUnavailableReasonCounts(artifact) {
    const counts = {};
    for (const row of artifact.rows) {
        for (const line of Object.values(row.features)) {
            for (const reason of line.unavailable_reason_codes) counts[reason] = (counts[reason] || 0) + 1;
        }
    }
    return Object.fromEntries(Object.entries(counts).sort(([left], [right]) => left.localeCompare(right)));
}

// eslint-disable-next-line complexity
function validatePriorStateArtifact(artifact) {
    assertObject(artifact, 'GD-A03 artifact');
    if (artifact.schema_version !== PRIOR_STATE_ARTIFACT_SCHEMA_VERSION) {
        fail('GD-A03 artifact schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    if (artifact.stage !== PRIOR_STATE_STAGE || artifact.artifact_kind !== 'prior_state_feature_view') {
        fail('GD-A03 artifact identity is invalid', 'SCHEMA_MISMATCH');
    }
    if (
        artifact.feature_cutoff_policy !== FEATURE_CUTOFF_POLICY ||
        artifact.feature_cutoff_relation !== FEATURE_CUTOFF_RELATION
    ) {
        fail('GD-A03 cutoff policy is invalid', 'TEMPORAL_SEMANTICS_UNPROVEN');
    }
    const featureContract = validateFeatureContract(artifact.feature_contract);
    const semantics = featureSemanticsInOrder(featureContract.ordered_features);
    if (stableStringify(artifact.feature_semantics) !== stableStringify(semantics)) {
        fail('GD-A03 semantic matrix mismatch', 'SCHEMA_MISMATCH');
    }
    validateSourceBindings(artifact.source_bindings);
    assertArray(artifact.rows, 'GD-A03 rows');
    const rowIds = new Set();
    for (const row of artifact.rows) {
        assertObject(row, 'GD-A03 row');
        for (const field of [
            'canonical_match_id',
            'target_kickoff',
            'home_team',
            'away_team',
            'feature_cutoff_policy',
            'feature_cutoff_time',
        ]) {
            assertText(row[field], `GD-A03 row.${field}`);
        }
        if (row.feature_cutoff_policy !== FEATURE_CUTOFF_POLICY || row.feature_cutoff_time !== row.target_kickoff) {
            fail('GD-A03 row cutoff mismatch', 'TEMPORAL_SEMANTICS_UNPROVEN');
        }
        if (rowIds.has(row.canonical_match_id)) {
            fail(`duplicate GD-A03 row ${row.canonical_match_id}`, 'POPULATION_MISMATCH');
        }
        rowIds.add(row.canonical_match_id);
        assertObject(row.features, `GD-A03 row ${row.canonical_match_id}.features`);
        if (
            stableStringify(Object.keys(row.features).sort()) !==
            stableStringify([...featureContract.ordered_features].sort())
        ) {
            fail(`GD-A03 feature key set mismatch for ${row.canonical_match_id}`, 'SCHEMA_MISMATCH');
        }
        for (const featureName of featureContract.ordered_features) {
            validateLineageLine(row.features[featureName], featureName, row);
        }
        assertObject(row.feature_vector_eligibility, `GD-A03 row ${row.canonical_match_id}.feature_vector_eligibility`);
        if (!['YES', 'NO'].includes(row.feature_vector_eligibility.status)) {
            fail('GD-A03 row eligibility is invalid', 'SCHEMA_MISMATCH');
        }
        const expectedEligible = featureContract.ordered_features.every(
            name => row.features[name].availability_status === FEATURE_AVAILABILITY.AVAILABLE
        );
        if ((row.feature_vector_eligibility.status === 'YES') !== expectedEligible) {
            fail('GD-A03 row eligibility disagrees with features', 'POPULATION_MISMATCH');
        }
        assertObject(row.target_label, `GD-A03 row ${row.canonical_match_id}.target_label`);
        if (row.target_label.role !== TRAINING_LABEL_ROLE || row.target_label.timing_class !== FACT_TIMING_CLASS) {
            fail('GD-A03 target label timing is invalid', 'TEMPORAL_SEMANTICS_UNPROVEN');
        }
    }
    const accounting = artifact.population_accounting;
    assertObject(accounting, 'GD-A03 population_accounting');
    if (
        accounting.target_population_count !== artifact.rows.length ||
        accounting.rows_accounted !== artifact.rows.length
    ) {
        fail('GD-A03 population accounting row mismatch', 'POPULATION_MISMATCH');
    }
    if (
        accounting.feature_eligible_count !==
        artifact.rows.filter(row => row.feature_vector_eligibility.status === 'YES').length
    ) {
        fail('GD-A03 eligible accounting mismatch', 'POPULATION_MISMATCH');
    }
    if (
        accounting.feature_unavailable_count !==
        artifact.rows.filter(row => row.feature_vector_eligibility.status === 'NO').length
    ) {
        fail('GD-A03 unavailable accounting mismatch', 'POPULATION_MISMATCH');
    }
    if (accounting.unaccounted_count !== 0 || accounting.duplicate_id_count !== 0 || accounting.extra_id_count !== 0) {
        fail('GD-A03 population is not conserved', 'POPULATION_MISMATCH');
    }
    validateFeatureAvailability(artifact, featureContract.ordered_features);
    if (
        stableStringify(artifact.unavailable_reason_counts) !==
        stableStringify(computeUnavailableReasonCounts(artifact))
    ) {
        fail('GD-A03 unavailable reason counts mismatch', 'POPULATION_MISMATCH');
    }
    if (artifact.numeric_parity?.canonical_20_name_order_parity !== true) {
        fail('GD-A03 canonical feature order parity is not proven', 'SCHEMA_MISMATCH');
    }
    const expectedCounters = computeArtifactCounters(artifact);
    if (stableStringify(artifact.validation_counters) !== stableStringify(expectedCounters)) {
        fail('GD-A03 validation counters mismatch', 'SCHEMA_MISMATCH');
    }
    const computedHash = computeBusinessHash({ ...artifact, business_content_sha256: null });
    if (artifact.business_content_sha256 !== computedHash) {
        fail('GD-A03 business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    return artifact;
}

// eslint-disable-next-line complexity -- receipt validation is the single safety-boundary gate.
function validateReceipt(receipt, artifactBytes, artifact) {
    assertObject(receipt, 'GD-A03 receipt');
    if (receipt.schema_version !== PRIOR_STATE_RECEIPT_SCHEMA_VERSION || receipt.stage !== PRIOR_STATE_STAGE) {
        fail('GD-A03 receipt identity is invalid', 'SCHEMA_MISMATCH');
    }
    if (typeof receipt.code_revision !== 'string' || !/^[0-9a-f]{40}$/.test(receipt.code_revision)) {
        fail('GD-A03 receipt code revision is invalid', 'PROVENANCE_INVALID');
    }
    validateSourceBindings(receipt.source_bindings);
    if (stableStringify(receipt.source_bindings) !== stableStringify(artifact.source_bindings)) {
        fail('GD-A03 receipt source binding mismatch', 'PROVENANCE_INVALID');
    }
    if (receipt.artifact_sha256 !== sha256Bytes(artifactBytes)) {
        fail('GD-A03 receipt artifact hash mismatch', 'ARTIFACT_HASH_MISMATCH');
    }
    if (receipt.output_business_sha256 !== artifact.business_content_sha256) {
        fail('GD-A03 receipt business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    for (const field of [
        'input_target_count',
        'rows_accounted',
        'feature_eligible_count',
        'feature_unavailable_count',
        'unaccounted_count',
        'duplicate_id_count',
        'extra_id_count',
    ]) {
        if (!Number.isSafeInteger(receipt[field]) || receipt[field] < 0) {
            fail(`GD-A03 receipt ${field} is invalid`, 'SCHEMA_MISMATCH');
        }
    }
    if (
        receipt.input_target_count !== artifact.population_accounting.target_population_count ||
        receipt.rows_accounted !== artifact.population_accounting.rows_accounted ||
        receipt.feature_eligible_count !== artifact.population_accounting.feature_eligible_count ||
        receipt.feature_unavailable_count !== artifact.population_accounting.feature_unavailable_count ||
        receipt.unaccounted_count !== artifact.population_accounting.unaccounted_count ||
        receipt.duplicate_id_count !== artifact.population_accounting.duplicate_id_count ||
        receipt.extra_id_count !== artifact.population_accounting.extra_id_count
    ) {
        fail('GD-A03 receipt population mismatch', 'POPULATION_MISMATCH');
    }
    if (
        receipt.offline !== true ||
        receipt.file_first !== true ||
        receipt.live_network_requests !== 0 ||
        receipt.db_writes !== 0 ||
        receipt.db_migrations !== 0 ||
        receipt.raw_mutations !== 0 ||
        receipt.db_connections !== 0 ||
        receipt.training_runs !== 0 ||
        receipt.backtest_runs !== 0 ||
        receipt.model_activations !== 0
    ) {
        fail('GD-A03 receipt safety boundary was widened', 'SAFETY_BOUNDARY');
    }
    return receipt;
}

function validatePriorStateOutputFiles(artifactBytes, receiptBytes) {
    let artifact;
    let receipt;
    try {
        artifact = JSON.parse(Buffer.from(artifactBytes).toString('utf8'));
        receipt = JSON.parse(Buffer.from(receiptBytes).toString('utf8'));
    } catch (error) {
        fail(`GD-A03 output is not valid JSON: ${error.message}`, 'SCHEMA_MISMATCH');
    }
    const normalizedArtifact = validatePriorStateArtifact(artifact);
    validateReceipt(receipt, artifactBytes, normalizedArtifact);
    return { artifact: normalizedArtifact, receipt };
}

module.exports = {
    validatePriorStateArtifact,
    validatePriorStateOutputFiles,
};
