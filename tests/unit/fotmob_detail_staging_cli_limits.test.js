'use strict';

// lifecycle: permanent
// R20-P2-2 (Codex round 20) CLI regressions: the canonical CLI archive
// limits override (--limits-file). Kept in a dedicated file so
// fotmob_detail_staging_cli.test.js stays under the ESLint max-lines cap.
// Fully offline: no network (structurally forbidden), no database.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { runReceipt, runBuild } = require('../../scripts/ops/fotmob_detail_staging');
const {
    buildPair,
    writeFixtureArchive,
    writeFixtureReceipt,
    buildSourceIndexFromArchive,
    createTarGz,
} = require('../helpers/fotmobDetailStagingFixtures');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// ── R20-P2-2 (Codex round 20): canonical CLI archive limits override.
//    The module documented `options.limits` but the canonical CLI/Make had
//    NO way to raise DEFAULT_ARCHIVE_LIMITS — a legal archive above the
//    defaults (compressed > 256 MiB, member > 256 MiB, > 10000 members, …)
//    was refused with no operator surface. --limits-file (repository-external
//    JSON, strictly validated, hard-cap bounded) now propagates to the
//    receipt SHA pass, the live archive inspection AND every per-entry
//    loader. ───────────────────────────────────────────────────────────────

function writeLimitsFile(dir, doc) {
    const limitsFile = path.join(dir, 'archive-limits.json');
    fs.writeFileSync(limitsFile, JSON.stringify(doc));
    return limitsFile;
}

test('R20-P2-2a: receipt refuses a legal >10000-member archive by default, then succeeds via --limits-file (raise)', async () => {
    const dir = tmpDir('fotmob-cli-r20p22a-');
    // A legal tar with 10001 tiny members: default maxMembers=10000 must
    // reject it; --limits-file raising the cap must let the SAME archive
    // pass the canonical receipt (structure/hashes all valid).
    const members = [];
    for (let i = 0; i < 10001; i += 1) {
        members.push({ name: `pairs/1-3901023.payload-${i}.json`, content: `{"i":${i}}` });
    }
    const archivePath = path.join(dir, 'many-members.tar.gz');
    const archiveBytes = createTarGz(members);
    fs.writeFileSync(archivePath, archiveBytes);
    const sha = require('node:crypto').createHash('sha256').update(archiveBytes).digest('hex');
    const base = {
        archive: archivePath,
        'expected-sha256': sha,
        'package-id': 'many-members',
        'payload-member': members[0].name,
        'manifest-member': members[1].name,
        'receipt-out': path.join(dir, 'receipt-default.json'),
    };
    await assert.rejects(
        async () => runReceipt(base),
        err => err.code === 'SAFETY_ERROR' && /tar member count exceeds the limit \(10000\)/.test(err.message)
    );
    const raised = await runReceipt({
        ...base,
        'limits-file': writeLimitsFile(dir, { maxMembers: 20000 }),
        'receipt-out': path.join(dir, 'receipt-raised.json'),
    });
    assert.strictEqual(raised.status, 'complete');
    assert.strictEqual(raised.member_count, 10001);
    assert.strictEqual(raised.zero_network, true);
    assert.strictEqual(raised.zero_database, true);
    assert.ok(fs.existsSync(path.join(dir, 'receipt-raised.json')));
});

test('R20-P2-2b: limits-file overrides propagate to the receipt SHA pass (compressed-size cap)', async () => {
    const dir = tmpDir('fotmob-cli-r20p22b-');
    const pair = buildPair();
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'one' });
    const base = {
        archive: archiveInfo.archivePath,
        'expected-sha256': archiveInfo.archiveSha256,
        'package-id': 'one',
        'payload-member': archiveInfo.payloadMember,
        'manifest-member': archiveInfo.manifestMember,
        'receipt-out': path.join(dir, 'receipt.json'),
    };
    // A 1-byte compressed cap must fail the FIRST SHA pass (verifyArchive),
    // before the archive is ever allocated.
    await assert.rejects(
        async () => runReceipt({ ...base, 'limits-file': writeLimitsFile(dir, { maxCompressedBytes: 1 }) }),
        err => err.code === 'SAFETY_ERROR' && /input file exceeds the size limit/.test(err.message)
    );
});

