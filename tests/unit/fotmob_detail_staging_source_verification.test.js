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
    // member is untouched) — must be rejected. R14-P2-1 (Codex round 14):
    // the added field also makes the file LARGER than its archive member,
    // so the member-derived read cap legitimately fires FIRST (the earlier
    // fail-closed layer); both layers are SAFETY_ERROR.
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
        err => err.code === 'SAFETY_ERROR' && /payload file sha256|input file exceeds the size limit/.test(err.message)
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
    // R14-P2-1: the tampered file is larger than its member, so the
    // member-derived read cap fires first; both layers are SAFETY_ERROR.
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
        err => err.code === 'SAFETY_ERROR' && /manifest file sha256|input file exceeds the size limit/.test(err.message)
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
    // R14-P2-1: if pair B's files happen to exceed member A's sizes the
    // member-derived read cap fires first; otherwise the member-hash
    // mismatch does — both layers are SAFETY_ERROR.
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
        err => err.code === 'SAFETY_ERROR' && /payload file sha256|manifest file sha256|input file exceeds the size limit/.test(err.message)
    );
});

// ── R14-P2-1 (Codex round 14): payload/manifest read pre-cap derived from
//    the LIVE ARCHIVE MEMBER size — an external file larger than its member
//    is refused at the fstat size gate BEFORE the read ─────────────────

test('R14-P2-1a: an external payload file larger than its live archive member is refused by the size gate before the SHA comparison', () => {
    const dir = tmpDir('fotmob-r14-p2-1a-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], {
        packageId: 'pkg-r14-p2-1a',
    });
    const receiptPath = path.join(dir, 'receipt.json');
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-r14-p2-1a',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath,
    });
    // The archive member is untouched; the EXTERNAL copy is padded well
    // beyond the member size. The read cap is derived from the LIVE member
    // (itself bounded by the archive limits), so the file must be refused
    // with SAFETY_ERROR at the fstat size gate — before any SHA comparison,
    // i.e. before the oversized bytes are ever allocated into memory.
    const oversizedPayload = Buffer.concat([
        fs.readFileSync(archiveInfo.payloadFile),
        Buffer.from('\n'.repeat(4096), 'utf8'),
    ]);
    fs.writeFileSync(archiveInfo.payloadFile, oversizedPayload);
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () => verifyEntryAgainstReceipt({
            entry: { package: 'pkg-r14-p2-1a' },
            payloadFile: archiveInfo.payloadFile,
            manifestFile: archiveInfo.manifestFile,
            binding,
            receipt,
            outputRoot: path.join(dir, 'out'),
            options: { repositoryRoot: REPO_ROOT },
        }),
        err => err.code === 'SAFETY_ERROR' && /input file exceeds the size limit/.test(err.message)
    );
    // legal control: restoring the exact member-size copy goes through clean
    fs.writeFileSync(archiveInfo.payloadFile, pair.payloadBytes);
    const loaded = verifyEntryAgainstReceipt({
        entry: { package: 'pkg-r14-p2-1a' },
        payloadFile: archiveInfo.payloadFile,
        manifestFile: archiveInfo.manifestFile,
        binding,
        receipt,
        outputRoot: path.join(dir, 'out'),
        options: { repositoryRoot: REPO_ROOT },
    });
    assert.strictEqual(loaded.payloadFileSha256, receipt.members[archiveInfo.payloadMember]);
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
        err => err.code === 'SAFETY_ERROR' && /not accepted by the exported API/.test(err.message)
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
        err => err.code === 'SAFETY_ERROR' && /not accepted by the exported API/.test(err.message)
    );
});

test('V34f (R17-P3-1): the inspection returned by verifyLiveArchiveAgainstReceipt is a PLAIN object — no reusable capability contract', () => {
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
    // R17-P3-1 (Codex round 17): the WeakSet registry and the deep-freeze
    // were REMOVED — the module never hands out a reusable capability, so
    // there is nothing left to register or freeze. The returned inspection
    // is an ordinary mutable object consumed only inside the call that
    // produced it; verifyEntryAgainstReceipt (the exported entry API) never
    // accepts it back (R16-P1-1, V34a-e).
    assert.strictEqual(Object.isFrozen(live), false);
    assert.strictEqual(Object.isFrozen(live.members), false);
    live.members[0].sha256 = '0'.repeat(64); // mutable — not a capability
    assert.strictEqual(live.members[0].sha256, '0'.repeat(64));
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
        err => err.code === 'SAFETY_ERROR' && /not accepted by the exported API/.test(err.message)
    );
});

