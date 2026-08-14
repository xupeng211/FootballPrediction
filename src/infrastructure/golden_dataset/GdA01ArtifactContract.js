'use strict';

// lifecycle: permanent
// GD-A01 artifact/receipt 层：绑定已验证的 spine+odds 业务内容、输出顺序、哈希和
// population profile。输入源的身份与 provider 合同仍由 sibling contract 负责。

const { isStrictAbsoluteTimestamp } = require('../fotmob/FotMobCandidateExporter');
const base = require('./GdA01AssemblyContract');

const {
    ASSEMBLY_SCHEMA_VERSION,
    GdA01ContractError,
    RECEIPT_SCHEMA_VERSION,
    STAGE,
    TEMPORAL_CAPABILITY,
    admittedIdSetHash,
    computeArtifactBusinessHash,
    linkageDecisionSetHash,
    observationSortKey,
    sha256Bytes,
    stableStringify,
    assertInteger,
    assertObject,
    assertSha,
    assertText,
    validateMatchLink,
    validateOddsObservation,
} = base;

const FORBIDDEN_A01_KEYS = new Set([
    'xg',
    'expected_goals',
    'shots_on_target',
    'possession',
    'lineup',
    'rating',
    'elo',
    'form',
    'standings',
    'result',
    'score',
    'feature',
    'training',
    'prediction',
]);
const GIT_REVISION_PATTERN = /^[0-9a-f]{40}$/;

function scanForbiddenKeys(value, pathLabel = 'artifact') {
    if (Array.isArray(value)) {
        value.forEach((item, index) => scanForbiddenKeys(item, `${pathLabel}[${index}]`));
        return;
    }
    if (!value || typeof value !== 'object') {
        return;
    }
    for (const [key, child] of Object.entries(value)) {
        if (FORBIDDEN_A01_KEYS.has(key.toLowerCase())) {
            throw new GdA01ContractError(`${pathLabel}.${key} is outside GD-A01 scope`, 'SCOPE_VIOLATION');
        }
        scanForbiddenKeys(child, `${pathLabel}.${key}`);
    }
}

function validateTemporalCapability(value, label = 'temporal_capability') {
    if (stableStringify(value) !== stableStringify(TEMPORAL_CAPABILITY)) {
        throw new GdA01ContractError(
            `${label} does not preserve the GD-A01 temporal boundary`,
            'TEMPORAL_SEMANTICS_UNPROVEN'
        );
    }
}

function validateOutputObservation(observation, label) {
    const normalized = validateOddsObservation(observation, label);
    if (normalized.match_link.matched_id !== observation.canonical_match_id) {
        throw new GdA01ContractError(`${label} link points to a different canonical match`, 'IDENTITY_CONFLICT');
    }
    // `canonical_match_id` is an enclosing assembly-row identity, not part of
    // the persisted odds observation projection. Do not leak the temporary
    // validation field into the normalized business projection.
    const { canonical_match_id: ignoredCanonicalMatchId, ...businessObservation } = observation;
    return {
        ...businessObservation,
        decimal_odds: normalized.decimal_odds,
        match_link: normalized.match_link,
    };
}

function validateAssemblyRow(row, index) {
    assertObject(row, `artifact.rows[${index}]`);
    for (const field of ['canonical_match_id', 'competition', 'season', 'kickoff_at', 'home_team', 'away_team']) {
        assertText(row[field], `artifact.rows[${index}].${field}`);
    }
    if (!isStrictAbsoluteTimestamp(row.kickoff_at) || row.home_team === row.away_team) {
        throw new GdA01ContractError(`artifact.rows[${index}] identity is malformed`, 'IDENTITY_CONFLICT');
    }
    const linkage = validateMatchLink(row.source_linkage, `artifact.rows[${index}].source_linkage`);
    assertText(row.source_linkage.authority, `artifact.rows[${index}].source_linkage.authority`);
    if (row.admission?.status !== 'ADMITTED' || row.admission.rejection_reason !== null) {
        throw new GdA01ContractError(`artifact.rows[${index}] admission is not admitted`);
    }
    assertObject(row.fotmob_frozen_source, `artifact.rows[${index}].fotmob_frozen_source`);
    assertSha(row.fotmob_frozen_source.raw_payload_sha256, `artifact.rows[${index}] FotMob raw hash`);
    assertObject(row.football_data, `artifact.rows[${index}].football_data`);
    if (!Array.isArray(row.football_data.observations) || row.football_data.observations.length === 0) {
        throw new GdA01ContractError(`artifact.rows[${index}] has no odds observations`, 'POPULATION_MISMATCH');
    }
    const observations = row.football_data.observations.map((observation, observationIndex) =>
        validateOutputObservation(
            { ...observation, canonical_match_id: row.canonical_match_id },
            `artifact.rows[${index}].football_data.observations[${observationIndex}]`
        )
    );
    const sorted = [...observations].sort((left, right) =>
        observationSortKey(left).localeCompare(observationSortKey(right))
    );
    if (stableStringify(observations) !== stableStringify(sorted)) {
        throw new GdA01ContractError(`artifact.rows[${index}] observations are not deterministically ordered`);
    }
    return {
        ...row,
        source_linkage: { authority: row.source_linkage.authority, ...linkage },
        football_data: { ...row.football_data, observations },
    };
}

