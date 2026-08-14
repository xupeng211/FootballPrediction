'use strict';

// lifecycle: permanent；GD-A01 合同/确定性/边界回归测试。
// 只使用 hermetic 内存 fixture；真实 888 验证由任务级 /tmp 离线验证单独完成。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const {
    ASSEMBLY_SCHEMA_VERSION,
    GdA01ContractError,
    RECEIPT_SCHEMA_VERSION,
    STAGE,
    TEMPORAL_CAPABILITY,
    admittedIdSetHash,
    computeArtifactBusinessHash,
    linkageDecisionSetHash,
    validateAssemblyArtifact,
    validateCanonicalCandidateDocument,
    validateFotMobManifestRows,
    validateOddsObservation,
    validateOutputFiles,
    validateProviderContractBinding,
} = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const { buildAssembly } = require('../../src/infrastructure/golden_dataset/GdA01Assembler');
const { decideMatchLink } = require('../../src/infrastructure/odds_staging/matchLinker');
const {
    FOOTBALL_DATA_PROVIDER_CONTRACT,
} = require('../../src/infrastructure/odds_staging/footballDataProviderContract');
const { computeBusinessContentHash } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const historicalOddsVerifier = require('../../scripts/ops/odds_staging/historical_odds_rebuild');
const { runRebuild } = historicalOddsVerifier;
const { parseArgs } = require('../../scripts/ops/gd_a01_assembler');

const HASH = 'a'.repeat(64);
const REVISION = 'b'.repeat(40);

function validObservation(overrides = {}) {
    return {
        schema_version: 'odds-observation/v1',
        source_provider: 'football-data-csv',
        source_url: 'git+repository://fixture/source.csv',
        source_match_id: null,
        competition: 'Premier League',
        season: '2023/2024',
        kickoff_at: '2023-08-05T14:00:00Z',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
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
        raw_record_locator: 'csv:row=1:b365:home',
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
            candidate_ids: ['m1'],
            matched_id: 'm1',
        },
        ...overrides,
    };
}

function validRow(overrides = {}) {
    const observation = validObservation(overrides.observation || {});
    return {
        canonical_match_id: 'm1',
        competition: 'Premier League',
        season: '2023/2024',
        kickoff_at: '2023-08-05T14:00:00Z',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        source_linkage: {
            authority: 'src/infrastructure/odds_staging/matchLinker.js',
            status: 'matched',
            method: 'exact_home_away_kickoff',
            candidate_ids: ['m1'],
            matched_id: 'm1',
        },
        fotmob_frozen_source: {
            snapshot_id: HASH,
            target_population_hash: HASH,
            manifest_sha256: HASH,
            canonical_match_id: 'm1',
            fotmob_match_id: '1234567',
            raw_payload_sha256: HASH,
            capture_semantics: 'POSTMATCH_ONLY',
            capture_timestamp: 'UNPROVEN',
        },
        football_data: {
            source_ids: ['fixture'],
            source_raw_sha256: [HASH],
            observation_count: 1,
            observations: [observation],
        },
        admission: { status: 'ADMITTED', rejection_reason: null },
        ...overrides,
    };
}

function validArtifact(overrides = {}) {
    const artifactWithoutHash = {
        schema_version: ASSEMBLY_SCHEMA_VERSION,
        stage: STAGE,
        artifact_kind: 'spine_odds_assembly',
        source_bindings: {
            canonical_candidate_artifact: { sha256: HASH, business_hash: HASH },
            fotmob_frozen_asset: { sha256: HASH, business_hash: HASH },
            football_data_historical_odds: { sha256: HASH, business_hash: HASH },
            canonical_linkage: { decision_set_sha256: HASH },
            provider_semantic_contract: { contract_id: 'football-data-provider-contract/v1' },
        },
        temporal_capability: TEMPORAL_CAPABILITY,
        rows: [validRow()],
        rejected_rows: [],
        ...overrides,
    };
    return {
        ...artifactWithoutHash,
        business_content_sha256: computeArtifactBusinessHash({ ...artifactWithoutHash, business_content_sha256: null }),
    };
}

