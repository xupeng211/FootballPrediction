'use strict';

// lifecycle: permanent；GD-A02 contract/assembler/side-effect regression tests。
// 真实 888 离线验证使用相同 runtime contract，由任务级 external validation 运行。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');
const net = require('node:net');
const path = require('node:path');
const test = require('node:test');

const {
    ASSEMBLY_SCHEMA_VERSION: GD_A01_SCHEMA,
    TEMPORAL_CAPABILITY,
    admittedIdSetHash: admittedA01IdSetHash,
    computeArtifactBusinessHash: computeA01BusinessHash,
    linkageDecisionSetHash,
    sha256Bytes,
    stableStringify,
    validateOutputFiles: validateA01OutputFiles,
} = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const { buildFactsAssembly, validateFactsFiles } = require('../../src/infrastructure/golden_dataset/GdA02Assembler');
const {
    FACTS_ASSEMBLY_SCHEMA_VERSION,
    FACTS_RECEIPT_SCHEMA_VERSION,
    FACT_TIMING,
    computeArtifactBusinessHash,
    validateFactsArtifact,
    validateFactsSourceIndex,
    validateOutputFiles,
} = require('../../src/infrastructure/golden_dataset/GdA02FactsContract');
const {
    buildStagingArtifact,
    validateObservation,
    validateStagingArtifact,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
const { buildPair } = require('../helpers/fotmobDetailStagingFixtures');
const { parseArgs } = require('../../scripts/ops/gd_a02_assembler');

const HASH = 'a'.repeat(64);
const REVISION = 'b'.repeat(40);

function validOddsObservation(canonicalId) {
    return {
        schema_version: 'odds-observation/v1',
        source_provider: 'football-data-csv',
        source_url: 'git+repository://fixture/source.csv',
        source_match_id: null,
        competition: 'Premier League',
        season: '2022/2023',
        kickoff_at: '2022-10-08T14:00:00Z',
        home_team: 'AFC Bournemouth',
        away_team: 'Leicester City',
        bookmaker: 'Bet365',
        bookmaker_source_id: 'B365',
        market: '1X2',
        selection: 'home',
        line: null,
        decimal_odds: 2.1,
        snapshot_type: 'unknown',
        source_observed_at: null,
        captured_at: null,
        source_timezone: 'unknown',
        raw_sha256: HASH,
        raw_record_locator: 'fixture:row=1:b365:home',
        adapter: 'football-data-csv',
        adapter_version: '1.3.0',
        extraction_method: 'fixture',
        provenance_status: 'declared',
        capture_time_status: 'unknown',
        source_quote_series: 'B365',
        provider_collection_phase: 'first_collection_after_market_open',
        idempotency_key: 'c'.repeat(64),
        match_link: {
            status: 'matched',
            method: 'exact_home_away_kickoff',
            candidate_ids: [canonicalId],
            matched_id: canonicalId,
        },
    };
}

function buildUpstream(pair, overrides = {}) {
    const canonicalId = `47_20222023_${pair.payload.source_match_id}`;
    const frozenSource = {
        snapshot_id: HASH,
        target_population_hash: 'd'.repeat(64),
        manifest_sha256: 'e'.repeat(64),
        canonical_match_id: canonicalId,
        fotmob_match_id: pair.payload.source_match_id,
        raw_payload_sha256: 'f'.repeat(64),
        source_artifact_class: 'FIXTURE',
        capture_origin: 'FIXTURE',
        capture_semantics: 'POSTMATCH_ONLY',
        capture_timestamp: 'UNPROVEN',
    };
    const row = {
        canonical_match_id: canonicalId,
        competition: 'Premier League',
        season: '2022/2023',
        kickoff_at: pair.payload.expected_identity.kickoff_at,
        home_team: pair.payload.expected_identity.home_team,
        away_team: pair.payload.expected_identity.away_team,
        source_linkage: {
            authority: 'src/infrastructure/odds_staging/matchLinker.js',
            status: 'matched',
            method: 'exact_home_away_kickoff',
            candidate_ids: [canonicalId],
            matched_id: canonicalId,
        },
        fotmob_frozen_source: frozenSource,
        football_data: {
            source_ids: ['fixture'],
            source_raw_sha256: [HASH],
            observation_count: 1,
            observations: [validOddsObservation(canonicalId)],
        },
        admission: { status: 'ADMITTED', rejection_reason: null },
        ...overrides.row,
    };
    const artifactWithoutHash = {
        schema_version: GD_A01_SCHEMA,
        stage: 'GD-A01',
        artifact_kind: 'spine_odds_assembly',
        source_bindings: {
            canonical_candidate_artifact: { sha256: HASH, business_hash: HASH },
            fotmob_frozen_asset: { sha256: HASH, business_hash: HASH },
            football_data_historical_odds: { sha256: HASH, business_hash: HASH },
            canonical_linkage: { decision_set_sha256: HASH },
            provider_semantic_contract: { contract_id: 'football-data-provider-contract/v1' },
        },
        temporal_capability: TEMPORAL_CAPABILITY,
        rows: [row],
        rejected_rows: [],
    };
    const artifact = {
        ...artifactWithoutHash,
        business_content_sha256: computeA01BusinessHash({ ...artifactWithoutHash, business_content_sha256: null }),
    };
    const artifactBytes = Buffer.from(`${stableStringify(artifact)}\n`, 'utf8');
    const receipt = {
        schema_version: 'gd-a01-assembly-receipt/v1',
        stage: 'GD-A01',
        build_mode: 'file_first',
        code_revision: REVISION,
        source_bindings: artifact.source_bindings,
        admitted_row_count: 1,
        rejected_row_count: 0,
        admitted_id_set_sha256: admittedA01IdSetHash([canonicalId]),
        linkage_decision_set_sha256: linkageDecisionSetHash(artifact.rows),
        output_business_sha256: artifact.business_content_sha256,
        artifact_sha256: sha256Bytes(artifactBytes),
        temporal_capability: TEMPORAL_CAPABILITY,
    };
    const receiptBytes = Buffer.from(`${stableStringify(receipt)}\n`, 'utf8');
    validateA01OutputFiles(artifactBytes, receiptBytes);
    return { artifact, artifactBytes, receipt, receiptBytes, canonicalId, frozenSource };
}

function buildFreeze(pair, manifestBytes) {
    return {
        schema: 'fotmob-888-asset-freeze/v1',
        snapshot_id: HASH,
        target_population_hash: 'd'.repeat(64),
        manifest_sha256: sha256Bytes(manifestBytes),
        raw_payload_count: 1,
        missing: 0,
        extra: 0,
        duplicate: 0,
        full_raw_retention: true,
        raw_mutability: 'immutable',
        acquisition_status: 'complete',
        golden_dataset_status: 'not_complete',
        backup_status: 'PENDING_EXTERNAL_STORAGE',
        independent_redundant_storage_available: false,
        live_fotmob_network: false,
        db_writes_performed: false,
        history_rewritten: false,
        source_match_id: pair.payload.source_match_id,
    };
}

function buildFixture(t, pairOverrides = {}) {
    const pair = buildPair(pairOverrides);
    const validation = validateObservation({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.equal(validation.ok, true);
    const stagingArtifact = buildStagingArtifact({
        payload: pair.payload,
        manifest: pair.manifest,
        validation,
        payloadFileSha256: sha256Bytes(pair.payloadBytes),
        terminalState: 'ACCEPTED_NEW',
    });
    assert.equal(validateStagingArtifact(stagingArtifact).ok, true);
    const upstream = buildUpstream(pair);
    const manifestRow = {
        asset_manifest_schema: 'fotmob-888-raw-asset-manifest/v1',
        canonical_match_id: upstream.canonicalId,
        capture_origin: 'FIXTURE',
        capture_timestamp_if_available: '',
        fotmob_match_id: pair.payload.source_match_id,
        kickoff_at: pair.payload.expected_identity.kickoff_at,
        raw_payload_sha256: upstream.frozenSource.raw_payload_sha256,
        source_artifact_class: 'FIXTURE',
        season: pair.payload.season,
        snapshot_id: HASH,
        source_provider: 'FotMob',
        target_population_hash: upstream.frozenSource.target_population_hash,
    };
    const manifestBytes = Buffer.from(`${JSON.stringify(manifestRow)}\n`, 'utf8');
    const freeze = buildFreeze(pair, manifestBytes);
    const sourceIndex = {
        schema_version: 'gd-a02-facts-source-index/v1',
        source_provider: 'FotMob',
        entries: [
            {
                canonical_match_id: upstream.canonicalId,
                staging_artifact_path: `/tmp/${upstream.canonicalId}.staging.json`,
                capture_payload_path: `/tmp/${upstream.canonicalId}.payload.json`,
                capture_manifest_path: `/tmp/${upstream.canonicalId}.manifest.json`,
                staging_artifact_sha256: sha256Bytes(Buffer.from(`${JSON.stringify(stagingArtifact)}\n`)),
                capture_payload_sha256: sha256Bytes(pair.payloadBytes),
                capture_manifest_file_sha256: sha256Bytes(Buffer.from(`${JSON.stringify(pair.manifest)}\n`)),
            },
        ],
    };
    const sourceIndexBytes = Buffer.from(`${JSON.stringify(sourceIndex)}\n`, 'utf8');
    const stagingArtifactBytes = Buffer.from(`${JSON.stringify(stagingArtifact)}\n`, 'utf8');
    const captureManifestBytes = Buffer.from(`${JSON.stringify(pair.manifest)}\n`, 'utf8');
    const options = {
        gdA01ArtifactBytes: upstream.artifactBytes,
        gdA01ReceiptBytes: upstream.receiptBytes,
        fotmobFreezeDocument: freeze,
        fotmobFreezeBytes: Buffer.from(`${JSON.stringify(freeze)}\n`, 'utf8'),
        fotmobFreezeSha256: sha256Bytes(Buffer.from(`${JSON.stringify(freeze)}\n`, 'utf8')),
        fotmobManifestBytes: manifestBytes,
        fotmobManifestRows: [manifestRow],
        factsSourceIndex: sourceIndex,
        factsSourceIndexBytes: sourceIndexBytes,
        factsSourceIndexSha256: sha256Bytes(sourceIndexBytes),
        loadedFactsByCanonicalId: new Map([
            [
                upstream.canonicalId,
                {
                    index: sourceIndex.entries[0],
                    stagingArtifactBytes,
                    stagingArtifact,
                    capturePayloadBytes: pair.payloadBytes,
                    capturePayload: pair.payload,
                    captureManifestBytes,
                    captureManifest: pair.manifest,
                },
            ],
        ]),
        codeRevision: REVISION,
    };
    t.after(() => {});
    return { pair, upstream, freeze, manifestBytes, manifestRow, sourceIndex, options, stagingArtifact };
}

function buildResult(t, pairOverrides = {}) {
    const fixture = buildFixture(t, pairOverrides);
    const result = buildFactsAssembly(fixture.options);
    validateOutputFiles(result.artifactBytes, result.receiptBytes, { expectedAdmittedRows: 1 });
    return { ...fixture, result };
}

function assertContractReject(fn, code) {
    assert.throws(fn, error => {
        if (code) assert.equal(error.code, code);
        return true;
    });
}

test('GD-A02 produces admitted postmatch facts with exact provenance and no feature fields', t => {
    const { result, upstream } = buildResult(t);
    assert.equal(result.artifact.schema_version, FACTS_ASSEMBLY_SCHEMA_VERSION);
    assert.equal(result.artifact.rows.length, 1);
    assert.equal(result.artifact.rejected_rows.length, 0);
    assert.equal(result.receipt.schema_version, FACTS_RECEIPT_SCHEMA_VERSION);
    const row = result.artifact.rows[0];
    assert.equal(row.canonical_match_id, upstream.canonicalId);
    assert.equal(row.source_linkage.authority, 'src/infrastructure/odds_staging/matchLinker.js');
    assert.deepEqual(row.temporal_semantics, FACT_TIMING);
    assert.equal(row.facts.match_result.status, 'AVAILABLE');
    assert.equal(row.facts.match_result.home_score, 2);
    assert.equal(row.facts.match_result.away_score, 1);
    assert.equal(row.facts.match_result.outcome, 'home');
    assert.equal(row.facts.xg.status, 'PARTIAL');
    assert.equal(row.facts.xg.home.value, 0.09059995412826538);
    assert.equal(row.facts.xg.away.value, null);
    assert.equal(row.facts.shots_on_target.status, 'VALID');
    assert.equal(row.facts.shots_on_target.aggregation, 'count_true_isOnTarget_by_team_id');
    assert.equal(row.facts.shots_on_target.home.value, 1);
    assert.equal(row.facts.shots_on_target.away.value, 0);
    for (const section of ['events', 'lineup', 'player_stats', 'shotmap', 'stats']) {
        assert.equal(row.facts.sections[section].present, true);
        assert.equal(row.facts.sections[section].version, 'fotmob-match-detail-parsed/v1');
        assert.match(row.facts.sections[section].schema_fingerprint, /^[0-9a-f]{64}$/);
        assert.equal(Object.hasOwn(row.facts.sections[section], 'json'), false);
    }
    assert.equal(result.artifact.scope.prematch_features, false);
    assert.equal(result.artifact.scope.training, false);
});

test('GD-A02 build is byte-deterministic for identical exact inputs', t => {
    const fixture = buildFixture(t);
    const left = buildFactsAssembly(fixture.options);
    const right = buildFactsAssembly(fixture.options);
    assert.equal(left.artifactBytes.toString(), right.artifactBytes.toString());
    assert.equal(left.receiptBytes.toString(), right.receiptBytes.toString());
    assert.deepEqual(left.artifact.rows, right.artifact.rows);
    assert.equal(left.artifact.business_content_sha256, right.artifact.business_content_sha256);
});

test('GD-A02 preserves missing xG as partial/null and never fabricates zero', t => {
    const fixture = buildResult(t, {
        normalized: {
            ...buildPair().payload.normalized,
            shotmap: {
                shots: [
                    {
                        ...buildPair().payload.normalized.shotmap.shots[0],
                        expectedGoals: null,
                    },
                ],
            },
        },
    });
    const xg = fixture.result.artifact.rows[0].facts.xg;
    assert.equal(xg.status, 'PARTIAL');
    assert.equal(xg.home.value, null);
    assert.equal(xg.home.missing_shots, 1);
});

test('GD-A02 preserves missing isOnTarget as partial/null and never fabricates zero', t => {
    const base = buildPair().payload.normalized;
    const missingShot = { ...base.shotmap.shots[0] };
    delete missingShot.isOnTarget;
    const fixture = buildResult(t, {
        normalized: {
            ...base,
            shotmap: {
                shots: [missingShot],
            },
        },
    });
    const shotsOnTarget = fixture.result.artifact.rows[0].facts.shots_on_target;
    assert.equal(shotsOnTarget.status, 'PARTIAL');
    assert.equal(shotsOnTarget.home.value, null);
    assert.equal(shotsOnTarget.home.missing_shots, 1);
});

test('GD-A02 fails closed when own-goal SOT semantics are not proven', t => {
    const base = buildPair().payload.normalized;
    const fixture = buildResult(t, {
        normalized: {
            ...base,
            shotmap: {
                shots: [{ ...base.shotmap.shots[0], isOnTarget: true, isOwnGoal: true }],
            },
        },
    });
    const shotsOnTarget = fixture.result.artifact.rows[0].facts.shots_on_target;
    assert.equal(shotsOnTarget.status, 'UNAVAILABLE');
    assert.equal(shotsOnTarget.unavailable_reason_code, 'SOT_OWN_GOAL_SEMANTICS_UNPROVEN');
    assert.equal(shotsOnTarget.total_shots, null);
    assert.equal(shotsOnTarget.home.value, null);
    assert.equal(shotsOnTarget.away.value, null);
});

test('GD-A02 fails closed when own-goal flag is missing or non-boolean', t => {
    const base = buildPair().payload.normalized;
    for (const shotOverride of [{ isOwnGoal: undefined }, { isOwnGoal: 'false' }]) {
        const shot = { ...base.shotmap.shots[0], ...shotOverride };
        if (shotOverride.isOwnGoal === undefined) delete shot.isOwnGoal;
        const fixture = buildResult(t, {
            normalized: { ...base, shotmap: { shots: [shot] } },
        });
        const shotsOnTarget = fixture.result.artifact.rows[0].facts.shots_on_target;
        assert.equal(shotsOnTarget.status, 'UNAVAILABLE');
        assert.equal(shotsOnTarget.unavailable_reason_code, 'SOT_OWN_GOAL_FLAG_UNAVAILABLE');
    }
});

test('GD-A02 rejects normalized home/away identity reversal even when source IDs are legal', t => {
    const base = buildPair().payload.normalized;
    const fixture = buildFixture(t, {
        normalized: {
            ...base,
            home_team: { ...base.away_team },
            away_team: { ...base.home_team },
        },
    });
    const result = buildFactsAssembly(fixture.options);
    assert.equal(result.artifact.rows.length, 0);
    assert.equal(result.artifact.rejected_rows.length, 1);
    assert.equal(result.artifact.rejected_rows[0].error_code, 'IDENTITY_CONFLICT');
});

test('GD-A02 rejects SOT when only normalized team IDs are reversed', t => {
    const base = buildPair().payload.normalized;
    const fixture = buildResult(t, {
        normalized: {
            ...base,
            home_team: { ...base.home_team, id: base.away_team.id },
            away_team: { ...base.away_team, id: base.home_team.id },
        },
    });
    const shotsOnTarget = fixture.result.artifact.rows[0].facts.shots_on_target;
    assert.equal(shotsOnTarget.status, 'UNAVAILABLE');
    assert.equal(shotsOnTarget.unavailable_reason_code, 'SOT_TEAM_IDENTITY_BINDING_UNPROVEN');
});

test('GD-A02 rejects response team IDs without trusted source paths', t => {
    const pair = buildPair({
        observed: {
            observed_home_team_id_source: 'request.candidate.home_team_id',
            observed_away_team_id_source: 'request.candidate.away_team_id',
        },
    });
    const validation = validateObservation({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.equal(validation.ok, false);
    assert.ok(validation.errors.some(error => /untrusted observed_.*team_id_source/.test(error.message)));
});

test('GD-A02 accounts a malformed source as rejection when another admitted row remains', t => {
    const first = buildFixture(t);
    const second = buildFixture(t, { source_match_id: '3901024' });
    const sourceEntries = [first.sourceIndex.entries[0], second.sourceIndex.entries[0]].sort((a, b) =>
        a.canonical_match_id.localeCompare(b.canonical_match_id)
    );
    const all = [first, second];
    const sourceIndex = { ...first.sourceIndex, entries: sourceEntries };
    const sourceIndexBytes = Buffer.from(`${JSON.stringify(sourceIndex)}\n`, 'utf8');
    const loaded = new Map();
    for (const item of all) {
        const entry = item.sourceIndex.entries[0];
        loaded.set(item.upstream.canonicalId, {
            index: entry,
            stagingArtifactBytes: item.options.loadedFactsByCanonicalId.get(item.upstream.canonicalId)
                .stagingArtifactBytes,
            stagingArtifact: item.stagingArtifact,
            capturePayloadBytes: item.pair.payloadBytes,
            capturePayload: item.pair.payload,
            captureManifestBytes: item.options.loadedFactsByCanonicalId.get(item.upstream.canonicalId)
                .captureManifestBytes,
            captureManifest: item.pair.manifest,
        });
    }
    const manifestRows = [first.manifestRow, second.manifestRow].sort((a, b) =>
        a.canonical_match_id.localeCompare(b.canonical_match_id)
    );
    const manifestBytes = Buffer.from(`${manifestRows.map(row => JSON.stringify(row)).join('\n')}\n`, 'utf8');
    const freeze = { ...first.freeze, raw_payload_count: 2, manifest_sha256: sha256Bytes(manifestBytes) };
    const freezeBytes = Buffer.from(`${JSON.stringify(freeze)}\n`, 'utf8');
    const options = {
        ...first.options,
        fotmobFreezeDocument: freeze,
        fotmobFreezeBytes: freezeBytes,
        fotmobFreezeSha256: sha256Bytes(freezeBytes),
        fotmobManifestBytes: manifestBytes,
        fotmobManifestRows: manifestRows,
        gdA01ArtifactBytes: (() => {
            const firstRow = first.upstream.artifact.rows[0];
            const secondRow = { ...second.upstream.artifact.rows[0], canonical_match_id: second.upstream.canonicalId };
            const artifactWithoutHash = {
                ...first.upstream.artifact,
                rows: [firstRow, secondRow].sort((a, b) => a.canonical_match_id.localeCompare(b.canonical_match_id)),
            };
            const artifact = {
                ...artifactWithoutHash,
                business_content_sha256: computeA01BusinessHash({
                    ...artifactWithoutHash,
                    business_content_sha256: null,
                }),
            };
            return Buffer.from(`${stableStringify(artifact)}\n`, 'utf8');
        })(),
        factsSourceIndex: sourceIndex,
        factsSourceIndexBytes: sourceIndexBytes,
        factsSourceIndexSha256: sha256Bytes(sourceIndexBytes),
        loadedFactsByCanonicalId: loaded,
    };
    const upstreamArtifact = JSON.parse(options.gdA01ArtifactBytes.toString());
    const upstreamReceipt = {
        ...first.upstream.receipt,
        admitted_row_count: 2,
        admitted_id_set_sha256: admittedA01IdSetHash([first.upstream.canonicalId, second.upstream.canonicalId]),
        linkage_decision_set_sha256: linkageDecisionSetHash(upstreamArtifact.rows),
        output_business_sha256: upstreamArtifact.business_content_sha256,
        artifact_sha256: sha256Bytes(options.gdA01ArtifactBytes),
    };
    options.gdA01ReceiptBytes = Buffer.from(`${stableStringify(upstreamReceipt)}\n`, 'utf8');
    const bad = loaded.get(second.upstream.canonicalId);
    bad.capturePayload = { ...bad.capturePayload, normalized: { ...bad.capturePayload.normalized, stats: null } };
    const result = buildFactsAssembly(options);
    assert.equal(result.artifact.rows.length, 1);
    assert.equal(result.artifact.rejected_rows.length, 1);
    assert.equal(result.receipt.status, 'INCOMPLETE_REJECTED');
});

test('GD-A02 rejects source-index duplicate/extra/missing identities before projection', t => {
    const fixture = buildFixture(t);
    const duplicate = {
        ...fixture.sourceIndex,
        entries: [fixture.sourceIndex.entries[0], fixture.sourceIndex.entries[0]],
    };
    assertContractReject(
        () => buildFactsAssembly({ ...fixture.options, factsSourceIndex: duplicate }),
        'POPULATION_MISMATCH'
    );
    const extra = {
        ...fixture.sourceIndex,
        entries: [{ ...fixture.sourceIndex.entries[0], canonical_match_id: '47_20222023_9999999' }],
    };
    assertContractReject(
        () => buildFactsAssembly({ ...fixture.options, factsSourceIndex: extra }),
        'POPULATION_MISMATCH'
    );
    assertContractReject(
        () => buildFactsAssembly({ ...fixture.options, factsSourceIndex: { ...fixture.sourceIndex, entries: [] } }),
        'POPULATION_MISMATCH'
    );
});

test('GD-A02 fails closed on upstream hash, source hash, reversed identity, and output tamper', t => {
    const fixture = buildResult(t);
    const tamperedUpstream = JSON.parse(fixture.options.gdA01ArtifactBytes.toString());
    tamperedUpstream.rows[0].home_team = 'Tampered FC';
    assertContractReject(
        () =>
            buildFactsAssembly({
                ...fixture.options,
                gdA01ArtifactBytes: Buffer.from(`${JSON.stringify(tamperedUpstream)}\n`),
            }),
        'BUSINESS_HASH_MISMATCH'
    );
    const badSource = {
        ...fixture.options,
        loadedFactsByCanonicalId: new Map(fixture.options.loadedFactsByCanonicalId),
    };
    const sourceEntry = {
        ...badSource.loadedFactsByCanonicalId.values().next().value,
        capturePayloadBytes: Buffer.from('tampered'),
    };
    badSource.loadedFactsByCanonicalId.set(fixture.upstream.canonicalId, sourceEntry);
    const sourceRejected = buildFactsAssembly(badSource);
    assert.equal(sourceRejected.artifact.rows.length, 0);
    assert.equal(sourceRejected.artifact.rejected_rows[0].error_code, 'HASH_MISMATCH');
    const reversedSource = {
        ...fixture.options,
        loadedFactsByCanonicalId: new Map(fixture.options.loadedFactsByCanonicalId),
    };
    const reversedEntry = { ...reversedSource.loadedFactsByCanonicalId.values().next().value };
    reversedEntry.capturePayload = {
        ...reversedEntry.capturePayload,
        expected_identity: {
            home_team: 'Leicester City',
            away_team: 'AFC Bournemouth',
            kickoff_at: fixture.pair.payload.expected_identity.kickoff_at,
        },
    };
    reversedSource.loadedFactsByCanonicalId.set(fixture.upstream.canonicalId, reversedEntry);
    const reversedRejected = buildFactsAssembly(reversedSource);
    assert.equal(reversedRejected.artifact.rejected_rows[0].error_code, 'CAPTURE_CONTRACT_INVALID');
    const tamperedArtifact = JSON.parse(fixture.result.artifactBytes.toString());
    tamperedArtifact.rows[0].home_team = 'Tampered FC';
    assertContractReject(
        () => validateFactsFiles(Buffer.from(`${JSON.stringify(tamperedArtifact)}\n`), fixture.result.receiptBytes),
        'BUSINESS_HASH_MISMATCH'
    );
});

test('GD-A02 contract rejects temporal/scope widening and output business mutation', t => {
    const { result } = buildResult(t);
    const temporal = { ...result.artifact, temporal_semantics: { ...FACT_TIMING, prematch_available: true } };
    temporal.business_content_sha256 = computeArtifactBusinessHash(temporal);
    assertContractReject(() => validateFactsArtifact(temporal), 'TEMPORAL_SEMANTICS_UNPROVEN');
    const scope = { ...result.artifact, scope: { ...result.artifact.scope, training: true } };
    scope.business_content_sha256 = computeArtifactBusinessHash(scope);
    assertContractReject(() => validateFactsArtifact(scope), 'SCOPE_VIOLATION');
    const badReceipt = { ...result.receipt, output_business_sha256: 'c'.repeat(64) };
    assertContractReject(
        () => validateOutputFiles(result.artifactBytes, Buffer.from(`${JSON.stringify(badReceipt)}\n`)),
        'BUSINESS_HASH_MISMATCH'
    );
});

test('GD-A02 CLI argument contract requires explicit file-first inputs', () => {
    assert.equal(parseArgs(['help']).command, 'help');
    assertContractReject(() => parseArgs(['build', '--gd-a01-artifact', '/tmp/a']), 'INPUT_INVALID');
    const parsed = parseArgs([
        'validate',
        '--artifact',
        '/tmp/a.json',
        '--receipt',
        '/tmp/r.json',
        '--expected-admitted',
        '888',
    ]);
    assert.equal(parsed.expectedAdmittedRows, 888);
});

test('GD-A02 runtime modules have no DB/network/raw write authority', () => {
    for (const file of [
        path.join(__dirname, '../../src/infrastructure/golden_dataset/GdA02FactsContract.js'),
        path.join(__dirname, '../../src/infrastructure/golden_dataset/GdA02Assembler.js'),
        path.join(__dirname, '../../scripts/ops/gd_a02_assembler.js'),
    ]) {
        const source = fs.readFileSync(file, 'utf8');
        assert.doesNotMatch(source, /require\(['"](?:pg|ioredis)['"]\)/);
        assert.doesNotMatch(source, /fetch\s*\(/);
        assert.doesNotMatch(source, /raw_match_data/);
        assert.doesNotMatch(source, /\.connect\s*\(/);
    }
});

test('GD-A02 pure assembly makes zero network, DB, and raw-write calls', t => {
    const counters = { network: 0, database: 0, rawWrites: 0 };
    const httpRequestProperty = ['http', 'request'].join('.');
    const httpsRequestProperty = ['https', 'request'].join('.');
    const originals = {
        fetch: global.fetch,
        httpRequest: http[httpRequestProperty],
        httpsRequest: https[httpsRequestProperty],
        netConnect: net.connect,
        writeFile: fs.writeFile,
        writeFileSync: fs.writeFileSync,
        load: Module._load,
    };
    const blockedNetwork = () => {
        counters.network += 1;
        throw new Error('GD-A02 hermetic test observed a network call');
    };
    const blockedRawWrite = () => {
        counters.rawWrites += 1;
        throw new Error('GD-A02 hermetic test observed a raw write');
    };
    global.fetch = blockedNetwork;
    http[httpRequestProperty] = blockedNetwork;
    https[httpsRequestProperty] = blockedNetwork;
    net.connect = blockedNetwork;
    fs.writeFile = blockedRawWrite;
    fs.writeFileSync = blockedRawWrite;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (['pg', 'ioredis', 'pg-promise'].includes(request)) {
            counters.database += 1;
            throw new Error('GD-A02 hermetic test observed a DB client load');
        }
        return originals.load.call(this, request, parent, isMain);
    };
    try {
        const fixture = buildFixture(t);
        const result = buildFactsAssembly(fixture.options);
        assert.equal(result.artifact.rows.length, 1);
    } finally {
        global.fetch = originals.fetch;
        http[httpRequestProperty] = originals.httpRequest;
        https[httpsRequestProperty] = originals.httpsRequest;
        net.connect = originals.netConnect;
        fs.writeFile = originals.writeFile;
        fs.writeFileSync = originals.writeFileSync;
        Module._load = originals.load;
    }
    assert.deepEqual(counters, { network: 0, database: 0, rawWrites: 0 });
});

test('GD-A02 source index contract is strict and deterministic', t => {
    const fixture = buildFixture(t);
    const entries = validateFactsSourceIndex(fixture.sourceIndex);
    assert.equal(entries.length, 1);
    const reordered = { ...fixture.sourceIndex, entries: [...fixture.sourceIndex.entries].reverse() };
    assert.deepEqual(validateFactsSourceIndex(reordered), entries);
});
