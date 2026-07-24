'use strict';

// lifecycle: permanent；D4E 唯一允许的确定性合成 fixture 到既有 staging 合同的受限转换。

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { appendObservationSignals, createCanonicalObservation, stableCanonicalize } = require('./contracts');
const { validateObservation } = require('./validators');

const FIXTURE_RELATIVE_PATH = 'tests/fixtures/odds_staging/m3_d4e_synthetic_v1.jsonl';
const FIXTURE_VERSION = 'm3-d4e-synthetic-v1';
const SOURCE_PROVIDER = 'm3-d4e-synthetic';
const CANDIDATE_MATCH_ID = 'm3-d4e-local-candidate-001';

function sha256(buffer) { return crypto.createHash('sha256').update(buffer).digest('hex'); }

function readFixture(repositoryRoot) {
    const absolutePath = path.join(repositoryRoot, FIXTURE_RELATIVE_PATH);
    const raw = fs.readFileSync(absolutePath);
    const lines = raw.toString('utf8').trim().split('\n');
    const rows = lines.map((line, index) => ({ ...JSON.parse(line), row_number: index + 1 }));
    if (rows.length !== 9) throw new Error('D4E fixture must contain exactly nine rows');
    return { absolutePath, rows, content_hash: sha256(raw), size: raw.length };
}

function toObservation(row, sourceHash) {
    const observation = createCanonicalObservation({
        source_provider: SOURCE_PROVIDER,
        source_url: 'synthetic://m3-d4e/fixture-v1',
        source_match_id: 'm3-d4e-fixture-001',
        competition: 'M3 D4E Synthetic League', season: '2099/2100',
        kickoff_at: '2099-01-03T12:00:00Z', home_team: 'M3 D4E Synthetic Home', away_team: 'M3 D4E Synthetic Away',
        bookmaker: 'M3 D4E FixtureBook', bookmaker_source_id: 'm3-d4e-fixture-book', market: '1X2',
        selection: row.selection, decimal_odds: row.decimal_odds, snapshot_type: row.snapshot_type,
        source_observed_at: row.source_observed_at, captured_at: '2099-01-01T00:00:00Z', source_timezone: 'UTC',
        raw_sha256: sourceHash, raw_record_locator: `m3-d4e-synthetic:row=${row.row_number}`,
        adapter: 'm3-d4e-synthetic-fixture', adapter_version: '1.0.0', extraction_method: 'deterministic_synthetic_fixture',
        provenance_status: 'fixture', ingested_at: '2099-01-01T00:00:00Z',
        match_link: row.kind === 'ambiguous_identity'
            ? { status: 'ambiguous', method: 'synthetic_ambiguous_identity', candidate_ids: ['m3-d4e-candidate-a', 'm3-d4e-candidate-b'], matched_id: null, evidence: { synthetic: true } }
            : { status: 'matched', method: 'synthetic_local_candidate', candidate_ids: [CANDIDATE_MATCH_ID], matched_id: CANDIDATE_MATCH_ID, evidence: { synthetic: true } },
    });
    const validated = validateObservation(observation);
    return row.kind === 'ambiguous_identity'
        ? appendObservationSignals(validated, ['match_link_ambiguous'], ['match_link_ambiguous'])
        : validated;
}

function quarantineFromObservation(observation) {
    return stableCanonicalize({
        schema_version: 'odds-quarantine/v1', source_provider: observation.source_provider,
        source_match_id: observation.source_match_id, raw_sha256: observation.raw_sha256,
        raw_record_locator: observation.raw_record_locator, adapter: observation.adapter, adapter_version: observation.adapter_version,
        reasons: observation.quarantine_reasons, evidence: { parsed_fields: { idempotency_key: observation.idempotency_key }, match_link: observation.match_link, synthetic: true },
    });
}

function buildD4ESyntheticResult(repositoryRoot) {
    const fixture = readFixture(repositoryRoot);
    const observations = fixture.rows.map(row => toObservation(row, fixture.content_hash));
    const accepted_observations = observations.filter(row => row.quarantine_reasons.length === 0);
    const quarantine = observations.filter(row => row.quarantine_reasons.length > 0).map(quarantineFromObservation);
    if (accepted_observations.length !== 6 || quarantine.length !== 3) throw new Error('D4E fixture must reconcile to 6 accepted and 3 quarantine rows');
    return {
        fixture,
        normalized_manifest: {
            schema_version: 'odds-source-manifest/v1', source_provider: SOURCE_PROVIDER, acquisition_mode: 'deterministic_synthetic_fixture',
            source_url: 'synthetic://m3-d4e/fixture-v1', captured_at: '2099-01-01T00:00:00Z', source_timezone: 'UTC',
            raw_path: fixture.absolutePath, raw_media_type: 'application/jsonl', raw_sha256: fixture.content_hash, raw_size_bytes: fixture.size,
            adapter: 'm3-d4e-synthetic-fixture', adapter_version: '1.0.0', provenance_status: 'fixture', source_match_id: 'm3-d4e-fixture-001',
            competition: 'M3 D4E Synthetic League', season: '2099/2100',
            repository_provenance: { path: FIXTURE_RELATIVE_PATH, synthetic: true, fixture_version: FIXTURE_VERSION, manifest_hash: sha256(Buffer.from(FIXTURE_VERSION + fixture.content_hash)) },
        },
        accepted_observations, quarantine,
        summary: { accepted_count: 6, quarantine_count: 3 },
    };
}

module.exports = { CANDIDATE_MATCH_ID, FIXTURE_RELATIVE_PATH, FIXTURE_VERSION, SOURCE_PROVIDER, buildD4ESyntheticResult, readFixture };
