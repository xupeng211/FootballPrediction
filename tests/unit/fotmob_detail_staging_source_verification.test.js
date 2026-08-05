/* eslint-disable complexity, max-lines */
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
const crypto = require('node:crypto');
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
    verifyLiveArchiveAgainstReceipt,
    verifyRepositoryExternalRegularFile,
    verifyRepositoryExternalDirectory,
    assertInputOutputNonOverlap,
    parseOctal,
    parsePaxRecords,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
const {
    buildPair,
    createTarGz,
    writeFixtureArchive,
    writeFixtureReceipt,
    sha256Hex,
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
        // R11-P3-3 (Codex round 11): PAX lengths are BYTE lengths — a
        // non-ASCII value (é = 2 UTF-8 bytes) must be measured with
        // Buffer.byteLength, not string.length (UTF-16 code units).
        if (Buffer.byteLength(rec) === n) return rec;
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
    const content = rawTarBlock(rawTarHeader('short-name', '0', 3), Buffer.from('abc'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([longNameBlock, paxBlock, content, Buffer.alloc(1024)])));
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

// ── P2-1: strict tar parsing (Codex review 4863122944 P2-1) ──

test('P2-1: GLOBAL PAX headers are rejected (not implemented, fail closed)', () => {
    const dir = tmpDir('fotmob-ver-globalpax-');
    const archive = path.join(dir, 'global-pax.tar.gz');
    const paxRecord = paxRecordFor('path', 'pairs/1-3901023.payload.json');
    const gBlock = rawTarBlock(rawTarHeader('', 'g', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
    const content = rawTarBlock(rawTarHeader('short-name', '0', 3), Buffer.from('abc'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([gBlock, content, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /GLOBAL PAX/.test(err.message)
    );
});

test('P2-1: a non-octal size field is rejected, never defaulted to zero', () => {
    const dir = tmpDir('fotmob-ver-badsize-');
    const archive = path.join(dir, 'bad-size.tar.gz');
    const header = rawTarHeader('pairs/x.json', '0', 3);
    header.fill(0x20, 124, 136); // overwrite size bytes WITHOUT breaking the checksum
    header.write('not-octal', 124, 'ascii');
    // recompute the header checksum over the tampered bytes (checksum field
    // counts as spaces) so the size-field check is what fires, not checksum.
    let sum = 0;
    for (let i = 0; i < 512; i += 1) {
        sum += i >= 148 && i < 156 ? 32 : header[i];
    }
    header.write(sum.toString(8).padStart(6, '0') + '\0 ', 148, 'utf8');
    const tar = rawTarBlock(header, Buffer.from('abc'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /size field is not valid octal/.test(err.message)
    );
});

test('P2-1: member content extending past the buffer (truncated tar) is rejected', () => {
    const dir = tmpDir('fotmob-ver-trunc-');
    const archive = path.join(dir, 'truncated.tar.gz');
    // header declares 10 bytes of content but the archive ends at the header
    const header = rawTarHeader('pairs/x.json', '0', 10);
    const tar = rawTarBlock(header, Buffer.alloc(0));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /beyond the archive/.test(err.message)
    );
});

test('P2-1: incomplete padding block (content without its 512-block padding) is rejected', () => {
    const dir = tmpDir('fotmob-ver-pad-');
    const archive = path.join(dir, 'pad.tar.gz');
    const header = rawTarHeader('pairs/x.json', '0', 513);
    const content = Buffer.alloc(513, 0x41);
    // rawTarBlock would auto-pad; build the truncated layout by hand:
    // header + 513 content bytes with NO padding block.
    fs.writeFileSync(archive, gzipOf(Buffer.concat([header, content])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /padding is incomplete/.test(err.message)
    );
});

test('P2-1: strict PAX rejects malformed length and missing trailing newline', () => {
    assert.throws(() => parsePaxRecords('abc'), err => err.code === 'SAFETY_ERROR');
    // length in bounds but the record does not end with newline
    assert.throws(
        () => parsePaxRecords('12 path=abcd'),
        err => err.code === 'SAFETY_ERROR' && /newline/.test(err.message)
    );
    assert.throws(
        () => parsePaxRecords('9999 path=x\n'),
        err => err.code === 'SAFETY_ERROR' && /out of bounds/.test(err.message)
    );
    // truncation of the last record is an error, not a silent stop
    assert.throws(() => parsePaxRecords('16 path=xy'), err => err.code === 'SAFETY_ERROR');
});

// ── P0-1: receipt ↔ LIVE archive strong binding (Codex review 4863122944
// ── P0-1) ─────────────────────────────────────────────────────────

/**
 * Build a package receipt document whose member table is forged relative to
 * the live archive: real archive SHA-256, but `members` describe files that
 * do not exist in the archive, with hashes of external legal files. The
 * receipt business hash and inventory hash are recomputed over the forged
 * content so the receipt is FULLY self-consistent — the exact P0-1 attack.
 */
function forgedSelfConsistentReceipt(archivePath, archiveSha256, members, payloadMember, manifestMember, packageId) {
    const { buildPackageReceipt } = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
    const forged = buildPackageReceipt({
        packageId,
        archivePath,
        archiveSha256,
        members,
        payloadMember,
        manifestMember,
    });
    // self-consistency re-check: the forged receipt must pass
    // verifyPackageReceipt (its own business hash is recomputed correctly)
    const { verifyPackageReceipt: verify } = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
    const check = verify(forged);
    assert.strictEqual(check.ok, true, 'forged receipt must be self-consistent for this test to be meaningful');
    return forged;
}

test('V26 (P0-1): self-consistent forged receipt is rejected by live archive verification', () => {
    const dir = tmpDir('fotmob-p0-1-forged-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-forged',
    });
    // The forged receipt claims the archive contains DIFFERENT members with
    // the hashes of unrelated external files, while keeping the REAL archive
    // SHA-256. All hashes are recomputed (receipt_sha256 AND
    // archive_inventory_sha256) — a receipt that only looks consistent.
    const externalPayload = Buffer.from('{"fake":"payload"}', 'utf8');
    const externalManifest = Buffer.from('{"fake":"manifest"}', 'utf8');
    const forged = forgedSelfConsistentReceipt(
        archiveInfo.archivePath,
        archiveInfo.archiveSha256,
        [
            { name: 'not-in-archive.json', sha256: sha256Hex(externalPayload) },
            { name: 'also-not-in-archive.json', sha256: sha256Hex(externalManifest) },
        ],
        'not-in-archive.json',
        'also-not-in-archive.json',
        'pkg-forged'
    );
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-forged' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt: forged,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /member inventory|member set/.test(err.message),
        'forged receipt must be rejected against the live archive'
    );
});

test('V27 (P0-1): receipt whose inventory omits a managed archive member is rejected', () => {
    const dir = tmpDir('fotmob-p0-1-missing-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-missing',
    });
    const { buildPackageReceipt, computeArchiveInventory } = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
    const receipt = buildPackageReceipt({
        packageId: 'pkg-missing',
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        members: [
            { name: archiveInfo.payloadMember, sha256: sha256Hex(fs.readFileSync(archiveInfo.payloadFile)) },
            { name: archiveInfo.manifestMember, sha256: sha256Hex(fs.readFileSync(archiveInfo.manifestFile)) },
        ],
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
    });
    // Forge the receipt so its archive_inventory_sha256 covers ONLY the
    // payload member (the managed manifest member is missing from the
    // inventory), then recompute the receipt business hash — the receipt is
    // fully self-consistent, but the live archive (two members) disagrees.
    const forged = {
        ...receipt,
        archive_inventory_sha256: computeArchiveInventory([
            { name: archiveInfo.payloadMember, type: 'file', size: 0, sha256: receipt.members[archiveInfo.payloadMember] },
        ]),
    };
    forged.receipt_sha256 = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract').canonicalJsonHash(
        (() => { const c = { ...forged }; delete c.receipt_sha256; return c; })()
    );
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-missing' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt: forged,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /member inventory/.test(err.message)
    );
});

test('V28 (P0-1): receipt member hash correct but path wrong is rejected', () => {
    const dir = tmpDir('fotmob-p0-1-pathswap-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-pathswap',
    });
    const { buildPackageReceipt } = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
    // swap the two members' PATHS while keeping their hashes: the receipt is
    // self-consistent but disagrees with the live archive member table
    const swapped = buildPackageReceipt({
        packageId: 'pkg-pathswap',
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        members: [
            { name: archiveInfo.manifestMember, sha256: sha256Hex(fs.readFileSync(archiveInfo.payloadFile)) },
            { name: archiveInfo.payloadMember, sha256: sha256Hex(fs.readFileSync(archiveInfo.manifestFile)) },
        ],
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-pathswap' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt: swapped,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /member inventory|member set/.test(err.message)
    );
});

test('V29 (P0-1): archive member content changed is rejected even with synchronized SHA forgery', () => {
    const dir = tmpDir('fotmob-p0-1-content-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-content',
    });
    const { buildPackageReceipt } = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
    const receipt = buildPackageReceipt({
        packageId: 'pkg-content',
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        members: [
            { name: archiveInfo.payloadMember, sha256: '0'.repeat(64) },
            { name: archiveInfo.manifestMember, sha256: '1'.repeat(64) },
        ],
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-content' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /member inventory|member set|member hash/.test(err.message)
    );
});

test('V30 (P0-1): archive bytes changed with SHA + receipt archive_sha256 both updated is rejected (inventory mismatch)', () => {
    const dir = tmpDir('fotmob-p0-1-tampered-archive-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-tampered',
    });
    const { buildPackageReceipt } = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
    const receipt = buildPackageReceipt({
        packageId: 'pkg-tampered',
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        members: [
            { name: archiveInfo.payloadMember, sha256: sha256Hex(fs.readFileSync(archiveInfo.payloadFile)) },
            { name: archiveInfo.manifestMember, sha256: sha256Hex(fs.readFileSync(archiveInfo.manifestFile)) },
        ],
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
    });
    // attacker tampers the archive bytes AND updates both the binding SHA and
    // the receipt archive_sha256 to the new value — but cannot make the
    // members table match the changed archive content
    const bytes = fs.readFileSync(archiveInfo.archivePath);
    const tampered = Buffer.concat([bytes.subarray(0, bytes.length - 2), Buffer.from([0, 0])]);
    fs.writeFileSync(archiveInfo.archivePath, tampered);
    const newSha = sha256Hex(tampered);
    const forgedReceipt = { ...receipt, archive_sha256: newSha };
    forgedReceipt.receipt_sha256 = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract').canonicalJsonHash(
        (() => { const c = { ...forgedReceipt }; delete c.receipt_sha256; return c; })()
    );
    const binding = { sha256: newSha, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-tampered' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt: forgedReceipt,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /member inventory/.test(err.message)
    );
});

