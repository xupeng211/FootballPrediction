'use strict';

// lifecycle: test-fixture；只验证离线 frame projection，不读取 DB、不联网、不训练。

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');

const { loadFeatureContract } = require('../../scripts/ops/gd_a03_assembler');
const {
    admittedIdSetHash,
    sha256Bytes,
} = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const { FEATURE_SEMANTICS } = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');
const {
    buildFrameOutput,
    projectFrameArtifact,
    sourceLineBindingDigest,
    validateFrameAgainstInputs,
    validateFrameOutputFiles,
} = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract');

const REPO_ROOT = path.resolve(__dirname, '../..');
const LOADED = loadFeatureContract(REPO_ROOT);
const ACCEPTED = LOADED.vNextContract.feature_statuses
    .filter(status => status.training_decision === 'ACCEPTED_FOR_TRAINING')
    .map(status => status.feature_name);

function line(targetKickoff, available = true) {
    return {
        availability_status: available ? 'AVAILABLE' : 'UNAVAILABLE',
        value: available ? 1 : null,
        cutoff_proof: {
            max_source_time: '2024-01-01T00:00:00Z',
            passed: true,
            relation: 'source_match_kickoff < target_match_kickoff',
            source_time_basis: 'MATCH_KICKOFF',
            target_cutoff: targetKickoff,
        },
        derivation_contract: 'test-lineage/v1:deterministic_fixture',
        latest_source_kickoff: '2024-01-01T00:00:00Z',
        provenance_digest: 'a'.repeat(64),
        provenance_inputs: [],
        source_evidence_match_ids: ['source-001'],
        source_fields: ['fixture.value'],
        source_identities: [
            {
                canonical_match_id: 'source-001',
                home_team: 'Source Home',
                away_team: 'Source Away',
                kickoff_at: '2024-01-01T00:00:00Z',
            },
        ],
        source_match_ids: ['source-001'],
        unavailable_reason_codes: available ? [] : ['INSUFFICIENT_HISTORY'],
    };
}

function targetLabel(id, available = true) {
    return {
        canonical_match_id: id,
        outcome: available ? 'home' : null,
        provenance_digest: 'b'.repeat(64),
        provenance_input: { source: 'fixture' },
        role: 'TRAINING_LABEL_POSTMATCH',
        source_fact_binding: {},
        status: available ? 'AVAILABLE' : 'UNAVAILABLE',
        timing_class: 'POSTMATCH_ONLY',
    };
}

function sourceArtifact() {
    const v1 = LOADED.contract;
    const makeRow = (id, kickoff, availableFeature = true, availableLabel = true) => ({
        canonical_match_id: id,
        target_kickoff: kickoff,
        home_team: 'Home Team',
        away_team: 'Away Team',
        feature_cutoff_policy: 'TARGET_KICKOFF_EXCLUSIVE',
        feature_cutoff_time: kickoff,
        features: Object.fromEntries(v1.ordered_features.map(name => [name, line(kickoff, ACCEPTED.includes(name) ? availableFeature : false)])),
        target_label: targetLabel(id, availableLabel),
    });
    return {
        feature_contract: {
            contract_id: v1.contract_id,
            feature_contract_version: v1.feature_contract_version,
            ordered_features: v1.ordered_features,
        },
        feature_semantics: FEATURE_SEMANTICS,
        population_authority: {
            schema_version: 'gd-a01-target-population-binding/v1',
            source_binding: 'gd-a01_receipt.admitted_id_set_sha256',
            target_id_set_sha256: admittedIdSetHash(['target-001', 'target-002', 'target-003']),
            target_population_count: 3,
        },
        business_content_sha256: 'a'.repeat(64),
        rows: [
            makeRow('target-001', '2024-02-01T12:00:00Z'),
            makeRow('target-002', '2024-02-02T12:00:00Z', false),
            makeRow('target-003', '2024-02-03T12:00:00Z', true, false),
        ],
    };
}

function projected() {
    return projectFrameArtifact({
        priorStateArtifact: sourceArtifact(),
        priorStateArtifactSha256: 'c'.repeat(64),
        priorStateReceipt: { schema_version: 'fixture/v1' },
        priorStateReceiptSha256: 'd'.repeat(64),
        featureContractBinding: {
            sha256: LOADED.sha256,
            registrySchemaVersion: LOADED.registrySchemaVersion,
        },
        vNextContract: LOADED.vNextContract,
        runtimeSemanticEngineBinding: { sha256: 'e'.repeat(64), adapterSha256: '1'.repeat(64) },
    });
}