function validateRejectionRows(rows) {
    if (!Array.isArray(rows)) {
        throw new GdA01ContractError('artifact.rejected_rows must be an array');
    }
    const ids = new Set();
    const normalized = rows.map((row, index) => {
        assertObject(row, `artifact.rejected_rows[${index}]`);
        assertText(row.canonical_match_id, `artifact.rejected_rows[${index}].canonical_match_id`);
        if (
            row.admission?.status !== 'REJECTED' ||
            !assertText(row.admission.rejection_reason, `artifact.rejected_rows[${index}].admission.rejection_reason`)
        ) {
            throw new GdA01ContractError(`artifact.rejected_rows[${index}] rejection is incomplete`);
        }
        if (ids.has(row.canonical_match_id)) {
            throw new GdA01ContractError(`duplicate rejected ID ${row.canonical_match_id}`);
        }
        ids.add(row.canonical_match_id);
        return row;
    });
    const sorted = [...normalized].sort((left, right) =>
        left.canonical_match_id.localeCompare(right.canonical_match_id)
    );
    if (stableStringify(normalized) !== stableStringify(sorted)) {
        throw new GdA01ContractError('artifact.rejected_rows are not deterministically ordered');
    }
    return normalized;
}

function validateSourceBindings(bindings) {
    assertObject(bindings, 'artifact.source_bindings');
    for (const [name, binding] of Object.entries(bindings)) {
        assertObject(binding, `artifact.source_bindings.${name}`);
        if (binding.sha256) {
            assertSha(binding.sha256, `artifact.source_bindings.${name}.sha256`);
        }
        if (binding.business_hash) {
            assertSha(binding.business_hash, `artifact.source_bindings.${name}.business_hash`);
        }
    }
    return bindings;
}