function validOutput(overrides = {}) {
    const artifact = validArtifact(overrides.artifact || {});
    const artifactBytes = Buffer.from(`${JSON.stringify(artifact)}\n`, 'utf8');
    const receipt = {
        schema_version: RECEIPT_SCHEMA_VERSION,
        stage: STAGE,
        build_mode: 'file_first',
        code_revision: REVISION,
        source_bindings: artifact.source_bindings,
        admitted_row_count: artifact.rows.length,
        rejected_row_count: artifact.rejected_rows.length,
        admitted_id_set_sha256: admittedIdSetHash(artifact.rows.map(row => row.canonical_match_id)),
        linkage_decision_set_sha256: linkageDecisionSetHash(artifact.rows),
        output_business_sha256: artifact.business_content_sha256,
        artifact_sha256: require('node:crypto').createHash('sha256').update(artifactBytes).digest('hex'),
        temporal_capability: artifact.temporal_capability,
    };
    return { artifact, receipt, artifactBytes, receiptBytes: Buffer.from(`${JSON.stringify(receipt)}\n`, 'utf8') };
}

function rehashArtifact(artifact) {
    return { ...artifact, business_content_sha256: computeArtifactBusinessHash(artifact) };
}

function assertReject(fn, code) {
    assert.throws(fn, error => {
        assert.ok(error instanceof GdA01ContractError || error.code);
        if (code) assert.equal(error.code, code);
        return true;
    });
}

function createHermeticBuildFixture(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gd-a01-test-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const csvPath = path.join(root, 'source.csv');
    const manifestPath = path.join(root, 'source.manifest.json');
    const candidatePath = path.join(root, 'candidates.json');
    const oddsRoot = path.join(root, 'odds');
    const fotmobManifestPath = path.join(root, 'fotmob-manifest.jsonl');
    const freezePath = path.join(root, 'freeze.json');
    fs.mkdirSync(oddsRoot);
    const csv = [
        'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A,B365CH,B365CD,B365CA',
        'fixture,E0,05/08/2023,15:00,Arsenal,Chelsea,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
    ].join('\n');
    fs.writeFileSync(csvPath, `${csv}\n`);
    const candidate = {
        id: '47_20232024_0000001',
        source_provider: 'FotMob',
        source_match_id: '0000001',
        competition: 'Premier League',
        season: '2023/2024',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        kickoff_at: '2023-08-05T14:00:00Z',
    };
    fs.writeFileSync(
        candidatePath,
        `${JSON.stringify({
            schema_version: 'candidate-match-identity/v1',
            snapshot: {
                source_provider: 'FotMob',
                competition: 'Premier League',
                candidate_count: 1,
                business_content_sha256: computeBusinessContentHash([candidate]),
            },
            candidates: [candidate],
        })}\n`
    );
    const rawSha = crypto.createHash('sha256').update(`${csv}\n`).digest('hex');
    fs.writeFileSync(
        manifestPath,
        `${JSON.stringify({
            schema_version: 'odds-source-manifest/v1',
            source_provider: 'football-data-csv',
            acquisition_mode: 'historical_git_recovery',
            source_url: 'git+repository://fixture/source.csv',
            declared_upstream_url: null,
            source_match_id: null,
            captured_at: null,
            capture_time_status: 'unknown',
            recovered_at: '2026-08-09T06:15:00Z',
            source_timezone: 'unknown',
            raw_path: csvPath,
            raw_media_type: 'text/csv',
            raw_size_bytes: Buffer.byteLength(`${csv}\n`),
            raw_sha256: rawSha,
            adapter: 'football-data-csv',
            adapter_version: '1.3.0',
            provenance_status: 'declared',
            upstream_provenance_status: 'unverified',
            license_status: 'unverified',
            repository_provenance: {
                repository: 'fixture',
                commit_sha: 'a'.repeat(40),
                blob_sha: 'b'.repeat(40),
                path: 'tests/fixtures/source.csv',
                commit_timestamp: '2026-08-09T00:00:00Z',
            },
            kickoff_time_interpretation: {
                status: 'derived',
                timezone: 'Europe/London',
                method: 'source_local_calendar_time',
                evidence_level: 'empirical_cross_source',
                official_source_declaration: false,
                evidence_reference: 'GD-A01 hermetic fixture',
                allowed_competitions: ['Premier League'],
                allowed_seasons: ['2023/2024'],
            },
            provider_contract: { ...FOOTBALL_DATA_PROVIDER_CONTRACT, applicable: true },
        })}\n`
    );
    const mRow = {
        asset_manifest_schema: 'fotmob-888-raw-asset-manifest/v1',
        canonical_match_id: candidate.id,
        capture_timestamp_if_available: '',
        fotmob_match_id: candidate.source_match_id,
        kickoff_at: candidate.kickoff_at,
        raw_payload_sha256: 'c'.repeat(64),
        season: candidate.season,
        snapshot_id: 'd'.repeat(64),
        source_provider: 'FotMob',
        target_population_hash: 'e'.repeat(64),
    };
    const fotmobManifest = `${JSON.stringify(mRow)}\n`;
    fs.writeFileSync(fotmobManifestPath, fotmobManifest);
    fs.writeFileSync(
        freezePath,
        `${JSON.stringify({
            schema: 'fotmob-888-asset-freeze/v1',
            snapshot_id: mRow.snapshot_id,
            created_at_utc: '2026-08-11T03:00:00Z',
            target_population_hash: mRow.target_population_hash,
            manifest_sha256: crypto.createHash('sha256').update(fotmobManifest).digest('hex'),
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
        })}\n`
    );
    fs.writeFileSync(
        path.join(root, 'sources.json'),
        JSON.stringify({
            schema_version: 'm3-historical-odds-rebuild-bundle/v1',
            sources: [{ id: 'fixture', csv: 'source.csv', manifest: 'source.manifest.json' }],
        })
    );
    runRebuild({ bundle: root, candidates: candidatePath, emitDir: oddsRoot, ingestedAt: '2026-08-09T06:15:00Z' });
    return { root, candidatePath, freezePath, fotmobManifestPath, oddsRoot };
}

