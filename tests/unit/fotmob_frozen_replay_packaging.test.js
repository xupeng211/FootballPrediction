'use strict';

// Offline-only coverage for the Stage-A bridge.  These tests exercise the
// production builder with real standard tar.gz fixtures and the official
// staging source-index contract; no provider or database is reachable.

global.fetch = () => { throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST'); };

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { buildReplaySourceIndex, sha256, assertOutputIsolation } = require('../../src/infrastructure/fotmob/FotMobFrozenReplayPackaging');
const { parseArgs } = require('../../scripts/ops/fotmob_frozen_replay_packaging');
const { validateSourceIndex } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
const { buildPair, writeFixtureArchive } = require('../helpers/fotmobDetailStagingFixtures');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
function temp() { return fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-replay-package-')); }
function write(file, value) { fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`); }

function setup(options = {}) {
    const dir = temp();
    const pairs = [
        { id: '3901023', pair: buildPair({ source_match_id: '3901023', candidate_id: '47_20222023_3901023' }) },
        { id: '3901024', pair: buildPair({ source_match_id: '3901024', candidate_id: '47_20222023_3901024' }) },
    ];
    const archive = writeFixtureArchive(dir, [{ sourceMatchId: pairs[0].id, pair: pairs[0].pair }], { packageId: 'existing' });
    const loosePayload = path.join(dir, 'loose.payload.json');
    const looseManifest = path.join(dir, 'loose.manifest.json');
    fs.writeFileSync(loosePayload, pairs[1].pair.payloadBytes);
    fs.writeFileSync(looseManifest, `${JSON.stringify(pairs[1].pair.manifest, null, 2)}\n`);
    const snapshotId = 'a'.repeat(64);
    const populationHash = 'b'.repeat(64);
    const assets = pairs.map(({ id, pair }) => ({
        asset_manifest_schema: 'fotmob-888-raw-asset-manifest/v1',
        canonical_match_id: pair.payload.candidate_id,
        capture_timestamp_if_available: '',
        fotmob_match_id: id,
        kickoff_at: pair.payload.expected_identity.kickoff_at,
        raw_payload_sha256: sha256(pair.payloadBytes),
        season: pair.payload.season,
        snapshot_id: snapshotId,
        source_provider: 'FotMob',
        target_population_hash: populationHash,
    }));
    const assetPath = path.join(dir, 'assets.jsonl');
    const assetBytes = Buffer.from(assets.map(row => JSON.stringify(row)).join('\n') + '\n');
    fs.writeFileSync(assetPath, assetBytes);
    const freezePath = path.join(dir, 'freeze.json');
    write(freezePath, {
        schema: 'fotmob-888-asset-freeze/v1', snapshot_id: snapshotId,
        target_population_hash: populationHash, manifest_sha256: sha256(assetBytes),
        raw_payload_count: 2, missing: 0, extra: 0, duplicate: 0,
        full_raw_retention: true, raw_mutability: 'immutable', acquisition_status: 'complete',
        golden_dataset_status: 'not_complete', live_fotmob_network: false, db_writes_performed: false,
    });
    const inputPath = path.join(dir, 'input.json');
    write(inputPath, {
        schema_version: 'fotmob-frozen-replay-package-input/v1',
        entries: [
            { kind: 'EXISTING_PACKAGE', fotmob_match_id: pairs[0].id, canonical_match_id: pairs[0].pair.payload.candidate_id, payload_path: archive.payloadFiles[pairs[0].id], manifest_path: archive.manifestFiles[pairs[0].id], package_id: 'existing', archive_path: archive.archivePath, archive_sha256: archive.archiveSha256, payload_member: archive.payloadMembers[pairs[0].id], manifest_member: archive.manifestMembers[pairs[0].id] },
            { kind: 'HISTORICAL_REUSE_LOOSE', source_provenance: 'HISTORICAL_REUSE', fotmob_match_id: pairs[1].id, canonical_match_id: pairs[1].pair.payload.candidate_id, payload_path: loosePayload, manifest_path: looseManifest },
        ],
    });
    return { dir, freezePath, assetPath, inputPath, outputBase: temp() };
}

function build(fixture, name) {
    return buildReplaySourceIndex({ freezePath: fixture.freezePath, assetManifestPath: fixture.assetPath, inputPath: fixture.inputPath, outputRoot: path.join(fixture.outputBase, name), repositoryRoot: REPO_ROOT });
}

test('PR1888-P1-001/P2-002 packages only frozen-authority-bound valid observations', () => {
    const fixture = setup();
    const result = build(fixture, 'out-a');
    assert.equal(result.summary.existing_packaged_count, 1);
    assert.equal(result.summary.newly_packaged_historical_reuse_count, 1);
    assert.equal(result.sourceIndex.entries.length, 2);
    assert.equal(validateSourceIndex(result.sourceIndex).ok, true);
    assert.ok(result.sourceIndex.archive_bindings.existing);
    assert.ok(result.sourceIndex.archive_bindings['historical-reuse-replay']);
    assert.equal(fs.existsSync(path.join(fixture.outputBase, 'out-a', 'packages', 'historical-reuse-replay.tar.gz')), true);
});

test('PR1888-P2-003 publishes deterministically into an atomic output tree', () => {
    const fixture = setup();
    const a = build(fixture, 'out-a');
    const b = build(fixture, 'out-b');
    const project = value => ({ ...value, archive_bindings: Object.fromEntries(Object.entries(value.archive_bindings).map(([id, binding]) => [id, { ...binding, path: path.basename(binding.path), receipt: path.basename(binding.receipt) }])) , entries: value.entries.map(entry => ({ ...entry, payload_file: path.basename(entry.payload_file), manifest_file: path.basename(entry.manifest_file) })) });
    assert.deepEqual(project(a.sourceIndex), project(b.sourceIndex));
    assert.equal(a.summary.source_ids_sha256, b.summary.source_ids_sha256);
    assert.equal(sha256(fs.readFileSync(path.join(fixture.outputBase, 'out-a', 'packages', 'historical-reuse-replay.tar.gz'))), sha256(fs.readFileSync(path.join(fixture.outputBase, 'out-b', 'packages', 'historical-reuse-replay.tar.gz'))));
});

test('PR1888-P2-002 fails closed for malformed provenance/hash and P2-003 output conflict', () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    input.entries[1].source_provenance = 'FORMAL_CAPTURE';
    write(fixture.inputPath, input);
    assert.throws(() => build(fixture, 'bad-provenance'), /source_provenance/);
    input.entries[1].source_provenance = 'HISTORICAL_REUSE';
    write(fixture.inputPath, input);
    const asset = fs.readFileSync(fixture.assetPath, 'utf8').split('\n').filter(Boolean).map(JSON.parse);
    asset[1].raw_payload_sha256 = '0'.repeat(64);
    const changedAssetBytes = Buffer.from(asset.map(JSON.stringify).join('\n') + '\n');
    fs.writeFileSync(fixture.assetPath, changedAssetBytes);
    const freeze = JSON.parse(fs.readFileSync(fixture.freezePath));
    freeze.manifest_sha256 = sha256(changedAssetBytes);
    write(fixture.freezePath, freeze);
    assert.throws(() => build(fixture, 'bad-hash'), /payload SHA mismatch/);
    asset[1].raw_payload_sha256 = sha256(fs.readFileSync(input.entries[1].payload_path));
    const restoredAssetBytes = Buffer.from(asset.map(JSON.stringify).join('\n') + '\n');
    fs.writeFileSync(fixture.assetPath, restoredAssetBytes);
    freeze.manifest_sha256 = sha256(restoredAssetBytes);
    write(fixture.freezePath, freeze);
    build(fixture, 'out');
    assert.throws(() => build(fixture, 'out'), /output root already exists/);
});

test('PR1888-P1-001 fails closed for duplicate IDs, missing entries, and symlinked input', { skip: process.platform === 'win32' }, () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    input.entries.push({ ...input.entries[1] });
    write(fixture.inputPath, input);
    assert.throws(() => build(fixture, 'duplicate'), /duplicate input/);
    input.entries.pop(); input.entries.pop();
    write(fixture.inputPath, input);
    assert.throws(() => build(fixture, 'missing'), /population mismatch/);
    const clean = setup();
    const data = JSON.parse(fs.readFileSync(clean.inputPath));
    const link = path.join(clean.dir, 'payload-link.json');
    fs.symlinkSync(data.entries[1].payload_path, link);
    data.entries[1].payload_path = link;
    write(clean.inputPath, data);
    assert.throws(() => build(clean, 'symlink'), /symlink/);
});

test('PR1888-P1-002 rejects equal/ancestor/descendant evidence overlap but allows similar prefixes', () => {
    const root = temp();
    const evidence = path.join(root, 'snapshot');
    fs.mkdirSync(path.join(evidence, 'raw'), { recursive: true });
    const freeze = path.join(evidence, 'freeze.json'); fs.writeFileSync(freeze, '{}');
    assert.throws(() => assertOutputIsolation(path.join(evidence, 'derived'), [freeze], REPO_ROOT), /overlaps/);
    assert.throws(() => assertOutputIsolation(evidence, [freeze], REPO_ROOT), /overlaps/);
    assert.throws(() => assertOutputIsolation(root, [freeze], REPO_ROOT), /overlaps/);
    const sibling = path.join(root, 'snapshot-derived');
    assert.equal(assertOutputIsolation(sibling, [freeze], REPO_ROOT), sibling);
});

test('PR1888-P2-001 rejects conflicting archive declarations before archive consumption', () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    const alternate = path.join(fixture.dir, 'alternate.tar.gz');
    fs.copyFileSync(input.entries[0].archive_path, alternate);
    input.entries[1].kind = 'EXISTING_PACKAGE';
    input.entries[1].package_id = 'existing';
    input.entries[1].archive_path = alternate;
    input.entries[1].archive_sha256 = sha256(fs.readFileSync(alternate));
    input.entries[1].payload_path = input.entries[0].payload_path;
    input.entries[1].manifest_path = input.entries[0].manifest_path;
    input.entries[1].payload_member = input.entries[0].payload_member;
    input.entries[1].manifest_member = input.entries[0].manifest_member;
    write(fixture.inputPath, input);
    assert.throws(() => build(fixture, 'conflict'), /conflicting archive binding/);
});

test('PR1888-P2-001 permits repeated declarations of the same canonical archive for one package ID', () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    const firstPair = buildPair({ source_match_id: '3901023', candidate_id: '47_20222023_3901023' });
    const secondPair = buildPair({ source_match_id: '3901024', candidate_id: '47_20222023_3901024' });
    const archive = writeFixtureArchive(fixture.dir, [
        { sourceMatchId: '3901023', pair: firstPair },
        { sourceMatchId: '3901024', pair: secondPair },
    ], { packageId: 'existing' });
    input.entries = [
        { ...input.entries[0], payload_path: archive.payloadFiles['3901023'], manifest_path: archive.manifestFiles['3901023'], archive_path: archive.archivePath, archive_sha256: archive.archiveSha256, payload_member: archive.payloadMembers['3901023'], manifest_member: archive.manifestMembers['3901023'] },
        { kind: 'EXISTING_PACKAGE', fotmob_match_id: '3901024', canonical_match_id: secondPair.payload.candidate_id, payload_path: archive.payloadFiles['3901024'], manifest_path: archive.manifestFiles['3901024'], package_id: 'existing', archive_path: archive.archivePath, archive_sha256: archive.archiveSha256, payload_member: archive.payloadMembers['3901024'], manifest_member: archive.manifestMembers['3901024'] },
    ];
    write(fixture.inputPath, input);
    const result = build(fixture, 'same-package-canonical-archive');
    assert.deepEqual(Object.keys(result.sourceIndex.archive_bindings), ['existing']);
});

test('PR1888-P2-001 rejects a canonical archive alias across different package IDs before output publication', () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    input.entries[1] = {
        ...input.entries[0],
        fotmob_match_id: input.entries[1].fotmob_match_id,
        canonical_match_id: input.entries[1].canonical_match_id,
        package_id: 'other-existing-package',
    };
    write(fixture.inputPath, input);
    const output = path.join(fixture.outputBase, 'cross-package-alias');
    assert.throws(() => build(fixture, 'cross-package-alias'), /canonical archive path is already bound/);
    assert.equal(fs.existsSync(output), false);
});

test('PR1888-P2-001 rejects a symlink archive alias at the input safety gate', { skip: process.platform === 'win32' }, () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    const archiveAlias = path.join(fixture.dir, 'archive-alias.tar.gz');
    fs.symlinkSync(input.entries[0].archive_path, archiveAlias);
    input.entries[1] = {
        ...input.entries[0],
        fotmob_match_id: input.entries[1].fotmob_match_id,
        canonical_match_id: input.entries[1].canonical_match_id,
        package_id: 'other-existing-package',
        archive_path: archiveAlias,
    };
    write(fixture.inputPath, input);
    assert.throws(() => build(fixture, 'symlink-archive-alias'), /symlink/);
    assert.equal(fs.existsSync(path.join(fixture.outputBase, 'symlink-archive-alias')), false);
});

test('PR1888-P2-001 permits distinct physical archives for different package IDs', () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    const secondPair = buildPair({ source_match_id: '3901024', candidate_id: '47_20222023_3901024' });
    const secondArchive = writeFixtureArchive(fixture.dir, [{ sourceMatchId: '3901024', pair: secondPair }], { packageId: 'other-existing-package' });
    input.entries[1] = {
        kind: 'EXISTING_PACKAGE',
        fotmob_match_id: '3901024',
        canonical_match_id: secondPair.payload.candidate_id,
        payload_path: secondArchive.payloadFiles['3901024'],
        manifest_path: secondArchive.manifestFiles['3901024'],
        package_id: 'other-existing-package',
        archive_path: secondArchive.archivePath,
        archive_sha256: secondArchive.archiveSha256,
        payload_member: secondArchive.payloadMembers['3901024'],
        manifest_member: secondArchive.manifestMembers['3901024'],
    };
    write(fixture.inputPath, input);
    const result = build(fixture, 'distinct-archives');
    assert.equal(result.sourceIndex.entries.length, 2);
    assert.deepEqual(Object.keys(result.sourceIndex.archive_bindings).sort(), ['existing', 'other-existing-package']);
});

test('NEW-P2-001 rejects an existing package that collides with the generated historical reuse ID before publication', () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    input.entries[0].package_id = 'historical-reuse-replay';
    write(fixture.inputPath, input);
    const output = path.join(fixture.outputBase, 'reserved-package-id');
    assert.throws(() => build(fixture, 'reserved-package-id'), /reserves generated package namespace/);
    assert.equal(fs.existsSync(output), false);
});

test('PR1888-P2-004 strict CLI parser enforces allowlist and exactly-once required keys', () => {
    const valid = ['--freeze=/tmp/a', '--asset-manifest=/tmp/m', '--input=/tmp/i=a.json', '--output-root=/tmp/o'];
    assert.deepEqual(parseArgs(valid)['input'], '/tmp/i=a.json');
    assert.throws(() => parseArgs([...valid, '--freeze=/tmp/b']), /duplicate/);
    assert.throws(() => parseArgs([...valid, '--foo=bar']), /unknown/);
    assert.throws(() => parseArgs(['foo']), /expected/);
    assert.throws(() => parseArgs(['--freeze']), /expected/);
    assert.throws(() => parseArgs(['--=abc']), /unknown or invalid/);
});
