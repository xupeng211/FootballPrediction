'use strict';

// lifecycle: permanent
// CLI tests for scripts/ops/fotmob_detail_staging.js.
// Fully offline: no network (structurally forbidden), no database.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const { main, parseArgs, runBuild, runValidate, USAGE } = require('../../scripts/ops/fotmob_detail_staging');
const {
    buildPair,
    buildSourceIndex,
    sourceIndexEntry,
    writeFixtureArchive,
    writeFixtureReceipt,
    buildSourceIndexFromArchive,
} = require('../helpers/fotmobDetailStagingFixtures');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const CLI_PATH = path.join(REPO_ROOT, 'scripts/ops/fotmob_detail_staging.js');

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function writePair(dir, pair, sourceMatchId) {
    const payloadFile = path.join(dir, `${sourceMatchId}.payload.json`);
    const manifestFile = path.join(dir, `${sourceMatchId}.manifest.json`);
    fs.writeFileSync(payloadFile, pair.payloadBytes);
    fs.writeFileSync(manifestFile, JSON.stringify(pair.manifest, null, 2) + '\n');
    return { payloadFile, manifestFile };
}

// ── G. CLI / Make ───────────────────────────────────────────

test('G47: build without required args fails closed', async () => {
    await assert.rejects(
        () => runBuild({}),
        err => err.code === 'INPUT_ERROR'
    );
    await assert.rejects(
        () => runBuild({ 'source-index': '/tmp/x.json' }),
        err => err.code === 'INPUT_ERROR'
    );
});

test('G48: help output states the offline boundary explicitly', () => {
    assert.match(USAGE, /OFFLINE ONLY/);
    assert.match(USAGE, /ZERO NETWORK/);
    assert.match(USAGE, /ZERO DATABASE/);
    assert.match(USAGE, /NO MIGRATION/);
    assert.match(USAGE, /NO CAPTURE/);
    assert.match(USAGE, /data-fotmob-detail-staging-/);
});

test('G49: build succeeds end-to-end (source index → artifacts + summary)', async () => {
    const dir = tmpDir('fotmob-cli-build-');
    const pair = buildPair();
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'ten-match' });
    writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'ten-match',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const index = buildSourceIndexFromArchive([{ sourceMatchId: '3901023', pair }], archiveInfo, {
        packageId: 'ten-match',
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const indexFile = path.join(dir, 'source-index.json');
    fs.writeFileSync(indexFile, JSON.stringify(index, null, 2) + '\n');
    const outputRoot = path.join(dir, 'out');

    const result = await runBuild({
        'source-index': indexFile,
        'output-root': outputRoot,
    });
    assert.strictEqual(result.status, 'complete');
    assert.strictEqual(result.accepted_new_count, 1);
    assert.strictEqual(result.rejected_count, 0);
    assert.strictEqual(result.zero_network, true);
    assert.strictEqual(result.zero_database, true);
    assert.ok(fs.readdirSync(outputRoot).some(f => f.startsWith('summary-') && f.endsWith('.json')));
    assert.strictEqual(fs.readdirSync(outputRoot).filter(f => f.startsWith('observation-')).length, 1);
});

test('G50: validate succeeds on a built output root', async () => {
    const dir = tmpDir('fotmob-cli-validate-');
    const pair = buildPair();
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'ten-match' });
    writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'ten-match',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const indexFile = path.join(dir, 'source-index.json');
    fs.writeFileSync(
        indexFile,
        JSON.stringify(
            buildSourceIndexFromArchive([{ sourceMatchId: '3901023', pair }], archiveInfo, {
                packageId: 'ten-match',
                receiptPath: path.join(dir, 'receipt.json'),
            }),
            null,
            2
        ) + '\n'
    );
    const outputRoot = path.join(dir, 'out');
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });

    const result = await runValidate({ 'output-root': outputRoot });
    assert.strictEqual(result.status, 'valid');
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.artifact_check_count, 1);
    assert.strictEqual(result.marker_count, 1);
    assert.strictEqual(result.ledger_version_count, 1);
    assert.strictEqual(result.summary_count, 1);
});