test('GD-A01 contract accepts a valid spine+odds artifact and receipt', () => {
    const output = validOutput();
    const result = validateOutputFiles(output.artifactBytes, output.receiptBytes);
    assert.equal(result.artifact.rows.length, 1);
    assert.equal(result.receipt.code_revision, REVISION);
});

test('GD-A01 deterministic artifact/receipt bytes are stable', () => {
    const left = validOutput();
    const right = validOutput();
    assert.deepEqual(left.artifact, right.artifact);
    assert.deepEqual(left.receipt, right.receipt);
    assert.equal(left.artifactBytes.toString(), right.artifactBytes.toString());
    assert.equal(left.receiptBytes.toString(), right.receiptBytes.toString());
});

test('GD-A01 assembler build and receipt are deterministic on a hermetic offline M3 fixture', t => {
    const fixture = createHermeticBuildFixture(t);
    const options = {
        spinePath: fixture.candidatePath,
        fotmobFreezePath: fixture.freezePath,
        fotmobManifestPath: fixture.fotmobManifestPath,
        oddsRootPath: fixture.oddsRoot,
        codeRevision: REVISION,
        expectedAdmittedRows: 1,
    };
    const left = buildAssembly(options, { historicalOddsVerifier });
    const right = buildAssembly(options, { historicalOddsVerifier });
    assert.equal(left.artifact.rows.length, 1);
    assert.equal(left.artifact.rejected_rows.length, 0);
    assert.equal(left.artifactBytes.toString(), right.artifactBytes.toString());
    assert.equal(left.receiptBytes.toString(), right.receiptBytes.toString());
    assert.equal(
        validateOutputFiles(left.artifactBytes, left.receiptBytes).receipt.population_profile.expected_admitted_rows,
        1
    );
});