test('V34d (R16-P1-1): a GENUINE registered capability is REFUSED by the exported API; the direct API loads clean', () => {
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
    // R16-P1-1 (Codex round 16): the exported API must not accept a reusable
    // capability — even a GENUINE one — because a WeakSet-registered object
    // proves only "once produced by this module", not "reflects the CURRENT
    // archive bytes" (the archive is mutable; see R16-P1-1a for the
    // replace-then-reuse attack). The per-entry path always freshly
    // re-inspects.
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-cap' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding,
                receipt,
                inspected: live,
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR' && /not accepted by the exported API/.test(err.message)
    );
    // legal control: the same entry WITHOUT an inspected capability loads
    // clean (fresh re-inspection passes for the un-replaced archive)
    const loaded = verifyEntryAgainstReceipt({
        entry: { package: 'pkg-cap' },
        payloadFile: archiveInfo.payloadFile,
        manifestFile: archiveInfo.manifestFile,
        binding,
        receipt,
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
        err => err.code === 'SAFETY_ERROR' && /dangling GNU\/PAX metadata override/.test(err.message)
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
        err => err.code === 'SAFETY_ERROR' && /dangling GNU\/PAX metadata override/.test(err.message)
    );
});

test('R17-P2-1a: a legal PAX size= override is applied as the member effective size (content, padding, hash)', () => {
    const dir = tmpDir('fotmob-ver-pax-size-');
    const archive = path.join(dir, 'pax-size.tar.gz');
    // The GNU-tar size-overflow shape: the PAX `x` header carries size=3,
    // and the following file header's OWN octal size field is 0 (the real
    // size lives only in the PAX record). The 3 content bytes exist in the
    // archive after the file header. Pre-fix, the parser read the header
    // size 0, advanced nothing, and hit a checksum mismatch on the content
    // bytes read as the next header — a legal archive could not stage.
    const paxRecord = paxRecordFor('size', '3');
    const paxBlock = rawTarBlock(rawTarHeader('', 'x', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
    const fileBlock = rawTarBlock(rawTarHeader('data.bin', '0', 0), Buffer.from('abc', 'utf8'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([paxBlock, fileBlock, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    const member = inspected.members.find(m => m.name === 'data.bin');
    assert.ok(member, 'data.bin member is present');
    assert.strictEqual(member.size, 3);
    assert.strictEqual(
        member.sha256,
        crypto.createHash('sha256').update('abc').digest('hex'),
        'content hash covers the PAX-effective 3 bytes'
    );
});

test('R17-P2-1b: PAX size + mtime + UTF-8 path records merge and apply to the next member', () => {
    const dir = tmpDir('fotmob-ver-pax-size-mixed-');
    const archive = path.join(dir, 'pax-size-mixed.tar.gz');
    // A legal record mix in ONE extended header: path override (non-ASCII),
    // size override, and an mtime record that is carried but unused. All
    // records must parse and the size override must win over the header's
    // 0-byte size field.
    const paxBytes = Buffer.from(
        paxRecordFor('path', '数据.json') + paxRecordFor('size', '5') + paxRecordFor('mtime', '1234567890'),
        'utf8'
    );
    const paxBlock = rawTarBlock(rawTarHeader('', 'x', paxBytes.length), paxBytes);
    const fileBlock = rawTarBlock(rawTarHeader('ignored.json', '0', 0), Buffer.from('hello', 'utf8'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([paxBlock, fileBlock, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    const member = inspected.members.find(m => m.name === '数据.json');
    assert.ok(member, 'PAX path override applies');
    assert.strictEqual(member.size, 5);
    assert.strictEqual(
        member.sha256,
        crypto.createHash('sha256').update('hello').digest('hex'),
        'content hash covers the PAX-effective 5 bytes'
    );
});

test('R17-P2-1c: a non-decimal / unsafe PAX size override fails closed', () => {
    const dir = tmpDir('fotmob-ver-pax-badsize-');
    // POSIX pax size is an unsigned decimal integer — a sign, whitespace,
    // a decimal point, an exponent or an overflow beyond the safe-integer
    // range must fail closed at the extended header, never be coerced into
    // a content bound.
    for (const bad of ['abc', '-3', '+3', '3.0', '1e3', '99999999999999999999']) {
        const archive = path.join(dir, `bad-${bad.replace(/[^0-9a-zA-Z]/g, '_')}.tar.gz`);
        const paxRecord = paxRecordFor('size', bad);
        const paxBlock = rawTarBlock(rawTarHeader('', 'x', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
        fs.writeFileSync(archive, gzipOf(Buffer.concat([paxBlock, Buffer.alloc(1024)])));
        assert.throws(
            () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
            err => err.code === 'SAFETY_ERROR' && /PAX size override is not a safe decimal integer/.test(err.message),
            `size=${bad} must fail closed`
        );
    }
});

test('R17-P2-1d: a DANGLING PAX size record at end-of-archive fails closed (no member consumes it)', () => {
    const dir = tmpDir('fotmob-ver-dangling-pax-size-');
    const archive = path.join(dir, 'dangling-pax-size.tar.gz');
    // A legal PAX `size=3` record followed directly by the end blocks: no
    // member follows to consume it — the unconsumed local-PAX metadata must
    // itself be a SAFETY_ERROR (R17-P2-1 extends the R10-P3-2 dangling rule
    // from path-only overrides to ANY pending local-PAX record).
    const paxRecord = paxRecordFor('size', '3');
    const paxBlock = rawTarBlock(rawTarHeader('', 'x', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([paxBlock, Buffer.alloc(1024)])));
    assert.throws(
        () => inspectArchive(archive, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR' && /dangling GNU\/PAX metadata override/.test(err.message)
    );
});

test('R17-P2-1e: consecutive PAX x headers accumulate — path from the first, size from the second (GNU tar merge)', () => {
    const dir = tmpDir('fotmob-ver-pax-x-x-');
    const archive = path.join(dir, 'pax-x-x.tar.gz');
    // Two extended headers in a row: the records MERGE for the next member
    // (GNU tar applies the accumulated records to the next file entry; a
    // later record wins) — path from the first x header, size from the
    // second, both consumed by the one member that follows.
    const pathPax = paxRecordFor('path', 'merged.bin');
    const sizePax = paxRecordFor('size', '4');
    const block1 = rawTarBlock(rawTarHeader('', 'x', pathPax.length), Buffer.from(pathPax, 'utf8'));
    const block2 = rawTarBlock(rawTarHeader('', 'x', sizePax.length), Buffer.from(sizePax, 'utf8'));
    const fileBlock = rawTarBlock(rawTarHeader('raw.bin', '0', 0), Buffer.from('data', 'utf8'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([block1, block2, fileBlock, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    const member = inspected.members.find(m => m.name === 'merged.bin');
    assert.ok(member, 'path from the first x header applies');
    assert.strictEqual(member.size, 4);
    assert.strictEqual(
        member.sha256,
        crypto.createHash('sha256').update('data').digest('hex'),
        'size from the second x header applies to content bounds and hash'
    );
});

test('R17-P2-1f: a pending PAX size override survives a GNU long-name record (x(size) → L → member)', () => {
    const dir = tmpDir('fotmob-ver-pax-l-size-');
    const archive = path.join(dir, 'pax-l-size.tar.gz');
    // The size override arrives BEFORE the GNU long-name record; it must
    // stay pending across the L metadata record and apply to the real
    // member that follows (GNU tar merge semantics), while the member NAME
    // comes from the L record.
    const longName = 'nested/deep/dir/a-very-long-member-name-that-overflows-the-100-byte-name-field.json';
    const sizePax = paxRecordFor('size', '6');
    const xBlock = rawTarBlock(rawTarHeader('', 'x', sizePax.length), Buffer.from(sizePax, 'utf8'));
    const lName = `${longName}\0`;
    const lBlock = rawTarBlock(rawTarHeader('', 'L', Buffer.byteLength(lName)), Buffer.from(lName, 'utf8'));
    const fileBlock = rawTarBlock(rawTarHeader('short', '0', 0), Buffer.from('abcdef', 'utf8'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([xBlock, lBlock, fileBlock, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    const member = inspected.members.find(m => m.name === longName);
    assert.ok(member, 'GNU long name applies after the PAX record');
    assert.strictEqual(member.size, 6);
    assert.strictEqual(
        member.sha256,
        crypto.createHash('sha256').update('abcdef').digest('hex'),
        'pending size override applies after the L record'
    );
});

test('R17-P2-1g: a PAX record before a DIRECTORY member is consumed by it (no dangling, following member intact)', () => {
    const dir = tmpDir('fotmob-ver-pax-dir-');
    const archive = path.join(dir, 'pax-dir.tar.gz');
    // A local-PAX record (path override + size=0) immediately before a
    // directory entry: the directory consumes the pending metadata (no
    // dangling error), has no content hash, and the member that follows is
    // parsed intact with the correct effective size.
    const paxBytes = Buffer.from(paxRecordFor('path', 'assets/') + paxRecordFor('size', '0'), 'utf8');
    const xBlock = rawTarBlock(rawTarHeader('', 'x', paxBytes.length), paxBytes);
    const dirBlock = rawTarBlock(rawTarHeader('assets', '5', 0), null);
    const fileBlock = rawTarBlock(rawTarHeader('assets/logo.json', '0', 2), Buffer.from('{}', 'utf8'));
    fs.writeFileSync(archive, gzipOf(Buffer.concat([xBlock, dirBlock, fileBlock, Buffer.alloc(1024)])));
    const inspected = inspectArchive(archive, { repositoryRoot: REPO_ROOT });
    const member = inspected.members.find(m => m.name === 'assets/logo.json');
    assert.ok(member, 'member after the directory is present');
    assert.strictEqual(member.size, 2);
    assert.strictEqual(
        member.sha256,
        crypto.createHash('sha256').update('{}').digest('hex'),
        'following member parsed with the correct content'
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

// ── R13-P2-1 (Codex round 13): the receipt entry's first SHA pass is
//    bounded like inspectArchive — a big archive is refused BEFORE any
//    allocation (runReceipt calls verifyArchive before the bounded
//    inspectArchive) ─────────────────────────────────────────────────

test('R13-P2-1a: verifyArchive refuses a compressed archive larger than maxCompressedBytes (receipt first pass)', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r13p21-size-'));
    // Incompressible content — the gzipped tar stays near its raw size, so
    // the pre-read fstat limit is what must fire in verifyArchive's SHA
    // pass, exactly like R12-P2-2b does for inspectArchive.
    const archive = createTarGz([
        { name: 'pairs/1-3901023.payload.json', content: crypto.randomBytes(2048) },
    ]);
    const archivePath = path.join(dir, 'big.tar.gz');
    fs.writeFileSync(archivePath, archive);
    assert.throws(
        () =>
            verifyArchive(archivePath, sha256Hex(archive), {
                repositoryRoot: REPO_ROOT,
                limits: { maxCompressedBytes: 64 },
            }),
        err => err.code === 'SAFETY_ERROR' && /input file exceeds the size limit/.test(err.message)
    );
});

test('R13-P2-1b (legal control): verifyArchive passes a real archive under the DEFAULT limits', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r13p21-legal-'));
    const pair = buildPair();
    const info = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-a' });
    const verified = verifyArchive(info.archivePath, info.archiveSha256, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(verified.archive_sha256, info.archiveSha256);
    assert.strictEqual(verified.archive_path, info.archivePath);
});

// ── R13-P2-2 (Codex round 13): the receipt↔binding SHA and the capability
//    path are enforced even when a registered live-verification capability
//    is supplied (the CLI's per-run cache skips live re-verification) ──

test('R13-P2-2a: a genuine capability does not bypass the receipt↔binding SHA check', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r13p22-shacap-'));
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-a' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    const live = verifyLiveArchiveAgainstReceipt({ binding, receipt, options: { repositoryRoot: REPO_ROOT } });
    // The attack: a GENUINE capability (archive A) with a binding whose
    // declared SHA is wrong. Before R13-P2-2 this PASSED — the SHA equality
    // check only ran inside verifyLiveArchiveAgainstReceipt, which the
    // capability branch skips entirely.
    const forgedBinding = { sha256: 'e'.repeat(64), path: archiveInfo.archivePath, receipt: '' };
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-a' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding: forgedBinding,
                receipt,
                inspected: live,
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR' && /does not match binding/.test(err.message)
    );
});

test('R13-P2-2b: a genuine capability for archive A is refused with a binding pointing at another archive', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fotmob-r13p22-pathcap-'));
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-a' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-a',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    const live = verifyLiveArchiveAgainstReceipt({ binding, receipt, options: { repositoryRoot: REPO_ROOT } });
    // a second, DIFFERENT archive whose path the forged binding points at
    // (declared SHA still A's — only the path lies)
    const pairB = buildPair({ source_match_id: '3901024' });
    const otherInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901024', pair: pairB }], { packageId: 'pkg-b' });
    const forgedBinding = { sha256: archiveInfo.archiveSha256, path: otherInfo.archivePath, receipt: '' };
    // R16-P1-1 supersedes the binding-path capability check: the exported
    // API refuses ANY supplied capability (the path lie could never be
    // reached — a capability proves nothing about the CURRENT archive), so
    // this attack is closed at the API boundary
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-a' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding: forgedBinding,
                receipt,
                inspected: live,
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR' && /not accepted by the exported API/.test(err.message)
    );
});

// ── R16-P1-1 (Codex round 16): the exported entry-verification API must
//    not accept a reusable inspected capability — an archive replaced at the
//    same path after a capability was issued would otherwise skip the
//    current re-verification. The live archive is always freshly
//    re-inspected per entry. ─────────────────────────────────────────

test('R16-P1-1a: an archive REPLACED at the same path after a capability was issued is caught by the fresh re-inspection', () => {
    const dir = tmpDir('fotmob-r16p11-replace-');
    const pair = buildPair({ source_match_id: '3901023' });
    const archiveInfo = writeFixtureArchive(dir, [{ sourceMatchId: '3901023', pair }], { packageId: 'pkg-replace' });
    const receipt = writeFixtureReceipt({
        archivePath: archiveInfo.archivePath,
        archiveSha256: archiveInfo.archiveSha256,
        packageId: 'pkg-replace',
        payloadMember: archiveInfo.payloadMember,
        manifestMember: archiveInfo.manifestMember,
        receiptPath: path.join(dir, 'receipt.json'),
    });
    const binding = { sha256: archiveInfo.archiveSha256, path: archiveInfo.archivePath, receipt: '' };
    // issue a GENUINE capability while the archive is still archive A
    const live = verifyLiveArchiveAgainstReceipt({ binding, receipt, options: { repositoryRoot: REPO_ROOT } });
    assert.strictEqual(live.archive_sha256, archiveInfo.archiveSha256);
    // the attacker replaces the archive AT THE SAME PATH with different
    // bytes (same member names so the member selectors still resolve) while
    // the receipt + payload/manifest files stay A's
    const replacedBytes = createTarGz([
        { name: archiveInfo.payloadMember, content: Buffer.concat([pair.payloadBytes, Buffer.from(' ')]) },
        { name: archiveInfo.manifestMember, content: '{"replaced":true}' },
    ]);
    fs.writeFileSync(archiveInfo.archivePath, replacedBytes);
    // 1) the OLD capability is refused outright by the exported API
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-replace' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding,
                receipt,
                inspected: live,
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR' && /not accepted by the exported API/.test(err.message)
    );
    // 2) the direct API (no capability) re-inspects the CURRENT bytes and
    //    catches the replacement — the attack is closed at the API boundary
    assert.throws(
        () =>
            verifyEntryAgainstReceipt({
                entry: { package: 'pkg-replace' },
                payloadFile: archiveInfo.payloadFile,
                manifestFile: archiveInfo.manifestFile,
                binding,
                receipt,
                options: { repositoryRoot: REPO_ROOT },
            }),
        err => err.code === 'SAFETY_ERROR' && /live archive sha256/.test(err.message)
    );
});

// ── R16-P2-1 (Codex round 16): a legal archive member named "__proto__"
//    (including a PAX path=__proto__ override) must keep its own hash in
//    the receipt — the old `{}` + `[name] =` write dropped it through the
//    legacy __proto__ setter, so legal archives could never complete
//    staging. ─────────────────────────────────────────────────────

test('R16-P2-1a: a PAX path=__proto__ member survives receipt → live reverify → entry load end-to-end', () => {
    const dir = tmpDir('fotmob-r16p21-paxproto-');
    const pair = buildPair({ source_match_id: '3901023' });
    const payloadFile = path.join(dir, '3901023.payload.json');
    const manifestFile = path.join(dir, '3901023.manifest.json');
    fs.writeFileSync(payloadFile, pair.payloadBytes);
    fs.writeFileSync(manifestFile, JSON.stringify(pair.manifest, null, 2) + '\n');
    const payloadMember = 'pairs/1-3901023.payload.json';
    const manifestMember = 'pairs/1-3901023.manifest.json';
    // legal member named "__proto__" via a PAX path= override (V12-style)
    const paxRecord = paxRecordFor('path', '__proto__');
    const paxBlock = rawTarBlock(rawTarHeader('', 'x', paxRecord.length), Buffer.from(paxRecord, 'utf8'));
    const protoContent = Buffer.from('{}', 'utf8');
    const protoBlock = rawTarBlock(rawTarHeader('__proto__', '0', protoContent.length), protoContent);
    const archiveBytes = gzipOf(
        Buffer.concat([
            rawTarBlock(rawTarHeader(payloadMember, '0', pair.payloadBytes.length), pair.payloadBytes),
            rawTarBlock(
                rawTarHeader(manifestMember, '0', Buffer.byteLength(JSON.stringify(pair.manifest, null, 2) + '\n')),
                Buffer.from(JSON.stringify(pair.manifest, null, 2) + '\n', 'utf8')
            ),
            paxBlock,
            protoBlock,
            Buffer.alloc(1024),
        ])
    );
    const archivePath = path.join(dir, 'fixture-pax-proto.tar.gz');
    fs.writeFileSync(archivePath, archiveBytes);
    const archiveSha256 = sha256Hex(archiveBytes);

    // receipt built via the REAL production path: inspectArchive (3 members)
    // → buildPackageReceipt — pre-fix the "__proto__" hash was dropped and
    // the receipt recorded only 2 members
    verifyArchive(archivePath, archiveSha256);
    const inspected = inspectArchive(archivePath, { repositoryRoot: REPO_ROOT });
    assert.deepStrictEqual(
        inspected.members.map(m => m.name).sort(),
        ['__proto__', payloadMember, manifestMember].sort()
    );
    const receipt = buildPackageReceipt({
        packageId: 'pkg-pax-proto',
        archivePath,
        archiveSha256,
        members: inspected.members,
        payloadMember,
        manifestMember,
    });
    // the receipt must carry the "__proto__" member as an own hash
    assert.ok(Object.prototype.hasOwnProperty.call(receipt.members, '__proto__'));
    assert.match(receipt.members.__proto__, /^[0-9a-f]{64}$/);
    assert.strictEqual(verifyPackageReceipt(receipt).ok, true);

    // live reverify: 3 members on both sides, hashes match (pre-fix this
    // failed with a member-set mismatch: live 3 vs receipt 2)
    const binding = { sha256: archiveSha256, path: archivePath, receipt: '' };
    assert.doesNotThrow(() => verifyLiveArchiveAgainstReceipt({ binding, receipt, options: { repositoryRoot: REPO_ROOT } }));

    // end-to-end: the entry loads — the "__proto__" member is part of the
    // managed inventory but is never extracted as payload/manifest
    const loaded = verifyEntryAgainstReceipt({
        entry: { package: 'pkg-pax-proto' },
        payloadFile,
        manifestFile,
        binding,
        receipt,
        options: { repositoryRoot: REPO_ROOT },
    });
    assert.strictEqual(loaded.payload.source_match_id, '3901023');
});

test('R16-P2-1b: buildPackageReceipt rejects a payloadMember reference to a MISSING "__proto__" member (hasOwnProperty, not the inherited accessor)', () => {
    const pair = buildPair({ source_match_id: '3901023' });
    const members = [
        { name: 'pairs/1-3901023.payload.json', sha256: 'a'.repeat(64) },
        { name: 'pairs/1-3901023.manifest.json', sha256: 'b'.repeat(64) },
    ];
    // pre-fix: `memberHashes['__proto__']` read through the inherited
    // Object.prototype accessor (truthy) even though no such member exists —
    // the receipt was built with a phantom reference
    assert.throws(
        () =>
            buildPackageReceipt({
                packageId: 'pkg-missing-proto',
                archivePath: '/tmp/any.tar.gz',
                archiveSha256: 'c'.repeat(64),
                members,
                payloadMember: '__proto__',
                manifestMember: 'pairs/1-3901023.manifest.json',
            }),
        err => err.code === 'INPUT_ERROR' && /payload member not found/.test(err.message)
    );
});

test('R16-P2-1c: verifyPackageReceipt fails closed when a parsed receipt references "__proto__" with no own member', () => {
    const pair = buildPair({ source_match_id: '3901023' });
    const valid = buildPackageReceipt({
        packageId: 'pkg-validator-proto',
        archivePath: '/tmp/any.tar.gz',
        archiveSha256: 'd'.repeat(64),
        members: [
            { name: 'pairs/1-3901023.payload.json', sha256: 'a'.repeat(64) },
            { name: 'pairs/1-3901023.manifest.json', sha256: 'b'.repeat(64) },
        ],
        payloadMember: 'pairs/1-3901023.payload.json',
        manifestMember: 'pairs/1-3901023.manifest.json',
    });
    // tamper: the receipt now references a member named "__proto__" that has
    // no own hash in the members table — the parsed doc has no own
    // "__proto__" member, so the inherited accessor must NOT satisfy it
    const tampered = JSON.parse(JSON.stringify(valid));
    tampered.payload_member = '__proto__';
    // receipt_sha256 intentionally left stale — the member-reference check
    // fires independently of the business-hash recomputation
    const validation = verifyPackageReceipt(tampered);
    assert.strictEqual(validation.ok, false);
    assert.ok(
        validation.errors.some(e => /payload_member must reference an existing member/.test(e)),
        JSON.stringify(validation.errors)
    );
});

// ── R16-P3-1 (Codex round 16): strict PAX parsing — a length-valid record
//    WITHOUT a key=value separator is malformed and must fail closed. ──

test('R16-P3-1: a length-valid PAX record without a key=value separator is rejected as SAFETY_ERROR', () => {
    // "9 broken\n": length field 9 is in bounds and the newline is present,
    // but there is no '=' — pre-fix this was silently ignored (empty records)
    assert.throws(
        () => parsePaxRecords('9 broken\n'),
        err => err.code === 'SAFETY_ERROR' && /missing key=value separator/.test(err.message)
    );
    // empty key (`=x`) is also malformed
    assert.throws(
        () => parsePaxRecords('5 =x\n'),
        err => err.code === 'SAFETY_ERROR' && /missing key=value separator/.test(err.message)
    );
    // legal control: well-formed records still parse
    const records = parsePaxRecords(paxRecordFor('path', 'pairs/1-3901023.payload.json'));
    assert.strictEqual(records.path, 'pairs/1-3901023.payload.json');
    // a legal PAX key "__proto__" is preserved as an own data property
    const proto = parsePaxRecords(paxRecordFor('__proto__', 'kept'));
    assert.ok(Object.prototype.hasOwnProperty.call(proto, '__proto__'));
    assert.strictEqual(proto.__proto__, 'kept');
});