test('G51: tampered artifact fails validate', async () => {
    const dir = tmpDir('fotmob-cli-tamper-');
    const pair = buildPair();
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'ten-match' });
    writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'ten-match',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const indexFile = path.join(dir, 'source-index.json');
    fs.writeFileSync(
        indexFile,
        JSON.stringify(
            buildSourceIndexFromArchive([{ sourceMatchId: '3901023', pair }], archiveInfo, {
                packageId: 'ten-match',
                receiptPath: path.join(dir, 'receipt.json'),
            }),
            null,
            2
        ) + '\n'
    );
    const outputRoot = path.join(dir, 'out');
    const buildResult = await runBuild({
        'source-index': indexFile,
        'output-root': outputRoot,
    });
    const artifactFile =
        buildResult.accepted_new_count === 1
            ? fs.readdirSync(outputRoot).find(f => f.startsWith('observation-'))
            : null;
    assert.ok(artifactFile);
    const artifactPath = path.join(outputRoot, artifactFile);
    const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
    artifact.business_hash = '1'.repeat(64);
    fs.writeFileSync(artifactPath, JSON.stringify(artifact, null, 2) + '\n');

    const result = await runValidate({ 'output-root': outputRoot });
    assert.strictEqual(result.status, 'invalid');
    assert.strictEqual(result.ok, false);
});

test('G51b: single-artifact validate detects tampering', async () => {
    const dir = tmpDir('fotmob-cli-artifact-');
    const pair = buildPair();
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'ten-match' });
    writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'ten-match',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const indexFile = path.join(dir, 'source-index.json');
    fs.writeFileSync(
        indexFile,
        JSON.stringify(
            buildSourceIndexFromArchive([{ sourceMatchId: '3901023', pair }], archiveInfo, {
                packageId: 'ten-match',
                receiptPath: path.join(dir, 'receipt.json'),
            }),
            null,
            2
        ) + '\n'
    );
    const outputRoot = path.join(dir, 'out');
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    const artifactPath = path.join(
        outputRoot,
        fs.readdirSync(outputRoot).find(f => f.startsWith('observation-'))
    );
    const clean = await runValidate({ artifact: artifactPath });
    assert.strictEqual(clean.status, 'valid');
    const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
    artifact.business_hash = '2'.repeat(64);
    fs.writeFileSync(artifactPath, JSON.stringify(artifact, null, 2) + '\n');
    const tampered = await runValidate({ artifact: artifactPath });
    assert.strictEqual(tampered.status, 'invalid');
});

test('G52: Makefile staging targets run container-first via $(COMPOSE_DEV) exec -T dev', () => {
    const makefile = fs.readFileSync(path.join(REPO_ROOT, 'Makefile'), 'utf8');
    const start = makefile.indexOf('data-fotmob-detail-staging-help:');
    assert.ok(start !== -1, 'data-fotmob-detail-staging-help target exists');
    // The block covers all three staging targets (help through validate).
    const end = makefile.indexOf('data-m3-canonical-inventory-preflight:', start);
    const block = makefile.slice(start, end === -1 ? makefile.length : end);
    // P2-5: the authoritative rule is container-first (CLAUDE.md) — every
    // staging command target must go through $(COMPOSE_DEV) exec -T dev;
    // no host-side `node` invocation may be self-declared as an exception.
    assert.match(block, /OFFLINE ONLY|ZERO NETWORK|ZERO DATABASE|NO MIGRATION|NO CAPTURE/);
    const recipes = block.split('\n').filter(line => line.startsWith('\t@'));
    for (const recipe of recipes) {
        // Echo (help prose) and @if guard lines are not business commands.
        // Every line that INVOKES the staging CLI must run container-first.
        if (!recipe.includes('fotmob_detail_staging.js')) continue;
        assert.match(
            recipe,
            /^\t@\$\(COMPOSE_DEV\) exec -T dev node scripts\/ops\/fotmob_detail_staging\.js/,
            `staging command must run inside the dev container: ${recipe.trim()}`
        );
    }
    assert.match(block, /\$\(COMPOSE_DEV\) exec -T dev node scripts\/ops\/fotmob_detail_staging\.js build/);
    assert.match(block, /\$\(COMPOSE_DEV\) exec -T dev node scripts\/ops\/fotmob_detail_staging\.js validate/);
    assert.match(block, /\$\(COMPOSE_DEV\) exec -T dev node scripts\/ops\/fotmob_detail_staging\.js receipt/);
});