function validateAssemblyArtifact(document, options = {}) {
    assertObject(document, 'GD-A01 artifact');
    if (document.schema_version !== ASSEMBLY_SCHEMA_VERSION) {
        throw new GdA01ContractError('GD-A01 artifact schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    if (document.stage !== STAGE || document.artifact_kind !== 'spine_odds_assembly') {
        throw new GdA01ContractError('GD-A01 artifact stage/kind mismatch');
    }
    assertSha(document.business_content_sha256, 'GD-A01 artifact business_content_sha256');
    const bindings = validateSourceBindings(document.source_bindings);
    validateTemporalCapability(document.temporal_capability);
    if (!Array.isArray(document.rows) || document.rows.length === 0) {
        throw new GdA01ContractError('GD-A01 artifact rows are required');
    }
    const rows = document.rows.map(validateAssemblyRow);
    const rejectedRows = validateRejectionRows(document.rejected_rows);
    if (options.expectedAdmittedRows !== undefined && rows.length !== Number(options.expectedAdmittedRows)) {
        throw new GdA01ContractError(
            'GD-A01 artifact does not satisfy the explicit population profile',
            'POPULATION_MISMATCH'
        );
    }
    const rowIds = new Set();
    for (const row of rows) {
        if (rowIds.has(row.canonical_match_id)) {
            throw new GdA01ContractError(`duplicate admitted ID ${row.canonical_match_id}`);
        }
        rowIds.add(row.canonical_match_id);
    }
    const sortedRows = [...rows].sort((left, right) => left.canonical_match_id.localeCompare(right.canonical_match_id));
    if (stableStringify(rows) !== stableStringify(sortedRows)) {
        throw new GdA01ContractError('GD-A01 rows are not deterministically ordered');
    }
    scanForbiddenKeys({ rows, rejected_rows: rejectedRows });
    // Hash the exact validated business document, rather than a normalized
    // clone. Validation may return a convenient normalized view, but accepting
    // a different projection would make the receipt unable to bind bytes to
    // the business hash.
    const recomputed = computeArtifactBusinessHash(document);
    if (recomputed !== document.business_content_sha256) {
        throw new GdA01ContractError('GD-A01 artifact business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    return {
        ...document,
        rows,
        rejected_rows: rejectedRows,
        source_bindings: bindings,
    };
}

function validateReceiptHeader(receipt) {
    if (receipt.schema_version !== RECEIPT_SCHEMA_VERSION) {
        throw new GdA01ContractError('GD-A01 receipt schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    if (receipt.stage !== STAGE || receipt.build_mode !== 'file_first') {
        throw new GdA01ContractError('GD-A01 receipt stage/build mode mismatch');
    }
    if (typeof receipt.code_revision !== 'string' || !GIT_REVISION_PATTERN.test(receipt.code_revision)) {
        throw new GdA01ContractError('GD-A01 receipt code_revision is invalid');
    }
    assertInteger(receipt.admitted_row_count, 'GD-A01 receipt admitted_row_count', 1);
    assertInteger(receipt.rejected_row_count, 'GD-A01 receipt rejected_row_count');
    assertSha(receipt.artifact_sha256, 'GD-A01 receipt artifact_sha256');
    assertSha(receipt.output_business_sha256, 'GD-A01 receipt output_business_sha256');
    assertSha(receipt.admitted_id_set_sha256, 'GD-A01 receipt admitted_id_set_sha256');
    assertSha(receipt.linkage_decision_set_sha256, 'GD-A01 receipt linkage_decision_set_sha256');
    validateTemporalCapability(receipt.temporal_capability, 'GD-A01 receipt temporal_capability');
}

function validateReceiptPopulationProfile(receipt) {
    if (receipt.population_profile !== undefined) {
        assertObject(receipt.population_profile, 'GD-A01 receipt population_profile');
        assertInteger(
            receipt.population_profile.expected_admitted_rows,
            'GD-A01 receipt population_profile.expected_admitted_rows',
            1
        );
        if (
            receipt.population_profile.expected_admitted_unmatched !== 0 ||
            receipt.population_profile.expected_admitted_ambiguous !== 0
        ) {
            throw new GdA01ContractError(
                'GD-A01 admitted profile must require zero unmatched/ambiguous rows',
                'POPULATION_MISMATCH'
            );
        }
    }
}

function validateReceiptArtifactByteBinding(receipt, artifactBytes) {
    if (artifactBytes && receipt.artifact_sha256 !== sha256Bytes(artifactBytes)) {
        throw new GdA01ContractError('GD-A01 artifact byte hash mismatch', 'ARTIFACT_HASH_MISMATCH');
    }
}

function validateReceiptArtifactBinding(receipt, artifact) {
    if (artifact) {
        const normalizedArtifact = validateAssemblyArtifact(artifact);
        if (receipt.output_business_sha256 !== normalizedArtifact.business_content_sha256) {
            throw new GdA01ContractError('GD-A01 receipt output business hash mismatch', 'BUSINESS_HASH_MISMATCH');
        }
        if (
            receipt.admitted_row_count !== normalizedArtifact.rows.length ||
            receipt.rejected_row_count !== normalizedArtifact.rejected_rows.length
        ) {
            throw new GdA01ContractError('GD-A01 receipt population does not match artifact', 'POPULATION_MISMATCH');
        }
        if (
            receipt.population_profile &&
            receipt.population_profile.expected_admitted_rows !== normalizedArtifact.rows.length
        ) {
            throw new GdA01ContractError(
                'GD-A01 receipt population profile does not match artifact',
                'POPULATION_MISMATCH'
            );
        }
        if (
            receipt.admitted_id_set_sha256 !==
            admittedIdSetHash(normalizedArtifact.rows.map(row => row.canonical_match_id))
        ) {
            throw new GdA01ContractError('GD-A01 receipt admitted ID hash mismatch', 'BUSINESS_HASH_MISMATCH');
        }
        if (receipt.linkage_decision_set_sha256 !== linkageDecisionSetHash(normalizedArtifact.rows)) {
            throw new GdA01ContractError('GD-A01 receipt linkage hash mismatch', 'BUSINESS_HASH_MISMATCH');
        }
        if (stableStringify(receipt.source_bindings) !== stableStringify(normalizedArtifact.source_bindings)) {
            throw new GdA01ContractError('GD-A01 receipt source bindings mismatch', 'BUSINESS_HASH_MISMATCH');
        }
    }
}

function validateReceiptDocument(receipt, artifactBytes, artifact) {
    assertObject(receipt, 'GD-A01 receipt');
    validateReceiptHeader(receipt);
    validateReceiptPopulationProfile(receipt);
    validateReceiptArtifactByteBinding(receipt, artifactBytes);
    validateReceiptArtifactBinding(receipt, artifact);
    return receipt;
}

function validateOutputFiles(artifactBytes, receiptBytes) {
    let artifact;
    let receipt;
    try {
        artifact = JSON.parse(Buffer.from(artifactBytes).toString('utf8'));
        receipt = JSON.parse(Buffer.from(receiptBytes).toString('utf8'));
    } catch {
        throw new GdA01ContractError('GD-A01 output files are not valid JSON', 'SCHEMA_MISMATCH');
    }
    const normalizedArtifact = validateAssemblyArtifact(artifact);
    validateReceiptDocument(receipt, artifactBytes, normalizedArtifact);
    return { artifact: normalizedArtifact, receipt };
}

module.exports = {
    validateAssemblyArtifact,
    validateOutputFiles,
    validateReceiptDocument,
};