test('GD-A01 rejects malformed schema and unsupported versions', () => {
    const output = validOutput();
    const malformed = { ...output.artifact, rows: null };
    assertReject(() => validateAssemblyArtifact(malformed));
    assertReject(
        () =>
            validateAssemblyArtifact({ ...output.artifact, schema_version: 'golden-dataset-v1-assembly-artifact/v99' }),
        'UNSUPPORTED_VERSION'
    );
});

test('GD-A01 rejects a missing manifest path at the CLI boundary', () => {
    assertReject(
        () =>
            parseArgs([
                'build',
                '--spine',
                '/tmp/spine.json',
                '--fotmob-freeze',
                '/tmp/freeze.json',
                '--odds-root',
                '/tmp/odds',
                '--output',
                '/tmp/out.json',
                '--receipt',
                '/tmp/receipt.json',
                '--code-revision',
                REVISION,
            ]),
        'INPUT_INVALID'
    );
});

test('GD-A01 rejects one-byte artifact mutation and receipt/business tamper', () => {
    const output = validOutput();
    const appended = Buffer.concat([output.artifactBytes, Buffer.from(' ', 'utf8')]);
    assertReject(() => validateOutputFiles(appended, output.receiptBytes), 'ARTIFACT_HASH_MISMATCH');
    const tamperedReceipt = { ...output.receipt, output_business_sha256: 'd'.repeat(64) };
    assertReject(
        () => validateOutputFiles(output.artifactBytes, Buffer.from(`${JSON.stringify(tamperedReceipt)}\n`)),
        'BUSINESS_HASH_MISMATCH'
    );
});

test('GD-A01 rejects duplicate canonical identity, missing link, ambiguous link, and conflict link', () => {
    const output = validOutput();
    const duplicate = rehashArtifact({ ...output.artifact, rows: [output.artifact.rows[0], output.artifact.rows[0]] });
    assertReject(() => validateAssemblyArtifact(duplicate));
    for (const linkage of [
        { status: 'unmatched', method: 'no_local_candidate', candidate_ids: [], matched_id: null },
        { status: 'ambiguous', method: 'candidate_identity_conflict', candidate_ids: ['m1', 'm2'], matched_id: null },
        { status: 'ambiguous', method: 'source_match_id_identity_conflict', candidate_ids: ['m1'], matched_id: null },
    ]) {
        const row = { ...output.artifact.rows[0], source_linkage: linkage };
        const artifact = rehashArtifact({ ...output.artifact, rows: [row] });
        assertReject(() => validateAssemblyArtifact(artifact), 'LINKAGE_NOT_EXACT');
    }
});

test('existing matchLinker rejects home/away reversal, kickoff mismatch, and ambiguous candidates', () => {
    const candidate = {
        id: 'm1',
        source_provider: 'FotMob',
        source_match_id: '1234567',
        competition: 'Premier League',
        season: '2023/2024',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        kickoff_at: '2023-08-05T14:00:00Z',
    };
    const base = { ...validObservation(), source_provider: 'football-data-csv' };
    assert.equal(
        decideMatchLink({ ...base, home_team: 'Chelsea', away_team: 'Arsenal' }, [candidate]).status,
        'ambiguous'
    );
    assert.equal(decideMatchLink({ ...base, kickoff_at: '2023-08-05T14:30:00Z' }, [candidate]).status, 'unmatched');
    const duplicate = { ...candidate, id: 'm2' };
    assert.equal(decideMatchLink(base, [candidate, duplicate]).status, 'ambiguous');
    assert.equal(decideMatchLink({ ...base, match_link: undefined }, []).status, 'unmatched');
});

test('GD-A01 rejects provider contract mismatch and semantic closing timestamp claims', () => {
    const providerReceipt = {
        provider_semantic_contract: {
            contract_id: 'wrong/v1',
            provider_id: 'football-data.co.uk',
            evidence_type: 'primary_provider_documentation',
            effective_from_season: '2019/20',
            exact_observation_timestamp_available: false,
            exact_capture_timestamp_available: false,
        },
        evaluation_readiness: { strict_decision_time_value_evaluation_ready: 'NO' },
    };
    assertReject(() => validateProviderContractBinding(providerReceipt), 'PROVIDER_CONTRACT_MISMATCH');
    assertReject(
        () =>
            validateOddsObservation(
                validObservation({
                    provider_collection_phase: 'closing',
                    snapshot_type: 'closing',
                    captured_at: '2023-08-05T13:00:00Z',
                }),
                'closing'
            ),
        'TEMPORAL_SEMANTICS_UNPROVEN'
    );
});