test('V31 (P0-1): external payload copy differing from the archive member is rejected', () => {
    const dir = tmpDir('fotmob-p0-1-payldiff-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-payldiff',
    });
    const receiptPath = path.join(dir, 'receipt.json');
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-payldiff',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath,
    });
    // replace the EXTERNAL payload copy with different bytes (the archive
    // member is untouched) — must be rejected
    const tamperedPayload = Buffer.from(JSON.stringify({ ...pair.payload, extra: 'tampered' }, null, 2) + '\n', 'utf8');
    fs.writeFileSync(archiveInfo.payloadFile, tamperedPayload);
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-payldiff' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /payload file sha256/.test(err.message)
    );
});

test('V32 (P0-1): external manifest copy differing from the archive member is rejected', () => {
    const dir = tmpDir('fotmob-p0-1-mandiff-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-mandiff',
    });
    const receiptPath = path.join(dir, 'receipt.json');
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-mandiff',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath,
    });
    const tamperedManifest = Buffer.from(JSON.stringify({ ...pair.manifest, extra: 'tampered' }, null, 2) + '\n', 'utf8');
    fs.writeFileSync(archiveInfo.manifestFile, tamperedManifest);
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-mandiff' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /manifest file sha256/.test(err.message)
    );
});

test('V33 (P0-1): entry bound to the wrong package is rejected', () => {
    const dir = tmpDir('fotmob-p0-1-wrongpkg-');
    const pairA = buildPair({ source_match_id: '3901023' });
    const pairB = buildPair({ source_match_id: '3901024' });
    const archiveA = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair: pairA }], { packageId: 'pkg-a' });
    const archiveB = writeFixtureArchive(dir, [{ sourceMatchId: '3901024', pair: pairB }], { packageId: 'pkg-b' });
    const receiptPathA = path.join(dir, 'receipt-a.json');
    const receiptA = writeFixtureReceipt({
        archivePath: archiveA.archivePath,
        archiveSha256: archiveA.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: archiveA.payloadMember,
        manifestMember: archiveA.manifestMember,
        receiptPath: receiptPathA,
    });
    // entry claims package pkg-a but points its files at package pkg-b's pair
    const bindingA = { sha256: archiveA.archiveSha256, path: archiveA.archivePath, receipt: receiptPathA };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-a' },
            payloadFile: archiveB.payloadFile,
            manifestFile: archiveB.manifestFile,
            binding: bindingA,
            receipt: receiptA,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /payload file sha256|manifest file sha256/.test(err.message)
    );
});