test('G52b: data-help lists the three staging targets as offline entries', () => {
    const makefile = fs.readFileSync(path.join(REPO_ROOT, 'Makefile'), 'utf8');
    const helpBlock = makefile.slice(makefile.indexOf('data-help:'));
    for (const target of [
        'data-fotmob-detail-staging-help',
        'data-fotmob-detail-staging-receipt',
        'data-fotmob-detail-staging-build',
        'data-fotmob-detail-staging-validate',
    ]) {
        assert.match(makefile, new RegExp(target));
    }
    assert.match(helpBlock, /fotmob-detail-staging/);
});

test('help subcommand and --help exit cleanly via main()', async () => {
    const help = await main(['help']);
    assert.strictEqual(help, 0);
    const parsed = parseArgs(['--help']);
    assert.strictEqual(parsed.args.help, true);
});

test('unknown subcommand fails closed', async () => {
    await assert.rejects(() => main(['explode']), /unknown subcommand/);
});

test('spawned CLI prints JSON status and exits non-zero on error (no network/DB)', () => {
    const result = spawnSync(process.execPath, [CLI_PATH, 'build'], {
        encoding: 'utf8',
        timeout: 30000,
    });
    assert.notStrictEqual(result.status, 0);
    const parsed = JSON.parse(result.stdout);
    assert.strictEqual(parsed.status, 'blocked');
    assert.strictEqual(parsed.zero_network, true);
    assert.strictEqual(parsed.zero_database, true);
});

// ── FINDING_2 end-to-end: new-observation lifecycle (offline) ──

