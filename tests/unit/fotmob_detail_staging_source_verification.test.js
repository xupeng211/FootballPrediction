'use strict';

// lifecycle: permanent
// Tests for FotMobDetailStagingSourceVerification.js — the
// VERIFIED_PACKAGE_RECEIPT binding model (FINDING_3) and the generic input
// path gates (FINDING_4): live archive SHA-256, safe tar member inspection,
// receipt build/verify, per-entry package binding, symlink-free inputs, and
// input/output non-overlap.
// Fully offline: no network, no database.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const zlib = require('node:zlib');

const {
    verifyArchive,
    inspectArchive,
    buildPackageReceipt,
    verifyPackageReceipt,
    verifyEntryAgainstReceipt,
    verifyRepositoryExternalRegularFile,
    verifyRepositoryExternalDirectory,
    assertInputOutputNonOverlap,
    parsePaxRecords,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
const {
    buildPair,
    createTarGz,
    writeFixtureArchive,
    writeFixtureReceipt,
} = require('../helpers/fotmobDetailStagingFixtures');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function gzipOf(bytes) {
    return zlib.gzipSync(bytes);
}

/**
 * Minimal raw tar header with an arbitrary typeflag (the shared fixture
 * helper only emits regular files). Mirror of the fixture tarHeader but
 * parameterized — used to build hostile archives.
 */
function rawTarHeader(name, typeflag, size) {
    const buf = Buffer.alloc(512);
    buf.write(String(name), 0, 'utf8');
    buf.write('0000644\0', 100, 'utf8'); // mode
    buf.write('0000000\0', 108, 'utf8'); // uid
    buf.write('0000000\0', 116, 'utf8'); // gid
    buf.write(Number(size).toString(8).padStart(11, '0') + '\0', 124, 'utf8'); // size
    buf.write('00000000000\0', 136, 'utf8'); // mtime
    buf.write(String(typeflag), 156, 'utf8'); // typeflag
    buf.write('ustar\0', 257, 'utf8'); // magic
    buf.write('00', 263, 'utf8'); // version
    let sum = 0;
    for (let i = 0; i < 512; i += 1) {
        sum += i >= 148 && i < 156 ? 32 : buf[i];
    }
    buf.write(sum.toString(8).padStart(6, '0') + '\0 ', 148, 'utf8');
    return buf;
}

/**
 * Build a PAX record whose leading length field exactly matches the total
 * record byte length (the field counts the digits, the space, the key, the
 * value and the trailing newline).
 */
function paxRecordFor(key, value) {
    for (let n = 10; n < 1000; n += 1) {
        const rec = `${n} ${key}=${value}\n`;
        if (rec.length === n) return rec;
    }
    throw new Error('pax record too long');
}

function rawTarBlock(header, content) {
    const blocks = [header];
    if (content && content.length > 0) {
        blocks.push(content);
        const remainder = content.length % 512;
        if (remainder > 0) blocks.push(Buffer.alloc(512 - remainder));
    }
    return Buffer.concat(blocks);
}

// ── live archive verification (FINDING_3) ───────────────────

test('V1: verifyArchive accepts a real archive with the true SHA', () => {
    const dir = tmpDir('fotmob-ver-ok-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    const verified = verifyArchive(info.archivePath, info.archiveSha256, {
        repositoryRoot: REPO_ROOT,
    });
    assert.strictEqual(verified.archive_sha256, info.archiveSha256);
});