test('GD-A01 canonical candidate hash and FotMob manifest identity are fail-closed', () => {
    const candidates = [
        {
            id: 'm1',
            source_provider: 'FotMob',
            source_match_id: '1234567',
            competition: 'Premier League',
            season: '2023/2024',
            home_team: 'Arsenal',
            away_team: 'Chelsea',
            kickoff_at: '2023-08-05T14:00:00Z',
        },
    ];
    const {
        computeV1IdentityProjectionHash,
    } = require('../../src/infrastructure/canonical/CanonicalInventoryContract');
    const document = {
        schema_version: 'candidate-match-identity/v1',
        snapshot: {
            source_provider: 'FotMob',
            competition: 'Premier League',
            candidate_count: 1,
            business_content_sha256: computeV1IdentityProjectionHash(candidates),
        },
        candidates,
    };
    const validated = validateCanonicalCandidateDocument(document);
    assert.equal(validated.candidates.length, 1);
    assertReject(
        () =>
            validateCanonicalCandidateDocument({
                ...document,
                snapshot: { ...document.snapshot, business_content_sha256: 'e'.repeat(64) },
            }),
        'BUSINESS_HASH_MISMATCH'
    );
    const freeze = { snapshot_id: HASH, target_population_hash: HASH, raw_payload_count: 1 };
    const row = {
        asset_manifest_schema: 'fotmob-888-raw-asset-manifest/v1',
        canonical_match_id: 'm1',
        capture_timestamp_if_available: '',
        fotmob_match_id: '1234567',
        kickoff_at: '2023-08-05T14:00:00Z',
        raw_payload_sha256: HASH,
        season: '2023/2024',
        snapshot_id: HASH,
        source_provider: 'FotMob',
        target_population_hash: HASH,
    };
    assert.equal(validateFotMobManifestRows([row], freeze, validated.byId).length, 1);
    assertReject(() => validateFotMobManifestRows([], freeze, validated.byId), 'POPULATION_MISMATCH');
});

test('GD-A01 output validation rejects silent population shrink when an explicit expectation is applied by the builder profile', () => {
    const output = validOutput();
    assert.equal(output.artifact.rows.length, 1);
    assertReject(() => validateAssemblyArtifact(output.artifact, { expectedAdmittedRows: 888 }), 'POPULATION_MISMATCH');
});

test('GD-A01 output order is stable and reordering is rejected', () => {
    const output = validOutput();
    const row = output.artifact.rows[0];
    const reorderedObservation = { ...row.football_data.observations[0], raw_record_locator: 'csv:row=0:b365:home' };
    const badRow = {
        ...row,
        football_data: {
            ...row.football_data,
            observations: [row.football_data.observations[0], reorderedObservation],
        },
    };
    assertReject(() => validateAssemblyArtifact(rehashArtifact({ ...output.artifact, rows: [badRow] })));
});

test('GD-A01 production modules have no DB/network/external-design runtime dependency and no import side effect', () => {
    const files = [
        path.join(__dirname, '../../src/infrastructure/golden_dataset/GdA01AssemblyContract.js'),
        path.join(__dirname, '../../src/infrastructure/golden_dataset/GdA01Assembler.js'),
        path.join(__dirname, '../../scripts/ops/gd_a01_assembler.js'),
    ];
    for (const file of files) {
        const source = fs.readFileSync(file, 'utf8');
        assert.doesNotMatch(source, /require\(['"](?:pg|ioredis)['"]\)/);
        assert.doesNotMatch(source, /fetch\s*\(/);
        assert.doesNotMatch(source, /~\/\.claude\/audits/);
    }
    assert.doesNotThrow(() => require('../../src/infrastructure/golden_dataset/GdA01Assembler'));
});