test('V34 (P0-1): archive_inventory_sha256 is required in the receipt schema', () => {
    const dir = tmpDir('fotmob-p0-1-schema-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-schema' });
    const receiptPath = path.join(dir, 'receipt.json');
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-schema',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath,
    });
    // old-format receipt (no inventory field) must be rejected
    const { archive_inventory_sha256, ...oldFormat } = receipt;
    const validation = verifyPackageReceipt(oldFormat);
    assert.strictEqual(validation.ok, false);
    assert.ok(validation.errors.some(e => /archive_inventory_sha256/.test(e)), JSON.stringify(validation.errors));
});

// ── R1-P0-1: unforgeable live-verification capability (Codex round 1) ──

test('V34b (R1-P0-1): a fabricated inspected member table is rejected (no capability, no bypass)', () => {
    const dir = tmpDir('fotmob-r1-p0-1-forgedinsp-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-cap' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-cap',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    // The forged inspected is fully self-consistent with the receipt — real
    // archive SHA, real member names and real per-member hashes — so the ONLY
    // thing missing is the module-private live-verification capability. This
    // is the exact R1-P0-1 bypass attempt: a fabricated member table would
    // otherwise skip the live archive check entirely.
    const inspected = {
        archive_sha256: receipt.archive_sha256,
        members: Object.entries(receipt.members).map(([name, sha256]) => ({ name, type: 'file', sha256 })),
    };
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-cap' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding: { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' },
                receipt,
                inspected,
            }),
        err => err.code === 'SAFETY_ERROR' && /registered by this module/.test(err.message)
    );
});