test('V2: verifyArchive fails closed on a wrong declared SHA', () => {
    const dir = tmpDir('fotmob-ver-wrongsha-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    assert.throws(
        () =>
            verifyArchive(info.archivePath, '1'.repeat(64), {
                repositoryRoot: REPO_ROOT,
            }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V3: verifyArchive rejects a non-64-hex declared SHA', () => {
    const dir = tmpDir('fotmob-ver-badsha-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    assert.throws(
        () => verifyArchive(info.archivePath, 'nope', { repositoryRoot: REPO_ROOT }),
        err => err.code === 'INPUT_ERROR'
    );
});

test('V4: verifyArchive rejects a symlinked archive path', () => {
    const dir = tmpDir('fotmob-ver-link-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    const link = path.join(dir, 'archive-link.tar.gz');
    fs.symlinkSync(info.archivePath, link);
    assert.throws(
        () => verifyArchive(link, info.archiveSha256, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

// ── safe tar inspection ─────────────────────────────────────

test('V5: inspectArchive rejects a corrupted gzip stream', () => {
    const dir = tmpDir('fotmob-ver-badgzip-');
    const bad = path.join(dir, 'bad.tar.gz');
    fs.writeFileSync(bad, Buffer.from('this is not gzip', 'utf8'));
    assert.throws(
        () => inspectArchive(bad, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'INPUT_ERROR'
    );
});

test('V6: inspectArchive rejects a tar header checksum mismatch (tampered)', () => {
    const dir = tmpDir('fotmob-ver-checksum-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    // Re-build the raw tar, flip one header byte (the name field), re-gzip.
    const original = zlib.gunzipSync(fs.readFileSync(info.archivePath));
    const tampered = Buffer.from(original);
    tampered[10] = tampered[10] ^ 0x01; // inside the first header name field
    const path2 = path.join(dir, 'tampered.tar.gz');
    fs.writeFileSync(path2, gzipOf(tampered));
    assert.throws(
        () => inspectArchive(path2, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V7: inspectArchive rejects absolute member paths', () => {
    const dir = tmpDir('fotmob-ver-abs-');
    const archive = path.join(dir, 'hostile.tar.gz');
    const tar = rawTarBlock(rawTarHeader('/etc/passwd', '0', 1), Buffer.from('x'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V8: inspectArchive rejects traversal member paths', () => {
    const dir = tmpDir('fotmob-ver-trav-');
    const archive = path.join(dir, 'hostile.tar.gz');
    const tar = rawTarBlock(rawTarHeader('../escape.json', '0', 1), Buffer.from('x'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V9: inspectArchive rejects symlink and hardlink members', () => {
    const dir = tmpDir('fotmob-ver-links-');
    for (const typeflag of ['1', '2']) {
        const archive = path.join(dir, `hostile-${typeflag}.tar.gz`);
        const header = rawTarHeader('pairs/1-link.json', typeflag, 0);
        const tar = rawTarBlock(header, Buffer.alloc(0));
        fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
        assert.throws(
            () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
            err => err.code === 'SAFETY_ERROR'
        );
    }
});

test('V10: inspectArchive rejects special-file members', () => {
    const dir = tmpDir('fotmob-ver-special-');
    for (const typeflag of ['3', '4', '6', '7']) {
        const archive = path.join(dir, `hostile-${typeflag}.tar.gz`);
        const header = rawTarHeader('pairs/1-dev', typeflag, 0);
        const tar = rawTarBlock(header, Buffer.alloc(0));
        fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
        assert.throws(
            () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
            err => err.code === 'SAFETY_ERROR'
        );
    }
});

test('V11: inspectArchive rejects duplicate member names', () => {
    const dir = tmpDir('fotmob-ver-dup-');
    const archive = path.join(dir, 'hostile.tar.gz');
    const a = rawTarBlock(rawTarHeader('pairs/1.payload.json', '0', 1), Buffer.from('a'));
    const b = rawTarBlock(rawTarHeader('pairs/1.payload.json', '0', 1), Buffer.from('b'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([a, b, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V12: inspectArchive resolves GNU long names and PAX path records', () => {
    const dir = tmpDir('fotmob-ver-pax-');
    const archive = path.join(dir, 'pax.tar.gz');
    const realName = 'pairs/1-3901023.payload.json';
    const longNameBlock = rawTarBlock(rawTarHeader('', 'L', realName.length), Buffer.from(realName, 'utf8'));
    const paxRecord = paxRecordFor('path', realName);
    const paxBlock = rawTarBlock(rawTarHeader('', 'x', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
    const gBlock = rawTarBlock(rawTarHeader('', 'g', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
    const content = rawTarBlock(rawTarHeader('short-name', '0', 3), Buffer.from('abc'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([longNameBlock, paxBlock, gBlock, content, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    const names = inspected.members.map(m => m.name);
    assert.ok(names.includes(realName), `resolved names: ${names.join(',')}`);
});

test('V13: inspectArchive accepts a clean fixture archive and hashes members', () => {
    const dir = tmpDir('fotmob-ver-clean-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    const inspected = inspectArchive(info.archivePath, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(inspected.archive_sha256, info.archiveSha256);
    assert.strictEqual(inspected.members.length, 2);
    const payloadMember = inspected.members.find(m => m.name === info.payloadMember);
    assert.ok(payloadMember);
    assert.strictEqual(payloadMember.sha256.length, 64);
});

// ── package receipts (FINDING_3) ────────────────────────────

test('V14: buildPackageReceipt is deterministic and self-hashed', () => {
    const dir = tmpDir('fotmob-ver-receipt-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    const inspected = inspectArchive(info.archivePath, { repositoryRoot: REPO_ROOT });
    const a = buildPackageReceipt({
        packageId: 'ten-match',
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        members: inspected.members,
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
    });
    const b = buildPackageReceipt({
        packageId: 'ten-match',
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        members: inspected.members,
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
    });
    assert.deepStrictEqual(a, b);
    const validation = verifyPackageReceipt(a);
    assert.strictEqual(validation.ok, true, validation.errors.join('; '));
});

test('V15: buildPackageReceipt fails when members are missing', () => {
    const pair = buildPair();
    assert.throws(
        () =>
            buildPackageReceipt({
                packageId: 'ten-match',
                archivePath: '/tmp/archive.tar.gz',
                archiveSha256: '0'.repeat(64),
                members: [],
                payloadMember: 'pairs/1-3901023.payload.json',
                manifestMember: 'pairs/1-3901023.manifest.json',
            }),
        err => err.code === 'INPUT_ERROR'
    );
});

test('V16: verifyPackageReceipt detects receipt tampering', () => {
    const dir = tmpDir('fotmob-ver-receipt-tamper-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'ten-match',
    });
    const inspected = inspectArchive(info.archivePath, { repositoryRoot: REPO_ROOT });
    const receipt = buildPackageReceipt({
        packageId: 'ten-match',
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        members: inspected.members,
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
    });
    assert.strictEqual(verifyPackageReceipt(receipt).ok, true);

    const tamperMember = {
        ...receipt,
        members: { ...receipt.members, [info.payloadMember]: 'f'.repeat(64) },
    };
    assert.strictEqual(verifyPackageReceipt(tamperMember).ok, false);

    const tamperSha = { ...receipt, archive_sha256: 'a'.repeat(64) };
    assert.strictEqual(verifyPackageReceipt(tamperSha).ok, false);

    const tamperSelf = { ...receipt, receipt_sha256: 'b'.repeat(64) };
    assert.strictEqual(verifyPackageReceipt(tamperSelf).ok, false);

    const tamperMemberName = {
        ...receipt,
        payload_member: 'pairs/../escape.payload.json',
    };
    assert.strictEqual(verifyPackageReceipt(tamperMemberName).ok, false);
});

// ── per-entry binding (FINDING_3) ───────────────────────────

test('V17: verifyEntryAgainstReceipt accepts a fully bound entry', () => {
    const dir = tmpDir('fotmob-ver-entry-ok-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-a',
    });
    const receiptPath = path.join(dir, 'receipt.json');
    writeFixtureReceipt({
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
        receiptPath,
    });
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    const binding = {
        sha256: info.archiveSha256,
        path: info.archivePath,
        receipt: receiptPath,
    };
    const entry = {
        source_match_id: '3901023',
        payload_file: info.payloadFile,
        manifest_file: info.manifestFile,
        package: 'pkg-a',
    };
    const loaded = verifyEntryAgainstReceipt({
        entry,
        binding,
        receipt,
        payloadFile: info.payloadFile,
        manifestFile: info.manifestFile,
        outputRoot: path.join(dir, 'out'),
        options: { repositoryRoot: REPO_ROOT },
    });
    assert.strictEqual(loaded.payload.source_match_id, '3901023');
    assert.strictEqual(loaded.payloadFileSha256.length, 64);
    assert.ok(Buffer.compare(loaded.payloadBytes, pair.payloadBytes) === 0);
});

test('V18: verifyEntryAgainstReceipt rejects a payload file that no longer matches the member', () => {
    const dir = tmpDir('fotmob-ver-entry-payload-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-a',
    });
    const receiptPath = path.join(dir, 'receipt.json');
    writeFixtureReceipt({
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
        receiptPath,
    });
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    const binding = {
        sha256: info.archiveSha256,
        path: info.archivePath,
        receipt: receiptPath,
    };
    const entry = {
        source_match_id: '3901023',
        payload_file: info.payloadFile,
        manifest_file: info.manifestFile,
        package: 'pkg-a',
    };
    // Tamper the extracted payload file: the live SHA must no longer equal the
    // receipt member hash.
    fs.writeFileSync(info.payloadFile, Buffer.from('tampered bytes', 'utf8'));
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry,
                binding,
                receipt,
                payloadFile: info.payloadFile,
                manifestFile: info.manifestFile,
                outputRoot: path.join(dir, 'out'),
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V19: verifyEntryAgainstReceipt rejects a receipt whose archive SHA differs from the binding', () => {
    const dir = tmpDir('fotmob-ver-entry-sha-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-a',
    });
    const receiptPath = path.join(dir, 'receipt.json');
    writeFixtureReceipt({
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
        receiptPath,
    });
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    const binding = {
        sha256: 'e'.repeat(64), // declared SHA disagrees with the receipt
        path: info.archivePath,
        receipt: receiptPath,
    };
    const entry = {
        source_match_id: '3901023',
        payload_file: info.payloadFile,
        manifest_file: info.manifestFile,
        package: 'pkg-a',
    };
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry,
                binding,
                receipt,
                payloadFile: info.payloadFile,
                manifestFile: info.manifestFile,
                outputRoot: path.join(dir, 'out'),
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V20: verifyEntryAgainstReceipt rejects an entry without a package', () => {
    const dir = tmpDir('fotmob-ver-entry-nopkg-');
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-a',
    });
    const receiptPath = path.join(dir, 'receipt.json');
    writeFixtureReceipt({
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
        receiptPath,
    });
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { source_match_id: '3901023' },
                binding: { sha256: info.archiveSha256, path: info.archivePath },
                receipt,
                payloadFile: info.payloadFile,
                manifestFile: info.manifestFile,
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR'
    );
});

// ── input path gates (FINDING_4) ────────────────────────────

test('V21: leaf and ancestor symlinks are rejected on input files', () => {
    const dir = tmpDir('fotmob-ver-symlink-');
    const realDir = path.join(dir, 'real');
    const linkDir = path.join(dir, 'linkdir');
    fs.mkdirSync(realDir);
    fs.writeFileSync(path.join(realDir, 'input.json'), '{}');
    // ancestor symlink: linkdir -> realDir
    fs.symlinkSync(realDir, linkDir, 'dir');
    assert.throws(
        () =>
            verifyRepositoryExternalRegularFile(path.join(linkDir, 'input.json'), {
                repositoryRoot: REPO_ROOT,
            }),
        err => err.code === 'SAFETY_ERROR'
    );
    // leaf symlink
    const linkFile = path.join(dir, 'link.json');
    fs.symlinkSync(path.join(realDir, 'input.json'), linkFile);
    assert.throws(
        () =>
            verifyRepositoryExternalRegularFile(linkFile, {
                repositoryRoot: REPO_ROOT,
            }),
        err => err.code === 'SAFETY_ERROR'
    );
    // symlinked directory leaf
    assert.throws(
        () =>
            verifyRepositoryExternalDirectory(linkDir, {
                repositoryRoot: REPO_ROOT,
            }),
        err => err.code === 'SAFETY_ERROR'
    );
    // directory without symlinks passes
    const ok = verifyRepositoryExternalDirectory(realDir, {
        repositoryRoot: REPO_ROOT,
    });
    assert.strictEqual(ok, realDir);
});

test('V22: assertInputOutputNonOverlap rejects input inside the output root', () => {
    assert.throws(
        () => assertInputOutputNonOverlap('/tmp/out/input.json', '/tmp/out'),
        err => err.code === 'SAFETY_ERROR'
    );
    assert.throws(
        () => assertInputOutputNonOverlap('/tmp/out', '/tmp/out'),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V23: assertInputOutputNonOverlap rejects output equal to the input directory', () => {
    assert.throws(
        () => assertInputOutputNonOverlap('/tmp/work/index.json', '/tmp/work'),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('V24: assertInputOutputNonOverlap allows a sibling subdirectory output', () => {
    assert.strictEqual(assertInputOutputNonOverlap('/tmp/work/index.json', '/tmp/work/out'), true);
    assert.strictEqual(assertInputOutputNonOverlap('/tmp/work/index.json', '/tmp/elsewhere/out'), true);
});

test('V25: parsePaxRecords parses length-prefixed key=value records', () => {
    const records = parsePaxRecords(
        paxRecordFor('path', 'pairs/1-3901023.payload.json') + paxRecordFor('mtime', '1234567890')
    );
    assert.strictEqual(records.path, 'pairs/1-3901023.payload.json');
    assert.strictEqual(records.mtime, '1234567890');
});
