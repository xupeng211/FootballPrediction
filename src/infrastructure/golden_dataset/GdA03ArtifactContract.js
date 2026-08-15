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
    computeReceiptHash,
    computeProvenanceDigest,
    featureSemanticsInOrder,
    GD_A03_SOURCE_BINDING_NAMES,
    isSemanticsProven,
    REQUIRED_ROLLING_HISTORY_COUNT,
    SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION,
    SCHEDULE_AWAY_FIXTURES_PER_TEAM,
    SCHEDULE_FIXTURES_PER_TEAM,
    SCHEDULE_HOME_FIXTURES_PER_TEAM,
    SCHEDULE_TEAMS_PER_SEASON,
    stableStringify,
    validateFeatureContract,
} = require('./GdA03PriorStateContract');
const { admittedIdSetHash, sha256Bytes } = require('./GdA01AssemblyContract');

const TRAINING_LABEL_ROLE = 'TRAINING_LABEL_POSTMATCH';
const FACT_TIMING_CLASS = 'POSTMATCH_ONLY';
const READINESS_CONTRACT = Object.freeze({
    feature_frame_readiness: 'NOT_READY',
    real_training_readiness: 'NOT_READY',
    training_execution_authorized: false,
    strict_decision_time_value_evaluation: 'NOT_READY',
    golden_dataset_complete: false,
});
const SOURCE_BINDING_FIELDS = Object.freeze({
    canonical_schedule: ['sha256', 'business_hash', 'schema_version'],
    feature_contract: ['sha256', 'schema_version'],
    gd_a01_artifact: ['sha256', 'business_hash', 'schema_version'],
    gd_a01_receipt: ['sha256', 'business_hash', 'schema_version'],
    gd_a02_artifact: ['sha256', 'business_hash', 'schema_version'],
    gd_a02_receipt: ['sha256', 'business_hash', 'schema_version'],
    runtime_feature_adapter: ['sha256', 'schema_version', 'ordered_features'],
});

function fail(message, code = 'GD_A03_CONTRACT_INVALID') {
    throw new GdA03ContractError(message, code);
}

function assertArray(value, label) {
    if (!Array.isArray(value)) fail(`${label} must be an array`, 'SCHEMA_MISMATCH');
    return value;
}

function validateSourceBindings(sourceBindings) {
    assertObject(sourceBindings, 'GD-A03 source_bindings');
    const actualNames = Object.keys(sourceBindings).sort();
    const expectedNames = [...GD_A03_SOURCE_BINDING_NAMES].sort();
    if (stableStringify(actualNames) !== stableStringify(expectedNames)) {
        fail('GD-A03 source_bindings must contain the complete canonical authority set', 'PROVENANCE_INVALID');
    }
    for (const name of expectedNames) {
        const binding = sourceBindings[name];
        assertObject(binding, `GD-A03 source_bindings.${name}`);
        const requiredFields = SOURCE_BINDING_FIELDS[name];
        const allowedFields = new Set(requiredFields);
        for (const field of Object.keys(binding)) {
            if (!allowedFields.has(field)) {
                fail(`GD-A03 source_bindings.${name}.${field} is unsupported`, 'SCHEMA_MISMATCH');
            }
        }
        for (const field of requiredFields) {
            if (binding[field] === undefined) {
                fail(`GD-A03 source_bindings.${name}.${field} is required`, 'PROVENANCE_INVALID');
            }
        }
        assertSha(binding.sha256, `GD-A03 source_bindings.${name}.sha256`);
        if (binding.business_hash !== undefined) {
            assertSha(binding.business_hash, `GD-A03 source_bindings.${name}.business_hash`);
        }
        assertText(binding.schema_version, `GD-A03 source_bindings.${name}.schema_version`);
        if (binding.ordered_features !== undefined) {
            assertArray(binding.ordered_features, `GD-A03 source_bindings.${name}.ordered_features`);
            binding.ordered_features.forEach((featureName, index) =>
                assertText(featureName, `GD-A03 source_bindings.${name}.ordered_features[${index}]`)
            );
        }
    }
    return sourceBindings;
}

function validateReadiness(value, label) {
    assertObject(value, label);
    for (const [field, expected] of Object.entries(READINESS_CONTRACT)) {
        if (value[field] !== expected) {
            fail(`${label}.${field} must remain ${String(expected)}`, 'READINESS_BOUNDARY');
        }
    }
}