test('V34e (R2-P0-1): spreading a GENUINE live result and replacing members is rejected (identity, not a symbol)', () => {
    const dir = tmpDir('fotmob-r2-p0-1-spread-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-cap' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-cap',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    const live = verifyLiveArchiveAgainstReceipt({ binding, receipt, options: { repositoryRoot: REPO_ROOT } });
    // the R2-P0-1 attack: `{ ...live, members: [...] }` copies any plain
    // enumerable property — the R1 symbol design was forgeable this way.
    // With the WeakSet identity registry the SPREAD OBJECT is a different
    // object and must be rejected outright.
    const forged = { ...live, members: [{ name: 'x.json', type: 'file', sha256: 'a'.repeat(64) }] };
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-cap' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding,
                receipt,
                inspected: forged,
            }),
        err => err.code === 'SAFETY_ERROR' && /registered by this module/.test(err.message)
    );
});

test('V34f (R2-P0-1): the registered inspection is deep-frozen (in-place member replacement is impossible)', () => {
    const dir = tmpDir('fotmob-r2-p0-1-frozen-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-cap' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-cap',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    const live = verifyLiveArchiveAgainstReceipt({ binding, receipt, options: { repositoryRoot: REPO_ROOT } });
    assert.strictEqual(Object.isFrozen(live), true);
    assert.strictEqual(Object.isFrozen(live.members), true);
    assert.strictEqual(Object.isFrozen(live.members[0]), true);
    assert.throws(
        () => {
            live.members[0].sha256 = '0'.repeat(64); // strict-mode mutation of a frozen row
        },
        TypeError
    );
    assert.throws(
        () => {
            live.members.length = 0; // frozen array
        },
        TypeError
    );
});

test('V34c (R1-P0-1): a GENUINE capability from a different archive is rejected (bound to the receipt archive)', () => {
    const dir = tmpDir('fotmob-r1-p0-1-crosscap-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-a' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt-a.json'),
    });
    // a second archive, live-verified, yields a REAL capability — but for a
    // DIFFERENT archive than this receipt's
    const pairB = buildPair({ source_match_id: '3901024' });
    const otherInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901024', pair: pairB }], { packageId: 'pkg-b' });
    const otherReceipt = writeFixtureReceipt({
        archivePath: otherInfo.archivePath,
        archiveSha256: otherInfo.archiveSha256,
        packageId: 'pkg-b',
        payloadMember: otherInfo.payloadMember,
        manifestMember: otherInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt-b.json'),
    });
    const liveOther = verifyLiveArchiveAgainstReceipt({
        binding: { sha256: otherInfo.archiveSha256, path: otherInfo.archivePath, receipt: '' },
        receipt: otherReceipt,
        options: { repositoryRoot: REPO_ROOT },
    });
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-a' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding: { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' },
                receipt,
                inspected: liveOther,
            }),
        err => err.code === 'SAFETY_ERROR' && /archive sha256 does not match the receipt/.test(err.message)
    );
});