test('E2E: FIRST_IMPORT → ACCEPTED_NEW; SECOND_LEGAL → REPEAT_EQUIVALENT (old artifact byte-identical); THIRD_EXACT_REPLAY → REPEAT_EXACT with zero new artifacts', async () => {
    const dir = tmpDir('fotmob-e2e-');
    const outputRoot = path.join(dir, 'out');

    const sha = p => require('node:crypto').createHash('sha256').update(fs.readFileSync(p)).digest('hex');

    const pair1v1 = buildPair({ source_match_id: '3901023' });
    const pair1v2 = buildPair({
        source_match_id: '3901023',
        normalized: { ...buildPair({ source_match_id: '3901023' }).payload.normalized, note: 'second observation' },
    });
    const pair2 = buildPair({ source_match_id: '3901024' });

    // package A: 3901023 v1; package B: 3901024; package C: 3901023 v2.
    // Extracted file names are arbitrary (only member hashes bind them), so
    // version-specific names avoid the same-match overwrite.
    const a1 = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair: pair1v1 }], { packageId: 'pkg-a' });
    fs.copyFileSync(path.join(dir, '3901023.payload.json'), path.join(dir, '3901023-v1.payload.json'));
    fs.copyFileSync(path.join(dir, '3901023.manifest.json'), path.join(dir, '3901023-v1.manifest.json'));
    writeFixtureReceipt({
        archivePath: a1.archivePath,
        archiveSha256: a1.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: a1.payloadMember,
        manifestMember: a1.manifestMember,
        receiptPath: path.join(dir, 'receipt-a.json'),
    });
    const a2 = writeFixtureArchive(dir, [{ sourceMatchId: '3901024', pair: pair2 }], { packageId: 'pkg-b' });
    writeFixtureReceipt({
        archivePath: a2.archivePath,
        archiveSha256: a2.archiveSha256,
        packageId: 'pkg-b',
        payloadMember: a2.payloadMember,
        manifestMember: a2.manifestMember,
        receiptPath: path.join(dir, 'receipt-b.json'),
    });
    const a3 = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair: pair1v2 }], { packageId: 'pkg-c' });
    fs.copyFileSync(path.join(dir, '3901023.payload.json'), path.join(dir, '3901023-v2.payload.json'));
    fs.copyFileSync(path.join(dir, '3901023.manifest.json'), path.join(dir, '3901023-v2.manifest.json'));
    writeFixtureReceipt({
        archivePath: a3.archivePath,
        archiveSha256: a3.archiveSha256,
        packageId: 'pkg-c',
        payloadMember: a3.payloadMember,
        manifestMember: a3.manifestMember,
        receiptPath: path.join(dir, 'receipt-c.json'),
    });

    const index1 = buildSourceIndexFromArchive(
        [{ sourceMatchId: '3901023', pair: pair1v1 }],
        {
            ...a1,
            payloadFiles: { 3901023: path.join(dir, '3901023-v1.payload.json') },
            manifestFiles: { 3901023: path.join(dir, '3901023-v1.manifest.json') },
        },
        { packageId: 'pkg-a', receiptPath: path.join(dir, 'receipt-a.json') }
    );
    const index2 = buildSourceIndexFromArchive(
        [{ sourceMatchId: '3901023', pair: pair1v2 }],
        {
            ...a3,
            payloadFiles: { 3901023: path.join(dir, '3901023-v2.payload.json') },
            manifestFiles: { 3901023: path.join(dir, '3901023-v2.manifest.json') },
        },
        { packageId: 'pkg-c', receiptPath: path.join(dir, 'receipt-c.json') }
    );
    index2.archive_bindings['pkg-b'] = {
        sha256: a2.archiveSha256,
        path: a2.archivePath,
        receipt: path.join(dir, 'receipt-b.json'),
    };
    index2.entries.push({
        source_match_id: '3901024',
        payload_file: a2.payloadFiles['3901024'],
        manifest_file: a2.manifestFiles['3901024'],
        payload_file_sha256: sha(a2.payloadFiles['3901024']),
        manifest_file_sha256: sha(a2.manifestFiles['3901024']),
        package: 'pkg-b',
    });
    const index1File = path.join(dir, 'index-1.json');
    const index2File = path.join(dir, 'index-2.json');
    fs.writeFileSync(index1File, JSON.stringify(index1, null, 2) + '\n');
    fs.writeFileSync(index2File, JSON.stringify(index2, null, 2) + '\n');

    // RUN_1 FIRST_IMPORT
    const r1 = await runBuild({
        'source-index': index1File,
        'output-root': outputRoot,
        'run-id': 'run-1',
    });
    assert.strictEqual(r1.status, 'complete');
    assert.strictEqual(r1.accepted_new_count, 1);
    const artifactsAfter1 = fs.readdirSync(outputRoot).filter(f => f.startsWith('observation-'));
    assert.strictEqual(artifactsAfter1.length, 1);
    const oldArtifactPath = path.join(outputRoot, artifactsAfter1[0]);
    const oldBytes = fs.readFileSync(oldArtifactPath);
    const oldHash = sha(oldArtifactPath);
    let v = await runValidate({ 'output-root': outputRoot });
    assert.strictEqual(v.status, 'valid', JSON.stringify(v.errors));

    // RUN_2 SECOND_LEGAL: 3901023 new version → REPEAT_EQUIVALENT (new artifact,
    // old untouched) + 3901024 first time → ACCEPTED_NEW
    const r2 = await runBuild({
        'source-index': index2File,
        'output-root': outputRoot,
        'run-id': 'run-2',
    });
    assert.strictEqual(r2.status, 'complete');
    assert.strictEqual(r2.accepted_repeat_equivalent_count, 1, JSON.stringify(r2));
    assert.strictEqual(r2.accepted_new_count, 1);
    const artifactsAfter2 = fs.readdirSync(outputRoot).filter(f => f.startsWith('observation-'));
    assert.strictEqual(artifactsAfter2.length, 3); // 1 old + 2 new
    assert.strictEqual(sha(oldArtifactPath), oldHash);
    assert.ok(Buffer.compare(oldBytes, fs.readFileSync(oldArtifactPath)) === 0);
    v = await runValidate({ 'output-root': outputRoot });
    assert.strictEqual(v.status, 'valid', JSON.stringify(v.errors));

    // RUN_3 THIRD_EXACT_REPLAY: both REPEAT_EXACT, zero new artifacts
    const r3 = await runBuild({
        'source-index': index2File,
        'output-root': outputRoot,
        'run-id': 'run-3',
    });
    assert.strictEqual(r3.accepted_repeat_exact_count, 2, JSON.stringify(r3));
    const artifactsAfter3 = fs.readdirSync(outputRoot).filter(f => f.startsWith('observation-'));
    assert.strictEqual(artifactsAfter3.length, 3);
    assert.strictEqual(sha(oldArtifactPath), oldHash);
    v = await runValidate({ 'output-root': outputRoot });
    assert.strictEqual(v.status, 'valid', JSON.stringify(v.errors));
});