function frameInputs() {
    const priorStateArtifact = sourceArtifact();
    const priorStateReceipt = { schema_version: 'fixture-receipt/v1' };
    return {
        priorStateArtifact,
        priorStateArtifactBytes: Buffer.from(`${JSON.stringify(priorStateArtifact, null, 2)}\n`),
        priorStateReceipt,
        priorStateReceiptBytes: Buffer.from(`${JSON.stringify(priorStateReceipt, null, 2)}\n`),
        featureContractBinding: {
            sha256: LOADED.sha256,
            registrySchemaVersion: LOADED.registrySchemaVersion,
        },
        vNextContract: LOADED.vNextContract,
        runtimeSemanticEngineBinding: {
            sha256: 'e'.repeat(64),
            adapterSha256: '1'.repeat(64),
        },
        codeRevision: 'f'.repeat(40),
    };
}

test('registry decisions derive a stable nine-feature training order', () => {
    const artifact = projected();

    assert.deepEqual(artifact.feature_contract.training_feature_order, [
        'rolling_xg_home',
        'rolling_xg_away',
        'home_points',
        'away_points',
        'points_diff',
        'home_recent_form_points',
        'home_fatigue_index',
        'away_fatigue_index',
        'fatigue_diff',
    ]);
    assert.equal(artifact.feature_contract.training_feature_count, 9);
    assert.equal(artifact.feature_decisions.length, 17);
});

test('projection conserves population and keeps ineligible rows explicit', () => {
    const artifact = projected();

    assert.deepEqual(artifact.population_accounting, {
        target_population: 3,
        rows_accounted: 3,
        training_eligible: 1,
        training_ineligible: 2,
        unaccounted: 0,
        duplicate: 0,
        extra: 0,
        target_id_set_sha256: artifact.population_accounting.target_id_set_sha256,
        accounted_id_set_sha256: artifact.population_accounting.accounted_id_set_sha256,
    });
    assert.equal(artifact.rows.length, 3);
    assert.equal(artifact.rows[1].training_eligibility.status, 'INELIGIBLE');
    assert.equal(artifact.rows[2].training_eligibility.status, 'INELIGIBLE');
    assert.equal(artifact.validation_counters.label_feature_dependency_count, 0);
});

test('generated artifact and receipt validate, and rebuilding is deterministic', () => {
    const first = projected();
    const second = projected();
    const firstArtifactBytes = Buffer.from(`${JSON.stringify(first, null, 2)}\n`);
    const firstReceipt = {
        schema_version: 'canonical-prematch-training-feature-frame-receipt/v1',
        stage: 'CANONICAL_PREMATCH_FEATURE_FRAME',
        code_revision: 'f'.repeat(40),
        artifact_sha256: require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract').sha256Bytes(firstArtifactBytes),
        output_business_sha256: first.business_content_sha256,
        receipt_content_sha256: null,
        target_population: 3,
        rows_accounted: 3,
        training_eligible: 1,
        training_ineligible: 2,
        unaccounted: 0,
        duplicate: 0,
        extra: 0,
        feature_frame_readiness: 'READY',
        real_training_readiness: 'READY',
        strict_decision_time_value_evaluation: 'NOT_READY',
        golden_dataset_complete: false,
        training_execution_authorized: false,
        offline: true,
        file_first: true,
        live_fetch: 0,
        db_writes: 0,
        raw_writes: 0,
        training_runs: 0,
        backtest_runs: 0,
        model_activations: 0,
        source_bindings: first.source_bindings,
        population_authority: first.population_authority,
    };
    const { computeFrameReceiptHash } = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract');
    firstReceipt.receipt_content_sha256 = computeFrameReceiptHash(firstReceipt);
    const firstReceiptBytes = Buffer.from(`${JSON.stringify(firstReceipt, null, 2)}\n`);

    validateFrameOutputFiles(firstArtifactBytes, firstReceiptBytes);
    assert.equal(JSON.stringify(first), JSON.stringify(second));
    assert.equal(first.business_content_sha256, second.business_content_sha256);
});