test('V34d (R1-P0-1): a GENUINE capability is accepted (the per-run cached path is not regressed)', () => {
    const dir = tmpDir('fotmob-r1-p0-1-goodcap-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-cap' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-cap',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    const live = verifyLiveArchiveAgainstReceipt({ binding, receipt, options: { repositoryRoot: REPO_ROOT } });
    const loaded = verifyEntryAgainstReceipt({
        entry: { package: 'pkg-cap' },
        payloadFile: archiveInfo.payloadFile,
        manifestFile: archiveInfo.manifestFile,
        binding,
        receipt,
        inspected: live,
        options: { repositoryRoot: REPO_ROOT },
    });
    assert.strictEqual(loaded.payload.source_match_id, '3901023');
});

// ── R1-P2-1 / R1-P2-2: strict octal sizes + two zero end blocks (Codex
// ── round 1) ─────────────────────────────────────────────────────

test('R1-P2-1: parseOctal returns null for an all-NUL/space field (empty is not zero)', () => {
    assert.strictEqual(parseOctal(Buffer.alloc(12), 0, 12), null);
    assert.strictEqual(parseOctal(Buffer.alloc(12, 32), 0, 12), null); // spaces
    assert.strictEqual(parseOctal(Buffer.from('00000000000\0', 'utf8'), 0, 12), 0); // explicit zero IS a digit
    assert.strictEqual(parseOctal(Buffer.from('00000000123\0', 'utf8'), 0, 12), 83); // 0o123
});

test('R1-P2-1: an archive member with an all-NUL size field is rejected, not read as zero bytes', () => {
    const dir = tmpDir('fotmob-r1-p2-1-emptysize-');
    const archive = path.join(dir, 'emptysize.tar.gz');
    const header = rawTarHeader('payload.json', '0', 5);
    header.fill(0, 124, 136); // erase the size field (12 bytes all-NUL)
    let sum = 0;
    for (let i = 0; i < 512; i += 1) sum += i >= 148 && i < 156 ? 32 : header[i];
    header.write(sum.toString(8).padStart(6, '0') + '\0 ', 148, 'utf8');
    fs.writeFileSync(archive, gzipOf(Buffer.concat([rawTarBlock(header, Buffer.from('hello')), Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /not valid octal/.test(err.message)
    );
});

test('R1-P2-2: a single zero end block is rejected (truncated end-of-archive marker)', () => {
    const dir = tmpDir('fotmob-r1-p2-2-singlezero-');
    const archive = path.join(dir, 'singlezero.tar.gz');
    const tar = rawTarBlock(rawTarHeader('payload.json', '0', 3), Buffer.from('abc'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(512)]))); // ONE zero block only
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /two zero blocks required/.test(err.message)
    );
});

test('R1-P2-2: the same archive with two zero end blocks is accepted (control)', () => {
    const dir = tmpDir('fotmob-r1-p2-2-twozero-');
    const archive = path.join(dir, 'twozero.tar.gz');
    const tar = rawTarBlock(rawTarHeader('payload.json', '0', 3), Buffer.from('abc'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(inspected.members.length, 1);
    assert.strictEqual(inspected.members[0].size, 3);
});

// ── P1-1: ustar magic / prefix / normalized-path safety (Codex review
// ── 4863122944 P1-1) ───────────────────────────────────────────────

/**
 * Raw ustar header with a PREFIX field (155 bytes at 345) and configurable
 * magic ('ustar\0' standard or 'ustar ' GNU).
 */
function rawTarHeaderWithPrefix(name, prefix, typeflag, size, magic = 'ustar\0') {
    const buf = Buffer.alloc(512);
    buf.write(String(name), 0, 'utf8');
    buf.write('0000644\0', 100, 'utf8');
    buf.write('0000000\0', 108, 'utf8');
    buf.write('0000000\0', 116, 'utf8');
    buf.write(Number(size).toString(8).padStart(11, '0') + '\0', 124, 'utf8');
    buf.write('00000000000\0', 136, 'utf8');
    buf.write(String(typeflag), 156, 'utf8');
    buf.write(magic, 257, 'utf8');
    buf.write('00', 263, 'utf8');
    buf.write(String(prefix), 345, 'utf8');
    let sum = 0;
    for (let i = 0; i < 512; i += 1) {
        sum += i >= 148 && i < 156 ? 32 : buf[i];
    }
    buf.write(sum.toString(8).padStart(6, '0') + '\0 ', 148, 'utf8');
    return buf;
}

test('V35 (P1-1): ustar prefix=../ combined with name is rejected (traversal via prefix)', () => {
    const dir = tmpDir('fotmob-p1-1-prefixtrav-');
    const archive = path.join(dir, 'hostile.tar.gz');
    // standard ustar\0 magic, prefix=../ — the OLD code ignored prefix (its
    // 5-byte 'ustar' comparison never matched) and accepted this archive
    const tar = rawTarBlock(rawTarHeaderWithPrefix('payload.json', '../', '0', 1), Buffer.from('x'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /unsafe tar member name/.test(err.message)
    );
});

test('V36 (P1-1): ustar absolute prefix is rejected', () => {
    const dir = tmpDir('fotmob-p1-1-prefixabs-');
    const archive = path.join(dir, 'hostile.tar.gz');
    const tar = rawTarBlock(rawTarHeaderWithPrefix('payload.json', '/etc', '0', 1), Buffer.from('x'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /unsafe tar member name/.test(err.message)
    );
});

test('V37 (P1-1): ustar prefix containing a backslash is rejected', () => {
    const dir = tmpDir('fotmob-p1-1-prefixback-');
    const archive = path.join(dir, 'hostile.tar.gz');
    const tar = rawTarBlock(rawTarHeaderWithPrefix('payload.json', '..\\..\\etc', '0', 1), Buffer.from('x'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /unsafe tar member name/.test(err.message)
    );
});

test('V38 (P1-1): prefix+name combination duplicating another member is rejected', () => {
    const dir = tmpDir('fotmob-p1-1-dupnorm-');
    const archive = path.join(dir, 'hostile.tar.gz');
    // member 1: 'captures/x.json'; member 2: prefix 'captures', name
    // './x.json' → combined 'captures/./x.json' → normalized 'captures/x.json'
    const m1 = rawTarBlock(rawTarHeader('captures/x.json', '0', 1), Buffer.from('x'));
    const m2 = rawTarBlock(rawTarHeaderWithPrefix('./x.json', 'captures', '0', 1), Buffer.from('y'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([m1, m2, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /duplicate tar member path/.test(err.message)
    );
});

test('V39 (P1-1): standard ustar\\0 magic with a legal prefix is accepted and combined', () => {
    const dir = tmpDir('fotmob-p1-1-prefixok-');
    const archive = path.join(dir, 'legal.tar.gz');
    const tar = rawTarBlock(rawTarHeaderWithPrefix('payload.json', 'captures', '0', 1), Buffer.from('x'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(inspected.members.length, 1);
    assert.strictEqual(inspected.members[0].name, 'captures/payload.json');
});

test('V40 (P1-1): GNU ustar-space magic with a legal prefix is accepted and combined', () => {
    const dir = tmpDir('fotmob-p1-1-gnumagic-');
    const archive = path.join(dir, 'legal-gnu.tar.gz');
    const tar = rawTarBlock(rawTarHeaderWithPrefix('manifest.json', 'captures', '0', 1, 'ustar '), Buffer.from('y'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(inspected.members[0].name, 'captures/manifest.json');
});

test('V41 (P1-1): PAX path override forming a traversal path is rejected', () => {
    const dir = tmpDir('fotmob-p1-1-paxtrav-');
    const archive = path.join(dir, 'hostile-pax.tar.gz');
    const paxRecord = paxRecordFor('path', '../evil.json');
    const paxHeader = rawTarHeader('pax-override', 'x', paxRecord.length);
    const dataHeader = rawTarHeader('innocent.json', '0', 1);
    const tar = Buffer.concat([
        rawTarBlock(paxHeader, Buffer.from(paxRecord, 'utf8')),
        rawTarBlock(dataHeader, Buffer.from('x')),
    ]);
    fs.writeFileSync(archive, gzipOf(Buffer.concat([tar, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /unsafe tar member name/.test(err.message)
    );
});

test('V56 (R4-P1-1): a multi-pair archive needs per-entry member selectors — the receipt names only the first pair globally', () => {
    const dir = tmpDir('fotmob-ver-multipair-');
    const pairA = buildPair({ source_match_id: '3901023' });
    const pairB = buildPair({ source_match_id: '3900933' });
    const info = writeFixtureArchive(
        dir,
        [
            { sourceMatchId: '3901023', pair: pairA },
            { sourceMatchId: '3900933', pair: pairB },
        ],
        { packageId: 'pkg-multi' }
    );
    // ONE receipt for the whole archive — its global selectors name the
    // FIRST pair only (this is exactly what the `receipt` CLI command emits
    // for a multi-pair archive).
    const receiptPath = path.join(dir, 'receipt.json');
    writeFixtureReceipt({
        archivePath: info.archivePath,
        archiveSha256: info.archiveSha256,
        packageId: 'pkg-multi',
        payloadMember: info.payloadMember,
        manifestMember: info.manifestMember,
        receiptPath,
    });
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    const binding = { sha256: info.archiveSha256, path: info.archivePath, receipt: receiptPath };
    const outputRoot = path.join(dir, 'out');
    const baseEntry = id => ({
        source_match_id: id,
        payload_file: info.payloadFiles[id],
        manifest_file: info.manifestFiles[id],
        package: 'pkg-multi',
    });
    // first pair: no selectors needed (receipt global = first pair)
    const a = verifyEntryAgainstReceipt({
        entry: baseEntry('3901023'),
        binding,
        receipt,
        payloadFile: info.payloadFiles['3901023'],
        manifestFile: info.manifestFiles['3901023'],
        outputRoot,
        options: { repositoryRoot: REPO_ROOT },
    });
    assert.strictEqual(a.payload.source_match_id, '3901023');
    // second pair WITHOUT per-entry selectors must fail closed: its file
    // hash cannot match the receipt's global (first-pair) member — this was
    // the R4-P1-1 E008 batch-killer for two-pair archives.
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: baseEntry('3900933'),
                binding,
                receipt,
                payloadFile: info.payloadFiles['3900933'],
                manifestFile: info.manifestFiles['3900933'],
                outputRoot,
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR'
    );
    // second pair WITH per-entry selectors binds ITS members (receipt hash
    // map + live archive) and passes.
    const b = verifyEntryAgainstReceipt({
        entry: {
            ...baseEntry('3900933'),
            payload_member: info.payloadMembers['3900933'],
            manifest_member: info.manifestMembers['3900933'],
        },
        binding,
        receipt,
        payloadFile: info.payloadFiles['3900933'],
        manifestFile: info.manifestFiles['3900933'],
        outputRoot,
        options: { repositoryRoot: REPO_ROOT },
    });
    assert.strictEqual(b.payload.source_match_id, '3900933');
    assert.strictEqual(b.payloadFileSha256.length, 64);
});

test('V57 (R4-P3-2): GNU L long-name records with the standard trailing NUL are accepted; embedded NULs fail closed', () => {
    const dir = tmpDir('fotmob-ver-lnul-');
    // Real GNU tar writes `path\0` + NUL padding to the block boundary.
    const realName = 'pairs/1-3901023.payload.json';
    const nulTerminated = Buffer.concat([Buffer.from(realName + '\0', 'utf8'), Buffer.alloc(511 - realName.length)]);
    const longNameBlock = rawTarBlock(rawTarHeader('', 'L', nulTerminated.length), nulTerminated);
    const content = rawTarBlock(rawTarHeader('short-name', '0', 3), Buffer.from('abc'));
    const archive = path.join(dir, 'gnu-l-nul.tar.gz');
    fs.writeFileSync(archive, gzipOf(Buffer.concat([longNameBlock, content, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(inspected.members[0].name, realName, 'trailing NUL padding stripped, no NUL in the resolved name');

    // Embedded NUL inside the long-name payload is not padding — fail closed.
    const evilName = Buffer.from('pairs/1-3901023.payload\0.json', 'utf8');
    const evilBlock = rawTarBlock(rawTarHeader('', 'L', evilName.length), evilName);
    const evilArchive = path.join(dir, 'gnu-l-embedded-nul.tar.gz');
    fs.writeFileSync(evilArchive, gzipOf(Buffer.concat([evilBlock, content, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(evilArchive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('R10-P3-2a: a DANGLING GNU L long-name record at end-of-archive fails closed (no member consumes it)', () => {
    const dir = tmpDir('fotmob-ver-dangling-gnu-l-');
    const archive = path.join(dir, 'dangling-gnu-l.tar.gz');
    // A legal GNU long-name record followed DIRECTLY by the end-of-archive
    // zero blocks: the override names a member that never follows. The
    // parser must reject it, not silently drop the pending name.
    const realName = 'pairs/1-3901023.payload.json';
    const nulTerminated = Buffer.concat([Buffer.from(realName + '\0', 'utf8'), Buffer.alloc(511 - realName.length)]);
    const longNameBlock = rawTarBlock(rawTarHeader('', 'L', nulTerminated.length), nulTerminated);
    fs.writeFileSync(archive, gzipOf(Buffer.concat([longNameBlock, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /dangling GNU\/PAX name override/.test(err.message)
    );
});

test('R10-P3-2b: a DANGLING PAX x path record at end-of-archive fails closed (no member consumes it)', () => {
    const dir = tmpDir('fotmob-ver-dangling-pax-');
    const archive = path.join(dir, 'dangling-pax.tar.gz');
    // A legal PAX `path=../unsafe` record followed directly by the end
    // blocks: even though the record itself would be unsafe when applied,
    // the failure mode here is that NO member follows to consume it — the
    // dangling metadata must itself be a SAFETY_ERROR.
    const paxRecord = paxRecordFor('path', '../unsafe');
    const paxBlock = rawTarBlock(rawTarHeader('', 'x', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([paxBlock, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /dangling GNU\/PAX name override/.test(err.message)
    );
});

test('R11-P3-3a: PAX path records are split at BYTE boundaries — a legal non-ASCII path is accepted', () => {
    const dir = tmpDir('fotmob-ver-pax-utf8-');
    const archive = path.join(dir, 'pax-utf8.tar.gz');
    // `é` is 2 UTF-8 bytes: the record length counts bytes, and the parser
    // must not measure it in UTF-16 code units (which would make the record
    // one unit shorter and reject it as out of bounds).
    const unicodeName = 'pairs/1-3901023-é.payload.json';
    const paxRecord = paxRecordFor('path', unicodeName);
    const paxBlock = rawTarBlock(rawTarHeader('', 'x', Buffer.byteLength(paxRecord)), Buffer.from(paxRecord, 'utf8'));
    const content = rawTarBlock(rawTarHeader('short-name', '0', 3), Buffer.from('abc'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([paxBlock, content, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(inspected.members[0].name, unicodeName, 'byte-boundary parsing keeps the non-ASCII path intact');
});

// ── R12-P2-2 (Codex round 12): bounded archive inspection — a compression
//    bomb or oversized tar can never exhaust the process ───────────────────

test('R12-P2-2a: inspectArchive refuses a gzip whose decompressed size exceeds maxDecompressedBytes (SAFETY_ERROR)', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r12p22-bomb-'));
    const archive = createTarGz([{ name: 'pairs/1-3901023.payload.json', content: Buffer.alloc(4096, 1) }]);
    const archivePath = path.join(dir, 'bomb.tar.gz');
    fs.writeFileSync(archivePath, archive);
    assert.throws(
        () => inspectArchive(archivePath, { repositoryRoot: REPO_ROOT, limits: { maxDecompressedBytes: 1024 } }),
        err => err.code === 'SAFETY_ERROR' && /archive decompressed size exceeds the limit/.test(err.message)
    );
});

test('R12-P2-2b: inspectArchive refuses a compressed archive larger than maxCompressedBytes BEFORE reading it (SAFETY_ERROR)', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r12p22-size-'));
    // Incompressible content — the gzipped tar stays near its raw size, so
    // the pre-read fstat limit is what must fire.
    const archive = createTarGz([
        { name: 'pairs/1-3901023.payload.json', content: crypto.randomBytes(2048) },
    ]);
    const archivePath = path.join(dir, 'big.tar.gz');
    fs.writeFileSync(archivePath, archive);
    assert.throws(
        () => inspectArchive(archivePath, { repositoryRoot: REPO_ROOT, limits: { maxCompressedBytes: 64 } }),
        err => err.code === 'SAFETY_ERROR' && /input file exceeds the size limit/.test(err.message)
    );
});

test('R12-P2-2c: inspectArchive refuses an archive with more members than maxMembers (SAFETY_ERROR)', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r12p22-members-'));
    const archive = createTarGz([
        { name: 'pairs/1-3901023.payload.json', content: 'a' },
        { name: 'pairs/1-3901023.manifest.json', content: 'b' },
    ]);
    const archivePath = path.join(dir, 'many.tar.gz');
    fs.writeFileSync(archivePath, archive);
    assert.throws(
        () => inspectArchive(archivePath, { repositoryRoot: REPO_ROOT, limits: { maxMembers: 1 } }),
        err => err.code === 'SAFETY_ERROR' && /tar member count exceeds the limit/.test(err.message)
    );
});

test('R12-P2-2d: inspectArchive refuses a member larger than maxMemberBytes (SAFETY_ERROR)', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r12p22-member-size-'));
    const archive = createTarGz([
        { name: 'pairs/1-3901023.payload.json', content: Buffer.alloc(512, 1) },
    ]);
    const archivePath = path.join(dir, 'big-member.tar.gz');
    fs.writeFileSync(archivePath, archive);
    assert.throws(
        () => inspectArchive(archivePath, { repositoryRoot: REPO_ROOT, limits: { maxMemberBytes: 64 } }),
        err => err.code === 'SAFETY_ERROR' && /tar member size exceeds the limit/.test(err.message)
    );
});

test('R12-P2-2e (legal control): a normal archive passes inspection under the DEFAULT limits', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r12p22-legal-'));
    const archive = createTarGz([
        { name: 'pairs/1-3901023.payload.json', content: 'payload-bytes' },
        { name: 'pairs/1-3901023.manifest.json', content: 'manifest-bytes' },
    ]);
    const archivePath = path.join(dir, 'legal.tar.gz');
    fs.writeFileSync(archivePath, archive);
    const inspected = inspectArchive(archivePath, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(inspected.members.length, 2);
    assert.strictEqual(inspected.members[0].name, 'pairs/1-3901023.payload.json');
});