// ── P1-5: MODE_1_UNANCHORED / MODE_2_EXTERNALLY_ANCHORED ────

function buildOneMatchStore(dir, sourceMatchId = '3901023') {
    const pair = buildPair({ source_match_id: sourceMatchId });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId, pair }], { packageId: 'ten-match' });
    writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'ten-match',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const indexFile = path.join(dir, 'source-index.json');
    fs.writeFileSync(
        indexFile,
        JSON.stringify(
            buildSourceIndexFromArchive([{ sourceMatchId, pair }], archiveInfo, {
                packageId: 'ten-match',
                receiptPath: path.join(dir, 'receipt.json'),
            }),
            null,
            2
        ) + '\n'
    );
    const outputRoot = path.join(dir, 'out');
    return { indexFile, outputRoot };
}

const sha256File = p => require('node:crypto').createHash('sha256').update(fs.readFileSync(p)).digest('hex');

test('P1-5: validate without an anchor reports MODE_1_UNANCHORED with INTACT integrity', async () => {
    const dir = tmpDir('fotmob-p15-mode1-');
    const { indexFile, outputRoot } = buildOneMatchStore(dir);
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    const result = await runValidate({ 'output-root': outputRoot });
    assert.strictEqual(result.status, 'valid');
    assert.strictEqual(result.anchor_mode, 'MODE_1_UNANCHORED');
    assert.strictEqual(result.authenticity_status, 'UNANCHORED');
    assert.strictEqual(result.integrity_status, 'INTACT');
});

test('P1-5: correct --expected-latest-marker-sha256 anchors the store (MODE_2, ANCHORED)', async () => {
    const dir = tmpDir('fotmob-p15-anchored-');
    const { indexFile, outputRoot } = buildOneMatchStore(dir);
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    const markerPath = path.join(outputRoot, 'commit-1.json');
    const anchor = sha256File(markerPath);
    const result = await runValidate({
        'output-root': outputRoot,
        'expected-latest-marker-sha256': anchor,
    });
    assert.strictEqual(result.status, 'valid', JSON.stringify(result.errors));
    assert.strictEqual(result.anchor_mode, 'MODE_2_EXTERNALLY_ANCHORED');
    assert.strictEqual(result.authenticity_status, 'ANCHORED');
    assert.strictEqual(result.integrity_status, 'INTACT');
    assert.strictEqual(result.latest_marker_sha256, anchor);
});

test('P1-5: a wrong anchor fails closed (ANCHOR_MISMATCH) even when integrity is intact', async () => {
    const dir = tmpDir('fotmob-p15-wronganchor-');
    const { indexFile, outputRoot } = buildOneMatchStore(dir);
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    const result = await runValidate({
        'output-root': outputRoot,
        'expected-latest-marker-sha256': 'a'.repeat(64),
    });
    assert.strictEqual(result.status, 'invalid');
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.authenticity_status, 'ANCHOR_MISMATCH');
    assert.strictEqual(result.integrity_status, 'INTACT', 'internal integrity still verifies');
    assert.ok(result.errors.some(e => e.code === 'ANCHOR_MISMATCH'));
});