// eslint-disable-next-line complexity -- artifact validation enumerates every schedule/team closure invariant.
function validateScheduleAuthority(scheduleAuthority) {
    assertObject(scheduleAuthority, 'GD-A03 schedule_authority');
    if (scheduleAuthority.schema_version !== 'candidate-match-identity/v1') {
        fail('GD-A03 schedule authority schema is invalid', 'HISTORY_CLOSURE_INVALID');
    }
    if (scheduleAuthority.closure_schema_version !== 'canonical-schedule-history/v1') {
        fail('GD-A03 schedule closure schema is invalid', 'HISTORY_CLOSURE_INVALID');
    }
    if (scheduleAuthority.closure_status !== 'PROVEN') {
        fail('GD-A03 schedule closure status is not PROVEN', 'HISTORY_CLOSURE_INVALID');
    }
    assertText(scheduleAuthority.authority, 'GD-A03 schedule_authority.authority');
    assertObject(scheduleAuthority.per_season_counts, 'GD-A03 schedule_authority.per_season_counts');
    for (const [season, count] of Object.entries(scheduleAuthority.per_season_counts)) {
        if (!season || !Number.isSafeInteger(count) || count <= 0) {
            fail('GD-A03 schedule season count is invalid', 'HISTORY_CLOSURE_INVALID');
        }
    }
    const teamClosure = scheduleAuthority.team_closure;
    assertObject(teamClosure, 'GD-A03 schedule_authority.team_closure');
    if (teamClosure.schema_version !== SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION || teamClosure.status !== 'PROVEN') {
        fail('GD-A03 team closure status/schema is invalid', 'HISTORY_CLOSURE_INVALID');
    }
    const canonicalTeamClosure = {
        teams_per_season: SCHEDULE_TEAMS_PER_SEASON,
        fixtures_per_team: SCHEDULE_FIXTURES_PER_TEAM,
        home_fixtures_per_team: SCHEDULE_HOME_FIXTURES_PER_TEAM,
        away_fixtures_per_team: SCHEDULE_AWAY_FIXTURES_PER_TEAM,
    };
    for (const [field, expected] of Object.entries(canonicalTeamClosure)) {
        if (teamClosure[field] !== expected) {
            fail(`GD-A03 team closure ${field} is not canonical`, 'HISTORY_CLOSURE_INVALID');
        }
    }
    assertObject(teamClosure.per_team_counts, 'GD-A03 schedule_authority.team_closure.per_team_counts');
    for (const [season, teamCounts] of Object.entries(teamClosure.per_team_counts)) {
        assertObject(teamCounts, `GD-A03 team closure ${season}`);
        let totalFixtures = 0;
        for (const [team, counts] of Object.entries(teamCounts)) {
            if (!team) fail('GD-A03 team closure has an empty team identity', 'HISTORY_CLOSURE_INVALID');
            assertObject(counts, `GD-A03 team closure ${season}.${team}`);
            for (const field of ['total', 'home', 'away']) {
                if (!Number.isSafeInteger(counts[field]) || counts[field] < 0) {
                    fail(`GD-A03 team closure ${season}.${team}.${field} is invalid`, 'HISTORY_CLOSURE_INVALID');
                }
            }
            if (counts.total !== counts.home + counts.away) {
                fail(`GD-A03 team closure ${season}.${team} totals do not reconcile`, 'HISTORY_CLOSURE_INVALID');
            }
            if (
                counts.total !== SCHEDULE_FIXTURES_PER_TEAM ||
                counts.home !== SCHEDULE_HOME_FIXTURES_PER_TEAM ||
                counts.away !== SCHEDULE_AWAY_FIXTURES_PER_TEAM
            ) {
                fail(`GD-A03 team closure ${season}.${team} is not canonical`, 'HISTORY_CLOSURE_INVALID');
            }
            totalFixtures += counts.total;
        }
        if (Object.keys(teamCounts).length !== SCHEDULE_TEAMS_PER_SEASON) {
            fail(`GD-A03 team closure ${season} team count is not canonical`, 'HISTORY_CLOSURE_INVALID');
        }
        if (scheduleAuthority.per_season_counts[season] !== totalFixtures / 2) {
            fail(`GD-A03 team closure ${season} does not reconcile to schedule count`, 'HISTORY_CLOSURE_INVALID');
        }
    }
    if (
        stableStringify(Object.keys(teamClosure.per_team_counts).sort()) !==
        stableStringify(Object.keys(scheduleAuthority.per_season_counts).sort())
    ) {
        fail('GD-A03 team closure seasons do not match schedule seasons', 'HISTORY_CLOSURE_INVALID');
    }
    return scheduleAuthority;
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

// eslint-disable-next-line complexity -- target-label validation enumerates identity, result, and digest invariants.
function validateTargetLabel(label, row) {
    assertObject(label, `GD-A03 row ${row.canonical_match_id}.target_label`);
    if (label.role !== TRAINING_LABEL_ROLE || label.timing_class !== FACT_TIMING_CLASS) {
        fail('GD-A03 target label timing is invalid', 'TEMPORAL_SEMANTICS_UNPROVEN');
    }
    if (label.canonical_match_id !== row.canonical_match_id) {
        fail('GD-A03 target label identity is invalid', 'PROVENANCE_INVALID');
    }
    assertObject(label.provenance_input, `GD-A03 row ${row.canonical_match_id}.target_label.provenance_input`);
    const result = label.provenance_input.result;
    if (result !== null) assertObject(result, `GD-A03 row ${row.canonical_match_id}.target_label.result`);
    const expectedStatus = result?.status || 'UNAVAILABLE';
    const expectedOutcome = result?.outcome || null;
    if (!['AVAILABLE', 'UNAVAILABLE'].includes(expectedStatus)) {
        fail('GD-A03 target label result status is invalid', 'FACT_VALUE_INVALID');
    }
    if (expectedStatus === 'AVAILABLE') {
        if (!['home', 'draw', 'away'].includes(expectedOutcome)) {
            fail('GD-A03 target label result outcome is invalid', 'FACT_VALUE_INVALID');
        }
        if (!Number.isSafeInteger(result.home_score) || result.home_score < 0) {
            fail('GD-A03 target label home score is invalid', 'FACT_VALUE_INVALID');
        }
        if (!Number.isSafeInteger(result.away_score) || result.away_score < 0) {
            fail('GD-A03 target label away score is invalid', 'FACT_VALUE_INVALID');
        }
    } else if (expectedOutcome !== null) {
        fail('GD-A03 unavailable target label carries an outcome', 'FACT_VALUE_INVALID');
    }
    if (label.status !== expectedStatus || label.outcome !== expectedOutcome) {
        fail('GD-A03 target label projection mismatch', 'FACT_VALUE_INVALID');
    }
    assertObject(
        label.provenance_input.source_provenance,
        `GD-A03 row ${row.canonical_match_id}.target_label.source_provenance`
    );
    assertSha(label.provenance_digest, `GD-A03 row ${row.canonical_match_id}.target_label.provenance_digest`);
    const expectedDigest = computeProvenanceDigest({
        role: TRAINING_LABEL_ROLE,
        target_match_id: row.canonical_match_id,
        result,
        source_provenance: label.provenance_input.source_provenance,
    });
    if (label.provenance_digest !== expectedDigest) {
        fail('GD-A03 target label provenance mismatch', 'PROVENANCE_INVALID');
    }
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
    const semanticsByName = new Map(semantics.map(definition => [definition.feature_name, definition]));
    if (stableStringify(artifact.feature_semantics) !== stableStringify(semantics)) {
        fail('GD-A03 semantic matrix mismatch', 'SCHEMA_MISMATCH');
    }
    validateSourceBindings(artifact.source_bindings);
    if (
        stableStringify(artifact.source_bindings.runtime_feature_adapter.ordered_features) !==
        stableStringify(featureContract.ordered_features)
    ) {
        fail('GD-A03 runtime feature binding order mismatch', 'PROVENANCE_INVALID');
    }
    validateReadiness(artifact, 'GD-A03 artifact');
    validateScheduleAuthority(artifact.schedule_authority);
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
        const expectedEligible = featureContract.ordered_features.every(name => {
            const definition = semanticsByName.get(name);
            return (
                isSemanticsProven(definition.semantics_status) &&
                row.features[name].availability_status === FEATURE_AVAILABILITY.AVAILABLE &&
                Number.isFinite(row.features[name].value)
            );
        });
        if ((row.feature_vector_eligibility.status === 'YES') !== expectedEligible) {
            fail('GD-A03 row eligibility disagrees with features', 'POPULATION_MISMATCH');
        }
        validateTargetLabel(row.target_label, row);
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
    assertSha(accounting.target_id_set_sha256, 'GD-A03 target_id_set_sha256');
    assertSha(accounting.accounted_id_set_sha256, 'GD-A03 accounted_id_set_sha256');
    const accountedIds = artifact.rows.map(row => row.canonical_match_id);
    const expectedIdHash = admittedIdSetHash(accountedIds);
    if (accounting.target_id_set_sha256 !== expectedIdHash || accounting.accounted_id_set_sha256 !== expectedIdHash) {
        fail('GD-A03 population ID set hash mismatch', 'POPULATION_MISMATCH');
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
    validateReadiness(receipt, 'GD-A03 receipt');
    for (const field of Object.keys(READINESS_CONTRACT)) {
        if (receipt[field] !== artifact[field]) {
            fail(`GD-A03 receipt ${field} does not match artifact`, 'READINESS_BOUNDARY');
        }
    }
    if (receipt.artifact_sha256 !== sha256Bytes(artifactBytes)) {
        fail('GD-A03 receipt artifact hash mismatch', 'ARTIFACT_HASH_MISMATCH');
    }
    if (receipt.output_business_sha256 !== artifact.business_content_sha256) {
        fail('GD-A03 receipt business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    assertSha(receipt.receipt_content_sha256, 'GD-A03 receipt receipt_content_sha256');
    if (receipt.receipt_content_sha256 !== computeReceiptHash(receipt)) {
        fail('GD-A03 receipt content hash mismatch', 'RECEIPT_HASH_MISMATCH');
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