test('R20-P2-2c: limits-file overrides propagate to the per-entry loader in build (tight member cap → E008)', async () => {
    const dir = tmpDir('fotmob-cli-r20p22c-');
    const pair = buildPair();
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'one' });
    writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'one',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const indexFile = path.join(dir, 'source-index.json');
    fs.writeFileSync(
        indexFile,
        JSON.stringify(
            buildSourceIndexFromArchive([{ sourceMatchId: '3901023', pair }], archiveInfo, {
                packageId: 'one',
                receiptPath: path.join(dir, 'receipt.json'),
            }),
            null,
            2
        ) + '\n'
    );
    // Tight member cap: the loader's live archive re-inspection fails closed
    // per entry (E008 REJECTED_PROVENANCE_BROKEN), the batch completes with
    // zero accepts — the limit flowed into makePairLoader → verifyEntryAgainstReceipt.
    const outputRoot = path.join(dir, 'out');
    const refused = await runBuild({
        'source-index': indexFile,
        'output-root': outputRoot,
        'limits-file': writeLimitsFile(dir, { maxMemberBytes: 512 }),
    });
    assert.strictEqual(refused.status, 'complete');
    assert.strictEqual(refused.accepted_new_count, 0);
    assert.strictEqual(refused.rejected_count, 1);
    assert.strictEqual(refused.zero_network, true);
    const summaryFile = fs.readdirSync(outputRoot).find(f => f.startsWith('summary-') && f.endsWith('.json'));
    const summary = JSON.parse(fs.readFileSync(path.join(outputRoot, summaryFile), 'utf8'));
    assert.strictEqual(summary.business_projection.observations[0].terminal_state, 'REJECTED_PROVENANCE_BROKEN');
    // Legal control: adequate limits → the same build accepts the pair.
    const outputRoot2 = path.join(dir, 'out2');
    const ok = await runBuild({
        'source-index': indexFile,
        'output-root': outputRoot2,
        'limits-file': writeLimitsFile(dir, { maxMemberBytes: 1024 * 1024 }),
    });
    assert.strictEqual(ok.status, 'complete');
    assert.strictEqual(ok.accepted_new_count, 1);
    assert.strictEqual(ok.rejected_count, 0);
});

test('R20-P2-2d: --limits-file values are strictly validated (hard caps, safe integers, plain object)', async () => {
    const dir = tmpDir('fotmob-cli-r20p22d-');
    const pair = buildPair();
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'one' });
    const base = {
        archive: archiveInfo.archivePath,
        'expected-sha256': archiveInfo.archiveSha256,
        'package-id': 'one',
        'payload-member': archiveInfo.payloadMember,
        'manifest-member': archiveInfo.manifestMember,
        'receipt-out': path.join(dir, 'receipt.json'),
    };
    // Above the hard safety cap → refused before any archive byte is read.
    await assert.rejects(
        async () => runReceipt({ ...base, 'limits-file': writeLimitsFile(dir, { maxMemberBytes: 1e15 }) }),
        err => err.code === 'INPUT_ERROR' && /hard cap/.test(err.message)
    );
    // Non-integer / non-positive values → refused.
    await assert.rejects(
        async () => runReceipt({ ...base, 'limits-file': writeLimitsFile(dir, { maxMembers: -3 }) }),
        err => err.code === 'INPUT_ERROR' && /positive safe integer/.test(err.message)
    );
    // Unknown keys are ignored, but the document must be a JSON object.
    const notObject = path.join(dir, 'limits-array.json');
    fs.writeFileSync(notObject, '[1, 2]');
    await assert.rejects(
        async () => runReceipt({ ...base, 'limits-file': notObject }),
        err => err.code === 'INPUT_ERROR' && /JSON object/.test(err.message)
    );
    // The limits file must pass the repository-external input gate.
    await assert.rejects(
        async () => runReceipt({ ...base, 'limits-file': path.join(REPO_ROOT, 'package.json') }),
        err => /outside the repository|repository/.test(err.message)
    );
});