test('P1-5: anchor checkpoint file (outside the store) anchors; store-internal checkpoint is rejected', async () => {
    const dir = tmpDir('fotmob-p15-checkpoint-');
    const { indexFile, outputRoot } = buildOneMatchStore(dir);
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    const markerPath = path.join(outputRoot, 'commit-1.json');
    const anchor = sha256File(markerPath);
    const checkpoint = path.join(dir, 'checkpoint.json');
    fs.writeFileSync(checkpoint, JSON.stringify({ latest_marker_sha256: anchor }, null, 2) + '\n');

    const good = await runValidate({ 'output-root': outputRoot, 'anchor-checkpoint': checkpoint });
    assert.strictEqual(good.status, 'valid', JSON.stringify(good.errors));
    assert.strictEqual(good.authenticity_status, 'ANCHORED');

    // checkpoint INSIDE the store directory must be rejected by the overlap gate
    const insideStore = path.join(outputRoot, 'checkpoint.json');
    fs.writeFileSync(insideStore, JSON.stringify({ latest_marker_sha256: anchor }, null, 2) + '\n');
    await assert.rejects(
        () => runValidate({ 'output-root': outputRoot, 'anchor-checkpoint': insideStore }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('P1-5: malformed anchors are rejected as INPUT_ERROR', async () => {
    const dir = tmpDir('fotmob-p15-badanchor-');
    const { indexFile, outputRoot } = buildOneMatchStore(dir);
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    await assert.rejects(
        () => runValidate({ 'output-root': outputRoot, 'expected-latest-marker-sha256': 'not-hex' }),
        err => err.code === 'INPUT_ERROR'
    );
    const badCheckpoint = path.join(dir, 'bad-checkpoint.json');
    fs.writeFileSync(badCheckpoint, JSON.stringify({ other: 1 }, null, 2) + '\n');
    await assert.rejects(
        () => runValidate({ 'output-root': outputRoot, 'anchor-checkpoint': badCheckpoint }),
        err => err.code === 'INPUT_ERROR'
    );
    await assert.rejects(
        () =>
            runValidate({
                'output-root': outputRoot,
                'anchor-checkpoint': path.join(dir, 'missing.json'),
            }),
        err => err.code === 'INPUT_ERROR' || err.code === 'SAFETY_ERROR'
    );
});

test('R1-P1-2: --anchor-checkpoint and --expected-latest-marker-sha256 together are rejected (mutually exclusive)', async () => {
    const dir = tmpDir('fotmob-r1-p12-bothanchor-');
    const { indexFile, outputRoot } = buildOneMatchStore(dir);
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    // a real checkpoint file: the mutual-exclusion check fires before the
    // file is read, so even a valid checkpoint cannot be combined with the
    // direct marker sha
    fs.writeFileSync(path.join(dir, 'checkpoint.json'), JSON.stringify({ latest_marker_sha256: '0'.repeat(64) }) + '\n');
    await assert.rejects(
        () =>
            runValidate({
                'output-root': outputRoot,
                'expected-latest-marker-sha256': '1'.repeat(64),
                'anchor-checkpoint': path.join(dir, 'checkpoint.json'),
            }),
        err => err.code === 'INPUT_ERROR' && /only one of/.test(err.message)
    );
});

test('P1-5: single-artifact validate reports integrity and UNANCHORED authenticity', async () => {
    const dir = tmpDir('fotmob-p15-artifact-');
    const { indexFile, outputRoot } = buildOneMatchStore(dir);
    await runBuild({ 'source-index': indexFile, 'output-root': outputRoot });
    const artifactPath = path.join(
        outputRoot,
        fs.readdirSync(outputRoot).find(f => f.startsWith('observation-'))
    );
    const result = await runValidate({ artifact: artifactPath });
    assert.strictEqual(result.status, 'valid');
    assert.strictEqual(result.authenticity_status, 'UNANCHORED');
    assert.strictEqual(result.integrity_status, 'INTACT');
});