test('target label mutation does not change prematch feature projection', () => {
    const originalSource = sourceArtifact();
    const mutatedSource = sourceArtifact();
    mutatedSource.rows[0].target_label.outcome = 'away';
    mutatedSource.rows[0].target_label.provenance_digest = '9'.repeat(64);
    const base = projectFrameArtifact({
        priorStateArtifact: originalSource,
        priorStateArtifactSha256: 'c'.repeat(64),
        priorStateReceipt: {},
        priorStateReceiptSha256: 'd'.repeat(64),
        featureContractBinding: { sha256: LOADED.sha256, registrySchemaVersion: LOADED.registrySchemaVersion },
        vNextContract: LOADED.vNextContract,
        runtimeSemanticEngineBinding: { sha256: 'e'.repeat(64), adapterSha256: '1'.repeat(64) },
    });
    const changed = projectFrameArtifact({
        priorStateArtifact: mutatedSource,
        priorStateArtifactSha256: 'c'.repeat(64),
        priorStateReceipt: {},
        priorStateReceiptSha256: 'd'.repeat(64),
        featureContractBinding: { sha256: LOADED.sha256, registrySchemaVersion: LOADED.registrySchemaVersion },
        vNextContract: LOADED.vNextContract,
        runtimeSemanticEngineBinding: { sha256: 'e'.repeat(64), adapterSha256: '1'.repeat(64) },
    });

    assert.deepEqual(base.rows[0].features, changed.rows[0].features);
    assert.notEqual(base.rows[0].target_label.outcome, changed.rows[0].target_label.outcome);
});

test('source-line and cutoff tampering fail closed', () => {
    const artifact = projected();
    const artifactBytes = Buffer.from(`${JSON.stringify(artifact, null, 2)}\n`);
    const tampered = JSON.parse(artifactBytes.toString('utf8'));
    tampered.rows[0].features.rolling_xg_home.value = 99;
    assert.throws(() => {
        validateFrameOutputFiles(artifactBytes, Buffer.from('{}'));
    }, /receipt/);
    assert.throws(() => {
        const bytes = Buffer.from(`${JSON.stringify(tampered, null, 2)}\n`);
        // The original receipt cannot authorize a changed business projection.
        validateFrameOutputFiles(bytes, Buffer.from('{}'));
    }, /source-line binding|receipt/);

    const future = projected();
    future.rows[0].features.rolling_xg_home.source_identities[0].kickoff_at = future.rows[0].target_kickoff_utc;
    assert.throws(() => {
        // Recompute only the source-line and outer hashes to reach the temporal validator.
        const line = future.rows[0].features.rolling_xg_home;
        line.source_line_sha256 = sourceLineBindingDigest(
            future.rows[0].canonical_match_id,
            'rolling_xg_home',
            line
        );
        const { computeFrameBusinessHash } = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract');
        future.business_content_sha256 = computeFrameBusinessHash(future);
        require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract').validateFrameArtifact(future);
    }, /future source identity|cutoff/);
});

test('source-bound validation rejects rehashed row, contract, and label tampering', () => {
    const inputs = frameInputs();
    const original = buildFrameOutput(inputs);
    const validate = (artifactBytes, receiptBytes) =>
        validateFrameAgainstInputs({
            ...inputs,
            artifactBytes,
            receiptBytes,
        });
    assert.doesNotThrow(() => validate(original.artifactBytes, original.receiptBytes));

    const rehash = artifact => {
        artifact.business_content_sha256 = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract').computeFrameBusinessHash(artifact);
        const artifactBytes = Buffer.from(`${JSON.stringify(artifact, null, 2)}\n`);
        const receipt = {
            ...original.receipt,
            artifact_sha256: sha256Bytes(artifactBytes),
            output_business_sha256: artifact.business_content_sha256,
            receipt_content_sha256: null,
        };
        receipt.receipt_content_sha256 = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract').computeFrameReceiptHash(receipt);
        return {
            artifactBytes,
            receiptBytes: Buffer.from(`${JSON.stringify(receipt, null, 2)}\n`),
        };
    };

    const missingRow = JSON.parse(original.artifactBytes.toString('utf8'));
    missingRow.rows.pop();
    assert.throws(() => validate(...Object.values(rehash(missingRow))), /population|source projection/);

    const oneFeature = JSON.parse(original.artifactBytes.toString('utf8'));
    oneFeature.feature_contract.training_feature_order.pop();
    oneFeature.feature_contract.training_feature_count -= 1;
    assert.throws(() => validate(...Object.values(rehash(oneFeature))), /binding|contract|source projection/);

    const label = JSON.parse(original.artifactBytes.toString('utf8'));
    label.rows[0].target_label.outcome = 'away';
    assert.throws(() => validate(...Object.values(rehash(label))), /bound|source projection|provenance/);
});
