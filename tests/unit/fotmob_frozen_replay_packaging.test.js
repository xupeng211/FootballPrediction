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

const { buildReplaySourceIndex, sha256 } = require('../../src/infrastructure/fotmob/FotMobFrozenReplayPackaging');
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
    const assets = pairs.map(({ id, pair }) => ({ fotmob_match_id: id, canonical_match_id: pair.payload.candidate_id, raw_payload_sha256: sha256(pair.payloadBytes) }));
    const assetPath = path.join(dir, 'assets.jsonl');
    fs.writeFileSync(assetPath, assets.map(row => JSON.stringify(row)).join('\n') + '\n');
    const freezePath = path.join(dir, 'freeze.json');
    write(freezePath, { raw_payload_count: 2 });
    const inputPath = path.join(dir, 'input.json');
    write(inputPath, {
        schema_version: 'fotmob-frozen-replay-package-input/v1',
        entries: [
            { kind: 'EXISTING_PACKAGE', fotmob_match_id: pairs[0].id, canonical_match_id: pairs[0].pair.payload.candidate_id, payload_path: archive.payloadFiles[pairs[0].id], manifest_path: archive.manifestFiles[pairs[0].id], package_id: 'existing', archive_path: archive.archivePath, archive_sha256: archive.archiveSha256, payload_member: archive.payloadMembers[pairs[0].id], manifest_member: archive.manifestMembers[pairs[0].id] },
            { kind: 'HISTORICAL_REUSE_LOOSE', source_provenance: 'HISTORICAL_REUSE', fotmob_match_id: pairs[1].id, canonical_match_id: pairs[1].pair.payload.candidate_id, payload_path: loosePayload, manifest_path: looseManifest },
        ],
    });
    return { dir, freezePath, assetPath, inputPath };
}

function build(fixture, name) {
    return buildReplaySourceIndex({ freezePath: fixture.freezePath, assetManifestPath: fixture.assetPath, inputPath: fixture.inputPath, outputRoot: path.join(fixture.dir, name), repositoryRoot: REPO_ROOT });
}

test('packages loose historical reuse, reuses an existing archive, and emits an official valid source index', () => {
    const fixture = setup();
    const result = build(fixture, 'out-a');
    assert.equal(result.summary.existing_packaged_count, 1);
    assert.equal(result.summary.newly_packaged_historical_reuse_count, 1);
    assert.equal(result.sourceIndex.entries.length, 2);
    assert.equal(validateSourceIndex(result.sourceIndex).ok, true);
    assert.ok(result.sourceIndex.archive_bindings.existing);
    assert.ok(result.sourceIndex.archive_bindings['historical-reuse-replay']);
    assert.equal(fs.existsSync(path.join(fixture.dir, 'out-a', 'packages', 'historical-reuse-replay.tar.gz')), true);
});

test('is deterministic for independent output roots', () => {
    const fixture = setup();
    const a = build(fixture, 'out-a');
    const b = build(fixture, 'out-b');
    const project = value => ({ ...value, archive_bindings: Object.fromEntries(Object.entries(value.archive_bindings).map(([id, binding]) => [id, { ...binding, path: path.basename(binding.path), receipt: path.basename(binding.receipt) }])) , entries: value.entries.map(entry => ({ ...entry, payload_file: path.basename(entry.payload_file), manifest_file: path.basename(entry.manifest_file) })) });
    assert.deepEqual(project(a.sourceIndex), project(b.sourceIndex));
    assert.equal(a.summary.source_ids_sha256, b.summary.source_ids_sha256);
    assert.equal(sha256(fs.readFileSync(path.join(fixture.dir, 'out-a', 'packages', 'historical-reuse-replay.tar.gz'))), sha256(fs.readFileSync(path.join(fixture.dir, 'out-b', 'packages', 'historical-reuse-replay.tar.gz'))));
});

test('fails closed for malformed historical provenance, hash mismatch, and existing output', () => {
    const fixture = setup();
    const input = JSON.parse(fs.readFileSync(fixture.inputPath));
    input.entries[1].source_provenance = 'FORMAL_CAPTURE';
    write(fixture.inputPath, input);
    assert.throws(() => build(fixture, 'bad-provenance'), /source_provenance/);
    input.entries[1].source_provenance = 'HISTORICAL_REUSE';
    write(fixture.inputPath, input);
    const asset = fs.readFileSync(fixture.assetPath, 'utf8').split('\n').filter(Boolean).map(JSON.parse);
    asset[1].raw_payload_sha256 = '0'.repeat(64);
    fs.writeFileSync(fixture.assetPath, asset.map(JSON.stringify).join('\n') + '\n');
    assert.throws(() => build(fixture, 'bad-hash'), /payload SHA mismatch/);
    asset[1].raw_payload_sha256 = sha256(fs.readFileSync(input.entries[1].payload_path));
    fs.writeFileSync(fixture.assetPath, asset.map(JSON.stringify).join('\n') + '\n');
    build(fixture, 'out');
    assert.throws(() => build(fixture, 'out'), /output root already exists/);
});

test('fails closed for duplicate IDs, missing entries, and symlinked input', { skip: process.platform === 'win32' }, () => {
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
